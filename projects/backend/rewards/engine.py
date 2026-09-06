"""
AlgoRacers — Session 5: Pack & Reward System
Module: engine.py
============================================
The core Reward Engine orchestrating pack validation, rarity rolling,
driver selection, and deterministic reward result generation.
"""

import json
from pathlib import Path
import random
from typing import Dict, Optional
import uuid

from backend.rewards.models import PackConfig, RewardResult, DriverTemplate
from backend.rewards.rarity import select_rarity, validate_rarity_weights
from backend.rewards.driver_pool import DriverPool

class RewardEngine:
    def __init__(self, packs_config_path: Optional[Path] = None, metadata_dir: Optional[Path] = None):
        if packs_config_path is None:
            self.config_path = Path(__file__).resolve().parent.parent / "data" / "packs.json"
        else:
            self.config_path = packs_config_path

        self.driver_pool = DriverPool(metadata_dir=metadata_dir)
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
            # Validate pack structure
            if cfg.get("price", 0) < 0:
                raise ValueError(f"Pack '{pack_id}' cannot have a negative price.")
            if not cfg.get("currency"):
                raise ValueError(f"Pack '{pack_id}' is missing a currency definition.")
            if cfg.get("reward_count", 0) != 1:
                raise ValueError(f"Pack '{pack_id}' reward_count must be 1 for current engine.")

            rarities = cfg.get("rarities", {})
            validate_rarity_weights(rarities)

            # Ensure driver pool has drivers for every rarity with weight > 0
            active_rarities = [r for r, w in rarities.items() if w > 0]
            self.driver_pool.validate_coverage(active_rarities)

            pack_obj = PackConfig(
                id=pack_id,
                name=cfg.get("name", pack_id.title()),
                price=float(cfg.get("price", 0)),
                currency=cfg.get("currency", "USDC"),
                reward_count=int(cfg.get("reward_count", 1)),
                description=cfg.get("description", ""),
                rarities=rarities
            )
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
          2. Selects a driver from the corresponding pool
          3. Emits an immutable RewardResult with unique reward_id
        """
        if pack_id not in self.packs:
            raise KeyError(f"Unknown pack type '{pack_id}'. Available packs: {list(self.packs.keys())}")

        pack = self.packs[pack_id]

        # 1. Rarity Selection
        selected_rarity = select_rarity(pack, rng=rng)

        # 2. Driver Selection from Rarity Pool
        selected_driver = self.driver_pool.select_driver(selected_rarity, rng=rng)

        # 3. Create Unique Reward Instance
        reward_id = f"rew_{uuid.uuid4().hex[:12]}"

        return RewardResult(
            reward_id=reward_id,
            pack_id=pack.id,
            pack_name=pack.name,
            rarity=selected_rarity,
            driver=selected_driver,
            purchase_id=purchase_id
        )

    def trace_pack_opening(self, pack_id: str, rng: Optional[random.Random] = None) -> RewardResult:
        """Runs a verbose step-by-step trace of a single pack opening."""
        print("=" * 65)
        print(f"🏎️  ALGORACERS REWARD ENGINE — PACK OPENING TRACE")
        print("=" * 65)

        if pack_id not in self.packs:
            raise KeyError(f"Unknown pack '{pack_id}'")

        pack = self.packs[pack_id]
        print(f"[1. Pack Loaded]: {pack.name} ({pack.price} {pack.currency})")
        print(f"    Rarity Table:")
        for r, w in pack.rarities.items():
            print(f"      • {r:<10}: {w:>5.1f}%")

        # Roll Rarity
        generator = rng if rng is not None else random
        roll = generator.uniform(0.0, 100.0)
        print(f"\n[2. Random Rarity Roll]: Generated value = {roll:.4f} / 100.0")

        selected_rarity = select_rarity(pack, rng=rng)
        print(f"    Selected Rarity: ---> {selected_rarity.upper()} <---")

        # Query Driver Pool
        pool = self.driver_pool.pools_by_rarity[selected_rarity]
        print(f"\n[3. Driver Pool Lookup]: Found {len(pool)} eligible '{selected_rarity}' driver(s):")
        for d in pool:
            print(f"      • ID #{d.id}: {d.name} ({d.team})")

        selected_driver = self.driver_pool.select_driver(selected_rarity, rng=rng)
        print(f"\n[4. Selected Driver Template]: {selected_driver.name} (ID: #{selected_driver.id})")
        print(f"    Stats: {selected_driver.stats}")

        reward = RewardResult(
            reward_id=f"rew_{uuid.uuid4().hex[:12]}",
            pack_id=pack.id,
            pack_name=pack.name,
            rarity=selected_rarity,
            driver=selected_driver
        )

        print(f"\n[5. Generated Reward Result]:")
        print(f"    Reward ID:    {reward.reward_id}")
        print(f"    Generated At: {reward.generated_at}")
        print("=" * 65)
        return reward
