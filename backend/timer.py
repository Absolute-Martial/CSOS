"""
Personal Engineering OS - Study Timer Module
Track study sessions with analytics and deep work detection
"""

from datetime import datetime, timedelta
from typing import Optional, List

from database import db


# ============================================
# ACTIVE TIMER OPERATIONS
# ============================================

async def get_active_timer() -> Optional[dict]:
    """Get currently running timer with elapsed time."""
    return await db.fetch_one("""
        SELECT
            at.*,
            s.code as subject_code,
            s.name as subject_name,
            s.color,
            EXTRACT(EPOCH FROM (NOW() - at.started_at))::INTEGER as elapsed_seconds
        FROM active_timer at
        LEFT JOIN subjects s ON at.subject_id = s.id
        LIMIT 1
    """)


async def start_timer(
    subject_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    title: Optional[str] = None
) -> dict:
    """Start a new study session timer."""
    # Check if timer already running
    active = await get_active_timer()
    if active:
        return {
            "success": False,
            "error": "Timer already running",
            "active_timer": active
        }

    # Create session record
    session = await db.execute_returning("""
        INSERT INTO study_sessions (subject_id, chapter_id, title, started_at)
        VALUES ($1, $2, $3, NOW())
        RETURNING *
    """, subject_id, chapter_id, title)

    # Create active timer pointer
    await db.execute("""
        INSERT INTO active_timer (id, session_id, started_at, subject_id, chapter_id, title)
        VALUES (1, $1, NOW(), $2, $3, $4)
        ON CONFLICT (id) DO UPDATE SET
            session_id = $1,
            started_at = NOW(),
            subject_id = $2,
            chapter_id = $3,
            title = $4
    """, session['id'], subject_id, chapter_id, title)

    # Get subject info for response
    subject_info = None
    if subject_id:
        subject_info = await db.fetch_one(
            "SELECT code, name, color FROM subjects WHERE id = $1", subject_id
        )

    return {
        "success": True,
        "session": session,
        "subject": subject_info,
        "message": f"Timer started{' for ' + title if title else ''}"
    }


async def stop_timer() -> dict:
    """Stop the active timer and finalize session."""
    active = await get_active_timer()
    if not active:
        return {
            "success": False,
            "error": "No active timer"
        }

    # Update session with stop time (trigger will calculate duration and points)
    session = await db.execute_returning("""
        UPDATE study_sessions
        SET stopped_at = NOW()
        WHERE id = $1
        RETURNING *
    """, active['session_id'])

    # Clear active timer
    await db.execute("DELETE FROM active_timer WHERE id = 1")

    # Format duration for response
    duration_mins = (session['duration_seconds'] or 0) // 60
    hours = duration_mins // 60
    mins = duration_mins % 60

    duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} minutes"

    # Update learning patterns from this session
    try:
        from learning_patterns import update_patterns_from_session
        await update_patterns_from_session(session['id'])
    except Exception:
        pass  # Don't fail timer stop if pattern update fails

    # Check for newly earned achievements after study session
    earned_achievements = []
    try:
        from achievements import check_achievements_after_action
        earned_achievements = await check_achievements_after_action("study_session")
    except Exception:
        pass  # Don't fail timer stop if achievement check fails

    return {
        "success": True,
        "session": session,
        "duration_seconds": session['duration_seconds'],
        "duration_formatted": duration_str,
        "is_deep_work": session['is_deep_work'],
        "points_earned": session['points_earned'],
        "message": f"Studied for {duration_str}" + (" (Deep Work!)" if session['is_deep_work'] else ""),
        "achievements_earned": earned_achievements
    }


# ============================================
# SESSION HISTORY
# ============================================

async def get_study_sessions(
    days: int = 7,
    subject_id: Optional[int] = None,
    limit: int = 50
) -> List[dict]:
    """Get past study sessions with optional filters."""
    if subject_id:
        return await db.fetch("""
            SELECT
                ss.*,
                s.code as subject_code,
                s.name as subject_name,
                s.color,
                c.number as chapter_number,
                c.title as chapter_title
            FROM study_sessions ss
            LEFT JOIN subjects s ON ss.subject_id = s.id
            LEFT JOIN chapters c ON ss.chapter_id = c.id
            WHERE ss.stopped_at IS NOT NULL
              AND ss.started_at >= NOW() - INTERVAL '%s days'
              AND ss.subject_id = $1
            ORDER BY ss.started_at DESC
            LIMIT $2
        """ % days, subject_id, limit)

    return await db.fetch("""
        SELECT
            ss.*,
            s.code as subject_code,
            s.name as subject_name,
            s.color,
            c.number as chapter_number,
            c.title as chapter_title
        FROM study_sessions ss
        LEFT JOIN subjects s ON ss.subject_id = s.id
        LEFT JOIN chapters c ON ss.chapter_id = c.id
        WHERE ss.stopped_at IS NOT NULL
          AND ss.started_at >= NOW() - INTERVAL '%s days'
        ORDER BY ss.started_at DESC
        LIMIT $1
    """ % days, limit)


