# ─── Theme & Styling ─────────────────────────────────────────────────────────
# Centralizes all visual styling: colors, status mappings, and the global
# dark stylesheet. Inline styles that were scattered across gui.py and
# gui_dialogs.py are now exposed as reusable helper functions.

# ─── Color palette ───────────────────────────────────────────────────────────

ACCENT = "#F88C5E"
ACCENT_HOVER = "#f9a07a"
BG_DEEP = "#0a0f1a"
BG_CARD = "#111827"
BG_INPUT = "#1e293b"
BG_BORDER = "#1f2937"
BG_BORDER_HOVER = "#2d3a4f"
BORDER_INPUT = "#334155"
BORDER_HOVER = "#475569"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
TEXT_DIM = "#64748b"
TEXT_FAINT = "#4b5563"
TEXT_DISABLED = "#475569"
CHAT_COMMENT_COLOR = "#F88C5E"
CHAT_GIFT_COLOR = "#fbbf24"
CHAT_JOIN_COLOR = "#60a5fa"
CHAT_CONTENT_COLOR = "#cbd5e1"
SPEED_INDICATOR_COLOR = "#60a5fa"

# ─── Status helpers ──────────────────────────────────────────────────────────

STATUS_COLORS: dict[str, tuple[str, str]] = {
    "idle": (BG_INPUT, "#6b7280"),
    "checking": ("rgba(96, 165, 250, 0.1)", "#60a5fa"),
    "monitoring": ("rgba(168, 85, 247, 0.1)", "#a855f7"),
    "recording": ("rgba(74, 222, 128, 0.1)", "#4ade80"),
    "encoding": ("rgba(251, 191, 36, 0.1)", "#fbbf24"),
    "done": ("rgba(16, 185, 129, 0.1)", "#10b981"),
    "error": ("rgba(248, 113, 113, 0.1)", "#f87171"),
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
    "recording": "#4ade80",
    "monitoring": "#a855f7",
    "checking": "#60a5fa",
    "encoding": "#fbbf24",
}

# ─── Inline style helpers ────────────────────────────────────────────────────
# These replace hardcoded style strings that were duplicated across modules.


