import importlib
import os
from fastapi.testclient import TestClient


def _get_client(tmp_path):
    """Create a TestClient with isolated storage for follower accounts."""

    store = tmp_path / "accounts.json"
    os.environ["ACCOUNTS_FILE"] = str(store)

    import server.storage as storage
    import server.accounts as accounts
    import api.follower_accounts as api_module
    import server.api as server_api
    import server.main as main

    importlib.reload(storage)
    importlib.reload(accounts)
    importlib.reload(api_module)
    importlib.reload(server_api)
    importlib.reload(main)

    app = main.create_app()
    return TestClient(app)


def test_create_and_delete_follower_account(tmp_path):
    client = _get_client(tmp_path)
    payload = {
        "name": "acc1",
        "exchange": "binance",
        "env": "test",
        "api_key": "key123",
        "api_secret": "secret456",
    }
    resp = client.post("/api/follower-accounts", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"name": "acc1"}

    # delete
    resp = client.delete("/api/follower-accounts/acc1")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}


def test_create_duplicate_account_fails(tmp_path):
    client = _get_client(tmp_path)
    payload = {
        "name": "acc1",
        "exchange": "binance",
        "env": "test",
        "api_key": "key",
        "api_secret": "secret",
    }
    assert client.post("/api/follower-accounts", json=payload).status_code == 200
    resp = client.post("/api/follower-accounts", json=payload)
    assert resp.status_code == 400


def test_verify_credentials(tmp_path):
    client = _get_client(tmp_path)
    valid_payload = {
        "exchange": "binance",
        "env": "test",
        "api_key": "key",
        "api_secret": "secret",
    }
    resp = client.post("/api/follower-accounts/verify", json=valid_payload)
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

    invalid_payload = {
        "exchange": "binance",
        "env": "test",
        "api_key": "",
        "api_secret": "secret",
    }
    resp = client.post("/api/follower-accounts/verify", json=invalid_payload)
    assert resp.status_code == 400
