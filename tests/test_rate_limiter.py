import asyncio
import threading
import time

import pytest

from regexsolver.clients.rate_limiter import RateLimiter, get_rate_limiter


@pytest.mark.asyncio
async def test_rate_limiter_wait_without_trigger_returns_immediately():
    rl = RateLimiter()
    start = time.monotonic()
    await rl.wait()
    assert time.monotonic() - start < 0.05


@pytest.mark.asyncio
async def test_rate_limiter_trigger():
    rl = RateLimiter()
    rl.trigger(0.1)
    start = time.monotonic()
    await rl.wait()
    assert time.monotonic() - start >= 0.09


@pytest.mark.asyncio
async def test_rate_limiter_trigger_keeps_later_deadline():
    rl = RateLimiter()

    # A shorter Retry-After arriving second must not shrink the deadline.
    rl.trigger(0.2)
    rl.trigger(0.05)
    start = time.monotonic()
    await rl.wait()
    assert time.monotonic() - start >= 0.15

    # A longer Retry-After arriving second must extend it.
    rl.trigger(0.05)
    rl.trigger(0.2)
    start = time.monotonic()
    await rl.wait()
    assert time.monotonic() - start >= 0.15


@pytest.mark.asyncio
async def test_rate_limiter_deadline_extended_while_waiting():
    rl = RateLimiter()
    rl.trigger(0.1)

    async def extend():
        await asyncio.sleep(0.05)
        rl.trigger(0.2)

    start = time.monotonic()
    await asyncio.gather(rl.wait(), extend())
    # The waiter woke at the original deadline, re-checked, and slept again.
    assert time.monotonic() - start >= 0.2


def test_get_rate_limiter_shared_by_token():
    rl1 = get_rate_limiter("token1")
    rl2 = get_rate_limiter("token1")
    assert rl1 is rl2
    assert get_rate_limiter("token2") is not rl1


def test_get_rate_limiter_shared_across_loops():
    # The limiter holds only a timestamp, so the registry is keyed by token
    # alone and the same instance is shared across event loops and threads.
    rl1 = get_rate_limiter("token1")
    container = []

    def thread_target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        container.append(get_rate_limiter("token1"))
        loop.close()

    t = threading.Thread(target=thread_target)
    t.start()
    t.join()

    assert rl1 is container[0]
