"""
Сервис стимулирования (мотивация и KPI)
"""

from typing import Dict, List
from department.models.employee import Employee


class StimulationService:
    """Стимулирование сотрудников через KPI и мотивацию"""

    def __init__(self, employees: List[Employee]):
        self.employees = employees

    def calculate_kpi(self, employee_id: str, completed_tasks: int, total_effort: float) -> Dict:
        """
        Рассчитать KPI сотрудника

        Returns:
            Словарь с показателями эффективности
        """
        emp = next((e for e in self.employees if e.id == employee_id), None)
        if not emp:
            return {"error": "Employee not found"}

        utilization_rate = total_effort / emp.max_capacity
        efficiency_score = completed_tasks / total_effort if total_effort > 0 else 0

        # Для цифровых сотрудников добавляем SLA
        if emp.type == "digital":
            sla_compliance = 0.95  # Цифровые должны иметь 95% SLA
            automation_rate = 0.8  # Уровень автоматизации
        else:
            sla_compliance = 0.85
            automation_rate = 0.2

        return {
            "employee_id": employee_id,
            "utilization_rate": utilization_rate,
            "efficiency_score": efficiency_score,
            "sla_compliance": sla_compliance,
            "automation_rate": automation_rate,
            "overall_score": (efficiency_score + sla_compliance) / 2
        }

    def generate_motivation_score(self, employee_id: str) -> float:
        """Генерировать оценку мотивации (0.0-1.0)"""
        emp = next((e for e in self.employees if e.id == employee_id), None)
        if not emp:
            return 0.0

        # Простая модель: мотивация обратно пропорциональна загрузке
        # для людей и прямо пропорциональна для цифровых
        if emp.type == "human":
            return max(0.1, 1.0 - emp.current_load)
        else:
            return emp.current_load  # Цифровые "мотивированы" работой