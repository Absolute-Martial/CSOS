"""
AI Engineering Study Assistant - Python-C Bridge
Uses ctypes to interface with the C optimization engine.

This module provides a Python wrapper around the C constraint satisfaction
solver for timeline optimization.
"""

import ctypes
import os
import json
import logging
from ctypes import Structure, c_int, c_bool, c_char, POINTER, byref
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import IntEnum

from config import get_engine_config, get_optimization_config, get_schedule_config

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS (must match C definitions)
# ============================================

MAX_TITLE_LEN = 200
MAX_SUBJECT_LEN = 20
SLOTS_PER_DAY = 48  # 30-minute slots per day
WEEK_SLOTS = 336    # 7 days * 48 slots
MAX_TASKS = 100


# ============================================
# TASK CATEGORY ENUM
# ============================================

class TaskCategory(IntEnum):
    """
    Task type enum matching C TaskCategory.
    Determines scheduling priority and placement heuristics.
    """
    FIXED_CLASS = 0      # University lectures (immutable)
    STUDY_CONCEPT = 1    # Conceptual learning (morning priority)
    STUDY_PRACTICE = 2   # Practice problems (evening priority)
    MICRO_GAP = 3        # 15-30 min tasks (flashcards, quick reviews)
    SLEEP = 4            # Rest blocks (immutable)
    BREAK = 5            # Break periods
    MEAL = 6             # Meal times
    REVISION = 7         # Spaced repetition reviews
    ASSIGNMENT = 8       # Assignment work
    LAB_WORK = 9         # Lab report work


# ============================================
# CTYPES STRUCTURES
# ============================================

