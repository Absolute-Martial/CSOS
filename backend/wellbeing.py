"""
Personal Engineering OS - Student Wellbeing Monitor
Tracks stress levels, enforces breaks, and promotes healthy study habits.
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel
from enum import Enum
import json

from database import db


# ============================================
# ENUMS AND CONSTANTS
# ============================================

class StressLevel(str, Enum):
    """Stress level classifications based on wellbeing score."""
    LOW = "low"           # Score 0.7-1.0
    MODERATE = "moderate"  # Score 0.4-0.7
    HIGH = "high"         # Score 0.0-0.4


class BreakType(str, Enum):
    """Types of breaks with different purposes."""
    SHORT = "short"            # 5-10 mins - quick mental reset
    POMODORO = "pomodoro"      # 5 mins after 25 work - technique-based
    MEAL = "meal"              # 30-60 mins - nutrition break
    EXERCISE = "exercise"      # 15-30 mins - physical activity
    MEDITATION = "meditation"  # 5-15 mins - mindfulness
    LONG = "long"              # 15-20 mins - extended rest


# Configurable thresholds for stress detection
THRESHOLDS = {
    # Daily study limits
    "daily_study_hours_warning": 8,
    "daily_study_hours_danger": 10,

    # Session duration limits (minutes)
    "session_without_break_warning": 60,
    "session_without_break_danger": 120,

    # Deep work session limits
    "consecutive_deep_work_warning": 2,   # sessions
    "consecutive_deep_work_danger": 4,

    # Task overload
    "overdue_tasks_warning": 3,
    "overdue_tasks_danger": 5,

    # Break compliance
    "skipped_breaks_warning": 2,

    # Minimum study before suggesting break
    "min_study_before_break": 25,  # Pomodoro standard

    # Rest requirements
    "min_breaks_per_day": 4,
    "min_break_total_mins_per_day": 30,
}

# Break duration recommendations by type
BREAK_DURATIONS = {
    BreakType.SHORT: (5, 10),
    BreakType.POMODORO: (5, 5),
    BreakType.MEAL: (30, 60),
    BreakType.EXERCISE: (15, 30),
    BreakType.MEDITATION: (5, 15),
    BreakType.LONG: (15, 20),
}


# ============================================
# PYDANTIC MODELS
# ============================================

class WellbeingMetrics(BaseModel):
    """Complete wellbeing status snapshot."""
    score: float  # 0.0 to 1.0 (higher is better)
    stress_level: StressLevel
    study_hours_today: float
    break_count: int
    break_total_mins: int
    deep_work_sessions: int
    overdue_tasks: int
    consecutive_study_mins: int
    indicators: Dict[str, Any]
    recommendations: List[Dict[str, Any]]


class BreakSession(BaseModel):
    """Break session record."""
    id: Optional[int] = None
    break_type: BreakType
    started_at: datetime
    ended_at: Optional[datetime] = None
    suggested_duration_mins: int
    actual_duration_mins: Optional[int] = None
    was_completed: bool = False


class PomodoroStatus(BaseModel):
    """Current Pomodoro timer status."""
    is_active: bool
    current_phase: str  # "work", "short_break", "long_break", "idle"
    cycles_completed: int
    current_cycle_start: Optional[datetime] = None
    time_remaining_seconds: Optional[int] = None
    next_phase: str


# ============================================
# WELLBEING MONITOR CLASS
# ============================================

class WellbeingMonitor:
    """
    Monitors student wellbeing and calculates stress scores.

    The wellbeing score (0-1) is calculated based on:
    - Study duration (too much reduces score)
    - Break compliance (skipped breaks reduce score)
    - Task overload (overdue tasks reduce score)
    - Session length (long sessions without breaks reduce score)
    - Positive habits (taking breaks, moderate deep work increase score)
    """

    async def calculate_wellbeing_score(self) -> WellbeingMetrics:
        """
        Calculate current wellbeing score and generate recommendations.

        Returns:
            WellbeingMetrics with score, stress level, indicators, and recommendations
        """
        today = date.today()

        # Gather all metrics in parallel using individual queries
        study_mins = await self._get_study_minutes_today(today)
        consecutive_mins = await self._get_consecutive_study_minutes()
        break_count, break_total = await self._get_break_stats_today(today)
        deep_work_count = await self._get_deep_work_sessions_today(today)
        overdue_count = await self._get_overdue_tasks_count()
        skipped_breaks = await self._get_skipped_breaks_today(today)

        # Calculate score
        score, indicators = self._calculate_score(
            study_hours=study_mins / 60,
            consecutive_mins=consecutive_mins,
            break_count=break_count,
            deep_work_sessions=deep_work_count,
            overdue_tasks=overdue_count,
            skipped_breaks=skipped_breaks
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(score, indicators)

        # Determine stress level
        if score >= 0.7:
            stress_level = StressLevel.LOW
        elif score >= 0.4:
            stress_level = StressLevel.MODERATE
        else:
            stress_level = StressLevel.HIGH

        return WellbeingMetrics(
            score=round(score, 2),
            stress_level=stress_level,
            study_hours_today=round(study_mins / 60, 1),
            break_count=break_count,
            break_total_mins=break_total,
            deep_work_sessions=deep_work_count,
            overdue_tasks=overdue_count,
            consecutive_study_mins=int(consecutive_mins),
            indicators=indicators,
            recommendations=recommendations
        )

    async def _get_study_minutes_today(self, today: date) -> float:
        """Get total study minutes for today."""
        result = await db.fetch_one('''
            SELECT COALESCE(SUM(duration_seconds)/60.0, 0) as mins
            FROM study_sessions
            WHERE DATE(started_at) = $1 AND stopped_at IS NOT NULL
        ''', today)
        return result['mins'] if result else 0

    async def _get_consecutive_study_minutes(self) -> float:
        """Get current consecutive study minutes (active session)."""
        active = await db.fetch_one('''
            SELECT started_at FROM active_timer LIMIT 1
        ''')
        if active:
            elapsed = datetime.now() - active['started_at']
            return elapsed.total_seconds() / 60
        return 0

    async def _get_break_stats_today(self, today: date) -> Tuple[int, int]:
        """Get break count and total minutes for today."""
        result = await db.fetch_one('''
            SELECT
                COUNT(*) as count,
                COALESCE(SUM(actual_duration_mins), 0) as total
            FROM break_sessions
            WHERE DATE(started_at) = $1 AND was_completed = true
        ''', today)
        if result:
            return result['count'], result['total']
        return 0, 0

    async def _get_deep_work_sessions_today(self, today: date) -> int:
        """Get count of deep work sessions (90+ min) today."""
        result = await db.fetch_one('''
            SELECT COUNT(*) as count
            FROM study_sessions
            WHERE DATE(started_at) = $1
              AND stopped_at IS NOT NULL
              AND duration_seconds >= 5400
        ''', today)
        return result['count'] if result else 0

    async def _get_overdue_tasks_count(self) -> int:
        """Get count of overdue tasks."""
        result = await db.fetch_one('''
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status != 'completed'
              AND status != 'cancelled'
              AND scheduled_end < NOW()
        ''')
        return result['count'] if result else 0

    async def _get_skipped_breaks_today(self, today: date) -> int:
        """Get count of suggested but not completed breaks today."""
        result = await db.fetch_one('''
            SELECT COUNT(*) as count
            FROM break_sessions
            WHERE DATE(started_at) = $1 AND was_completed = false
        ''', today)
        return result['count'] if result else 0

    def _calculate_score(self, **metrics) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate wellbeing score based on metrics.

        Args:
            study_hours: Total study hours today
            consecutive_mins: Current continuous study minutes
            break_count: Number of completed breaks today
            deep_work_sessions: Number of deep work sessions today
            overdue_tasks: Number of overdue tasks
            skipped_breaks: Number of skipped break suggestions

        Returns:
            Tuple of (score, indicators dict)
        """
        base_score = 0.85
        deductions = 0.0
        indicators: Dict[str, Any] = {}

        # Study hours deductions
        study_hours = metrics.get('study_hours', 0)
        if study_hours > THRESHOLDS['daily_study_hours_danger']:
            deductions += 0.30
            indicators['excessive_study'] = {
                'hours': round(study_hours, 1),
                'threshold': THRESHOLDS['daily_study_hours_danger'],
                'severity': 'high'
            }
        elif study_hours > THRESHOLDS['daily_study_hours_warning']:
            deductions += 0.15
            indicators['high_study'] = {
                'hours': round(study_hours, 1),
                'threshold': THRESHOLDS['daily_study_hours_warning'],
                'severity': 'medium'
            }

        # Consecutive study without break deductions
        consecutive = metrics.get('consecutive_mins', 0)
        if consecutive > THRESHOLDS['session_without_break_danger']:
            deductions += 0.25
            indicators['long_session'] = {
                'minutes': int(consecutive),
                'threshold': THRESHOLDS['session_without_break_danger'],
                'severity': 'high'
            }
        elif consecutive > THRESHOLDS['session_without_break_warning']:
            deductions += 0.10
            indicators['needs_break'] = {
                'minutes': int(consecutive),
                'threshold': THRESHOLDS['session_without_break_warning'],
                'severity': 'medium'
            }

        # Overdue tasks (causes anxiety)
        overdue = metrics.get('overdue_tasks', 0)
        if overdue > THRESHOLDS['overdue_tasks_danger']:
            deductions += 0.20
            indicators['overdue_stress'] = {
                'count': overdue,
                'threshold': THRESHOLDS['overdue_tasks_danger'],
                'severity': 'high'
            }
        elif overdue > THRESHOLDS['overdue_tasks_warning']:
            deductions += 0.10
            indicators['overdue_warning'] = {
                'count': overdue,
                'threshold': THRESHOLDS['overdue_tasks_warning'],
                'severity': 'medium'
            }

        # Skipped breaks deductions
        skipped = metrics.get('skipped_breaks', 0)
        if skipped > THRESHOLDS['skipped_breaks_warning']:
            deductions += min(0.05 * skipped, 0.20)  # Cap at 0.20
            indicators['skipped_breaks'] = {
                'count': skipped,
                'threshold': THRESHOLDS['skipped_breaks_warning'],
                'severity': 'medium'
            }

        # Too many deep work sessions in a row
        deep_work = metrics.get('deep_work_sessions', 0)
        if deep_work >= THRESHOLDS['consecutive_deep_work_danger']:
            deductions += 0.15
            indicators['too_much_deep_work'] = {
                'count': deep_work,
                'threshold': THRESHOLDS['consecutive_deep_work_danger'],
                'severity': 'medium'
            }

        # Positive factors (bonuses)
        bonuses = 0.0

        # Took adequate breaks
        break_count = metrics.get('break_count', 0)
        if break_count >= THRESHOLDS['min_breaks_per_day']:
            bonuses += 0.10
            indicators['healthy_breaks'] = {'count': break_count}
        elif break_count >= 2:
            bonuses += 0.05

        # Healthy amount of deep work (1-2 sessions is ideal)
        if 1 <= deep_work <= 2:
            bonuses += 0.05
            indicators['optimal_deep_work'] = {'count': deep_work}

        # Moderate study hours (4-6 is healthy)
        if 4 <= study_hours <= 6:
            bonuses += 0.05
            indicators['balanced_study'] = {'hours': round(study_hours, 1)}

        # Calculate final score
        final_score = max(0.0, min(1.0, base_score - deductions + bonuses))

        return final_score, indicators

    def _generate_recommendations(
        self,
        score: float,
        indicators: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate actionable recommendations based on score and indicators.

        Args:
            score: Current wellbeing score
            indicators: Dict of triggered indicators

        Returns:
            List of recommendation dictionaries
        """
        recommendations: List[Dict[str, Any]] = []

        # Critical stress level
        if score < 0.3:
            recommendations.append({
                "priority": "urgent",
                "action": "Stop studying immediately and take a 30-minute break",
                "reason": "Your stress level is critically high. Rest now to prevent burnout.",
                "type": "break",
                "suggested_duration_mins": 30
            })

        # Excessive study hours
        if 'excessive_study' in indicators:
            hours = indicators['excessive_study']['hours']
            recommendations.append({
                "priority": "high",
                "action": "Consider finishing your study session for today",
                "reason": f"You have studied {hours} hours today. Rest improves memory consolidation.",
                "type": "stop"
            })
        elif 'high_study' in indicators:
            hours = indicators['high_study']['hours']
            recommendations.append({
                "priority": "medium",
                "action": "Plan to wrap up soon",
                "reason": f"You have studied {hours} hours. Start winding down for better retention.",
                "type": "plan_stop"
            })

        # Long session without break
        if 'long_session' in indicators:
            mins = indicators['long_session']['minutes']
            recommendations.append({
                "priority": "high",
                "action": "Take a 15-20 minute break right now",
                "reason": f"You have been studying for {mins} minutes without a break. This hurts focus.",
                "type": "break",
                "suggested_duration_mins": 15
            })
        elif 'needs_break' in indicators:
            mins = indicators['needs_break']['minutes']
            recommendations.append({
                "priority": "medium",
                "action": "Take a 10-minute break",
                "reason": f"You have been studying for {mins} minutes. A short break will refresh your mind.",
                "type": "break",
                "suggested_duration_mins": 10
            })

        # Overdue tasks causing stress
        if 'overdue_stress' in indicators:
            count = indicators['overdue_stress']['count']
            recommendations.append({
                "priority": "high",
                "action": "Focus on clearing your oldest overdue task first",
                "reason": f"You have {count} overdue tasks. Reducing this backlog will lower anxiety.",
                "type": "prioritize"
            })
        elif 'overdue_warning' in indicators:
            count = indicators['overdue_warning']['count']
            recommendations.append({
                "priority": "medium",
                "action": "Address overdue tasks when possible",
                "reason": f"You have {count} overdue tasks. Consider prioritizing these.",
                "type": "prioritize"
            })

        # Skipped breaks
        if 'skipped_breaks' in indicators:
            count = indicators['skipped_breaks']['count']
            recommendations.append({
                "priority": "medium",
                "action": "Honor your next scheduled break",
                "reason": f"You skipped {count} breaks today. Regular breaks boost productivity.",
                "type": "habit"
            })

        # Too much deep work
        if 'too_much_deep_work' in indicators:
            count = indicators['too_much_deep_work']['count']
            recommendations.append({
                "priority": "medium",
                "action": "Switch to lighter tasks or review material",
                "reason": f"You have completed {count} deep work sessions. Mental fatigue accumulates.",
                "type": "variety"
            })

        # Positive reinforcement
        if score >= 0.7 and not recommendations:
            recommendations.append({
                "priority": "low",
                "action": "Keep up the excellent work!",
                "reason": "Your study habits are healthy and sustainable.",
                "type": "encouragement"
            })
        elif 'healthy_breaks' in indicators:
            recommendations.append({
                "priority": "low",
                "action": "Great break discipline!",
                "reason": "Taking regular breaks is key to sustained performance.",
                "type": "encouragement"
            })

        return recommendations


# ============================================
# BREAK MANAGEMENT FUNCTIONS
# ============================================

async def suggest_break(current_study_mins: Optional[int] = None) -> BreakSession:
    """
    Suggest an appropriate break based on current study duration.

    Args:
        current_study_mins: Override for current study duration

    Returns:
        BreakSession with suggested type and duration
    """
    # Get current session duration if not provided
    if current_study_mins is None:
        active = await db.fetch_one('''
            SELECT started_at FROM active_timer LIMIT 1
        ''')
        if active:
            elapsed = datetime.now() - active['started_at']
            current_study_mins = int(elapsed.total_seconds() / 60)
        else:
            current_study_mins = 0

    # Determine appropriate break type
    if current_study_mins >= 90:
        # After deep work session, suggest exercise
        break_type = BreakType.EXERCISE
        duration = 20
    elif current_study_mins >= 60:
        # After extended session, suggest longer break
        break_type = BreakType.LONG
        duration = 15
    elif current_study_mins >= 45:
        # Standard break
        break_type = BreakType.SHORT
        duration = 10
    elif current_study_mins >= 25:
        # Pomodoro-style break
        break_type = BreakType.POMODORO
        duration = 5
    else:
        # Too early for break, but if requested, short one
        break_type = BreakType.SHORT
        duration = 5

    return BreakSession(
        break_type=break_type,
        started_at=datetime.now(),
        suggested_duration_mins=duration
    )


async def start_break(
    break_type: BreakType,
    suggested_mins: Optional[int] = None
) -> Dict[str, Any]:
    """
    Start a break session and record it.

    Args:
        break_type: Type of break to start
        suggested_mins: Override for suggested duration

    Returns:
        Dict with break_id and session details
    """
    if suggested_mins is None:
        min_dur, max_dur = BREAK_DURATIONS.get(break_type, (10, 10))
        suggested_mins = (min_dur + max_dur) // 2

    result = await db.execute_returning('''
        INSERT INTO break_sessions (break_type, started_at, suggested_duration_mins)
        VALUES ($1, NOW(), $2)
        RETURNING *
    ''', break_type.value, suggested_mins)

    return {
        "success": True,
        "break_id": result['id'],
        "break_type": break_type.value,
        "started_at": result['started_at'].isoformat(),
        "suggested_duration_mins": suggested_mins,
        "message": f"Started {break_type.value} break. Relax for {suggested_mins} minutes."
    }


async def end_break(break_id: int, was_completed: bool = True) -> Dict[str, Any]:
    """
    End a break session and record completion status.

    Args:
        break_id: ID of the break session
        was_completed: Whether the full break was taken

    Returns:
        Dict with break session details
    """
    result = await db.execute_returning('''
        UPDATE break_sessions
        SET ended_at = NOW(),
            actual_duration_mins = EXTRACT(EPOCH FROM (NOW() - started_at))/60,
            was_completed = $2
        WHERE id = $1
        RETURNING *
    ''', break_id, was_completed)

    if not result:
        return {"success": False, "error": "Break session not found"}

    actual_mins = int(result['actual_duration_mins'] or 0)
    suggested_mins = result['suggested_duration_mins']

    message = f"Break ended after {actual_mins} minutes."
    if was_completed and actual_mins >= suggested_mins:
        message += " Well done taking a proper break!"
    elif not was_completed:
        message += " Break was cut short. Try to take full breaks when possible."

    return {
        "success": True,
        "break_id": break_id,
        "break_type": result['break_type'],
        "actual_duration_mins": actual_mins,
        "suggested_duration_mins": suggested_mins,
        "was_completed": was_completed,
        "message": message
    }


async def get_active_break() -> Optional[Dict[str, Any]]:
    """Get currently active break session if any."""
    result = await db.fetch_one('''
        SELECT * FROM break_sessions
        WHERE ended_at IS NULL
        ORDER BY started_at DESC
        LIMIT 1
    ''')

    if not result:
        return None

    elapsed = datetime.now() - result['started_at']
    elapsed_mins = int(elapsed.total_seconds() / 60)
    remaining = max(0, result['suggested_duration_mins'] - elapsed_mins)

    return {
        "break_id": result['id'],
        "break_type": result['break_type'],
        "started_at": result['started_at'].isoformat(),
        "elapsed_mins": elapsed_mins,
        "suggested_duration_mins": result['suggested_duration_mins'],
        "remaining_mins": remaining,
        "is_overdue": elapsed_mins > result['suggested_duration_mins']
    }


async def get_break_stats(days: int = 7) -> Dict[str, Any]:
    """
    Get break statistics for the specified period.

    Args:
        days: Number of days to analyze

    Returns:
        Dict with break statistics
    """
    # Overall stats
    overall = await db.fetch_one('''
        SELECT
            COUNT(*) as total_breaks,
            COUNT(*) FILTER (WHERE was_completed) as completed_breaks,
            COALESCE(AVG(actual_duration_mins), 0) as avg_duration,
            COALESCE(SUM(actual_duration_mins), 0) as total_mins
        FROM break_sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
    ''' % days)

    # By type breakdown
    by_type = await db.fetch('''
        SELECT
            break_type,
            COUNT(*) as count,
            COALESCE(AVG(actual_duration_mins), 0) as avg_duration
        FROM break_sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY break_type
        ORDER BY count DESC
    ''' % days)

    # Daily breakdown
    daily = await db.fetch('''
        SELECT
            DATE(started_at) as date,
            COUNT(*) as breaks,
            COALESCE(SUM(actual_duration_mins), 0) as total_mins
        FROM break_sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
        GROUP BY DATE(started_at)
        ORDER BY date
    ''' % days)

    total = overall['total_breaks'] or 0
    completed = overall['completed_breaks'] or 0
    completion_rate = (completed / total * 100) if total > 0 else 0

    return {
        "period_days": days,
        "totals": {
            "total_breaks": total,
            "completed_breaks": completed,
            "completion_rate": round(completion_rate, 1),
            "avg_duration_mins": round(overall['avg_duration'] or 0, 1),
            "total_break_mins": int(overall['total_mins'] or 0)
        },
        "by_type": [dict(row) for row in by_type],
        "daily": [dict(row) for row in daily]
    }


# ============================================
# DAILY METRICS STORAGE
# ============================================

async def save_daily_metrics() -> Dict[str, Any]:
    """
    Save today's wellbeing metrics for historical tracking.
    Called at end of day or periodically.

    Returns:
        Dict with saved metrics summary
    """
    monitor = WellbeingMonitor()
    metrics = await monitor.calculate_wellbeing_score()

    # Calculate task completion rate
    task_stats = await db.fetch_one('''
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) as total
        FROM tasks
        WHERE DATE(scheduled_start) = CURRENT_DATE
    ''')
    completion_rate = 0
    if task_stats and task_stats['total'] > 0:
        completion_rate = int(task_stats['completed'] / task_stats['total'] * 100)

    # Save to database
    await db.execute('''
        INSERT INTO wellbeing_metrics
        (metric_date, study_hours, break_count, break_total_mins,
         deep_work_sessions, task_completion_rate, overdue_tasks,
         stress_indicators, wellbeing_score, recommendations)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (metric_date) DO UPDATE SET
            study_hours = EXCLUDED.study_hours,
            break_count = EXCLUDED.break_count,
            break_total_mins = EXCLUDED.break_total_mins,
            deep_work_sessions = EXCLUDED.deep_work_sessions,
            task_completion_rate = EXCLUDED.task_completion_rate,
            overdue_tasks = EXCLUDED.overdue_tasks,
            stress_indicators = EXCLUDED.stress_indicators,
            wellbeing_score = EXCLUDED.wellbeing_score,
            recommendations = EXCLUDED.recommendations,
            updated_at = NOW()
    ''',
        date.today(),
        metrics.study_hours_today,
        metrics.break_count,
        metrics.break_total_mins,
        metrics.deep_work_sessions,
        completion_rate,
        metrics.overdue_tasks,
        json.dumps(metrics.indicators),
        metrics.score,
        json.dumps([r for r in metrics.recommendations])
    )

    return {
        "success": True,
        "date": date.today().isoformat(),
        "score": metrics.score,
        "stress_level": metrics.stress_level.value
    }


async def get_wellbeing_history(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get wellbeing history for trend visualization.

    Args:
        days: Number of days of history to retrieve

    Returns:
        List of daily wellbeing records
    """
    rows = await db.fetch('''
        SELECT
            metric_date,
            study_hours,
            break_count,
            break_total_mins,
            deep_work_sessions,
            task_completion_rate,
            overdue_tasks,
            wellbeing_score,
            stress_indicators,
            recommendations
        FROM wellbeing_metrics
        WHERE metric_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY metric_date DESC
    ''' % days)

    result = []
    for row in rows:
        stress_level = StressLevel.LOW
        if row['wellbeing_score'] < 0.7:
            stress_level = StressLevel.MODERATE
        if row['wellbeing_score'] < 0.4:
            stress_level = StressLevel.HIGH

        result.append({
            "date": row['metric_date'].isoformat(),
            "wellbeing_score": row['wellbeing_score'],
            "stress_level": stress_level.value,
            "study_hours": row['study_hours'],
            "break_count": row['break_count'],
            "break_total_mins": row['break_total_mins'],
            "deep_work_sessions": row['deep_work_sessions'],
            "task_completion_rate": row['task_completion_rate'],
            "overdue_tasks": row['overdue_tasks'],
            "indicators": row['stress_indicators'],
            "recommendations": row['recommendations']
        })

    return result


async def get_wellbeing_trends(days: int = 30) -> Dict[str, Any]:
    """
    Analyze wellbeing trends over time.

    Args:
        days: Period to analyze

    Returns:
        Dict with trend analysis
    """
    history = await get_wellbeing_history(days)

    if not history:
        return {
            "period_days": days,
            "has_data": False,
            "message": "No wellbeing data available for this period"
        }

    scores = [h['wellbeing_score'] for h in history]
    avg_score = sum(scores) / len(scores)

    # Calculate trend (positive = improving)
    if len(scores) >= 7:
        recent_avg = sum(scores[:7]) / 7
        older_avg = sum(scores[7:14]) / min(7, len(scores) - 7) if len(scores) > 7 else recent_avg
        trend = recent_avg - older_avg
    else:
        trend = 0

    # Count stress days
    high_stress_days = sum(1 for h in history if h['stress_level'] == 'high')
    moderate_stress_days = sum(1 for h in history if h['stress_level'] == 'moderate')

    # Average metrics
    avg_study_hours = sum(h['study_hours'] for h in history) / len(history)
    avg_breaks = sum(h['break_count'] for h in history) / len(history)

    trend_direction = "improving" if trend > 0.05 else "declining" if trend < -0.05 else "stable"

    return {
        "period_days": days,
        "has_data": True,
        "data_points": len(history),
        "average_score": round(avg_score, 2),
        "current_score": history[0]['wellbeing_score'] if history else None,
        "trend": {
            "direction": trend_direction,
            "change": round(trend, 2)
        },
        "stress_distribution": {
            "high_stress_days": high_stress_days,
            "moderate_stress_days": moderate_stress_days,
            "low_stress_days": len(history) - high_stress_days - moderate_stress_days
        },
        "averages": {
            "study_hours_per_day": round(avg_study_hours, 1),
            "breaks_per_day": round(avg_breaks, 1)
        }
    }


# ============================================
# POMODORO TIMER SUPPORT
# ============================================

class PomodoroTimer:
    """
    Pomodoro technique implementation.

    Standard Pomodoro: 25 min work, 5 min break
    After 4 cycles: 15-30 min long break
    """

    WORK_DURATION = 25   # minutes
    SHORT_BREAK = 5      # minutes
    LONG_BREAK = 15      # minutes
    CYCLES_BEFORE_LONG = 4

    async def get_status(self) -> Dict[str, Any]:
        """Get current Pomodoro status."""
        status = await db.fetch_one('''
            SELECT * FROM pomodoro_status LIMIT 1
        ''')

        if not status:
            return {
                "is_active": False,
                "current_phase": "idle",
                "cycles_completed": 0,
                "current_cycle_start": None,
                "time_remaining_seconds": None,
                "next_phase": "work"
            }

        elapsed = datetime.now() - status['phase_started_at']
        elapsed_mins = elapsed.total_seconds() / 60

        # Determine phase duration
        if status['current_phase'] == 'work':
            phase_duration = self.WORK_DURATION
            next_phase = 'long_break' if (status['cycles_completed'] + 1) % self.CYCLES_BEFORE_LONG == 0 else 'short_break'
        elif status['current_phase'] == 'short_break':
            phase_duration = self.SHORT_BREAK
            next_phase = 'work'
        else:  # long_break
            phase_duration = self.LONG_BREAK
            next_phase = 'work'

        remaining = max(0, int((phase_duration - elapsed_mins) * 60))

        return {
            "is_active": status['is_active'],
            "current_phase": status['current_phase'],
            "cycles_completed": status['cycles_completed'],
            "current_cycle_start": status['cycle_started_at'].isoformat() if status['cycle_started_at'] else None,
            "time_remaining_seconds": remaining,
            "next_phase": next_phase,
            "phase_started_at": status['phase_started_at'].isoformat()
        }

    async def start_work(self) -> Dict[str, Any]:
        """Start a work session."""
        await db.execute('''
            INSERT INTO pomodoro_status
            (is_active, current_phase, cycles_completed, phase_started_at, cycle_started_at)
            VALUES (true, 'work', 0, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                is_active = true,
                current_phase = 'work',
                phase_started_at = NOW(),
                cycle_started_at = CASE
                    WHEN pomodoro_status.current_phase IN ('short_break', 'long_break', 'idle')
                    THEN NOW()
                    ELSE pomodoro_status.cycle_started_at
                END
        ''')

        return {
            "success": True,
            "phase": "work",
            "duration_mins": self.WORK_DURATION,
            "message": f"Pomodoro started! Focus for {self.WORK_DURATION} minutes."
        }

    async def start_break(self) -> Dict[str, Any]:
        """Start break (short or long based on cycle count)."""
        status = await self.get_status()

        # Increment cycle if coming from work
        new_cycles = status['cycles_completed']
        if status['current_phase'] == 'work':
            new_cycles += 1

        # Determine break type
        is_long_break = new_cycles % self.CYCLES_BEFORE_LONG == 0 and new_cycles > 0
        break_type = 'long_break' if is_long_break else 'short_break'
        duration = self.LONG_BREAK if is_long_break else self.SHORT_BREAK

        await db.execute('''
            UPDATE pomodoro_status
            SET current_phase = $1,
                cycles_completed = $2,
                phase_started_at = NOW()
            WHERE id = 1
        ''', break_type, new_cycles)

        return {
            "success": True,
            "phase": break_type,
            "duration_mins": duration,
            "cycles_completed": new_cycles,
            "message": f"{'Long' if is_long_break else 'Short'} break! Rest for {duration} minutes."
        }

    async def stop(self) -> Dict[str, Any]:
        """Stop the Pomodoro timer."""
        status = await self.get_status()

        await db.execute('''
            UPDATE pomodoro_status
            SET is_active = false,
                current_phase = 'idle'
            WHERE id = 1
        ''')

        return {
            "success": True,
            "cycles_completed": status['cycles_completed'],
            "message": f"Pomodoro stopped. You completed {status['cycles_completed']} cycles."
        }

    async def reset(self) -> Dict[str, Any]:
        """Reset Pomodoro timer completely."""
        await db.execute('''
            DELETE FROM pomodoro_status WHERE id = 1
        ''')

        return {
            "success": True,
            "message": "Pomodoro timer reset."
        }


# ============================================
# INTEGRATION WITH TIMER SYSTEM
# ============================================

async def check_wellbeing_after_session(
    session_duration_seconds: int
) -> Optional[Dict[str, Any]]:
    """
    Check wellbeing after a study session ends.
    Returns recommendations if needed.

    Args:
        session_duration_seconds: Duration of the completed session

    Returns:
        Dict with wellbeing check results, or None if all is well
    """
    monitor = WellbeingMonitor()
    metrics = await monitor.calculate_wellbeing_score()

    # Filter to only urgent/high priority recommendations
    urgent_recs = [
        r for r in metrics.recommendations
        if r['priority'] in ('urgent', 'high')
    ]

    if not urgent_recs and metrics.stress_level == StressLevel.LOW:
        return None

    return {
        "wellbeing_score": metrics.score,
        "stress_level": metrics.stress_level.value,
        "study_hours_today": metrics.study_hours_today,
        "recommendations": urgent_recs or metrics.recommendations[:2],
        "should_take_break": metrics.stress_level != StressLevel.LOW or metrics.consecutive_study_mins > 45
    }


async def should_suggest_break() -> Tuple[bool, Optional[BreakSession]]:
    """
    Check if a break should be suggested based on current state.

    Returns:
        Tuple of (should_suggest, suggested_break)
    """
    # Check active session duration
    active = await db.fetch_one('''
        SELECT started_at FROM active_timer LIMIT 1
    ''')

    if not active:
        return False, None

    elapsed = datetime.now() - active['started_at']
    elapsed_mins = elapsed.total_seconds() / 60

    # Don't suggest if studied less than minimum
    if elapsed_mins < THRESHOLDS['min_study_before_break']:
        return False, None

    # Check last break
    last_break = await db.fetch_one('''
        SELECT ended_at FROM break_sessions
        WHERE was_completed = true
        ORDER BY ended_at DESC
        LIMIT 1
    ''')

    time_since_break = elapsed_mins
    if last_break and last_break['ended_at']:
        time_since_break = (datetime.now() - last_break['ended_at']).total_seconds() / 60

    # Suggest break if studied long enough
    if time_since_break >= THRESHOLDS['session_without_break_warning']:
        suggestion = await suggest_break(int(elapsed_mins))
        return True, suggestion

    # Pomodoro-style: suggest after 25 mins if no recent break
    if elapsed_mins >= 25 and time_since_break >= 25:
        suggestion = await suggest_break(int(elapsed_mins))
        return True, suggestion

    return False, None


# ============================================
# NOTIFICATION GENERATION
# ============================================

async def generate_wellbeing_notifications() -> List[Dict[str, Any]]:
    """
    Generate notifications based on current wellbeing state.

    Returns:
        List of notification dictionaries
    """
    monitor = WellbeingMonitor()
    metrics = await monitor.calculate_wellbeing_score()
    notifications = []

    # High stress notification
    if metrics.stress_level == StressLevel.HIGH:
        notifications.append({
            "type": "wellbeing",
            "priority": "high",
            "title": "High Stress Detected",
            "message": "Your stress level is high. Consider taking a break to prevent burnout.",
            "action": "take_break"
        })

    # Long session notification
    if metrics.consecutive_study_mins > THRESHOLDS['session_without_break_warning']:
        notifications.append({
            "type": "break_reminder",
            "priority": "medium",
            "title": "Break Time",
            "message": f"You've been studying for {int(metrics.consecutive_study_mins)} minutes. Time for a break!",
            "action": "suggest_break"
        })

    # Excessive study hours
    if metrics.study_hours_today > THRESHOLDS['daily_study_hours_warning']:
        notifications.append({
            "type": "study_limit",
            "priority": "medium",
            "title": "Study Hours Warning",
            "message": f"You've studied {metrics.study_hours_today:.1f} hours today. Consider wrapping up.",
            "action": "end_day"
        })

    # Overdue tasks
    if metrics.overdue_tasks > THRESHOLDS['overdue_tasks_warning']:
        notifications.append({
            "type": "task_overdue",
            "priority": "low",
            "title": "Overdue Tasks",
            "message": f"You have {metrics.overdue_tasks} overdue tasks. Clearing these can reduce stress.",
            "action": "view_tasks"
        })

    return notifications
