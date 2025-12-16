# Architecture Guide

This document provides a comprehensive overview of the Personal Engineering OS (CSOS) architecture, explaining how all components work together to create an AI-powered study management system.

## System Overview

Personal Engineering OS is built as a three-tier application with additional specialized components:

```
                                    +------------------+
                                    |     User         |
                                    |   (Browser)      |
                                    +--------+---------+
                                             |
                                             | HTTP/HTTPS
                                             v
+------------------------------------------------------------------------------------+
|                              PRESENTATION LAYER                                     |
|  +---------------------------+                                                      |
|  |    Next.js Frontend       |   Port: 3000                                        |
|  |    - React 18             |   - Server-side rendering                           |
|  |    - TypeScript           |   - API proxy via rewrites                          |
|  |    - Tailwind CSS         |   - Real-time UI updates                            |
|  +---------------------------+                                                      |
+------------------------------------------------------------------------------------+
                                             |
                                             | API Calls (/api/*)
                                             v
+------------------------------------------------------------------------------------+
|                               APPLICATION LAYER                                     |
|  +---------------------------+       +---------------------------+                  |
|  |    FastAPI Backend        |       |    copilot-api            |                  |
|  |    Port: 8000             |<----->|    Port: 4141             |                  |
|  |    - Async Python         |       |    - OpenAI-compatible    |                  |
|  |    - Tool definitions     |       |    - GitHub Copilot proxy |                  |
|  |    - Business logic       |       +---------------------------+                  |
|  +---------------------------+                                                      |
|              |                                                                      |
|              | Subprocess                                                           |
|              v                                                                      |
|  +---------------------------+                                                      |
|  |    C Scheduler Engine     |                                                      |
|  |    - Gap analysis         |                                                      |
|  |    - Priority queue       |                                                      |
|  |    - JSON output          |                                                      |
|  +---------------------------+                                                      |
+------------------------------------------------------------------------------------+
                                             |
                                             | SQL (asyncpg)
                                             v
+------------------------------------------------------------------------------------+
|                                  DATA LAYER                                         |
|  +---------------------------+                                                      |
|  |    PostgreSQL 16          |   Port: 5432                                        |
|  |    - Triggers             |   - Auto-scheduling                                  |
|  |    - Stored procedures    |   - Streak updates                                   |
|  |    - JSONB columns        |   - Session analytics                                |
|  +---------------------------+                                                      |
+------------------------------------------------------------------------------------+
```

## Component Details

### 1. Frontend (Next.js)

**Location**: `frontend/`

The frontend is built with Next.js 14 using the App Router pattern.

#### Key Files

| File | Purpose |
|------|---------|
| `src/app/page.tsx` | Main dashboard with tab navigation |
| `src/app/layout.tsx` | Root layout with global styles |
| `src/app/globals.css` | Tailwind CSS + custom styles |
| `next.config.js` | API proxy configuration |

#### Components

| Component | Description |
|-----------|-------------|
| `TodayDashboard.tsx` | "Today at a Glance" - shows KU timetable, tasks, gaps, and deadlines |
| `TimelineView.tsx` | Full day timeline visualization with all activity blocks |
| `ScheduleInput.tsx` | Natural language input for schedule redistribution |
| `LabReportTracker.tsx` | Lab report countdown with status indicators |
| `StudyTimer.tsx` | Header-mounted timer with subject selection |
| `StudyAnalytics.tsx` | Analytics dashboard with charts |
| `GoalTracker.tsx` | Goal management with progress bars |
| `Dashboard.tsx` | Task and subject management |
| `AICommandCenter.tsx` | Chat interface with the AI |
| `SystemBadge.tsx` | System status indicator |

#### API Proxy

The frontend proxies all `/api/*` requests to the backend:

```javascript
// next.config.js
async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL || 'http://localhost:8000'
    return [{ source: '/api/:path*', destination: `${apiUrl}/api/:path*` }]
}
```

### 2. Backend (FastAPI)

**Location**: `backend/`

The backend is an async Python application using FastAPI with Pydantic v2.

#### Key Modules

| Module | Responsibility |
|--------|---------------|
| `main.py` | API routes, middleware, startup/shutdown |
| `tools.py` | AI tool definitions (40+ tools) |
| `scheduler.py` | KU timetable, gap analysis, optimization |
| `timer.py` | Study session management |
| `goals.py` | Goal tracking with categories |
| `database.py` | Async PostgreSQL operations |
| `models.py` | Pydantic schemas |
| `file_handler.py` | File upload processing |

#### Request Flow

```
Request -> FastAPI Router -> Handler Function -> Database/Service -> Response
                                |
                                +-> AI Chat: copilot-api -> Tool Calls -> Handler
```

### 3. AI Tool System

The AI tool system enables natural language interaction with the application.

#### Tool Categories

**Core Tools**
- `edit_schedule` - Create, update, delete tasks
- `analyze_gaps` - Find deep work opportunities
- `update_chapter_progress` - Track study progress
- `get_revision_queue` - Get pending revisions
- `save_memory` / `get_memory` - Persistent AI memory
- `add_guideline` - User-defined AI rules

