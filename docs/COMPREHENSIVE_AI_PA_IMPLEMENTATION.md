# Comprehensive AI Personal Assistant Implementation Plan

## Executive Summary

This document outlines the complete implementation plan for integrating CopilotKit into the Personal Engineering OS, transforming it into a fully AI-controlled Personal Assistant (PA) system for KU Engineering students.

**Key Objectives:**
- Replace current copilot-api integration with CopilotKit + CoAgents
- Enable AI to have full control over timeline/schedule
- Implement proactive notifications and reminders
- Add adaptive learning pattern detection
- Build achievement and motivation systems
- Reduce student stress through intelligent workload management

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │  CopilotChat    │  │  CoAgent State  │  │  Frontend Tools         │  │
│  │  (Main UI)      │  │  Renderer       │  │  - showNotification     │  │
│  │                 │  │  - Schedule     │  │  - confirmSchedule      │  │
│  │  useCoAgent()   │  │  - Progress     │  │  - displayAchievement   │  │
│  │  useReadable()  │  │  - Goals        │  │  - focusModeToggle      │  │
│  └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘  │
│           │                    │                       │                 │
│           └────────────────────┴───────────────────────┘                 │
│                                │                                         │
│                    ┌───────────▼───────────┐                            │
│                    │   CopilotRuntime      │                            │
│                    │   (WebSocket/HTTP)    │                            │
│                    └───────────┬───────────┘                            │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Remote Endpoint       │
                    │   /copilotkit           │
                    └────────────┬────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────┐
│                         BACKEND (FastAPI)                                │
│                                │                                         │
│  ┌─────────────────────────────▼─────────────────────────────────────┐  │
│  │                    LangGraph Agent Hub                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │  │
│  │  │ Scheduler   │  │ Study       │  │ Progress    │  │ Wellbeing │ │  │
│  │  │ Agent       │  │ Planner     │  │ Tracker     │  │ Monitor   │ │  │
│  │  │             │  │ Agent       │  │ Agent       │  │ Agent     │ │  │
│  │  │ - Timeline  │  │ - Adaptive  │  │ - Goals     │  │ - Stress  │ │  │
│  │  │ - Blocks    │  │ - Patterns  │  │ - Achieve   │  │ - Breaks  │ │  │
│  │  │ - Optimize  │  │ - Revisions │  │ - Stats     │  │ - Load    │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                │                                         │
│  ┌─────────────────────────────▼─────────────────────────────────────┐  │
│  │                      Tool Registry (52+ tools)                     │  │
│  │  Schedule Tools │ Timer Tools │ Goal Tools │ Memory │ Notifications│  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                │                                         │
│  ┌─────────────────────────────▼─────────────────────────────────────┐  │
│  │                      PostgreSQL Database                           │  │
│  │  tasks │ schedules │ study_sessions │ goals │ achievements │ etc   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Gap Analysis: Current vs Required Features

### HIGH Priority Gaps (Must Implement)

| Feature | Current State | Required Implementation |
|---------|---------------|------------------------|
| **Smart Notifications** | None | Push notifications, in-app alerts, proactive reminders |
| **Learning Patterns** | None | Track study effectiveness, adapt recommendations |
| **Achievement System** | Table exists, no logic | Gamification, badges, streaks, celebrations |
| **Resource Search** | None | Search notes, materials, past assignments |
| **Stress Detection** | None | Workload monitoring, break enforcement |

### MEDIUM Priority Gaps (Enhancement)

| Feature | Current State | Required Implementation |
|---------|---------------|------------------------|
| **Break Suggestions** | Basic timer | Intelligent break timing based on focus duration |
| **Energy Optimization** | Static curves | Learn personal energy patterns |
| **Task Dependencies** | None | Chain tasks, prerequisites |

### Already Implemented (Leverage)

- Task CRUD operations (52 tools)
- Schedule management with KU timetable
- Study timer with deep work detection
- Goal tracking with progress
- Spaced repetition scheduling
- AI memory system

---

## Feature Implementation Details

### 1. Smart Task Management

**Objective:** AI-controlled task creation, organization, and prioritization

```python
# Backend: New LangGraph Node for Task Intelligence
class TaskIntelligenceNode:
    """AI node that analyzes and optimizes tasks"""

    async def analyze_task(self, state: AgentState) -> AgentState:
        # Extract task details from user input
        task_info = state["messages"][-1].content

        # AI determines:
        # - Priority based on deadline proximity + difficulty
        # - Estimated duration based on similar past tasks
        # - Best time slot based on energy curves
        # - Prerequisites and dependencies

        analysis = await self.llm.analyze(task_info, context={
            "upcoming_deadlines": state["deadlines"],
            "current_workload": state["workload"],
            "energy_profile": state["user_energy_profile"]
        })

        return {
            **state,
            "task_analysis": analysis,
            "suggested_schedule": self.find_optimal_slot(analysis)
        }
```

