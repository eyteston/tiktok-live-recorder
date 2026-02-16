# ─── Task Card Widget ────────────────────────────────────────────────────────
# Self-contained widget representing a single recording task with status,
# stats, preview, chat/log feeds, and action buttons.

import logging
import os
import sys
import time

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import Config
from src.gui_constants import (
    CHAT_FEED_MAX_LINES,
    DURATION_UPDATE_INTERVAL,
    ENCODE_FEED_MAX_LINES,
    FILE_SIZE_UPDATE_INTERVAL,
    INFO_PANEL_FIELDS,
    LOG_FEED_MAX_LINES,
)
from src.gui_theme import (
    CHAT_COMMENT_COLOR,
    CHAT_GIFT_COLOR,
    CHAT_JOIN_COLOR,
    DETAIL_TABS_PANE_STYLE,
    INFO_KEY_STYLE,
    INFO_VALUE_STYLE,
    PREVIEW_LABEL_STYLE,
    PREVIEW_TITLE_STYLE,
    PROGRESS_COLORS,
    SPLITTER_HANDLE_STYLE,
    STAT_LABEL_STYLE,
    STATUS_COLORS,
    TOGGLE_PREVIEW_STYLE,
    USERNAME_STYLE,
    VOLUME_LABEL_STYLE,
    format_chat_html,
    format_log_html,
    info_status_style,
    progress_bar_style,
    status_badge_style,
)
from src.gui_workers import EncodeWorker, RecordingWorker, VideoPreviewWorker
from src.models import ChatMessage
from src.utils import format_duration


