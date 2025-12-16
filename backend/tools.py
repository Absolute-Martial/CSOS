"""
Personal Engineering OS - AI Tools
Function definitions for copilot-api tool calling
"""

import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from database import (
    get_all_subjects, get_subject_by_code, create_subject,
    get_chapters_by_subject, create_chapter, update_chapter_progress, get_chapter,
    get_tasks_today, create_task, update_task, delete_task,
    get_lab_reports, create_lab_report,
    get_pending_revisions, complete_revision,
    get_streak, add_points,
    get_ai_memory, save_ai_memory, get_ai_guidelines, add_ai_guideline,
    create_notification, get_unread_notifications
)


# Base upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
ENGINE_PATH = os.getenv("ENGINE_PATH", "../engine/scheduler")


# ============================================
# TOOL DEFINITIONS (for AI to call)
# ============================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "edit_schedule",
            "description": "Add, update, or remove tasks from the schedule. Use for schedule modifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "update", "delete"],
                        "description": "Action to perform"
                    },
                    "task_id": {
                        "type": "integer",
                        "description": "Task ID (for update/delete)"
                    },
                    "title": {"type": "string", "description": "Task title"},
                    "subject_code": {"type": "string", "description": "Subject code like MATH101"},
                    "scheduled_start": {"type": "string", "description": "ISO datetime"},
                    "duration_mins": {"type": "integer", "description": "Duration in minutes"},
                    "priority": {"type": "integer", "description": "1-10, higher = more important"}
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_gaps",
            "description": "Find deep work gaps (>90 mins) in today's schedule using the C engine.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lab_status",
            "description": "Get status of lab reports for PHYS, CHEM, or Thermal Science.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {
                        "type": "string",
                        "description": "Optional: filter by subject code"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "update_chapter_progress",
            "description": "Update reading, assignment, or mastery status for a chapter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {"type": "string", "description": "Subject code like PHYS102"},
                    "chapter_number": {"type": "integer", "description": "Chapter number"},
                    "reading_status": {
                        "type": "string",
                        "enum": ["not_started", "in_progress", "completed"]
                    },
                    "assignment_status": {
                        "type": "string",
                        "enum": ["locked", "available", "in_progress", "submitted"]
                    },
                    "mastery_level": {"type": "integer", "description": "0-100"}
                },
                "required": ["subject_code", "chapter_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_revision_queue",
            "description": "Get pending chapter revisions sorted by credit priority.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_revision",
            "description": "Mark a revision as complete and award points.",
            "parameters": {
                "type": "object",
                "properties": {
                    "revision_id": {"type": "integer", "description": "Revision ID"}
                },
                "required": ["revision_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save information to long-term memory for future reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category like 'preference', 'pattern', 'context'"
                    },
                    "key": {"type": "string", "description": "Memory key"},
                    "value": {"type": "string", "description": "Value to remember"}
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_memory",
            "description": "Retrieve all stored memories.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_guideline",
            "description": "Add a new rule for the AI to follow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string", "description": "The rule text"},
                    "priority": {"type": "integer", "description": "1-10, lower = more important"}
                },
                "required": ["rule"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_guidelines",
            "description": "List all active AI guidelines.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder_supervised",
            "description": "Create a folder structure for subjects/chapters. Always confirms naming convention.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {"type": "string", "description": "Subject code like MATH101"},
                    "chapter_number": {"type": "integer", "description": "Chapter number"},
                    "chapter_title": {"type": "string", "description": "Chapter title"}
                },
                "required": ["subject_code", "chapter_number", "chapter_title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Queue a notification for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["due_date", "revision", "streak_warning", "achievement"]
                    },
                    "title": {"type": "string"},
                    "message": {"type": "string"},
                    "due_at": {"type": "string", "description": "ISO datetime"}
                },
                "required": ["type", "title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_streak_status",
            "description": "Get current streak and points status.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "morning_briefing",
            "description": "Get a summary of today's priorities, due dates, and streak status.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    # ============================================
    # STUDY TIMER TOOLS
    # ============================================
    {
        "type": "function",
        "function": {
            "name": "start_study_timer",
            "description": "Start a study timer. Use when user says 'I'm studying X' or 'Start timer for X'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {"type": "string", "description": "Subject code like MATH101"},
                    "chapter_number": {"type": "integer", "description": "Optional chapter number"},
                    "title": {"type": "string", "description": "Custom session title"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_study_timer",
            "description": "Stop the current study timer and record the session.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_timer_status",
            "description": "Get the status of the current study timer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_study_stats",
            "description": "Get study time statistics and analytics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days to analyze (default 7)"}
                },
                "required": []
            }
        }
    },
    # ============================================
    # SCHEDULER & CALENDAR TOOLS
    # ============================================
    {
        "type": "function",
        "function": {
            "name": "get_today_schedule",
            "description": "Get today's complete schedule including KU timetable, tasks, and available gaps.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_week_schedule",
            "description": "Get the full week's schedule with timetable, tasks, and gap analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "ISO date to start from (default: today)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_deep_work_slots",
            "description": "Find available deep work slots (90+ min blocks) in the upcoming days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days to look ahead (default 7)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_event_prep",
            "description": "Schedule study blocks for an upcoming test, assignment, or deadline. AI redistributes your schedule automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_type": {
                        "type": "string",
                        "enum": ["test", "quiz", "assignment", "lab_report", "project", "exam"],
                        "description": "Type of event to prepare for"
                    },
                    "subject_code": {"type": "string", "description": "Subject code like CHEM103"},
                    "event_date": {"type": "string", "description": "ISO date of the event"},
                    "apply_immediately": {"type": "boolean", "description": "Create tasks immediately (default: false, just shows plan)"}
                },
                "required": ["event_type", "subject_code", "event_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_lab_reports",
            "description": "Get pending lab reports with countdown to deadlines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {"type": "string", "description": "Filter by subject code"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_lab_report",
            "description": "Add a new lab report to track.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {"type": "string", "description": "Subject code like PHYS102"},
                    "experiment_name": {"type": "string", "description": "Name of the experiment"},
                    "due_date": {"type": "string", "description": "ISO date when report is due"},
                    "lab_date": {"type": "string", "description": "ISO date when lab was performed"}
                },
                "required": ["subject_code", "experiment_name", "due_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_lab_report",
            "description": "Update lab report status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_id": {"type": "integer", "description": "Lab report ID"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "draft_complete", "submitted"]
                    },
                    "notes": {"type": "string", "description": "Optional notes"}
                },
                "required": ["report_id", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_upcoming_deadlines",
            "description": "Get all upcoming deadlines (lab reports, assignments, goals) in the next N days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Days to look ahead (default 7)"}
                },
                "required": []
            }
        }
    },
    # ============================================
    # STUDY GOALS TOOLS
    # ============================================
    {
        "type": "function",
        "function": {
            "name": "create_study_goal",
            "description": "Create a new study goal with optional target and deadline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Goal title"},
                    "category": {"type": "string", "enum": ["Academic", "Skill Building", "Personal", "Career"]},
                    "subject_code": {"type": "string", "description": "Optional: link to subject"},
                    "description": {"type": "string"},
                    "target_value": {"type": "integer", "description": "Target to reach"},
                    "unit": {"type": "string", "description": "Unit of measurement (chapters, hours, etc.)"},
                    "deadline": {"type": "string", "description": "ISO date for deadline"},
                    "priority": {"type": "integer", "description": "1-10, higher = more important"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_goal_progress",
            "description": "Update progress on a study goal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "integer", "description": "Goal ID"},
                    "progress_delta": {"type": "integer", "description": "Amount to add to progress"},
                    "set_value": {"type": "integer", "description": "Directly set progress value"},
                    "mark_complete": {"type": "boolean", "description": "Mark goal as complete"}
                },
                "required": ["goal_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_goals",
            "description": "Get list of study goals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"},
                    "include_completed": {"type": "boolean", "description": "Include completed goals"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_goals_summary",
            "description": "Get summary of goal completion statistics.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    # ============================================
    # AI SCHEDULE CONTROL TOOLS (Full Calendar Access)
    # ============================================
    {
        "type": "function",
        "function": {
            "name": "create_time_block",
            "description": "Create a new time block in the schedule. Use this to add study sessions, revision blocks, assignments, or any scheduled activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "ISO date for the block (YYYY-MM-DD)"},
                    "start_time": {"type": "string", "description": "Start time in HH:MM format (24-hour)"},
                    "duration_mins": {"type": "integer", "description": "Duration in minutes"},
                    "activity_type": {
                        "type": "string",
                        "enum": ["study", "revision", "practice", "assignment", "lab_work", "deep_work", "break", "free_time"],
                        "description": "Type of activity"
                    },
                    "title": {"type": "string", "description": "Title/description of the block"},
                    "subject_code": {"type": "string", "description": "Optional subject code (e.g., MATH101)"},
                    "priority": {"type": "integer", "description": "Priority 1-10 (default 5)"}
                },
                "required": ["date", "start_time", "duration_mins", "activity_type", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_time_block",
            "description": "Move an existing scheduled block to a different time/date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task/block to move"},
                    "new_date": {"type": "string", "description": "New date (YYYY-MM-DD)"},
                    "new_start_time": {"type": "string", "description": "New start time (HH:MM)"}
                },
                "required": ["task_id", "new_date", "new_start_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_time_block",
            "description": "Delete a scheduled block from the calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task/block to delete"}
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_optimized_schedule",
            "description": "Get AI-optimized schedule for a specific day. Returns the best arrangement of tasks based on energy levels, priorities, and deadlines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date to optimize (YYYY-MM-DD). Defaults to today."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weekly_timeline",
            "description": "Get optimized timeline for the entire week with all scheduled blocks, gaps, and recommendations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD). Defaults to today."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_all",
            "description": "Reschedule all pending tasks when major changes occur. Use when user says 'I got sick', 'cancel today', 'surprise exam', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for rescheduling (e.g., 'user is sick', 'surprise exam announced')"}
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "backward_plan",
            "description": "Create a backward plan from a deadline. Distributes study time across available days leading up to a deadline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "deadline_date": {"type": "string", "description": "Deadline date (YYYY-MM-DD)"},
                    "item_type": {"type": "string", "enum": ["assignment", "lab_report", "exam", "project", "test"], "description": "Type of deadline"},
                    "subject_code": {"type": "string", "description": "Subject code (e.g., CHEM103)"},
                    "hours_needed": {"type": "number", "description": "Estimated hours needed to complete"},
                    "title": {"type": "string", "description": "Title/name of the item"}
                },
                "required": ["deadline_date", "item_type", "subject_code", "hours_needed", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_chapter_revision",
            "description": "Schedule spaced repetition revisions for a chapter. Creates revision entries at optimal intervals (1, 3, 7, 14, 30 days).",
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter_id": {"type": "integer", "description": "Chapter ID to schedule revisions for"},
                    "intervals": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Custom intervals in days (default: [1, 3, 7, 14, 30])"
                    }
                },
                "required": ["chapter_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "allocate_free_time",
            "description": "Intelligently allocate free/relaxation time in the schedule. Places breaks in low-energy periods.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date to allocate free time (YYYY-MM-DD)"},
                    "minutes": {"type": "integer", "description": "Minutes of free time desired (default 60)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_schedule_preference",
            "description": "Update user's schedule preferences (stored in long-term memory). Use when user says things like 'I wake up at 5am' or 'I prefer studying in the morning'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "enum": ["sleep_start", "sleep_end", "preferred_study_times", "max_study_block_mins", "commute_mins", "wake_time", "lunch_time", "dinner_time"],
                        "description": "Preference key to update"
                    },
                    "value": {"type": "string", "description": "New value (times in HH:MM format, preferences comma-separated)"}
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_schedule_context",
            "description": "Get full scheduling context including today's schedule, pending items, weekly stats, and user preferences. Use this before making scheduling decisions.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending_items",
            "description": "Get all pending work items (revisions, lab reports, assignments, goals) sorted by priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {"type": "integer", "description": "Days to look ahead (default 14)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_full_timeline",
            "description": "Get complete day timeline with all blocks (sleep, meals, classes, study, breaks, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date to get timeline for (YYYY-MM-DD)"}
                },
                "required": []
            }
        }
    },
    # ============================================
    # ENHANCED AI MEMORY TOOLS
    # ============================================
    {
        "type": "function",
        "function": {
            "name": "remember_user_info",
            "description": "Store important information about the user for long-term memory. Use this when user shares preferences, habits, constraints, or personal info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["preference", "habit", "constraint", "goal", "personal", "schedule", "academic"],
                        "description": "Category of information"
                    },
                    "key": {"type": "string", "description": "Short key for this memory (e.g., 'wake_time', 'favorite_subject')"},
                    "value": {"type": "string", "description": "The information to remember"},
                    "importance": {"type": "string", "enum": ["low", "medium", "high"], "description": "How important this is to remember"}
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memories",
            "description": "Recall stored memories about the user. Use this to personalize responses and scheduling decisions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category (optional)"},
                    "search_key": {"type": "string", "description": "Search for specific key (optional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "forget_memory",
            "description": "Remove a specific memory. Use when user says 'forget that' or information is outdated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category of the memory"},
                    "key": {"type": "string", "description": "Key of the memory to forget"}
                },
                "required": ["category", "key"]
            }
        }
    },
    # ============================================
    # PROACTIVE NOTIFICATION TOOLS
    # ============================================
    {
        "type": "function",
        "function": {
            "name": "send_proactive_notification",
            "description": "Send a proactive notification to the user. Use this for reminders, suggestions, achievements, or warnings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notification_type": {
                        "type": "string",
                        "enum": ["reminder", "suggestion", "achievement", "warning", "motivation"],
                        "description": "Type of notification"
                    },
                    "title": {"type": "string", "description": "Short notification title"},
                    "message": {"type": "string", "description": "Detailed notification message"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "description": "Notification priority (default: normal)"
                    },
                    "action_url": {"type": "string", "description": "Optional URL for action button"},
                    "action_label": {"type": "string", "description": "Label for action button"}
                },
                "required": ["notification_type", "title", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": "Schedule a reminder notification for a future time. Use when user says 'remind me to...' or you want to schedule a future notification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Reminder title"},
                    "message": {"type": "string", "description": "Reminder message"},
                    "scheduled_time": {"type": "string", "description": "ISO datetime when to send the reminder"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "description": "Reminder priority"
                    }
                },
                "required": ["title", "message", "scheduled_time"]
            }
        }
    }
]