**Schedule Control**
- `create_time_block` - Create calendar blocks
- `move_time_block` - Reschedule blocks
- `delete_time_block` - Remove blocks
- `get_optimized_schedule` - AI-optimized day view
- `reschedule_all` - Emergency rescheduling
- `backward_plan` - Plan from deadline backward
- `schedule_chapter_revision` - Set up spaced repetition

**Scheduler Tools**
- `get_today_schedule` / `get_week_schedule` - View schedules
- `find_deep_work_slots` - Find 90+ min gaps
- `schedule_event_prep` - Auto-prep for exams
- `get_lab_reports` - Lab countdown
- `get_upcoming_deadlines` - Deadline aggregation

**Timer Tools**
- `start_study_timer` / `stop_study_timer` - Session control
- `get_timer_status` - Current timer state
- `get_study_stats` - Analytics

**Goal Tools**
- `create_study_goal` - Create goals
- `update_goal_progress` - Update progress
- `get_goals` - List goals
- `get_goals_summary` - Statistics

#### Tool Execution Flow

```
1. User Message -> Backend
2. Backend builds system prompt with:
   - User guidelines
   - AI memories
   - Current context
3. Message + Tools sent to copilot-api
4. LLM returns response with tool_calls
5. Backend executes each tool
6. Results sent back to LLM
7. Final response returned to user
```

### 4. Scheduler Engine

**Location**: `engine/`

The C scheduler engine provides high-performance gap analysis.

#### Data Structures

```c
typedef struct {
    int hour;
    int minute;
} TimeSlot;

typedef struct {
    int id;
    char title[MAX_TITLE_LEN];
    char subject[20];
    int priority;
    int duration_mins;
    TimeSlot start_time;
    TimeSlot end_time;
    bool is_deep_work;
    bool completed;
} Task;

typedef struct {
    TimeSlot start;
    TimeSlot end;
    int duration_mins;
} ScheduleGap;
```

#### Key Functions

- `analyze_gaps()` - Find gaps between scheduled items
- `get_deep_work_gaps()` - Filter gaps >= 90 minutes
- `pq_insert()` / `pq_extract_min()` - Priority queue operations
- `print_gaps_json()` - JSON output for Python integration

### 5. Database Schema

**Location**: `database/init.sql`

#### Core Tables

| Table | Purpose |
|-------|---------|
| `subjects` | Course subjects with credits and type |
| `chapters` | Chapter definitions per subject |
| `chapter_progress` | Reading/assignment completion status |
| `tasks` | Scheduled tasks with priority |
| `revision_schedule` | Spaced repetition schedule |

#### Feature Tables

| Table | Purpose |
|-------|---------|
| `study_sessions` | Completed study sessions |
| `active_timer` | Currently running timer (max 1) |
| `lab_reports` | Lab report tracking |
| `study_goals` | Goal definitions |
| `goal_categories` | Goal categories |
| `daily_study_stats` | Aggregated daily statistics |

#### AI Tables

| Table | Purpose |
|-------|---------|
| `ai_memory` | Persistent AI memory (key-value by category) |
| `ai_guidelines` | User-defined AI rules |
| `conversation_history` | Chat history |

#### Supporting Tables

| Table | Purpose |
|-------|---------|
| `user_streaks` | Current/longest streak, total points |
| `rewards` | Unlockable rewards |
| `achievements` | Achievement definitions |
| `notifications` | User notifications |
| `flashcards` / `flashcard_decks` | Flashcard system |

#### Key Triggers

**Auto-Schedule Revisions**
```sql
-- When chapter reading completes, schedule revisions at 7, 14, 21 days
CREATE TRIGGER tr_schedule_revisions
    BEFORE UPDATE ON chapter_progress
    FOR EACH ROW
    EXECUTE FUNCTION schedule_weekly_revisions();
```

**Update Daily Stats**
```sql
-- When study session stops, calculate duration and update stats
CREATE TRIGGER tr_update_daily_stats
    BEFORE UPDATE ON study_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_daily_study_stats();
```

**Streak Updates**
```sql
-- When revision completed or 30+ min session, update streak
CREATE TRIGGER tr_update_streak_session
    AFTER UPDATE ON study_sessions
    WHEN (NEW.stopped_at IS NOT NULL AND OLD.stopped_at IS NULL)
    EXECUTE FUNCTION update_streak_on_session();
```

## Energy-Based Scheduling

The scheduler models user energy levels throughout the day:

```python
ENERGY_CURVE = {
    "06:00": 5,   # Waking up
    "07:00": 7,   # Morning routine done
    "08:00": 9,   # Peak morning
    "09:00": 10,  # Peak
    "10:00": 9,   # Slight dip
    "12:00": 6,   # Pre-lunch
    "13:00": 4,   # Post-lunch dip
    "14:00": 5,   # Recovery
    "15:00": 7,   # Afternoon pickup
    "16:00": 8,   # Good focus
    "17:00": 7,   # Winding down
    "18:00": 6,   # Evening
    "19:00": 5,   # Dinner time
    "20:00": 4,   # Low energy
    "21:00": 3,   # Pre-sleep
    "22:00": 2,   # Sleep time
}
```

