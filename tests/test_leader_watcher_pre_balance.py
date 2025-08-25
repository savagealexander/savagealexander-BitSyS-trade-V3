import asyncio
import contextlib
from unittest.mock import patch

import pytest

from server.leader_watcher import watch_leader_orders


class DummyConnector:
    def __init__(self, events):
        self.events = events

    def get_balance(self):
        return {"USDT": 100.0, "BTC": 1.0}

    def start_user_socket(self, callback):
        for ev in self.events:
            callback(ev)
        return 1


def run(coro):
    return asyncio.run(coro)


def _run_test(exec_event, bal_event):
    async def main():
        events = [exec_event, bal_event]
        with patch(
            "server.leader_watcher.BinanceSDKConnector",
            new=lambda *a, **k: DummyConnector(events),
        ):
            agen = watch_leader_orders("apikey", "secret")
            event = await agen.__anext__()
            with contextlib.suppress(BaseException):
                await agen.aclose()
            return event

    return run(main())


def test_buy_event_pre_balances():
    exec_event = {
        "e": "executionReport",
        "X": "FILLED",
        "o": "MARKET",
        "i": 123,
        "S": "BUY",
        "Z": 10.0,
        "z": 0.001,
    }
    bal_event = {
        "e": "outboundAccountPosition",
        "B": [{"a": "USDT", "f": "90.0"}, {"a": "BTC", "f": "1.001"}],
    }
    event = _run_test(exec_event, bal_event)
    assert event["event_id"] == 123
    assert event["leader_pre_usdt"] == pytest.approx(100.0)
    assert event["leader_pre_btc"] == pytest.approx(1.0)


def test_sell_event_pre_balances():
    exec_event = {
        "e": "executionReport",
        "X": "FILLED",
        "o": "MARKET",
        "i": 456,
        "S": "SELL",
        "Z": 10.0,
        "z": 0.001,
    }
    bal_event = {
        "e": "outboundAccountPosition",
        "B": [{"a": "USDT", "f": "110.0"}, {"a": "BTC", "f": "0.999"}],
    }
    event = _run_test(exec_event, bal_event)
    assert event["event_id"] == 456
    assert event["leader_pre_usdt"] == pytest.approx(100.0)
    assert event["leader_pre_btc"] == pytest.approx(1.0)
