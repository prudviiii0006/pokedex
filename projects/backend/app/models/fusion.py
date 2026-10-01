"""
Pokédex (AlgoCreatures) — Fusion Data Models
Module: models/fusion.py
============================================
Pydantic schemas for the 5-Epic-to-1-Legendary Fusion engine.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FusionInitiateRequest(BaseModel):
    wallet_address: str = Field(..., description="Connected Algorand wallet initiating the fusion")
    input_asset_ids: List[int] = Field(..., min_length=5, max_length=5, description="List of exactly 5 Epic Pokémon asset IDs to sacrifice")

class FusionInputItem(BaseModel):
    asset_id: int
    pokemon_id: Optional[int] = None
    name: str
    rarity: str
    image: Optional[str] = None
    status: str = "PENDING"

class FusionConfirmRequest(BaseModel):
    wallet_address: str = Field(..., description="Connected Algorand wallet")
    transfer_tx_id: str = Field(..., description="Transaction ID of the 5-asset transfer to the minter/burn address")

class FusionReward(BaseModel):
    pokemon_id: int
    name: str
    primary_type: str
    secondary_type: Optional[str] = None
    rarity: str = "Legendary"
    image: str
    stats: Optional[Dict[str, int]] = None
    asset_id: int
    metadata_uri: Optional[str] = None
    delivery_tx_id: Optional[str] = None

class FusionResponse(BaseModel):
    fusion_id: str
    wallet_address: str
    status: str
    input_asset_ids: List[int]
    inputs: List[FusionInputItem] = []
    reward: Optional[FusionReward] = None
    transfer_tx_id: Optional[str] = None
    delivery_tx_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
