import asyncio
import json
import contextlib
from unittest.mock import patch

from server.leader_watcher import watch_leader_orders


class DummyWS:
    def __init__(self, messages):
        self._queue = asyncio.Queue()
        for msg in messages:
            self._queue.put_nowait(msg)

    async def recv(self):
        return await self._queue.get()

    async def ping(self):
        pass

    async def close(self):
        pass


class DummyConnector:
    def __init__(self, messages):
        self._messages = messages

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def create_listen_key(self, api_key):
        return "k"

    async def ws_connect(self, listen_key):
        return DummyWS(self._messages)

    async def keepalive_listen_key(self, api_key, listen_key):
        pass

    async def get_balance(self, api_key, api_secret):
        return {"USDT": 100.0, "BTC": 1.0}


def run(coro):
    return asyncio.run(coro)


def _run_test(message):
    async def main():
        with patch(
            "server.leader_watcher.BinanceConnector",
            new=lambda testnet=False: DummyConnector([message]),
        ):
            agen = watch_leader_orders("apikey", "secret")
            event = await agen.__anext__()
            with contextlib.suppress(BaseException):
                await agen.aclose()
            return event

    return run(main())


def test_unwrapped_event_processed():
    data = {
        "e": "executionReport",
        "X": "FILLED",
        "o": "MARKET",
        "i": 123,
        "S": "BUY",
        "Z": 10.5,
        "z": 0.001,
    }
    msg = json.dumps(data)
    event = _run_test(msg)
    assert event["event_id"] == 123
    assert event["side"] == "BUY"
    assert event["quote_filled"] == 10.5


def test_wrapped_event_processed():
    data = {
        "e": "executionReport",
        "X": "FILLED",
        "o": "MARKET",
        "i": 456,
        "S": "SELL",
        "Z": 5.0,
        "z": 0.002,
    }
    msg = json.dumps({"data": data})
    event = _run_test(msg)
    assert event["event_id"] == 456
    assert event["side"] == "SELL"
    assert event["quote_filled"] == 5.0

