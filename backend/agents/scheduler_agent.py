"""
Personal Engineering OS - Scheduler Agent
LangGraph-based agent for timeline optimization and schedule management
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import SchedulerState, create_scheduler_state


# ============================================
# NODE: Analyze Schedule
# ============================================

async def analyze_schedule(state: SchedulerState) -> SchedulerState:
    """
    Analyze current schedule for the target date.

    Fetches timetable, existing tasks, and identifies constraints.
    """
    from scheduler import (
        get_timetable_for_date, analyze_day_gaps,
        get_user_schedule_config
    )
    from database import db

    target_date_str = state.get("target_date")
    if not target_date_str:
        target_date_str = str(date.today())

    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    # Get timetable (fixed university classes)
    timetable = get_timetable_for_date(target_date)

    # Get existing tasks
    existing_tasks = await db.fetch("""
        SELECT t.*, s.code as subject_code, s.color
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        WHERE DATE(t.scheduled_start) = $1
        ORDER BY t.scheduled_start
    """, target_date)

    # Get configuration
    config = await get_user_schedule_config()

    return {
        **state,
        "timetable": timetable,
        "existing_tasks": list(existing_tasks),
        "constraints": {
            "sleep_start": config.get("sleep_start", "23:00"),
            "sleep_end": config.get("sleep_end", "06:00"),
            "max_study_block_mins": config.get("max_study_block_mins", 90),
            "min_break_after_study": config.get("min_break_after_study", 15),
            "lunch_time": config.get("lunch_time", "13:00"),
            "dinner_time": config.get("dinner_time", "19:30")
        }
    }


# ============================================
# NODE: Find Gaps
# ============================================

async def find_gaps(state: SchedulerState) -> SchedulerState:
    """
    Find available gaps in the schedule.

    Identifies deep work opportunities and short break slots.
    """
    from scheduler import analyze_day_gaps

    target_date_str = state.get("target_date", str(date.today()))
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()

    # Analyze gaps
    gap_analysis = await analyze_day_gaps(target_date)

    return {
        **state,
        "gaps": gap_analysis.get("gaps", [])
    }


# ============================================
# NODE: Optimize Schedule
# ============================================

async def optimize_schedule(state: SchedulerState) -> SchedulerState:
    """
    Optimize the schedule by matching tasks to gaps.

    Uses energy levels and priorities to place tasks optimally.
    """
    from scheduler import (
        get_pending_work_items, get_energy_level,
        time_to_minutes, minutes_to_time, parse_time,
        DEEP_WORK_MIN_MINUTES
    )

    target_date_str = state.get("target_date", str(date.today()))
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    gaps = state.get("gaps", [])
    constraints = state.get("constraints", {})

    # Get pending work items
    pending_items = await get_pending_work_items(14)

    # Filter schedulable items
    schedulable = [
        item for item in pending_items
        if item.get("estimated_mins", 0) > 0
    ]

    optimized = []
    remaining_gaps = list(gaps)
    total_study_mins = 0
    deep_work_mins = 0

    for item in schedulable:
        if not remaining_gaps:
            break

        # Find best gap for this item
        best_gap_idx = None
        best_score = -1

        for idx, gap in enumerate(remaining_gaps):
            estimated_mins = item.get("estimated_mins", 60)
            if gap["duration_mins"] < min(estimated_mins, 30):
                continue

            # Score based on energy level
            start_hour = int(gap["start"].split(":")[0])
            energy = get_energy_level(start_hour)

            # High-priority items should go in high-energy slots
            priority_normalized = item.get("computed_priority", 50) / 100
            energy_normalized = energy / 10

            # Match priority to energy
            energy_match = 1 - abs(priority_normalized - energy_normalized)

            # Bonus for deep work suitability
            deep_work_bonus = 0.3 if gap["is_deep_work_suitable"] and estimated_mins >= 60 else 0

            score = energy_match + deep_work_bonus

            if score > best_score:
                best_score = score
                best_gap_idx = idx

        if best_gap_idx is not None:
            gap = remaining_gaps[best_gap_idx]
            estimated_mins = item.get("estimated_mins", 60)
            duration = min(
                estimated_mins,
                gap["duration_mins"],
                constraints.get("max_study_block_mins", 120)
            )

            is_deep = gap["is_deep_work_suitable"] and duration >= DEEP_WORK_MIN_MINUTES

            optimized.append({
                "item_id": item.get("id"),
                "item_type": item.get("item_type"),
                "title": (
                    item.get("title") or
                    item.get("chapter_title") or
                    item.get("experiment_name") or
                    "Study Block"
                ),
                "subject": item.get("subject_code"),
                "start": gap["start"],
                "duration_mins": duration,
                "priority": item.get("computed_priority", 50),
                "is_deep_work": is_deep
            })

            total_study_mins += duration
            if is_deep:
                deep_work_mins += duration

            # Update remaining gap
            gap_start_mins = time_to_minutes(parse_time(gap["start"]))
            new_gap_start_mins = gap_start_mins + duration

            if gap["duration_mins"] - duration >= 30:
                remaining_gaps[best_gap_idx] = {
                    **gap,
                    "start": minutes_to_time(new_gap_start_mins).strftime("%H:%M"),
                    "duration_mins": gap["duration_mins"] - duration,
                    "is_deep_work_suitable": (gap["duration_mins"] - duration) >= DEEP_WORK_MIN_MINUTES
                }
            else:
                remaining_gaps.pop(best_gap_idx)

    # Add breaks between long sessions
    final_schedule = []
    for i, block in enumerate(optimized):
        final_schedule.append(block)

        # Add break after 90+ min blocks
        if block["duration_mins"] >= 90 and i < len(optimized) - 1:
            from scheduler import time_to_minutes, minutes_to_time, parse_time
            block_end_mins = time_to_minutes(parse_time(block["start"])) + block["duration_mins"]
            final_schedule.append({
                "item_type": "break",
                "title": "Short Break",
                "start": minutes_to_time(block_end_mins).strftime("%H:%M"),
                "duration_mins": 15,
                "is_deep_work": False
            })

    return {
        **state,
        "optimized_schedule": final_schedule,
        "pending_items": schedulable[:10],  # Store top 10 for reference
        "total_study_mins": total_study_mins,
        "deep_work_mins": deep_work_mins,
        "items_scheduled": len(optimized),
        "gaps_filled": len(gaps) - len(remaining_gaps)
    }


# ============================================
# NODE: Create Blocks
# ============================================

async def create_blocks(state: SchedulerState) -> SchedulerState:
    """
    Create time blocks in the database.

    Converts optimized schedule to actual task entries.
    """
    from scheduler import ai_create_time_block

    target_date_str = state.get("target_date", str(date.today()))
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    optimized = state.get("optimized_schedule", [])

    created = []
    recommendations = []

    for block in optimized:
        if block.get("item_type") == "break":
            # Don't create database entries for breaks
            continue

        # Determine activity type
        item_type = block.get("item_type", "study")
        activity_type = {
            "revision": "revision",
            "lab_report": "lab_work",
            "assignment": "assignment",
            "goal": "study",
            "task": "study"
        }.get(item_type, "study")

        result = await ai_create_time_block(
            block_date=target_date,
            start_time=block["start"],
            duration_mins=block["duration_mins"],
            activity_type=activity_type,
            title=block["title"],
            subject_code=block.get("subject"),
            priority=int(block.get("priority", 50) / 10)  # Convert 0-100 to 0-10
        )

        if result.get("success"):
            created.append(result.get("task"))

    # Generate recommendations
    if state.get("total_study_mins", 0) < 120:
        recommendations.append(
            "Consider adding more study time to meet your daily target."
        )

    if state.get("deep_work_mins", 0) == 0:
        recommendations.append(
            "No deep work sessions scheduled. Try to find a 90+ minute block for focused study."
        )

    unscheduled = len(state.get("pending_items", [])) - state.get("items_scheduled", 0)
    if unscheduled > 0:
        recommendations.append(
            f"{unscheduled} items couldn't be scheduled today. Consider spreading them across the week."
        )

    # Generate summary
    summary = (
        f"Scheduled {state.get('items_scheduled', 0)} study blocks "
        f"totaling {state.get('total_study_mins', 0)} minutes. "
        f"Deep work: {state.get('deep_work_mins', 0)} minutes."
    )

    return {
        **state,
        "created_blocks": created,
        "summary": summary,
        "recommendations": recommendations
    }


# ============================================
# GRAPH CONSTRUCTION
# ============================================

def create_scheduler_agent_graph() -> StateGraph:
    """
    Create the Scheduler agent graph.

    Flow:
    1. analyze_schedule - Get current schedule data
    2. find_gaps - Identify available time slots
    3. optimize_schedule - Match tasks to gaps optimally
    4. create_blocks - Create database entries
    """
    workflow = StateGraph(SchedulerState)

    # Add nodes
    workflow.add_node("analyze_schedule", analyze_schedule)
    workflow.add_node("find_gaps", find_gaps)
    workflow.add_node("optimize_schedule", optimize_schedule)
    workflow.add_node("create_blocks", create_blocks)

    # Define edges
    workflow.set_entry_point("analyze_schedule")
    workflow.add_edge("analyze_schedule", "find_gaps")
    workflow.add_edge("find_gaps", "optimize_schedule")
    workflow.add_edge("optimize_schedule", "create_blocks")
    workflow.add_edge("create_blocks", END)

    return workflow


def compile_scheduler_agent(checkpointer: Optional[MemorySaver] = None):
    """Compile the scheduler agent graph."""
    graph = create_scheduler_agent_graph()

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# ============================================
# AGENT INTERFACE
# ============================================

class SchedulerAgent:
    """
    High-level interface for the Scheduler agent.
    """

    def __init__(self, checkpointer: Optional[MemorySaver] = None):
        self.checkpointer = checkpointer or MemorySaver()
        self.agent = compile_scheduler_agent(self.checkpointer)

    async def optimize_day(
        self,
        target_date: Optional[str] = None,
        reason: Optional[str] = None,
        thread_id: str = "scheduler"
    ) -> Dict[str, Any]:
        """
        Optimize schedule for a specific day.

        Args:
            target_date: Date to optimize (YYYY-MM-DD format)
            reason: Reason for optimization
            thread_id: Thread ID for state persistence

        Returns:
            Optimization results
        """
        if target_date is None:
            target_date = str(date.today())

        initial_state = create_scheduler_state(target_date, reason)
        config = {"configurable": {"thread_id": thread_id}}

        final_state = await self.agent.ainvoke(initial_state, config)

        return {
            "date": target_date,
            "optimized_schedule": final_state.get("optimized_schedule", []),
            "created_blocks": final_state.get("created_blocks", []),
            "total_study_mins": final_state.get("total_study_mins", 0),
            "deep_work_mins": final_state.get("deep_work_mins", 0),
            "items_scheduled": final_state.get("items_scheduled", 0),
            "summary": final_state.get("summary", ""),
            "recommendations": final_state.get("recommendations", [])
        }

    async def optimize_week(
        self,
        start_date: Optional[str] = None,
        thread_id: str = "scheduler_week"
    ) -> Dict[str, Any]:
        """
        Optimize schedule for an entire week.

        Args:
            start_date: Start date (YYYY-MM-DD format)
            thread_id: Thread ID prefix for state persistence

        Returns:
            Weekly optimization results
        """
        if start_date is None:
            start_date = str(date.today())

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        weekly_results = []

        total_study_mins = 0
        total_deep_work_mins = 0
        total_items_scheduled = 0

        for i in range(7):
            day_date = start + timedelta(days=i)
            day_result = await self.optimize_day(
                str(day_date),
                thread_id=f"{thread_id}_{i}"
            )
            weekly_results.append(day_result)

            total_study_mins += day_result.get("total_study_mins", 0)
            total_deep_work_mins += day_result.get("deep_work_mins", 0)
            total_items_scheduled += day_result.get("items_scheduled", 0)

        return {
            "start_date": start_date,
            "end_date": str(start + timedelta(days=6)),
            "days": weekly_results,
            "summary": {
                "total_study_mins": total_study_mins,
                "total_study_hours": round(total_study_mins / 60, 1),
                "total_deep_work_mins": total_deep_work_mins,
                "total_items_scheduled": total_items_scheduled
            }
        }


# Create default agent instance
default_scheduler_agent = None


def get_scheduler_agent() -> SchedulerAgent:
    """Get or create the default scheduler agent instance."""
    global default_scheduler_agent
    if default_scheduler_agent is None:
        default_scheduler_agent = SchedulerAgent()
    return default_scheduler_agent
