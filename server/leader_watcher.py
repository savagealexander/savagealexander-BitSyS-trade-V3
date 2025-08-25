"""Leader account order watcher using Binance SDK."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Dict

from .connectors.binance_sdk_connector import BinanceSDKConnector

logger = logging.getLogger(__name__)


async def watch_leader_orders(
    api_key: str,
    api_secret: str,
    *,
    testnet: bool = False,
) -> AsyncIterator[dict]:
    """Yield leader account trade events from Binance user data stream.

    The official ``python-binance`` SDK manages the websocket connection and
    listen-key keepalive internally.  This coroutine simply bridges the SDK's
    callback-based interface into an async iterator.
    """

    logger.info("Starting leader order watcher: testnet=%s", testnet)

    queue: asyncio.Queue[Dict] = asyncio.Queue()

    async with BinanceSDKConnector(api_key, api_secret, testnet=testnet) as connector:
        # Push websocket messages into an asyncio queue for processing.
        def _handle_message(msg: Dict) -> None:  # pragma: no cover - simple callback
            queue.put_nowait(msg)

        connector.start_user_socket(_handle_message)

        # Seed balances so the first trade has meaningful ratios.
        balances = await connector.get_balance()
        free_usdt = float(balances.get("USDT", 0.0))
        free_btc = float(balances.get("BTC", 0.0))

        pending_fill: Dict | None = None

        while True:
            payload = await queue.get()
            etype = payload.get("e")

            if etype == "outboundAccountPosition":
                balances = {b["a"]: float(b["f"]) for b in payload.get("B", [])}
                free_usdt = balances.get("USDT", free_usdt)
                free_btc = balances.get("BTC", free_btc)
                if pending_fill:
                    fill = pending_fill
                    pending_fill = None
                    quote = float(fill.get("Z", 0.0))
                    base = float(fill.get("z", 0.0))
                    side = fill.get("S")
                    if side == "BUY":
                        pre_usdt = free_usdt + quote
                        pre_btc = free_btc - base
                    else:  # SELL
                        pre_usdt = free_usdt - quote
                        pre_btc = free_btc + base
                    yield {
                        "event_id": fill.get("i"),
                        "side": side,
                        "quote_filled": quote,
                        "base_filled": base,
                        "leader_pre_usdt": max(pre_usdt, 1e-9),
                        "leader_pre_btc": max(pre_btc, 1e-9),
                    }
                continue

            if etype != "executionReport":
                continue
            if payload.get("X") != "FILLED" or payload.get("o") != "MARKET":
                continue

            pending_fill = payload
