# ─── Main Window ─────────────────────────────────────────────────────────────
# Application main window with sidebar task list, content area, and global
# controls. Extracted from the monolithic gui.py for maintainability.

import json
import os
import time
from dataclasses import asdict

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import Config
from src.gui_constants import (
    GLOBAL_SPEED_UPDATE_INTERVAL,
    SIDEBAR_WIDTH,
    TASKS_FILE,
    TITLEBAR_HEIGHT,
)
from src.gui_dialogs import NewTaskDialog, PreferencesDialog
from src.gui_persistence import load_settings, save_settings
from src.gui_task_card import TaskCard
from src.gui_theme import (
    ACTIVE_STATUSES,
    APP_TITLE_STYLE,
    CONTENT_BG_STYLE,
    EMPTY_CIRCLE_STYLE,
    EMPTY_SUB_STYLE,
    EMPTY_TEXT_STYLE,
    GLOBAL_SPEED_STYLE,
    LOGO_STYLE,
    SCROLL_AREA_TRANSPARENT,
    SEARCH_INPUT_STYLE,
    SEPARATOR_STYLE,
    SIDEBAR_BODY_STYLE,
    STATUS_DOTS,
    STOPPED_STATUSES,
    TASK_COUNT_STYLE,
    TASK_HEADER_LABEL_STYLE,
    TITLEBAR_STYLE,
    VERSION_CHIP_STYLE,
    WAITING_STATUSES,
)
from src.gui_workers import (
    AVATAR_CACHE_DIR,
    AVATAR_SIZE,
    AvatarFetchWorker,
    _make_circular_pixmap,
    _make_placeholder_avatar,
)
from src.rate_limiter import RateLimiter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Live Recorder")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 750)
        self.tasks: list[tuple[QListWidgetItem, TaskCard]] = []
        self.settings = load_settings()
        self.rate_limiter = RateLimiter(min_delay=float(self.settings.get("rate_limit_delay", 10)))
        self._active_filter: str | None = None
        self._search_text = ""
        self._avatar_workers: list[AvatarFetchWorker] = []
        self._build_ui()
        self._load_tasks()

        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._update_global_speed)
        self._speed_timer.start(GLOBAL_SPEED_UPDATE_INTERVAL)

    # ── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_titlebar(main_layout)
        self._build_body(main_layout)

    def _build_titlebar(self, main_layout: QVBoxLayout):
        titlebar = QWidget()
        titlebar.setStyleSheet(TITLEBAR_STYLE)
        titlebar.setFixedHeight(TITLEBAR_HEIGHT)
        tb_layout = QHBoxLayout(titlebar)
        tb_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("\u25cf")
        logo.setStyleSheet(LOGO_STYLE)
        tb_layout.addWidget(logo)

        app_title = QLabel("TikTok Live Recorder")
        app_title.setStyleSheet(APP_TITLE_STYLE)
        tb_layout.addWidget(app_title)

        version_chip = QLabel("v2.0")
        version_chip.setStyleSheet(VERSION_CHIP_STYLE)
        tb_layout.addWidget(version_chip)

        tb_layout.addStretch()

        self.global_speed_label = QLabel("\u2193 0 KB/s")
        self.global_speed_label.setStyleSheet(GLOBAL_SPEED_STYLE)
        tb_layout.addWidget(self.global_speed_label)

        main_layout.addWidget(titlebar)

    def _build_body(self, main_layout: QVBoxLayout):
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)
        body.setStyleSheet(SIDEBAR_BODY_STYLE)

        self._build_sidebar(body)
        self._build_content(body)

        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)
        main_layout.addWidget(body)

    def _build_sidebar(self, body: QSplitter):
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(SIDEBAR_WIDTH)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 18, 14, 14)
        sb_layout.setSpacing(10)

        # New task button
        new_btn = QPushButton("+  New Task")
        new_btn.setObjectName("accent")
        new_btn.setFixedHeight(44)
        new_btn.clicked.connect(self._new_task)
        sb_layout.addWidget(new_btn)

        # Status filter row
        self._build_filter_row(sb_layout)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks...")
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet(SEARCH_INPUT_STYLE)
        self.search_input.textChanged.connect(self._on_search_changed)
        sb_layout.addWidget(self.search_input)

        # Tasks header
        tasks_header = QHBoxLayout()
        tasks_label = QLabel("TASKS")
        tasks_label.setStyleSheet(TASK_HEADER_LABEL_STYLE)
        tasks_header.addWidget(tasks_label)
        tasks_header.addStretch()
        self.task_count_label = QLabel("0")
        self.task_count_label.setStyleSheet(TASK_COUNT_STYLE)
        tasks_header.addWidget(self.task_count_label)
        sb_layout.addLayout(tasks_header)

        # Task list
        self.task_list = QListWidget()
        self.task_list.setIconSize(QSize(AVATAR_SIZE, AVATAR_SIZE))
        self.task_list.currentRowChanged.connect(self._on_task_selected)
        sb_layout.addWidget(self.task_list)

        # Separator + preferences
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR_STYLE)
        sb_layout.addWidget(sep)

        settings_btn = QPushButton("\u2699  Preferences")
        settings_btn.setObjectName("ghost")
        settings_btn.setFixedHeight(36)
        settings_btn.clicked.connect(self._open_settings)
        sb_layout.addWidget(settings_btn)

        body.addWidget(sidebar)

    def _build_filter_row(self, sb_layout: QVBoxLayout):
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)

        self.filter_active_btn = self._filter_btn("\u25b6 Active", "active")
        filter_row.addWidget(self.filter_active_btn)

        self.filter_waiting_btn = self._filter_btn("\u2016 Waiting", "waiting")
        filter_row.addWidget(self.filter_waiting_btn)

        self.filter_stopped_btn = self._filter_btn("\u25a0 Stopped", "stopped")
        filter_row.addWidget(self.filter_stopped_btn)

        sb_layout.addLayout(filter_row)

    def _filter_btn(self, text: str, filter_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("filterBtn")
        btn.setFixedHeight(28)
        btn.clicked.connect(lambda: self._toggle_filter(filter_name))
        return btn

    def _build_content(self, body: QSplitter):
        content = QWidget()
        content.setStyleSheet(CONTENT_BG_STYLE)
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(28, 24, 28, 24)
        self.content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        self._build_empty_state()
        body.addWidget(content)

    def _build_empty_state(self):
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_circle = QLabel("\u25b6")
        empty_circle.setStyleSheet(EMPTY_CIRCLE_STYLE)
        empty_circle.setFixedSize(80, 80)
        empty_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_circle, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addSpacing(16)

        empty_text = QLabel("No recording tasks yet")
        empty_text.setStyleSheet(EMPTY_TEXT_STYLE)
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text)
        empty_layout.addSpacing(6)

        empty_sub = QLabel('Click "+ New Task" to start monitoring a TikTok live stream')
        empty_sub.setStyleSheet(EMPTY_SUB_STYLE)
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_sub)

        self.stack.addWidget(self.empty_state)

    # ── Task Management ──────────────────────────────────────────────────

    def _new_task(self):
        dialog = NewTaskDialog(self)
        if self.settings.get("default_quality"):
            idx = dialog.quality_combo.findText(self.settings["default_quality"])
            if idx >= 0:
                dialog.quality_combo.setCurrentIndex(idx)
        if self.settings.get("default_output_dir"):
            dialog.output_input.setText(self.settings["default_output_dir"])
        if self.settings.get("default_session_id"):
            dialog.session_input.setText(self.settings["default_session_id"])
        if self.tasks:
            _, last_card = self.tasks[-1]
            if last_card.config.session_id:
                dialog.session_input.setText(last_card.config.session_id)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_config:
            config = dialog.result_config
            if config.session_id and config.session_id != self.settings.get("default_session_id", ""):
                self.settings["default_session_id"] = config.session_id
                save_settings(self.settings)
            self._add_task(config, auto_start=True)

    def _add_task(self, config: Config, auto_start: bool = False):
        card = TaskCard(config, rate_limiter=self.rate_limiter)
        card.remove_btn.clicked.connect(lambda: self._remove_task(card))
        card.edit_btn.clicked.connect(lambda: self._edit_task(card))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(card)
        scroll.setStyleSheet(SCROLL_AREA_TRANSPARENT)

        idx = self.stack.addWidget(scroll)
        card._scroll_area = scroll  # type: ignore[attr-defined]

        item = QListWidgetItem(f"@{config.unique_id}")
        item.setIcon(QIcon(_make_placeholder_avatar()))
        self.task_list.addItem(item)
        self.tasks.append((item, card))

        self.task_list.setCurrentRow(self.task_list.count() - 1)
        self.stack.setCurrentIndex(idx)

        self._fetch_avatar(config.unique_id, config.avatar_url, item, config)

        def update_item_status(status):
            symbol = STATUS_DOTS.get(status, "\u25cb")
            item.setText(f"{symbol}  @{config.unique_id}")
            if status == "recording" and not card.last_live_time:
                card.last_live_time = time.strftime("%Y-%m-%d %H:%M:%S")
                card.info_last_live.setText(card.last_live_time)
            self._apply_filters()

        card.worker_status_callback = update_item_status  # type: ignore[assignment]
        card.status_updated.connect(update_item_status)

        self._update_task_count()

        if auto_start:
            card.start_recording()

        self._save_tasks()

    def _remove_task(self, card: TaskCard):
        card._remove_task()
        card._stop_preview()

        for i, (_item, c) in enumerate(self.tasks):
            if c is card:
                self.task_list.takeItem(i)
                if hasattr(c, "_scroll_area"):
                    self.stack.removeWidget(c._scroll_area)
                    c._scroll_area.deleteLater()
                self.tasks.pop(i)
                break

        if not self.tasks:
            self.stack.setCurrentWidget(self.empty_state)

        self._update_task_count()
        self._save_tasks()

    def _update_task_count(self):
        self.task_count_label.setText(str(len(self.tasks)))

    def _edit_task(self, card: TaskCard):
        if card.worker and card.worker.isRunning():
            return
        dialog = NewTaskDialog(self, existing_config=card.config)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.result_config:
            new_config = dialog.result_config
            card.config = new_config
            card.username_label.setText(f"@{new_config.unique_id}")
            card.quality_label.setText(f"\u25aa {new_config.quality.upper()}")
            for item, c in self.tasks:
                if c is card:
                    item.setText(f"@{new_config.unique_id}")
                    break
            self._save_tasks()

    def _on_task_selected(self, row: int):
        if row < 0 or row >= len(self.tasks):
            return
        _, card = self.tasks[row]
        if hasattr(card, "_scroll_area"):
            self.stack.setCurrentWidget(card._scroll_area)

    # ── Filters & Search ─────────────────────────────────────────────────

    def _toggle_filter(self, filter_name: str):
        if self._active_filter == filter_name:
            self._active_filter = None
        else:
            self._active_filter = filter_name
        self._update_filter_buttons()
        self._apply_filters()

    def _update_filter_buttons(self):
        for btn, name in [
            (self.filter_active_btn, "active"),
            (self.filter_waiting_btn, "waiting"),
            (self.filter_stopped_btn, "stopped"),
        ]:
            if self._active_filter == name:
                btn.setObjectName("filterBtnActive")
            else:
                btn.setObjectName("filterBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_search_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._apply_filters()

    def _apply_filters(self):
        for _i, (item, card) in enumerate(self.tasks):
            visible = True
            if self._active_filter:
                if card.status in ACTIVE_STATUSES:
                    status_group = "active"
                elif card.status in WAITING_STATUSES:
                    status_group = "waiting"
                elif card.status in STOPPED_STATUSES:
                    status_group = "stopped"
                else:
                    status_group = None
                if status_group != self._active_filter:
                    visible = False
            if self._search_text and self._search_text not in card.config.unique_id.lower():
                visible = False
            item.setHidden(not visible)

    # ── Global Speed ─────────────────────────────────────────────────────

    def _update_global_speed(self):
        if not self.tasks:
            return
        total_speed = sum(card.download_speed for _, card in self.tasks)
        if total_speed > 1_000_000:
            self.global_speed_label.setText(f"\u2193 {total_speed / 1_000_000:.1f} MB/s")
        elif total_speed > 0:
            self.global_speed_label.setText(f"\u2193 {total_speed / 1_000:.1f} KB/s")
        else:
            self.global_speed_label.setText("\u2193 0 KB/s")

    # ── Settings ─────────────────────────────────────────────────────────

    def _open_settings(self):
        dialog = PreferencesDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings = dialog.settings
            save_settings(self.settings)
            self.rate_limiter.min_delay = float(self.settings.get("rate_limit_delay", 10))

    # ── Avatars ──────────────────────────────────────────────────────────

    def _fetch_avatar(self, unique_id: str, avatar_url: str, item: QListWidgetItem, config: Config):
        cache_path = os.path.join(AVATAR_CACHE_DIR, f"{unique_id}.jpg")
        if os.path.isfile(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                item.setIcon(QIcon(_make_circular_pixmap(pixmap)))
                return

        worker = AvatarFetchWorker(unique_id, avatar_url)

        def on_avatar_ready(uid: str, circular_pixmap: QPixmap):
            for it, card in self.tasks:
                if card.config.unique_id == uid:
                    it.setIcon(QIcon(circular_pixmap))
                    if not card.config.avatar_url:
                        card.config.avatar_url = f"cached:{uid}"
                    break
            if worker in self._avatar_workers:
                self._avatar_workers.remove(worker)

        worker.avatar_ready.connect(on_avatar_ready)
        self._avatar_workers.append(worker)
        worker.start()

    # ── Persistence ──────────────────────────────────────────────────────

    def _save_tasks(self):
        tasks_data = []
        for _, card in self.tasks:
            d = asdict(card.config)
            d.pop("session_id", None)
            d.pop("terminal_chat", None)
            tasks_data.append(d)
        data = {"tasks": tasks_data}
        try:
            with open(TASKS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def _load_tasks(self):
        if not os.path.isfile(TASKS_FILE):
            return
        try:
            with open(TASKS_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        valid_keys = set(Config.__dataclass_fields__.keys())
        global_session_id = self.settings.get("default_session_id", "")
        for task_data in data.get("tasks", []):
            try:
                filtered = {k: v for k, v in task_data.items() if k in valid_keys}
                filtered["terminal_chat"] = False
                if "no_overlay" in filtered and not filtered["no_overlay"]:
                    filtered["no_overlay"] = True
                if not filtered.get("session_id"):
                    filtered["session_id"] = global_session_id
                config = Config(**filtered)
                self._add_task(config, auto_start=config.auto_monitor)
            except (TypeError, ValueError):
                continue

    def closeEvent(self, event):
        self._save_tasks()
        for _, card in self.tasks:
            if card.worker and card.worker.isRunning():
                card.stop_recording()
                card.worker.wait(3000)
        super().closeEvent(event)
