"""
Personal Engineering OS - Study Goals Module
Track academic and personal learning goals with progress
"""

from datetime import datetime, date
from typing import Optional, List

from database import db


# ============================================
# CATEGORY OPERATIONS
# ============================================

async def get_goal_categories() -> List[dict]:
    """Get all goal categories."""
    return await db.fetch("""
        SELECT
            gc.*,
            COUNT(sg.id) as goal_count,
            COUNT(CASE WHEN sg.completed THEN 1 END) as completed_count
        FROM goal_categories gc
        LEFT JOIN study_goals sg ON gc.id = sg.category_id
        GROUP BY gc.id
        ORDER BY gc.sort_order, gc.name
    """)


async def create_goal_category(
    name: str,
    color: str = '#6366f1',
    icon: str = '🎯'
) -> dict:
    """Create a new goal category."""
    # Get next sort order
    max_order = await db.fetch_one(
        "SELECT COALESCE(MAX(sort_order), 0) + 1 as next FROM goal_categories"
    )

    return await db.execute_returning("""
        INSERT INTO goal_categories (name, color, icon, sort_order)
        VALUES ($1, $2, $3, $4)
        RETURNING *
    """, name, color, icon, max_order['next'])


async def update_goal_category(category_id: int, **updates) -> dict:
    """Update a goal category."""
    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), 1):
        set_parts.append(f"{k} = ${i}")
        values.append(v)
    values.append(category_id)
    set_clause = ", ".join(set_parts)

    return await db.execute_returning(
        f"UPDATE goal_categories SET {set_clause} WHERE id = ${len(values)} RETURNING *",
        *values
    )


async def delete_goal_category(category_id: int) -> bool:
    """Delete a goal category."""
    result = await db.execute(
        "DELETE FROM goal_categories WHERE id = $1", category_id
    )
    return "DELETE 1" in result


# ============================================
# GOAL OPERATIONS
# ============================================

async def get_goals(
    category_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    include_completed: bool = False
) -> List[dict]:
    """Get study goals with optional filters."""
    conditions = []
    params = []
    param_idx = 1

    if category_id:
        conditions.append(f"sg.category_id = ${param_idx}")
        params.append(category_id)
        param_idx += 1

    if subject_id:
        conditions.append(f"sg.subject_id = ${param_idx}")
        params.append(subject_id)
        param_idx += 1

    if not include_completed:
        conditions.append("sg.completed = false")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    return await db.fetch(f"""
        SELECT
            sg.*,
            gc.name as category_name,
            gc.color as category_color,
            gc.icon as category_icon,
            s.code as subject_code,
            s.name as subject_name,
            s.color as subject_color,
            CASE
                WHEN sg.target_value > 0
                THEN ROUND(sg.current_value::NUMERIC / sg.target_value * 100, 1)
                ELSE 0
            END as progress_percent,
            CASE
                WHEN sg.deadline IS NOT NULL
                THEN sg.deadline - CURRENT_DATE
                ELSE NULL
            END as days_remaining
        FROM study_goals sg
        LEFT JOIN goal_categories gc ON sg.category_id = gc.id
        LEFT JOIN subjects s ON sg.subject_id = s.id
        {where_clause}
        ORDER BY sg.completed, sg.deadline NULLS LAST, sg.priority, sg.created_at DESC
    """, *params)


async def get_goal(goal_id: int) -> Optional[dict]:
    """Get a single goal by ID."""
    return await db.fetch_one("""
        SELECT
            sg.*,
            gc.name as category_name,
            gc.color as category_color,
            gc.icon as category_icon,
            s.code as subject_code,
            s.name as subject_name,
            s.color as subject_color,
            CASE
                WHEN sg.target_value > 0
                THEN ROUND(sg.current_value::NUMERIC / sg.target_value * 100, 1)
                ELSE 0
            END as progress_percent
        FROM study_goals sg
        LEFT JOIN goal_categories gc ON sg.category_id = gc.id
        LEFT JOIN subjects s ON sg.subject_id = s.id
        WHERE sg.id = $1
    """, goal_id)


async def create_goal(
    title: str,
    category_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    description: Optional[str] = None,
    target_value: Optional[int] = None,
    unit: Optional[str] = None,
    deadline: Optional[date] = None,
    priority: int = 5
) -> dict:
    """Create a new study goal."""
    return await db.execute_returning("""
        INSERT INTO study_goals
            (title, category_id, subject_id, description, target_value, unit, deadline, priority)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
    """, title, category_id, subject_id, description, target_value, unit, deadline, priority)


async def update_goal(goal_id: int, **updates) -> dict:
    """Update a study goal."""
    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), 1):
        set_parts.append(f"{k} = ${i}")
        values.append(v)
    values.append(goal_id)
    set_clause = ", ".join(set_parts)

    return await db.execute_returning(
        f"UPDATE study_goals SET {set_clause}, updated_at = NOW() WHERE id = ${len(values)} RETURNING *",
        *values
    )


