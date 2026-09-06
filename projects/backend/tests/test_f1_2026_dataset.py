import os
import sys
from pathlib import Path
import pytest

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
projects_dir = root_dir / "projects"
if str(projects_dir) not in sys.path:
    sys.path.insert(0, str(projects_dir))

from backend.rewards.driver_pool import DriverPool, CONSTRUCTORS
from backend.rewards.engine import RewardEngine
from backend.rewards.models import DriverTemplate

EXPECTED_CONSTRUCTORS = {
    "mclaren": "McLaren",
    "mercedes": "Mercedes",
    "ferrari": "Ferrari",
    "red_bull_racing": "Red Bull Racing",
    "racing_bulls": "Racing Bulls",
    "aston_martin": "Aston Martin",
    "haas": "Haas F1 Team",
    "audi": "Audi",
    "alpine": "Alpine",
    "williams": "Williams",
    "cadillac": "Cadillac"
}

EXPECTED_DRIVERS = [
    # McLaren
    ("lando_norris", "Lando Norris", "NOR", 4, "mclaren", "Epic"),
    ("oscar_piastri", "Oscar Piastri", "PIA", 81, "mclaren", "Rare"),
    # Mercedes
    ("george_russell", "George Russell", "RUS", 63, "mercedes", "Epic"),
    ("kimi_antonelli", "Kimi Antonelli", "ANT", 12, "mercedes", "Rare"),
    # Ferrari
    ("charles_leclerc", "Charles Leclerc", "LEC", 16, "ferrari", "Epic"),
    ("lewis_hamilton", "Lewis Hamilton", "HAM", 44, "ferrari", "Legendary"),
    # Red Bull Racing
    ("max_verstappen", "Max Verstappen", "VER", 1, "red_bull_racing", "Legendary"),
    ("isack_hadjar", "Isack Hadjar", "HAD", 6, "red_bull_racing", "Common"),
    # Racing Bulls
    ("liam_lawson", "Liam Lawson", "LAW", 30, "racing_bulls", "Common"),
    ("arvid_lindblad", "Arvid Lindblad", "LIN", 41, "racing_bulls", "Common"),
    # Aston Martin
    ("fernando_alonso", "Fernando Alonso", "ALO", 14, "aston_martin", "Epic"),
    ("lance_stroll", "Lance Stroll", "STR", 18, "aston_martin", "Common"),
    # Haas F1 Team
    ("esteban_ocon", "Esteban Ocon", "OCO", 31, "haas", "Rare"),
    ("oliver_bearman", "Oliver Bearman", "BEA", 87, "haas", "Common"),
    # Audi
    ("nico_hulkenberg", "Nico Hulkenberg", "HUL", 27, "audi", "Rare"),
    ("gabriel_bortoleto", "Gabriel Bortoleto", "BOR", 5, "audi", "Common"),
    # Alpine
    ("pierre_gasly", "Pierre Gasly", "GAS", 10, "alpine", "Rare"),
    ("franco_colapinto", "Franco Colapinto", "COL", 43, "alpine", "Common"),
    # Williams
    ("carlos_sainz", "Carlos Sainz", "SAI", 55, "williams", "Epic"),
    ("alexander_albon", "Alexander Albon", "ALB", 23, "williams", "Rare"),
    # Cadillac
    ("sergio_perez", "Sergio Perez", "PER", 11, "cadillac", "Rare"),
    ("valtteri_bottas", "Valtteri Bottas", "BOT", 77, "cadillac", "Common")
]

REQUIRED_STATS = ["Speed", "Qualifying", "Racecraft", "Overtaking", "Wet Weather", "Consistency"]

def test_driver_count_and_constructors():
    pool = DriverPool()
    drivers = pool.get_all_drivers()
    assert len(drivers) == 22, f"Expected exactly 22 drivers, got {len(drivers)}"
    
    constructors = pool.get_all_constructors()
    assert len(constructors) == 11, f"Expected exactly 11 constructors, got {len(constructors)}"
    
    constructor_ids = {c["id"] for c in constructors}
    assert constructor_ids == set(EXPECTED_CONSTRUCTORS.keys())

def test_two_drivers_per_constructor():
    pool = DriverPool()
    for cid in EXPECTED_CONSTRUCTORS.keys():
        c_drivers = pool.get_drivers_by_constructor(cid)
        assert len(c_drivers) == 2, f"Constructor '{cid}' must have exactly 2 drivers, found {len(c_drivers)}"

def test_all_expected_drivers_present_and_valid():
    pool = DriverPool()
    seen_ids = set()
    seen_names = set()
    seen_numbers = set()

    for d_id, d_name, d_code, d_num, d_cid, d_rarity in EXPECTED_DRIVERS:
        driver = pool.get_driver_by_id(d_id)
        assert driver is not None, f"Driver '{d_id}' not found in DriverPool"
        
        assert driver.name == d_name
        assert driver.code == d_code
        assert driver.number == d_num
        assert driver.constructor_id == d_cid
        assert driver.constructor_name == EXPECTED_CONSTRUCTORS[d_cid]
        assert driver.season == 2026
        assert driver.rarity == d_rarity

        # Check required stats
        for stat in REQUIRED_STATS:
            assert stat in driver.stats, f"Driver '{driver.name}' missing required stat '{stat}'"
            val = driver.stats[stat]
            assert 60 <= val <= 100, f"Driver '{driver.name}' stat '{stat}'={val} out of expected bounds [60, 100]"

        # Ensure uniqueness
        assert driver.id not in seen_ids, f"Duplicate driver ID: {driver.id}"
        assert driver.name not in seen_names, f"Duplicate driver name: {driver.name}"
        assert (driver.constructor_id, driver.number) not in seen_numbers, f"Duplicate number in team: {driver.number}"
        
        seen_ids.add(driver.id)
        seen_names.add(driver.name)
        seen_numbers.add((driver.constructor_id, driver.number))

def test_rarity_distribution():
    pool = DriverPool()
    assert len(pool.pools_by_rarity["Legendary"]) == 2
    assert len(pool.pools_by_rarity["Epic"]) == 5
    assert len(pool.pools_by_rarity["Rare"]) == 7
    assert len(pool.pools_by_rarity["Common"]) == 8

def test_reward_engine_pack_opening_f1_grid():
    engine = RewardEngine()
    for pack_type in ["basic", "premium"]:
        res = engine.open_pack(pack_type)
        assert res.driver is not None
        assert res.driver.season == 2026
        assert res.driver.constructor_id in EXPECTED_CONSTRUCTORS
        assert res.driver.number > 0
        assert res.driver.code != ""
        assert res.driver.name != "Neon Racer"
        assert res.driver.name != "Neon Viper"
        assert res.driver.name != "Apex Phantom"
