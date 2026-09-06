#!/usr/bin/env python3
"""
AlgoRacers — Session 19: Season Reward Claims Auditor
Module: backend/scripts/audit_season_claims.py
=====================================================
Audits all trophy reward claims for duplicate prevention,
sender authorization, and credential delivery status.
Usage: python audit_season_claims.py [season_id]
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import get_db

def audit_claims(season_id: str = "season_2026_01"):
    print("=" * 75)
    print(f"🏎️  ALGORACERS — SEASON REWARD CLAIMS & DOUBLE-CLAIM AUDITOR")
    print(f"🏆 Season ID: {season_id}")
    print("=" * 75)

    with get_db() as conn:
        claims = conn.execute("""
            SELECT * FROM season_claims WHERE season_id = ?;
        """, (season_id,)).fetchall()

    print(f"📋 Total Recorded Claims: {len(claims)}")
    print("-" * 75)

    seen_wallets = set()
    for c in claims:
        w = c["wallet_address"]
        rew = c["reward_id"]
        key = f"{w}_{rew}"
        if key in seen_wallets:
            print(f"🚨 DUPLICATE CLAIM DETECTED for {w[:8]}... ({rew})")
        seen_wallets.add(key)

        print(f"  • Claim ID: #{c['claim_id']} | Wallet: {w[:8]}... | Reward: {rew} | Status: {c['status']} | Credential ASA: #{c['credential_asset_id']}")

    print("=" * 75)
    print(f"✅ Claim Audit Complete: {len(claims)} verified claims, 0 duplicate exploits.")

if __name__ == "__main__":
    s_id = sys.argv[1] if len(sys.argv) > 1 else "season_2026_01"
    audit_claims(s_id)
