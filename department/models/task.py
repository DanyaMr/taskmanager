"""
Модели задач и статусы.
Обновленная версия с поддержкой чек-листов.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from department.models.checklist import Checklist


class TaskStatus(str, Enum):
    """Статусы жизненного цикла задачи"""
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(int, Enum):
    """Шкала приоритетов"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """
    Модель задачи подразделения.
    
    Attributes:
        id: Уникальный идентификатор
        title: Заголовок задачи
        description: Описание
        priority: Приоритет
        estimated_effort: Оценка трудоемкости (часы)
        required_skills: Требуемые навыки {skill_name: level}
        dependencies: Зависимости (ID других задач)
        status: Текущий статус
        assigned_id: ID назначенного сотрудника
        is_decomposed: Флаг декомпозиции
        deadline: Дедлайн
        created_at: Дата создания
        assigned_at: Дата назначения
        actual_effort: Фактическая трудоемкость (заполняется после выполнения)
        actual_duration_hours: Фактическая длительность (часы)
        checklist: Чек-лист требований (опционально)
        checklist_template: Шаблон чек-листа (software_development, hardware_maintenance, general_task)
        metadata: Дополнительные метаданные
    """
    id: str
    title: str
    description: str = ""
    priority: Priority = Priority.MEDIUM
    estimated_effort: float = 1.0
    required_skills: Dict[str, int] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.BACKLOG
    assigned_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    is_decomposed: bool = False
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Новые поля для контроля качества
    actual_effort: Optional[float] = None
    actual_duration_hours: Optional[float] = None
    checklist: Optional[Checklist] = None
    checklist_template: str = "general_task"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_ready_to_start(self, completed_task_ids: set) -> bool:
        """Проверить готовность к выполнению (все зависимости выполнены)"""
        return all(dep in completed_task_ids for dep in self.dependencies)
    
    def update_status(self, new_status: TaskStatus):
        """Обновить статус задачи"""
        self.status = new_status
    
    def set_checklist(self, checklist: Checklist):
        """Установить чек-лист для задачи"""
        checklist.task_id = self.id
        self.checklist = checklist
    
    def apply_checklist_template(self, template_name: str = "general_task"):
        """
        Применить шаблон чек-листа к задаче.
        
        Args:
            template_name: Название шаблона (software_development, hardware_maintenance, general_task)
        """
        from department.models.checklist import get_template
        template = get_template(template_name)
        if template:
            template.task_id = self.id
            template.name = f"{template.name} для {self.title}"
            self.checklist = template
            self.checklist_template = template_name
    
    def is_checklist_complete(self) -> bool:
        """Проверить, завершен ли чек-лист"""
        if not self.checklist:
            return True  # Если чек-лист не установлен, считаем выполненным
        return self.checklist.is_complete()
    
    def can_complete(self) -> bool:
        """
        Проверить возможность завершения задачи.
        Задача может быть завершена если:
        - Статус REVIEW или DONE
        - Чек-лист завершен (если есть)
        """
        if self.status not in (TaskStatus.REVIEW, TaskStatus.DONE):
            return False
        return self.is_checklist_complete()
    
    def get_checklist_stats(self) -> Optional[Dict[str, Any]]:
        """Получить статистику чек-листа"""
        if not self.checklist:
            return None
        return self.checklist.get_completion_stats()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь"""
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value if isinstance(self.priority, Priority) else self.priority,
            "estimated_effort": self.estimated_effort,
            "required_skills": self.required_skills,
            "dependencies": self.dependencies,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "assigned_id": self.assigned_id,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "is_decomposed": self.is_decomposed,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat(),
            "actual_effort": self.actual_effort,
            "actual_duration_hours": self.actual_duration_hours,
            "checklist_template": self.checklist_template,
            "metadata": self.metadata
        }
        
        if self.checklist:
            data["checklist"] = self.checklist.to_dict()
            data["checklist_stats"] = self.get_checklist_stats()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Создать задачу из словаря"""
        # Парсинг priority
        priority = data.get("priority", Priority.MEDIUM)
        if isinstance(priority, int):
            priority = Priority(priority)
        elif isinstance(priority, str):
            priority_map = {
                "low": Priority.LOW,
                "medium": Priority.MEDIUM,
                "high": Priority.HIGH,
                "critical": Priority.CRITICAL,
                1: Priority.LOW,
                2: Priority.MEDIUM,
                3: Priority.HIGH,
                4: Priority.CRITICAL
            }
            priority = priority_map.get(priority, Priority.MEDIUM)
        
        # Парсинг status
        status = data.get("status", TaskStatus.BACKLOG)
        if isinstance(status, str):
            status = TaskStatus(status)
        
        # Парсинг дат
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        assigned_at = data.get("assigned_at")
        if isinstance(assigned_at, str):
            assigned_at = datetime.fromisoformat(assigned_at)
        
        deadline = data.get("deadline")
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)
        
        # Создание задачи
        task = cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            priority=priority,
            estimated_effort=data.get("estimated_effort", 1.0),
            required_skills=data.get("required_skills", {}),
            dependencies=data.get("dependencies", []),
            status=status,
            assigned_id=data.get("assigned_id"),
            assigned_at=assigned_at,
            is_decomposed=data.get("is_decomposed", False),
            deadline=deadline,
            created_at=created_at or datetime.now(),
            actual_effort=data.get("actual_effort"),
            actual_duration_hours=data.get("actual_duration_hours"),
            checklist_template=data.get("checklist_template", "general_task"),
            metadata=data.get("metadata", {})
        )
        
        # Парсинг чек-листа
        checklist_data = data.get("checklist")
        if checklist_data:
            task.checklist = Checklist.from_dict(checklist_data)
        
        return task