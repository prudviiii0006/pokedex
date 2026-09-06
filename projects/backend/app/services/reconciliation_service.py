"""
AlgoRacers — Session 16: Profile Reconciliation Service
Module: services/reconciliation_service.py
=========================================================
Re-derives player XP, level, reputation, and achievements from raw immutable ledger records,
detects any cached state drift, and safely repairs profile state.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any

from backend.app.core.database import get_db
from backend.app.services.progression_service import progression_service
from backend.app.services.player_stats_service import player_stats_service
from backend.app.services.achievement_service import achievement_service
from backend.app.services.reputation_service import reputation_service
from backend.app.models.profile import ProfileReconcileResponse

logger = logging.getLogger("algoracers.reconciliation")

class ReconciliationService:
    def reconcile_player(self, wallet_address: str) -> ProfileReconcileResponse:
        """
        Reconstructs the full player profile from trusted ledger events.
        Detects drift and reconciles the cache.
        """
        with get_db() as conn:
            # 1. Read current cached profile
            prof = conn.execute("SELECT * FROM player_profiles WHERE wallet_address = ?;", (wallet_address,)).fetchone()
            cached_xp = prof["xp"] if prof else 0
            cached_level = prof["level"] if prof else 1
            cached_rep = prof["reputation_score"] if prof and prof["reputation_score"] is not None else 1000

            # 2. Recalculate true XP from progression_events ledger
            recalc_xp = conn.execute("""
                SELECT SUM(xp_delta) as total FROM progression_events WHERE wallet_address = ?;
            """, (wallet_address,)).fetchone()["total"] or 0

            # 3. Recalculate level
            recalc_level, _, _ = progression_service.calculate_level(recalc_xp)

            # 4. Recalculate true reputation from reputation_events
            last_rep_event = conn.execute("""
                SELECT new_rating FROM reputation_events 
                WHERE wallet_address = ? ORDER BY created_at DESC LIMIT 1;
            """, (wallet_address,)).fetchone()
            recalc_rep = last_rep_event["new_rating"] if last_rep_event else 1000

            # 5. Re-evaluate achievements
            achievement_service.evaluate_and_unlock(
                wallet_address=wallet_address,
                source_event_id="reconciliation"
            )

            total_achievements = conn.execute("""
                SELECT COUNT(*) as cnt FROM player_achievements WHERE wallet_address = ?;
            """, (wallet_address,)).fetchone()["cnt"]

            # 6. Check for drift
            drift_detected = (cached_xp != recalc_xp) or (cached_level != recalc_level) or (cached_rep != recalc_rep)

            now_iso = datetime.now(timezone.utc).isoformat()
            # Update cache to perfect consistency
            conn.execute("""
                INSERT INTO player_profiles (
                    wallet_address, xp, level, reputation_score, achievement_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(wallet_address) DO UPDATE SET
                    xp = excluded.xp,
                    level = excluded.level,
                    reputation_score = excluded.reputation_score,
                    achievement_count = excluded.achievement_count,
                    updated_at = excluded.updated_at;
            """, (wallet_address, recalc_xp, recalc_level, recalc_rep, total_achievements, now_iso, now_iso))
            conn.commit()

        if drift_detected:
            logger.warning(f"⚠️ State drift detected for {wallet_address[:8]}...! Cached XP: {cached_xp} -> Reconciled XP: {recalc_xp}")
        else:
            logger.info(f"✅ Profile for {wallet_address[:8]}... is 100% consistent with ledger.")

        return ProfileReconcileResponse(
            wallet_address=wallet_address,
            drift_detected=drift_detected,
            recalculated_xp=recalc_xp,
            cached_xp=cached_xp,
            recalculated_level=recalc_level,
            recalculated_reputation=recalc_rep,
            achievements_unlocked_count=total_achievements,
            message="State drift repaired successfully." if drift_detected else "Profile is 100% consistent with ledger records."
        )

reconciliation_service = ReconciliationService()
