# ─── Theme & Styling ─────────────────────────────────────────────────────────
# Centralizes all visual styling: colors, status mappings, and the global
# dark stylesheet. Inline styles that were scattered across gui.py and
# gui_dialogs.py are now exposed as reusable helper functions.
#
# 2026 "Dark Minimal" redesign — GitHub Dark / Discord / Spotify inspired.

# ─── Color palette ───────────────────────────────────────────────────────────

ACCENT = "#58a6ff"
ACCENT_HOVER = "#79c0ff"
ACCENT_MUTED = "rgba(88, 166, 255, 0.10)"
BG_DEEP = "#0d1117"
BG_CARD = "#161b22"
BG_INPUT = "#21262d"
BG_BORDER = "#30363d"
BG_BORDER_HOVER = "#484f58"
BORDER_INPUT = "#30363d"
BORDER_HOVER = "#484f58"
TEXT_PRIMARY = "#e6edf3"
TEXT_SECONDARY = "#c9d1d9"
TEXT_MUTED = "#8b949e"
TEXT_DIM = "#484f58"
TEXT_FAINT = "#30363d"
TEXT_DISABLED = "#484f58"
CHAT_COMMENT_COLOR = "#79c0ff"
CHAT_GIFT_COLOR = "#f0883e"
CHAT_JOIN_COLOR = "#56d364"
CHAT_CONTENT_COLOR = "#c9d1d9"
SPEED_INDICATOR_COLOR = "#58a6ff"

# ─── Status helpers ──────────────────────────────────────────────────────────

STATUS_COLORS: dict[str, tuple[str, str]] = {
    "idle": (BG_INPUT, "#8b949e"),
    "checking": ("rgba(88, 166, 255, 0.10)", "#58a6ff"),
    "monitoring": ("rgba(188, 140, 255, 0.10)", "#bc8cff"),
    "recording": ("rgba(86, 211, 100, 0.10)", "#56d364"),
    "encoding": ("rgba(219, 171, 9, 0.10)", "#dbab09"),
    "done": ("rgba(63, 185, 80, 0.10)", "#3fb950"),
    "error": ("rgba(248, 81, 73, 0.10)", "#f85149"),
}

STATUS_DOTS: dict[str, str] = {
    "idle": "\u25cb",  # empty circle
    "checking": "\u25d4",  # quarter circle
    "monitoring": "\u25ce",  # bullseye
    "recording": "\u25cf",  # filled circle
    "encoding": "\u25d0",  # left half
    "done": "\u2713",  # checkmark
    "error": "\u2717",  # x mark
}

ACTIVE_STATUSES = {"recording", "encoding", "checking"}
WAITING_STATUSES = {"monitoring", "idle"}
STOPPED_STATUSES = {"done", "error"}

PROGRESS_COLORS: dict[str, str] = {
    "recording": "#56d364",
    "monitoring": "#bc8cff",
    "checking": "#58a6ff",
    "encoding": "#dbab09",
}

# ─── Inline style helpers ────────────────────────────────────────────────────
# These replace hardcoded style strings that were duplicated across modules.


def status_badge_style(bg: str, fg: str) -> str:
    """Dynamic style for the status badge on a TaskCard."""
    return (
        f"background-color: {bg}; color: {fg}; "
        f"font-size: 11px; font-weight: 600; padding: 4px 14px; "
        f"border-radius: 12px; letter-spacing: 0.5px;"
    )


def progress_bar_style(color: str) -> str:
    """Dynamic style for a TaskCard progress bar chunk color."""
    return (
        f"QProgressBar {{ background-color: {BG_INPUT}; border-radius: 3px; }}"
        f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
    )


def info_status_style(fg: str) -> str:
    """Dynamic style for the info panel status value."""
    return f"color: {fg}; font-size: 12px; font-weight: 600;"


