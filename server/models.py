"""Pydantic models used across the application."""

from pydantic import BaseModel


class StatusResponse(BaseModel):
    """Response model for the `/status` endpoint."""

    status: str
