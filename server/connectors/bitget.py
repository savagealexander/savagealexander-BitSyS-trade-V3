"""Bitget exchange connectors."""

from dataclasses import dataclass
from typing import Dict, Optional

import base64
import hmac
import time
from hashlib import sha256
import json

import httpx
import websockets


@dataclass
class BitgetConnector:
    """Minimal Bitget REST/WebSocket connector with testnet switch."""

    testnet: bool = False
    rest_base: str = "https://api.bitget.com"
    ws_base: str = "wss://ws.bitget.com/spot/v1/stream"

    def __post_init__(self) -> None:
        if self.testnet:
            self.rest_base = "https://api-testnet.bitget.com"
            self.ws_base = "wss://ws.bitgetapi.com/spot/v1/stream"
        self._client = httpx.AsyncClient(base_url=self.rest_base)
        self._ws = None

    async def get_time(self) -> Optional[int]:
        """Example REST call to fetch server time."""
        try:
            resp = await self._client.get("/api/spot/v1/public/time")
            resp.raise_for_status()
            data = resp.json()
            return int(data.get("serverTime")) if data else None
        except Exception:
            return None

    async def get_balance(self, api_key: str, api_secret: str, passphrase: str) -> Dict[str, float]:
        """Return available BTC and USDT balances.

        Uses the ``/api/spot/v1/account/assets`` endpoint which requires a
        signed request. Failures result in zero balances being returned.
        """
        try:
            ts = str(int(time.time() * 1000))
            method = "GET"
            path = "/api/spot/v1/account/assets"
            prehash = f"{ts}{method}{path}"
            sign = base64.b64encode(
                hmac.new(api_secret.encode(), prehash.encode(), sha256).digest()
            ).decode()
            headers = {
                "ACCESS-KEY": api_key,
                "ACCESS-SIGN": sign,
                "ACCESS-TIMESTAMP": ts,
                "ACCESS-PASSPHRASE": passphrase,
                "Content-Type": "application/json",
            }
            if self.testnet:
                headers["paptrading"] = "1"
            resp = await self._client.get(path, headers=headers)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            result: Dict[str, float] = {"BTC": 0.0, "USDT": 0.0}
            for item in data:
                coin = item.get("coinName")
                if coin in result:
                    result[coin] = float(item.get("available", 0.0))
            return result
        except Exception:
            return {"BTC": 0.0, "USDT": 0.0}

    async def ws_connect(self, channel: str):
        """Return a websocket connection for a given channel."""
        url = f"{self.ws_base}?channel={channel}"
        self._ws = await websockets.connect(url)
        return self._ws

    async def create_market_order(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        side: str,
        *,
        quote_amount: float | None = None,
        base_amount: float | None = None,
        symbol: str = "BTCUSDT",
    ) -> Dict:
        """Place a market order on Bitget.

        Bitget's v2 spot trade API uses a single ``size`` field for both BUY and
        SELL orders. For BUY orders, ``size`` represents the quote (USDT) amount
        to spend. For SELL orders, ``size`` is the base asset amount to sell.
        Orders also require ``orderType`` and ``force`` parameters. Errors will
        raise ``httpx.HTTPStatusError`` so callers can surface meaningful
        messages to users.
        """

        ts = str(int(time.time() * 1000))
        path = "/api/v2/spot/trade/place-order"
        body: Dict[str, str] = {
            "symbol": symbol,
            "side": side.lower(),
            "orderType": "market",
            "force": "gtc",
        }

        if side.upper() == "BUY":
            if quote_amount is None:
                raise ValueError("quote_amount required for BUY orders")
            body["size"] = str(quote_amount)
        else:
            if base_amount is None:
                raise ValueError("base_amount required for SELL orders")
            body["size"] = str(base_amount)

        body_str = json.dumps(body)
        prehash = f"{ts}POST{path}{body_str}"
        sign = base64.b64encode(
            hmac.new(api_secret.encode(), prehash.encode(), sha256).digest()
        ).decode()
        headers = {
            "ACCESS-KEY": api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
        }
        if self.testnet:
            headers["paptrading"] = "1"

        resp = await self._client.post(path, headers=headers, content=body_str)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        """Close underlying HTTP and WebSocket connections."""
        await self._client.aclose()
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        self._ws = None

    async def __aenter__(self) -> "BitgetConnector":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
