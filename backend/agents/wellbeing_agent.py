"""
Personal Engineering OS - Wellbeing Monitor Agent
LangGraph-based agent for tracking and supporting student wellbeing
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import WellbeingState, WellbeingStatus, create_wellbeing_state


# ============================================
# CONSTANTS
# ============================================

# Thresholds for various metrics
MAX_DAILY_STUDY_HOURS = 8
MAX_CONTINUOUS_STUDY_MINS = 120
RECOMMENDED_BREAK_INTERVAL_MINS = 90
MIN_BREAKS_PER_DAY = 3
HEALTHY_DEEP_WORK_RATIO = 0.4


# ============================================
# NODE: Calculate Metrics
# ============================================

async def calculate_metrics(state: WellbeingState) -> WellbeingState:
    """
    Calculate wellbeing metrics from study data.

    Analyzes study time, breaks, and patterns.
    """
    from database import db
    from timer import get_active_timer

    today = date.today()
    week_start = today - timedelta(days=7)

    # Get today's study sessions
    today_sessions = await db.fetch("""
        SELECT
            duration_seconds,
            is_deep_work,
            started_at,
            stopped_at
        FROM study_sessions
        WHERE DATE(started_at) = $1
          AND stopped_at IS NOT NULL
        ORDER BY started_at
    """, today)

    # Get week's study sessions
    week_sessions = await db.fetch("""
        SELECT
            DATE(started_at) as study_date,
            SUM(duration_seconds) as total_seconds,
            COUNT(*) as session_count,
            SUM(CASE WHEN is_deep_work THEN 1 ELSE 0 END) as deep_work_count
        FROM study_sessions
        WHERE started_at >= $1
          AND stopped_at IS NOT NULL
        GROUP BY DATE(started_at)
    """, week_start)

    # Calculate today's metrics
    study_hours_today = sum(
        (s["duration_seconds"] or 0) for s in today_sessions
    ) / 3600

    deep_work_today = len([s for s in today_sessions if s["is_deep_work"]])

    # Calculate breaks (gaps between sessions)
    breaks_today = 0
    last_end = None
    for session in today_sessions:
        if last_end and session["started_at"]:
            gap_mins = (session["started_at"] - last_end).total_seconds() / 60
            if 5 <= gap_mins <= 60:  # Count as break if 5-60 mins
                breaks_today += 1
        last_end = session.get("stopped_at")

    # Calculate week metrics
    study_hours_week = sum(
        (s["total_seconds"] or 0) for s in week_sessions
    ) / 3600

    # Check last break
    last_break_at = None
    if today_sessions:
        # Find last session end time
        for s in reversed(today_sessions):
            if s.get("stopped_at"):
                last_break_at = s["stopped_at"].isoformat()
                break

    # Check active timer
    active_timer = await get_active_timer()
    last_break_mins_ago = 0
    if active_timer:
        started = active_timer.get("started_at")
        if started:
            elapsed_mins = active_timer.get("elapsed_seconds", 0) / 60
            last_break_mins_ago = int(elapsed_mins)
    elif last_break_at:
        last_break_dt = datetime.fromisoformat(last_break_at)
        last_break_mins_ago = int((datetime.now() - last_break_dt).total_seconds() / 60)

    return {
        **state,
        "study_hours_today": round(study_hours_today, 2),
        "study_hours_week": round(study_hours_week, 2),
        "deep_work_sessions_today": deep_work_today,
        "breaks_taken_today": breaks_today,
        "last_break_at": last_break_at
    }


# ============================================
# NODE: Check Stress
# ============================================

async def check_stress(state: WellbeingState) -> WellbeingState:
    """
    Analyze metrics to determine stress and fatigue levels.

    Identifies risk factors and positive indicators.
    """
    from database import db
    from scheduler import get_pending_work_items

    study_hours_today = state.get("study_hours_today", 0)
    study_hours_week = state.get("study_hours_week", 0)
    deep_work_today = state.get("deep_work_sessions_today", 0)
    breaks_today = state.get("breaks_taken_today", 0)

    risk_factors = []
    positive_factors = []
    stress_level = 3  # Base level
    fatigue_level = 3

    # Check study time today
    if study_hours_today > MAX_DAILY_STUDY_HOURS:
        risk_factors.append(
            f"You've studied {study_hours_today:.1f} hours today - "
            f"that's above the recommended {MAX_DAILY_STUDY_HOURS} hours."
        )
        stress_level += 2
        fatigue_level += 2
    elif study_hours_today > MAX_DAILY_STUDY_HOURS * 0.75:
        stress_level += 1
        fatigue_level += 1

    # Check breaks
    if study_hours_today > 2 and breaks_today < MIN_BREAKS_PER_DAY:
        risk_factors.append(
            f"Only {breaks_today} break(s) taken today. "
            "Regular breaks improve focus and retention."
        )
        fatigue_level += 1

    # Check weekly load
    avg_daily_hours = study_hours_week / 7
    if avg_daily_hours > 6:
        risk_factors.append(
            f"Averaging {avg_daily_hours:.1f} hours/day this week. "
            "Consider scheduling rest days."
        )
        stress_level += 1

    # Check pending deadlines
    pending = await get_pending_work_items(3)  # Next 3 days
    urgent_items = [p for p in pending if p.get("days_until", 99) <= 1]
    if len(urgent_items) > 3:
        risk_factors.append(
            f"{len(urgent_items)} items due in the next 24 hours!"
        )
        stress_level += 2

    # Check positive factors
    if 4 <= study_hours_today <= 6:
        positive_factors.append(
            "Good study time today - staying within healthy limits."
        )

    if deep_work_today >= 2:
        positive_factors.append(
            f"{deep_work_today} deep work sessions completed!"
        )

    if breaks_today >= MIN_BREAKS_PER_DAY:
        positive_factors.append(
            "Taking regular breaks - great for sustained focus!"
        )

    # Get streak info
    streak = await db.fetch_one(
        "SELECT current_streak FROM user_streaks WHERE id = 1"
    )
    if streak and streak.get("current_streak", 0) >= 7:
        positive_factors.append(
            f"Amazing {streak['current_streak']}-day streak!"
        )

    # Cap levels
    stress_level = min(10, max(1, stress_level))
    fatigue_level = min(10, max(1, fatigue_level))

    # Calculate productivity and balance scores
    productivity_score = min(1.0, study_hours_today / 6) * 0.7 + (
        0.3 if deep_work_today > 0 else 0
    )

    balance_score = 1.0
    if breaks_today < MIN_BREAKS_PER_DAY and study_hours_today > 2:
        balance_score -= 0.3
    if study_hours_today > MAX_DAILY_STUDY_HOURS:
        balance_score -= 0.3
    if stress_level > 6:
        balance_score -= 0.2
    balance_score = max(0, balance_score)

    return {
        **state,
        "stress_level": stress_level,
        "fatigue_level": fatigue_level,
        "productivity_score": round(productivity_score, 2),
        "balance_score": round(balance_score, 2),
        "risk_factors": risk_factors,
        "positive_factors": positive_factors
    }


# ============================================
# NODE: Suggest Break
# ============================================

async def suggest_break(state: WellbeingState) -> WellbeingState:
    """
    Generate break and wellbeing recommendations.

    Determines if user should take a break and suggests activities.
    """
    from timer import get_active_timer

    stress_level = state.get("stress_level", 5)
    fatigue_level = state.get("fatigue_level", 5)
    study_hours_today = state.get("study_hours_today", 0)
    breaks_today = state.get("breaks_taken_today", 0)
    risk_factors = state.get("risk_factors", [])
    positive_factors = state.get("positive_factors", [])

    suggestions = []
    should_take_break = False
    recommended_break_mins = 0
    immediate_action = None

    # Determine overall status
    if stress_level >= 7 or fatigue_level >= 7:
        status = WellbeingStatus.STRESSED
    elif stress_level >= 5 or fatigue_level >= 5:
        status = WellbeingStatus.MODERATE
    elif len(positive_factors) > len(risk_factors):
        status = WellbeingStatus.GOOD
    elif stress_level <= 3 and fatigue_level <= 3:
        status = WellbeingStatus.EXCELLENT
    else:
        status = WellbeingStatus.MODERATE

    # Check if currently studying
    active_timer = await get_active_timer()
    if active_timer:
        elapsed_mins = active_timer.get("elapsed_seconds", 0) / 60

        if elapsed_mins >= MAX_CONTINUOUS_STUDY_MINS:
            should_take_break = True
            recommended_break_mins = 15
            immediate_action = (
                f"You've been studying for {elapsed_mins:.0f} minutes. "
                "Time for a 15-minute break!"
            )
        elif elapsed_mins >= RECOMMENDED_BREAK_INTERVAL_MINS:
            suggestions.append(
                "Consider taking a short break soon to maintain focus."
            )

    # Generate contextual suggestions
    if status == WellbeingStatus.STRESSED:
        suggestions.extend([
            "Take a 10-minute walk outside to clear your mind.",
            "Practice deep breathing: 4 seconds in, 4 seconds hold, 4 seconds out.",
            "Consider talking to a friend or classmate about your workload."
        ])
        should_take_break = True
        recommended_break_mins = max(recommended_break_mins, 20)

    elif status == WellbeingStatus.EXHAUSTED:
        suggestions.extend([
            "Your body needs rest. Consider calling it a day.",
            "Get some fresh air and physical movement.",
            "Make sure you get enough sleep tonight."
        ])
        should_take_break = True
        recommended_break_mins = 30
        immediate_action = immediate_action or (
            "You're showing signs of exhaustion. Please take a longer break."
        )

    elif status == WellbeingStatus.MODERATE:
        suggestions.extend([
            "A short break every 90 minutes helps maintain productivity.",
            "Stretch your body - neck rolls, shoulder shrugs, back stretches.",
            "Drink water and have a healthy snack."
        ])

    elif status in [WellbeingStatus.GOOD, WellbeingStatus.EXCELLENT]:
        suggestions.extend([
            "You're doing great! Keep up the balanced approach.",
            "Consider tackling a challenging topic while your focus is strong."
        ])

    # Time-based suggestions
    current_hour = datetime.now().hour
    if current_hour >= 22:
        suggestions.append(
            "It's getting late. Consider wrapping up to maintain your sleep schedule."
        )
    elif current_hour >= 20 and study_hours_today > 5:
        suggestions.append(
            "You've had a productive day. Consider some relaxation time."
        )

    # Break suggestions based on break count
    if breaks_today < 2 and study_hours_today > 3:
        suggestions.append(
            "Try the Pomodoro technique: 25 min work, 5 min break, repeat."
        )

    return {
        **state,
        "status": status,
        "immediate_action": immediate_action,
        "suggestions": suggestions,
        "should_take_break": should_take_break,
        "recommended_break_mins": recommended_break_mins
    }


# ============================================
# GRAPH CONSTRUCTION
# ============================================

def create_wellbeing_agent_graph() -> StateGraph:
    """
    Create the Wellbeing Monitor agent graph.

    Flow:
    1. calculate_metrics - Gather study and break data
    2. check_stress - Analyze stress and fatigue levels
    3. suggest_break - Generate recommendations
    """
    workflow = StateGraph(WellbeingState)

    # Add nodes
    workflow.add_node("calculate_metrics", calculate_metrics)
    workflow.add_node("check_stress", check_stress)
    workflow.add_node("suggest_break", suggest_break)

    # Define edges
    workflow.set_entry_point("calculate_metrics")
    workflow.add_edge("calculate_metrics", "check_stress")
    workflow.add_edge("check_stress", "suggest_break")
    workflow.add_edge("suggest_break", END)

    return workflow


def compile_wellbeing_agent(checkpointer: Optional[MemorySaver] = None):
    """Compile the wellbeing agent graph."""
    graph = create_wellbeing_agent_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# ============================================
# AGENT INTERFACE
# ============================================

class WellbeingAgent:
    """
    High-level interface for the Wellbeing Monitor agent.
    """

    def __init__(self, checkpointer: Optional[MemorySaver] = None):
        self.checkpointer = checkpointer or MemorySaver()
        self.agent = compile_wellbeing_agent(self.checkpointer)

    async def check_wellbeing(
        self,
        thread_id: str = "wellbeing"
    ) -> Dict[str, Any]:
        """
        Perform a comprehensive wellbeing check.

        Returns:
            Wellbeing status, metrics, and recommendations
        """
        initial_state = create_wellbeing_state()
        config = {"configurable": {"thread_id": thread_id}}

        final_state = await self.agent.ainvoke(initial_state, config)

        return {
            "status": final_state.get("status", WellbeingStatus.MODERATE),
            "stress_level": final_state.get("stress_level", 5),
            "fatigue_level": final_state.get("fatigue_level", 5),
            "productivity_score": final_state.get("productivity_score", 0.5),
            "balance_score": final_state.get("balance_score", 0.5),
            "study_hours_today": final_state.get("study_hours_today", 0),
            "study_hours_week": final_state.get("study_hours_week", 0),
            "deep_work_sessions_today": final_state.get("deep_work_sessions_today", 0),
            "breaks_taken_today": final_state.get("breaks_taken_today", 0),
            "should_take_break": final_state.get("should_take_break", False),
            "recommended_break_mins": final_state.get("recommended_break_mins", 0),
            "immediate_action": final_state.get("immediate_action"),
            "suggestions": final_state.get("suggestions", []),
            "risk_factors": final_state.get("risk_factors", []),
            "positive_factors": final_state.get("positive_factors", [])
        }

    async def should_suggest_break(
        self,
        thread_id: str = "wellbeing_quick"
    ) -> Dict[str, Any]:
        """
        Quick check if user should take a break.

        Returns minimal data for break suggestion.
        """
        from timer import get_active_timer

        active_timer = await get_active_timer()

        if not active_timer:
            return {
                "should_break": False,
                "message": None
            }

        elapsed_mins = active_timer.get("elapsed_seconds", 0) / 60

        if elapsed_mins >= MAX_CONTINUOUS_STUDY_MINS:
            return {
                "should_break": True,
                "elapsed_mins": int(elapsed_mins),
                "message": f"You've been studying for {int(elapsed_mins)} minutes. Time for a break!",
                "recommended_break_mins": 15
            }
        elif elapsed_mins >= RECOMMENDED_BREAK_INTERVAL_MINS:
            return {
                "should_break": True,
                "elapsed_mins": int(elapsed_mins),
                "message": "Consider a short break to maintain focus.",
                "recommended_break_mins": 10
            }

        return {
            "should_break": False,
            "elapsed_mins": int(elapsed_mins),
            "message": None,
            "minutes_until_break_suggested": int(RECOMMENDED_BREAK_INTERVAL_MINS - elapsed_mins)
        }

    async def get_daily_summary(
        self,
        thread_id: str = "wellbeing_summary"
    ) -> Dict[str, Any]:
        """
        Get a summary of today's wellbeing metrics.

        Returns metrics without full analysis.
        """
        initial_state = create_wellbeing_state()

        # Only run metrics calculation
        state_with_metrics = await calculate_metrics(initial_state)

        return {
            "date": str(date.today()),
            "study_hours": state_with_metrics.get("study_hours_today", 0),
            "deep_work_sessions": state_with_metrics.get("deep_work_sessions_today", 0),
            "breaks_taken": state_with_metrics.get("breaks_taken_today", 0),
            "week_total_hours": state_with_metrics.get("study_hours_week", 0),
            "avg_daily_hours": round(
                state_with_metrics.get("study_hours_week", 0) / 7, 1
            )
        }


# Create default agent instance
default_wellbeing_agent = None


def get_wellbeing_agent() -> WellbeingAgent:
    """Get or create the default wellbeing agent instance."""
    global default_wellbeing_agent
    if default_wellbeing_agent is None:
        default_wellbeing_agent = WellbeingAgent()
    return default_wellbeing_agent
