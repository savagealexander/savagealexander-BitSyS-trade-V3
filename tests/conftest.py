import sys
from pathlib import Path
import pytest

# Ensure repository root is on sys.path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def dummy_binance_sdk(monkeypatch):
    """Provide a dummy Binance SDK connector used by tests.

    The connector tracks order method usage and can replay websocket events for
    leader watcher tests.
    """

    class DummyBinanceSDKConnector:
        _events = []
        last_instance = None

        def __init__(self, *args, **kwargs):
            self.events = list(self._events)
            self.order_calls = []
            DummyBinanceSDKConnector.last_instance = self

        @classmethod
        def set_events(cls, events):
            cls._events = events or []

        async def get_balance(self):
            return {"USDT": 100.0, "BTC": 1.0}

        async def start_user_socket(self, callback):
            for ev in self.events:
                callback(ev)

        async def __aenter__(self):  # pragma: no cover - simple passthrough
            return self

        async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover
            return None

        async def order_market_buy(self, symbol, quote_amount):
            self.order_calls.append(("BUY", quote_amount))
            return {"symbol": symbol, "quote": quote_amount}

        async def order_market_sell(self, symbol, quantity):
            self.order_calls.append(("SELL", quantity))
            return {"symbol": symbol, "base": quantity}

        async def create_market_order(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("SDK order methods should be used")

    # Patch modules that construct the SDK connector
    monkeypatch.setattr(
        "server.leader_watcher.BinanceSDKConnector", DummyBinanceSDKConnector
    )
    monkeypatch.setattr(
        "server.copy_dispatcher.BinanceConnector", DummyBinanceSDKConnector
    )
    return DummyBinanceSDKConnector
