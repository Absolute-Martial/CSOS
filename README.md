# Personal Engineering OS

> AI-powered study management system for KU Engineering students

![Version](https://img.shields.io/badge/version-1.0.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 Features

- **AI Command Center** - Chat with GitHub Copilot to manage your schedule
- **Chapter Tracking** - Track reading → assignment → revision progress
- **Weekly Revision** - Auto-scheduled spaced repetition (7/14/21 days)
- **Credit Priority** - Higher-credit subjects get priority in revision queue
- **Streak & Rewards** - Gamification to keep you consistent (🔥→⚡→🌟→💎)
- **File Storage** - Upload slides/assignments per chapter (PDF, DOCX, PPTX)
- **Deep Work Analysis** - C engine finds >90 min gaps in your schedule
- **AI Guidelines** - Define rules the AI must follow
- **Long-term Memory** - AI remembers your patterns and preferences

## 📁 Project Structure

```
CSOS/
├── database/
│   └── init.sql           # PostgreSQL schema
├── engine/
│   ├── scheduler.c        # C logic (COMP 102 style)
│   ├── scheduler.h
│   └── Makefile
├── backend/
│   ├── main.py            # FastAPI server
│   ├── models.py          # Pydantic schemas
│   ├── tools.py           # AI function definitions
│   ├── file_handler.py    # PDF/DOCX parsing
│   ├── database.py        # PostgreSQL connection
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   └── components/    # React components
│   └── package.json
├── deploy/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── backup.sh
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- [Node.js 20+](https://nodejs.org/)
- [Python 3.11+](https://python.org/)
- [Docker](https://docker.com/) (optional)
- [GitHub Copilot Pro subscription](https://github.com/features/copilot)

### Option 1: Docker (Recommended)

```bash
# 1. First, authenticate copilot-api (one-time)
npx copilot-api@latest start
# Follow browser prompts to authenticate with GitHub
# Press Ctrl+C after authentication

# 2. Start all services
cd deploy
docker-compose up -d

# 3. Open browser
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# Terminal 1: Start copilot-api
npx copilot-api@latest start

# Terminal 2: Start PostgreSQL (Docker)
docker run -d --name eng-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=engineering_os \
  -p 5432:5432 \
  -v ./database/init.sql:/docker-entrypoint-initdb.d/init.sql \
  postgres:16-alpine

# Terminal 3: Start backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 4: Start frontend
cd frontend
npm install
npm run dev
```

## 🌐 Tailscale Deployment

For remote access via Tailscale:

```bash
# 1. Install Tailscale
# https://tailscale.com/download

# 2. Start Tailscale
tailscale up

# 3. Note your Tailscale IP
tailscale ip -4

# 4. Update docker-compose.yml ports to bind to Tailscale IP
# Or use: docker-compose up with EXPOSE_HOST=100.x.x.x

# 5. Access from any Tailscale device
# http://100.x.x.x:3000
```

## 📖 Usage

### AI Commands

```
"What should I revise today?"
"I finished PHYS 102 Chapter 3 assignment"
"Add rule: No studying after 21:00"
"Find deep work gaps in my schedule"
"Give me my morning briefing"
```

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `POST /api/chat` | AI chat |
| `GET /api/briefing` | Morning summary |
| `GET /api/subjects` | List subjects |
| `GET /api/revisions/pending` | Revision queue |
| `POST /api/chapters/{id}/upload` | Upload file |

## 🔧 Configuration

### Environment Variables

```env
# Backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/engineering_os
COPILOT_API_URL=http://localhost:4141
UPLOAD_DIR=./uploads

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📦 Versioning

We use [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (e.g., `1.0.1`)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Current: **v1.0.1**

## 🔒 Backup

Nightly backups run via cron:

```bash
# Add to crontab
0 3 * * * /path/to/deploy/backup.sh
```

Backups are stored in `/backups/` with 7-day retention.

## 🛠 Maintenance

### Compile C Engine

```bash
cd engine
make clean && make
./scheduler --help
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

## 📝 License

MIT License - Feel free to use and modify!

---

Built with ❤️ for KU Engineering Students
