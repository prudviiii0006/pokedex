"""
AlgoRacers — Session 18: Merkle Tree Engine & Membership Proofs
Module: crypto/merkle.py
==============================================================
Provides deterministic Merkle tree construction, leaf hashing with domain separation,
proof generation, and cryptographic membership verification.
"""

import hashlib
import json
from typing import List, Dict, Any, Tuple, Optional

LEAF_DOMAIN_PREFIX = b"ALGORACERS_LEAF_V1:"
NODE_DOMAIN_PREFIX = b"ALGORACERS_NODE_V1:"

def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    """Deterministic UTF-8 serialization: sorted keys, compact separators."""
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False
    ).encode("utf-8")

def hash_leaf(record: Dict[str, Any]) -> bytes:
    """Computes SHA-256 leaf hash with domain separation."""
    raw_bytes = canonical_json_bytes(record)
    return hashlib.sha256(LEAF_DOMAIN_PREFIX + raw_bytes).digest()

def hash_node(left_hash: bytes, right_hash: bytes) -> bytes:
    """Computes SHA-256 internal parent node hash with domain separation."""
    return hashlib.sha256(NODE_DOMAIN_PREFIX + left_hash + right_hash).digest()

class MerkleTree:
    def __init__(self, records: List[Dict[str, Any]], key_field: str = "driver_id"):
        self.key_field = key_field
        self.raw_records = self._validate_and_sort(records)
        self.leaves = [hash_leaf(r) for r in self.raw_records]
        self.levels: List[List[bytes]] = []
        if self.leaves:
            self._build_tree()

    def _validate_and_sort(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not records:
            return []

        # Check for duplicates on key_field
        seen_keys = set()
        for r in records:
            k = r.get(self.key_field)
            if k is None:
                raise ValueError(f"Record missing key field '{self.key_field}': {r}")
            if k in seen_keys:
                raise ValueError(f"Duplicate record key detected: '{k}'")
            seen_keys.add(k)

        # Deterministic sorting by key_field ascending
        return sorted(records, key=lambda x: str(x[self.key_field]))

    def _build_tree(self):
        current_level = self.leaves
        self.levels = [current_level]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                    parent = hash_node(left, right)
                else:
                    # Odd leaf promotion scheme: promote unpaired node to next level
                    parent = left
                next_level.append(parent)
            current_level = next_level
            self.levels.append(current_level)

    @property
    def root(self) -> bytes:
        if not self.levels or not self.levels[-1]:
            return b"\x00" * 32
        return self.levels[-1][0]

    @property
    def root_hex(self) -> str:
        return self.root.hex()

    def generate_proof(self, target_key: Any) -> Optional[List[Dict[str, str]]]:
        """
        Generates a cryptographic membership proof for the record with target_key.
        Returns list of {'hash': '<hex>', 'position': 'left' | 'right'}
        """
        target_idx = None
        for i, r in enumerate(self.raw_records):
            if str(r.get(self.key_field)) == str(target_key):
                target_idx = i
                break

        if target_idx is None:
            return None

        proof: List[Dict[str, str]] = []
        idx = target_idx

        for level in self.levels[:-1]:
            is_right_child = (idx % 2 == 1)
            if is_right_child:
                sibling_idx = idx - 1
                sibling_pos = "left"
            else:
                sibling_idx = idx + 1
                sibling_pos = "right"

            if sibling_idx < len(level):
                sibling_hash = level[sibling_idx]
                proof.append({
                    "hash": sibling_hash.hex(),
                    "position": sibling_pos
                })

            idx = idx // 2

        return proof

def verify_merkle_proof(
    record: Dict[str, Any],
    proof: List[Dict[str, str]],
    expected_root_hex: str
) -> bool:
    """
    Independently verifies that record belongs to expected_root_hex using proof.
    Algorithm:
      current = hash_leaf(record)
      for sibling in proof:
          if sibling.position == 'left':
              current = hash_node(sibling.hash, current)
          else:
              current = hash_node(current, sibling.hash)
      return current == expected_root
    """
    try:
        current_hash = hash_leaf(record)

        for elem in proof:
            sibling_hash = bytes.fromhex(elem["hash"])
            pos = elem.get("position", "right")

            if pos == "left":
                current_hash = hash_node(sibling_hash, current_hash)
            elif pos == "right":
                current_hash = hash_node(current_hash, sibling_hash)
            else:
                return False

        return current_hash.hex().lower() == expected_root_hex.lower()
    except Exception:
        return False
