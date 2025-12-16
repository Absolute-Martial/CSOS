"""
Personal Engineering OS - CopilotKit Integration
SDK setup for CopilotKit with LangGraph agents
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent
from langgraph.checkpoint.memory import MemorySaver

from agents import (
    # Agents
    get_pa_agent,
    get_scheduler_agent,
    get_planner_agent,
    get_wellbeing_agent,
    # Graph compilers
    compile_pa_agent,
    compile_scheduler_agent,
    compile_planner_agent,
    compile_wellbeing_agent,
)


# ============================================
# CONFIGURATION
# ============================================

COPILOTKIT_RUNTIME_URL = os.getenv("COPILOTKIT_RUNTIME_URL", "http://localhost:4141")
COPILOTKIT_PUBLIC_API_KEY = os.getenv("COPILOTKIT_PUBLIC_API_KEY", "")


# ============================================
# AGENT REGISTRY
# ============================================

class AgentRegistry:
    """
    Registry for all LangGraph agents in the system.

    Manages agent instances and provides access for CopilotKit.
    """

    def __init__(self):
        self._checkpointer = MemorySaver()
        self._agents: Dict[str, Any] = {}
        self._initialized = False

    def initialize(self):
        """Initialize all agents."""
        if self._initialized:
            return

        # Compile agents with shared checkpointer
        self._agents["personal_assistant"] = compile_pa_agent(self._checkpointer)
        self._agents["scheduler"] = compile_scheduler_agent(self._checkpointer)
        self._agents["planner"] = compile_planner_agent(self._checkpointer)
        self._agents["wellbeing"] = compile_wellbeing_agent(self._checkpointer)

        self._initialized = True

    def get_agent(self, name: str):
        """Get an agent by name."""
        if not self._initialized:
            self.initialize()
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """List all available agents."""
        return list(self._agents.keys())

    @property
    def checkpointer(self) -> MemorySaver:
        """Get the shared checkpointer."""
        return self._checkpointer


# Global registry instance
agent_registry = AgentRegistry()


# ============================================
# COPILOTKIT SDK SETUP
# ============================================

def create_copilotkit_sdk() -> CopilotKitSDK:
    """
    Create and configure the CopilotKit SDK with all agents.

    Returns:
        Configured CopilotKitSDK instance
    """
    # Initialize agents
    agent_registry.initialize()

    # Create LangGraph agent wrappers for CopilotKit
    langgraph_agents = [
        LangGraphAgent(
            name="personal_assistant",
            description=(
                "Main personal assistant for study management. "
                "Handles schedule queries, task management, study sessions, "
                "revisions, goals, and general conversation."
            ),
            agent=agent_registry.get_agent("personal_assistant"),
        ),
        LangGraphAgent(
            name="scheduler",
            description=(
                "Schedule optimization agent. "
                "Analyzes schedule gaps, optimizes task placement, "
                "and creates study blocks based on energy levels."
            ),
            agent=agent_registry.get_agent("scheduler"),
        ),
        LangGraphAgent(
            name="planner",
            description=(
                "Study planner agent. "
                "Analyzes study patterns, generates recommendations, "
                "and creates comprehensive study plans."
            ),
            agent=agent_registry.get_agent("planner"),
        ),
        LangGraphAgent(
            name="wellbeing",
            description=(
                "Wellbeing monitor agent. "
                "Tracks study time, stress levels, and break compliance. "
                "Provides health recommendations."
            ),
            agent=agent_registry.get_agent("wellbeing"),
        ),
    ]

    # Create SDK
    sdk = CopilotKitSDK(
        agents=langgraph_agents,
    )

    return sdk


# Global SDK instance
_copilotkit_sdk: Optional[CopilotKitSDK] = None


def get_copilotkit_sdk() -> CopilotKitSDK:
    """Get or create the CopilotKit SDK instance."""
    global _copilotkit_sdk
    if _copilotkit_sdk is None:
        _copilotkit_sdk = create_copilotkit_sdk()
    return _copilotkit_sdk


# ============================================
# FASTAPI INTEGRATION
# ============================================

def setup_copilotkit(app: FastAPI, path: str = "/copilotkit"):
    """
    Add CopilotKit endpoint to FastAPI application.

    Args:
        app: FastAPI application instance
        path: URL path for CopilotKit endpoint (default: /copilotkit)
    """
    sdk = get_copilotkit_sdk()

    # Add the CopilotKit endpoint
    add_fastapi_endpoint(app, sdk, path)

    # Add additional helper endpoints
    @app.get(f"{path}/agents")
    async def list_available_agents():
        """List all available agents."""
        return {
            "agents": agent_registry.list_agents(),
            "count": len(agent_registry.list_agents())
        }

    @app.get(f"{path}/health")
    async def copilotkit_health():
        """Check CopilotKit health status."""
        return {
            "status": "healthy",
            "sdk_initialized": _copilotkit_sdk is not None,
            "agents_initialized": agent_registry._initialized,
            "timestamp": datetime.now().isoformat()
        }

    return sdk


# ============================================
# DIRECT AGENT API
# ============================================

async def chat_with_agent(
    agent_name: str,
    message: str,
    thread_id: str = "default",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Chat with a specific agent directly.

    Args:
        agent_name: Name of the agent to use
        message: User message
        thread_id: Conversation thread ID
        metadata: Additional metadata to pass

    Returns:
        Agent response
    """
    if agent_name == "personal_assistant":
        pa = get_pa_agent()
        return await pa.chat(message, thread_id)

    elif agent_name == "scheduler":
        scheduler = get_scheduler_agent()
        # For scheduler, extract date from message or use today
        from datetime import date
        return await scheduler.optimize_day(str(date.today()), thread_id=thread_id)

    elif agent_name == "planner":
        planner = get_planner_agent()
        return await planner.create_study_plan(thread_id=thread_id)

    elif agent_name == "wellbeing":
        wellbeing = get_wellbeing_agent()
        return await wellbeing.check_wellbeing(thread_id)

    else:
        raise ValueError(f"Unknown agent: {agent_name}")


