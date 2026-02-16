# ─── Settings & Task Persistence ─────────────────────────────────────────────
# Handles loading/saving of application settings and task lists to JSON files.

import json
import os

from src.gui_constants import DEFAULT_SETTINGS, SETTINGS_FILE


def load_settings() -> dict:
    """Load application settings from disk, merging with defaults."""
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULT_SETTINGS, **data}
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    """Persist application settings to disk."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass
