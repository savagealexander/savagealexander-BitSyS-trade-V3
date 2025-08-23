import asyncio
import contextlib
from collections import deque

from services.leader_ws import watch_leader_orders


def run(coro):
    """Helper to run async coroutines inside tests."""
    return asyncio.run(coro)


def test_keepalive_runs_periodically():
    async def main():
        keepalive_calls = []

        async def create_listen_key():
            return "key1"

        async def keepalive(key: str):
            keepalive_calls.append(key)

        async def connect_ws(key: str):
            while True:
                await asyncio.sleep(0.01)
                yield {"msg": key}

        task = asyncio.create_task(
            watch_leader_orders(
                create_listen_key,
                connect_ws,
                keepalive,
                keepalive_interval=0.05,
            )
        )
        await asyncio.sleep(0.18)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        assert len(keepalive_calls) >= 2

    run(main())


def test_reconnect_after_connection_drop():
    async def main():
        keys = deque(["k1", "k2"])
        created = []
        keepalive_calls = []

        async def create_listen_key():
            key = keys.popleft()
            created.append(key)
            return key

        async def keepalive(key: str):
            keepalive_calls.append(key)

        class Connector:
            def __init__(self):
                self.calls = 0

            def __call__(self, key: str):
                self.calls += 1
                if self.calls == 1:
                    async def first():
                        yield {"msg": key}
                        raise RuntimeError("ws dropped")
                    return first()
                else:
                    async def second():
                        while True:
                            await asyncio.sleep(0.01)
                            yield {"msg": key}
                    return second()

        connector = Connector()

        task = asyncio.create_task(
            watch_leader_orders(
                create_listen_key,
                connector,
                keepalive,
                keepalive_interval=0.05,
            )
        )

        await asyncio.sleep(0.15)  # allow first connection and drop
        await asyncio.sleep(0.15)  # allow reconnect and keepalive
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        assert created == ["k1", "k2"]
        assert keepalive_calls and keepalive_calls[-1] == "k2"

    run(main())
