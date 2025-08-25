import importlib
import os
from fastapi.testclient import TestClient
import pytest


async def _setup(tmp_path):
    store = tmp_path / "accounts.json"
    os.environ["ACCOUNTS_FILE"] = str(store)
    import server.storage as storage
    import server.accounts as accounts
    import server.balances as balances
    import server.api as api_module
    import server.main as main
    importlib.reload(storage)
    importlib.reload(accounts)
    importlib.reload(balances)
    importlib.reload(api_module)
    importlib.reload(main)
    app = main.create_app()
    return TestClient(app), accounts, balances


@pytest.mark.asyncio
async def test_balance_endpoint_returns_values(monkeypatch, tmp_path):
    client, accounts_mod, balances_mod = await _setup(tmp_path)
    balance_service = balances_mod.balance_service
    account_service = accounts_mod.account_service
    monkeypatch.setattr(balance_service, "register_account", lambda name: None)
    from server.accounts import Account
    account = Account(
        name="acc1",
        exchange="bitget",
        env="demo",
        api_key="k",
        api_secret="s",
        passphrase="p",
    )
    account_service.add_account(account)

    class DummyConnector:
        def __init__(self, demo=False):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def get_balance(self, api_key, api_secret, passphrase):
            return {"BTC": 0.5, "USDT": 100.0}

    balance_service._connectors["bitget"] = DummyConnector
    await balance_service.update_balance("acc1")
    resp = client.get("/api/balances/acc1")
    assert resp.status_code == 200
    assert resp.json() == {"BTC": 0.5, "USDT": 100.0, "stale": False}
