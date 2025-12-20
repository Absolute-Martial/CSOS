"""
AI Engineering Study Assistant - Notifier Agent
Specialized agent for proactive notifications, reminders, and intelligent alerts.
"""

import os
import json
import logging
from datetime import datetime, date, timedelta, time
from typing import Optional, Dict, Any, List, TypedDict
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI

from .state import Message

logger = logging.getLogger(__name__)


# ============================================
# NOTIFICATION TYPES
# ============================================

class NotificationType(str, Enum):
    """Types of notifications the agent can generate."""
    REMINDER = "reminder"           # Task/deadline reminders
    SUGGESTION = "suggestion"       # Study suggestions
    ACHIEVEMENT = "achievement"     # Milestone celebrations
    WARNING = "warning"             # Schedule conflicts, overdue items
    MOTIVATION = "motivation"       # Encouragement messages
    BREAK_REMINDER = "break"        # Time to take a break
    REVISION_DUE = "revision"       # Spaced repetition reminders
    GAP_OPPORTUNITY = "gap"         # Available study gap detected
    DEADLINE_ALERT = "deadline"     # Upcoming deadline


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "in_app"
    TOAST = "toast"
    WEBSOCKET = "websocket"
    EMAIL = "email"


# ============================================
# DATA STRUCTURES
# ============================================

@dataclass
class Notification:
    """A single notification to be delivered."""
    id: str
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }


class NotifierState(TypedDict):
    """State for the Notifier agent."""
    # Trigger context
    trigger_type: str  # "scheduled", "event", "manual"
    trigger_event: Optional[str]
    current_time: datetime
    
    # User context
    user_preferences: Dict[str, Any]
    quiet_hours_start: Optional[time]
    quiet_hours_end: Optional[time]
    
    # Data sources
    pending_tasks: List[Dict[str, Any]]
    upcoming_deadlines: List[Dict[str, Any]]
    revisions_due: List[Dict[str, Any]]
    schedule_gaps: List[Dict[str, Any]]
    recent_achievements: List[Dict[str, Any]]
    current_streak: int
    
    # Generated notifications
    notifications: List[Dict[str, Any]]
    filtered_notifications: List[Dict[str, Any]]
    
    # Output
    delivery_queue: List[Dict[str, Any]]
    websocket_payload: Optional[Dict[str, Any]]
    
    # Metadata
    messages: List[Message]
    error: Optional[str]


def create_notifier_state(
    trigger_type: str = "scheduled"
) -> NotifierState:
    """Create initial state for notifier."""
    return NotifierState(
        trigger_type=trigger_type,
        trigger_event=None,
        current_time=datetime.now(),
        user_preferences={},
        quiet_hours_start=None,
        quiet_hours_end=None,
        pending_tasks=[],
        upcoming_deadlines=[],
        revisions_due=[],
        schedule_gaps=[],
        recent_achievements=[],
        current_streak=0,
        notifications=[],
        filtered_notifications=[],
        delivery_queue=[],
        websocket_payload=None,
        messages=[],
        error=None,
    )


# ============================================
# LLM INITIALIZATION
# ============================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("NOTIFIER_MODEL_NAME", "gpt-3.5-turbo")


def get_llm():
    """Get LLM instance for notification generation."""
    if OPENAI_API_KEY:
        return ChatOpenAI(
            model=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            temperature=0.7  # Slightly creative for motivational messages
        )
    return None


# ============================================
# DATA GATHERING FUNCTIONS
# ============================================

