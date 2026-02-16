# ─── GUI Entry Point & Public API ────────────────────────────────────────────
# This module is the public entry point for the GUI. It re-exports the key
# classes so existing code that imports from `src.gui` continues to work.
#
# Internals have been split into:
#   gui_constants.py   — shared constants (paths, sizes, field definitions)
#   gui_persistence.py — settings load/save
#   gui_theme.py       — colors, status mappings, stylesheet, style helpers
#   gui_task_card.py   — TaskCard widget
#   gui_main_window.py — MainWindow
#   gui_dialogs.py     — NewTaskDialog, PreferencesDialog
#   gui_workers.py     — background QThread workers

import logging
import logging.handlers
import os
import sys

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from src.gui_main_window import MainWindow  # noqa: F401
from src.gui_task_card import TaskCard  # noqa: F401
from src.gui_theme import DARK_STYLESHEET


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