def status_badge_style(bg: str, fg: str) -> str:
    """Dynamic style for the status badge on a TaskCard."""
    return (
        f"background-color: {bg}; color: {fg}; "
        f"font-size: 11px; font-weight: 700; padding: 4px 12px; "
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
    return f"color: {fg}; font-size: 12px; font-weight: 700;"


STAT_LABEL_STYLE = f"color: {TEXT_DIM}; font-size: 12px; font-weight: 500;"
INFO_KEY_STYLE = f"color: {TEXT_DIM}; font-size: 12px; font-weight: 600;"
INFO_VALUE_STYLE = f"color: {TEXT_SECONDARY}; font-size: 12px;"
USERNAME_STYLE = f"font-size: 18px; font-weight: 700; color: {TEXT_PRIMARY}; letter-spacing: -0.3px;"
PREVIEW_TITLE_STYLE = f"font-size: 12px; font-weight: 600; color: {TEXT_MUTED};"
PREVIEW_LABEL_STYLE = (
    f"QLabel {{ background-color: #000000; border: 1px solid {BORDER_INPUT}; "
    f"border-radius: 8px; color: {TEXT_DISABLED}; font-size: 12px; }}"
)
VOLUME_LABEL_STYLE = f"color: {TEXT_DIM}; font-size: 11px; min-width: 32px;"
TOGGLE_PREVIEW_STYLE = "QPushButton { padding: 2px 8px; font-size: 11px; }"
DETAIL_TABS_PANE_STYLE = (
    f"QTabWidget::pane {{ border: 1px solid {BG_BORDER}; border-radius: 8px; "
    f"background-color: #0d1321; padding: 8px; }}"
)
SPLITTER_HANDLE_STYLE = f"QSplitter::handle {{ background-color: {BG_BORDER}; border-radius: 2px; }}"
TITLEBAR_STYLE = f"background-color: {BG_CARD}; border-bottom: 1px solid {BG_BORDER};"
LOGO_STYLE = f"color: {ACCENT}; font-size: 20px; padding: 2px 6px; margin-right: 4px;"
APP_TITLE_STYLE = f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY}; letter-spacing: -0.3px;"
VERSION_CHIP_STYLE = (
    f"font-size: 10px; font-weight: 600; color: {TEXT_DIM}; "
    f"background-color: {BG_INPUT}; border-radius: 4px; "
    f"padding: 2px 6px; margin-left: 8px;"
)
GLOBAL_SPEED_STYLE = (
    f"color: {SPEED_INDICATOR_COLOR}; font-size: 11px; font-weight: 600; "
    f"background-color: rgba(96, 165, 250, 0.08); "
    f"border-radius: 6px; padding: 4px 10px; margin-right: 8px;"
)
SIDEBAR_BODY_STYLE = f"QSplitter::handle {{ background-color: {BG_BORDER}; }}"
TASK_HEADER_LABEL_STYLE = (
    f"color: {TEXT_FAINT}; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; padding-top: 6px;"
)
TASK_COUNT_STYLE = (
    f"color: #6b7280; font-size: 10px; font-weight: 700; "
    f"background-color: {BG_BORDER}; border-radius: 8px; "
    f"padding: 2px 8px; margin-top: 4px;"
)
SEARCH_INPUT_STYLE = (
    f"QLineEdit {{ background-color: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; "
    f"border-radius: 6px; padding: 4px 10px; font-size: 12px; }}"
)
SEPARATOR_STYLE = f"background-color: {BG_BORDER}; max-height: 1px;"
SCROLL_AREA_TRANSPARENT = f"QScrollArea {{ border: none; background-color: {BG_DEEP}; }}"
SCROLL_AREA_BORDERLESS = "QScrollArea { border: none; }"
CONTENT_BG_STYLE = f"background-color: {BG_DEEP};"
EMPTY_CIRCLE_STYLE = (
    f"font-size: 36px; color: {ACCENT}; background-color: rgba(248, 140, 94, 0.08); border-radius: 40px; padding: 20px;"
)
EMPTY_TEXT_STYLE = f"font-size: 18px; font-weight: 600; color: {TEXT_SECONDARY};"
EMPTY_SUB_STYLE = f"font-size: 13px; color: {TEXT_DIM};"
FORM_LABEL_STYLE = f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 600;"
DIALOG_BUTTON_BAR_STYLE = f"background-color: #0f172a; border-top: 1px solid {BORDER_INPUT};"
DIALOG_HEADER_STYLE = f"background-color: {BG_CARD}; border-bottom: 1px solid {BG_BORDER};"
DIALOG_HEADER_TITLE_STYLE = f"font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};"
SECONDARY_BUTTON_STYLE = (
    f"QPushButton {{ background-color: {BG_INPUT}; border: 1px solid {BORDER_INPUT}; "
    f"border-radius: 8px; padding: 8px 16px; color: {TEXT_SECONDARY}; font-weight: 500; }}"
    f"QPushButton:hover {{ background-color: #293548; border-color: {BORDER_HOVER}; }}"
)
SAVE_BUTTON_STYLE = (
    f"QPushButton {{ background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
    f"stop:0 {ACCENT}, stop:1 #f47944); border: none; border-radius: 8px; "
    f"padding: 8px 24px; color: white; font-weight: 700; }}"
    f"QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}"
)
VALIDATION_ERROR_STYLE = (
    f"QLineEdit {{ border: 1px solid #ef4444; background-color: {BORDER_INPUT}; "
    f"border-radius: 8px; padding: 8px 12px; color: {TEXT_SECONDARY}; }}"
)

# ─── Log entry formatting ────────────────────────────────────────────────────


def format_log_html(timestamp: str, text: str) -> str:
    """Format a log/encoding entry as HTML."""
    return f'<span style="color:{TEXT_DISABLED};">[{timestamp}]</span> <span style="color:{TEXT_MUTED};">{text}</span>'


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
    background-color: #0a0f1a;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
    font-size: 13px;
}
QLabel#title {
    font-size: 22px;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: -0.3px;
}
QLabel#subtitle {
    font-size: 11px;
    color: #94a3b8;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 600;
    color: #cbd5e1;
    padding: 4px 0;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
