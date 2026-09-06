"""
AlgoRacers — Session 5: Pack & Reward System
Module: rarity.py
============================================
Implements transparent weighted random selection for pack rarity tiers.
Algorithm:
  1. Validate that weights sum to exactly 100.0 (within float tolerance).
  2. Pick a random float `r` uniformly in the interval [0.0, 100.0).
  3. Iterate through cumulative intervals:
     - [0.0, W_common) -> Common
     - [W_common, W_common + W_rare) -> Rare
     - [W_common + W_rare, W_common + W_rare + W_epic) -> Epic
     - [..., 100.0) -> Legendary
"""

import random
from typing import Dict, Optional
from backend.rewards.models import PackConfig

SUPPORTED_RARITIES = {"Common", "Rare", "Epic", "Legendary"}

def validate_rarity_weights(rarities: Dict[str, float]) -> None:
    """Validates that rarity weights are positive and sum to 100%."""
    if not rarities:
        raise ValueError("Rarities configuration cannot be empty.")

    total = 0.0
    for rarity, weight in rarities.items():
        if rarity not in SUPPORTED_RARITIES:
            raise ValueError(f"Unsupported rarity tier '{rarity}'. Must be one of {SUPPORTED_RARITIES}")
        if weight < 0:
            raise ValueError(f"Rarity weight for '{rarity}' cannot be negative (received {weight}).")
        total += weight

    # Check total sums to 100 (using 0.001 tolerance for floating point representations)
    if abs(total - 100.0) > 0.001:
        raise ValueError(f"Rarity weights must sum to exactly 100% (currently sums to {total:.2f}%).")

def select_rarity(pack: PackConfig, rng: Optional[random.Random] = None) -> str:
    """
    Selects a rarity tier using cumulative weighted random sampling.
    Accepts an optional `rng` instance for deterministic automated testing.
    """
    validate_rarity_weights(pack.rarities)
    
    # Use injected or global random generator
    generator = rng if rng is not None else random

    # Generate a uniform float in [0.0, 100.0)
    roll = generator.uniform(0.0, 100.0)

    cumulative = 0.0
    for rarity, weight in pack.rarities.items():
        cumulative += weight
        if roll < cumulative:
            return rarity

    # Fallback to last rarity tier in the rare event roll == 100.0
    return list(pack.rarities.keys())[-1]
