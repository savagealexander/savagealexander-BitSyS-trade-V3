import pytest
from types import SimpleNamespace
from server import balances
from server.balances import BalanceService


@pytest.mark.asyncio
async def test_start_prefetches_balance(monkeypatch):
    svc = BalanceService()

    # Stub account listing
    account = SimpleNamespace(name="acc1")
    monkeypatch.setattr(balances, "account_service", SimpleNamespace(list_accounts=lambda: [account]))

    calls = []

    async def fake_update(name):
        calls.append(f"update:{name}")
        svc._cache[name] = {"BTC": 1.0, "USDT": 2.0, "stale": False}

    def fake_register(name):
        calls.append(f"register:{name}")

    monkeypatch.setattr(svc, "update_balance", fake_update)
    monkeypatch.setattr(svc, "register_account", fake_register)

    await svc.start()

    assert calls == ["update:acc1", "register:acc1"]
    assert await svc.get_balance("acc1") == {
        "BTC": 1.0,
        "USDT": 2.0,
        "stale": False,
    }


@pytest.mark.asyncio
async def test_update_failure_marks_stale(monkeypatch):
    svc = BalanceService()

    account = SimpleNamespace(
        name="acc1",
        exchange="binance",
        env="test",
        api_key="k",
        api_secret="s",
        passphrase=None,
    )
    monkeypatch.setattr(
        balances,
        "account_service",
        SimpleNamespace(list_accounts=lambda: [account]),
    )

    class FailingConnector:
        def __init__(self, api_key, api_secret, testnet=False):
            pass

        async def get_balance(self):
            raise RuntimeError("boom")

    svc._connectors["binance"] = FailingConnector
    svc._cache["acc1"] = {"BTC": 1.0, "USDT": 2.0, "stale": False}
    await svc.update_balance("acc1")
    assert svc._cache["acc1"] == {"BTC": 1.0, "USDT": 2.0, "stale": True}


@pytest.mark.asyncio
async def test_update_failure_retains_previous_balance(monkeypatch):
    svc = BalanceService()

    account = SimpleNamespace(
        name="acc1",
        exchange="binance",
        env="test",
        api_key="k",
        api_secret="s",
        passphrase=None,
    )
    monkeypatch.setattr(
        balances,
        "account_service",
        SimpleNamespace(list_accounts=lambda: [account]),
    )

    class FailingConnector:
        def __init__(self, api_key, api_secret, testnet=False):
            pass

        async def get_balance(self):
            raise RuntimeError("boom")

    svc._connectors["binance"] = FailingConnector
    svc._cache["acc1"] = {"BTC": 0.5, "USDT": 10.0, "stale": False}
    await svc.update_balance("acc1")
    assert svc._cache["acc1"] == {"BTC": 0.5, "USDT": 10.0, "stale": True}