# ============================================
# TOOL IMPLEMENTATIONS
# ============================================

async def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name and return the result."""

    handlers = {
        "edit_schedule": tool_edit_schedule,
        "analyze_gaps": tool_analyze_gaps,
        "get_lab_status": tool_get_lab_status,
        "update_chapter_progress": tool_update_chapter_progress,
        "get_revision_queue": tool_get_revision_queue,
        "complete_revision": tool_complete_revision,
        "save_memory": tool_save_memory,
        "get_memory": tool_get_memory,
        "add_guideline": tool_add_guideline,
        "list_guidelines": tool_list_guidelines,
        "create_folder_supervised": tool_create_folder_supervised,
        "send_notification": tool_send_notification,
        "get_streak_status": tool_get_streak_status,
        "morning_briefing": tool_morning_briefing,
        # Timer tools
        "start_study_timer": tool_start_study_timer,
        "stop_study_timer": tool_stop_study_timer,
        "get_timer_status": tool_get_timer_status,
        "get_study_stats": tool_get_study_stats,
        # Scheduler tools
        "get_today_schedule": tool_get_today_schedule,
        "get_week_schedule": tool_get_week_schedule,
        "find_deep_work_slots": tool_find_deep_work_slots,
        "schedule_event_prep": tool_schedule_event_prep,
        "get_lab_reports": tool_get_lab_reports_tool,
        "add_lab_report": tool_add_lab_report,
        "update_lab_report": tool_update_lab_report,
        "get_upcoming_deadlines": tool_get_upcoming_deadlines,
        # Goal tools
        "create_study_goal": tool_create_study_goal,
        "update_goal_progress": tool_update_goal_progress,
        "get_goals": tool_get_goals,
        "get_goals_summary": tool_get_goals_summary,
        # AI Schedule Control tools
        "create_time_block": tool_create_time_block,
        "move_time_block": tool_move_time_block,
        "delete_time_block": tool_delete_time_block,
        "get_optimized_schedule": tool_get_optimized_schedule,
        "get_weekly_timeline": tool_get_weekly_timeline_schedule,
        "reschedule_all": tool_reschedule_all,
        "backward_plan": tool_backward_plan,
        "schedule_chapter_revision": tool_schedule_chapter_revision,
        "allocate_free_time": tool_allocate_free_time,
        "update_schedule_preference": tool_update_schedule_preference,
        "get_schedule_context": tool_get_schedule_context,
        "get_pending_items": tool_get_pending_items,
        "get_full_timeline": tool_get_full_timeline,
        # Enhanced AI Memory tools
        "remember_user_info": tool_remember_user_info,
        "recall_memories": tool_recall_memories,
        "forget_memory": tool_forget_memory,
        # Proactive Notification tools
        "send_proactive_notification": tool_send_proactive_notification,
        "schedule_reminder": tool_schedule_reminder,
    }
    
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unknown tool: {name}"}
    
    try:
        return await handler(arguments)
    except Exception as e:
        return {"error": str(e)}


async def tool_edit_schedule(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add, update, or delete schedule tasks."""
    action = args.get("action")
    
    if action == "add":
        task = await create_task({
            "title": args.get("title", "Untitled Task"),
            "subject_id": None,  # Will resolve from subject_code if needed
            "scheduled_start": args.get("scheduled_start"),
            "duration_mins": args.get("duration_mins", 60),
            "priority": args.get("priority", 5),
            "is_deep_work": args.get("duration_mins", 60) >= 90
        })
        return {"success": True, "task": task, "message": f"Task '{task['title']}' added"}
    
    elif action == "update":
        task_id = args.get("task_id")
        updates = {k: v for k, v in args.items() if k not in ["action", "task_id"] and v is not None}
        task = await update_task(task_id, **updates)
        return {"success": True, "task": task, "message": "Task updated"}
    
    elif action == "delete":
        task_id = args.get("task_id")
        success = await delete_task(task_id)
        return {"success": success, "message": "Task deleted" if success else "Task not found"}
    
    return {"error": "Invalid action"}


