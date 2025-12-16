"""
Personal Engineering OS - Main Personal Assistant Agent
LangGraph-based agent for handling user interactions
"""

import os
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .state import (
    PAState, Message, IntentType, ScheduleContext, UserProfile,
    CurrentTask, PendingAction, create_initial_pa_state
)


# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL_NAME = os.getenv("PA_MODEL_NAME", "claude-3-5-sonnet-20241022")


# Initialize LLM
def get_llm():
    """Get the LLM instance for the PA agent."""
    return ChatAnthropic(
        model=MODEL_NAME,
        anthropic_api_key=ANTHROPIC_API_KEY,
        temperature=0.3,
        max_tokens=2048
    )


# ============================================
# NODE: Understand Intent
# ============================================

async def understand_intent(state: PAState) -> PAState:
    """
    Analyze user message to understand intent.

    This node classifies the user's intent to route to appropriate handlers.
    """
    messages = state.get("messages", [])
    if not messages:
        return {**state, "identified_intent": IntentType.UNKNOWN, "intent_confidence": 0.0}

    last_message = messages[-1]
    user_text = last_message.get("content", "").lower()

    # Intent classification rules
    intent_patterns = {
        IntentType.SCHEDULE_QUERY: [
            "schedule", "what's my", "when is", "timetable", "today", "calendar",
            "what do i have", "classes", "next class"
        ],
        IntentType.SCHEDULE_MODIFY: [
            "add", "schedule", "create", "block", "set up", "plan", "move", "reschedule"
        ],
        IntentType.STUDY_START: [
            "start study", "i'm studying", "begin study", "start timer", "studying now",
            "focus on", "work on"
        ],
        IntentType.STUDY_STOP: [
            "stop timer", "done studying", "finished", "stop study", "end session"
        ],
        IntentType.REVISION: [
            "revision", "review", "revise", "due revision", "spaced repetition"
        ],
        IntentType.LAB_REPORT: [
            "lab report", "lab", "experiment", "physics lab", "chemistry lab", "thermal lab"
        ],
        IntentType.GOAL_MANAGE: [
            "goal", "target", "set goal", "progress", "achieve"
        ],
        IntentType.DEADLINE: [
            "deadline", "due", "when is", "assignment due", "submission"
        ],
        IntentType.RESCHEDULE: [
            "reschedule", "sick", "cancel", "emergency", "surprise", "can't make it",
            "something came up"
        ],
        IntentType.BACKWARD_PLAN: [
            "exam", "test", "prepare for", "i have a test", "quiz", "midterm", "final"
        ],
        IntentType.WELLBEING: [
            "tired", "stressed", "exhausted", "break", "rest", "overwhelmed",
            "can't focus", "need help"
        ],
        IntentType.ANALYTICS: [
            "how much", "statistics", "analytics", "study time", "progress report",
            "this week", "this month"
        ],
        IntentType.MEMORY: [
            "remember", "i wake up", "i prefer", "my schedule", "i like",
            "note that", "keep in mind"
        ],
        IntentType.TASK_MANAGE: [
            "mark", "complete", "done", "finish", "check off", "update task"
        ]
    }

    # Score each intent
    scores = {}
    for intent, patterns in intent_patterns.items():
        score = sum(1 for p in patterns if p in user_text)
        if score > 0:
            scores[intent] = score

    # Determine best intent
    if scores:
        best_intent = max(scores, key=scores.get)
        confidence = min(1.0, scores[best_intent] / 3)  # Normalize confidence
    else:
        best_intent = IntentType.GENERAL_CHAT
        confidence = 0.5

    return {
        **state,
        "identified_intent": best_intent,
        "intent_confidence": confidence
    }


# ============================================
# NODE: Gather Context
# ============================================

