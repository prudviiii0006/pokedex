"""
AlgoRacers — Session 23: In-Memory Sliding Window Rate Limiter
Module: core/rate_limiter.py
==============================================================
Provides tiered per-IP and per-Wallet sliding-window rate limiting
with automatic cleanup, Retry-After headers, and FastAPI dependency integration.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple
from fastapi import Request, HTTPException, status, Depends
from backend.app.core.security import get_optional_wallet

logger = logging.getLogger("algoracers.security.ratelimit")

class SlidingWindowRateLimiter:
    def __init__(self):
        # Maps key (e.g. "ip:127.0.0.1:auth") -> list of epoch timestamps
        self._windows: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()

    def _cleanup_stale(self, window_seconds: int = 3600):
        """Purges entries older than window_seconds."""
        now = time.time()
        if now - self._last_cleanup < 60:
            return

        cutoff = now - window_seconds
        keys_to_delete = []
        for k, timestamps in self._windows.items():
            self._windows[k] = [t for t in timestamps if t > cutoff]
            if not self._windows[k]:
                keys_to_delete.append(k)

        for k in keys_to_delete:
            del self._windows[k]
        self._last_cleanup = now

    def check_rate_limit(
        self,
        identifier: str,
        scope: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int]:
        """
        Evaluates whether the given identifier has exceeded max_requests in window_seconds.
        Returns:
          - (True, remaining_requests) if allowed
          - (False, retry_after_seconds) if rate limited
        """
        now = time.time()
        self._cleanup_stale()
        key = f"{scope}:{identifier}"

        timestamps = self._windows.get(key, [])
        cutoff = now - window_seconds

        # Keep only timestamps within current window
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= max_requests:
            oldest_in_window = valid_timestamps[0]
            retry_after = max(1, int(oldest_in_window + window_seconds - now))
            logger.warning(f"🚨 Rate limit EXCEEDED for '{key}': {len(valid_timestamps)}/{max_requests} reqs. Retry-After: {retry_after}s")
            return False, retry_after

        # Record this request
        valid_timestamps.append(now)
        self._windows[key] = valid_timestamps
        remaining = max_requests - len(valid_timestamps)
        return True, remaining

rate_limiter = SlidingWindowRateLimiter()

def rate_limit(
    max_requests: int,
    window_seconds: int = 60,
    scope: str = "default",
    by_wallet: bool = False
):
    """
    FastAPI dependency factory enforcing rate limits.
    """
    async def dependency(
        request: Request,
        wallet: Optional[str] = Depends(get_optional_wallet)
    ):
        # Use wallet address if present and requested, otherwise client IP
        if by_wallet and wallet:
            ident = f"wallet:{wallet}"
        else:
            client_ip = request.client.host if request.client else "unknown_ip"
            ident = f"ip:{client_ip}"

        allowed, retry_or_remaining = rate_limiter.check_rate_limit(
            identifier=ident,
            scope=scope,
            max_requests=max_requests,
            window_seconds=window_seconds
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for scope '{scope}'. Maximum {max_requests} requests per {window_seconds}s.",
                headers={"Retry-After": str(retry_or_remaining)}
            )

    return dependency
