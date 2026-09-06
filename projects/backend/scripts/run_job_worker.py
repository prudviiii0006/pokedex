#!/usr/bin/env python3
"""
AlgoRacers — Session 22: Background Job Worker CLI
Module: backend/scripts/run_job_worker.py
=================================================
Runs a standalone job worker claiming and processing jobs from the queue.
Usage: python run_job_worker.py [--once]
"""

import sys
import time
from pathlib import Path

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.jobs.worker import job_worker
from backend.app.jobs.queue import job_queue

def run_worker(once: bool = False):
    print("=" * 75)
    print("🏎️  ALGORACERS — DURABLE BACKGROUND JOB WORKER")
    print(f"🆔 Worker ID: {job_worker.worker_id}")
    print("=" * 75)

    # First, recover any expired leases
    recovered = job_queue.recover_expired_leases(lease_timeout_seconds=120)
    if recovered > 0:
        print(f"🔄 Recovered {recovered} expired leases from crashed workers.")

    if once:
        executed = job_worker.process_one_job()
        print(f"⚙️ Single job pass completed: {'Processed 1 job' if executed else 'No pending jobs'}")
        return

    print("🚀 Worker listening for jobs (Ctrl+C to stop)...")
    try:
        while True:
            did_work = job_worker.process_one_job()
            if not did_work:
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n🛑 Worker gracefully stopped.")

if __name__ == "__main__":
    run_once = "--once" in sys.argv
    run_worker(run_once)
