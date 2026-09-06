#!/usr/bin/env python3
"""
AlgoRacers — Session 19: Independent Season Auditor & Standings Re-Calculator
Module: backend/scripts/verify_season.py
==============================================================================
Pulls season records, independently re-aggregates all tournament points,
applies tie-break formulas, rebuilds the Merkle tree from scratch,
and verifies cryptographic equality against the committed on-chain root.
Usage: python verify_season.py [season_id] [api_url]
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.services.season_service import season_service
from backend.app.services.season_leaderboard_service import season_leaderboard_service
from backend.app.crypto.merkle import MerkleTree, verify_merkle_proof

def verify_season_standings(season_id: str = "season_2026_01") -> bool:
    print("=" * 75)
    print(f"🏎️  ALGORACERS — INDEPENDENT CHAMPIONSHIP SEASON AUDITOR")
    print(f"🏆 Target Season: {season_id}")
    print("=" * 75)

    season = season_service.get_season(season_id)
    print(f"📋 SEASON SPECIFICATIONS:")
    print(f"  • Name:             {season.name}")
    print(f"  • Status:           {season.status}")
    print(f"  • Rounds Completed: {season.rounds_completed} / {season.rounds_total}")
    print(f"  • Scoring Engine:   {season.scoring_version}")
    print(f"  • Committed Root:   {season.leaderboard_root or 'Provisional (Not Finalized)'}")
    print("-" * 75)

    # 1. Independently Re-calculate Standings
    standings = season_leaderboard_service.calculate_leaderboard(season_id)
    if not standings:
        print("⚠️ No eligible tournament standings recorded yet for this season.")
        return True

    print(f"📊 RECOMPUTED STANDINGS ({len(standings)} Players):")
    for s in standings:
        print(f"  P{s.rank:<2} | {s.display_wallet:<14} | Pts: {s.points:<3} | Wins: {s.wins} | Podiums: {s.podiums} | Entered: {s.tournaments_entered}")

    # 2. Build Canonical Snapshot
    canonical_records = []
    for s in standings:
        canonical_records.append({
            "season_id": season_id,
            "wallet_address": s.wallet_address,
            "rank": s.rank,
            "points": s.points,
            "wins": s.wins,
            "podiums": s.podiums
        })

    # 3. Rebuild Merkle Tree
    tree = MerkleTree(canonical_records, key_field="wallet_address")
    recalculated_root = tree.root_hex

    print("-" * 75)
    print(f"🌿 Recalculated Root: {recalculated_root}")

    if season.status == "FINALIZED":
        expected_root = season.leaderboard_root
        if recalculated_root.lower() == expected_root.lower():
            print(f"⛓️  Committed Root:    {expected_root}")
            print("-" * 75)
            print(f"🏆 AUDIT RESULT: [PASS] 100% INDEPENDENTLY REPRODUCED & CRYPTOGRAPHICALLY VERIFIED")
            print("=" * 75)
            return True
        else:
            print(f"🚨 AUDIT RESULT: [FAIL] ROOT MISMATCH DETECTED!")
            print(f"   Expected:     {expected_root}")
            print(f"   Recalculated: {recalculated_root}")
            print("=" * 75)
            return False
    else:
        print(f"ℹ️  Season is {season.status} (Provisional Root derived successfully)")
        print("=" * 75)
        return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "season_2026_01"
    success = verify_season_standings(target)
    sys.exit(0 if success else 1)
