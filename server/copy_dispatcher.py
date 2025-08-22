"""Dispatch copy trading orders to follower accounts."""

from typing import Iterable


class CopyDispatcher:
    """Placeholder dispatcher that will copy leader orders to followers."""

    def __init__(self) -> None:
        self._followers: Iterable[str] = []

    async def dispatch(self, order_event: dict) -> None:
        """Dispatch an order event to all followers.

        Real implementation will place orders on the exchanges.
        """
        _ = order_event
        for _f in self._followers:
            pass
