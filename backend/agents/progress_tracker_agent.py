"""
AI Engineering Study Assistant - Progress Tracker Agent
Specialized agent for tracking academic progress, analytics, and growth insights.
"""

import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, TypedDict
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from .state import Message

logger = logging.getLogger(__name__)


# ============================================
# STATE DEFINITION
# ============================================

class ProgressMetricType(str, Enum):
    """Types of progress metrics to track."""
    STUDY_HOURS = "study_hours"
    TASKS_COMPLETED = "tasks_completed"
    REVISIONS_DONE = "revisions_done"
    STREAK_DAYS = "streak_days"
    MASTERY_LEVEL = "mastery_level"
    DEEP_WORK_HOURS = "deep_work_hours"
    GAP_UTILIZATION = "gap_utilization"


class AnalysisPeriod(str, Enum):
    """Time periods for analysis."""
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    ALL_TIME = "all_time"


@dataclass
class ProgressMetric:
    """A single progress metric with trend."""
    metric_type: ProgressMetricType
    current_value: float
    previous_value: float
    target_value: Optional[float]
    trend_direction: str  # "up", "down", "stable"
    trend_percentage: float
    period: AnalysisPeriod


@dataclass
class SubjectProgress:
    """Progress for a specific subject."""
    subject_code: str
    subject_name: str
    chapters_completed: int
    total_chapters: int
    mastery_level: float  # 0-100
    study_hours: float
    last_studied: Optional[datetime]
    revision_status: str  # "on_track", "behind", "ahead"


class ProgressTrackerState(TypedDict):
    """State for the Progress Tracker agent."""
    # Input
    user_query: str
    analysis_type: str  # "overview", "subject", "comparison", "goals"
    target_subject: Optional[str]
    target_period: AnalysisPeriod
    
    # Gathered data
    metrics: List[Dict[str, Any]]
    subject_progress: List[Dict[str, Any]]
    goals: List[Dict[str, Any]]
    study_sessions: List[Dict[str, Any]]
    
    # Analysis results
    insights: List[str]
    recommendations: List[str]
    achievements: List[str]
    warnings: List[str]
    
    # Output
    response: str
    visualization_data: Dict[str, Any]
    
    # Metadata
    messages: List[Message]
    error: Optional[str]


def create_progress_tracker_state(
    query: str = "",
    period: AnalysisPeriod = AnalysisPeriod.THIS_WEEK
) -> ProgressTrackerState:
    """Create initial state for progress tracker."""
    return ProgressTrackerState(
        user_query=query,
        analysis_type="overview",
        target_subject=None,
        target_period=period,
        metrics=[],
        subject_progress=[],
        goals=[],
        study_sessions=[],
        insights=[],
        recommendations=[],
        achievements=[],
        warnings=[],
        response="",
        visualization_data={},
        messages=[],
        error=None,
    )


# ============================================
# LLM INITIALIZATION
# ============================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("PROGRESS_MODEL_NAME", "gpt-4")


def get_llm():
    """Get LLM instance for progress analysis."""
    if OPENAI_API_KEY:
        return ChatOpenAI(
            model=MODEL_NAME,
            api_key=OPENAI_API_KEY,
            temperature=0.3  # Lower temperature for analytics
        )
    elif ANTHROPIC_API_KEY:
        return ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            api_key=ANTHROPIC_API_KEY,
            temperature=0.3
        )
    else:
        logger.warning("No API key found, using mock LLM")
        return None


# ============================================
# DATA GATHERING FUNCTIONS
# ============================================

