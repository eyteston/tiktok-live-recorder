# TikTok Live Recorder

[![CI](https://github.com/eyteston/tiktok-live-recorder/actions/workflows/ci.yml/badge.svg)](https://github.com/eyteston/tiktok-live-recorder/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Record TikTok live streams with real-time chat capture, overlay generation, and automatic go-live detection. Includes a full PyQt6 desktop GUI and a headless CLI for servers.

---

## Features

- **Auto-monitoring** — watches usernames and starts recording the moment they go live
- **Video + chat capture** — records the stream via FFmpeg while capturing chat, gifts, and joins in real-time
- **Chat overlay** — burns an animated ASS subtitle overlay onto the final video with per-user color coding
- **Multi-user support** — monitor and record multiple users concurrently with per-key rate limiting
- **Quality selection** — choose from `ld`, `sd`, `hd`, `uhd`, or `origin` with automatic fallback
- **Notifications** — get alerted via Discord, Telegram, or email when someone goes live
- **Desktop GUI** — full PyQt6 dark-themed interface with task management, avatar caching, and video preview
- **CLI mode** — headless operation for servers and automation
- **Docker ready** — Dockerfile and docker-compose included for containerized deployments

## Quick Start

### Prerequisites

- **Python 3.10+**
- **FFmpeg** — [install guide](https://ffmpeg.org/download.html) (must be on PATH or configured)

### Install

```bash
# Clone the repo
git clone https://github.com/eyteston/tiktok-live-recorder.git
cd tiktok-live-recorder

# Install core dependencies
pip install -r requirements.txt

# (Optional) Install GUI support
pip install PyQt6>=6.6.0

# (Optional) Install notification support
pip install aiohttp>=3.9.0
```

### Run the GUI

```bash
python -m src
```

### Run from CLI

```bash
# Record a user (auto-monitors until they go live)
python -m src username123

# Specify quality and output directory
python -m src username123 -q uhd -o ./my_recordings

# Chat-only mode (no video)
python -m src username123 --chat-only

# Record without chat overlay
python -m src username123 --no-overlay

# Use a TikTok session ID for age-restricted streams
python -m src username123 --sessionid YOUR_SESSION_ID

# See all options
python -m src --help
```

## CLI Reference

| Flag | Description | Default |
|------|-------------|---------|
| `username` | TikTok @username (with or without @) | *required* |
| `-o, --output` | Output directory | `./recordings` |
| `-q, --quality` | Video quality: `ld` `sd` `hd` `uhd` `origin` | `hd` |
| `--max-duration` | Max recording seconds (-1 = unlimited) | `-1` |
| `--font-size` | Chat overlay font size | `24` |
| `--max-lines` | Max visible chat lines in overlay | `8` |
| `--chat-duration` | Seconds each message stays visible | `5.0` |
| `--chat-position` | Overlay position | `bottom-left` |
| `--chat-opacity` | Background opacity (0.0–1.0) | `0.6` |
| `--no-overlay` | Skip overlay generation | `false` |
| `--chat-only` | Capture chat only, no video | `false` |
| `--no-gifts` | Exclude gift events | `false` |
| `--include-joins` | Include join events | `false` |
| `--no-terminal-chat` | Disable real-time chat in terminal | `false` |
| `--ffmpeg` | Custom FFmpeg path | `ffmpeg` |
| `--sessionid` | TikTok session cookie | *(none)* |
| `-v, --verbose` | Verbose logging | `false` |

## Notifications

Configure alerts in `.env` (copy from `.env.example`):

**Discord** — set `DISCORD_WEBHOOK_URL` to your webhook URL

**Telegram** — set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

**Email** — set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, and `NOTIFY_EMAIL`

## Docker

```bash
# Build
docker build -t tiktok-recorder .

# Record a user
docker run --rm -v ./recordings:/app/recordings tiktok-recorder username123

# Using docker-compose
docker compose run recorder username123
```

## Output Structure

Each recording session creates a timestamped folder:

```
recordings/
└── username_20250215_143022/
    ├── raw_video.flv       # Raw stream capture
    ├── chat_log.jsonl      # Chat messages (one JSON per line)
    ├── overlay.ass         # Generated subtitle file
    └── final_output.mp4    # Video with chat overlay burned in
```

## Project Structure

```
tiktok-live-recorder/
├── src/                    # Source code
│   ├── __main__.py         # Entry point
│   ├── recorder.py         # Main orchestrator
│   ├── stream.py           # FFmpeg stream recording
│   ├── chat.py             # Chat capture
│   ├── subtitle.py         # ASS subtitle generation
│   ├── overlay.py          # Subtitle burn-in
│   ├── notifications.py    # Discord/Telegram/email
│   ├── gui.py              # PyQt6 GUI
│   ├── gui_theme.py        # Dark theme
│   ├── gui_workers.py      # Background threads
│   ├── gui_dialogs.py      # Dialog windows
│   └── ...
├── tests/                  # Test suite
├── .github/workflows/      # CI/CD pipelines
├── Dockerfile              # Container build
├── docker-compose.yml      # Compose config
├── pyproject.toml          # Package config
├── requirements.txt        # Core dependencies
└── .env.example            # Environment template
```

## Development

```bash
# Install dev dependencies
pip install -e ".[all]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/

# Type check
mypy src/ --ignore-missing-imports
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide.

## License

[MIT](LICENSE)