**Frontend Integration:**
```typescript
// useCopilotReadable for task context
useCopilotReadable({
  description: "Current tasks and their status",
  value: JSON.stringify({
    tasks: tasks,
    overdue: tasks.filter(t => new Date(t.deadline) < new Date()),
    todayDue: tasks.filter(t => isToday(t.deadline)),
    priorityOrder: tasks.sort((a, b) => b.priority - a.priority)
  })
});

// Frontend tool for task confirmation
useCopilotAction({
  name: "createTaskWithSchedule",
  description: "Create a task and schedule it optimally",
  parameters: [
    { name: "title", type: "string", required: true },
    { name: "deadline", type: "string", required: true },
    { name: "estimatedMinutes", type: "number" },
    { name: "subject", type: "string" }
  ],
  handler: async ({ title, deadline, estimatedMinutes, subject }) => {
    // Show confirmation UI with suggested time slot
    const confirmed = await showTaskConfirmation({
      title,
      deadline,
      suggestedSlot: await api.getSuggestedSlot(estimatedMinutes)
    });

    if (confirmed) {
      await api.createTask({ title, deadline, estimatedMinutes, subject });
      toast.success(`Task "${title}" created and scheduled!`);
    }
  }
});
```

---

### 2. Adaptive Study Planner

**Objective:** Learn student patterns and adapt recommendations

**Database Schema Addition:**
```sql
-- Learning pattern tracking
CREATE TABLE learning_patterns (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(10),
    avg_comprehension_time_mins INTEGER,
    best_study_time VARCHAR(20), -- 'morning', 'afternoon', 'evening', 'night'
    retention_rate DECIMAL(3,2), -- 0.00 to 1.00
    preferred_session_length INTEGER,
    break_frequency_mins INTEGER,
    effectiveness_score DECIMAL(3,2),
    samples_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Study session effectiveness tracking
CREATE TABLE session_effectiveness (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES study_sessions(id),
    subject_code VARCHAR(10),
    time_of_day VARCHAR(20),
    duration_mins INTEGER,
    focus_score DECIMAL(3,2), -- Self-reported or inferred
    material_covered TEXT,
    retention_test_score DECIMAL(3,2), -- Optional quiz result
    created_at TIMESTAMP DEFAULT NOW()
);

-- Adaptive recommendations
CREATE TABLE study_recommendations (
    id SERIAL PRIMARY KEY,
    recommendation_type VARCHAR(50), -- 'schedule', 'duration', 'subject_order', 'break'
    recommendation_text TEXT,
    confidence_score DECIMAL(3,2),
    was_accepted BOOLEAN,
    outcome_score DECIMAL(3,2), -- Did following it help?
    created_at TIMESTAMP DEFAULT NOW()
);
```

**LangGraph Agent: Study Planner**
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint import MemorySaver

class StudyPlannerState(TypedDict):
    user_id: int
    subject: str
    available_time: int
    energy_level: str
    learning_patterns: dict
    recommendations: list
    final_plan: dict

def create_study_planner_agent():
    workflow = StateGraph(StudyPlannerState)

    # Node 1: Analyze patterns
    async def analyze_patterns(state: StudyPlannerState):
        patterns = await db.get_learning_patterns(state["user_id"], state["subject"])
        return {"learning_patterns": patterns}

    # Node 2: Generate recommendations
    async def generate_recommendations(state: StudyPlannerState):
        patterns = state["learning_patterns"]

        recommendations = []

        # Time-based recommendation
        current_hour = datetime.now().hour
        if patterns["best_study_time"] == "morning" and current_hour > 12:
            recommendations.append({
                "type": "timing",
                "text": f"Your best study time for {state['subject']} is morning. Consider scheduling this for tomorrow AM.",
                "confidence": patterns["effectiveness_score"]
            })

        # Duration recommendation
        if state["available_time"] > patterns["preferred_session_length"] * 1.5:
            recommendations.append({
                "type": "duration",
                "text": f"Break this into {state['available_time'] // patterns['preferred_session_length']} sessions of {patterns['preferred_session_length']} mins each.",
                "confidence": 0.85
            })

        # Break recommendation
        recommendations.append({
            "type": "break",
            "text": f"Take a 10-min break every {patterns['break_frequency_mins']} minutes.",
            "confidence": 0.9
        })

        return {"recommendations": recommendations}

    # Node 3: Create optimized plan
    async def create_plan(state: StudyPlannerState):
        plan = {
            "sessions": [],
            "breaks": [],
            "total_study_time": 0,
            "expected_retention": 0
        }

        # Build session plan based on patterns and recommendations
        remaining_time = state["available_time"]
        session_length = state["learning_patterns"]["preferred_session_length"]

        while remaining_time > 0:
            session_mins = min(session_length, remaining_time)
            plan["sessions"].append({
                "duration": session_mins,
                "subject": state["subject"],
                "focus_tip": get_focus_tip(state["energy_level"])
            })
            remaining_time -= session_mins

            if remaining_time > 15:  # Add break if more study time
                plan["breaks"].append({"duration": 10, "type": "short"})
                remaining_time -= 10

        plan["total_study_time"] = state["available_time"] - len(plan["breaks"]) * 10
        plan["expected_retention"] = state["learning_patterns"]["retention_rate"]

        return {"final_plan": plan}

    workflow.add_node("analyze", analyze_patterns)
    workflow.add_node("recommend", generate_recommendations)
    workflow.add_node("plan", create_plan)

    workflow.add_edge("analyze", "recommend")
    workflow.add_edge("recommend", "plan")
    workflow.add_edge("plan", END)

    workflow.set_entry_point("analyze")

    return workflow.compile(checkpointer=MemorySaver())
```

---

### 3. AI Progress Tracking & Achievements

**Objective:** Track accomplishments, visualize growth, motivate students

**Database Schema:**
```sql
-- Achievement definitions
CREATE TABLE achievement_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10), -- emoji
    category VARCHAR(50), -- 'streak', 'study', 'goal', 'revision', 'special'
    threshold_value INTEGER, -- e.g., 7 for "7-day streak"
    points INTEGER DEFAULT 10,
    rarity VARCHAR(20) DEFAULT 'common' -- 'common', 'rare', 'epic', 'legendary'
);

