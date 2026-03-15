import asyncio
import threading
from typing import Dict, Optional


class RateLimiter:
    """Shared across all client instances with the same API token and event loop.

    Asyncio primitives (Event, Lock) are NOT thread-safe and are bound to the loop
    that created them. This class lazily initializes these primitives to ensure
    they are bound to the correct loop.
    """

    def __init__(self):
        self._event: Optional[asyncio.Event] = None
        self._lock: Optional[asyncio.Lock] = None
        self._reopen_task: Optional[asyncio.Task] = None

    def _ensure_primitives(self):
        """Lazily initialize asyncio primitives on the current running loop."""
        if self._event is None:
            self._event = asyncio.Event()
            self._event.set()
        if self._lock is None:
            self._lock = asyncio.Lock()

    async def wait(self):
        """Asynchronously waits until the rate limit is no longer triggered.

        If the limiter is currently triggered (e.g., after a 429 error), this method
        will block until the delay has passed.
        """
        self._ensure_primitives()
        if self._event is None:
            raise RuntimeError("RateLimiter event not initialized.")
        await self._event.wait()

    async def trigger(self, retry_after: float):
        """Triggers the rate limiter for a specific duration.

        Args:
            retry_after: The duration in seconds to keep the limiter triggered.

        This method will cause all subsequent calls to wait() to block until
        the duration has elapsed.
        """
        self._ensure_primitives()
        if self._lock is None or self._event is None:
            raise RuntimeError("RateLimiter primitives not initialized.")
        async with self._lock:
            if not self._event.is_set():
                return  # already being handled
            self._event.clear()
            if self._reopen_task and not self._reopen_task.done():
                self._reopen_task.cancel()
            self._reopen_task = asyncio.create_task(self._lift(retry_after))

    async def _lift(self, delay: float):
        """Background task that lifts the rate limit after the specified delay.

        Args:
            delay: The delay in seconds.
        """
        await asyncio.sleep(delay)
        if self._event is None:
            raise RuntimeError("RateLimiter event not initialized.")
        self._event.set()


_rate_limiters: Dict[tuple, RateLimiter] = {}
_registry_lock = threading.Lock()


def get_rate_limiter(api_token: str) -> RateLimiter:
    """Returns a RateLimiter instance for the given token and current event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no loop is running, we can't reliably provide a loop-bound limiter.
        # This shouldn't happen during normal client usage as methods are called
        # within a loop.
        loop = None

    key = (api_token, loop)
    with _registry_lock:
        if key not in _rate_limiters:
            _rate_limiters[key] = RateLimiter()
        return _rate_limiters[key]