async def gather_context(state: PAState) -> PAState:
    """
    Gather relevant context based on identified intent.

    This node fetches schedule, tasks, and other relevant data.
    """
    from database import db, get_ai_memory, get_ai_guidelines
    from scheduler import (
        get_today_at_glance, get_pending_work_items,
        get_user_schedule_config, get_energy_level
    )
    from timer import get_active_timer

    intent = state.get("identified_intent", IntentType.GENERAL_CHAT)

    # Always get basic context
    schedule_context: ScheduleContext = {}
    user_profile: UserProfile = {}
    current_task: Optional[CurrentTask] = None

    try:
        # Get today's schedule
        today_data = await get_today_at_glance()
        schedule_context = {
            "date": today_data.get("date"),
            "day_name": today_data.get("day"),
            "current_time": datetime.now().strftime("%H:%M"),
            "timetable": today_data.get("timetable", {}).get("classes", []),
            "tasks": today_data.get("tasks", {}).get("scheduled", []),
            "gaps": today_data.get("gaps", {}).get("slots", []),
            "total_available_mins": today_data.get("gaps", {}).get("total_available_mins", 0),
            "deep_work_available_mins": today_data.get("gaps", {}).get("deep_work_mins", 0),
            "active_timer": today_data.get("active_timer"),
            "pending_revisions": [],
            "upcoming_deadlines": today_data.get("deadlines", []),
            "lab_reports": today_data.get("lab_reports", {}).get("urgent", [])
        }

        # Get user preferences
        config = await get_user_schedule_config()
        memories = await get_ai_memory()
        guidelines = await get_ai_guidelines()
        streak_data = today_data.get("streak", {})

        user_profile = {
            "sleep_start": config.get("sleep_start", "23:00"),
            "sleep_end": config.get("sleep_end", "06:00"),
            "preferred_study_times": config.get("preferred_study_times", ["morning"]),
            "max_study_block_mins": config.get("max_study_block_mins", 90),
            "commute_mins": config.get("commute_mins", 30),
            "energy_level": get_energy_level(datetime.now().hour),
            "current_streak": streak_data.get("current_streak", 0) if streak_data else 0,
            "total_points": streak_data.get("total_points", 0) if streak_data else 0,
            "memories": memories,
            "guidelines": guidelines
        }

        # Get active timer if any
        active_timer = await get_active_timer()
        if active_timer:
            current_task = {
                "task_id": active_timer.get("task_id"),
                "session_id": active_timer.get("session_id"),
                "title": active_timer.get("title", "Study Session"),
                "subject_code": active_timer.get("subject_code"),
                "started_at": str(active_timer.get("started_at")),
                "elapsed_seconds": active_timer.get("elapsed_seconds", 0),
                "is_deep_work": active_timer.get("elapsed_seconds", 0) >= 5400  # 90 mins
            }

        # Get intent-specific context
        if intent in [IntentType.REVISION, IntentType.SCHEDULE_QUERY]:
            pending = await get_pending_work_items(7)
            revisions = [p for p in pending if p.get("item_type") == "revision"]
            schedule_context["pending_revisions"] = revisions[:5]

    except Exception as e:
        # Log error but continue with partial context
        print(f"Error gathering context: {e}")

    return {
        **state,
        "schedule_context": schedule_context,
        "user_profile": user_profile,
        "current_task": current_task
    }


# ============================================
# NODE: Plan Action
# ============================================

async def plan_action(state: PAState) -> PAState:
    """
    Plan actions based on intent and context.

    This node determines what tools to call and parameters.
    """
    intent = state.get("identified_intent", IntentType.GENERAL_CHAT)
    messages = state.get("messages", [])
    schedule_context = state.get("schedule_context", {})

    last_message = messages[-1].get("content", "") if messages else ""
    planned_actions: List[PendingAction] = []

    # Plan actions based on intent
    if intent == IntentType.SCHEDULE_QUERY:
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_today_schedule",
            "parameters": {},
            "confirmation_required": False,
            "description": "Fetching today's schedule"
        })

    elif intent == IntentType.STUDY_START:
        # Extract subject from message
        subject_code = None
        for word in last_message.upper().split():
            if len(word) >= 4 and word[:4].isalpha() and len(word) >= 7:
                if word[-3:].isdigit():
                    subject_code = word
                    break

        planned_actions.append({
            "action_type": "execute",
            "tool_name": "start_study_timer",
            "parameters": {"subject_code": subject_code} if subject_code else {},
            "confirmation_required": False,
            "description": f"Starting study timer{' for ' + subject_code if subject_code else ''}"
        })

    elif intent == IntentType.STUDY_STOP:
        planned_actions.append({
            "action_type": "execute",
            "tool_name": "stop_study_timer",
            "parameters": {},
            "confirmation_required": False,
            "description": "Stopping study timer"
        })

    elif intent == IntentType.REVISION:
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_revision_queue",
            "parameters": {},
            "confirmation_required": False,
            "description": "Fetching pending revisions"
        })

    elif intent == IntentType.LAB_REPORT:
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_lab_reports",
            "parameters": {},
            "confirmation_required": False,
            "description": "Fetching lab report status"
        })

    elif intent == IntentType.DEADLINE:
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_upcoming_deadlines",
            "parameters": {"days": 14},
            "confirmation_required": False,
            "description": "Fetching upcoming deadlines"
        })

    elif intent == IntentType.RESCHEDULE:
        # Extract reason from message
        reason = last_message[:100]  # Truncate for safety
        planned_actions.append({
            "action_type": "execute",
            "tool_name": "reschedule_all",
            "parameters": {"reason": reason},
            "confirmation_required": True,
            "description": "Rescheduling all pending tasks"
        })

    elif intent == IntentType.BACKWARD_PLAN:
        # This would need more parsing in production
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_schedule_context",
            "parameters": {},
            "confirmation_required": False,
            "description": "Getting context for backward planning"
        })

    elif intent == IntentType.ANALYTICS:
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_study_stats",
            "parameters": {"days": 7},
            "confirmation_required": False,
            "description": "Fetching study statistics"
        })

    elif intent == IntentType.WELLBEING:
        # Trigger wellbeing check
        planned_actions.append({
            "action_type": "check",
            "tool_name": "wellbeing_check",
            "parameters": {},
            "confirmation_required": False,
            "description": "Checking wellbeing status"
        })

    elif intent == IntentType.MEMORY:
        # Memory operations need LLM to extract key-value
        planned_actions.append({
            "action_type": "llm_extract",
            "tool_name": "remember_user_info",
            "parameters": {"raw_input": last_message},
            "confirmation_required": False,
            "description": "Extracting information to remember"
        })

    elif intent == IntentType.GOAL_MANAGE:
        planned_actions.append({
            "action_type": "query",
            "tool_name": "get_goals",
            "parameters": {},
            "confirmation_required": False,
            "description": "Fetching goals"
        })

    return {
        **state,
        "planned_actions": planned_actions
    }


