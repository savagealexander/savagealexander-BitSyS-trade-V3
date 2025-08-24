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
        svc._cache[name] = {"BTC": 1.0, "USDT": 2.0}

    def fake_register(name):
        calls.append(f"register:{name}")

    monkeypatch.setattr(svc, "update_balance", fake_update)
    monkeypatch.setattr(svc, "register_account", fake_register)

    await svc.start()

    assert calls == ["update:acc1", "register:acc1"]
    assert await svc.get_balance("acc1") == {"BTC": 1.0, "USDT": 2.0}
