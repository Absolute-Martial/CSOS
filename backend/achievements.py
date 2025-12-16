"""
Personal Engineering OS - Achievement & Gamification System
Track and award achievements to motivate students
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from enum import Enum

from database import db


# ============================================
# ENUMS
# ============================================

class AchievementRarity(str, Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class AchievementCategory(str, Enum):
    STREAK = "streak"
    STUDY = "study"
    GOAL = "goal"
    REVISION = "revision"
    SPECIAL = "special"


# ============================================
# PYDANTIC MODELS
# ============================================

class Achievement(BaseModel):
    id: int
    code: str
    name: str
    description: str
    icon: str
    category: AchievementCategory
    threshold_value: int
    points: int
    rarity: AchievementRarity


class UserAchievement(BaseModel):
    id: int
    achievement: Achievement
    earned_at: datetime
    progress_value: int
    is_complete: bool


class AchievementProgress(BaseModel):
    achievement: Achievement
    current_value: int
    target_value: int
    percentage: float
    is_complete: bool


# ============================================
# ACHIEVEMENT DEFINITIONS
# ============================================

# These match the achievement definitions that should exist in the database
ACHIEVEMENT_DEFINITIONS = {
    # Streak achievements
    "streak_3": {
        "name": "Getting Started",
        "description": "Maintain a 3-day study streak",
        "icon": "fire",
        "category": "streak",
        "threshold_value": 3,
        "points": 10,
        "rarity": "common"
    },
    "streak_7": {
        "name": "Week Warrior",
        "description": "Maintain a 7-day study streak",
        "icon": "flame",
        "category": "streak",
        "threshold_value": 7,
        "points": 25,
        "rarity": "common"
    },
    "streak_30": {
        "name": "Month Master",
        "description": "Maintain a 30-day study streak",
        "icon": "calendar-check",
        "category": "streak",
        "threshold_value": 30,
        "points": 100,
        "rarity": "rare"
    },
    "streak_100": {
        "name": "Centurion",
        "description": "Maintain a 100-day study streak",
        "icon": "crown",
        "category": "streak",
        "threshold_value": 100,
        "points": 500,
        "rarity": "legendary"
    },
    # Study achievements
    "deep_work_1": {
        "name": "Deep Diver",
        "description": "Complete your first 90+ minute deep work session",
        "icon": "brain",
        "category": "study",
        "threshold_value": 1,
        "points": 15,
        "rarity": "common"
    },
    "deep_work_10": {
        "name": "Focus Master",
        "description": "Complete 10 deep work sessions",
        "icon": "target",
        "category": "study",
        "threshold_value": 10,
        "points": 50,
        "rarity": "rare"
    },
    # Goal achievements
    "tasks_10": {
        "name": "Task Tackler",
        "description": "Complete 10 tasks",
        "icon": "check-square",
        "category": "goal",
        "threshold_value": 10,
        "points": 10,
        "rarity": "common"
    },
    "tasks_100": {
        "name": "Productivity Pro",
        "description": "Complete 100 tasks",
        "icon": "trophy",
        "category": "goal",
        "threshold_value": 100,
        "points": 100,
        "rarity": "rare"
    },
    # Revision achievements
    "revision_master": {
        "name": "Memory Champion",
        "description": "Complete all revisions for 5 chapters",
        "icon": "book-open",
        "category": "revision",
        "threshold_value": 5,
        "points": 30,
        "rarity": "rare"
    },
    # Special achievements
    "early_bird": {
        "name": "Early Bird",
        "description": "Start studying before 7 AM",
        "icon": "sunrise",
        "category": "special",
        "threshold_value": 1,
        "points": 20,
        "rarity": "common"
    },
    "night_owl": {
        "name": "Night Owl",
        "description": "Have a productive study session after midnight",
        "icon": "moon",
        "category": "special",
        "threshold_value": 1,
        "points": 20,
        "rarity": "common"
    },
    "perfectionist": {
        "name": "Perfectionist",
        "description": "Complete all tasks for 7 consecutive days",
        "icon": "star",
        "category": "special",
        "threshold_value": 7,
        "points": 75,
        "rarity": "epic"
    }
}


# ============================================
# DATABASE INITIALIZATION
# ============================================

async def ensure_achievement_tables() -> None:
    """Create achievement tables if they don't exist."""

    # Create achievement_definitions table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS achievement_definitions (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            icon VARCHAR(50) NOT NULL,
            category VARCHAR(50) NOT NULL,
            threshold_value INTEGER NOT NULL DEFAULT 1,
            points INTEGER NOT NULL DEFAULT 0,
            rarity VARCHAR(20) NOT NULL DEFAULT 'common',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Create user_achievements table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            id SERIAL PRIMARY KEY,
            achievement_id INTEGER NOT NULL REFERENCES achievement_definitions(id) ON DELETE CASCADE,
            progress_value INTEGER DEFAULT 0,
            is_complete BOOLEAN DEFAULT FALSE,
            earned_at TIMESTAMP WITH TIME ZONE,
            notified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(achievement_id)
        )
    """)

    # Create progress_snapshots table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS progress_snapshots (
            id SERIAL PRIMARY KEY,
            snapshot_date DATE NOT NULL UNIQUE,
            total_study_mins INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            revisions_completed INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            achievement_points INTEGER DEFAULT 0,
            deep_work_sessions INTEGER DEFAULT 0,
            goals_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Create indexes
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_achievements_complete
        ON user_achievements(is_complete, earned_at)
    """)

    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_progress_snapshots_date
        ON progress_snapshots(snapshot_date DESC)
    """)


async def seed_achievement_definitions() -> int:
    """Seed achievement definitions into database. Returns count of inserted."""
    inserted = 0

    for code, data in ACHIEVEMENT_DEFINITIONS.items():
        existing = await db.fetch_one(
            "SELECT id FROM achievement_definitions WHERE code = $1",
            code
        )

        if not existing:
            await db.execute("""
                INSERT INTO achievement_definitions
                (code, name, description, icon, category, threshold_value, points, rarity)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, code, data["name"], data["description"], data["icon"],
                data["category"], data["threshold_value"], data["points"], data["rarity"])
            inserted += 1

    return inserted


