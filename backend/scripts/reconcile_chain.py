#!/usr/bin/env python3
"""
AlgoRacers — Session 21: Blockchain State Reconciliation CLI
Module: backend/scripts/reconcile_chain.py
=========================================================
Compares cached SQLite database state against on-chain Algorand Layer-1 truth.
Usage: python reconcile_chain.py [--repair]
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.chain.reconciliation import blockchain_reconciler

def run_reconciliation(repair: bool = False):
    print("=" * 75)
    print("🏎️  ALGORACERS — BLOCKCHAIN STATE RECONCILER & AUDITOR")
    print(f"🔧 Mode: {'REPAIR & RECONCILE' if repair else 'AUDIT / REPORT ONLY'}")
    print("=" * 75)

    report = blockchain_reconciler.run_reconciliation_audit(repair=repair)

    print(f"📊 RECONCILIATION AUDIT RESULTS:")
    print(f"  • Timestamp:                {report.audited_at}")
    print(f"  • NFT Ownership Drift:      {report.nft_drift_count}")
    print(f"  • Season Root Drift:        {report.season_drift_count}")
    print(f"  • Tournament State Drift:   {report.tournament_drift_count}")
    print(f"  • Overall Status:           [{report.status}]")
    print("-" * 75)
    print("📋 AUDIT LOG:")
    for d in report.details:
        print(f"  {d}")
    print("=" * 75)

if __name__ == "__main__":
    should_repair = "--repair" in sys.argv
    run_reconciliation(should_repair)
