import asyncio
import contextlib

import pytest

from server.leader_watcher import watch_leader_orders


def run(coro):
    return asyncio.run(coro)


def _run_test(exec_event, bal_event, dummy_binance_sdk):
    async def main():
        dummy_binance_sdk.set_events([exec_event, bal_event])
        agen = watch_leader_orders("apikey", "secret")
        event = await agen.__anext__()
        with contextlib.suppress(BaseException):
            await agen.aclose()
        return event

    return run(main())


def test_buy_event_pre_balances(dummy_binance_sdk):
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
    event = _run_test(exec_event, bal_event, dummy_binance_sdk)
    assert event["event_id"] == 123
    assert event["leader_pre_usdt"] == pytest.approx(100.0)
    assert event["leader_pre_btc"] == pytest.approx(1.0)


def test_sell_event_pre_balances(dummy_binance_sdk):
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
    event = _run_test(exec_event, bal_event, dummy_binance_sdk)
    assert event["event_id"] == 456
    assert event["leader_pre_usdt"] == pytest.approx(100.0)
    assert event["leader_pre_btc"] == pytest.approx(1.0)
