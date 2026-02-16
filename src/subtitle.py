from src.config import Config
from src.models import ChatMessage
from src.utils import seconds_to_ass_time, escape_ass_text


class SubtitleGenerator:
    """Generates ASS subtitle files from chat messages."""

    # Username colors (cycle through these for visual variety)
    USERNAME_COLORS = [
        "&H0088FF00",  # Green
        "&H00FFFF00",  # Cyan
        "&H0000FFFF",  # Yellow
        "&H00FF88FF",  # Pink
        "&H00FFAA00",  # Teal
        "&H008888FF",  # Light orange
        "&H00FF00FF",  # Magenta
        "&H0000AAFF",  # Orange
    ]

    GIFT_COLOR = "&H0000FFFF"  # Yellow for gifts
    JOIN_COLOR = "&H00888888"  # Grey for joins

    def __init__(self, config: Config):
        self.config = config

    def _get_username_color(self, username: str) -> str:
        """Deterministic color based on username hash."""
        idx = hash(username) % len(self.USERNAME_COLORS)
        return self.USERNAME_COLORS[idx]

    def _opacity_to_ass_alpha(self, opacity: float) -> str:
        """Convert 0.0-1.0 opacity to ASS alpha hex (00=opaque, FF=transparent)."""
        alpha = int((1.0 - max(0.0, min(1.0, opacity))) * 255)
        return f"{alpha:02X}"

    def _build_header(self, video_width: int, video_height: int) -> str:
        bg_alpha = self._opacity_to_ass_alpha(self.config.chat_opacity)
        font_size = self.config.chat_font_size
        mx = self.config.chat_margin_x
        my = self.config.chat_margin_y

        return (
            "[Script Info]\n"
            "Title: TikTok Live Chat Overlay\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {video_width}\n"
            f"PlayResY: {video_height}\n"
            "WrapStyle: 0\n"
            "ScaledBorderAndShadow: yes\n"
            "\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: ChatBox,Segoe UI,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H{bg_alpha}000000,"
            f"0,0,0,0,100,100,0,0,3,2,0,7,{mx},{mx},{my},1\n"
            f"Style: GiftBox,Segoe UI,{font_size},&H0000FFFF,&H000000FF,&H00000000,&H{bg_alpha}000000,"
            f"1,0,0,0,100,100,0,0,3,2,0,7,{mx},{mx},{my},1\n"
            "\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )

    def _calculate_position(
        self, slot: int, video_width: int, video_height: int
    ) -> tuple[int, int]:
        """Calculate x,y position for a chat message at a given slot (0=bottom)."""
        line_height = self.config.chat_font_size + 8
        margin_x = self.config.chat_margin_x
        margin_y = self.config.chat_margin_y

        pos = self.config.chat_position
        if pos.endswith("left"):
            x = margin_x
        else:
            x = video_width - margin_x

        if pos.startswith("bottom"):
            y = video_height - margin_y - (slot * line_height)
        else:
            y = margin_y + (slot * line_height)

        return x, y

    def _format_comment(self, msg: ChatMessage) -> str:
        color = self._get_username_color(msg.username)
        username = escape_ass_text(msg.username)
        content = escape_ass_text(msg.content)
        return f"{{\\b1\\1c{color}}}@{username} {{\\b0\\1c&H00FFFFFF&}}{content}"

    def _format_gift(self, msg: ChatMessage) -> str:
        username = escape_ass_text(msg.username)
        content = escape_ass_text(msg.content)
        return f"{{\\b1\\1c{self.GIFT_COLOR}}}@{username} {{\\b0}}{content}"

    def _format_join(self, msg: ChatMessage) -> str:
        username = escape_ass_text(msg.username)
        return f"{{\\1c{self.JOIN_COLOR}}}@{username} joined"

    def _format_message(self, msg: ChatMessage) -> str:
        if msg.event_type == "gift":
            return self._format_gift(msg)
        elif msg.event_type == "join":
            return self._format_join(msg)
        return self._format_comment(msg)

    def generate(
        self, messages: list[ChatMessage], video_width: int = 1920, video_height: int = 1080
    ) -> str:
        """Generate complete ASS subtitle content from chat messages."""
        lines = [self._build_header(video_width, video_height)]
        duration = self.config.chat_display_duration

        for i, msg in enumerate(messages):
            start = msg.timestamp
            end = msg.timestamp + duration

            # Count how many messages are visible at this message's start time
            visible = [
                m for m in messages[:i]
                if m.timestamp + duration > start
            ]
            slot = len(visible)
            slot = min(slot, self.config.chat_max_lines - 1)

            x, y = self._calculate_position(slot, video_width, video_height)

            start_str = seconds_to_ass_time(max(0, start))
            end_str = seconds_to_ass_time(end)

            style = "GiftBox" if msg.event_type == "gift" else "ChatBox"
            text = self._format_message(msg)

            alignment = "\\an7" if self.config.chat_position.endswith("left") else "\\an9"
            line = (
                f"Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,"
                f"{{{alignment}\\pos({x},{y})\\fad(200,500)}}{text}"
            )
            lines.append(line)

        return "\n".join(lines) + "\n"

    def write(
        self,
        messages: list[ChatMessage],
        output_path: str,
        video_width: int = 1920,
        video_height: int = 1080,
    ) -> None:
        content = self.generate(messages, video_width, video_height)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
