import importlib
import os
from fastapi.testclient import TestClient

def _get_client(tmp_path):
    cred_file = tmp_path / "leader_credentials.json"
    accounts_file = tmp_path / "accounts.json"
    os.environ["LEADER_CRED_FILE"] = str(cred_file)
    os.environ["ACCOUNTS_FILE"] = str(accounts_file)

    import server.storage as storage
    import server.accounts as accounts
    import server.copy_dispatcher as copy_module
    import server.api as server_api
    import server.main as main

    importlib.reload(storage)
    importlib.reload(accounts)
    importlib.reload(copy_module)
    importlib.reload(server_api)
    importlib.reload(main)

    app = main.create_app()
    return TestClient(app)

def test_copy_status_endpoint(tmp_path):
    client = _get_client(tmp_path)

    # default state: dispatcher running, no leader creds
    resp = client.get("/api/copy/status")
    assert resp.status_code == 200
    assert resp.json() == {"running": True, "leader": None}

    # stop dispatcher and save leader credentials
    from server.copy_dispatcher import copy_dispatcher
    from server.storage import save_leader_credentials

    copy_dispatcher.stop()
    save_leader_credentials({"api_key": "abc", "api_secret": "x", "exchange": "binance", "env": "test"})

    resp = client.get("/api/copy/status")
    assert resp.status_code == 200
    assert resp.json() == {"running": False, "leader": "abc"}
