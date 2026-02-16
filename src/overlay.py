import logging
import subprocess
import sys
import threading
from collections.abc import Callable

from src.config import Config
from src.utils import normalize_path_for_ffmpeg

logger = logging.getLogger(__name__)


class OverlayEncoder:
    """Encodes chat overlay onto video. Supports cancellation."""

    def __init__(self):
        self._process: subprocess.Popen | None = None
        self._cancelled = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._process is not None and self._process.poll() is None

    def cancel(self):
        """Cancel the encoding process."""
        self._cancelled = True
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()

    def burn_subtitles(
        self,
        raw_video: str,
        subtitle_file: str,
        output_file: str,
        config: Config,
        on_progress: Callable[[str], None] | None = None,
    ) -> bool:
        """Burn ASS subtitles onto video using FFmpeg.

        Args:
            on_progress: Optional callback receiving stderr lines (for progress).
        Returns True on success, False on failure/cancellation.
        """
        self._cancelled = False
        sub_path = normalize_path_for_ffmpeg(subtitle_file)
        vf = f"ass='{sub_path}'"

        cmd = [
            config.ffmpeg_path,
            "-y",
            "-loglevel",
            "error",
            "-i",
            raw_video,
            "-vf",
            vf,
            "-c:a",
            "copy",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-stats",
            output_file,
        ]

        logger.info(f"Burning subtitles: {' '.join(cmd)}")

        try:
            kwargs = dict(
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            with self._lock:
                self._process = subprocess.Popen(cmd, **kwargs)  # type: ignore[call-overload]

            # Read stderr line-by-line to prevent pipe buffer deadlock.
            # Previously used self._process.wait() which deadlocks when
            # the stderr pipe buffer fills (~65KB) and nobody reads it.
            stderr_lines: list[str] = []
            assert self._process.stderr is not None
            for line in iter(self._process.stderr.readline, b""):
                if self._cancelled:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    stderr_lines.append(decoded)
                    if on_progress:
                        on_progress(decoded)

            self._process.wait()

            if self._cancelled:
                logger.info("Encoding cancelled by user.")
                return False

            if self._process.returncode != 0:
                stderr_text = "\n".join(stderr_lines[-20:])  # last 20 lines
                logger.error(f"FFmpeg subtitle burn failed (code {self._process.returncode}): {stderr_text}")
                return False
            return True
        except FileNotFoundError:
            logger.error(f"FFmpeg not found at: {config.ffmpeg_path}")
            return False
        finally:
            with self._lock:
                self._process = None


def burn_subtitles(
    raw_video: str,
    subtitle_file: str,
    output_file: str,
    config: Config,
) -> bool:
    """Convenience wrapper for CLI / non-GUI usage."""
    encoder = OverlayEncoder()
    return encoder.burn_subtitles(raw_video, subtitle_file, output_file, config)
