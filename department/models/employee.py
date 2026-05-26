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
        """Проверить возможность выполнения задачи (проверка наличия навыка, любой уровень > 0)"""
        for skill_name, required_level in task.required_skills.items():
            skill_level = self.get_skill_level(skill_name)
            # Проверяем наличие навыка (уровень > 0)
            if skill_level < 1:
                return False
        return True

    def has_skill(self, skill_name: str, required_level: int = 1) -> bool:
        """Проверить наличие навыка (регистронезависимо и без учета префикса skill_)"""
        return self.get_skill_level(skill_name) >= required_level
    
    def get_skill_level(self, skill_name: str) -> int:
        """Получить уровень навыка (регистронезависимо и без учета префикса skill_)"""
        # Нормализуем имя требуемого навыка
        skill_name_lower = skill_name.lower().replace("skill_", "")
        for name, skill_level in self.skills.items():
            # Нормализуем имя навыка у сотрудника
            if name.lower().replace("skill_", "") == skill_name_lower:
                return skill_level.level
        return 0


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
        """Цифровой сотрудник проверяет наличие навыка (любой уровень > 0)"""
        # Если есть хотя бы один требуемый навык - цифровой сотрудник может выполнить задачу
        for skill_name, required_level in task.required_skills.items():
            skill_level = self.get_skill_level(skill_name)
            # Проверяем наличие навыка (уровень > 0)
            if skill_level >= 1:
                return True
        
        # Если навыков нет в задаче, проверяем capabilities
        task_keywords = f"{task.title} {task.description}".lower()
        capabilities = self.config.get("capabilities", [])
        return any(cap in task_keywords for cap in capabilities) or "all" in capabilities

    def has_skill(self, skill_name: str, required_level: int = 1) -> bool:
        """Проверить наличие цифрового навыка (регистронезависимо и без учета префикса skill_)"""
        skill_name_lower = skill_name.lower().replace("skill_", "")
        for name in self.skills.keys():
            if name.lower().replace("skill_", "") == skill_name_lower:
                return True
        return "all" in self.config.get("capabilities", [])
    
    def get_skill_level(self, skill_name: str) -> int:
        """Получить уровень навыка (регистронезависимо и без учета префикса skill_)"""
        skill_name_lower = skill_name.lower().replace("skill_", "")
        for name, skill_level in self.skills.items():
            if name.lower().replace("skill_", "") == skill_name_lower:
                return skill_level.level
        return 0