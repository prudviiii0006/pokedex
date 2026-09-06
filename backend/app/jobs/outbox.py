"""
AlgoRacers — Session 22: Transactional Outbox Pattern
Module: jobs/outbox.py
=====================================================
Ensures zero message loss between database business state mutations
and background worker job execution.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.app.core.database import get_db
from backend.app.jobs.queue import job_queue

logger = logging.getLogger("algoracers.jobs.outbox")

class TransactionalOutbox:
    def record_event(
        self,
        conn: Any,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any]
    ) -> str:
        """
        Inserts an outbox event within the caller's active database transaction.
        """
        outbox_id = f"outbox_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        conn.execute("""
            INSERT INTO outbox_events (
                outbox_id, event_type, aggregate_type, aggregate_id,
                payload_json, status, created_at
            ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?);
        """, (
            outbox_id, event_type, aggregate_type, aggregate_id,
            json.dumps(payload), now_iso
        ))
        return outbox_id

    def dispatch_pending(self, limit: int = 50) -> int:
        """
        Polls un-dispatched outbox events and enqueues them into durable jobs.
        """
        dispatched_count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            rows = conn.execute("""
                SELECT outbox_id, event_type, aggregate_type, aggregate_id, payload_json
                FROM outbox_events
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?;
            """, (limit,)).fetchall()

            for r in rows:
                outbox_id = r["outbox_id"]
                event_type = r["event_type"]
                payload = json.loads(r["payload_json"])

                # Enqueue corresponding durable job
                job_queue.enqueue(
                    job_type=event_type,
                    payload=payload,
                    max_attempts=3
                )

                # Mark outbox event as DISPATCHED
                conn.execute("""
                    UPDATE outbox_events
                    SET status = 'DISPATCHED', dispatched_at = ?
                    WHERE outbox_id = ?;
                """, (now_iso, outbox_id))
                dispatched_count += 1

            conn.commit()

        if dispatched_count > 0:
            logger.info(f"📤 Dispatched {dispatched_count} transactional outbox events into job queue")
        return dispatched_count

transactional_outbox = TransactionalOutbox()
