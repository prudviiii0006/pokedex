"""
AlgoRacers — Session 14: On-Chain Tournament Models
Module: models/tournament.py
===================================================
Pydantic schemas for tournament state, registration preparation,
canonical result hashing, and on-chain verification.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class TournamentStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINALIZED = "FINALIZED"

class TournamentParticipant(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    asset_id: int = Field(..., examples=[700051010])
    registered_at: str = Field(..., examples=["2026-08-30T15:45:00Z"])

class TournamentCreateRequest(BaseModel):
    name: str = Field(..., examples=["Nova Grand Prix Cup"])
    circuit_id: str = Field("nova_circuit", examples=["nova_circuit"])
    max_players: int = Field(8, ge=2, le=16, examples=[8])

class TournamentResponse(BaseModel):
    app_id: int = Field(..., examples=[75001234])
    name: str = Field(..., examples=["Nova Grand Prix Cup"])
    creator: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    circuit_id: str = Field(..., examples=["nova_circuit"])
    max_players: int = Field(..., examples=[8])
    participant_count: int = Field(..., examples=[4])
    status: TournamentStatus = Field(..., examples=[TournamentStatus.OPEN])
    randomness_round: Optional[int] = Field(None, examples=[45000008])
    randomness_value: Optional[str] = Field(None, examples=["7a1b2c..."])
    race_engine_version: str = Field("v1", examples=["v1"])
    winner_asset_id: Optional[int] = Field(None, examples=[700051010])
    result_hash: Optional[str] = Field(None, examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"])
    participants: List[TournamentParticipant] = Field(default_factory=list)
    created_at: str

class TournamentPrepareRegisterRequest(BaseModel):
    asset_id: int = Field(..., examples=[700051010], description="ASA ID of the driver NFT owned by caller")

class TournamentPrepareRegisterResponse(BaseModel):
    app_id: int = Field(..., examples=[75001234])
    unsigned_txn_b64: str = Field(..., description="Base64 encoded unsigned application-call transaction for Pera Wallet")
    message: str

class TournamentFinalizeRequest(BaseModel):
    winner_asset_id: int = Field(..., examples=[700051010])
    result_hash: str = Field(..., examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"])

class TournamentVerifyResultResponse(BaseModel):
    app_id: int = Field(..., examples=[75001234])
    on_chain_hash: str
    computed_hash: str
    is_valid: bool
    tampered: bool
    off_chain_result: Optional[Dict[str, Any]] = None

class TournamentVerificationReport(BaseModel):
    app_id: int
    verified: bool
    randomness_verified: bool
    result_reproducible: bool
    result_hash_matches: bool
    randomness_round: Optional[int] = None
    randomness_value: Optional[str] = None
    race_engine_version: str = "v1"
    recalculated_hash: str
    on_chain_hash: str
    winner_asset_id: Optional[int] = None
    winner_driver_name: Optional[str] = None
    message: str