### Task Allocation Strategy

1. **High Energy (8-10)**: Complex problem-solving, new concepts
2. **Medium Energy (5-7)**: Review, practice problems
3. **Low Energy (3-5)**: Administrative tasks, easy reading

### Priority System

```python
class TaskPriority:
    OVERDUE = 100      # Past deadline
    DUE_TODAY = 90     # Due today
    EXAM_PREP = 85     # Exam preparation
    URGENT_LAB = 75    # Lab report due soon
    REVISION_DUE = 65  # Spaced repetition due
    ASSIGNMENT = 60    # Regular assignment
    REGULAR_STUDY = 50 # Normal study
    FREE_TIME = 10     # Relaxation
```

## Spaced Repetition

The system implements evidence-based spaced repetition:

### Default Intervals
- Day 1: Initial learning
- Day 3: First revision
- Day 7: Second revision
- Day 14: Third revision
- Day 30: Long-term retention

### SM-2 Algorithm (Flashcards)

```python
def calculate_next_review(quality: int, repetitions: int, ease_factor: float, interval: int):
    if quality < 3:  # Failed recall
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = round(interval * ease_factor)

        ease_factor = max(1.3, ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        repetitions += 1

    return repetitions, ease_factor, interval
```

## Data Flow Examples

### 1. Starting a Study Session

```
User clicks "Start Timer"
    |
    v
Frontend: POST /api/timer/start
    |
    v
Backend: timer.start_timer(subject_id, chapter_id, title)
    |
    +-> Check if timer already running
    +-> INSERT INTO study_sessions
    +-> INSERT INTO active_timer
    |
    v
Response: {success: true, session: {...}}
    |
    v
Frontend: Update UI with running timer
```

### 2. AI Schedule Optimization

```
User: "I have a physics test on Friday"
    |
    v
Frontend: POST /api/chat {message: "..."}
    |
    v
Backend:
    1. Build system prompt with context
    2. Call copilot-api with tools
    |
    v
LLM: Calls schedule_event_prep tool
    |
    v
Backend:
    1. Get days until Friday
    2. Find available gaps
    3. Create study blocks
    4. INSERT INTO tasks
    |
    v
Response: "I've scheduled 3 study sessions..."
    |
    v
Frontend: Refresh timeline
```

### 3. Backward Planning

```
User: "Plan study for MATH101 exam in 5 days"
    |
    v
AI calls backward_plan tool:
    1. Calculate total hours needed
    2. Find all gaps between now and deadline
    3. Distribute hours with increasing intensity
       - Day 1: 1 hour (overview)
       - Day 2: 1.5 hours (concepts)
       - Day 3: 2 hours (practice)
       - Day 4: 2.5 hours (intensive)
       - Day 5: 3 hours (final review)
    4. Match tasks to high-energy slots
    5. Create time blocks
    |
    v
Response: Timeline with scheduled blocks
```

## Security Considerations

### Database
- Parameterized queries via asyncpg
- Connection pooling (min 2, max 10)
- No raw SQL string concatenation

### API
- CORS configured for localhost in development
- File upload size limits
- Input validation via Pydantic

### copilot-api
- Runs locally only
- Requires GitHub authentication
- No API keys exposed

## Performance Optimizations

### Database
- Indexes on frequently queried columns
- Connection pooling
- Aggregated stats in `daily_study_stats`

### Frontend
- Server-side rendering where beneficial
- Optimistic UI updates
- Skeleton loading states

### Backend
- Async operations throughout
- Efficient query batching
- Subprocess calls for C engine

## Deployment Architecture

### Docker Compose

```
+------------------+     +------------------+
|     frontend     |---->|     backend      |
|    Port: 3000    |     |    Port: 8000    |
+------------------+     +--------+---------+
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                  +-----------+     +-----------+
                  |    db     |     |copilot-api|
                  |Port: 5432 |     |Port: 4141 |
                  +-----------+     +-----------+
```

### Environment Configuration

| Service | Environment Variables |
|---------|----------------------|
| Backend | DATABASE_URL, COPILOT_API_URL, UPLOAD_DIR, ENGINE_PATH |
| Frontend | NEXT_PUBLIC_API_URL, INTERNAL_API_URL |
| Database | POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB |

## Extending the Architecture

### Adding New AI Tools

1. Define tool in `backend/tools.py`:
```python
{
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "What this tool does",
        "parameters": {
            "type": "object",
            "properties": {...},
            "required": [...]
        }
    }
}
```

2. Implement handler in tool execution switch

### Adding New API Endpoints

1. Add route in `backend/main.py`
2. Create handler function
3. Add database queries if needed
4. Update frontend to consume

### Adding New Frontend Components

1. Create component in `frontend/src/components/`
2. Import in page or parent component
3. Add API calls as needed
