"""
Сервис планирования работ сотрудников.
Реализует оптимизацию распределения задач методом линейного программирования.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

try:
    from scipy.optimize import linprog
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    linprog = None

from department.models.task import Task, TaskStatus, Priority
from department.models.employee import Employee
from department.services.forecasting import ForecastingService
from department.database.service import DatabaseService
from department.llm.service import LLMService


@dataclass
class AssignmentResult:
    """Результат назначения задачи"""
    task_id: str
    employee_id: str
    predicted_effort: float
    predicted_completion_days: float
    confidence: float


@dataclass
class OptimizationResult:
    """Результат оптимизации планирования"""
    success: bool
    assignments: List[AssignmentResult] = field(default_factory=list)
    total_time: float = 0.0
    message: str = ""
    unassigned_tasks: List[str] = field(default_factory=list)
    method: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "total_time_hours": self.total_time,
            "message": self.message,
            "method": self.method,
            "assignments_count": len(self.assignments),
            "unassigned_count": len(self.unassigned_tasks),
            "assignments": [
                {
                    "task_id": a.task_id,
                    "employee_id": a.employee_id,
                    "predicted_effort": a.predicted_effort,
                    "predicted_completion_days": a.predicted_completion_days
                }
                for a in self.assignments
            ],
            "unassigned_tasks": self.unassigned_tasks
        }


class Planning:
    """
    Планирование с оптимизацией методом линейного программирования.
    
    Целевая функция: минимизация общего времени выполнения всех задач
    Ограничения:
    - Capacity сотрудников (часы в неделю)
    - Навыки сотрудников
    - Зависимости между задачами
    - Приоритеты задач
    """
    
    def __init__(
        self,
        employees: List[Employee],
        forecasting_service: Optional[ForecastingService] = None,
        llm_service: Optional[LLMService] = None
    ):
        """
        Инициализация планировщика.
        
        Args:
            employees: Список сотрудников
            forecasting_service: Сервис прогнозирования
            llm_service: Сервис LLM для оценки возможности выполнения
        """
        self.employees = employees
        self.forecasting_service = forecasting_service or ForecastingService(employees)
        self._employees_by_id = {emp.id: emp for emp in employees}
        self.llm_service = llm_service
    
    def create_plan(
        self,
        tasks: List[Task],
        days: int = 14,
        use_optimization: bool = True
    ) -> Dict[str, List[Task]]:
        """
        Создать план распределения задач.
        
        Args:
            tasks: Список задач для планирования
            days: Период планирования в днях
            use_optimization: Использовать линейное программирование
            
        Returns:
            Словарь {employee_id: [задачи]}
        """
        if use_optimization and SCIPY_AVAILABLE:
            return self._create_optimized_plan(tasks, days)
        else:
            return self._create_greedy_plan(tasks, days)
    
    def _create_greedy_plan(
        self,
        tasks: List[Task],
        days: int
    ) -> Dict[str, List[Task]]:
        """Жадный алгоритм распределения (fallback)"""
        plan = defaultdict(list)
        remaining_capacity = {
            emp.id: (1.0 - emp.current_load) * emp.max_capacity * days / 7
            for emp in self.employees
        }
        
        # Разделение сотрудников
        human_employees = [emp for emp in self.employees if emp.type == "human"]
        digital_employees = [emp for emp in self.employees if emp.type == "digital"]
        
        # Сортировка задач по приоритету
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (-t.priority.value, len(t.dependencies))
        )
        
        for task in sorted_tasks:
            # Сначала пробуем найти человека
            human_suitable = [
                emp for emp in human_employees
                if emp.can_perform_task(task) and remaining_capacity[emp.id] > 0
            ]
            
            if human_suitable:
                suitable = human_suitable
            else:
                # Если не найден - берем цифрового с наименьшей загрузкой
                suitable = [
                    emp for emp in digital_employees
                    if remaining_capacity[emp.id] > 0
                ]
            
            if not suitable:
                continue
            
            # Назначаем задачу наименее загруженному
            forecast = self.forecasting_service.estimate_task(task)
            best_emp = min(suitable, key=lambda e: remaining_capacity[e.id])
            
            if remaining_capacity[best_emp.id] >= forecast.predicted_effort:
                plan[best_emp.id].append(task)
                remaining_capacity[best_emp.id] -= forecast.predicted_effort
        
        return dict(plan)
    
    def _create_optimized_plan(
        self,
        tasks: List[Task],
        days: int
    ) -> Dict[str, List[Task]]:
        """
        Оптимизированный план с использованием линейного программирования.
        
        Минимизируем: sum(time[i,j] * x[i,j]) для всех задач i и сотрудников j
        где x[i,j] = 1 если задача i назначена сотруднику j, иначе 0
        
        Ограничения:
        1. Каждая задача назначена ровно одному сотруднику
        2. Capacity каждого сотрудника не превышена
        3. Задача может быть назначена только сотруднику с нужными навыками
        """
        if not tasks or not self.employees:
            return {}
        
        n_tasks = len(tasks)
        n_employees = len(self.employees)
        
        # Сортируем задачи по приоритету (критичные сначала)
        sorted_tasks = sorted(tasks, key=lambda t: -t.priority.value)
        
        # Вычисляем матрицу времени выполнения (часы)
        # time_matrix[i][j] = время выполнения задачи i сотрудником j
        time_matrix = np.zeros((n_tasks, n_employees))
        feasibility_matrix = np.zeros((n_tasks, n_employees), dtype=bool)
        
        for i, task in enumerate(sorted_tasks):
            for j, emp in enumerate(self.employees):
                # LLM оценивает возможность выполнения на основе логики
                can_perform, confidence = self._llm_can_perform(emp, task)
                feasibility_matrix[i][j] = can_perform
                
                if can_perform:
                    forecast = self.forecasting_service.estimate_task(task, emp.type)
                    # Применяем confidence к effort (уверенность снижает время)
                    time_matrix[i][j] = forecast.predicted_effort * (2 - confidence)
                else:
                    # Большое число для невозможных назначений
                    time_matrix[i][j] = 1e6
        
        # Capacity сотрудников (часы на период планирования)
        capacities = np.array([
            (1.0 - emp.current_load) * emp.max_capacity * days / 7
            for emp in self.employees
        ])
        capacities = np.maximum(capacities, 0)  # Не отрицательные
        
        # Решаем задачу оптимизации
        result = self._solve_assignment_lp(
            time_matrix, capacities, feasibility_matrix
        )
        
        # Формируем план из результатов оптимизации
        plan = defaultdict(list)
        
        if result and result[0] is not None:
            assignments = result[0]
            for i, j in assignments:
                if feasibility_matrix[i][j]:
                    emp = self.employees[j]
                    plan[emp.id].append(sorted_tasks[i])
        
        return dict(plan)
    
    def _solve_assignment_lp(
        self,
        time_matrix: np.ndarray,
        capacities: np.ndarray,
        feasibility_matrix: np.ndarray
    ) -> Tuple[Optional[List[Tuple[int, int]]], str]:
        """
        Решить задачу назначения с помощью scipy.optimize.linprog.
        
        Минимизация makespan (времени завершения всех задач):
        - Добавляем переменную makespan (последняя переменная в векторе)
        - Для каждого сотрудника: sum(time[i,j] * x[i,j]) <= makespan
        - Целевая функция: minimize makespan
        
        Returns:
            (список назначений (task_idx, emp_idx), сообщение)
        """
        n_tasks, n_employees = time_matrix.shape
        n_vars = n_tasks * n_employees + 1  # +1 для переменной makespan
        
        # Целевая функция: minimize makespan (коэффициент 1 для makespan, 0 для x[i,j])
        c = np.zeros(n_vars)
        c[-1] = 1.0  # makespan
        
        # Ограничения-равенства: каждая задача назначена ровно 1 сотруднику
        A_eq = []
        b_eq = []
        
        for i in range(n_tasks):
            row = np.zeros(n_vars)
            for j in range(n_employees):
                if feasibility_matrix[i][j]:
                    row[i * n_employees + j] = 1
            A_eq.append(row)
            b_eq.append(1)
        
        # Ограничения-неравенства:
        # 1. Capacity сотрудников: sum(time[i,j] * x[i,j]) <= capacity[j]
        # 2. Makespan: sum(time[i,j] * x[i,j]) - makespan <= 0 для каждого сотрудника
        A_ub = []
        b_ub = []
        
        # Capacity ограничения
        for j in range(n_employees):
            row = np.zeros(n_vars)
            for i in range(n_tasks):
                if feasibility_matrix[i][j]:
                    row[i * n_employees + j] = time_matrix[i][j]
            A_ub.append(row)
            b_ub.append(capacities[j])
        
        # Makespan ограничения: sum(time[i,j] * x[i,j]) - makespan <= 0
        for j in range(n_employees):
            row = np.zeros(n_vars)
            for i in range(n_tasks):
                if feasibility_matrix[i][j]:
                    row[i * n_employees + j] = time_matrix[i][j]
            row[-1] = -1  # -makespan
            A_ub.append(row)
            b_ub.append(0)
        
        # Границы переменных: 0 <= x <= 1, 0 <= makespan <= infinity
        bounds = [(0, 1) for _ in range(n_tasks * n_employees)]
        bounds.append((0, None))  # makespan >= 0
        
        try:
            # Добавляем небольшую регуляризацию для равномерного распределения
            epsilon = 0.001
            for j in range(n_employees):
                for i in range(n_tasks):
                    idx = i * n_employees + j
                    c[idx] = epsilon  # Маленький штраф за каждое назначение
            
            res = linprog(
                c=c,
                A_eq=np.array(A_eq) if A_eq else None,
                b_eq=b_eq if b_eq else None,
                A_ub=np.array(A_ub) if A_ub else None,
                b_ub=b_ub,
                bounds=bounds,
                method='highs',
                options={'time_limit': 30}
            )
            
            if res.success:
                # Извлекаем назначения из решения
                assignments = []
                x = res.x
                
                # Считаем количество задач на каждого сотрудника
                task_counts = [0] * n_employees
                for i in range(n_tasks):
                    for j in range(n_employees):
                        idx = i * n_employees + j
                        if x[idx] > 0.5:
                            assignments.append((i, j))
                            task_counts[j] += 1
                
                return assignments, f"Makespan: {x[-1]:.1f} hours, Distribution: {task_counts}"
            else:
                return None, f"Optimization failed: {res.message}"
                
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def optimize_assignment(
        self,
        tasks: List[Task],
        days: int = 14
    ) -> OptimizationResult:
        """
        Оптимизировать распределение задач с минимизацией общего времени.
        
        Args:
            tasks: Список задач
            days: Период планирования
            
        Returns:
            OptimizationResult с результатами
        """
        if not SCIPY_AVAILABLE:
            return OptimizationResult(
                success=False,
                message="scipy не установлен. Установите: pip install scipy",
                method="none"
            )
        
        if not tasks:
            return OptimizationResult(
                success=True,
                message="Нет задач для планирования",
                method="scipy_linprog"
            )
        
        if not self.employees:
            return OptimizationResult(
                success=False,
                message="Нет сотрудников для назначения",
                method="scipy_linprog"
            )
        
        n_tasks = len(tasks)
        n_employees = len(self.employees)
        
        # Сортируем задачи по приоритету
        sorted_tasks = sorted(tasks, key=lambda t: -t.priority.value)
        
        # Матрица времени выполнения
        time_matrix = np.zeros((n_tasks, n_employees))
        feasibility_matrix = np.zeros((n_tasks, n_employees), dtype=bool)
        
        # Используем batch метод для оценки всех задач каждым сотрудником (один LLM вызов на сотрудника)
        for j, emp in enumerate(self.employees):
            print(f"  Evaluating employee {j}: {emp.name} ({emp.type})")
            # Оцениваем все задачи для этого сотрудника одним вызовом
            results = self._llm_can_perform_batch(emp, sorted_tasks)
            
            for i, task in enumerate(sorted_tasks):
                can_perform, confidence = results.get(task.id, (False, 0.5))
                feasibility_matrix[i][j] = can_perform
                
                if can_perform:
                    forecast = self.forecasting_service.estimate_task(task, emp.type)
                    time_matrix[i][j] = forecast.predicted_effort * (2 - confidence)
                    print(f"    Task {i} ({task.title}): can_perform={can_perform}, confidence={confidence:.2f}, effort={time_matrix[i][j]:.1f}")
                else:
                    time_matrix[i][j] = 1e6  # Большое число для невозможных
        
        print(f"  Feasibility matrix: {feasibility_matrix.tolist()}")
        print(f"  Time matrix: {time_matrix.tolist()}")
        
        # Capacity
        capacities = np.array([
            (1.0 - emp.current_load) * emp.max_capacity * days / 7
            for emp in self.employees
        ])
        capacities = np.maximum(capacities, 0)
        
        # Оптимизация
        opt_result, message = self._solve_assignment_lp(
            time_matrix, capacities, feasibility_matrix
        )
        
        if opt_result is None:
            return OptimizationResult(
                success=False,
                message=message,
                method="scipy_linprog",
                unassigned_tasks=[t.id for t in sorted_tasks]
            )
        
        # Формируем результат
        assignments = []
        total_time = 0.0
        assigned_task_ids = set()
        
        for i, j in opt_result:
            if feasibility_matrix[i][j]:
                task = sorted_tasks[i]
                emp = self.employees[j]
                effort = time_matrix[i][j]
                
                # Оценка дней до завершения
                completion_days = effort / (emp.max_capacity / 7)  # часы -> дни
                
                assignments.append(AssignmentResult(
                    task_id=task.id,
                    employee_id=emp.id,
                    predicted_effort=effort,
                    predicted_completion_days=round(completion_days, 1),
                    confidence=0.8
                ))
                
                total_time += effort
                assigned_task_ids.add(task.id)
        
        # Находим неназначенные задачи
        unassigned = [t.id for t in sorted_tasks if t.id not in assigned_task_ids]
        
        return OptimizationResult(
            success=True,
            assignments=assignments,
            total_time=round(total_time, 1),
            message=message,
            unassigned_tasks=unassigned,
            method="scipy_linprog"
        )
    
    def create_capacity_plan(self, required_effort: float) -> Dict[str, Any]:
        """Создать план по емкости подразделения"""
        total_capacity = sum(
            emp.max_capacity * (1 - emp.current_load)
            for emp in self.employees
        )
        digital_capacity = sum(
            emp.max_capacity * (1 - emp.current_load)
            for emp in self.employees if emp.type == "digital"
        )
        
        return {
            "total_capacity": round(total_capacity, 1),
            "digital_capacity": round(digital_capacity, 1),
            "required_effort": required_effort,
            "is_sufficient": total_capacity >= required_effort,
            "digital_share": round(digital_capacity / total_capacity, 3) if total_capacity > 0 else 0,
            "surplus_deficit": round(total_capacity - required_effort, 1)
        }
    
    def _llm_can_perform_batch(self, employee: Employee, tasks: List[Task]) -> Dict[str, Tuple[bool, float]]:
        """
        LLM оценивает возможность выполнения ВСЕХ задач одним сотрудником за ОДИН вызов.
        Это сокращает количество вызовов LLM с N*M до N (где N - количество сотрудников).
        
        Args:
            employee: Сотрудник
            tasks: Список задач
            
        Returns:
            Dict[task_id -> (can_perform: bool, confidence: float)]
        """
        results = {}
        
        if not self.llm_service or not tasks:
            # Fallback для каждой задачи
            for task in tasks:
                results[task.id] = (employee.can_perform_task(task), 0.5)
            return results
        
        # Формируем список навыков без префиксов
        emp_skills = list(employee.skills.keys())
        emp_skills_clean = [s.replace("skill_", "") for s in emp_skills]
        
        # Формируем список задач для промпта
        tasks_str = ""
        for i, task in enumerate(tasks):
            required_skills = {k.replace("skill_", ""): v for k, v in task.required_skills.items()}
            tasks_str += f"{i+1}. \"{task.title}\" - требуется: {list(required_skills.keys()) if required_skills else 'none'}\n"
        
        prompt = f"""