async def gather_study_metrics(period: AnalysisPeriod) -> List[Dict[str, Any]]:
    """Gather study metrics from database."""
    from database import db
    
    # Calculate date range
    today = date.today()
    if period == AnalysisPeriod.TODAY:
        start_date = today
    elif period == AnalysisPeriod.THIS_WEEK:
        start_date = today - timedelta(days=today.weekday())
    elif period == AnalysisPeriod.THIS_MONTH:
        start_date = today.replace(day=1)
    else:
        start_date = date(2020, 1, 1)  # All time
    
    metrics = []
    
    try:
        # Study hours
        study_hours_query = """
            SELECT COALESCE(SUM(duration_minutes) / 60.0, 0) as hours
            FROM study_sessions
            WHERE started_at >= $1
        """
        result = await db.fetchrow(study_hours_query, start_date)
        current_hours = float(result['hours']) if result else 0
        
        # Previous period for comparison
        period_days = (today - start_date).days or 1
        prev_start = start_date - timedelta(days=period_days)
        prev_result = await db.fetchrow(study_hours_query, prev_start)
        prev_hours = float(prev_result['hours']) if prev_result else 0
        
        trend = calculate_trend(current_hours, prev_hours)
        
        metrics.append({
            "type": ProgressMetricType.STUDY_HOURS.value,
            "current": round(current_hours, 1),
            "previous": round(prev_hours, 1),
            "trend_direction": trend[0],
            "trend_percentage": trend[1],
        })
        
        # Tasks completed
        tasks_query = """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status = 'completed' AND updated_at >= $1
        """
        result = await db.fetchrow(tasks_query, start_date)
        current_tasks = result['count'] if result else 0
        
        prev_result = await db.fetchrow(tasks_query, prev_start)
        prev_tasks = prev_result['count'] if prev_result else 0
        
        trend = calculate_trend(current_tasks, prev_tasks)
        
        metrics.append({
            "type": ProgressMetricType.TASKS_COMPLETED.value,
            "current": current_tasks,
            "previous": prev_tasks,
            "trend_direction": trend[0],
            "trend_percentage": trend[1],
        })
        
        # Deep work hours
        deep_work_query = """
            SELECT COALESCE(SUM(duration_minutes) / 60.0, 0) as hours
            FROM study_sessions
            WHERE started_at >= $1 AND is_deep_work = true
        """
        result = await db.fetchrow(deep_work_query, start_date)
        deep_hours = float(result['hours']) if result else 0
        
        metrics.append({
            "type": ProgressMetricType.DEEP_WORK_HOURS.value,
            "current": round(deep_hours, 1),
            "previous": 0,
            "trend_direction": "stable",
            "trend_percentage": 0,
        })
        
    except Exception as e:
        logger.error(f"Error gathering metrics: {e}")
    
    return metrics


async def gather_subject_progress() -> List[Dict[str, Any]]:
    """Gather progress for each subject."""
    from database import db
    
    progress_list = []
    
    try:
        query = """
            SELECT 
                s.code, s.name,
                COUNT(CASE WHEN cp.reading_status = 'completed' THEN 1 END) as completed,
                COUNT(c.id) as total,
                COALESCE(AVG(cp.mastery_level), 0) as avg_mastery,
                MAX(ss.started_at) as last_studied
            FROM subjects s
            LEFT JOIN chapters c ON c.subject_id = s.id
            LEFT JOIN chapter_progress cp ON cp.chapter_id = c.id
            LEFT JOIN study_sessions ss ON ss.subject_code = s.code
            GROUP BY s.id, s.code, s.name
        """
        
        rows = await db.fetch(query)
        
        for row in rows:
            completion_rate = (row['completed'] / row['total'] * 100) if row['total'] > 0 else 0
            
            progress_list.append({
                "subject_code": row['code'],
                "subject_name": row['name'],
                "chapters_completed": row['completed'],
                "total_chapters": row['total'],
                "completion_percentage": round(completion_rate, 1),
                "mastery_level": round(row['avg_mastery'], 1),
                "last_studied": row['last_studied'].isoformat() if row['last_studied'] else None,
            })
            
    except Exception as e:
        logger.error(f"Error gathering subject progress: {e}")
    
    return progress_list


async def gather_goals() -> List[Dict[str, Any]]:
    """Gather active goals and their status."""
    from database import db
    
    goals = []
    
    try:
        query = """
            SELECT 
                g.id, g.title, g.description, g.target_value, g.current_value,
                g.deadline, g.status, gc.name as category
            FROM study_goals g
            LEFT JOIN goal_categories gc ON gc.id = g.category_id
            WHERE g.status IN ('active', 'in_progress')
            ORDER BY g.deadline NULLS LAST
        """
        
        rows = await db.fetch(query)
        
        for row in rows:
            progress = (row['current_value'] / row['target_value'] * 100) if row['target_value'] else 0
            
            # Determine if on track
            days_remaining = (row['deadline'] - date.today()).days if row['deadline'] else None
            
            goals.append({
                "id": row['id'],
                "title": row['title'],
                "category": row['category'],
                "progress_percentage": round(progress, 1),
                "days_remaining": days_remaining,
                "status": "on_track" if progress >= 50 or days_remaining is None else "behind",
            })
            
    except Exception as e:
        logger.error(f"Error gathering goals: {e}")
    
    return goals


def calculate_trend(current: float, previous: float) -> tuple[str, float]:
    """Calculate trend direction and percentage."""
    if previous == 0:
        return ("up", 100.0) if current > 0 else ("stable", 0.0)
    
    change = ((current - previous) / previous) * 100
    
    if change > 5:
        return ("up", round(change, 1))
    elif change < -5:
        return ("down", round(abs(change), 1))
    else:
        return ("stable", round(abs(change), 1))


# ============================================
# GRAPH NODES
# ============================================