-- User achievements
CREATE TABLE user_achievements (
    id SERIAL PRIMARY KEY,
    achievement_id INTEGER REFERENCES achievement_definitions(id),
    earned_at TIMESTAMP DEFAULT NOW(),
    progress_value INTEGER, -- Current progress toward achievement
    is_complete BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE
);

-- Progress snapshots for visualization
CREATE TABLE progress_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    total_study_mins INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    revisions_completed INTEGER DEFAULT 0,
    goals_progress JSONB, -- {"goal_id": progress_value, ...}
    streak_count INTEGER DEFAULT 0,
    achievement_points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default achievements
INSERT INTO achievement_definitions (code, name, description, icon, category, threshold_value, points, rarity) VALUES
('streak_3', 'Getting Started', 'Maintain a 3-day study streak', '🔥', 'streak', 3, 10, 'common'),
('streak_7', 'Week Warrior', 'Maintain a 7-day study streak', '⚡', 'streak', 7, 25, 'common'),
('streak_30', 'Month Master', 'Maintain a 30-day study streak', '🏆', 'streak', 30, 100, 'rare'),
('streak_100', 'Centurion', 'Maintain a 100-day study streak', '👑', 'streak', 100, 500, 'legendary'),
('deep_work_1', 'Deep Diver', 'Complete your first 90+ min deep work session', '🧠', 'study', 1, 15, 'common'),
('deep_work_10', 'Focus Master', 'Complete 10 deep work sessions', '🎯', 'study', 10, 50, 'rare'),
('tasks_10', 'Task Tackler', 'Complete 10 tasks', '✅', 'goal', 10, 10, 'common'),
('tasks_100', 'Productivity Pro', 'Complete 100 tasks', '🚀', 'goal', 100, 100, 'rare'),
('revision_master', 'Memory Champion', 'Complete all revisions for a chapter', '📚', 'revision', 5, 30, 'rare'),
('early_bird', 'Early Bird', 'Start studying before 7 AM', '🌅', 'special', 1, 20, 'common'),
('night_owl', 'Night Owl', 'Study past midnight productively', '🦉', 'special', 1, 20, 'common'),
('perfectionist', 'Perfectionist', 'Complete all tasks for a week', '💎', 'special', 7, 75, 'epic');
```

**Achievement Checker Tool:**
```python
async def check_achievements() -> list[dict]:
    """Check and award any newly earned achievements"""

    # Get current stats
    stats = await db.get_user_stats()
    achievements_earned = []

    # Check streak achievements
    streak_achievements = [
        ("streak_3", 3), ("streak_7", 7),
        ("streak_30", 30), ("streak_100", 100)
    ]
    for code, threshold in streak_achievements:
        if stats["current_streak"] >= threshold:
            if await award_achievement_if_new(code):
                achievements_earned.append(code)

    # Check deep work achievements
    deep_work_count = await db.count_deep_work_sessions()
    if deep_work_count >= 1:
        if await award_achievement_if_new("deep_work_1"):
            achievements_earned.append("deep_work_1")
    if deep_work_count >= 10:
        if await award_achievement_if_new("deep_work_10"):
            achievements_earned.append("deep_work_10")

    # Check task achievements
    tasks_completed = await db.count_completed_tasks()
    if tasks_completed >= 10:
        if await award_achievement_if_new("tasks_10"):
            achievements_earned.append("tasks_10")
    if tasks_completed >= 100:
        if await award_achievement_if_new("tasks_100"):
            achievements_earned.append("tasks_100")

    # Check time-based achievements
    current_hour = datetime.now().hour
    if current_hour < 7 and await db.has_active_session():
        if await award_achievement_if_new("early_bird"):
            achievements_earned.append("early_bird")

    return achievements_earned
```

**Frontend Achievement Display:**
```typescript
// Achievement notification component
function AchievementPopup({ achievement }: { achievement: Achievement }) {
  return (
    <motion.div
      initial={{ scale: 0, y: 100 }}
      animate={{ scale: 1, y: 0 }}
      className="fixed bottom-4 right-4 glass rounded-2xl p-6 z-50"
    >
      <div className="flex items-center gap-4">
        <div className="text-5xl animate-bounce">{achievement.icon}</div>
        <div>
          <p className="text-sm text-primary font-medium">Achievement Unlocked!</p>
          <h3 className="text-xl font-bold text-white">{achievement.name}</h3>
          <p className="text-sm text-zinc-400">{achievement.description}</p>
          <p className="text-sm text-yellow-400">+{achievement.points} points</p>
        </div>
      </div>
    </motion.div>
  );
}

