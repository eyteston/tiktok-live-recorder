import json
import logging
import logging.handlers
import os
import sys
import time
from dataclasses import asdict

from PyQt6.QtCore import QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QIcon, QImage, QPalette, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import Config
from src.gui_dialogs import NewTaskDialog, PreferencesDialog
from src.gui_theme import (
    ACTIVE_STATUSES,
    DARK_STYLESHEET,
    PROGRESS_COLORS,
    STATUS_COLORS,
    STATUS_DOTS,
    STOPPED_STATUSES,
    WAITING_STATUSES,
)
from src.gui_workers import (
    AVATAR_CACHE_DIR,
    AVATAR_SIZE,
    AvatarFetchWorker,
    EncodeWorker,
    RecordingWorker,
    VideoPreviewWorker,
    _make_circular_pixmap,
    _make_placeholder_avatar,
)
from src.models import ChatMessage
from src.rate_limiter import RateLimiter
from src.utils import format_duration

# ─── Persistence ─────────────────────────────────────────────────────────────

TASKS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tasks.json")
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "settings.json")

DEFAULT_SETTINGS = {
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


def load_settings() -> dict:
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            merged = {**DEFAULT_SETTINGS, **data}
            return merged
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass


# ─── Task Card ───────────────────────────────────────────────────────────────


class TaskCard(QFrame):
    """Widget representing a single recording task with OlivedPro-inspired layout."""

    from PyQt6.QtCore import pyqtSignal

    status_updated = pyqtSignal(str)  # emitted after status changes, for parent to update sidebar

    _task_logger = logging.getLogger("src.gui.task")

    def __init__(self, config: Config, rate_limiter=None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.config = config
        self.rate_limiter = rate_limiter
        self.worker: RecordingWorker | None = None
        self.preview_worker: VideoPreviewWorker | None = None
        self.audio_player: QMediaPlayer | None = None
        self.audio_output: QAudioOutput | None = None
        self._last_volume: float = 0.5
        self._is_muted: bool = True
        self.stream_url: str | None = None
        self._preview_hidden: bool = True
        self.status = "idle"
        self.msg_count = 0
        self.monitoring_start_time: float | None = None
        self.start_time: float | None = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_duration)
        self._file_size_timer = QTimer()
        self._file_size_timer.timeout.connect(self._update_file_size)
        self._last_file_size = 0
        self._last_size_time = 0.0
        self._download_speed = 0.0
        self.last_live_time: str | None = None
        self.record_start_time: str | None = None
        self._encode_worker: EncodeWorker | None = None
        self.last_recording_dir: str | None = None
        self._encode_after_stop: bool = False
        self.worker_status_callback = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # ── Header: username + status badge ──
        header = QHBoxLayout()
        self.username_label = QLabel(f"@{self.config.unique_id}")
        self.username_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #f8fafc; letter-spacing: -0.3px;")
        header.addWidget(self.username_label)
        header.addStretch()

        self.status_label = QLabel("\u25cf IDLE")
        self.status_label.setObjectName("statusBadge")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # ── Progress bar ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: #1e293b; border-radius: 3px; }"
            "QProgressBar::chunk { background-color: #334155; border-radius: 3px; }"
        )
        layout.addWidget(self.progress_bar)

        # ── Stats row ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        self.speed_label = QLabel("\u2193 0 KB/s")
        self.speed_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        stats_row.addWidget(self.speed_label)

        self.duration_label = QLabel("\u23f1 0:00:00")
        self.duration_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        self.duration_label.setToolTip("Recording duration")
        stats_row.addWidget(self.duration_label)

        self.monitoring_label = QLabel("\u231b 0:00:00")
        self.monitoring_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        self.monitoring_label.setToolTip("Monitoring time")
        stats_row.addWidget(self.monitoring_label)

        self.chat_count_label = QLabel("\u2709 0 msgs")
        self.chat_count_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        stats_row.addWidget(self.chat_count_label)

        self.quality_label = QLabel(f"\u25aa {self.config.quality.upper()}")
        self.quality_label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500;")
        stats_row.addWidget(self.quality_label)

        stats_row.addStretch()
        layout.addLayout(stats_row)

        # ── Action buttons row (icon style) ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.start_btn = QPushButton("\u25b6")
        self.start_btn.setObjectName("iconBtn")
        self.start_btn.setToolTip("Start Recording")
        self.start_btn.clicked.connect(self.start_recording)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("\u25a0")
        self.stop_btn.setObjectName("iconBtn")
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)
        btn_row.addWidget(self.stop_btn)

        self.folder_btn = QPushButton("\ud83d\udcc1")
        self.folder_btn.setObjectName("iconBtn")
        self.folder_btn.setToolTip("Open Folder")
        self.folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self.folder_btn)

        self.open_live_btn = QPushButton("\ud83d\udd17")
        self.open_live_btn.setObjectName("iconBtn")
        self.open_live_btn.setToolTip("Open Live in Browser")
        self.open_live_btn.clicked.connect(self._open_live_in_browser)
        btn_row.addWidget(self.open_live_btn)

        self.encode_btn = QPushButton("\u2699")
        self.encode_btn.setObjectName("iconBtn")
        self.encode_btn.setToolTip("Encode Recording")
        self.encode_btn.clicked.connect(self._start_encode)
        btn_row.addWidget(self.encode_btn)

        self.edit_btn = QPushButton("\u270e")
        self.edit_btn.setObjectName("iconBtn")
        self.edit_btn.setToolTip("Edit Task")
        btn_row.addWidget(self.edit_btn)

        self.remove_btn = QPushButton("\u2715")
        self.remove_btn.setObjectName("iconBtn")
        self.remove_btn.setToolTip("Remove Task")
        btn_row.addWidget(self.remove_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ── Preview container ──
        self.preview_container = QWidget()
        self.preview_container.setVisible(False)
        pc_layout = QVBoxLayout(self.preview_container)
        pc_layout.setContentsMargins(0, 8, 0, 0)
        pc_layout.setSpacing(4)

        preview_header = QHBoxLayout()
        preview_title = QLabel("Live Preview")
        preview_title.setStyleSheet("font-size: 12px; font-weight: 600; color: #94a3b8;")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        self.toggle_preview_btn = QPushButton("Hide")
        self.toggle_preview_btn.setObjectName("ghost")
        self.toggle_preview_btn.setFixedHeight(24)
        self.toggle_preview_btn.setMinimumWidth(50)
        self.toggle_preview_btn.setStyleSheet("QPushButton { padding: 2px 8px; font-size: 11px; }")
        self.toggle_preview_btn.clicked.connect(self._toggle_preview)
        preview_header.addWidget(self.toggle_preview_btn)
        pc_layout.addLayout(preview_header)

        self.preview_label = QLabel()
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setText("Connecting to stream...")
        self.preview_label.setStyleSheet(
            "QLabel { background-color: #000000; border: 1px solid #334155; "
            "border-radius: 8px; color: #475569; font-size: 12px; }"
        )
        pc_layout.addWidget(self.preview_label)

        # ── Audio controls row ──
        audio_row = QHBoxLayout()
        audio_row.setContentsMargins(0, 4, 0, 0)
        audio_row.setSpacing(8)

        self.mute_btn = QPushButton("\U0001f507")
        self.mute_btn.setObjectName("iconBtn")
        self.mute_btn.setToolTip("Mute / Unmute")
        self.mute_btn.clicked.connect(self._toggle_mute)
        audio_row.addWidget(self.mute_btn)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(0)
        self.volume_slider.setFixedHeight(20)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        audio_row.addWidget(self.volume_slider)

        self.volume_label = QLabel("0%")
        self.volume_label.setStyleSheet("color: #64748b; font-size: 11px; min-width: 32px;")
        audio_row.addWidget(self.volume_label)

        pc_layout.addLayout(audio_row)

        # ── Detail panel (info + chat + log tabs) ──
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #1f2937; border-radius: 8px; "
            "background-color: #0d1321; padding: 8px; }"
        )

        # Info tab
        info_widget = QWidget()
        info_layout = QGridLayout(info_widget)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(12, 12, 12, 12)

        row = 0
        for label_text, attr_name in [
            ("Status:", "info_status"),
            ("Last Live:", "info_last_live"),
            ("Record Start:", "info_record_start"),
            ("Duration:", "info_duration"),
            ("Monitoring Time:", "info_monitoring_time"),
            ("Filename:", "info_filename"),
            ("File Size:", "info_file_size"),
            ("Download Speed:", "info_speed"),
            ("Chat Messages:", "info_chat_count"),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
            val = QLabel("--")
            val.setStyleSheet("color: #e2e8f0; font-size: 12px;")
            val.setWordWrap(True)
            info_layout.addWidget(lbl, row, 0, Qt.AlignmentFlag.AlignTop)
            info_layout.addWidget(val, row, 1, Qt.AlignmentFlag.AlignTop)
            setattr(self, attr_name, val)
            row += 1

        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(info_widget)
        info_scroll.setStyleSheet("QScrollArea { border: none; }")
        self.detail_tabs.addTab(info_scroll, "\u2139 Info")

        # Chat tab
        self.chat_feed = QTextEdit()
        self.chat_feed.setObjectName("chatFeed")
        self.chat_feed.setReadOnly(True)
        self.detail_tabs.addTab(self.chat_feed, "\u2709 Chat")

        # Log tab
        self.log_feed = QTextEdit()
        self.log_feed.setObjectName("chatFeed")
        self.log_feed.setReadOnly(True)
        self.detail_tabs.addTab(self.log_feed, "\u2630 Log")

        # Encoding tab
        self.encoding_feed = QTextEdit()
        self.encoding_feed.setObjectName("chatFeed")
        self.encoding_feed.setReadOnly(True)
        self.detail_tabs.addTab(self.encoding_feed, "\u2699 Encoding")

        # ── Splitter: preview + detail tabs (drag to resize) ──
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setHandleWidth(4)
        self.content_splitter.setStyleSheet("QSplitter::handle { background-color: #1f2937; border-radius: 2px; }")
        self.content_splitter.addWidget(self.preview_container)
        self.content_splitter.addWidget(self.detail_tabs)
        self.content_splitter.setStretchFactor(0, 2)  # preview gets more space
        self.content_splitter.setStretchFactor(1, 1)  # tabs get less
        layout.addWidget(self.content_splitter)

        # Apply initial status style (must be after all widgets are created)
        self._update_status_style()

    def _update_status_style(self):
        bg, fg = STATUS_COLORS.get(self.status, ("#1e293b", "#6b7280"))
        self.status_label.setStyleSheet(
            f"background-color: {bg}; color: {fg}; "
            f"font-size: 11px; font-weight: 700; padding: 4px 12px; "
            f"border-radius: 12px; letter-spacing: 0.5px;"
        )
        self.status_label.setText(f"\u25cf {self.status.upper()}")

        # Update progress bar color
        color = PROGRESS_COLORS.get(self.status, "#334155")
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background-color: #1e293b; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )

        # Update info panel
        self.info_status.setText(self.status.upper())
        self.info_status.setStyleSheet(f"color: {fg}; font-size: 12px; font-weight: 700;")

    def _on_status(self, status):
        self.status = status
        self._update_status_style()

        if status == "recording":
            # Reset recording duration each time we go live
            self.start_time = time.time()
            self.progress_bar.setRange(0, 0)  # indeterminate animation
            if self.config.max_duration > 0:
                self.progress_bar.setRange(0, self.config.max_duration)
            # Ensure timers are running during recording
            if not self._timer.isActive():
                self._timer.start(1000)
            if not self._file_size_timer.isActive():
                self._file_size_timer.start(2000)
        elif status == "encoding":
            # Recording finished, overlay encoding in progress
            self.start_time = None
            self.duration_label.setText("\u23f1 0:00:00")
            self.info_duration.setText("--")
            self.progress_bar.setRange(0, 0)  # indeterminate
            self._file_size_timer.stop()
            self._download_speed = 0.0
            self.speed_label.setText("\u2193 0 KB/s")
            # Keep _timer running for monitoring duration
            if not self._timer.isActive():
                self._timer.start(1000)
        elif status in ("done", "error", "idle"):
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0 if status == "idle" else 1)
            self._timer.stop()
            self._file_size_timer.stop()
        elif status in ("monitoring", "checking"):
            self.progress_bar.setRange(0, 0)  # indeterminate
            # Keep timer for monitoring duration, stop file size timer
            if not self._timer.isActive():
                self._timer.start(1000)
            self._file_size_timer.stop()
            self._download_speed = 0.0
            self.speed_label.setText("\u2193 0 KB/s")
            # Clear recording duration when not recording
            self.start_time = None
            self.duration_label.setText("\u23f1 0:00:00")
            self.info_duration.setText("--")

        self.status_updated.emit(status)

    def _on_chat(self, msg: ChatMessage):
        self.msg_count += 1
        self.chat_count_label.setText(f"\u2709 {self.msg_count} msgs")
        self.info_chat_count.setText(str(self.msg_count))

        if msg.event_type == "gift":
            color = "#fbbf24"
            prefix = "\ud83c\udf81"
        elif msg.event_type == "join":
            color = "#60a5fa"
            prefix = "\u2192"
        else:
            color = "#F88C5E"
            prefix = ""

        self.chat_feed.append(
            f'<span style="color:{color};">{prefix} <b>{msg.nickname}</b></span> '
            f'<span style="color:#cbd5e1;">{msg.content}</span>'
        )
        # Cap chat feed to 500 lines to prevent unbounded memory growth
        doc = self.chat_feed.document()
        while doc.blockCount() > 500:
            cursor = self.chat_feed.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

    def _on_log(self, text: str):
        self.log_feed.append(
            f'<span style="color:#475569;">[{time.strftime("%H:%M:%S")}]</span> '
            f'<span style="color:#94a3b8;">{text}</span>'
        )
        # Also route to file log with username prefix
        self._task_logger.info(f"[@{self.config.unique_id}] {text}")
        # Track last recording directory from recorder output messages
        if text.startswith("Output: "):
            self.last_recording_dir = text[8:].strip()
        # Cap log feed to 1000 lines to prevent unbounded memory growth
        doc = self.log_feed.document()
        while doc.blockCount() > 1000:
            cursor = self.log_feed.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

    def _on_stream_url(self, url: str):
        self.stream_url = url
        self.preview_container.setVisible(True)

    def _start_preview(self):
        if not self.stream_url:
            return
        self.preview_worker = VideoPreviewWorker(self.stream_url, self.config.ffmpeg_path)
        self.preview_worker.frame_ready.connect(self._on_preview_frame)
        self.preview_worker.start()

    def _on_preview_frame(self, image: QImage):
        pixmap = QPixmap.fromImage(image)
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)

    def _start_audio(self):
        """Start audio playback of the live stream using QMediaPlayer."""
        if not self.stream_url:
            return
        self._stop_audio()

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.0 if self._is_muted else self.volume_slider.value() / 100.0)

        self.audio_player = QMediaPlayer()
        self.audio_player.setAudioOutput(self.audio_output)
        self.audio_player.setSource(QUrl(self.stream_url))
        self.audio_player.play()

    def _stop_audio(self):
        """Stop and clean up audio playback."""
        if self.audio_player:
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            self.audio_player = None
        if self.audio_output:
            self.audio_output = None

    def _toggle_mute(self):
        """Toggle audio mute on/off."""
        if not self.audio_output:
            return
        if self._is_muted:
            self.audio_output.setVolume(self._last_volume)
            self.volume_slider.setValue(int(self._last_volume * 100))
            self.mute_btn.setText("\U0001f50a")
            self._is_muted = False
        else:
            self._last_volume = self.audio_output.volume()
            self.audio_output.setVolume(0.0)
            self.volume_slider.setValue(0)
            self.mute_btn.setText("\U0001f507")
            self._is_muted = True

    def _on_volume_changed(self, value: int):
        """Handle volume slider changes."""
        volume = value / 100.0
        if self.audio_output:
            self.audio_output.setVolume(volume)
        self.volume_label.setText(f"{value}%")
        if value == 0:
            self.mute_btn.setText("\U0001f507")
            self._is_muted = True
        elif self._is_muted:
            self.mute_btn.setText("\U0001f50a")
            self._is_muted = False

    def _stop_preview(self):
        self._stop_audio()
        if self.preview_worker:
            try:
                self.preview_worker.frame_ready.disconnect(self._on_preview_frame)
            except (TypeError, RuntimeError):
                pass
            self.preview_worker.stop()
            self.preview_worker.wait(3000)
            self.preview_worker = None

    def _toggle_preview(self):
        if self.preview_label.isVisible():
            # Hiding — stop FFmpeg + audio to save resources
            self._preview_hidden = True
            self._stop_preview()
            self.preview_label.setVisible(False)
            self.toggle_preview_btn.setText("Show")
        else:
            # Showing — restart FFmpeg + audio
            self._preview_hidden = False
            self.preview_label.setVisible(True)
            self.preview_label.setText("Connecting to stream...")
            self.toggle_preview_btn.setText("Hide")
            if self.stream_url:
                self._start_preview()
                self._start_audio()

    def start_recording(self):
        self.config.auto_monitor = True
        # Disconnect previous worker signals
        if self.worker:
            try:
                self.worker.status_changed.disconnect()
                self.worker.chat_message.disconnect()
                self.worker.log_message.disconnect()
                self.worker.stream_url_ready.disconnect()
                self.worker.finished_signal.disconnect()
            except (TypeError, RuntimeError):
                pass
        self._stop_preview()

        # Reset state
        self.chat_feed.clear()
        self.log_feed.clear()
        self.msg_count = 0
        self.chat_count_label.setText("\u2709 0 msgs")
        self.speed_label.setText("\u2193 0 KB/s")
        self.duration_label.setText("\u23f1 0:00:00")
        self.monitoring_label.setText("\u231b 0:00:00")
        self._download_speed = 0.0
        self._last_file_size = 0
        self.monitoring_start_time = time.time()
        self.start_time = None
        self.record_start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.info_record_start.setText(self.record_start_time)
        self.info_filename.setText("--")
        self.info_file_size.setText("--")

        # Create and wire worker
        self.worker = RecordingWorker(self.config, rate_limiter=self.rate_limiter)
        self.worker.status_changed.connect(self._on_status)
        self.worker.chat_message.connect(self._on_chat)
        self.worker.log_message.connect(self._on_log)
        self.worker.stream_url_ready.connect(self._on_stream_url)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._timer.start(1000)
        self._file_size_timer.start(2000)

    def stop_recording(self):
        self.config.auto_monitor = False
        if self.worker:
            self.worker.request_stop()
        self._stop_preview()
        self.stop_btn.setEnabled(False)

    def _on_finished(self):
        self._timer.stop()
        self._file_size_timer.stop()
        self._stop_preview()
        if self.worker:
            self.worker.wait(5000)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if self._encode_after_stop and self.last_recording_dir:
            # One-click encode: recording stopped, now auto-encode last folder
            self._do_encode(self.last_recording_dir)
            return  # encoding will handle final status

        if self.status not in ("error", "done"):
            self._on_status("done")

    def _update_duration(self):
        # Recording duration (only while actively recording)
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.duration_label.setText(f"\u23f1 {format_duration(elapsed)}")
            self.info_duration.setText(format_duration(elapsed))
            if self.config.max_duration > 0:
                self.progress_bar.setValue(min(int(elapsed), self.config.max_duration))
        # Monitoring duration (ticks while task is running)
        if self.monitoring_start_time:
            mon_elapsed = time.time() - self.monitoring_start_time
            self.monitoring_label.setText(f"\u231b {format_duration(mon_elapsed)}")
            self.info_monitoring_time.setText(format_duration(mon_elapsed))

    def _update_file_size(self):
        """Periodically check output file size for speed calculation."""
        if not self.worker or not self.worker.recorder:
            return
        session = self.worker.recorder.session
        path = session.raw_video_path
        if not path or not os.path.exists(path):
            return
        try:
            size = os.path.getsize(path)
        except OSError:
            return
        now = time.time()
        if self._last_size_time > 0 and now > self._last_size_time:
            dt = now - self._last_size_time
            speed = (size - self._last_file_size) / dt if dt > 0 else 0
            self._download_speed = speed
            if speed > 1_000_000:
                self.speed_label.setText(f"\u2193 {speed / 1_000_000:.1f} MB/s")
                self.info_speed.setText(f"{speed / 1_000_000:.1f} MB/s")
            else:
                self.speed_label.setText(f"\u2193 {speed / 1_000:.1f} KB/s")
                self.info_speed.setText(f"{speed / 1_000:.1f} KB/s")
        self._last_file_size = size
        self._last_size_time = now

        # Update file size display
        if size > 1_000_000_000:
            self.info_file_size.setText(f"{size / 1_000_000_000:.2f} GB")
        elif size > 1_000_000:
            self.info_file_size.setText(f"{size / 1_000_000:.1f} MB")
        else:
            self.info_file_size.setText(f"{size / 1_000:.0f} KB")

        # Update filename
        self.info_filename.setText(os.path.basename(path))

    def _open_folder(self):
        try:
            if self.worker and self.worker.recorder:
                output_dir = self.worker.recorder.session.output_dir
                if output_dir and os.path.isdir(output_dir):
                    if sys.platform == "win32":
                        os.startfile(output_dir)
                    return
        except Exception:
            pass
        # Fallback to config output dir
        d = os.path.abspath(self.config.output_dir)
        os.makedirs(d, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(d)

    def _open_live_in_browser(self):
        import webbrowser

        webbrowser.open(f"https://www.tiktok.com/@{self.config.unique_id}/live")

    def _on_encode_log(self, text: str):
        """Append encoding progress to the Encoding tab."""
        self.encoding_feed.append(
            f'<span style="color:#475569;">[{time.strftime("%H:%M:%S")}]</span> '
            f'<span style="color:#94a3b8;">{text}</span>'
        )
        # Cap to 500 lines
        doc = self.encoding_feed.document()
        while doc.blockCount() > 500:
            cursor = self.encoding_feed.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

    def _start_encode(self):
        """Start manual overlay encoding. If recording, stops first then auto-encodes."""
        # Don't start if already encoding (manual)
        if self._encode_worker and self._encode_worker.isRunning():
            return
        # Don't start if recorder is auto-encoding
        if (
            self.worker
            and self.worker.recorder
            and self.worker.recorder._encoder
            and self.worker.recorder._encoder.is_running
        ):
            self._on_log("Auto-encoding already in progress. Wait for it to finish.")
            return

        if self.worker and self.worker.isRunning():
            # Recording is active — stop first, then encode automatically
            self._encode_after_stop = True
            self.worker.request_stop()
            self._stop_preview()
            self.stop_btn.setEnabled(False)
            return

        # Not recording — use folder picker (default to last recording dir)
        start_dir = self.last_recording_dir or os.path.abspath(self.config.output_dir)
        folder = QFileDialog.getExistingDirectory(self, "Select Recording Folder", start_dir)
        if not folder:
            return
        self._do_encode(folder)

    def _do_encode(self, folder: str):
        """Run the encoding worker on a given folder."""
        self.encoding_feed.clear()
        self._encode_worker = EncodeWorker(folder, self.config)
        self._encode_worker.progress.connect(self._on_encode_log)
        self._encode_worker.finished_signal.connect(self._on_encode_finished)
        self._on_status("encoding")
        self.detail_tabs.setCurrentIndex(3)  # switch to Encoding tab
        self._encode_worker.start()

    def _on_encode_finished(self, success: bool):
        self._encode_worker = None
        if self._encode_after_stop:
            # Encoding triggered by one-click encode — resume monitoring
            self._encode_after_stop = False
            self._on_encode_log("Encoding finished. Resuming monitoring...")
            self.start_recording()
        else:
            self._on_status("done" if success else "error")

    def _remove_task(self):
        if self._encode_worker and self._encode_worker.isRunning():
            self._encode_worker.cancel()
            self._encode_worker.wait(5000)
            self._encode_worker = None
        if self.worker and self.worker.isRunning():
            self.stop_recording()
            if self.worker:
                self.worker.wait(3000)
        self._stop_preview()

    @property
    def download_speed(self) -> float:
        return self._download_speed


# ─── Main Window ─────────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Live Recorder")
        self.setMinimumSize(1100, 700)
        self.resize(1200, 750)
        self.tasks: list[tuple[QListWidgetItem, TaskCard]] = []
        self.settings = load_settings()
        self.rate_limiter = RateLimiter(min_delay=float(self.settings.get("rate_limit_delay", 10)))
        self._active_filter: str | None = None  # None = show all
        self._search_text = ""
        self._build_ui()
        self._load_tasks()

        # Global speed indicator update timer
        self._speed_timer = QTimer()
        self._speed_timer.timeout.connect(self._update_global_speed)
        self._speed_timer.start(2000)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Title bar ──
        titlebar = QWidget()
        titlebar.setStyleSheet("background-color: #111827; border-bottom: 1px solid #1f2937;")
        titlebar.setFixedHeight(52)
        tb_layout = QHBoxLayout(titlebar)
        tb_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("\u25cf")
        logo.setStyleSheet("color: #F88C5E; font-size: 20px; padding: 2px 6px; margin-right: 4px;")
        tb_layout.addWidget(logo)

        app_title = QLabel("TikTok Live Recorder")
        app_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc; letter-spacing: -0.3px;")
        tb_layout.addWidget(app_title)

        version_chip = QLabel("v2.0")
        version_chip.setStyleSheet(
            "font-size: 10px; font-weight: 600; color: #64748b; "
            "background-color: #1e293b; border-radius: 4px; "
            "padding: 2px 6px; margin-left: 8px;"
        )
        tb_layout.addWidget(version_chip)

        tb_layout.addStretch()

        # Global download speed indicator
        self.global_speed_label = QLabel("\u2193 0 KB/s")
        self.global_speed_label.setStyleSheet(
            "color: #60a5fa; font-size: 11px; font-weight: 600; "
            "background-color: rgba(96, 165, 250, 0.08); "
            "border-radius: 6px; padding: 4px 10px; margin-right: 8px;"
        )
        tb_layout.addWidget(self.global_speed_label)

        main_layout.addWidget(titlebar)

        # ── Body: sidebar + content ──
        body = QSplitter(Qt.Orientation.Horizontal)
        body.setHandleWidth(1)
        body.setStyleSheet("QSplitter::handle { background-color: #1f2937; }")

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 18, 14, 14)
        sb_layout.setSpacing(10)

        new_btn = QPushButton("+  New Task")
        new_btn.setObjectName("accent")
        new_btn.setFixedHeight(44)
        new_btn.clicked.connect(self._new_task)
        sb_layout.addWidget(new_btn)

        # Status filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        self.filter_active_btn = QPushButton("\u25b6 Active")
        self.filter_active_btn.setObjectName("filterBtn")
        self.filter_active_btn.setFixedHeight(28)
        self.filter_active_btn.clicked.connect(lambda: self._toggle_filter("active"))
        filter_row.addWidget(self.filter_active_btn)

        self.filter_waiting_btn = QPushButton("\u2016 Waiting")
        self.filter_waiting_btn.setObjectName("filterBtn")
        self.filter_waiting_btn.setFixedHeight(28)
        self.filter_waiting_btn.clicked.connect(lambda: self._toggle_filter("waiting"))
        filter_row.addWidget(self.filter_waiting_btn)

        self.filter_stopped_btn = QPushButton("\u25a0 Stopped")
        self.filter_stopped_btn.setObjectName("filterBtn")
        self.filter_stopped_btn.setFixedHeight(28)
        self.filter_stopped_btn.clicked.connect(lambda: self._toggle_filter("stopped"))
        filter_row.addWidget(self.filter_stopped_btn)
        sb_layout.addLayout(filter_row)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tasks...")
        self.search_input.setFixedHeight(32)
        self.search_input.setStyleSheet(
            "QLineEdit { background-color: #1e293b; border: 1px solid #334155; "
            "border-radius: 6px; padding: 4px 10px; font-size: 12px; }"
        )
        self.search_input.textChanged.connect(self._on_search_changed)
        sb_layout.addWidget(self.search_input)

        # Tasks header with count
        tasks_header = QHBoxLayout()
        tasks_label = QLabel("TASKS")
        tasks_label.setStyleSheet(
            "color: #4b5563; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; padding-top: 6px;"
        )
        tasks_header.addWidget(tasks_label)
        tasks_header.addStretch()
        self.task_count_label = QLabel("0")
        self.task_count_label.setStyleSheet(
            "color: #6b7280; font-size: 10px; font-weight: 700; "
            "background-color: #1f2937; border-radius: 8px; "
            "padding: 2px 8px; margin-top: 4px;"
        )
        tasks_header.addWidget(self.task_count_label)
        sb_layout.addLayout(tasks_header)

        self.task_list = QListWidget()
        self.task_list.setIconSize(QSize(AVATAR_SIZE, AVATAR_SIZE))
        self.task_list.currentRowChanged.connect(self._on_task_selected)
        sb_layout.addWidget(self.task_list)
        self._avatar_workers: list[AvatarFetchWorker] = []  # prevent GC

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #1f2937; max-height: 1px;")
        sb_layout.addWidget(sep)

        settings_btn = QPushButton("\u2699  Preferences")
        settings_btn.setObjectName("ghost")
        settings_btn.setFixedHeight(36)
        settings_btn.clicked.connect(self._open_settings)
        sb_layout.addWidget(settings_btn)

        body.addWidget(sidebar)

        # ── Content area ──
        content = QWidget()
        content.setStyleSheet("background-color: #0a0f1a;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(28, 24, 28, 24)
        self.content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.content_layout.addWidget(self.stack)

        # Empty state
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_circle = QLabel("\u25b6")
        empty_circle.setStyleSheet(
            "font-size: 36px; color: #F88C5E; "
            "background-color: rgba(248, 140, 94, 0.08); "
            "border-radius: 40px; padding: 20px;"
        )
        empty_circle.setFixedSize(80, 80)
        empty_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_circle, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addSpacing(16)

        empty_text = QLabel("No recording tasks yet")
        empty_text.setStyleSheet("font-size: 18px; font-weight: 600; color: #e2e8f0;")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text)
        empty_layout.addSpacing(6)

        empty_sub = QLabel('Click "+ New Task" to start monitoring a TikTok live stream')
        empty_sub.setStyleSheet("font-size: 13px; color: #64748b;")
        empty_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_sub)

        self.stack.addWidget(self.empty_state)

        body.addWidget(content)
        body.setStretchFactor(0, 0)
        body.setStretchFactor(1, 1)

        main_layout.addWidget(body)

    # ── Task Management ──

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
            # Sync session_id to global settings
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
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #0a0f1a; }")

        idx = self.stack.addWidget(scroll)
        card._scroll_area = scroll

        item = QListWidgetItem(f"@{config.unique_id}")
        # Set placeholder avatar, then fetch real one in background
        item.setIcon(QIcon(_make_placeholder_avatar()))
        self.task_list.addItem(item)
        self.tasks.append((item, card))

        self.task_list.setCurrentRow(self.task_list.count() - 1)
        self.stack.setCurrentIndex(idx)

        # Fetch avatar in background
        self._fetch_avatar(config.unique_id, config.avatar_url, item, config)

        def update_item_status(status):
            symbol = STATUS_DOTS.get(status, "\u25cb")
            item.setText(f"{symbol}  @{config.unique_id}")
            # Track last live time
            if status == "recording" and not card.last_live_time:
                card.last_live_time = time.strftime("%Y-%m-%d %H:%M:%S")
                card.info_last_live.setText(card.last_live_time)
            self._apply_filters()

        card.worker_status_callback = update_item_status
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

    # ── Filters & Search ──

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
        """Show/hide task list items based on active filter and search text."""
        for _i, (item, card) in enumerate(self.tasks):
            visible = True
            # Status filter
            if self._active_filter:
                status_group = None
                if card.status in ACTIVE_STATUSES:
                    status_group = "active"
                elif card.status in WAITING_STATUSES:
                    status_group = "waiting"
                elif card.status in STOPPED_STATUSES:
                    status_group = "stopped"
                if status_group != self._active_filter:
                    visible = False
            # Search filter
            if self._search_text and self._search_text not in card.config.unique_id.lower():
                visible = False
            item.setHidden(not visible)

    def _get_visible_tasks(self):
        return [(item, card) for item, card in self.tasks if not item.isHidden()]

    # ── Global Speed ──

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

    # ── Settings ──

    def _open_settings(self):
        dialog = PreferencesDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.settings = dialog.settings
            save_settings(self.settings)
            self.rate_limiter.min_delay = float(self.settings.get("rate_limit_delay", 10))

    # ── Avatars ──

    def _fetch_avatar(self, unique_id: str, avatar_url: str, item: QListWidgetItem, config: Config):
        """Start a background fetch for a user's TikTok avatar."""
        # Check disk cache first (synchronous, fast)
        cache_path = os.path.join(AVATAR_CACHE_DIR, f"{unique_id}.jpg")
        if os.path.isfile(cache_path):
            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                item.setIcon(QIcon(_make_circular_pixmap(pixmap)))
                return

        # Fetch in background thread
        worker = AvatarFetchWorker(unique_id, avatar_url)

        def on_avatar_ready(uid: str, circular_pixmap: QPixmap):
            # Find the matching item and update its icon
            for it, card in self.tasks:
                if card.config.unique_id == uid:
                    it.setIcon(QIcon(circular_pixmap))
                    # Save the URL for next launch
                    if not card.config.avatar_url:
                        card.config.avatar_url = f"cached:{uid}"
                    break
            # Clean up worker reference
            if worker in self._avatar_workers:
                self._avatar_workers.remove(worker)

        worker.avatar_ready.connect(on_avatar_ready)
        self._avatar_workers.append(worker)
        worker.start()

    # ── Persistence ──

    def _save_tasks(self):
        tasks_data = []
        for _, card in self.tasks:
            d = asdict(card.config)
            # session_id stored globally in settings.json — exclude from per-task data
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
                # Migration: old tasks had no_overlay=False (auto-encode on).
                # New default is True (encoding off). Force migration.
                if "no_overlay" in filtered and not filtered["no_overlay"]:
                    filtered["no_overlay"] = True
                # Inject global session_id if not present in per-task data
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


# ─── Launch Function ─────────────────────────────────────────────────────────


def _setup_file_logging():
    """Configure rotating file log for persistent debugging across sessions."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "recorder.log")
    handler = logging.handlers.RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)


def launch_gui():
    _setup_file_logging()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLESHEET)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0a0f1a"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#111827"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1e293b"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e2e8f0"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#F88C5E"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#4b5563"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
