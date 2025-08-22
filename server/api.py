"""API routes for the trading service."""

import asyncio
from fastapi import APIRouter

from .balances import balance_service
from .copy_dispatcher import copy_dispatcher
from .models import LeaderConfig, StatusResponse
from .storage import save_leader_credentials
from . import leader_watcher
from typing import Dict


_leader_task: asyncio.Task | None = None


async def _run_leader_watcher(cfg: LeaderConfig) -> None:
    async for event in leader_watcher.watch_leader_orders(
        cfg.api_key, testnet=cfg.env == "test"
    ):
        await copy_dispatcher.dispatch(event)

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def read_status() -> StatusResponse:
    """Simple health check endpoint."""
    return StatusResponse(status="ok")


@router.get("/balances/{account}")
async def read_balance(account: str) -> Dict[str, float]:
    """Return the most recently cached balance for ``account``."""
    return await balance_service.get_balance(account)


@router.put("/leader")
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
