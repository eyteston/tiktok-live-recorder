import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime

from rich.console import Console
from TikTokLive.client.client import TikTokLiveClient
from TikTokLive.client.errors import SignatureRateLimitError, UserNotFoundError, UserOfflineError

from src.chat import ChatCapture
from src.config import Config
from src.models import ChatMessage, RecordingSession
from src.overlay import OverlayEncoder
from src.stream import StreamRecorder, extract_stream_url
from src.subtitle import SubtitleGenerator
from src.utils import find_ffmpeg, format_duration, sanitize_filename

logger = logging.getLogger(__name__)
console = Console()

# Whitelist the Euler Stream sign server for authenticated TikTokLive connections.
# Set once at module level so concurrent recordings don't race on os.environ.
os.environ["WHITELIST_AUTHENTICATED_SESSION_ID_HOST"] = "tiktok.eulerstream.com"


class TikTokRecorder:
    """Main orchestrator that coordinates stream recording, chat capture, and overlay."""

    def __init__(
        self, config: Config, on_status=None, on_chat=None, on_log=None, on_stream_url=None, rate_limiter=None
    ):
        self.config = config
        self.session: RecordingSession = RecordingSession(unique_id=config.unique_id)
        self._on_status = on_status  # fn(status_str)
        self._on_chat = on_chat  # fn(ChatMessage)
        self._on_log = on_log  # fn(text_str)
        self._on_stream_url = on_stream_url  # fn(url_str)
        self._rate_limiter = rate_limiter
        self._stop_requested = False
        self._encoder: OverlayEncoder | None = None

    def request_stop(self):
        self._stop_requested = True
        if self._encoder and self._encoder.is_running:
            self._encoder.cancel()

    @staticmethod
    def _parse_session(raw: str) -> tuple[str, str]:
        """Parse session input — accepts a bare session ID or a full cookie string.

        Returns (session_id, tt_target_idc).
        """
        raw = raw.strip()
        # If it looks like a cookie string (contains '=' and ';'), parse it
        if ";" in raw and "=" in raw:
            cookies = {}
            for part in raw.split(";"):
                part = part.strip()
                if "=" in part:
                    key, _, val = part.partition("=")
                    cookies[key.strip()] = val.strip()
            sid = cookies.get("sessionid", cookies.get("sid_tt", ""))
            idc = cookies.get("tt-target-idc", "useast5")
            return sid, idc
        # Otherwise treat the whole string as a session ID
        return raw, "useast5"

    def _create_client(self) -> TikTokLiveClient:
        """Create a TikTokLiveClient with session config applied."""
        client = TikTokLiveClient(unique_id=self.config.unique_id)
        if self.config.session_id:
            session_id, target_idc = self._parse_session(self.config.session_id)
            client._web.set_session(session_id=session_id, tt_target_idc=target_idc)
        return client

    def _emit_status(self, status: str):
        if self._on_status:
            try:
                self._on_status(status)
            except Exception:
                pass

    def _emit_log(self, text: str):
        if self._on_log:
            try:
                self._on_log(text)
            except Exception:
                pass

    def _setup_output_dir(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = sanitize_filename(self.config.unique_id)
        dirname = f"{safe_name}_{timestamp}"
        self.session.output_dir = os.path.join(self.config.output_dir, dirname)
        os.makedirs(self.session.output_dir, exist_ok=True)

        self.session.raw_video_path = os.path.join(self.session.output_dir, f"raw_video.{self.config.format}")
        self.session.chat_log_path = os.path.join(self.session.output_dir, "chat_log.jsonl")
        self.session.subtitle_path = os.path.join(self.session.output_dir, "overlay.ass")
        self.session.final_video_path = os.path.join(
            self.session.output_dir, f"final_output.{self.config.output_format}"
        )

    def _cleanup_empty_dir(self, dir_path: str) -> None:
        """Remove an output directory if it contains only empty files."""
        if not dir_path or not os.path.isdir(dir_path):
            return
        try:
            all_empty = True
            for entry in os.scandir(dir_path):
                if entry.is_file() and entry.stat().st_size > 0:
                    all_empty = False
                    break
                elif entry.is_dir():
                    all_empty = False
                    break
            if all_empty:
                for entry in os.scandir(dir_path):
                    if entry.is_file():
                        os.remove(entry.path)
                os.rmdir(dir_path)
                self._log(f"Cleaned up empty output directory: {os.path.basename(dir_path)}")
        except OSError as e:
            logger.debug(f"Cleanup failed for {dir_path}: {e}")

    def _log(self, text: str) -> None:
        console.print(text)
        self._emit_log(text)

    async def run(self) -> None:
        """Monitoring loop: check if live → record → repeat until stopped."""
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        self._emit_status("checking")

        # Check FFmpeg availability (unless chat-only mode)
        if not self.config.chat_only:
            resolved = find_ffmpeg(self.config.ffmpeg_path)
            if not resolved:
                self._log("FFmpeg not found! Install FFmpeg and add to PATH.")
                self._emit_status("error")
                return
            self.config.ffmpeg_path = resolved

        if self.config.verbose:
            logger.setLevel(logging.DEBUG)

        self._log(f"Target: @{self.config.unique_id}")

        # ── Monitoring loop ──
        # Create client once and reuse for is_live() checks
        client = self._create_client()
        first_check = True
        user_not_found_count = 0

        while not self._stop_requested:
            if first_check:
                self._emit_status("checking")
                first_check = False
            else:
                self._emit_status("monitoring")

            # Rate limit: per-task acquire so tasks don't block each other
            if self._rate_limiter:
                self._rate_limiter.acquire_for(self.config.unique_id)

            if self._stop_requested:
                break

            self._log("Checking if user is live...")
            try:
                is_live = await client.is_live()
            except UserNotFoundError:
                user_not_found_count += 1
                if user_not_found_count >= 3:
                    self._log(
                        f"User @{self.config.unique_id} not found after {user_not_found_count} consecutive checks. Stopping."
                    )
                    self._emit_status("error")
                    try:
                        await client.close()
                    except Exception:
                        pass
                    return  # Fatal — user genuinely doesn't exist
                self._log(f"User @{self.config.unique_id} not found (attempt {user_not_found_count}/3). Retrying...")
                try:
                    await client.close()
                except Exception:
                    pass
                client = self._create_client()
                await self._interruptible_sleep(self.config.rate_limit_delay)
                continue
            except SignatureRateLimitError as e:
                self._log(f"Rate limited by TikTok. Waiting {e.retry_after}s...")
                await self._interruptible_sleep(e.retry_after)
                continue
            except Exception as e:
                self._log(f"Error checking live status (transient API issue, retrying): {e}")
                # Recreate client on connection errors
                try:
                    await client.close()
                except Exception:
                    pass
                client = self._create_client()
                await self._interruptible_sleep(self.config.rate_limit_delay)
                continue

            user_not_found_count = 0  # Reset on successful API call

            if not is_live:
                self._log(f"@{self.config.unique_id} is not live. Monitoring...")
                self._emit_status("monitoring")
                await self._interruptible_sleep(self.config.rate_limit_delay)
                continue

            # ── User IS live — start recording ──
            self._log(f"@{self.config.unique_id} is live!")
            await self._record_session(client)

            # After recording, create fresh client for next monitoring cycle
            if not self._stop_requested:
                self._log("Recording ended. Returning to monitoring...")
                self.session = RecordingSession(unique_id=self.config.unique_id)
                client = self._create_client()

        # Clean exit
        if self._stop_requested:
            self._log("Monitoring stopped by user.")
        try:
            await client.close()
        except Exception:
            pass
        self._emit_status("done")

    async def _record_session(self, client: TikTokLiveClient) -> None:
        """Handle a single recording session when user is confirmed live."""
        stream_recorder = None
        ffmpeg_start = time.time()
        chat = None

        try:
            # ── Phase 1: Validate stream BEFORE creating any files ──
            if self._rate_limiter:
                self._rate_limiter.acquire_for(self.config.unique_id)

            task = await client.start(
                fetch_room_info=True,
                fetch_gift_info=True,
            )

            self.session.room_id = client.room_id
            stream_url = None
            actual_quality = None

            if not self.config.chat_only:
                room_info = client.room_info
                if room_info is None:
                    self._log("Failed to fetch room info for stream URL.")
                    await client.disconnect(close_client=True)
                    return

                try:
                    stream_url, actual_quality = extract_stream_url(room_info, self.config.quality, self.config.format)
                except (KeyError, json.JSONDecodeError) as e:
                    self._log(f"Failed to extract stream URL: {e}")
                    await client.disconnect(close_client=True)
                    return

            # ── Phase 2: Validation passed — create output dir and files ──
            self._setup_output_dir()
            self._log(f"Output: {self.session.output_dir}")

            chat = ChatCapture(
                client,
                self.config,
                self.session.chat_log_path,
                on_message=self._on_chat,
            )
            await chat.start()

            if not self.config.chat_only:
                logger.debug(f"Stream URL: {stream_url}")
                if self._on_stream_url:
                    try:
                        self._on_stream_url(stream_url)
                    except Exception:
                        pass
                assert stream_url is not None
                stream_recorder = StreamRecorder(stream_url, self.session.raw_video_path, self.config)
                stream_recorder.start()
                self._log(f"Recording video (quality: {actual_quality}) + capturing chat...")
            else:
                self._log("Capturing chat only (no video recording)...")

            self._emit_status("recording")

            ffmpeg_start = stream_recorder.start_time if stream_recorder else time.time()
            ws_reconnect_attempts = 0
            max_ws_reconnects = 5

            while not self._stop_requested:
                if stream_recorder and not stream_recorder.is_alive:
                    self._log("Stream ended (FFmpeg exited).")
                    break
                if task.done():
                    if not stream_recorder:
                        self._log("WebSocket disconnected.")
                        break
                    if ws_reconnect_attempts < max_ws_reconnects:
                        ws_reconnect_attempts += 1
                        self._log(f"Chat disconnected, reconnecting ({ws_reconnect_attempts}/{max_ws_reconnects})...")
                        try:
                            await asyncio.sleep(3)
                            client = self._create_client()
                            chat.client = client
                            chat._register_events()
                            task = await client.start(fetch_room_info=False, fetch_gift_info=False)
                            self._log("Chat reconnected!")
                            ws_reconnect_attempts = 0
                        except Exception as e:
                            self._log(f"Chat reconnect failed: {e}")
                    else:
                        self._log("Chat reconnect limit reached. Video still recording (no chat).")
                        ws_reconnect_attempts = max_ws_reconnects + 1
                await asyncio.sleep(0.5)

        except UserOfflineError:
            self._log(f"@{self.config.unique_id} went offline.")
        except SignatureRateLimitError as e:
            self._log(f"Rate limited. Retry in {e.retry_after}s.")
        except KeyboardInterrupt:
            self._log("Stopping recording...")
        except Exception as e:
            self._log(f"Error during recording: {e}")
            logger.exception("Recording error")
        finally:
            if stream_recorder and stream_recorder.is_alive:
                self._log("Stopping FFmpeg...")
                try:
                    stderr = stream_recorder.stop()
                    if stderr and self.config.verbose:
                        self._log(f"FFmpeg: {stderr.strip()}")
                except Exception as e:
                    self._log(f"Error stopping FFmpeg: {e}")
                    logger.exception("FFmpeg stop error")

            if chat:
                chat.stop()
            try:
                await client.disconnect(close_client=True)
            except Exception:
                pass

        # Post-processing
        try:
            duration = time.time() - (stream_recorder.start_time if stream_recorder else ffmpeg_start)
            chat_count = len(chat.messages) if chat else 0
            self._log(f"Recording complete! Duration: {format_duration(duration)}, Chat: {chat_count} msgs")

            has_video = (
                stream_recorder is not None
                and os.path.exists(self.session.raw_video_path)
                and os.path.getsize(self.session.raw_video_path) > 0
            )
            has_chat = chat is not None and len(chat.messages) > 0

            if has_chat and has_video and not self.config.no_overlay and not self._stop_requested:
                assert chat is not None
                self._emit_status("encoding")
                self._log("Generating chat overlay...")

                time_offset = chat.start_time - (stream_recorder.start_time if stream_recorder else 0)
                adjusted_messages = []
                for msg in chat.messages:
                    adjusted = ChatMessage(
                        timestamp=max(0, msg.timestamp - time_offset),
                        absolute_time=msg.absolute_time,
                        username=msg.username,
                        nickname=msg.nickname,
                        content=msg.content,
                        event_type=msg.event_type,
                        extra=msg.extra,
                    )
                    adjusted_messages.append(adjusted)

                gen = SubtitleGenerator(self.config)
                gen.write(adjusted_messages, self.session.subtitle_path)

                self._log("Encoding final video with chat overlay...")
                self._encoder = OverlayEncoder()
                success = self._encoder.burn_subtitles(
                    self.session.raw_video_path,
                    self.session.subtitle_path,
                    self.session.final_video_path,
                    self.config,
                )
                self._encoder = None
                if success:
                    self._log(f"Final video: {self.session.final_video_path}")
                else:
                    self._log("Overlay encoding failed or cancelled. Raw video + subtitle file preserved.")
            elif has_chat and not has_video:
                assert chat is not None
                gen = SubtitleGenerator(self.config)
                gen.write(chat.messages, self.session.subtitle_path)
                self._log("Chat-only mode: subtitle file saved for later use.")

            # Clean up empty output directories (no video, no chat)
            if not has_video and not has_chat:
                self._cleanup_empty_dir(self.session.output_dir)

        except Exception as e:
            self._log(f"Post-processing error: {e}")
            logger.exception("Post-processing error")

    async def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep for the given duration, checking _stop_requested every 0.5s."""
        elapsed = 0.0
        while elapsed < seconds and not self._stop_requested:
            await asyncio.sleep(min(0.5, seconds - elapsed))
            elapsed += 0.5
