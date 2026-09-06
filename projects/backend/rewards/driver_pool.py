"""
AlgoRacers — 2026 Formula 1 Driver Pool & Reward Engine Dataset
Module: driver_pool.py
==============================================================
Loads, categorizes, and indexes canonical 2026 F1 driver templates from metadata.
"""

import json
from pathlib import Path
import random
from typing import Dict, List, Optional, Set
from backend.rewards.models import DriverTemplate

CONSTRUCTORS: Dict[str, Dict[str, str]] = {
    "mclaren": {"id": "mclaren", "name": "McLaren"},
    "mercedes": {"id": "mercedes", "name": "Mercedes"},
    "ferrari": {"id": "ferrari", "name": "Ferrari"},
    "red_bull_racing": {"id": "red_bull_racing", "name": "Red Bull Racing"},
    "racing_bulls": {"id": "racing_bulls", "name": "Racing Bulls"},
    "aston_martin": {"id": "aston_martin", "name": "Aston Martin"},
    "haas": {"id": "haas", "name": "Haas F1 Team"},
    "audi": {"id": "audi", "name": "Audi"},
    "alpine": {"id": "alpine", "name": "Alpine"},
    "williams": {"id": "williams", "name": "Williams"},
    "cadillac": {"id": "cadillac", "name": "Cadillac"}
}

class DriverPool:
    def __init__(self, metadata_dir: Optional[Path] = None):
        if metadata_dir is None:
            candidate_1 = Path(__file__).resolve().parent.parent.parent.parent / "blockchain" / "metadata"
            candidate_2 = Path(__file__).resolve().parent.parent.parent / "blockchain" / "metadata"
            if candidate_1.exists():
                self.metadata_dir = candidate_1
            elif candidate_2.exists():
                self.metadata_dir = candidate_2
            else:
                self.metadata_dir = candidate_1
        else:
            self.metadata_dir = metadata_dir

        self.drivers_by_id: Dict[str, DriverTemplate] = {}
        self._lookup_map: Dict[str, DriverTemplate] = {}
        self.pools_by_rarity: Dict[str, List[DriverTemplate]] = {
            "Common": [],
            "Rare": [],
            "Epic": [],
            "Legendary": []
        }
        self.load_drivers()

    @property
    def drivers(self) -> Dict[str, DriverTemplate]:
        """Backward compatibility property returning primary drivers dictionary."""
        return self.drivers_by_id

    def load_drivers(self) -> None:
        """Parses all driver metadata JSON files into structured memory pools."""
        if not self.metadata_dir.exists():
            raise FileNotFoundError(f"Metadata directory not found at: {self.metadata_dir}")

        json_files = sorted(list(self.metadata_dir.glob("driver_*.json")))
        if not json_files:
            raise ValueError(f"No driver metadata files found in: {self.metadata_dir}")

        self.drivers_by_id.clear()
        self._lookup_map.clear()
        for pool in self.pools_by_rarity.values():
            pool.clear()

        seen_unique_ids: Set[str] = set()

        for file_path in json_files:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            props = data.get("properties", {})
            slug_id = props.get("driver_id", file_path.stem.replace("driver_", ""))
            numeric_id = props.get("numeric_id", file_path.stem.replace("driver_", ""))
            driver_name = props.get("driver_name", data.get("name", "Unknown"))
            code = props.get("code", "")
            number = int(props.get("number", 0))
            constructor_id = props.get("constructor_id", "")
            constructor_name = props.get("constructor_name", props.get("team", "Formula 1"))
            nationality = props.get("nationality", "")
            season = int(props.get("season", 2026))

            # Extract attributes
            attr_map = {}
            for attr in data.get("attributes", []):
                attr_map[attr.get("trait_type")] = attr.get("value")

            rarity = attr_map.get("Rarity", "Common")
            if rarity not in self.pools_by_rarity:
                rarity = "Common"

            stats = {k: v for k, v in attr_map.items() if k not in ["Rarity", "Constructor", "Number", "Nationality"] and isinstance(v, (int, float))}

            # Primary canonical key: slug_id (e.g. 'max_verstappen') or numeric_id if slug not present
            primary_id = slug_id if not slug_id.isdigit() else numeric_id

            template = DriverTemplate(
                id=primary_id,
                name=driver_name,
                code=code,
                number=number,
                constructor_id=constructor_id,
                constructor_name=constructor_name,
                team=constructor_name,
                nationality=nationality,
                season=season,
                rarity=rarity,
                description=data.get("description", ""),
                image=data.get("image", ""),
                stats=stats,
                raw_metadata_path=str(file_path)
            )

            # Avoid duplicating in pools if both driver_001.json and driver_lando_norris.json exist
            if primary_id not in seen_unique_ids and driver_name not in [d.name for d in self.drivers_by_id.values()]:
                seen_unique_ids.add(primary_id)
                self.drivers_by_id[primary_id] = template
                self.pools_by_rarity[rarity].append(template)

            # Populate flexible lookup map
            self._lookup_map[primary_id] = template
            self._lookup_map[primary_id.lower()] = template
            self._lookup_map[slug_id] = template
            self._lookup_map[slug_id.lower()] = template
            self._lookup_map[numeric_id] = template
            if numeric_id.isdigit():
                self._lookup_map[str(int(numeric_id))] = template
                self._lookup_map[f"{int(numeric_id):03d}"] = template
            if code:
                self._lookup_map[code.upper()] = template
                self._lookup_map[code.lower()] = template
            self._lookup_map[driver_name.lower()] = template

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
        """Retrieves a driver template by ID, slug, numeric index, code, or name."""
        if not driver_id:
            return None
        key = str(driver_id).strip()
        if key in self._lookup_map:
            return self._lookup_map[key]
        if key.lower() in self._lookup_map:
            return self._lookup_map[key.lower()]
        if key.isdigit():
            norm_id = f"{int(key):03d}"
            if norm_id in self._lookup_map:
                return self._lookup_map[norm_id]
        return self.drivers_by_id.get(key)

    def get_all_drivers(self) -> List[DriverTemplate]:
        """Returns all 22 unique driver templates."""
        return list(self.drivers_by_id.values())

    def get_all_constructors(self) -> List[Dict[str, str]]:
        """Returns all 11 normalized constructor descriptors."""
        return list(CONSTRUCTORS.values())

    def get_drivers_by_constructor(self, constructor_id: str) -> List[DriverTemplate]:
        """Returns the 2 drivers for a given constructor."""
        norm_cid = constructor_id.lower().replace(" ", "_")
        return [d for d in self.drivers_by_id.values() if d.constructor_id == norm_cid or d.constructor_name.lower() == constructor_id.lower()]

    def validate_coverage(self, required_rarities: List[str]) -> None:
        """Ensures every required rarity has at least one driver available."""
        for r in required_rarities:
            if not self.pools_by_rarity.get(r):
                raise ValueError(f"Driver pool has 0 drivers for configured pack rarity '{r}'")