async def gather_notification_context() -> Dict[str, Any]:
    """Gather all context needed for notification generation."""
    from database import db
    
    context = {
        "pending_tasks": [],
        "upcoming_deadlines": [],
        "revisions_due": [],
        "schedule_gaps": [],
        "recent_achievements": [],
        "current_streak": 0,
    }
    
    today = date.today()
    now = datetime.now()
    
    try:
        # Pending tasks for today
        tasks_query = """
            SELECT id, title, priority, scheduled_start, subject_id
            FROM tasks
            WHERE status = 'pending' AND DATE(scheduled_start) = $1
            ORDER BY priority DESC, scheduled_start
            LIMIT 10
        """
        context["pending_tasks"] = [
            dict(row) for row in await db.fetch(tasks_query, today)
        ]
        
        # Upcoming deadlines (next 7 days)
        deadlines_query = """
            SELECT id, title, deadline, priority
            FROM tasks
            WHERE status != 'completed' AND deadline BETWEEN $1 AND $2
            ORDER BY deadline
            LIMIT 10
        """
        context["upcoming_deadlines"] = [
            dict(row) for row in await db.fetch(deadlines_query, today, today + timedelta(days=7))
        ]
        
        # Lab reports
        labs_query = """
            SELECT id, title, deadline, status
            FROM lab_reports
            WHERE status != 'submitted' AND deadline >= $1
            ORDER BY deadline
            LIMIT 5
        """
        labs = await db.fetch(labs_query, today)
        for lab in labs:
            context["upcoming_deadlines"].append({
                "id": f"lab_{lab['id']}",
                "title": f"Lab: {lab['title']}",
                "deadline": lab['deadline'],
                "priority": 8,
                "type": "lab_report",
            })
        
        # Revisions due
        revisions_query = """
            SELECT rs.id, c.title as chapter_title, s.name as subject_name, rs.scheduled_date
            FROM revision_schedule rs
            JOIN chapters c ON c.id = rs.chapter_id
            JOIN subjects s ON s.id = c.subject_id
            WHERE rs.status = 'pending' AND rs.scheduled_date <= $1
            ORDER BY rs.scheduled_date
            LIMIT 5
        """
        context["revisions_due"] = [
            dict(row) for row in await db.fetch(revisions_query, today + timedelta(days=1))
        ]
        
        # Current streak
        streak_query = """
            SELECT current_streak FROM user_streak WHERE id = 1
        """
        streak_row = await db.fetchrow(streak_query)
        context["current_streak"] = streak_row['current_streak'] if streak_row else 0
        
        # Recent achievements (last 24 hours)
        achievements_query = """
            SELECT type, title, message, created_at
            FROM proactive_notifications
            WHERE type = 'achievement' AND created_at >= $1
            ORDER BY created_at DESC
            LIMIT 3
        """
        context["recent_achievements"] = [
            dict(row) for row in await db.fetch(achievements_query, now - timedelta(hours=24))
        ]
        
    except Exception as e:
        logger.error(f"Error gathering notification context: {e}")
    
    return context


async def get_user_preferences() -> Dict[str, Any]:
    """Get user notification preferences."""
    from database import db
    
    prefs = {
        "enabled_types": list(NotificationType),
        "quiet_hours_start": time(22, 0),
        "quiet_hours_end": time(7, 0),
        "frequency_limit": 5,  # Max notifications per hour
    }
    
    try:
        query = """
            SELECT * FROM notification_preferences
        """
        rows = await db.fetch(query)
        for row in rows:
            prefs[row['notification_type']] = {
                "enabled": row['enabled'],
                "quiet_hours_start": row.get('quiet_hours_start'),
                "quiet_hours_end": row.get('quiet_hours_end'),
            }
    except Exception as e:
        logger.warning(f"Could not load preferences: {e}")
    
    return prefs


# ============================================
# NOTIFICATION GENERATORS
# ============================================