class TaskCard(QFrame):
    """Widget representing a single recording task."""

    status_updated = pyqtSignal(str)

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

    # ── UI Construction ──────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        self._build_header(layout)
        self._build_progress_bar(layout)
        self._build_stats_row(layout)
        self._build_action_buttons(layout)
        self._build_content_area(layout)

        self._update_status_style()

    def _build_header(self, parent_layout: QVBoxLayout):
        header = QHBoxLayout()
        self.username_label = QLabel(f"@{self.config.unique_id}")
        self.username_label.setStyleSheet(USERNAME_STYLE)
        header.addWidget(self.username_label)
        header.addStretch()

        self.status_label = QLabel("\u25cf IDLE")
        self.status_label.setObjectName("statusBadge")
        header.addWidget(self.status_label)
        parent_layout.addLayout(header)

    def _build_progress_bar(self, parent_layout: QVBoxLayout):
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(progress_bar_style("#334155"))
        parent_layout.addWidget(self.progress_bar)

    def _build_stats_row(self, parent_layout: QVBoxLayout):
        stats_row = QHBoxLayout()
        stats_row.setSpacing(20)

        self.speed_label = self._stat_label("\u2193 0 KB/s")
        stats_row.addWidget(self.speed_label)

        self.duration_label = self._stat_label("\u23f1 0:00:00", "Recording duration")
        stats_row.addWidget(self.duration_label)

        self.monitoring_label = self._stat_label("\u231b 0:00:00", "Monitoring time")
        stats_row.addWidget(self.monitoring_label)

        self.chat_count_label = self._stat_label("\u2709 0 msgs")
        stats_row.addWidget(self.chat_count_label)

        self.quality_label = self._stat_label(f"\u25aa {self.config.quality.upper()}")
        stats_row.addWidget(self.quality_label)

        stats_row.addStretch()
        parent_layout.addLayout(stats_row)

    def _stat_label(self, text: str, tooltip: str = "") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(STAT_LABEL_STYLE)
        if tooltip:
            lbl.setToolTip(tooltip)
        return lbl

    def _build_action_buttons(self, parent_layout: QVBoxLayout):
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.start_btn = self._icon_btn("\u25b6", "Start Recording")
        self.start_btn.clicked.connect(self.start_recording)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = self._icon_btn("\u25a0", "Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)
        btn_row.addWidget(self.stop_btn)

        self.folder_btn = self._icon_btn("\ud83d\udcc1", "Open Folder")
        self.folder_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self.folder_btn)

        self.open_live_btn = self._icon_btn("\ud83d\udd17", "Open Live in Browser")
        self.open_live_btn.clicked.connect(self._open_live_in_browser)
        btn_row.addWidget(self.open_live_btn)

        self.encode_btn = self._icon_btn("\u2699", "Encode Recording")
        self.encode_btn.clicked.connect(self._start_encode)
        btn_row.addWidget(self.encode_btn)

        self.edit_btn = self._icon_btn("\u270e", "Edit Task")
        btn_row.addWidget(self.edit_btn)

        self.remove_btn = self._icon_btn("\u2715", "Remove Task")
        btn_row.addWidget(self.remove_btn)

        btn_row.addStretch()
        parent_layout.addLayout(btn_row)

    def _icon_btn(self, icon: str, tooltip: str) -> QPushButton:
        btn = QPushButton(icon)
        btn.setObjectName("iconBtn")
        btn.setToolTip(tooltip)
        return btn

    def _build_content_area(self, parent_layout: QVBoxLayout):
        # Preview container
        self.preview_container = QWidget()
        self.preview_container.setVisible(False)
        pc_layout = QVBoxLayout(self.preview_container)
        pc_layout.setContentsMargins(0, 8, 0, 0)
        pc_layout.setSpacing(4)

        self._build_preview_header(pc_layout)
        self._build_preview_label(pc_layout)
        self._build_audio_controls(pc_layout)

        # Detail tabs
        self._build_detail_tabs()

        # Splitter
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setHandleWidth(4)
        self.content_splitter.setStyleSheet(SPLITTER_HANDLE_STYLE)
        self.content_splitter.addWidget(self.preview_container)
        self.content_splitter.addWidget(self.detail_tabs)
        self.content_splitter.setStretchFactor(0, 2)
        self.content_splitter.setStretchFactor(1, 1)
        parent_layout.addWidget(self.content_splitter)

    def _build_preview_header(self, pc_layout: QVBoxLayout):
        preview_header = QHBoxLayout()
        preview_title = QLabel("Live Preview")
        preview_title.setStyleSheet(PREVIEW_TITLE_STYLE)
        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        self.toggle_preview_btn = QPushButton("Hide")
        self.toggle_preview_btn.setObjectName("ghost")
        self.toggle_preview_btn.setFixedHeight(24)
        self.toggle_preview_btn.setMinimumWidth(50)
        self.toggle_preview_btn.setStyleSheet(TOGGLE_PREVIEW_STYLE)
        self.toggle_preview_btn.clicked.connect(self._toggle_preview)
        preview_header.addWidget(self.toggle_preview_btn)
        pc_layout.addLayout(preview_header)

    def _build_preview_label(self, pc_layout: QVBoxLayout):
        self.preview_label = QLabel()
        self.preview_label.setMinimumHeight(180)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setText("Connecting to stream...")
        self.preview_label.setStyleSheet(PREVIEW_LABEL_STYLE)
        pc_layout.addWidget(self.preview_label)

    def _build_audio_controls(self, pc_layout: QVBoxLayout):
        audio_row = QHBoxLayout()
        audio_row.setContentsMargins(0, 4, 0, 0)
        audio_row.setSpacing(8)

        self.mute_btn = self._icon_btn("\U0001f507", "Mute / Unmute")
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
        self.volume_label.setStyleSheet(VOLUME_LABEL_STYLE)
        audio_row.addWidget(self.volume_label)

        pc_layout.addLayout(audio_row)

    def _build_detail_tabs(self):
        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet(DETAIL_TABS_PANE_STYLE)

        # Info tab
        info_widget = QWidget()
        info_layout = QGridLayout(info_widget)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(12, 12, 12, 12)

        for row, (label_text, attr_name) in enumerate(INFO_PANEL_FIELDS):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(INFO_KEY_STYLE)
            val = QLabel("--")
            val.setStyleSheet(INFO_VALUE_STYLE)
            val.setWordWrap(True)
            info_layout.addWidget(lbl, row, 0, Qt.AlignmentFlag.AlignTop)
            info_layout.addWidget(val, row, 1, Qt.AlignmentFlag.AlignTop)
            setattr(self, attr_name, val)

        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(info_widget)
        info_scroll.setStyleSheet("QScrollArea { border: none; }")
        self.detail_tabs.addTab(info_scroll, "\u2139 Info")

        # Chat tab
        self.chat_feed = self._create_feed()
        self.detail_tabs.addTab(self.chat_feed, "\u2709 Chat")

        # Log tab
        self.log_feed = self._create_feed()
        self.detail_tabs.addTab(self.log_feed, "\u2630 Log")

        # Encoding tab
        self.encoding_feed = self._create_feed()
        self.detail_tabs.addTab(self.encoding_feed, "\u2699 Encoding")

    def _create_feed(self) -> QTextEdit:
        feed = QTextEdit()
        feed.setObjectName("chatFeed")
        feed.setReadOnly(True)
        return feed

    # ── Status Management ────────────────────────────────────────────────

    def _update_status_style(self):
        bg, fg = STATUS_COLORS.get(self.status, ("#1e293b", "#6b7280"))
        self.status_label.setStyleSheet(status_badge_style(bg, fg))
        self.status_label.setText(f"\u25cf {self.status.upper()}")

        color = PROGRESS_COLORS.get(self.status, "#334155")
        self.progress_bar.setStyleSheet(progress_bar_style(color))

        self.info_status.setText(self.status.upper())
        self.info_status.setStyleSheet(info_status_style(fg))

    def _on_status(self, status):
        self.status = status
        self._update_status_style()

        if status == "recording":
            self.start_time = time.time()
            self.progress_bar.setRange(0, 0)
            if self.config.max_duration > 0:
                self.progress_bar.setRange(0, self.config.max_duration)
            if not self._timer.isActive():
                self._timer.start(DURATION_UPDATE_INTERVAL)
            if not self._file_size_timer.isActive():
                self._file_size_timer.start(FILE_SIZE_UPDATE_INTERVAL)
        elif status == "encoding":
            self.start_time = None
            self.duration_label.setText("\u23f1 0:00:00")
            self.info_duration.setText("--")
            self.progress_bar.setRange(0, 0)
            self._file_size_timer.stop()
            self._download_speed = 0.0
            self.speed_label.setText("\u2193 0 KB/s")
            if not self._timer.isActive():
                self._timer.start(DURATION_UPDATE_INTERVAL)
        elif status in ("done", "error", "idle"):
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0 if status == "idle" else 1)
            self._timer.stop()
            self._file_size_timer.stop()
        elif status in ("monitoring", "checking"):
            self.progress_bar.setRange(0, 0)
            if not self._timer.isActive():
                self._timer.start(DURATION_UPDATE_INTERVAL)
            self._file_size_timer.stop()
            self._download_speed = 0.0
            self.speed_label.setText("\u2193 0 KB/s")
            self.start_time = None
            self.duration_label.setText("\u23f1 0:00:00")
            self.info_duration.setText("--")

        self.status_updated.emit(status)

    # ── Chat & Log Handlers ──────────────────────────────────────────────

    def _on_chat(self, msg: ChatMessage):
        self.msg_count += 1
        self.chat_count_label.setText(f"\u2709 {self.msg_count} msgs")
        self.info_chat_count.setText(str(self.msg_count))  # type: ignore[attr-defined]

        if msg.event_type == "gift":
            color, prefix = CHAT_GIFT_COLOR, "\ud83c\udf81"
        elif msg.event_type == "join":
            color, prefix = CHAT_JOIN_COLOR, "\u2192"
        else:
            color, prefix = CHAT_COMMENT_COLOR, ""

        self.chat_feed.append(format_chat_html(prefix, color, msg.nickname, msg.content))
        _truncate_feed(self.chat_feed, CHAT_FEED_MAX_LINES)

    def _on_log(self, text: str):
        self.log_feed.append(format_log_html(time.strftime("%H:%M:%S"), text))
        self._task_logger.info(f"[@{self.config.unique_id}] {text}")
        if text.startswith("Output: "):
            self.last_recording_dir = text[8:].strip()
        _truncate_feed(self.log_feed, LOG_FEED_MAX_LINES)

    def _on_encode_log(self, text: str):
        self.encoding_feed.append(format_log_html(time.strftime("%H:%M:%S"), text))
        _truncate_feed(self.encoding_feed, ENCODE_FEED_MAX_LINES)

    # ── Stream Preview ───────────────────────────────────────────────────

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
            self._preview_hidden = True
            self._stop_preview()
            self.preview_label.setVisible(False)
            self.toggle_preview_btn.setText("Show")
        else:
            self._preview_hidden = False
            self.preview_label.setVisible(True)
            self.preview_label.setText("Connecting to stream...")
            self.toggle_preview_btn.setText("Hide")
            if self.stream_url:
                self._start_preview()
                self._start_audio()

    # ── Audio Playback ───────────────────────────────────────────────────

    def _start_audio(self):
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
        if self.audio_player:
            self.audio_player.stop()
            self.audio_player.setSource(QUrl())
            self.audio_player = None
        if self.audio_output:
            self.audio_output = None

    def _toggle_mute(self):
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

    # ── Recording Lifecycle ──────────────────────────────────────────────

    def start_recording(self):
        self.config.auto_monitor = True
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

        self.worker = RecordingWorker(self.config, rate_limiter=self.rate_limiter)
        self.worker.status_changed.connect(self._on_status)
        self.worker.chat_message.connect(self._on_chat)
        self.worker.log_message.connect(self._on_log)
        self.worker.stream_url_ready.connect(self._on_stream_url)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._timer.start(DURATION_UPDATE_INTERVAL)
        self._file_size_timer.start(FILE_SIZE_UPDATE_INTERVAL)

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
            self._do_encode(self.last_recording_dir)
            return

        if self.status not in ("error", "done"):
            self._on_status("done")

    # ── Timer Callbacks ──────────────────────────────────────────────────

    def _update_duration(self):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.duration_label.setText(f"\u23f1 {format_duration(elapsed)}")
            self.info_duration.setText(format_duration(elapsed))
            if self.config.max_duration > 0:
                self.progress_bar.setValue(min(int(elapsed), self.config.max_duration))
        if self.monitoring_start_time:
            mon_elapsed = time.time() - self.monitoring_start_time
            self.monitoring_label.setText(f"\u231b {format_duration(mon_elapsed)}")
            self.info_monitoring_time.setText(format_duration(mon_elapsed))

    def _update_file_size(self):
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

        if size > 1_000_000_000:
            self.info_file_size.setText(f"{size / 1_000_000_000:.2f} GB")
        elif size > 1_000_000:
            self.info_file_size.setText(f"{size / 1_000_000:.1f} MB")
        else:
            self.info_file_size.setText(f"{size / 1_000:.0f} KB")

        self.info_filename.setText(os.path.basename(path))

    # ── Actions ──────────────────────────────────────────────────────────

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
        d = os.path.abspath(self.config.output_dir)
        os.makedirs(d, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(d)

    def _open_live_in_browser(self):
        import webbrowser

        webbrowser.open(f"https://www.tiktok.com/@{self.config.unique_id}/live")

    # ── Encoding ─────────────────────────────────────────────────────────

    def _start_encode(self):
        if self._encode_worker and self._encode_worker.isRunning():
            return
        if (
            self.worker
            and self.worker.recorder
            and self.worker.recorder._encoder
            and self.worker.recorder._encoder.is_running
        ):
            self._on_log("Auto-encoding already in progress. Wait for it to finish.")
            return

        if self.worker and self.worker.isRunning():
            self._encode_after_stop = True
            self.worker.request_stop()
            self._stop_preview()
            self.stop_btn.setEnabled(False)
            return

        start_dir = self.last_recording_dir or os.path.abspath(self.config.output_dir)
        folder = QFileDialog.getExistingDirectory(self, "Select Recording Folder", start_dir)
        if not folder:
            return
        self._do_encode(folder)

    def _do_encode(self, folder: str):
        self.encoding_feed.clear()
        self._encode_worker = EncodeWorker(folder, self.config)
        self._encode_worker.progress.connect(self._on_encode_log)
        self._encode_worker.finished_signal.connect(self._on_encode_finished)
        self._on_status("encoding")
        self.detail_tabs.setCurrentIndex(3)
        self._encode_worker.start()

    def _on_encode_finished(self, success: bool):
        self._encode_worker = None
        if self._encode_after_stop:
            self._encode_after_stop = False
            self._on_encode_log("Encoding finished. Resuming monitoring...")
            self.start_recording()
        else:
            self._on_status("done" if success else "error")

    # ── Cleanup ──────────────────────────────────────────────────────────

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


# ─── Feed truncation helper ─────────────────────────────────────────────────


def _truncate_feed(feed: QTextEdit, max_lines: int) -> None:
    """Remove oldest lines from a QTextEdit when it exceeds max_lines."""
    doc = feed.document()
    if doc is None:
        return
    while doc.blockCount() > max_lines:
        cursor = feed.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        cursor.movePosition(cursor.MoveOperation.NextBlock, cursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
