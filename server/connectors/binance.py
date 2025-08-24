"""Binance exchange connectors."""

from dataclasses import dataclass
from typing import Dict, Optional

import hmac
import time
from hashlib import sha256
from urllib.parse import urlencode

import httpx
import websockets


@dataclass
class BinanceConnector:
    """Minimal Binance REST/WebSocket connector.

    Attributes are configured for mainnet or testnet based on `testnet` flag.
    """

    testnet: bool = False
    rest_base: str = "https://api.binance.com"
    ws_base: str = "wss://stream.binance.com:9443/stream"

    def __post_init__(self) -> None:
        if self.testnet:
            self.rest_base = "https://testnet.binance.vision"
            self.ws_base = "wss://stream.testnet.binance.vision:9443/stream"
        self._client = httpx.AsyncClient(base_url=self.rest_base)
        self._ws = None

    async def get_time(self) -> Optional[int]:
        """Example REST call to fetch server time."""
        try:
            resp = await self._client.get("/api/v3/time")
            resp.raise_for_status()
            data = resp.json()
            return data.get("serverTime")
        except Exception:
            return None

    async def get_balance(self, api_key: str, api_secret: str) -> Dict[str, float]:
        """Return available BTC and USDT balances.

        If authentication fails or the request errors, zero balances are
        returned. This method uses the signed ``/api/v3/account`` endpoint.
        """
        try:
            timestamp = int(time.time() * 1000)
            params = {"timestamp": timestamp}
            query = urlencode(params)
            signature = hmac.new(api_secret.encode(), query.encode(), sha256).hexdigest()
            headers = {"X-MBX-APIKEY": api_key}
            url = f"/api/v3/account?{query}&signature={signature}"
            resp = await self._client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("balances", [])
            result: Dict[str, float] = {"BTC": 0.0, "USDT": 0.0}
            for bal in data:
                asset = bal.get("asset")
                if asset in result:
                    result[asset] = float(bal.get("free", 0.0))
            return result
        except Exception:
            return {"BTC": 0.0, "USDT": 0.0}

    async def ws_connect(self, stream: str):
        """Return a websocket connection for a given stream."""
        url = f"{self.ws_base}?streams={stream}"
        self._ws = await websockets.connect(url)
        return self._ws

    async def create_market_order(
        self,
        api_key: str,
        api_secret: str,
        side: str,
        *,
        quote_amount: float | None = None,
        base_amount: float | None = None,
        symbol: str = "BTCUSDT",
    ) -> Dict:
        """Place a market order on Binance.

        Depending on ``side`` the order uses either ``quote_amount`` (for
        BUY orders) or ``base_amount`` (for SELL orders). Errors from the
        exchange are propagated as ``httpx.HTTPStatusError`` allowing callers
        to capture the failure reason.
        """

        timestamp = int(time.time() * 1000)
        params: Dict[str, str] = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "timestamp": str(timestamp),
        }

        if side.upper() == "BUY":
            if quote_amount is None:
                raise ValueError("quote_amount required for BUY orders")
            params["quoteOrderQty"] = str(quote_amount)
        else:
            if base_amount is None:
                raise ValueError("base_amount required for SELL orders")
            params["quantity"] = str(base_amount)

        query = urlencode(params)
        signature = hmac.new(api_secret.encode(), query.encode(), sha256).hexdigest()
        headers = {"X-MBX-APIKEY": api_key}
        url = f"/api/v3/order?{query}&signature={signature}"

        resp = await self._client.post(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def create_listen_key(self, api_key: str) -> Optional[str]:
        """Create a userDataStream listen key."""
        try:
            resp = await self._client.post(
                "/api/v3/userDataStream", headers={"X-MBX-APIKEY": api_key}
            )
            resp.raise_for_status()
            return resp.json().get("listenKey")
        except Exception:
            return None

    async def keepalive_listen_key(self, api_key: str, listen_key: str) -> None:
        """Ping the listen key to keep the stream alive."""
        try:
            await self._client.put(
                "/api/v3/userDataStream",
                params={"listenKey": listen_key},
                headers={"X-MBX-APIKEY": api_key},
            )
        except Exception:
            pass

    async def close(self) -> None:
        """Close underlying HTTP and WebSocket connections."""
        await self._client.aclose()
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None

    async def __aenter__(self) -> "BinanceConnector":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
