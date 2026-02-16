import asyncio
import sys


def main():
    # Launch GUI if no args or --gui flag
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        from src.gui import launch_gui

        launch_gui()
    else:
        from src.cli import parse_args
        from src.recorder import TikTokRecorder

        config = parse_args(sys.argv[1:])
        recorder = TikTokRecorder(config)
        try:
            asyncio.run(recorder.run())
        except KeyboardInterrupt:
            print("\nRecording stopped.")


if __name__ == "__main__":
    main()
