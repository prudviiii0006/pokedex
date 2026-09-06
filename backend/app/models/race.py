"""
AlgoRacers — Session 10: Racing Mechanics & Leaderboard
Module: models/race.py
======================================================
Pydantic models for circuits, racing simulation, grid participants,
leaderboard records, and user collection responses.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class Circuit(BaseModel):
    id: str = Field(..., examples=["nova_circuit"])
    name: str = Field(..., examples=["Nova Circuit"])
    track_type: str = Field(..., examples=["high_speed"])
    weather: str = Field(..., examples=["dry"])
    overtaking_difficulty: str = Field(..., examples=["medium"])
    description: str = Field(..., examples=["High-velocity power circuit with long drafting straights."])
    stat_weights: Dict[str, float] = Field(
        ...,
        examples=[{"Speed": 0.35, "Racecraft": 0.20, "Overtaking": 0.15, "Consistency": 0.15, "Qualifying": 0.10, "Wet Weather": 0.05}]
    )

class RaceSimulateRequest(BaseModel):
    wallet_address: str = Field(
        ...,
        examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"],
        description="Public 58-character Algorand wallet address of the driver owner"
    )
    asset_id: int = Field(
        ...,
        examples=[700051456],
        description="On-chain Algorand ASA ID of the driver NFT instance to enter into the race"
    )
    circuit_id: str = Field(
        ...,
        examples=["nova_circuit"],
        description="Identifier of the target racing circuit"
    )
    idempotency_key: Optional[str] = Field(
        None,
        examples=["race_idem_12345"],
        description="Client UUID preventing duplicate simulation runs on network retries"
    )

class GridParticipant(BaseModel):
    position: int = Field(..., examples=[1])
    driver_name: str = Field(..., examples=["Velocity One"])
    team: str = Field(..., examples=["Apex Pulse Racing"])
    rarity: str = Field(..., examples=["Epic"])
    is_player: bool = Field(..., examples=[True])
    base_score: float = Field(..., examples=[91.4])
    variance: float = Field(..., examples=[1.3])
    final_score: float = Field(..., examples=[92.7])
    points: int = Field(..., examples=[25])

class RaceResponse(BaseModel):
    race_id: str = Field(..., examples=["race_a1b2c3d4"])
    idempotency_key: Optional[str] = Field(None, examples=["race_idem_12345"])
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    asset_id: int = Field(..., examples=[700051456])
    driver_id: str = Field(..., examples=["001"])
    driver_name: str = Field(..., examples=["Velocity One"])
    circuit_id: str = Field(..., examples=["nova_circuit"])
    circuit_name: str = Field(..., examples=["Nova Circuit"])
    base_score: float = Field(..., examples=[91.4])
    variance: float = Field(..., examples=[1.3])
    final_score: float = Field(..., examples=[92.7])
    position: int = Field(..., examples=[1])
    points: int = Field(..., examples=[25])
    result_category: str = Field(..., examples=["Winner (P1)"])
    analysis: str = Field(
        ...,
        examples=["Velocity One dominated due to exceptional 94 Speed on this high-speed circuit."]
    )
    grid: List[GridParticipant] = Field(...)
    created_at: str

class LeaderboardEntry(BaseModel):
    rank: int = Field(..., examples=[1])
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    display_wallet: str = Field(..., examples=["3VZQZ4...N2PM"])
    total_races: int = Field(..., examples=[12])
    wins: int = Field(..., examples=[5])
    podiums: int = Field(..., examples=[9])
    total_points: int = Field(..., examples=[184])

class OwnedDriverItem(BaseModel):
    asset_id: int = Field(..., examples=[700051456])
    purchase_id: str = Field(..., examples=["pur_e673eaf4d206"])
    driver_id: str = Field(..., examples=["001"])
    name: str = Field(..., examples=["Velocity One"])
    team: str = Field(..., examples=["Apex Pulse Racing"])
    rarity: str = Field(..., examples=["Epic"])
    description: str = Field(..., examples=["Engineered for high-speed circuits."])
    image: str = Field(..., examples=["ipfs://bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t/driver_001.png"])
    stats: Dict[str, int] = Field(
        ...,
        examples=[{"Speed": 94, "Racecraft": 91, "Qualifying": 90, "Overtaking": 88, "Wet Weather": 82, "Consistency": 87}]
    )

class UserCollectionResponse(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    total_owned: int = Field(..., examples=[2])
    drivers: List[OwnedDriverItem] = Field(...)
