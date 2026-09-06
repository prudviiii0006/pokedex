"""
AlgoRacers — Session 15: Deterministic Race Engine v1
Module: services/race_engine_v1.py
===================================================
Public, fully reproducible racing simulation engine:
  - Strict canonical participant ordering
  - Zero unseeded global RNG calls
  - Domain-separated sub-seed variance derivation
  - Exact mathematical reproducibility
"""

import hashlib
import json
from typing import Dict, List, Any, Tuple
from backend.app.models.race import Circuit, GridParticipant
from backend.app.services.seed_derivation import (
    derive_master_race_seed, derive_sub_seed,
    bytes_to_uniform_float, canonicalize_participants
)
from backend.rewards.engine import RewardEngine
from backend.app.core.config import settings

POINTS_DISTRIBUTION = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4
}

class DeterministicRaceEngineV1:
    """
    Race Engine Version 1.0 (Deterministic).
    Every execution with identical inputs produces the EXACT same ranking and hash.
    """
    ENGINE_VERSION = "v1"

    def __init__(self):
        self.reward_engine = RewardEngine(
            packs_config_path=settings.PACKS_CONFIG_PATH,
            metadata_dir=settings.METADATA_DIR
        )

    def calculate_base_performance(self, driver_stats: Dict[str, int], circuit: Circuit) -> float:
        """Computes weighted base score based on circuit demands."""
        score = 0.0
        for stat_name, weight in circuit.stat_weights.items():
            stat_val = driver_stats.get(stat_name, 70)
            score += stat_val * weight
        return round(score, 2)

    def simulate_deterministic_tournament(
        self,
        app_id: int,
        registered_participants: List[Dict[str, Any]],
        circuit: Circuit,
        beacon_randomness: bytes
    ) -> Dict[str, Any]:
        """
        Executes a 100% deterministic 8-car Grand Prix race.
        """
        # 1. Canonicalize participant list (Sort by asset_id ascending)
        sorted_participants = sorted(registered_participants, key=lambda p: p["asset_id"])

        # 2. Derive Master Race Seed
        master_seed = derive_master_race_seed(
            beacon_randomness=beacon_randomness,
            app_id=app_id,
            participants=sorted_participants,
            circuit_id=circuit.id,
            race_engine_version=self.ENGINE_VERSION
        )

        # 3. Assemble 8-Car Grid (Fill with deterministic CPU templates if needed)
        all_drivers = self.reward_engine.driver_pool.get_all_drivers()
        all_drivers_sorted = sorted(all_drivers, key=lambda d: d.id)

        grid_drivers = []
        # Add real registered participants
        for p in sorted_participants:
            driver_template = self.reward_engine.driver_pool.get_driver_by_id(p.get("driver_id", "010"))
            if not driver_template:
                driver_template = all_drivers_sorted[0]
            grid_drivers.append({
                "wallet_address": p["wallet_address"],
                "asset_id": p["asset_id"],
                "driver_id": driver_template.id,
                "driver_name": driver_template.name,
                "rarity": driver_template.rarity,
                "stats": driver_template.stats,
                "is_player": True
            })

        # Fill remaining slots up to 8 with deterministic CPU opponents
        cpu_sub_seed = derive_sub_seed(master_seed, "cpu_selection")
        cpu_idx = 0
        slot = len(grid_drivers) + 1
        while len(grid_drivers) < 8:
            cpu_template = all_drivers_sorted[(int.from_bytes(cpu_sub_seed[cpu_idx:cpu_idx+2], "big") + cpu_idx) % len(all_drivers_sorted)]
            grid_drivers.append({
                "wallet_address": f"CPU_OPPONENT_{slot}",
                "asset_id": 900000000 + slot,
                "driver_id": cpu_template.id,
                "driver_name": f"{cpu_template.name} (AI #{slot})",
                "rarity": cpu_template.rarity,
                "stats": cpu_template.stats,
                "is_player": False
            })
            cpu_idx = (cpu_idx + 2) % 30
            slot += 1

        # 4. Calculate Scores with Deterministic Domain-Separated Variances
        calculated_grid = []
        for d in grid_drivers:
            base_score = self.calculate_base_performance(d["stats"], circuit)
            # Derive deterministic variance in [-2.5, +2.5]
            var_seed = derive_sub_seed(master_seed, "driver_variance", str(d["asset_id"]))
            variance = bytes_to_uniform_float(var_seed, -2.5, 2.5)
            final_score = round(base_score + variance, 2)
            
            # Deterministic lap time (approx 75s +/- score impact)
            lap_time = round(85.0 - (final_score * 0.2), 3)

            calculated_grid.append({
                "wallet_address": d["wallet_address"],
                "asset_id": d["asset_id"],
                "driver_id": d["driver_id"],
                "driver_name": d["driver_name"],
                "rarity": d["rarity"],
                "base_score": base_score,
                "variance": variance,
                "final_score": final_score,
                "lap_time_seconds": lap_time,
                "is_player": d["is_player"]
            })

        # 5. Sort Grid Descending by Final Score
        ranked_grid = sorted(calculated_grid, key=lambda x: x["final_score"], reverse=True)

        # 6. Assign Positions & Championship Points
        final_grid = []
        for pos, item in enumerate(ranked_grid, start=1):
            pts = POINTS_DISTRIBUTION.get(pos, 0)
            item["position"] = pos
            item["points"] = pts
            final_grid.append(item)

        winner = final_grid[0]

        # 7. Construct Canonical Result Object
        canonical_result = {
            "app_id": app_id,
            "circuit_id": circuit.id,
            "circuit_name": circuit.name,
            "race_engine_version": self.ENGINE_VERSION,
            "total_drivers": len(final_grid),
            "winner_wallet": winner["wallet_address"],
            "winner_asset_id": winner["asset_id"],
            "winner_driver_name": winner["driver_name"],
            "grid": final_grid
        }

        # 8. Compute SHA-256 Canonical Result Hash
        canonical_json = json.dumps(canonical_result, sort_keys=True, separators=(",", ":"))
        result_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        canonical_result["result_hash"] = result_hash

        return canonical_result

deterministic_race_engine = DeterministicRaceEngineV1()
