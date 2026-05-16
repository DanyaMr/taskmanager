"""
FastAPI endpoints для подразделения.
Обновленная версия с поддержкой чек-листов, оптимизации и RAG.
"""
from uuid import uuid4
import json
from fastapi.responses import HTMLResponse
from datetime import datetime
from typing import Dict, Any, List, Optional
from starlette.requests import Request
from fastapi import APIRouter, HTTPException, Query, Depends, status, Body

from department.database.service import DatabaseService
from department.models.employee import HumanEmployee, DigitalEmployee
from department.models.skill import SkillDetail, SkillLevel
from department.models.checklist import (
    Checklist, ChecklistItem, ChecklistVerification, VerificationStatus,
    TEMPLATE_CHECKLISTS, get_template
)
from department.services.planning import Planning, OptimizationResult
from department.services.control import ControlService
from department.llm.service import LLMService
from department.models.task import Task, TaskStatus, Priority
from department.services.forecasting import ForecastingService
from department.integration.enterprise_adapter import EnterpriseAdapter
from department.api.schemas import *
from department.database.db_models import *
from department.rag.retriever import TaskRetriever

# Создаем router для API
router = APIRouter(prefix="/api/v1", tags=["department"])

# Dependency для получения DB service
def get_db():
    return DatabaseService()

def get_llm_service():
    return LLMService()

def get_task_retriever():
    return TaskRetriever()

def priority_int_to_enum(priority_value: int) -> str:
    """Конвертирует integer priority в строковый enum"""
    priority_map = {
        1: "critical",
        2: "high",
        3: "medium",
        4: "low"
    }
    return priority_map.get(priority_value, "medium")


@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "fractal_level": "department",
        "version": "2.0.0",
        "features": {
            "rag_enabled": True,
            "llm_enabled": True,
            "checklists_enabled": True,
            "optimization_enabled": True
        }
    }


# === Checklist API ===

@router.get("/checklists/templates")
async def get_checklist_templates():
    """Получить доступные шаблоны чек-листов"""
    return {
        "templates": [
            {"name": "software_development", "description": "Для задач разработки ПО"},
            {"name": "hardware_maintenance", "description": "Для обслуживания оборудования"},
            {"name": "general_task", "description": "Общий шаблон"}
        ]
    }


@router.get("/checklists/templates/{template_name}")
async def get_checklist_template(template_name: str):
    """Получить конкретный шаблон чек-листа"""
    template = get_template(template_name)
    if not template:
        raise HTTPException(status_code=404, detail=f"Шаблон {template_name} не найден")
    return template.to_dict()


@router.post("/tasks/{task_id}/checklist/apply")
async def apply_checklist_template(
    task_id: str,
    template_name: str = Query(...),
    db: DatabaseService = Depends(get_db)
):
    """Применить шаблон чек-листа к задаче"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        template = get_template(template_name)
        if not template:
            raise HTTPException(status_code=404, detail=f"Шаблон {template_name} не найден")
        
        # Применяем шаблон
        template.task_id = task_id
        template.name = f"{template.name} для {task_db.title}"
        
        # Сохраняем в JSON поле
        task_db.metadata = task_db.metadata or {}
        task_db.metadata["checklist"] = template.to_dict()
        task_db.metadata["checklist_template"] = template_name
        
        session.commit()
        return {"success": True, "task_id": task_id, "template": template_name}
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/tasks/{task_id}/checklist")
async def get_task_checklist(task_id: str, db: DatabaseService = Depends(get_db)):
    """Получить чек-лист задачи"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        checklist_data = task_db.metadata.get("checklist") if task_db.metadata else None
        if not checklist_data:
            return {"checklist": None, "message": "Чек-лист не установлен"}
        
        return {"checklist": checklist_data}
    
    finally:
        session.close()


