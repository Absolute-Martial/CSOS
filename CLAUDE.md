# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal Engineering OS is an AI-powered study management system for KU Engineering students. It uses GitHub Copilot (via copilot-api proxy) for AI chat capabilities with tool calling. The system features smart scheduling with KU timetable integration, deep work gap analysis, lab report tracking, and AI-driven schedule optimization.

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Next.js Frontend   │────▶│  FastAPI Backend │────▶│   PostgreSQL    │
│  (React/TypeScript) │     │     (Python)     │     │    Database     │
└─────────────────────┘     └────────┬─────────┘     └─────────────────┘
                                     │
                            ┌────────┴─────────┐
                            ▼                  ▼
                    ┌─────────────┐    ┌─────────────┐
                    │ copilot-api │    │  C Engine   │
                    │   (LLM)     │    │ (Scheduler) │
                    └─────────────┘    └─────────────┘
```

### Key Components

- **Frontend** (`frontend/`): Next.js 14 with App Router, TypeScript, Tailwind CSS. Uses API rewrites to proxy `/api/*` to backend.
- **Backend** (`backend/`): FastAPI with async PostgreSQL (asyncpg). Handles AI chat via copilot-api's OpenAI-compatible endpoint with tool calling.
- **C Engine** (`engine/`): Deep work gap analyzer. Called via subprocess from Python. Outputs JSON for integration.
- **Database** (`database/init.sql`): PostgreSQL schema with triggers for auto-scheduling revisions and streak updates.

### Frontend Components

| Component | Purpose |
|-----------|---------|
| `TodayDashboard.tsx` | "Today at a Glance" - KU timetable + tasks + gaps + deadlines |
| `TimelineView.tsx` | Full day timeline with all activity blocks + optimization |
| `ScheduleInput.tsx` | AI-driven schedule redistribution ("I have a test Friday") |
| `LabReportTracker.tsx` | Lab report countdown with status tracking |
| `StudyTimer.tsx` | Header timer with subject selection, deep work indicator |
| `StudyAnalytics.tsx` | Analytics dashboard with charts and period selector |
| `GoalTracker.tsx` | Goal listing with progress bars and creation modal |
| `Dashboard.tsx` | Main dashboard with tasks and subjects |
| `AICommandCenter.tsx` | Chat interface with AI |

### AI Tool System

The backend exposes AI tools in `backend/tools.py` that the LLM can call:

**Core Tools:**
- `edit_schedule` - Add/update/delete tasks
- `analyze_gaps` - Find deep work opportunities (calls C engine)
- `update_chapter_progress` - Track reading/assignment completion
- `get_revision_queue` - Get pending spaced repetition revisions
- `save_memory` / `get_memory` - AI long-term memory
- `add_guideline` - User-defined AI behavior rules

**AI Schedule Control Tools (Full Calendar Access):**
- `create_time_block` - Create study/revision/assignment blocks in calendar
- `move_time_block` - Move existing blocks to new times
- `delete_time_block` - Remove blocks from schedule
- `get_optimized_schedule` - Get AI-optimized day schedule based on energy levels
- `get_weekly_timeline` - Get full week optimization
- `reschedule_all` - Reschedule everything when plans change drastically
- `backward_plan` - Plan backward from a deadline
- `schedule_chapter_revision` - Set up spaced repetition (1, 3, 7, 14, 30 days)
- `allocate_free_time` - Add relaxation blocks intelligently
- `update_schedule_preference` - Update user preferences (sleep time, etc.)
- `get_schedule_context` - Get full context before making decisions
- `get_pending_items` - See all pending work sorted by priority
- `get_full_timeline` - Get complete day with all blocks

**Scheduler Tools (Smart Scheduling):**
- `get_today_schedule` - Full view (KU timetable + tasks + gaps)
- `get_week_schedule` - Week view with gap analysis
- `find_deep_work_slots` - Find 90+ min blocks for deep work
- `schedule_event_prep` - "I have a test Friday" → auto-schedule study blocks
- `get_lab_reports` - Lab report countdown (Physics, Chemistry, Thermal)
- `add_lab_report` / `update_lab_report` - Track lab report progress
- `get_upcoming_deadlines` - All upcoming due dates

**Study Timer Tools:**
- `start_study_timer` - Start timed study session with optional subject
- `stop_study_timer` - Stop timer and record session
- `get_timer_status` - Check if timer is running
- `get_study_stats` - Get study analytics for period

**Goal Tools:**
- `create_study_goal` - Create goal with optional target/deadline
- `update_goal_progress` - Update progress value
- `get_goals` - List active/completed goals
- `get_goals_summary` - Get completion stats by category

**Long-Term Memory Tools:**
- `remember_user_info` - Store user preferences, habits, constraints
- `recall_memories` - Retrieve stored information
- `forget_memory` - Remove outdated information

**Proactive Notification Tools:**
- `send_proactive_notification` - Send immediate notifications (reminder, suggestion, achievement, warning, motivation)
- `schedule_reminder` - Schedule future reminders for specific times

System prompt is built dynamically in `build_system_prompt()` with user guidelines and memories.

### Key Modules

| Module | Purpose |
|--------|---------|
| `backend/scheduler.py` | KU timetable, gap analysis, timeline optimization, energy-based allocation |
| `backend/timer.py` | Study session timer with deep work detection |
| `backend/goals.py` | Study goal tracking with progress |
| `backend/tools.py` | AI tool definitions and handlers |
| `backend/wellbeing.py` | Student wellbeing monitoring, stress detection, break management |
| `backend/notifications.py` | Proactive notification system with WebSocket support |
| `backend/learning_patterns.py` | Study pattern analysis, effectiveness tracking, adaptive recommendations |

## Dynamic Timeline Optimization

The scheduler implements intelligent timeline optimization:

### Activity Types
- `sleep`, `wake_routine`, `breakfast`, `lunch`, `dinner` - Fixed daily routines
- `university` - KU classes (fixed)
- `study`, `revision`, `practice`, `assignment`, `lab_work` - Flexible study blocks
- `deep_work` - Extended focus sessions (90+ min)
- `break`, `free_time` - Rest and relaxation

### Energy-Based Scheduling
The system models energy levels throughout the day:
- Peak energy (8-10): 8-10am, 4-6pm → Schedule difficult tasks
- Medium energy (5-7): 6-8am, 10am-12pm, 2-4pm, 6-8pm
- Low energy (3-5): After meals, late evening → Schedule easy tasks or breaks

### Priority System (TaskPriority)
Tasks are prioritized by urgency:
```
OVERDUE = 100      # Past deadline
DUE_TODAY = 90     # Due today
EXAM_PREP = 85     # Exam preparation
URGENT_LAB = 75    # Lab report due soon
REVISION_DUE = 65  # Spaced repetition due
ASSIGNMENT = 60    # Regular assignment
REGULAR_STUDY = 50 # Normal study
FREE_TIME = 10     # Relaxation
```

### Spaced Repetition
Default intervals for chapter revision: 1, 3, 7, 14, 30 days (based on forgetting curve)

### Backward Planning
When given a deadline, the system:
1. Calculates days available
2. Finds all gaps between now and deadline
3. Distributes work evenly with increasing intensity near deadline
4. Creates time blocks automatically

## KU Timetable Configuration

Edit `backend/scheduler.py` to configure your university timetable:

```python
KU_TIMETABLE = {
    "Sunday": [
        {"start": "08:00", "end": "09:00", "subject": "MATH101", "type": "lecture", "room": "ENG-101"},
        ...
    ],
    "Monday": [...],
    ...
}

DAILY_ROUTINE_CONFIG = {
    "sleep_start": "23:00",
    "sleep_end": "06:00",
    "wake_routine_mins": 30,
    "breakfast_mins": 30,
    "lunch_time": "13:00",
    "dinner_time": "19:30",
    "max_study_block_mins": 90,
    "min_break_after_study": 15,
    ...
}
```

The scheduler uses this to:
- Find gaps between classes for study blocks
- Identify deep work opportunities (90+ min gaps)
- Auto-schedule preparation for tests/assignments
- Match task difficulty to energy levels

## Commands

### Local Development (Windows)
```batch
# Start all services (PostgreSQL, copilot-api, backend, frontend)
start-local.bat

# Stop all services
stop-local.bat
```

### Manual Start
```bash
# Frontend (localhost:3000)
cd frontend && npm install && npm run dev

# Backend (localhost:8000)
cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

# C Engine
cd engine && make && ./scheduler --help
```

### Docker
```bash
cd deploy && docker-compose up -d
```

## Database

Schema in `database/init.sql`. Key tables: `subjects`, `chapters`, `chapter_progress`, `tasks`, `revision_schedule`, `ai_memory`, `ai_guidelines`, `lab_reports`.

**Feature Tables:**
- `study_sessions` / `active_timer` - Study timer tracking
- `lab_reports` - Lab report tracking with status and deadlines
- `study_goals` / `goal_categories` - Goal tracking with progress
- `daily_study_stats` - Aggregated daily statistics
- `tasks` - Includes `task_type` (study, revision, practice, assignment, lab_work)
- `wellbeing_metrics` - Daily wellbeing scores, stress indicators, recommendations
- `break_sessions` - Break tracking with types (short, pomodoro, meal, exercise, meditation)
- `pomodoro_status` - Pomodoro timer state (singleton table)
- `learning_patterns` - Cached learning patterns per subject (best time, effectiveness, duration)
- `session_effectiveness` - Per-session focus scores, energy levels, material covered

Database triggers automatically:
- Schedule weekly revisions (7/14/21 days) when chapter reading completes
- Update user streaks on revision completion
- Calculate session duration and points when timer stops

## Environment Variables

```env
# Backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/engineering_os
COPILOT_API_URL=http://localhost:4141
UPLOAD_DIR=./uploads
ENGINE_PATH=../engine/scheduler

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Naming Conventions (AI-Enforced)

- Subject codes: `[A-Z]{4}[0-9]{3}` (e.g., MATH101, PHYS102)
- Chapter folders: `chapter[0-9]{2}` (e.g., chapter01)
- Uploaded files: snake_case (e.g., lecture_notes.pdf)

## Critical Files

These files require extra care when modifying:

| File | Impact | Notes |
|------|--------|-------|
| `backend/tools.py` | AI behavior | TOOL_DEFINITIONS array - changes affect what LLM can do |
| `backend/scheduler.py` | Schedule logic | KU_TIMETABLE, gap analysis, timeline optimization, energy curves |
| `database/init.sql` | Data integrity | Schema + triggers - changes need migration strategy |
| `backend/main.py` | All API routes | Central entry point, CORS config |
| `backend/timer.py` | Timer logic | Deep work detection (90min threshold) |
| `backend/learning_patterns.py` | Pattern analysis | PatternAnalyzer, RecommendationEngine - affects study suggestions |
| `frontend/next.config.js` | API proxy | Rewrites `/api/*` to backend |

## API Reference

### Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (copilot-api status) |
| GET | `/api/version` | Version metadata |

### AI Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Chat with AI (tool calling enabled) |
| GET | `/api/briefing` | Morning briefing summary |

### Scheduler & Calendar
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/schedule/today` | Today at a Glance (timetable + tasks + gaps) |
| GET | `/api/schedule/week` | Week schedule with gap analysis |
| GET | `/api/schedule/gaps` | Deep work opportunities |
| GET | `/api/schedule/timetable` | KU timetable configuration |
| POST | `/api/schedule/redistribute` | Auto-schedule for event prep |
| GET | `/api/schedule/deadlines` | All upcoming deadlines |
| GET | `/api/schedule/context` | Full context for AI decisions |
| POST | `/api/schedule/preferences` | Update schedule preferences |

### Timeline Optimization (NEW)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/timeline/today` | Optimized timeline for today |
| GET | `/api/timeline/{date}` | Timeline for specific date |
| GET | `/api/timeline/week/{date}` | Weekly timeline |
| POST | `/api/timeline/optimize/{date}` | Run optimization for day |
| GET | `/api/timeline/pending` | Pending work items by priority |
| POST | `/api/timeline/backward-plan` | Create backward plan from deadline |
| POST | `/api/timeline/reschedule` | Reschedule all pending tasks |
| POST | `/api/timeline/blocks` | Create time block |
| PATCH | `/api/timeline/blocks/{id}` | Move time block |
| DELETE | `/api/timeline/blocks/{id}` | Delete time block |
| POST | `/api/timeline/free-time` | Allocate free time |
| POST | `/api/timeline/revision` | Schedule chapter revisions |

### Lab Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/labs/countdown` | Pending reports with countdown |
| POST | `/api/labs/track` | Track new lab report |
| PATCH | `/api/labs/{id}/status` | Update report status |

### Study Timer
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/timer/status` | Get active timer status |
| POST | `/api/timer/start` | Start study timer |
| POST | `/api/timer/stop` | Stop timer, record session |
| GET | `/api/timer/sessions` | List study sessions |
| GET | `/api/timer/analytics` | Get study analytics |

### Study Goals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/goals` | List goals |
| POST | `/api/goals` | Create goal |
| POST | `/api/goals/{id}/progress` | Update goal progress |
| GET | `/api/goals/summary/stats` | Get goals summary |

### Wellbeing Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/wellbeing/score` | Get wellbeing score (0-1) with stress level and recommendations |
| GET | `/api/wellbeing/check` | Quick health check - returns alerts if needed |
| POST | `/api/wellbeing/break/start` | Start a break session (types: short, pomodoro, meal, exercise, meditation, long) |
| POST | `/api/wellbeing/break/{id}/end` | End a break session |
| GET | `/api/wellbeing/break/active` | Get currently active break |
| GET | `/api/wellbeing/break/suggest` | Get break suggestion based on current state |
| GET | `/api/wellbeing/break/stats` | Get break statistics for period |
| GET | `/api/wellbeing/history` | Get wellbeing history for trends |
| GET | `/api/wellbeing/trends` | Get wellbeing trend analysis |
| POST | `/api/wellbeing/save-daily` | Save daily wellbeing metrics |
| GET | `/api/wellbeing/notifications` | Get wellbeing notifications |

### Pomodoro Timer
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pomodoro/status` | Get Pomodoro timer status |
| POST | `/api/pomodoro/work` | Start Pomodoro work session (25 min) |
| POST | `/api/pomodoro/break` | Start Pomodoro break (5 or 15 min) |
| POST | `/api/pomodoro/stop` | Stop Pomodoro timer |
| POST | `/api/pomodoro/reset` | Reset Pomodoro timer |

### Learning Patterns
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patterns` | Get all cached learning patterns |
| GET | `/api/patterns/overall` | Get overall pattern across all subjects |
| GET | `/api/patterns/subject/{code}` | Get pattern for specific subject |
| GET | `/api/patterns/hourly` | Get productivity by hour of day |
| GET | `/api/patterns/trends` | Get productivity trend analysis |
| POST | `/api/sessions/{id}/effectiveness` | Record session effectiveness (focus, energy) |
| GET | `/api/sessions/effectiveness` | Get effectiveness history |
| GET | `/api/recommendations` | Get personalized study recommendations |
| GET | `/api/recommendations/optimal-time` | Get optimal study time for subject |
| GET | `/api/recommendations/duration` | Get suggested session duration |

### Proactive Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| WebSocket | `/ws/notifications` | Real-time notification delivery (WebSocket) |
| GET | `/api/notifications/proactive` | Get proactive notifications (supports limit, unread_only, offset) |
| GET | `/api/notifications/proactive/count` | Get unread and total notification counts |
| POST | `/api/notifications/proactive/{id}/read` | Mark notification as read |
| POST | `/api/notifications/proactive/{id}/dismiss` | Dismiss (hide) notification |
| POST | `/api/notifications/proactive/read-all` | Mark all notifications as read |
| GET | `/api/notifications/preferences` | Get notification preferences by type |
| PUT | `/api/notifications/preferences/{type}` | Update preferences (enabled, quiet_hours, frequency_limit) |
| POST | `/api/notifications/test` | Send test notification (debugging) |

### Tasks & Schedule
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/today` | Today's tasks |
| POST | `/api/tasks` | Create task |
| PATCH | `/api/tasks/{id}` | Update task |
| DELETE | `/api/tasks/{id}` | Delete task |

## Error Handling

### Backend Patterns
- Use `HTTPException` for API errors with appropriate status codes
- Log errors via `log_system("error", message, context)`
- copilot-api fallback: Returns helpful message if AI service unavailable

### Frontend Patterns
- API calls wrapped in `.catch(() => [])` for graceful degradation
- Loading states with skeleton UI (`animate-pulse`)

## Debugging Tips

### copilot-api Not Connecting
```bash
# Check if running
curl http://localhost:4141/v1/models

# Start if needed
npx copilot-api@latest start
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Or start via Docker
docker-compose -f deploy/docker-compose.yml up -d postgres
```

### Schedule Not Showing Classes
- Verify `KU_TIMETABLE` in `backend/scheduler.py` matches your actual schedule
- Check the day names are correct (Sunday, Monday, etc.)
- Times must be in "HH:MM" 24-hour format
