"""
Personal Engineering OS - Study Planner Agent
LangGraph-based agent for study pattern analysis and planning
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import PlannerState, create_planner_state


# ============================================
# NODE: Get Patterns
# ============================================

async def get_patterns(state: PlannerState) -> PlannerState:
    """
    Analyze user's study patterns from historical data.

    Looks at study sessions, completion rates, and timing preferences.
    """
    from database import db

    horizon_days = state.get("planning_horizon_days", 7)
    lookback_days = 30  # Look at last 30 days for patterns

    cutoff_date = date.today() - timedelta(days=lookback_days)

    # Get study session patterns
    sessions = await db.fetch("""
        SELECT
            EXTRACT(DOW FROM started_at) as day_of_week,
            EXTRACT(HOUR FROM started_at) as hour,
            duration_seconds,
            is_deep_work,
            s.code as subject_code
        FROM study_sessions ss
        LEFT JOIN subjects s ON ss.subject_id = s.id
        WHERE started_at >= $1
          AND stopped_at IS NOT NULL
        ORDER BY started_at
    """, cutoff_date)

    # Analyze patterns
    patterns = {
        "total_sessions": len(sessions),
        "total_study_hours": sum(s["duration_seconds"] or 0 for s in sessions) / 3600,
        "deep_work_sessions": len([s for s in sessions if s["is_deep_work"]]),
        "avg_session_mins": 0,
        "preferred_hours": [],
        "preferred_days": [],
        "subject_distribution": {}
    }

    if sessions:
        patterns["avg_session_mins"] = (
            sum(s["duration_seconds"] or 0 for s in sessions) / len(sessions) / 60
        )

        # Find preferred hours
        hour_counts = {}
        for s in sessions:
            hour = int(s["hour"]) if s["hour"] else 0
            hour_counts[hour] = hour_counts.get(hour, 0) + 1

        if hour_counts:
            sorted_hours = sorted(hour_counts.items(), key=lambda x: -x[1])
            patterns["preferred_hours"] = [h[0] for h in sorted_hours[:3]]

        # Find preferred days
        day_counts = {}
        for s in sessions:
            day = int(s["day_of_week"]) if s["day_of_week"] is not None else 0
            day_counts[day] = day_counts.get(day, 0) + 1

        if day_counts:
            sorted_days = sorted(day_counts.items(), key=lambda x: -x[1])
            day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            patterns["preferred_days"] = [day_names[d[0]] for d in sorted_days[:3]]

        # Subject distribution
        for s in sessions:
            subject = s["subject_code"] or "General"
            duration_hours = (s["duration_seconds"] or 0) / 3600
            patterns["subject_distribution"][subject] = (
                patterns["subject_distribution"].get(subject, 0) + duration_hours
            )

    # Get subject progress
    subject_progress = await db.fetch("""
        SELECT
            s.code,
            s.name,
            COUNT(DISTINCT c.id) as total_chapters,
            COUNT(DISTINCT CASE WHEN cp.reading_status = 'completed' THEN c.id END) as completed_chapters,
            COALESCE(AVG(cp.mastery_level), 0) as avg_mastery
        FROM subjects s
        LEFT JOIN chapters c ON s.id = c.subject_id
        LEFT JOIN chapter_progress cp ON c.id = cp.chapter_id
        GROUP BY s.id, s.code, s.name
    """)

    return {
        **state,
        "study_patterns": patterns,
        "subject_progress": {sp["code"]: dict(sp) for sp in subject_progress}
    }


# ============================================
# NODE: Generate Recommendations
# ============================================

async def generate_recommendations(state: PlannerState) -> PlannerState:
    """
    Generate study recommendations based on patterns and goals.

    Identifies subjects needing attention and optimal study times.
    """
    from database import db

    patterns = state.get("study_patterns", {})
    subject_progress = state.get("subject_progress", {})
    horizon_days = state.get("planning_horizon_days", 7)

    insights = []
    warnings = []
    achievements = []

    # Check study volume
    weekly_hours = patterns.get("total_study_hours", 0) / 4  # Avg over 4 weeks
    if weekly_hours < 15:
        warnings.append(
            f"Your average weekly study time is {weekly_hours:.1f} hours. "
            "Consider increasing to 20+ hours for optimal progress."
        )
    elif weekly_hours >= 25:
        achievements.append(
            f"Great job! You're averaging {weekly_hours:.1f} hours of study per week."
        )

    # Check deep work ratio
    total_sessions = patterns.get("total_sessions", 0)
    deep_sessions = patterns.get("deep_work_sessions", 0)
    if total_sessions > 0:
        deep_ratio = deep_sessions / total_sessions
        if deep_ratio < 0.3:
            warnings.append(
                "Less than 30% of your sessions are deep work. "
                "Try scheduling longer, uninterrupted blocks."
            )
        elif deep_ratio >= 0.5:
            achievements.append(
                f"{deep_ratio*100:.0f}% of your sessions are deep work sessions!"
            )

    # Check subject balance
    subject_dist = patterns.get("subject_distribution", {})
    if subject_dist:
        max_hours = max(subject_dist.values())
        min_hours = min(subject_dist.values())
        if max_hours > min_hours * 3 and len(subject_dist) > 1:
            neglected = [
                s for s, h in subject_dist.items()
                if h < max_hours / 3
            ]
            if neglected:
                warnings.append(
                    f"Subjects needing more attention: {', '.join(neglected)}"
                )

    # Check mastery levels
    for code, progress in subject_progress.items():
        mastery = progress.get("avg_mastery", 0)
        if mastery < 40 and progress.get("completed_chapters", 0) > 0:
            warnings.append(
                f"{code}: Low mastery level ({mastery:.0f}%). Schedule more revision."
            )
        elif mastery >= 80:
            achievements.append(
                f"{code}: Excellent mastery level ({mastery:.0f}%)!"
            )

    # Preferred study times insight
    preferred_hours = patterns.get("preferred_hours", [])
    if preferred_hours:
        hour_strs = [f"{h}:00" for h in preferred_hours]
        insights.append(
            f"Your most productive study hours are: {', '.join(hour_strs)}"
        )

    # Get revision schedule
    revisions = await db.fetch("""
        SELECT
            rs.*, c.title as chapter_title, s.code as subject_code
        FROM revision_schedule rs
        JOIN chapters c ON rs.chapter_id = c.id
        JOIN subjects s ON c.subject_id = s.id
        WHERE rs.completed = false
          AND rs.due_date <= CURRENT_DATE + $1
        ORDER BY rs.due_date
    """, horizon_days)

    # Get goals
    goals = await db.fetch("""
        SELECT * FROM study_goals
        WHERE completed = false
        ORDER BY deadline NULLS LAST, priority DESC
    """)

    return {
        **state,
        "revision_schedule": list(revisions),
        "goals": list(goals),
        "insights": insights,
        "warnings": warnings,
        "achievements": achievements
    }


# ============================================
# NODE: Create Plan
# ============================================

async def create_plan(state: PlannerState) -> PlannerState:
    """
    Create a concrete study plan based on analysis.

    Generates daily targets and priority ordering.
    """
    patterns = state.get("study_patterns", {})
    subject_progress = state.get("subject_progress", {})
    revisions = state.get("revision_schedule", [])
    goals = state.get("goals", [])
    horizon_days = state.get("planning_horizon_days", 7)

    # Calculate daily targets based on weekly goals
    target_weekly_hours = 20  # Default target
    avg_session_mins = patterns.get("avg_session_mins", 60) or 60

    daily_targets = {
        "study_hours": round(target_weekly_hours / 7, 1),
        "deep_work_sessions": 2,
        "revisions": max(1, len(revisions) // horizon_days),
        "break_mins": 60
    }

    # Determine priority order for subjects
    priority_scores = {}

    for code, progress in subject_progress.items():
        score = 0

        # Lower mastery = higher priority
        mastery = progress.get("avg_mastery", 50)
        score += (100 - mastery) * 0.5

        # More incomplete chapters = higher priority
        total = progress.get("total_chapters", 0)
        completed = progress.get("completed_chapters", 0)
        if total > 0:
            completion_rate = completed / total
            score += (1 - completion_rate) * 30

        # Less recent study = higher priority
        hours_studied = patterns.get("subject_distribution", {}).get(code, 0)
        if hours_studied < 5:
            score += 20

        priority_scores[code] = score

    priority_order = sorted(
        priority_scores.keys(),
        key=lambda x: -priority_scores[x]
    )

    # Create recommended daily plan structure
    recommended_plan = []

    today = date.today()
    for i in range(horizon_days):
        plan_date = today + timedelta(days=i)
        day_name = plan_date.strftime("%A")

        # Get revisions due that day
        day_revisions = [
            r for r in revisions
            if str(r.get("due_date")) == str(plan_date)
        ]

        day_plan = {
            "date": str(plan_date),
            "day": day_name,
            "targets": {
                "study_hours": daily_targets["study_hours"],
                "deep_work_sessions": daily_targets["deep_work_sessions"]
            },
            "revisions": [
                {
                    "subject": r.get("subject_code"),
                    "chapter": r.get("chapter_title"),
                    "revision_number": r.get("revision_number")
                }
                for r in day_revisions
            ],
            "focus_subjects": priority_order[:2],  # Top 2 priority subjects
            "suggestions": []
        }

        # Add suggestions based on day
        preferred_hours = patterns.get("preferred_hours", [9, 14, 16])
        if preferred_hours:
            day_plan["suggestions"].append(
                f"Schedule deep work between {preferred_hours[0]}:00-{preferred_hours[0]+2}:00"
            )

        if day_revisions:
            day_plan["suggestions"].append(
                f"Complete {len(day_revisions)} revision(s) today"
            )

        recommended_plan.append(day_plan)

    return {
        **state,
        "recommended_plan": recommended_plan,
        "daily_targets": daily_targets,
        "priority_order": priority_order
    }


# ============================================
# GRAPH CONSTRUCTION
# ============================================

def create_planner_agent_graph() -> StateGraph:
    """
    Create the Study Planner agent graph.

    Flow:
    1. get_patterns - Analyze historical study data
    2. generate_recommendations - Create insights and warnings
    3. create_plan - Build concrete study plan
    """
    workflow = StateGraph(PlannerState)

    # Add nodes
    workflow.add_node("get_patterns", get_patterns)
    workflow.add_node("generate_recommendations", generate_recommendations)
    workflow.add_node("create_plan", create_plan)

    # Define edges
    workflow.set_entry_point("get_patterns")
    workflow.add_edge("get_patterns", "generate_recommendations")
    workflow.add_edge("generate_recommendations", "create_plan")
    workflow.add_edge("create_plan", END)

    return workflow


def compile_planner_agent(checkpointer: Optional[MemorySaver] = None):
    """Compile the planner agent graph."""
    graph = create_planner_agent_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# ============================================
# AGENT INTERFACE
# ============================================

class PlannerAgent:
    """
    High-level interface for the Study Planner agent.
    """

    def __init__(self, checkpointer: Optional[MemorySaver] = None):
        self.checkpointer = checkpointer or MemorySaver()
        self.agent = compile_planner_agent(self.checkpointer)

    async def create_study_plan(
        self,
        horizon_days: int = 7,
        focus_subject: Optional[str] = None,
        deadline_date: Optional[str] = None,
        thread_id: str = "planner"
    ) -> Dict[str, Any]:
        """
        Create a comprehensive study plan.

        Args:
            horizon_days: Number of days to plan for
            focus_subject: Optional subject to prioritize
            deadline_date: Optional deadline to plan around
            thread_id: Thread ID for state persistence

        Returns:
            Study plan with daily targets and recommendations
        """
        initial_state = create_planner_state(horizon_days)
        initial_state["focus_subject"] = focus_subject
        initial_state["deadline_date"] = deadline_date

        config = {"configurable": {"thread_id": thread_id}}

        final_state = await self.agent.ainvoke(initial_state, config)

        return {
            "horizon_days": horizon_days,
            "study_patterns": final_state.get("study_patterns", {}),
            "subject_progress": final_state.get("subject_progress", {}),
            "recommended_plan": final_state.get("recommended_plan", []),
            "daily_targets": final_state.get("daily_targets", {}),
            "priority_order": final_state.get("priority_order", []),
            "insights": final_state.get("insights", []),
            "warnings": final_state.get("warnings", []),
            "achievements": final_state.get("achievements", []),
            "revisions_upcoming": len(final_state.get("revision_schedule", [])),
            "goals_active": len(final_state.get("goals", []))
        }

    async def get_quick_insights(
        self,
        thread_id: str = "planner_quick"
    ) -> Dict[str, Any]:
        """
        Get quick insights without full planning.

        Returns pattern analysis and immediate recommendations.
        """
        initial_state = create_planner_state(7)
        config = {"configurable": {"thread_id": thread_id}}

        # Only run first two nodes
        graph = self.agent.get_graph()

        # Run pattern analysis
        state_after_patterns = await get_patterns(initial_state)
        state_after_recommendations = await generate_recommendations(state_after_patterns)

        return {
            "patterns": state_after_recommendations.get("study_patterns", {}),
            "insights": state_after_recommendations.get("insights", []),
            "warnings": state_after_recommendations.get("warnings", []),
            "achievements": state_after_recommendations.get("achievements", [])
        }


# Create default agent instance
default_planner_agent = None


def get_planner_agent() -> PlannerAgent:
    """Get or create the default planner agent instance."""
    global default_planner_agent
    if default_planner_agent is None:
        default_planner_agent = PlannerAgent()
    return default_planner_agent
