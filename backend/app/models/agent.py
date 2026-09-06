"""
AlgoRacers — Session 11: AI Racing Agent + x402 Paid Analytics
Module: models/agent.py
=============================================================
Pydantic models for AI Agent recommendations, baseline calculations,
premium circuit analytics, and audit logging.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class AgentRecommendRequest(BaseModel):
    wallet_address: str = Field(
        ...,
        examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"],
        description="Public 58-character Algorand wallet address owning driver NFTs"
    )
    circuit_id: str = Field(
        ...,
        examples=["nova_circuit"],
        description="Target circuit identifier ('nova_circuit', 'apex_ring', 'storm_harbor')"
    )
    allow_premium_analytics: bool = Field(
        False,
        description="Explicit user consent to purchase premium x402 analytics if the AI agent determines confidence is marginal"
    )
    max_approved_budget_usdc: float = Field(
        0.01,
        description="Maximum authorized spending limit in TestNet USDC for premium telemetry"
    )

class PremiumCircuitAnalytics(BaseModel):
    circuit_id: str = Field(..., examples=["nova_circuit"])
    circuit_name: str = Field(..., examples=["Nova Circuit"])
    track_type: str = Field(..., examples=["high_speed"])
    weather: str = Field(..., examples=["dry"])
    projected_tire_wear_pct: float = Field(..., examples=[68.5], description="Expected tire wear percentage over 20 laps")
    overtaking_opportunity_index: float = Field(..., examples=[8.2], description="Calculated passing delta score (0-10)")
    volatility_score: float = Field(..., examples=[4.1], description="Weather and safety car uncertainty factor")
    recommended_driver_archetype: str = Field(..., examples=["High-Velocity Power Specialist (Speed >= 90)"])
    strategic_tactical_note: str = Field(
        ..., 
        examples=["Turn 4 parabolic exit demands top-end speed. High tire degradation in sector 2 favors high Consistency drivers."]
    )
    paid_at: str

class BaselineRecommendResponse(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    circuit_id: str = Field(..., examples=["nova_circuit"])
    recommended_asset_id: int = Field(..., examples=[700051456])
    driver_name: str = Field(..., examples=["Velocity One"])
    driver_rarity: str = Field(..., examples=["Rare"])
    suitability_score: float = Field(..., examples=[87.4])
    method: str = Field("baseline_rule_engine")
    all_evaluated_drivers: List[Dict[str, Any]] = Field(...)

class AgentRecommendResponse(BaseModel):
    recommendation_id: str = Field(..., examples=["rec_a1b2c3d4e5f6"])
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    circuit_id: str = Field(..., examples=["nova_circuit"])
    circuit_name: str = Field(..., examples=["Nova Circuit"])
    recommended_asset_id: int = Field(..., examples=[700051456])
    driver_name: str = Field(..., examples=["Velocity One"])
    driver_rarity: str = Field(..., examples=["Rare"])
    suitability_score: float = Field(..., examples=[87.4])
    confidence: float = Field(..., examples=[0.88], description="Agent confidence index between 0.0 and 1.0")
    reasoning_summary: str = Field(
        ...,
        examples=["Velocity One is selected due to a 91 Speed rating aligning with Nova Circuit's 35% speed demand. Second-best driver trails by 4.2 points."]
    )
    factors: List[str] = Field(..., examples=[["Speed 91 (+3.2% over avg)", "Low Wet Weather impact on Dry track", "Optimal Tire Preservation"]])
    premium_used: bool = Field(False)
    cost_usdc: float = Field(0.0)
    audit_status: str = Field("VERIFIED_OWNED_ON_BLOCKCHAIN")
    created_at: str