@router.post("/tasks/{task_id}/checklist/verify")
async def verify_checklist_item(
    task_id: str,
    item_id: str = Query(...),
    status: str = Query(...),
    verified_by: str = Query(...),
    comments: str = Body("", embed=True),
    db: DatabaseService = Depends(get_db)
):
    """Проверить элемент чек-листа"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        checklist_data = task_db.metadata.get("checklist") if task_db.metadata else None
        if not checklist_data:
            raise HTTPException(status_code=400, detail="Чек-лист не установлен")
        
        # Находим элемент
        items = checklist_data.get("items", [])
        item_exists = any(item["id"] == item_id for item in items)
        if not item_exists:
            raise HTTPException(status_code=404, detail=f"Элемент {item_id} не найден")
        
        # Обновляем верификацию
        verifications = checklist_data.get("verifications", {})
        verifications[item_id] = {
            "item_id": item_id,
            "status": status,
            "verified_by": verified_by,
            "verified_at": datetime.now().isoformat(),
            "comments": comments
        }
        
        checklist_data["verifications"] = verifications
        task_db.metadata["checklist"] = checklist_data
        
        # Проверяем завершение
        checklist = Checklist.from_dict(checklist_data)
        if checklist.is_complete() and task_db.status == "review":
            task_db.status = "done"
        
        session.commit()
        return {"success": True, "checklist_stats": checklist.get_completion_stats()}
    
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@router.get("/tasks/{task_id}/checklist/validate")
async def validate_task_completion(task_id: str, db: DatabaseService = Depends(get_db)):
    """Проверить возможность завершения задачи"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        checklist_data = task_db.metadata.get("checklist") if task_db.metadata else None
        
        if not checklist_data:
            return {
                "can_complete": task_db.status in ("review", "done"),
                "checklist_complete": True,
                "blocking_items": [],
                "message": "Чек-лист не установлен"
            }
        
        checklist = Checklist.from_dict(checklist_data)
        blocking_items = []
        
        for item in checklist.items:
            if not item.is_mandatory:
                continue
            verification = checklist.verifications.get(item.id)
            if not verification or verification.status != VerificationStatus.PASSED:
                blocking_items.append({
                    "item_id": item.id,
                    "title": item.title,
                    "reason": "Не пройдено обязательное требование"
                })
        
        return {
            "can_complete": len(blocking_items) == 0 and task_db.status in ("review", "done"),
            "blocking_items": blocking_items,
            "checklist_complete": checklist.is_complete(),
            "checklist_stats": checklist.get_completion_stats()
        }
    
    finally:
        session.close()


# === Optimization API ===

@router.post("/planning/optimize", response_model=Dict[str, Any])
async def optimize_task_assignment(
    days: int = Query(14, ge=1, le=60),
    db: DatabaseService = Depends(get_db)
):
    """
    Оптимизировать распределение задач методом линейного программирования.
    Минимизирует общее время выполнения.
    """
    session = db.Session()
    try:
        # Получаем задачи из backlog
        tasks_db = session.query(TaskDB).filter(
            TaskDB.status.in_(["backlog", "planned"])
        ).all()
        
        employees_db = session.query(EmployeeDB).all()
        
        if not tasks_db:
            return {"success": True, "message": "Нет задач для оптимизации", "assignments": []}
        
        if not employees_db:
            raise HTTPException(status_code=400, detail="Нет сотрудников")
        
        # Конвертируем в бизнес-модели
        from department.models.task import Task as TaskModel
        from department.models.employee import HumanEmployee, DigitalEmployee
        
        tasks = []
        for t in tasks_db:
            task = TaskModel(
                id=t.id,
                title=t.title,
                description=t.description or "",
                priority=Priority(t.priority) if isinstance(t.priority, int) else Priority.MEDIUM,
                estimated_effort=t.estimated_effort or 1.0,
                required_skills=t.required_skills or {},
                dependencies=t.dependencies or []
            )
            tasks.append(task)
        
        employees = []
        for e in employees_db:
            if e.type == "digital":
                emp = DigitalEmployee(id=e.id, name=e.name)
            else:
                emp = HumanEmployee(id=e.id, name=e.name)
            emp.current_load = e.current_load or 0.0
            emp.max_capacity = e.max_capacity or 40.0
            emp.performance_score = e.performance_score or 1.0
            
            # 🔧 Загружаем навыки из БД
            for skill_db in e.skills:
                # Создаём SkillDetail для SkillLevel
                skill_detail = SkillDetail(
                    id=skill_db.id,
                    name=skill_db.name,
                    description=skill_db.description,
                    category=skill_db.category,
                    is_digital=skill_db.is_digital
                )
                skill_level = SkillLevel(
                    skill=skill_detail,
                    level=1
                )
                emp.skills[skill_db.name] = skill_level
            
            employees.append(emp)
        
        # Запускаем оптимизацию
        planning = Planning(employees)
        result = planning.optimize_assignment(tasks, days=days)
        
        return result.to_dict()
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


# === RAG API ===

@router.get("/rag/statistics")
async def get_rag_statistics(
    db: DatabaseService = Depends(get_db)
):
    """Получить статистику RAG хранилища"""
    retriever = TaskRetriever()
    stats = retriever.get_statistics()
    return stats


