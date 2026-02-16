import threading
import time
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe rate limiter for TikTok API calls.

    Supports per-key rate limiting so each task (username) independently
    enforces a minimum delay between its own API calls without blocking
    other tasks.  This prevents the global bottleneck where N tasks
    serialize through a single timestamp, causing multi-minute delays.
    """

    def __init__(self, min_delay: float = 10.0):
        self._min_delay = max(1.0, min_delay)
        self._lock = threading.Lock()
        self._last_call: float = 0.0
        self._per_key: dict[str, float] = {}

    @property
    def min_delay(self) -> float:
        return self._min_delay

    @min_delay.setter
    def min_delay(self, value: float):
        self._min_delay = max(1.0, value)

    def acquire(self) -> None:
        """Block until global rate-limit window has passed (legacy)."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_delay:
                wait_time = self._min_delay - elapsed
                logger.debug(f"Rate limiter: waiting {wait_time:.1f}s")
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()
            self._last_call = time.monotonic()

    def acquire_for(self, key: str) -> None:
        """Per-key rate limit — each key tracks its own last-call time.

        Tasks with different keys can proceed concurrently. Only calls
        with the *same* key are serialized with the minimum delay.
        """
        with self._lock:
            now = time.monotonic()
            last = self._per_key.get(key, 0.0)
            elapsed = now - last
            if elapsed < self._min_delay:
                wait_time = self._min_delay - elapsed
                logger.debug(f"Rate limiter [{key}]: waiting {wait_time:.1f}s")
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()
            self._per_key[key] = time.monotonic()
