"""
AlgoRacers — Session 5: Pack & Reward System Test Suite
======================================================
Tests:
  1. Basic pack probabilities sum to 100
  2. Premium pack probabilities sum to 100
  3. Unknown pack type raises KeyError
  4. Invalid/negative rarity raises ValueError
  5. Missing driver pool raises ValueError
  6. Reward result contains valid driver template
  7. Reward rarity matches driver's configured rarity
  8. Generated reward IDs are unique
  9. Injected deterministic RNG produces reproducible results
  10. Monte Carlo distribution matches configuration within statistical tolerance
"""

import os
import random
import sys
from pathlib import Path
import pytest

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.rewards.engine import RewardEngine
from backend.rewards.models import PackConfig
from backend.rewards.rarity import validate_rarity_weights, select_rarity

@pytest.fixture
def engine():
    return RewardEngine()

def test_basic_probabilities_sum_100(engine):
    """Test 1: Basic pack probabilities total exactly 100%."""
    basic_pack = engine.packs["basic"]
    total = sum(basic_pack.rarities.values())
    assert abs(total - 100.0) < 0.001

def test_premium_probabilities_sum_100(engine):
    """Test 2: Premium pack probabilities total exactly 100%."""
    prem_pack = engine.packs["premium"]
    total = sum(prem_pack.rarities.values())
    assert abs(total - 100.0) < 0.001

def test_unknown_pack_rejected(engine):
    """Test 3: Requesting non-existent pack raises KeyError."""
    with pytest.raises(KeyError):
        engine.open_pack("hyper_pack_9000")

def test_invalid_rarity_rejected():
    """Test 4: Invalid rarity weights (e.g. sums to 110%) raise ValueError."""
    invalid_weights = {"Common": 80.0, "Rare": 30.0}  # Sums to 110%
    with pytest.raises(ValueError, match="must sum to exactly 100%"):
        validate_rarity_weights(invalid_weights)

    negative_weights = {"Common": -10.0, "Rare": 110.0}
    with pytest.raises(ValueError, match="cannot be negative"):
        validate_rarity_weights(negative_weights)

def test_empty_driver_pool_rejected(tmp_path):
    """Test 5: Empty driver directory raises error during initialization."""
    empty_dir = tmp_path / "empty_metadata"
    empty_dir.mkdir()
    with pytest.raises(ValueError, match="No driver metadata files found"):
        RewardEngine(metadata_dir=empty_dir)

def test_reward_contains_valid_driver(engine):
    """Test 6: Reward contains complete driver template."""
    reward = engine.open_pack("basic")
    assert reward.driver is not None
    assert reward.driver.id != ""
    assert reward.driver.name != ""
    assert "Speed" in reward.driver.stats
    assert "Racecraft" in reward.driver.stats

def test_reward_rarity_matches_driver(engine):
    """Test 7: Rolled rarity strictly matches the driver's intrinsic rarity."""
    for _ in range(50):
        reward = engine.open_pack("premium")
        assert reward.rarity == reward.driver.rarity

def test_reward_id_unique(engine):
    """Test 8: Successive openings emit unique reward IDs."""
    ids = {engine.open_pack("basic").reward_id for _ in range(100)}
    assert len(ids) == 100

def test_deterministic_test_rng(engine):
    """Test 9: Seeded RNG produces identical deterministic outcomes."""
    rng1 = random.Random(42)
    reward1 = engine.open_pack("premium", rng=rng1)

    rng2 = random.Random(42)
    reward2 = engine.open_pack("premium", rng=rng2)

    assert reward1.rarity == reward2.rarity
    assert reward1.driver.id == reward2.driver.id
    assert reward1.driver.name == reward2.driver.name

def test_statistical_tolerance(engine):
    """Test 10: 10,000 Basic openings converge within statistical tolerance (+-2%)."""
    count = 10000
    counts = {"Common": 0, "Rare": 0, "Epic": 0, "Legendary": 0}
    
    for _ in range(count):
        reward = engine.open_pack("basic")
        counts[reward.rarity] += 1

    common_pct = (counts["Common"] / count) * 100.0
    rare_pct = (counts["Rare"] / count) * 100.0

    # Basic expected: Common 65%, Rare 25%
    assert abs(common_pct - 65.0) < 2.0, f"Common % was {common_pct:.2f}%, expected ~65%"
    assert abs(rare_pct - 25.0) < 2.0, f"Rare % was {rare_pct:.2f}%, expected ~25%"
