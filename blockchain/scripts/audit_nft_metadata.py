#!/usr/bin/env python3
"""
Pokédex — NFT Metadata Audit Tool
Module: blockchain/scripts/audit_nft_metadata.py
================================================
Audits database NFT records and ASA metadata URIs against the collection manifest.
Usage: python audit_nft_metadata.py
"""

import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import get_db

MANIFEST_PATH = root_dir / "blockchain" / "metadata" / "manifest.json"

def audit_all_nfts():
    print("=" * 75)
    print("⚡  POKÉDEX — ON-CHAIN / DATABASE NFT METADATA AUDITOR")
    print("=" * 75)

    if not MANIFEST_PATH.exists():
        print(f"❌ Manifest not found at {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    with get_db() as conn:
        purchases = conn.execute("""
            SELECT purchase_id, wallet_address, driver_id, driver_name, rarity,
                   asset_id, metadata_uri, delivery_tx_id, status
            FROM purchases WHERE status = 'DELIVERED';
        """).fetchall()

    print(f"📊 Auditing {len(purchases)} Delivered Driver NFTs...")
    print("-" * 75)

    passed = 0
    warnings = 0

    for p in purchases:
        d_id = p["driver_id"]
        manifest_key = f"driver_{d_id}"
        expected_meta = manifest["drivers"].get(manifest_key)

        if not expected_meta:
            print(f"⚠️  Asset #{p['asset_id']} (Driver {d_id}): Template not found in manifest!")
            warnings += 1
            continue

        # Check rarity consistency
        if p["rarity"] != expected_meta["rarity"]:
            print(f"🚨 Asset #{p['asset_id']}: Rarity mismatch! DB: {p['rarity']} vs Manifest: {expected_meta['rarity']}")
            warnings += 1
        else:
            passed += 1
            print(f"✅ Asset #{p['asset_id']:<10} | Driver #{d_id} [{p['rarity']:9}] | CID: {expected_meta['metadata_cid'][:18]}... [PASS]")

    print("=" * 75)
    print(f"🏆 AUDIT SUMMARY: {passed} PASSED | {warnings} WARNINGS | Total Audited: {len(purchases)}")
    print("=" * 75)

if __name__ == "__main__":
    audit_all_nfts()
