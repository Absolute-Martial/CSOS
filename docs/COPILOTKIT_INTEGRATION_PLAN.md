# CopilotKit Integration Plan for Personal Engineering OS

## Overview

This document outlines a comprehensive plan to integrate CopilotKit into the Personal Engineering OS, replacing the current copilot-api implementation. CopilotKit provides native React integration with streaming, multi-turn tool calling, and a robust context-sharing system that will significantly enhance the AI-driven personal assistant capabilities.

**Current State**: Custom chat UI with copilot-api backend proxy
**Target State**: CopilotKit-powered AI assistant with real-time state sync, generative UI, and intelligent task reminders

---

## Architecture Comparison

### Current Architecture
```
┌─────────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  AICommandCenter.tsx│────▶│  FastAPI Backend │────▶│   copilot-api   │
│  (Custom Chat UI)   │     │  POST /api/chat  │     │  (localhost:4141)│
└─────────────────────┘     └────────┬─────────┘     └─────────────────┘
                                     │
                            ┌────────┴─────────┐
                            ▼                  ▼
                    ┌─────────────┐    ┌─────────────┐
                    │  52 Python  │    │  PostgreSQL │
                    │    Tools    │    │   Database  │
                    └─────────────┘    └─────────────┘
```

### Target Architecture with CopilotKit
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                                  │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────────────────┐ │
│  │ CopilotKit  │  │ useCopilotRead- │  │  useFrontendTool (Actions)   │ │
│  │  Provider   │  │ able (Context)  │  │  - Quick task add            │ │
│  └─────────────┘  └─────────────────┘  │  - Timer control             │ │
│         │                              │  - UI updates                │ │
│         ▼                              └──────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    CopilotSidebar / CopilotChat                     ││
│  │  - Streaming responses                                              ││
│  │  - Generative UI for tool results                                   ││
│  │  - Human-in-the-loop confirmations                                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │              API Route: /api/copilotkit/route.ts                    ││
│  │  CopilotRuntime with Remote Endpoint → FastAPI                      ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Backend                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                 /copilotkit - CopilotKit Endpoint                   ││
│  │  - Handles tool definitions from CopilotKit SDK                     ││
│  │  - Routes to Python action handlers                                 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    52 Backend Actions                               ││
│  │  - Schedule Control (14 actions)                                    ││
│  │  - Timer Tools (4 actions)                                          ││
│  │  - Goal Tools (4 actions)                                           ││
│  │  - Memory Tools (6 actions)                                         ││
│  │  - Scheduler Tools (9 actions)                                      ││
│  │  - Core Tools (11 actions)                                          ││
│  └─────────────────────────────────────────────────────────────────────┘│
│         │                                                               │
│         ▼                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  scheduler.py │  │   timer.py   │  │   goals.py   │  ← Business Logic│
│  │  database.py  │  │   models.py  │  │   tools.py   │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                          ┌─────────────────┐
                          │   PostgreSQL    │
                          │    Database     │
                          └─────────────────┘
```

---

## Implementation Phases

## Phase 1: Frontend Setup

### 1.1 Install CopilotKit Packages

```bash
cd frontend
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime
```

### 1.2 Create CopilotKit Provider Wrapper

**File: `frontend/src/providers/CopilotProvider.tsx`**

```typescript
'use client'

import { CopilotKit } from "@copilotkit/react-core";
import { ReactNode } from "react";

interface CopilotProviderProps {
  children: ReactNode;
}

export default function CopilotProvider({ children }: CopilotProviderProps) {
  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      transcribeAudioUrl="/api/copilotkit" // For voice input (optional)
      agent="study_assistant" // Default agent name
    >
      {children}
    </CopilotKit>
  );
}
```

### 1.3 Update Root Layout

**File: `frontend/src/app/layout.tsx`**

```typescript
import CopilotProvider from "@/providers/CopilotProvider";
import "@copilotkit/react-ui/styles.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <CopilotProvider>
          {children}
        </CopilotProvider>
      </body>
    </html>
  );
}
```

---

## Phase 2: Create CopilotKit API Route

**File: `frontend/src/app/api/copilotkit/route.ts`**

```typescript
import { NextRequest } from "next/server";
import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  ExperimentalEmptyAdapter,
} from "@copilotkit/runtime";

