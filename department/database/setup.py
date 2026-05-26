# """
# Модуль инициализации примерных данных для демонстрации
# """

# from department.database.service import DatabaseService
# from department.llm.service import LLMService
# from department.models.employee import HumanEmployee, DigitalEmployee
# from department.models.skill import SkillDetail, SkillLevel
# from department.models.task import Task, TaskStatus, Priority


# def setup_example_data(db: DatabaseService):
#     """Заполнить примерными данными для демонстрации"""
    
#     # Создаем навыки (id и name должны совпадать для корректной работы)
#     skills = [
#         SkillDetail("python", "python", "Python 3.10+, asyncio, type hints", "technical", False),
#         SkillDetail("ml", "ml", "Machine Learning, Scikit-learn, TensorFlow", "technical", False),
#         SkillDetail("devops", "devops", "Docker, Kubernetes, CI/CD", "technical", False),
#         SkillDetail("nlp", "nlp", "NLP Processing, LLM API", "technical", True),
#         SkillDetail("auto_test", "auto_test", "Автоматическое тестирование UI", "technical", True),
#         SkillDetail("backend", "backend", "Backend разработка, API, базы данных", "technical", False),
#         SkillDetail("frontend", "frontend", "Frontend разработка, JavaScript, React", "technical", False),
#     ]

#     for skill in skills:
#         db.add_skill(skill)
#     print(f"✅ Created {len(skills)} skills")

#     # Создаем цифрового сотрудника с skill_ids
#     digital_bot = DigitalEmployee(
#         id="BOT_001",
#         name="AutoTester-3000",
#         capabilities=["тестирование", "автоматизация", "ui", "проверка"]
#     )
#     digital_bot.skill_ids = ["auto_test"]  # Используем skill_ids для БД
#     digital_bot.max_capacity = 168.0
#     digital_bot.config = {
#         "webhook_url": "http://autotester-3000.internal/api",
#         "auto_retry": True,
#         "parallel_jobs": 5
#     }
#     db.add_employee(digital_bot)
#     print(f"✅ Created employee {digital_bot.name} with skills: {digital_bot.skill_ids}")

#     # Создаем человеческих сотрудников с skill_ids
#     emp1 = HumanEmployee(id="E001", name="Алексей Петров")
#     emp1.skill_ids = ["python", "ml"]  # Используем skill_ids для БД
#     db.add_employee(emp1)
#     print(f"✅ Created employee {emp1.name} with skills: {emp1.skill_ids}")

#     emp2 = HumanEmployee(id="E002", name="Мария Иванова")
#     emp2.skill_ids = ["devops"]  # Используем skill_ids для БД
#     db.add_employee(emp2)
#     print(f"✅ Created employee {emp2.name} with skills: {emp2.skill_ids}")

#     # Создаем задачи с навыками по имени
#     task1 = Task(
#         id="T001",
#         title="Разработка модуля авторизации",
#         description="Реализовать OAuth 2.0 с JWT токенами",
#         priority=Priority.HIGH,
#         estimated_effort=40.0,
#         required_skills={"python": 4}
#     )
#     db.add_task(task1)

#     task2 = Task(
#         id="T002",
#         title="Автоматизация тестирования UI",
#         description="Настроить автотесты для интерфейса",
#         priority=Priority.MEDIUM,
#         estimated_effort=20.0,
#         required_skills={"auto_test": 3}
#     )
#     db.add_task(task2)

#     print("✅ Example data loaded successfully")
#     print(f"📊 {len(skills)} skills, {3} employees, {2} tasks created")

# if __name__ == "__main__":
#     setup_example_data(DatabaseService())