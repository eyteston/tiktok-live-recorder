from dataclasses import dataclass


@dataclass
class Config:
    unique_id: str = ""
    output_dir: str = "./recordings"
    quality: str = "hd"
    format: str = "flv"
    output_format: str = "mp4"
    max_duration: int = -1  # -1 = infinite
    chat_font_size: int = 24
    chat_max_lines: int = 8
    chat_display_duration: float = 5.0
    chat_position: str = "bottom-left"
    chat_margin_x: int = 20
    chat_margin_y: int = 50
    chat_opacity: float = 0.6
    include_gifts: bool = True
    include_joins: bool = True
    terminal_chat: bool = True
    no_overlay: bool = True
    chat_only: bool = False
    ffmpeg_path: str = "ffmpeg"
    session_id: str = ""
    rate_limit_delay: int = 10  # seconds between API requests (global)
    verbose: bool = False
    avatar_url: str = ""  # TikTok profile picture URL (cached)
    auto_monitor: bool = True  # auto-start monitoring when app opens