STAT_LABEL_STYLE = f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 500;"
INFO_KEY_STYLE = f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 600;"
INFO_VALUE_STYLE = f"color: {TEXT_SECONDARY}; font-size: 12px;"
USERNAME_STYLE = f"font-size: 18px; font-weight: 700; color: {TEXT_PRIMARY}; letter-spacing: -0.3px;"
PREVIEW_TITLE_STYLE = f"font-size: 12px; font-weight: 600; color: {TEXT_MUTED};"
PREVIEW_LABEL_STYLE = (
    f"QLabel {{ background-color: #010409; border: 1px solid {BORDER_INPUT}; "
    f"border-radius: 8px; color: {TEXT_DISABLED}; font-size: 12px; }}"
)
VOLUME_LABEL_STYLE = f"color: {TEXT_MUTED}; font-size: 11px; min-width: 32px;"
TOGGLE_PREVIEW_STYLE = "QPushButton { padding: 2px 8px; font-size: 11px; }"
DETAIL_TABS_PANE_STYLE = (
    f"QTabWidget::pane {{ border: 1px solid {BG_BORDER}; border-radius: 8px; "
    f"background-color: {BG_DEEP}; padding: 8px; }}"
)
SPLITTER_HANDLE_STYLE = f"QSplitter::handle {{ background-color: {BG_BORDER}; border-radius: 2px; }}"
TITLEBAR_STYLE = f"background-color: {BG_CARD}; border-bottom: 1px solid {BG_BORDER};"
LOGO_STYLE = f"color: {ACCENT}; font-size: 20px; padding: 2px 6px; margin-right: 4px;"
APP_TITLE_STYLE = f"font-size: 15px; font-weight: 600; color: {TEXT_PRIMARY}; letter-spacing: -0.2px;"
VERSION_CHIP_STYLE = (
    f"font-size: 10px; font-weight: 600; color: {TEXT_MUTED}; "
    f"background-color: {BG_INPUT}; border-radius: 10px; "
    f"padding: 2px 8px; margin-left: 8px;"
)
GLOBAL_SPEED_STYLE = (
    f"color: {SPEED_INDICATOR_COLOR}; font-size: 11px; font-weight: 600; "
    f"background-color: {ACCENT_MUTED}; "
    f"border-radius: 10px; padding: 4px 12px; margin-right: 8px;"
)
SIDEBAR_BODY_STYLE = f"QSplitter::handle {{ background-color: {BG_BORDER}; }}"
TASK_HEADER_LABEL_STYLE = (
    f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; padding-top: 6px;"
)
TASK_COUNT_STYLE = (
    f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 700; "
    f"background-color: {BG_INPUT}; border-radius: 10px; "
    f"padding: 2px 8px; margin-top: 4px;"
)
SEARCH_INPUT_STYLE = (
    f"QLineEdit {{ background-color: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; "
    f"border-radius: 8px; padding: 6px 12px; font-size: 12px; color: {TEXT_SECONDARY}; }}"
    f"QLineEdit:focus {{ border: 1px solid {ACCENT}; }}"
)
SEPARATOR_STYLE = f"background-color: {BG_BORDER}; max-height: 1px;"
SCROLL_AREA_TRANSPARENT = f"QScrollArea {{ border: none; background-color: {BG_DEEP}; }}"
SCROLL_AREA_BORDERLESS = "QScrollArea { border: none; }"
CONTENT_BG_STYLE = f"background-color: {BG_DEEP};"
EMPTY_CIRCLE_STYLE = (
    f"font-size: 36px; color: {ACCENT}; background-color: {ACCENT_MUTED}; border-radius: 40px; padding: 20px;"
)
EMPTY_TEXT_STYLE = f"font-size: 18px; font-weight: 600; color: {TEXT_SECONDARY};"
EMPTY_SUB_STYLE = f"font-size: 13px; color: {TEXT_MUTED};"
FORM_LABEL_STYLE = f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 600;"
DIALOG_BUTTON_BAR_STYLE = f"background-color: {BG_CARD}; border-top: 1px solid {BG_BORDER};"
DIALOG_HEADER_STYLE = f"background-color: {BG_CARD}; border-bottom: 1px solid {BG_BORDER};"
DIALOG_HEADER_TITLE_STYLE = f"font-size: 16px; font-weight: 600; color: {TEXT_PRIMARY};"
SECONDARY_BUTTON_STYLE = (
    f"QPushButton {{ background-color: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; "
    f"border-radius: 8px; padding: 8px 16px; color: {TEXT_SECONDARY}; font-weight: 500; }}"
    f"QPushButton:hover {{ background-color: #30363d; border-color: {BORDER_HOVER}; }}"
)
SAVE_BUTTON_STYLE = (
    f"QPushButton {{ background-color: {ACCENT}; border: none; border-radius: 8px; "
    f"padding: 8px 24px; color: #ffffff; font-weight: 600; }}"
    f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
)
VALIDATION_ERROR_STYLE = (
    f"QLineEdit {{ border: 1px solid #f85149; background-color: {BG_INPUT}; "
    f"border-radius: 8px; padding: 8px 12px; color: {TEXT_SECONDARY}; }}"
)

# ─── Log entry formatting ────────────────────────────────────────────────────


def format_log_html(timestamp: str, text: str) -> str:
    """Format a log/encoding entry as HTML."""
    return f'<span style="color:{TEXT_DIM};">[{timestamp}]</span> <span style="color:{TEXT_MUTED};">{text}</span>'


def format_chat_html(prefix: str, color: str, nickname: str, content: str) -> str:
    """Format a chat message as HTML."""
    return (
        f'<span style="color:{color};">{prefix} <b>{nickname}</b></span> '
        f'<span style="color:{CHAT_CONTENT_COLOR};">{content}</span>'
    )


# ─── Dark Theme ──────────────────────────────────────────────────────────────

DARK_STYLESHEET = """
/* ── Base ─────────────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #0d1117;
}
QWidget {
    color: #c9d1d9;
    font-family: 'Inter', 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
    font-size: 13px;
}
QLabel#title {
    font-size: 20px;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: -0.3px;
}
QLabel#subtitle {
    font-size: 11px;
    color: #8b949e;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #c9d1d9;
    padding: 4px 0;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #161b22;
    border-right: 1px solid #30363d;
}
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    background-color: transparent;
    border-radius: 8px;
    border-left: 3px solid transparent;
    padding: 8px 12px;
    margin: 2px 4px;
    color: #8b949e;
    font-weight: 500;
}
QListWidget::item:selected {
    background-color: rgba(88, 166, 255, 0.08);
    border-left: 3px solid #58a6ff;
    color: #e6edf3;
}
QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.04);
    color: #c9d1d9;
}

/* ── Cards ────────────────────────────────────────────────────────────── */
QFrame#card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
}
QFrame#card:hover {
    border: 1px solid #484f58;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #c9d1d9;
    min-height: 20px;
    selection-background-color: #58a6ff;
    selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #58a6ff;
    background-color: #0d1117;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    selection-background-color: rgba(88, 166, 255, 0.15);
    selection-color: #e6edf3;
    color: #c9d1d9;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border-radius: 4px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    color: #c9d1d9;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #484f58;
}
QPushButton:pressed {
    background-color: #484f58;
}
QPushButton:disabled {
    background-color: #161b22;
    border-color: #21262d;
    color: #484f58;
}
QPushButton#accent {
    background-color: #238636;
    border: 1px solid rgba(240, 246, 252, 0.1);
    color: #ffffff;
    font-weight: 600;
    padding: 10px 22px;
    border-radius: 6px;
    letter-spacing: 0.2px;
}
QPushButton#accent:hover {
    background-color: #2ea043;
}
QPushButton#accent:pressed {
    background-color: #238636;
}
QPushButton#accent:disabled {
    background-color: #21262d;
    border-color: #30363d;
    color: #484f58;
}
QPushButton#danger {
    background-color: transparent;
    border: 1px solid #f85149;
    color: #f85149;
    font-weight: 600;
}
QPushButton#danger:hover {
    background-color: rgba(248, 81, 73, 0.10);
    border-color: #f85149;
}
QPushButton#danger:pressed {
    background-color: rgba(248, 81, 73, 0.20);
}
QPushButton#ghost {
    background-color: transparent;
    border: none;
    color: #8b949e;
    font-weight: 500;
}
QPushButton#ghost:hover {
    color: #c9d1d9;
    background-color: rgba(255, 255, 255, 0.04);
    border-radius: 6px;
}
QPushButton#filterBtn {
    background-color: transparent;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    color: #8b949e;
}
QPushButton#filterBtn:hover {
    background-color: rgba(255, 255, 255, 0.04);
    border-color: #484f58;
    color: #c9d1d9;
}
QPushButton#filterBtnActive {
    background-color: rgba(88, 166, 255, 0.10);
    border: 1px solid #58a6ff;
    border-radius: 14px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: 600;
    color: #58a6ff;
}
QPushButton#iconBtn {
    background-color: transparent;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    font-size: 14px;
    color: #8b949e;
}
QPushButton#iconBtn:hover {
    background-color: rgba(255, 255, 255, 0.06);
    border-color: #484f58;
    color: #e6edf3;
}

/* ── Chat feed ────────────────────────────────────────────────────────── */
QTextEdit#chatFeed {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px;
    color: #c9d1d9;
    font-size: 12px;
    font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
    line-height: 1.5;
}

/* ── Checkbox ─────────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #c9d1d9;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 4px;
    border: 2px solid #484f58;
    background-color: #0d1117;
}
QCheckBox::indicator:hover {
    border-color: #58a6ff;
}
QCheckBox::indicator:checked {
    background-color: #58a6ff;
    border-color: #58a6ff;
    image: none;
}

/* ── Scrollbars ───────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #484f58;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    height: 0;
}

/* ── Status badge ─────────────────────────────────────────────────────── */
QLabel#statusBadge {
    font-size: 11px;
    font-weight: 600;
    padding: 4px 14px;
    border-radius: 12px;
    letter-spacing: 0.5px;
}

/* ── Progress bar ─────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 3px;
    height: 4px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 3px;
}

/* ── Tooltip ──────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1b1f23;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Slider ───────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background: #21262d;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #58a6ff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #79c0ff;
}
QSlider::sub-page:horizontal {
    background: #58a6ff;
    border-radius: 2px;
}

/* ── Tab Widget ───────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background-color: #0d1117;
}
QTabBar::tab {
    background-color: transparent;
    color: #8b949e;
    padding: 10px 18px;
    font-weight: 600;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #e6edf3;
    border-bottom: 2px solid #58a6ff;
}
QTabBar::tab:hover {
    color: #c9d1d9;
}
"""
