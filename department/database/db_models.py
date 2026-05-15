"""
ИСПРАВЛЕННЫЕ SQLAlchemy модели
Все несогласованности устранены
"""

from sqlalchemy import Column, String, Float, Integer, Boolean, ForeignKey, Table, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

# Таблица связи сотрудников и навыков
employee_skills = Table(
    'employee_skills',
    Base.metadata,
    Column('employee_id', String, ForeignKey('employees.id')),
    Column('skill_id', String, ForeignKey('skills.id')),
    Column('level', Integer, default=1)
)

class SkillDB(Base):
    """Навыки в БД"""
    __tablename__ = "skills"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)
    is_digital = Column(Boolean, default=False)

    # Добавляем обратную связь
    employees = relationship("EmployeeDB", secondary=employee_skills, back_populates="skills")

class EmployeeDB(Base):
    """Сотрудники в БД"""
    __tablename__ = "employees"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # human/digital
    current_load = Column(Float, default=0.0)
    performance_score = Column(Float, default=1.0)
    max_capacity = Column(Float, default=40.0)
    config = Column(JSON, default=dict)  # Используем JSON вместо Text
    fractal_level = Column(String, default="department")  # Добавлено
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Правильная связь
    skills = relationship("SkillDB", secondary=employee_skills, back_populates="employees")

class TaskDB(Base):
    """Задачи в БД"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    priority = Column(Integer, default=2)
    status = Column(String, default="backlog")
    estimated_effort = Column(Float, default=1.0)
    actual_effort = Column(Float, nullable=True)  # ✅ ДОБАВЬТЕ ЭТО
    required_skills = Column(JSON)  # ✅ Используйте JSON вместо Text
    dependencies = Column(JSON)     # ✅ Используйте JSON вместо Text
    assigned_id = Column(String, ForeignKey('employees.id'))
    parent_task_id = Column(String, nullable=True)  # ✅ ДОБАВЬТЕ ЭТО
    is_decomposed = Column(Boolean, default=False)
    deadline = Column(DateTime(timezone=True), nullable=True)  # ✅ УБЕРИТЕ server_default
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    assigned_at = Column(DateTime(timezone=True), nullable=True)  # ДОБАВЬТЕ ЭТО ПОЛЕ
    fractal_level = Column(String, default="department")  # ✅ ДОБАВЬТЕ ЭТО

    assignee = relationship("EmployeeDB", backref="assigned_tasks")