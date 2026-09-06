"""
AlgoRacers — Session 16: Competitive Reputation Service
Module: services/reputation_service.py
======================================================
Manages competitive Elo rating for verified on-chain tournaments.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from backend.app.core.database import get_db

logger = logging.getLogger("algoracers.reputation")

RANK_TIERS = [
    (1400, "Master"),
    (1200, "Diamond"),
    (1100, "Platinum"),
    (1000, "Gold"),
    (900, "Silver"),
    (0, "Bronze")
]

class ReputationService:
    def get_rank_tier(self, score: int) -> str:
        for threshold, tier in RANK_TIERS:
            if score >= threshold:
                return tier
        return "Bronze"

    def get_reputation(self, wallet_address: str) -> int:
        with get_db() as conn:
            row = conn.execute("SELECT reputation_score FROM player_profiles WHERE wallet_address = ?;", (wallet_address,)).fetchone()
            if row and row["reputation_score"] is not None:
                return row["reputation_score"]
            return 1000

    def process_tournament_reputation(
        self,
        app_id: int,
        grid_results: List[Dict[str, Any]],
        k_factor: int = 32
    ):
        """
        Updates Elo-based competitive reputation for participants in a finalized verified tournament.
        P1 gets +32, P2 gets +16, P3 gets +8, P4-P5 gets 0, P6-P8 gets -8 to -16 (clamped >= 500).
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        DELTA_MAP = {
            1: 32,
            2: 16,
            3: 8,
            4: 0,
            5: 0,
            6: -8,
            7: -12,
            8: -16
        }

        with get_db() as conn:
            for p in grid_results:
                wallet = p.get("wallet_address")
                if not wallet or wallet.startswith("CPU_"):
                    continue

                pos = p.get("position", 8)
                rating_delta = DELTA_MAP.get(pos, 0)
                source_id = f"tourn_{app_id}"

                # Check existing event
                existing = conn.execute("""
                    SELECT event_id FROM reputation_events 
                    WHERE source_type = 'TOURNAMENT' AND source_id = ? AND wallet_address = ?;
                """, (source_id, wallet)).fetchone()

                if existing:
                    continue

                # Current rating
                prof = conn.execute("SELECT reputation_score FROM player_profiles WHERE wallet_address = ?;", (wallet,)).fetchone()
                current_rating = prof["reputation_score"] if prof and prof["reputation_score"] else 1000
                new_rating = max(500, current_rating + rating_delta)

                event_id = f"re_tourn_{app_id}_{abs(hash(wallet)) % 100000}"
                conn.execute("""
                    INSERT INTO reputation_events (
                        event_id, wallet_address, source_type, source_id,
                        rating_delta, new_rating, reason, created_at
                    ) VALUES (?, ?, 'TOURNAMENT', ?, ?, ?, ?, ?);
                """, (event_id, wallet, source_id, rating_delta, new_rating, f"Tournament #{app_id} (P{pos})", now_iso))

                conn.execute("""
                    INSERT INTO player_profiles (wallet_address, reputation_score, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(wallet_address) DO UPDATE SET
                        reputation_score = excluded.reputation_score,
                        updated_at = excluded.updated_at;
                """, (wallet, new_rating, now_iso, now_iso))

                logger.info(f"🏅 Updated reputation for {wallet[:8]}...: {current_rating} -> {new_rating} (Delta: {rating_delta:+d})")

            conn.commit()

reputation_service = ReputationService()
