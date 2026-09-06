"""
AlgoRacers — Session 13: Authentication REST Endpoints
Module: api/v1/endpoints/auth.py
======================================================
Endpoints for:
  - Requesting signed challenge (POST /auth/challenge)
  - Verifying ed25519 signature (POST /auth/verify)
  - Inspecting session state (GET /auth/me)
  - Invalidation/Logout (POST /auth/logout)
"""

from typing import Optional
from fastapi import APIRouter, Response, Request, Header, Depends, HTTPException, status
from backend.app.models.auth import (
    ChallengeRequest, ChallengeResponse,
    VerifyRequest, AuthResponse,
    SessionMeResponse
)
from backend.app.services.auth_service import auth_service
from backend.app.core.security import get_current_wallet, get_session_from_request

router = APIRouter()

@router.post(
    "/challenge",
    response_model=ChallengeResponse,
    summary="Request Signed Authentication Challenge",
    description="Generates a cryptographically random, short-lived (5m), domain-bound challenge for Pera Wallet to sign."
)
async def request_challenge(body: ChallengeRequest):
    return auth_service.create_challenge(wallet_address=body.wallet_address)

@router.post(
    "/verify",
    response_model=AuthResponse,
    summary="Verify Signed Challenge & Create Session",
    description="Cryptographically verifies ed25519 signature, enforces single-use replay defense, and sets HttpOnly session cookie."
)
async def verify_signature(body: VerifyRequest, response: Response):
    auth_result = auth_service.verify_challenge(
        challenge_id=body.challenge_id,
        wallet_address=body.wallet_address,
        signature=body.signature
    )

    # Set secure HttpOnly session cookie (SameSite=Lax)
    response.set_cookie(
        key="algoracers_session",
        value=auth_result.session_id,
        httponly=True,
        samesite="lax",
        secure=False,  # Set to True on HTTPS in production
        max_age=86400  # 24 hours
    )

    return auth_result

@router.get(
    "/me",
    response_model=SessionMeResponse,
    summary="Get Authenticated Wallet Identity",
    description="Inspects active session cookie/bearer token and returns authenticated wallet address."
)
async def get_my_session(
    request: Request,
    authorization: Optional[str] = Header(None),
    current_wallet: str = Depends(get_current_wallet)
):
    session = get_session_from_request(request, authorization)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return SessionMeResponse(
        authenticated=True,
        wallet_address=current_wallet,
        session_id=session["session_id"],
        expires_at=session["expires_at"],
        created_at=session["created_at"]
    )

@router.post(
    "/logout",
    summary="Revoke Authenticated Session",
    description="Invalidates the session in SQLite and clears the session cookie."
)
async def logout(
    request: Request,
    response: Response,
    authorization: Optional[str] = Header(None)
):
    session = get_session_from_request(request, authorization)
    if session:
        auth_service.logout(session["session_id"])

    response.delete_cookie(key="algoracers_session")
    return {"authenticated": False, "message": "Session revoked successfully."}
