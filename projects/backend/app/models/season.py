"""
AlgoRacers — Session 19: Season & Championship Models
Module: models/season.py
======================================================
Pydantic models for season configuration, leaderboard standings,
Merkle proofs, reward claims, and independent audit reports.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SeasonLeaderboardEntry(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    display_wallet: str = Field(..., examples=["3VZQ...N2PM"])
    driver_id: Optional[str] = Field(None, examples=["001"])
    driver_name: Optional[str] = Field(None, examples=["Velocity One"])
    rank: int = Field(..., examples=[1])
    points: int = Field(..., examples=[75])
    wins: int = Field(0, examples=[2])
    podiums: int = Field(0, examples=[3])
    tournaments_entered: int = Field(0, examples=[3])

class SeasonDetails(BaseModel):
    season_id: str = Field(..., examples=["season_2026_01"])
    name: str = Field(..., examples=["Neon Championship 2026"])
    version: int = Field(1, examples=[1])
    status: str = Field("ACTIVE", examples=["DRAFT", "OPEN", "ACTIVE", "CLOSING", "FINALIZED"])
    scoring_version: str = Field("v1", examples=["v1"])
    rounds_total: int = Field(4, examples=[4])
    rounds_completed: int = Field(0, examples=[3])
    player_count: int = Field(0, examples=[8])
    leaderboard_root: Optional[str] = Field(None, examples=["8319631f..."])
    manifest_cid: Optional[str] = None
    app_id: Optional[int] = Field(None, examples=[88002001])
    champion_wallet: Optional[str] = None
    created_at: str
    finalized_at: Optional[str] = None
    tournaments: List[Dict[str, Any]] = Field(default_factory=list)

class SeasonPlayerProofResponse(BaseModel):
    season_id: str
    wallet_address: str
    record: Dict[str, Any]
    leaf_hash: str
    proof: List[Dict[str, str]]
    root: str
    manifest_cid: Optional[str] = None
    status: str
    is_finalized: bool

class SeasonClaimRequest(BaseModel):
    season_id: str
    reward_id: str = Field("SEASON_CHAMPION_TROPHY", examples=["SEASON_CHAMPION_TROPHY", "SEASON_PODIUM_BADGE"])
    proof: List[Dict[str, str]]
    signed_tx: Optional[str] = None

class SeasonClaimResponse(BaseModel):
    claim_id: str
    season_id: str
    wallet_address: str
    reward_id: str
    status: str
    credential_asset_id: Optional[int] = None
    claim_tx_id: Optional[str] = None
    message: str

class SeasonVerificationReport(BaseModel):
    season_id: str
    verified: bool
    recalculated_root: str
    on_chain_root: str
    player_count: int
    champion_wallet: str
    rounds_audited: int
    message: str
