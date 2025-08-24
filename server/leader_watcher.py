"""Leader account order watcher."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
from datetime import datetime
from typing import AsyncIterator

from .connectors.binance import BinanceConnector

WS_HEARTBEAT_SEC = int(os.getenv("WS_HEARTBEAT_SEC", "30"))
LISTEN_KEY_KEEPALIVE_SEC = int(
    os.getenv("LISTEN_KEY_KEEPALIVE_SEC", str(25 * 60))
)

logger = logging.getLogger(__name__)


async def _keepalive_loop(
    api_key: str, listen_key: str, connector: BinanceConnector, interval: int
) -> None:
    """Periodically refresh the websocket listen key.

    This coroutine sleeps for ``interval`` seconds between keepalive calls. If
    ``connector.keepalive_listen_key`` raises an exception the task terminates
    allowing the caller to reconnect with a fresh listen key.
    """

    try:
        while True:
            await asyncio.sleep(interval)
            logger.info(
                "Refreshing listen key %s at %s",
                listen_key,
                datetime.utcnow().isoformat(),
            )
            await connector.keepalive_listen_key(api_key, listen_key)
    except asyncio.CancelledError:
        # Normal shutdown of the keepalive task.
        raise
    except Exception:
        logger.exception("Listen key keepalive failed")
        raise


async def watch_leader_orders(
    api_key: str, *, testnet: bool = False
) -> AsyncIterator[dict]:
    """Yield leader account trade events from Binance user data stream.

    The iterator reconnects on errors and sends websocket ping frames if no
    message is received for ``WS_HEARTBEAT_SEC`` seconds.
    """

    logger.info("Starting leader order watcher: testnet=%s", testnet)
    async with BinanceConnector(testnet=testnet) as connector:
        while True:
            listen_key = await connector.create_listen_key(api_key)
            if not listen_key:
                logger.warning("Failed to obtain listen key; retrying")
                await asyncio.sleep(WS_HEARTBEAT_SEC)
                continue

            logger.info(
                "Obtained listen key %s at %s",
                listen_key,
                datetime.utcnow().isoformat(),
            )

            free_usdt = 0.0
            free_btc = 0.0
            last_free_usdt = 0.0
            last_free_btc = 0.0

            try:
                ws = await connector.ws_connect(listen_key)
                keepalive_task = asyncio.create_task(
                    _keepalive_loop(
                        api_key, listen_key, connector, LISTEN_KEY_KEEPALIVE_SEC
                    )
                )
                try:
                    while True:
                        if keepalive_task.done():
                            # Propagate keepalive errors to reconnect
                            await keepalive_task

                        try:
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=WS_HEARTBEAT_SEC
                            )
                        except asyncio.TimeoutError:
                            await ws.ping()
                            continue

                        print("DEBUG WS EVENT:", raw)
                        data = json.loads(raw)
                        payload = data.get("data", data)
                        etype = payload.get("e")

                        if etype == "outboundAccountPosition":
                            balances = {b["a"]: float(b["f"]) for b in payload.get("B", [])}
                            last_free_usdt = free_usdt
                            last_free_btc = free_btc
                            free_usdt = balances.get("USDT", free_usdt)
                            free_btc = balances.get("BTC", free_btc)
                            continue

                        if etype != "executionReport":
                            continue

                        if payload.get("X") != "FILLED" or payload.get("o") != "MARKET":
                            continue

                        yield {
                            "event_id": payload.get("i"),
                            "side": payload.get("S"),
                            "quote_filled": float(payload.get("Z", 0.0)),
                            "base_filled": float(payload.get("z", 0.0)),
                            "leader_free_usdt": max(last_free_usdt, 1e-9),
                            "leader_free_btc": max(last_free_btc, 1e-9),
                        }
                finally:
                    keepalive_task.cancel()
                    with contextlib.suppress(Exception):
                        await keepalive_task
                    await ws.close()
            except Exception:
                logger.exception("Error in leader order watcher; reconnecting")
                await asyncio.sleep(WS_HEARTBEAT_SEC)
                continue
