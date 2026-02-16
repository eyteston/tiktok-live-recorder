# Contributing to TikTok Live Recorder

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/eyteston/tiktok-live-recorder.git
cd tiktok-live-recorder

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install all dependencies (including dev tools)
pip install -e ".[all]"

# Copy the example env file
cp .env.example .env
```

## Running Tests

```bash
pytest tests/ -v
```

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src/          # Lint
ruff format src/         # Format
```

## Pull Request Process

1. Fork the repo and create your branch from `main`
2. Add tests for any new functionality
3. Make sure all tests pass (`pytest`)
4. Make sure linting passes (`ruff check src/`)
5. Update the README if you changed any public-facing behavior
6. Open a PR with a clear description of what changed and why

## Project Structure

```
src/
├── __init__.py          # Package init
├── __main__.py          # Entry point (GUI or CLI)
├── cli.py               # Argument parser
├── config.py            # Config dataclass
├── models.py            # ChatMessage, RecordingSession
├── recorder.py          # Main orchestrator
├── stream.py            # FFmpeg stream recording
├── chat.py              # TikTok chat capture
├── subtitle.py          # ASS subtitle generation
├── overlay.py           # FFmpeg subtitle burn-in
├── utils.py             # Shared utilities
├── notifications.py     # Discord/Telegram/email alerts
├── rate_limiter.py      # Per-key rate limiting
├── gui.py               # PyQt6 main window
├── gui_theme.py         # Dark theme styles
├── gui_workers.py       # Background threads
└── gui_dialogs.py       # Dialog windows
```

## Reporting Bugs

Open an issue with:
- Your OS and Python version
- Steps to reproduce
- Expected vs actual behavior
- Any error output or logs
