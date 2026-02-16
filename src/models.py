from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChatMessage:
    timestamp: float  # Seconds since recording start
    absolute_time: float  # Unix timestamp
    username: str
    nickname: str
    content: str
    event_type: str  # "comment", "gift", "join"
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "absolute_time": self.absolute_time,
            "username": self.username,
            "nickname": self.nickname,
            "content": self.content,
            "event_type": self.event_type,
            "extra": self.extra,
        }


@dataclass
class RecordingSession:
    unique_id: str
    room_id: Optional[int] = None
    start_time: float = 0.0
    output_dir: str = ""
    raw_video_path: str = ""
    chat_log_path: str = ""
    subtitle_path: str = ""
    final_video_path: str = ""
    quality: str = "hd"
    format: str = "flv"