# ============================================
# NODE: Execute Action
# ============================================

async def execute_action(state: PAState) -> PAState:
    """
    Execute planned actions using tools.

    This node calls the appropriate tool handlers.
    """
    from tools import execute_tool

    planned_actions = state.get("planned_actions", [])
    tool_calls_made = []
    last_result = None

    for action in planned_actions:
        if action.get("confirmation_required"):
            # Skip actions needing confirmation for now
            continue

        tool_name = action.get("tool_name")
        parameters = action.get("parameters", {})

        try:
            # Handle special action types
            if action.get("action_type") == "llm_extract":
                # Use LLM to extract structured data
                result = await _llm_extract_memory(parameters.get("raw_input", ""))
            elif action.get("action_type") == "check":
                # Wellbeing check
                result = await _check_wellbeing(state)
            else:
                # Regular tool execution
                result = await execute_tool(tool_name, parameters)

            tool_calls_made.append({
                "tool": tool_name,
                "parameters": parameters,
                "result": result,
                "success": "error" not in result
            })
            last_result = result

        except Exception as e:
            tool_calls_made.append({
                "tool": tool_name,
                "parameters": parameters,
                "result": {"error": str(e)},
                "success": False
            })

    return {
        **state,
        "tool_calls_made": tool_calls_made,
        "last_action": planned_actions[0].get("tool_name") if planned_actions else None,
        "last_action_result": last_result
    }


async def _llm_extract_memory(raw_input: str) -> Dict[str, Any]:
    """Use LLM to extract structured memory from user input."""
    from tools import execute_tool

    # Simple extraction logic - could be enhanced with LLM
    lower_input = raw_input.lower()

    # Common patterns
    if "wake up" in lower_input or "i wake" in lower_input:
        # Extract time
        import re
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', lower_input)
        if time_match:
            return await execute_tool("remember_user_info", {
                "category": "schedule",
                "key": "wake_time",
                "value": time_match.group(1)
            })

    if "sleep" in lower_input or "bed" in lower_input:
        import re
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)', lower_input)
        if time_match:
            return await execute_tool("remember_user_info", {
                "category": "schedule",
                "key": "sleep_start",
                "value": time_match.group(1)
            })

    if "prefer" in lower_input:
        return await execute_tool("remember_user_info", {
            "category": "preference",
            "key": "user_preference",
            "value": raw_input
        })

    # Generic memory save
    return await execute_tool("remember_user_info", {
        "category": "personal",
        "key": "note",
        "value": raw_input
    })