@router.post("/rag/add-completed-task")
async def add_completed_task_to_rag(
    task_id: str = Query(...),
    db: DatabaseService = Depends(get_db),
    retriever: TaskRetriever = Depends(get_task_retriever)
):
    """Добавить выполненную задачу в RAG хранилище"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        if task_db.status != "done":
            raise HTTPException(status_code=400, detail="Задача не завершена")
        
        # Получаем сотрудника
        employee = None
        if task_db.assigned_id:
            employee = session.query(EmployeeDB).get(task_db.assigned_id)
        
        success = retriever.add_completed_task(
            task_id=task_id,
            title=task_db.title,
            description=task_db.description or "",
            actual_effort=task_db.actual_effort or task_db.estimated_effort,
            actual_duration_hours=8.0,  # Можно вычислять по датам
            skills_used=list((task_db.required_skills or {}).keys()),
            employee_type=employee.type if employee else "human"
        )
        
        return {"success": success, "task_id": task_id}
    
    finally:
        session.close()


@router.get("/tasks/{task_id}/similar")
async def get_similar_tasks(
    task_id: str,
    n_results: int = Query(5, ge=1, le=10),
    db: DatabaseService = Depends(get_db),
    retriever: TaskRetriever = Depends(get_task_retriever)
):
    """Найти похожие задачи в истории"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        # Создаем временную задачу для поиска
        from department.models.task import Task as TaskModel
        temp_task = TaskModel(
            id=task_id,
            title=task_db.title,
            description=task_db.description or "",
            required_skills=task_db.required_skills or {},
            dependencies=task_db.dependencies or []
        )
        
        similar = retriever.find_similar(temp_task, n_results=n_results)
        
        return {
            "query_task": {"id": task_id, "title": task_db.title},
            "similar_tasks": [
                {
                    "task_id": st.task_id,
                    "title": st.title,
                    "actual_effort": st.actual_effort,
                    "actual_duration_hours": st.actual_duration_hours,
                    "similarity_score": round(st.similarity_score, 3)
                }
                for st in similar
            ]
        }
    
    finally:
        session.close()


# === Forecasting API с RAG ===

