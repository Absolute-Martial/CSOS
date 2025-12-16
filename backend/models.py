"""
Personal Engineering OS - Pydantic Models (v2 syntax)
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


# ============================================
# ENUMS
# ============================================

class SubjectType(str, Enum):
    PRACTICE_HEAVY = "practice_heavy"
    CONCEPT_HEAVY = "concept_heavy"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProgressStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AssignmentStatus(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"


class FileType(str, Enum):
    SLIDE = "slide"
    ASSIGNMENT = "assignment"
    NOTE = "note"


class NotificationType(str, Enum):
    DUE_DATE = "due_date"
    REVISION = "revision"
    STREAK_WARNING = "streak_warning"
    ACHIEVEMENT = "achievement"


# ============================================
# SUBJECT MODELS
# ============================================

class SubjectBase(BaseModel):
    code: str
    name: str
    credits: int = 3
    type: SubjectType
    color: str = "#6366f1"


class SubjectCreate(SubjectBase):
    pass


class Subject(SubjectBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime


# ============================================
# CHAPTER MODELS
# ============================================

class ChapterBase(BaseModel):
    number: int
    title: str
    total_pages: int = 0


class ChapterCreate(ChapterBase):
    subject_id: int


class ChapterProgress(BaseModel):
    reading_status: ProgressStatus = ProgressStatus.NOT_STARTED
    assignment_status: AssignmentStatus = AssignmentStatus.LOCKED
    mastery_level: int = 0
    revision_count: int = 0
    last_revised_at: Optional[datetime] = None
    notes: Optional[str] = None


class Chapter(ChapterBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    subject_id: int
    folder_path: Optional[str] = None
    created_at: datetime
    progress: Optional[ChapterProgress] = None


# ============================================
# TASK MODELS
# ============================================

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: Optional[int] = None
    priority: int = 5
    duration_mins: int = 60
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    is_deep_work: bool = False


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


# ============================================
# LAB REPORT MODELS
# ============================================

class LabReportBase(BaseModel):
    title: str
    subject_id: int
    deadline: datetime
    notes: Optional[str] = None


class LabReportCreate(LabReportBase):
    pass


class LabReport(LabReportBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: TaskStatus
    file_path: Optional[str] = None
    created_at: datetime


# ============================================
# AI MODELS
# ============================================

class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Any]] = None


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[List[dict]] = None
    notifications: Optional[List[dict]] = None


class AIGuidelineCreate(BaseModel):
    rule: str
    priority: int = 5


class AIMemoryCreate(BaseModel):
    category: str
    key: str
    value: str


# ============================================
# API RESPONSE MODELS
# ============================================

class HealthStatus(BaseModel):
    status: str = "healthy"
    version: str = "1.0.1"
    database: str = "connected"
    copilot_api: str = "unknown"


class MorningBriefing(BaseModel):
    greeting: str
    current_streak: int
    streak_icon: str = ""
    tasks_today: int
    revisions_due: int
    deep_work_available: int
    unread_notifications: int
    next_reward: Optional[str] = None
    points_to_next: Optional[int] = None


class UserStreak(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    current_streak: int = 0
    longest_streak: int = 0
    total_points: int = 0
    last_activity_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    type: NotificationType
    title: str
    message: str
    read: bool = False
    dismissed: bool = False
    due_at: Optional[datetime] = None
    created_at: datetime


class AIGuideline(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    rule: str
    priority: int = 5
    active: bool = True
    created_at: datetime
