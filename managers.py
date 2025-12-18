import json
import os
import shutil
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from data_manager import DataManager

USAGE_LOG_FILE = "usage_log.json"
HISTORY_FILE = "history.json"
HISTORY_CACHE_DIR = "history_cache"

class RateLimiter:
    @staticmethod
    def load_usage() -> Dict[str, List[float]]:
        """
        Loads request timestamps (unix epoch) from file.
        Returns a dict mapping model_name -> list of timestamps.
        If file contains a list (old format), it migrates it to the current active model or default.
        """
        if not os.path.exists(USAGE_LOG_FILE):
            return {}
        try:
            with open(USAGE_LOG_FILE, "r") as f:
                data = json.load(f)

            # Backward compatibility: if list, wrap it in a dict under the default model
            if isinstance(data, list):
                active_model = DataManager.get_active_model()
                return {active_model: data}

            if isinstance(data, dict):
                return data

            return {}
        except (json.JSONDecodeError, IOError):
            return {}

    @staticmethod
    def save_usage(usage_data: Dict[str, List[float]]):
        """Saves request timestamps map to file."""
        with open(USAGE_LOG_FILE, "w") as f:
            json.dump(usage_data, f)

    @staticmethod
    def check_limit(model_name: str = None) -> tuple[bool, str]:
        """
        Checks if the current request is within limits for the specified (or active) model.
        Returns (True, "") if allowed, (False, error_message) if blocked.
        """
        if model_name is None:
            model_name = DataManager.get_active_model()

        limit_min, limit_day = DataManager.get_limits(model_name)
        all_usage = RateLimiter.load_usage()
        timestamps = all_usage.get(model_name, [])
        now = time.time()

        # Filter timestamps
        last_minute = [t for t in timestamps if now - t < 60]
        last_day = [t for t in timestamps if now - t < 86400]

        if len(last_minute) >= limit_min:
            return False, f"Rate limit exceeded for {model_name}: Max {limit_min} requests per minute."

        if len(last_day) >= limit_day:
            return False, f"Rate limit exceeded for {model_name}: Max {limit_day} requests per day."

        return True, ""

    @staticmethod
    def log_request(model_name: str = None):
        """Logs a successful request timestamp for the specified model."""
        if model_name is None:
            model_name = DataManager.get_active_model()

        all_usage = RateLimiter.load_usage()
        if model_name not in all_usage:
            all_usage[model_name] = []

        timestamps = all_usage[model_name]
        now = time.time()
        timestamps.append(now)

        # Cleanup old logs (older than 24h)
        timestamps = [t for t in timestamps if now - t < 86400]
        all_usage[model_name] = timestamps

        RateLimiter.save_usage(all_usage)

    @staticmethod
    def get_usage_stats(model_name: str = None) -> dict[str, int]:
        """Returns current usage counts for the specified model."""
        if model_name is None:
            model_name = DataManager.get_active_model()

        all_usage = RateLimiter.load_usage()
        timestamps = all_usage.get(model_name, [])
        now = time.time()

        last_minute = [t for t in timestamps if now - t < 60]
        last_day = [t for t in timestamps if now - t < 86400]

        return {
            "used_min": len(last_minute),
            "used_day": len(last_day)
        }

    @staticmethod
    def clear_usage():
        """Clears all usage logs."""
        RateLimiter.save_usage({})

class HistoryManager:
    @staticmethod
    def ensure_cache_dir():
        if not os.path.exists(HISTORY_CACHE_DIR):
            os.makedirs(HISTORY_CACHE_DIR)

    @staticmethod
    def load_history() -> List[Dict[str, Any]]:
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def save_history(history: List[Dict[str, Any]]):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    @staticmethod
    def add_entry(char_name: str, text: str, voice: str, style: str, audio_source_path: str):
        """
        Adds an entry to history and copies audio file to cache.
        """
        HistoryManager.ensure_cache_dir()

        # Generate unique filename for cache
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Use simple hash or random part to ensure uniqueness if needed,
        # but timestamp + simple counter or just unique enough name is fine.
        # Let's use the basename of source plus timestamp to be safe.
        base_name = os.path.basename(audio_source_path)
        cache_filename = f"{timestamp_str}_{base_name}"
        cache_path = os.path.join(HISTORY_CACHE_DIR, cache_filename)

        # Copy file
        try:
            shutil.copy2(audio_source_path, cache_path)
        except IOError as e:
            print(f"Error copying to history cache: {e}")
            return

        # Create entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "char_name": char_name,
            "text": text,
            "voice": voice,
            "style": style,
            "audio_path": cache_path
        }

        history = HistoryManager.load_history()
        history.insert(0, entry) # Prepend to show newest first
        HistoryManager.save_history(history)

    @staticmethod
    def get_history() -> List[Dict[str, Any]]:
        return HistoryManager.load_history()

    @staticmethod
    def clear_history():
        """Clears the history list, deletes cached files, and clears usage logs."""
        # clear files
        if os.path.exists(HISTORY_CACHE_DIR):
            shutil.rmtree(HISTORY_CACHE_DIR)
            os.makedirs(HISTORY_CACHE_DIR)

        # clear json
        HistoryManager.save_history([])

        # clear usage logs
        RateLimiter.clear_usage()
