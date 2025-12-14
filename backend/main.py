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
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
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
    # Startup
    await db.connect()
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    await log_system("info", "Server started", {"version": "1.0.1"})
    yield
    # Shutdown
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


# ============================================
# HEALTH & STATUS
# ============================================

@app.get("/health", response_model=HealthStatus)
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
# RUN SERVER
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
