"""
AlgoRacers — Session 22: Durable PostgreSQL Job Queue
Module: jobs/queue.py
=====================================================
PostgreSQL-backed durable job queue implementing:
  - Atomic job enqueuing
  - Concurrency-safe job claiming via SKIP LOCKED / conditional lock
  - Exponential backoff retries and dead-letter failure states
  - Lease timeout recovery for crashed worker processes
"""

import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from backend.app.core.database import get_db

logger = logging.getLogger("algoracers.jobs.queue")

class JobQueue:
    def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        max_attempts: int = 3,
        delay_seconds: int = 0
    ) -> str:
        """Enqueues a durable background job with an optional execution delay."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        available_at = (now + timedelta(seconds=delay_seconds)).isoformat()
        now_iso = now.isoformat()

        with get_db() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    job_id, job_type, payload_json, status, attempts, max_attempts,
                    available_at, created_at, updated_at
                ) VALUES (?, ?, ?, 'PENDING', 0, ?, ?, ?, ?);
            """, (
                job_id, job_type, json.dumps(payload), max_attempts,
                available_at, now_iso, now_iso
            ))
            conn.commit()

        logger.info(f"📥 Enqueued job #{job_id} [{job_type}] (Available at: {available_at})")
        return job_id

    def enqueue_transactional(
        self,
        conn: Any,
        job_type: str,
        payload: Dict[str, Any],
        max_attempts: int = 3,
        delay_seconds: int = 0
    ) -> str:
        """Enqueues a job inside an existing database transaction."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        available_at = (now + timedelta(seconds=delay_seconds)).isoformat()
        now_iso = now.isoformat()

        conn.execute("""
            INSERT INTO jobs (
                job_id, job_type, payload_json, status, attempts, max_attempts,
                available_at, created_at, updated_at
            ) VALUES (?, ?, ?, 'PENDING', 0, ?, ?, ?, ?);
        """, (
            job_id, job_type, json.dumps(payload), max_attempts,
            available_at, now_iso, now_iso
        ))
        return job_id

    def claim_next_job(self, worker_id: str, lease_seconds: int = 60) -> Optional[Dict[str, Any]]:
        """
        Atomically claims the next available job using optimistic locking / SKIP LOCKED semantics.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with get_db() as conn:
            # Find candidate job
            row = conn.execute("""
                SELECT job_id, job_type, payload_json, attempts, max_attempts 
                FROM jobs 
                WHERE status IN ('PENDING', 'RETRY_PENDING') 
                  AND available_at <= ?
                ORDER BY created_at ASC
                LIMIT 1;
            """, (now_iso,)).fetchone()

            if not row:
                return None

            job_id = row["job_id"]
            # Atomic conditional update claiming the row
            res = conn.execute("""
                UPDATE jobs 
                SET status = 'RUNNING',
                    locked_at = ?,
                    locked_by = ?,
                    attempts = attempts + 1,
                    updated_at = ?
                WHERE job_id = ? AND status IN ('PENDING', 'RETRY_PENDING');
            """, (now_iso, worker_id, now_iso, job_id))

            conn.commit()

            if res.rowcount == 1:
                return {
                    "job_id": job_id,
                    "job_type": row["job_type"],
                    "payload": json.loads(row["payload_json"]),
                    "attempts": row["attempts"] + 1,
                    "max_attempts": row["max_attempts"]
                }

        return None

    def mark_succeeded(self, job_id: str):
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE jobs 
                SET status = 'SUCCEEDED', locked_by = NULL, updated_at = ?
                WHERE job_id = ?;
            """, (now_iso, job_id))
            conn.commit()
        logger.info(f"✅ Job #{job_id} SUCCEEDED")

    def mark_failed(self, job_id: str, error_msg: str, retry_delay_seconds: int = 10):
        now = datetime.now(timezone.utc)
        with get_db() as conn:
            row = conn.execute("SELECT attempts, max_attempts FROM jobs WHERE job_id = ?;", (job_id,)).fetchone()
            if not row:
                return

            attempts = row["attempts"]
            max_attempts = row["max_attempts"]

            if attempts >= max_attempts:
                new_status = "FAILED"
                available_at = now.isoformat()
                logger.error(f"❌ Job #{job_id} permanently FAILED after {attempts}/{max_attempts} attempts: {error_msg}")
            else:
                new_status = "RETRY_PENDING"
                # Exponential backoff: base * (2 ^ attempt)
                backoff_secs = retry_delay_seconds * (2 ** (attempts - 1))
                available_at = (now + timedelta(seconds=backoff_secs)).isoformat()
                logger.warning(f"⚠️ Job #{job_id} scheduled for retry #{attempts + 1} at {available_at} (Error: {error_msg})")

            conn.execute("""
                UPDATE jobs 
                SET status = ?, 
                    last_error = ?, 
                    available_at = ?,
                    locked_by = NULL,
                    updated_at = ?
                WHERE job_id = ?;
            """, (new_status, error_msg, available_at, now.isoformat(), job_id))
            conn.commit()

    def recover_expired_leases(self, lease_timeout_seconds: int = 120) -> int:
        """Recovers stuck RUNNING jobs from dead/crashed worker processes."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=lease_timeout_seconds)).isoformat()
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            res = conn.execute("""
                UPDATE jobs 
                SET status = 'RETRY_PENDING',
                    locked_by = NULL,
                    last_error = 'Lease expired (Worker crash recovery)',
                    updated_at = ?
                WHERE status = 'RUNNING' AND locked_at < ?;
            """, (now_iso, cutoff))
            conn.commit()
            if res.rowcount > 0:
                logger.warning(f"🔄 Recovered {res.rowcount} expired job leases")
            return res.rowcount

job_queue = JobQueue()
