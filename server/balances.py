"""Balance querying service.

Provides a placeholder implementation for retrieving account balances.
"""

from typing import Dict


class BalanceService:
    """Service responsible for fetching account balances."""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, float]] = {}

    async def get_balance(self, account_name: str) -> Dict[str, float]:
        """Return cached balance information for an account.

        Real implementation will query the exchange's API.
        """
        return self._cache.get(account_name, {})