async def tool_analyze_gaps(args: Dict[str, Any]) -> Dict[str, Any]:
    """Call C engine to analyze deep work gaps."""
    try:
        result = subprocess.run(
            [ENGINE_PATH, "--analyze-gaps", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            gaps = json.loads(result.stdout)
            return {"success": True, "gaps": gaps}
        else:
            return {"success": False, "error": result.stderr}
    except FileNotFoundError:
        # Fallback: return mock data if engine not compiled
        return {
            "success": True,
            "gaps": {
                "gaps": [
                    {"start": "04:30", "end": "08:00", "duration_mins": 210},
                    {"start": "14:00", "end": "16:30", "duration_mins": 150}
                ],
                "count": 2
            },
            "note": "Using mock data - compile C engine for real analysis"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def tool_get_lab_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get lab report status."""
    reports = await get_lab_reports(status="pending")
    
    subject_code = args.get("subject_code")
    if subject_code:
        reports = [r for r in reports if r.get("subject_code") == subject_code]
    
    return {
        "success": True,
        "reports": reports,
        "count": len(reports)
    }


async def tool_update_chapter_progress(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update chapter progress."""
    subject = await get_subject_by_code(args["subject_code"])
    if not subject:
        return {"error": f"Subject {args['subject_code']} not found"}
    
    chapters = await get_chapters_by_subject(subject["id"])
    chapter = next((c for c in chapters if c["number"] == args["chapter_number"]), None)
    
    if not chapter:
        return {"error": f"Chapter {args['chapter_number']} not found"}
    
    updates = {}
    if "reading_status" in args:
        updates["reading_status"] = args["reading_status"]
    if "assignment_status" in args:
        updates["assignment_status"] = args["assignment_status"]
    if "mastery_level" in args:
        updates["mastery_level"] = args["mastery_level"]
    
    result = await update_chapter_progress(chapter["id"], **updates)
    
    # Award points for completion
    if args.get("reading_status") == "completed":
        await add_points(10)
    if args.get("assignment_status") == "submitted":
        await add_points(20)
    
    return {"success": True, "progress": result, "message": "Chapter progress updated"}


async def tool_get_revision_queue(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get pending revisions sorted by priority."""
    revisions = await get_pending_revisions()
    return {
        "success": True,
        "revisions": revisions,
        "count": len(revisions)
    }


async def tool_complete_revision(args: Dict[str, Any]) -> Dict[str, Any]:
    """Mark revision complete and award points."""
    revision = await complete_revision(args["revision_id"], points=15)
    await add_points(15)
    
    streak = await get_streak()
    
    return {
        "success": True,
        "revision": revision,
        "points_earned": 15,
        "current_streak": streak["current_streak"],
        "total_points": streak["total_points"]
    }


async def tool_save_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save to long-term memory."""
    memory = await save_ai_memory(
        args["category"],
        args["key"],
        args["value"]
    )
    return {"success": True, "memory": memory, "message": "Memory saved"}


async def tool_get_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all memories."""
    memories = await get_ai_memory()
    return {"success": True, "memories": memories}


async def tool_add_guideline(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add new AI guideline."""
    guideline = await add_ai_guideline(
        args["rule"],
        args.get("priority", 5)
    )
    return {"success": True, "guideline": guideline, "message": "Guideline added"}


async def tool_list_guidelines(args: Dict[str, Any]) -> Dict[str, Any]:
    """List all guidelines."""
    guidelines = await get_ai_guidelines()
    return {"success": True, "guidelines": guidelines}


async def tool_create_folder_supervised(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create folder structure with AI-supervised naming."""
    subject_code = args["subject_code"].upper()
    chapter_num = args["chapter_number"]
    chapter_title = args["chapter_title"]
    
    # Validate naming convention
    import re
    if not re.match(r"^[A-Z]{4}[0-9]{3}$", subject_code):
        return {"error": f"Invalid subject code format: {subject_code}. Use format like MATH101"}
    
    # Create folder structure
    folder_name = f"chapter{chapter_num:02d}"
    base_path = os.path.join(UPLOAD_DIR, subject_code, folder_name)
    
    subdirs = ["slides", "assignments", "notes"]
    created_paths = []
    
    for subdir in subdirs:
        path = os.path.join(base_path, subdir)
        os.makedirs(path, exist_ok=True)
        created_paths.append(path)
    
    # Create chapter in database
    subject = await get_subject_by_code(subject_code)
    if subject:
        await create_chapter(subject["id"], chapter_num, chapter_title, base_path)
    
    return {
        "success": True,
        "folder_path": base_path,
        "created": created_paths,
        "message": f"Created folder structure for {subject_code} Chapter {chapter_num}"
    }


async def tool_send_notification(args: Dict[str, Any]) -> Dict[str, Any]:
    """Queue a notification."""
    notification = await create_notification(
        args["type"],
        args["title"],
        args["message"],
        args.get("due_at")
    )
    return {"success": True, "notification": notification}


async def tool_get_streak_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get streak status."""
    streak = await get_streak()
    return {"success": True, "streak": streak}


async def tool_morning_briefing(args: Dict[str, Any]) -> Dict[str, Any]:
    """Generate morning briefing."""
    tasks = await get_tasks_today()
    revisions = await get_pending_revisions()
    streak = await get_streak()
    notifications = await get_unread_notifications()
    
    # Calculate available deep work time
    # This would normally come from C engine
    deep_work_mins = 360  # Mock: 6 hours
    
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning! ☀️"
    elif hour < 17:
        greeting = "Good afternoon! 🌤️"
    else:
        greeting = "Good evening! 🌙"
    
    return {
        "success": True,
        "briefing": {
            "greeting": greeting,
            "current_streak": streak["current_streak"],
            "streak_icon": "🔥" if streak["current_streak"] >= 3 else "",
            "tasks_today": len(tasks),
            "revisions_due": len([r for r in revisions if str(r.get("due_date")) == str(datetime.now().date())]),
            "deep_work_available": deep_work_mins,
            "unread_notifications": len(notifications),
            "next_reward": streak.get("next_reward"),
            "points_to_next": streak.get("points_to_next")
        }
    }


# ============================================
# SYSTEM PROMPT BUILDER
# ============================================

async def build_system_prompt() -> str:
    """Build system prompt with guidelines and memory."""

    guidelines = await get_ai_guidelines()
    memories = await get_ai_memory()

    guidelines_text = "\n".join([f"- {g['rule']}" for g in guidelines])
    memories_text = "\n".join([f"- {m['category']}/{m['key']}: {m['value']}" for m in memories])

    return f"""You are the AI assistant for a Personal Engineering OS, helping a KU CS student manage their studies.

## Your Guidelines (MUST FOLLOW):
{guidelines_text}

## What You Remember About This User:
{memories_text}

## Available Tools:

### Core Tools:
- edit_schedule: Add/update/delete tasks
- analyze_gaps: Find deep work opportunities
- get_lab_status: Check lab report deadlines
- update_chapter_progress: Update study progress
- get_revision_queue: See pending revisions
- complete_revision: Mark revision done
- save_memory: Remember something for later
- add_guideline: Add a new rule for yourself
- create_folder_supervised: Create organized folders
- send_notification: Notify user about something
- morning_briefing: Get daily summary

### Schedule Control Tools (AI has FULL control):
- create_time_block: Create new study/revision/assignment blocks in calendar
- move_time_block: Move existing blocks to new times
- delete_time_block: Remove blocks from schedule
- get_optimized_schedule: Get AI-optimized day schedule
- get_weekly_timeline: Get full week optimization
- reschedule_all: Reschedule everything (use when plans change drastically)
- backward_plan: Plan backward from a deadline
- schedule_chapter_revision: Set up spaced repetition (1, 3, 7, 14, 30 days)
- allocate_free_time: Add relaxation blocks intelligently
- update_schedule_preference: Update user preferences (sleep time, etc.)
- get_schedule_context: Get full context before making decisions
- get_pending_items: See all pending work sorted by priority
- get_full_timeline: Get complete day with all blocks

### Scheduler Tools:
- get_today_schedule: Full view of today (KU timetable + tasks + gaps)
- get_week_schedule: Week view with gap analysis
- find_deep_work_slots: Find 90+ min blocks for deep work
- schedule_event_prep: "I have a test on Friday" -> auto-schedule study blocks
- get_lab_reports: Lab report countdown (Physics, Chemistry, Thermal)
- add_lab_report / update_lab_report: Track lab report progress
- get_upcoming_deadlines: All upcoming due dates

### Timer Tools:
- start_study_timer/stop_study_timer: Track study sessions
- get_study_stats: View study time analytics

### Goal Tools:
- create_study_goal: Set study goals with targets
- update_goal_progress: Track goal progress
- get_goals/get_goals_summary: View goals and stats

### Long-Term Memory Tools:
- remember_user_info: Store user preferences, habits, constraints
- recall_memories: Retrieve stored information
- forget_memory: Remove outdated information

### Proactive Notification Tools:
- send_proactive_notification: Send immediate notifications (reminders, suggestions, achievements, warnings, motivation)
- schedule_reminder: Schedule future reminders ("remind me to...")

## Naming Conventions You Enforce:
- Subjects: UPPERCASE + number (MATH101, PHYS102)
- Chapters: chapter + 2 digits (chapter01)
- Files: snake_case (lecture_notes.pdf)

## Smart Scheduling Behavior:
1. When user mentions a surprise test/exam/assignment, IMMEDIATELY use schedule_event_prep or backward_plan
2. When user shares preferences ("I wake up at 5am"), use update_schedule_preference to store it
3. Use get_schedule_context before making complex scheduling decisions
4. Schedule difficult tasks in high-energy periods (8-10am, 4-6pm), easy tasks in low-energy periods
5. Always add breaks after 90+ min deep work sessions
6. Remember user's patterns and adapt scheduling over time

Always be helpful, proactive about study habits, and encouraging about streaks!
"""


# ============================================
# TIMER TOOL IMPLEMENTATIONS
# ============================================

async def tool_start_study_timer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Start a study timer."""
    from timer import start_timer, get_active_timer
    from database import get_subject_by_code, get_chapters_by_subject

    subject_id = None
    chapter_id = None

    # Resolve subject code to ID
    if args.get("subject_code"):
        subject = await get_subject_by_code(args["subject_code"].upper())
        if subject:
            subject_id = subject["id"]

            # Resolve chapter number to ID if provided
            if args.get("chapter_number"):
                chapters = await get_chapters_by_subject(subject_id)
                chapter = next(
                    (c for c in chapters if c["number"] == args["chapter_number"]),
                    None
                )
                if chapter:
                    chapter_id = chapter["id"]

    return await start_timer(
        subject_id=subject_id,
        chapter_id=chapter_id,
        title=args.get("title")
    )


async def tool_stop_study_timer(args: Dict[str, Any]) -> Dict[str, Any]:
    """Stop the current study timer."""
    from timer import stop_timer
    return await stop_timer()


async def tool_get_timer_status(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get current timer status."""
    from timer import get_active_timer

    active = await get_active_timer()
    if not active:
        return {"success": True, "running": False, "message": "No timer running"}

    # Format elapsed time
    elapsed = active.get("elapsed_seconds", 0)
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60

    return {
        "success": True,
        "running": True,
        "elapsed_seconds": elapsed,
        "elapsed_formatted": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
        "subject_code": active.get("subject_code"),
        "title": active.get("title"),
        "started_at": str(active.get("started_at"))
    }


async def tool_get_study_stats(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get study time statistics."""
    from timer import get_study_analytics

    days = args.get("days", 7)
    return await get_study_analytics(days)


# ============================================
# SCHEDULER TOOL IMPLEMENTATIONS
# ============================================

async def tool_get_today_schedule(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get today's complete schedule."""
    from scheduler import get_today_at_glance
    return await get_today_at_glance()


async def tool_get_week_schedule(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get the full week's schedule."""
    from scheduler import get_week_schedule
    from datetime import datetime

    start_date = None
    if args.get("start_date"):
        try:
            start_date = datetime.fromisoformat(args["start_date"]).date()
        except ValueError:
            pass

    return await get_week_schedule(start_date)


async def tool_find_deep_work_slots(args: Dict[str, Any]) -> Dict[str, Any]:
    """Find deep work opportunities."""
    from scheduler import find_deep_work_slots

    days = args.get("days", 7)
    slots = await find_deep_work_slots(days)

    return {
        "success": True,
        "slots": slots,
        "count": len(slots),
        "message": f"Found {len(slots)} deep work slots in the next {days} days"
    }


async def tool_schedule_event_prep(args: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule study blocks for an upcoming event."""
    from scheduler import redistribute_schedule, apply_redistribution
    from datetime import datetime

    event_date = datetime.fromisoformat(args["event_date"]).date()

    plan = await redistribute_schedule(
        event_type=args["event_type"],
        event_subject=args["subject_code"].upper(),
        event_date=event_date,
        priority=8
    )

    if args.get("apply_immediately") and plan.get("success"):
        result = await apply_redistribution(plan["blocks"])
        plan["applied"] = True
        plan["tasks_created"] = result["tasks_created"]

    return plan


async def tool_get_lab_reports_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get pending lab reports with countdown."""
    from scheduler import get_lab_report_countdown

    reports = await get_lab_report_countdown()

    if args.get("subject_code"):
        reports = [r for r in reports if r.get("subject_code") == args["subject_code"].upper()]

    return {
        "success": True,
        "reports": reports,
        "count": len(reports),
        "urgent_count": len([r for r in reports if r["urgency"] in ("overdue", "urgent")])
    }


async def tool_add_lab_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new lab report to track."""
    from scheduler import create_lab_report_entry
    from datetime import datetime

    due_date = datetime.fromisoformat(args["due_date"]).date()
    lab_date = None
    if args.get("lab_date"):
        lab_date = datetime.fromisoformat(args["lab_date"]).date()

    return await create_lab_report_entry(
        subject_code=args["subject_code"],
        experiment_name=args["experiment_name"],
        due_date=due_date,
        lab_date=lab_date
    )


async def tool_update_lab_report(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update lab report status."""
    from scheduler import update_lab_report_status

    return await update_lab_report_status(
        report_id=args["report_id"],
        status=args["status"],
        notes=args.get("notes")
    )


async def tool_get_upcoming_deadlines(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all upcoming deadlines."""
    from scheduler import get_upcoming_deadlines as fetch_deadlines

    days = args.get("days", 7)
    deadlines = await fetch_deadlines(days)

    return {
        "success": True,
        "deadlines": deadlines,
        "count": len(deadlines),
        "message": f"{len(deadlines)} deadlines in the next {days} days"
    }


# ============================================
# GOAL TOOL IMPLEMENTATIONS
# ============================================

async def tool_create_study_goal(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new study goal."""
    from goals import create_goal, get_goal_categories
    from database import get_subject_by_code
    from datetime import datetime

    # Resolve category name to ID
    category_id = None
    if args.get("category"):
        categories = await get_goal_categories()
        cat = next((c for c in categories if c["name"] == args["category"]), None)
        if cat:
            category_id = cat["id"]

    # Resolve subject code to ID
    subject_id = None
    if args.get("subject_code"):
        subject = await get_subject_by_code(args["subject_code"].upper())
        if subject:
            subject_id = subject["id"]

    # Parse deadline
    deadline = None
    if args.get("deadline"):
        try:
            deadline = datetime.fromisoformat(args["deadline"]).date()
        except ValueError:
            pass

    goal = await create_goal(
        title=args["title"],
        category_id=category_id,
        subject_id=subject_id,
        description=args.get("description"),
        target_value=args.get("target_value"),
        unit=args.get("unit"),
        deadline=deadline,
        priority=args.get("priority", 5)
    )

    return {
        "success": True,
        "goal": goal,
        "message": f"Created goal: {args['title']}"
    }


async def tool_update_goal_progress(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update progress on a study goal."""
    from goals import update_goal_progress

    return await update_goal_progress(
        goal_id=args["goal_id"],
        progress_delta=args.get("progress_delta", 0),
        set_value=args.get("set_value"),
        mark_complete=args.get("mark_complete")
    )


async def tool_get_goals(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get list of study goals."""
    from goals import get_goals, get_goal_categories

    # Resolve category name to ID
    category_id = None
    if args.get("category"):
        categories = await get_goal_categories()
        cat = next((c for c in categories if c["name"] == args["category"]), None)
        if cat:
            category_id = cat["id"]

    goals = await get_goals(
        category_id=category_id,
        include_completed=args.get("include_completed", False)
    )

    return {
        "success": True,
        "goals": goals,
        "count": len(goals)
    }


async def tool_get_goals_summary(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get goal completion summary."""
    from goals import get_goals_summary
    return await get_goals_summary()


# ============================================
# AI SCHEDULE CONTROL TOOL IMPLEMENTATIONS
# ============================================

async def tool_create_time_block(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new time block in the schedule."""
    from scheduler import ai_create_time_block
    from datetime import datetime

    block_date = datetime.fromisoformat(args["date"]).date()

    return await ai_create_time_block(
        block_date=block_date,
        start_time=args["start_time"],
        duration_mins=args["duration_mins"],
        activity_type=args["activity_type"],
        title=args["title"],
        subject_code=args.get("subject_code"),
        priority=args.get("priority", 5)
    )


async def tool_move_time_block(args: Dict[str, Any]) -> Dict[str, Any]:
    """Move a scheduled block to a new time."""
    from scheduler import ai_move_time_block
    from datetime import datetime

    new_date = datetime.fromisoformat(args["new_date"]).date()

    return await ai_move_time_block(
        task_id=args["task_id"],
        new_date=new_date,
        new_start=args["new_start_time"]
    )


async def tool_delete_time_block(args: Dict[str, Any]) -> Dict[str, Any]:
    """Delete a scheduled block."""
    from scheduler import ai_delete_time_block
    return await ai_delete_time_block(args["task_id"])


async def tool_get_optimized_schedule(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get optimized schedule for a day."""
    from scheduler import optimize_day_schedule
    from datetime import datetime, date

    if args.get("date"):
        target_date = datetime.fromisoformat(args["date"]).date()
    else:
        target_date = date.today()

    result = await optimize_day_schedule(target_date)
    return {"success": True, **result}


async def tool_get_weekly_timeline_schedule(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get optimized weekly timeline."""
    from scheduler import get_weekly_timeline
    from datetime import datetime, date

    start_date = None
    if args.get("start_date"):
        start_date = datetime.fromisoformat(args["start_date"]).date()

    result = await get_weekly_timeline(start_date)
    return {"success": True, **result}


async def tool_reschedule_all(args: Dict[str, Any]) -> Dict[str, Any]:
    """Reschedule all pending tasks."""
    from scheduler import ai_reschedule_all
    return await ai_reschedule_all(args["reason"])


async def tool_backward_plan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Create backward plan from deadline."""
    from scheduler import backward_plan_deadline
    from datetime import datetime

    deadline_date = datetime.fromisoformat(args["deadline_date"]).date()

    return await backward_plan_deadline(
        deadline_date=deadline_date,
        item_type=args["item_type"],
        subject_code=args["subject_code"],
        total_hours_needed=args["hours_needed"],
        item_title=args["title"]
    )


async def tool_schedule_chapter_revision(args: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule spaced repetition revisions for a chapter."""
    from scheduler import schedule_revision_with_spaced_repetition

    return await schedule_revision_with_spaced_repetition(
        chapter_id=args["chapter_id"],
        intervals=args.get("intervals")
    )


async def tool_allocate_free_time(args: Dict[str, Any]) -> Dict[str, Any]:
    """Allocate free time in the schedule."""
    from scheduler import allocate_free_time
    from datetime import datetime, date

    if args.get("date"):
        target_date = datetime.fromisoformat(args["date"]).date()
    else:
        target_date = date.today()

    return await allocate_free_time(
        target_date=target_date,
        mins_desired=args.get("minutes", 60)
    )


async def tool_update_schedule_preference(args: Dict[str, Any]) -> Dict[str, Any]:
    """Update schedule preferences."""
    from scheduler import ai_update_schedule_preference

    return await ai_update_schedule_preference(
        key=args["key"],
        value=args["value"]
    )


async def tool_get_schedule_context(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get full schedule context."""
    from scheduler import ai_get_schedule_context
    return await ai_get_schedule_context()


async def tool_get_pending_items(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get all pending work items."""
    from scheduler import get_pending_work_items

    days = args.get("days_ahead", 14)
    items = await get_pending_work_items(days)

    return {
        "success": True,
        "items": items,
        "count": len(items),
        "message": f"Found {len(items)} pending items in next {days} days"
    }


async def tool_get_full_timeline(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get complete day timeline."""
    from scheduler import generate_optimized_timeline
    from datetime import datetime, date

    if args.get("date"):
        target_date = datetime.fromisoformat(args["date"]).date()
    else:
        target_date = date.today()

    result = await generate_optimized_timeline(target_date)
    return {"success": True, **result}


# ============================================
# ENHANCED AI MEMORY TOOL IMPLEMENTATIONS
# ============================================

async def tool_remember_user_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Store information in long-term memory."""
    from database import save_ai_memory

    # Add importance as metadata in the value if provided
    value = args["value"]
    importance = args.get("importance", "medium")

    memory = await save_ai_memory(
        args["category"],
        args["key"],
        value
    )

    return {
        "success": True,
        "memory": memory,
        "message": f"Remembered {args['category']}/{args['key']}: {value}"
    }


async def tool_recall_memories(args: Dict[str, Any]) -> Dict[str, Any]:
    """Recall stored memories."""
    from database import get_ai_memory

    memories = await get_ai_memory()

    # Filter by category if provided
    if args.get("category"):
        memories = [m for m in memories if m["category"] == args["category"]]

    # Filter by key if provided
    if args.get("search_key"):
        search_term = args["search_key"].lower()
        memories = [m for m in memories if search_term in m["key"].lower()]

    return {
        "success": True,
        "memories": memories,
        "count": len(memories)
    }


async def tool_forget_memory(args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a memory."""
    from database import db

    result = await db.execute("""
        DELETE FROM ai_memory
        WHERE category = $1 AND key = $2
        RETURNING id
    """, args["category"], args["key"])

    if result:
        return {
            "success": True,
            "message": f"Forgot {args['category']}/{args['key']}"
        }
    else:
        return {
            "success": False,
            "message": f"Memory {args['category']}/{args['key']} not found"
        }


# ============================================
# PROACTIVE NOTIFICATION TOOL IMPLEMENTATIONS
# ============================================

async def tool_send_proactive_notification(args: Dict[str, Any]) -> Dict[str, Any]:
    """Send a proactive notification to the user."""
    from notifications import create_notification, broadcast_notification

    notif = await create_notification(
        notif_type=args["notification_type"],
        title=args["title"],
        message=args["message"],
        priority=args.get("priority", "normal"),
        action_url=args.get("action_url"),
        action_label=args.get("action_label")
    )

    if notif:
        # Broadcast immediately via WebSocket
        await broadcast_notification(notif)
        return {
            "success": True,
            "notification": notif,
            "message": f"Notification sent: {args['title']}"
        }

    return {
        "success": False,
        "message": "Failed to create notification (may be duplicate)"
    }


async def tool_schedule_reminder(args: Dict[str, Any]) -> Dict[str, Any]:
    """Schedule a reminder notification for a future time."""
    from notifications import create_notification
    from datetime import datetime

    try:
        scheduled_time = datetime.fromisoformat(args["scheduled_time"])
    except ValueError:
        return {"error": "Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"}

    # Check if time is in the future
    if scheduled_time <= datetime.now():
        return {"error": "Scheduled time must be in the future"}

    notif = await create_notification(
        notif_type="reminder",
        title=args["title"],
        message=args["message"],
        priority=args.get("priority", "normal"),
        scheduled_for=scheduled_time,
        dedup_key=f"scheduled_reminder_{args['title']}_{scheduled_time.isoformat()}"
    )

    if notif:
        return {
            "success": True,
            "notification": notif,
            "message": f"Reminder scheduled for {scheduled_time.strftime('%Y-%m-%d %H:%M')}"
        }

    return {
        "success": False,
        "message": "Failed to schedule reminder (may be duplicate)"
    }
