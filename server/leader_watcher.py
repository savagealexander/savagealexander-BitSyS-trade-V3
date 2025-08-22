"""Leader account order watcher.

This module will connect to the leader account's websocket stream and emit
trade events. Current implementation is a placeholder.
"""

from typing import AsyncIterator


async def watch_leader_orders() -> AsyncIterator[dict]:
    """Yield leader order events.

    Actual websocket connection logic will be implemented later.
    """
    while False:
        yield {}
        break