async def gather_data_node(state: ProgressTrackerState) -> Dict[str, Any]:
    """Gather all relevant progress data."""
    try:
        metrics = await gather_study_metrics(state["target_period"])
        subject_progress = await gather_subject_progress()
        goals = await gather_goals()
        
        return {
            "metrics": metrics,
            "subject_progress": subject_progress,
            "goals": goals,
        }
    except Exception as e:
        logger.error(f"Error in gather_data_node: {e}")
        return {"error": str(e)}


async def analyze_progress_node(state: ProgressTrackerState) -> Dict[str, Any]:
    """Analyze progress data and generate insights."""
    insights = []
    recommendations = []
    achievements = []
    warnings = []
    
    metrics = state.get("metrics", [])
    subjects = state.get("subject_progress", [])
    goals = state.get("goals", [])
    
    # Analyze metrics
    for metric in metrics:
        if metric["trend_direction"] == "up" and metric["trend_percentage"] > 20:
            achievements.append(
                f"Great progress! {metric['type'].replace('_', ' ').title()} increased by {metric['trend_percentage']}%"
            )
        elif metric["trend_direction"] == "down" and metric["trend_percentage"] > 20:
            warnings.append(
                f"{metric['type'].replace('_', ' ').title()} decreased by {metric['trend_percentage']}%"
            )
    
    # Analyze subjects
    for subject in subjects:
        if subject["mastery_level"] >= 80:
            achievements.append(f"Excellent mastery in {subject['subject_name']}!")
        elif subject["completion_percentage"] < 30:
            recommendations.append(
                f"Focus more on {subject['subject_name']} - only {subject['completion_percentage']}% complete"
            )
    
    # Analyze goals
    for goal in goals:
        if goal["status"] == "behind" and goal.get("days_remaining", 999) < 7:
            warnings.append(
                f"Goal '{goal['title']}' is behind schedule with only {goal['days_remaining']} days left"
            )
        elif goal["progress_percentage"] >= 100:
            achievements.append(f"Goal '{goal['title']}' completed!")
    
    # Generate general insights
    total_study_hours = next(
        (m["current"] for m in metrics if m["type"] == "study_hours"),
        0
    )
    
    if total_study_hours > 20:
        insights.append("You've put in significant study time this period!")
    elif total_study_hours < 10:
        insights.append("Consider increasing your study hours for better results.")
    
    deep_work_hours = next(
        (m["current"] for m in metrics if m["type"] == "deep_work_hours"),
        0
    )
    
    if deep_work_hours > 0:
        deep_work_ratio = (deep_work_hours / total_study_hours * 100) if total_study_hours > 0 else 0
        insights.append(f"Deep work ratio: {round(deep_work_ratio, 1)}% of study time")
    
    return {
        "insights": insights,
        "recommendations": recommendations,
        "achievements": achievements,
        "warnings": warnings,
    }


async def generate_response_node(state: ProgressTrackerState) -> Dict[str, Any]:
    """Generate natural language response."""
    llm = get_llm()
    
    if not llm:
        # Fallback without LLM
        response = _generate_fallback_response(state)
        return {"response": response}
    
    # Build prompt
    prompt = f"""You are a study progress analyst for an engineering student.

Based on the following data, provide a helpful summary:

**Metrics:**
{json.dumps(state.get('metrics', []), indent=2)}

**Subject Progress:**
{json.dumps(state.get('subject_progress', []), indent=2)}

**Goals:**
{json.dumps(state.get('goals', []), indent=2)}

**Key Insights:**
{json.dumps(state.get('insights', []))}

**Achievements:**
{json.dumps(state.get('achievements', []))}

**Warnings:**
{json.dumps(state.get('warnings', []))}

**Recommendations:**
{json.dumps(state.get('recommendations', []))}

User query: {state.get('user_query', 'Show my progress')}

Provide a concise, encouraging summary with actionable next steps. Use emoji sparingly for key points."""

    try:
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        return {"response": response.content}
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return {"response": _generate_fallback_response(state)}


def _generate_fallback_response(state: ProgressTrackerState) -> str:
    """Generate response without LLM."""
    parts = ["📊 **Progress Summary**\n"]
    
    # Metrics
    metrics = state.get("metrics", [])
    if metrics:
        parts.append("\n**Key Metrics:**")
        for m in metrics:
            arrow = "📈" if m["trend_direction"] == "up" else ("📉" if m["trend_direction"] == "down" else "➡️")
            parts.append(f"- {m['type'].replace('_', ' ').title()}: {m['current']} {arrow}")
    
    # Achievements
    achievements = state.get("achievements", [])
    if achievements:
        parts.append("\n**🌟 Achievements:**")
        for a in achievements:
            parts.append(f"- {a}")
    
    # Warnings
    warnings = state.get("warnings", [])
    if warnings:
        parts.append("\n**⚠️ Attention Needed:**")
        for w in warnings:
            parts.append(f"- {w}")
    
    # Recommendations
    recommendations = state.get("recommendations", [])
    if recommendations:
        parts.append("\n**💡 Recommendations:**")
        for r in recommendations:
            parts.append(f"- {r}")
    
    return "\n".join(parts)


