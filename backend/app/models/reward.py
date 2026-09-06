"""
AlgoRacers — Session 6: FastAPI Backend
Module: models/reward.py
=======================================
Pydantic schemas for driver rewards and pack simulations.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field

class DriverSummary(BaseModel):
    id: str = Field(..., examples=["001"])
    name: str = Field(..., examples=["Velocity One"])
    team: str = Field(..., examples=["Apex Pulse Racing"])
    rarity: str = Field(..., examples=["Rare"])
    description: str = Field(..., examples=["Engineered for high-speed circuits."])
    image: str = Field(..., examples=["ipfs://bafybei.../driver_001.png"])
    stats: Dict[str, int] = Field(..., examples=[{"Speed": 91, "Qualifying": 88, "Racecraft": 87}])

class SimulatePackRequest(BaseModel):
    wallet_address: Optional[str] = Field(
        None, 
        examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"],
        description="Optional connected user address for simulation telemetry context"
    )

class RewardResponse(BaseModel):
    reward_id: str = Field(..., examples=["rew_a1b2c3d4e5f6"])
    pack_id: str = Field(..., examples=["basic"])
    pack_name: str = Field(..., examples=["Basic Pack"])
    rarity: str = Field(..., examples=["Rare"])
    driver: DriverSummary
    generated_at: str = Field(..., examples=["2026-08-30T07:30:00Z"])
    is_simulation: bool = Field(True, description="Indicates this reward is an off-chain simulation without on-chain payment")
