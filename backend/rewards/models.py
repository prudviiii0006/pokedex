"""
AlgoRacers — Session 5: Pack & Reward System
Module: models.py
============================================
Defines clean data structures for packs, driver templates, and reward results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

@dataclass
class DriverTemplate:
    id: str
    name: str
    team: str
    rarity: str
    description: str
    image: str
    stats: Dict[str, int]
    raw_metadata_path: Optional[str] = None

@dataclass
class PackConfig:
    id: str
    name: str
    price: float
    currency: str
    reward_count: int
    description: str
    rarities: Dict[str, float]

@dataclass
class RewardResult:
    reward_id: str
    pack_id: str
    pack_name: str
    rarity: str
    driver: DriverTemplate
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    purchase_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "reward_id": self.reward_id,
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "rarity": self.rarity,
            "driver": {
                "id": self.driver.id,
                "name": self.driver.name,
                "team": self.driver.team,
                "rarity": self.driver.rarity,
                "description": self.driver.description,
                "image": self.driver.image,
                "stats": self.driver.stats
            },
            "generated_at": self.generated_at,
            "purchase_id": self.purchase_id
        }
