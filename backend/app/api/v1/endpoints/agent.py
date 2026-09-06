"""
AlgoRacers — Session 11: AI Racing Agent + x402 Paid Analytics
Module: api/v1/endpoints/agent.py
=============================================================
REST Endpoints for AI Agent Recommendations, Baseline Scoring,
x402 Premium Analytics, and Agent-assisted Grand Prix Race Entry.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Header, Body, Path, Query, HTTPException, status, Depends
from backend.app.core.database import get_db
from backend.app.models.agent import (
    AgentRecommendRequest,
    AgentRecommendResponse,
    BaselineRecommendResponse,
    PremiumCircuitAnalytics
)
from backend.app.models.race import RaceResponse, RaceSimulateRequest
from backend.app.services.ai_agent import ai_racing_agent, BaselineRecommender
from backend.app.services.agent_tools import agent_tools
from backend.app.services.circuit_service import circuit_service
from backend.app.services.race_engine import race_engine
from backend.app.core.security import get_optional_wallet

router = APIRouter()

@router.post(
    "/agent/recommend/baseline",
    response_model=BaselineRecommendResponse,
    summary="Compute deterministic baseline driver recommendation"
)
async def get_baseline_recommendation(
    request: AgentRecommendRequest,
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    """Calculates weighted suitability scores for all owned drivers and picks the top candidate."""
    target_wallet = authenticated_wallet if authenticated_wallet else request.wallet_address
    return BaselineRecommender.evaluate_collection(
        wallet_address=target_wallet,
        circuit_id=request.circuit_id
    )

@router.post(
    "/agent/recommend",
    response_model=AgentRecommendResponse,
    summary="AI Racing Agent driver recommendation with optional x402 telemetry"
)
async def get_agent_recommendation(
    request: AgentRecommendRequest,
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    """
    Executes the full AI Agent loop:
      1. Observe (Collection & Circuit Read Tools)
      2. Reason (Compare Suitability & Assess Confidence)
      3. Decide on x402 Telemetry (if confidence < threshold & approved)
      4. Validate Output & Enforce Ownership Trust Boundary
      5. Audit Log to SQLite
    """
    if authenticated_wallet:
        request.wallet_address = authenticated_wallet
    return ai_racing_agent.recommend_driver(request)

@router.get(
    "/analytics/circuits/{circuit_id}/premium",
    response_model=PremiumCircuitAnalytics,
    summary="x402 Guarded Premium Circuit Telemetry"
)
async def get_premium_circuit_analytics(
    circuit_id: str = Path(..., examples=["nova_circuit"]),
    x_402_payment_proof: Optional[str] = Header(None, alias="X-402-Payment-Proof")
):
    """
    HTTP 402 Guarded Endpoint for Deep Track Telemetry.
    Requires 0.01 TestNet USDC payment authorization.
    """
    if not x_402_payment_proof:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "PaymentRequired",
                "message": "Access to deep circuit telemetry requires x402 micropayment.",
                "payment_requirements": {
                    "price_usdc": 0.01,
                    "amount_microusdc": 10000,
                    "asset": "USDC",
                    "asset_id": 10458941,
                    "network": "algorand-testnet",
                    "recipient": "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
                }
            }
        )

    # Return telemetry
    return agent_tools.purchase_premium_analytics(
        circuit_id=circuit_id,
        wallet_address="3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
        user_approved=True,
        approved_budget_usdc=0.01
    )

@router.get(
    "/agent/recommendations/{recommendation_id}",
    summary="Retrieve audit trail for an AI agent recommendation"
)
async def get_recommendation_audit(
    recommendation_id: str = Path(..., examples=["rec_a1b2c3d4e5f6"])
):
    """Returns stored audit record for a past AI agent decision."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM recommendations WHERE recommendation_id = ?;
        """, (recommendation_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation audit record not found.")

        data = dict(row)
        data["factors"] = json.loads(data["factors"])
        return data

@router.post(
    "/agent/race",
    response_model=RaceResponse,
    summary="AI Agent-Assisted Grand Prix Race Entry"
)
async def agent_assisted_race(
    request: AgentRecommendRequest,
    seed: Optional[int] = Query(None, description="Optional RNG seed for test determinism")
):
    """
    1. Runs AI recommendation
    2. Validates ownership and circuit
    3. Executes 8-car Grand Prix race simulation
    """
    rec = ai_racing_agent.recommend_driver(request)
    driver = race_engine.verify_driver_ownership(request.wallet_address, rec.recommended_asset_id)
    circuit = circuit_service.get_circuit(request.circuit_id)
    
    return race_engine.simulate_multi_car_race(
        player_driver=driver,
        circuit=circuit,
        player_wallet=request.wallet_address,
        player_asset_id=rec.recommended_asset_id,
        seed=seed
    )
