"""API routes for the trading service."""

from fastapi import APIRouter

from .models import StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def read_status() -> StatusResponse:
    """Simple health check endpoint."""
    return StatusResponse(status="ok")
