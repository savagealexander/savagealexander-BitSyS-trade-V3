"""API routes for the trading service."""

import asyncio
import os
from typing import Any, Dict, List

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from . import leader_watcher
from .accounts import AccountStatus, account_service
from .balances import balance_service
from .copy_dispatcher import copy_dispatcher
from .models import LeaderConfig, StatusResponse
from .storage import save_leader_credentials


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

API_TOKEN = os.getenv("API_TOKEN", "")


async def verify_token(authorization: str = Header("")) -> None:
    """Validate ``Authorization`` header against ``API_TOKEN`` env var."""

    if not API_TOKEN:
        return
    expected = f"Bearer {API_TOKEN}"
    if authorization != expected and authorization != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

_leader_task: asyncio.Task | None = None


async def _run_leader_watcher(cfg: LeaderConfig) -> None:
    async for event in leader_watcher.watch_leader_orders(
        cfg.api_key, testnet=cfg.env == "test"
    ):
        await copy_dispatcher.dispatch(event)


# Routers
public_router = APIRouter()
protected_router = APIRouter()


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------

@public_router.get("/status", response_model=StatusResponse)
async def read_status() -> StatusResponse:
    """Simple health check endpoint."""
    return StatusResponse(status="ok")


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------

@protected_router.get("/balances/{account}")
async def read_balance(account: str) -> Dict[str, float]:
    """Return the most recently cached balance for ``account``."""
    return await balance_service.get_balance(account)


@protected_router.put("/leader")
async def configure_leader(config: LeaderConfig) -> Dict[str, bool]:
    """Persist leader credentials and start watching orders."""

    save_leader_credentials(config.dict())

    global _leader_task
    if _leader_task:
        _leader_task.cancel()
        try:
            await _leader_task
        except Exception:
            pass
    _leader_task = asyncio.create_task(_run_leader_watcher(config))
    return {"listening": True}


@protected_router.post("/copy/start")
async def start_copy() -> Dict[str, bool]:
    """Enable order copying."""
    copy_dispatcher.start()
    return {"running": True}


@protected_router.post("/copy/stop")
async def stop_copy() -> Dict[str, bool]:
    """Disable order copying."""
    copy_dispatcher.stop()
    return {"running": False}


# ---------------------------------------------------------------------------
# Account management
# ---------------------------------------------------------------------------


class AccountStatusPayload(BaseModel):
    """Payload for updating an account's status."""

    status: AccountStatus


@protected_router.get("/accounts")
async def list_accounts() -> List[Dict[str, Any]]:
    """Return all configured accounts."""
    return [acc.to_dict() for acc in account_service.list_accounts()]


@protected_router.put("/accounts/{name}/status")
async def update_account_status(
    name: str, payload: AccountStatusPayload
) -> Dict[str, str]:
    """Update the status of an account."""

    account_service.update_account(name, status=payload.status)
    return {"status": payload.status.value}

