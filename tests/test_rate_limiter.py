import asyncio

import pytest

from regexsolver.clients.rate_limiter import RateLimiter, get_rate_limiter


@pytest.mark.asyncio
async def test_rate_limiter_wait():
    rl = RateLimiter()
    # Primitives are None before use
    assert rl._event is None
    # Initially set after wait ensures it
    await rl.wait()
    assert rl._event is not None
    assert rl._event.is_set()


@pytest.mark.asyncio
async def test_rate_limiter_trigger():
    rl = RateLimiter()
    await rl.trigger(0.1)
    # trigger ensures primitives
    assert rl._event is not None
    assert not rl._event.is_set()

    await asyncio.sleep(0.15)
    assert rl._event.is_set()


@pytest.mark.asyncio
async def test_rate_limiter_trigger_already_cleared():
    rl = RateLimiter()
    await rl.trigger(0.2)
    task1 = rl._reopen_task

    # Trigger again while still clearing
    await rl.trigger(0.1)
    # It should not have changed the event or task if handled correctly
    # (actually the implementation returns if not set)
    assert rl._event is not None
    assert not rl._event.is_set()
    assert rl._reopen_task == task1


def test_get_rate_limiter_loop_aware():
    # We can't easily start multiple loops in one sync test easily without some boilerplate,
    # but we can verify the singleton logic still works for the same loop.
    rl1 = get_rate_limiter("token1")
    rl2 = get_rate_limiter("token1")
    assert rl1 is rl2


@pytest.mark.asyncio
async def test_get_rate_limiter_different_loops():
    # In an async test, get_running_loop() works.
    rl1 = get_rate_limiter("token1")

    async def other_loop_task():
        new_loop = asyncio.new_event_loop()
        try:
            # We must run this in the context of the new loop
            # But get_rate_limiter uses get_running_loop()
            # So we use the new loop to run a call.
            def call_in_loop():
                return get_rate_limiter("token1")

            rl2 = new_loop.run_until_complete(
                asyncio.to_thread(call_in_loop)
            )  # This is getting complicated
            # Simpler: just mock the loop or use a separate thread
            return rl2
        finally:
            new_loop.close()

    # Let's just use a thread to get a different loop context
    import threading

    rl2_container = []

    def thread_target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        rl2_container.append(get_rate_limiter("token1"))
        loop.close()

    t = threading.Thread(target=thread_target)
    t.start()
    t.join()

    assert rl1 is not rl2_container[0]
