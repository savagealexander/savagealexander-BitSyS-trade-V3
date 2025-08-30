"""Leader account order watcher using a Binance connector that manually
manages WebSocket connections and listen-key lifecycles via HTTP and
``websockets`` instead of the SDK's ``AsyncClient``."""

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
    logger.info(f"👀 Entered watch_leader_orders with testnet={testnet}")
    """Yield leader account trade events from Binance user data stream.

    The underlying :class:`BinanceSDKConnector` manages the listen-key lifecycle
    and websocket connection manually through HTTP requests and the
    ``websockets`` library rather than relying on the SDK's ``AsyncClient``.
    This coroutine bridges the connector's callback-based stream into an async
    iterator.
    """

    logger.info("Starting leader order watcher: testnet=%s", testnet)

    queue: asyncio.Queue[Dict] = asyncio.Queue()

    async with BinanceSDKConnector(api_key, api_secret, testnet=testnet) as connector:
        # The connector handles listen-key refresh and websocket management
        # itself via HTTP and ``websockets``.
        # Push websocket messages into an asyncio queue for processing.
        def _handle_message(msg: Dict) -> None:  # pragma: no cover - simple callback
            queue.put_nowait(msg)

        await connector.start_user_socket(_handle_message)

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
                    yield {
                        "type": "order_fill",
                        "order": fill,  # the original pending_fill executionReport
                        "balances": {"USDT": free_usdt, "BTC": free_btc},
                    }
                    pending_fill = None
                continue

            if etype != "executionReport":
                continue
            if payload.get("X") != "FILLED" or payload.get("o") != "MARKET":
                continue

            pending_fill = payload
