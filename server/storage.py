"""Storage layer abstractions."""

from typing import Any, Dict


class InMemoryStorage:
    """Simple in-memory key-value store."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