def generate_deadline_notifications(
    deadlines: List[Dict[str, Any]],
    current_time: datetime
) -> List[Notification]:
    """Generate notifications for upcoming deadlines."""
    import uuid
    notifications = []
    
    for deadline in deadlines:
        deadline_dt = deadline.get('deadline')
        if isinstance(deadline_dt, date) and not isinstance(deadline_dt, datetime):
            deadline_dt = datetime.combine(deadline_dt, time(23, 59))
        
        if not deadline_dt:
            continue
        
        hours_until = (deadline_dt - current_time).total_seconds() / 3600
        
        if hours_until < 0:
            # Overdue
            notifications.append(Notification(
                id=str(uuid.uuid4()),
                type=NotificationType.WARNING,
                priority=NotificationPriority.URGENT,
                title="⚠️ Overdue Task",
                message=f"'{deadline['title']}' is overdue!",
                action_url=f"/tasks/{deadline['id']}",
                action_label="View Task",
            ))
        elif hours_until < 24:
            # Due within 24 hours
            notifications.append(Notification(
                id=str(uuid.uuid4()),
                type=NotificationType.DEADLINE_ALERT,
                priority=NotificationPriority.HIGH,
                title="⏰ Due Soon",
                message=f"'{deadline['title']}' is due in {int(hours_until)} hours",
                action_url=f"/tasks/{deadline['id']}",
                action_label="Work on it",
            ))
        elif hours_until < 72:
            # Due within 3 days
            days = int(hours_until / 24)
            notifications.append(Notification(
                id=str(uuid.uuid4()),
                type=NotificationType.REMINDER,
                priority=NotificationPriority.MEDIUM,
                title="📅 Upcoming Deadline",
                message=f"'{deadline['title']}' is due in {days} days",
                action_url=f"/tasks/{deadline['id']}",
                action_label="Plan ahead",
            ))
    
    return notifications


def generate_revision_notifications(
    revisions: List[Dict[str, Any]]
) -> List[Notification]:
    """Generate notifications for due revisions (spaced repetition)."""
    import uuid
    notifications = []
    
    for revision in revisions:
        notifications.append(Notification(
            id=str(uuid.uuid4()),
            type=NotificationType.REVISION_DUE,
            priority=NotificationPriority.MEDIUM,
            title="📚 Revision Due",
            message=f"Time to revise: {revision['chapter_title']} ({revision['subject_name']})",
            action_url=f"/revisions/{revision['id']}",
            action_label="Start Revision",
            metadata={"chapter_id": revision.get("chapter_id")},
        ))
    
    return notifications


def generate_break_reminder(
    last_study_start: Optional[datetime],
    current_time: datetime
) -> Optional[Notification]:
    """Generate break reminder if studying too long."""
    import uuid
    
    if not last_study_start:
        return None
    
    study_duration = (current_time - last_study_start).total_seconds() / 60
    
    if study_duration >= 90:
        return Notification(
            id=str(uuid.uuid4()),
            type=NotificationType.BREAK_REMINDER,
            priority=NotificationPriority.MEDIUM,
            title="☕ Time for a Break",
            message=f"You've been studying for {int(study_duration)} minutes. Take a 15-minute break!",
            action_url="/timer/break",
            action_label="Start Break",
        )
    
    return None


def generate_motivation_notification(streak: int) -> Optional[Notification]:
    """Generate motivational notification based on streak."""
    import uuid
    
    messages = {
        3: ("🔥 3-Day Streak!", "You're building momentum! Keep it up!"),
        7: ("⭐ One Week Strong!", "A full week of consistent study. Amazing!"),
        14: ("🏆 Two Weeks!", "Your dedication is impressive. You're unstoppable!"),
        30: ("👑 Monthly Master!", "30 days of consistency. You're a legend!"),
    }
    
    if streak in messages:
        title, message = messages[streak]
        return Notification(
            id=str(uuid.uuid4()),
            type=NotificationType.ACHIEVEMENT,
            priority=NotificationPriority.LOW,
            title=title,
            message=message,
        )
    
    return None


def generate_gap_notification(
    gaps: List[Dict[str, Any]],
    current_time: datetime
) -> Optional[Notification]:
    """Generate notification for available study gap."""
    import uuid
    
    for gap in gaps:
        gap_start = gap.get("start_time")
        if not gap_start:
            continue
        
        # Check if gap is coming up soon (within 30 mins)
        if isinstance(gap_start, str):
            # Parse time string
            hour, minute = map(int, gap_start.split(":"))
            gap_start = current_time.replace(hour=hour, minute=minute, second=0)
        
        minutes_until = (gap_start - current_time).total_seconds() / 60
        
        if 0 < minutes_until <= 30:
            duration = gap.get("duration_slots", 2) * 30  # 30 min slots
            
            return Notification(
                id=str(uuid.uuid4()),
                type=NotificationType.GAP_OPPORTUNITY,
                priority=NotificationPriority.LOW,
                title="💡 Study Opportunity",
                message=f"You have a {duration}-minute gap coming up. Perfect for a quick study session!",
                action_url="/schedule/gaps",
                action_label="Fill Gap",
                metadata={"gap_duration": duration},
            )
    
    return None


