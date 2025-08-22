"""Dispatch copy trading orders to follower accounts."""

from __future__ import annotations

from .accounts import AccountStatus, account_service, AccountService
from .balances import balance_service, BalanceService
from .idempotency import IdempotencyStore
from .connectors import BinanceConnector, BitgetConnector


class CopyDispatcher:
    """Dispatcher that will copy leader orders to follower accounts."""

    def __init__(
        self,
        accounts: AccountService,
        balances: BalanceService,
        idem_store: IdempotencyStore,
    ) -> None:
        self._accounts = accounts
        self._balances = balances
        self._idem = idem_store
        self._connectors = {
            "binance": BinanceConnector,
            "bitget": BitgetConnector,
        }

    async def dispatch(self, order_event: dict) -> None:
        """Dispatch an order event to all followers."""
        event_id = order_event.get("event_id")
        side = order_event.get("side")
        leader_quote = float(order_event.get("quote_filled", 0.0))
        leader_base = float(order_event.get("base_filled", 0.0))
        free_usdt = float(order_event.get("leader_free_usdt", 0.0))
        free_btc = float(order_event.get("leader_free_btc", 0.0))

        quote_ratio = leader_quote / free_usdt if free_usdt else 0.0
        base_ratio = leader_base / free_btc if free_btc else 0.0

        for account in self._accounts.list_accounts():
            if account.status != AccountStatus.ACTIVE:
                continue
            key = (event_id, account.name)
            if self._idem.is_processed(key):
                continue
            connector_cls = self._connectors.get(account.exchange)
            if connector_cls is None:
                continue
            balance = await self._balances.get_balance(account.name)
            quote_amt = balance.get("USDT", 0.0) * quote_ratio
            base_amt = balance.get("BTC", 0.0) * base_ratio
            try:
                async with connector_cls(testnet=account.env == "test") as connector:
                    if side == "BUY":
                        await connector.create_market_order(
                            account.api_key,
                            account.api_secret,
                            side,
                            quote_amount=quote_amt,
                        )
                    else:
                        await connector.create_market_order(
                            account.api_key,
                            account.api_secret,
                            side,
                            base_amount=base_amt,
                        )
                self._balances.trigger_update(account.name)
                self._idem.mark_processed(key)
            except Exception:
                continue


copy_dispatcher = CopyDispatcher(account_service, balance_service, IdempotencyStore())
