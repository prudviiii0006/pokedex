"""
AlgoRacers — Session 8: Real x402 Payments on Algorand TestNet
Module: api/v1/endpoints/premium.py
==============================================================
Paid API resource guarded by Algorand TestNet x402 payment gate.
Price: 0.01 USDC (Asset ID: 10458941)
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Header
from backend.app.models.x402 import PremiumAnalysisResponse
from backend.app.services.payment_gate import payment_gate

router = APIRouter()

@router.get(
    "/premium-analysis",
    response_model=PremiumAnalysisResponse,
    summary="Premium Circuit Telemetry (Algorand x402 Protected)",
    description="Paid tactical telemetry resource for the upcoming Grand Prix. Protected by Algorand TestNet x402 protocol (0.01 USDC, Asset ID 10458941)."
)
async def get_premium_analysis(
    x_402_payment_proof: Optional[str] = Header(None, alias="X-402-Payment-Proof"),
    authorization: Optional[str] = Header(None)
):
    # 1. Verify & Settle payment on Algorand TestNet
    receipt = payment_gate.verify_and_settle_payment(
        resource_path="/premium-analysis",
        required_amount_usdc=0.01,
        x_402_payment_proof=x_402_payment_proof,
        authorization=authorization,
        settle_on_chain=False  # Auto-detected based on payload type
    )

    # 2. Return Premium Protected Payload
    return PremiumAnalysisResponse(
        title="Apex Grand Prix — Sector Telemetry & Pit Delta Intelligence",
        circuit="Neo-Monza SuperSpeedway (TestNet Circuit #01)",
        track_conditions="Asphalt Temp: 38°C | Rain Probability: 12% | Grip Factor: 94%",
        driver_telemetry=[
            {"driver": "Velocity One (#001)", "apex_speed": "288 km/h", "sector_2_gain": "-0.182s", "recommended_aero": "Low Downforce"},
            {"driver": "Apex Storm (#003)", "apex_speed": "294 km/h", "sector_2_gain": "-0.245s", "recommended_aero": "Ultra-Low Drag"},
            {"driver": "Nova Rush (#002)", "apex_speed": "282 km/h", "sector_2_gain": "-0.095s", "recommended_aero": "Balanced Trim"}
        ],
        tactical_ai_insights="Aggressive undercut on Lap 18 recommended if trailing within 1.2 seconds of the race leader.",
        unlocked_at=datetime.now(timezone.utc).isoformat(),
        payment_receipt=receipt
    )
