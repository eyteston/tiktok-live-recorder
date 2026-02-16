import glob
import os
import re
import subprocess
import sys


def _find_ffmpeg_winget() -> str | None:
    """Search for FFmpeg installed via winget."""
    base = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    pattern = os.path.join(base, "Gyan.FFmpeg*", "ffmpeg-*", "bin", "ffmpeg.exe")
    matches = glob.glob(pattern)
    if matches:
        return matches[0]
    return None


def find_ffmpeg(ffmpeg_path: str = "ffmpeg") -> str | None:
    """Find a working ffmpeg binary. Returns the path if found, None otherwise."""
    # Try the provided path first (could be "ffmpeg" on PATH or a custom path)
    try:
        run_kwargs = dict(capture_output=True, text=True, timeout=10)
        if sys.platform == "win32":
            run_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            **run_kwargs,  # type: ignore[call-overload]
        )
        if result.returncode == 0:
            return ffmpeg_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # On Windows, check common install locations
    if os.name == "nt":
        winget_path = _find_ffmpeg_winget()
        if winget_path and os.path.isfile(winget_path):
            return winget_path

    return None


def ensure_ffmpeg(ffmpeg_path: str = "ffmpeg") -> bool:
    return find_ffmpeg(ffmpeg_path) is not None


def seconds_to_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def escape_ass_text(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = text.replace("\n", "\\N")
    return text


def normalize_path_for_ffmpeg(path: str) -> str:
    path = path.replace("\\", "/")
    # Escape colon after drive letter for FFmpeg filter chains on Windows
    path = re.sub(r"^([A-Za-z]):", r"\1\\:", path)
    return path


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip()


def format_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
