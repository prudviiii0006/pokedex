"""
AlgoRacers — Core Product Redesign: Trading System
Module: models/trading.py
=================================================
Data models for 1-for-1 atomic card swaps.
Guarantees database consistency, opt-in verification, and atomic swap states.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TradeStatus(str, Enum):
    OPEN = "OPEN"
    ACCEPTING = "ACCEPTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"

class CreateTradeRequest(BaseModel):
    creator_wallet: str = Field(..., description="58-character Algorand wallet address offering the card")
    offered_asset_id: int = Field(..., description="ASA ID of the owned card offered by creator")
    requested_asset_id: int = Field(..., description="ASA ID of the target card wanted by creator")
    requested_driver_name: Optional[str] = Field(None, description="Optional target driver name for display")
    notes: Optional[str] = Field(None, description="Optional trade description or note")
    expires_in_hours: Optional[int] = Field(24, description="Offer expiration window in hours")

class AcceptTradeRequest(BaseModel):
    acceptor_wallet: str = Field(..., description="58-character Algorand wallet address accepting the trade")
    signed_group_tx_id: Optional[str] = Field(None, description="Optional atomic group transaction ID if broadcast by client")

class TradeOfferResponse(BaseModel):
    trade_id: str
    creator_wallet: str
    offered_asset_id: int
    offered_driver_name: str
    offered_driver_team: str
    offered_driver_rarity: str
    requested_asset_id: int
    requested_driver_name: str
    requested_driver_team: Optional[str] = None
    requested_driver_rarity: Optional[str] = None
    status: TradeStatus
    accepted_by: Optional[str] = None
    notes: Optional[str] = None
    atomic_group_id: Optional[str] = None
    execution_tx_ids: Optional[List[str]] = None
    created_at: str
    expires_at: str
    completed_at: Optional[str] = None
    is_expired: bool = False
