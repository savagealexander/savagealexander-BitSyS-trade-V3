"""Balance querying and caching service."""

from __future__ import annotations

import asyncio
from typing import Dict

from .accounts import account_service

try:  # Optional imports during tests where dependencies may be missing
    from .connectors.binance import BinanceConnector
    from .connectors.bitget import BitgetConnector
except Exception:  # pragma: no cover - degraded functionality for tests
    BinanceConnector = BitgetConnector = None


class BalanceService:
    """Service responsible for fetching and caching account balances.

    Balances are retrieved from exchange REST endpoints and cached in-memory.
    Updates can be triggered by external events via :meth:`trigger_update`
    while a polling loop running every few seconds acts as a fallback.
    """

    def __init__(self, poll_interval: float = 5.0) -> None:
        self._cache: Dict[str, Dict[str, float]] = {}
        self._poll_interval = poll_interval
        self._connectors = {}
        if BinanceConnector:
            self._connectors["binance"] = BinanceConnector
        if BitgetConnector:
            self._connectors["bitget"] = BitgetConnector
        self._tasks: Dict[str, asyncio.Task] = {}

    async def update_balance(self, account_name: str) -> None:
        """Fetch and cache the latest balance for ``account_name``."""

        account = next(
            (a for a in account_service.list_accounts() if a.name == account_name),
            None,
        )
        if account is None:
            return

        connector_cls = self._connectors.get(account.exchange)
        if connector_cls is None:
            return
        try:
            if account.exchange == "bitget":
                async with connector_cls(demo=account.env == "demo") as connector:
                    balance = await connector.get_balance(
                        account.api_key, account.api_secret, account.passphrase or ""
                    )
            else:
                async with connector_cls(testnet=account.env == "test") as connector:
                    balance = await connector.get_balance(
                        account.api_key, account.api_secret
                    )
            self._cache[account_name] = balance
        except Exception:
            # Errors are swallowed to keep polling alive
            self._cache.setdefault(account_name, {"BTC": 0.0, "USDT": 0.0})

    def trigger_update(self, account_name: str) -> None:
        """Trigger an asynchronous balance refresh for ``account_name``."""
        asyncio.create_task(self.update_balance(account_name))

    def register_account(self, account_name: str) -> None:
        """Begin polling balances for ``account_name`` if not already running."""
        if account_name not in self._tasks:
            self._tasks[account_name] = asyncio.create_task(self._poll(account_name))
            # Populate initial balance data immediately
            self.trigger_update(account_name)

    async def _poll(self, account_name: str) -> None:
        while True:
            await self.update_balance(account_name)
            await asyncio.sleep(self._poll_interval)

    async def start(self) -> None:
        """Start polling balances for all known accounts."""
        for account in account_service.list_accounts():
            # Synchronously populate cache before starting background polling
            await self.update_balance(account.name)
            self.register_account(account.name)

    async def get_balance(self, account_name: str) -> Dict[str, float]:
        """Return cached balance information for an account."""
        return self._cache.get(account_name, {"BTC": 0.0, "USDT": 0.0})


# Singleton instance used by API routes
balance_service = BalanceService()

