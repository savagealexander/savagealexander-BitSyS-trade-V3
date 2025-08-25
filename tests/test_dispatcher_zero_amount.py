import asyncio
from dataclasses import dataclass

from server.copy_dispatcher import CopyDispatcher
from server.idempotency import IdempotencyStore
from server.accounts import Account


@dataclass
class StubAccounts:
    accounts: list
    def list_accounts(self):
        return self.accounts


class StubBalances:
    def __init__(self, balances):
        self.balances = balances
    async def get_balance(self, name):
        return self.balances.get(name, {"USDT": 0.0, "BTC": 0.0})


class DummyConnector:
    def __init__(self, *args, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def create_market_order(self, *args, **kwargs):
        raise AssertionError("should not be called")


async def _run_dispatch(side: str):
    account = Account(
        name="acc1",
        exchange="binance",
        env="test",
        api_key="k",
        api_secret="s",
    )
    accounts = StubAccounts([account])
    balances = StubBalances({"acc1": {"USDT": 0.0, "BTC": 0.0}})
    dispatcher = CopyDispatcher(accounts, balances, IdempotencyStore())
    dispatcher._connectors = {"binance": DummyConnector}
    event = {
        "event_id": 1,
        "side": side,
        "quote_filled": 10.0,
        "base_filled": 0.001,
        "leader_pre_usdt": 100.0,
        "leader_pre_btc": 1.0,
    }
    await dispatcher.dispatch(event)
    return dispatcher.get_last_results()["acc1"]


def test_zero_quote_amount_recorded():
    result = asyncio.run(_run_dispatch("BUY"))
    assert result == {"success": False, "error": "zero quote_amt"}


def test_zero_base_amount_recorded():
    result = asyncio.run(_run_dispatch("SELL"))
    assert result == {"success": False, "error": "zero base_amt"}

