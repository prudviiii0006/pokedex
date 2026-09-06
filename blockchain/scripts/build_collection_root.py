#!/usr/bin/env python3
"""
AlgoRacers — Session 18: Driver Collection Root & Test Vector Generator
Module: blockchain/scripts/build_collection_root.py
========================================================================
Builds the canonical Merkle tree over the AlgoRacers Genesis Driver collection,
updates manifest.json with the Merkle root, and exports cross-language test vectors.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.crypto.merkle import MerkleTree, hash_leaf, verify_merkle_proof

MANIFEST_PATH = root_dir / "blockchain" / "metadata" / "manifest.json"
TEST_VECTORS_PATH = root_dir / "docs" / "merkle-test-vectors.json"

def build_collection_root():
    print("=" * 75)
    print("🏎️  ALGORACERS — DRIVER COLLECTION MERKLE ROOT BUILDER")
    print("=" * 75)

    if not MANIFEST_PATH.exists():
        print(f"❌ Manifest not found at {MANIFEST_PATH}. Run build_metadata.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # 1. Format canonical leaf records
    driver_records: List[Dict[str, Any]] = []
    for k, v in sorted(manifest["drivers"].items()):
        driver_records.append({
            "driver_id": v["driver_id"],
            "driver_name": v["driver_name"],
            "rarity": v["rarity"],
            "metadata_cid": v["metadata_cid"],
            "image_cid": v["image_cid"],
            "sha256_hash": v["sha256_hash"]
        })

    # 2. Construct Merkle Tree
    tree = MerkleTree(driver_records, key_field="driver_id")
    root_hex = tree.root_hex

    print(f"🌳 Merkle Tree Built Successfully:")
    print(f"  • Collection:       {manifest.get('collection_name', 'AlgoRacers Drivers')}")
    print(f"  • Leaf Count:        {len(driver_records)} Drivers")
    print(f"  • Tree Depth:        {len(tree.levels)} Levels")
    print(f"  • Tree Scheme:       Domain-Separated SHA-256 (RFC 6962 Promotion)")
    print(f"  • MERKLE ROOT:       {root_hex}")
    print("-" * 75)

    # 3. Update manifest.json
    manifest["collection_version"] = 1
    manifest["collection_root"] = root_hex
    manifest["leaf_count"] = len(driver_records)
    manifest["tree_scheme"] = "ALGORACERS_LEAF_NODE_V1"
    manifest["canonical_records"] = driver_records

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f_man:
        json.dump(manifest, f_man, indent=2)

    # 4. Generate Test Vectors for Cross-Language Verification (Python, TypeScript, TEAL)
    sample_driver = "001"
    sample_record = next(r for r in driver_records if r["driver_id"] == sample_driver)
    sample_proof = tree.generate_proof(sample_driver)
    sample_leaf_hash = hash_leaf(sample_record).hex()

    # Self-verify sample proof
    assert verify_merkle_proof(sample_record, sample_proof, root_hex) is True

    test_vectors = {
        "description": "AlgoRacers Session 18 Merkle Proof Test Vectors",
        "hash_algorithm": "SHA-256",
        "leaf_domain_prefix": "ALGORACERS_LEAF_V1:",
        "node_domain_prefix": "ALGORACERS_NODE_V1:",
        "collection_version": 1,
        "collection_root": root_hex,
        "leaf_count": len(driver_records),
        "sample_proof_driver_001": {
            "record": sample_record,
            "leaf_hash": sample_leaf_hash,
            "proof": sample_proof,
            "expected_root": root_hex
        },
        "all_driver_proofs": {
            r["driver_id"]: {
                "record": r,
                "leaf_hash": hash_leaf(r).hex(),
                "proof": tree.generate_proof(r["driver_id"])
            }
            for r in driver_records
        }
    }

    TEST_VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TEST_VECTORS_PATH, "w", encoding="utf-8") as f_vec:
        json.dump(test_vectors, f_vec, indent=2)

    print(f"✅ Updated Collection Manifest: {MANIFEST_PATH}")
    print(f"📜 Exported Cross-Language Test Vectors: {TEST_VECTORS_PATH}")
    print("=" * 75)
    return root_hex

if __name__ == "__main__":
    build_collection_root()
