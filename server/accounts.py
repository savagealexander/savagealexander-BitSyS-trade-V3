"""Account management module."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List

from .storage import load_accounts, save_accounts


class AccountStatus(str, Enum):
    """Enumeration of supported account states."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


@dataclass
class Account:
    """Representation of an exchange account."""

    name: str
    exchange: str
    env: str
    api_key: str
    api_secret: str
    status: AccountStatus = AccountStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Account":
        copied = data.copy()
        copied["status"] = AccountStatus(copied.get("status", "active"))
        return cls(**copied)


class AccountService:
    """Service responsible for managing accounts."""

    def __init__(self) -> None:
        stored = load_accounts()
        self._accounts: Dict[str, Account] = {
            acc["name"]: Account.from_dict(acc) for acc in stored
        }

    def list_accounts(self) -> List[Account]:
        """Return all configured accounts."""
        return list(self._accounts.values())

    def add_account(self, account: Account) -> None:
        """Register a new trading account."""
        self._validate(account)
        self._accounts[account.name] = account
        self._persist()

    def update_account(self, name: str, **updates: Any) -> None:
        """Update fields for an existing account."""
        acct = self._accounts.get(name)
        if not acct:
            raise KeyError(f"Account '{name}' not found")
        for key, value in updates.items():
            if hasattr(acct, key):
                if key == "status":
                    value = AccountStatus(value)
                setattr(acct, key, value)
        self._validate(acct)
        self._persist()

    def remove_account(self, name: str) -> None:
        """Remove an existing account by name."""
        if name in self._accounts:
            del self._accounts[name]
            self._persist()

    def _persist(self) -> None:
        save_accounts([a.to_dict() for a in self._accounts.values()])

    def _validate(self, account: Account) -> None:
        """Placeholder for account validation logic."""
        # TODO: implement real validation logic
        pass


# Singleton instance used by other modules
account_service = AccountService()