# ============================================
# GRAPH NODES
# ============================================

async def gather_context_node(state: NotifierState) -> Dict[str, Any]:
    """Gather all context for notification generation."""
    try:
        context = await gather_notification_context()
        preferences = await get_user_preferences()
        
        return {
            **context,
            "user_preferences": preferences,
            "quiet_hours_start": preferences.get("quiet_hours_start"),
            "quiet_hours_end": preferences.get("quiet_hours_end"),
        }
    except Exception as e:
        logger.error(f"Error gathering context: {e}")
        return {"error": str(e)}


async def generate_notifications_node(state: NotifierState) -> Dict[str, Any]:
    """Generate all relevant notifications."""
    notifications = []
    current_time = state.get("current_time", datetime.now())
    
    # Deadline notifications
    notifications.extend(
        generate_deadline_notifications(
            state.get("upcoming_deadlines", []),
            current_time
        )
    )
    
    # Revision notifications
    notifications.extend(
        generate_revision_notifications(
            state.get("revisions_due", [])
        )
    )
    
    # Motivation/streak notification
    motivation = generate_motivation_notification(state.get("current_streak", 0))
    if motivation:
        notifications.append(motivation)
    
    # Gap opportunity
    gap_notif = generate_gap_notification(
        state.get("schedule_gaps", []),
        current_time
    )
    if gap_notif:
        notifications.append(gap_notif)
    
    return {
        "notifications": [n.to_dict() for n in notifications]
    }


async def filter_notifications_node(state: NotifierState) -> Dict[str, Any]:
    """Filter notifications based on user preferences and quiet hours."""
    notifications = state.get("notifications", [])
    preferences = state.get("user_preferences", {})
    current_time = state.get("current_time", datetime.now())
    
    # Check quiet hours
    quiet_start = state.get("quiet_hours_start")
    quiet_end = state.get("quiet_hours_end")
    
    in_quiet_hours = False
    if quiet_start and quiet_end:
        current_time_only = current_time.time()
        if quiet_start > quiet_end:
            # Overnight quiet hours (e.g., 22:00 - 07:00)
            in_quiet_hours = current_time_only >= quiet_start or current_time_only <= quiet_end
        else:
            in_quiet_hours = quiet_start <= current_time_only <= quiet_end
    
    filtered = []
    for notif in notifications:
        # Skip non-urgent during quiet hours
        if in_quiet_hours and notif.get("priority") not in ["urgent", "high"]:
            continue
        
        # Check if notification type is enabled
        notif_type = notif.get("type")
        type_prefs = preferences.get(notif_type, {})
        if isinstance(type_prefs, dict) and not type_prefs.get("enabled", True):
            continue
        
        filtered.append(notif)
    
    return {"filtered_notifications": filtered}


async def prepare_delivery_node(state: NotifierState) -> Dict[str, Any]:
    """Prepare notifications for delivery."""
    filtered = state.get("filtered_notifications", [])
    
    # Sort by priority
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    sorted_notifications = sorted(
        filtered,
        key=lambda n: priority_order.get(n.get("priority", "low"), 3)
    )
    
    # Prepare WebSocket payload
    websocket_payload = {
        "type": "notifications",
        "count": len(sorted_notifications),
        "notifications": sorted_notifications,
        "timestamp": datetime.now().isoformat(),
    }
    
    return {
        "delivery_queue": sorted_notifications,
        "websocket_payload": websocket_payload,
    }


