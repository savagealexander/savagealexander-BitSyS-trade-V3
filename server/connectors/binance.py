"""Binance exchange connectors."""

from dataclasses import dataclass
from typing import Optional

import httpx
import websockets


@dataclass
class BinanceConnector:
    """Minimal Binance REST/WebSocket connector.

    Attributes are configured for mainnet or testnet based on `testnet` flag.
    """

    testnet: bool = False
    rest_base: str = "https://api.binance.com"
    ws_base: str = "wss://stream.binance.com:9443/ws"

    def __post_init__(self) -> None:
        if self.testnet:
            self.rest_base = "https://testnet.binance.vision"
            self.ws_base = "wss://testnet.binance.vision/ws"
        self._client = httpx.AsyncClient(base_url=self.rest_base)

    async def get_time(self) -> Optional[int]:
        """Example REST call to fetch server time."""
        try:
            resp = await self._client.get("/api/v3/time")
            resp.raise_for_status()
            data = resp.json()
            return data.get("serverTime")
        except Exception:
            return None

    async def ws_connect(self, stream: str):
        """Return a websocket connection for a given stream."""
        url = f"{self.ws_base}/{stream}"
        return await websockets.connect(url)
