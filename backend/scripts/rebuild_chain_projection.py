#!/usr/bin/env python3
"""
AlgoRacers — Session 21: Historical Projection Rebuilder CLI
Module: backend/scripts/rebuild_chain_projection.py
===========================================================
Reconstructs blockchain-derived database tables by replaying
stored historical chain events in strict round sequence.
Usage: python rebuild_chain_projection.py
"""

import sys
import json
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import get_db

def rebuild_projections():
    print("=" * 75)
    print("🏎️  ALGORACERS — HISTORICAL CHAIN PROJECTION REBUILDER")
    print("=" * 75)

    with get_db() as conn:
        events = conn.execute("""
            SELECT * FROM chain_events
            ORDER BY round_number ASC, created_at ASC;
        """).fetchall()

    print(f"📦 Total Stored Chain Events: {len(events)}")
    print("-" * 75)

    replayed = 0
    with get_db() as conn:
        for ev in events:
            e_type = ev["event_type"]
            app_id = ev["app_id"]

            if e_type == "TOURNAMENT_FINALIZED" and app_id:
                conn.execute("UPDATE tournaments SET status = 'FINALIZED' WHERE app_id = ?;", (app_id,))
                replayed += 1
            elif e_type == "SEASON_FINALIZED" and app_id:
                conn.execute("UPDATE seasons SET status = 'FINALIZED' WHERE app_id = ?;", (app_id,))
                replayed += 1

        conn.commit()

    print(f"✅ Replayed {replayed} state transitions successfully.")
    print("=" * 75)

if __name__ == "__main__":
    rebuild_projections()