async def _check_wellbeing(state: PAState) -> Dict[str, Any]:
    """Check user wellbeing based on current state."""
    schedule_context = state.get("schedule_context", {})
    user_profile = state.get("user_profile", {})
    current_task = state.get("current_task")

    stress_indicators = 0
    positive_indicators = 0
    recommendations = []

    # Check study time today
    # (Would need to query actual study time in production)

    # Check if been studying too long
    if current_task:
        elapsed_mins = current_task.get("elapsed_seconds", 0) / 60
        if elapsed_mins > 120:
            stress_indicators += 2
            recommendations.append("You've been studying for over 2 hours. Consider taking a 15-minute break.")

    # Check energy level
    energy = user_profile.get("energy_level", 5)
    if energy < 4:
        stress_indicators += 1
        recommendations.append("Your energy is low. A short walk or snack might help.")
    elif energy > 7:
        positive_indicators += 1

    # Check pending deadlines
    deadlines = schedule_context.get("upcoming_deadlines", [])
    urgent = [d for d in deadlines if d.get("days_remaining", 99) <= 2]
    if len(urgent) > 2:
        stress_indicators += 1
        recommendations.append(f"You have {len(urgent)} urgent deadlines. Let's prioritize them.")

    # Calculate status
    if stress_indicators >= 3:
        status = "stressed"
    elif stress_indicators >= 2:
        status = "moderate"
    elif positive_indicators >= 2:
        status = "good"
    else:
        status = "moderate"

    return {
        "success": True,
        "status": status,
        "stress_level": min(10, stress_indicators * 2 + 3),
        "recommendations": recommendations
    }


# ============================================
# NODE: Generate Response
# ============================================

async def generate_response(state: PAState) -> PAState:
    """
    Generate natural language response using LLM.

    This node creates the final response to the user.
    """
    intent = state.get("identified_intent", IntentType.GENERAL_CHAT)
    messages = state.get("messages", [])
    schedule_context = state.get("schedule_context", {})
    user_profile = state.get("user_profile", {})
    tool_calls_made = state.get("tool_calls_made", [])

    # Build context for LLM
    user_message = messages[-1].get("content", "") if messages else ""

    # Build system prompt
    guidelines_text = "\n".join([
        f"- {g['rule']}" for g in user_profile.get("guidelines", [])
    ])

    memories_text = "\n".join([
        f"- {m['category']}/{m['key']}: {m['value']}"
        for m in user_profile.get("memories", [])
    ])

    tool_results_text = ""
    for tc in tool_calls_made:
        tool_results_text += f"\nTool: {tc['tool']}\nResult: {json.dumps(tc['result'], default=str)[:500]}\n"

    system_prompt = f"""You are a helpful Personal Assistant AI for a KU Engineering student's study management system.

Current Context:
- Date: {schedule_context.get('date', 'Unknown')} ({schedule_context.get('day_name', '')})
- Time: {schedule_context.get('current_time', '')}
- Energy Level: {user_profile.get('energy_level', 'Unknown')}/10
- Streak: {user_profile.get('current_streak', 0)} days

User Guidelines:
{guidelines_text or 'None set'}

What I Remember About User:
{memories_text or 'Nothing yet'}

Tool Results:
{tool_results_text or 'No tools called'}

Instructions:
1. Be concise and helpful
2. Reference the tool results in your response
3. If showing schedule data, format it clearly
4. Encourage the user and mention streaks when relevant
5. Suggest breaks if they've been studying too long
6. Be proactive about upcoming deadlines
"""

    try:
        llm = get_llm()

        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        response_text = response.content

    except Exception as e:
        # Fallback response generation
        response_text = _generate_fallback_response(intent, tool_calls_made, schedule_context)

    # Add assistant message to history
    new_message: Message = {
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.now().isoformat(),
        "tool_calls": tool_calls_made if tool_calls_made else None,
        "tool_results": None
    }

    return {
        **state,
        "response_text": response_text,
        "messages": [new_message]  # This will be appended via reducer
    }


def _generate_fallback_response(
    intent: str,
    tool_calls: List[Dict],
    context: Dict
) -> str:
    """Generate a fallback response without LLM."""
    if not tool_calls:
        return "I understand your request. How can I help you with your studies today?"

    result = tool_calls[0].get("result", {})

    if intent == IntentType.SCHEDULE_QUERY:
        tasks = result.get("tasks", {})
        return f"Here's your schedule for today. You have {tasks.get('count', 0)} tasks scheduled."

    elif intent == IntentType.STUDY_START:
        if result.get("success"):
            return "Timer started! Good luck with your study session."
        return "I couldn't start the timer. Please try again."

    elif intent == IntentType.STUDY_STOP:
        if result.get("success"):
            duration = result.get("duration_mins", 0)
            return f"Great work! You studied for {duration} minutes."
        return "There's no active timer to stop."

    elif intent == IntentType.REVISION:
        revisions = result.get("revisions", [])
        return f"You have {len(revisions)} revisions due."

    return "I've processed your request. Is there anything else you'd like to know?"