@router.get("/tasks/{task_id}/forecast")
async def get_task_forecast(
    task_id: str,
    employee_type: str = Query("human", enum=["human", "digital"]),
    db: DatabaseService = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Получить прогноз выполнения задачи с использованием RAG + LLM"""
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        if not task_db:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        # Создаем модель задачи
        from department.models.task import Task as TaskModel
        task = TaskModel(
            id=task_id,
            title=task_db.title,
            description=task_db.description or "",
            priority=Priority(task_db.priority) if isinstance(task_db.priority, int) else Priority.MEDIUM,
            estimated_effort=task_db.estimated_effort or 1.0,
            required_skills=task_db.required_skills or {},
            dependencies=task_db.dependencies or []
        )
        
        # Получаем прогноз
        forecast = llm_service.predict_effort_with_rag(task, employee_type)
        
        return forecast.to_dict()
    
    finally:
        session.close()


@router.post("/forecast/batch")
async def get_batch_forecast(
    task_ids: List[str] = Body(...),
    employee_type: str = Body("human"),
    db: DatabaseService = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Получить прогнозы для пакета задач"""
    session = db.Session()
    try:
        from department.models.task import Task as TaskModel
        
        forecasts = {}
        for task_id in task_ids:
            task_db = session.query(TaskDB).get(task_id)
            if task_db:
                task = TaskModel(
                    id=task_id,
                    title=task_db.title,
                    description=task_db.description or "",
                    priority=Priority(task_db.priority) if isinstance(task_db.priority, int) else Priority.MEDIUM,
                    estimated_effort=task_db.estimated_effort or 1.0,
                    required_skills=task_db.required_skills or {},
                    dependencies=task_db.dependencies or []
                )
                forecast = llm_service.predict_effort_with_rag(task, employee_type)
                forecasts[task_id] = forecast.to_dict()
        
        return {"forecasts": forecasts, "count": len(forecasts)}
    
    finally:
        session.close()


# === Quality Metrics API ===

@router.get("/quality/metrics")
async def get_quality_metrics(db: DatabaseService = Depends(get_db)):
    """Получить метрики качества выполнения задач"""
    session = db.Session()
    try:
        tasks_db = session.query(TaskDB).all()
        
        from department.models.task import Task as TaskModel
        
        tasks = []
        for t in tasks_db:
            task = TaskModel(
                id=t.id,
                title=t.title,
                description=t.description or "",
                priority=Priority(t.priority) if isinstance(t.priority, int) else Priority.MEDIUM,
                estimated_effort=t.estimated_effort or 1.0,
                required_skills=t.required_skills or {},
                dependencies=t.dependencies or [],
                status=TaskStatus(t.status) if isinstance(t.status, str) else TaskStatus.BACKLOG,
                assigned_id=t.assigned_id,
                actual_effort=t.actual_effort,
                actual_duration_hours=t.metadata.get("actual_duration_hours") if t.metadata else None
            )
            
            # Загружаем чек-лист из metadata
            if t.metadata and "checklist" in t.metadata:
                task.checklist = Checklist.from_dict(t.metadata["checklist"])
            
            tasks.append(task)
        
        control_service = ControlService(tasks)
        return control_service.get_quality_metrics()
    
    finally:
        session.close()


@router.get("/quality/anomalies")
async def detect_quality_anomalies(db: DatabaseService = Depends(get_db)):
    """Обнаружить аномалии в выполнении задач"""
    session = db.Session()
    try:
        tasks_db = session.query(TaskDB).all()
        
        from department.models.task import Task as TaskModel
        
        tasks = []
        for t in tasks_db:
            task = TaskModel(
                id=t.id,
                title=t.title,
                description=t.description or "",
                priority=Priority(t.priority) if isinstance(t.priority, int) else Priority.MEDIUM,
                estimated_effort=t.estimated_effort or 1.0,
                status=TaskStatus(t.status) if isinstance(t.status, str) else TaskStatus.BACKLOG,
                assigned_id=t.assigned_id,
                actual_effort=t.actual_effort,
                created_at=t.created_at,
                assigned_at=t.assigned_at
            )
            tasks.append(task)
        
        control_service = ControlService(tasks)
        anomalies = control_service.detect_anomalies()
        
        return {"anomalies": anomalies, "count": len(anomalies)}
    
    finally:
        session.close()


# === Существующие endpoints (оставляем) ===
# (Предыдущие endpoints остаются без изменений, кроме добавления новых функций)

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_metrics(db: DatabaseService = Depends(get_db)):
    """Получить метрики дашборда с фрактальными показателями"""
    session = db.Session()
    try:
        total_tasks = session.query(TaskDB).count()
        completed_tasks = session.query(TaskDB).filter_by(status="done").count()
        total_employees = session.query(EmployeeDB).count()
        digital_employees = session.query(EmployeeDB).filter_by(type="digital").count()

        adapter = EnterpriseAdapter("DEPT_MAIN", "Главное подразделение")
        fractal_metrics = adapter.get_fractal_metrics()

        return DashboardResponse(
            timestamp=datetime.now(),
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=session.query(TaskDB).filter_by(status="in_progress").count(),
            blocked_tasks=session.query(TaskDB).filter_by(status="blocked").count(),
            total_employees=total_employees,
            digital_employees=digital_employees,
            automation_rate=fractal_metrics["automation_rate"],
            forecast_accuracy=fractal_metrics["forecast_accuracy"],
            capacity_utilization=fractal_metrics["capacity_utilization"]
        )
    finally:
        session.close()


@router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees_list(
    employee_type: Optional[str] = Query(None, enum=["human", "digital"]),
    db: DatabaseService = Depends(get_db)
):
    """Получить список сотрудников с фильтрацией по типу"""
    session = db.Session()
    try:
        query = session.query(EmployeeDB)
        if employee_type:
            query = query.filter_by(type=employee_type)

        employees = query.all()
        return [
            EmployeeResponse(
                id=e.id,
                name=e.name,
                type=e.type,
                current_load=e.current_load,
                max_capacity=e.max_capacity,
                performance_score=e.performance_score,
                skills_count=len(e.skills),
                skills=[{"id": s.id, "name": s.name, "category": s.category} for s in e.skills],
                is_overloaded=e.current_load > 0.8
            )
            for e in employees
        ]
    finally:
        session.close()


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = Query(None),
    assigned_id: Optional[str] = Query(None),
    db: DatabaseService = Depends(get_db)
):
    """Получить задачи с фильтрацией"""
    session = db.Session()
    try:
        query = session.query(TaskDB)

        if status:
            query = query.filter(TaskDB.status == status)
        if assigned_id:
            query = query.filter(TaskDB.assigned_id == assigned_id)

        tasks = query.all()

        return [
            TaskResponse(
                id=t.id,
                title=t.title,
                description=t.description or "",
                status=TaskStatusResponse(t.status),
                priority=PriorityResponse(priority_int_to_enum(t.priority)),
                priority_value=t.priority,
                estimated_effort=t.estimated_effort,
                actual_effort=t.actual_effort,
                assigned_id=t.assigned_id,
                assigned_at=t.assigned_at,
                assignee_name=t.assignee.name if t.assignee else None,
                deadline=t.deadline,
                dependencies=json.loads(t.dependencies) if isinstance(t.dependencies, str) and t.dependencies else (t.dependencies or []),
                is_overdue=t.deadline is not None and t.deadline < datetime.now(),
                is_decomposed=t.is_decomposed,
                fractal_level=FractalLevel.DEPARTMENT
            )
            for t in tasks
        ]
    finally:
        session.close()


# === Дополнительные endpoint'ы для фронтенда ===

