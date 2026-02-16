"""Shared fixtures for TikTok Live Recorder tests."""

import pytest

from src.config import Config
from src.models import ChatMessage


@pytest.fixture
def default_config():
    """A Config with sensible test defaults."""
    return Config(
        unique_id="testuser",
        output_dir="/tmp/test_recordings",
        quality="hd",
        session_id="",
        rate_limit_delay=1,
    )


@pytest.fixture
def sample_messages():
    """A list of sample ChatMessage objects for testing."""
    return [
        ChatMessage(
            timestamp=0.0,
            absolute_time=1700000000.0,
            username="alice",
            nickname="Alice",
            content="Hello everyone!",
            event_type="comment",
        ),
        ChatMessage(
            timestamp=2.5,
            absolute_time=1700000002.5,
            username="bob",
            nickname="Bob",
            content="sent Rose x5",
            event_type="gift",
            extra={"gift_name": "Rose", "count": 5},
        ),
        ChatMessage(
            timestamp=5.0,
            absolute_time=1700000005.0,
            username="charlie",
            nickname="Charlie",
            content="joined",
            event_type="join",
        ),
        ChatMessage(
            timestamp=8.0,
            absolute_time=1700000008.0,
            username="alice",
            nickname="Alice",
            content="This stream is great!",
            event_type="comment",
        ),
    ]
