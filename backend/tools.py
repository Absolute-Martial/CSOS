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
You can call these functions to help the user:
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

## Naming Conventions You Enforce:
- Subjects: UPPERCASE + number (MATH101, PHYS102)
- Chapters: chapter + 2 digits (chapter01)
- Files: snake_case (lecture_notes.pdf)

Always be helpful, proactive about study habits, and encouraging about streaks!
"""
