import re

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.config import Config
from src.gui_constants import CHAT_POSITION_OPTIONS, QUALITY_OPTIONS
from src.gui_theme import (
    DIALOG_BUTTON_BAR_STYLE,
    DIALOG_HEADER_STYLE,
    DIALOG_HEADER_TITLE_STYLE,
    FORM_LABEL_STYLE,
    SAVE_BUTTON_STYLE,
    SCROLL_AREA_BORDERLESS,
    SECONDARY_BUTTON_STYLE,
    VALIDATION_ERROR_STYLE,
)

# ─── New Task Dialog ─────────────────────────────────────────────────────────


class NewTaskDialog(QDialog):
    """Dialog for creating or editing a recording task."""

    def __init__(self, parent=None, existing_config: Config | None = None):
        super().__init__(parent)
        self._editing = existing_config is not None
        self.setWindowTitle("Edit Task" if self._editing else "New Recording Task")
        self.setFixedSize(500, 740)
        self.result_config: Config | None = None
        self._build_ui()
        if existing_config:
            self._prefill(existing_config)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(SCROLL_AREA_BORDERLESS)
        form = QWidget()
        layout = QVBoxLayout(form)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 16)

        title = QLabel("Edit Task" if self._editing else "New Recording Task")
        title.setObjectName("title")
        layout.addWidget(title)

        layout.addWidget(self._label("TikTok Username"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("@username or TikTok live URL")
        layout.addWidget(self.username_input)

        layout.addWidget(self._label("Video Quality"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_OPTIONS)
        layout.addWidget(self.quality_combo)

        layout.addWidget(self._label("Output Directory"))
        dir_row = QHBoxLayout()
        self.output_input = QLineEdit("./recordings")
        dir_row.addWidget(self.output_input)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        layout.addWidget(self._label("Session ID (for age-restricted streams)"))
        self.session_input = QLineEdit()
        self.session_input.setPlaceholderText("Optional: paste TikTok sessionid cookie")
        self.session_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.session_input)

        layout.addWidget(self._label("Max Duration (seconds, 0 = unlimited)"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 86400)
        self.duration_spin.setValue(0)
        self.duration_spin.setSpecialValueText("Unlimited")
        layout.addWidget(self.duration_spin)

        toggles = QHBoxLayout()
        self.overlay_check = QCheckBox("Generate chat overlay")
        self.overlay_check.setChecked(False)
        toggles.addWidget(self.overlay_check)
        self.gifts_check = QCheckBox("Include gifts")
        self.gifts_check.setChecked(True)
        toggles.addWidget(self.gifts_check)
        layout.addLayout(toggles)

        toggles2 = QHBoxLayout()
        self.joins_check = QCheckBox("Include joins")
        self.joins_check.setChecked(True)
        toggles2.addWidget(self.joins_check)
        self.chat_only_check = QCheckBox("Chat only (no video)")
        toggles2.addWidget(self.chat_only_check)
        layout.addLayout(toggles2)

        layout.addWidget(self._label("Chat Overlay Settings"))
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(QLabel("Font:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 72)
        self.font_spin.setValue(24)
        overlay_row.addWidget(self.font_spin)
        overlay_row.addWidget(QLabel("Lines:"))
        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(1, 20)
        self.lines_spin.setValue(8)
        overlay_row.addWidget(self.lines_spin)
        overlay_row.addWidget(QLabel("Duration:"))
        self.chat_dur_spin = QDoubleSpinBox()
        self.chat_dur_spin.setRange(1.0, 30.0)
        self.chat_dur_spin.setValue(5.0)
        self.chat_dur_spin.setSingleStep(0.5)
        overlay_row.addWidget(self.chat_dur_spin)
        layout.addLayout(overlay_row)

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("Position:"))
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(CHAT_POSITION_OPTIONS)
        pos_row.addWidget(self.pos_combo)
        pos_row.addWidget(QLabel("Opacity:"))
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.0, 1.0)
        self.opacity_spin.setValue(0.6)
        self.opacity_spin.setSingleStep(0.1)
        pos_row.addWidget(self.opacity_spin)
        layout.addLayout(pos_row)

        margin_row = QHBoxLayout()
        margin_row.addWidget(QLabel("Margin X:"))
        self.margin_x_spin = QSpinBox()
        self.margin_x_spin.setRange(0, 500)
        self.margin_x_spin.setValue(20)
        self.margin_x_spin.setSuffix("px")
        margin_row.addWidget(self.margin_x_spin)
        margin_row.addWidget(QLabel("Margin Y:"))
        self.margin_y_spin = QSpinBox()
        self.margin_y_spin.setRange(0, 500)
        self.margin_y_spin.setValue(50)
        self.margin_y_spin.setSuffix("px")
        margin_row.addWidget(self.margin_y_spin)
        layout.addLayout(margin_row)

        scroll.setWidget(form)
        outer.addWidget(scroll, 1)

        btn_bar = QWidget()
        btn_bar.setStyleSheet(DIALOG_BUTTON_BAR_STYLE)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(24, 12, 24, 16)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        self.accept_btn = QPushButton("Save" if self._editing else "Create Task")
        self.accept_btn.setObjectName("accent")
        self.accept_btn.clicked.connect(self._accept)
        btn_layout.addWidget(self.accept_btn)
        outer.addWidget(btn_bar)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(FORM_LABEL_STYLE)
        return lbl

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if d:
            self.output_input.setText(d)

    def _prefill(self, config: Config):
        self.username_input.setText(config.unique_id)
        idx = self.quality_combo.findText(config.quality)
        if idx >= 0:
            self.quality_combo.setCurrentIndex(idx)
        self.output_input.setText(config.output_dir)
        self.session_input.setText(config.session_id)
        self.duration_spin.setValue(max(0, config.max_duration) if config.max_duration > 0 else 0)
        self.overlay_check.setChecked(not config.no_overlay)
        self.chat_only_check.setChecked(config.chat_only)
        self.gifts_check.setChecked(config.include_gifts)
        self.joins_check.setChecked(config.include_joins)
        self.font_spin.setValue(config.chat_font_size)
        self.lines_spin.setValue(config.chat_max_lines)
        self.chat_dur_spin.setValue(config.chat_display_duration)
        pos_idx = self.pos_combo.findText(config.chat_position)
        if pos_idx >= 0:
            self.pos_combo.setCurrentIndex(pos_idx)
        self.opacity_spin.setValue(config.chat_opacity)
        self.margin_x_spin.setValue(config.chat_margin_x)
        self.margin_y_spin.setValue(config.chat_margin_y)

    @staticmethod
    def _extract_username(text: str) -> str:
        text = text.strip()
        m = re.search(r"tiktok\.com/@([a-zA-Z0-9._-]+)", text)
        if m:
            return m.group(1)
        return text.lstrip("@")

    def _accept(self):
        username = self._extract_username(self.username_input.text())
        if not username:
            self.username_input.setStyleSheet(VALIDATION_ERROR_STYLE)
            return

        max_dur = self.duration_spin.value()
        self.result_config = Config(
            unique_id=username,
            output_dir=self.output_input.text() or "./recordings",
            quality=self.quality_combo.currentText(),
            max_duration=max_dur if max_dur > 0 else -1,
            no_overlay=not self.overlay_check.isChecked(),
            chat_only=self.chat_only_check.isChecked(),
            include_gifts=self.gifts_check.isChecked(),
            include_joins=self.joins_check.isChecked(),
            chat_font_size=self.font_spin.value(),
            chat_max_lines=self.lines_spin.value(),
            chat_display_duration=self.chat_dur_spin.value(),
            chat_position=self.pos_combo.currentText(),
            chat_margin_x=self.margin_x_spin.value(),
            chat_margin_y=self.margin_y_spin.value(),
            chat_opacity=self.opacity_spin.value(),
            session_id=self.session_input.text().strip(),
            terminal_chat=False,
        )
        self.accept()


# ─── Preferences Dialog (Multi-Tab) ─────────────────────────────────────────


class PreferencesDialog(QDialog):
    """Multi-tab preferences dialog."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = dict(settings)
        self.setWindowTitle("Preferences")
        self.setFixedSize(620, 540)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet(DIALOG_HEADER_STYLE)
        header.setFixedHeight(48)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel("Preferences")
        title.setStyleSheet(DIALOG_HEADER_TITLE_STYLE)
        h_layout.addWidget(title)
        outer.addWidget(header)

        # Tab widget
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, 1)

        self._build_basic_tab()
        self._build_advanced_tab()
        self._build_overlay_tab()
        self._build_button_bar(outer)

    def _build_basic_tab(self):
        basic = QWidget()
        bl = QVBoxLayout(basic)
        bl.setSpacing(16)
        bl.setContentsMargins(24, 20, 24, 20)

        bl.addWidget(self._label("Default Quality"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(QUALITY_OPTIONS)
        idx = self.quality_combo.findText(self.settings.get("default_quality", "hd"))
        if idx >= 0:
            self.quality_combo.setCurrentIndex(idx)
        bl.addWidget(self.quality_combo)

        bl.addWidget(self._label("Default Output Directory"))
        dir_row = QHBoxLayout()
        self.output_input = QLineEdit(self.settings.get("default_output_dir", "./recordings"))
        dir_row.addWidget(self.output_input)
        browse_btn = QPushButton("Browse")
        browse_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        bl.addLayout(dir_row)

        bl.addWidget(self._label("Default Session ID"))
        self.session_input = QLineEdit(self.settings.get("default_session_id", ""))
        self.session_input.setPlaceholderText("Paste TikTok sessionid cookie")
        self.session_input.setEchoMode(QLineEdit.EchoMode.Password)
        bl.addWidget(self.session_input)

        bl.addStretch()
        self.tabs.addTab(basic, "Basic")

    def _build_advanced_tab(self):
        advanced = QWidget()
        al = QVBoxLayout(advanced)
        al.setSpacing(16)
        al.setContentsMargins(24, 20, 24, 20)

        al.addWidget(self._label("Rate Limit Delay (seconds between API checks)"))
        self.rate_limit_spin = QSpinBox()
        self.rate_limit_spin.setRange(5, 60)
        self.rate_limit_spin.setValue(int(self.settings.get("rate_limit_delay", 10)))
        self.rate_limit_spin.setSuffix(" sec")
        al.addWidget(self.rate_limit_spin)

        al.addWidget(self._label("Default Encoding"))
        self.encoding_check = QCheckBox("Auto generate chat overlay on recordings")
        self.encoding_check.setChecked(not self.settings.get("default_no_overlay", False))
        al.addWidget(self.encoding_check)

        al.addStretch()
        self.tabs.addTab(advanced, "Advanced")

    def _build_overlay_tab(self):
        overlay = QWidget()
        ol = QVBoxLayout(overlay)
        ol.setSpacing(12)
        ol.setContentsMargins(24, 20, 24, 20)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Font Size:"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 72)
        self.font_spin.setValue(int(self.settings.get("default_chat_font_size", 24)))
        row1.addWidget(self.font_spin)
        row1.addWidget(QLabel("Max Lines:"))
        self.lines_spin = QSpinBox()
        self.lines_spin.setRange(1, 20)
        self.lines_spin.setValue(int(self.settings.get("default_chat_max_lines", 8)))
        row1.addWidget(self.lines_spin)
        ol.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Display Duration:"))
        self.dur_spin = QDoubleSpinBox()
        self.dur_spin.setRange(1.0, 30.0)
        self.dur_spin.setValue(float(self.settings.get("default_chat_display_duration", 5.0)))
        self.dur_spin.setSingleStep(0.5)
        self.dur_spin.setSuffix(" sec")
        row2.addWidget(self.dur_spin)
        row2.addWidget(QLabel("Opacity:"))
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.0, 1.0)
        self.opacity_spin.setValue(float(self.settings.get("default_chat_opacity", 0.6)))
        self.opacity_spin.setSingleStep(0.1)
        row2.addWidget(self.opacity_spin)
        ol.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Position:"))
        self.pos_combo = QComboBox()
        self.pos_combo.addItems(CHAT_POSITION_OPTIONS)
        pos_idx = self.pos_combo.findText(self.settings.get("default_chat_position", "bottom-left"))
        if pos_idx >= 0:
            self.pos_combo.setCurrentIndex(pos_idx)
        row3.addWidget(self.pos_combo)
        ol.addLayout(row3)

        row4 = QHBoxLayout()
        row4.addWidget(QLabel("Margin X:"))
        self.margin_x_spin = QSpinBox()
        self.margin_x_spin.setRange(0, 500)
        self.margin_x_spin.setValue(int(self.settings.get("default_chat_margin_x", 20)))
        self.margin_x_spin.setSuffix("px")
        row4.addWidget(self.margin_x_spin)
        row4.addWidget(QLabel("Margin Y:"))
        self.margin_y_spin = QSpinBox()
        self.margin_y_spin.setRange(0, 500)
        self.margin_y_spin.setValue(int(self.settings.get("default_chat_margin_y", 50)))
        self.margin_y_spin.setSuffix("px")
        row4.addWidget(self.margin_y_spin)
        ol.addLayout(row4)

        self.gifts_check = QCheckBox("Include gifts in overlay")
        self.gifts_check.setChecked(self.settings.get("default_include_gifts", True))
        ol.addWidget(self.gifts_check)

        self.joins_check = QCheckBox("Include joins in overlay")
        self.joins_check.setChecked(self.settings.get("default_include_joins", True))
        ol.addWidget(self.joins_check)

        ol.addStretch()
        self.tabs.addTab(overlay, "Chat Overlay")

    def _build_button_bar(self, outer: QVBoxLayout):
        btn_bar = QWidget()
        btn_bar.setStyleSheet(DIALOG_BUTTON_BAR_STYLE)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(24, 12, 24, 16)

        cancel_btn = QPushButton("Discard")
        cancel_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(SAVE_BUTTON_STYLE)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        outer.addWidget(btn_bar)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(FORM_LABEL_STYLE)
        return lbl

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if d:
            self.output_input.setText(d)

    def _save(self):
        self.settings["default_quality"] = self.quality_combo.currentText()
        self.settings["default_output_dir"] = self.output_input.text()
        self.settings["default_session_id"] = self.session_input.text().strip()
        self.settings["rate_limit_delay"] = self.rate_limit_spin.value()
        self.settings["default_no_overlay"] = not self.encoding_check.isChecked()
        self.settings["default_chat_font_size"] = self.font_spin.value()
        self.settings["default_chat_max_lines"] = self.lines_spin.value()
        self.settings["default_chat_display_duration"] = self.dur_spin.value()
        self.settings["default_chat_position"] = self.pos_combo.currentText()
        self.settings["default_chat_opacity"] = self.opacity_spin.value()
        self.settings["default_chat_margin_x"] = self.margin_x_spin.value()
        self.settings["default_chat_margin_y"] = self.margin_y_spin.value()
        self.settings["default_include_gifts"] = self.gifts_check.isChecked()
        self.settings["default_include_joins"] = self.joins_check.isChecked()
        self.accept()
