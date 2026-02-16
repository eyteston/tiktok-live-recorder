import json
import logging
import time

from rich.console import Console
from TikTokLive.client.client import TikTokLiveClient
from TikTokLive.events.custom_events import ConnectEvent, DisconnectEvent, LiveEndEvent
from TikTokLive.events.proto_events import CommentEvent, GiftEvent, JoinEvent

from src.config import Config
from src.models import ChatMessage

logger = logging.getLogger(__name__)
console = Console()


class ChatCapture:
    """Captures TikTok live chat messages with timestamps."""

    def __init__(self, client: TikTokLiveClient, config: Config, log_path: str, on_message=None):
        self.client = client
        self.config = config
        self.log_path = log_path
        self.on_message = on_message  # Optional callback: fn(ChatMessage)
        self.messages: list[ChatMessage] = []
        self.start_time: float = 0.0
        self.connected: bool = False
        self.stream_ended: bool = False
        self._log_file = None

    def _register_events(self) -> None:
        self.client.add_listener(ConnectEvent, self._on_connect)
        self.client.add_listener(DisconnectEvent, self._on_disconnect)
        self.client.add_listener(LiveEndEvent, self._on_live_end)
        self.client.add_listener(CommentEvent, self._on_comment)

        if self.config.include_gifts:
            self.client.add_listener(GiftEvent, self._on_gift)

        if self.config.include_joins:
            self.client.add_listener(JoinEvent, self._on_join)

    async def start(self) -> None:
        self._log_file = open(self.log_path, "w", encoding="utf-8")
        self._register_events()

    def stop(self) -> None:
        if self._log_file and not self._log_file.closed:
            self._log_file.close()

    def _add_message(self, msg: ChatMessage) -> None:
        self.messages.append(msg)
        if self._log_file and not self._log_file.closed:
            self._log_file.write(json.dumps(msg.to_dict(), ensure_ascii=False) + "\n")
            self._log_file.flush()
        if self.on_message:
            try:
                self.on_message(msg)
            except Exception:
                pass

    def _display(self, msg: ChatMessage) -> None:
        if not self.config.terminal_chat:
            return
        if msg.event_type == "comment":
            console.print(f"[bold green]@{msg.username}[/]: {msg.content}")
        elif msg.event_type == "gift":
            gift_name = msg.extra.get("gift_name", "gift")
            count = msg.extra.get("count", 1)
            console.print(f"[bold yellow]@{msg.username}[/] sent [cyan]{gift_name}[/] x{count}")
        elif msg.event_type == "join":
            console.print(f"[dim]@{msg.username} joined[/]")

    async def _on_connect(self, event: ConnectEvent) -> None:
        self.start_time = time.time()
        self.connected = True
        logger.info(f"Connected to @{event.unique_id} (room {event.room_id})")
        if self.config.terminal_chat:
            console.print(f"[bold]Connected to @{event.unique_id}[/] - capturing chat...")

    async def _on_disconnect(self, event: DisconnectEvent) -> None:
        logger.info("Disconnected from stream")
        if self.config.terminal_chat:
            console.print("[bold red]Disconnected from stream[/]")

    async def _on_live_end(self, event: LiveEndEvent) -> None:
        self.stream_ended = True
        logger.info("Stream has ended")
        if self.config.terminal_chat:
            console.print("[bold red]Stream has ended[/]")

    async def _on_comment(self, event: CommentEvent) -> None:
        now = time.time()
        if self.start_time == 0.0:
            self.start_time = now
        msg = ChatMessage(
            timestamp=now - self.start_time,
            absolute_time=now,
            username=event.user.nickname or "unknown",
            nickname=event.user.nickname or "unknown",
            content=event.comment,
            event_type="comment",
        )
        self._add_message(msg)
        self._display(msg)

    async def _on_gift(self, event: GiftEvent) -> None:
        # Only count non-streaking gifts (final count) or non-streakable gifts
        try:
            if event.streaking:
                return
        except AttributeError:
            pass  # TikTokLive 6.6.5 bug: Gift proto missing 'streakable' field

        now = time.time()
        if self.start_time == 0.0:
            self.start_time = now
        gift_name = ""
        try:
            gift_name = event.gift.name if event.gift else ""
        except Exception:
            gift_name = "gift"

        msg = ChatMessage(
            timestamp=now - self.start_time,
            absolute_time=now,
            username=event.user.nickname or "unknown",
            nickname=event.user.nickname or "unknown",
            content=f"sent {gift_name} x{event.repeat_count}",
            event_type="gift",
            extra={"gift_name": gift_name, "count": event.repeat_count},
        )
        self._add_message(msg)
        self._display(msg)

    async def _on_join(self, event: JoinEvent) -> None:
        now = time.time()
        if self.start_time == 0.0:
            self.start_time = now
        msg = ChatMessage(
            timestamp=now - self.start_time,
            absolute_time=now,
            username=event.user.nickname or "unknown",
            nickname=event.user.nickname or "unknown",
            content="joined",
            event_type="join",
        )
        self._add_message(msg)
        self._display(msg)