class TimelineTask(Structure):
    """
    Matches C TimelineTask struct.
    Represents a task to be placed in the timeline.
    """
    _fields_ = [
        ("id", c_int),
        ("duration_slots", c_int),      # Duration in 30-min slots
        ("priority", c_int),            # 1-10, higher = more important
        ("category", c_int),            # TaskCategory enum value
        ("deadline_slot", c_int),       # Absolute slot index for deadline
        ("is_locked", c_bool),          # If true, cannot be moved
        ("title", c_char * MAX_TITLE_LEN),
        ("subject", c_char * MAX_SUBJECT_LEN),
        ("preferred_slot", c_int),      # Preferred placement (-1 for none)
        ("assigned_slot", c_int),       # Assigned slot after optimization
    ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Python dictionary."""
        return {
            "id": self.id,
            "duration_slots": self.duration_slots,
            "priority": self.priority,
            "category": self.category,
            "deadline_slot": self.deadline_slot,
            "is_locked": self.is_locked,
            "title": self.title.decode('utf-8', errors='ignore').strip('\x00'),
            "subject": self.subject.decode('utf-8', errors='ignore').strip('\x00'),
            "preferred_slot": self.preferred_slot,
            "assigned_slot": self.assigned_slot,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimelineTask':
        """Create from Python dictionary."""
        task = cls()
        task.id = data.get('id', 0)
        task.duration_slots = data.get('duration_slots', 2)
        task.priority = data.get('priority', 5)
        task.category = data.get('category', TaskCategory.STUDY_CONCEPT)
        task.deadline_slot = data.get('deadline_slot', WEEK_SLOTS)
        task.is_locked = data.get('is_locked', False)
        
        title = data.get('title', '')
        task.title = title.encode('utf-8')[:MAX_TITLE_LEN-1]
        
        subject = data.get('subject', '')
        task.subject = subject.encode('utf-8')[:MAX_SUBJECT_LEN-1]
        
        task.preferred_slot = data.get('preferred_slot', -1)
        task.assigned_slot = data.get('assigned_slot', -1)
        
        return task


class OptimizationConfig(Structure):
    """
    Matches C OptimizationConfig struct.
    Contains scheduling constraints and heuristic parameters.
    """
    _fields_ = [
        ("sleep_start_slot", c_int),
        ("sleep_end_slot", c_int),
        ("concept_peak_start", c_int),
        ("concept_peak_end", c_int),
        ("practice_peak_start", c_int),
        ("practice_peak_end", c_int),
        ("deep_work_min_slots", c_int),
        ("micro_gap_max_slots", c_int),
        ("enable_heuristics", c_bool),
    ]
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'OptimizationConfig':
        """Create from Python dictionary."""
        config = cls()
        config.sleep_start_slot = data.get('sleep_start_slot', 46)
        config.sleep_end_slot = data.get('sleep_end_slot', 12)
        config.concept_peak_start = data.get('concept_peak_start', 16)
        config.concept_peak_end = data.get('concept_peak_end', 24)
        config.practice_peak_start = data.get('practice_peak_start', 32)
        config.practice_peak_end = data.get('practice_peak_end', 40)
        config.deep_work_min_slots = data.get('deep_work_min_slots', 3)
        config.micro_gap_max_slots = data.get('micro_gap_max_slots', 1)
        config.enable_heuristics = data.get('enable_heuristics', True)
        return config


class WeeklyTimeline(Structure):
    """
    Matches C WeeklyTimeline struct.
    Represents the optimized weekly schedule.
    """
    _fields_ = [
        ("slots", c_int * WEEK_SLOTS),  # Task ID in each slot (-1 = empty)
        ("slot_count", c_int),
        ("tasks", POINTER(TimelineTask)),
        ("task_count", c_int),
        ("optimization_status", c_int),  # 0=success, -1=unsolvable, -2=timeout
        ("error_code", c_int),
        ("total_gaps_filled", c_int),
        ("total_conflicts", c_int),
    ]


class ScheduleGap(Structure):
    """Gap in the schedule that can be filled."""
    _fields_ = [
        ("start_slot", c_int),
        ("end_slot", c_int),
        ("duration_slots", c_int),
        ("day_index", c_int),
        ("gap_type", c_int),  # 0=micro, 1=standard, 2=deep_work
    ]


# ============================================
# OPTIMIZATION RESULT
# ============================================

@dataclass
class OptimizationResult:
    """Result of timeline optimization."""
    success: bool
    status_code: int
    status_message: str
    slots: List[int]
    tasks: List[Dict[str, Any]]
    gaps_filled: int
    conflicts: int
    execution_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "status_code": self.status_code,
            "status_message": self.status_message,
            "slots": self.slots,
            "tasks": self.tasks,
            "gaps_filled": self.gaps_filled,
            "conflicts": self.conflicts,
            "execution_time_ms": self.execution_time_ms,
        }


# ============================================
# SCHEDULER ENGINE
# ============================================

class SchedulerEngine:
    """
    Python wrapper for the C optimization engine.
    
    Provides high-level interface for:
    - Timeline optimization using constraint satisfaction
    - Gap detection and micro-task filling
    - Schedule validation
    
    Usage:
        engine = SchedulerEngine()
        result = engine.optimize_timeline(tasks, config)
        if result.success:
            print(f"Optimized {len(result.tasks)} tasks")
    """
    
    def __init__(self, library_path: Optional[str] = None):
        """
        Initialize the scheduler engine.
        
        Args:
            library_path: Path to shared library (.dll/.so)
                         Auto-detected if not provided
        """
        self._lib: Optional[ctypes.CDLL] = None
        self._is_loaded = False
        
        if library_path:
            self._library_path = Path(library_path)
        else:
            self._library_path = self._find_library()
        
        self._load_library()
    
    def _find_library(self) -> Path:
        """Find the scheduler engine shared library."""
        config = get_engine_config()
        engine_dir = Path(__file__).parent.parent / config.engine_path
        
        if os.name == 'nt':
            lib_name = f"{config.shared_library_name}.dll"
        else:
            lib_name = f"lib{config.shared_library_name}.so"
        
        lib_path = engine_dir / lib_name
        
        # Also check without 'lib' prefix on Linux
        if not lib_path.exists() and os.name != 'nt':
            lib_path = engine_dir / f"{config.shared_library_name}.so"
        
        return lib_path
    
    def _load_library(self):
        """Load the shared library and configure function signatures."""
        if not self._library_path.exists():
            logger.warning(f"C engine library not found at {self._library_path}")
            logger.info("Falling back to Python-only optimization")
            self._is_loaded = False
            return
        
        try:
            self._lib = ctypes.CDLL(str(self._library_path))
            self._setup_functions()
            self._is_loaded = True
            logger.info(f"Loaded C engine from {self._library_path}")
        except OSError as e:
            logger.error(f"Failed to load C engine: {e}")
            self._is_loaded = False
    
    def _setup_functions(self):
        """Configure C function signatures."""
        if not self._lib:
            return
        
        # optimize_timeline
        self._lib.optimize_timeline.argtypes = [
            POINTER(TimelineTask),
            c_int,
            POINTER(OptimizationConfig)
        ]
        self._lib.optimize_timeline.restype = POINTER(WeeklyTimeline)
        
        # free_timeline_memory
        self._lib.free_timeline_memory.argtypes = [POINTER(WeeklyTimeline)]
        self._lib.free_timeline_memory.restype = None
        
        # validate_constraints
        self._lib.validate_constraints.argtypes = [POINTER(WeeklyTimeline)]
        self._lib.validate_constraints.restype = c_int
        
        # find_gaps
        if hasattr(self._lib, 'find_gaps'):
            self._lib.find_gaps.argtypes = [
                POINTER(WeeklyTimeline),
                POINTER(ScheduleGap),
                c_int
            ]
            self._lib.find_gaps.restype = c_int
    
    @property
    def is_available(self) -> bool:
        """Check if C engine is available."""
        return self._is_loaded and self._lib is not None
    
    def optimize_timeline(
        self,
        tasks: List[Dict[str, Any]],
        config: Optional[Dict[str, int]] = None
    ) -> OptimizationResult:
        """
        Optimize a weekly timeline using the C engine.
        
        Args:
            tasks: List of task dictionaries with:
                   - id, duration_slots, priority, category
                   - deadline_slot, is_locked, title, subject
            config: Optimization configuration (uses defaults if None)
            
        Returns:
            OptimizationResult with optimized schedule
        """
        import time
        start_time = time.time()
        
        if not self.is_available:
            # Fall back to Python optimization
            return self._python_optimize(tasks, config)
        
        # Prepare configuration
        if config is None:
            schedule_cfg = get_schedule_config()
            config = get_optimization_config(schedule_cfg)
        
        opt_config = OptimizationConfig.from_dict(config)
        
        # Convert tasks to C structures
        task_count = min(len(tasks), MAX_TASKS)
        task_array = (TimelineTask * task_count)()
        
        for i, task in enumerate(tasks[:task_count]):
            task_array[i] = TimelineTask.from_dict(task)
        
        # Call C function
        try:
            timeline_ptr = self._lib.optimize_timeline(
                task_array,
                task_count,
                byref(opt_config)
            )
        except Exception as e:
            logger.error(f"C engine call failed: {e}")
            return OptimizationResult(
                success=False,
                status_code=-3,
                status_message=f"C engine error: {str(e)}",
                slots=[],
                tasks=[],
                gaps_filled=0,
                conflicts=0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        if not timeline_ptr:
            return OptimizationResult(
                success=False,
                status_code=-4,
                status_message="C engine returned null",
                slots=[],
                tasks=[],
                gaps_filled=0,
                conflicts=0,
                execution_time_ms=(time.time() - start_time) * 1000
            )
        
        try:
            timeline = timeline_ptr.contents
            
            # Extract results
            slots = list(timeline.slots[:WEEK_SLOTS])
            
            # Extract optimized tasks
            optimized_tasks = []
            for i in range(task_count):
                optimized_tasks.append(task_array[i].to_dict())
            
            # Determine status message
            status_messages = {
                0: "Optimization successful",
                -1: "Schedule unsolvable - too many tasks for available slots",
                -2: "Optimization timeout",
            }
            status_msg = status_messages.get(
                timeline.optimization_status,
                f"Unknown status: {timeline.optimization_status}"
            )
            
            result = OptimizationResult(
                success=timeline.optimization_status == 0,
                status_code=timeline.optimization_status,
                status_message=status_msg,
                slots=slots,
                tasks=optimized_tasks,
                gaps_filled=timeline.total_gaps_filled,
                conflicts=timeline.total_conflicts,
                execution_time_ms=(time.time() - start_time) * 1000
            )
            
            return result
            
        finally:
            # Always free C memory
            self._lib.free_timeline_memory(timeline_ptr)
    
    def _python_optimize(
        self,
        tasks: List[Dict[str, Any]],
        config: Optional[Dict[str, int]] = None
    ) -> OptimizationResult:
        """
        Pure Python fallback optimization.
        Uses a simple greedy algorithm instead of full CSP.
        """
        import time
        start_time = time.time()
        
        if config is None:
            schedule_cfg = get_schedule_config()
            config = get_optimization_config(schedule_cfg)
        
        # Initialize empty timeline
        slots = [-1] * WEEK_SLOTS
        
        # Mark sleep slots as blocked
        for day in range(7):
            day_offset = day * SLOTS_PER_DAY
            
            # Sleep slots
            sleep_start = config.get('sleep_start_slot', 46)
            sleep_end = config.get('sleep_end_slot', 12)
            
            # Handle overnight sleep
            if sleep_start > sleep_end:
                # Sleep from evening to morning
                for slot in range(sleep_start, SLOTS_PER_DAY):
                    idx = day_offset + slot
                    if idx < WEEK_SLOTS:
                        slots[idx] = -2  # Blocked for sleep
                
                next_day_offset = ((day + 1) % 7) * SLOTS_PER_DAY
                for slot in range(0, sleep_end):
                    idx = next_day_offset + slot
                    if idx < WEEK_SLOTS:
                        slots[idx] = -2  # Blocked for sleep
            else:
                for slot in range(sleep_start, sleep_end):
                    idx = day_offset + slot
                    if idx < WEEK_SLOTS:
                        slots[idx] = -2
        
        # Sort tasks by priority (descending) and deadline (ascending)
        sorted_tasks = sorted(
            enumerate(tasks),
            key=lambda x: (-x[1].get('priority', 5), x[1].get('deadline_slot', WEEK_SLOTS))
        )
        
        optimized_tasks = []
        gaps_filled = 0
        conflicts = 0
        
        for original_idx, task in sorted_tasks:
            task_copy = task.copy()
            duration = task.get('duration_slots', 2)
            category = task.get('category', TaskCategory.STUDY_CONCEPT)
            deadline = task.get('deadline_slot', WEEK_SLOTS)
            is_locked = task.get('is_locked', False)
            preferred = task.get('preferred_slot', -1)
            
            # Find best slot
            best_slot = -1
            
            if is_locked and preferred >= 0:
                # Locked tasks go to preferred slot
                best_slot = preferred
            else:
                # Find first available slot that fits
                best_slot = self._find_best_slot(
                    slots, duration, deadline, category, config
                )
            
            if best_slot >= 0:
                # Place task
                for i in range(duration):
                    if best_slot + i < WEEK_SLOTS:
                        if slots[best_slot + i] >= 0:
                            conflicts += 1
                        slots[best_slot + i] = task.get('id', original_idx)
                
                task_copy['assigned_slot'] = best_slot
                gaps_filled += 1
            else:
                task_copy['assigned_slot'] = -1
                conflicts += 1
            
            optimized_tasks.append(task_copy)
        
        # Restore original order
        optimized_tasks = sorted(optimized_tasks, key=lambda x: x.get('id', 0))
        
        success = conflicts == 0
        
        return OptimizationResult(
            success=success,
            status_code=0 if success else -1,
            status_message="Python optimization successful" if success else "Some tasks could not be placed",
            slots=slots,
            tasks=optimized_tasks,
            gaps_filled=gaps_filled,
            conflicts=conflicts,
            execution_time_ms=(time.time() - start_time) * 1000
        )
    
    def _find_best_slot(
        self,
        slots: List[int],
        duration: int,
        deadline: int,
        category: int,
        config: Dict[str, int]
    ) -> int:
        """Find the best slot for a task using heuristics."""
        concept_start = config.get('concept_peak_start', 16)
        concept_end = config.get('concept_peak_end', 24)
        practice_start = config.get('practice_peak_start', 32)
        practice_end = config.get('practice_peak_end', 40)
        
        # Determine preferred time range based on category
        if category == TaskCategory.STUDY_CONCEPT:
            preferred_ranges = [(concept_start, concept_end)]
        elif category == TaskCategory.STUDY_PRACTICE:
            preferred_ranges = [(practice_start, practice_end)]
        else:
            preferred_ranges = []
        
        # Try preferred ranges first
        for pref_start, pref_end in preferred_ranges:
            for day in range(7):
                day_offset = day * SLOTS_PER_DAY
                for slot in range(pref_start, min(pref_end, SLOTS_PER_DAY - duration + 1)):
                    abs_slot = day_offset + slot
                    if abs_slot + duration <= min(deadline, WEEK_SLOTS):
                        if self._can_place(slots, abs_slot, duration):
                            return abs_slot
        
        # Fall back to any available slot before deadline
        for abs_slot in range(min(deadline, WEEK_SLOTS) - duration + 1):
            if abs_slot + duration <= WEEK_SLOTS:
                if self._can_place(slots, abs_slot, duration):
                    return abs_slot
        
        return -1
    
    def _can_place(self, slots: List[int], start: int, duration: int) -> bool:
        """Check if a task can be placed at the given slot."""
        for i in range(duration):
            if start + i >= WEEK_SLOTS:
                return False
            if slots[start + i] != -1:  # Slot is occupied
                return False
        return True
    
    def find_gaps(
        self,
        slots: List[int],
        min_duration: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Find gaps in the timeline.
        
        Args:
            slots: Current slot assignments
            min_duration: Minimum gap duration in slots
            
        Returns:
            List of gap dictionaries
        """
        gaps = []
        gap_start = None
        
        for i, slot_value in enumerate(slots):
            if slot_value == -1:  # Empty slot
                if gap_start is None:
                    gap_start = i
            else:
                if gap_start is not None:
                    duration = i - gap_start
                    if duration >= min_duration:
                        day_index = gap_start // SLOTS_PER_DAY
                        
                        # Classify gap type
                        if duration <= 1:
                            gap_type = "micro"
                        elif duration <= 4:
                            gap_type = "standard"
                        else:
                            gap_type = "deep_work"
                        
                        gaps.append({
                            "start_slot": gap_start,
                            "end_slot": i,
                            "duration_slots": duration,
                            "day_index": day_index,
                            "gap_type": gap_type,
                            "start_time": self._slot_to_time_str(gap_start % SLOTS_PER_DAY),
                            "end_time": self._slot_to_time_str(i % SLOTS_PER_DAY),
                        })
                    gap_start = None
        
        # Check final gap
        if gap_start is not None:
            duration = WEEK_SLOTS - gap_start
            if duration >= min_duration:
                day_index = gap_start // SLOTS_PER_DAY
                gap_type = "micro" if duration <= 1 else ("standard" if duration <= 4 else "deep_work")
                gaps.append({
                    "start_slot": gap_start,
                    "end_slot": WEEK_SLOTS,
                    "duration_slots": duration,
                    "day_index": day_index,
                    "gap_type": gap_type,
                    "start_time": self._slot_to_time_str(gap_start % SLOTS_PER_DAY),
                    "end_time": "24:00",
                })
        
        return gaps
    
    def _slot_to_time_str(self, slot: int) -> str:
        """Convert slot index to time string."""
        hour = slot // 2
        minute = 30 if slot % 2 else 0
        return f"{hour:02d}:{minute:02d}"
    
    def validate(self, slots: List[int], tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a timeline meets all constraints.
        
        Returns:
            Validation result with any violations
        """
        violations = []
        
        # Check for overlaps
        for i, task in enumerate(tasks):
            assigned = task.get('assigned_slot', -1)
            duration = task.get('duration_slots', 2)
            
            if assigned < 0:
                continue
            
            for j in range(duration):
                slot_idx = assigned + j
                if slot_idx >= WEEK_SLOTS:
                    violations.append({
                        "type": "out_of_bounds",
                        "task_id": task.get('id', i),
                        "slot": slot_idx
                    })
                elif slots[slot_idx] != task.get('id', i):
                    violations.append({
                        "type": "overlap",
                        "task_id": task.get('id', i),
                        "slot": slot_idx
                    })
        
        # Check deadlines
        for task in tasks:
            assigned = task.get('assigned_slot', -1)
            deadline = task.get('deadline_slot', WEEK_SLOTS)
            duration = task.get('duration_slots', 2)
            
            if assigned >= 0 and assigned + duration > deadline:
                violations.append({
                    "type": "deadline_violation",
                    "task_id": task.get('id'),
                    "assigned_end": assigned + duration,
                    "deadline": deadline
                })
        
        return {
            "valid": len(violations) == 0,
            "violations": violations
        }


# ============================================
# SINGLETON INSTANCE
# ============================================

_engine: Optional[SchedulerEngine] = None


def get_scheduler_engine() -> SchedulerEngine:
    """Get or create the scheduler engine singleton."""
    global _engine
    if _engine is None:
        _engine = SchedulerEngine()
    return _engine


def reset_scheduler_engine():
    """Reset the scheduler engine singleton."""
    global _engine
    _engine = None
