"""
Personal Engineering OS - Agent State Definitions
Shared state types for LangGraph agents
"""

from typing import TypedDict, Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum
import operator


class IntentType(str, Enum):
    """Types of user intents the PA agent can identify."""
    SCHEDULE_QUERY = "schedule_query"           # "What's my schedule today?"
    SCHEDULE_MODIFY = "schedule_modify"         # "Add a study block at 3pm"
    TASK_MANAGE = "task_manage"                 # "Mark physics revision as done"
    STUDY_START = "study_start"                 # "Start studying calculus"
    STUDY_STOP = "study_stop"                   # "Stop timer"
    GOAL_MANAGE = "goal_manage"                 # "Create a goal to finish chapter 5"
    LAB_REPORT = "lab_report"                   # "Add a physics lab report"
    REVISION = "revision"                       # "What revisions are due?"
    DEADLINE = "deadline"                       # "When is the chemistry assignment due?"
    WELLBEING = "wellbeing"                     # "I'm feeling stressed"
    GENERAL_CHAT = "general_chat"               # General conversation
    RESCHEDULE = "reschedule"                   # "I got sick, reschedule everything"
    BACKWARD_PLAN = "backward_plan"             # "I have an exam on Friday"
    ANALYTICS = "analytics"                     # "How much did I study this week?"
    MEMORY = "memory"                           # "Remember that I wake up at 5am"
    UNKNOWN = "unknown"


