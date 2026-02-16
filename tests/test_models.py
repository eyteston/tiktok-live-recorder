"""Tests for data models."""

from src.models import ChatMessage, RecordingSession


def test_chat_message_to_dict():
    msg = ChatMessage(
        timestamp=1.5,
        absolute_time=1700000001.5,
        username="alice",
        nickname="Alice",
        content="Hello!",
        event_type="comment",
    )
    d = msg.to_dict()
    assert d["username"] == "alice"
    assert d["content"] == "Hello!"
    assert d["event_type"] == "comment"
    assert d["timestamp"] == 1.5
    assert d["extra"] == {}


def test_chat_message_with_extras():
    msg = ChatMessage(
        timestamp=3.0,
        absolute_time=1700000003.0,
        username="bob",
        nickname="Bob",
        content="sent Rose x5",
        event_type="gift",
        extra={"gift_name": "Rose", "count": 5},
    )
    d = msg.to_dict()
    assert d["extra"]["gift_name"] == "Rose"
    assert d["extra"]["count"] == 5


def test_recording_session_defaults():
    session = RecordingSession(unique_id="testuser")
    assert session.unique_id == "testuser"
    assert session.room_id is None
    assert session.output_dir == ""
    assert session.quality == "hd"
