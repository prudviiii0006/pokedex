"""
Pokédex — Creature Collectible & Battle System
Module: rewards/models.py
========================================================================
Defines clean canonical data structures for Packs, Creature Templates,
Battle Attributes, and Reward Results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import uuid

@dataclass
class CreatureTemplate:
    id: str
    index_number: int
    name: str
    primary_type: str
    secondary_type: Optional[str] = None
    faction: str = ""
    rarity: str = "Common"
    evolution_family: str = ""
    evolution_stage: int = 1
    next_evolution_id: Optional[str] = None
    base_hp: int = 70
    base_attack: int = 70
    base_defense: int = 70
    base_speed: int = 70
    base_stamina: int = 70
    description: str = ""
    image: str = ""
    stats: Dict[str, int] = field(default_factory=dict)
    raw_metadata_path: Optional[str] = None

    def __post_init__(self):
        if not self.stats:
            self.stats = {
                "HP": self.base_hp,
                "Attack": self.base_attack,
                "Defense": self.base_defense,
                "Speed": self.base_speed,
                "Stamina": self.base_stamina
            }
        if not self.faction and self.primary_type:
            faction_map = {
                "Fire": "Ignis",
                "Water": "Hydra",
                "Grass": "Sylvan",
                "Electric": "Volt",
                "Earth": "Geo",
                "Ice": "Glacier",
                "Dark": "Umbra",
                "Light": "Aether"
            }
            self.faction = faction_map.get(self.primary_type, self.primary_type)

    # Backward compatibility properties for legacy code
    @property
    def driver_id(self) -> str:
        return self.id

    @property
    def driver_name(self) -> str:
        return self.name

    @property
    def team(self) -> str:
        return self.faction

    @property
    def constructor_name(self) -> str:
        return self.faction

    @property
    def number(self) -> int:
        return self.index_number

# Alias for backward compatibility
DriverTemplate = CreatureTemplate

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
    creature: CreatureTemplate
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    purchase_id: Optional[str] = None

    # Backward compatibility property
    @property
    def driver(self) -> CreatureTemplate:
        return self.creature

    def to_dict(self) -> dict:
        return {
            "reward_id": self.reward_id,
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "rarity": self.rarity,
            "creature": {
                "id": self.creature.id,
                "index_number": self.creature.index_number,
                "name": self.creature.name,
                "primary_type": self.creature.primary_type,
                "secondary_type": self.creature.secondary_type,
                "faction": self.creature.faction,
                "rarity": self.creature.rarity,
                "evolution_family": self.creature.evolution_family,
                "evolution_stage": self.creature.evolution_stage,
                "next_evolution_id": self.creature.next_evolution_id,
                "description": self.creature.description,
                "image": self.creature.image,
                "stats": self.creature.stats
            },
            # Backward compatibility nested structure
            "driver": {
                "id": self.creature.id,
                "name": self.creature.name,
                "code": self.creature.id[:3].upper(),
                "number": self.creature.index_number,
                "constructor_id": self.creature.primary_type.lower(),
                "constructor_name": self.creature.faction,
                "team": self.creature.faction,
                "rarity": self.creature.rarity,
                "description": self.creature.description,
                "image": self.creature.image,
                "stats": self.creature.stats
            },
            "generated_at": self.generated_at,
            "purchase_id": self.purchase_id
        }
