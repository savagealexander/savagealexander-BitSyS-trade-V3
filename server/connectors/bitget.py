"""Bitget exchange connectors."""

from dataclasses import dataclass
from typing import Optional

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

    async def get_time(self) -> Optional[int]:
        """Example REST call to fetch server time."""
        try:
            resp = await self._client.get("/api/spot/v1/public/time")
            resp.raise_for_status()
            data = resp.json()
            return int(data.get("serverTime")) if data else None
        except Exception:
            return None

    async def ws_connect(self, channel: str):
        """Return a websocket connection for a given channel."""
        url = f"{self.ws_base}?channel={channel}"
        return await websockets.connect(url)
