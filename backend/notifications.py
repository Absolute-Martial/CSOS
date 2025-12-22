"""
Personal Engineering OS - Proactive Notification System
AI-driven notifications for reminders, achievements, suggestions, and warnings
"""

import asyncio
import json
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Set
from enum import Enum

from database import db


# ============================================
# NOTIFICATION TYPES AND MODELS
# ============================================

class NotificationType(str, Enum):
    REMINDER = "reminder"           # Deadline reminders, revision due
    ACHIEVEMENT = "achievement"     # Unlocked achievements
    SUGGESTION = "suggestion"       # Break suggestions, optimization tips
    WARNING = "warning"             # Overwork warnings, streak at risk
    MOTIVATION = "motivation"       # Daily motivation, streak celebration


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# Connected WebSocket clients
connected_clients: Set = set()


# ============================================
# DATABASE OPERATIONS
# ============================================

async def create_notification(
    notif_type: str,
    title: str,
    message: str,
    priority: str = "normal",
    action_url: Optional[str] = None,
    action_label: Optional[str] = None,
    scheduled_for: Optional[datetime] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    dedup_key: Optional[str] = None
) -> Optional[Dict]:
    """
    Create a new notification in the database.
    Uses dedup_key to prevent duplicate notifications.
    """
    # Check for duplicates if dedup_key provided
    if dedup_key:
        existing = await db.fetch_one("""
            SELECT id FROM proactive_notifications
            WHERE dedup_key = $1 AND dismissed = false
        """, dedup_key)
        if existing:
            return None  # Already exists, skip

    notification = await db.execute_returning("""
        INSERT INTO proactive_notifications (
            type, title, message, priority,
            action_url, action_label, scheduled_for,
            reference_type, reference_id, dedup_key
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING *
    """,
        notif_type, title, message, priority,
        action_url, action_label, scheduled_for,
        reference_type, reference_id, dedup_key
    )

    return notification


async def get_pending_notifications() -> List[Dict]:
    """Get all unsent notifications that should be sent now."""
    return await db.fetch("""
        SELECT * FROM proactive_notifications
        WHERE sent = false
          AND dismissed = false
          AND (scheduled_for IS NULL OR scheduled_for <= NOW())
        ORDER BY
            CASE priority
                WHEN 'urgent' THEN 1
                WHEN 'high' THEN 2
                WHEN 'normal' THEN 3
                WHEN 'low' THEN 4
            END,
            created_at ASC
    """)


async def mark_notification_sent(notification_id: int) -> Dict:
    """Mark notification as sent."""
    return await db.execute_returning("""
        UPDATE proactive_notifications
        SET sent = true, sent_at = NOW()
        WHERE id = $1
        RETURNING *
    """, notification_id)


async def mark_notification_read(notification_id: int) -> Dict:
    """Mark notification as read by user."""
    return await db.execute_returning("""
        UPDATE proactive_notifications
        SET read = true, read_at = NOW()
        WHERE id = $1
        RETURNING *
    """, notification_id)


async def dismiss_notification(notification_id: int) -> Dict:
    """Dismiss a notification (user wants to hide it)."""
    return await db.execute_returning("""
        UPDATE proactive_notifications
        SET dismissed = true
        WHERE id = $1
        RETURNING *
    """, notification_id)


