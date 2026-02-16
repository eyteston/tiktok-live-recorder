"""Notification system for TikTok Live Recorder.

Sends alerts when a monitored user goes live via Discord, Telegram, or email.
All notification methods are optional — configure only what you need via .env or settings.
"""

import asyncio
import logging
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationManager:
    """Dispatches go-live notifications to configured channels."""

    def __init__(
        self,
        discord_webhook: str = "",
        telegram_token: str = "",
        telegram_chat_id: str = "",
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_pass: str = "",
        notify_email: str = "",
    ):
        self.discord_webhook = discord_webhook or os.getenv("DISCORD_WEBHOOK_URL", "")
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        self.smtp_pass = smtp_pass or os.getenv("SMTP_PASS", "")
        self.notify_email = notify_email or os.getenv("NOTIFY_EMAIL", "")
        self._cooldowns: dict[str, float] = {}
        self._cooldown_seconds = 300  # 5 min between duplicate notifications

    @property
    def has_any_configured(self) -> bool:
        return bool(self.discord_webhook or self.telegram_token or self.smtp_host)

    def _check_cooldown(self, username: str) -> bool:
        """Returns True if notification should be sent (not in cooldown)."""
        import time
        now = time.time()
        last = self._cooldowns.get(username, 0)
        if now - last < self._cooldown_seconds:
            return False
        self._cooldowns[username] = now
        return True

    async def notify_live(self, username: str, room_id: Optional[int] = None) -> None:
        """Send go-live notification to all configured channels."""
        if not self._check_cooldown(username):
            logger.debug(f"Notification cooldown active for @{username}")
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tiktok_url = f"https://www.tiktok.com/@{username}/live"
        message = f"@{username} is now LIVE on TikTok!\n{tiktok_url}\n{timestamp}"

        tasks = []
        if self.discord_webhook:
            tasks.append(self._send_discord(username, tiktok_url, timestamp))
        if self.telegram_token and self.telegram_chat_id:
            tasks.append(self._send_telegram(message))
        if self.smtp_host and self.notify_email:
            tasks.append(self._send_email(username, tiktok_url, timestamp))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Notification error: {result}")

    async def _send_discord(self, username: str, url: str, timestamp: str) -> None:
        """Send a Discord webhook notification with embed."""
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed — Discord notifications disabled. "
                           "Install with: pip install aiohttp")
            return

        embed = {
            "title": f"🔴 @{username} is LIVE!",
            "description": f"[Watch on TikTok]({url})",
            "color": 0xFF0050,  # TikTok red
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "TikTok Live Recorder"},
        }
        payload = {"embeds": [embed]}

        async with aiohttp.ClientSession() as session:
            async with session.post(self.discord_webhook, json=payload) as resp:
                if resp.status not in (200, 204):
                    text = await resp.text()
                    logger.error(f"Discord webhook failed ({resp.status}): {text}")
                else:
                    logger.info(f"Discord notification sent for @{username}")

    async def _send_telegram(self, message: str) -> None:
        """Send a Telegram bot message."""
        try:
            import aiohttp
        except ImportError:
            logger.warning("aiohttp not installed — Telegram notifications disabled. "
                           "Install with: pip install aiohttp")
            return

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Telegram send failed ({resp.status}): {text}")
                else:
                    logger.info("Telegram notification sent")

    async def _send_email(self, username: str, url: str, timestamp: str) -> None:
        """Send an email notification via SMTP."""
        subject = f"TikTok LIVE: @{username} is streaming!"
        body = (
            f"@{username} just went live on TikTok.\n\n"
            f"Watch: {url}\n"
            f"Detected at: {timestamp}\n\n"
            f"— TikTok Live Recorder"
        )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.smtp_user
        msg["To"] = self.notify_email

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._smtp_send, msg)
        logger.info(f"Email notification sent for @{username}")

    def _smtp_send(self, msg: MIMEText) -> None:
        """Blocking SMTP send (run in executor)."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
