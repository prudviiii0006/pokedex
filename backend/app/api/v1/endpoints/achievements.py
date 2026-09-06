"""
AlgoRacers — Session 16: Achievements REST Endpoints
Module: api/v1/endpoints/achievements.py
===================================================
Provides endpoints for:
  - Listing all achievements with player progress (`GET /achievements`)
  - Verifying achievement unlock and on-chain credential (`GET /achievements/{achievement_id}/verify`)
"""

from typing import List, Optional
from fastapi import APIRouter, Header, Body, Path, Query, HTTPException, status, Depends
from backend.app.models.achievement import AchievementItem, AchievementVerifyResponse
from backend.app.services.achievement_service import achievement_service
from backend.app.services.credential_service import credential_service
from backend.app.core.security import get_optional_wallet

router = APIRouter()

@router.get(
    "",
    response_model=List[AchievementItem],
    summary="List Achievements Catalog",
    description="Retrieves all available game achievements along with unlock progress for the caller."
)
async def list_achievements(
    wallet: Optional[str] = Query(None, description="Optional wallet address to inspect"),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    target_wallet = wallet or authenticated_wallet or "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    return achievement_service.get_player_achievements(target_wallet)

@router.get(
    "/{achievement_id}/verify",
    response_model=AchievementVerifyResponse,
    summary="Verify Achievement Credential",
    description="Audits achievement unlock proof and on-chain credential state."
)
async def verify_achievement(
    achievement_id: str = Path(..., examples=["TOURNAMENT_CHAMPION"]),
    wallet: str = Query(..., description="Wallet address to verify achievement for")
):
    res = credential_service.verify_credential(wallet, achievement_id)
    return AchievementVerifyResponse(
        achievement_id=achievement_id,
        wallet_address=wallet,
        verified=res["verified"],
        credential_status=res["credential_status"],
        credential_asset_id=res.get("credential_asset_id"),
        issuance_tx_id=res.get("issuance_tx_id"),
        source_event_id=res.get("source_event_id"),
        message=res["message"]
    )
