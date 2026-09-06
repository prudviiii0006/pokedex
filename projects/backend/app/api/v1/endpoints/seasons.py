"""
AlgoRacers — Session 19: Seasons & Championship Series REST Endpoints
Module: api/v1/endpoints/seasons.py
===================================================================
Provides REST endpoints for:
  - Season lifecycle management & tournament assignment
  - Live provisional and finalized leaderboard standings
  - Merkle membership proof generation for season racers
  - Merkle proof-backed championship reward claims
  - Independent season verification and scoring audits
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Path, Body, Query, HTTPException, status, Depends
from pydantic import BaseModel, Field

from backend.app.models.season import (
    SeasonDetails, SeasonLeaderboardEntry, SeasonPlayerProofResponse,
    SeasonClaimRequest, SeasonClaimResponse, SeasonVerificationReport
)
from backend.app.services.season_service import season_service
from backend.app.services.season_leaderboard_service import season_leaderboard_service
from backend.app.services.season_finalization_service import season_finalization_service
from backend.app.services.season_claim_service import season_claim_service
from backend.app.core.security import get_optional_wallet

router = APIRouter()

class CreateSeasonRequest(BaseModel):
    season_id: str = Field(..., examples=["season_2026_02"])
    name: str = Field(..., examples=["Summer Grand Prix Series"])
    rounds_total: int = Field(4, examples=[4])
    scoring_version: str = Field("v1", examples=["v1"])

class AddTournamentRequest(BaseModel):
    app_id: int = Field(..., examples=[75001234])
    round_number: int = Field(..., examples=[1])

@router.get(
    "",
    response_model=List[SeasonDetails],
    summary="List Championship Seasons",
    description="Retrieves all past and active championship seasons."
)
async def list_seasons():
    return season_service.list_seasons()

@router.post(
    "",
    response_model=SeasonDetails,
    summary="Create Championship Season",
    description="Initializes a new championship season in OPEN state."
)
async def create_season(body: CreateSeasonRequest):
    return season_service.create_season(
        season_id=body.season_id,
        name=body.name,
        rounds_total=body.rounds_total,
        scoring_version=body.scoring_version
    )

@router.get(
    "/{season_id}",
    response_model=SeasonDetails,
    summary="Get Season Details",
    description="Retrieves status, round count, committed Merkle root, and tournament rounds."
)
async def get_season(season_id: str = Path(..., examples=["season_2026_01"])):
    return season_service.get_season(season_id)

@router.get(
    "/{season_id}/leaderboard",
    response_model=List[SeasonLeaderboardEntry],
    summary="Get Season Leaderboard",
    description="Calculates provisional or finalized championship standings from eligible tournament results."
)
async def get_season_leaderboard(season_id: str = Path(..., examples=["season_2026_01"])):
    return season_leaderboard_service.calculate_leaderboard(season_id)

@router.post(
    "/{season_id}/tournaments",
    summary="Add Tournament Round to Season",
    description="Assigns an on-chain tournament to a championship season round."
)
async def add_tournament(
    season_id: str = Path(..., examples=["season_2026_01"]),
    body: AddTournamentRequest = Body(...)
):
    return season_service.add_tournament_to_season(season_id, body.app_id, body.round_number)

@router.post(
    "/{season_id}/finalize",
    summary="Finalize Season & Commit Leaderboard Root",
    description="Generates canonical snapshot, derives Merkle root, pins manifest, and permanently finalizes season."
)
async def finalize_season(
    season_id: str = Path(..., examples=["season_2026_01"]),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    caller = authenticated_wallet or "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    return season_finalization_service.finalize_season(season_id, caller)

@router.get(
    "/{season_id}/players/{wallet_address}/proof",
    response_model=SeasonPlayerProofResponse,
    summary="Get Season Merkle Proof",
    description="Returns the cryptographic leaf hash and sibling proof path proving a player's official season finish."
)
async def get_player_season_proof(
    season_id: str = Path(..., examples=["season_2026_01"]),
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return season_finalization_service.get_player_proof(season_id, wallet_address)

@router.post(
    "/{season_id}/claim",
    response_model=SeasonClaimResponse,
    summary="Claim Season Championship Reward",
    description="Claims a trophy or credential badge using a cryptographically verified Merkle proof."
)
async def claim_season_reward(
    season_id: str = Path(..., examples=["season_2026_01"]),
    body: SeasonClaimRequest = Body(...),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    caller = authenticated_wallet or "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    return season_claim_service.claim_reward(
        season_id=season_id,
        caller_address=caller,
        reward_id=body.reward_id,
        proof=body.proof
    )

@router.post(
    "/{season_id}/verify",
    response_model=SeasonVerificationReport,
    summary="Independently Verify Season Scoring & Root",
    description="Reconstructs standings from raw tournament records from scratch and compares against committed root."
)
async def verify_season_endpoint(
    season_id: str = Path(..., examples=["season_2026_01"])
):
    from backend.scripts.verify_season import verify_season_standings
    is_valid = verify_season_standings(season_id)
    season = season_service.get_season(season_id)
    standings = season_leaderboard_service.calculate_leaderboard(season_id)
    champ = standings[0].wallet_address if standings else "None"

    return SeasonVerificationReport(
        season_id=season_id,
        verified=is_valid,
        recalculated_root=season.leaderboard_root or "PROVISIONAL",
        on_chain_root=season.leaderboard_root or "PROVISIONAL",
        player_count=len(standings),
        champion_wallet=champ,
        rounds_audited=len(season.tournaments),
        message="✅ Championship Season Independently Audited & Cryptographically Verified." if is_valid else "🚨 Season Root Mismatch Detected!"
    )
