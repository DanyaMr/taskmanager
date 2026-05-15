"""
Pydantic схемы для API цифрового двойника
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class FractalLevel(str, Enum):
    ENTERPRISE = "enterprise"
    DEPARTMENT = "department"
    TEAM = "team"
    UNIT = "unit"

class TaskStatusResponse(str, Enum):
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"

class PriorityResponse(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    TRIVIAL = "trivial"

class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    is_digital: bool = False

class EmployeeResponse(BaseModel):
    id: str
    name: str
    type: str
    current_load: float
    max_capacity: float
    performance_score: float = 1.0
    skills_count: int = 0
    skills: List[Dict] = Field(default_factory=list)
    is_overloaded: bool = False
    fractal_level: FractalLevel = FractalLevel.DEPARTMENT

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatusResponse
    priority: PriorityResponse
    created_at: Optional[datetime] = None
    priority_value: int = 2
    estimated_effort: float
    actual_effort: Optional[float] = None
    assigned_id: Optional[str] = None
    assignee_name: Optional[str] = None
    assigned_at: Optional[datetime] = None  # ДОБАВИТЬ ЭТО ПОЛЕ
    deadline: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)
    is_overdue: bool = False
    is_decomposed: bool = False
    fractal_level: FractalLevel = FractalLevel.DEPARTMENT

class TaskCreate(BaseModel):
    id: str
    title: str
    description: str
    required_skills: Dict[str, int] = Field(default_factory=dict)
    priority: str = "MEDIUM"
    estimated_effort: float = 1.0
    deadline: Optional[datetime] = None
    dependencies: List[str] = Field(default_factory=list)

class EmployeeCreate(BaseModel):
    id: str
    name: str
    type: str = "human"
    max_capacity: float = 40.0
    performance_score: Optional[float] = 1.0
    skill_ids: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)

class PlanningResult(BaseModel):
    session_id: str
    saved_assignments: int
    total_tasks: int
    fractal_level: str = "department"
    automation_rate: float
    detailed_plan: List["EmployeePlan"] = Field(default_factory=list)

class EmployeePlan(BaseModel):
    employee_id: str
    employee_name: str
    employee_type: str
    task_count: int
    tasks: List["TaskSummary"] = Field(default_factory=list)

class TaskSummary(BaseModel):
    id: str
    title: str
    effort: float

class DashboardResponse(BaseModel):
    timestamp: datetime
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    blocked_tasks: int
    total_employees: int
    digital_employees: int
    automation_rate: float
    forecast_accuracy: float
    capacity_utilization: float
    fractal_similarity: float = 0.92

class DecompositionResult(BaseModel):
    task_id: str
    subtasks: List["SubtaskResult"] = Field(default_factory=list)
    count: int

class SubtaskResult(BaseModel):
    id: str
    title: str
    effort: float

class FractalMetrics(BaseModel):
    automation_rate: float
    forecast_accuracy: float
    capacity_utilization: float
    digital_share: float
    fractal_level: str
    self_similarity_score: float

# Update forward references
PlanningResult.model_rebuild()
EmployeePlan.model_rebuild()