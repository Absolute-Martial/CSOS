
import os
import dotenv
from typing import Dict, Any, List
from pathlib import Path
from logger import logger

ENV_PATH = Path(__file__).parent / ".env"

class SettingsManager:
    """Manages reading and writing of environment settings"""
    
    @staticmethod
    def get_all_settings() -> Dict[str, str]:
        """Read all settings from .env"""
        if not ENV_PATH.exists():
            logger.warning(f".env file not found at {ENV_PATH}")
            return {}
            
        return dotenv.dotenv_values(ENV_PATH)

    @staticmethod
    def update_setting(key: str, value: str) -> bool:
        """Update a specific setting in .env"""
        try:
            # Create .env if it doesn't exist
            if not ENV_PATH.exists():
                logger.info("Creating new .env file")
                with open(ENV_PATH, 'w') as f:
                    f.write("")
            
            dotenv.set_key(ENV_PATH, key, value)
            logger.info(f"Updated setting {key} = {value}")
            
            # Also update current environment for immediate effect (where possible)
            os.environ[key] = value
            
            return True
        except Exception as e:
            logger.error(f"Failed to update setting {key}: {str(e)}")
            return False

    @staticmethod
    def get_manageable_settings() -> List[Dict[str, Any]]:
        """Return a schema of settings that can be managed in UI"""
        current = SettingsManager.get_all_settings()
        
        return [
            {
                "category": "AI Configuration",
                "settings": [
                    {
                        "key": "AI_API_BASE_URL",
                        "label": "API Base URL",
                        "type": "text",
                        "value": current.get("AI_API_BASE_URL", "https://api.openai.com/v1"),
                        "description": "Endpoint for OpenAI-compatible API"
                    },
                    {
                        "key": "AI_API_KEY",
                        "label": "API Key",
                        "type": "password",
                        "value": current.get("AI_API_KEY", ""),
                        "description": "Your API Key"
                    },
                    {
                        "key": "AI_MODEL_NAME",
                        "label": "Model Name",
                        "type": "select",
                        "options": ["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet", "llama3"],
                        "value": current.get("AI_MODEL_NAME", "gpt-4"),
                        "description": "AI Model to use for reasoning"
                    }
                ]
            },
            {
                "category": "Schedule",
                "settings": [
                    {
                        "key": "SLEEP_START_HOUR",
                        "label": "Sleep Start Hour",
                        "type": "number",
                        "min": 0,
                        "max": 23,
                        "value": current.get("SLEEP_START_HOUR", "23"),
                        "description": "Hour to start sleep block (0-23)"
                    },
                    {
                        "key": "SLEEP_DURATION",
                        "label": "Sleep Duration (Hours)",
                        "type": "number",
                        "step": 0.5,
                        "value": current.get("SLEEP_DURATION", "7.0"),
                        "description": "Target sleep duration"
                    }
                ]
            }
        ]
