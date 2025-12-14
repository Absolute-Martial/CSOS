"""
Personal Engineering OS - Pydantic Models
MIT 6.100L aligned: abstraction, type safety
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field


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
    code: str = Field(..., pattern=r"^[A-Z]{4}[0-9]{3}$", example="MATH101")
    name: str
    credits: int = Field(ge=1, le=6, default=3)
    type: SubjectType
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class SubjectCreate(SubjectBase):
    pass


class Subject(SubjectBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# CHAPTER MODELS
# ============================================

class ChapterBase(BaseModel):
    number: int = Field(ge=1)
    title: str
    total_pages: int = Field(default=0, ge=0)


class ChapterCreate(ChapterBase):
    subject_id: int


class ChapterProgress(BaseModel):
    reading_status: ProgressStatus = ProgressStatus.NOT_STARTED
    assignment_status: AssignmentStatus = AssignmentStatus.LOCKED
    mastery_level: int = Field(default=0, ge=0, le=100)
    revision_count: int = 0
    last_revised_at: Optional[datetime] = None
    notes: Optional[str] = None


class Chapter(ChapterBase):
    id: int
    subject_id: int
    folder_path: Optional[str]
    created_at: datetime
    progress: Optional[ChapterProgress] = None

    class Config:
        from_attributes = True


# ============================================
# TASK MODELS
# ============================================

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: Optional[int] = None
    priority: int = Field(default=5, ge=1, le=10)
    duration_mins: int = Field(default=60, ge=5)
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    is_deep_work: bool = False


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    id: int
    status: TaskStatus
    file_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# REVISION MODELS
# ============================================

class RevisionSchedule(BaseModel):
    id: int
    chapter_id: int
    revision_number: int
    due_date: date
    completed: bool
    completed_at: Optional[datetime]
    points_earned: int

    class Config:
        from_attributes = True


class RevisionQueueItem(BaseModel):
    revision_id: int
    chapter_number: int
    chapter_title: str
    subject_code: str
    subject_credits: int
    due_date: date
    revision_number: int


# ============================================
# FILE MODELS
# ============================================

class ChapterFile(BaseModel):
    id: int
    chapter_id: int
    file_type: FileType
    filename: str
    filepath: str
    mimetype: Optional[str]
    file_size: Optional[int]
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ============================================
# STREAK & REWARDS
# ============================================

class UserStreak(BaseModel):
    current_streak: int
    longest_streak: int
    total_points: int
    last_activity: Optional[date]
    next_reward: Optional[str] = None
    points_to_next: Optional[int] = None


class Reward(BaseModel):
    id: int
    name: str
    icon: str
    required_streak: int
    unlocked: bool
    unlocked_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================
# AI MODELS
# ============================================

class AIMemory(BaseModel):
    id: int
    category: str
    key: str
    value: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIMemoryCreate(BaseModel):
    category: str
    key: str
    value: str


class AIGuideline(BaseModel):
    id: int
    rule: str
    priority: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AIGuidelineCreate(BaseModel):
    rule: str
    priority: int = 5


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    tool_calls: Optional[List[Any]] = None


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: Optional[List[dict]] = None
    notifications: Optional[List[dict]] = None


# ============================================
# NOTIFICATION MODELS
# ============================================

class Notification(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str
    due_at: Optional[datetime]
    read: bool
    dismissed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# DEEP WORK GAP MODELS
# ============================================

class TimeSlot(BaseModel):
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)


class ScheduleGap(BaseModel):
    start: str  # "HH:MM" format
    end: str
    duration_mins: int


class GapAnalysisResult(BaseModel):
    gaps: List[ScheduleGap]
    count: int


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
    due_today: List[dict]
    revisions_today: List[dict]
    deep_work_available: int  # minutes
