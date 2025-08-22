"""Pydantic models used across the application."""

from pydantic import BaseModel


class LeaderConfig(BaseModel):
    """Configuration for the leader (main) account."""

    exchange: str
    env: str
    api_key: str
    api_secret: str


class StatusResponse(BaseModel):
    """Response model for the `/status` endpoint."""

    status: str
