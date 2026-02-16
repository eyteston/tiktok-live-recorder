"""Tests for the TikTokRecorder (unit-level, no network)."""

from src.recorder import TikTokRecorder
from src.config import Config


class TestParseSession:
    def test_bare_session_id(self):
        sid, idc = TikTokRecorder._parse_session("abc123def")
        assert sid == "abc123def"
        assert idc == "useast5"

    def test_cookie_string(self):
        cookies = "sessionid=mysession; tt-target-idc=alisg; other=value"
        sid, idc = TikTokRecorder._parse_session(cookies)
        assert sid == "mysession"
        assert idc == "alisg"

    def test_cookie_string_with_sid_tt(self):
        cookies = "sid_tt=mysid; tt-target-idc=useast2"
        sid, idc = TikTokRecorder._parse_session(cookies)
        assert sid == "mysid"
        assert idc == "useast2"

    def test_empty_string(self):
        sid, idc = TikTokRecorder._parse_session("")
        assert sid == ""
        assert idc == "useast5"

    def test_whitespace(self):
        sid, idc = TikTokRecorder._parse_session("  abc123  ")
        assert sid == "abc123"
        assert idc == "useast5"


class TestRecorderInit:
    def test_creates_with_config(self):
        config = Config(unique_id="testuser")
        recorder = TikTokRecorder(config)
        assert recorder.config.unique_id == "testuser"
        assert recorder._stop_requested is False

    def test_request_stop(self):
        config = Config(unique_id="testuser")
        recorder = TikTokRecorder(config)
        recorder.request_stop()
        assert recorder._stop_requested is True
