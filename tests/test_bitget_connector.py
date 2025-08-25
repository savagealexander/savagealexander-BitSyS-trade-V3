import base64
import hmac
import json
import time
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from server.connectors.bitget import BitgetConnector
import services.follower_account_service as fas


class DummyResponse:
    def __init__(self, data=None):
        self._data = data or {}

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


@pytest.mark.asyncio
async def test_create_market_order_builds_correct_request_buy(monkeypatch):
    connector = BitgetConnector(demo=True)

    monkeypatch.setattr(time, "time", lambda: 1.0)

    mock_post = AsyncMock(return_value=DummyResponse({"ok": True}))
    connector._client.post = mock_post  # type: ignore

    await connector.create_market_order(
        api_key="k",
        api_secret="s",
        passphrase="p",
        side="buy",
        quote_amount=100,
    )

    call = mock_post.await_args
    assert call.args[0] == "/api/v2/spot/trade/place-order"
    headers = call.kwargs["headers"]
    body = json.loads(call.kwargs["content"])

    assert body == {
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "market",
        "force": "gtc",
        "size": "100",
    }
    assert headers["paptrading"] == "1"
    ts = "1000"
    prehash = f"{ts}POST/api/v2/spot/trade/place-order{json.dumps(body)}"
    expected = base64.b64encode(
        hmac.new(b"s", prehash.encode(), sha256).digest()
    ).decode()
    assert headers["ACCESS-SIGN"] == expected


@pytest.mark.asyncio
async def test_create_market_order_builds_correct_request_sell(monkeypatch):
    connector = BitgetConnector(demo=True)

    monkeypatch.setattr(time, "time", lambda: 1.0)

    mock_post = AsyncMock(return_value=DummyResponse({"ok": True}))
    connector._client.post = mock_post  # type: ignore

    await connector.create_market_order(
        api_key="k",
        api_secret="s",
        passphrase="p",
        side="sell",
        base_amount=0.5,
    )

    call = mock_post.await_args
    body = json.loads(call.kwargs["content"])
    assert body["size"] == "0.5"


@pytest.mark.asyncio
async def test_verify_credentials_bitget_headers(monkeypatch):
    called = {}

    class DummyClient:
        def __init__(self, base_url):
            called["base_url"] = base_url

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get(self, path, headers=None):
            called["path"] = path
            called["headers"] = headers
            return DummyResponse({"data": []})

    monkeypatch.setattr(fas, "httpx", SimpleNamespace(AsyncClient=DummyClient))
    monkeypatch.setattr(time, "time", lambda: 1.0)

    valid, error = await fas.verify_credentials(
        exchange="bitget",
        env="demo",
        api_key="k",
        api_secret="s",
        passphrase="p",
    )

    assert valid is True and error == ""
    assert called["base_url"] == "https://api.bitget.com"
    assert called["path"] == "/api/v2/spot/account/assets"
    headers = called["headers"]
    assert headers["paptrading"] == "1"
    assert headers["Content-Type"] == "application/json"
    ts = "1000"
    prehash = f"{ts}GET/api/v2/spot/account/assets"
    expected = base64.b64encode(
        hmac.new(b"s", prehash.encode(), sha256).digest()
    ).decode()
    assert headers["ACCESS-SIGN"] == expected


@pytest.mark.asyncio
async def test_get_balance_parses_available(monkeypatch):
    connector = BitgetConnector()
    data = [
        {"coinName": "BTC", "available": "1.23"},
        {"coinName": "USDT", "available": "456.7"},
    ]
    mock_get = AsyncMock(return_value=DummyResponse({"data": data}))
    monkeypatch.setattr(connector._client, "get", mock_get)  # type: ignore
    result = await connector.get_balance("k", "s", "p")
    assert mock_get.await_args[0][0] == "/api/v2/spot/account/assets"
    assert result == {"BTC": 1.23, "USDT": 456.7}


@pytest.mark.asyncio
async def test_verify_credentials_bitget_rejects_test_env():
    valid, error = await fas.verify_credentials(
        exchange="bitget",
        env="test",
        api_key="k",
        api_secret="s",
        passphrase="p",
    )
    assert valid is False
    assert "testnet" in error