@router.get("/tasks/filtered")
async def get_filtered_tasks(
    status: Optional[str] = Query(None),
    assigned_id: Optional[str] = Query(None),
    db: DatabaseService = Depends(get_db)
):
    """Получить задачи с фильтрацией (для фронтенда)"""
    session = db.Session()
    try:
        query = session.query(TaskDB)

        if status:
            query = query.filter(TaskDB.status == status)
        if assigned_id:
            if assigned_id == "unassigned":
                query = query.filter(TaskDB.assigned_id.is_(None))
            else:
                query = query.filter(TaskDB.assigned_id == assigned_id)

        tasks = query.all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description or "",
                "status": t.status,
                "priority": priority_int_to_enum(t.priority),
                "estimated_effort": t.estimated_effort,
                "assigned_id": t.assigned_id,
                "assignee_name": t.assignee.name if t.assignee else None,
            }
            for t in tasks
        ]
    finally:
        session.close()


@router.get("/tasks/unassigned")
async def get_unassigned_tasks(db: DatabaseService = Depends(get_db)):
    """Получить все неназначенные задачи"""
    session = db.Session()
    try:
        tasks = session.query(TaskDB).filter(TaskDB.assigned_id.is_(None)).all()
        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description or '',
                "priority": priority_int_to_enum(t.priority),
                "estimated_effort": t.estimated_effort,
                "required_skills": t.required_skills if t.required_skills else {},
                "deadline": t.deadline.isoformat() if t.deadline else None,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in tasks
        ]
    finally:
        session.close()


