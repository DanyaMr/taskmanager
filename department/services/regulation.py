"""
Сервис регулирования (корректирующие действия)
"""

from typing import Dict, List
from department.models.employee import Employee
from department.models.task import Task


class RegulationService:
    """Регулирование работы подразделения"""

    def __init__(self, employees: List[Employee]):
        self.employees = employees

    def apply_corrective_actions(self, plan: Dict[str, List[Task]]) -> Dict[str, List[str]]:
        """
        Применить корректирующие действия к плану

        Returns:
            Словарь с действиями по каждому сотруднику
        """
        actions = {}
        for emp_id, tasks in plan.items():
            emp = next((e for e in self.employees if e.id == emp_id), None)
            if not emp:
                continue

            actions[emp_id] = []
            total_load = sum(t.estimated_effort for t in tasks) / emp.max_capacity

            # Регулирование нагрузки
            if total_load > 1.0:
                actions[emp_id].append(f"Снижение нагрузки с {total_load:.2f} до 1.0")
                # Автоматически переназначить избыточные задачи
                excess_tasks = tasks[int(emp.max_capacity):]
                for task in excess_tasks:
                    actions[emp_id].append(f"Переназначить задачу {task.id} на цифрового сотрудника")
            elif total_load < 0.3 and emp.type == "digital":
                actions[emp_id].append(f"Увеличить загрузку цифрового сотрудника до 0.7")

        return actions

    def reallocate_resources(self, bottleneck_id: str, digital_pool: List[Employee]) -> List[Dict]:
        """Перераспределить ресурсы при узких местах"""
        reallocations = []
        for digital in digital_pool:
            if digital.current_load < 0.5:
                reallocations.append({
                    "from": bottleneck_id,
                    "to": digital.id,
                    "capacity": digital.max_capacity * (1 - digital.current_load),
                    "reason": "Разгрузка узкого места"
                })
        return reallocations