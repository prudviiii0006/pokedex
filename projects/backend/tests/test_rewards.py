"""
AlgoCreatures — Pack & Creature Reward System Test Suite
========================================================
Tests:
  1. Basic pack probabilities sum to 100
  2. Premium pack probabilities sum to 100
  3. Unknown pack type raises KeyError
  4. Invalid/negative rarity raises ValueError
  5. Reward result contains valid creature template
  6. Reward rarity matches creature's configured rarity
  7. Generated reward IDs are unique
  8. Injected deterministic RNG produces reproducible results
  9. Monte Carlo distribution matches configuration within statistical tolerance
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

def test_reward_contains_valid_creature(engine):
    """Test 5: Reward contains complete creature template."""
    reward = engine.open_pack("basic")
    assert reward.creature is not None
    assert reward.creature.id != ""
    assert reward.creature.name != ""
    assert "HP" in reward.creature.stats
    assert "Attack" in reward.creature.stats
    assert "Defense" in reward.creature.stats
    assert "Speed" in reward.creature.stats

def test_reward_rarity_matches_creature(engine):
    """Test 6: Rolled rarity strictly matches the creature's intrinsic rarity."""
    for _ in range(50):
        reward = engine.open_pack("premium")
        assert reward.rarity == reward.creature.rarity

def test_reward_id_unique(engine):
    """Test 7: Successive openings emit unique reward IDs."""
    ids = {engine.open_pack("basic").reward_id for _ in range(100)}
    assert len(ids) == 100

def test_deterministic_test_rng(engine):
    """Test 8: Seeded RNG produces identical deterministic outcomes."""
    rng1 = random.Random(42)
    reward1 = engine.open_pack("premium", rng=rng1)

    rng2 = random.Random(42)
    reward2 = engine.open_pack("premium", rng=rng2)

    assert reward1.rarity == reward2.rarity
    assert reward1.creature.id == reward2.creature.id
    assert reward1.creature.name == reward2.creature.name

def test_statistical_tolerance(engine):
    """Test 9: 10,000 Basic openings converge within statistical tolerance (+-2%)."""
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