@router.get("/tasks/{task_id}")
async def get_task_by_id(task_id: str, db: DatabaseService = Depends(get_db)):
    """Получить задачу по ID"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "status": task.status,
            "priority": priority_int_to_enum(task.priority),
            "estimated_effort": task.estimated_effort,
            "actual_effort": task.actual_effort,
            "assigned_id": task.assigned_id,
            "assignee_name": task.assignee.name if task.assignee else None,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "dependencies": task.dependencies or [],
            "is_decomposed": task.is_decomposed
        }
    finally:
        session.close()


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, db: DatabaseService = Depends(get_db)):
    """Создать новую задачу"""
    session = db.Session()
    try:
        # Проверяем, существует ли задача с таким ID
        existing = session.query(TaskDB).get(task.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Задача с ID {task.id} уже существует")

        priority_map = {
            "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "TRIVIAL": 3
        }
        priority_value = priority_map.get(task.priority.upper(), 3)

        created_at = datetime.now()
        task_db = TaskDB(
            id=task.id,
            title=task.title,
            description=task.description,
            priority=priority_value,
            status="backlog",
            estimated_effort=task.estimated_effort,
            required_skills=task.required_skills,
            dependencies=task.dependencies,
            created_at=created_at,
            deadline=task.deadline
        )
        session.add(task_db)
        session.commit()

        return TaskResponse(
            id=task.id,
            title=task.title,
            description=task.description,
            status="backlog",
            priority=PriorityResponse(task.priority.lower()),
            estimated_effort=task.estimated_effort,
            dependencies=task.dependencies or [],
            is_overdue=False,
            assigned_id=None,
            assignee_name=None
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания задачи: {str(e)}")
    finally:
        session.close()


@router.get("/employees/available")
async def get_available_employees(db: DatabaseService = Depends(get_db)):
    """Получить всех доступных сотрудников для назначения задач"""
    session = db.Session()
    try:
        employees = session.query(EmployeeDB).all()
        return [
            {
                "id": emp.id,
                "name": emp.name,
                "type": emp.type,
                "current_load": emp.current_load,
                "max_capacity": emp.max_capacity,
                "performance_score": emp.performance_score,
                "skills": [{"id": s.id, "name": s.name} for s in emp.skills]
            }
            for emp in employees
        ]
    finally:
        session.close()


@router.get("/employees/detailed")
async def get_employees_detailed(db: DatabaseService = Depends(get_db)):
    """Получить детальную информацию о сотрудниках с задачами"""
    session = db.Session()
    try:
        employees = session.query(EmployeeDB).all()
        result = []
        for emp in employees:
            tasks = session.query(TaskDB).filter_by(assigned_id=emp.id).all()
            result.append({
                "id": emp.id,
                "name": emp.name,
                "type": emp.type,
                "current_load": emp.current_load,
                "max_capacity": emp.max_capacity,
                "skills": [{"id": s.id, "name": s.name} for s in emp.skills],
                "task_count": len(tasks),
                "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in tasks]
            })
        return result
    finally:
        session.close()


@router.get("/skills", response_model=List[SkillResponse])
async def get_all_skills(db: DatabaseService = Depends(get_db)):
    """Получить список всех навыков"""
    session = db.Session()
    try:
        skills = session.query(SkillDB).all()
        return [
            SkillResponse(
                id=skill.id,
                name=skill.name,
                description=skill.description,
                category=skill.category,
                is_digital=skill.is_digital
            )
            for skill in skills
        ]
    finally:
        session.close()


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(employee: EmployeeCreate, db: DatabaseService = Depends(get_db)):
    """Создать нового сотрудника"""
    session = db.Session()
    try:
        # Проверяем, существует ли сотрудник с таким ID
        existing = session.query(EmployeeDB).get(employee.id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Сотрудник с ID {employee.id} уже существует")

        emp_db = EmployeeDB(
            id=employee.id,
            name=employee.name,
            type=employee.type,
            max_capacity=employee.max_capacity,
            current_load=0.0,
            performance_score=employee.performance_score or 1.0,
            config={}
        )
        session.add(emp_db)
        
        # 🔧 Привязываем навыки из employee.skill_ids
        if employee.skill_ids:
            for skill_id in employee.skill_ids:
                skill = session.query(SkillDB).get(skill_id)
                if skill:
                    emp_db.skills.append(skill)
                    print(f"✅ Added skill {skill.name} to employee {employee.name}")
        
        session.commit()

        return EmployeeResponse(
            id=employee.id,
            name=employee.name,
            type=employee.type,
            current_load=0.0,
            max_capacity=employee.max_capacity,
            performance_score=employee.performance_score or 1.0,
            skills_count=len(emp_db.skills),
            skills=[{"id": s.id, "name": s.name, "category": s.category} for s in emp_db.skills],
            is_overloaded=False
        )
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка создания сотрудника: {str(e)}")
    finally:
        session.close()


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(employee_id: str, db: DatabaseService = Depends(get_db)):
    """Удалить сотрудника"""
    session = db.Session()
    try:
        employee = session.query(EmployeeDB).get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник {employee_id} не найден")
        
        # Проверяем, есть ли назначенные задачи
        assigned_tasks = session.query(TaskDB).filter_by(assigned_id=employee_id).all()
        if assigned_tasks:
            raise HTTPException(
                status_code=400,
                detail=f"Нельзя удалить: назначено задач: {len(assigned_tasks)}. Сначала переназначьте задачи."
            )
        
        # Удаляем связи с навыками
        employee.skills = []
        session.delete(employee)
        session.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления сотрудника: {str(e)}")
    finally:
        session.close()


# Алиас для фронтенда (без /v1/) - используем include_router с другим префиксом
# Это нужно для совместимости с JavaScript, который делает запросы на /api/employees/
router_legacy = APIRouter(tags=["department_legacy"])

@router_legacy.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee_legacy(employee_id: str, db: DatabaseService = Depends(get_db)):
    """Удалить сотрудника (алиас для совместимости)"""
    session = db.Session()
    try:
        employee = session.query(EmployeeDB).get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник {employee_id} не найден")
        
        assigned_tasks = session.query(TaskDB).filter_by(assigned_id=employee_id).all()
        if assigned_tasks:
            raise HTTPException(
                status_code=400,
                detail=f"Нельзя удалить: назначено задач: {len(assigned_tasks)}. Сначала переназначьте задачи."
            )
        
        employee.skills = []
        session.delete(employee)
        session.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления сотрудника: {str(e)}")
    finally:
        session.close()

# Включаем legacy router в main.py с префиксом /api


# === Назначение задач ===

@router.put("/tasks/{task_id}/assign")
async def assign_task_to_employee(
    task_id: str,
    employee_id: str = Query(...),
    db: DatabaseService = Depends(get_db)
):
    """Назначить задачу сотруднику"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        employee = session.query(EmployeeDB).get(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail=f"Сотрудник {employee_id} не найден")
        
        task.assigned_id = employee_id
        task.assigned_at = datetime.now()
        task.status = "planned"
        
        session.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "employee_id": employee_id,
            "assigned_at": task.assigned_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка назначения задачи: {str(e)}")
    finally:
        session.close()


@router.put("/tasks/{task_id}/unassign")
async def unassign_task(
    task_id: str,
    db: DatabaseService = Depends(get_db)
):
    """Снять задачу с исполнителя"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        task.assigned_id = None
        task.assigned_at = None
        task.status = "backlog"
        
        session.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Задача снята с исполнителя"
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка снятия задачи: {str(e)}")
    finally:
        session.close()


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: DatabaseService = Depends(get_db)
):
    """Удалить задачу"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        # Проверяем, есть ли подзадачи
        subtasks = session.query(TaskDB).filter(TaskDB.dependencies.contains([task_id])).all()
        if subtasks:
            raise HTTPException(
                status_code=400,
                detail=f"Нельзя удалить: есть {len(subtasks)} подзадач. Сначала удалите подзадачи."
            )
        
        session.delete(task)
        session.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления задачи: {str(e)}")
    finally:
        session.close()


