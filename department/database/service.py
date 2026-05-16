"""
ИСПРАВЛЕННЫЙ Сервис работы с базой данных
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from department.database.db_models import Base, SkillDB, EmployeeDB, TaskDB, employee_skills
from department.models.task import Priority

class DatabaseService:
    def __init__(self, db_url: str = None):
        BASE_DIR = Path(__file__).resolve().parent
        DB_PATH = BASE_DIR / "department.db"
        db_url = f"sqlite:///{DB_PATH}"

        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def init_database(self):
        Base.metadata.create_all(self.engine)
        print("Database initialized")

    def add_skill(self, skill_detail) -> SkillDB:
        session = self.Session()
        try:
            skill = SkillDB(
                id=skill_detail.id,
                name=skill_detail.name,
                description=getattr(skill_detail, 'description', ''),
                category=getattr(skill_detail, 'category', ''),
                is_digital=getattr(skill_detail, 'is_digital', False)
            )
            session.merge(skill)
            session.commit()
            return skill
        finally:
            session.close()

    def add_employee(self, employee_detail) -> EmployeeDB:
        """Добавить сотрудника с правильной обработкой навыков"""
        session = self.Session()
        try:
            employee = EmployeeDB(
                id=employee_detail.id,
                name=employee_detail.name,
                type=employee_detail.type,
                max_capacity=employee_detail.max_capacity,
                config=getattr(employee_detail, 'config', {}),
                current_load=0.0,
                performance_score=1.0
            )
            session.merge(employee)

            # Правильная работа с many-to-many (skill_ids - это названия навыков)
            if hasattr(employee_detail, 'skill_ids') and employee_detail.skill_ids:
                for skill_name in employee_detail.skill_ids:
                    # Ищем по имени (case-insensitive)
                    skill = session.query(SkillDB).filter(SkillDB.name.ilike(skill_name)).first()
                    if skill and skill not in employee.skills:
                        employee.skills.append(skill)
                        print(f"✅ Added skill {skill.name} to employee {employee.name}")

            session.commit()
            return employee
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add_task(self, task_detail) -> TaskDB:
        """Добавить задачу с JSON-полями"""
        session = self.Session()
        try:
            # Маппинг приоритета

            priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4, "trivial": 5}
            priority_value = priority_map.get(
                getattr(task_detail, 'priority', Priority.MEDIUM), 3
            )

            task = TaskDB(
                id=task_detail.id,
                title=task_detail.title,
                description=getattr(task_detail, 'description', ''),
                priority=priority_value,
                status="backlog",
                estimated_effort=task_detail.estimated_effort,
                required_skills=getattr(task_detail, 'required_skills', {}),
                dependencies=getattr(task_detail, 'dependencies', []),
                assigned_id=getattr(task_detail, 'assigned_id', None),
                assigned_at=getattr(task_detail, 'assigned_at', None),  # ДОБАВИТЬ
                deadline=getattr(task_detail, 'deadline', None)
            )
            session.add(task)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_dashboard_data(self) -> Dict[str, Any]:
        session = self.Session()
        try:
            return {
                "total_tasks": session.query(TaskDB).count(),
                "total_employees": session.query(EmployeeDB).count(),
                "completed_tasks": session.query(TaskDB).filter_by(status="done").count(),
                "in_progress_tasks": session.query(TaskDB).filter_by(status="in_progress").count(),
                "blocked_tasks": session.query(TaskDB).filter_by(status="blocked").count(),
                "digital_employees": session.query(EmployeeDB).filter_by(type="digital").count(),
                "automation_rate": 0.0,
                "forecast_accuracy": 0.85,
                "capacity_utilization": 0.72,
                "fractal_similarity": 0.92
            }
        finally:
            session.close()