# ============================================
# ACHIEVEMENT CHECKER
# ============================================

class AchievementChecker:
    """Checks and awards achievements based on user activity."""

    async def check_all(self) -> List[Dict[str, Any]]:
        """Check all achievement conditions and return newly earned ones."""
        earned = []

        earned.extend(await self.check_streak_achievements())
        earned.extend(await self.check_study_achievements())
        earned.extend(await self.check_task_achievements())
        earned.extend(await self.check_revision_achievements())
        earned.extend(await self.check_special_achievements())

        return earned

    async def check_streak_achievements(self) -> List[Dict[str, Any]]:
        """Check streak-based achievements."""
        earned = []

        # Get current streak
        streak_data = await db.fetch_one(
            "SELECT current_streak, longest_streak FROM user_streaks LIMIT 1"
        )

        if not streak_data:
            return earned

        current_streak = streak_data.get("current_streak", 0)
        longest_streak = max(current_streak, streak_data.get("longest_streak", 0))

        # Check streak thresholds
        streak_achievements = [
            ("streak_3", 3),
            ("streak_7", 7),
            ("streak_30", 30),
            ("streak_100", 100)
        ]

        for code, threshold in streak_achievements:
            if longest_streak >= threshold:
                result = await self._award_achievement(code, longest_streak)
                if result:
                    earned.append(result)
            else:
                # Update progress
                await self._update_progress(code, current_streak)

        return earned

    async def check_study_achievements(self) -> List[Dict[str, Any]]:
        """Check study session achievements."""
        earned = []

        # Count deep work sessions (90+ mins = 5400 seconds)
        deep_work_count = await db.fetch_one("""
            SELECT COUNT(*) as count FROM study_sessions
            WHERE is_deep_work = true AND stopped_at IS NOT NULL
        """)

        count = deep_work_count.get("count", 0) if deep_work_count else 0

        # Check deep work achievements
        if count >= 1:
            result = await self._award_achievement("deep_work_1", count)
            if result:
                earned.append(result)
        else:
            await self._update_progress("deep_work_1", count)

        if count >= 10:
            result = await self._award_achievement("deep_work_10", count)
            if result:
                earned.append(result)
        else:
            await self._update_progress("deep_work_10", count)

        return earned

    async def check_task_achievements(self) -> List[Dict[str, Any]]:
        """Check task completion achievements."""
        earned = []

        # Count completed tasks
        task_count = await db.fetch_one("""
            SELECT COUNT(*) as count FROM tasks
            WHERE status = 'completed'
        """)

        count = task_count.get("count", 0) if task_count else 0

        # Check task achievements
        if count >= 10:
            result = await self._award_achievement("tasks_10", count)
            if result:
                earned.append(result)
        else:
            await self._update_progress("tasks_10", count)

        if count >= 100:
            result = await self._award_achievement("tasks_100", count)
            if result:
                earned.append(result)
        else:
            await self._update_progress("tasks_100", count)

        return earned

    async def check_revision_achievements(self) -> List[Dict[str, Any]]:
        """Check revision completion achievements."""
        earned = []

        # Count chapters with all revisions completed
        # A chapter typically has 3 revisions (7, 14, 21 days)
        completed_chapters = await db.fetch_one("""
            SELECT COUNT(DISTINCT chapter_id) as count
            FROM (
                SELECT chapter_id
                FROM revision_schedule
                GROUP BY chapter_id
                HAVING COUNT(*) = SUM(CASE WHEN completed THEN 1 ELSE 0 END)
                   AND COUNT(*) >= 3
            ) as fully_revised
        """)

        count = completed_chapters.get("count", 0) if completed_chapters else 0

        if count >= 5:
            result = await self._award_achievement("revision_master", count)
            if result:
                earned.append(result)
        else:
            await self._update_progress("revision_master", count)

        return earned

    async def check_special_achievements(self) -> List[Dict[str, Any]]:
        """Check special/time-based achievements."""
        earned = []

        # Early bird: Study started before 7 AM
        early_sessions = await db.fetch_one("""
            SELECT COUNT(*) as count FROM study_sessions
            WHERE EXTRACT(HOUR FROM started_at) < 7
              AND stopped_at IS NOT NULL
              AND duration_seconds >= 1800
        """)

        if early_sessions and early_sessions.get("count", 0) >= 1:
            result = await self._award_achievement("early_bird", early_sessions["count"])
            if result:
                earned.append(result)

        # Night owl: Productive study after midnight (00:00-04:00)
        night_sessions = await db.fetch_one("""
            SELECT COUNT(*) as count FROM study_sessions
            WHERE EXTRACT(HOUR FROM started_at) BETWEEN 0 AND 4
              AND stopped_at IS NOT NULL
              AND duration_seconds >= 1800
        """)

        if night_sessions and night_sessions.get("count", 0) >= 1:
            result = await self._award_achievement("night_owl", night_sessions["count"])
            if result:
                earned.append(result)

        # Perfectionist: All tasks completed for 7 consecutive days
        perfect_days = await self._count_perfect_days()
        if perfect_days >= 7:
            result = await self._award_achievement("perfectionist", perfect_days)
            if result:
                earned.append(result)
        else:
            await self._update_progress("perfectionist", perfect_days)

        return earned

    async def _count_perfect_days(self) -> int:
        """Count consecutive days where all tasks were completed."""
        # Get daily task completion rates for the last 30 days
        daily_completion = await db.fetch("""
            SELECT
                DATE(scheduled_start) as task_date,
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks
            FROM tasks
            WHERE scheduled_start >= CURRENT_DATE - INTERVAL '30 days'
              AND scheduled_start < CURRENT_DATE + INTERVAL '1 day'
            GROUP BY DATE(scheduled_start)
            ORDER BY task_date DESC
        """)

        if not daily_completion:
            return 0

        consecutive = 0
        today = date.today()

        for i, day_data in enumerate(daily_completion):
            expected_date = today - timedelta(days=i)
            task_date = day_data.get("task_date")

            if task_date and task_date == expected_date:
                total = day_data.get("total_tasks", 0)
                completed = day_data.get("completed_tasks", 0)

                if total > 0 and completed == total:
                    consecutive += 1
                else:
                    break
            else:
                break

        return consecutive

    async def _award_achievement(
        self,
        achievement_code: str,
        progress_value: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Award an achievement if not already earned."""

        # Check if already earned
        existing = await db.fetch_one("""
            SELECT ua.id, ua.is_complete
            FROM user_achievements ua
            JOIN achievement_definitions ad ON ua.achievement_id = ad.id
            WHERE ad.code = $1
        """, achievement_code)

        if existing and existing.get("is_complete"):
            return None

        # Get achievement definition
        achievement = await db.fetch_one("""
            SELECT * FROM achievement_definitions WHERE code = $1
        """, achievement_code)

        if not achievement:
            return None

        now = datetime.now()

        if existing:
            # Update existing record to complete
            await db.execute("""
                UPDATE user_achievements
                SET progress_value = $1, is_complete = true,
                    earned_at = $2, notified = false, updated_at = $2
                WHERE id = $3
            """, progress_value, now, existing["id"])
        else:
            # Insert new record
            await db.execute("""
                INSERT INTO user_achievements
                (achievement_id, progress_value, is_complete, earned_at, notified)
                VALUES ($1, $2, true, $3, false)
            """, achievement["id"], progress_value, now)

        # Add points to user
        await db.execute("""
            UPDATE user_streaks
            SET total_points = total_points + $1, updated_at = NOW()
        """, achievement["points"])

        return {
            "code": achievement_code,
            "name": achievement["name"],
            "description": achievement["description"],
            "icon": achievement["icon"],
            "category": achievement["category"],
            "points": achievement["points"],
            "rarity": achievement["rarity"],
            "earned_at": now.isoformat()
        }

    async def _update_progress(
        self,
        achievement_code: str,
        progress_value: int
    ) -> None:
        """Update progress toward an incomplete achievement."""

        # Get achievement definition
        achievement = await db.fetch_one("""
            SELECT id FROM achievement_definitions WHERE code = $1
        """, achievement_code)

        if not achievement:
            return

        # Upsert progress record
        await db.execute("""
            INSERT INTO user_achievements (achievement_id, progress_value, is_complete)
            VALUES ($1, $2, false)
            ON CONFLICT (achievement_id) DO UPDATE SET
                progress_value = GREATEST(user_achievements.progress_value, $2),
                updated_at = NOW()
            WHERE user_achievements.is_complete = false
        """, achievement["id"], progress_value)


# ============================================
# CRUD OPERATIONS
# ============================================

async def get_all_achievements() -> List[Dict[str, Any]]:
    """Get all achievement definitions."""
    return await db.fetch("""
        SELECT * FROM achievement_definitions
        ORDER BY
            CASE rarity
                WHEN 'common' THEN 1
                WHEN 'rare' THEN 2
                WHEN 'epic' THEN 3
                WHEN 'legendary' THEN 4
            END,
            category, threshold_value
    """)


async def get_user_achievements(include_incomplete: bool = False) -> List[Dict[str, Any]]:
    """Get user's achievements with details."""
    if include_incomplete:
        return await db.fetch("""
            SELECT
                ua.id,
                ua.progress_value,
                ua.is_complete,
                ua.earned_at,
                ua.notified,
                ad.code,
                ad.name,
                ad.description,
                ad.icon,
                ad.category,
                ad.threshold_value,
                ad.points,
                ad.rarity,
                CASE
                    WHEN ad.threshold_value > 0
                    THEN ROUND(ua.progress_value::NUMERIC / ad.threshold_value * 100, 1)
                    ELSE 0
                END as progress_percent
            FROM user_achievements ua
            JOIN achievement_definitions ad ON ua.achievement_id = ad.id
            ORDER BY ua.is_complete DESC, ua.earned_at DESC NULLS LAST
        """)

    return await db.fetch("""
        SELECT
            ua.id,
            ua.progress_value,
            ua.is_complete,
            ua.earned_at,
            ua.notified,
            ad.code,
            ad.name,
            ad.description,
            ad.icon,
            ad.category,
            ad.threshold_value,
            ad.points,
            ad.rarity
        FROM user_achievements ua
        JOIN achievement_definitions ad ON ua.achievement_id = ad.id
        WHERE ua.is_complete = true
        ORDER BY ua.earned_at DESC
    """)


async def get_achievement_progress() -> List[Dict[str, Any]]:
    """Get progress toward all achievements."""

    # First, ensure all achievements have a user_achievements record
    await db.execute("""
        INSERT INTO user_achievements (achievement_id, progress_value, is_complete)
        SELECT id, 0, false FROM achievement_definitions
        WHERE id NOT IN (SELECT achievement_id FROM user_achievements)
    """)

    return await db.fetch("""
        SELECT
            ad.code,
            ad.name,
            ad.description,
            ad.icon,
            ad.category,
            ad.threshold_value as target_value,
            ad.points,
            ad.rarity,
            COALESCE(ua.progress_value, 0) as current_value,
            COALESCE(ua.is_complete, false) as is_complete,
            ua.earned_at,
            CASE
                WHEN ad.threshold_value > 0
                THEN ROUND(COALESCE(ua.progress_value, 0)::NUMERIC / ad.threshold_value * 100, 1)
                ELSE 0
            END as percentage
        FROM achievement_definitions ad
        LEFT JOIN user_achievements ua ON ad.id = ua.achievement_id
        ORDER BY
            ua.is_complete DESC,
            CASE ad.rarity
                WHEN 'common' THEN 1
                WHEN 'rare' THEN 2
                WHEN 'epic' THEN 3
                WHEN 'legendary' THEN 4
            END,
            ad.category
    """)


async def get_total_points() -> int:
    """Get user's total achievement points."""
    result = await db.fetch_one("""
        SELECT COALESCE(SUM(ad.points), 0) as total_points
        FROM user_achievements ua
        JOIN achievement_definitions ad ON ua.achievement_id = ad.id
        WHERE ua.is_complete = true
    """)

    return result.get("total_points", 0) if result else 0


async def get_achievements_by_category(category: str) -> List[Dict[str, Any]]:
    """Get achievements filtered by category."""
    return await db.fetch("""
        SELECT
            ad.*,
            ua.progress_value,
            ua.is_complete,
            ua.earned_at,
            CASE
                WHEN ad.threshold_value > 0
                THEN ROUND(COALESCE(ua.progress_value, 0)::NUMERIC / ad.threshold_value * 100, 1)
                ELSE 0
            END as progress_percent
        FROM achievement_definitions ad
        LEFT JOIN user_achievements ua ON ad.id = ua.achievement_id
        WHERE ad.category = $1
        ORDER BY ua.is_complete DESC, ad.threshold_value
    """, category)


async def get_recent_achievements(days: int = 7) -> List[Dict[str, Any]]:
    """Get recently earned achievements."""
    return await db.fetch("""
        SELECT
            ua.id,
            ua.earned_at,
            ad.code,
            ad.name,
            ad.description,
            ad.icon,
            ad.category,
            ad.points,
            ad.rarity
        FROM user_achievements ua
        JOIN achievement_definitions ad ON ua.achievement_id = ad.id
        WHERE ua.is_complete = true
          AND ua.earned_at >= NOW() - INTERVAL '%s days'
        ORDER BY ua.earned_at DESC
    """ % days)


async def get_unnotified_achievements() -> List[Dict[str, Any]]:
    """Get achievements that haven't been notified to the user."""
    return await db.fetch("""
        SELECT
            ua.id,
            ua.earned_at,
            ad.code,
            ad.name,
            ad.description,
            ad.icon,
            ad.category,
            ad.points,
            ad.rarity
        FROM user_achievements ua
        JOIN achievement_definitions ad ON ua.achievement_id = ad.id
        WHERE ua.is_complete = true AND ua.notified = false
        ORDER BY ua.earned_at DESC
    """)


async def mark_achievements_notified(achievement_ids: List[int]) -> None:
    """Mark achievements as notified."""
    if not achievement_ids:
        return

    placeholders = ", ".join(f"${i+1}" for i in range(len(achievement_ids)))
    await db.execute(f"""
        UPDATE user_achievements
        SET notified = true
        WHERE id IN ({placeholders})
    """, *achievement_ids)


async def get_achievement_summary() -> Dict[str, Any]:
    """Get summary statistics for achievements."""

    # Total counts
    totals = await db.fetch_one("""
        SELECT
            COUNT(*) as total_achievements,
            SUM(CASE WHEN ua.is_complete THEN 1 ELSE 0 END) as earned_count
        FROM achievement_definitions ad
        LEFT JOIN user_achievements ua ON ad.id = ua.achievement_id
    """)

    # By category
    by_category = await db.fetch("""
        SELECT
            ad.category,
            COUNT(*) as total,
            SUM(CASE WHEN ua.is_complete THEN 1 ELSE 0 END) as earned
        FROM achievement_definitions ad
        LEFT JOIN user_achievements ua ON ad.id = ua.achievement_id
        GROUP BY ad.category
        ORDER BY ad.category
    """)

    # By rarity
    by_rarity = await db.fetch("""
        SELECT
            ad.rarity,
            COUNT(*) as total,
            SUM(CASE WHEN ua.is_complete THEN 1 ELSE 0 END) as earned
        FROM achievement_definitions ad
        LEFT JOIN user_achievements ua ON ad.id = ua.achievement_id
        GROUP BY ad.rarity
    """)

    # Points
    points = await get_total_points()

    # Recent
    recent = await get_recent_achievements(7)

    total = totals.get("total_achievements", 0) if totals else 0
    earned = totals.get("earned_count", 0) if totals else 0

    return {
        "total_achievements": total,
        "earned_achievements": earned,
        "completion_percent": round(earned / total * 100, 1) if total > 0 else 0,
        "total_points": points,
        "by_category": by_category,
        "by_rarity": by_rarity,
        "recent": recent
    }


# ============================================
# PROGRESS TRACKING
# ============================================

async def create_progress_snapshot() -> Dict[str, Any]:
    """Create daily progress snapshot for visualization."""
    today = date.today()

    # Get today's study minutes
    study_data = await db.fetch_one("""
        SELECT
            COALESCE(SUM(duration_seconds) / 60, 0) as study_mins,
            COUNT(CASE WHEN is_deep_work THEN 1 END) as deep_work_sessions
        FROM study_sessions
        WHERE DATE(started_at) = $1 AND stopped_at IS NOT NULL
    """, today)

    study_mins = study_data.get("study_mins", 0) if study_data else 0
    deep_work_sessions = study_data.get("deep_work_sessions", 0) if study_data else 0

    # Get tasks completed today
    tasks_data = await db.fetch_one("""
        SELECT COUNT(*) as count FROM tasks
        WHERE status = 'completed' AND DATE(updated_at) = $1
    """, today)

    tasks_completed = tasks_data.get("count", 0) if tasks_data else 0

    # Get revisions completed today
    revisions_data = await db.fetch_one("""
        SELECT COUNT(*) as count FROM revision_schedule
        WHERE completed = true AND DATE(completed_at) = $1
    """, today)

    revisions_completed = revisions_data.get("count", 0) if revisions_data else 0

    # Get goals completed today
    goals_data = await db.fetch_one("""
        SELECT COUNT(*) as count FROM study_goals
        WHERE completed = true AND DATE(completed_at) = $1
    """, today)

    goals_completed = goals_data.get("count", 0) if goals_data else 0

    # Get streak
    streak_data = await db.fetch_one(
        "SELECT current_streak FROM user_streaks LIMIT 1"
    )
    streak = streak_data.get("current_streak", 0) if streak_data else 0

    # Get total achievement points
    points = await get_total_points()

    # Upsert snapshot
    await db.execute("""
        INSERT INTO progress_snapshots
        (snapshot_date, total_study_mins, tasks_completed, revisions_completed,
         streak_count, achievement_points, deep_work_sessions, goals_completed)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (snapshot_date) DO UPDATE SET
            total_study_mins = $2,
            tasks_completed = $3,
            revisions_completed = $4,
            streak_count = $5,
            achievement_points = $6,
            deep_work_sessions = $7,
            goals_completed = $8,
            updated_at = NOW()
    """, today, study_mins, tasks_completed, revisions_completed,
        streak, points, deep_work_sessions, goals_completed)

    return {
        "date": today.isoformat(),
        "study_mins": study_mins,
        "tasks_completed": tasks_completed,
        "revisions_completed": revisions_completed,
        "goals_completed": goals_completed,
        "streak": streak,
        "points": points,
        "deep_work_sessions": deep_work_sessions
    }


async def get_progress_history(days: int = 30) -> List[Dict[str, Any]]:
    """Get progress snapshots for visualization."""
    return await db.fetch("""
        SELECT
            snapshot_date,
            total_study_mins,
            tasks_completed,
            revisions_completed,
            streak_count,
            achievement_points,
            deep_work_sessions,
            goals_completed
        FROM progress_snapshots
        WHERE snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY snapshot_date
    """ % days)


async def get_growth_stats() -> Dict[str, Any]:
    """Calculate growth statistics."""

    # Get current week stats
    this_week = await db.fetch_one("""
        SELECT
            COALESCE(SUM(total_study_mins), 0) as study_mins,
            COALESCE(SUM(tasks_completed), 0) as tasks,
            COALESCE(SUM(revisions_completed), 0) as revisions,
            COALESCE(SUM(deep_work_sessions), 0) as deep_work,
            COALESCE(SUM(goals_completed), 0) as goals
        FROM progress_snapshots
        WHERE snapshot_date >= DATE_TRUNC('week', CURRENT_DATE)
    """)

    # Get last week stats
    last_week = await db.fetch_one("""
        SELECT
            COALESCE(SUM(total_study_mins), 0) as study_mins,
            COALESCE(SUM(tasks_completed), 0) as tasks,
            COALESCE(SUM(revisions_completed), 0) as revisions,
            COALESCE(SUM(deep_work_sessions), 0) as deep_work,
            COALESCE(SUM(goals_completed), 0) as goals
        FROM progress_snapshots
        WHERE snapshot_date >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '7 days'
          AND snapshot_date < DATE_TRUNC('week', CURRENT_DATE)
    """)

    # Get current month stats
    this_month = await db.fetch_one("""
        SELECT
            COALESCE(SUM(total_study_mins), 0) as study_mins,
            COALESCE(SUM(tasks_completed), 0) as tasks,
            COALESCE(SUM(revisions_completed), 0) as revisions,
            COALESCE(SUM(deep_work_sessions), 0) as deep_work,
            COALESCE(SUM(goals_completed), 0) as goals
        FROM progress_snapshots
        WHERE snapshot_date >= DATE_TRUNC('month', CURRENT_DATE)
    """)

    # Get last month stats
    last_month = await db.fetch_one("""
        SELECT
            COALESCE(SUM(total_study_mins), 0) as study_mins,
            COALESCE(SUM(tasks_completed), 0) as tasks,
            COALESCE(SUM(revisions_completed), 0) as revisions,
            COALESCE(SUM(deep_work_sessions), 0) as deep_work,
            COALESCE(SUM(goals_completed), 0) as goals
        FROM progress_snapshots
        WHERE snapshot_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1 month'
          AND snapshot_date < DATE_TRUNC('month', CURRENT_DATE)
    """)

    # All-time stats
    all_time = await db.fetch_one("""
        SELECT
            COALESCE(SUM(total_study_mins), 0) as study_mins,
            COALESCE(SUM(tasks_completed), 0) as tasks,
            COALESCE(SUM(revisions_completed), 0) as revisions,
            COALESCE(SUM(deep_work_sessions), 0) as deep_work,
            COALESCE(SUM(goals_completed), 0) as goals,
            COUNT(*) as total_days
        FROM progress_snapshots
    """)

    def calc_growth(current: int, previous: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round((current - previous) / previous * 100, 1)

    tw = this_week or {}
    lw = last_week or {}
    tm = this_month or {}
    lm = last_month or {}
    at = all_time or {}

    return {
        "weekly": {
            "current": {
                "study_mins": tw.get("study_mins", 0),
                "tasks": tw.get("tasks", 0),
                "revisions": tw.get("revisions", 0),
                "deep_work": tw.get("deep_work", 0),
                "goals": tw.get("goals", 0)
            },
            "previous": {
                "study_mins": lw.get("study_mins", 0),
                "tasks": lw.get("tasks", 0),
                "revisions": lw.get("revisions", 0),
                "deep_work": lw.get("deep_work", 0),
                "goals": lw.get("goals", 0)
            },
            "growth": {
                "study_mins": calc_growth(tw.get("study_mins", 0), lw.get("study_mins", 0)),
                "tasks": calc_growth(tw.get("tasks", 0), lw.get("tasks", 0)),
                "revisions": calc_growth(tw.get("revisions", 0), lw.get("revisions", 0)),
                "deep_work": calc_growth(tw.get("deep_work", 0), lw.get("deep_work", 0)),
                "goals": calc_growth(tw.get("goals", 0), lw.get("goals", 0))
            }
        },
        "monthly": {
            "current": {
                "study_mins": tm.get("study_mins", 0),
                "tasks": tm.get("tasks", 0),
                "revisions": tm.get("revisions", 0),
                "deep_work": tm.get("deep_work", 0),
                "goals": tm.get("goals", 0)
            },
            "previous": {
                "study_mins": lm.get("study_mins", 0),
                "tasks": lm.get("tasks", 0),
                "revisions": lm.get("revisions", 0),
                "deep_work": lm.get("deep_work", 0),
                "goals": lm.get("goals", 0)
            },
            "growth": {
                "study_mins": calc_growth(tm.get("study_mins", 0), lm.get("study_mins", 0)),
                "tasks": calc_growth(tm.get("tasks", 0), lm.get("tasks", 0)),
                "revisions": calc_growth(tm.get("revisions", 0), lm.get("revisions", 0)),
                "deep_work": calc_growth(tm.get("deep_work", 0), lm.get("deep_work", 0)),
                "goals": calc_growth(tm.get("goals", 0), lm.get("goals", 0))
            }
        },
        "all_time": {
            "study_hours": round(at.get("study_mins", 0) / 60, 1),
            "tasks": at.get("tasks", 0),
            "revisions": at.get("revisions", 0),
            "deep_work_sessions": at.get("deep_work", 0),
            "goals": at.get("goals", 0),
            "total_days_tracked": at.get("total_days", 0)
        }
    }


# ============================================
# INTEGRATION HELPERS
# ============================================

async def check_achievements_after_action(action_type: str) -> List[Dict[str, Any]]:
    """
    Check achievements after a specific action.
    Call this from timer.py, goals.py, etc. after relevant actions.

    Args:
        action_type: One of 'study_session', 'task_complete', 'revision_complete', 'goal_complete'

    Returns:
        List of newly earned achievements
    """
    checker = AchievementChecker()
    earned = []

    if action_type == "study_session":
        earned.extend(await checker.check_study_achievements())
        earned.extend(await checker.check_streak_achievements())
        earned.extend(await checker.check_special_achievements())

    elif action_type == "task_complete":
        earned.extend(await checker.check_task_achievements())
        earned.extend(await checker.check_special_achievements())

    elif action_type == "revision_complete":
        earned.extend(await checker.check_revision_achievements())
        earned.extend(await checker.check_streak_achievements())

    elif action_type == "goal_complete":
        earned.extend(await checker.check_task_achievements())  # Goals count as task-like

    else:
        # Full check
        earned = await checker.check_all()

    return earned


async def initialize_achievements() -> Dict[str, Any]:
    """
    Initialize the achievement system.
    Call this on server startup.
    """
    await ensure_achievement_tables()
    inserted = await seed_achievement_definitions()

    return {
        "tables_created": True,
        "definitions_seeded": inserted,
        "message": f"Achievement system initialized. {inserted} new definitions added."
    }
