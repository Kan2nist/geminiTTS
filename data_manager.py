import json
import os
import copy
from typing import Dict, Any

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "api_key": "",
    "characters": {},
    # Default model configuration
    "models": ["gemini-2.5-pro-preview-tts"],
    "active_model": "gemini-2.5-pro-preview-tts",
    "model_limits": {
        "gemini-2.5-pro-preview-tts": {
            "requests_per_minute": 10,
            "requests_per_day": 50
        }
    }
}

class DataManager:
    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """Loads settings from the JSON file. Creates it if it doesn't exist."""
        if not os.path.exists(SETTINGS_FILE):
            DataManager.save_settings(DEFAULT_SETTINGS)
            return copy.deepcopy(DEFAULT_SETTINGS)

        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)

                # Migration: If old flat limits exist but no model_limits, migrate them
                if "model_limits" not in settings:
                    old_min = settings.pop("requests_per_minute", 10)
                    old_day = settings.pop("requests_per_day", 50)

                    # Ensure models list exists
                    if "models" not in settings:
                        settings["models"] = copy.deepcopy(DEFAULT_SETTINGS["models"])

                    if "active_model" not in settings:
                        settings["active_model"] = DEFAULT_SETTINGS["active_model"]

                    # Assign old limits to the default/first model
                    default_model = settings["models"][0]
                    settings["model_limits"] = {
                        default_model: {
                            "requests_per_minute": old_min,
                            "requests_per_day": old_day
                        }
                    }

                # Ensure all default keys exist (shallow check)
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value

                return settings
        except (json.JSONDecodeError, IOError):
            # Fallback if file is corrupted
            return copy.deepcopy(DEFAULT_SETTINGS)

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
    def get_models() -> list[str]:
        return DataManager.load_settings().get("models", [])

    @staticmethod
    def add_model(model_name: str):
        settings = DataManager.load_settings()
        if model_name not in settings["models"]:
            settings["models"].append(model_name)
            # Initialize limits for new model with defaults
            if model_name not in settings["model_limits"]:
                settings["model_limits"][model_name] = {
                    "requests_per_minute": 10,
                    "requests_per_day": 50
                }
            DataManager.save_settings(settings)

    @staticmethod
    def delete_model(model_name: str):
        settings = DataManager.load_settings()
        if model_name in settings["models"]:
            settings["models"].remove(model_name)
            if model_name in settings["model_limits"]:
                del settings["model_limits"][model_name]

            # If active model was deleted, switch to the last one or fallback
            if settings["active_model"] == model_name:
                if settings["models"]:
                    settings["active_model"] = settings["models"][-1]
                else:
                    # Fallback as requested
                    fallback = "gemini-2.5-pro-tts"
                    settings["models"] = [fallback]
                    settings["active_model"] = fallback
                    settings["model_limits"][fallback] = {"requests_per_minute": 10, "requests_per_day": 50}

            DataManager.save_settings(settings)

    @staticmethod
    def get_active_model() -> str:
        settings = DataManager.load_settings()
        active = settings.get("active_model", "")
        # Verification: if active model is not in models list (e.g. somehow out of sync), fix it
        models = settings.get("models", [])
        if active not in models and models:
             active = models[0]
             DataManager.set_active_model(active)
        elif not models:
             # Should practically not happen due to load/delete logic, but safe fallback
             return "gemini-2.5-pro-preview-tts"
        return active

    @staticmethod
    def set_active_model(model_name: str):
        settings = DataManager.load_settings()
        if model_name in settings["models"]:
            settings["active_model"] = model_name
            DataManager.save_settings(settings)

    @staticmethod
    def get_limits(model_name: str = None) -> tuple[int, int]:
        settings = DataManager.load_settings()
        if model_name is None:
            model_name = settings.get("active_model")

        model_limits = settings.get("model_limits", {}).get(model_name, {})
        return (
            model_limits.get("requests_per_minute", 10),
            model_limits.get("requests_per_day", 50)
        )

    @staticmethod
    def save_limits(per_minute: int, per_day: int, model_name: str = None):
        settings = DataManager.load_settings()
        if model_name is None:
            model_name = settings.get("active_model")

        if "model_limits" not in settings:
            settings["model_limits"] = {}

        if model_name not in settings["model_limits"]:
             settings["model_limits"][model_name] = {}

        settings["model_limits"][model_name]["requests_per_minute"] = per_minute
        settings["model_limits"][model_name]["requests_per_day"] = per_day
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
