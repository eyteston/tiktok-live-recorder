import asyncio
import os
import re
import subprocess
import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPixmap

from src.config import Config
from src.models import ChatMessage
from src.recorder import TikTokRecorder

# ─── Avatar helpers ──────────────────────────────────────────────────────────

AVATAR_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "avatar_cache")
AVATAR_SIZE = 32


def _make_circular_pixmap(pixmap: QPixmap, size: int = AVATAR_SIZE) -> QPixmap:
    """Scale a pixmap and clip it to a circle."""
    scaled = pixmap.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
    )
    # Center-crop if not square
    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    cropped = scaled.copy(x, y, size, size)

    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0.0, 0.0, float(size), float(size))
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


def _make_placeholder_avatar(size: int = AVATAR_SIZE) -> QPixmap:
    """Create a gray circle placeholder avatar."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor("#374151")))
    painter.setPen(QPen(QColor("#4b5563"), 1))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    # Draw a simple user silhouette (head + shoulders)
    painter.setBrush(QBrush(QColor("#6b7280")))
    painter.setPen(Qt.PenStyle.NoPen)
    head_r = size // 6
    cx, cy = size // 2, size // 3
    painter.drawEllipse(cx - head_r, cy - head_r, head_r * 2, head_r * 2)
    # Shoulders arc
    body_path = QPainterPath()
    body_y = cy + head_r + 2
    body_path.addEllipse(float(cx - size // 3), float(body_y), float(size * 2 // 3), float(size // 2))
    painter.setClipRect(0, 0, size, size)
    painter.drawPath(body_path)
    painter.end()
    return pixmap


class AvatarFetchWorker(QThread):
    """Background thread to fetch a TikTok avatar image."""

    avatar_ready = pyqtSignal(str, QPixmap)  # unique_id, circular pixmap

    def __init__(self, unique_id: str, avatar_url: str = "", parent=None):
        super().__init__(parent)
        self.unique_id = unique_id
        self.avatar_url = avatar_url

    def run(self):
        import httpx
        from TikTokLive.client.web.web_settings import (
            DEFAULT_COOKIES,
            DEFAULT_REQUEST_HEADERS,
            DEFAULT_WEB_CLIENT_PARAMS,
            WebDefaults,
        )

        os.makedirs(AVATAR_CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(AVATAR_CACHE_DIR, f"{self.unique_id}.jpg")

        # Try loading from disk cache first
        if os.path.isfile(cache_path):
            try:
                pixmap = QPixmap(cache_path)
                if not pixmap.isNull():
                    circular = _make_circular_pixmap(pixmap)
                    self.avatar_ready.emit(self.unique_id, circular)
                    return
            except Exception:
                pass

        # Resolve avatar URL if not provided or just a cache marker
        url = self.avatar_url if self.avatar_url and not self.avatar_url.startswith("cached:") else ""
        if not url:
            try:
                params = dict(DEFAULT_WEB_CLIENT_PARAMS)
                params["uniqueId"] = self.unique_id
                params["sourceType"] = 54
                resp = httpx.get(
                    WebDefaults.tiktok_app_url + "/api-live/user/room/",
                    params=params,
                    headers=DEFAULT_REQUEST_HEADERS,
                    cookies=DEFAULT_COOKIES,
                    timeout=10,
                    follow_redirects=True,
                )
                data = resp.json()
                user_data = data.get("data") or {}
                user = user_data.get("user") or {}
                url = user.get("avatarThumb") or user.get("avatarMedium") or user.get("avatarLarger") or ""
            except Exception:
                return  # No avatar — placeholder stays

        if not url:
            return

        # Download the image
        try:
            resp = httpx.get(
                url,
                timeout=10,
                follow_redirects=True,
                headers={"User-Agent": DEFAULT_REQUEST_HEADERS.get("User-Agent", "Mozilla/5.0")},
            )
            if resp.status_code == 200 and len(resp.content) > 100:
                # Cache to disk
                with open(cache_path, "wb") as f:
                    f.write(resp.content)
                img = QImage()
                img.loadFromData(resp.content)
                if not img.isNull():
                    pixmap = QPixmap.fromImage(img)
                    circular = _make_circular_pixmap(pixmap)
                    self.avatar_ready.emit(self.unique_id, circular)
        except Exception:
            pass


# ─── Recording Worker (QThread) ─────────────────────────────────────────────


class RecordingWorker(QThread):
    status_changed = pyqtSignal(str)
    chat_message = pyqtSignal(ChatMessage)
    log_message = pyqtSignal(str)
    stream_url_ready = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, config: Config, rate_limiter=None):
        super().__init__()
        self.config = config
        self.rate_limiter = rate_limiter
        self.recorder: TikTokRecorder | None = None

    def run(self):
        import traceback as _tb

        max_retries = 5
        consecutive_errors = 0
        backoff = 10.0

        while consecutive_errors < max_retries:
            # Windows ProactorEventLoop can cause [Errno 22] with some async libs.
            # Force SelectorEventLoop which is more compatible with websockets.
            if sys.platform == "win32":
                loop = asyncio.SelectorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                self.recorder = TikTokRecorder(
                    self.config,
                    on_status=self._on_status,
                    on_chat=self._on_chat,
                    on_log=self._on_log,
                    on_stream_url=self._on_stream_url,
                    rate_limiter=self.rate_limiter,
                )
                loop.run_until_complete(self.recorder.run())
                # Normal completion (user stopped) — break cleanly
                break
            except Exception as e:
                consecutive_errors += 1
                self._on_log(f"Worker error ({consecutive_errors}/{max_retries}): {e}")
                self._on_log(_tb.format_exc())
                if consecutive_errors >= max_retries:
                    self._on_log("Max retries reached. Stopping.")
                    self._on_status("error")
                else:
                    self._on_log(f"Retrying in {backoff:.0f}s...")
                    self._on_status("monitoring")
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for t in pending:
                        t.cancel()
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.run_until_complete(loop.shutdown_default_executor())
                except Exception:
                    pass
                loop.close()

            if consecutive_errors < max_retries:
                # Sleep with backoff before retry (check stop flag)
                import time as _time

                slept = 0.0
                while slept < backoff:
                    if self.recorder and self.recorder._stop_requested:
                        break
                    _time.sleep(0.5)
                    slept += 0.5
                if self.recorder and self.recorder._stop_requested:
                    break
                backoff = min(backoff * 1.5, 120.0)

        self.finished_signal.emit()

    def request_stop(self):
        if self.recorder:
            self.recorder.request_stop()

    def _on_status(self, status):
        self.status_changed.emit(status)

    def _on_chat(self, msg):
        self.chat_message.emit(msg)

    def _on_log(self, text):
        self.log_message.emit(text)

    def _on_stream_url(self, url):
        self.stream_url_ready.emit(url)


# ─── Video Preview Worker ────────────────────────────────────────────────────


class VideoPreviewWorker(QThread):
    frame_ready = pyqtSignal(QImage)
    PREVIEW_WIDTH = 480

    def __init__(self, stream_url: str, ffmpeg_path: str = "ffmpeg"):
        super().__init__()
        self.stream_url = stream_url
        self.ffmpeg_path = ffmpeg_path
        self._process = None
        self._running = False

    def run(self):
        self._running = True
        w = self.PREVIEW_WIDTH
        kwargs = dict(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        # Detect actual height by probing with showinfo filter
        detect_cmd = [
            self.ffmpeg_path,
            "-loglevel",
            "error",
            "-i",
            self.stream_url,
            "-vframes",
            "1",
            "-vf",
            f"scale={w}:-2,showinfo",
            "-f",
            "null",
            "-",
        ]
        detect_kwargs = dict(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if sys.platform == "win32":
            detect_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        h = 270  # fallback
        try:
            det = subprocess.Popen(detect_cmd, **detect_kwargs)
            _, stderr_data = det.communicate(timeout=15)
            if stderr_data:
                m = re.search(r"n:\s*\d+\s+.*?s:(\d+)x(\d+)", stderr_data.decode("utf-8", errors="replace"))
                if m:
                    detected_w, detected_h = int(m.group(1)), int(m.group(2))
                    if detected_w == w:
                        h = detected_h
        except Exception:
            pass

        frame_size = w * h * 3
        cmd = [
            self.ffmpeg_path,
            "-loglevel",
            "error",
            "-i",
            self.stream_url,
            "-vf",
            f"scale={w}:{h}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-r",
            "15",
            "-an",
            "pipe:1",
        ]
        try:
            self._process = subprocess.Popen(cmd, **kwargs)
            while self._running and self._process.poll() is None:
                data = self._process.stdout.read(frame_size)
                if len(data) != frame_size:
                    break
                image = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
                self.frame_ready.emit(image.copy())
        except Exception:
            pass
        finally:
            self._stop_process()

    def _stop_process(self):
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None

    def stop(self):
        self._running = False
        self._stop_process()


# ─── Encode Worker (manual overlay encoding) ────────────────────────────────


class EncodeWorker(QThread):
    """Background thread for manual overlay encoding from a recording folder."""

    progress = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, folder: str, config: Config):
        super().__init__()
        self.folder = folder
        self.config = config
        from src.overlay import OverlayEncoder

        self._encoder = OverlayEncoder()

    def run(self):
        import json

        from src.models import ChatMessage
        from src.subtitle import SubtitleGenerator

        # Find raw video
        raw_video = None
        for ext in ("flv", "mp4", "ts"):
            candidate = os.path.join(self.folder, f"raw_video.{ext}")
            if os.path.isfile(candidate):
                raw_video = candidate
                break
        if not raw_video:
            self.progress.emit("No raw_video file found in selected folder.")
            self.finished_signal.emit(False)
            return

        # Find chat log
        chat_log = os.path.join(self.folder, "chat_log.jsonl")
        if not os.path.isfile(chat_log):
            self.progress.emit("No chat_log.jsonl found in selected folder.")
            self.finished_signal.emit(False)
            return

        # Parse chat messages
        messages = []
        try:
            with open(chat_log, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        messages.append(ChatMessage(**data))
        except Exception as e:
            self.progress.emit(f"Error reading chat log: {e}")
            self.finished_signal.emit(False)
            return

        if not messages:
            self.progress.emit("Chat log is empty.")
            self.finished_signal.emit(False)
            return

        self.progress.emit(f"Found {len(messages)} chat messages.")

        # Generate subtitle
        subtitle_path = os.path.join(self.folder, "overlay.ass")
        gen = SubtitleGenerator(self.config)
        gen.write(messages, subtitle_path)
        self.progress.emit("Subtitle file generated.")

        # Determine output file
        base = os.path.splitext(os.path.basename(raw_video))[0]
        output_file = os.path.join(self.folder, f"{base}_overlay.{self.config.output_format}")
        self.progress.emit(f"Encoding to {os.path.basename(output_file)}...")

        def emit_progress(line: str):
            self.progress.emit(line)

        success = self._encoder.burn_subtitles(
            raw_video,
            subtitle_path,
            output_file,
            self.config,
            on_progress=emit_progress,
        )

        if success:
            self.progress.emit(f"Encoding complete: {output_file}")
        else:
            self.progress.emit("Encoding failed or was cancelled.")
        self.finished_signal.emit(success)

    def cancel(self):
        self._encoder.cancel()
