"""API endpoints for follower account management."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.follower_account_service import (
    FollowerAccount,
    follower_account_service,
)

router = APIRouter(prefix="/follower-accounts", tags=["follower-accounts"])


class CredentialsPayload(BaseModel):
    """Payload for verifying credentials."""

    exchange: str = Field(..., min_length=1)
    env: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)


@router.post("", response_model=Dict[str, str])
async def create_follower_account(account: FollowerAccount) -> Dict[str, str]:
    """Register a new follower account."""

    try:
        follower_account_service.create_account(account)
    except ValueError as exc:  # duplicate
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": account.id}


@router.delete("/{account_id}", response_model=Dict[str, bool])
async def delete_follower_account(account_id: str) -> Dict[str, bool]:
    """Delete an existing follower account."""

    try:
        follower_account_service.delete_account(account_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"deleted": True}


@router.post("/verify", response_model=Dict[str, bool])
async def verify_account_credentials(payload: CredentialsPayload) -> Dict[str, bool]:
    """Validate account credentials without storing them."""

    valid = follower_account_service.verify_credentials(
        payload.exchange, payload.env, payload.api_key, payload.api_secret
    )
    if not valid:
        raise HTTPException(status_code=400, detail="invalid credentials")
    return {"valid": True}
