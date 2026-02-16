import argparse
from src.config import Config


def parse_args(argv: list[str]) -> Config:
    parser = argparse.ArgumentParser(
        prog="tiktok-live-recorder",
        description="Record TikTok live streams with chat overlay",
    )

    parser.add_argument(
        "username",
        help="TikTok @username (with or without @)",
    )
    parser.add_argument(
        "-o", "--output",
        default="./recordings",
        help="Output directory (default: ./recordings/)",
    )
    parser.add_argument(
        "-q", "--quality",
        choices=["ld", "sd", "hd", "uhd", "origin"],
        default="hd",
        help="Video quality (default: hd)",
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=-1,
        help="Max recording duration in seconds (default: unlimited)",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=24,
        help="Chat overlay font size (default: 24)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=8,
        help="Max visible chat lines (default: 8)",
    )
    parser.add_argument(
        "--chat-duration",
        type=float,
        default=5.0,
        help="Seconds each chat message stays visible (default: 5.0)",
    )
    parser.add_argument(
        "--chat-position",
        choices=["bottom-left", "bottom-right", "top-left", "top-right"],
        default="bottom-left",
        help="Chat overlay position (default: bottom-left)",
    )
    parser.add_argument(
        "--chat-opacity",
        type=float,
        default=0.6,
        help="Chat background opacity 0.0-1.0 (default: 0.6)",
    )
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="Record video + chat log only, skip overlay generation",
    )
    parser.add_argument(
        "--chat-only",
        action="store_true",
        help="Capture chat only, no video recording",
    )
    parser.add_argument(
        "--no-gifts",
        action="store_true",
        help="Exclude gift events from overlay",
    )
    parser.add_argument(
        "--include-joins",
        action="store_true",
        help="Include join events in overlay",
    )
    parser.add_argument(
        "--no-terminal-chat",
        action="store_true",
        help="Disable real-time chat display in terminal",
    )
    parser.add_argument(
        "--ffmpeg",
        default="ffmpeg",
        help="Custom FFmpeg binary path",
    )
    parser.add_argument(
        "--sessionid",
        default="",
        help="TikTok sessionid cookie for age-restricted/login-required streams",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging output",
    )

    args = parser.parse_args(argv)

    # Strip @ from username
    unique_id = args.username.lstrip("@").strip()

    return Config(
        unique_id=unique_id,
        output_dir=args.output,
        quality=args.quality,
        max_duration=args.max_duration,
        chat_font_size=args.font_size,
        chat_max_lines=args.max_lines,
        chat_display_duration=args.chat_duration,
        chat_position=args.chat_position,
        chat_opacity=args.chat_opacity,
        no_overlay=args.no_overlay,
        chat_only=args.chat_only,
        include_gifts=not args.no_gifts,
        include_joins=args.include_joins,
        terminal_chat=not args.no_terminal_chat,
        ffmpeg_path=args.ffmpeg,
        session_id=args.sessionid,
        verbose=args.verbose,
    )
