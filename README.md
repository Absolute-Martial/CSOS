# Personal Engineering OS (CSOS)

> AI-powered study management system for KU Engineering students with intelligent scheduling, deep work optimization, and spaced repetition.

![Version](https://img.shields.io/badge/version-1.0.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Next.js](https://img.shields.io/badge/Next.js-14-black)

## Overview

Personal Engineering OS is a comprehensive study management platform designed specifically for KU Engineering students. It combines AI-powered scheduling with proven study techniques like spaced repetition and deep work to maximize learning efficiency.

### Key Features

| Feature | Description |
|---------|-------------|
| **AI Command Center** | Chat interface with GitHub Copilot for natural language schedule management |
| **Smart Scheduling** | KU timetable integration with automatic gap analysis and deep work detection |
| **Spaced Repetition** | Auto-scheduled revisions at optimal intervals (1, 3, 7, 14, 30 days) |
| **Energy-Based Allocation** | Tasks matched to energy levels throughout the day |
| **Lab Report Tracking** | Countdown timers and status tracking for Physics, Chemistry, and Thermal labs |
| **Study Timer** | Session tracking with deep work detection (90+ min threshold) |
| **Goal Tracking** | Academic and personal goals with progress visualization |
| **Timeline Optimization** | AI-driven schedule redistribution for exams and deadlines |
| **Streak and Rewards** | Gamification system to maintain consistency |
| **Long-Term Memory** | AI remembers preferences, patterns, and constraints |

## Architecture

```
+---------------------+     +------------------+     +-----------------+
|  Next.js Frontend   |---->|  FastAPI Backend |---->|   PostgreSQL    |
|  (React/TypeScript) |     |     (Python)     |     |    Database     |
+---------------------+     +--------+---------+     +-----------------+
        |                            |
        |                   +--------+--------+
        |                   |                 |
        v                   v                 v
   +---------+      +-------------+    +-----------+
   | Tailwind|      | copilot-api |    | C Engine  |
   |   CSS   |      |    (LLM)    |    | (Scheduler)|
   +---------+      +-------------+    +-----------+
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons |
| Backend | FastAPI, Python 3.11+, asyncpg, httpx, Pydantic v2 |
| Database | PostgreSQL 16 with triggers and stored procedures |
| AI | GitHub Copilot via copilot-api (OpenAI-compatible endpoint) |
| Scheduler Engine | C (compiled binary for gap analysis) |
| Deployment | Docker, Docker Compose, Dokploy-ready |

## Project Structure

```
CSOS/
+-- backend/
|   +-- main.py              # FastAPI server and all API routes
|   +-- models.py            # Pydantic schemas (v2 syntax)
|   +-- tools.py             # AI tool definitions (40+ tools)
|   +-- scheduler.py         # KU timetable, gap analysis, optimization
|   +-- timer.py             # Study session timer with analytics
|   +-- goals.py             # Goal tracking module
|   +-- database.py          # Async PostgreSQL with asyncpg
|   +-- file_handler.py      # PDF/DOCX file processing
|   +-- requirements.txt     # Python dependencies
|
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   |   +-- page.tsx         # Main dashboard page
|   |   |   +-- layout.tsx       # Root layout
|   |   |   +-- globals.css      # Global styles
|   |   +-- components/
|   |       +-- TodayDashboard.tsx     # Today at a Glance view
|   |       +-- TimelineView.tsx       # Full day timeline
|   |       +-- ScheduleInput.tsx      # AI schedule redistribution
|   |       +-- LabReportTracker.tsx   # Lab report countdown
|   |       +-- StudyTimer.tsx         # Header timer component
|   |       +-- StudyAnalytics.tsx     # Analytics dashboard
|   |       +-- GoalTracker.tsx        # Goal management
|   |       +-- Dashboard.tsx          # Tasks and subjects
|   |       +-- AICommandCenter.tsx    # Chat interface
|   |       +-- SystemBadge.tsx        # System status badge
|   +-- next.config.js       # API proxy configuration
|   +-- package.json
|
+-- database/
|   +-- init.sql             # Complete schema with triggers
|
+-- engine/
|   +-- scheduler.c          # C implementation
|   +-- scheduler.h          # Header file
|   +-- Makefile             # Build configuration
|
+-- deploy/
|   +-- docker-compose.yml   # Full stack deployment (see deploy/docker-compose.yml)
|   +-- Dockerfile.backend   # Multi-stage backend build
|   +-- Dockerfile.frontend  # Multi-stage frontend build
|   +-- .env.example         # Environment template
|
+-- start-local.bat          # Windows local launcher
+-- stop-local.bat           # Windows stop script
+-- CLAUDE.md                # AI assistant instructions
+-- README.md                # This file
```

## Getting Started

### Prerequisites

- **Node.js 20+**: [nodejs.org](https://nodejs.org/)
- **Python 3.11+**: [python.org](https://python.org/)
- **Docker Desktop**: [docker.com](https://docker.com/)
- **GitHub Copilot Pro**: Required for AI features ([github.com/features/copilot](https://github.com/features/copilot))

### Windows Quick Start (Recommended)

```batch
REM Double-click or run from terminal
start-local.bat
```

This will:
1. Start PostgreSQL in Docker (with persistent volume)
2. Initialize the database schema
3. Launch copilot-api (authenticate with GitHub on first run)
4. Start the FastAPI backend on port 8000
5. Start the Next.js frontend on port 3000
6. Open your browser to http://localhost:3000

### Docker Deployment

```bash
# 1. First-time only: Authenticate copilot-api
npx copilot-api@latest start
# Follow browser prompts, then Ctrl+C

# 2. Start all services
docker compose up -d

# 3. View logs
docker compose logs -f

# Services available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Manual Development Setup

```bash
# Terminal 1: PostgreSQL
docker run --name engineering-os-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=engineering_os \
  -p 5432:5432 \
  -v engineering-os-data:/var/lib/postgresql/data \
  -d postgres:16-alpine

# Initialize schema (first time only)
docker exec -i engineering-os-db psql -U postgres -d engineering_os < database/init.sql

# Terminal 2: copilot-api
npx copilot-api@latest start

# Terminal 3: Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 4: Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://postgres:postgres@localhost:5432/engineering_os | PostgreSQL connection string |
| COPILOT_API_URL | http://localhost:4141 | copilot-api endpoint |
| UPLOAD_DIR | ./uploads | File upload directory |
| ENGINE_PATH | ../engine/scheduler | Path to C engine binary |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| NEXT_PUBLIC_API_URL | http://localhost:8000 | Backend API URL (client-side) |
| INTERNAL_API_URL | - | Backend URL for Docker networking |

## AI Tool System

The AI assistant has access to 40+ tools organized into categories:

### Core Tools
- edit_schedule - Add/update/delete tasks
- analyze_gaps - Find deep work opportunities
- update_chapter_progress - Track reading/assignment completion
- get_revision_queue - Pending spaced repetition items
- save_memory / get_memory - Long-term AI memory
- add_guideline - User-defined behavior rules

### Schedule Control Tools
- create_time_block - Create study/revision blocks
- move_time_block / delete_time_block - Modify schedule
- get_optimized_schedule - AI-optimized day view
- reschedule_all - Emergency rescheduling
- backward_plan - Plan from deadline backward
- schedule_chapter_revision - Set up spaced repetition

### Scheduler Tools
- get_today_schedule / get_week_schedule - View schedules
- find_deep_work_slots - 90+ min available blocks
- schedule_event_prep - Auto-schedule for exams/tests
- get_lab_reports - Lab countdown with urgency
- get_upcoming_deadlines - All deadlines aggregated

### Timer and Analytics Tools
- start_study_timer / stop_study_timer - Session tracking
- get_study_stats - Study time analytics
- create_study_goal / update_goal_progress - Goal management

## API Reference

See [docs/API.md](docs/API.md) for complete API documentation.

### Quick Reference

| Category | Endpoints |
|----------|-----------|
| Health | GET /health, GET /api/version |
| AI Chat | POST /api/chat, GET /api/briefing |
| Schedule | GET /api/schedule/today, GET /api/schedule/week, POST /api/schedule/redistribute |
| Timeline | GET /api/timeline/today, POST /api/timeline/blocks, POST /api/timeline/backward-plan |
| Timer | GET /api/timer/status, POST /api/timer/start, POST /api/timer/stop |
| Goals | GET /api/goals, POST /api/goals, POST /api/goals/{id}/progress |
| Labs | GET /api/labs/countdown, POST /api/labs/track |
| Tasks | GET /api/tasks/today, POST /api/tasks |

## KU Timetable Configuration

Edit backend/scheduler.py to configure your university schedule:

```python
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
    # ... continue for other days
}
```

## Usage Examples

### AI Chat Commands

```
"What should I study today?"
"I have a CHEM103 test on Friday"
"Schedule 3 hours for the physics lab report"
"Find deep work slots for this week"
"I finished reading MATH101 Chapter 5"
"Give me my morning briefing"
"Remember that I wake up at 5am"
"Add rule: Always schedule breaks after 90 min sessions"
```

### Example Workflow

1. **Morning**: Check the briefing for today priorities
2. **Study Session**: Start timer, the system tracks deep work automatically
3. **Chapter Complete**: Mark reading done, spaced repetition auto-scheduled
4. **Test Announced**: Tell AI "I have a test Friday", schedule redistributes
5. **End of Day**: Review analytics, adjust goals

## Troubleshooting

### copilot-api Not Connecting

```bash
# Check if running
curl http://localhost:4141/v1/models

# If not authenticated
npx copilot-api@latest start
# Complete GitHub OAuth flow
```

### Database Connection Issues

```bash
# Check PostgreSQL container
docker ps | grep engineering-os-db

# View logs
docker logs engineering-os-db

# Reset database (CAUTION: loses data)
docker compose down -v
docker compose up -d
```

### Schedule Not Showing Classes

1. Verify KU_TIMETABLE in backend/scheduler.py matches your schedule
2. Check day names are correct (Sunday, Monday, etc.)
3. Times must be in "HH:MM" 24-hour format

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - System design and components
- [API Reference](docs/API.md) - Complete endpoint documentation
- [Development Guide](docs/DEVELOPMENT.md) - Contributing and extending

## Contributing

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit changes (git commit -m 'Add amazing feature')
4. Push to branch (git push origin feature/amazing-feature)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with care for KU Engineering Students | Version 1.0.1