@router.put("/tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: str = Query(...),
    db: DatabaseService = Depends(get_db)
):
    """Обновить статус задачи"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        valid_statuses = ["backlog", "planned", "in_progress", "review", "done", "blocked"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Неверный статус. Допустимые: {valid_statuses}")
        
        task.status = status
        session.commit()
        
        return {"success": True, "task_id": task_id, "new_status": status}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления статуса: {str(e)}")
    finally:
        session.close()


@router.put("/tasks/{task_id}/priority")
async def update_task_priority(
    task_id: str,
    priority: str = Query(...),
    db: DatabaseService = Depends(get_db)
):
    """Обновить приоритет задачи"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        priority_map = {
            "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "TRIVIAL": 3,
            "critical": 1, "high": 2, "medium": 3, "low": 4
        }
        priority_value = priority_map.get(priority)
        if priority_value is None:
            raise HTTPException(status_code=400, detail=f"Неверный приоритет: {priority}")
        
        task.priority = priority_value
        session.commit()
        
        return {"success": True, "task_id": task_id, "new_priority": priority}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления приоритета: {str(e)}")
    finally:
        session.close()


@router.put("/tasks/{task_id}/skills")
async def update_task_skills(
    task_id: str,
    skills: Dict[str, int],
    db: DatabaseService = Depends(get_db)
):
    """Обновить навыки задачи"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        task.required_skills = skills
        session.commit()
        
        return {"success": True, "task_id": task_id, "skills": skills}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления навыков: {str(e)}")
    finally:
        session.close()


@router.put("/tasks/{task_id}/effort")
async def update_task_effort(
    task_id: str,
    effort: float = Query(...),
    db: DatabaseService = Depends(get_db)
):
    """Обновить оценку трудоемкости задачи"""
    session = db.Session()
    try:
        task = session.query(TaskDB).get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        task.estimated_effort = effort
        session.commit()
        
        return {"success": True, "task_id": task_id, "effort": effort}
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка обновления оценки: {str(e)}")
    finally:
        session.close()


# === Декомпозиция и перераспределение ===

@router.post("/tasks/{task_id}/decompose")
async def decompose_task(
    task_id: str,
    max_subtasks: int = Query(5, ge=1, le=10),
    db: DatabaseService = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Декомпозировать задачу на подзадачи через LLM"""
    print(f"=== DECOMPOSE START: task_id={task_id}")
    
    session = db.Session()
    try:
        task_db = session.query(TaskDB).get(task_id)
        print(f"=== Task DB: {task_db is not None}")
        
        if not task_db:
            raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
        
        # Создаем модель задачи
        from department.models.task import Task as TaskModel
        task = TaskModel(
            id=task_id,
            title=task_db.title,
            description=task_db.description or "",
            priority=Priority(task_db.priority) if isinstance(task_db.priority, int) else Priority.MEDIUM,
            estimated_effort=task_db.estimated_effort or 1.0,
            required_skills=task_db.required_skills or {},
            dependencies=task_db.dependencies or []
        )
        
        # Вызываем LLM для декомпозиции
        print(f"=== Calling LLM decompose...")
        subtasks = llm_service.decompose_task_sync(task, max_subtasks)
        print(f"=== LLM returned {len(subtasks)} subtasks")
        print(f"=== Subtasks: {subtasks}")
        
        if not subtasks:
            print("=== No subtasks, using mock")
            subtasks = llm_service._mock_decompose(task, max_subtasks)
        
        # Проверяем, существуют ли уже подзадачи - удаляем их
        import json
        for i in range(max_subtasks):
            existing_subtask_id = f"{task_id}_sub{i+1}"
            existing_subtask = session.query(TaskDB).get(existing_subtask_id)
            if existing_subtask:
                print(f"=== Deleting existing subtask {existing_subtask_id}")
                session.delete(existing_subtask)
        
        # Сохраняем подзадачи в БД
        created_subtasks = []
        for i, subtask in enumerate(subtasks):
            subtask_id = f"{task_id}_sub{i+1}"
            print(f"=== Creating subtask {subtask_id}")
            
            subtask_db = TaskDB(
                id=subtask_id,
                title=subtask.get("title", f"{task_db.title} - Часть {i+1}"),
                description=subtask.get("description", ""),
                priority=task_db.priority,
                status="backlog",
                estimated_effort=float(subtask.get("estimated_effort", task_db.estimated_effort / len(subtasks))),
                required_skills=task_db.required_skills or {},
                dependencies=json.dumps([task_id]),
                created_at=datetime.now()
            )
            session.add(subtask_db)
            created_subtasks.append({
                "id": subtask_id,
                "title": subtask.get("title", ""),
                "estimated_effort": float(subtask.get("estimated_effort", 0))
            })
            print(f"=== Subtask {subtask_id} added")
        
        task_db.is_decomposed = True
        print(f"=== Committing...")
        session.commit()
        print(f"=== SUCCESS: Created {len(created_subtasks)} subtasks")
        
        return {
            "task_id": task_id,
            "subtasks": created_subtasks,
            "count": len(created_subtasks)
        }
    except HTTPException as http_exc:
        print(f"=== HTTPException: {http_exc.detail}")
        raise
    except Exception as e:
        session.rollback()
        print(f"=== ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Ошибка декомпозиции: {str(e)}")
    finally:
        session.close()
        print(f"=== Session closed")


