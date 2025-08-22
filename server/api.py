"""API routes for the trading service."""

from fastapi import APIRouter

from .balances import balance_service
from .models import StatusResponse
from typing import Dict

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def read_status() -> StatusResponse:
    """Simple health check endpoint."""
    return StatusResponse(status="ok")


@router.get("/balances/{account}")
async def read_balance(account: str) -> Dict[str, float]:
    """Return the most recently cached balance for ``account``."""
    return await balance_service.get_balance(account)
