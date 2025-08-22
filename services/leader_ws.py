"""Utilities for maintaining a websocket connection to watch leader orders.

This module intentionally keeps the implementation light-weight so that tests
can inject their own coroutines for creating listen keys, keeping them alive
and connecting to a websocket.  The ``watch_leader_orders`` coroutine manages
these components and automatically restarts the connection when it is dropped.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Awaitable, Callable, AsyncIterator, Any

ListenKeyFactory = Callable[[], Awaitable[str]]
KeepAliveFunc = Callable[[str], Awaitable[None]]
WsConnector = Callable[[str], AsyncIterator[Any]]


async def _keepalive_loop(
    listen_key: str, keepalive: KeepAliveFunc, interval: float
) -> None:
    """Periodically invoke ``keepalive`` for ``listen_key``.

    This loop sleeps for ``interval`` seconds between keepalive calls.  It is
    cancelled when the websocket connection is closed or the watcher is
    stopped.
    """

    try:
        while True:
            await asyncio.sleep(interval)
            await keepalive(listen_key)
    except asyncio.CancelledError:
        # Normal shutdown of the keepalive task.
        pass


async def watch_leader_orders(
    create_listen_key: ListenKeyFactory,
    connect_ws: WsConnector,
    keepalive_listen_key: KeepAliveFunc,
    keepalive_interval: float = 30 * 60,
) -> None:
    """Watch leader orders via websocket.

    The coroutine obtains an initial listen key, starts a background task to
    keep it alive and then consumes messages from the websocket connection
    provided by ``connect_ws``.  If the connection ends or raises an
    exception it will attempt to fetch a new listen key and resume watching.

    Parameters
    ----------
    create_listen_key:
        Coroutine returning a new listen key.
    connect_ws:
        Callable receiving a listen key and returning an asynchronous iterator
        yielding websocket messages.
    keepalive_listen_key:
        Coroutine used to keep the listen key alive.
    keepalive_interval:
        Interval in seconds between keepalive calls.  Defaults to thirty
        minutes which mirrors Binance's listen key policy.  Tests can reduce
        this for faster execution.
    """

    listen_key = await create_listen_key()

    while True:
        keepalive_task = asyncio.create_task(
            _keepalive_loop(listen_key, keepalive_listen_key, keepalive_interval)
        )
        try:
            async for _ in connect_ws(listen_key):
                # The actual message processing is not implemented here.  The
                # caller can wrap ``connect_ws`` to process messages as needed.
                await asyncio.sleep(0)  # allow cancellation between messages
        except asyncio.CancelledError:
            keepalive_task.cancel()
            with contextlib.suppress(Exception):
                await keepalive_task
            raise
        except Exception:
            # Connection dropped.  Fall through to obtain a new listen key.
            pass
        finally:
            keepalive_task.cancel()
            with contextlib.suppress(Exception):
                await keepalive_task

        # Obtain a new listen key and retry the connection.
        listen_key = await create_listen_key()
