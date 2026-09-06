"""
AlgoRacers — Core Product Redesign: Fusion System
Module: models/fusion.py
=================================================
Data models for the 5-Epic -> 1-Premium card fusion pipeline.
Enforces server-authoritative validation, state tracking, and recovery.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FusionStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AWAITING_SIGNATURE = "AWAITING_SIGNATURE"
    CONSUMING = "CONSUMING"
    MINTING = "MINTING"
    DELIVERING = "DELIVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MINT_PENDING = "MINT_PENDING"

class FusionInitiateRequest(BaseModel):
    wallet_address: str = Field(..., description="58-character Algorand wallet address of card owner")
    selected_asset_ids: List[int] = Field(..., description="Exactly 5 distinct Epic ASA asset IDs to consume")
    idempotency_key: Optional[str] = Field(None, description="Client-provided idempotency key")
    signed_burn_tx_ids: Optional[List[str]] = Field(None, description="Optional transaction IDs if user broadcast burn txns directly")

class FusionInputCard(BaseModel):
    asset_id: int
    driver_id: str
    driver_name: str
    rarity: str
    consumed_at: str

class FusionResponse(BaseModel):
    fusion_id: str
    idempotency_key: Optional[str] = None
    wallet_address: str
    status: FusionStatus
    input_asset_ids: List[int]
    input_cards: Optional[List[FusionInputCard]] = None
    output_asset_id: Optional[int] = None
    premium_driver_id: Optional[str] = None
    premium_driver_name: Optional[str] = None
    premium_driver_team: Optional[str] = None
    premium_driver_stats: Optional[Dict[str, int]] = None
    metadata_uri: Optional[str] = None
    burn_tx_ids: Optional[List[str]] = None
    delivery_tx_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
