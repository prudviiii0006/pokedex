#!/usr/bin/env python3
"""
AlgoRacers — Session 18: Standalone Merkle Proof Verifier CLI
Module: backend/scripts/verify_merkle_proof.py
=============================================================
Independently verifies that an individual driver record is cryptographically
included in the on-chain committed collection root.
Usage: python verify_merkle_proof.py <driver_id> [collection_id] [version] [api_url]
"""

import sys
import json
import hashlib
from typing import Dict, Any, List
try:
    import httpx
except ImportError:
    print("Error: 'httpx' required. Run 'pip install httpx'.")
    sys.exit(1)

LEAF_DOMAIN_PREFIX = b"ALGORACERS_LEAF_V1:"
NODE_DOMAIN_PREFIX = b"ALGORACERS_NODE_V1:"

def canonical_json_bytes(data: Dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def hash_leaf(record: Dict[str, Any]) -> bytes:
    return hashlib.sha256(LEAF_DOMAIN_PREFIX + canonical_json_bytes(record)).digest()

def hash_node(left_hash: bytes, right_hash: bytes) -> bytes:
    return hashlib.sha256(NODE_DOMAIN_PREFIX + left_hash + right_hash).digest()

def verify_proof_cli(
    driver_id: str,
    collection_id: str = "drivers",
    version: int = 1,
    api_url: str = "http://localhost:8000"
):
    print("=" * 75)
    print(f"🏎️  ALGORACERS — INDEPENDENT MERKLE MEMBERSHIP PROOF AUDITOR")
    print(f"🔍 Driver ID: {driver_id} | Collection: {collection_id} (v{version})")
    print("=" * 75)

    clean_id = driver_id.replace("driver_", "")

    try:
        res = httpx.get(f"{api_url}/collections/{collection_id}/{version}/drivers/{clean_id}/proof", timeout=10.0)
        if res.status_code != 200:
            print(f"❌ Error fetching proof: HTTP {res.status_code} - {res.text}")
            sys.exit(1)

        data = res.json()
        record = data["record"]
        proof = data["proof"]
        expected_root = data["root"]

        print(f"📋 RECORD IDENTIFIERS:")
        print(f"  • Driver ID:        #{record.get('driver_id')}")
        print(f"  • Driver Name:      {record.get('driver_name')}")
        print(f"  • Rarity:           {record.get('rarity')}")
        print(f"  • Metadata CID:     {record.get('metadata_cid')}")
        print("-" * 75)

        # 1. Compute leaf hash
        current_hash = hash_leaf(record)
        print(f"🌿 Leaf Hash:         {current_hash.hex()}")
        print(f"🪜 Proof Path ({len(proof)} steps):")

        # 2. Iterate through proof path
        for i, step in enumerate(proof, 1):
            sibling_hash = bytes.fromhex(step["hash"])
            pos = step["position"]
            if pos == "left":
                current_hash = hash_node(sibling_hash, current_hash)
                print(f"  [Step {i}] H(Node_{i} [LEFT] || Current) -> {current_hash.hex()[:24]}...")
            else:
                current_hash = hash_node(current_hash, sibling_hash)
                print(f"  [Step {i}] H(Current || Node_{i} [RIGHT]) -> {current_hash.hex()[:24]}...")

        calculated_root = current_hash.hex()
        is_match = (calculated_root.lower() == expected_root.lower())

        print("-" * 75)
        print(f"🔐 Calculated Root:   {calculated_root}")
        print(f"⛓️  Committed Root:    {expected_root}")
        print("-" * 75)

        if is_match:
            print(f"🏆 AUDIT RESULT: [PASS] CRYPTOGRAPHIC MEMBERSHIP 100% VERIFIED")
            print("=" * 75)
            return True
        else:
            print(f"🚨 AUDIT RESULT: [FAIL] ROOT MISMATCH DETECTED!")
            print("=" * 75)
            return False

    except Exception as e:
        print(f"❌ Error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_merkle_proof.py <driver_id> [collection_id] [version] [api_url]")
        sys.exit(1)

    target_driver = sys.argv[1]
    col = sys.argv[2] if len(sys.argv) > 2 else "drivers"
    ver = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    api = sys.argv[4] if len(sys.argv) > 4 else "http://localhost:8000"

    success = verify_proof_cli(target_driver, col, ver, api)
    sys.exit(0 if success else 1)
