import json
import os
from typing import Dict, Any

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "api_key": "",
    "characters": {}
}

class DataManager:
    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """Loads settings from the JSON file. Creates it if it doesn't exist."""
        if not os.path.exists(SETTINGS_FILE):
            DataManager.save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Fallback if file is corrupted
            return DEFAULT_SETTINGS.copy()

    @staticmethod
    def save_settings(settings: Dict[str, Any]):
        """Saves settings to the JSON file."""
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_api_key() -> str:
        return DataManager.load_settings().get("api_key", "")

    @staticmethod
    def save_api_key(api_key: str):
        settings = DataManager.load_settings()
        settings["api_key"] = api_key
        DataManager.save_settings(settings)

    @staticmethod
    def get_characters() -> Dict[str, Dict[str, str]]:
        return DataManager.load_settings().get("characters", {})

    @staticmethod
    def add_or_update_character(name: str, voice: str, style: str):
        settings = DataManager.load_settings()
        settings["characters"][name] = {
            "voice": voice,
            "style": style
        }
        DataManager.save_settings(settings)

    @staticmethod
    def delete_character(name: str):
        settings = DataManager.load_settings()
        if name in settings["characters"]:
            del settings["characters"][name]
            DataManager.save_settings(settings)