async def get_user_notifications(
    limit: int = 20,
    unread_only: bool = False,
    offset: int = 0
) -> List[Dict]:
    """Get user's notifications for display."""
    if unread_only:
        return await db.fetch("""
            SELECT * FROM proactive_notifications
            WHERE dismissed = false AND read = false
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)

    return await db.fetch("""
        SELECT * FROM proactive_notifications
        WHERE dismissed = false
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
    """, limit, offset)


async def get_notification_count() -> Dict:
    """Get notification counts."""
    result = await db.fetch_one("""
        SELECT
            COUNT(*) FILTER (WHERE read = false AND dismissed = false) as unread,
            COUNT(*) FILTER (WHERE dismissed = false) as total
        FROM proactive_notifications
    """)
    return {
        "unread": result["unread"] or 0,
        "total": result["total"] or 0
    }


# ============================================
# NOTIFICATION PREFERENCES
# ============================================

async def get_notification_preferences() -> List[Dict]:
    """Get user notification preferences."""
    return await db.fetch("""
        SELECT * FROM notification_preferences
        ORDER BY notification_type
    """)


async def update_notification_preference(
    notification_type: str,
    enabled: Optional[bool] = None,
    quiet_hours_start: Optional[str] = None,
    quiet_hours_end: Optional[str] = None,
    frequency_limit: Optional[int] = None
) -> Dict:
    """Update notification preferences for a type."""
    # Build update query dynamically
    updates = []
    values = []
    param_idx = 1

    if enabled is not None:
        updates.append(f"enabled = ${param_idx}")
        values.append(enabled)
        param_idx += 1

    if quiet_hours_start is not None:
        updates.append(f"quiet_hours_start = ${param_idx}")
        values.append(quiet_hours_start)
        param_idx += 1

    if quiet_hours_end is not None:
        updates.append(f"quiet_hours_end = ${param_idx}")
        values.append(quiet_hours_end)
        param_idx += 1

    if frequency_limit is not None:
        updates.append(f"frequency_limit = ${param_idx}")
        values.append(frequency_limit)
        param_idx += 1

    if not updates:
        return {"error": "No updates provided"}

    values.append(notification_type)

    result = await db.execute_returning(f"""
        INSERT INTO notification_preferences (notification_type, {', '.join(u.split(' = ')[0] for u in updates)})
        VALUES (${param_idx}, {', '.join(f'${i+1}' for i in range(len(values)-1))})
        ON CONFLICT (notification_type) DO UPDATE SET
            {', '.join(updates)},
            updated_at = NOW()
        RETURNING *
    """, *values)

    return result


async def is_notification_allowed(notification_type: str) -> bool:
    """Check if notification type is allowed based on preferences."""
    pref = await db.fetch_one("""
        SELECT enabled, quiet_hours_start, quiet_hours_end, frequency_limit
        FROM notification_preferences
        WHERE notification_type = $1
    """, notification_type)

    if not pref:
        return True  # Default: allow all

    if not pref["enabled"]:
        return False

    # Check quiet hours
    if pref["quiet_hours_start"] and pref["quiet_hours_end"]:
        now = datetime.now().time()
        try:
            quiet_start = datetime.strptime(pref["quiet_hours_start"], "%H:%M").time()
            quiet_end = datetime.strptime(pref["quiet_hours_end"], "%H:%M").time()

            # Handle overnight quiet hours (e.g., 22:00 to 07:00)
            if quiet_start > quiet_end:
                if now >= quiet_start or now <= quiet_end:
                    return False
            else:
                if quiet_start <= now <= quiet_end:
                    return False
        except ValueError:
            pass

    # Check frequency limit
    if pref["frequency_limit"]:
        today_count = await db.fetch_one("""
            SELECT COUNT(*) as count
            FROM proactive_notifications
            WHERE type = $1
              AND DATE(created_at) = CURRENT_DATE
        """, notification_type)

        if today_count and today_count["count"] >= pref["frequency_limit"]:
            return False

    return True


def get_next_available_time(quiet_end: str) -> datetime:
    """Calculate next available time after quiet hours end."""
    now = datetime.now()
    quiet_end_time = datetime.strptime(quiet_end, "%H:%M").time()
    next_available = datetime.combine(now.date(), quiet_end_time)

    if next_available <= now:
        next_available += timedelta(days=1)

    return next_available


# ============================================
# NOTIFICATION GENERATOR
# ============================================

class NotificationGenerator:
    """Generates proactive notifications based on user state."""

    DEADLINE_THRESHOLDS = {
        "24h": (24, "high", "Tomorrow"),
        "4h": (4, "urgent", "In 4 hours"),
        "1h": (1, "urgent", "In 1 hour"),
    }

    BREAK_THRESHOLD_MINS = 90  # Suggest break after 90 mins

    async def check_and_generate(self) -> List[Dict]:
        """Run all notification checks and generate notifications."""
        notifications = []

        try:
            # Check deadlines
            notifications.extend(await self.check_deadlines())

            # Check break needs
            notifications.extend(await self.check_break_needed())

            # Check revisions due
            notifications.extend(await self.check_revisions())

            # Check achievements
            notifications.extend(await self.check_achievements())

            # Daily motivation
            notifications.extend(await self.check_daily_motivation())

            # Overwork warning
            notifications.extend(await self.check_overwork())

            # Streak warning
            notifications.extend(await self.check_streak_at_risk())

        except Exception as e:
            print(f"Error generating notifications: {e}")

        return notifications

    async def check_deadlines(self) -> List[Dict]:
        """Check for upcoming deadlines and generate reminders."""
        notifications = []
        now = datetime.now()

        # Get upcoming deadlines (tasks, lab reports, goals)
        deadlines = []

        # Tasks with deadlines
        tasks = await db.fetch("""
            SELECT
                t.id, t.title, t.scheduled_start as deadline,
                s.code as subject_code, 'task' as item_type
            FROM tasks t
            LEFT JOIN subjects s ON t.subject_id = s.id
            WHERE t.status NOT IN ('completed', 'cancelled')
              AND t.scheduled_start IS NOT NULL
              AND t.scheduled_start BETWEEN NOW() AND NOW() + INTERVAL '25 hours'
        """)
        deadlines.extend(tasks)

        # Lab reports
        labs = await db.fetch("""
            SELECT
                lr.id, lr.experiment_name as title, lr.deadline,
                s.code as subject_code, 'lab_report' as item_type
            FROM lab_reports lr
            JOIN subjects s ON lr.subject_id = s.id
            WHERE lr.status NOT IN ('completed', 'cancelled')
              AND lr.deadline BETWEEN NOW() AND NOW() + INTERVAL '25 hours'
        """)
        deadlines.extend(labs)

        # Goals with deadlines
        goals = await db.fetch("""
            SELECT
                sg.id, sg.title, sg.deadline::timestamp as deadline,
                COALESCE(s.code, 'General') as subject_code, 'goal' as item_type
            FROM study_goals sg
            LEFT JOIN subjects s ON sg.subject_id = s.id
            WHERE sg.completed = false
              AND sg.deadline IS NOT NULL
              AND sg.deadline BETWEEN CURRENT_DATE AND CURRENT_DATE + 1
        """)
        deadlines.extend(goals)

        for item in deadlines:
            if not item["deadline"]:
                continue

            deadline_dt = item["deadline"]
            if isinstance(deadline_dt, date) and not isinstance(deadline_dt, datetime):
                deadline_dt = datetime.combine(deadline_dt, time(23, 59))

            hours_until = (deadline_dt - now).total_seconds() / 3600

            for threshold_key, (hours, priority, prefix) in self.DEADLINE_THRESHOLDS.items():
                if 0 < hours_until <= hours:
                    dedup_key = f"deadline_{item['item_type']}_{item['id']}_{threshold_key}"

                    if await is_notification_allowed(NotificationType.REMINDER):
                        notif = await create_notification(
                            notif_type=NotificationType.REMINDER,
                            title=f"{prefix}: {item['title']}",
                            message=f"{item['item_type'].replace('_', ' ').title()} for {item['subject_code']} is due soon.",
                            priority=priority,
                            action_url=f"/schedule",
                            action_label="View Schedule",
                            reference_type=item["item_type"],
                            reference_id=item["id"],
                            dedup_key=dedup_key
                        )
                        if notif:
                            notifications.append(notif)
                    break

        return notifications

    async def check_break_needed(self) -> List[Dict]:
        """Check if user has been studying too long without break."""
        notifications = []

        # Get active timer
        active_timer = await db.fetch_one("""
            SELECT
                at.*,
                s.code as subject_code,
                EXTRACT(EPOCH FROM (NOW() - at.started_at))::INTEGER as elapsed_seconds
            FROM active_timer at
            LEFT JOIN subjects s ON at.subject_id = s.id
            LIMIT 1
        """)

        if active_timer:
            elapsed_mins = active_timer["elapsed_seconds"] // 60

            if elapsed_mins >= self.BREAK_THRESHOLD_MINS:
                # Check if we already sent a break notification recently
                dedup_key = f"break_suggestion_{active_timer['session_id']}_{elapsed_mins // 30}"

                if await is_notification_allowed(NotificationType.SUGGESTION):
                    notif = await create_notification(
                        notif_type=NotificationType.SUGGESTION,
                        title="Time for a break!",
                        message=f"You've been studying for {elapsed_mins} minutes. Take a short break to maintain focus.",
                        priority="normal",
                        action_url="/timer",
                        action_label="Take Break",
                        dedup_key=dedup_key
                    )
                    if notif:
                        notifications.append(notif)

        return notifications

    async def check_revisions(self) -> List[Dict]:
        """Check for due revisions."""
        notifications = []

        # Get revisions due today or overdue
        revisions = await db.fetch("""
            SELECT
                rs.id, rs.due_date, rs.revision_number,
                c.title as chapter_title, c.number as chapter_number,
                s.code as subject_code
            FROM revision_schedule rs
            JOIN chapters c ON rs.chapter_id = c.id
            JOIN subjects s ON c.subject_id = s.id
            WHERE rs.completed = false
              AND rs.due_date <= CURRENT_DATE
            ORDER BY rs.due_date, s.credits DESC
        """)

        if revisions and await is_notification_allowed(NotificationType.REMINDER):
            # Create a single notification for all due revisions
            count = len(revisions)
            first_rev = revisions[0]

            dedup_key = f"revisions_due_{date.today()}"

            notif = await create_notification(
                notif_type=NotificationType.REMINDER,
                title=f"{count} Revision{'s' if count > 1 else ''} Due",
                message=f"You have {count} chapter revision{'s' if count > 1 else ''} due. "
                        f"First: {first_rev['subject_code']} Ch.{first_rev['chapter_number']}",
                priority="high" if count > 2 else "normal",
                action_url="/revisions",
                action_label="Start Revisions",
                dedup_key=dedup_key
            )
            if notif:
                notifications.append(notif)

        return notifications

    async def check_achievements(self) -> List[Dict]:
        """Check for newly earned achievements."""
        notifications = []

        # Get unlocked but not notified achievements
        achievements = await db.fetch("""
            SELECT id, name, description, icon, points_reward
            FROM achievements
            WHERE unlocked = true
              AND id NOT IN (
                  SELECT reference_id FROM proactive_notifications
                  WHERE reference_type = 'achievement' AND reference_id IS NOT NULL
              )
        """)

        for achievement in achievements:
            if await is_notification_allowed(NotificationType.ACHIEVEMENT):
                notif = await create_notification(
                    notif_type=NotificationType.ACHIEVEMENT,
                    title=f"Achievement Unlocked: {achievement['name']}!",
                    message=f"{achievement['icon']} {achievement['description']} (+{achievement['points_reward']} points)",
                    priority="normal",
                    action_url="/achievements",
                    action_label="View Achievements",
                    reference_type="achievement",
                    reference_id=achievement["id"],
                    dedup_key=f"achievement_{achievement['id']}"
                )
                if notif:
                    notifications.append(notif)

        return notifications

    async def check_daily_motivation(self) -> List[Dict]:
        """Send once-daily motivational message."""
        notifications = []
        today = date.today()

        # Check if already sent today
        existing = await db.fetch_one("""
            SELECT id FROM proactive_notifications
            WHERE type = $1 AND DATE(created_at) = $2
        """, NotificationType.MOTIVATION, today)

        if existing:
            return notifications

        # Only send in the morning (6 AM - 9 AM)
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour >= 9:
            return notifications

        if not await is_notification_allowed(NotificationType.MOTIVATION):
            return notifications

        # Get streak and stats
        streak = await db.fetch_one("SELECT current_streak, total_points FROM user_streaks LIMIT 1")
        current_streak = streak["current_streak"] if streak else 0
        total_points = streak["total_points"] if streak else 0

        # Get yesterday's study time
        yesterday_stats = await db.fetch_one("""
            SELECT COALESCE(SUM(duration_seconds), 0) as total_seconds
            FROM study_sessions
            WHERE DATE(started_at) = CURRENT_DATE - 1
              AND stopped_at IS NOT NULL
        """)
        yesterday_mins = (yesterday_stats["total_seconds"] or 0) // 60

        # Build motivational message
        messages = [
            ("Rise and shine! Ready to learn something new today?", "normal"),
            ("New day, new opportunities to grow. Let's make it count!", "normal"),
            ("Small consistent steps lead to big achievements. Keep going!", "normal"),
        ]

        if current_streak >= 7:
            messages.append((f"Amazing! You're on a {current_streak}-day streak. Keep the momentum!", "high"))
        elif current_streak >= 3:
            messages.append((f"Great job! {current_streak}-day streak and counting!", "normal"))

        if yesterday_mins >= 120:
            messages.append((f"You studied {yesterday_mins} minutes yesterday. Impressive dedication!", "normal"))

        import random
        message, priority = random.choice(messages)

        notif = await create_notification(
            notif_type=NotificationType.MOTIVATION,
            title="Good Morning!",
            message=message,
            priority=priority,
            dedup_key=f"motivation_{today}"
        )
        if notif:
            notifications.append(notif)

        return notifications

    async def check_overwork(self) -> List[Dict]:
        """Check if user is overworking."""
        notifications = []

        # Get today's total study time
        today_stats = await db.fetch_one("""
            SELECT
                COALESCE(SUM(duration_seconds), 0) as total_seconds,
                COUNT(*) as session_count
            FROM study_sessions
            WHERE DATE(started_at) = CURRENT_DATE
              AND stopped_at IS NOT NULL
        """)

        # Also check active timer
        active_timer = await db.fetch_one("""
            SELECT EXTRACT(EPOCH FROM (NOW() - started_at))::INTEGER as elapsed_seconds
            FROM active_timer
            LIMIT 1
        """)

        total_seconds = today_stats["total_seconds"] or 0
        if active_timer:
            total_seconds += active_timer["elapsed_seconds"]

        total_hours = total_seconds / 3600

        if total_hours >= 10:
            # Urgent: Stop studying
            if await is_notification_allowed(NotificationType.WARNING):
                notif = await create_notification(
                    notif_type=NotificationType.WARNING,
                    title="Please take a rest!",
                    message=f"You've studied over {int(total_hours)} hours today. Your brain needs rest to consolidate learning.",
                    priority="urgent",
                    action_url="/timer",
                    action_label="Stop Timer",
                    dedup_key=f"overwork_10h_{date.today()}"
                )
                if notif:
                    notifications.append(notif)

        elif total_hours >= 8:
            # Warning: Consider stopping
            if await is_notification_allowed(NotificationType.WARNING):
                notif = await create_notification(
                    notif_type=NotificationType.WARNING,
                    title="Extended study session",
                    message=f"You've studied {int(total_hours)} hours today. Consider wrapping up soon for better retention.",
                    priority="high",
                    action_url="/analytics",
                    action_label="View Stats",
                    dedup_key=f"overwork_8h_{date.today()}"
                )
                if notif:
                    notifications.append(notif)

        return notifications

    async def check_streak_at_risk(self) -> List[Dict]:
        """Check if user's streak is at risk of breaking."""
        notifications = []

        streak_data = await db.fetch_one("""
            SELECT current_streak, last_activity
            FROM user_streaks
            LIMIT 1
        """)

        if not streak_data or not streak_data["current_streak"]:
            return notifications

        current_streak = streak_data["current_streak"]
        last_activity = streak_data["last_activity"]

        # Only warn if streak is worth protecting (3+ days)
        if current_streak < 3:
            return notifications

        today = date.today()
        now = datetime.now()

        # If last activity was yesterday and it's getting late
        if last_activity and last_activity == today - timedelta(days=1):
            # After 8 PM, warn about streak
            if now.hour >= 20 and await is_notification_allowed(NotificationType.WARNING):
                notif = await create_notification(
                    notif_type=NotificationType.WARNING,
                    title="Protect your streak!",
                    message=f"Your {current_streak}-day streak is at risk! Study for at least 30 minutes today to keep it going.",
                    priority="high",
                    action_url="/timer",
                    action_label="Start Studying",
                    dedup_key=f"streak_at_risk_{today}"
                )
                if notif:
                    notifications.append(notif)

        return notifications


# ============================================
# NOTIFICATION SERVICE (Background Runner)
# ============================================

class NotificationService:
    """Background service that runs notification checks periodically."""

    def __init__(self, check_interval_seconds: int = 300):  # 5 minutes default
        self.check_interval = check_interval_seconds
        self.generator = NotificationGenerator()
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the notification service."""
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(self._run_loop())
        print(f"[NotificationService] Started with {self.check_interval}s interval")

    async def stop(self):
        """Stop the notification service."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("[NotificationService] Stopped")

    async def _run_loop(self):
        """Main loop that checks and sends notifications."""
        while self.running:
            try:
                # Generate new notifications
                new_notifications = await self.generator.check_and_generate()

                # Get pending notifications (including newly generated ones)
                pending = await get_pending_notifications()

                for notif in pending:
                    await self._send_notification(notif)

            except Exception as e:
                print(f"[NotificationService] Error in loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _send_notification(self, notification: Dict):
        """Send notification through available channels."""
        try:
            # Mark as sent
            await mark_notification_sent(notification["id"])

            # Broadcast via WebSocket to all connected clients
            await broadcast_notification(notification)

        except Exception as e:
            print(f"[NotificationService] Error sending notification {notification['id']}: {e}")


# ============================================
# WEBSOCKET MANAGEMENT
# ============================================

async def register_client(websocket):
    """Register a new WebSocket client."""
    connected_clients.add(websocket)
    print(f"[WebSocket] Client connected. Total: {len(connected_clients)}")

    # Send pending notifications to newly connected client
    pending = await get_user_notifications(limit=10, unread_only=True)
    for notif in pending:
        try:
            await websocket.send_json({
                "type": "notification",
                "data": serialize_notification(notif)
            })
        except Exception:
            pass


async def unregister_client(websocket):
    """Remove a WebSocket client."""
    connected_clients.discard(websocket)
    print(f"[WebSocket] Client disconnected. Total: {len(connected_clients)}")


async def broadcast_notification(notification: Dict):
    """Broadcast notification to all connected WebSocket clients."""
    if not connected_clients:
        return

    message = {
        "type": "notification",
        "data": serialize_notification(notification)
    }

    # Broadcast to all clients
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.add(client)

    # Clean up disconnected clients
    for client in disconnected:
        connected_clients.discard(client)


def serialize_notification(notification: Dict) -> Dict:
    """Serialize notification for JSON transmission."""
    result = dict(notification)

    # Convert datetime objects to ISO strings
    for key in ["created_at", "sent_at", "read_at", "scheduled_for"]:
        if key in result and result[key]:
            if isinstance(result[key], datetime):
                result[key] = result[key].isoformat()

    return result


# ============================================
# SINGLETON SERVICE INSTANCE
# ============================================

notification_service = NotificationService()


# ============================================
# DATABASE SCHEMA MIGRATION
# ============================================

NOTIFICATION_SCHEMA = """
-- Proactive notifications table
CREATE TABLE IF NOT EXISTS proactive_notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(20) DEFAULT 'normal',
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    scheduled_for TIMESTAMP WITH TIME ZONE,
    reference_type VARCHAR(50),
    reference_id INTEGER,
    dedup_key VARCHAR(200) UNIQUE,
    sent BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP WITH TIME ZONE,
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proactive_notif_pending
    ON proactive_notifications(sent, dismissed, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_proactive_notif_type
    ON proactive_notifications(type, created_at);
CREATE INDEX IF NOT EXISTS idx_proactive_notif_dedup
    ON proactive_notifications(dedup_key);

-- Notification preferences table
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start VARCHAR(5),  -- "HH:MM"
    quiet_hours_end VARCHAR(5),    -- "HH:MM"
    frequency_limit INTEGER,       -- Max notifications per day
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default preferences
INSERT INTO notification_preferences (notification_type, enabled, quiet_hours_start, quiet_hours_end, frequency_limit)
VALUES
    ('reminder', true, '22:00', '07:00', 10),
    ('achievement', true, NULL, NULL, NULL),
    ('suggestion', true, '22:00', '07:00', 5),
    ('warning', true, NULL, NULL, 3),
    ('motivation', true, NULL, NULL, 1)
ON CONFLICT (notification_type) DO NOTHING;
"""


async def ensure_notification_tables():
    """Create notification tables if they don't exist."""
    try:
        # Check if tables exist
        exists = await db.fetch_one("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'proactive_notifications'
            ) as exists
        """)

        if not exists or not exists["exists"]:
            # Execute schema creation
            async with db._pool.acquire() as conn:
                await conn.execute(NOTIFICATION_SCHEMA)
            print("[NotificationService] Database tables created")

    except Exception as e:
        print(f"[NotificationService] Error creating tables: {e}")