async def save_notifications_node(state: NotifierState) -> Dict[str, Any]:
    """Save notifications to database."""
    from database import db
    
    notifications = state.get("delivery_queue", [])
    
    try:
        for notif in notifications:
            query = """
                INSERT INTO proactive_notifications 
                (type, title, message, priority, action_url, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                RETURNING id
            """
            await db.execute(
                query,
                notif.get("type"),
                notif.get("title"),
                notif.get("message"),
                notif.get("priority"),
                notif.get("action_url"),
            )
    except Exception as e:
        logger.error(f"Error saving notifications: {e}")
    
    return {}


# ============================================
# GRAPH CONSTRUCTION
# ============================================

def create_notifier_agent_graph() -> StateGraph:
    """Create the notifier agent graph."""
    graph = StateGraph(NotifierState)
    
    # Add nodes
    graph.add_node("gather_context", gather_context_node)
    graph.add_node("generate_notifications", generate_notifications_node)
    graph.add_node("filter_notifications", filter_notifications_node)
    graph.add_node("prepare_delivery", prepare_delivery_node)
    graph.add_node("save_notifications", save_notifications_node)
    
    # Add edges
    graph.set_entry_point("gather_context")
    graph.add_edge("gather_context", "generate_notifications")
    graph.add_edge("generate_notifications", "filter_notifications")
    graph.add_edge("filter_notifications", "prepare_delivery")
    graph.add_edge("prepare_delivery", "save_notifications")
    graph.add_edge("save_notifications", END)
    
    return graph


def compile_notifier_agent(checkpointer: Optional[MemorySaver] = None):
    """Compile the notifier agent graph."""
    graph = create_notifier_agent_graph()
    return graph.compile(checkpointer=checkpointer)


# ============================================
# AGENT CLASS
# ============================================

class NotifierAgent:
    """
    High-level interface for the Notifier agent.
    
    Generates proactive notifications for:
    - Upcoming deadlines
    - Due revisions
    - Study break reminders
    - Achievement celebrations
    - Schedule gap opportunities
    """
    
    def __init__(self, checkpointer: Optional[MemorySaver] = None):
        """Initialize the agent."""
        self.graph = compile_notifier_agent(checkpointer)
    
    async def run(
        self,
        trigger_type: str = "scheduled"
    ) -> Dict[str, Any]:
        """
        Run the notification generation cycle.
        
        Args:
            trigger_type: What triggered this run ("scheduled", "event", "manual")
            
        Returns:
            Generated notifications ready for delivery
        """
        initial_state = create_notifier_state(trigger_type)
        
        try:
            result = await self.graph.ainvoke(initial_state)
            
            return {
                "notifications": result.get("delivery_queue", []),
                "websocket_payload": result.get("websocket_payload"),
                "count": len(result.get("delivery_queue", [])),
            }
        except Exception as e:
            logger.error(f"Notification generation failed: {e}")
            return {
                "notifications": [],
                "count": 0,
                "error": str(e),
            }
    
    async def get_websocket_payload(self) -> Dict[str, Any]:
        """Get notifications as WebSocket payload."""
        result = await self.run(trigger_type="websocket")
        return result.get("websocket_payload", {})
    
    async def send_immediate(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> Dict[str, Any]:
        """
        Send an immediate notification.
        
        Args:
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            priority: Priority level
            
        Returns:
            Sent notification details
        """
        import uuid
        from database import db
        
        notification = Notification(
            id=str(uuid.uuid4()),
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
        )
        
        try:
            query = """
                INSERT INTO proactive_notifications 
                (type, title, message, priority, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
            """
            result = await db.fetchrow(
                query,
                notification_type.value,
                title,
                message,
                priority.value,
            )
            
            notification.id = str(result['id'])
            
            return notification.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return {"error": str(e)}


# ============================================
# SINGLETON INSTANCE
# ============================================

_agent: Optional[NotifierAgent] = None


def get_notifier_agent() -> NotifierAgent:
    """Get or create the notifier agent instance."""
    global _agent
    if _agent is None:
        _agent = NotifierAgent()
    return _agent
