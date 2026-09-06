"""
AlgoRacers — Session 21: Blockchain Event & Synchronization Models
Module: chain/models.py
==================================================================
Pydantic data models for typed blockchain events, sync health,
checkpoints, and reconciliation audit reports.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class ChainEventType(str, Enum):
    NFT_MINTED = "NFT_MINTED"
    NFT_TRANSFERRED = "NFT_TRANSFERRED"
    TOURNAMENT_CREATED = "TOURNAMENT_CREATED"
    TOURNAMENT_FINALIZED = "TOURNAMENT_FINALIZED"
    SEASON_FINALIZED = "SEASON_FINALIZED"
    REWARD_CLAIMED = "REWARD_CLAIMED"
    GOVERNANCE_ACTION_EXECUTED = "GOVERNANCE_ACTION_EXECUTED"

class ChainEvent(BaseModel):
    event_id: str = Field(..., examples=["chain_evt_testnet_TX123_NFT_TRANSFERRED"])
    network: str = Field("TestNet", examples=["TestNet", "LocalNet"])
    tx_id: str = Field(..., examples=["TX1234567890"])
    round_number: int = Field(..., examples=[45123456])
    event_type: ChainEventType
    app_id: Optional[int] = None
    asset_id: Optional[int] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field("PROCESSED", examples=["PROCESSED", "FAILED", "PENDING"])
    created_at: str
    processed_at: str

class ChainSyncStatus(BaseModel):
    network: str = Field("TestNet")
    algod_round: int
    indexer_round: int
    checkpoint_round: int
    indexer_lag_rounds: int
    subscriber_lag_rounds: int
    events_processed_total: int
    events_failed_total: int
    is_healthy: bool
    subscriber_name: str = Field("algoracers_primary_subscriber")

class ReconciliationReport(BaseModel):
    audited_at: str
    nft_drift_count: int
    season_drift_count: int
    tournament_drift_count: int
    status: str = Field("MATCH", examples=["MATCH", "DRIFT_DETECTED"])
    repaired: bool = False
    details: List[str] = Field(default_factory=list)

class ActivityFeedItem(BaseModel):
    event_id: str
    event_type: str
    source: str = Field("ON-CHAIN")
    title: str
    description: str
    tx_id: str
    round_number: int
    timestamp: str
    asset_id: Optional[int] = None
    app_id: Optional[int] = None
    wallet_address: Optional[str] = None
