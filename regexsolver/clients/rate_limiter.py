import asyncio
import logging
import threading
import time
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Shared across all client instances with the same API token.

    Holds a single deadline on the monotonic clock. `trigger` keeps the later
    of the current and the new deadline, so a longer `Retry-After` arriving
    while the limiter is already engaged is never dropped. `wait` sleeps until
    the deadline and re-checks it after every wake, so a deadline extended by
    a concurrent 429 is honored too. Being a plain timestamp, the limiter is
    not bound to any event loop and is safe to share across loops.
    """

    def __init__(self):
        self._deadline = 0.0

    def trigger(self, retry_after: float) -> None:
        """Blocks operations for `retry_after` seconds from now.

        Keeps the later deadline when one is already pending.
        """
        deadline = time.monotonic() + retry_after
        if deadline > self._deadline:
            logger.debug(
                f"Rate limit triggered. Delaying operations for {retry_after} seconds."
            )
            self._deadline = deadline

    async def wait(self) -> None:
        """Asynchronously waits until the rate limit is no longer triggered."""
        while (remaining := self._deadline - time.monotonic()) > 0:
            await asyncio.sleep(remaining)


_rate_limiters: Dict[str, RateLimiter] = {}
_registry_lock = threading.Lock()


def get_rate_limiter(api_token: str) -> RateLimiter:
    """Returns the RateLimiter shared by every client using the given token."""
    with _registry_lock:
        if api_token not in _rate_limiters:
            logger.debug("Creating new RateLimiter instance.")
            _rate_limiters[api_token] = RateLimiter()
        return _rate_limiters[api_token]