async def update_goal_progress(
    goal_id: int,
    progress_delta: int = 0,
    set_value: Optional[int] = None,
    mark_complete: Optional[bool] = None
) -> dict:
    """
    Update goal progress.

    Args:
        goal_id: The goal ID
        progress_delta: Amount to add to current_value
        set_value: Directly set current_value (overrides delta)
        mark_complete: Force completion status

    Returns:
        Updated goal with progress info
    """
    # Get current goal
    goal = await db.fetch_one("SELECT * FROM study_goals WHERE id = $1", goal_id)
    if not goal:
        return {"error": "Goal not found"}

    # Calculate new value
    if set_value is not None:
        new_value = set_value
    else:
        new_value = (goal['current_value'] or 0) + progress_delta

    # Check if goal is completed
    completed = goal['completed']
    completed_at = goal['completed_at']

    if mark_complete is not None:
        completed = mark_complete
        completed_at = datetime.now() if mark_complete else None
    elif goal['target_value'] and new_value >= goal['target_value']:
        completed = True
        completed_at = datetime.now()

    # Update goal
    updated = await db.execute_returning("""
        UPDATE study_goals SET
            current_value = $1,
            completed = $2,
            completed_at = $3,
            updated_at = NOW()
        WHERE id = $4
        RETURNING *
    """, new_value, completed, completed_at, goal_id)

    # If just completed, update daily stats
    just_completed = completed and not goal['completed']
    if just_completed:
        await db.execute("""
            INSERT INTO daily_study_stats (stat_date, goals_progress)
            VALUES (CURRENT_DATE, 1)
            ON CONFLICT (stat_date) DO UPDATE SET
                goals_progress = daily_study_stats.goals_progress + 1,
                updated_at = NOW()
        """)

    # Calculate progress
    progress_percent = 0
    if updated['target_value'] and updated['target_value'] > 0:
        progress_percent = round(updated['current_value'] / updated['target_value'] * 100, 1)

    # Check for newly earned achievements if goal was just completed
    earned_achievements = []
    if just_completed:
        try:
            from achievements import check_achievements_after_action
            earned_achievements = await check_achievements_after_action("goal_complete")
        except Exception:
            pass  # Don't fail if achievement check fails

    return {
        "success": True,
        "goal": updated,
        "progress_percent": progress_percent,
        "just_completed": just_completed,
        "achievements_earned": earned_achievements
    }


async def delete_goal(goal_id: int) -> bool:
    """Delete a study goal."""
    result = await db.execute("DELETE FROM study_goals WHERE id = $1", goal_id)
    return "DELETE 1" in result


# ============================================
# STATISTICS
# ============================================

async def get_goals_summary() -> dict:
    """Get goal completion statistics."""

    # Overall stats
    totals = await db.fetch_one("""
        SELECT
            COUNT(*) as total_goals,
            COUNT(CASE WHEN completed THEN 1 END) as completed_goals,
            COUNT(CASE WHEN NOT completed AND deadline < CURRENT_DATE THEN 1 END) as overdue_goals,
            COUNT(CASE WHEN NOT completed AND deadline BETWEEN CURRENT_DATE AND CURRENT_DATE + 7 THEN 1 END) as due_this_week
        FROM study_goals
    """)

    # By category
    by_category = await db.fetch("""
        SELECT
            gc.id,
            gc.name,
            gc.color,
            gc.icon,
            COUNT(sg.id) as total_goals,
            COUNT(CASE WHEN sg.completed THEN 1 END) as completed_goals,
            ROUND(
                COUNT(CASE WHEN sg.completed THEN 1 END)::NUMERIC /
                NULLIF(COUNT(sg.id), 0) * 100, 1
            ) as completion_rate
        FROM goal_categories gc
        LEFT JOIN study_goals sg ON gc.id = sg.category_id
        GROUP BY gc.id
        ORDER BY gc.sort_order
    """)

    # By subject
    by_subject = await db.fetch("""
        SELECT
            s.id,
            s.code,
            s.name,
            s.color,
            COUNT(sg.id) as total_goals,
            COUNT(CASE WHEN sg.completed THEN 1 END) as completed_goals
        FROM subjects s
        JOIN study_goals sg ON s.id = sg.subject_id
        GROUP BY s.id
        ORDER BY total_goals DESC
    """)

    # Recent completions
    recent_completions = await db.fetch("""
        SELECT
            sg.*,
            gc.name as category_name,
            gc.icon as category_icon
        FROM study_goals sg
        LEFT JOIN goal_categories gc ON sg.category_id = gc.id
        WHERE sg.completed = true
        ORDER BY sg.completed_at DESC
        LIMIT 5
    """)

    # Calculate completion rate
    completion_rate = 0
    if totals['total_goals'] > 0:
        completion_rate = round(totals['completed_goals'] / totals['total_goals'] * 100, 1)

    return {
        "totals": {
            "total": totals['total_goals'],
            "completed": totals['completed_goals'],
            "active": totals['total_goals'] - totals['completed_goals'],
            "overdue": totals['overdue_goals'],
            "due_this_week": totals['due_this_week'],
            "completion_rate": completion_rate
        },
        "by_category": by_category,
        "by_subject": by_subject,
        "recent_completions": recent_completions
    }


async def get_upcoming_deadlines(days: int = 14) -> List[dict]:
    """Get goals with upcoming deadlines."""
    return await db.fetch("""
        SELECT
            sg.*,
            gc.name as category_name,
            gc.color as category_color,
            gc.icon as category_icon,
            s.code as subject_code,
            sg.deadline - CURRENT_DATE as days_remaining,
            CASE
                WHEN sg.target_value > 0
                THEN ROUND(sg.current_value::NUMERIC / sg.target_value * 100, 1)
                ELSE 0
            END as progress_percent
        FROM study_goals sg
        LEFT JOIN goal_categories gc ON sg.category_id = gc.id
        LEFT JOIN subjects s ON sg.subject_id = s.id
        WHERE sg.completed = false
          AND sg.deadline IS NOT NULL
          AND sg.deadline <= CURRENT_DATE + $1
        ORDER BY sg.deadline, sg.priority
    """, days)
