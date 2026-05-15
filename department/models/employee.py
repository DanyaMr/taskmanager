"""
Модели сотрудников: человеческие и цифровые
"""

from typing import List
from department.models.base_entity import Employee, Task
from department.models.skill import SkillLevel


class HumanEmployee(Employee):
    """Человеческий сотрудник"""

    def __init__(self, id: str, name: str, capabilities: List[str] = None):
        super().__init__(
            id=id,
            name=name,
            type="human",
            max_capacity=40.0,
            config={"capabilities": capabilities or ["general"]}
        )

    def can_perform_task(self, task: Task) -> bool:
        """Проверить возможность выполнения задачи"""
        for skill_name, required_level in task.required_skills.items():
            if self.get_skill_level(skill_name) < required_level:
                return False
        return True

    def has_skill(self, skill_name: str, required_level: int = 1) -> bool:
        """Проверить наличие навыка"""
        return self.get_skill_level(skill_name) >= required_level


class DigitalEmployee(Employee):
    """Цифровой сотрудник (бот, агент)"""

    def __init__(self, id: str, name: str, capabilities: List[str] = None):
        super().__init__(
            id=id,
            name=name,
            type="digital",
            max_capacity=168.0,  # 24/7 работа
            config={"capabilities": capabilities or ["automation"]}
        )

    def can_perform_task(self, task: Task) -> bool:
        """Цифровой сотрудник проверяет по capabilities"""
        # Проверка навыков
        for skill_name, required_level in task.required_skills.items():
            if self.get_skill_level(skill_name) < required_level:
                return False

        # Проверка по шаблонам возможностей
        task_keywords = f"{task.title} {task.description}".lower()
        capabilities = self.config.get("capabilities", [])
        return any(cap in task_keywords for cap in capabilities) or "all" in capabilities

    def has_skill(self, skill_name: str, required_level: int = 1) -> bool:
        """Проверить наличие цифрового навыка"""
        return skill_name in self.skills or "all" in self.config.get("capabilities", [])