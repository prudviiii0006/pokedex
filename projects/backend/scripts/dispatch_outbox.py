#!/usr/bin/env python3
"""
AlgoRacers — Session 22: Transactional Outbox Dispatcher CLI
Module: backend/scripts/dispatch_outbox.py
===========================================================
Flushes un-dispatched outbox events into the durable job queue.
Usage: python dispatch_outbox.py [--once]
"""

import sys
import time
from pathlib import Path

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.jobs.outbox import transactional_outbox

def run_outbox_dispatcher(once: bool = False):
    print("=" * 75)
    print("🏎️  ALGORACERS — TRANSACTIONAL OUTBOX DISPATCHER")
    print("=" * 75)

    if once:
        count = transactional_outbox.dispatch_pending()
        print(f"📤 Flushed {count} outbox events into the durable job queue.")
        return

    print("🚀 Outbox dispatcher running (Ctrl+C to stop)...")
    try:
        while True:
            count = transactional_outbox.dispatch_pending()
            if count == 0:
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n🛑 Outbox dispatcher gracefully stopped.")

if __name__ == "__main__":
    run_once = "--once" in sys.argv
    run_outbox_dispatcher(run_once)