// Connect to FastAPI backend for Python actions
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const runtime = new CopilotRuntime({
  remoteEndpoints: [
    {
      url: `${BACKEND_URL}/copilotkit`,
    },
  ],
});

// Use ExperimentalEmptyAdapter since LLM calls go through backend
const serviceAdapter = new ExperimentalEmptyAdapter();

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
```

---

## Phase 3: Backend CopilotKit Integration

### 3.1 Install Python SDK

```bash
cd backend
pip install copilotkit fastapi-copilotkit
# Add to requirements.txt
```

### 3.2 Create CopilotKit Endpoint

**File: `backend/copilotkit_endpoint.py`**

```python
"""
CopilotKit integration endpoint for Personal Engineering OS
Handles AI chat with tool calling through CopilotKit protocol
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

from tools import TOOL_DEFINITIONS, execute_tool, build_system_prompt
from database import get_ai_guidelines, get_ai_memory, log_system

router = APIRouter()

# Configuration
COPILOT_API_URL = "http://localhost:4141"  # LLM provider endpoint


def convert_tools_to_copilotkit_format(tools: List[Dict]) -> List[Dict]:
    """
    Convert existing OpenAI-format tool definitions to CopilotKit format.
    CopilotKit uses a similar but slightly different structure.
    """
    converted = []
    for tool in tools:
        if tool.get("type") == "function":
            func = tool["function"]
            converted.append({
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"]
            })
    return converted


async def stream_chat_response(messages: List[Dict], tools: List[Dict]):
    """
    Stream chat response from LLM with tool handling.
    """
    system_prompt = await build_system_prompt()

    full_messages = [
        {"role": "system", "content": system_prompt},
        *messages
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COPILOT_API_URL}/v1/chat/completions",
            json={
                "model": "gpt-4",
                "messages": full_messages,
                "tools": TOOL_DEFINITIONS,
                "tool_choice": "auto",
                "stream": True  # Enable streaming
            },
            timeout=120
        )

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="LLM service error")

        async for chunk in response.aiter_text():
            yield chunk


@router.post("/copilotkit")
async def copilotkit_handler(request: Request):
    """
    Main CopilotKit endpoint.
    Handles the CopilotKit protocol for chat and tool execution.
    """
    try:
        body = await request.json()

        # CopilotKit sends different types of requests
        request_type = body.get("type", "chat")

        if request_type == "actions":
            # Return available actions/tools
            return {
                "actions": convert_tools_to_copilotkit_format(TOOL_DEFINITIONS)
            }

        elif request_type == "execute":
            # Execute a specific tool
            action_name = body.get("name")
            action_args = body.get("arguments", {})

            await log_system("info", f"Executing action: {action_name}", {"args": action_args})

            result = await execute_tool(action_name, action_args)

            return {"result": result}

        elif request_type == "chat":
            # Handle chat request with streaming
            messages = body.get("messages", [])

            return StreamingResponse(
                stream_chat_response(messages, TOOL_DEFINITIONS),
                media_type="text/event-stream"
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown request type: {request_type}")

    except Exception as e:
        await log_system("error", f"CopilotKit error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/copilotkit/context")
async def get_copilotkit_context():
    """
    Return current context for CopilotKit.
    Used to provide knowledge base to the AI.
    """
    from scheduler import get_today_at_glance, get_lab_report_countdown
    from timer import get_active_timer
    from goals import get_goals

    # Gather current state
    today_schedule = await get_today_at_glance()
    lab_reports = await get_lab_report_countdown()
    active_timer = await get_active_timer()
    goals = await get_goals(include_completed=False)
    guidelines = await get_ai_guidelines()
    memories = await get_ai_memory()

    return {
        "schedule": today_schedule,
        "lab_reports": lab_reports,
        "active_timer": active_timer,
        "goals": goals,
        "guidelines": [g["rule"] for g in guidelines],
        "memories": {m["key"]: m["value"] for m in memories},
        "timestamp": datetime.now().isoformat()
    }
```

### 3.3 Register Router in main.py

**Add to `backend/main.py`:**

```python
from copilotkit_endpoint import router as copilotkit_router

# Add after other middleware setup
app.include_router(copilotkit_router, tags=["CopilotKit"])
```

---

## Phase 4: Migrate Tools to CopilotKit Actions

### 4.1 Tool Categories and Migration Strategy

The 52 existing tools will be migrated in the following categories:

#### Category 1: Frontend Actions (8 tools)
These are quick, UI-focused actions that can run client-side:

| Tool | Frontend Action | Reason |
|------|-----------------|--------|
| `start_study_timer` | Yes | Quick UI interaction |
| `stop_study_timer` | Yes | Quick UI interaction |
| `get_timer_status` | Yes | Read-only, UI display |
| `send_notification` | Yes | Browser notification API |
| `quick_add_task` | Yes (New) | Fast task creation |
| `toggle_deep_work` | Yes (New) | UI mode switch |
| `refresh_schedule` | Yes (New) | Force UI refresh |
| `show_help` | Yes (New) | Display help modal |

#### Category 2: Backend Actions with Streaming UI (15 tools)
Complex operations that need progress indicators:

| Tool | Streaming | Reason |
|------|-----------|--------|
| `schedule_event_prep` | Yes | Multi-step planning |
| `backward_plan` | Yes | Creates multiple blocks |
| `reschedule_all` | Yes | Batch operation |
| `analyze_gaps` | Yes | Calls C engine |
| `optimize_day_schedule` | Yes | Algorithm processing |
| `get_optimized_schedule` | Yes | Algorithm processing |
| `get_weekly_timeline` | Yes | Multi-day processing |

#### Category 3: Standard Backend Actions (29 tools)
Regular CRUD operations:

All remaining tools including:
- `edit_schedule`, `create_time_block`, `move_time_block`, `delete_time_block`
- `create_study_goal`, `update_goal_progress`, `get_goals`, `get_goals_summary`
- `add_lab_report`, `update_lab_report`, `get_lab_reports`
- `save_memory`, `get_memory`, `remember_user_info`, `recall_memories`, `forget_memory`
- etc.

### 4.2 Frontend Action Definitions

**File: `frontend/src/hooks/useCopilotActions.ts`**

```typescript
import { useFrontendTool, useCopilotReadable } from "@copilotkit/react-core";
import { useCallback, useEffect, useState } from "react";

// Types
interface Task {
  id: number;
  title: string;
  subject_code?: string;
  duration_mins: number;
  priority: number;
  status: string;
}

interface TimerStatus {
  running: boolean;
  elapsed_seconds?: number;
  subject_code?: string;
  title?: string;
}

interface Schedule {
  timetable: any[];
  tasks: Task[];
  gaps: any[];
  lab_reports: any[];
  revisions: any[];
}

export function useCopilotActions() {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [timerStatus, setTimerStatus] = useState<TimerStatus>({ running: false });
  const [pendingRevisions, setPendingRevisions] = useState<any[]>([]);
  const [goals, setGoals] = useState<any[]>([]);

  // Fetch initial data
  useEffect(() => {
    fetchSchedule();
    fetchTimerStatus();
    fetchRevisions();
    fetchGoals();

    // Poll for updates every 30 seconds
    const interval = setInterval(() => {
      fetchTimerStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const fetchSchedule = async () => {
    const res = await fetch('/api/schedule/today');
    if (res.ok) setSchedule(await res.json());
  };

  const fetchTimerStatus = async () => {
    const res = await fetch('/api/timer/status');
    if (res.ok) setTimerStatus(await res.json());
  };

  const fetchRevisions = async () => {
    const res = await fetch('/api/revisions/pending');
    if (res.ok) setPendingRevisions(await res.json());
  };

  const fetchGoals = async () => {
    const res = await fetch('/api/goals');
    if (res.ok) setGoals(await res.json());
  };

  // ============================================
  // CONTEXT SHARING (useCopilotReadable)
  // ============================================

  useCopilotReadable({
    description: "Today's complete schedule including KU timetable classes, scheduled tasks, available time gaps, and energy levels throughout the day. Use this to understand what the user has planned and when they're free.",
    value: schedule,
  });

  useCopilotReadable({
    description: "Current study timer status - whether a timer is running, for how long, and which subject. Use this to know if user is actively studying.",
    value: timerStatus,
  });

  useCopilotReadable({
    description: "Pending spaced repetition revisions sorted by priority. These are chapters due for review based on the forgetting curve (1, 3, 7, 14, 30 day intervals).",
    value: pendingRevisions,
  });

  useCopilotReadable({
    description: "Active study goals with progress, targets, and deadlines. Goals are categorized as Academic, Skill Building, Personal, or Career.",
    value: goals,
  });

  // ============================================
  // FRONTEND ACTIONS (useFrontendTool)
  // ============================================

  // Timer: Start
  useFrontendTool({
    name: "start_study_timer",
    description: "Start a study timer. Use when user says 'I'm studying X' or 'Start timer for X'. This helps track study sessions and awards points.",
    parameters: [
      {
        name: "subject_code",
        type: "string",
        description: "Subject code like MATH101, PHYS102. Optional.",
        required: false
      },
      {
        name: "title",
        type: "string",
        description: "Custom session title like 'Chapter 5 review'. Optional.",
        required: false
      }
    ],
    render: ({ status, args }) => (
      <div className="p-4 bg-green-500/20 rounded-lg">
        {status === "executing" && <p>Starting timer...</p>}
        {status === "complete" && (
          <p>Timer started{args.subject_code ? ` for ${args.subject_code}` : ''}!</p>
        )}
      </div>
    ),
    handler: async ({ subject_code, title }) => {
      const res = await fetch('/api/timer/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject_code, title })
      });
      const result = await res.json();
      await fetchTimerStatus();
      return result;
    }
  });

  // Timer: Stop
  useFrontendTool({
    name: "stop_study_timer",
    description: "Stop the current study timer and record the session. Use when user says 'stop timer' or 'done studying'.",
    parameters: [],
    render: ({ status, result }) => (
      <div className="p-4 bg-blue-500/20 rounded-lg">
        {status === "executing" && <p>Stopping timer...</p>}
        {status === "complete" && result && (
          <div>
            <p>Session recorded!</p>
            <p>Duration: {Math.round(result.duration_seconds / 60)} minutes</p>
            {result.is_deep_work && <p>Deep work session!</p>}
          </div>
        )}
      </div>
    ),
    handler: async () => {
      const res = await fetch('/api/timer/stop', { method: 'POST' });
      const result = await res.json();
      await fetchTimerStatus();
      return result;
    }
  });

  // Quick Add Task
  useFrontendTool({
    name: "quick_add_task",
    description: "Quickly add a task to today's schedule. Use for simple task additions.",
    parameters: [
      { name: "title", type: "string", description: "Task title", required: true },
      { name: "subject_code", type: "string", description: "Subject code (optional)", required: false },
      { name: "duration_mins", type: "number", description: "Duration in minutes (default 60)", required: false },
      { name: "priority", type: "number", description: "Priority 1-10 (default 5)", required: false }
    ],
    render: ({ status, args }) => (
      <div className="p-4 bg-purple-500/20 rounded-lg">
        {status === "executing" && <p>Adding task: {args.title}...</p>}
        {status === "complete" && <p>Task added to schedule!</p>}
      </div>
    ),
    handler: async ({ title, subject_code, duration_mins = 60, priority = 5 }) => {
      const res = await fetch('/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          subject_code,
          duration_mins,
          priority,
          scheduled_start: new Date().toISOString()
        })
      });
      const result = await res.json();
      await fetchSchedule();
      return result;
    }
  });

  // Refresh Schedule
  useFrontendTool({
    name: "refresh_schedule",
    description: "Force refresh of today's schedule and timeline. Use when user asks to see updated schedule.",
    parameters: [],
    handler: async () => {
      await fetchSchedule();
      await fetchRevisions();
      await fetchGoals();
      return { success: true, message: "Schedule refreshed" };
    }
  });

  // Return refresh functions for components to use
  return {
    schedule,
    timerStatus,
    pendingRevisions,
    goals,
    refreshSchedule: fetchSchedule,
    refreshTimer: fetchTimerStatus,
    refreshRevisions: fetchRevisions,
    refreshGoals: fetchGoals
  };
}
```

---

## Phase 5: Replace AICommandCenter with CopilotSidebar

### 5.1 Create New Chat Component

**File: `frontend/src/components/StudyAssistant.tsx`**

```typescript
'use client'

import { CopilotSidebar } from "@copilotkit/react-ui";
import { useCopilotAdditionalInstructions, useCopilotChatSuggestions } from "@copilotkit/react-core";
import { useCopilotActions } from "@/hooks/useCopilotActions";
import { useEffect, useState } from "react";

interface StudyAssistantProps {
  className?: string;
}

export default function StudyAssistant({ className }: StudyAssistantProps) {
  const { schedule, timerStatus, pendingRevisions, goals } = useCopilotActions();
  const [userGuidelines, setUserGuidelines] = useState<string[]>([]);
  const [userMemories, setUserMemories] = useState<Record<string, string>>({});

  // Fetch user guidelines and memories
  useEffect(() => {
    fetchGuidelines();
    fetchMemories();
  }, []);

  const fetchGuidelines = async () => {
    const res = await fetch('/api/ai/guidelines');
    if (res.ok) {
      const data = await res.json();
      setUserGuidelines(data.filter((g: any) => g.active).map((g: any) => g.rule));
    }
  };

  const fetchMemories = async () => {
    const res = await fetch('/api/ai/memory');
    if (res.ok) {
      const data = await res.json();
      const memoryMap: Record<string, string> = {};
      data.forEach((m: any) => {
        memoryMap[`${m.category}/${m.key}`] = m.value;
      });
      setUserMemories(memoryMap);
    }
  };

  // Build dynamic instructions based on user data
  const dynamicInstructions = `
## User Guidelines (MUST FOLLOW):
${userGuidelines.map(g => `- ${g}`).join('\n')}

## What You Remember About This User:
${Object.entries(userMemories).map(([k, v]) => `- ${k}: ${v}`).join('\n')}

## Current Context:
- Timer: ${timerStatus.running ? `Running for ${Math.round((timerStatus.elapsed_seconds || 0) / 60)} mins` : 'Not running'}
- Pending Revisions: ${pendingRevisions.length} items
- Active Goals: ${goals.length} goals
- Today's Tasks: ${schedule?.tasks?.length || 0} tasks
`;

  // Add dynamic instructions
  useCopilotAdditionalInstructions({
    instructions: dynamicInstructions
  });

  // Smart suggestions based on context
  useCopilotChatSuggestions({
    instructions: `Based on the current context, suggest 3 helpful actions the user might want to take. Consider:
- Whether they should start studying (if timer not running)
- Pending revisions that are due
- Upcoming deadlines
- Time gaps available for deep work`,
    minSuggestions: 2,
    maxSuggestions: 4
  });

  return (
    <CopilotSidebar
      className={className}
      instructions={`You are the AI assistant for Personal Engineering OS, helping a KU Computer Science student manage their studies effectively.

## Your Personality:
- Proactive and encouraging about study habits
- Knowledgeable about spaced repetition and deep work principles
- Always celebrates streaks and progress
- Gives specific, actionable advice

## Your Capabilities:
1. **Schedule Management**: Create, move, delete time blocks. Optimize schedules based on energy levels.
2. **Timer Control**: Start/stop study timers, track deep work sessions (90+ min).
3. **Revision Planning**: Schedule spaced repetition (1, 3, 7, 14, 30 day intervals).
4. **Goal Tracking**: Create goals, update progress, check completion.
5. **Lab Reports**: Track deadlines, update status, prioritize urgent reports.
6. **Backward Planning**: Plan backward from deadlines to distribute work.
7. **Memory**: Remember user preferences, habits, and constraints.

## Smart Scheduling Rules:
- Schedule difficult tasks during high-energy periods (8-10am, 4-6pm)
- Easy tasks during low-energy periods (after meals, late evening)
- Always add 15-min breaks after 90-min deep work sessions
- Never schedule outside user's wake/sleep times
- Prioritize overdue items > due today > exam prep > urgent labs > revisions

## Naming Conventions:
- Subjects: UPPERCASE + number (MATH101, PHYS102)
- Chapters: chapter + 2 digits (chapter01)
- Files: snake_case (lecture_notes.pdf)

## When User Says:
- "I have a test on [date]" → Use schedule_event_prep or backward_plan
- "I woke up at [time]" → Use update_schedule_preference to remember
- "Cancel today's schedule" → Use reschedule_all
- "I'm studying [subject]" → Start timer with subject
- "What should I do?" → Check schedule context, suggest based on gaps and priorities
`}
      labels={{
        title: "Study Assistant",
        initial: "Hi! How can I help with your studies today?",
        placeholder: "Ask about schedule, start timer, plan revision..."
      }}
      defaultOpen={false}
      clickOutsideToClose={true}
      shortcut="mod+k" // Cmd/Ctrl + K to open
    />
  );
}
```

### 5.2 Update Main Page

**File: `frontend/src/app/page.tsx`** (Updated)

```typescript
'use client'

import { useEffect, useState } from 'react'
import Dashboard from '@/components/Dashboard'
import StudyAssistant from '@/components/StudyAssistant'
import SystemBadge from '@/components/SystemBadge'
import StudyTimer from '@/components/StudyTimer'
import TodayDashboard from '@/components/TodayDashboard'
import TimelineView from '@/components/TimelineView'
import ScheduleInput from '@/components/ScheduleInput'
import LabReportTracker from '@/components/LabReportTracker'
import StudyAnalytics from '@/components/StudyAnalytics'
import GoalTracker from '@/components/GoalTracker'
import { useCopilotActions } from '@/hooks/useCopilotActions'

// ... rest of the component remains similar but replace:
// <AICommandCenter /> with <StudyAssistant />
```

---

## Phase 6: Implement Human-in-the-Loop for Sensitive Operations

### 6.1 Schedule Confirmation Component

**File: `frontend/src/components/ScheduleConfirmation.tsx`**

```typescript
'use client'

import { useHumanInTheLoop } from "@copilotkit/react-core";

export function useScheduleConfirmation() {
  useHumanInTheLoop({
    name: "reschedule_all",
    render: ({ args, status, respond }) => {
      if (status === "pending") return null;

      return (
        <div className="p-4 bg-yellow-500/20 rounded-lg border border-yellow-500/50">
          <h3 className="font-bold text-yellow-300 mb-2">Schedule Change Confirmation</h3>
          <p className="text-sm text-zinc-300 mb-3">
            {args.reason}
          </p>
          <p className="text-sm text-zinc-400 mb-4">
            This will reschedule all pending tasks. Are you sure?
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => respond?.({ approved: true })}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white text-sm"
            >
              Confirm
            </button>
            <button
              onClick={() => respond?.({ approved: false })}
              className="px-4 py-2 bg-zinc-600 hover:bg-zinc-700 rounded text-white text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      );
    }
  });

  useHumanInTheLoop({
    name: "backward_plan",
    render: ({ args, status, respond }) => {
      if (status === "pending") return null;

      return (
        <div className="p-4 bg-blue-500/20 rounded-lg border border-blue-500/50">
          <h3 className="font-bold text-blue-300 mb-2">Backward Planning</h3>
          <p className="text-sm text-zinc-300 mb-2">
            Creating study plan for: <strong>{args.title}</strong>
          </p>
          <ul className="text-sm text-zinc-400 mb-4 list-disc list-inside">
            <li>Subject: {args.subject_code}</li>
            <li>Deadline: {args.deadline_date}</li>
            <li>Hours needed: {args.hours_needed}</li>
          </ul>
          <div className="flex gap-2">
            <button
              onClick={() => respond?.({ approved: true })}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm"
            >
              Create Plan
            </button>
            <button
              onClick={() => respond?.({ approved: false })}
              className="px-4 py-2 bg-zinc-600 hover:bg-zinc-700 rounded text-white text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      );
    }
  });
}
```

---

## Phase 7: Task Reminder/Notification System

### 7.1 Notification Service

**File: `frontend/src/hooks/useTaskReminders.ts`**

```typescript
'use client'

import { useEffect, useCallback, useState } from 'react';
import { useCopilotChat } from "@copilotkit/react-core";

interface Reminder {
  id: string;
  type: 'task' | 'revision' | 'lab_report' | 'goal';
  title: string;
  message: string;
  dueAt: Date;
  priority: number;
}

export function useTaskReminders() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const { appendMessage } = useCopilotChat();

  // Check for due items every minute
  useEffect(() => {
    const checkReminders = async () => {
      const res = await fetch('/api/schedule/context');
      if (!res.ok) return;

      const context = await res.json();
      const now = new Date();
      const newReminders: Reminder[] = [];

      // Check tasks starting soon (15 min warning)
      context.schedule?.tasks?.forEach((task: any) => {
        if (task.scheduled_start) {
          const startTime = new Date(task.scheduled_start);
          const diffMins = (startTime.getTime() - now.getTime()) / 60000;

          if (diffMins > 0 && diffMins <= 15) {
            newReminders.push({
              id: `task-${task.id}`,
              type: 'task',
              title: task.title,
              message: `Task "${task.title}" starts in ${Math.round(diffMins)} minutes`,
              dueAt: startTime,
              priority: task.priority
            });
          }
        }
      });

      // Check revisions due today
      context.schedule?.revisions?.forEach((rev: any) => {
        if (rev.due_date === now.toISOString().split('T')[0]) {
          newReminders.push({
            id: `revision-${rev.id}`,
            type: 'revision',
            title: `${rev.subject_code} ${rev.chapter_title}`,
            message: `Revision due today: ${rev.chapter_title}`,
            dueAt: new Date(rev.due_date),
            priority: 8
          });
        }
      });

      // Check urgent lab reports (3 days or less)
      context.schedule?.lab_reports?.forEach((lab: any) => {
        const dueDate = new Date(lab.due_date);
        const daysUntilDue = (dueDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);

        if (daysUntilDue <= 3 && daysUntilDue > 0 && lab.status !== 'submitted') {
          newReminders.push({
            id: `lab-${lab.id}`,
            type: 'lab_report',
            title: lab.experiment_name,
            message: `Lab report "${lab.experiment_name}" due in ${Math.round(daysUntilDue)} days!`,
            dueAt: dueDate,
            priority: 9
          });
        }
      });

      setReminders(newReminders);

      // Show browser notification for high-priority items
      if (newReminders.length > 0 && Notification.permission === 'granted') {
        const urgent = newReminders.filter(r => r.priority >= 8);
        urgent.forEach(r => {
          new Notification('Study Reminder', {
            body: r.message,
            icon: '/icon.png'
          });
        });
      }

      // Proactively suggest via AI if there are pending items
      if (newReminders.length > 0) {
        const topReminder = newReminders.sort((a, b) => b.priority - a.priority)[0];

        // Only send proactive message once per session per reminder
        const shownKey = `reminder-shown-${topReminder.id}`;
        if (!sessionStorage.getItem(shownKey)) {
          sessionStorage.setItem(shownKey, 'true');

          // Trigger AI assistant with context
          appendMessage({
            role: 'user',
            content: `[System Reminder] ${topReminder.message}. What should I do?`
          });
        }
      }
    };

    // Initial check
    checkReminders();

    // Check every minute
    const interval = setInterval(checkReminders, 60000);

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }

    return () => clearInterval(interval);
  }, [appendMessage]);

  return { reminders };
}
```

### 7.2 Reminder Display Component

**File: `frontend/src/components/ReminderBar.tsx`**

```typescript
'use client'

import { useTaskReminders } from '@/hooks/useTaskReminders';

export default function ReminderBar() {
  const { reminders } = useTaskReminders();

  if (reminders.length === 0) return null;

  const urgentReminders = reminders.filter(r => r.priority >= 8);

  if (urgentReminders.length === 0) return null;

  return (
    <div className="bg-yellow-500/10 border-b border-yellow-500/30 px-6 py-2">
      <div className="max-w-7xl mx-auto flex items-center gap-4">
        <span className="text-yellow-400 text-xl">⚠️</span>
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-4">
            {urgentReminders.map(reminder => (
              <div
                key={reminder.id}
                className="flex items-center gap-2 px-3 py-1 bg-yellow-500/20 rounded-full whitespace-nowrap"
              >
                <span className="text-sm">
                  {reminder.type === 'task' && '📋'}
                  {reminder.type === 'revision' && '📚'}
                  {reminder.type === 'lab_report' && '🧪'}
                  {reminder.type === 'goal' && '🎯'}
                </span>
                <span className="text-sm text-yellow-100">{reminder.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 8: Testing and Migration Checklist

### 8.1 Testing Checklist

- [ ] CopilotKit provider loads correctly
- [ ] API route handles requests
- [ ] Backend endpoint responds
- [ ] Context sharing works (useCopilotReadable)
- [ ] All 52 tools callable
- [ ] Streaming responses work
- [ ] Human-in-the-loop confirmations display
- [ ] Reminders trigger correctly
- [ ] Browser notifications work
- [ ] Timer control via AI works
- [ ] Schedule modifications persist
- [ ] Memory/guidelines persist

### 8.2 Migration Sequence

1. **Week 1**: Frontend setup (Phase 1-2)
2. **Week 2**: Backend endpoint (Phase 3)
3. **Week 3**: Tool migration (Phase 4)
4. **Week 4**: Chat UI replacement (Phase 5)
5. **Week 5**: HITL + Reminders (Phase 6-7)
6. **Week 6**: Testing + Bug fixes (Phase 8)

### 8.3 Rollback Plan

Keep the old `AICommandCenter.tsx` and `/api/chat` endpoint functional during migration. Add feature flag:

```typescript
// env variable
NEXT_PUBLIC_USE_COPILOTKIT=true

// In page.tsx
{process.env.NEXT_PUBLIC_USE_COPILOTKIT === 'true'
  ? <StudyAssistant />
  : <AICommandCenter />
}
```

---

## Dependencies Update

### Frontend (package.json additions)
```json
{
  "dependencies": {
    "@copilotkit/react-core": "^1.0.0",
    "@copilotkit/react-ui": "^1.0.0",
    "@copilotkit/runtime": "^1.0.0"
  }
}
```

### Backend (requirements.txt additions)
```
copilotkit>=0.1.72
```

---

## Environment Variables

```env
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_COPILOTKIT=true

# Backend (.env)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/engineering_os
COPILOT_API_URL=http://localhost:4141
```

---

## Expected Benefits

1. **Streaming Responses**: Real-time AI responses instead of waiting for full completion
2. **Multi-Turn Tool Calling**: Complex multi-step operations with intermediate results
3. **Generative UI**: Dynamic UI components based on AI actions
4. **Human-in-the-Loop**: Confirmation dialogs for sensitive operations
5. **Smart Context**: Automatic state sharing with useCopilotReadable
6. **Proactive Reminders**: AI-powered notifications and suggestions
7. **Better UX**: Modern chat interface with suggestions and shortcuts
8. **Open Source**: No vendor lock-in, community support

---

## Conclusion

This integration plan provides a comprehensive pathway to migrate from copilot-api to CopilotKit while preserving all 52 existing AI tools and adding significant new capabilities. The phased approach allows for incremental testing and rollback if needed.

The key architectural change is moving from a simple REST chat endpoint to CopilotKit's streaming runtime with bidirectional state synchronization. This enables more sophisticated AI interactions including proactive reminders, human approval workflows, and real-time schedule optimization.
