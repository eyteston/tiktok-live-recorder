"""Tests for the CLI argument parser."""

from src.cli import parse_args


def test_basic_args():
    config = parse_args(["someuser"])
    assert config.unique_id == "someuser"
    assert config.quality == "hd"
    assert config.output_dir == "./recordings"


def test_strip_at_sign():
    config = parse_args(["@someuser"])
    assert config.unique_id == "someuser"


def test_quality_flag():
    config = parse_args(["user", "-q", "uhd"])
    assert config.quality == "uhd"


def test_output_dir():
    config = parse_args(["user", "-o", "/tmp/my_recordings"])
    assert config.output_dir == "/tmp/my_recordings"


def test_no_overlay():
    config = parse_args(["user", "--no-overlay"])
    assert config.no_overlay is True


def test_chat_only():
    config = parse_args(["user", "--chat-only"])
    assert config.chat_only is True


def test_max_duration():
    config = parse_args(["user", "--max-duration", "3600"])
    assert config.max_duration == 3600


def test_verbose():
    config = parse_args(["user", "-v"])
    assert config.verbose is True


def test_session_id():
    config = parse_args(["user", "--sessionid", "abc123"])
    assert config.session_id == "abc123"


def test_no_gifts():
    config = parse_args(["user", "--no-gifts"])
    assert config.include_gifts is False


def test_include_joins():
    config = parse_args(["user", "--include-joins"])
    assert config.include_joins is True
