"""
Pokédex — Safe Cache-Aside Engine
Module: core/cache.py
=================================================
Implements safe cache-aside pattern for immutable IPFS metadata,
static configurations, and verified game collections with automatic DB fallback.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Callable

from backend.app.core.database import get_db

logger = logging.getLogger("pokedex.core.cache")

class SafeCache:
    def get_or_set(
        self,
        cache_key: str,
        getter_fn: Callable[[], Any],
        ttl_seconds: int = 3600,
        is_immutable: bool = False
    ) -> Any:
        """
        Retrieves cached value or executes getter_fn and populates cache.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with get_db() as conn:
            row = conn.execute("""
                SELECT cache_value, expires_at, is_immutable
                FROM cache_entries
                WHERE cache_key = ?;
            """, (cache_key,)).fetchone()

            if row:
                exp = row["expires_at"]
                if row["is_immutable"] or (exp and exp > now_iso):
                    logger.debug(f"⚡ Cache HIT: {cache_key}")
                    return json.loads(row["cache_value"])

        # Cache MISS
        logger.debug(f"🔍 Cache MISS: {cache_key} -> fetching from source")
        val = getter_fn()
        if val is None:
            return None

        val_json = json.dumps(val)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat() if not is_immutable else None

        with get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries (
                    cache_key, cache_value, is_immutable, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?);
            """, (cache_key, val_json, 1 if is_immutable else 0, expires_at, now_iso))
            conn.commit()

        return val

    def invalidate(self, cache_key: str):
        with get_db() as conn:
            conn.execute("DELETE FROM cache_entries WHERE cache_key = ?;", (cache_key,))
            conn.commit()
        logger.info(f"🗑️ Invalidated cache key: {cache_key}")

    def invalidate_prefix(self, prefix: str):
        with get_db() as conn:
            conn.execute("DELETE FROM cache_entries WHERE cache_key LIKE ?;", (f"{prefix}%",))
            conn.commit()
        logger.info(f"🗑️ Invalidated cache prefix: {prefix}*")

safe_cache = SafeCache()
