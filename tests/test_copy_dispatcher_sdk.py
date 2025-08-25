import asyncio
from dataclasses import dataclass

import pytest

from server.copy_dispatcher import CopyDispatcher
from server.accounts import Account


@dataclass
class StubAccounts:
    accounts: list

    def list_accounts(self):
        return self.accounts


class StubBalances:
    def __init__(self, balances):
        self._balances = balances
        self.updated = []

    async def get_balance(self, name):
        return self._balances[name]

    def trigger_update(self, name):  # pragma: no cover - simple record
        self.updated.append(name)


from server.idempotency import IdempotencyStore


def _dispatch(event, dummy_binance_sdk, tmp_path):
    async def _run():
        account = Account(
            name="acc1",
            exchange="binance",
            env="test",
            api_key="k",
            api_secret="s",
        )
        accounts = StubAccounts([account])
        balances = StubBalances({"acc1": {"USDT": 50.0, "BTC": 1.0}})
        idem = IdempotencyStore(path=str(tmp_path / "idem.json"))
        dispatcher = CopyDispatcher(accounts, balances, idem)
        dispatcher._connectors = {"binance": dummy_binance_sdk}
        await dispatcher.dispatch(event)
        return dummy_binance_sdk.last_instance.order_calls[0]

    return asyncio.run(_run())


def test_buy_clamps_and_uses_sdk(dummy_binance_sdk, tmp_path):
    event = {
        "event_id": 1,
        "side": "BUY",
        "quote_filled": 150.0,
        "base_filled": 0.0,
        "leader_pre_usdt": 100.0,
        "leader_pre_btc": 1.0,
    }
    call = _dispatch(event, dummy_binance_sdk, tmp_path)
    assert call == ("BUY", pytest.approx(50.0))


def test_sell_clamps_and_uses_sdk(dummy_binance_sdk, tmp_path):
    event = {
        "event_id": 2,
        "side": "SELL",
        "quote_filled": 0.0,
        "base_filled": 2.0,
        "leader_pre_usdt": 100.0,
        "leader_pre_btc": 1.0,
    }
    call = _dispatch(event, dummy_binance_sdk, tmp_path)
    assert call == ("SELL", pytest.approx(1.0))
