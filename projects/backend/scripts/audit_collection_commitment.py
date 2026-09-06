#!/usr/bin/env python3
"""
AlgoRacers — Session 18: Full Collection Commitment Auditor
Module: backend/scripts/audit_collection_commitment.py
======================================================
Audits the complete collection dataset, rebuilds the Merkle tree from scratch,
and verifies membership proofs for all drivers against the root.
Usage: python audit_collection_commitment.py
"""

import sys
import json
from pathlib import Path

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.crypto.merkle import MerkleTree, verify_merkle_proof

MANIFEST_PATH = root_dir / "blockchain" / "metadata" / "manifest.json"

def audit_collection():
    print("=" * 75)
    print("🏎️  ALGORACERS — FULL COLLECTION COMMITMENT AUDITOR")
    print("=" * 75)

    if not MANIFEST_PATH.exists():
        print(f"❌ Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    expected_root = manifest.get("collection_root")
    drivers = manifest.get("drivers", {})

    print(f"📋 COLLECTION SPECIFICATIONS:")
    print(f"  • Collection:       {manifest.get('collection_name')}")
    print(f"  • Version:          v{manifest.get('collection_version')}")
    print(f"  • Leaf Count:       {len(drivers)} Drivers")
    print(f"  • Manifest Root:    {expected_root}")
    print("-" * 75)

    # 1. Build canonical records
    records = []
    for k, v in sorted(drivers.items()):
        records.append({
            "driver_id": v["driver_id"],
            "driver_name": v["driver_name"],
            "rarity": v["rarity"],
            "metadata_cid": v["metadata_cid"],
            "image_cid": v["image_cid"],
            "sha256_hash": v["sha256_hash"]
        })

    # 2. Rebuild Merkle Tree from scratch
    rebuilt_tree = MerkleTree(records, key_field="driver_id")
    rebuilt_root = rebuilt_tree.root_hex

    if rebuilt_root.lower() != expected_root.lower():
        print(f"🚨 ROOT MISMATCH: Rebuilt {rebuilt_root} != Expected {expected_root}")
        sys.exit(1)

    print(f"✅ Root Rebuilt from Scratch: {rebuilt_root} [MATCH]")
    print("-" * 75)
    print(f"🧪 Auditing Individual Driver Membership Proofs:")

    # 3. Test proof verification for every driver
    for r in records:
        d_id = r["driver_id"]
        proof = rebuilt_tree.generate_proof(d_id)
        is_valid = verify_merkle_proof(r, proof, rebuilt_root)

        status_str = "PASS" if is_valid else "FAIL"
        print(f"  • Driver #{d_id:<3} [{r['rarity']:9}] | Proof Steps: {len(proof)} | Audit: [{status_str}]")
        if not is_valid:
            print(f"❌ Proof verification failed for Driver #{d_id}")
            sys.exit(1)

    print("=" * 75)
    print(f"🏆 AUDIT RESULT: [PASS] ALL {len(records)} DRIVERS 100% VERIFIED AGAINST MERKLE ROOT")
    print("=" * 75)

if __name__ == "__main__":
    audit_collection()
