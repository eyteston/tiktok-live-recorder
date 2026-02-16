"""Tests for utility functions."""

from src.utils import (
    seconds_to_ass_time,
    escape_ass_text,
    normalize_path_for_ffmpeg,
    sanitize_filename,
    format_duration,
)


class TestSecondsToAssTime:
    def test_zero(self):
        assert seconds_to_ass_time(0) == "0:00:00.00"

    def test_simple(self):
        assert seconds_to_ass_time(65.5) == "0:01:05.50"

    def test_hours(self):
        assert seconds_to_ass_time(3661.25) == "1:01:01.25"

    def test_large(self):
        assert seconds_to_ass_time(7200) == "2:00:00.00"


class TestEscapeAssText:
    def test_backslash(self):
        assert escape_ass_text("a\\b") == "a\\\\b"

    def test_braces(self):
        assert escape_ass_text("{bold}") == "\\{bold\\}"

    def test_newline(self):
        assert escape_ass_text("line1\nline2") == "line1\\Nline2"

    def test_no_escape_needed(self):
        assert escape_ass_text("Hello world") == "Hello world"


class TestNormalizePathForFfmpeg:
    def test_backslash_to_forward(self):
        assert normalize_path_for_ffmpeg("C:\\Users\\file.ass") == "C\\:/Users/file.ass"

    def test_unix_path_unchanged(self):
        assert normalize_path_for_ffmpeg("/home/user/file.ass") == "/home/user/file.ass"


class TestSanitizeFilename:
    def test_removes_special_chars(self):
        assert sanitize_filename('user<>:"/\\|?*name') == "user_________name"

    def test_normal_name(self):
        assert sanitize_filename("cool_streamer123") == "cool_streamer123"


class TestFormatDuration:
    def test_seconds(self):
        assert format_duration(45) == "0:45"

    def test_minutes(self):
        assert format_duration(125) == "2:05"

    def test_hours(self):
        assert format_duration(3665) == "1:01:05"
