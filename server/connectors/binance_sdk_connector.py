"""Binance connector using the official python-binance SDK.

This provides a minimal wrapper around :class:`binance.Client` exposing the
operations used by the service layer.  Only the pieces required by the current
codebase are implemented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

try:  # pragma: no cover - optional dependency during tests
    from binance import Client, ThreadedWebsocketManager
except Exception:  # pragma: no cover
    Client = ThreadedWebsocketManager = None  # type: ignore


CallbackType = Callable[[Dict], None]


@dataclass
class BinanceSDKConnector:
    """Thin wrapper around the `python-binance` client."""

    api_key: str
    api_secret: str
    testnet: bool = False
    _client: Client = field(init=False)
    _twm: Optional[ThreadedWebsocketManager] = field(default=None, init=False)

    def __post_init__(self) -> None:  # pragma: no cover - simple assignment
        if Client is None:  # pragma: no cover - dependency missing
            raise RuntimeError("python-binance package is required")
        self._client = Client(self.api_key, self.api_secret, testnet=self.testnet)

    # ------------------------------------------------------------------
    # Balance and order helpers
    # ------------------------------------------------------------------
    def get_balance(self) -> Dict[str, float]:
        """Return available BTC and USDT balances."""

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

    def order_market_buy(self, symbol: str, quote_amount: float) -> Dict:
        """Place a market buy order spending ``quote_amount`` USDT."""

        return self._client.create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quoteOrderQty=quote_amount,
        )

    def order_market_sell(self, symbol: str, quantity: float) -> Dict:
        """Place a market sell order for ``quantity`` base asset."""

        return self._client.create_order(
            symbol=symbol,
            side="SELL",
            type="MARKET",
            quantity=quantity,
        )

    # ------------------------------------------------------------------
    # Websocket handling
    # ------------------------------------------------------------------
    def start_user_socket(self, callback: CallbackType) -> int:
        """Start a user data stream and return its socket id."""

        if self._twm is None:
            self._twm = ThreadedWebsocketManager(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=self.testnet,
            )
            self._twm.start()
        return self._twm.start_user_socket(callback)

