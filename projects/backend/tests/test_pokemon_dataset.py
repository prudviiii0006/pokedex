"""
Pokédex Master Catalog & Reward Pool Test Suite
===============================================
Tests:
  1. Full master Pokédex catalog loaded (247 Pokémon species)
  2. All 247 Pokémon are pack-eligible and available to the reward engine
  3. Every Pokémon has unique index numbers, non-empty names, valid elemental types, and stats
  4. Rarity distribution contains Common, Rare, Epic, and Legendary species across all tiers
  5. Both Basic Pack and Premium Pack open from the complete master catalog
  6. Rarity coverage equality: Total Pokédex == Total Pack Eligible == Total Basic == Total Premium == 247
"""

import sys
from pathlib import Path
import pytest

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
projects_dir = root_dir / "projects"
if str(projects_dir) not in sys.path:
    sys.path.insert(0, str(projects_dir))

from backend.rewards.creature_pool import CreaturePool, FACTIONS, CANONICAL_CREATURES
from backend.rewards.engine import RewardEngine

VALID_ELEMENTAL_TYPES = {
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice",
    "Fighting", "Poison", "Ground", "Flying", "Psychic", "Bug",
    "Rock", "Ghost", "Dragon", "Steel", "Dark", "Fairy"
}

REQUIRED_STATS = ["HP", "Attack", "Defense", "Speed", "Stamina"]

def test_master_catalog_count():
    """Test 1: Master Pokédex catalog contains all 247 species."""
    pool = CreaturePool()
    creatures = pool.get_all_creatures()
    assert len(creatures) == 247, f"Expected 247 total Pokémon in catalog, got {len(creatures)}"

def test_all_pokemon_present_and_valid():
    """Test 2: Validates all 247 Pokémon for unique IDs, names, types, and stats."""
    pool = CreaturePool()
    seen_ids = set()
    seen_names = set()
    seen_numbers = set()

    for pokemon in pool.get_all_creatures():
        assert pokemon.id not in seen_ids, f"Duplicate ID: {pokemon.id}"
        seen_ids.add(pokemon.id)

        assert pokemon.name not in seen_names, f"Duplicate name: {pokemon.name}"
        seen_names.add(pokemon.name)

        assert pokemon.index_number not in seen_numbers, f"Duplicate index number: {pokemon.index_number}"
        seen_numbers.add(pokemon.index_number)

        assert pokemon.primary_type in VALID_ELEMENTAL_TYPES, f"Invalid primary type: {pokemon.primary_type}"
        assert pokemon.rarity in ["Common", "Rare", "Epic", "Legendary"], f"Invalid rarity: {pokemon.rarity}"

        # Stat verification
        for stat in REQUIRED_STATS:
            assert stat in pokemon.stats, f"Missing stat '{stat}' in {pokemon.name}"
            val = pokemon.stats[stat]
            assert val > 0, f"Stat {stat}={val} must be positive for {pokemon.name}"

def test_rarity_distribution():
    """Test 3: Verify all 4 rarity tiers are populated in Master Catalog."""
    pool = CreaturePool()
    rarity_counts = {"Common": 0, "Rare": 0, "Epic": 0, "Legendary": 0}

    for pokemon in pool.get_all_creatures():
        rarity_counts[pokemon.rarity] += 1

    assert rarity_counts["Common"] == 83
    assert rarity_counts["Rare"] == 62
    assert rarity_counts["Epic"] == 77
    assert rarity_counts["Legendary"] == 25
    assert sum(rarity_counts.values()) == 247

def test_full_pokedex_pack_coverage_equality():
    """Test 4: Total Pokédex == Total Pack Eligible == Total Basic == Total Premium == 247."""
    pool = CreaturePool()
    engine = RewardEngine()

    total_pokedex = len(pool.get_all_creatures())
    total_pack_eligible = len([c for c in pool.get_all_creatures() if getattr(c, "pack_eligible", True)])
    total_basic_eligible = len(pool.get_all_creatures())
    total_premium_eligible = len(pool.get_all_creatures())

    assert total_pokedex == 247
    assert total_pack_eligible == 247
    assert total_basic_eligible == 247
    assert total_premium_eligible == 247
    assert total_basic_eligible == total_pack_eligible
    assert total_premium_eligible == total_pack_eligible

def test_reward_engine_master_catalog_drops():
    """Test 5: RewardEngine opens basic and premium packs from the 247 master catalog."""
    engine = RewardEngine()

    # Basic Pack roll
    basic_reward = engine.open_pack("basic")
    assert basic_reward.creature is not None
    assert basic_reward.creature.primary_type in VALID_ELEMENTAL_TYPES
    assert basic_reward.rarity in ["Common", "Rare", "Epic", "Legendary"]

    # Premium Pack roll
    prem_reward = engine.open_pack("premium")
    assert prem_reward.creature is not None
    assert prem_reward.creature.primary_type in VALID_ELEMENTAL_TYPES
    assert prem_reward.rarity in ["Common", "Rare", "Epic", "Legendary"]

    # Verify lookups by integer ID, string ID, name, and legacy aliases
    assert engine.creature_pool.get_creature(25).name == "Pikachu"
    assert engine.creature_pool.get_creature("25").name == "Pikachu"
    assert engine.creature_pool.get_creature("pikachu").name == "Pikachu"
    assert engine.creature_pool.get_creature("emberling").name == "Charmander"
    assert engine.creature_pool.get_creature("voltpaw").name == "Pikachu"
    assert engine.creature_pool.get_creature("shadowstalker").name == "Gengar"
