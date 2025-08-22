"""Idempotency utilities for safe order replication."""

from __future__ import annotations

import json
import os
from typing import Set, Tuple


class IdempotencyStore:
    """Tracks processed events to avoid duplicate actions.

    The store persists processed keys to a JSON file so that restarts do not
    result in duplicate orders being submitted. Each key is a tuple of
    ``(event_id, account_name)``.
    """

    def __init__(self, path: str = "idempotency.json") -> None:
        self._path = path
        self._processed: Set[Tuple[str, str]] = set()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                if isinstance(item, list) and len(item) == 2:
                    self._processed.add((item[0], item[1]))
        except Exception:
            # Corrupt files are ignored; start with empty store
            self._processed = set()

    def _save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump([list(k) for k in self._processed], f)
        except Exception:
            pass

    def is_processed(self, key: Tuple[str, str]) -> bool:
        return key in self._processed

    def mark_processed(self, key: Tuple[str, str]) -> None:
        self._processed.add(key)
        self._save()
