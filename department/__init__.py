"""
Пакет моделирования подразделения предприятия.
Фрактальная архитектура: подразделение является самодостаточной единицей
с полным набором управленческих функций.
"""

__version__ = "1.0.0"

# Публичный API
from department.models.base_entity import (
    BaseEntity, Employee, Task, TaskStatus, Priority
)
from department.models.employee import HumanEmployee, DigitalEmployee
from department.models.task import TaskStatus, Priority, Task
from department.models.skill import SkillDetail, SkillLevel
from department.models.checklist import (
    Checklist, ChecklistItem, ChecklistVerification,
    ChecklistItemType, VerificationStatus, TEMPLATE_CHECKLISTS, get_template
)

# Сервисы
from department.database.service import DatabaseService
from department.services.planning import Planning, OptimizationResult, AssignmentResult
from department.services.coordination import Coordination
from department.services.forecasting import ForecastingService, Forecast
from department.services.regulation import RegulationService
from department.services.stimulation import StimulationService
from department.services.control import ControlService

# RAG модуль
from department.rag.vector_store import VectorStore
from department.rag.embeddings import EmbeddingService
from department.rag.retriever import TaskRetriever, RetrievedTask

# LLM модуль
from department.llm.service import LLMService, ForecastPrediction

__all__ = [
    # Модели
    "HumanEmployee", "DigitalEmployee", "Task", "SkillDetail", "SkillLevel",
    "BaseEntity", "TaskStatus", "Priority",
    # Чек-листы
    "Checklist", "ChecklistItem", "ChecklistVerification",
    "ChecklistItemType", "VerificationStatus", "TEMPLATE_CHECKLISTS", "get_template",
    # Сервисы
    "DatabaseService", "Planning", "OptimizationResult", "AssignmentResult",
    "Coordination", "ForecastingService", "Forecast",
    "RegulationService", "StimulationService", "ControlService",
    # RAG
    "VectorStore", "EmbeddingService", "TaskRetriever", "RetrievedTask",
    # LLM
    "LLMService", "ForecastPrediction"
]