async def prepare_visualization_node(state: ProgressTrackerState) -> Dict[str, Any]:
    """Prepare data for visualization."""
    metrics = state.get("metrics", [])
    subjects = state.get("subject_progress", [])
    
    viz_data = {
        "metrics_chart": {
            "labels": [m["type"].replace("_", " ").title() for m in metrics],
            "current": [m["current"] for m in metrics],
            "previous": [m["previous"] for m in metrics],
        },
        "subject_progress_chart": {
            "labels": [s["subject_code"] for s in subjects],
            "completion": [s["completion_percentage"] for s in subjects],
            "mastery": [s["mastery_level"] for s in subjects],
        },
        "trend_indicators": [
            {
                "metric": m["type"],
                "direction": m["trend_direction"],
                "percentage": m["trend_percentage"],
            }
            for m in metrics
        ],
    }
    
    return {"visualization_data": viz_data}


# ============================================
# GRAPH CONSTRUCTION
# ============================================

def create_progress_tracker_graph() -> StateGraph:
    """Create the progress tracker agent graph."""
    graph = StateGraph(ProgressTrackerState)
    
    # Add nodes
    graph.add_node("gather_data", gather_data_node)
    graph.add_node("analyze_progress", analyze_progress_node)
    graph.add_node("generate_response", generate_response_node)
    graph.add_node("prepare_visualization", prepare_visualization_node)
    
    # Add edges
    graph.set_entry_point("gather_data")
    graph.add_edge("gather_data", "analyze_progress")
    graph.add_edge("analyze_progress", "generate_response")
    graph.add_edge("generate_response", "prepare_visualization")
    graph.add_edge("prepare_visualization", END)
    
    return graph


def compile_progress_tracker(checkpointer: Optional[MemorySaver] = None):
    """Compile the progress tracker graph."""
    graph = create_progress_tracker_graph()
    return graph.compile(checkpointer=checkpointer)


# ============================================
# AGENT CLASS
# ============================================

class ProgressTrackerAgent:
    """
    High-level interface for the Progress Tracker agent.
    
    Tracks and analyzes:
    - Study hours and productivity
    - Subject-wise progress
    - Goal completion
    - Learning trends
    """
    
    def __init__(self, checkpointer: Optional[MemorySaver] = None):
        """Initialize the agent."""
        self.graph = compile_progress_tracker(checkpointer)
    
    async def analyze(
        self,
        query: str = "",
        period: AnalysisPeriod = AnalysisPeriod.THIS_WEEK,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run progress analysis.
        
        Args:
            query: User's question about progress
            period: Time period to analyze
            subject: Optional subject to focus on
            
        Returns:
            Analysis results with response and visualization data
        """
        initial_state = create_progress_tracker_state(query, period)
        initial_state["target_subject"] = subject
        
        if subject:
            initial_state["analysis_type"] = "subject"
        
        try:
            result = await self.graph.ainvoke(initial_state)
            
            return {
                "response": result.get("response", ""),
                "metrics": result.get("metrics", []),
                "subject_progress": result.get("subject_progress", []),
                "insights": result.get("insights", []),
                "achievements": result.get("achievements", []),
                "warnings": result.get("warnings", []),
                "recommendations": result.get("recommendations", []),
                "visualization_data": result.get("visualization_data", {}),
            }
        except Exception as e:
            logger.error(f"Progress analysis failed: {e}")
            return {
                "response": f"Error analyzing progress: {str(e)}",
                "error": str(e),
            }
    
    async def get_quick_stats(self) -> Dict[str, Any]:
        """Get quick stats for dashboard display."""
        try:
            metrics = await gather_study_metrics(AnalysisPeriod.THIS_WEEK)
            return {
                "study_hours": next((m["current"] for m in metrics if m["type"] == "study_hours"), 0),
                "tasks_completed": next((m["current"] for m in metrics if m["type"] == "tasks_completed"), 0),
                "deep_work_hours": next((m["current"] for m in metrics if m["type"] == "deep_work_hours"), 0),
            }
        except Exception as e:
            logger.error(f"Error getting quick stats: {e}")
            return {}


# ============================================
# SINGLETON INSTANCE
# ============================================

_agent: Optional[ProgressTrackerAgent] = None


def get_progress_tracker_agent() -> ProgressTrackerAgent:
    """Get or create the progress tracker agent instance."""
    global _agent
    if _agent is None:
        _agent = ProgressTrackerAgent()
    return _agent