// Progress visualization component
function ProgressVisualization() {
  const [snapshots, setSnapshots] = useState<ProgressSnapshot[]>([]);

  // Share with AI
  useCopilotReadable({
    description: "User's progress history for motivation",
    value: JSON.stringify({
      weeklyGrowth: calculateGrowth(snapshots, 7),
      monthlyGrowth: calculateGrowth(snapshots, 30),
      totalAchievements: snapshots[0]?.achievement_points || 0,
      streakRecord: Math.max(...snapshots.map(s => s.streak_count))
    })
  });

  return (
    <div className="glass rounded-2xl p-6">
      <h3 className="text-lg font-bold text-white mb-4">Your Growth</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={snapshots}>
          <Area
            type="monotone"
            dataKey="total_study_mins"
            stroke="#6366f1"
            fill="url(#gradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

---

### 4. Proactive Notification System

**Objective:** AI-initiated reminders without user prompting

**Database Schema:**
```sql
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'reminder', 'achievement', 'suggestion', 'warning'
    title VARCHAR(200) NOT NULL,
    message TEXT,
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    scheduled_for TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    dismissed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    frequency_limit INTEGER, -- Max per day
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Notification Generator Agent:**
```python
class NotificationAgent:
    """Proactively generates helpful notifications"""

    async def run_check_cycle(self):
        """Run every 15 minutes"""
        notifications = []

        # Check upcoming deadlines
        deadlines = await db.get_upcoming_deadlines(hours=24)
        for deadline in deadlines:
            hours_left = (deadline["due_date"] - datetime.now()).total_seconds() / 3600
            if hours_left < 4 and not deadline["notified_4h"]:
                notifications.append({
                    "type": "reminder",
                    "priority": "high",
                    "title": f"⏰ {deadline['title']} due in {int(hours_left)} hours",
                    "message": f"Don't forget to complete this before {deadline['due_date'].strftime('%I:%M %p')}",
                    "action_label": "View Task",
                    "action_url": f"/tasks/{deadline['id']}"
                })

        # Check if user should take a break
        active_session = await db.get_active_timer()
        if active_session:
            duration = (datetime.now() - active_session["started_at"]).total_seconds() / 60
            if duration > 90 and not active_session["break_reminded"]:
                notifications.append({
                    "type": "suggestion",
                    "priority": "normal",
                    "title": "🧘 Time for a break!",
                    "message": f"You've been studying for {int(duration)} minutes. A short break will help you retain more.",
                    "action_label": "Take 10-min Break",
                    "action_url": "/timer/break"
                })

        # Check revision due
        revisions = await db.get_due_revisions()
        if revisions:
            notifications.append({
                "type": "reminder",
                "priority": "normal",
                "title": f"📚 {len(revisions)} revision(s) due today",
                "message": "Keep your memory fresh with spaced repetition!",
                "action_label": "Start Revision",
                "action_url": "/revisions"
            })

        # Motivational notification (once per day)
        if await self.should_send_motivation():
            stats = await db.get_user_stats()
            notifications.append({
                "type": "achievement",
                "priority": "low",
                "title": f"🔥 {stats['streak']} day streak!",
                "message": f"You've studied {stats['weekly_hours']}h this week. Keep it up!",
            })

        # Check for overwork
        today_mins = await db.get_today_study_minutes()
        if today_mins > 480:  # 8 hours
            notifications.append({
                "type": "warning",
                "priority": "high",
                "title": "⚠️ Long study day",
                "message": "You've studied 8+ hours today. Consider wrapping up to avoid burnout.",
                "action_label": "View Wellness Tips",
                "action_url": "/wellness"
            })

        # Send notifications
        for notif in notifications:
            await self.send_notification(notif)

    async def send_notification(self, notification: dict):
        # Check user preferences
        prefs = await db.get_notification_preferences(notification["type"])
        if not prefs["enabled"]:
            return

        # Check quiet hours
        now = datetime.now().time()
        if prefs["quiet_hours_start"] and prefs["quiet_hours_end"]:
            if prefs["quiet_hours_start"] <= now <= prefs["quiet_hours_end"]:
                notification["scheduled_for"] = self.next_available_time(prefs)
                await db.schedule_notification(notification)
                return

        # Send immediately
        await db.create_notification(notification)
        await self.push_to_frontend(notification)
```

**Frontend Notification Handler:**
```typescript
// Notification context provider
export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);

  // WebSocket connection for real-time notifications
  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/notifications`);

    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications(prev => [notification, ...prev]);

      // Show toast for high priority
      if (notification.priority === 'high' || notification.priority === 'urgent') {
        showNotificationToast(notification);
      }

      // Browser notification if permitted
      if (Notification.permission === 'granted') {
        new Notification(notification.title, {
          body: notification.message,
          icon: '/icon.png'
        });
      }
    };

    return () => ws.close();
  }, []);

  // AI can trigger frontend notifications
  useCopilotAction({
    name: "showNotification",
    description: "Display a notification to the user",
    parameters: [
      { name: "title", type: "string", required: true },
      { name: "message", type: "string", required: true },
      { name: "type", type: "string", enum: ["info", "success", "warning", "error"] }
    ],
    handler: async ({ title, message, type }) => {
      toast[type || 'info'](message, { title });
    }
  });

  return (
    <NotificationContext.Provider value={{ notifications, setNotifications }}>
      {children}
      <NotificationCenter />
    </NotificationContext.Provider>
  );
}
```

---

### 5. Stress Reduction & Wellbeing

**Objective:** Monitor workload, enforce breaks, prevent burnout

**Database Schema:**
```sql
CREATE TABLE wellbeing_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    study_hours DECIMAL(4,2),
    break_count INTEGER,
    break_total_mins INTEGER,
    deep_work_sessions INTEGER,
    task_completion_rate DECIMAL(3,2),
    overdue_tasks INTEGER,
    stress_indicators JSONB, -- {"long_sessions": 2, "skipped_breaks": 1, ...}
    wellbeing_score DECIMAL(3,2), -- 0.00 to 1.00
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE break_sessions (
    id SERIAL PRIMARY KEY,
    break_type VARCHAR(50), -- 'short', 'pomodoro', 'meal', 'exercise', 'meditation'
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    suggested_duration_mins INTEGER,
    actual_duration_mins INTEGER,
    was_completed BOOLEAN DEFAULT FALSE
);
```

**Wellbeing Monitor Agent:**
```python
class WellbeingMonitorAgent:
    """Monitors student wellbeing and suggests interventions"""

    STRESS_THRESHOLDS = {
        "daily_study_hours": 10,      # Max recommended
        "session_without_break": 120,  # Minutes
        "consecutive_deep_work": 3,    # Sessions
        "overdue_tasks": 5,            # Count
        "skipped_breaks": 2            # Count
    }

    async def calculate_wellbeing_score(self) -> dict:
        """Calculate daily wellbeing score (0-1)"""

        today_stats = await db.get_today_stats()

        # Factors that reduce wellbeing score
        deductions = 0
        indicators = {}

        # Long study hours
        if today_stats["study_hours"] > self.STRESS_THRESHOLDS["daily_study_hours"]:
            deductions += 0.2
            indicators["excessive_study"] = today_stats["study_hours"]

        # Sessions without breaks
        long_sessions = today_stats["sessions_over_90_mins_no_break"]
        if long_sessions > 0:
            deductions += 0.1 * long_sessions
            indicators["long_sessions"] = long_sessions

        # Skipped breaks
        if today_stats["skipped_breaks"] > 0:
            deductions += 0.1 * today_stats["skipped_breaks"]
            indicators["skipped_breaks"] = today_stats["skipped_breaks"]

        # Overdue tasks (causes anxiety)
        overdue = await db.count_overdue_tasks()
        if overdue > 0:
            deductions += 0.05 * min(overdue, 5)  # Cap at 5
            indicators["overdue_tasks"] = overdue

        # Positive factors
        bonuses = 0

        # Took breaks
        if today_stats["break_count"] >= 3:
            bonuses += 0.1

        # Completed tasks
        if today_stats["tasks_completed"] > 0:
            bonuses += 0.05 * min(today_stats["tasks_completed"], 5)

        # Calculate final score
        base_score = 0.7
        final_score = max(0, min(1, base_score - deductions + bonuses))

        # Generate recommendations
        recommendations = self.generate_recommendations(final_score, indicators)

        return {
            "score": final_score,
            "indicators": indicators,
            "recommendations": recommendations
        }

    def generate_recommendations(self, score: float, indicators: dict) -> list:
        """Generate wellbeing recommendations"""
        recommendations = []

        if score < 0.4:
            recommendations.append({
                "priority": "urgent",
                "action": "Take a 30-minute break now",
                "reason": "Your stress indicators are high"
            })

        if "excessive_study" in indicators:
            recommendations.append({
                "priority": "high",
                "action": "Consider stopping for today",
                "reason": f"You've studied {indicators['excessive_study']:.1f} hours"
            })

        if "overdue_tasks" in indicators:
            recommendations.append({
                "priority": "medium",
                "action": "Focus on overdue tasks first",
                "reason": f"You have {indicators['overdue_tasks']} overdue tasks causing stress"
            })

        if "skipped_breaks" in indicators:
            recommendations.append({
                "priority": "medium",
                "action": "Don't skip your next break",
                "reason": "Regular breaks improve retention and reduce fatigue"
            })

        return recommendations
```

**Pomodoro Integration:**
```typescript
// Enhanced timer with Pomodoro mode
function StudyTimerWithWellbeing() {
  const [mode, setMode] = useState<'normal' | 'pomodoro'>('normal');
  const [pomodoroCount, setPomodoroCount] = useState(0);
  const [wellbeingScore, setWellbeingScore] = useState(1);

  // Share wellbeing status with AI
  useCopilotReadable({
    description: "User wellbeing and break status",
    value: JSON.stringify({
      currentMode: mode,
      pomodorosCompleted: pomodoroCount,
      wellbeingScore,
      needsBreak: wellbeingScore < 0.5
    })
  });

  // AI can suggest break
  useCopilotAction({
    name: "suggestBreak",
    description: "Suggest user takes a break for wellbeing",
    parameters: [
      { name: "duration", type: "number", description: "Break duration in minutes" },
      { name: "reason", type: "string" }
    ],
    handler: async ({ duration, reason }) => {
      showBreakSuggestion({
        duration,
        reason,
        onAccept: () => startBreakTimer(duration),
        onDecline: () => recordSkippedBreak()
      });
    }
  });

  // Pomodoro cycle: 25 work, 5 break, repeat 4x, then 15 break
  const startPomodoro = async () => {
    setMode('pomodoro');
    await api.startTimer({ type: 'pomodoro', duration: 25 });

    // Auto-trigger break after 25 mins
    setTimeout(() => {
      const breakDuration = pomodoroCount % 4 === 3 ? 15 : 5;
      showBreakModal({
        duration: breakDuration,
        type: pomodoroCount % 4 === 3 ? 'long' : 'short'
      });
    }, 25 * 60 * 1000);
  };

  return (
    <div className="glass rounded-xl p-4">
      {/* Wellbeing indicator */}
      <div className="flex items-center gap-2 mb-4">
        <div
          className={`w-3 h-3 rounded-full ${
            wellbeingScore > 0.7 ? 'bg-green-500' :
            wellbeingScore > 0.4 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
        />
        <span className="text-sm text-zinc-400">
          Wellbeing: {Math.round(wellbeingScore * 100)}%
        </span>
      </div>

      {/* Timer controls */}
      {/* ... existing timer UI ... */}

      {/* Pomodoro toggle */}
      <button
        onClick={() => setMode(mode === 'pomodoro' ? 'normal' : 'pomodoro')}
        className="mt-2 text-sm text-primary"
      >
        {mode === 'pomodoro' ? '🍅 Pomodoro Active' : 'Enable Pomodoro'}
      </button>
    </div>
  );
}
```

---

## CopilotKit Integration

### Backend Setup (FastAPI + LangGraph)

**File: `backend/copilot.py`**
```python
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver

# Define the main agent state
class PAState(TypedDict):
    messages: list
    schedule_context: dict
    user_profile: dict
    current_task: Optional[dict]
    wellbeing_score: float
    pending_notifications: list

# Create the main PA agent graph
def create_pa_agent():
    workflow = StateGraph(PAState)

    # Add nodes for different capabilities
    workflow.add_node("understand_intent", understand_user_intent)
    workflow.add_node("gather_context", gather_schedule_context)
    workflow.add_node("plan_action", plan_action_with_tools)
    workflow.add_node("execute_action", execute_with_confirmation)
    workflow.add_node("check_wellbeing", check_user_wellbeing)
    workflow.add_node("generate_response", generate_helpful_response)

    # Define edges
    workflow.add_edge("understand_intent", "gather_context")
    workflow.add_conditional_edges(
        "gather_context",
        route_based_on_intent,
        {
            "schedule_change": "plan_action",
            "information": "generate_response",
            "wellbeing_check": "check_wellbeing"
        }
    )
    workflow.add_edge("plan_action", "execute_action")
    workflow.add_edge("execute_action", "generate_response")
    workflow.add_edge("check_wellbeing", "generate_response")

    workflow.set_entry_point("understand_intent")

    return workflow.compile(checkpointer=MemorySaver())

