import importlib
import os
from unittest.mock import AsyncMock

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
    import services.follower_account_service as fas

    valid_payload = {
        "exchange": "binance",
        "env": "test",
        "api_key": "key",
        "api_secret": "secret",
    }

    fas.verify_credentials = AsyncMock(return_value=(True, ""))
    resp = client.post("/api/follower-accounts/verify", json=valid_payload)
    assert resp.status_code == 200
    assert resp.json() == {"valid": True, "error": ""}

    fas.verify_credentials = AsyncMock(return_value=(False, "boom"))
    resp = client.post("/api/follower-accounts/verify", json=valid_payload)
    assert resp.status_code == 200
    assert resp.json() == {"valid": False, "error": "boom"}

    invalid_payload = {
        "exchange": "binance",
        "env": "test",
        "api_key": "",
        "api_secret": "secret",
    }
    resp = client.post("/api/follower-accounts/verify", json=invalid_payload)
    assert resp.status_code == 400


def test_bitget_requires_passphrase(tmp_path):
    client = _get_client(tmp_path)

    payload = {
        "name": "acc1",
        "exchange": "bitget",
        "env": "test",
        "api_key": "key1",
        "api_secret": "secret1",
        "passphrase": "pp1",
    }
    resp = client.post("/api/follower-accounts", json=payload)
    assert resp.status_code == 200

    missing_pp = payload.copy()
    missing_pp["name"] = "acc2"
    missing_pp.pop("passphrase")
    resp = client.post("/api/follower-accounts", json=missing_pp)
    assert resp.status_code == 400

    verify_payload = {
        "exchange": "bitget",
        "env": "test",
        "api_key": "key",
        "api_secret": "secret",
        "passphrase": "pp",
    }
    import services.follower_account_service as fas
    fas.verify_credentials = AsyncMock(return_value=(True, ""))
    resp = client.post("/api/follower-accounts/verify", json=verify_payload)
    assert resp.status_code == 200

    verify_missing = verify_payload.copy()
    verify_missing.pop("passphrase")
    resp = client.post("/api/follower-accounts/verify", json=verify_missing)
    assert resp.status_code == 400