@router.post("/planning/redistribute")
async def redistribute_tasks(
    days: int = Query(14, ge=1, le=60),
    db: DatabaseService = Depends(get_db)
):
    """Перераспределить задачи оптимально через линейное программирование"""
    import traceback as tb
    session = db.Session()
    try:
        print("=== REDISTRIBUTE START ===")
        
        # Получаем нераспределенные задачи
        tasks_db = session.query(TaskDB).filter(
            TaskDB.assigned_id.is_(None),
            TaskDB.status.in_(["backlog", "planned"])
        ).all()
        print(f"=== Found {len(tasks_db)} unassigned tasks")
        
        employees_db = session.query(EmployeeDB).all()
        print(f"=== Found {len(employees_db)} employees")
        
        if not tasks_db:
            print("=== No tasks to redistribute")
            return {
                "success": True,
                "message": "Нет нераспределенных задач",
                "saved_assignments": 0,
                "assignments": []
            }
        
        if not employees_db:
            print("=== No employees available")
            raise HTTPException(status_code=400, detail="Нет сотрудников")
        
        # Конвертируем в бизнес-модели
        from department.models.task import Task as TaskModel
        from department.models.employee import HumanEmployee, DigitalEmployee
        
        tasks = []
        for t in tasks_db:
            task = TaskModel(
                id=t.id,
                title=t.title,
                description=t.description or "",
                priority=Priority(t.priority) if isinstance(t.priority, int) else Priority.MEDIUM,
                estimated_effort=t.estimated_effort or 1.0,
                required_skills=t.required_skills or {},
                dependencies=t.dependencies or []
            )
            tasks.append(task)
        print(f"=== Converted {len(tasks)} tasks")
        
        employees = []
        for e in employees_db:
            if e.type == "digital":
                emp = DigitalEmployee(id=e.id, name=e.name)
            else:
                emp = HumanEmployee(id=e.id, name=e.name)
            emp.current_load = e.current_load or 0.0
            emp.max_capacity = e.max_capacity or 40.0
            emp.performance_score = e.performance_score or 1.0
            
            # 🔧 Загружаем навыки из БД
            skill_names = [s.name for s in e.skills]
            print(f"=== Employee {e.name} ({e.type}) has {len(e.skills)} skills: {skill_names}")
            for skill_db in e.skills:
                # Создаём SkillDetail для SkillLevel
                skill_detail = SkillDetail(
                    id=skill_db.id,
                    name=skill_db.name,
                    description=skill_db.description,
                    category=skill_db.category,
                    is_digital=skill_db.is_digital
                )
                skill_level = SkillLevel(
                    skill=skill_detail,
                    level=1
                )
                emp.skills[skill_db.name] = skill_level
                print(f"    Added skill: {skill_db.name} -> {skill_level.level}")
            
            employees.append(emp)
        print(f"=== Converted {len(employees)} employees")
        
        # Запускаем оптимизацию
        print("=== Starting Planning optimization...")
        from department.services.planning import Planning
        planning = Planning(employees)
        result = planning.optimize_assignment(tasks, days=days)
        print(f"=== Optimization result: success={result.success}, assignments={len(result.assignments)}")
        
        # Сохраняем назначения в БД
        saved_count = 0
        for assignment in result.assignments:
            task = session.query(TaskDB).get(assignment.task_id)
            if task:
                task.assigned_id = assignment.employee_id
                task.assigned_at = datetime.now()
                task.status = "planned"
                saved_count += 1
        
        session.commit()
        print(f"=== SUCCESS: Saved {saved_count} assignments")
        
        return {
            "success": True,
            "saved_assignments": saved_count,
            "total_time_hours": result.total_time,
            "message": result.message,
            "assignments": result.assignments
        }
    except HTTPException:
        print("=== HTTPException raised")
        raise
    except Exception as e:
        session.rollback()
        print("=== EXCEPTION occurred!")
        print(f"=== Error: {type(e).__name__}: {e}")
        print("=== Traceback:")
        print(tb.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка перераспределения: {str(e)}")
    finally:
        session.close()
        print("=== Session closed")
