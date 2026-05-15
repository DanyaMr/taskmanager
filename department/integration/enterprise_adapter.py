"""
Адаптер интеграции с метамоделью предприятия (фрактальность)
"""

from typing import Dict, Any
from department.models.base_entity import BaseEntity


class EnterpriseAdapter:
    """
    Адаптер для интеграции подразделения в метамодель предприятия
    Согласно [2], подразделение отображается как BusinessCapability
    """

    def __init__(self, department_id: str, department_name: str):
        self.department_id = department_id
        self.department_name = department_name

    def to_business_capability(self) -> Dict[str, Any]:
        """
        Преобразовать подразделение в BusinessCapability метамодели

        Реализация на основе Приложения Б [2]:
        - maturity_current/target для оценки зрелости
        - regulatory_constraints для учета ограничений
        """
        return {
            "id": f"BC_{self.department_id}",
            "name": self.department_name,
            "type": "BusinessCapability",
            "maturity_current": 3,  # Оценка текущей зрелости (1-5)
            "maturity_target": 4,
            "regulatory_constraints": ["ISO 9001", "GDPR"],
            "owner": f"head_{self.department_id}",
            "dependencies": []  # Связи с другими подразделениями
        }

    def to_automated_system(self) -> Dict[str, Any]:
        """
        Преобразовать в AutomatedSystem для технологического слоя [2]
        """
        return {
            "id": f"AS_{self.department_id}",
            "name": f"Digital Twin: {self.department_name}",
            "system_category": "operational",
            "criticality": "high",
            "integration_type": "api",
            "capabilities": ["task_management", "resource_planning", "forecasting"]
        }

    def get_fractal_metrics(self) -> Dict[str, float]:
        """
        Получить метрики фрактального подразделения для сводного отчета
        """
        return {
            "automation_rate": 0.6,  # Доля цифровых сотрудников
            "forecast_accuracy": 0.85,
            "capacity_utilization": 0.75,
            "digital_share": 0.4  # Доля цифровой емкости
        }