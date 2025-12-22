"""
Personal Engineering OS - Database Connection
Async PostgreSQL with asyncpg
"""

import os
import json
from typing import Any, Optional, List

import asyncpg


def _default_database_url() -> str:
    """Choose a sensible default DB URL.

    - Local dev: Postgres on localhost
    - Docker/Compose: use the `db` service hostname

    Users can always override by setting DATABASE_URL.
    """
    # Heuristic: when running inside a container, /.dockerenv typically exists.
    in_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER") == "true"
    if in_docker:
        return "postgresql://postgres:postgres@db:5432/engineering_os"
    return "postgresql://postgres:postgres@localhost:5432/engineering_os"


def get_database_url() -> str:
    """Get the database URL from environment (evaluated at runtime)."""
    return os.getenv("DATABASE_URL") or _default_database_url()


class Database:
    """Async database connection manager."""
    
    def __init__(self):
        self._pool = None
    
    async def connect(self):
        """Create connection pool."""
        database_url = get_database_url()
        self._pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
        print("✓ Database connected")
    
    async def disconnect(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            print("✓ Database disconnected")
    
    async def fetch(self, query: str, *args) -> List[dict]:
        """Fetch multiple rows."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def fetch_one(self, query: str, *args) -> Optional[dict]:
        """Fetch single row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def execute(self, query: str, *args) -> str:
        """Execute query (INSERT, UPDATE, DELETE)."""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def execute_returning(self, query: str, *args) -> Optional[dict]:
        """Execute and return the affected row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None


# Global database instance
db = Database()


# ============================================
# SUBJECT QUERIES
# ============================================

async def get_all_subjects() -> List[dict]:
    return await db.fetch("SELECT * FROM subjects ORDER BY credits DESC, code")


async def get_subject(subject_id: int) -> Optional[dict]:
    return await db.fetch_one("SELECT * FROM subjects WHERE id = $1", subject_id)


async def get_subject_by_code(code: str) -> Optional[dict]:
    return await db.fetch_one("SELECT * FROM subjects WHERE code = $1", code)


async def create_subject(code: str, name: str, credits: int, type: str, color: str) -> dict:
    return await db.execute_returning(
        """INSERT INTO subjects (code, name, credits, type, color)
           VALUES ($1, $2, $3, $4, $5) RETURNING *""",
        code, name, credits, type, color
    )


# ============================================
# CHAPTER QUERIES
# ============================================

async def get_chapters_by_subject(subject_id: int) -> List[dict]:
    return await db.fetch(
        """SELECT c.*, cp.reading_status, cp.assignment_status, cp.mastery_level
           FROM chapters c
           LEFT JOIN chapter_progress cp ON c.id = cp.chapter_id
           WHERE c.subject_id = $1
           ORDER BY c.number""",
        subject_id
    )


async def get_chapter(chapter_id: int) -> Optional[dict]:
    return await db.fetch_one(
        """SELECT c.*, cp.reading_status, cp.assignment_status, cp.mastery_level,
                  cp.revision_count, cp.last_revised_at, cp.notes
           FROM chapters c
           LEFT JOIN chapter_progress cp ON c.id = cp.chapter_id
           WHERE c.id = $1""",
        chapter_id
    )


async def create_chapter(subject_id: int, number: int, title: str, folder_path: str) -> dict:
    chapter = await db.execute_returning(
        """INSERT INTO chapters (subject_id, number, title, folder_path)
           VALUES ($1, $2, $3, $4) RETURNING *""",
        subject_id, number, title, folder_path
    )
    await db.execute("INSERT INTO chapter_progress (chapter_id) VALUES ($1)", chapter['id'])
    return chapter


async def update_chapter_progress(chapter_id: int, **updates) -> dict:
    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), 1):
        set_parts.append(f"{k} = ${i}")
        values.append(v)
    values.append(chapter_id)
    set_clause = ", ".join(set_parts)
    return await db.execute_returning(
        f"UPDATE chapter_progress SET {set_clause}, updated_at = NOW() WHERE chapter_id = ${len(values)} RETURNING *",
        *values
    )


# ============================================
# TASK QUERIES
# ============================================

async def get_tasks_today() -> List[dict]:
    return await db.fetch(
        """SELECT t.*, s.code as subject_code, s.color
           FROM tasks t
           LEFT JOIN subjects s ON t.subject_id = s.id
           WHERE DATE(t.scheduled_start) = CURRENT_DATE
           ORDER BY t.scheduled_start"""
    )


async def create_task(data: dict) -> dict:
    return await db.execute_returning(
        """INSERT INTO tasks (title, description, subject_id, priority, 
                              duration_mins, scheduled_start, scheduled_end, is_deep_work)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *""",
        data['title'], data.get('description'), data.get('subject_id'),
        data.get('priority', 5), data.get('duration_mins', 60),
        data.get('scheduled_start'), data.get('scheduled_end'),
        data.get('is_deep_work', False)
    )


async def update_task(task_id: int, **updates) -> dict:
    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), 1):
        set_parts.append(f"{k} = ${i}")
        values.append(v)
    values.append(task_id)
    set_clause = ", ".join(set_parts)
    return await db.execute_returning(
        f"UPDATE tasks SET {set_clause}, updated_at = NOW() WHERE id = ${len(values)} RETURNING *",
        *values
    )


async def delete_task(task_id: int) -> bool:
    result = await db.execute("DELETE FROM tasks WHERE id = $1", task_id)
    return "DELETE 1" in result


# ============================================
# LAB REPORT QUERIES
# ============================================

async def get_lab_reports(status: str = None) -> List[dict]:
    if status:
        return await db.fetch(
            """SELECT lr.*, s.code as subject_code, s.credits
               FROM lab_reports lr
               JOIN subjects s ON lr.subject_id = s.id
               WHERE lr.status = $1
               ORDER BY lr.deadline, s.credits DESC""",
            status
        )
    return await db.fetch(
        """SELECT lr.*, s.code as subject_code, s.credits
           FROM lab_reports lr
           JOIN subjects s ON lr.subject_id = s.id
           ORDER BY lr.deadline, s.credits DESC"""
    )


async def create_lab_report(data: dict) -> dict:
    return await db.execute_returning(
        """INSERT INTO lab_reports (title, subject_id, deadline, notes)
           VALUES ($1, $2, $3, $4) RETURNING *""",
        data['title'], data['subject_id'], data['deadline'], data.get('notes')
    )


# ============================================
# REVISION QUERIES
# ============================================

async def get_pending_revisions() -> List[dict]:
    return await db.fetch(
        """SELECT rs.*, c.number as chapter_number, c.title as chapter_title,
                  s.code as subject_code, s.credits as subject_credits, s.color
           FROM revision_schedule rs
           JOIN chapters c ON rs.chapter_id = c.id
           JOIN subjects s ON c.subject_id = s.id
           WHERE rs.completed = false AND rs.due_date <= CURRENT_DATE + 1
           ORDER BY s.credits DESC, rs.due_date"""
    )


async def complete_revision(revision_id: int, points: int = 15) -> dict:
    result = await db.execute_returning(
        """UPDATE revision_schedule
           SET completed = true, completed_at = NOW(), points_earned = $1
           WHERE id = $2 RETURNING *""",
        points, revision_id
    )

    # Check for newly earned achievements after revision completion
    earned_achievements = []
    try:
        from achievements import check_achievements_after_action
        earned_achievements = await check_achievements_after_action("revision_complete")
    except Exception:
        pass  # Don't fail if achievement check fails

    if result:
        result['achievements_earned'] = earned_achievements

    return result


# ============================================
# STREAK QUERIES
# ============================================

async def get_streak() -> dict:
    streak = await db.fetch_one("SELECT * FROM user_streaks LIMIT 1")
    next_reward = await db.fetch_one(
        """SELECT * FROM rewards 
           WHERE unlocked = false 
           ORDER BY required_streak LIMIT 1"""
    )
    if streak and next_reward:
        streak['next_reward'] = next_reward['name']
        streak['points_to_next'] = next_reward['required_streak'] - streak['current_streak']
    return streak


async def add_points(points: int) -> dict:
    return await db.execute_returning(
        """UPDATE user_streaks 
           SET total_points = total_points + $1, updated_at = NOW()
           RETURNING *""",
        points
    )


# ============================================
# AI MEMORY QUERIES
# ============================================

async def get_ai_memory() -> List[dict]:
    return await db.fetch("SELECT * FROM ai_memory ORDER BY category, key")


async def save_ai_memory(category: str, key: str, value: str) -> dict:
    return await db.execute_returning(
        """INSERT INTO ai_memory (category, key, value)
           VALUES ($1, $2, $3)
           ON CONFLICT (category, key) 
           DO UPDATE SET value = $4, updated_at = NOW()
           RETURNING *""",
        category, key, value, value
    )


async def get_ai_guidelines(active_only: bool = True) -> List[dict]:
    if active_only:
        return await db.fetch("SELECT * FROM ai_guidelines WHERE active = true ORDER BY priority")
    return await db.fetch("SELECT * FROM ai_guidelines ORDER BY priority")


async def add_ai_guideline(rule: str, priority: int) -> dict:
    return await db.execute_returning(
        "INSERT INTO ai_guidelines (rule, priority) VALUES ($1, $2) RETURNING *",
        rule, priority
    )


# ============================================
# NOTIFICATION QUERIES
# ============================================

async def get_unread_notifications() -> List[dict]:
    return await db.fetch(
        """SELECT * FROM notifications 
           WHERE read = false AND dismissed = false
           ORDER BY due_at NULLS LAST, created_at DESC"""
    )


async def create_notification(type: str, title: str, message: str, due_at=None) -> dict:
    return await db.execute_returning(
        """INSERT INTO notifications (type, title, message, due_at)
           VALUES ($1, $2, $3, $4) RETURNING *""",
        type, title, message, due_at
    )


async def mark_notification_read(notification_id: int) -> dict:
    return await db.execute_returning(
        "UPDATE notifications SET read = true WHERE id = $1 RETURNING *",
        notification_id
    )


# ============================================
# FILE QUERIES
# ============================================

async def save_file_record(chapter_id: int, file_type: str, filename: str, 
                           filepath: str, mimetype: str, file_size: int) -> dict:
    return await db.execute_returning(
        """INSERT INTO chapter_files (chapter_id, file_type, filename, filepath, mimetype, file_size)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
        chapter_id, file_type, filename, filepath, mimetype, file_size
    )


async def get_chapter_files(chapter_id: int) -> List[dict]:
    return await db.fetch(
        "SELECT * FROM chapter_files WHERE chapter_id = $1 ORDER BY uploaded_at DESC",
        chapter_id
    )


# ============================================
# SYSTEM QUERIES
# ============================================

async def get_version() -> dict:
    return await db.fetch_one("SELECT * FROM version_metadata ORDER BY deployed_at DESC LIMIT 1")


async def log_system(level: str, message: str, context: dict = None) -> None:
    await db.execute(
        "INSERT INTO system_logs (level, message, context) VALUES ($1, $2, $3)",
        level, message, json.dumps(context) if context else None
    )
