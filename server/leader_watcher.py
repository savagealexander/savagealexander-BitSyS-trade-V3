"""Leader account order watcher."""

from __future__ import annotations

import asyncio
import json
import os
from typing import AsyncIterator

from .connectors.binance import BinanceConnector

WS_HEARTBEAT_SEC = int(os.getenv("WS_HEARTBEAT_SEC", "30"))


async def watch_leader_orders(
    api_key: str, *, testnet: bool = False
) -> AsyncIterator[dict]:
    """Yield leader account trade events from Binance user data stream.

    The iterator reconnects on errors and sends websocket ping frames if no
    message is received for ``WS_HEARTBEAT_SEC`` seconds.
    """

    async with BinanceConnector(testnet=testnet) as connector:
        while True:
            listen_key = await connector.create_listen_key(api_key)
            if not listen_key:
                await asyncio.sleep(WS_HEARTBEAT_SEC)
                continue

            free_usdt = 0.0
            free_btc = 0.0

            try:
                ws = await connector.ws_connect(listen_key)
                try:
                    while True:
                        try:
                            raw = await asyncio.wait_for(
                                ws.recv(), timeout=WS_HEARTBEAT_SEC
                            )
                        except asyncio.TimeoutError:
                            await ws.ping()
                            continue

                        data = json.loads(raw)
                        etype = data.get("e")

                        if etype == "outboundAccountPosition":
                            balances = {b["a"]: float(b["f"]) for b in data.get("B", [])}
                            free_usdt = balances.get("USDT", free_usdt)
                            free_btc = balances.get("BTC", free_btc)
                            continue

                        if etype != "executionReport":
                            continue

                        if data.get("X") != "FILLED" or data.get("o") != "MARKET":
                            continue

                        yield {
                            "event_id": data.get("i"),
                            "side": data.get("S"),
                            "quote_filled": float(data.get("Z", 0.0)),
                            "base_filled": float(data.get("z", 0.0)),
                            "leader_free_usdt": free_usdt,
                            "leader_free_btc": free_btc,
                        }
                finally:
                    await ws.close()
            except Exception:
                await asyncio.sleep(WS_HEARTBEAT_SEC)
                continue
