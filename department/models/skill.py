"""
Модели навыков и компетенций
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SkillCategory(str, Enum):
    """Категории навыков"""
    TECHNICAL = "technical"
    SOFT = "soft"
    BUSINESS = "business"


@dataclass
class SkillDetail:
    """Детальная информация о навыке"""
    id: str
    name: str
    description: str
    category: str
    is_digital: bool = False


@dataclass
class SkillLevel:
    """Уровень владения навыком"""
    skill: SkillDetail
    level: int  # 1-5

    def __post_init__(self):
        if not 1 <= self.level <= 5:
            raise ValueError("Уровень навыка должен быть от 1 до 5")