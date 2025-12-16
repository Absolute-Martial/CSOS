# Development Guide

This guide covers everything you need to know to develop, extend, and maintain the Personal Engineering OS project.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Backend Development](#backend-development)
4. [Frontend Development](#frontend-development)
5. [Adding New AI Tools](#adding-new-ai-tools)
6. [Modifying the Scheduler](#modifying-the-scheduler)
7. [Database Migrations](#database-migrations)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## Development Environment Setup

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 20+ | Frontend runtime |
| Python | 3.11+ | Backend runtime |
| Docker | Latest | Database and containerization |
| Git | Latest | Version control |
| VS Code | Latest | Recommended IDE |

### Initial Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd CSOS
```

2. **Install backend dependencies**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Install frontend dependencies**
```bash
cd frontend
npm install
```

4. **Start PostgreSQL**
```bash
docker run --name engineering-os-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=engineering_os \
  -p 5432:5432 \
  -v engineering-os-data:/var/lib/postgresql/data \
  -d postgres:16-alpine
```

5. **Initialize the database**
```bash
docker exec -i engineering-os-db psql -U postgres -d engineering_os < database/init.sql
```

6. **Start copilot-api**
```bash
npx copilot-api@latest start
# Follow GitHub OAuth prompts on first run
```

7. **Start the backend**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

8. **Start the frontend**
```bash
cd frontend
npm run dev
```

### VS Code Extensions

Recommended extensions for development:
- Python (Microsoft)
- Pylance
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- PostgreSQL (ckolkman)

### Environment Files

Create `.env` files for local development:

**backend/.env**
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/engineering_os
COPILOT_API_URL=http://localhost:4141
UPLOAD_DIR=./uploads
ENGINE_PATH=../engine/scheduler
```

**frontend/.env.local**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Project Structure

```
CSOS/
+-- backend/                 # FastAPI backend
|   +-- main.py             # API routes and app setup
|   +-- models.py           # Pydantic schemas
|   +-- tools.py            # AI tool definitions
|   +-- scheduler.py        # Scheduling logic
|   +-- timer.py            # Study timer module
|   +-- goals.py            # Goals module
|   +-- database.py         # Database operations
|   +-- file_handler.py     # File processing
|   +-- requirements.txt    # Python dependencies
|
+-- frontend/               # Next.js frontend
|   +-- src/
|   |   +-- app/           # App router pages
|   |   +-- components/    # React components
|   +-- next.config.js     # Next.js configuration
|   +-- tailwind.config.js # Tailwind configuration
|   +-- package.json       # Node dependencies
|
+-- database/              # Database scripts
|   +-- init.sql          # Schema initialization
|
+-- engine/               # C scheduler engine
|   +-- scheduler.c       # Main implementation
|   +-- scheduler.h       # Header file
|   +-- Makefile         # Build configuration
|
+-- deploy/              # Deployment files
|   +-- docker-compose.yml
|   +-- Dockerfile.backend
|   +-- Dockerfile.frontend
|
+-- docs/                # Documentation
```

---

## Backend Development

### Adding New API Endpoints

1. **Add the route in `main.py`**:

```python
@app.get("/api/my-endpoint")
async def my_endpoint(param: str = Query(default="default")):
    """Endpoint description for API docs."""
    # Implementation
    return {"result": "value"}

@app.post("/api/my-endpoint")
async def create_something(
    field1: str = Form(...),
    field2: Optional[int] = Form(None)
):
    """Create something new."""
    # Implementation
    return {"success": True, "data": {...}}
```

2. **Add database queries in `database.py`** if needed:

```python
async def my_query(param: str) -> List[dict]:
    return await db.fetch(
        "SELECT * FROM my_table WHERE field = $1",
        param
    )
```

3. **Add Pydantic models in `models.py`** for request/response validation:

```python
class MyRequest(BaseModel):
    field1: str
    field2: Optional[int] = None

class MyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field1: str
    created_at: datetime
```

### Database Operations Pattern

All database operations use the async `Database` class:

```python
from database import db

# Fetch multiple rows
rows = await db.fetch("SELECT * FROM table WHERE x = $1", value)

# Fetch single row
row = await db.fetch_one("SELECT * FROM table WHERE id = $1", id)

# Execute (INSERT, UPDATE, DELETE)
await db.execute("UPDATE table SET x = $1 WHERE id = $2", value, id)

# Execute with RETURNING
result = await db.execute_returning(
    "INSERT INTO table (x) VALUES ($1) RETURNING *",
    value
)
```

### Error Handling

Use HTTPException for API errors:

```python
from fastapi import HTTPException

if not item:
    raise HTTPException(status_code=404, detail="Item not found")

if invalid_input:
    raise HTTPException(status_code=400, detail="Invalid input: reason")
```

Log system events:

```python
from database import log_system

await log_system("info", "Operation completed", {"key": "value"})
await log_system("error", "Something failed", {"error": str(e)})
```

---

## Frontend Development

### Component Structure

Components follow this pattern:

```typescript
'use client'

import { useEffect, useState } from 'react'

interface MyComponentProps {
    initialValue?: string
    onUpdate?: (value: string) => void
}

export default function MyComponent({ initialValue, onUpdate }: MyComponentProps) {
    const [data, setData] = useState<DataType | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        fetchData()
    }, [])

    const fetchData = async () => {
        try {
            setLoading(true)
            const res = await fetch('/api/endpoint')
            if (!res.ok) throw new Error('Failed to fetch')
            const data = await res.json()
            setData(data)
        } catch (error) {
            setError('Failed to load data')
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return <div className="animate-pulse">Loading...</div>
    }

    if (error) {
        return <div className="text-red-500">{error}</div>
    }

    return (
        <div className="glass rounded-2xl p-6">
            {/* Component content */}
        </div>
    )
}
```

### Styling Conventions

The project uses Tailwind CSS with custom classes defined in `globals.css`:

```css
/* Custom glass effect */
.glass {
    @apply bg-surface/80 backdrop-blur-lg border border-white/10;
}

/* Card hover effect */
.card-hover {
    @apply transition-all duration-200 hover:translate-y-[-2px] hover:shadow-lg;
}

/* Gradient backgrounds */
.gradient-primary {
    @apply bg-gradient-to-r from-primary to-secondary;
}
```

### API Calls

Use the fetch API with proper error handling:

```typescript
const apiCall = async (endpoint: string, options?: RequestInit) => {
    try {
        const res = await fetch(`/api/${endpoint}`, options)
        if (!res.ok) {
            const error = await res.json()
            throw new Error(error.detail || 'API error')
        }
        return await res.json()
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error)
        throw error
    }
}

// Usage
const data = await apiCall('schedule/today')
const result = await apiCall('tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(taskData)
})
```

---

## Adding New AI Tools

### Step 1: Define the Tool

Add the tool definition to `TOOL_DEFINITIONS` in `backend/tools.py`:

```python
{
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "Clear description of what this tool does and when to use it",
        "parameters": {
            "type": "object",
            "properties": {
                "required_param": {
                    "type": "string",
                    "description": "What this parameter is for"
                },
                "optional_param": {
                    "type": "integer",
                    "description": "Optional parameter description"
                }
            },
            "required": ["required_param"]
        }
    }
}
```

### Step 2: Implement the Handler

Add the handler function in `tools.py`:

```python
async def tool_my_new_tool(args: dict) -> dict:
    """
    Handler for my_new_tool.

    Args:
        args: Dictionary containing:
            - required_param: Description
            - optional_param: Description (optional)

    Returns:
        Dictionary with results
    """
    required_param = args.get("required_param")
    optional_param = args.get("optional_param", default_value)

    # Validate inputs
    if not required_param:
        return {"error": "required_param is required"}

    # Perform the operation
    try:
        result = await some_operation(required_param)
        return {
            "success": True,
            "data": result,
            "message": "Operation completed successfully"
        }
    except Exception as e:
        await log_system("error", f"my_new_tool failed: {e}")
        return {"error": str(e)}
```

### Step 3: Register in Execute Tool

Add the tool to the `execute_tool` function:

```python
async def execute_tool(name: str, args: dict) -> dict:
    """Execute a tool by name."""
    tools = {
        # ... existing tools ...
        "my_new_tool": tool_my_new_tool,
    }

    if name not in tools:
        return {"error": f"Unknown tool: {name}"}

    return await tools[name](args)
```

### Tool Design Guidelines

1. **Clear naming**: Use descriptive verb_noun names (e.g., `get_schedule`, `create_task`)
2. **Good descriptions**: Help the LLM understand when to use the tool
3. **Robust validation**: Always validate inputs before processing
4. **Meaningful responses**: Return success/failure status and helpful messages
5. **Error handling**: Catch exceptions and return error messages, don't crash

---

## Modifying the Scheduler

### KU Timetable Configuration

Edit `KU_TIMETABLE` in `backend/scheduler.py`:

```python
KU_TIMETABLE = {
    "Sunday": [
        {
            "start": "08:00",
            "end": "09:00",
            "subject": "MATH101",
            "type": "lecture",
            "room": "ENG-101"
        },
        # Add more classes...
    ],
    "Monday": [...],
    # Continue for all days...
}
```

### Daily Routine Configuration

Modify `DAILY_ROUTINE_CONFIG`:

```python
DAILY_ROUTINE_CONFIG = {
    "sleep_start": "23:00",
    "sleep_end": "06:00",
    "wake_routine_mins": 30,
    "breakfast_mins": 30,
    "breakfast_time": "07:00",
    "lunch_time": "13:00",
    "lunch_mins": 45,
    "dinner_time": "19:30",
    "dinner_mins": 45,
    "max_study_block_mins": 90,
    "min_break_after_study": 15,
    "deep_work_min_duration": 90,
}
```

### Energy Curve

Customize energy levels throughout the day:

```python
ENERGY_CURVE = {
    "06:00": 5,   # Just woke up
    "07:00": 7,   # After routine
    "08:00": 9,   # Peak morning
    "09:00": 10,  # Peak
    "10:00": 9,   # Still high
    "11:00": 8,   # Pre-lunch dip
    "12:00": 6,   # Lunch time
    "13:00": 4,   # Post-lunch low
    "14:00": 5,   # Recovery
    "15:00": 7,   # Afternoon rise
    "16:00": 8,   # Second peak
    "17:00": 7,   # Evening
    "18:00": 6,   # Winding down
    "19:00": 5,   # Dinner
    "20:00": 4,   # Low energy
    "21:00": 3,   # Pre-sleep
    "22:00": 2,   # Sleep time
}
```

### Adding New Activity Types

1. Add the type to `ActivityType` enum:

```python
class ActivityType(str, Enum):
    STUDY = "study"
    REVISION = "revision"
    # Add your new type
    MY_TYPE = "my_type"
```

2. Update the scheduling functions to handle the new type

3. Add UI support in the frontend

---

## Database Migrations

### Adding New Columns

```sql
-- Add column to existing table
ALTER TABLE tasks ADD COLUMN new_field VARCHAR(100);

-- Add with default value
ALTER TABLE tasks ADD COLUMN priority_level INTEGER DEFAULT 5;

-- Add with constraint
ALTER TABLE tasks ADD COLUMN status VARCHAR(20)
    CHECK (status IN ('pending', 'active', 'done'));
```

### Creating New Tables

```sql
-- Create new table
CREATE TABLE my_new_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    related_id INTEGER REFERENCES other_table(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_my_table_name ON my_new_table(name);
CREATE INDEX idx_my_table_related ON my_new_table(related_id);
```

### Adding Triggers

```sql
-- Create trigger function
CREATE OR REPLACE FUNCTION my_trigger_function()
RETURNS TRIGGER AS $$
BEGIN
    -- Trigger logic here
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        -- Do something when status changes to completed
        UPDATE other_table SET count = count + 1 WHERE id = NEW.related_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER tr_my_trigger
    AFTER UPDATE ON my_table
    FOR EACH ROW
    EXECUTE FUNCTION my_trigger_function();
```

### Migration Best Practices

1. **Always backup** before running migrations
2. **Test locally** before production
3. **Keep migrations reversible** when possible
4. **Document changes** in migration files
5. **Use transactions** for multi-step migrations

---

## Testing

### Backend Testing

Create test files in `backend/tests/`:

```python
# tests/test_api.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_create_task(client):
    response = await client.post(
        "/api/tasks",
        json={"title": "Test task", "priority": 5}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Test task"
```

Run tests:
```bash
cd backend
pytest -v
```

### Frontend Testing

```typescript
// __tests__/components/Dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import Dashboard from '@/components/Dashboard'

describe('Dashboard', () => {
    it('renders loading state initially', () => {
        render(<Dashboard />)
        expect(screen.getByText(/loading/i)).toBeInTheDocument()
    })

    it('displays tasks after loading', async () => {
        render(<Dashboard />)
        await waitFor(() => {
            expect(screen.getByText(/tasks/i)).toBeInTheDocument()
        })
    })
})
```

Run tests:
```bash
cd frontend
npm test
```

---

## Deployment

### Docker Deployment

1. **Build and start services**:
```bash
cd deploy
docker-compose up -d --build
```

2. **View logs**:
```bash
docker-compose logs -f
```

3. **Stop services**:
```bash
docker-compose down
```

4. **Reset database** (caution: loses data):
```bash
docker-compose down -v
docker-compose up -d
```

### Production Checklist

- [ ] Update environment variables
- [ ] Run database migrations
- [ ] Test all critical functionality
- [ ] Configure backups
- [ ] Set up monitoring
- [ ] Configure SSL/TLS
- [ ] Review security settings

### Dokploy Deployment

See `deploy/DOKPLOY.md` for detailed Dokploy deployment instructions.

---

## Troubleshooting

### Common Issues

#### copilot-api Not Connecting

```bash
# Check if running
curl http://localhost:4141/v1/models

# If authentication needed
npx copilot-api@latest start
# Complete OAuth flow
```

#### Database Connection Errors

```bash
# Check PostgreSQL container
docker ps | grep postgres

# View container logs
docker logs engineering-os-db

# Restart container
docker restart engineering-os-db
```

#### Frontend Build Errors

```bash
# Clear cache and rebuild
rm -rf frontend/.next frontend/node_modules
cd frontend
npm install
npm run build
```

#### Python Import Errors

```bash
# Ensure virtual environment is active
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Debug Mode

**Backend**: Uvicorn runs with `--reload` by default in development

**Frontend**: Next.js provides detailed error pages in development

**Database**: Enable query logging:
```python
# In database.py
import logging
logging.getLogger('asyncpg').setLevel(logging.DEBUG)
```

### Performance Issues

1. **Slow API responses**: Check database indexes
2. **Memory usage**: Monitor with `docker stats`
3. **Frontend slow**: Use React DevTools Profiler

---

## Contributing

### Code Style

**Python**: Follow PEP 8, use type hints
```python
async def my_function(param: str, optional: Optional[int] = None) -> dict:
    """Function description."""
    pass
```

**TypeScript**: Use ESLint configuration
```typescript
interface MyType {
    field: string
    optionalField?: number
}

const myFunction = (param: string): MyType => {
    // Implementation
}
```

### Commit Messages

Use conventional commits:
```
feat: Add new scheduling feature
fix: Resolve timer calculation bug
docs: Update API documentation
refactor: Improve database query performance
test: Add tests for goals module
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with tests
3. Update documentation if needed
4. Submit PR with clear description
5. Address review feedback
6. Merge after approval
