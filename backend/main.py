"""
Personal Engineering OS - FastAPI Backend
Main server with copilot-api integration
"""

import os
import json
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Optional, List

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import (
    db, get_all_subjects, get_subject_by_code, create_subject,
    get_chapters_by_subject, get_chapter, get_chapter_files,
    get_tasks_today, get_lab_reports, get_pending_revisions,
    get_streak, get_unread_notifications, get_version,
    log_system, save_file_record
)
from models import (
    Subject, SubjectCreate, Chapter, ChapterCreate, Task, TaskCreate,
    LabReport, LabReportCreate, ChatRequest, ChatResponse,
    HealthStatus, MorningBriefing, UserStreak, Notification,
    AIGuideline, AIGuidelineCreate, AIMemoryCreate
)
from tools import TOOL_DEFINITIONS, execute_tool, build_system_prompt
from copilot import setup_copilotkit
from file_handler import (
    save_uploaded_file, read_file_content, validate_filename,
    list_chapter_files, SUPPORTED_EXTENSIONS
)


# Configuration
COPILOT_API_URL = os.getenv("COPILOT_API_URL", "http://localhost:4141")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Import notification service
    from notifications import notification_service, ensure_notification_tables
    # Import achievement system
    from achievements import initialize_achievements

    # Startup
    await db.connect()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Initialize notification system
    await ensure_notification_tables()
    await notification_service.start()

    # Initialize achievement system
    achievement_result = await initialize_achievements()
    await log_system("info", "Achievement system initialized", achievement_result)

    await log_system("info", "Server started", {"version": "1.0.1"})
    yield
    # Shutdown
    await notification_service.stop()
    await log_system("info", "Server shutting down")
    await db.disconnect()


