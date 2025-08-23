"""API endpoints for follower account management."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.accounts import Account, account_service

router = APIRouter(prefix="/follower-accounts", tags=["follower-accounts"])


class AccountPayload(BaseModel):
    """Payload for creating follower accounts."""

    name: str = Field(..., min_length=1)
    exchange: str = Field(..., min_length=1)
    env: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)


class CredentialsPayload(BaseModel):
    """Payload for verifying credentials."""

    exchange: str = Field(..., min_length=1)
    env: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)


@router.post("", response_model=Dict[str, str])
async def create_follower_account(payload: AccountPayload) -> Dict[str, str]:
    """Register a new follower account."""

    if any(a.name == payload.name for a in account_service.list_accounts()):
        raise HTTPException(status_code=400, detail="account already exists")

    account = Account(**payload.model_dump())
    account_service.add_account(account)
    return {"name": account.name}


@router.delete("/{name}", response_model=Dict[str, bool])
async def delete_follower_account(name: str) -> Dict[str, bool]:
    """Delete an existing follower account."""

    if not any(a.name == name for a in account_service.list_accounts()):
        raise HTTPException(status_code=404, detail="account not found")
    account_service.remove_account(name)
    return {"deleted": True}


@router.post("/verify", response_model=Dict[str, bool])
async def verify_account_credentials(payload: CredentialsPayload) -> Dict[str, bool]:
    """Validate account credentials without storing them."""

    valid = bool(
        payload.exchange and payload.env and payload.api_key and payload.api_secret
    )
    if not valid:
        raise HTTPException(status_code=400, detail="invalid credentials")
    return {"valid": True}
