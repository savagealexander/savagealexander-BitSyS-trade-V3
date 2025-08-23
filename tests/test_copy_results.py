import importlib
import os
from fastapi.testclient import TestClient


def _get_client(tmp_path):
    """Create a TestClient with fresh module state."""
    store = tmp_path / "accounts.json"
    os.environ["ACCOUNTS_FILE"] = str(store)

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


def test_copy_results_endpoint(tmp_path):
    client = _get_client(tmp_path)

    # Initially no results
    resp = client.get("/api/copy/results")
    assert resp.status_code == 200
    assert resp.json() == {}

    # Update dispatcher results and ensure endpoint reflects it
    from server.copy_dispatcher import copy_dispatcher

    copy_dispatcher._last_results = {"acc1": {"success": True}}
    resp = client.get("/api/copy/results")
    assert resp.status_code == 200
    assert resp.json() == {"acc1": {"success": True}}
