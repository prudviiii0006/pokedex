"""
Pokédex (AlgoCreatures) — Canonical Pokémon Master Catalog & Dataset Registry
Module: rewards/creature_pool.py
=============================================================================
Unified authoritative master catalog of all 247 canonical Pokémon species
from Generation I (#001–#151) through later generations with official PokéAPI
artwork, elemental types, stats, base experience, and stable rarity tiers.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from backend.rewards.models import CreatureTemplate

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "pokemon_catalog.json"

FACTIONS: Dict[str, Dict[str, str]] = {
    "ignis": {"id": "ignis", "name": "Ignis (Fire)", "element": "Fire", "color": "#FF4422"},
    "hydra": {"id": "hydra", "name": "Hydra (Water)", "element": "Water", "color": "#3399FF"},
    "sylvan": {"id": "sylvan", "name": "Sylvan (Grass)", "element": "Grass", "color": "#44BB44"},
    "volt": {"id": "volt", "name": "Volt (Electric)", "element": "Electric", "color": "#FFCC00"},
    "geo": {"id": "geo", "name": "Geo (Ground/Rock)", "element": "Ground", "color": "#AA7744"},
    "glacier": {"id": "glacier", "name": "Glacier (Ice)", "element": "Ice", "color": "#66DDFF"},
    "umbra": {"id": "umbra", "name": "Umbra (Dark/Ghost)", "element": "Dark", "color": "#8844AA"},
    "aether": {"id": "aether", "name": "Aether (Psychic/Fairy)", "element": "Psychic", "color": "#FF88DD"},
    "draco": {"id": "draco", "name": "Draco (Dragon)", "element": "Dragon", "color": "#7766EE"},
    "titan": {"id": "titan", "name": "Titan (Steel/Fighting)", "element": "Steel", "color": "#99AABB"}
}

# Legacy creature name aliases to preserve backwards compatibility with test fixtures
LEGACY_ALIASES: Dict[str, str] = {
    "emberling": "4",       # Charmander
    "pyreclaw": "5",        # Charmeleon
    "infernovar": "6",      # Charizard
    "aquafox": "7",         # Squirtle
    "tidalsurge": "8",      # Wartortle
    "hydravale": "9",       # Blastoise
    "leafpup": "1",         # Bulbasaur
    "bramblethorn": "2",    # Ivysaur
    "verdantitan": "3",     # Venusaur
    "sparkpup": "172",      # Pichu
    "voltpaw": "25",        # Pikachu
    "thundermane": "26",    # Raichu
    "gravelit": "443",      # Gible
    "terrashell": "444",    # Gabite
    "obsidimoth": "445",    # Garchomp
    "frostkit": "447",      # Riolu
    "blizzardfang": "448",  # Lucario
    "glacioron": "144",     # Articuno
    "umbrabbit": "92",      # Gastly
    "nightreaver": "93",    # Haunter
    "shadowstalker": "94",  # Gengar
    "luminling": "147",     # Dratini
    "solarynx": "148",      # Dragonair
    "aetheris": "149"       # Dragonite
}

def load_canonical_pokemon_catalog() -> List[CreatureTemplate]:
    """Loads all 247 Pokémon from authoritative pokemon_catalog.json."""
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(f"Master Pokemon catalog JSON not found at {CATALOG_PATH}")

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        raw_catalog = json.load(f)

    templates: List[CreatureTemplate] = []
    for item in raw_catalog:
        pid = int(item["id"])
        name = item.get("name", f"Pokemon #{pid}")
        primary_type = item.get("primaryType", "Normal")
        secondary_type = item.get("secondaryType")
        rarity = item.get("rarity", "Common")
        stats_dict = item.get("stats", {})

        base_hp = int(stats_dict.get("hp", stats_dict.get("HP", 70)))
        base_atk = int(stats_dict.get("attack", stats_dict.get("Attack", 70)))
        base_def = int(stats_dict.get("defense", stats_dict.get("Defense", 70)))
        base_spd = int(stats_dict.get("speed", stats_dict.get("Speed", 70)))
        base_stamina = int((base_hp + base_def) / 2)

        # Faction mapping based on primary type
        faction_map = {
            "Fire": "Ignis",
            "Water": "Hydra",
            "Grass": "Sylvan",
            "Electric": "Volt",
            "Ground": "Geo",
            "Rock": "Geo",
            "Ice": "Glacier",
            "Dark": "Umbra",
            "Ghost": "Umbra",
            "Poison": "Umbra",
            "Psychic": "Aether",
            "Fairy": "Aether",
            "Dragon": "Draco",
            "Steel": "Titan",
            "Fighting": "Titan",
            "Normal": "Aether",
            "Bug": "Sylvan",
            "Flying": "Aether"
        }
        faction = faction_map.get(primary_type, "Ignis")

        tmpl = CreatureTemplate(
            id=str(pid),
            index_number=pid,
            name=name,
            primary_type=primary_type,
            secondary_type=secondary_type,
            faction=faction,
            rarity=rarity,
            evolution_family=item.get("evolutionFamily", f"pokemon_line_{pid}"),
            evolution_stage=item.get("evolutionStage", 1),
            next_evolution_id=item.get("nextEvolutionId"),
            base_hp=base_hp,
            base_attack=base_atk,
            base_defense=base_def,
            base_speed=base_spd,
            base_stamina=base_stamina,
            description=f"Authentic {primary_type}-type {rarity} Pokémon #{pid:03d}. Collectible on-chain in your wallet.",
            image=item.get("image", f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pid}.png"),
            stats={
                "HP": base_hp,
                "Attack": base_atk,
                "Defense": base_def,
                "Speed": base_spd,
                "Stamina": base_stamina
            }
        )
        templates.append(tmpl)

    return templates

CANONICAL_CREATURES: List[CreatureTemplate] = load_canonical_pokemon_catalog()

class CreaturePool:
    """Master registry of all pack-eligible Pokémon in the Pokédex."""
    def __init__(self):
        self.creatures_by_id: Dict[str, CreatureTemplate] = {}
        self.unique_creatures: List[CreatureTemplate] = []
        self.pools_by_rarity: Dict[str, List[CreatureTemplate]] = {
            "Common": [],
            "Rare": [],
            "Epic": [],
            "Legendary": []
        }
        self.load_creatures()

    @property
    def creatures(self) -> Dict[str, CreatureTemplate]:
        return self.creatures_by_id

    @property
    def drivers(self) -> Dict[str, CreatureTemplate]:
        return self.creatures_by_id

    def load_creatures(self) -> None:
        self.creatures_by_id.clear()
        self.unique_creatures.clear()
        for pool in self.pools_by_rarity.values():
            pool.clear()

        global CANONICAL_CREATURES
        if not CANONICAL_CREATURES:
            CANONICAL_CREATURES = load_canonical_pokemon_catalog()

        for c in CANONICAL_CREATURES:
            self.unique_creatures.append(c)

            # Map by integer ID string ('25')
            self.creatures_by_id[str(c.index_number)] = c
            # Map by lowercase name ('pikachu')
            self.creatures_by_id[c.name.lower().strip()] = c
            # Map by formatted Pokédex number ('#025', '#25', '025')
            self.creatures_by_id[f"#{c.index_number:03d}"] = c
            self.creatures_by_id[f"#{c.index_number}"] = c
            self.creatures_by_id[f"{c.index_number:03d}"] = c
            # Map by template ID ('pokemon_25')
            self.creatures_by_id[f"pokemon_{c.index_number}"] = c

            # Index into rarity pools
            rarity = c.rarity
            if rarity in self.pools_by_rarity:
                self.pools_by_rarity[rarity].append(c)
            else:
                self.pools_by_rarity["Common"].append(c)

        # Register legacy aliases
        for alias, target_id in LEGACY_ALIASES.items():
            if target_id in self.creatures_by_id:
                self.creatures_by_id[alias.lower()] = self.creatures_by_id[target_id]

    def select_creature(self, rarity: str, rng: Optional[random.Random] = None) -> CreatureTemplate:
        """Draws a random Pokémon from the requested rarity tier in the master catalog."""
        pool = self.pools_by_rarity.get(rarity, [])
        if not pool:
            if self.unique_creatures:
                return next(iter(self.unique_creatures))
            raise ValueError(f"No Pokémon available for rarity: {rarity}")
        generator = rng if rng is not None else random
        return generator.choice(pool)

    def select_driver(self, rarity: str, rng: Optional[random.Random] = None) -> CreatureTemplate:
        return self.select_creature(rarity, rng=rng)

    def validate_coverage(self, active_rarities: List[str]) -> None:
        """Verifies that every active rarity tier has at least one eligible Pokémon."""
        for rarity in active_rarities:
            if not self.pools_by_rarity.get(rarity):
                raise ValueError(f"No Pokémon in pool for active rarity tier '{rarity}'")

    def get_creature(self, creature_id: Union[str, int]) -> Optional[CreatureTemplate]:
        """Resolves a Pokémon by ID, name, pokedex number, or legacy alias."""
        if creature_id is None:
            return None
        key = str(creature_id).lower().strip()
        if key in self.creatures_by_id:
            return self.creatures_by_id[key]
        
        # Strip leading # if present
        clean_key = key.lstrip('#')
        if clean_key in self.creatures_by_id:
            return self.creatures_by_id[clean_key]

        # Check legacy alias
        if key in LEGACY_ALIASES:
            target = LEGACY_ALIASES[key]
            if target in self.creatures_by_id:
                return self.creatures_by_id[target]

        return None

    def get_creature_by_id(self, creature_id: Union[str, int]) -> Optional[CreatureTemplate]:
        return self.get_creature(creature_id)

    def get_by_rarity(self, rarity: str) -> List[CreatureTemplate]:
        return self.pools_by_rarity.get(rarity, [])

    def get_all_creatures(self) -> List[CreatureTemplate]:
        return list(self.unique_creatures)

    def get_all_drivers(self) -> List[CreatureTemplate]:
        return self.get_all_creatures()

    def get_all_factions(self) -> List[Dict[str, str]]:
        return list(FACTIONS.values())

    def get_all_constructors(self) -> List[Dict[str, str]]:
        return self.get_all_factions()

    def get_creatures_by_faction(self, faction: str) -> List[CreatureTemplate]:
        f_norm = faction.lower().strip()
        return [
            c for c in self.unique_creatures 
            if c.faction.lower() == f_norm or c.primary_type.lower() == f_norm
        ]

    def get_drivers_by_constructor(self, cid: str) -> List[CreatureTemplate]:
        return self.get_creatures_by_faction(cid)

    def get_driver(self, driver_id: Union[str, int]) -> Optional[CreatureTemplate]:
        return self.get_creature(driver_id)

    def get_driver_by_id(self, driver_id: Union[str, int]) -> Optional[CreatureTemplate]:
        return self.get_creature(driver_id)

# Global singleton instance
creature_pool = CreaturePool()
driver_pool = creature_pool
DriverPool = CreaturePool
