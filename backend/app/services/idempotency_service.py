"""
AlgoRacers — Session 22: Idempotency & Concurrency Service
Module: services/idempotency_service.py
==========================================================
Protects state mutations from concurrent duplicate requests and enforces
safe idempotency keys with request fingerprints.
"""

import json
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple

from backend.app.core.database import get_db

logger = logging.getLogger("algoracers.services.idempotency")

class IdempotencyService:
    def check_or_reserve(
        self,
        idempotency_key: str,
        scope: str,
        wallet_address: Optional[str],
        request_body: Dict[str, Any],
        ttl_seconds: int = 86400
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Atomically checks or reserves an idempotency key.
        Returns:
          - (True, None): Key reserved; proceed with execution.
          - (False, cached_response): Key already executed; return cached response.
        Raises:
          - ValueError: If key was previously used with a different request fingerprint.
        """
        req_hash = hashlib.sha256(json.dumps(request_body, sort_keys=True).encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()

        with get_db() as conn:
            row = conn.execute("""
                SELECT request_hash, response_json, status 
                FROM idempotency_records 
                WHERE idempotency_key = ? AND scope = ?;
            """, (idempotency_key, scope)).fetchone()

            if row:
                if row["request_hash"] != req_hash:
                    raise ValueError(
                        f"Idempotency key '{idempotency_key}' was previously used with different request parameters."
                    )
                if row["status"] == "COMPLETED" and row["response_json"]:
                    return False, json.loads(row["response_json"])
                elif row["status"] == "PROCESSING":
                    # Concurrent duplicate request in progress
                    return False, {"status": "PROCESSING", "message": "Request is already being processed."}

            # Reserve key
            conn.execute("""
                INSERT OR REPLACE INTO idempotency_records (
                    idempotency_key, scope, wallet_address, request_hash, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, 'PROCESSING', ?, ?);
            """, (idempotency_key, scope, wallet_address, req_hash, now_iso, expires_at))
            conn.commit()

        return True, None

    def store_response(
        self,
        idempotency_key: str,
        scope: str,
        response_data: Dict[str, Any]
    ):
        with get_db() as conn:
            conn.execute("""
                UPDATE idempotency_records 
                SET status = 'COMPLETED', response_json = ? 
                WHERE idempotency_key = ? AND scope = ?;
            """, (json.dumps(response_data), idempotency_key, scope))
            conn.commit()

idempotency_service = IdempotencyService()
