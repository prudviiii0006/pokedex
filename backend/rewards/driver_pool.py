"""
AlgoRacers — Session 5: Pack & Reward System
Module: driver_pool.py
============================================
Loads, categorizes, and selects driver templates from the collection metadata.
"""

import json
from pathlib import Path
import random
from typing import Dict, List, Optional
from backend.rewards.models import DriverTemplate

class DriverPool:
    def __init__(self, metadata_dir: Optional[Path] = None):
        if metadata_dir is None:
            # Default to blockchain/metadata
            self.metadata_dir = Path(__file__).resolve().parent.parent.parent / "blockchain" / "metadata"
        else:
            self.metadata_dir = metadata_dir

        self.drivers_by_id: Dict[str, DriverTemplate] = {}
        self.pools_by_rarity: Dict[str, List[DriverTemplate]] = {
            "Common": [],
            "Rare": [],
            "Epic": [],
            "Legendary": []
        }
        self.load_drivers()

    def load_drivers(self) -> None:
        """Parses all driver metadata JSON files into structured memory pools."""
        if not self.metadata_dir.exists():
            raise FileNotFoundError(f"Metadata directory not found at: {self.metadata_dir}")

        json_files = sorted(list(self.metadata_dir.glob("driver_*.json")))
        if not json_files:
            raise ValueError(f"No driver metadata files found in: {self.metadata_dir}")

        self.drivers_by_id.clear()
        for pool in self.pools_by_rarity.values():
            pool.clear()

        for file_path in json_files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            props = data.get("properties", {})
            driver_id = props.get("driver_id", file_path.stem.replace("driver_", ""))
            driver_name = props.get("driver_name", data.get("name", "Unknown"))
            team = props.get("team", "Independent")
            
            # Extract attributes
            attr_map = {}
            for attr in data.get("attributes", []):
                attr_map[attr.get("trait_type")] = attr.get("value")

            rarity = attr_map.get("Rarity")
            if not rarity or rarity not in self.pools_by_rarity:
                raise ValueError(f"Driver '{file_path.name}' has invalid rarity '{rarity}'")

            stats = {k: v for k, v in attr_map.items() if k != "Rarity" and isinstance(v, (int, float))}

            template = DriverTemplate(
                id=driver_id,
                name=driver_name,
                team=team,
                rarity=rarity,
                description=data.get("description", ""),
                image=data.get("image", ""),
                stats=stats,
                raw_metadata_path=str(file_path)
            )

            if driver_id in self.drivers_by_id:
                raise ValueError(f"Duplicate driver ID detected: '{driver_id}'")

            self.drivers_by_id[driver_id] = template
            self.pools_by_rarity[rarity].append(template)

    def select_driver(self, rarity: str, rng: Optional[random.Random] = None) -> DriverTemplate:
        """Selects a random driver template from the specified rarity pool."""
        if rarity not in self.pools_by_rarity:
            raise KeyError(f"Rarity '{rarity}' is not a valid tier.")

        pool = self.pools_by_rarity[rarity]
        if not pool:
            raise ValueError(f"No eligible drivers found in the '{rarity}' rarity pool.")

        generator = rng if rng is not None else random
        return generator.choice(pool)

    def get_driver_by_id(self, driver_id: str) -> Optional[DriverTemplate]:
        """Retrieves a driver template by ID (normalized e.g. '001' or '1')."""
        norm_id = f"{int(driver_id):03d}" if str(driver_id).isdigit() else str(driver_id)
        return self.drivers_by_id.get(norm_id) or self.drivers_by_id.get(driver_id)

    def get_all_drivers(self) -> List[DriverTemplate]:
        """Returns all loaded driver templates."""
        return list(self.drivers_by_id.values())

    def validate_coverage(self, required_rarities: List[str]) -> None:
        """Ensures every required rarity has at least one driver available."""
        for r in required_rarities:
            if not self.pools_by_rarity.get(r):
                raise ValueError(f"Driver pool has 0 drivers for configured pack rarity '{r}'")
