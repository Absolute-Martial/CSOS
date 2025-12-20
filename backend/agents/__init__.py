"""
Personal Engineering OS - Agent Package
LangGraph-based agents for the Personal Engineering OS
"""

from .state import (
    # State types
    PAState,
    SchedulerState,
    PlannerState,
    WellbeingState,
    # Supporting types
    Message,
    ScheduleContext,
    UserProfile,
    CurrentTask,
    PendingAction,
    WellbeingMetrics,
    # Enums
    IntentType,
    WellbeingStatus,
    # State creators
    create_initial_pa_state,
    create_scheduler_state,
    create_planner_state,
    create_wellbeing_state,
)

from .pa_agent import (
    PersonalAssistantAgent,
    get_pa_agent,
    create_pa_agent_graph,
    compile_pa_agent,
)

from .scheduler_agent import (
    SchedulerAgent,
    get_scheduler_agent,
    create_scheduler_agent_graph,
    compile_scheduler_agent,
)

from .planner_agent import (
    PlannerAgent,
    get_planner_agent,
    create_planner_agent_graph,
    compile_planner_agent,
)

from .wellbeing_agent import (
    WellbeingAgent,
    get_wellbeing_agent,
    create_wellbeing_agent_graph,
    compile_wellbeing_agent,
)

from .progress_tracker_agent import (
    ProgressTrackerAgent,
    get_progress_tracker_agent,
    create_progress_tracker_graph,
    compile_progress_tracker,
    AnalysisPeriod,
    ProgressMetricType,
)

from .notifier_agent import (
    NotifierAgent,
    get_notifier_agent,
    create_notifier_agent_graph,
    compile_notifier_agent,
    NotificationType,
    NotificationPriority,
)


__all__ = [
    # State types
    "PAState",
    "SchedulerState",
    "PlannerState",
    "WellbeingState",
    "Message",
    "ScheduleContext",
    "UserProfile",
    "CurrentTask",
    "PendingAction",
    "WellbeingMetrics",
    # Enums
    "IntentType",
    "WellbeingStatus",
    "AnalysisPeriod",
    "ProgressMetricType",
    "NotificationType",
    "NotificationPriority",
    # State creators
    "create_initial_pa_state",
    "create_scheduler_state",
    "create_planner_state",
    "create_wellbeing_state",
    # Agent classes
    "PersonalAssistantAgent",
    "SchedulerAgent",
    "PlannerAgent",
    "WellbeingAgent",
    "ProgressTrackerAgent",
    "NotifierAgent",
    # Agent getters
    "get_pa_agent",
    "get_scheduler_agent",
    "get_planner_agent",
    "get_wellbeing_agent",
    "get_progress_tracker_agent",
    "get_notifier_agent",
    # Graph builders
    "create_pa_agent_graph",
    "create_scheduler_agent_graph",
    "create_planner_agent_graph",
    "create_wellbeing_agent_graph",
    "create_progress_tracker_graph",
    "create_notifier_agent_graph",
    # Graph compilers
    "compile_pa_agent",
    "compile_scheduler_agent",
    "compile_planner_agent",
    "compile_wellbeing_agent",
    "compile_progress_tracker",
    "compile_notifier_agent",
]

