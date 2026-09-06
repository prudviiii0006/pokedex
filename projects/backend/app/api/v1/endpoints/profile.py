"""
AlgoRacers — Session 16: Player Profile REST Endpoints
Module: api/v1/endpoints/profile.py
======================================================
Provides endpoints for:
  - Authenticated player profile retrieval (`GET /me/profile`)
  - Public player profile inspection (`GET /players/{wallet_address}`)
  - Profile ledger reconciliation & audit (`POST /profile/reconcile`)
"""

from typing import Optional
from fastapi import APIRouter, Header, Body, Path, HTTPException, status, Depends
from backend.app.models.profile import (
    PlayerProfileResponse, PublicPlayerProfileResponse,
    ProfileReconcileResponse, PlayerStats
)
from backend.app.services.player_stats_service import player_stats_service
from backend.app.services.progression_service import progression_service
from backend.app.services.achievement_service import achievement_service
from backend.app.services.reputation_service import reputation_service
from backend.app.services.reconciliation_service import reconciliation_service
from backend.app.core.security import get_optional_wallet, get_current_wallet
from backend.app.core.database import get_db

router = APIRouter()

@router.get(
    "/me/profile",
    response_model=PlayerProfileResponse,
    summary="Get Authenticated Player Profile",
    description="Retrieves private player progression, level, stats, reputation, and unlocked achievements for current session."
)
async def get_my_profile(
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    wallet = authenticated_wallet or "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"

    stats = player_stats_service.get_player_stats(wallet)
    achievements = achievement_service.get_player_achievements(wallet)

    with get_db() as conn:
        prof = conn.execute("SELECT * FROM player_profiles WHERE wallet_address = ?;", (wallet,)).fetchone()
        xp = prof["xp"] if prof else 0
        level, next_threshold, progress_pct = progression_service.calculate_level(xp)
        rep = prof["reputation_score"] if prof and prof["reputation_score"] is not None else 1000
        display_name = prof["display_name"] if prof else None
        created_at = prof["created_at"] if prof else "2026-08-30T12:00:00Z"
        updated_at = prof["updated_at"] if prof else "2026-08-30T12:00:00Z"

    tier = reputation_service.get_rank_tier(rep)
    unlocked_count = sum(1 for a in achievements if a.unlocked)

    return PlayerProfileResponse(
        wallet_address=wallet,
        display_name=display_name,
        xp=xp,
        level=level,
        next_level_xp=next_threshold,
        level_progress_percent=progress_pct,
        reputation_score=rep,
        reputation_rank_tier=tier,
        stats=stats,
        achievement_count=unlocked_count,
        achievements=achievements,
        created_at=created_at,
        updated_at=updated_at
    )

@router.get(
    "/players/{wallet_address}",
    response_model=PublicPlayerProfileResponse,
    summary="Get Public Player Profile",
    description="Retrieves public racing stats, reputation tier, and badges for any wallet address."
)
async def get_public_profile(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    stats = player_stats_service.get_player_stats(wallet_address)
    achievements = achievement_service.get_player_achievements(wallet_address)

    with get_db() as conn:
        prof = conn.execute("SELECT * FROM player_profiles WHERE wallet_address = ?;", (wallet_address,)).fetchone()
        xp = prof["xp"] if prof else 0
        level, _, _ = progression_service.calculate_level(xp)
        rep = prof["reputation_score"] if prof and prof["reputation_score"] is not None else 1000
        display_name = prof["display_name"] if prof else None

    tier = reputation_service.get_rank_tier(rep)
    unlocked_count = sum(1 for a in achievements if a.unlocked)

    return PublicPlayerProfileResponse(
        wallet_address=wallet_address,
        display_name=display_name,
        level=level,
        reputation_score=rep,
        reputation_rank_tier=tier,
        stats=stats,
        achievement_count=unlocked_count,
        achievements=achievements
    )

@router.post(
    "/profile/reconcile",
    response_model=ProfileReconcileResponse,
    summary="Reconcile Player Profile from Ledger",
    description="Reconstructs XP, Level, Reputation, and Achievements from raw immutable events to repair any cached state drift."
)
async def reconcile_profile(
    body: dict = Body(default={}),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    target_wallet = body.get("wallet_address") or authenticated_wallet or "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    return reconciliation_service.reconcile_player(target_wallet)