Сотрудник: {employee.name}
Тип: {employee.type}
Навыки: {emp_skills_clean}
Capabilities: {employee.config.get('capabilities', [])}

Задачи для оценки ({len(tasks)} шт):
{tasks_str}

**ИНСТРУКЦИЯ:**
Для каждой задачи определи может ли сотрудник её выполнить based on skills.
Учитывай семантическую близость: python≈backend, devops≈infrastructure, ml≈ai, frontend≈react

Верни JSON в формате:
{{
    "{tasks[0].id}": {{"can_perform": true, "confidence": 0.8}},
    "{tasks[1].id}": {{"can_perform": false, "confidence": 0.5}}
}}
"""
        
        messages = [
            {"role": "system", "content": "Ты эксперт по оценке компетенций. Верни ТОЛЬКО JSON с оценкой всех задач."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self.llm_service._make_chat_request(messages, temperature=0.1, max_tokens=1024)
            
            if response:
                start_idx = response.find("{")
                end_idx = response.rfind("}") + 1
                if start_idx >= 0 and end_idx > start_idx:
                    import json
                    data = json.loads(response[start_idx:end_idx])
                    
                    for task in tasks:
                        if task.id in data:
                            task_result = data[task.id]
                            can_perform = task_result.get("can_perform", False)
                            confidence = float(task_result.get("confidence", 0.5))
                            results[task.id] = (can_perform, confidence)
                        else:
                            # Fallback для задачи без ответа
                            results[task.id] = (employee.can_perform_task(task), 0.5)
                    return results
        except Exception as e:
            print(f"LLM batch evaluation error: {e}")
        
        # Fallback для всех задач
        for task in tasks:
            results[task.id] = (employee.can_perform_task(task), 0.5)
        return results

    def _llm_can_perform(self, employee: Employee, task: Task) -> Tuple[bool, float]:
        """Обёртка для совместимости - вызывает batch метод для одной задачи"""
        results = self._llm_can_perform_batch(employee, [task])
        return results.get(task.id, (employee.can_perform_task(task), 0.5))

    def assign_task_to_employee(
        self,
        task: Task,
        employee: Employee
    ) -> bool:
        """
        Назначить задачу сотруднику.
        
        Args:
            task: Задача для назначения
            employee: Сотрудник
            
        Returns:
            True если успешно
        """
        if not employee.can_perform_task(task):
            return False
        
        task.assigned_id = employee.id
        task.assigned_at = datetime.now()
        task.status = TaskStatus.PLANNED
        
        # Обновляем нагрузку
        forecast = self.forecasting_service.estimate_task(task, employee.type)
        effort_fraction = forecast.predicted_effort / employee.max_capacity
        employee.current_load = min(1.0, employee.current_load + effort_fraction)
        
        # Сохраняем в БД
        try:
            db = DatabaseService()
            db.update_task(task)
        except:
            pass  # Игнорируем ошибки БД
        
        return True