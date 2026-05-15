"""
Базовые сущности подразделения
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    """Статусы задач"""
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class Priority(int, Enum):
    """Приоритеты задач"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class BaseEntity:
    """Базовый класс для всех сущностей"""
    id: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Employee(BaseEntity, ABC):
    """Базовый класс сотрудника (человек или цифровой)"""
    type: str = "Digital"
    current_load: float = 0.0
    performance_score: float = 1.0
    max_capacity: float = 40.0
    skills: Dict[str, 'SkillLevel'] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def can_perform_task(self, task: 'Task') -> bool:
        pass

    @abstractmethod
    def has_skill(self, skill_name: str, required_level: int = 1) -> bool:
        pass

    def get_skill_level(self, skill_name: str) -> int:
        """Получить уровень навыка"""
        if skill_name in self.skills:
            return self.skills[skill_name].level
        return 0

    '''def assign_task(self, task: 'Task') -> bool:
        """Назначить задачу сотруднику"""
        if self.can_perform_task(task) and self.current_load < 1.0:
            self.current_load = min(1.0, self.current_load + 0.2)
            return True
        return False'''


@dataclass
class Task(BaseEntity):
    """Задача подразделения"""
    title: str = "title"
    description: str = ""
    priority: Priority = Priority.MEDIUM
    estimated_effort: float = 100
    required_skills: Dict[str, int] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.BACKLOG
    assigned_id: Optional[str] = None
    assigned_at: Optional[datetime] = None  # ДОБАВИТЬ ЭТО ПОЛЕ
    is_decomposed: bool = False

    def is_ready_to_start(self, completed_task_ids: Set[str]) -> bool:
        """Проверить готовность к запуску (все зависимости выполнены)"""
        return all(dep in completed_task_ids for dep in self.dependencies)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "estimated_effort": self.estimated_effort,
            "required_skills": self.required_skills,
            "dependencies": self.dependencies,
            "assigned_id": self.assigned_id,
            "is_decomposed": self.is_decomposed
        })
        return data