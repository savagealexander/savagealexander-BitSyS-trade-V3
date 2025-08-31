"""Dispatch copy trading orders to follower accounts."""

from __future__ import annotations
import logging
from math import floor

from .accounts import AccountStatus, account_service, AccountService
from .balances import balance_service, BalanceService
from .idempotency import IdempotencyStore

try:  # optional during tests
    from .connectors import BinanceSDKConnector, BitgetConnector
except Exception:  # pragma: no cover
    BinanceSDKConnector = BitgetConnector = None

# Maintain backwards compatibility for tests that patch BinanceConnector
BinanceConnector = BinanceSDKConnector

SYMBOL = "BTCUSDT"


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
        self._log = logging.getLogger(__name__)

    def start(self) -> None:
        self._enabled = True

    def stop(self) -> None:
        self._enabled = False

    def is_running(self) -> bool:
        return self._enabled

    def get_last_results(self) -> dict[str, dict]:
        return self._last_results

    # 小工具：用于排查是否同一个实例（不影响业务）
    def get_instance_id(self) -> int:
        return id(self)

    @staticmethod
    def _round_down(v: float, decimals: int) -> float:
        """向下截断到指定小数位（比四舍五入更安全，避免超额）。"""
        if decimals <= 0:
            return float(floor(v))
        scale = 10 ** decimals
        return floor(v * scale) / scale

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

        # 计算比例（保持原逻辑）
        quote_ratio = max(0.0, min(leader_quote / free_usdt, 1.0)) if free_usdt else 0.0
        base_ratio = max(0.0, min(leader_base / free_btc, 1.0)) if free_btc else 0.0

        for account in self._accounts.list_accounts():
            if account.status != AccountStatus.ACTIVE:
                continue
            key = (event_id, account.name)
            if self._idem.is_processed(key):
                continue

            connector_cls = self._connectors.get(account.exchange)
            if connector_cls is None:
                continue

            # 读取余额并按比例换算金额（保持原逻辑）
            balance = await self._balances.get_balance(account.name)
            quote_amt = max(0.0, balance.get("USDT", 0.0) * quote_ratio)
            base_amt = max(0.0, balance.get("BTC", 0.0) * base_ratio)

            # 原有的计算日志（保留）
            try:
                print(
                    f"[DISPATCH] {event_id=} {side=} {leader_quote=} {free_usdt=} "
                    f"{quote_ratio=} {leader_base=} {free_btc=} {base_ratio=} "
                    f"{account.name=} {balance=} {quote_amt=} {base_amt=}"
                )
            except Exception:
                pass

            # 下单前日志（新增）
            self._log.info(
                "[ORDER] -> inst=%s acct=%s ex=%s env=%s side=%s symbol=%s "
                "quote_amt=%.10f base_amt=%.10f q_ratio=%.6f b_ratio=%.6f "
                "leader_quote=%.10f leader_base=%.10f free_usdt=%.10f free_btc=%.10f",
                id(self), account.name, account.exchange, getattr(account, "env", ""),
                side, SYMBOL, quote_amt, base_amt, quote_ratio, base_ratio,
                leader_quote, leader_base, free_usdt, free_btc
            )

            # === 仅新增：按交易所规则向下截断小数位，避免精度拒单 ===
            if account.exchange == "binance":
                if side == "BUY":
                    # Binance BUY 用 quoteOrderQty（USDT），一般按 2 位处理
                    quote_amt = self._round_down(quote_amt, 2)
                else:
                    # Binance SELL 用 quantity（BTC），常见 6 位足够
                    base_amt = self._round_down(base_amt, 6)
            elif account.exchange == "bitget":
                # Bitget 错误明确提示 checkScale=8
                if side == "BUY":
                    quote_amt = self._round_down(quote_amt, 8)
                else:
                    base_amt = self._round_down(base_amt, 8)

            # 记录对齐后的金额（新增）
            self._log.info(
                "[ORDER-SANITIZED] inst=%s acct=%s ex=%s side=%s quote_amt=%.10f base_amt=%.10f",
                id(self), account.name, account.exchange, side, quote_amt, base_amt
            )

            # 金额为 0 的早退（保持原语义，仅加一条提示日志）
            if side == "BUY" and quote_amt <= 0:
                self._last_results[account.name] = {
                    "success": False,
                    "error": "zero quote_amt",
                }
                self._log.warning(
                    "[ORDER-SKIP] zero quote_amt inst=%s acct=%s", id(self), account.name
                )
                continue
            if side == "SELL" and base_amt <= 0:
                self._last_results[account.name] = {
                    "success": False,
                    "error": "zero base_amt",
                }
                self._log.warning(
                    "[ORDER-SKIP] zero base_amt inst=%s acct=%s", id(self), account.name
                )
                continue

            # === 下单逻辑（保持原调用方式与连接器用法不变）===
            try:
                if account.exchange == "binance":
                    connector = connector_cls(
                        api_key=account.api_key,
                        api_secret=account.api_secret,
                        testnet=getattr(account, "env", "") == "test",
                    )
                    try:
                        if side == "BUY":
                            # BUY 用 quote 数量
                            result = await connector.order_market_buy(SYMBOL, quote_amt)
                        else:
                            # SELL 用 base 数量
                            result = await connector.order_market_sell(SYMBOL, base_amt)
                    finally:
                        await connector.close()
                else:
                    # 兼容 bitget / 其它 HTTP 连接器的构造参数（保持原有判断）
                    kwargs = (
                        {"demo": getattr(account, "env", "") == "demo"}
                        if account.exchange == "bitget"
                        else {"testnet": getattr(account, "env", "") == "test"}
                    )
                    async with connector_cls(**kwargs) as connector:
                        if account.exchange == "bitget":
                            if side == "BUY":
                                result = await connector.create_market_order(
                                    account.api_key,
                                    account.api_secret,
                                    getattr(account, "passphrase", "") or "",
                                    side,
                                    quote_amount=quote_amt,
                                )
                            else:
                                result = await connector.create_market_order(
                                    account.api_key,
                                    account.api_secret,
                                    getattr(account, "passphrase", "") or "",
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

                # 成功：触发余额刷新、标记幂等、记录结果（保持原逻辑）
                self._balances.trigger_update(account.name)
                self._idem.mark_processed(key)
                self._last_results[account.name] = {"success": True, "data": result}
                self._log.info(
                    "[ORDER-OK] <- acct=%s inst=%s ex=%s",
                    account.name, id(self), account.exchange
                )
            except Exception as exc:
                # 失败：提取 reason 并落地（保持原逻辑）
                reason = str(exc)
                if hasattr(exc, "response"):
                    try:
                        reason = exc.response.text
                    except Exception:
                        pass
                self._last_results[account.name] = {"success": False, "error": reason}
                self._log.error(
                    "[ORDER-FAIL] <- acct=%s inst=%s ex=%s reason=%s",
                    account.name, id(self), account.exchange, reason
                )
                continue


copy_dispatcher = CopyDispatcher(account_service, balance_service, IdempotencyStore())