app = FastAPI(
    title="Personal Engineering OS",
    description="AI-powered study management system for KU students",
    version="1.0.1",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_copilotkit(app, "/copilotkit")


# ============================================
# HEALTH & STATUS
# ============================================

@app.get("/health", response_model=HealthStatus)
@app.get("/api/health", response_model=HealthStatus)
async def health_check():
    """Check API and dependencies health."""
    copilot_status = "unknown"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{COPILOT_API_URL}/v1/models", timeout=5)
            copilot_status = "connected" if resp.status_code == 200 else "error"
    except Exception:
        copilot_status = "disconnected"

    return HealthStatus(
        status="healthy",
        version="1.0.1",
        database="connected",
        copilot_api=copilot_status
    )


@app.get("/api/version")
async def get_current_version():
    """Get current version metadata."""
    return await get_version()


# ============================================
# AI CHAT (copilot-api integration)
# ============================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Chat with AI using copilot-api as OpenAI-compatible backend."""
    
    try:
        # Build system prompt with guidelines and memory
        system_prompt = await build_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{COPILOT_API_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4",
                    "messages": messages,
                    "tools": TOOL_DEFINITIONS,
                    "tool_choice": "auto"
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="AI service error")
            
            data = response.json()
            choice = data["choices"][0]
            message = choice["message"]
            
            # Handle tool calls
            tool_results = []
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    func = tool_call["function"]
                    result = await execute_tool(
                        func["name"],
                        json.loads(func["arguments"])
                    )
                    tool_results.append({
                        "tool": func["name"],
                        "result": result
                    })
            
            # Get notifications to include
            notifications = await get_unread_notifications()
            
            return ChatResponse(
                response=message.get("content", ""),
                tool_calls=tool_results if tool_results else None,
                notifications=[dict(n) for n in notifications[:3]] if notifications else None
            )
    
    except httpx.ConnectError:
        # Fallback when copilot-api is not running
        await log_system("warning", "copilot-api not available, using fallback")
        
        return ChatResponse(
            response=f"⚠️ AI service not connected. Please start copilot-api:\n\n```\nnpx copilot-api@latest start\n```\n\nYour message: {request.message}",
            tool_calls=None,
            notifications=None
        )
    
    except Exception as e:
        await log_system("error", f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/briefing", response_model=MorningBriefing)
async def get_morning_briefing():
    """Get daily briefing summary."""
    from tools import tool_morning_briefing
    result = await tool_morning_briefing({})
    return result["briefing"]


# ============================================
# SUBJECTS
# ============================================

@app.get("/api/subjects", response_model=List[dict])
async def list_subjects():
    """Get all subjects ordered by credits."""
    return await get_all_subjects()


@app.post("/api/subjects", response_model=dict)
async def add_subject(subject: SubjectCreate):
    """Add a new subject."""
    existing = await get_subject_by_code(subject.code)
    if existing:
        raise HTTPException(status_code=400, detail="Subject already exists")
    
    return await create_subject(
        subject.code, subject.name, subject.credits,
        subject.type.value, subject.color
    )


@app.get("/api/subjects/{code}/chapters", response_model=List[dict])
async def get_subject_chapters(code: str):
    """Get all chapters for a subject."""
    subject = await get_subject_by_code(code.upper())
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    return await get_chapters_by_subject(subject["id"])


# ============================================
# CHAPTERS & FILES
# ============================================

@app.post("/api/chapters")
async def create_new_chapter(
    subject_code: str = Form(...),
    chapter_number: int = Form(...),
    chapter_title: str = Form(...)
):
    """Create a new chapter with folder structure."""
    from tools import tool_create_folder_supervised
    
    result = await tool_create_folder_supervised({
        "subject_code": subject_code,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title
    })
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@app.get("/api/chapters/{chapter_id}")
async def get_chapter_details(chapter_id: int):
    """Get chapter with progress and files."""
    chapter = await get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    files = await get_chapter_files(chapter_id)
    chapter["files"] = files
    
    return chapter


@app.post("/api/chapters/{chapter_id}/upload")
async def upload_chapter_file(
    chapter_id: int,
    file_type: str = Form(...),  # slides, assignments, notes
    file: UploadFile = File(...)
):
    """Upload a file to a chapter."""
    # Validate filename
    valid, message = validate_filename(file.filename)
    if not valid:
        raise HTTPException(status_code=400, detail=message)
    
    # Get chapter info
    chapter = await get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    
    # Read file content
    content = await file.read()
    
    # Get subject code from chapter
    from database import get_subject
    subject = await get_subject(chapter["subject_id"])
    
    # Save file
    file_path, file_size = await save_uploaded_file(
        content,
        subject["code"],
        chapter["number"],
        file_type,
        file.filename
    )
    
    # Record in database
    record = await save_file_record(
        chapter_id,
        file_type.rstrip('s'),  # 'slides' -> 'slide'
        file.filename,
        file_path,
        file.content_type,
        file_size
    )
    
    return {"success": True, "file": record}


@app.get("/api/chapters/{chapter_id}/files/{file_id}/content")
async def get_file_text_content(chapter_id: int, file_id: int):
    """Extract and return text content from a file."""
    files = await get_chapter_files(chapter_id)
    file_record = next((f for f in files if f["id"] == file_id), None)
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    content = await read_file_content(file_record["filepath"])
    
    return {"filename": file_record["filename"], "content": content}


# ============================================
# TASKS
# ============================================

@app.get("/api/tasks/today", response_model=List[dict])
async def get_todays_tasks():
    """Get today's scheduled tasks."""
    return await get_tasks_today()


@app.post("/api/tasks", response_model=dict)
async def create_new_task(task: TaskCreate):
    """Create a new task."""
    from database import create_task
    return await create_task(task.model_dump())


@app.patch("/api/tasks/{task_id}")
async def update_existing_task(task_id: int, updates: dict):
    """Update a task."""
    from database import update_task
    return await update_task(task_id, **updates)


@app.delete("/api/tasks/{task_id}")
async def delete_existing_task(task_id: int):
    """Delete a task."""
    from database import delete_task
    success = await delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True}


# ============================================
# LAB REPORTS
# ============================================

@app.get("/api/labs", response_model=List[dict])
async def list_lab_reports(status: Optional[str] = Query(None)):
    """Get lab reports, optionally filtered by status."""
    return await get_lab_reports(status)


@app.post("/api/labs", response_model=dict)
async def create_lab_report(lab: LabReportCreate):
    """Create a new lab report."""
    from database import create_lab_report
    return await create_lab_report(lab.model_dump())


# ============================================
# REVISIONS
# ============================================

@app.get("/api/revisions/pending", response_model=List[dict])
async def list_pending_revisions():
    """Get pending revisions sorted by priority."""
    return await get_pending_revisions()


@app.post("/api/revisions/{revision_id}/complete")
async def complete_revision_endpoint(revision_id: int):
    """Mark a revision as complete."""
    from tools import tool_complete_revision
    return await tool_complete_revision({"revision_id": revision_id})


# ============================================
# STREAKS & REWARDS
# ============================================

@app.get("/api/streak", response_model=dict)
async def get_streak_info():
    """Get current streak and rewards status."""
    return await get_streak()


# ============================================
# NOTIFICATIONS
# ============================================

@app.get("/api/notifications", response_model=List[dict])
async def list_notifications():
    """Get unread notifications."""
    return await get_unread_notifications()


@app.post("/api/notifications/{notification_id}/read")
async def mark_notification_as_read(notification_id: int):
    """Mark notification as read."""
    from database import mark_notification_read
    return await mark_notification_read(notification_id)


# ============================================
# PROACTIVE NOTIFICATIONS (WebSocket + REST)
# ============================================

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications."""
    from notifications import register_client, unregister_client

    await websocket.accept()
    await register_client(websocket)

    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()

            # Handle client commands
            try:
                message = json.loads(data)
                cmd = message.get("command")

                if cmd == "mark_read":
                    from notifications import mark_notification_read as mark_read
                    notif_id = message.get("notification_id")
                    if notif_id:
                        await mark_read(notif_id)
                        await websocket.send_json({
                            "type": "ack",
                            "command": "mark_read",
                            "notification_id": notif_id
                        })

                elif cmd == "dismiss":
                    from notifications import dismiss_notification
                    notif_id = message.get("notification_id")
                    if notif_id:
                        await dismiss_notification(notif_id)
                        await websocket.send_json({
                            "type": "ack",
                            "command": "dismiss",
                            "notification_id": notif_id
                        })

                elif cmd == "ping":
                    await websocket.send_json({"type": "pong"})

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        await unregister_client(websocket)
    except Exception as e:
        await unregister_client(websocket)


@app.get("/api/notifications/proactive")
async def list_proactive_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0)
):
    """Get proactive notifications with pagination."""
    from notifications import get_user_notifications, get_notification_count

    notifications = await get_user_notifications(limit, unread_only, offset)
    counts = await get_notification_count()

    return {
        "notifications": notifications,
        "unread_count": counts["unread"],
        "total_count": counts["total"]
    }


@app.get("/api/notifications/proactive/count")
async def get_proactive_notification_count():
    """Get notification counts (for badge display)."""
    from notifications import get_notification_count
    return await get_notification_count()


@app.post("/api/notifications/proactive/{notification_id}/read")
async def mark_proactive_notification_read(notification_id: int):
    """Mark a proactive notification as read."""
    from notifications import mark_notification_read as mark_read
    result = await mark_read(notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "notification": result}


@app.post("/api/notifications/proactive/{notification_id}/dismiss")
async def dismiss_proactive_notification(notification_id: int):
    """Dismiss a proactive notification."""
    from notifications import dismiss_notification
    result = await dismiss_notification(notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"success": True, "notification": result}


@app.post("/api/notifications/proactive/read-all")
async def mark_all_notifications_read():
    """Mark all notifications as read."""
    from database import db
    result = await db.execute("""
        UPDATE proactive_notifications
        SET read = true, read_at = NOW()
        WHERE read = false AND dismissed = false
    """)
    return {"success": True, "message": "All notifications marked as read"}


@app.get("/api/notifications/preferences")
async def get_all_notification_preferences():
    """Get notification preferences."""
    from notifications import get_notification_preferences
    return await get_notification_preferences()


@app.put("/api/notifications/preferences/{notification_type}")
async def update_notification_type_preference(
    notification_type: str,
    enabled: Optional[bool] = Form(None),
    quiet_hours_start: Optional[str] = Form(None),
    quiet_hours_end: Optional[str] = Form(None),
    frequency_limit: Optional[int] = Form(None)
):
    """Update preferences for a notification type."""
    from notifications import update_notification_preference

    valid_types = ["reminder", "achievement", "suggestion", "warning", "motivation"]
    if notification_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid notification type. Valid types: {valid_types}"
        )

    result = await update_notification_preference(
        notification_type,
        enabled,
        quiet_hours_start,
        quiet_hours_end,
        frequency_limit
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"success": True, "preference": result}


@app.post("/api/notifications/test")
async def send_test_notification(
    title: str = Form("Test Notification"),
    message: str = Form("This is a test notification from the system."),
    priority: str = Form("normal"),
    notification_type: str = Form("suggestion")
):
    """Send a test notification (for debugging)."""
    from notifications import create_notification, broadcast_notification

    notif = await create_notification(
        notif_type=notification_type,
        title=title,
        message=message,
        priority=priority
    )

    if notif:
        await broadcast_notification(notif)
        return {"success": True, "notification": notif}

    return {"success": False, "message": "Notification not created (may be duplicate)"}


# ============================================
# AI GUIDELINES & MEMORY
# ============================================

@app.get("/api/ai/guidelines", response_model=List[dict])
async def list_ai_guidelines():
    """Get all AI guidelines."""
    from database import get_ai_guidelines
    return await get_ai_guidelines(active_only=False)


@app.post("/api/ai/guidelines", response_model=dict)
async def add_new_guideline(guideline: AIGuidelineCreate):
    """Add a new AI guideline."""
    from database import add_ai_guideline
    return await add_ai_guideline(guideline.rule, guideline.priority)


@app.get("/api/ai/memory", response_model=List[dict])
async def list_ai_memories():
    """Get all AI memories."""
    from database import get_ai_memory
    return await get_ai_memory()


@app.post("/api/ai/memory", response_model=dict)
async def save_new_memory(memory: AIMemoryCreate):
    """Save a new memory."""
    from database import save_ai_memory
    return await save_ai_memory(memory.category, memory.key, memory.value)


# ============================================
# C ENGINE INTEGRATION
# ============================================

@app.get("/api/gaps")
async def analyze_schedule_gaps():
    """Analyze schedule for deep work gaps using C engine."""
    from tools import tool_analyze_gaps
    return await tool_analyze_gaps({})


# ============================================
# STUDY TIMER ENDPOINTS
# ============================================

@app.get("/api/timer/status")
async def get_timer_status():
    """Get current timer status."""
    from timer import get_active_timer

    active = await get_active_timer()
    if not active:
        return {"running": False}

    elapsed = active.get("elapsed_seconds", 0)
    return {
        "running": True,
        "session_id": active.get("session_id"),
        "elapsed_seconds": elapsed,
        "subject_code": active.get("subject_code"),
        "subject_name": active.get("subject_name"),
        "color": active.get("color"),
        "title": active.get("title"),
        "started_at": active.get("started_at")
    }


@app.post("/api/timer/start")
async def start_timer_endpoint(
    subject_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    title: Optional[str] = None
):
    """Start a new study timer."""
    from timer import start_timer
    return await start_timer(subject_id, chapter_id, title)


@app.post("/api/timer/stop")
async def stop_timer_endpoint():
    """Stop the current timer."""
    from timer import stop_timer
    return await stop_timer()


@app.get("/api/timer/sessions")
async def get_timer_sessions(
    days: int = Query(default=7, ge=1, le=90),
    subject_id: Optional[int] = None
):
    """Get past study sessions."""
    from timer import get_study_sessions
    return await get_study_sessions(days, subject_id)


@app.get("/api/timer/analytics")
async def get_timer_analytics(days: int = Query(default=7, ge=1, le=90)):
    """Get study time analytics."""
    from timer import get_study_analytics
    return await get_study_analytics(days)


# ============================================
# SCHEDULER & CALENDAR ENDPOINTS
# ============================================

@app.get("/api/schedule/today")
async def get_today_schedule():
    """Get today's complete schedule (KU timetable + tasks + gaps)."""
    from scheduler import get_today_at_glance
    return await get_today_at_glance()


@app.get("/api/schedule/week")
async def get_week_schedule_endpoint(start_date: Optional[str] = None):
    """Get the full week's schedule."""
    from scheduler import get_week_schedule
    from datetime import datetime

    start = None
    if start_date:
        try:
            start = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    return await get_week_schedule(start)


@app.get("/api/schedule/gaps")
async def get_schedule_gaps(days: int = Query(default=7, ge=1, le=30)):
    """Find deep work opportunities in schedule gaps."""
    from scheduler import find_deep_work_slots
    slots = await find_deep_work_slots(days)
    return {
        "slots": slots,
        "count": len(slots),
        "total_deep_work_mins": sum(s["duration_mins"] for s in slots)
    }


@app.get("/api/schedule/timetable")
async def get_ku_timetable():
    """Get the KU university timetable."""
    from scheduler import KU_TIMETABLE, get_today_timetable
    today = await get_today_timetable()
    return {
        "today": today,
        "full_week": KU_TIMETABLE
    }


@app.post("/api/schedule/redistribute")
async def redistribute_schedule(
    event_type: str = Form(...),
    subject_code: str = Form(...),
    event_date: str = Form(...),
    apply_immediately: bool = Form(False)
):
    """Redistribute schedule for an upcoming event (test, assignment, etc.)."""
    from scheduler import redistribute_schedule as do_redistribute, apply_redistribution
    from datetime import datetime

    try:
        target_date = datetime.fromisoformat(event_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    plan = await do_redistribute(
        event_type=event_type,
        event_subject=subject_code.upper(),
        event_date=target_date,
        priority=8
    )

    if apply_immediately and plan.get("success") and plan.get("blocks"):
        result = await apply_redistribution(plan["blocks"])
        plan["applied"] = True
        plan["tasks_created"] = result["tasks_created"]

    return plan


@app.get("/api/schedule/deadlines")
async def get_all_deadlines(days: int = Query(default=14, ge=1, le=60)):
    """Get all upcoming deadlines (labs, assignments, goals)."""
    from scheduler import get_upcoming_deadlines
    deadlines = await get_upcoming_deadlines(days)
    return {
        "deadlines": deadlines,
        "count": len(deadlines),
        "days": days
    }


# ============================================
# LAB REPORT TRACKER ENDPOINTS
# ============================================

@app.get("/api/labs/countdown")
async def get_lab_report_countdown():
    """Get pending lab reports with countdown."""
    from scheduler import get_lab_report_countdown
    reports = await get_lab_report_countdown()
    return {
        "reports": reports,
        "total": len(reports),
        "urgent": len([r for r in reports if r["urgency"] in ("overdue", "urgent")])
    }


@app.post("/api/labs/track")
async def track_new_lab_report(
    subject_code: str = Form(...),
    experiment_name: str = Form(...),
    due_date: str = Form(...),
    lab_date: Optional[str] = Form(None)
):
    """Add a new lab report to track."""
    from scheduler import create_lab_report_entry
    from datetime import datetime

    try:
        due = datetime.fromisoformat(due_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid due_date format")

    lab = None
    if lab_date:
        try:
            lab = datetime.fromisoformat(lab_date).date()
        except ValueError:
            pass

    return await create_lab_report_entry(subject_code, experiment_name, due, lab)


@app.patch("/api/labs/{report_id}/status")
async def update_lab_report_status_endpoint(
    report_id: int,
    status: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """Update lab report status."""
    from scheduler import update_lab_report_status
    return await update_lab_report_status(report_id, status, notes)


# ============================================
# STUDY GOALS ENDPOINTS
# ============================================

@app.get("/api/goals/categories")
async def list_goal_categories():
    """List all goal categories."""
    from goals import get_goal_categories
    return await get_goal_categories()


@app.post("/api/goals/categories")
async def create_goal_category_endpoint(
    name: str = Form(...),
    color: str = Form("#6366f1"),
    icon: str = Form("🎯")
):
    """Create a goal category."""
    from goals import create_goal_category
    return await create_goal_category(name, color, icon)


@app.get("/api/goals")
async def list_goals(
    category_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    include_completed: bool = False
):
    """List study goals."""
    from goals import get_goals
    return await get_goals(category_id, subject_id, include_completed)


@app.get("/api/goals/{goal_id}")
async def get_goal_endpoint(goal_id: int):
    """Get a single goal."""
    from goals import get_goal
    goal = await get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@app.post("/api/goals")
async def create_goal_endpoint(
    title: str = Form(...),
    category_id: Optional[int] = Form(None),
    subject_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    target_value: Optional[int] = Form(None),
    unit: Optional[str] = Form(None),
    deadline: Optional[str] = Form(None),
    priority: int = Form(5)
):
    """Create a study goal."""
    from goals import create_goal
    from datetime import datetime

    deadline_date = None
    if deadline:
        try:
            deadline_date = datetime.fromisoformat(deadline).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline format")

    return await create_goal(
        title=title,
        category_id=category_id,
        subject_id=subject_id,
        description=description,
        target_value=target_value,
        unit=unit,
        deadline=deadline_date,
        priority=priority
    )


@app.patch("/api/goals/{goal_id}")
async def update_goal_endpoint(goal_id: int, updates: dict):
    """Update a goal."""
    from goals import update_goal
    return await update_goal(goal_id, **updates)


@app.post("/api/goals/{goal_id}/progress")
async def update_goal_progress_endpoint(
    goal_id: int,
    progress_delta: int = Form(default=0),
    set_value: Optional[int] = Form(None),
    mark_complete: Optional[bool] = Form(None)
):
    """Update goal progress."""
    from goals import update_goal_progress
    return await update_goal_progress(goal_id, progress_delta, set_value, mark_complete)


@app.delete("/api/goals/{goal_id}")
async def delete_goal_endpoint(goal_id: int):
    """Delete a goal."""
    from goals import delete_goal
    success = await delete_goal(goal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"success": True}


@app.get("/api/goals/summary/stats")
async def get_goals_summary_endpoint():
    """Get goals summary statistics."""
    from goals import get_goals_summary
    return await get_goals_summary()


@app.get("/api/goals/upcoming/deadlines")
async def get_upcoming_deadlines_endpoint(days: int = Query(default=14, ge=1, le=60)):
    """Get goals with upcoming deadlines."""
    from goals import get_upcoming_deadlines
    return await get_upcoming_deadlines(days)


# ============================================
# TIMELINE OPTIMIZATION ENDPOINTS
# ============================================

@app.get("/api/timeline/today")
async def get_today_timeline():
    """Get optimized timeline for today with all activity blocks."""
    from scheduler import generate_optimized_timeline
    from datetime import date
    return await generate_optimized_timeline(date.today())


@app.get("/api/timeline/{target_date}")
async def get_timeline_for_date(target_date: str):
    """Get optimized timeline for a specific date."""
    from scheduler import generate_optimized_timeline
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(target_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    return await generate_optimized_timeline(dt)


@app.get("/api/timeline/week/{start_date}")
async def get_weekly_timeline_endpoint(start_date: Optional[str] = None):
    """Get optimized weekly timeline."""
    from scheduler import get_weekly_timeline
    from datetime import datetime, date

    start = None
    if start_date:
        try:
            start = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    return await get_weekly_timeline(start)


@app.post("/api/timeline/optimize/{target_date}")
async def optimize_day_endpoint(target_date: str):
    """Run optimization algorithm for a specific day."""
    from scheduler import optimize_day_schedule
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(target_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    return await optimize_day_schedule(dt)


@app.get("/api/timeline/pending")
async def get_pending_work_items(days: int = Query(default=14, ge=1, le=60)):
    """Get all pending work items sorted by priority."""
    from scheduler import get_pending_work_items as fetch_pending
    items = await fetch_pending(days)
    return {
        "items": items,
        "count": len(items),
        "days": days
    }


@app.post("/api/timeline/backward-plan")
async def create_backward_plan(
    deadline_date: str = Form(...),
    item_type: str = Form(...),
    subject_code: str = Form(...),
    hours_needed: float = Form(...),
    title: str = Form(...)
):
    """Create a backward plan from a deadline."""
    from scheduler import backward_plan_deadline
    from datetime import datetime

    try:
        deadline = datetime.fromisoformat(deadline_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    return await backward_plan_deadline(
        deadline_date=deadline,
        item_type=item_type,
        subject_code=subject_code.upper(),
        total_hours_needed=hours_needed,
        item_title=title
    )


@app.post("/api/timeline/reschedule")
async def reschedule_all_endpoint(reason: str = Form(...)):
    """Reschedule all pending tasks."""
    from scheduler import ai_reschedule_all
    return await ai_reschedule_all(reason)


@app.post("/api/timeline/blocks")
async def create_time_block_endpoint(
    date: str = Form(...),
    start_time: str = Form(...),
    duration_mins: int = Form(...),
    activity_type: str = Form(...),
    title: str = Form(...),
    subject_code: Optional[str] = Form(None),
    priority: int = Form(5)
):
    """Create a new time block in the schedule."""
    from scheduler import ai_create_time_block
    from datetime import datetime

    try:
        block_date = datetime.fromisoformat(date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    return await ai_create_time_block(
        block_date=block_date,
        start_time=start_time,
        duration_mins=duration_mins,
        activity_type=activity_type,
        title=title,
        subject_code=subject_code,
        priority=priority
    )


@app.patch("/api/timeline/blocks/{task_id}")
async def move_time_block_endpoint(
    task_id: int,
    new_date: str = Form(...),
    new_start_time: str = Form(...)
):
    """Move a time block to a new date/time."""
    from scheduler import ai_move_time_block
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(new_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    return await ai_move_time_block(task_id, dt, new_start_time)


@app.delete("/api/timeline/blocks/{task_id}")
async def delete_time_block_endpoint(task_id: int):
    """Delete a time block."""
    from scheduler import ai_delete_time_block
    return await ai_delete_time_block(task_id)


@app.post("/api/timeline/free-time")
async def allocate_free_time_endpoint(
    date: Optional[str] = Form(None),
    minutes: int = Form(60)
):
    """Allocate free time in the schedule."""
    from scheduler import allocate_free_time
    from datetime import datetime, date as dt

    target = dt.today()
    if date:
        try:
            target = datetime.fromisoformat(date).date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    return await allocate_free_time(target, minutes)


@app.post("/api/timeline/revision")
async def schedule_revision_endpoint(
    chapter_id: int = Form(...),
    intervals: Optional[str] = Form(None)
):
    """Schedule spaced repetition revisions for a chapter."""
    from scheduler import schedule_revision_with_spaced_repetition

    interval_list = None
    if intervals:
        try:
            interval_list = [int(x.strip()) for x in intervals.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid intervals format. Use comma-separated numbers")

    return await schedule_revision_with_spaced_repetition(chapter_id, interval_list)


@app.get("/api/schedule/context")
async def get_full_schedule_context():
    """Get full scheduling context for AI decisions."""
    from scheduler import ai_get_schedule_context
    return await ai_get_schedule_context()


@app.post("/api/schedule/preferences")
async def update_schedule_preference_endpoint(
    key: str = Form(...),
    value: str = Form(...)
):
    """Update user's schedule preferences."""
    from scheduler import ai_update_schedule_preference
    return await ai_update_schedule_preference(key, value)


# ============================================
# ACHIEVEMENTS & GAMIFICATION ENDPOINTS
# ============================================

@app.get("/api/achievements")
async def list_achievements():
    """Get all achievement definitions."""
    from achievements import get_all_achievements
    return await get_all_achievements()


@app.get("/api/achievements/user")
async def user_achievements(include_incomplete: bool = False):
    """Get user's achievements with progress."""
    from achievements import get_user_achievements
    return await get_user_achievements(include_incomplete)


@app.get("/api/achievements/progress")
async def achievement_progress():
    """Get progress toward all achievements."""
    from achievements import get_achievement_progress
    return await get_achievement_progress()


@app.get("/api/achievements/points")
async def total_points():
    """Get user's total achievement points."""
    from achievements import get_total_points
    return {"points": await get_total_points()}


@app.get("/api/achievements/summary")
async def achievement_summary():
    """Get achievement summary statistics."""
    from achievements import get_achievement_summary
    return await get_achievement_summary()


@app.get("/api/achievements/category/{category}")
async def achievements_by_category(category: str):
    """Get achievements filtered by category."""
    from achievements import get_achievements_by_category
    return await get_achievements_by_category(category)


@app.get("/api/achievements/recent")
async def recent_achievements(days: int = Query(default=7, ge=1, le=90)):
    """Get recently earned achievements."""
    from achievements import get_recent_achievements
    return await get_recent_achievements(days)


@app.get("/api/achievements/unnotified")
async def unnotified_achievements():
    """Get achievements that haven't been shown to user yet."""
    from achievements import get_unnotified_achievements
    return await get_unnotified_achievements()


@app.post("/api/achievements/mark-notified")
async def mark_notified(achievement_ids: List[int]):
    """Mark achievements as notified."""
    from achievements import mark_achievements_notified
    await mark_achievements_notified(achievement_ids)
    return {"success": True, "marked": len(achievement_ids)}


@app.post("/api/achievements/check")
async def check_achievements_endpoint():
    """Manually trigger achievement check."""
    from achievements import AchievementChecker
    checker = AchievementChecker()
    earned = await checker.check_all()
    return {"earned": earned, "count": len(earned)}


# ============================================
# PROGRESS TRACKING ENDPOINTS
# ============================================

@app.get("/api/progress/history")
async def progress_history(days: int = Query(default=30, ge=1, le=365)):
    """Get progress history for visualization."""
    from achievements import get_progress_history
    return await get_progress_history(days)


@app.get("/api/progress/growth")
async def growth_stats():
    """Get growth statistics (weekly, monthly, all-time)."""
    from achievements import get_growth_stats
    return await get_growth_stats()


@app.post("/api/progress/snapshot")
async def create_snapshot():
    """Create a progress snapshot for today."""
    from achievements import create_progress_snapshot
    return await create_progress_snapshot()


# ============================================
# WELLBEING MONITORING ENDPOINTS
# ============================================

@app.get("/api/wellbeing/score")
async def get_wellbeing_score():
    """Get current wellbeing score and recommendations."""
    from wellbeing import WellbeingMonitor
    monitor = WellbeingMonitor()
    metrics = await monitor.calculate_wellbeing_score()
    return metrics.model_dump()


@app.get("/api/wellbeing/check")
async def check_wellbeing_status():
    """Quick wellbeing check - returns alerts if needed."""
    from wellbeing import check_wellbeing_after_session
    # Check current state (pass 0 as no session just ended)
    result = await check_wellbeing_after_session(0)
    if result is None:
        return {"status": "healthy", "alerts": []}
    return {"status": "attention_needed", "alerts": result}


@app.post("/api/wellbeing/break/start")
async def start_break_endpoint(
    break_type: str = Form(...),
    duration: Optional[int] = Form(None)
):
    """Start a break session."""
    from wellbeing import start_break, BreakType
    try:
        bt = BreakType(break_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid break type. Valid types: short, pomodoro, meal, exercise, meditation, long")
    return await start_break(bt, duration)


@app.post("/api/wellbeing/break/{break_id}/end")
async def end_break_endpoint(break_id: int, completed: bool = True):
    """End a break session."""
    from wellbeing import end_break
    return await end_break(break_id, completed)


@app.get("/api/wellbeing/break/active")
async def get_active_break_endpoint():
    """Get currently active break if any."""
    from wellbeing import get_active_break
    result = await get_active_break()
    if result is None:
        return {"active": False}
    return {"active": True, "break": result}


@app.get("/api/wellbeing/break/suggest")
async def get_break_suggestion():
    """Get a break suggestion based on current study state."""
    from wellbeing import should_suggest_break, suggest_break
    should_break, suggestion = await should_suggest_break()
    if not should_break:
        return {"suggest_break": False, "message": "Keep studying, no break needed yet"}
    return {
        "suggest_break": True,
        "suggestion": {
            "break_type": suggestion.break_type.value,
            "suggested_duration_mins": suggestion.suggested_duration_mins
        }
    }


@app.get("/api/wellbeing/break/stats")
async def get_break_stats_endpoint(days: int = Query(default=7, ge=1, le=90)):
    """Get break statistics for the specified period."""
    from wellbeing import get_break_stats
    return await get_break_stats(days)


@app.get("/api/wellbeing/history")
async def get_wellbeing_history_endpoint(days: int = Query(default=30, ge=1, le=365)):
    """Get wellbeing history for trend analysis."""
    from wellbeing import get_wellbeing_history
    return await get_wellbeing_history(days)


@app.get("/api/wellbeing/trends")
async def get_wellbeing_trends_endpoint(days: int = Query(default=30, ge=1, le=365)):
    """Get wellbeing trend analysis."""
    from wellbeing import get_wellbeing_trends
    return await get_wellbeing_trends(days)


@app.post("/api/wellbeing/save-daily")
async def save_daily_wellbeing_metrics():
    """Save today's wellbeing metrics for historical tracking."""
    from wellbeing import save_daily_metrics
    return await save_daily_metrics()


@app.get("/api/wellbeing/notifications")
async def get_wellbeing_notifications():
    """Get wellbeing-related notifications."""
    from wellbeing import generate_wellbeing_notifications
    notifications = await generate_wellbeing_notifications()
    return {"notifications": notifications, "count": len(notifications)}


# ============================================
# POMODORO TIMER ENDPOINTS
# ============================================

@app.get("/api/pomodoro/status")
async def get_pomodoro_status():
    """Get current Pomodoro timer status."""
    from wellbeing import PomodoroTimer
    timer = PomodoroTimer()
    return await timer.get_status()


@app.post("/api/pomodoro/work")
async def start_pomodoro_work():
    """Start a Pomodoro work session."""
    from wellbeing import PomodoroTimer
    timer = PomodoroTimer()
    return await timer.start_work()


@app.post("/api/pomodoro/break")
async def start_pomodoro_break():
    """Start a Pomodoro break (short or long based on cycle)."""
    from wellbeing import PomodoroTimer
    timer = PomodoroTimer()
    return await timer.start_break()


@app.post("/api/pomodoro/stop")
async def stop_pomodoro():
    """Stop the Pomodoro timer."""
    from wellbeing import PomodoroTimer
    timer = PomodoroTimer()
    return await timer.stop()


@app.post("/api/pomodoro/reset")
async def reset_pomodoro():
    """Reset the Pomodoro timer completely."""
    from wellbeing import PomodoroTimer
    timer = PomodoroTimer()
    return await timer.reset()


# ============================================
# LEARNING PATTERNS ENDPOINTS
# ============================================

@app.get("/api/patterns")
async def get_all_learning_patterns():
    """Get all cached learning patterns."""
    from learning_patterns import get_all_patterns
    patterns = await get_all_patterns()
    return {"patterns": [p.model_dump() for p in patterns], "count": len(patterns)}


@app.get("/api/patterns/overall")
async def get_overall_pattern():
    """Get overall learning pattern across all subjects."""
    from learning_patterns import get_learning_pattern
    pattern = await get_learning_pattern(None)
    return pattern.model_dump()


@app.get("/api/patterns/subject/{subject_code}")
async def get_subject_learning_pattern(subject_code: str):
    """Get learning pattern for a specific subject."""
    from learning_patterns import get_learning_pattern
    pattern = await get_learning_pattern(subject_code.upper())
    return pattern.model_dump()


@app.get("/api/patterns/hourly")
async def get_hourly_productivity_endpoint(
    days: int = Query(default=30, ge=7, le=90),
    subject_code: Optional[str] = None
):
    """Get productivity breakdown by hour of day."""
    from learning_patterns import PatternAnalyzer
    analyzer = PatternAnalyzer()
    hourly = await analyzer.get_hourly_productivity(days, subject_code.upper() if subject_code else None)
    return {
        "hourly_data": [h.model_dump() for h in hourly],
        "days_analyzed": days,
        "subject": subject_code
    }


@app.get("/api/patterns/trends")
async def get_productivity_trends_endpoint(days: int = Query(default=30, ge=7, le=90)):
    """Get productivity trend analysis."""
    from learning_patterns import get_productivity_trends
    return await get_productivity_trends(days)


@app.post("/api/sessions/{session_id}/effectiveness")
async def record_session_effectiveness_endpoint(
    session_id: int,
    focus_score: float = Form(...),
    material_covered: Optional[str] = Form(None),
    retention_score: Optional[float] = Form(None),
    energy_level: Optional[int] = Form(None)
):
    """Record effectiveness data for a completed study session."""
    from learning_patterns import record_session_effectiveness

    if not 0.0 <= focus_score <= 1.0:
        raise HTTPException(status_code=400, detail="focus_score must be between 0.0 and 1.0")

    if retention_score is not None and not 0.0 <= retention_score <= 1.0:
        raise HTTPException(status_code=400, detail="retention_score must be between 0.0 and 1.0")

    if energy_level is not None and not 1 <= energy_level <= 10:
        raise HTTPException(status_code=400, detail="energy_level must be between 1 and 10")

    try:
        effectiveness = await record_session_effectiveness(
            session_id, focus_score, material_covered, retention_score, energy_level
        )
        return effectiveness.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/sessions/effectiveness")
async def get_effectiveness_history_endpoint(
    days: int = Query(default=30, ge=1, le=90),
    subject_code: Optional[str] = None
):
    """Get session effectiveness history."""
    from learning_patterns import get_session_effectiveness_history
    history = await get_session_effectiveness_history(days, subject_code.upper() if subject_code else None)
    return {"history": history, "count": len(history), "days": days}


@app.get("/api/recommendations")
async def get_study_recommendations_endpoint(
    subject_code: Optional[str] = None,
    planned_duration: Optional[int] = None
):
    """Get personalized study recommendations."""
    from learning_patterns import RecommendationEngine
    engine = RecommendationEngine()
    context = {}
    if subject_code:
        context["subject_code"] = subject_code.upper()
    if planned_duration:
        context["planned_duration"] = planned_duration

    recommendations = await engine.get_recommendations(context)
    return {
        "recommendations": [r.model_dump() for r in recommendations],
        "count": len(recommendations),
        "context": context
    }


@app.get("/api/recommendations/optimal-time")
async def get_optimal_study_time_endpoint(subject_code: Optional[str] = None):
    """Get the optimal time to study a subject."""
    from learning_patterns import RecommendationEngine
    engine = RecommendationEngine()
    return await engine.get_optimal_study_time(subject_code.upper() if subject_code else None)


@app.get("/api/recommendations/duration")
async def suggest_session_duration_endpoint(
    subject_code: Optional[str] = None,
    difficulty: str = Query(default="medium", pattern="^(easy|medium|hard)$")
):
    """Get suggested session duration based on patterns and task difficulty."""
    from learning_patterns import RecommendationEngine
    engine = RecommendationEngine()
    return await engine.suggest_session_duration(
        subject_code.upper() if subject_code else None,
        difficulty
    )


# ============================================
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
