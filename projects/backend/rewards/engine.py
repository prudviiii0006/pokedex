"""
AlgoCreatures — Pack & Reward Engine
Module: rewards/engine.py
====================================
Orchestrates pack validation, weighted rarity rolling, creature species
selection, and deterministic reward result generation.
"""

import json
from pathlib import Path
import random
from typing import Dict, Optional
import uuid

from backend.rewards.models import PackConfig, RewardResult, CreatureTemplate
from backend.rewards.rarity import select_rarity, validate_rarity_weights
from backend.rewards.creature_pool import CreaturePool, creature_pool

class RewardEngine:
    def __init__(self, packs_config_path: Optional[Path] = None, metadata_dir: Optional[Path] = None):
        if packs_config_path is None:
            self.config_path = Path(__file__).resolve().parent.parent / "data" / "packs.json"
        else:
            self.config_path = packs_config_path

        self.creature_pool = CreaturePool()
        # Backward compatibility alias
        self.driver_pool = self.creature_pool
        self.packs: Dict[str, PackConfig] = {}
        self.load_pack_configurations()

    def load_pack_configurations(self) -> None:
        """Loads and validates all pack configurations from JSON."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Packs configuration not found at: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw_packs = json.load(f)

        self.packs.clear()
        for pack_id, cfg in raw_packs.items():
            if cfg.get("price", 0) < 0:
                raise ValueError(f"Pack '{pack_id}' cannot have a negative price.")
            if not cfg.get("currency"):
                raise ValueError(f"Pack '{pack_id}' is missing a currency definition.")
            if cfg.get("reward_count", 0) < 1:
                raise ValueError(f"Pack '{pack_id}' reward_count must be at least 1.")

            rarities = cfg.get("rarities", {})
            validate_rarity_weights(rarities)

            active_rarities = [r for r, w in rarities.items() if w > 0]
            self.creature_pool.validate_coverage(active_rarities)

            pack_obj = PackConfig(
                id=pack_id,
                name=cfg.get("name", pack_id.title()),
                price=float(cfg.get("price", 0)),
                currency=cfg.get("currency", "USDC"),
                reward_count=int(cfg.get("reward_count", 1)),
                description=cfg.get("description", ""),
                rarities=rarities
            )
            # Store extra metadata like type_pool on pack_obj if present
            setattr(pack_obj, "type_pool", cfg.get("type_pool"))
            self.packs[pack_id] = pack_obj

    def open_pack(
        self, 
        pack_id: str, 
        rng: Optional[random.Random] = None, 
        purchase_id: Optional[str] = None
    ) -> RewardResult:
        """
        Executes a single pack opening:
          1. Selects rarity via weighted sampling
          2. Selects a creature from the corresponding pool (filtered by type_pool if configured)
          3. Emits an immutable RewardResult with unique reward_id
        """
        if pack_id not in self.packs:
            raise KeyError(f"Unknown pack type '{pack_id}'. Available packs: {list(self.packs.keys())}")

        pack = self.packs[pack_id]

        # 1. Rarity Selection
        selected_rarity = select_rarity(pack, rng=rng)

        # 2. Creature Selection from Rarity Pool (optionally filtered by type_pool)
        type_pool = getattr(pack, "type_pool", None)
        generator = rng if rng is not None else random
        candidate_pool = self.creature_pool.get_by_rarity(selected_rarity)
        
        if type_pool and isinstance(type_pool, list):
            norm_types = [t.lower().strip() for t in type_pool]
            filtered = [
                c for c in candidate_pool 
                if c.primary_type.lower() in norm_types or (c.secondary_type and c.secondary_type.lower() in norm_types) or c.faction.lower() in norm_types
            ]
            if filtered:
                selected_creature = generator.choice(filtered)
            else:
                # Fallback to any species matching the type across all rarities
                all_matching = [
                    c for c in self.creature_pool.get_all_creatures()
                    if c.primary_type.lower() in norm_types or (c.secondary_type and c.secondary_type.lower() in norm_types) or c.faction.lower() in norm_types
                ]
                selected_creature = generator.choice(all_matching) if all_matching else self.creature_pool.select_creature(selected_rarity, rng=rng)
        else:
            selected_creature = self.creature_pool.select_creature(selected_rarity, rng=rng)

        # 3. Create Unique Reward Instance
        reward_id = f"rew_{uuid.uuid4().hex[:12]}"

        return RewardResult(
            reward_id=reward_id,
            pack_id=pack.id,
            pack_name=pack.name,
            rarity=selected_rarity,
            creature=selected_creature,
            purchase_id=purchase_id
        )

    def trace_pack_opening(self, pack_id: str, rng: Optional[random.Random] = None) -> RewardResult:
        """Runs a step-by-step trace of a single pack opening."""
        if pack_id not in self.packs:
            raise KeyError(f"Unknown pack '{pack_id}'")

        pack = self.packs[pack_id]
        selected_rarity = select_rarity(pack, rng=rng)
        selected_creature = self.creature_pool.select_creature(selected_rarity, rng=rng)

        return RewardResult(
            reward_id=f"rew_{uuid.uuid4().hex[:12]}",
            pack_id=pack.id,
            pack_name=pack.name,
            rarity=selected_rarity,
            creature=selected_creature
        )
