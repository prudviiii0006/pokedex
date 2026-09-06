"""
AlgoRacers — Session 15: Verifiable Seed Derivation & Domain Separation
Module: services/seed_derivation.py
=======================================================================
Implements deterministic, domain-separated cryptographic key derivation:
  1. Master Race Seed from VRF Randomness + Canonical Tournament Parameters
  2. Domain-separated sub-seeds (qualifying, race variance, incident)
  3. Non-biased uniform mapping from cryptographic bytes to float ranges
"""

import hashlib
import json
from typing import List, Dict, Any

def canonicalize_participants(participants: List[Dict[str, Any]]) -> str:
    """
    Sorts participants strictly by asset_id ascending to eliminate database
    query ordering discrepancies and produce a canonical JSON string.
    """
    sorted_parts = sorted(participants, key=lambda p: p["asset_id"])
    return json.dumps(sorted_parts, sort_keys=True, separators=(",", ":"))

def derive_master_race_seed(
    beacon_randomness: bytes,
    app_id: int,
    participants: List[Dict[str, Any]],
    circuit_id: str,
    race_engine_version: str = "v1"
) -> bytes:
    """
    Derives 32-byte Master Race Seed using SHA-256 over all locked tournament inputs.
    All inputs MUST be committed on-chain BEFORE randomness is revealed!
    """
    canonical_parts_str = canonicalize_participants(participants)
    
    hasher = hashlib.sha256()
    hasher.update(b"AlgoRacersMasterSeed_v1:")
    hasher.update(beacon_randomness)
    hasher.update(f":app_{app_id}:".encode("utf-8"))
    hasher.update(canonical_parts_str.encode("utf-8"))
    hasher.update(f":circuit_{circuit_id}:version_{race_engine_version}".encode("utf-8"))
    
    return hasher.digest()

def derive_sub_seed(master_seed: bytes, domain: str, extra_key: str = "") -> bytes:
    """
    Derives a domain-separated 32-byte sub-seed using SHA-256.
    Example domains: 'qualifying', 'race', 'variance', 'incident'.
    """
    hasher = hashlib.sha256()
    hasher.update(b"AlgoRacersSubSeed:")
    hasher.update(master_seed)
    hasher.update(f":{domain}:{extra_key}".encode("utf-8"))
    return hasher.digest()

def bytes_to_uniform_float(seed_bytes: bytes, min_val: float, max_val: float) -> float:
    """
    Maps 32-byte cryptographic digest to a uniform floating-point value
    in [min_val, max_val] using the first 8 bytes (64-bit integer) without modulo bias.
    """
    uint64_val = int.from_bytes(seed_bytes[:8], byteorder="big", signed=False)
    # Normalize to [0.0, 1.0)
    normalized = uint64_val / float(2**64 - 1)
    # Scale to [min_val, max_val]
    result = min_val + normalized * (max_val - min_val)
    return round(result, 2)