class WellbeingStatus(str, Enum):
    """User wellbeing status levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    STRESSED = "stressed"
    EXHAUSTED = "exhausted"


class Message(TypedDict):
    """Chat message structure."""
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: Optional[str]
    tool_calls: Optional[List[Dict]]
    tool_results: Optional[List[Dict]]


class ScheduleContext(TypedDict, total=False):
    """Current schedule context for AI decision making."""
    date: str
    day_name: str
    current_time: str
    timetable: List[Dict]
    tasks: List[Dict]
    gaps: List[Dict]
    total_available_mins: int
    deep_work_available_mins: int
    active_timer: Optional[Dict]
    pending_revisions: List[Dict]
    upcoming_deadlines: List[Dict]
    lab_reports: List[Dict]


class UserProfile(TypedDict, total=False):
    """User profile and preferences."""
    sleep_start: str
    sleep_end: str
    preferred_study_times: List[str]
    max_study_block_mins: int
    commute_mins: int
    energy_level: int  # Current energy 1-10
    current_streak: int
    total_points: int
    memories: List[Dict]
    guidelines: List[Dict]


class CurrentTask(TypedDict, total=False):
    """Currently active task or study session."""
    task_id: Optional[int]
    session_id: Optional[int]
    title: str
    subject_code: Optional[str]
    started_at: str
    elapsed_seconds: int
    is_deep_work: bool


class PendingAction(TypedDict, total=False):
    """An action pending execution."""
    action_type: str
    tool_name: str
    parameters: Dict[str, Any]
    confirmation_required: bool
    description: str


class WellbeingMetrics(TypedDict, total=False):
    """Wellbeing metrics for the user."""
    status: str
    stress_level: int  # 1-10
    study_hours_today: float
    study_hours_week: float
    break_compliance: float  # 0-1
    deep_work_ratio: float  # 0-1
    streak_days: int
    last_break_mins_ago: int
    recommendations: List[str]


# Reducer function for messages - appends new messages
def add_messages(left: List[Message], right: List[Message]) -> List[Message]:
    """Reducer that appends messages to the list."""
    return left + right


# Reducer function for notifications - appends new notifications
def add_notifications(left: List[Dict], right: List[Dict]) -> List[Dict]:
    """Reducer that appends notifications to the list."""
    return left + right


class PAState(TypedDict, total=False):
    """
    Personal Assistant Agent State.

    This is the main state that flows through the LangGraph.
    Uses reducers for append-only fields.
    """
    # Conversation history - uses reducer to append
    messages: Annotated[List[Message], add_messages]

    # Current context
    schedule_context: ScheduleContext
    user_profile: UserProfile
    current_task: Optional[CurrentTask]

    # Wellbeing tracking
    wellbeing_score: float  # 0-1 overall score
    wellbeing_metrics: WellbeingMetrics

    # Action planning
    identified_intent: str
    intent_confidence: float
    planned_actions: List[PendingAction]
    pending_notifications: Annotated[List[Dict], add_notifications]

    # Execution tracking
    last_action: Optional[str]
    last_action_result: Optional[Dict]
    action_history: List[Dict]

    # Response generation
    response_text: str
    tool_calls_made: List[Dict]

    # Error handling
    error: Optional[str]
    retry_count: int


class SchedulerState(TypedDict, total=False):
    """
    Scheduler Agent State.

    Specialized state for schedule optimization.
    """
    # Input
    target_date: str
    optimization_reason: Optional[str]
    constraints: Dict[str, Any]

    # Schedule data
    timetable: List[Dict]
    existing_tasks: List[Dict]
    gaps: List[Dict]
    pending_items: List[Dict]

    # Optimization results
    optimized_schedule: List[Dict]
    created_blocks: List[Dict]
    moved_blocks: List[Dict]
    deleted_blocks: List[Dict]

    # Statistics
    total_study_mins: int
    deep_work_mins: int
    items_scheduled: int
    gaps_filled: int

    # Output
    summary: str
    recommendations: List[str]


class PlannerState(TypedDict, total=False):
    """
    Study Planner Agent State.

    Specialized state for study planning and pattern analysis.
    """
    # Input
    planning_horizon_days: int
    focus_subject: Optional[str]
    deadline_date: Optional[str]

    # Analysis data
    study_patterns: Dict[str, Any]
    subject_progress: Dict[str, Any]
    revision_schedule: List[Dict]
    goals: List[Dict]

    # Planning output
    recommended_plan: List[Dict]
    daily_targets: Dict[str, int]
    priority_order: List[str]

    # Insights
    insights: List[str]
    warnings: List[str]
    achievements: List[str]


class WellbeingState(TypedDict, total=False):
    """
    Wellbeing Monitor Agent State.

    Specialized state for tracking user wellbeing.
    """
    # Current metrics
    study_hours_today: float
    study_hours_week: float
    deep_work_sessions_today: int
    breaks_taken_today: int
    last_break_at: Optional[str]

    # Calculated scores
    stress_level: int  # 1-10
    fatigue_level: int  # 1-10
    productivity_score: float  # 0-1
    balance_score: float  # 0-1

    # Analysis
    status: str
    risk_factors: List[str]
    positive_factors: List[str]

    # Recommendations
    immediate_action: Optional[str]
    suggestions: List[str]
    should_take_break: bool
    recommended_break_mins: int


# Helper functions for state manipulation

def create_initial_pa_state(user_message: str) -> PAState:
    """Create initial PA state from user message."""
    return PAState(
        messages=[{
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
            "tool_calls": None,
            "tool_results": None
        }],
        schedule_context={},
        user_profile={},
        current_task=None,
        wellbeing_score=0.7,
        wellbeing_metrics={},
        identified_intent=IntentType.UNKNOWN,
        intent_confidence=0.0,
        planned_actions=[],
        pending_notifications=[],
        last_action=None,
        last_action_result=None,
        action_history=[],
        response_text="",
        tool_calls_made=[],
        error=None,
        retry_count=0
    )


def create_scheduler_state(target_date: str, reason: Optional[str] = None) -> SchedulerState:
    """Create initial scheduler state."""
    return SchedulerState(
        target_date=target_date,
        optimization_reason=reason,
        constraints={},
        timetable=[],
        existing_tasks=[],
        gaps=[],
        pending_items=[],
        optimized_schedule=[],
        created_blocks=[],
        moved_blocks=[],
        deleted_blocks=[],
        total_study_mins=0,
        deep_work_mins=0,
        items_scheduled=0,
        gaps_filled=0,
        summary="",
        recommendations=[]
    )


def create_planner_state(horizon_days: int = 7) -> PlannerState:
    """Create initial planner state."""
    return PlannerState(
        planning_horizon_days=horizon_days,
        focus_subject=None,
        deadline_date=None,
        study_patterns={},
        subject_progress={},
        revision_schedule=[],
        goals=[],
        recommended_plan=[],
        daily_targets={},
        priority_order=[],
        insights=[],
        warnings=[],
        achievements=[]
    )


def create_wellbeing_state() -> WellbeingState:
    """Create initial wellbeing state."""
    return WellbeingState(
        study_hours_today=0.0,
        study_hours_week=0.0,
        deep_work_sessions_today=0,
        breaks_taken_today=0,
        last_break_at=None,
        stress_level=5,
        fatigue_level=5,
        productivity_score=0.5,
        balance_score=0.5,
        status=WellbeingStatus.MODERATE,
        risk_factors=[],
        positive_factors=[],
        immediate_action=None,
        suggestions=[],
        should_take_break=False,
        recommended_break_mins=0
    )
