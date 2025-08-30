"""Binance connector using the official python-binance SDK.

This provides a minimal wrapper around :class:`binance.Client` exposing the
operations used by the service layer.  Only the pieces required by the current
codebase are implemented.
"""

from __future__ import annotations

import asyncio
import json
import contextlib
import logging
import inspect
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

try:  # pragma: no cover - optional dependency during tests
    from binance import Client
except Exception:  # pragma: no cover
    Client = None  # type: ignore

try:  # pragma: no cover - optional dependency during tests
    import websockets
except Exception:  # pragma: no cover
    websockets = None

try:  # pragma: no cover - optional dependency during tests
    import httpx
except Exception:  # pragma: no cover
    httpx = None


CallbackType = Callable[[Dict], None]

logger = logging.getLogger(__name__)


@dataclass
class BinanceSDKConnector:
    """Thin wrapper around the `python-binance` client."""

    api_key: str
    api_secret: str
    testnet: bool = False
    _client: Client = field(init=False)
    _ws_task: Optional[asyncio.Task] = field(default=None, init=False)
    _keepalive_task: Optional[asyncio.Task] = field(default=None, init=False)
    _http: Optional[httpx.AsyncClient] = field(default=None, init=False)
    _ws: Optional[websockets.WebSocketClientProtocol] = field(default=None, init=False)

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
        if self._ws is not None:
            with contextlib.suppress(Exception):
                await self._ws.close()
            self._ws = None
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        # Ensure underlying HTTP session is properly closed to release resources
        session = getattr(self._client, "session", None)
        if session is not None:
            await asyncio.to_thread(session.close)

    async def __aexit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - simple pass
        await self.close()

    async def start_user_socket(self, callback: CallbackType) -> None:
        """Start the user data stream and dispatch messages to ``callback``."""

        if websockets is None or httpx is None:  # pragma: no cover - dependency missing
            raise RuntimeError("websockets and httpx packages are required")

        rest_base = "https://api.binance.com"
        ws_base = "wss://stream.binance.com:9443/ws"
        if self.testnet:
            rest_base = "https://testnet.binance.vision"
            ws_base = "wss://stream.testnet.binance.vision:9443/ws"
        if self._http is None:
            self._http = httpx.AsyncClient(base_url=rest_base)

        headers = {"X-MBX-APIKEY": self.api_key}

        async def _runner() -> None:
            while True:
                try:
                    resp = await self._http.post("/api/v3/userDataStream", headers=headers)
                    resp.raise_for_status()
                    listen_key = resp.json().get("listenKey")
                    logger.info("listen key retrieved")
                except asyncio.CancelledError:  # pragma: no cover - task cancelled
                    raise
                except Exception as exc:  # pragma: no cover - network errors
                    logger.warning("failed to obtain listen key: %s", exc)
                    await asyncio.sleep(5)
                    continue

                async with websockets.connect(f"{ws_base}/{listen_key}") as ws:
                    self._ws = ws

                    async def _keepalive() -> None:
                        logger.info("keepalive started")
                        try:
                            while True:
                                await asyncio.sleep(30 * 60)
                                try:
                                    await self._http.put(
                                        "/api/v3/userDataStream",
                                        params={"listenKey": listen_key},
                                        headers=headers,
                                    )
                                except Exception as exc:  # pragma: no cover - network errors
                                    logger.warning("keepalive failed: %s", exc)
                                    await ws.close()
                                    break
                        except asyncio.CancelledError:  # pragma: no cover - task cancelled
                            pass
                        finally:
                            logger.info("keepalive stopped")

                    self._keepalive_task = asyncio.create_task(_keepalive())

                    try:
                        async for message in ws:
                            data = json.loads(message)
                            res = callback(data)
                            if inspect.isawaitable(res):
                                await res
                    except asyncio.CancelledError:  # pragma: no cover - task cancelled
                        raise
                    except Exception as exc:  # pragma: no cover - network errors
                        logger.warning("websocket error: %s", exc)
                    finally:
                        if self._keepalive_task is not None:
                            self._keepalive_task.cancel()
                            with contextlib.suppress(Exception):
                                await self._keepalive_task
                            self._keepalive_task = None
                        self._ws = None
                        logger.info("websocket closed, reconnecting")
                        await asyncio.sleep(1)

        self._ws_task = asyncio.create_task(_runner())

