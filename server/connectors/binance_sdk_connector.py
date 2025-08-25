"""Binance connector using the official python-binance SDK.

This provides a minimal wrapper around :class:`binance.Client` exposing the
operations used by the service layer.  Only the pieces required by the current
codebase are implemented.
"""

from __future__ import annotations

import asyncio
import json
import contextlib
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

try:  # pragma: no cover - optional dependency during tests
    from binance import Client, AsyncClient
except Exception:  # pragma: no cover
    Client = AsyncClient = None  # type: ignore

try:  # pragma: no cover - optional dependency during tests
    import websockets
except Exception:  # pragma: no cover
    websockets = None


CallbackType = Callable[[Dict], None]


@dataclass
class BinanceSDKConnector:
    """Thin wrapper around the `python-binance` client."""

    api_key: str
    api_secret: str
    testnet: bool = False
    _client: Client = field(init=False)
    _async_client: Optional[AsyncClient] = field(default=None, init=False)
    _ws_task: Optional[asyncio.Task] = field(default=None, init=False)
    _keepalive_task: Optional[asyncio.Task] = field(default=None, init=False)

    def __post_init__(self) -> None:  # pragma: no cover - simple assignment
        if Client is None:  # pragma: no cover - dependency missing
            raise RuntimeError("python-binance package is required")
        self._client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        if self.testnet:
            self._client.API_URL = "https://testnet.binance.vision/api"

    # ------------------------------------------------------------------
    # Balance and order helpers
    # ------------------------------------------------------------------
    async def get_balance(self) -> Dict[str, float]:
        """Return available BTC and USDT balances."""

        def _get_balance() -> Dict[str, float]:
            result: Dict[str, float] = {"BTC": 0.0, "USDT": 0.0}
            try:
                bal = self._client.get_asset_balance(asset="BTC")
                result["BTC"] = float(bal.get("free", 0.0)) if bal else 0.0
            except Exception:  # pragma: no cover - network errors
                pass
            try:
                bal = self._client.get_asset_balance(asset="USDT")
                result["USDT"] = float(bal.get("free", 0.0)) if bal else 0.0
            except Exception:  # pragma: no cover - network errors
                pass
            return result

        return await asyncio.to_thread(_get_balance)

    async def order_market_buy(self, symbol: str, quote_amount: float) -> Dict:
        """Place a market buy order spending ``quote_amount`` USDT."""

        def _order() -> Dict:
            return self._client.create_order(
                symbol=symbol,
                side="BUY",
                type="MARKET",
                quoteOrderQty=quote_amount,
            )

        return await asyncio.to_thread(_order)

    async def order_market_sell(self, symbol: str, quantity: float) -> Dict:
        """Place a market sell order for ``quantity`` base asset."""

        def _order() -> Dict:
            return self._client.create_order(
                symbol=symbol,
                side="SELL",
                type="MARKET",
                quantity=quantity,
            )

        return await asyncio.to_thread(_order)

    # ------------------------------------------------------------------
    # Websocket handling
    # ------------------------------------------------------------------
    async def __aenter__(self) -> "BinanceSDKConnector":
        return self

    async def close(self) -> None:
        if self._ws_task is not None:
            self._ws_task.cancel()
            with contextlib.suppress(Exception):
                await self._ws_task
            self._ws_task = None
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            with contextlib.suppress(Exception):
                await self._keepalive_task
            self._keepalive_task = None
        if self._async_client is not None:
            await self._async_client.close_connection()
            self._async_client = None
        # Ensure underlying HTTP session is properly closed to release resources
        session = getattr(self._client, "session", None)
        if session is not None:
            await asyncio.to_thread(session.close)

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple pass
        await self.close()

    async def start_user_socket(self, callback: CallbackType) -> None:
        """Start the user data stream and dispatch messages to ``callback``."""

        if AsyncClient is None or websockets is None:  # pragma: no cover - dependency missing
            raise RuntimeError("python-binance and websockets packages are required")

        self._async_client = await AsyncClient.create(
            self.api_key, self.api_secret, testnet=self.testnet
        )
        if self.testnet:
            self._async_client.API_URL = "https://testnet.binance.vision/api"
            ws_base = "wss://testnet.binance.vision/ws"
        else:
            ws_base = "wss://stream.binance.com:9443/ws"

        response = await self._async_client.new_listen_key()
        listen_key = response["listenKey"] if isinstance(response, dict) else response

        async def _keepalive() -> None:
            while True:
                await asyncio.sleep(30 * 60)
                try:
                    await self._async_client.keepalive_listen_key(listen_key)
                except Exception:  # pragma: no cover - network errors
                    break

        self._keepalive_task = asyncio.create_task(_keepalive())

        async def _ws_listener() -> None:
            url = f"{ws_base}/{listen_key}"
            async with websockets.connect(url) as ws:
                async for message in ws:
                    data = json.loads(message)
                    callback(data)

        self._ws_task = asyncio.create_task(_ws_listener())

