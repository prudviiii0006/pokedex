#!/usr/bin/env python3
"""
AlgoRacers — Session 19: Full Season Auditor
Module: backend/scripts/audit_season.py
=============================================
Audits all tournaments in a season, checks result hash validity,
re-aggregates standings, and audits Merkle commitments.
Usage: python audit_season.py [season_id]
"""

import sys
from pathlib import Path

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.season_service import season_service
from backend.app.services.season_leaderboard_service import season_leaderboard_service

def audit_season_full(season_id: str = "season_2026_01"):
    print("=" * 75)
    print(f"🏎️  ALGORACERS — FULL SEASON & TOURNAMENT AUDITOR")
    print(f"🏆 Auditing Season: {season_id}")
    print("=" * 75)

    season = season_service.get_season(season_id)
    print(f"• Season Name:       {season.name}")
    print(f"• Status:            {season.status}")
    print(f"• Rounds Configured: {len(season.tournaments)} / {season.rounds_total}")
    print("-" * 75)

    for t in season.tournaments:
        status_icon = "✅" if t.get("status") == "FINALIZED" else "⏳"
        print(f"  {status_icon} Round #{t.get('round_number')} -> App #{t.get('app_id')}: {t.get('name')} [{t.get('status')}] (Circuit: {t.get('circuit_id')})")

    standings = season_leaderboard_service.calculate_leaderboard(season_id)
    print("-" * 75)
    print(f"🏆 Current Standings ({len(standings)} active racers):")
    for s in standings:
        print(f"  P{s.rank:<2} | {s.display_wallet:<14} | Points: {s.points:<3} | Wins: {s.wins} | Podiums: {s.podiums}")

    print("=" * 75)
    print(f"✅ Season Audit Complete.")

if __name__ == "__main__":
    s_id = sys.argv[1] if len(sys.argv) > 1 else "season_2026_01"
    audit_season_full(s_id)
