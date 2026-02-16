"""Tests for the Config dataclass."""

from src.config import Config


def test_default_config():
    c = Config()
    assert c.unique_id == ""
    assert c.quality == "hd"
    assert c.format == "flv"
    assert c.output_format == "mp4"
    assert c.max_duration == -1
    assert c.no_overlay is True
    assert c.chat_only is False
    assert c.rate_limit_delay == 10


def test_config_custom():
    c = Config(unique_id="streamer1", quality="uhd", max_duration=3600)
    assert c.unique_id == "streamer1"
    assert c.quality == "uhd"
    assert c.max_duration == 3600