async def get_agent_state(
    agent_name: str,
    thread_id: str = "default"
) -> Optional[Dict[str, Any]]:
    """
    Get the current state of an agent thread.

    Args:
        agent_name: Name of the agent
        thread_id: Thread ID

    Returns:
        Current state or None
    """
    agent = agent_registry.get_agent(agent_name)
    if agent is None:
        return None

    config = {"configurable": {"thread_id": thread_id}}
    return agent.get_state(config)


# ============================================
# STREAMING SUPPORT
# ============================================

async def stream_agent_response(
    agent_name: str,
    message: str,
    thread_id: str = "default"
):
    """
    Stream responses from an agent.

    Yields state updates as the agent processes.

    Args:
        agent_name: Name of the agent
        message: User message
        thread_id: Thread ID

    Yields:
        State updates from the agent
    """
    if agent_name == "personal_assistant":
        pa = get_pa_agent()
        async for event in pa.stream_chat(message, thread_id):
            yield event
    else:
        # For non-PA agents, yield single result
        result = await chat_with_agent(agent_name, message, thread_id)
        yield result


# ============================================
# MULTI-AGENT ORCHESTRATION
# ============================================

async def orchestrate_request(
    message: str,
    thread_id: str = "default"
) -> Dict[str, Any]:
    """
    Orchestrate a request across multiple agents.

    The PA agent routes to specialized agents as needed.

    Args:
        message: User message
        thread_id: Conversation thread ID

    Returns:
        Combined response from agents
    """
    # Start with PA agent to understand intent
    pa = get_pa_agent()
    pa_response = await pa.chat(message, thread_id)

    intent = pa_response.get("intent", "unknown")
    results = {"pa_response": pa_response}

    # Route to specialized agents based on intent
    if intent in ["schedule_query", "schedule_modify", "reschedule"]:
        scheduler = get_scheduler_agent()
        results["scheduler_analysis"] = await scheduler.optimize_day(
            thread_id=f"{thread_id}_scheduler"
        )

    elif intent == "analytics":
        planner = get_planner_agent()
        results["study_plan"] = await planner.get_quick_insights(
            thread_id=f"{thread_id}_planner"
        )

    elif intent == "wellbeing":
        wellbeing = get_wellbeing_agent()
        results["wellbeing_check"] = await wellbeing.check_wellbeing(
            thread_id=f"{thread_id}_wellbeing"
        )

    # Always include wellbeing check if studying for long time
    wellbeing = get_wellbeing_agent()
    break_check = await wellbeing.should_suggest_break()
    if break_check.get("should_break"):
        results["break_suggestion"] = break_check

    return results


# ============================================
# COPILOTKIT ACTIONS
# ============================================

def get_copilotkit_actions() -> List[Dict[str, Any]]:
    """
    Get CopilotKit actions for frontend integration.

    These actions can be called from the frontend CopilotKit components.
    """
    return [
        {
            "name": "start_study_session",
            "description": "Start a study timer for a subject",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject_code": {
                        "type": "string",
                        "description": "Subject code (e.g., MATH101)"
                    },
                    "title": {
                        "type": "string",
                        "description": "Session title"
                    }
                }
            }
        },
        {
            "name": "stop_study_session",
            "description": "Stop the current study timer",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "get_schedule",
            "description": "Get today's schedule",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "optimize_day",
            "description": "Optimize schedule for a specific day",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                }
            }
        },
        {
            "name": "check_wellbeing",
            "description": "Check user wellbeing status",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "create_study_plan",
            "description": "Create a study plan for the next N days",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to plan for"
                    }
                }
            }
        }
    ]


# ============================================
# INITIALIZATION
# ============================================

def initialize_copilotkit():
    """Initialize CopilotKit and all agents."""
    agent_registry.initialize()
    get_copilotkit_sdk()
    print("CopilotKit initialized with agents:", agent_registry.list_agents())