# Initialize SDK
sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="personal_assistant",
            description="AI Personal Assistant for study management",
            agent=create_pa_agent(),
        ),
        LangGraphAgent(
            name="scheduler",
            description="Specialized agent for schedule optimization",
            agent=create_scheduler_agent(),
        ),
        LangGraphAgent(
            name="study_planner",
            description="Adaptive study planning agent",
            agent=create_study_planner_agent(),
        ),
        LangGraphAgent(
            name="wellbeing_monitor",
            description="Student wellbeing monitoring agent",
            agent=create_wellbeing_agent(),
        )
    ]
)

# Add endpoint to FastAPI
def setup_copilotkit(app: FastAPI):
    add_fastapi_endpoint(app, sdk, "/copilotkit")
```

**File: `backend/main.py` (additions)**
```python
from copilot import setup_copilotkit

# After creating FastAPI app
app = FastAPI(title="Engineering OS API")

# Setup CopilotKit endpoint
setup_copilotkit(app)

# Keep existing endpoints for backward compatibility
# ...existing code...
```

### Frontend Setup

**File: `frontend/src/app/layout.tsx`**
```typescript
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotPopup } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          agent="personal_assistant"
        >
          {children}
          <CopilotPopup
            labels={{
              title: "Study Assistant",
              initial: "Hi! I'm your personal study assistant. How can I help you today?"
            }}
          />
        </CopilotKit>
      </body>
    </html>
  );
}
```

**File: `frontend/src/components/AIAssistant.tsx` (replaces AICommandCenter)**
```typescript
'use client';

import { useCoAgent, useCoAgentStateRender } from "@copilotkit/react-core";
import { useCopilotReadable, useCopilotAction } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";

interface AgentState {
  schedule_context: {
    today_tasks: Task[];
    upcoming_deadlines: Deadline[];
    current_gaps: Gap[];
  };
  user_profile: {
    energy_level: string;
    preferred_study_time: string;
    current_streak: number;
  };
  wellbeing_score: number;
  pending_notifications: Notification[];
}

