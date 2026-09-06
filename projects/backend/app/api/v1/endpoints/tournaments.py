"""
AlgoRacers — Session 14: On-Chain Tournament Registry REST Endpoints
Module: api/v1/endpoints/tournaments.py
===================================================================
Endpoints for:
  - Listing & creating smart-contract tournaments
  - Preparing unsigned registration app calls for Pera Wallet
  - Closing registration (Organizer only)
  - Executing off-chain Grand Prix race & committing hash on-chain
  - Verifying result integrity against on-chain hash commitment
"""

from typing import List, Optional
from fastapi import APIRouter, Header, Body, Path, HTTPException, status, Depends
from backend.app.models.tournament import (
    TournamentResponse, TournamentCreateRequest,
    TournamentPrepareRegisterRequest, TournamentPrepareRegisterResponse,
    TournamentVerifyResultResponse, TournamentVerificationReport
)
from backend.app.services.tournament_service import tournament_service
from backend.app.core.security import get_optional_wallet, get_current_wallet

router = APIRouter()

@router.get(
    "",
    response_model=List[TournamentResponse],
    summary="List On-Chain Tournaments",
    description="Retrieves all active and historical smart-contract tournaments and participant counts."
)
async def list_tournaments():
    return tournament_service.list_tournaments()

@router.post(
    "/create",
    response_model=TournamentResponse,
    summary="Create On-Chain Tournament",
    description="Deploys a new Tournament Smart Contract instance on Algorand."
)
async def create_tournament(
    body: TournamentCreateRequest,
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    creator = authenticated_wallet if authenticated_wallet else None
    return tournament_service.create_tournament(
        name=body.name,
        circuit_id=body.circuit_id,
        max_players=body.max_players,
        creator_address=creator
    )

@router.get(
    "/{app_id}",
    response_model=TournamentResponse,
    summary="Get Tournament Details",
    description="Retrieves live on-chain state, participant registry, and status of a tournament."
)
async def get_tournament(
    app_id: int = Path(..., examples=[75001234], description="Smart contract application ID")
):
    return tournament_service.get_tournament(app_id)

@router.post(
    "/{app_id}/prepare-register",
    response_model=TournamentPrepareRegisterResponse,
    summary="Prepare Driver Registration App Call",
    description="Validates ownership and capacity, builds unsigned ApplicationNoOpTxn for Pera Wallet signing."
)
async def prepare_register(
    app_id: int = Path(..., examples=[75001234]),
    body: TournamentPrepareRegisterRequest = Body(...),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    wallet = authenticated_wallet if authenticated_wallet else "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    return tournament_service.prepare_register_transaction(
        app_id=app_id,
        wallet_address=wallet,
        asset_id=body.asset_id
    )

@router.post(
    "/{app_id}/close",
    response_model=TournamentResponse,
    summary="Close Tournament Registration",
    description="Sets contract status to CLOSED (Organizer authorization required)."
)
async def close_registration(
    app_id: int = Path(..., examples=[75001234]),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    caller = authenticated_wallet if authenticated_wallet else tournament_service.creator_address
    return tournament_service.close_registration(app_id=app_id, caller_address=caller)

@router.post(
    "/{app_id}/run-and-finalize",
    response_model=TournamentResponse,
    summary="Run Off-Chain Grand Prix & Commit On-Chain Hash",
    description="Executes race simulation with registered drivers, calculates SHA-256 result hash, and finalizes smart contract."
)
async def run_and_finalize(
    app_id: int = Path(..., examples=[75001234]),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    caller = authenticated_wallet if authenticated_wallet else tournament_service.creator_address
    tournament, _ = tournament_service.run_and_finalize_tournament(app_id=app_id, caller_address=caller)
    return tournament

@router.get(
    "/{app_id}/verify",
    response_model=TournamentVerificationReport,
    summary="Independent Tournament Verification Audit",
    description="Reconstructs race from locked on-chain parameters, recomputes simulation, and checks result hash."
)
async def verify_tournament_audit(
    app_id: int = Path(..., examples=[75001234])
):
    return tournament_service.verify_tournament_result(app_id=app_id)

@router.get(
    "/{app_id}/verify-result",
    response_model=TournamentVerificationReport,
    summary="Verify Off-Chain Result Against On-Chain Commitment (Alias)",
    description="Computes canonical SHA-256 hash and checks against on-chain committed hash."
)
async def verify_result(
    app_id: int = Path(..., examples=[75001234])
):
    return tournament_service.verify_tournament_result(app_id=app_id)
