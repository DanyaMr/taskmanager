"""
Сервис координации параллельной работы
"""

from collections import defaultdict
from typing import Dict, List, Set
from department.models.task import Task, TaskStatus


class Coordination:
    """Координация задач и управление зависимостями"""

    def __init__(self):
        self.task_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.blocked_tasks: Dict[str, List[str]] = defaultdict(list)

    def add_dependency(self, task_id: str, depends_on: str):
        """Добавить зависимость задачи"""
        self.task_dependencies[task_id].add(depends_on)

    def get_ready_tasks(self, all_tasks: List[Task], completed_task_ids: Set[str]) -> List[Task]:
        """Получить задачи, готовые к выполнению"""
        ready = []
        for task in all_tasks:
            if task.status == TaskStatus.BACKLOG and task.is_ready_to_start(completed_task_ids):
                ready.append(task)
        return ready

    def identify_blockers(self, in_progress_tasks: List[Task], all_tasks: Dict[str, Task]) -> Dict[str, List[str]]:
        """Выявить задачи, которые блокируют другие"""
        blockers = {}
        for task in in_progress_tasks:
            blocked = [
                tid for tid, deps in self.task_dependencies.items()
                if task.id in deps and all_tasks[tid].status != TaskStatus.DONE
            ]
            if blocked:
                blockers[task.id] = blocked
        return blockers

    def resolve_conflicts(self, overloaded_employees: Dict[str, float]) -> List[Dict]:
        """Выявить и предложить решения по перегрузкам"""
        conflicts = []
        for emp_id, load in overloaded_employees.items():
            if load > 1.0:
                conflicts.append({
                    "employee_id": emp_id,
                    "overload": load - 1.0,
                    "recommendation": "Переназначить задачи цифровым сотрудникам",
                    "priority": "high" if load > 1.3 else "medium"
                })
        return conflicts