# ============================================
# ANALYTICS
# ============================================

async def get_study_analytics(days: int = 7) -> dict:
    """Get comprehensive study time analytics."""

    # Daily breakdown
    daily_stats = await db.fetch("""
        SELECT
            DATE(started_at) as date,
            SUM(duration_seconds) as total_seconds,
            COUNT(*) as session_count,
            SUM(CASE WHEN is_deep_work THEN duration_seconds ELSE 0 END) as deep_work_seconds,
            SUM(points_earned) as points
        FROM study_sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
          AND stopped_at IS NOT NULL
        GROUP BY DATE(started_at)
        ORDER BY date
    """ % days)

    # By subject breakdown
    by_subject = await db.fetch("""
        SELECT
            s.id,
            s.code,
            s.name,
            s.color,
            SUM(ss.duration_seconds) as total_seconds,
            COUNT(*) as session_count,
            AVG(ss.duration_seconds) as avg_session_seconds
        FROM study_sessions ss
        JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.started_at >= NOW() - INTERVAL '%s days'
          AND ss.stopped_at IS NOT NULL
        GROUP BY s.id
        ORDER BY total_seconds DESC
    """ % days)

    # Overall totals
    totals = await db.fetch_one("""
        SELECT
            COALESCE(SUM(duration_seconds), 0) as total_seconds,
            COUNT(*) as total_sessions,
            COALESCE(AVG(duration_seconds), 0) as avg_session_seconds,
            COALESCE(SUM(CASE WHEN is_deep_work THEN duration_seconds ELSE 0 END), 0) as deep_work_seconds,
            COALESCE(SUM(points_earned), 0) as total_points
        FROM study_sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
          AND stopped_at IS NOT NULL
    """ % days)

    # Today's stats
    today = await db.fetch_one("""
        SELECT
            COALESCE(SUM(duration_seconds), 0) as total_seconds,
            COUNT(*) as session_count,
            COALESCE(SUM(CASE WHEN is_deep_work THEN duration_seconds ELSE 0 END), 0) as deep_work_seconds
        FROM study_sessions
        WHERE DATE(started_at) = CURRENT_DATE
          AND stopped_at IS NOT NULL
    """)

    # Format totals
    total_hours = (totals['total_seconds'] or 0) / 3600
    deep_work_hours = (totals['deep_work_seconds'] or 0) / 3600
    deep_work_ratio = deep_work_hours / total_hours * 100 if total_hours > 0 else 0

    return {
        "period_days": days,
        "daily": daily_stats,
        "by_subject": by_subject,
        "totals": {
            "total_seconds": totals['total_seconds'],
            "total_hours": round(total_hours, 1),
            "total_sessions": totals['total_sessions'],
            "avg_session_minutes": round((totals['avg_session_seconds'] or 0) / 60, 1),
            "deep_work_seconds": totals['deep_work_seconds'],
            "deep_work_hours": round(deep_work_hours, 1),
            "deep_work_ratio": round(deep_work_ratio, 1),
            "total_points": totals['total_points']
        },
        "today": {
            "total_seconds": today['total_seconds'],
            "total_minutes": round((today['total_seconds'] or 0) / 60, 1),
            "session_count": today['session_count'],
            "deep_work_seconds": today['deep_work_seconds']
        }
    }


async def get_productivity_by_hour(days: int = 30) -> List[dict]:
    """Get average productivity by hour of day."""
    return await db.fetch("""
        SELECT
            EXTRACT(HOUR FROM started_at)::INTEGER as hour,
            COUNT(*) as session_count,
            AVG(duration_seconds) as avg_duration,
            SUM(CASE WHEN is_deep_work THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 as deep_work_rate
        FROM study_sessions
        WHERE started_at >= NOW() - INTERVAL '%s days'
          AND stopped_at IS NOT NULL
        GROUP BY EXTRACT(HOUR FROM started_at)
        ORDER BY hour
    """ % days)
