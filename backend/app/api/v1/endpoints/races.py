"""
AlgoRacers — Session 10: Racing Mechanics & Leaderboard
Module: api/v1/endpoints/races.py
===================================================
Endpoints for racing simulation, result tracking, leaderboard, and collections.
"""

from typing import List, Optional
from fastapi import APIRouter, Body, Path, Query, HTTPException, status, Depends
from backend.app.models.race import (
    RaceSimulateRequest, 
    RaceResponse, 
    LeaderboardEntry, 
    UserCollectionResponse
)
from backend.app.services.race_engine import race_engine
from backend.app.services.circuit_service import circuit_service
from backend.app.core.security import get_optional_wallet

router = APIRouter()

@router.post(
    "/races",
    response_model=RaceResponse,
    summary="Enter Driver in Multi-Car Grand Prix Race",
    description="Verifies driver NFT ownership server-side, runs 8-car race simulation with CPU opponents, calculates points, and updates leaderboard."
)
async def enter_race(
    body: RaceSimulateRequest = Body(...),
    seed: Optional[int] = Query(None, description="Optional seed for deterministic testing"),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    # Enforce session identity: Authenticated session overrides body.wallet_address (Prevents impersonation)
    target_wallet = authenticated_wallet if authenticated_wallet else body.wallet_address

    # 1. Verify Circuit
    circuit = circuit_service.get_circuit(body.circuit_id)
    # 2. Verify NFT Ownership (Never trust client stats!)
    driver = race_engine.verify_driver_ownership(target_wallet, body.asset_id)
    # 3. Execute Simulation
    return race_engine.simulate_multi_car_race(
        player_driver=driver,
        circuit=circuit,
        player_wallet=target_wallet,
        player_asset_id=body.asset_id,
        idempotency_key=body.idempotency_key,
        seed=seed
    )

@router.post(
    "/races/simulate",
    response_model=RaceResponse,
    summary="Simulate Race (Quick Run)",
    description="Identical simulation entry point for single-driver / multi-driver simulations."
)
async def simulate_race(
    body: RaceSimulateRequest = Body(...),
    seed: Optional[int] = Query(None, description="Optional seed for deterministic testing")
):
    circuit = circuit_service.get_circuit(body.circuit_id)
    driver = race_engine.verify_driver_ownership(body.wallet_address, body.asset_id)
    return race_engine.simulate_multi_car_race(
        player_driver=driver,
        circuit=circuit,
        player_wallet=body.wallet_address,
        player_asset_id=body.asset_id,
        idempotency_key=body.idempotency_key,
        seed=seed
    )

@router.get(
    "/races/{race_id}",
    response_model=RaceResponse,
    summary="Get Race Result by ID",
    description="Retrieves a full past race result, grid standings, and telemetry analysis."
)
async def get_race(
    race_id: str = Path(..., examples=["race_a1b2c3d4"], description="Race identifier")
):
    return race_engine.get_race(race_id)

@router.get(
    "/leaderboard",
    response_model=List[LeaderboardEntry],
    summary="Get Global Racing Leaderboard",
    description="Retrieves aggregated racing leaderboard with total points, wins, and podiums."
)
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100, description="Max entries to return")
):
    return race_engine.get_leaderboard(limit=limit)

@router.get(
    "/wallets/{wallet_address}/races",
    response_model=List[RaceResponse],
    summary="Get Wallet Racing History",
    description="Retrieves chronological race history for a specific driver wallet address."
)
async def get_wallet_races(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return race_engine.get_wallet_races(wallet_address)

@router.get(
    "/wallets/{wallet_address}/collection",
    response_model=UserCollectionResponse,
    summary="Get Owned Driver NFT Collectibles",
    description="Retrieves all verified AlgoRacers driver NFT instances owned by a wallet with their attributes and stats."
)
async def get_wallet_collection(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return race_engine.get_wallet_collection(wallet_address)
