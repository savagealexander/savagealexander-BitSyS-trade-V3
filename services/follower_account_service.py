from __future__ import annotations

"""Service for follower account credential validation."""

import base64
import time
import hmac
from hashlib import sha256
from urllib.parse import urlencode
from typing import Tuple

try:  # Optional dependency in test environments
    import httpx
except Exception:  # pragma: no cover - degraded functionality
    httpx = None


async def verify_credentials(
    *,
    exchange: str,
    env: str,
    api_key: str,
    api_secret: str,
    passphrase: str | None = None,
) -> Tuple[bool, str]:
    """Verify API credentials against the exchange REST API.

    Returns a tuple ``(valid, error)`` where ``valid`` indicates whether the
    credentials are accepted by the exchange and ``error`` contains any error
    message returned by the exchange (or a generic message on failure).
    """

    exchange = exchange.lower()
    env = env.lower()

    if httpx is None:
        return False, "httpx not installed"

    if exchange == "binance":
        testnet = env in {"test", "testnet"}
        base = "https://api.binance.com"
        if testnet:
            base = "https://testnet.binance.vision"
        async with httpx.AsyncClient(base_url=base) as client:
            try:
                ts = int(time.time() * 1000)
                params = {"timestamp": ts}
                query = urlencode(params)
                sig = hmac.new(api_secret.encode(), query.encode(), sha256).hexdigest()
                headers = {"X-MBX-APIKEY": api_key}
                url = f"/api/v3/account?{query}&signature={sig}"
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return True, ""
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors
                try:
                    err = exc.response.json().get("msg", exc.response.text)
                except Exception:  # pragma: no cover - best effort
                    err = exc.response.text
                return False, err or "invalid credentials"
            except Exception as exc:  # pragma: no cover
                return False, str(exc)

    elif exchange == "bitget":
        if not passphrase:
            return False, "passphrase required"
        demo = env == "demo"
        base = "https://api.bitget.com"
        async with httpx.AsyncClient(base_url=base) as client:
            try:
                ts = str(int(time.time() * 1000))
                method = "GET"
                path = "/api/spot/v1/account/assets"
                prehash = f"{ts}{method}{path}"
                sig = base64.b64encode(
                    hmac.new(api_secret.encode(), prehash.encode(), sha256).digest()
                ).decode()
                headers = {
                    "ACCESS-KEY": api_key,
                    "ACCESS-SIGN": sig,
                    "ACCESS-TIMESTAMP": ts,
                    "ACCESS-PASSPHRASE": passphrase,
                    "Content-Type": "application/json",
                }
                if demo:
                    headers["paptrading"] = "1"
                resp = await client.get(path, headers=headers)
                resp.raise_for_status()
                return True, ""
            except httpx.HTTPStatusError as exc:  # pragma: no cover
                try:
                    data = exc.response.json()
                    err = (
                        data.get("msg")
                        or data.get("message")
                        or data.get("error")
                        or data.get("errmsg")
                        or exc.response.text
                    )
                except Exception:  # pragma: no cover
                    err = exc.response.text
                return False, err or "invalid credentials"
            except Exception as exc:  # pragma: no cover
                return False, str(exc)

    else:
        return False, "unsupported exchange"
