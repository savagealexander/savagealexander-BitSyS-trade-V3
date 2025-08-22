"""Idempotency utilities for safe order replication."""

from typing import Set, Tuple


class IdempotencyStore:
    """Tracks processed events to avoid duplicate actions."""

    def __init__(self) -> None:
        self._processed: Set[Tuple[str, str]] = set()

    def is_processed(self, key: Tuple[str, str]) -> bool:
        return key in self._processed

    def mark_processed(self, key: Tuple[str, str]) -> None:
        self._processed.add(key)
