"""Tests for the notification system."""

import pytest
from src.notifications import NotificationManager


def test_no_channels_configured():
    mgr = NotificationManager()
    assert mgr.has_any_configured is False


def test_discord_configured():
    mgr = NotificationManager(discord_webhook="https://discord.com/api/webhooks/123/abc")
    assert mgr.has_any_configured is True


def test_telegram_configured():
    mgr = NotificationManager(telegram_token="123:ABC", telegram_chat_id="456")
    assert mgr.has_any_configured is True


def test_email_configured():
    mgr = NotificationManager(smtp_host="smtp.gmail.com", notify_email="test@test.com")
    assert mgr.has_any_configured is True


def test_cooldown():
    mgr = NotificationManager()
    mgr._cooldown_seconds = 60

    # First check should pass
    assert mgr._check_cooldown("user1") is True
    # Immediate second check should be blocked
    assert mgr._check_cooldown("user1") is False
    # Different user should pass
    assert mgr._check_cooldown("user2") is True


@pytest.mark.asyncio
async def test_notify_live_no_channels():
    """notify_live should complete without error when nothing is configured."""
    mgr = NotificationManager()
    await mgr.notify_live("testuser")  # Should not raise
