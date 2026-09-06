"""
AlgoRacers — Session 16: Achievement Models
Module: models/achievement.py
============================================
Pydantic schemas for achievements, unlock records, and credential verification.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class AchievementItem(BaseModel):
    id: str = Field(..., examples=["TOURNAMENT_CHAMPION"])
    name: str = Field(..., examples=["Tournament Champion"])
    description: str = Field(..., examples=["Win a verified Algorand tournament."])
    category: str = Field("competitive", examples=["competitive"])
    trigger: str = Field("COUNT_TOURNAMENTS_WON", examples=["COUNT_TOURNAMENTS_WON"])
    threshold: int = Field(1, examples=[1])
    permanent: bool = Field(True, examples=[True])
    credential_policy: str = Field("on_chain_badge", examples=["on_chain_badge"])
    icon: str = Field("🏆", examples=["🏆"])
    unlocked: bool = Field(False)
    unlocked_at: Optional[str] = None
    progress: int = Field(0)
    credential_status: str = Field("OFF_CHAIN", examples=["OFF_CHAIN", "ELIGIBLE", "ISSUANCE_PENDING", "ISSUED"])
    credential_asset_id: Optional[int] = None
    issuance_tx_id: Optional[str] = None

class AchievementVerifyResponse(BaseModel):
    achievement_id: str
    wallet_address: str
    verified: bool
    credential_status: str
    credential_asset_id: Optional[int] = None
    issuance_tx_id: Optional[str] = None
    source_event_id: Optional[str] = None
    message: str
