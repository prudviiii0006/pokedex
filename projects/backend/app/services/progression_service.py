"""
AlgoRacers — Session 16: Progression Service & XP Ledger
Module: services/progression_service.py
========================================================
Manages XP event auditing, deterministic level formulas, and profile caching.
"""

import json
import math
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

from backend.app.core.database import get_db
from backend.app.services.player_stats_service import player_stats_service

logger = logging.getLogger("algoracers.progression")

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "progression.json"

class ProgressionService:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {
                "race_complete": 20,
                "podium_bonus": 15,
                "win_bonus": 25,
                "tournament_complete": 40,
                "tournament_win_bonus": 100,
                "level_xp_base": 50,
                "initial_reputation": 1000,
                "reputation_k_factor": 32
            }

    def calculate_level(self, total_xp: int) -> Tuple[int, int, float]:
        """
        Deterministic level formula:
          Level(XP) = 1 + floor(sqrt(XP / 50))
          XP required for Level L = 50 * (L - 1)^2
          XP required for Level L+1 = 50 * L^2
        Returns: (current_level, next_level_threshold_xp, progress_percentage)
        """
        if total_xp <= 0:
            return 1, 50, 0.0

        base = self.config.get("level_xp_base", 50)
        level = 1 + int(math.floor(math.sqrt(total_xp / base)))
        
        current_level_base_xp = base * ((level - 1) ** 2)
        next_level_threshold_xp = base * (level ** 2)
        
        xp_in_level = total_xp - current_level_base_xp
        xp_needed_for_next = next_level_threshold_xp - current_level_base_xp
        progress_pct = round((xp_in_level / xp_needed_for_next) * 100.0, 1) if xp_needed_for_next > 0 else 100.0

        return level, next_level_threshold_xp, progress_pct

    def award_xp(
        self,
        wallet_address: str,
        source_type: str,
        source_id: str,
        xp_delta: int,
        reason: str
    ) -> bool:
        """
        Appends a progression event to the audit ledger.
        Enforces 100% idempotency via UNIQUE(source_type, source_id, wallet_address).
        """
        if xp_delta <= 0:
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        event_id = f"pe_{source_type}_{source_id}_{abs(hash(wallet_address)) % 100000}"

        with get_db() as conn:
            # Check for existing event (Idempotency)
            existing = conn.execute("""
                SELECT event_id FROM progression_events 
                WHERE source_type = ? AND source_id = ? AND wallet_address = ?;
            """, (source_type, source_id, wallet_address)).fetchone()

            if existing:
                logger.info(f"🔄 Idempotent XP event detected for {wallet_address[:8]}... (Source: {source_type}:{source_id}). Skipped.")
                return False

            # Insert event into ledger
            conn.execute("""
                INSERT INTO progression_events (
                    event_id, wallet_address, event_type, source_type, source_id,
                    xp_delta, reason, created_at
                ) VALUES (?, ?, 'XP_GAIN', ?, ?, ?, ?, ?);
            """, (event_id, wallet_address, source_type, source_id, xp_delta, reason, now_iso))

            # Compute sum from ledger
            total_xp = conn.execute("""
                SELECT SUM(xp_delta) as total FROM progression_events WHERE wallet_address = ?;
            """, (wallet_address,)).fetchone()["total"] or 0

            level, _, _ = self.calculate_level(total_xp)

            # Upsert into player_profiles cache
            conn.execute("""
                INSERT INTO player_profiles (
                    wallet_address, xp, level, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(wallet_address) DO UPDATE SET
                    xp = excluded.xp,
                    level = excluded.level,
                    updated_at = excluded.updated_at;
            """, (wallet_address, total_xp, level, now_iso, now_iso))

            conn.commit()

        logger.info(f"⚡ Awarded +{xp_delta} XP to {wallet_address[:8]}... ({reason}) -> Total XP: {total_xp} (Level {level})")
        return True

    def process_race_xp(self, wallet_address: str, race_id: str, position: int):
        """Processes XP for completing a race, plus podium and win bonuses."""
        xp_total = self.config.get("race_complete", 20)
        reason_parts = ["Race Completed (+20)"]

        if position == 1:
            xp_total += self.config.get("win_bonus", 25)
            reason_parts.append("Victory Bonus (+25)")
        elif position in [2, 3]:
            xp_total += self.config.get("podium_bonus", 15)
            reason_parts.append(f"P{position} Podium Bonus (+15)")

        self.award_xp(
            wallet_address=wallet_address,
            source_type="RACE",
            source_id=race_id,
            xp_delta=xp_total,
            reason=", ".join(reason_parts)
        )

    def process_tournament_xp(self, wallet_address: str, app_id: int, is_winner: bool):
        """Processes XP for tournament participation and championship victory."""
        xp_total = self.config.get("tournament_complete", 40)
        reason_parts = ["Tournament Entry Completed (+40)"]

        if is_winner:
            xp_total += self.config.get("tournament_win_bonus", 100)
            reason_parts.append("Championship Victory (+100)")

        self.award_xp(
            wallet_address=wallet_address,
            source_type="TOURNAMENT",
            source_id=f"tourn_{app_id}",
            xp_delta=xp_total,
            reason=", ".join(reason_parts)
        )

progression_service = ProgressionService()
