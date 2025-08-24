"""API endpoints for follower account management."""

from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.accounts import Account, account_service
from services import follower_account_service

router = APIRouter(prefix="/follower-accounts", tags=["follower-accounts"])


class AccountPayload(BaseModel):
    """Payload for creating follower accounts."""

    name: str = Field(..., min_length=1)
    exchange: str = Field(..., min_length=1)
    env: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    passphrase: str | None = Field(default=None, min_length=1)


class CredentialsPayload(BaseModel):
    """Payload for verifying credentials."""

    exchange: str
    env: str
    api_key: str
    api_secret: str
    passphrase: str | None = None


class VerificationResult(BaseModel):
    """Result of credential verification."""

    valid: bool
    error: str | None = None


@router.post("", response_model=Dict[str, str])
async def create_follower_account(payload: AccountPayload) -> Dict[str, str]:
    """Register a new follower account."""

    if any(a.name == payload.name for a in account_service.list_accounts()):
        raise HTTPException(status_code=400, detail="account already exists")

    if payload.exchange.lower() == "bitget" and not payload.passphrase:
        raise HTTPException(status_code=400, detail="passphrase required")
    valid, error = await follower_account_service.verify_credentials(
        exchange=payload.exchange,
        env=payload.env,
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        passphrase=payload.passphrase,
    )
    if not valid:
        raise HTTPException(status_code=400, detail=error)

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


@router.post("/verify", response_model=VerificationResult)
async def verify_account_credentials(payload: CredentialsPayload) -> VerificationResult:
    """Validate account credentials without storing them."""

    require_pp = payload.exchange.lower() == "bitget"
    if require_pp and not payload.passphrase:
        raise HTTPException(status_code=400, detail="passphrase required")

    valid_fields = bool(
        payload.exchange
        and payload.env
        and payload.api_key
        and payload.api_secret
        and (payload.passphrase if require_pp else True)
    )
    if not valid_fields:
        raise HTTPException(status_code=400, detail="invalid credentials")

    valid, error = await follower_account_service.verify_credentials(
        exchange=payload.exchange,
        env=payload.env,
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        passphrase=payload.passphrase,
    )
    return {"valid": valid, "error": error}
