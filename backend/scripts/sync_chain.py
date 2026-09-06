#!/usr/bin/env python3
"""
AlgoRacers — Session 21: Blockchain Synchronization CLI
Module: backend/scripts/sync_chain.py
=====================================================
Polls the Algorand Indexer/Algod and processes new blocks
advancing the subscriber checkpoint and updating database projections.
Usage: python sync_chain.py [max_rounds]
"""

import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from backend.app.chain.subscriber import chain_subscriber

def run_sync(max_rounds: int = 50):
    print("=" * 75)
    print("🏎️  ALGORACERS — BLOCKCHAIN SUBSCRIBER & SYNCHRONIZER")
    print("=" * 75)

    status_before = chain_subscriber.get_sync_status()
    print(f"📊 BEFORE SYNC:")
    print(f"  • Algod Current Round:      #{status_before.algod_round}")
    print(f"  • Indexer Processed Round:  #{status_before.indexer_round}")
    print(f"  • Subscriber Checkpoint:    #{status_before.checkpoint_round}")
    print(f"  • Indexer Lag:              {status_before.indexer_lag_rounds} rounds")
    print(f"  • Subscriber Lag:           {status_before.subscriber_lag_rounds} rounds")
    print("-" * 75)

    res = chain_subscriber.run_sync_batch(max_rounds=max_rounds)

    status_after = chain_subscriber.get_sync_status()
    print(f"✅ SYNC BATCH COMPLETE:")
    print(f"  • Range Processed:          #{res['start_round']} ──> #{res['end_round']}")
    print(f"  • Rounds Advanced:          +{res['rounds_advanced']}")
    print(f"  • New Checkpoint:           #{status_after.checkpoint_round}")
    print(f"  • Total Events Logged:      {status_after.events_processed_total}")
    print("=" * 75)

if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    run_sync(rounds)
