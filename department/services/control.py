"""
Сервис контроля (мониторинг, отчетность и проверка чек-листов).
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from department.models.task import Task, TaskStatus
from department.models.checklist import (
    Checklist, ChecklistItem, ChecklistVerification, VerificationStatus
)
from department.models.employee import Employee


class ControlService:
    """
    Контроль выполнения задач, проверка чек-листов и отчетность.
    
    Функции:
    - Мониторинг статусов задач
    - Проверка чек-листов
    - Отчетность по сотрудникам
    - Обнаружение аномалий
    """
    
    def __init__(self, tasks: List[Task], employees: Optional[List[Employee]] = None):
        """
        Инициализация сервиса контроля.
        
        Args:
            tasks: Список задач для контроля
            employees: Список сотрудников (опционально)
        """
        self.tasks = tasks
        self.employees = employees or []
        self._tasks_by_id = {task.id: task for task in tasks}
    
    def get_status_report(self) -> Dict[str, Any]:
        """Получить сводный отчет по статусам задач"""
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for t in self.tasks if t.status == status)
        
        total = len(self.tasks)
        completion_rate = status_counts[TaskStatus.DONE.value] / total if total > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": total,
            "status_breakdown": status_counts,
            "completion_rate": round(completion_rate, 3),
            "blocked_tasks": status_counts.get(TaskStatus.BLOCKED.value, 0),
            "in_review": status_counts.get(TaskStatus.REVIEW.value, 0)
        }
    
    def get_employee_workload(self, employee_id: str) -> Dict[str, Any]:
        """Получить загрузку сотрудника"""
        assigned_tasks = [t for t in self.tasks if t.assigned_id == employee_id]
        completed = sum(1 for t in assigned_tasks if t.status == TaskStatus.DONE)
        in_progress = sum(1 for t in assigned_tasks if t.status == TaskStatus.IN_PROGRESS)
        planned = sum(1 for t in assigned_tasks if t.status == TaskStatus.PLANNED)
        
        total_effort = sum(t.estimated_effort for t in assigned_tasks)
        actual_effort = sum(t.actual_effort for t in assigned_tasks if t.actual_effort)
        
        return {
            "employee_id": employee_id,
            "total_assigned": len(assigned_tasks),
            "completed": completed,
            "in_progress": in_progress,
            "planned": planned,
            "completion_rate": round(completed / len(assigned_tasks), 3) if assigned_tasks else 0,
            "total_effort": total_effort,
            "actual_effort": actual_effort,
            "effort_variance": round((actual_effort - total_effort) / total_effort, 3) if total_effort > 0 else 0
        }
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Обнаружить аномалии в выполнении задач.
        
        Аномалии:
        - Задачи в статусе "в работе" более 30 дней
        - Задачи в REVIEW более 7 дней
        - Фактическая трудоемкость > 2x от оценки
        """
        anomalies = []
        now = datetime.now()
        
        for task in self.tasks:
            # Аномалия: задачи в статусе "в работе" более 30 дней
            if task.status == TaskStatus.IN_PROGRESS:
                age_days = (now - task.created_at).days
                if age_days > 30:
                    anomalies.append({
                        "type": "stalled_task",
                        "task_id": task.id,
                        "title": task.title,
                        "message": f"Задача в работе {age_days} дней",
                        "severity": "high",
                        "age_days": age_days
                    })
            
            # Аномалия: задачи в REVIEW более 7 дней
            if task.status == TaskStatus.REVIEW:
                # Используем assigned_at как время перехода в REVIEW
                if task.assigned_at:
                    review_days = (now - task.assigned_at).days
                    if review_days > 7:
                        anomalies.append({
                            "type": "stuck_review",
                            "task_id": task.id,
                            "title": task.title,
                            "message": f"Задача в ревью {review_days} дней",
                            "severity": "medium",
                            "review_days": review_days
                        })
            
            # Аномалия: фактическая трудоемкость > 2x от оценки
            if task.actual_effort and task.estimated_effort > 0:
                variance = task.actual_effort / task.estimated_effort
                if variance > 2.0:
                    anomalies.append({
                        "type": "effort_overrun",
                        "task_id": task.id,
                        "title": task.title,
                        "message": f"Превышение трудоемкости в {variance:.1f} раз",
                        "severity": "medium",
                        "variance": round(variance, 2)
                    })
        
        return anomalies
    
    # === Методы для работы с чек-листами ===
    
    def verify_checklist_item(
        self,
        task_id: str,
        item_id: str,
        status: VerificationStatus,
        verified_by: str,
        comments: str = "",
        evidence: List[str] = None
    ) -> Tuple[bool, str]:
        """
        Проверить элемент чек-листа.
        
        Args:
            task_id: ID задачи
            item_id: ID элемента чек-листа
            status: Статус проверки (PASSED/FAILED/SKIPPED)
            verified_by: ID сотрудника, проводящего проверку
            comments: Комментарии
            evidence: Ссылки на доказательства
            
        Returns:
            (success, message)
        """
        task = self._tasks_by_id.get(task_id)
        if not task:
            return False, f"Задача {task_id} не найдена"
        
        if not task.checklist:
            return False, f"У задачи {task_id} нет чек-листа"
        
        # Проверяем существование элемента
        item_exists = any(item.id == item_id for item in task.checklist.items)
        if not item_exists:
            return False, f"Элемент чек-листа {item_id} не найден"
        
        # Выполняем проверку
        success = task.checklist.verify_item(
            item_id=item_id,
            status=status,
            verified_by=verified_by,
            comments=comments,
            evidence=evidence or []
        )
        
        if success:
            # Проверяем, можно ли завершить задачу
            if task.checklist.is_complete() and task.status == TaskStatus.REVIEW:
                task.status = TaskStatus.DONE
        
        return success, "Чек-лист обновлен"
    
    def get_checklist_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получить статус чек-листа задачи"""
        task = self._tasks_by_id.get(task_id)
        if not task or not task.checklist:
            return None
        return task.checklist.get_completion_stats()
    
    def get_pending_verifications(self, employee_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получить элементы чек-листов, ожидающие проверки.
        
        Args:
            employee_id: Фильтр по сотруднику (если None - все)
        """
        pending = []
        
        for task in self.tasks:
            if not task.checklist:
                continue
            
            for item in task.checklist.items:
                verification = task.checklist.verifications.get(item.id)
                
                # Если нет проверки или статус PENDING
                if not verification or verification.status == VerificationStatus.PENDING:
                    pending.append({
                        "task_id": task.id,
                        "task_title": task.title,
                        "item_id": item.id,
                        "item_title": item.title,
                        "item_type": item.item_type.value,
                        "is_mandatory": item.is_mandatory,
                        "verification_criteria": item.verification_criteria,
                        "current_status": verification.status.value if verification else "pending"
                    })
        
        return pending
    
    def validate_task_completion(self, task_id: str) -> Dict[str, Any]:
        """
        Проверить возможность завершения задачи.
        
        Returns:
            {
                "can_complete": bool,
                "blocking_items": [...],
                "checklist_complete": bool,
                "message": str
            }
        """
        task = self._tasks_by_id.get(task_id)
        if not task:
            return {
                "can_complete": False,
                "blocking_items": [],
                "checklist_complete": False,
                "message": f"Задача {task_id} не найдена"
            }
        
        blocking_items = []
        
        # Проверяем чек-лист
        checklist_complete = True
        if task.checklist:
            for item in task.checklist.items:
                if not item.is_mandatory:
                    continue
                
                verification = task.checklist.verifications.get(item.id)
                if not verification or verification.status != VerificationStatus.PASSED:
                    blocking_items.append({
                        "item_id": item.id,
                        "title": item.title,
                        "reason": "Не пройдено обязательное требование"
                    })
                    checklist_complete = False
        
        # Проверяем статус
        status_ok = task.status in (TaskStatus.REVIEW, TaskStatus.DONE)
        
        can_complete = status_ok and checklist_complete
        
        return {
            "can_complete": can_complete,
            "blocking_items": blocking_items,
            "checklist_complete": checklist_complete,
            "status_ok": status_ok,
            "message": "Готово к завершению" if can_complete else "Есть блокирующие факторы"
        }
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Получить метрики качества выполнения задач.
        
        Returns:
            {
                "total_checklists": int,
                "completed_checklists": int,
                "average_completion_rate": float,
                "failed_items_count": int,
                "quality_score": float (0-1)
            }
        """
        checklists = [t.checklist for t in self.tasks if t.checklist]
        
        if not checklists:
            return {
                "total_checklists": 0,
                "completed_checklists": 0,
                "average_completion_rate": 0,
                "failed_items_count": 0,
                "quality_score": 0
            }
        
        completed = sum(1 for c in checklists if c.is_complete())
        completion_rates = [c.get_completion_stats()["completion_rate"] for c in checklists]
        avg_completion = sum(completion_rates) / len(completion_rates) if completion_rates else 0
        
        failed_count = sum(
            c.get_completion_stats()["failed_count"]
            for c in checklists
        )
        
        # Quality score: комбинация completion rate и отсутствия failed
        quality_score = avg_completion * (1 - failed_count / max(1, sum(
            c.get_completion_stats()["total_items"] for c in checklists
        )))
        
        return {
            "total_checklists": len(checklists),
            "completed_checklists": completed,
            "average_completion_rate": round(avg_completion, 3),
            "failed_items_count": failed_count,
            "quality_score": round(quality_score, 3)
        }
    
    def add_task(self, task: Task):
        """Добавить задачу в контроль"""
        self.tasks.append(task)
        self._tasks_by_id[task.id] = task
    
    def remove_task(self, task_id: str):
        """Удалить задачу из контроля"""
        self.tasks = [t for t in self.tasks if t.id != task_id]
        if task_id in self._tasks_by_id:
            del self._tasks_by_id[task_id]