export default function AIAssistant() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [schedule, setSchedule] = useState<ScheduleBlock[]>([]);

  // Connect to the PA agent with state sync
  const { state, setState, run } = useCoAgent<AgentState>({
    name: "personal_assistant",
    initialState: {
      schedule_context: { today_tasks: [], upcoming_deadlines: [], current_gaps: [] },
      user_profile: { energy_level: 'medium', preferred_study_time: 'morning', current_streak: 0 },
      wellbeing_score: 1.0,
      pending_notifications: []
    }
  });

  // Share current app state with AI
  useCopilotReadable({
    description: "Current tasks and schedule visible to user",
    value: JSON.stringify({
      tasks: tasks,
      schedule: schedule,
      currentTime: new Date().toISOString(),
      activeTab: 'today'
    })
  });

  // Render agent state changes in UI
  useCoAgentStateRender({
    name: "personal_assistant",
    render: ({ state }) => {
      // Update UI when agent modifies state
      if (state.schedule_context.today_tasks !== tasks) {
        setTasks(state.schedule_context.today_tasks);
      }

      // Show wellbeing warning if needed
      if (state.wellbeing_score < 0.4) {
        return (
          <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 mb-4">
            <p className="text-red-400 font-medium">⚠️ High stress detected</p>
            <p className="text-sm text-zinc-400">Consider taking a break</p>
          </div>
        );
      }

      return null;
    }
  });

  // Define frontend actions AI can trigger
  useCopilotAction({
    name: "navigateToTab",
    description: "Navigate to a specific tab in the app",
    parameters: [
      { name: "tab", type: "string", enum: ["today", "timeline", "tasks", "labs", "analytics", "goals"] }
    ],
    handler: async ({ tab }) => {
      window.dispatchEvent(new CustomEvent('navigate', { detail: { tab } }));
    }
  });

  useCopilotAction({
    name: "highlightTask",
    description: "Highlight a specific task for user attention",
    parameters: [
      { name: "taskId", type: "number" }
    ],
    handler: async ({ taskId }) => {
      document.getElementById(`task-${taskId}`)?.scrollIntoView({ behavior: 'smooth' });
      document.getElementById(`task-${taskId}`)?.classList.add('ring-2', 'ring-primary');
    }
  });

  useCopilotAction({
    name: "showScheduleConfirmation",
    description: "Show user a schedule change for approval",
    parameters: [
      { name: "changes", type: "object[]", description: "Array of schedule changes" },
      { name: "reason", type: "string" }
    ],
    handler: async ({ changes, reason }) => {
      return new Promise((resolve) => {
        showConfirmationModal({
          title: "Schedule Update",
          message: reason,
          changes: changes,
          onConfirm: () => resolve({ approved: true }),
          onCancel: () => resolve({ approved: false })
        });
      });
    }
  });

  return (
    <div className="glass rounded-2xl p-6 h-full flex flex-col">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
          <span className="text-lg">🤖</span>
        </div>
        <div>
          <h3 className="font-semibold text-white">Study Assistant</h3>
          <p className="text-xs text-zinc-400">
            Wellbeing: {Math.round(state.wellbeing_score * 100)}%
          </p>
        </div>
      </div>

      <CopilotChat
        className="flex-1"
        labels={{
          placeholder: "Ask me anything about your schedule..."
        }}
        instructions={`
          You are a helpful study assistant for a KU Engineering student.
          You have full control over their schedule and can:
          - Create, move, and delete time blocks
          - Suggest optimal study times
          - Track their progress and achievements
          - Monitor their wellbeing
          - Send reminders and notifications

          Always be encouraging but honest. If they're overworking, tell them.
          Use their learning patterns to give personalized advice.
        `}
      />
    </div>
  );
}
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Foundation)
**Duration: Foundation sprint**

Tasks:
1. Install CopilotKit packages
   ```bash
   # Frontend
   cd frontend && npm install @copilotkit/react-core @copilotkit/react-ui

   # Backend
   cd backend && pip install copilotkit langgraph langchain-anthropic
   ```

2. Create `backend/copilot.py` with basic agent setup

3. Update `frontend/src/app/layout.tsx` with CopilotKit provider

4. Create basic agent state types and initial graph

5. Test basic chat functionality

**Deliverables:**
- Working CopilotKit integration
- Basic chat with context awareness
- Agent can read current schedule

---

### Phase 2: Smart Task Management
**Duration: Feature sprint**

Tasks:
1. Implement task intelligence node in LangGraph
2. Add `useCopilotReadable` for task context
3. Create `createTaskWithSchedule` action
4. Build confirmation UI for AI-suggested tasks
5. Add task dependency tracking

**Deliverables:**
- AI can create tasks with optimal scheduling
- User confirms AI task suggestions
- Task priorities auto-calculated

---

### Phase 3: Adaptive Study Planner
**Duration: Feature sprint**

Tasks:
1. Create database tables for learning patterns
2. Implement pattern tracking on session end
3. Build Study Planner agent
4. Add pattern-based recommendations
5. Create UI for showing personalized suggestions

**Deliverables:**
- System learns user study patterns
- Recommendations adapt over time
- Personalized session length suggestions

---

### Phase 4: Progress Tracking & Achievements
**Duration: Feature sprint**

Tasks:
1. Create achievement tables and definitions
2. Implement achievement checking logic
3. Build achievement popup component
4. Create progress visualization charts
5. Add achievement sharing with AI context

**Deliverables:**
- Working achievement system
- Progress visualization
- AI celebrates achievements with user

---

### Phase 5: Proactive Notifications
**Duration: Feature sprint**

Tasks:
1. Create notification tables
2. Build notification generator agent
3. Implement WebSocket for real-time notifications
4. Create notification preferences UI
5. Add browser notification support

**Deliverables:**
- AI sends proactive reminders
- User can configure notification preferences
- Real-time notification delivery

---

### Phase 6: Wellbeing & Stress Reduction
**Duration: Feature sprint**

Tasks:
1. Create wellbeing metrics tables
2. Build wellbeing monitor agent
3. Implement Pomodoro mode
4. Add break enforcement UI
5. Create wellbeing dashboard

**Deliverables:**
- Wellbeing score tracking
- Pomodoro timer integration
- AI enforces healthy breaks

---

### Phase 7: Full Integration & Polish
**Duration: Integration sprint**

Tasks:
1. Connect all agents in main PA graph
2. Optimize state synchronization
3. Add error handling and fallbacks
4. Performance optimization
5. UI polish and animations

**Deliverables:**
- Seamless multi-agent coordination
- Smooth user experience
- Production-ready system

---

### Phase 8: Testing & Documentation
**Duration: Final sprint**

Tasks:
1. Write unit tests for agents
2. Integration testing
3. User acceptance testing
4. Update CLAUDE.md documentation
5. Create user guide

**Deliverables:**
- Comprehensive test coverage
- Updated documentation
- User onboarding guide

---

## Database Migration

Run these migrations to add new tables:

