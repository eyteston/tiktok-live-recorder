import json
import logging
import subprocess
import sys
import time
from typing import Optional

from src.config import Config

logger = logging.getLogger(__name__)


QUALITY_FALLBACK_ORDER = ["origin", "uhd", "hd", "sd", "ld"]


def extract_stream_url(room_info: dict, quality: str, fmt: str = "flv") -> tuple[str, str]:
    """Extract the livestream URL from TikTok room info.

    Returns (url, actual_quality).  Falls back through quality levels
    if the requested quality is unavailable.
    """
    stream_data_json = room_info["stream_url"]["live_core_sdk_data"]["pull_data"]["stream_data"]
    stream_data = json.loads(stream_data_json)
    available = stream_data.get("data", {})

    # Build fallback order: requested quality first, then standard order
    candidates = [quality] + [q for q in QUALITY_FALLBACK_ORDER if q != quality]

    for q in candidates:
        if q in available and "main" in available[q]:
            url_data = available[q]["main"]
            url = url_data.get(fmt) or url_data.get("flv")
            if url:
                if q != quality:
                    logger.warning(f"Quality '{quality}' unavailable, using '{q}'")
                return url, q

    raise KeyError(
        f"No stream URL found. Requested: '{quality}'. "
        f"Available qualities: {list(available.keys())}"
    )


class StreamRecorder:
    """Manages an FFmpeg subprocess that records a live stream."""

    def __init__(self, stream_url: str, output_path: str, config: Config):
        self.stream_url = stream_url
        self.output_path = output_path
        self.config = config
        self._process: Optional[subprocess.Popen] = None
        self._start_time: float = 0.0

    @property
    def start_time(self) -> float:
        return self._start_time

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        cmd = [
            self.config.ffmpeg_path,
            "-y",
            "-loglevel", "error",
            "-i", self.stream_url,
            "-c", "copy",
        ]
        if self.config.max_duration > 0:
            cmd.extend(["-t", str(self.config.max_duration)])
        cmd.append(self.output_path)

        logger.info(f"Starting FFmpeg: {' '.join(cmd)}")
        kwargs = dict(
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # On Windows, give each FFmpeg its own process group to prevent
        # handle inheritance conflicts between concurrent recordings
        if sys.platform == "win32":
            kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            )
        self._process = subprocess.Popen(cmd, **kwargs)
        self._start_time = time.time()

    def stop(self) -> Optional[str]:
        """Stop the FFmpeg process. Returns stderr output if any."""
        if self._process is None:
            return None

        if self._process.poll() is None:
            # Terminate FFmpeg — FLV format handles truncation gracefully
            # (stdin 'q' approach is unreliable on Windows)
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)

        # Read and close stderr
        stderr_data = b""
        if self._process.stderr:
            try:
                stderr_data = self._process.stderr.read()
                self._process.stderr.close()
            except OSError:
                pass

        stderr = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""

        ret = self._process.returncode
        self._process = None
        # 0 = normal, 255 = stream end, -15 = SIGTERM (unix), 1 = terminated (windows)
        if ret and ret not in (255, -15, 1):
            logger.warning(f"FFmpeg exited with code {ret}: {stderr}")
        return stderr

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for FFmpeg to exit on its own. Returns the exit code."""
        if self._process is None:
            return -1
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        return self._process.returncode if self._process.returncode is not None else -1
