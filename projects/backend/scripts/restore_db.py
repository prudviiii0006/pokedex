#!/usr/bin/env python3
"""
Pokédex — Database Restore & Verification CLI
Module: backend/scripts/restore_db.py
============================================================
Restores database from a snapshot and runs verification audits.
Usage: python restore_db.py <backup_path>
"""

import sys
import shutil
import sqlite3
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.core.database import DB_PATH
from backend.app.chain.reconciliation import blockchain_reconciler

def restore_database(backup_path: str):
    print("=" * 75)
    print("⚡  POKÉDEX — DATABASE RESTORE & INTEGRITY AUDITOR")
    print("=" * 75)

    src = Path(backup_path)
    if not src.exists():
        print(f"❌ Backup file not found: {src}")
        sys.exit(1)

    # 1. Restore file
    shutil.copy2(src, DB_PATH)
    print(f"📦 Restored from: {src} ──> {DB_PATH}")

    # 2. Verify table counts
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    tables = [
        "purchases", "races", "tournaments", "seasons", "governance_proposals",
        "chain_events", "jobs", "outbox_events", "race_simulation_batches"
    ]
    print("-" * 75)
    print("📊 TABLE ROW COUNTS POST-RESTORE:")
    for t in tables:
        try:
            cnt = cursor.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
            print(f"  • {t.ljust(25)}: {cnt} rows")
        except Exception as e:
            print(f"  • {t.ljust(25)}: ERROR ({e})")
    conn.close()

    # 3. Run Session 21 Blockchain State Reconciliation
    print("-" * 75)
    print("🔍 RUNNING BLOCKCHAIN STATE RECONCILIATION POST-RESTORE...")
    rep = blockchain_reconciler.run_reconciliation_audit(repair=False)
    print(f"  • Reconciliation Status: [{rep.status}] (NFT Drifts: {rep.nft_drift_count}, Season Drifts: {rep.season_drift_count})")
    print("=" * 75)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_db.py <backup_path>")
        sys.exit(1)
    restore_database(sys.argv[1])