```sql
-- Migration: Add CopilotKit integration tables

-- Learning patterns
CREATE TABLE IF NOT EXISTS learning_patterns (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(10),
    avg_comprehension_time_mins INTEGER,
    best_study_time VARCHAR(20),
    retention_rate DECIMAL(3,2),
    preferred_session_length INTEGER,
    break_frequency_mins INTEGER,
    effectiveness_score DECIMAL(3,2),
    samples_count INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Session effectiveness
CREATE TABLE IF NOT EXISTS session_effectiveness (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES study_sessions(id),
    subject_code VARCHAR(10),
    time_of_day VARCHAR(20),
    duration_mins INTEGER,
    focus_score DECIMAL(3,2),
    material_covered TEXT,
    retention_test_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Achievements
CREATE TABLE IF NOT EXISTS achievement_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10),
    category VARCHAR(50),
    threshold_value INTEGER,
    points INTEGER DEFAULT 10,
    rarity VARCHAR(20) DEFAULT 'common'
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    achievement_id INTEGER REFERENCES achievement_definitions(id),
    earned_at TIMESTAMP DEFAULT NOW(),
    progress_value INTEGER,
    is_complete BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE
);

-- Progress snapshots
CREATE TABLE IF NOT EXISTS progress_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    total_study_mins INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    revisions_completed INTEGER DEFAULT 0,
    goals_progress JSONB,
    streak_count INTEGER DEFAULT 0,
    achievement_points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT,
    priority VARCHAR(20) DEFAULT 'normal',
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    scheduled_for TIMESTAMP,
    sent_at TIMESTAMP,
    read_at TIMESTAMP,
    dismissed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    frequency_limit INTEGER,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Wellbeing
CREATE TABLE IF NOT EXISTS wellbeing_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    study_hours DECIMAL(4,2),
    break_count INTEGER,
    break_total_mins INTEGER,
    deep_work_sessions INTEGER,
    task_completion_rate DECIMAL(3,2),
    overdue_tasks INTEGER,
    stress_indicators JSONB,
    wellbeing_score DECIMAL(3,2),
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS break_sessions (
    id SERIAL PRIMARY KEY,
    break_type VARCHAR(50),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    suggested_duration_mins INTEGER,
    actual_duration_mins INTEGER,
    was_completed BOOLEAN DEFAULT FALSE
);

-- Insert default achievements
INSERT INTO achievement_definitions (code, name, description, icon, category, threshold_value, points, rarity) VALUES
('streak_3', 'Getting Started', 'Maintain a 3-day study streak', '🔥', 'streak', 3, 10, 'common'),
('streak_7', 'Week Warrior', 'Maintain a 7-day study streak', '⚡', 'streak', 7, 25, 'common'),
('streak_30', 'Month Master', 'Maintain a 30-day study streak', '🏆', 'streak', 30, 100, 'rare'),
('streak_100', 'Centurion', 'Maintain a 100-day study streak', '👑', 'streak', 100, 500, 'legendary'),
('deep_work_1', 'Deep Diver', 'Complete your first 90+ min deep work session', '🧠', 'study', 1, 15, 'common'),
('deep_work_10', 'Focus Master', 'Complete 10 deep work sessions', '🎯', 'study', 10, 50, 'rare'),
('tasks_10', 'Task Tackler', 'Complete 10 tasks', '✅', 'goal', 10, 10, 'common'),
('tasks_100', 'Productivity Pro', 'Complete 100 tasks', '🚀', 'goal', 100, 100, 'rare'),
('revision_master', 'Memory Champion', 'Complete all revisions for a chapter', '📚', 'revision', 5, 30, 'rare'),
('early_bird', 'Early Bird', 'Start studying before 7 AM', '🌅', 'special', 1, 20, 'common'),
('night_owl', 'Night Owl', 'Study past midnight productively', '🦉', 'special', 1, 20, 'common'),
('perfectionist', 'Perfectionist', 'Complete all tasks for a week', '💎', 'special', 7, 75, 'epic')
ON CONFLICT (code) DO NOTHING;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON notifications(scheduled_for) WHERE scheduled_for IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_wellbeing_date ON wellbeing_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_progress_date ON progress_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_learning_subject ON learning_patterns(subject_code);
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task completion rate | > 80% | Weekly calculation |
| Study streak average | > 7 days | Rolling average |
| Wellbeing score average | > 0.7 | Daily average |
| AI interaction satisfaction | > 4/5 | User feedback |
| Notification engagement | > 60% | Click-through rate |
| Break compliance | > 70% | Breaks taken vs suggested |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| CopilotKit API changes | Pin versions, maintain fallback to current system |
| Performance issues | Implement caching, lazy loading agents |
| User overwhelm | Progressive disclosure, customizable notifications |
| Data privacy | Local-first approach, user controls data retention |
| Agent conflicts | Clear agent boundaries, coordinator pattern |

---

## Conclusion

This implementation plan transforms the Personal Engineering OS from a tool-based system to a true AI Personal Assistant. By leveraging CopilotKit's CoAgents architecture, the system gains:

1. **Bidirectional State Sync**: UI and AI agents share state seamlessly
2. **Proactive Intelligence**: AI acts without waiting for user prompts
3. **Adaptive Learning**: System improves based on user patterns
4. **Human-in-the-Loop**: User maintains control over significant changes
5. **Holistic Wellbeing**: Beyond productivity to sustainable studying

The phased approach ensures stable progress while the modular agent design allows for future expansion and refinement.
