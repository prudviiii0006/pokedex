"""
AlgoRacers — Session 16: Player Profile & Progression Models
Module: models/profile.py
===========================================================
Pydantic schemas for player profile, XP progression, stats, and reconciliation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from backend.app.models.achievement import AchievementItem

class PlayerStats(BaseModel):
    races_completed: int = Field(0, examples=[42])
    wins: int = Field(0, examples=[7])
    podiums: int = Field(0, examples=[14])
    tournaments_entered: int = Field(0, examples=[5])
    tournaments_won: int = Field(0, examples=[2])
    drivers_owned: int = Field(0, examples=[4])
    win_rate: float = Field(0.0, examples=[0.167])
    podium_rate: float = Field(0.0, examples=[0.333])

class PlayerProfileResponse(BaseModel):
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    display_name: Optional[str] = Field(None, examples=["ApexRacer"])
    xp: int = Field(0, examples=[2450])
    level: int = Field(1, examples=[12])
    next_level_xp: int = Field(100, examples=[2880])
    level_progress_percent: float = Field(0.0, examples=[72.5])
    reputation_score: int = Field(1000, examples=[1064])
    reputation_rank_tier: str = Field("Gold", examples=["Gold"])
    stats: PlayerStats
    achievement_count: int = Field(0, examples=[5])
    achievements: List[AchievementItem] = Field(default_factory=list)
    created_at: str
    updated_at: str

class PublicPlayerProfileResponse(BaseModel):
    wallet_address: str
    display_name: Optional[str] = None
    level: int
    reputation_score: int
    reputation_rank_tier: str
    stats: PlayerStats
    achievement_count: int
    achievements: List[AchievementItem] = Field(default_factory=list)

class ProfileReconcileResponse(BaseModel):
    wallet_address: str
    drift_detected: bool
    recalculated_xp: int
    cached_xp: int
    recalculated_level: int
    recalculated_reputation: int
    achievements_unlocked_count: int
    message: str
