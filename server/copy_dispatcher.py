"""Dispatch copy trading orders to follower accounts."""

from __future__ import annotations

import inspect

from .accounts import AccountStatus, account_service, AccountService
from .balances import balance_service, BalanceService
from .idempotency import IdempotencyStore

try:  # optional during tests
    from .connectors import BinanceSDKConnector, BitgetConnector
except Exception:  # pragma: no cover
    BinanceSDKConnector = BitgetConnector = None

# Maintain backwards compatibility for tests that patch BinanceConnector
BinanceConnector = BinanceSDKConnector


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
        self._connectors = {}
        if BinanceConnector:
            self._connectors["binance"] = BinanceConnector
        if BitgetConnector:
            self._connectors["bitget"] = BitgetConnector
        self._enabled: bool = True
        # Store per-account results for UI consumption
        self._last_results: dict[str, dict] = {}

    def start(self) -> None:
        self._enabled = True

    def stop(self) -> None:
        self._enabled = False

    def is_running(self) -> bool:
        return self._enabled

    def get_last_results(self) -> dict[str, dict]:
        return self._last_results

    async def dispatch(self, order_event: dict) -> None:
        """Dispatch an order event to all followers.

        Real order results are recorded and any failures are captured so the UI
        can surface them to the user.
        """
        if not self._enabled:
            return

        event_id = order_event.get("event_id")
        side = order_event.get("side")
        leader_quote = float(order_event.get("quote_filled", 0.0))
        leader_base = float(order_event.get("base_filled", 0.0))
        free_usdt = float(
            order_event.get("leader_pre_usdt")
            or order_event.get("leader_free_usdt", 0.0)
        )
        free_btc = float(
            order_event.get("leader_pre_btc")
            or order_event.get("leader_free_btc", 0.0)
        )

        quote_ratio = (
            max(0.0, min(leader_quote / free_usdt, 1.0)) if free_usdt else 0.0
        )
        base_ratio = (
            max(0.0, min(leader_base / free_btc, 1.0)) if free_btc else 0.0
        )

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
            quote_amt = max(0.0, balance.get("USDT", 0.0) * quote_ratio)
            base_amt = max(0.0, balance.get("BTC", 0.0) * base_ratio)
            try:
                print(
                    f"[DISPATCH] {event_id=} {side=} {leader_quote=} {free_usdt=} "
                    f"{quote_ratio=} {leader_base=} {free_btc=} {base_ratio=} "
                    f"{account.name=} {balance=} {quote_amt=} {base_amt=}"
                )
            except Exception:
                pass

            if side == "BUY" and quote_amt <= 0:
                self._last_results[account.name] = {
                    "success": False,
                    "error": "zero quote_amt",
                }
                continue
            if side == "SELL" and base_amt <= 0:
                self._last_results[account.name] = {
                    "success": False,
                    "error": "zero base_amt",
                }
                continue

            try:
                if account.exchange == "binance":
                    connector = connector_cls(
                        api_key=account.api_key,
                        api_secret=account.api_secret,
                        testnet=account.env == "test",
                    )
                    if side == "BUY":
                        result = connector.order_market_buy("BTCUSDT", quote_amt)
                    else:
                        result = connector.order_market_sell("BTCUSDT", base_amt)
                    if inspect.isawaitable(result):
                        result = await result
                else:
                    kwargs = (
                        {"demo": account.env == "demo"}
                        if account.exchange == "bitget"
                        else {"testnet": account.env == "test"}
                    )
                    async with connector_cls(**kwargs) as connector:
                        if account.exchange == "bitget":
                            if side == "BUY":
                                result = await connector.create_market_order(
                                    account.api_key,
                                    account.api_secret,
                                    account.passphrase or "",
                                    side,
                                    quote_amount=quote_amt,
                                )
                            else:
                                result = await connector.create_market_order(
                                    account.api_key,
                                    account.api_secret,
                                    account.passphrase or "",
                                    side,
                                    base_amount=base_amt,
                                )
                        else:
                            if side == "BUY":
                                result = await connector.create_market_order(
                                    account.api_key,
                                    account.api_secret,
                                    side,
                                    quote_amount=quote_amt,
                                )
                            else:
                                result = await connector.create_market_order(
                                    account.api_key,
                                    account.api_secret,
                                    side,
                                    base_amount=base_amt,
                                )
                self._balances.trigger_update(account.name)
                self._idem.mark_processed(key)
                self._last_results[account.name] = {"success": True, "data": result}
            except Exception as exc:
                # Record failure reason for UI display
                reason = str(exc)
                if hasattr(exc, "response"):
                    try:
                        reason = exc.response.text
                    except Exception:
                        pass
                self._last_results[account.name] = {"success": False, "error": reason}
                continue


copy_dispatcher = CopyDispatcher(account_service, balance_service, IdempotencyStore())
