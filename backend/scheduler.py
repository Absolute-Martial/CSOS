"""
Personal Engineering OS - Smart Scheduler Module
Manages calendar, timetable, gap analysis, and AI-driven schedule optimization
Includes: Daily routine, sleep management, revision scheduling, and dynamic task allocation
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from database import db


# ============================================
# CONFIGURATION - Daily Routine Settings
# ============================================

class ActivityType(str, Enum):
    SLEEP = "sleep"
    WAKE_ROUTINE = "wake_routine"      # Morning routine (brush, shower, etc.)
    BREAKFAST = "breakfast"
    UNIVERSITY = "university"           # KU classes
    STUDY = "study"                     # New material / lectures
    REVISION = "revision"               # Review past material
    PRACTICE = "practice"               # Problems, coding, exercises
    ASSIGNMENT = "assignment"           # Homework, projects
    LAB_WORK = "lab_work"              # Lab reports, experiments
    DEEP_WORK = "deep_work"            # Focused 90+ min sessions
    BREAK = "break"                     # Short breaks (15-30 min)
    LUNCH = "lunch"
    DINNER = "dinner"
    FREE_TIME = "free_time"            # Entertainment, relaxation
    EXERCISE = "exercise"               # Physical activity
    TRAVEL = "travel"                   # Commute time
    BUFFER = "buffer"                   # Flexible/unscheduled time


# Default daily routine configuration (customize per user preference)
DAILY_ROUTINE_CONFIG = {
    # Sleep schedule
    "sleep_start": "23:00",            # Bedtime
    "sleep_end": "06:00",              # Wake up
    "min_sleep_hours": 7,

    # Morning routine
    "wake_routine_mins": 30,           # Morning hygiene, etc.
    "breakfast_mins": 30,

    # Meals
    "lunch_time": "13:00",
    "lunch_mins": 45,
    "dinner_time": "19:30",
    "dinner_mins": 45,

    # Study preferences
    "max_study_block_mins": 90,        # Pomodoro-style max focus
    "min_break_after_study": 15,       # Rest after study block
    "preferred_study_times": ["morning", "afternoon"],  # When to schedule hard tasks

    # Energy levels by time of day (1-10)
    "energy_curve": {
        "06:00": 5,   # Just woke up
        "08:00": 8,   # Peak morning
        "10:00": 9,   # High energy
        "12:00": 7,   # Pre-lunch dip
        "14:00": 5,   # Post-lunch slump
        "16:00": 7,   # Afternoon recovery
        "18:00": 6,   # Evening
        "20:00": 5,   # Winding down
        "22:00": 3,   # Low energy
    },

    # Weekly targets (in hours)
    "weekly_targets": {
        "study": 20,
        "revision": 10,
        "practice": 8,
        "assignment": 6,
        "exercise": 5,
        "free_time": 10,
    },

    # Travel time to university
    "commute_mins": 30,
}

# KU Timetable - edit this to match your actual schedule
KU_TIMETABLE = {
    "Sunday": [
        {"start": "08:00", "end": "09:00", "subject": "MATH101", "type": "lecture", "room": "ENG-101"},
        {"start": "09:00", "end": "10:00", "subject": "PHYS102", "type": "lecture", "room": "ENG-201"},
        {"start": "10:30", "end": "12:30", "subject": "CHEM103", "type": "lab", "room": "LAB-A"},
    ],
    "Monday": [
        {"start": "08:00", "end": "09:30", "subject": "COMP104", "type": "lecture", "room": "IT-301"},
        {"start": "14:00", "end": "16:00", "subject": "THER105", "type": "lab", "room": "MECH-LAB"},
    ],
    "Tuesday": [
        {"start": "08:00", "end": "09:00", "subject": "MATH101", "type": "lecture", "room": "ENG-101"},
        {"start": "09:00", "end": "10:00", "subject": "PHYS102", "type": "lecture", "room": "ENG-201"},
        {"start": "10:00", "end": "11:00", "subject": "CHEM103", "type": "lecture", "room": "ENG-102"},
        {"start": "11:30", "end": "13:30", "subject": "PHYS102", "type": "lab", "room": "PHYS-LAB"},
    ],
    "Wednesday": [
        {"start": "08:00", "end": "09:30", "subject": "COMP104", "type": "lecture", "room": "IT-301"},
        {"start": "10:00", "end": "11:00", "subject": "THER105", "type": "lecture", "room": "MECH-201"},
    ],
    "Thursday": [
        {"start": "08:00", "end": "09:00", "subject": "MATH101", "type": "lecture", "room": "ENG-101"},
        {"start": "09:00", "end": "10:00", "subject": "PHYS102", "type": "lecture", "room": "ENG-201"},
        {"start": "10:00", "end": "11:00", "subject": "CHEM103", "type": "lecture", "room": "ENG-102"},
        {"start": "14:00", "end": "16:00", "subject": "CHEM103", "type": "lab", "room": "CHEM-LAB"},
    ],
    "Friday": [],  # No classes
    "Saturday": [],  # No classes
}

# Day boundaries
DAY_START = time(6, 0)  # 6 AM
DAY_END = time(23, 0)   # 11 PM
DEEP_WORK_MIN_MINUTES = 90


# ============================================
# UTILITY FUNCTIONS
# ============================================

def time_to_minutes(t: time) -> int:
    """Convert time to minutes since midnight."""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convert minutes since midnight to time."""
    minutes = minutes % (24 * 60)  # Handle overflow
    return time(minutes // 60, minutes % 60)


def parse_time(time_str: str) -> time:
    """Parse time string (HH:MM) to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def format_time(t: time) -> str:
    """Format time to HH:MM string."""
    return t.strftime("%H:%M")


def get_energy_level(hour: int) -> int:
    """Get energy level (1-10) for a given hour."""
    curve = DAILY_ROUTINE_CONFIG["energy_curve"]
    times = sorted(curve.keys())

    for i, t in enumerate(times):
        t_hour = int(t.split(":")[0])
        if hour < t_hour:
            if i == 0:
                return curve[times[0]]
            # Interpolate between previous and current
            prev_t = times[i-1]
            prev_hour = int(prev_t.split(":")[0])
            prev_energy = curve[prev_t]
            curr_energy = curve[t]
            ratio = (hour - prev_hour) / (t_hour - prev_hour)
            return int(prev_energy + (curr_energy - prev_energy) * ratio)

    return curve[times[-1]]


# ============================================
# TIMETABLE OPERATIONS
# ============================================

def get_timetable_for_day(day_name: str) -> List[Dict]:
    """Get university timetable for a specific day."""
    return KU_TIMETABLE.get(day_name, [])


def get_timetable_for_date(target_date: date) -> List[Dict]:
    """Get university timetable for a specific date."""
    day_name = target_date.strftime("%A")
    timetable = get_timetable_for_day(day_name)

    # Add date to each entry
    return [
        {**entry, "date": str(target_date)}
        for entry in timetable
    ]


async def get_today_timetable() -> Dict:
    """Get today's timetable with additional context."""
    today = date.today()
    day_name = today.strftime("%A")
    timetable = get_timetable_for_day(day_name)

    return {
        "date": str(today),
        "day": day_name,
        "classes": timetable,
        "class_count": len(timetable),
        "has_lab": any(c["type"] == "lab" for c in timetable)
    }


# ============================================
# GAP ANALYSIS
# ============================================

def time_to_minutes(t: time) -> int:
    """Convert time to minutes since midnight."""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """Convert minutes since midnight to time."""
    return time(minutes // 60, minutes % 60)


def parse_time(time_str: str) -> time:
    """Parse time string (HH:MM) to time object."""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


async def analyze_day_gaps(target_date: date) -> Dict:
    """
    Analyze gaps in a day's schedule for deep work opportunities.

    Returns:
        Dictionary with gaps, total available time, and recommendations
    """
    day_name = target_date.strftime("%A")

    # Get fixed timetable
    timetable = get_timetable_for_day(day_name)

    # Get scheduled tasks for this day
    tasks = await db.fetch("""
        SELECT scheduled_start, duration_mins, title, is_deep_work
        FROM tasks
        WHERE DATE(scheduled_start) = $1
        ORDER BY scheduled_start
    """, target_date)

    # Build list of busy blocks
    busy_blocks = []

    # Add timetable classes
    for cls in timetable:
        start_mins = time_to_minutes(parse_time(cls["start"]))
        end_mins = time_to_minutes(parse_time(cls["end"]))
        busy_blocks.append({
            "start": start_mins,
            "end": end_mins,
            "type": cls["type"],
            "label": f"{cls['subject']} ({cls['type']})"
        })

    # Add scheduled tasks
    for task in tasks:
        if task["scheduled_start"]:
            start_time = task["scheduled_start"]
            start_mins = start_time.hour * 60 + start_time.minute
            end_mins = start_mins + (task["duration_mins"] or 60)
            busy_blocks.append({
                "start": start_mins,
                "end": end_mins,
                "type": "task",
                "label": task["title"]
            })

    # Sort by start time
    busy_blocks.sort(key=lambda x: x["start"])

    # Find gaps
    gaps = []
    day_start_mins = time_to_minutes(DAY_START)
    day_end_mins = time_to_minutes(DAY_END)

    current_time = day_start_mins

    for block in busy_blocks:
        if block["start"] > current_time:
            gap_duration = block["start"] - current_time
            gaps.append({
                "start": minutes_to_time(current_time).strftime("%H:%M"),
                "end": minutes_to_time(block["start"]).strftime("%H:%M"),
                "duration_mins": gap_duration,
                "is_deep_work_suitable": gap_duration >= DEEP_WORK_MIN_MINUTES
            })
        current_time = max(current_time, block["end"])

    # Check for gap after last block until day end
    if current_time < day_end_mins:
        gap_duration = day_end_mins - current_time
        gaps.append({
            "start": minutes_to_time(current_time).strftime("%H:%M"),
            "end": minutes_to_time(day_end_mins).strftime("%H:%M"),
            "duration_mins": gap_duration,
            "is_deep_work_suitable": gap_duration >= DEEP_WORK_MIN_MINUTES
        })

    # Calculate totals
    total_gap_mins = sum(g["duration_mins"] for g in gaps)
    deep_work_mins = sum(g["duration_mins"] for g in gaps if g["is_deep_work_suitable"])

    return {
        "date": str(target_date),
        "day": day_name,
        "gaps": gaps,
        "total_gaps": len(gaps),
        "total_available_mins": total_gap_mins,
        "deep_work_available_mins": deep_work_mins,
        "deep_work_blocks": len([g for g in gaps if g["is_deep_work_suitable"]]),
        "busy_blocks": busy_blocks
    }


async def find_deep_work_slots(days: int = 7) -> List[Dict]:
    """Find deep work opportunities over the next N days."""
    slots = []
    today = date.today()

    for i in range(days):
        target_date = today + timedelta(days=i)
        analysis = await analyze_day_gaps(target_date)

        for gap in analysis["gaps"]:
            if gap["is_deep_work_suitable"]:
                slots.append({
                    "date": str(target_date),
                    "day": analysis["day"],
                    **gap
                })

    return slots


# ============================================
# SCHEDULE REDISTRIBUTION (AI-Driven)
# ============================================

async def get_week_schedule(start_date: Optional[date] = None) -> Dict:
    """Get the full week's schedule including timetable and tasks."""
    if not start_date:
        start_date = date.today()

    week = []
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_name = current_date.strftime("%A")

        # Get timetable
        timetable = get_timetable_for_day(day_name)

        # Get tasks
        tasks = await db.fetch("""
            SELECT t.*, s.code as subject_code, s.color
            FROM tasks t
            LEFT JOIN subjects s ON t.subject_id = s.id
            WHERE DATE(t.scheduled_start) = $1
            ORDER BY t.scheduled_start
        """, current_date)

        # Analyze gaps
        gap_analysis = await analyze_day_gaps(current_date)

        week.append({
            "date": str(current_date),
            "day": day_name,
            "timetable": timetable,
            "tasks": tasks,
            "gap_analysis": gap_analysis
        })

    return {
        "start_date": str(start_date),
        "days": week
    }


async def redistribute_schedule(
    event_type: str,
    event_subject: str,
    event_date: date,
    priority: int = 8
) -> Dict:
    """
    Redistribute study blocks when a surprise event (test, assignment) is added.

    This is the core AI scheduling function that finds optimal slots for preparation.

    Args:
        event_type: 'test', 'assignment', 'lab_report', etc.
        event_subject: Subject code like 'CHEM103'
        event_date: Date of the event
        priority: How important (1-10)

    Returns:
        Redistribution plan with suggested changes
    """
    today = date.today()
    days_until = (event_date - today).days

    if days_until < 0:
        return {"error": "Event date is in the past"}

    # Determine study hours needed based on event type
    study_hours_needed = {
        "test": 4,
        "quiz": 2,
        "assignment": 3,
        "lab_report": 2,
        "project": 6,
        "exam": 8
    }.get(event_type, 3)

    study_mins_needed = study_hours_needed * 60

    # Find available slots between now and event
    available_slots = []
    for i in range(days_until):
        target_date = today + timedelta(days=i)
        analysis = await analyze_day_gaps(target_date)

        for gap in analysis["gaps"]:
            if gap["duration_mins"] >= 30:  # Minimum useful block
                available_slots.append({
                    "date": str(target_date),
                    "day": analysis["day"],
                    **gap
                })

    # Sort by suitability (prefer deep work slots closer to event)
    available_slots.sort(
        key=lambda s: (
            not s["is_deep_work_suitable"],  # Deep work first
            -datetime.strptime(s["date"], "%Y-%m-%d").timestamp()  # Later dates first
        )
    )

    # Allocate study blocks
    allocated = []
    remaining_mins = study_mins_needed

    for slot in available_slots:
        if remaining_mins <= 0:
            break

        # Take what we can from this slot (max 120 mins per block)
        block_mins = min(slot["duration_mins"], remaining_mins, 120)

        allocated.append({
            "date": slot["date"],
            "day": slot["day"],
            "start": slot["start"],
            "duration_mins": block_mins,
            "subject": event_subject,
            "title": f"Prepare for {event_type}: {event_subject}",
            "is_deep_work": block_mins >= DEEP_WORK_MIN_MINUTES
        })

        remaining_mins -= block_mins

    return {
        "success": True,
        "event": {
            "type": event_type,
            "subject": event_subject,
            "date": str(event_date),
            "days_until": days_until
        },
        "study_needed_mins": study_mins_needed,
        "study_allocated_mins": study_mins_needed - remaining_mins,
        "fully_scheduled": remaining_mins <= 0,
        "blocks": allocated,
        "message": f"Scheduled {len(allocated)} study blocks for {event_subject} {event_type}"
    }


async def apply_redistribution(blocks: List[Dict]) -> Dict:
    """Apply the redistribution plan by creating tasks."""
    created = []

    for block in blocks:
        # Parse date and time
        block_date = datetime.strptime(block["date"], "%Y-%m-%d").date()
        start_time = parse_time(block["start"])
        scheduled_start = datetime.combine(block_date, start_time)

        # Get subject ID
        subject = await db.fetch_one(
            "SELECT id FROM subjects WHERE code = $1",
            block["subject"]
        )

        task = await db.execute_returning("""
            INSERT INTO tasks (
                title, subject_id, scheduled_start, duration_mins,
                priority, is_deep_work, task_type
            ) VALUES ($1, $2, $3, $4, $5, $6, 'study')
            RETURNING *
        """,
            block["title"],
            subject["id"] if subject else None,
            scheduled_start,
            block["duration_mins"],
            8,  # High priority for event prep
            block.get("is_deep_work", False)
        )

        created.append(task)

    return {
        "success": True,
        "tasks_created": len(created),
        "tasks": created
    }


# ============================================
# LAB REPORT TRACKING
# ============================================

async def get_lab_report_countdown() -> List[Dict]:
    """Get pending lab reports with countdown."""
    reports = await db.fetch("""
        SELECT
            lr.*,
            s.code as subject_code,
            s.name as subject_name,
            s.color,
            lr.due_date - CURRENT_DATE as days_remaining
        FROM lab_reports lr
        JOIN subjects s ON lr.subject_id = s.id
        WHERE lr.status != 'submitted'
        ORDER BY lr.due_date ASC
    """)

    return [
        {
            **report,
            "urgency": "overdue" if report["days_remaining"] < 0
                else "urgent" if report["days_remaining"] <= 2
                else "soon" if report["days_remaining"] <= 7
                else "normal"
        }
        for report in reports
    ]


async def create_lab_report_entry(
    subject_code: str,
    experiment_name: str,
    due_date: date,
    lab_date: Optional[date] = None
) -> Dict:
    """Create a new lab report tracking entry."""
    subject = await db.fetch_one(
        "SELECT id FROM subjects WHERE code = $1",
        subject_code.upper()
    )

    if not subject:
        return {"error": f"Subject {subject_code} not found"}

    report = await db.execute_returning("""
        INSERT INTO lab_reports (
            subject_id, experiment_name, lab_date, due_date, status
        ) VALUES ($1, $2, $3, $4, 'pending')
        RETURNING *
    """, subject["id"], experiment_name, lab_date or date.today(), due_date)

    return {
        "success": True,
        "report": report,
        "message": f"Lab report for {experiment_name} added"
    }


async def update_lab_report_status(
    report_id: int,
    status: str,
    notes: Optional[str] = None
) -> Dict:
    """Update lab report status."""
    valid_statuses = ["pending", "in_progress", "draft_complete", "submitted"]
    if status not in valid_statuses:
        return {"error": f"Invalid status. Use: {valid_statuses}"}

    report = await db.execute_returning("""
        UPDATE lab_reports SET
            status = $1,
            notes = COALESCE($2, notes),
            updated_at = NOW(),
            submitted_at = CASE WHEN $1 = 'submitted' THEN NOW() ELSE NULL END
        WHERE id = $3
        RETURNING *
    """, status, notes, report_id)

    return {"success": True, "report": report}


# ============================================
# NOTIFICATIONS & REMINDERS
# ============================================

async def get_upcoming_deadlines(days: int = 7) -> List[Dict]:
    """Get all upcoming deadlines in the next N days."""
    cutoff = date.today() + timedelta(days=days)

    # Get lab reports
    reports = await db.fetch("""
        SELECT
            'lab_report' as type,
            lr.experiment_name as title,
            s.code as subject_code,
            s.color,
            lr.due_date,
            lr.due_date - CURRENT_DATE as days_remaining
        FROM lab_reports lr
        JOIN subjects s ON lr.subject_id = s.id
        WHERE lr.status != 'submitted'
          AND lr.due_date <= $1
        ORDER BY lr.due_date
    """, cutoff)

    # Get scheduled assignments
    assignments = await db.fetch("""
        SELECT
            'assignment' as type,
            t.title,
            s.code as subject_code,
            s.color,
            DATE(t.scheduled_start) as due_date,
            DATE(t.scheduled_start) - CURRENT_DATE as days_remaining
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE t.task_type = 'assignment'
          AND t.status != 'completed'
          AND DATE(t.scheduled_start) <= $1
        ORDER BY t.scheduled_start
    """, cutoff)

    # Get goals with deadlines
    goals = await db.fetch("""
        SELECT
            'goal' as type,
            sg.title,
            s.code as subject_code,
            s.color,
            sg.deadline as due_date,
            sg.deadline - CURRENT_DATE as days_remaining
        FROM study_goals sg
        LEFT JOIN subjects s ON sg.subject_id = s.id
        WHERE sg.completed = false
          AND sg.deadline IS NOT NULL
          AND sg.deadline <= $1
        ORDER BY sg.deadline
    """, cutoff)

    # Combine and sort by date
    all_deadlines = list(reports) + list(assignments) + list(goals)
    all_deadlines.sort(key=lambda x: x["due_date"] or date.max)

    return all_deadlines


async def schedule_notifications_for_deadlines() -> Dict:
    """Auto-schedule notifications for upcoming deadlines."""
    deadlines = await get_upcoming_deadlines(14)  # 2 weeks out

    notifications_created = 0

    for deadline in deadlines:
        days = deadline["days_remaining"]

        # Create notifications at key intervals
        notification_days = []
        if days == 7:
            notification_days.append((7, "1 week until"))
        if days == 3:
            notification_days.append((3, "3 days until"))
        if days == 1:
            notification_days.append((1, "Tomorrow:"))
        if days == 0:
            notification_days.append((0, "TODAY:"))

        for day_offset, prefix in notification_days:
            # Check if notification already exists
            existing = await db.fetch_one("""
                SELECT id FROM notifications
                WHERE reference_type = $1
                  AND reference_id = $2
                  AND DATE(due_at) = $3
            """, deadline["type"], deadline.get("id"), deadline["due_date"])

            if not existing:
                await db.execute("""
                    INSERT INTO notifications (type, title, message, due_at)
                    VALUES ($1, $2, $3, $4)
                """,
                    "due_date",
                    f"{prefix} {deadline['title']}",
                    f"{deadline['type'].replace('_', ' ').title()} for {deadline.get('subject_code', 'General')}",
                    deadline["due_date"]
                )
                notifications_created += 1

    return {
        "success": True,
        "notifications_created": notifications_created,
        "deadlines_checked": len(deadlines)
    }


# ============================================
# TODAY AT A GLANCE
# ============================================

async def get_today_at_glance() -> Dict:
    """Get comprehensive view of today's schedule and priorities."""
    today = date.today()
    day_name = today.strftime("%A")

    # Get timetable
    timetable = get_timetable_for_day(day_name)

    # Get today's tasks
    tasks = await db.fetch("""
        SELECT t.*, s.code as subject_code, s.color
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE DATE(t.scheduled_start) = $1
        ORDER BY t.scheduled_start
    """, today)

    # Get gap analysis
    gaps = await analyze_day_gaps(today)

    # Get pending lab reports
    lab_reports = await get_lab_report_countdown()
    urgent_reports = [r for r in lab_reports if r["urgency"] in ("overdue", "urgent")]

    # Get upcoming deadlines (next 3 days)
    deadlines = await get_upcoming_deadlines(3)

    # Get active timer if any
    active_timer = await db.fetch_one("""
        SELECT at.*, s.code as subject_code
        FROM active_timer at
        LEFT JOIN subjects s ON at.subject_id = s.id
        WHERE at.id = 1
    """)

    # Get study stats for today
    today_stats = await db.fetch_one("""
        SELECT
            COALESCE(SUM(duration_seconds), 0) as total_seconds,
            COUNT(*) as session_count,
            SUM(CASE WHEN is_deep_work THEN 1 ELSE 0 END) as deep_work_count
        FROM study_sessions
        WHERE DATE(started_at) = $1
          AND stopped_at IS NOT NULL
    """, today)

    # Get current streak
    streak = await db.fetch_one(
        "SELECT current_streak, total_points FROM user_streaks WHERE id = 1"
    )

    return {
        "date": str(today),
        "day": day_name,
        "timetable": {
            "classes": timetable,
            "class_count": len(timetable),
            "next_class": next(
                (c for c in timetable if parse_time(c["start"]) > datetime.now().time()),
                None
            )
        },
        "tasks": {
            "scheduled": tasks,
            "count": len(tasks),
            "completed": len([t for t in tasks if t["status"] == "completed"])
        },
        "gaps": {
            "total_available_mins": gaps["total_available_mins"],
            "deep_work_mins": gaps["deep_work_available_mins"],
            "slots": gaps["gaps"]
        },
        "lab_reports": {
            "urgent": urgent_reports,
            "total_pending": len(lab_reports)
        },
        "deadlines": deadlines[:5],  # Top 5 urgent
        "study_today": {
            "total_minutes": (today_stats["total_seconds"] or 0) // 60,
            "sessions": today_stats["session_count"] or 0,
            "deep_work_sessions": today_stats["deep_work_count"] or 0
        },
        "active_timer": active_timer,
        "streak": streak
    }


# ============================================
# DYNAMIC TIMELINE OPTIMIZATION ENGINE
# ============================================

class TaskPriority:
    """Priority weights for different task types."""
    OVERDUE = 100
    DUE_TODAY = 90
    EXAM_PREP = 85
    DUE_TOMORROW = 80
    URGENT_LAB = 75
    TEST_PREP = 70
    REVISION_DUE = 65
    ASSIGNMENT = 60
    LAB_WORK = 55
    REGULAR_STUDY = 50
    PRACTICE = 45
    REVISION_UPCOMING = 40
    FREE_TIME = 10


async def get_user_schedule_config() -> Dict:
    """
    Get user's schedule configuration from AI memory.
    This allows the AI to adjust the user's preferences over time.
    """
    from database import get_ai_memory

    memories = await get_ai_memory()

    # Extract schedule-related memories
    config = dict(DAILY_ROUTINE_CONFIG)  # Start with defaults

    for mem in memories:
        if mem["category"] == "schedule":
            key = mem["key"]
            try:
                if key == "sleep_start":
                    config["sleep_start"] = mem["value"]
                elif key == "sleep_end":
                    config["sleep_end"] = mem["value"]
                elif key == "preferred_study_times":
                    config["preferred_study_times"] = mem["value"].split(",")
                elif key == "max_study_block_mins":
                    config["max_study_block_mins"] = int(mem["value"])
                elif key == "commute_mins":
                    config["commute_mins"] = int(mem["value"])
            except (ValueError, KeyError):
                pass

    return config


async def generate_optimized_timeline(target_date: date) -> Dict:
    """
    Generate a fully optimized timeline for a specific day.
    Combines fixed events (KU classes), scheduled tasks, and auto-fills gaps.

    Returns a complete day timeline with all activity blocks.
    """
    config = await get_user_schedule_config()
    day_name = target_date.strftime("%A")

    # Build timeline structure
    timeline = []

    # 1. Add sleep block (night before to morning)
    sleep_end = parse_time(config["sleep_end"])
    wake_routine_end_mins = time_to_minutes(sleep_end) + config["wake_routine_mins"]

    timeline.append({
        "type": ActivityType.SLEEP,
        "start": config["sleep_start"],
        "end": config["sleep_end"],
        "duration_mins": 7 * 60,  # Approx
        "label": "Sleep",
        "fixed": True,
        "energy_required": 0
    })

    # 2. Wake routine
    timeline.append({
        "type": ActivityType.WAKE_ROUTINE,
        "start": config["sleep_end"],
        "end": minutes_to_time(wake_routine_end_mins).strftime("%H:%M"),
        "duration_mins": config["wake_routine_mins"],
        "label": "Morning Routine",
        "fixed": True,
        "energy_required": 2
    })

    # 3. Breakfast
    breakfast_start = wake_routine_end_mins
    breakfast_end = breakfast_start + config["breakfast_mins"]
    timeline.append({
        "type": ActivityType.BREAKFAST,
        "start": minutes_to_time(breakfast_start).strftime("%H:%M"),
        "end": minutes_to_time(breakfast_end).strftime("%H:%M"),
        "duration_mins": config["breakfast_mins"],
        "label": "Breakfast",
        "fixed": True,
        "energy_required": 1
    })

    # 4. Add university classes
    timetable = get_timetable_for_day(day_name)
    for cls in timetable:
        start_mins = time_to_minutes(parse_time(cls["start"]))
        end_mins = time_to_minutes(parse_time(cls["end"]))
        timeline.append({
            "type": ActivityType.UNIVERSITY,
            "start": cls["start"],
            "end": cls["end"],
            "duration_mins": end_mins - start_mins,
            "label": f"{cls['subject']} ({cls['type']})",
            "subject": cls["subject"],
            "room": cls["room"],
            "fixed": True,
            "energy_required": 7 if cls["type"] == "lab" else 5
        })

    # 5. Add lunch
    lunch_time = config["lunch_time"]
    lunch_mins = time_to_minutes(parse_time(lunch_time))
    timeline.append({
        "type": ActivityType.LUNCH,
        "start": lunch_time,
        "end": minutes_to_time(lunch_mins + config["lunch_mins"]).strftime("%H:%M"),
        "duration_mins": config["lunch_mins"],
        "label": "Lunch",
        "fixed": True,
        "energy_required": 2
    })

    # 6. Add dinner
    dinner_time = config["dinner_time"]
    dinner_mins = time_to_minutes(parse_time(dinner_time))
    timeline.append({
        "type": ActivityType.DINNER,
        "start": dinner_time,
        "end": minutes_to_time(dinner_mins + config["dinner_mins"]).strftime("%H:%M"),
        "duration_mins": config["dinner_mins"],
        "label": "Dinner",
        "fixed": True,
        "energy_required": 2
    })

    # 7. Add scheduled tasks
    tasks = await db.fetch("""
        SELECT t.*, s.code as subject_code, s.color
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE DATE(t.scheduled_start) = $1
        ORDER BY t.scheduled_start
    """, target_date)

    for task in tasks:
        if task["scheduled_start"]:
            start_t = task["scheduled_start"]
            start_mins = start_t.hour * 60 + start_t.minute
            duration = task["duration_mins"] or 60

            # Determine activity type from task
            task_type = task.get("task_type", "study")
            activity_type = {
                "study": ActivityType.STUDY,
                "revision": ActivityType.REVISION,
                "practice": ActivityType.PRACTICE,
                "assignment": ActivityType.ASSIGNMENT,
                "lab_work": ActivityType.LAB_WORK,
            }.get(task_type, ActivityType.STUDY)

            timeline.append({
                "type": activity_type,
                "start": minutes_to_time(start_mins).strftime("%H:%M"),
                "end": minutes_to_time(start_mins + duration).strftime("%H:%M"),
                "duration_mins": duration,
                "label": task["title"],
                "task_id": task["id"],
                "subject": task.get("subject_code"),
                "is_deep_work": task.get("is_deep_work", False),
                "fixed": False,
                "energy_required": 8 if task.get("is_deep_work") else 5
            })

    # Sort timeline by start time
    def sort_key(block):
        return time_to_minutes(parse_time(block["start"]))

    timeline.sort(key=sort_key)

    # 8. Calculate gaps and suggest optimal activities
    gaps = await analyze_day_gaps(target_date)

    return {
        "date": str(target_date),
        "day": day_name,
        "timeline": timeline,
        "gaps": gaps["gaps"],
        "total_scheduled_mins": sum(b["duration_mins"] for b in timeline),
        "deep_work_scheduled_mins": sum(
            b["duration_mins"] for b in timeline
            if b.get("is_deep_work") or b["type"] == ActivityType.DEEP_WORK
        ),
        "config": config
    }


async def get_pending_work_items(days_ahead: int = 14) -> List[Dict]:
    """
    Get all pending work items that need to be scheduled.
    Includes: revisions, assignments, lab reports, goals with deadlines.
    """
    cutoff = date.today() + timedelta(days=days_ahead)

    # Pending revisions (spaced repetition)
    revisions = await db.fetch("""
        SELECT
            rs.id, rs.chapter_id, rs.revision_number, rs.due_date,
            c.title as chapter_title, c.number as chapter_number,
            s.code as subject_code, s.credits, s.color,
            'revision' as item_type,
            rs.due_date - CURRENT_DATE as days_until
        FROM revision_schedule rs
        JOIN chapters c ON rs.chapter_id = c.id
        JOIN subjects s ON c.subject_id = s.id
        WHERE rs.completed = false
          AND rs.due_date <= $1
        ORDER BY rs.due_date ASC
    """, cutoff)

    # Pending lab reports
    labs = await db.fetch("""
        SELECT
            lr.id, lr.experiment_name, lr.due_date, lr.status,
            s.code as subject_code, s.credits, s.color,
            'lab_report' as item_type,
            lr.due_date - CURRENT_DATE as days_until
        FROM lab_reports lr
        JOIN subjects s ON lr.subject_id = s.id
        WHERE lr.status != 'submitted'
          AND lr.due_date <= $1
        ORDER BY lr.due_date ASC
    """, cutoff)

    # Goals with deadlines
    goals = await db.fetch("""
        SELECT
            sg.id, sg.title, sg.deadline, sg.priority,
            sg.target_value, sg.current_value, sg.unit,
            s.code as subject_code, s.color,
            'goal' as item_type,
            sg.deadline - CURRENT_DATE as days_until
        FROM study_goals sg
        LEFT JOIN subjects s ON sg.subject_id = s.id
        WHERE sg.completed = false
          AND sg.deadline IS NOT NULL
          AND sg.deadline <= $1
        ORDER BY sg.deadline ASC
    """, cutoff)

    # Pending tasks
    tasks = await db.fetch("""
        SELECT
            t.id, t.title, t.task_type, t.priority,
            t.scheduled_start, t.duration_mins,
            s.code as subject_code, s.color,
            'task' as item_type,
            DATE(t.scheduled_start) - CURRENT_DATE as days_until
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE t.status NOT IN ('completed', 'cancelled')
          AND DATE(t.scheduled_start) <= $1
        ORDER BY t.scheduled_start ASC
    """, cutoff)

    # Combine and prioritize
    all_items = []

    for rev in revisions:
        priority = TaskPriority.REVISION_DUE if rev["days_until"] <= 1 else TaskPriority.REVISION_UPCOMING
        all_items.append({
            **dict(rev),
            "computed_priority": priority + (rev["credits"] * 5),
            "estimated_mins": 30  # Revisions are typically 30 mins
        })

    for lab in labs:
        days = lab["days_until"] or 0
        if days < 0:
            priority = TaskPriority.OVERDUE
        elif days == 0:
            priority = TaskPriority.DUE_TODAY
        elif days <= 2:
            priority = TaskPriority.URGENT_LAB
        else:
            priority = TaskPriority.LAB_WORK
        all_items.append({
            **dict(lab),
            "computed_priority": priority,
            "estimated_mins": 120  # Lab reports take ~2 hours
        })

    for goal in goals:
        days = goal["days_until"] or 0
        priority = TaskPriority.DUE_TODAY if days <= 1 else TaskPriority.ASSIGNMENT
        all_items.append({
            **dict(goal),
            "computed_priority": priority,
            "estimated_mins": 60  # Variable, estimate 1 hour
        })

    for task in tasks:
        days = task["days_until"] or 0
        if days < 0:
            priority = TaskPriority.OVERDUE
        elif days == 0:
            priority = TaskPriority.DUE_TODAY
        else:
            priority = TaskPriority.REGULAR_STUDY
        all_items.append({
            **dict(task),
            "computed_priority": priority + (task["priority"] or 5),
            "estimated_mins": task["duration_mins"] or 60
        })

    # Sort by computed priority (highest first)
    all_items.sort(key=lambda x: -x["computed_priority"])

    return all_items


async def backward_plan_deadline(
    deadline_date: date,
    item_type: str,
    subject_code: str,
    total_hours_needed: float,
    item_title: str
) -> Dict:
    """
    Create a backward plan from a deadline.
    Distributes work evenly across available days leading up to the deadline.
    """
    today = date.today()
    days_available = (deadline_date - today).days

    if days_available < 1:
        return {"error": "Deadline is too soon or already passed"}

    total_mins_needed = int(total_hours_needed * 60)

    # Find all available slots between now and deadline
    all_slots = []
    for i in range(days_available):
        target_date = today + timedelta(days=i)
        gaps = await analyze_day_gaps(target_date)

        for gap in gaps["gaps"]:
            if gap["duration_mins"] >= 30:  # Minimum useful block
                all_slots.append({
                    "date": str(target_date),
                    "day": target_date.strftime("%A"),
                    **gap
                })

    # Allocate time across slots (prefer later dates for less stress)
    # Distribute evenly but with increasing intensity closer to deadline
    allocated = []
    remaining_mins = total_mins_needed

    # Calculate ideal daily target (slightly weighted toward end)
    for slot in all_slots:
        if remaining_mins <= 0:
            break

        slot_date = datetime.strptime(slot["date"], "%Y-%m-%d").date()
        days_to_deadline = (deadline_date - slot_date).days

        # Weight: closer to deadline = allocate more
        weight = max(0.5, 1.0 - (days_to_deadline / days_available))
        max_block = min(
            slot["duration_mins"],
            int(total_mins_needed * weight / max(1, days_available // 2)),
            120  # Max 2 hour blocks
        )

        if max_block >= 30:
            allocated.append({
                "date": slot["date"],
                "day": slot["day"],
                "start": slot["start"],
                "duration_mins": max_block,
                "subject": subject_code,
                "title": f"{item_type.replace('_', ' ').title()}: {item_title}",
                "is_deep_work": max_block >= DEEP_WORK_MIN_MINUTES
            })
            remaining_mins -= max_block

    return {
        "success": True,
        "item_type": item_type,
        "subject": subject_code,
        "title": item_title,
        "deadline": str(deadline_date),
        "days_until": days_available,
        "total_needed_mins": total_mins_needed,
        "total_allocated_mins": total_mins_needed - remaining_mins,
        "fully_scheduled": remaining_mins <= 0,
        "blocks": allocated,
        "message": f"Planned {len(allocated)} study blocks for {item_title}"
    }


async def schedule_revision_with_spaced_repetition(
    chapter_id: int,
    intervals: List[int] = None
) -> Dict:
    """
    Schedule revisions for a chapter using spaced repetition.
    Default intervals: 1, 3, 7, 14, 30 days (based on forgetting curve).
    """
    if intervals is None:
        intervals = [1, 3, 7, 14, 30]

    today = date.today()

    # Get chapter info
    chapter = await db.fetch_one("""
        SELECT c.*, s.code as subject_code, s.name as subject_name
        FROM chapters c
        JOIN subjects s ON c.subject_id = s.id
        WHERE c.id = $1
    """, chapter_id)

    if not chapter:
        return {"error": "Chapter not found"}

    # Check existing revisions
    existing = await db.fetch("""
        SELECT * FROM revision_schedule
        WHERE chapter_id = $1 AND completed = false
    """, chapter_id)

    if existing:
        return {
            "message": f"Revisions already scheduled for {chapter['title']}",
            "existing": list(existing)
        }

    # Create revision entries
    created = []
    for i, days in enumerate(intervals):
        rev_date = today + timedelta(days=days)

        revision = await db.execute_returning("""
            INSERT INTO revision_schedule (chapter_id, revision_number, due_date)
            VALUES ($1, $2, $3)
            RETURNING *
        """, chapter_id, i + 1, rev_date)

        created.append({
            "revision_number": i + 1,
            "due_date": str(rev_date),
            "days_from_now": days
        })

    return {
        "success": True,
        "chapter": chapter["title"],
        "subject": chapter["subject_code"],
        "revisions_scheduled": len(created),
        "schedule": created,
        "message": f"Scheduled {len(created)} revisions for {chapter['title']}"
    }


async def allocate_free_time(target_date: date, mins_desired: int = 60) -> Dict:
    """
    Intelligently allocate free time in the schedule.
    Places free time in low-energy periods.
    """
    gaps = await analyze_day_gaps(target_date)
    config = await get_user_schedule_config()

    allocated_free_time = []
    remaining_mins = mins_desired

    for gap in gaps["gaps"]:
        if remaining_mins <= 0:
            break

        # Check energy level for this time slot
        start_hour = int(gap["start"].split(":")[0])
        energy = get_energy_level(start_hour)

        # Prefer low-energy slots for free time
        if energy <= 5 and gap["duration_mins"] >= 30:
            block_mins = min(gap["duration_mins"], remaining_mins, 60)
            allocated_free_time.append({
                "start": gap["start"],
                "duration_mins": block_mins,
                "type": ActivityType.FREE_TIME,
                "label": "Free Time / Relaxation"
            })
            remaining_mins -= block_mins

    return {
        "date": str(target_date),
        "free_time_requested_mins": mins_desired,
        "free_time_allocated_mins": mins_desired - remaining_mins,
        "blocks": allocated_free_time,
        "message": f"Allocated {mins_desired - remaining_mins} mins of free time"
    }


async def optimize_day_schedule(target_date: date) -> Dict:
    """
    Main optimization function - creates the best possible schedule for a day.
    Considers: energy levels, priorities, deadlines, breaks, and preferences.
    """
    config = await get_user_schedule_config()
    day_name = target_date.strftime("%A")

    # Get fixed events
    timetable = get_timetable_for_day(day_name)
    gaps = await analyze_day_gaps(target_date)

    # Get pending work items
    pending_items = await get_pending_work_items(14)

    # Filter items that could be scheduled today
    schedulable = [item for item in pending_items if item["estimated_mins"] > 0]

    # Build optimized schedule
    schedule = []
    remaining_gaps = list(gaps["gaps"])

    for item in schedulable:
        if not remaining_gaps:
            break

        # Find best gap for this item
        best_gap_idx = None
        best_score = -1

        for idx, gap in enumerate(remaining_gaps):
            if gap["duration_mins"] < item["estimated_mins"]:
                continue

            # Score this gap based on:
            # 1. Energy level match
            start_hour = int(gap["start"].split(":")[0])
            energy = get_energy_level(start_hour)

            # High-priority items should go in high-energy slots
            energy_match = 1 - abs((item["computed_priority"] / 100) - (energy / 10))

            # 2. Deep work suitability
            deep_work_bonus = 1.0 if gap["is_deep_work_suitable"] and item["estimated_mins"] >= 60 else 0

            score = energy_match + deep_work_bonus

            if score > best_score:
                best_score = score
                best_gap_idx = idx

        if best_gap_idx is not None:
            gap = remaining_gaps[best_gap_idx]
            duration = min(item["estimated_mins"], gap["duration_mins"], 120)

            schedule.append({
                "item_id": item["id"],
                "item_type": item["item_type"],
                "title": item.get("title") or item.get("chapter_title") or item.get("experiment_name"),
                "subject": item.get("subject_code"),
                "start": gap["start"],
                "duration_mins": duration,
                "priority": item["computed_priority"],
                "is_deep_work": gap["is_deep_work_suitable"] and duration >= 60
            })

            # Update remaining gap
            gap_start_mins = time_to_minutes(parse_time(gap["start"]))
            new_gap_start_mins = gap_start_mins + duration

            if gap["duration_mins"] - duration >= 30:
                remaining_gaps[best_gap_idx] = {
                    **gap,
                    "start": minutes_to_time(new_gap_start_mins).strftime("%H:%M"),
                    "duration_mins": gap["duration_mins"] - duration,
                    "is_deep_work_suitable": (gap["duration_mins"] - duration) >= DEEP_WORK_MIN_MINUTES
                }
            else:
                remaining_gaps.pop(best_gap_idx)

    # Add breaks between long study sessions
    final_schedule = []
    for i, block in enumerate(schedule):
        final_schedule.append(block)

        # Add break after 90+ min blocks
        if block["duration_mins"] >= 90 and i < len(schedule) - 1:
            block_end_mins = time_to_minutes(parse_time(block["start"])) + block["duration_mins"]
            final_schedule.append({
                "item_type": "break",
                "title": "Short Break",
                "start": minutes_to_time(block_end_mins).strftime("%H:%M"),
                "duration_mins": 15,
                "is_deep_work": False
            })

    return {
        "date": str(target_date),
        "day": day_name,
        "timetable": timetable,
        "optimized_schedule": final_schedule,
        "items_scheduled": len(schedule),
        "total_study_mins": sum(b["duration_mins"] for b in schedule if b.get("item_type") != "break"),
        "deep_work_mins": sum(b["duration_mins"] for b in schedule if b.get("is_deep_work")),
        "remaining_gaps": remaining_gaps,
        "unscheduled_items": len(schedulable) - len(schedule)
    }


async def get_weekly_timeline(start_date: Optional[date] = None) -> Dict:
    """Generate optimized timeline for the entire week."""
    if not start_date:
        start_date = date.today()

    weekly_data = []
    total_study_mins = 0
    total_deep_work_mins = 0

    for i in range(7):
        target_date = start_date + timedelta(days=i)
        day_schedule = await optimize_day_schedule(target_date)

        weekly_data.append(day_schedule)
        total_study_mins += day_schedule["total_study_mins"]
        total_deep_work_mins += day_schedule["deep_work_mins"]

    # Get weekly targets
    config = await get_user_schedule_config()
    targets = config.get("weekly_targets", {})

    return {
        "start_date": str(start_date),
        "end_date": str(start_date + timedelta(days=6)),
        "days": weekly_data,
        "summary": {
            "total_study_mins": total_study_mins,
            "total_study_hours": round(total_study_mins / 60, 1),
            "total_deep_work_mins": total_deep_work_mins,
            "deep_work_hours": round(total_deep_work_mins / 60, 1),
            "items_scheduled": sum(d["items_scheduled"] for d in weekly_data)
        },
        "targets": targets,
        "target_met": {
            "study": total_study_mins >= targets.get("study", 20) * 60,
            "deep_work": total_deep_work_mins >= targets.get("revision", 10) * 60
        }
    }


# ============================================
# AI SCHEDULE CONTROL FUNCTIONS
# ============================================

async def ai_create_time_block(
    block_date: date,
    start_time: str,
    duration_mins: int,
    activity_type: str,
    title: str,
    subject_code: Optional[str] = None,
    priority: int = 5
) -> Dict:
    """
    AI tool to create a time block in the schedule.
    This allows the AI to directly control the calendar.
    """
    start_dt = datetime.combine(block_date, parse_time(start_time))

    # Get subject ID if provided
    subject_id = None
    if subject_code:
        subject = await db.fetch_one(
            "SELECT id FROM subjects WHERE code = $1",
            subject_code.upper()
        )
        if subject:
            subject_id = subject["id"]

    # Map activity type to task type
    task_type = {
        "study": "study",
        "revision": "revision",
        "practice": "practice",
        "assignment": "assignment",
        "lab_work": "lab_work",
        "deep_work": "study",
    }.get(activity_type, "study")

    task = await db.execute_returning("""
        INSERT INTO tasks (
            title, subject_id, scheduled_start, duration_mins,
            priority, is_deep_work, task_type
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
    """,
        title,
        subject_id,
        start_dt,
        duration_mins,
        priority,
        duration_mins >= DEEP_WORK_MIN_MINUTES,
        task_type
    )

    return {
        "success": True,
        "task": task,
        "message": f"Created '{title}' on {block_date} at {start_time} for {duration_mins}min"
    }


async def ai_move_time_block(task_id: int, new_date: date, new_start: str) -> Dict:
    """
    AI tool to move a scheduled block to a new time.
    """
    new_start_dt = datetime.combine(new_date, parse_time(new_start))

    task = await db.execute_returning("""
        UPDATE tasks SET
            scheduled_start = $1,
            updated_at = NOW()
        WHERE id = $2
        RETURNING *
    """, new_start_dt, task_id)

    if not task:
        return {"error": "Task not found"}

    return {
        "success": True,
        "task": task,
        "message": f"Moved task to {new_date} at {new_start}"
    }


async def ai_delete_time_block(task_id: int) -> Dict:
    """AI tool to delete a scheduled block."""
    result = await db.execute(
        "DELETE FROM tasks WHERE id = $1 RETURNING id",
        task_id
    )

    if not result:
        return {"error": "Task not found"}

    return {"success": True, "message": f"Deleted task {task_id}"}


async def ai_reschedule_all(reason: str) -> Dict:
    """
    AI tool to reschedule all pending tasks.
    Used when major changes happen (e.g., "I got sick" or "surprise exam").
    """
    today = date.today()

    # Get all pending tasks
    pending = await db.fetch("""
        SELECT t.*, s.code as subject_code
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE t.status = 'pending'
          AND DATE(t.scheduled_start) >= $1
        ORDER BY t.priority DESC, t.scheduled_start
    """, today)

    if not pending:
        return {"message": "No pending tasks to reschedule"}

    # Clear existing schedules for next 7 days
    await db.execute("""
        UPDATE tasks SET scheduled_start = NULL
        WHERE status = 'pending'
          AND DATE(scheduled_start) >= $1
          AND DATE(scheduled_start) <= $1 + INTERVAL '7 days'
    """, today)

    # Re-run optimization for next week
    week_schedule = await get_weekly_timeline(today)

    # Log the reschedule
    await db.execute("""
        INSERT INTO system_logs (level, message, context)
        VALUES ('info', 'AI rescheduled all pending tasks', $1)
    """, {"reason": reason, "tasks_affected": len(pending)})

    return {
        "success": True,
        "tasks_rescheduled": len(pending),
        "reason": reason,
        "new_schedule": week_schedule,
        "message": f"Rescheduled {len(pending)} tasks due to: {reason}"
    }


async def ai_update_schedule_preference(key: str, value: str) -> Dict:
    """
    AI tool to update user's schedule preferences.
    Stores in long-term memory so preferences persist.
    """
    from database import save_ai_memory

    valid_keys = [
        "sleep_start", "sleep_end", "preferred_study_times",
        "max_study_block_mins", "commute_mins", "wake_time",
        "lunch_time", "dinner_time"
    ]

    if key not in valid_keys:
        return {"error": f"Invalid preference key. Valid keys: {valid_keys}"}

    await save_ai_memory("schedule", key, value)

    return {
        "success": True,
        "preference": key,
        "value": value,
        "message": f"Updated schedule preference: {key} = {value}"
    }


async def ai_get_schedule_context() -> Dict:
    """
    AI tool to get full scheduling context.
    Used by AI to understand current situation before making decisions.
    """
    today = date.today()

    # Today's schedule
    today_schedule = await get_today_at_glance()

    # Pending items
    pending = await get_pending_work_items(7)

    # Weekly load
    week_stats = await db.fetch_one("""
        SELECT
            COUNT(*) as total_tasks,
            SUM(duration_mins) as total_mins,
            SUM(CASE WHEN is_deep_work THEN duration_mins ELSE 0 END) as deep_work_mins
        FROM tasks
        WHERE status = 'pending'
          AND DATE(scheduled_start) >= $1
          AND DATE(scheduled_start) <= $1 + INTERVAL '7 days'
    """, today)

    # User preferences
    config = await get_user_schedule_config()

    return {
        "today": today_schedule,
        "pending_items": pending[:10],  # Top 10 most urgent
        "pending_count": len(pending),
        "week_stats": week_stats,
        "preferences": config,
        "current_time": datetime.now().strftime("%H:%M"),
        "current_energy": get_energy_level(datetime.now().hour)
    }
