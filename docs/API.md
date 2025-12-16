# API Reference

This document provides complete documentation for all API endpoints in the Personal Engineering OS backend.

## Base URL

- **Development**: `http://localhost:8000`
- **Docker**: `http://localhost:8000` (proxied through frontend)

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Response Format

All responses are JSON. Successful responses return the requested data directly. Errors return:

```json
{
  "detail": "Error message describing what went wrong"
}
```

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

---

## Health & Status

### GET /health

Check API and dependencies health.

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.1",
  "database": "connected",
  "copilot_api": "connected"
}
```

### GET /api/version

Get current version metadata.

**Response**
```json
{
  "id": 1,
  "version": "1.0.1",
  "deployed_at": "2024-01-15T10:30:00Z",
  "changelog": "Initial release"
}
```

---

## AI Chat

### POST /api/chat

Chat with the AI assistant. The AI can call tools to perform actions.

**Request Body**
```json
{
  "message": "What should I study today?",
  "context": {}
}
```

**Response**
```json
{
  "response": "Based on your schedule, I recommend starting with PHYS102 Chapter 3...",
  "tool_calls": [
    {
      "tool": "get_today_schedule",
      "result": { "tasks": [...], "gaps": [...] }
    }
  ],
  "notifications": [
    {
      "id": 1,
      "type": "revision",
      "title": "Revision Due",
      "message": "MATH101 Chapter 2 revision due today"
    }
  ]
}
```

### GET /api/briefing

Get daily briefing summary.

**Response**
```json
{
  "greeting": "Good morning! Ready for a productive day?",
  "current_streak": 5,
  "streak_icon": "fire",
  "tasks_today": 4,
  "revisions_due": 2,
  "deep_work_available": 180,
  "unread_notifications": 3,
  "next_reward": "Silver",
  "points_to_next": 50
}
```

---

## Subjects

### GET /api/subjects

List all subjects ordered by credits.

**Response**
```json
[
  {
    "id": 1,
    "code": "PHYS102",
    "name": "Physics I",
    "credits": 4,
    "type": "practice_heavy",
    "color": "#ef4444",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### POST /api/subjects

Add a new subject.

**Request Body**
```json
{
  "code": "MATH201",
  "name": "Calculus II",
  "credits": 3,
  "type": "practice_heavy",
  "color": "#3b82f6"
}
```

**Response**: Created subject object

### GET /api/subjects/{code}/chapters

Get all chapters for a subject.

**Path Parameters**
- `code`: Subject code (e.g., "MATH101")

**Response**
```json
[
  {
    "id": 1,
    "subject_id": 1,
    "number": 1,
    "title": "Introduction to Vectors",
    "total_pages": 25,
    "folder_path": "MATH101/chapter01",
    "reading_status": "completed",
    "assignment_status": "submitted",
    "mastery_level": 85
  }
]
```

---

## Chapters & Files

### POST /api/chapters

Create a new chapter with folder structure.

**Request Body (Form)**
- `subject_code`: Subject code
- `chapter_number`: Chapter number (1-99)
- `chapter_title`: Chapter title

**Response**
```json
{
  "success": true,
  "chapter": {
    "id": 5,
    "number": 5,
    "title": "Linear Algebra",
    "folder_path": "MATH101/chapter05"
  },
  "folder_created": true
}
```

### GET /api/chapters/{chapter_id}

Get chapter with progress and files.

**Response**
```json
{
  "id": 1,
  "subject_id": 1,
  "number": 1,
  "title": "Introduction",
  "reading_status": "in_progress",
  "assignment_status": "available",
  "mastery_level": 40,
  "revision_count": 2,
  "files": [
    {
      "id": 1,
      "file_type": "slide",
      "filename": "lecture_notes.pdf",
      "uploaded_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### POST /api/chapters/{chapter_id}/upload

Upload a file to a chapter.

**Request Body (Multipart Form)**
- `file_type`: Type of file ("slides", "assignments", "notes")
- `file`: The file to upload

**Response**
```json
{
  "success": true,
  "file": {
    "id": 3,
    "filename": "homework_1.pdf",
    "file_type": "assignment",
    "file_size": 245000
  }
}
```

### GET /api/chapters/{chapter_id}/files/{file_id}/content

Extract and return text content from a file.

**Response**
```json
{
  "filename": "lecture_notes.pdf",
  "content": "Extracted text content from the file..."
}
```

---

## Tasks

### GET /api/tasks/today

Get today's scheduled tasks.

**Response**
```json
[
  {
    "id": 1,
    "title": "Study PHYS102 Chapter 3",
    "description": "Focus on wave equations",
    "subject_id": 2,
    "subject_code": "PHYS102",
    "color": "#ef4444",
    "priority": 7,
    "duration_mins": 60,
    "scheduled_start": "2024-01-15T09:00:00Z",
    "scheduled_end": "2024-01-15T10:00:00Z",
    "status": "pending",
    "is_deep_work": false
  }
]
```

### POST /api/tasks

Create a new task.

**Request Body**
```json
{
  "title": "Complete homework",
  "description": "Problems 1-10",
  "subject_id": 1,
  "priority": 6,
  "duration_mins": 45,
  "scheduled_start": "2024-01-15T14:00:00Z",
  "scheduled_end": "2024-01-15T14:45:00Z",
  "is_deep_work": false
}
```

### PATCH /api/tasks/{task_id}

Update a task.

**Request Body**
```json
{
  "status": "completed",
  "priority": 8
}
```

### DELETE /api/tasks/{task_id}

Delete a task.

**Response**
```json
{
  "success": true
}
```

---

## Lab Reports

### GET /api/labs

Get lab reports, optionally filtered by status.

**Query Parameters**
- `status` (optional): Filter by status ("pending", "in_progress", "completed")

**Response**
```json
[
  {
    "id": 1,
    "title": "Pendulum Experiment",
    "subject_id": 2,
    "subject_code": "PHYS102",
    "deadline": "2024-01-20T23:59:00Z",
    "status": "pending"
  }
]
```

### POST /api/labs

Create a new lab report.

**Request Body**
```json
{
  "title": "Ohm's Law Verification",
  "subject_id": 2,
  "deadline": "2024-01-25T23:59:00Z",
  "notes": "Use circuit simulator for calculations"
}
```

### GET /api/labs/countdown

Get pending lab reports with countdown.

**Response**
```json
{
  "reports": [
    {
      "id": 1,
      "title": "Pendulum Experiment",
      "subject_code": "PHYS102",
      "days_remaining": 5,
      "urgency": "normal",
      "status": "pending"
    }
  ],
  "total": 3,
  "urgent": 1
}
```

### POST /api/labs/track

Add a new lab report to track.

**Request Body (Form)**
- `subject_code`: Subject code
- `experiment_name`: Name of the experiment
- `due_date`: Due date (ISO format)
- `lab_date` (optional): Date lab was performed

### PATCH /api/labs/{report_id}/status

Update lab report status.

**Request Body (Form)**
- `status`: New status
- `notes` (optional): Additional notes

---

## Revisions

### GET /api/revisions/pending

Get pending revisions sorted by priority.

**Response**
```json
[
  {
    "id": 1,
    "chapter_id": 3,
    "chapter_number": 3,
    "chapter_title": "Kinematics",
    "subject_code": "PHYS102",
    "subject_credits": 4,
    "revision_number": 1,
    "due_date": "2024-01-15",
    "completed": false
  }
]
```

### POST /api/revisions/{revision_id}/complete

Mark a revision as complete.

**Response**
```json
{
  "success": true,
  "revision": { ... },
  "points_earned": 15,
  "streak_updated": true
}
```

---

## Streaks & Rewards

### GET /api/streak

Get current streak and rewards status.

**Response**
```json
{
  "id": 1,
  "current_streak": 7,
  "longest_streak": 14,
  "total_points": 350,
  "last_activity_date": "2024-01-15",
  "next_reward": "Gold",
  "points_to_next": 50
}
```

---

## Notifications

### GET /api/notifications

Get unread notifications.

**Response**
```json
[
  {
    "id": 1,
    "type": "revision",
    "title": "Revision Due",
    "message": "MATH101 Chapter 2 revision due today",
    "read": false,
    "due_at": "2024-01-15T18:00:00Z"
  }
]
```

### POST /api/notifications/{notification_id}/read

Mark notification as read.

---

## AI Guidelines & Memory

### GET /api/ai/guidelines

Get all AI guidelines.

**Response**
```json
[
  {
    "id": 1,
    "rule": "Wake time is 04:30, sleep time is 22:30",
    "priority": 1,
    "active": true
  }
]
```

### POST /api/ai/guidelines

Add a new AI guideline.

**Request Body**
```json
{
  "rule": "Never schedule more than 3 hours of continuous study",
  "priority": 3
}
```

### GET /api/ai/memory

Get all AI memories.

**Response**
```json
[
  {
    "id": 1,
    "category": "preferences",
    "key": "study_style",
    "value": "prefers visual learning"
  }
]
```

### POST /api/ai/memory

Save a new memory.

**Request Body**
```json
{
  "category": "preferences",
  "key": "favorite_subject",
  "value": "Physics"
}
```

---

## Study Timer

### GET /api/timer/status

Get current timer status.

**Response (timer running)**
```json
{
  "running": true,
  "session_id": 15,
  "elapsed_seconds": 1800,
  "subject_code": "MATH101",
  "subject_name": "Mathematics I",
  "color": "#3b82f6",
  "title": "Chapter 5 Practice",
  "started_at": "2024-01-15T09:00:00Z"
}
```

**Response (timer not running)**
```json
{
  "running": false
}
```

### POST /api/timer/start

Start a new study timer.

**Query Parameters**
- `subject_id` (optional): Subject ID
- `chapter_id` (optional): Chapter ID
- `title` (optional): Session title

**Response**
```json
{
  "success": true,
  "session": {
    "id": 16,
    "started_at": "2024-01-15T14:00:00Z"
  },
  "subject": {
    "code": "MATH101",
    "name": "Mathematics I",
    "color": "#3b82f6"
  },
  "message": "Timer started for Chapter 5 Practice"
}
```

### POST /api/timer/stop

Stop the current timer.

**Response**
```json
{
  "success": true,
  "session": { ... },
  "duration_seconds": 5400,
  "duration_formatted": "1h 30m",
  "is_deep_work": true,
  "points_earned": 9,
  "message": "Studied for 1h 30m (Deep Work!)"
}
```

### GET /api/timer/sessions

Get past study sessions.

**Query Parameters**
- `days` (default: 7): Number of days to look back
- `subject_id` (optional): Filter by subject

**Response**
```json
[
  {
    "id": 15,
    "subject_code": "MATH101",
    "subject_name": "Mathematics I",
    "title": "Chapter 5 Practice",
    "started_at": "2024-01-15T09:00:00Z",
    "stopped_at": "2024-01-15T10:30:00Z",
    "duration_seconds": 5400,
    "is_deep_work": true,
    "points_earned": 9
  }
]
```

### GET /api/timer/analytics

Get study time analytics.

**Query Parameters**
- `days` (default: 7): Number of days to analyze

**Response**
```json
{
  "period_days": 7,
  "daily": [
    {
      "date": "2024-01-15",
      "total_seconds": 10800,
      "session_count": 3,
      "deep_work_seconds": 5400,
      "points": 18
    }
  ],
  "by_subject": [
    {
      "id": 1,
      "code": "MATH101",
      "name": "Mathematics I",
      "color": "#3b82f6",
      "total_seconds": 7200,
      "session_count": 2,
      "avg_session_seconds": 3600
    }
  ],
  "totals": {
    "total_seconds": 25200,
    "total_hours": 7.0,
    "total_sessions": 8,
    "avg_session_minutes": 52.5,
    "deep_work_seconds": 10800,
    "deep_work_hours": 3.0,
    "deep_work_ratio": 42.9,
    "total_points": 42
  },
  "today": {
    "total_seconds": 3600,
    "total_minutes": 60.0,
    "session_count": 1,
    "deep_work_seconds": 0
  }
}
```

---

## Schedule & Calendar

### GET /api/schedule/today

Get today's complete schedule.

**Response**
```json
{
  "date": "2024-01-15",
  "day_name": "Monday",
  "timetable": [
    {
      "start": "08:00",
      "end": "09:30",
      "subject": "MATH101",
      "type": "lecture",
      "room": "ENG-101"
    }
  ],
  "tasks": [...],
  "gaps": [
    {
      "start": "10:00",
      "end": "12:00",
      "duration_mins": 120,
      "is_deep_work": true
    }
  ],
  "deadlines": [...]
}
```

### GET /api/schedule/week

Get the full week's schedule.

**Query Parameters**
- `start_date` (optional): Start date (ISO format)

**Response**
```json
{
  "start_date": "2024-01-15",
  "end_date": "2024-01-21",
  "days": [
    {
      "date": "2024-01-15",
      "day_name": "Monday",
      "timetable": [...],
      "tasks": [...],
      "gaps": [...]
    }
  ]
}
```

### GET /api/schedule/gaps

Find deep work opportunities in schedule gaps.

**Query Parameters**
- `days` (default: 7): Number of days to analyze

**Response**
```json
{
  "slots": [
    {
      "date": "2024-01-15",
      "start": "14:00",
      "end": "16:00",
      "duration_mins": 120
    }
  ],
  "count": 5,
  "total_deep_work_mins": 450
}
```

### GET /api/schedule/timetable

Get the KU university timetable.

**Response**
```json
{
  "today": [
    {
      "start": "08:00",
      "end": "09:30",
      "subject": "MATH101",
      "type": "lecture",
      "room": "ENG-101"
    }
  ],
  "full_week": {
    "Sunday": [...],
    "Monday": [...],
    ...
  }
}
```

### POST /api/schedule/redistribute

Redistribute schedule for an upcoming event.

**Request Body (Form)**
- `event_type`: Type of event ("test", "assignment", "presentation")
- `subject_code`: Subject code
- `event_date`: Date of event (ISO format)
- `apply_immediately`: Whether to create tasks immediately

**Response**
```json
{
  "success": true,
  "event": {
    "type": "test",
    "subject": "PHYS102",
    "date": "2024-01-20"
  },
  "blocks": [
    {
      "date": "2024-01-16",
      "start": "14:00",
      "duration_mins": 90,
      "title": "PHYS102 Test Prep: Day 1"
    }
  ],
  "applied": true,
  "tasks_created": 4
}
```

### GET /api/schedule/deadlines

Get all upcoming deadlines.

**Query Parameters**
- `days` (default: 14): Number of days to look ahead

**Response**
```json
{
  "deadlines": [
    {
      "type": "lab_report",
      "title": "PHYS102 Lab Report",
      "due_date": "2024-01-20",
      "days_remaining": 5,
      "urgency": "normal"
    }
  ],
  "count": 8,
  "days": 14
}
```

### GET /api/schedule/context

Get full scheduling context for AI decisions.

**Response**
```json
{
  "current_time": "2024-01-15T14:30:00Z",
  "today": { ... },
  "pending_revisions": [...],
  "upcoming_deadlines": [...],
  "available_gaps": [...],
  "preferences": {
    "sleep_time": "22:30",
    "wake_time": "04:30",
    "max_study_block": 90
  }
}
```

### POST /api/schedule/preferences

Update user's schedule preferences.

**Request Body (Form)**
- `key`: Preference key (e.g., "sleep_time", "wake_time")
- `value`: New value

---

## Timeline Optimization

### GET /api/timeline/today

Get optimized timeline for today with all activity blocks.

**Response**
```json
{
  "date": "2024-01-15",
  "blocks": [
    {
      "id": 1,
      "type": "wake_routine",
      "start": "04:30",
      "end": "05:00",
      "duration_mins": 30,
      "energy_level": 5
    },
    {
      "id": 2,
      "type": "study",
      "start": "05:00",
      "end": "06:30",
      "duration_mins": 90,
      "title": "MATH101 Deep Work",
      "subject_code": "MATH101",
      "is_deep_work": true,
      "energy_level": 9
    }
  ],
  "summary": {
    "study_hours": 6.5,
    "deep_work_hours": 3.0,
    "class_hours": 4.0,
    "free_time_mins": 60
  }
}
```

### GET /api/timeline/{target_date}

Get optimized timeline for a specific date.

**Path Parameters**
- `target_date`: Date in YYYY-MM-DD format

### GET /api/timeline/week/{start_date}

Get optimized weekly timeline.

**Path Parameters**
- `start_date`: Start date in YYYY-MM-DD format (optional)

### POST /api/timeline/optimize/{target_date}

Run optimization algorithm for a specific day.

**Path Parameters**
- `target_date`: Date to optimize

**Response**
```json
{
  "success": true,
  "date": "2024-01-15",
  "changes_made": 3,
  "blocks_optimized": [
    {
      "id": 5,
      "previous_start": "10:00",
      "new_start": "08:00",
      "reason": "Matched to high energy slot"
    }
  ]
}
```

### GET /api/timeline/pending

Get all pending work items sorted by priority.

**Query Parameters**
- `days` (default: 14): Number of days to look ahead

**Response**
```json
{
  "items": [
    {
      "type": "revision",
      "title": "MATH101 Chapter 3 Revision",
      "priority": 65,
      "due_date": "2024-01-16",
      "estimated_mins": 30
    }
  ],
  "count": 12,
  "days": 14
}
```

### POST /api/timeline/backward-plan

Create a backward plan from a deadline.

**Request Body (Form)**
- `deadline_date`: Deadline date (ISO format)
- `item_type`: Type of item ("exam", "assignment", "project")
- `subject_code`: Subject code
- `hours_needed`: Total hours needed
- `title`: Title of the item

**Response**
```json
{
  "success": true,
  "plan": {
    "title": "PHYS102 Final Exam",
    "deadline": "2024-01-25",
    "total_hours": 10,
    "days_available": 10,
    "blocks": [
      {
        "date": "2024-01-16",
        "start": "14:00",
        "duration_mins": 60,
        "title": "Day 1: Overview and concepts"
      }
    ]
  },
  "tasks_created": 10
}
```

### POST /api/timeline/reschedule

Reschedule all pending tasks.

**Request Body (Form)**
- `reason`: Reason for rescheduling

**Response**
```json
{
  "success": true,
  "reason": "Sick day",
  "tasks_moved": 5,
  "new_schedule": [...]
}
```

### POST /api/timeline/blocks

Create a new time block in the schedule.

**Request Body (Form)**
- `date`: Date (ISO format)
- `start_time`: Start time (HH:MM)
- `duration_mins`: Duration in minutes
- `activity_type`: Type ("study", "revision", "assignment", etc.)
- `title`: Block title
- `subject_code` (optional): Subject code
- `priority` (default: 5): Priority level

**Response**
```json
{
  "success": true,
  "block": {
    "id": 25,
    "date": "2024-01-15",
    "start": "14:00",
    "end": "15:30",
    "title": "MATH101 Practice Problems"
  }
}
```

### PATCH /api/timeline/blocks/{task_id}

Move a time block to a new date/time.

**Request Body (Form)**
- `new_date`: New date (ISO format)
- `new_start_time`: New start time (HH:MM)

### DELETE /api/timeline/blocks/{task_id}

Delete a time block.

### POST /api/timeline/free-time

Allocate free time in the schedule.

**Request Body (Form)**
- `date` (optional): Date (defaults to today)
- `minutes` (default: 60): Duration in minutes

**Response**
```json
{
  "success": true,
  "block": {
    "id": 26,
    "type": "free_time",
    "start": "16:00",
    "end": "17:00",
    "title": "Relaxation"
  }
}
```

### POST /api/timeline/revision

Schedule spaced repetition revisions for a chapter.

**Request Body (Form)**
- `chapter_id`: Chapter ID
- `intervals` (optional): Comma-separated intervals (e.g., "1,3,7,14,30")

**Response**
```json
{
  "success": true,
  "chapter": {
    "id": 5,
    "title": "Wave Mechanics"
  },
  "revisions_scheduled": [
    {"day": 1, "date": "2024-01-16"},
    {"day": 3, "date": "2024-01-18"},
    {"day": 7, "date": "2024-01-22"},
    {"day": 14, "date": "2024-01-29"},
    {"day": 30, "date": "2024-02-14"}
  ]
}
```

---

## Study Goals

### GET /api/goals/categories

List all goal categories.

**Response**
```json
[
  {
    "id": 1,
    "name": "Academic",
    "color": "#3b82f6",
    "icon": "book",
    "goal_count": 5,
    "completed_count": 2
  }
]
```

### POST /api/goals/categories

Create a goal category.

**Request Body (Form)**
- `name`: Category name
- `color` (default: "#6366f1"): Color hex code
- `icon` (default: "target"): Icon name

### GET /api/goals

List study goals.

**Query Parameters**
- `category_id` (optional): Filter by category
- `subject_id` (optional): Filter by subject
- `include_completed` (default: false): Include completed goals

**Response**
```json
[
  {
    "id": 1,
    "title": "Complete MATH101 chapters 1-5",
    "category_id": 1,
    "category_name": "Academic",
    "category_color": "#3b82f6",
    "subject_code": "MATH101",
    "target_value": 5,
    "current_value": 3,
    "unit": "chapters",
    "progress_percent": 60.0,
    "deadline": "2024-01-31",
    "days_remaining": 16,
    "completed": false
  }
]
```

### GET /api/goals/{goal_id}

Get a single goal.

### POST /api/goals

Create a study goal.

**Request Body (Form)**
- `title`: Goal title
- `category_id` (optional): Category ID
- `subject_id` (optional): Subject ID
- `description` (optional): Description
- `target_value` (optional): Target value
- `unit` (optional): Unit (e.g., "chapters", "hours")
- `deadline` (optional): Deadline date (ISO format)
- `priority` (default: 5): Priority (1-10)

### PATCH /api/goals/{goal_id}

Update a goal.

**Request Body**
```json
{
  "title": "Updated title",
  "priority": 8
}
```

### POST /api/goals/{goal_id}/progress

Update goal progress.

**Request Body (Form)**
- `progress_delta` (default: 0): Amount to add
- `set_value` (optional): Set value directly
- `mark_complete` (optional): Force completion status

**Response**
```json
{
  "success": true,
  "goal": { ... },
  "progress_percent": 80.0,
  "just_completed": false
}
```

### DELETE /api/goals/{goal_id}

Delete a goal.

### GET /api/goals/summary/stats

Get goals summary statistics.

**Response**
```json
{
  "totals": {
    "total": 10,
    "completed": 4,
    "active": 6,
    "overdue": 1,
    "due_this_week": 2,
    "completion_rate": 40.0
  },
  "by_category": [...],
  "by_subject": [...],
  "recent_completions": [...]
}
```

### GET /api/goals/upcoming/deadlines

Get goals with upcoming deadlines.

**Query Parameters**
- `days` (default: 14): Number of days to look ahead

---

## C Engine Integration

### GET /api/gaps

Analyze schedule for deep work gaps using C engine.

**Response**
```json
{
  "gaps": [
    {
      "start": "10:00",
      "end": "12:00",
      "duration_mins": 120,
      "is_deep_work": true
    }
  ],
  "total_deep_work_mins": 240,
  "engine_version": "1.0"
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD"
}
```

### 404 Not Found

```json
{
  "detail": "Chapter not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Database connection error"
}
```

---

## Rate Limiting

Currently, there are no rate limits on the API. This may change in future versions.

## Versioning

The API version is included in responses from `/health` and `/api/version`. Breaking changes will be communicated through version increments.
