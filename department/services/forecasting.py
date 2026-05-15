"""
Сервис прогнозирования выполнения задач.
Интегрирует RAG + LLM для точного прогнозирования.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from department.models.task import Task
from department.models.employee import Employee
from department.llm.service import LLMService, ForecastPrediction
from department.rag.retriever import TaskRetriever


@dataclass
class Forecast:
    """Прогноз выполнения задачи"""
    task_id: str
    predicted_completion: datetime
    predicted_effort: float
    confidence: float  # 0.0-1.0
    risk_factors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    llm_prediction: Optional[ForecastPrediction] = None
    similar_tasks_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "predicted_completion": self.predicted_completion.isoformat(),
            "predicted_effort": self.predicted_effort,
            "confidence": self.confidence,
            "risk_factors": self.risk_factors,
            "similar_tasks_count": self.similar_tasks_count,
            "llm_used": self.llm_prediction is not None
        }


class ForecastingService:
    """
    Прогнозирование на основе RAG + LLM и текущей загрузки.
    
    Использует векторный поиск похожих задач и LLM для точной оценки.
    """
    
    def __init__(
        self,
        employees: List[Employee],
        llm_service: Optional[LLMService] = None,
        task_retriever: Optional[TaskRetriever] = None
    ):
        """
        Инициализация сервиса прогнозирования.
        
        Args:
            employees: Список сотрудников
            llm_service: LLM сервис (создается новый если не указан)
            task_retriever: RAG retriever для поиска похожих задач
        """
        self.employees = employees
        self.llm_service = llm_service or LLMService()
        self.task_retriever = task_retriever or self.llm_service.rag_retriever
        self.forecasts: Dict[str, Forecast] = {}
    
    def estimate_task(self, task: Task, employee_type: str = "human") -> Forecast:
        """
        Оценить задачу с использованием RAG + LLM.
        
        Args:
            task: Задача для оценки
            employee_type: Тип исполнителя (human/digital)
            
        Returns:
            Forecast с прогнозом
        """
        # 1. Получаем прогноз от LLM с RAG
        llm_prediction = self.llm_service.predict_effort_with_rag(
            task=task,
            employee_type=employee_type,
            n_similar_tasks=3
        )
        
        # 2. Находим подходящих сотрудников
        suitable = self._find_suitable_employees(task, employee_type)
        
        if not suitable:
            return Forecast(
                task_id=task.id,
                predicted_completion=datetime.now() + timedelta(days=999),
                predicted_effort=llm_prediction.predicted_effort_hours,
                confidence=0.1,
                risk_factors=["Нет сотрудников с требуемыми навыками"] + llm_prediction.risk_factors,
                llm_prediction=llm_prediction,
                similar_tasks_count=len(llm_prediction.similar_tasks_used)
            )
        
        # 3. Выбираем наименее загруженного сотрудника
        best_employee = min(suitable, key=lambda e: e.current_load)
        
        # 4. Расчет времени с учетом загрузки
        base_duration = llm_prediction.predicted_effort_hours / best_employee.performance_score
        load_multiplier = 1 + best_employee.current_load * 0.5
        predicted_days = base_duration * load_multiplier / 8  # Переводим часы в дни
        
        # 5. Факторы риска
        risk_factors = list(llm_prediction.risk_factors)
        if task.dependencies:
            risk_factors.append(f"Зависимости от {len(task.dependencies)} задач")
        if best_employee.current_load > 0.8:
            risk_factors.append("Высокая загрузка исполнителя")
        
        # 6. Корректируем confidence с учетом загрузки
        adjusted_confidence = llm_prediction.confidence * (1 - best_employee.current_load * 0.3)
        
        forecast = Forecast(
            task_id=task.id,
            predicted_completion=datetime.now() + timedelta(days=predicted_days),
            predicted_effort=llm_prediction.predicted_effort_hours,
            confidence=max(0.1, adjusted_confidence),
            risk_factors=risk_factors,
            llm_prediction=llm_prediction,
            similar_tasks_count=len(llm_prediction.similar_tasks_used)
        )
        
        self.forecasts[task.id] = forecast
        return forecast
    
    def estimate_task_batch(
        self,
        tasks: List[Task],
        employee_type: str = "human"
    ) -> Dict[str, Forecast]:
        """
        Оценить пакет задач.
        
        Args:
            tasks: Список задач
            employee_type: Тип исполнителя
            
        Returns:
            Словарь прогнозов по ID задач
        """
        results = {}
        for task in tasks:
            results[task.id] = self.estimate_task(task, employee_type)
        return results
    
    def _find_suitable_employees(
        self,
        task: Task,
        employee_type: Optional[str] = None
    ) -> List[Employee]:
        """Найти подходящих сотрудников"""
        suitable = []
        for emp in self.employees:
            # Фильтр по типу если указан
            if employee_type and emp.type != employee_type:
                continue
            
            # Цифровые сотрудники могут выполнять любые задачи
            if emp.type == "digital":
                suitable.append(emp)
            # Люди проверяются по навыкам
            elif emp.can_perform_task(task):
                suitable.append(emp)
        
        return suitable
    
    def get_forecast(self, task_id: str) -> Optional[Forecast]:
        """Получить прогноз по ID задачи"""
        return self.forecasts.get(task_id)
    
    def add_completed_task_to_history(
        self,
        task_id: str,
        title: str,
        description: str,
        actual_effort: float,
        actual_duration_hours: float,
        skills_used: List[str],
        employee_type: str
    ) -> bool:
        """
        Добавить выполненную задачу в историю для RAG.
        
        Args:
            task_id: ID задачи
            title: Заголовок
            description: Описание
            actual_effort: Фактическая трудоемкость
            actual_duration_hours: Фактическая длительность
            skills_used: Использованные навыки
            employee_type: Тип сотрудника
        """
        return self.task_retriever.add_completed_task(
            task_id=task_id,
            title=title,
            description=description,
            actual_effort=actual_effort,
            actual_duration_hours=actual_duration_hours,
            skills_used=skills_used,
            employee_type=employee_type
        )
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """Получить статистику RAG хранилища"""
        return self.task_retriever.get_statistics()