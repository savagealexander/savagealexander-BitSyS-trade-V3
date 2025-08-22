"""Balance querying and caching service."""

from __future__ import annotations

import asyncio
from typing import Dict

from .accounts import account_service
from .connectors.binance import BinanceConnector
from .connectors.bitget import BitgetConnector


class BalanceService:
    """Service responsible for fetching and caching account balances.

    Balances are retrieved from exchange REST endpoints and cached in-memory.
    Updates can be triggered by external events via :meth:`trigger_update`
    while a polling loop running every few seconds acts as a fallback.
    """

    def __init__(self, poll_interval: float = 5.0) -> None:
        self._cache: Dict[str, Dict[str, float]] = {}
        self._poll_interval = poll_interval
        self._connectors = {
            "binance": BinanceConnector,
            "bitget": BitgetConnector,
        }
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

    async def _poll(self, account_name: str) -> None:
        while True:
            await self.update_balance(account_name)
            await asyncio.sleep(self._poll_interval)

    async def start(self) -> None:
        """Start polling balances for all known accounts."""
        for account in account_service.list_accounts():
            if account.name not in self._tasks:
                self._tasks[account.name] = asyncio.create_task(
                    self._poll(account.name)
                )

    async def get_balance(self, account_name: str) -> Dict[str, float]:
        """Return cached balance information for an account."""
        return self._cache.get(account_name, {"BTC": 0.0, "USDT": 0.0})


# Singleton instance used by API routes
balance_service = BalanceService()

