"""Storage layer abstractions."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Dict


class InMemoryStorage:
    """Simple in-memory key-value store."""

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value


class EncryptedJSONStorage:
    """Persist data to disk with a naive XOR-based encryption."""

    def __init__(self, path: str, secret: str) -> None:
        self._path = path
        self._secret = secret.encode()

    def _xor(self, data: bytes) -> bytes:
        key = hashlib.sha256(self._secret).digest()
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self._path):
            return {}
        with open(self._path, "rb") as f:
            raw = f.read()
        if not raw:
            return {}
        decrypted = self._xor(base64.b64decode(raw))
        return json.loads(decrypted.decode("utf-8"))

    def save(self, data: Dict[str, Any]) -> None:
        plaintext = json.dumps(data).encode("utf-8")
        encrypted = base64.b64encode(self._xor(plaintext))
        with open(self._path, "wb") as f:
            f.write(encrypted)


_secret = os.getenv("STORAGE_SECRET", "changeme")
_cred_file = os.getenv("LEADER_CRED_FILE", "leader_credentials.json")
_leader_storage = EncryptedJSONStorage(_cred_file, _secret)


def save_leader_credentials(creds: Dict[str, str]) -> None:
    """Persist leader account credentials to disk."""

    _leader_storage.save(creds)


def load_leader_credentials() -> Dict[str, str]:
    """Load leader account credentials from storage."""

    return _leader_storage.load()
