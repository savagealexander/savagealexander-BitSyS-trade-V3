"""Account management module.

Provides CRUD operations for trading accounts and placeholder
implementations for future development.
"""

from typing import Any, Dict, List


class Account:
    """Placeholder representation of an exchange account."""

    def __init__(self, name: str, api_key: str, api_secret: str) -> None:
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret


class AccountService:
    """Service responsible for managing accounts.

    Actual storage and validation logic will be implemented in later stages.
    """

    def __init__(self) -> None:
        self._accounts: Dict[str, Account] = {}

    def list_accounts(self) -> List[Account]:
        """Return all configured accounts."""
        return list(self._accounts.values())

    def add_account(self, account: Account) -> None:
        """Register a new trading account."""
        self._accounts[account.name] = account

    def remove_account(self, name: str) -> None:
        """Remove an existing account by name."""
        self._accounts.pop(name, None)
