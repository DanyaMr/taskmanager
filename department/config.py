"""
Конфигурация подразделения и константы
"""

from enum import Enum
from typing import Dict, Any

# Управленческие константы
PLANNING_HORIZON_DAYS = 14
MAX_DIGITAL_CAPACITY_HOURS = 168.0  # 24/7
MAX_HUMAN_CAPACITY_HOURS = 40.0
DEFAULT_CONFIDENCE_THRESHOLD = 0.6

# Типы сотрудников
class EmployeeType(str, Enum):
    HUMAN = "human"
    DIGITAL = "digital"

# Конфигурация цифровых сотрудников
DEFAULT_DIGITAL_CONFIG: Dict[str, Any] = {
    "webhook_url": None,
    "auto_retry": True,
    "parallel_jobs": 3,
    "capabilities": ["automation", "testing", "analysis"]
}