"""
Модуль инициализации примерных данных для демонстрации
"""

from enterprise_twin.models.department.database.service import DatabaseService
from enterprise_twin.models.department.llm.service import LLMService
from enterprise_twin.models.department.models.employee import HumanEmployee, DigitalEmployee
from enterprise_twin.models.department.models.skill import SkillDetail, SkillLevel
from enterprise_twin.models.department.models.task import Task, TaskStatus, Priority


def setup_example_data(db: DatabaseService):
    """Заполнить примерными данными для демонстрации"""

    # Создаем навыки
    skills = [
        SkillDetail("py", "Python", "Python 3.10+, asyncio, type hints", "technical", False),
        SkillDetail("ml", "Machine Learning", "Scikit-learn, TensorFlow, нейросети", "technical", False),
        SkillDetail("devops", "DevOps", "Docker, Kubernetes, CI/CD", "technical", False),
        SkillDetail("nlp", "NLP Processing", "Обработка естественного языка, LLM API", "technical", True),
        SkillDetail("auto_test", "Auto Testing", "Автоматическое тестирование UI", "technical", True),
    ]

    for skill in skills:
        db.add_skill(skill)

    # Создаем цифрового сотрудника
    digital_bot = DigitalEmployee(
        id="BOT_001",
        name="AutoTester-3000",
        capabilities=["тестирование", "автоматизация", "ui", "проверка"]
    )
    digital_bot.skills["auto_test"] = SkillLevel(skills[4], 5)
    digital_bot.max_capacity = 168.0
    digital_bot.config = {
        "webhook_url": "http://autotester-3000.internal/api",
        "auto_retry": True,
        "parallel_jobs": 5
    }
    db.add_employee(digital_bot)

    # Создаем человеческих сотрудников
    emp1 = HumanEmployee(id="E001", name="Алексей Петров")
    emp1.skills["py"] = SkillLevel(skills[0], 5)
    emp1.skills["ml"] = SkillLevel(skills[1], 4)
    db.add_employee(emp1)

    emp2 = HumanEmployee(id="E002", name="Мария Иванова")
    emp2.skills["devops"] = SkillLevel(skills[2], 5)
    db.add_employee(emp2)

    # Создаем задачи
    task1 = Task(
        id="T001",
        title="Разработка модуля авторизации",
        description="Реализовать OAuth 2.0 с JWT токенами",
        priority=Priority.HIGH,
        estimated_effort=40.0,
        required_skills={"py": 4}
    )
    db.add_task(task1)

    task2 = Task(
        id="T002",
        title="Автоматизация тестирования UI",
        description="Настроить автотесты для интерфейса",
        priority=Priority.MEDIUM,
        estimated_effort=20.0,
        required_skills={"auto_test": 3}
    )
    db.add_task(task2)

    print("✅ Example data loaded successfully")
    print(f"📊 {len(skills)} skills, {3} employees, {2} tasks created")

if __name__ == "__main__":
    setup_example_data(DatabaseService())