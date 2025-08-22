"""Service layer for managing follower accounts."""

from __future__ import annotations

import os
from typing import Dict, List, Literal

from pydantic import BaseModel, Field

from server.storage import JSONStorage


class FollowerAccount(BaseModel):
    """Representation of a follower trading account."""

    id: str = Field(..., min_length=1)
    exchange: str = Field(..., min_length=1)
    env: Literal["live", "test"]
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)


class FollowerAccountService:
    """Service responsible for CRUD operations on follower accounts."""

    def __init__(self, storage_path: str | None = None) -> None:
        path = storage_path or os.getenv(
            "FOLLOWER_ACCOUNTS_FILE", "follower_accounts.json"
        )
        self._storage = JSONStorage(path)
        data = self._storage.load().get("accounts", [])
        self._accounts: Dict[str, FollowerAccount] = {
            acc["id"]: FollowerAccount(**acc) for acc in data
        }

    def list_accounts(self) -> List[FollowerAccount]:
        """Return all stored follower accounts."""

        return list(self._accounts.values())

    def create_account(self, account: FollowerAccount) -> None:
        """Persist a new follower account.

        Raises:
            ValueError: If an account with the same ``id`` already exists.
        """

        if account.id in self._accounts:
            raise ValueError("account already exists")
        self._accounts[account.id] = account
        self._persist()

    def delete_account(self, account_id: str) -> None:
        """Remove a follower account.

        Raises:
            KeyError: If the account does not exist.
        """

        if account_id not in self._accounts:
            raise KeyError("account not found")
        del self._accounts[account_id]
        self._persist()

    def verify_credentials(
        self, exchange: str, env: str, api_key: str, api_secret: str
    ) -> bool:
        """Basic credential verification.

        This implementation simply checks that keys are non-empty. Real-world
        implementations would perform requests to the target exchange.
        """

        return bool(exchange and env and api_key and api_secret)

    def _persist(self) -> None:
        self._storage.save(
            {"accounts": [acc.model_dump() for acc in self._accounts.values()]}
        )


# Singleton instance used by API routes
follower_account_service = FollowerAccountService()
