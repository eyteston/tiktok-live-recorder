# ─── Shared GUI Constants ────────────────────────────────────────────────────
# Centralizes magic numbers, labels, and UI configuration used across modules.

import os

# ─── File paths ──────────────────────────────────────────────────────────────

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKS_FILE = os.path.join(_PROJECT_ROOT, "tasks.json")
SETTINGS_FILE = os.path.join(_PROJECT_ROOT, "settings.json")

# ─── Default settings ────────────────────────────────────────────────────────

DEFAULT_SETTINGS: dict = {
    "default_session_id": "",
    "default_output_dir": "./recordings",
    "default_quality": "hd",
    "rate_limit_delay": 10,
    "default_no_overlay": True,
    "default_chat_font_size": 24,
    "default_chat_max_lines": 8,
    "default_chat_display_duration": 5.0,
    "default_chat_position": "bottom-left",
    "default_chat_opacity": 0.6,
    "default_chat_margin_x": 20,
    "default_chat_margin_y": 50,
    "default_include_gifts": True,
    "default_include_joins": True,
}

# ─── Layout constants ────────────────────────────────────────────────────────

SIDEBAR_WIDTH = 250
TITLEBAR_HEIGHT = 52
CARD_SPACING = 12
CARD_PADDING = 20
BUTTON_ICON_SIZE = 30

# ─── Feed limits (prevent unbounded memory growth) ───────────────────────────

CHAT_FEED_MAX_LINES = 500
LOG_FEED_MAX_LINES = 1000
ENCODE_FEED_MAX_LINES = 500

# ─── Timer intervals (ms) ───────────────────────────────────────────────────

DURATION_UPDATE_INTERVAL = 1000
FILE_SIZE_UPDATE_INTERVAL = 2000
GLOBAL_SPEED_UPDATE_INTERVAL = 2000

# ─── Info panel field definitions ────────────────────────────────────────────
# Each tuple is (display_label, attribute_name) — used to build the info grid.

INFO_PANEL_FIELDS: list[tuple[str, str]] = [
    ("Status:", "info_status"),
    ("Last Live:", "info_last_live"),
    ("Record Start:", "info_record_start"),
    ("Duration:", "info_duration"),
    ("Monitoring Time:", "info_monitoring_time"),
    ("Filename:", "info_filename"),
    ("File Size:", "info_file_size"),
    ("Download Speed:", "info_speed"),
    ("Chat Messages:", "info_chat_count"),
]

# ─── Quality options ─────────────────────────────────────────────────────────

QUALITY_OPTIONS = ["hd", "uhd", "sd", "ld", "origin"]

# ─── Chat position options ───────────────────────────────────────────────────

CHAT_POSITION_OPTIONS = ["bottom-left", "bottom-right", "top-left", "top-right"]