QWidget#sidebar {
    background-color: #111827;
    border-right: 1px solid #1f2937;
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
    padding: 6px 10px;
    margin: 2px 4px;
    color: #94a3b8;
    font-weight: 500;
}
QListWidget::item:selected {
    background-color: rgba(248, 140, 94, 0.08);
    border-left: 3px solid #F88C5E;
    color: #f8fafc;
}
QListWidget::item:hover {
    background-color: rgba(255, 255, 255, 0.04);
    color: #cbd5e1;
}

/* ── Cards ────────────────────────────────────────────────────────────── */
QFrame#card {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 14px;
    padding: 20px;
}
QFrame#card:hover {
    border: 1px solid #2d3a4f;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
    min-height: 20px;
    selection-background-color: #F88C5E;
    selection-color: white;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #F88C5E;
    background-color: #1e293b;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    selection-background-color: rgba(248, 140, 94, 0.15);
    selection-color: #f8fafc;
    color: #e2e8f0;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    padding: 6px 10px;
    border-radius: 4px;
}

/* ── Buttons ──────────────────────────────────────────────────────────── */
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    color: #e2e8f0;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #293548;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #334155;
}
QPushButton:disabled {
    background-color: #111827;
    border-color: #1f2937;
    color: #475569;
}
QPushButton#accent {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #F88C5E, stop:1 #f47944);
    border: none;
    color: white;
    font-weight: 700;
    padding: 10px 22px;
    letter-spacing: 0.3px;
}
QPushButton#accent:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f9a07a, stop:1 #f58d5e);
}
QPushButton#accent:pressed {
    background-color: #e06d3a;
}
QPushButton#accent:disabled {
    background-color: #4a3528;
    color: #8b7a70;
}
QPushButton#danger {
    background-color: #991b1b;
    border: 1px solid #b91c1c;
    color: white;
    font-weight: 600;
}
QPushButton#danger:hover {
    background-color: #b91c1c;
    border-color: #dc2626;
}
QPushButton#danger:pressed {
    background-color: #dc2626;
}
QPushButton#ghost {
    background-color: transparent;
    border: none;
    color: #64748b;
    font-weight: 500;
}
QPushButton#ghost:hover {
    color: #e2e8f0;
    background-color: rgba(255, 255, 255, 0.05);
    border-radius: 6px;
}
QPushButton#filterBtn {
    background-color: transparent;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
}
QPushButton#filterBtn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #94a3b8;
}
QPushButton#filterBtnActive {
    background-color: rgba(248, 140, 94, 0.12);
    border: 1px solid #F88C5E;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    color: #F88C5E;
}
QPushButton#iconBtn {
    background-color: transparent;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 6px;
    min-width: 30px;
    max-width: 30px;
    min-height: 30px;
    max-height: 30px;
    font-size: 14px;
    color: #64748b;
}
QPushButton#iconBtn:hover {
    background-color: rgba(255, 255, 255, 0.06);
    border-color: #334155;
    color: #e2e8f0;
}

/* ── Chat feed ────────────────────────────────────────────────────────── */
QTextEdit#chatFeed {
    background-color: #0a0f1a;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 10px;
    color: #e2e8f0;
    font-size: 12px;
    font-family: 'Segoe UI', sans-serif;
}

/* ── Checkbox ─────────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-weight: 500;
}
QCheckBox::indicator {
    width: 18px; height: 18px;
    border-radius: 5px;
    border: 2px solid #475569;
    background-color: #1e293b;
}
QCheckBox::indicator:hover {
    border-color: #64748b;
}
QCheckBox::indicator:checked {
    background-color: #F88C5E;
    border-color: #F88C5E;
    image: none;
}

/* ── Scrollbars ───────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
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
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 12px;
    letter-spacing: 0.5px;
}

/* ── Progress bar ─────────────────────────────────────────────────────── */
QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 3px;
}

/* ── Tooltip ──────────────────────────────────────────────────────────── */
QToolTip {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Slider ───────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background: #1e293b;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #F88C5E;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background: #F88C5E;
    border-radius: 2px;
}

/* ── Tab Widget ───────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: none;
    background-color: #0a0f1a;
}
QTabBar::tab {
    background-color: transparent;
    color: #64748b;
    padding: 10px 18px;
    font-weight: 600;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #F88C5E;
    border-bottom: 2px solid #F88C5E;
}
QTabBar::tab:hover {
    color: #e2e8f0;
}
"""
