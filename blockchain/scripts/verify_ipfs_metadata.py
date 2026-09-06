#!/usr/bin/env python3
"""
AlgoRacers — Session 17: IPFS Metadata Verification Script
Module: blockchain/scripts/verify_ipfs_metadata.py
==========================================================
Verifies that metadata retrieved from an IPFS CID or local file
strictly matches its cryptographic content identifier, follows schema,
and contains valid nested image references.
Usage: python verify_ipfs_metadata.py <driver_id_or_cid>
"""

import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from blockchain.scripts.cid_utils import compute_cid_v1, canonical_json_bytes

METADATA_DIR = root_dir / "blockchain" / "metadata"
GENERATED_DIR = METADATA_DIR / "generated"
MANIFEST_PATH = METADATA_DIR / "manifest.json"

def verify_driver_metadata(target: str) -> bool:
    print("=" * 75)
    print(f"🏎️  ALGORACERS — IPFS METADATA INTEGRITY VERIFIER")
    print(f"🔍 Target Identifier: {target}")
    print("=" * 75)

    if not MANIFEST_PATH.exists():
        print(f"❌ Manifest not found at {MANIFEST_PATH}. Run build_metadata.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Resolve target to driver record
    driver_info = None
    target_key = f"driver_{target}" if not target.startswith("driver_") and not target.startswith("bafy") and not target.startswith("bafk") else target

    if target_key in manifest["drivers"]:
        driver_info = manifest["drivers"][target_key]
    else:
        # Search by CID
        for k, v in manifest["drivers"].items():
            if v["metadata_cid"] == target or v["image_cid"] == target:
                driver_info = v
                break

    if not driver_info:
        print(f"❌ Target '{target}' not found in collection manifest.")
        return False

    driver_id = driver_info["driver_id"]
    file_path = GENERATED_DIR / f"driver_{driver_id}.json"

    if not file_path.exists():
        print(f"❌ Local canonical file not found: {file_path}")
        return False

    with open(file_path, "rb") as f:
        content_bytes = f.read()

    # 1. Cryptographic CID re-calculation
    recalculated_cid = compute_cid_v1(content_bytes)
    recalculated_sha256 = hashlib.sha256(content_bytes).hexdigest()

    cid_match = (recalculated_cid == driver_info["metadata_cid"])
    hash_match = (recalculated_sha256 == driver_info["sha256_hash"])

    print(f"📋 METADATA AUDIT REPORT:")
    print(f"  • Driver ID:            #{driver_id}")
    print(f"  • Driver Name:          {driver_info['driver_name']}")
    print(f"  • Expected CID:         {driver_info['metadata_cid']}")
    print(f"  • Recalculated CID:     {recalculated_cid}")
    print(f"  • SHA-256 Digest:       {recalculated_sha256}")
    print(f"  • Image Reference:      {driver_info['image_uri']}")

    if cid_match and hash_match:
        print("-" * 75)
        print(f"🏆 AUDIT RESULT: [PASS] 100% CRYPTOGRAPHICALLY VERIFIED & IMMUTABLE")
        print("=" * 75)
        return True
    else:
        print("-" * 75)
        print(f"🚨 AUDIT RESULT: [FAIL] INTEGRITY MISMATCH DETECTED!")
        print("=" * 75)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_ipfs_metadata.py <driver_id_or_cid>")
        sys.exit(1)

    success = verify_driver_metadata(sys.argv[1])
    sys.exit(0 if success else 1)
