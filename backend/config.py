"""
AI Engineering Study Assistant - Configuration Management
Supports .env files and runtime configuration for AI, scheduling, and subject priorities.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


# ============================================
# AI / LLM CONFIGURATION
# ============================================

class AIConfig(BaseSettings):
    """
    AI/LLM Configuration.
    Supports OpenAI, Ollama, and any OpenAI-compatible API.
    """
    api_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for OpenAI-compatible API (e.g., OpenAI, Ollama, local LLMs)"
    )
    api_key: str = Field(
        default="",
        description="API key for the LLM provider"
    )
    model_name: str = Field(
        default="gpt-4",
        description="Model name to use for chat completions"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for AI responses"
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Maximum tokens in AI responses"
    )
    
    model_config = {
        "env_prefix": "AI_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# ============================================
# SCHEDULE CONFIGURATION
# ============================================

class ScheduleConfig(BaseSettings):
    """Schedule and daily routine configuration."""
    
    # Sleep settings
    sleep_start_hour: int = Field(
        default=23,
        ge=0,
        le=23,
        description="Hour when sleep begins (24-hour format)"
    )
    sleep_start_minute: int = Field(
        default=0,
        ge=0,
        le=59,
        description="Minute when sleep begins"
    )
    sleep_duration_hours: float = Field(
        default=7.0,
        ge=4.0,
        le=12.0,
        description="Total sleep duration in hours"
    )
    
    # Energy peak periods (for heuristic scheduling)
    concept_peak_start_hour: int = Field(
        default=8,
        ge=0,
        le=23,
        description="Start hour for concept/theory study peak"
    )
    concept_peak_end_hour: int = Field(
        default=12,
        ge=0,
        le=23,
        description="End hour for concept/theory study peak"
    )
    practice_peak_start_hour: int = Field(
        default=16,
        ge=0,
        le=23,
        description="Start hour for practice/problem-solving peak"
    )
    practice_peak_end_hour: int = Field(
        default=20,
        ge=0,
        le=23,
        description="End hour for practice/problem-solving peak"
    )
    
    # Task configuration
    deep_work_min_minutes: int = Field(
        default=90,
        ge=30,
        le=180,
        description="Minimum duration for deep work blocks"
    )
    micro_gap_max_minutes: int = Field(
        default=30,
        ge=10,
        le=60,
        description="Maximum duration for micro-gap tasks"
    )
    standard_block_minutes: int = Field(
        default=60,
        ge=30,
        le=120,
        description="Standard study block duration"
    )
    min_break_minutes: int = Field(
        default=15,
        ge=5,
        le=30,
        description="Minimum break duration after study blocks"
    )
    
    model_config = {
        "env_prefix": "SCHEDULE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# ============================================
# SUBJECT PRIORITY CONFIGURATION
# ============================================

class SubjectConfig(BaseSettings):
    """Subject priority and categorization configuration."""
    
    # Default priorities (1-10, higher = more important)
    default_priorities: Dict[str, int] = Field(
        default_factory=lambda: {
            "MATH101": 9,
            "PHYS102": 8,
            "COMP101": 7,
            "CHEM101": 6,
            "ENG101": 5,
        },
        description="Default subject priorities"
    )
    
    # Subject types: concept_heavy or practice_heavy
    subject_types: Dict[str, str] = Field(
        default_factory=lambda: {
            "MATH101": "practice_heavy",
            "PHYS102": "concept_heavy",
            "COMP101": "practice_heavy",
            "CHEM101": "concept_heavy",
            "ENG101": "concept_heavy",
        },
        description="Subject learning type classification"
    )
    
    model_config = {
        "env_prefix": "SUBJECT_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# ============================================
# ENGINE CONFIGURATION
# ============================================

class EngineConfig(BaseSettings):
    """C Engine path and configuration."""
    
    engine_path: str = Field(
        default="../engine",
        description="Path to the C engine directory"
    )
    shared_library_name: str = Field(
        default="scheduler_engine",
        description="Name of the shared library (without extension)"
    )
    enable_c_engine: bool = Field(
        default=True,
        description="Enable C engine optimization (falls back to Python if disabled)"
    )
    optimization_timeout_ms: int = Field(
        default=5000,
        ge=100,
        le=30000,
        description="Timeout for C engine optimization in milliseconds"
    )
    
    model_config = {
        "env_prefix": "ENGINE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_slot_from_time(hour: int, minute: int = 0) -> int:
    """
    Convert time to slot index (30-minute slots).
    
    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
        
    Returns:
        Slot index (0-47 for a single day)
    """
    return hour * 2 + (1 if minute >= 30 else 0)


def get_time_from_slot(slot: int) -> tuple[int, int]:
    """
    Convert slot index to time.
    
    Args:
        slot: Slot index
        
    Returns:
        Tuple of (hour, minute)
    """
    hour = (slot // 2) % 24
    minute = 30 if slot % 2 else 0
    return hour, minute


def get_optimization_config(schedule_config: ScheduleConfig) -> Dict[str, int]:
    """
    Get optimization configuration for C engine.
    
    Args:
        schedule_config: Schedule configuration instance
        
    Returns:
        Dictionary with slot-based configuration for C engine
    """
    sleep_end_hour = (
        schedule_config.sleep_start_hour + 
        int(schedule_config.sleep_duration_hours)
    ) % 24
    sleep_end_minute = int((schedule_config.sleep_duration_hours % 1) * 60)
    
    return {
        "sleep_start_slot": get_slot_from_time(
            schedule_config.sleep_start_hour,
            schedule_config.sleep_start_minute
        ),
        "sleep_end_slot": get_slot_from_time(sleep_end_hour, sleep_end_minute),
        "concept_peak_start": get_slot_from_time(schedule_config.concept_peak_start_hour),
        "concept_peak_end": get_slot_from_time(schedule_config.concept_peak_end_hour),
        "practice_peak_start": get_slot_from_time(schedule_config.practice_peak_start_hour),
        "practice_peak_end": get_slot_from_time(schedule_config.practice_peak_end_hour),
        "deep_work_min_slots": schedule_config.deep_work_min_minutes // 30,
        "micro_gap_max_slots": schedule_config.micro_gap_max_minutes // 30,
    }


# ============================================
# CACHED CONFIGURATION INSTANCES
# ============================================

@lru_cache()
def get_ai_config() -> AIConfig:
    """Get cached AI configuration instance."""
    return AIConfig()


@lru_cache()
def get_schedule_config() -> ScheduleConfig:
    """Get cached schedule configuration instance."""
    return ScheduleConfig()


@lru_cache()
def get_subject_config() -> SubjectConfig:
    """Get cached subject configuration instance."""
    return SubjectConfig()


@lru_cache()
def get_engine_config() -> EngineConfig:
    """Get cached engine configuration instance."""
    return EngineConfig()


def reload_config():
    """Clear configuration cache and reload from environment."""
    get_ai_config.cache_clear()
    get_schedule_config.cache_clear()
    get_subject_config.cache_clear()
    get_engine_config.cache_clear()


# ============================================
# CONFIGURATION SUMMARY
# ============================================

def get_config_summary() -> Dict[str, Any]:
    """
    Get a summary of all configuration values.
    Useful for debugging and settings display.
    """
    ai = get_ai_config()
    schedule = get_schedule_config()
    subject = get_subject_config()
    engine = get_engine_config()
    
    return {
        "ai": {
            "base_url": ai.api_base_url,
            "model": ai.model_name,
            "has_key": bool(ai.api_key),
            "temperature": ai.temperature,
            "max_tokens": ai.max_tokens,
        },
        "schedule": {
            "sleep_start": f"{schedule.sleep_start_hour:02d}:{schedule.sleep_start_minute:02d}",
            "sleep_duration": schedule.sleep_duration_hours,
            "concept_peak": f"{schedule.concept_peak_start_hour:02d}:00 - {schedule.concept_peak_end_hour:02d}:00",
            "practice_peak": f"{schedule.practice_peak_start_hour:02d}:00 - {schedule.practice_peak_end_hour:02d}:00",
            "deep_work_min": schedule.deep_work_min_minutes,
            "micro_gap_max": schedule.micro_gap_max_minutes,
        },
        "subjects": {
            "priorities": subject.default_priorities,
            "types": subject.subject_types,
        },
        "engine": {
            "path": engine.engine_path,
            "enabled": engine.enable_c_engine,
            "timeout_ms": engine.optimization_timeout_ms,
        },
    }