# ============================================
# ROUTING LOGIC
# ============================================

def should_execute_actions(state: PAState) -> Literal["execute_action", "generate_response"]:
    """Determine if we should execute actions or go directly to response."""
    planned_actions = state.get("planned_actions", [])

    if planned_actions:
        return "execute_action"
    return "generate_response"


def should_continue(state: PAState) -> Literal["generate_response", END]:
    """Determine if we should generate response or end."""
    error = state.get("error")

    if error:
        return END
    return "generate_response"


# ============================================
# GRAPH CONSTRUCTION
# ============================================

def create_pa_agent_graph() -> StateGraph:
    """
    Create the Personal Assistant agent graph.

    Flow:
    1. understand_intent - Classify user intent
    2. gather_context - Fetch relevant data
    3. plan_action - Determine actions needed
    4. execute_action - Run tools (conditional)
    5. generate_response - Create response
    """
    # Create the graph
    workflow = StateGraph(PAState)

    # Add nodes
    workflow.add_node("understand_intent", understand_intent)
    workflow.add_node("gather_context", gather_context)
    workflow.add_node("plan_action", plan_action)
    workflow.add_node("execute_action", execute_action)
    workflow.add_node("generate_response", generate_response)

    # Define edges
    workflow.set_entry_point("understand_intent")
    workflow.add_edge("understand_intent", "gather_context")
    workflow.add_edge("gather_context", "plan_action")

    # Conditional edge: execute actions or skip to response
    workflow.add_conditional_edges(
        "plan_action",
        should_execute_actions,
        {
            "execute_action": "execute_action",
            "generate_response": "generate_response"
        }
    )

    # After execution, always generate response
    workflow.add_edge("execute_action", "generate_response")

    # End after response
    workflow.add_edge("generate_response", END)

    return workflow


def compile_pa_agent(checkpointer: Optional[MemorySaver] = None):
    """
    Compile the PA agent graph with optional checkpointing.

    Args:
        checkpointer: Optional MemorySaver for conversation persistence

    Returns:
        Compiled agent graph
    """
    graph = create_pa_agent_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# ============================================
# AGENT INTERFACE
# ============================================

class PersonalAssistantAgent:
    """
    High-level interface for the Personal Assistant agent.
    """

    def __init__(self, checkpointer: Optional[MemorySaver] = None):
        """Initialize the agent with optional checkpointing."""
        self.checkpointer = checkpointer or MemorySaver()
        self.agent = compile_pa_agent(self.checkpointer)

    async def chat(
        self,
        message: str,
        thread_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Process a chat message and return response.

        Args:
            message: User message
            thread_id: Conversation thread ID for state persistence

        Returns:
            Response dict with text, tool_calls, and metadata
        """
        # Create initial state
        initial_state = create_initial_pa_state(message)

        # Configure thread
        config = {"configurable": {"thread_id": thread_id}}

        # Run the agent
        final_state = await self.agent.ainvoke(initial_state, config)

        return {
            "response": final_state.get("response_text", ""),
            "tool_calls": final_state.get("tool_calls_made", []),
            "intent": final_state.get("identified_intent", "unknown"),
            "intent_confidence": final_state.get("intent_confidence", 0.0),
            "schedule_context": final_state.get("schedule_context", {}),
            "wellbeing_metrics": final_state.get("wellbeing_metrics", {})
        }

    async def stream_chat(
        self,
        message: str,
        thread_id: str = "default"
    ):
        """
        Stream a chat response for real-time updates.

        Yields state updates as the agent processes.
        """
        initial_state = create_initial_pa_state(message)
        config = {"configurable": {"thread_id": thread_id}}

        async for event in self.agent.astream(initial_state, config):
            yield event

    def get_state(self, thread_id: str = "default") -> Optional[PAState]:
        """Get the current state for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        return self.agent.get_state(config)


# Create default agent instance
default_pa_agent = None


def get_pa_agent() -> PersonalAssistantAgent:
    """Get or create the default PA agent instance."""
    global default_pa_agent
    if default_pa_agent is None:
        default_pa_agent = PersonalAssistantAgent()
    return default_pa_agent
