"""
AlgoRacers — Session 16: Achievement Engine
Module: services/achievement_service.py
===========================================
Loads achievement catalog, evaluates rules, unlocks achievements,
and coordinates on-chain credential issuance.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.app.core.database import get_db
from backend.app.models.achievement import AchievementItem
from backend.app.services.player_stats_service import player_stats_service
from backend.app.services.credential_service import credential_service

logger = logging.getLogger("algoracers.achievements")

ACHIEVEMENTS_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "achievements.json"

class AchievementService:
    def __init__(self):
        self.achievements_catalog = self._load_catalog()

    def _load_catalog(self) -> List[Dict[str, Any]]:
        try:
            with open(ACHIEVEMENTS_CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def get_player_achievements(self, wallet_address: str) -> List[AchievementItem]:
        """Returns the full catalog of achievements with progress and unlock status for the player."""
        stats = player_stats_service.get_player_stats(wallet_address)

        with get_db() as conn:
            unlocked_rows = conn.execute("""
                SELECT achievement_id, unlocked_at, credential_status, credential_asset_id, issuance_tx_id
                FROM player_achievements WHERE wallet_address = ?;
            """, (wallet_address,)).fetchall()

            unlocked_map = {r["achievement_id"]: r for r in unlocked_rows}

            # Count wet race wins using circuit_service
            race_wins = conn.execute("""
                SELECT circuit_id FROM races 
                WHERE wallet_address = ? AND position = 1;
            """, (wallet_address,)).fetchall()

            from backend.app.services.circuit_service import circuit_service
            wet_wins = 0
            for rw in race_wins:
                c = circuit_service.get_circuit(rw["circuit_id"])
                if c and c.weather in ["Wet", "Heavy Rain", "Rain", "Tropical Storm"]:
                    wet_wins += 1

            # Count Legendary drivers owned
            legendary_owned = conn.execute("""
                SELECT COUNT(*) as cnt FROM purchases 
                WHERE wallet_address = ? AND rarity = 'Legendary' AND status = 'DELIVERED';
            """, (wallet_address,)).fetchone()["cnt"]

            result = []
            for ach in self.achievements_catalog:
                ach_id = ach["id"]
                unlocked_info = unlocked_map.get(ach_id)
                is_unlocked = unlocked_info is not None

                # Compute current progress
                trigger = ach.get("trigger", "")
                threshold = ach.get("threshold", 1)
                
                if trigger == "COUNT_RACES":
                    progress = min(threshold, stats.races_completed)
                elif trigger == "COUNT_PODIUMS":
                    progress = min(threshold, stats.podiums)
                elif trigger == "COUNT_WINS":
                    progress = min(threshold, stats.wins)
                elif trigger == "COUNT_WET_WINS":
                    progress = min(threshold, wet_wins)
                elif trigger == "COUNT_TOURNAMENTS_ENTERED":
                    progress = min(threshold, stats.tournaments_entered)
                elif trigger == "COUNT_TOURNAMENTS_WON":
                    progress = min(threshold, stats.tournaments_won)
                elif trigger == "OWNERSHIP_COUNT":
                    progress = min(threshold, stats.drivers_owned)
                elif trigger == "OWN_RARITY":
                    progress = min(threshold, legendary_owned)
                else:
                    progress = 1 if is_unlocked else 0

                item = AchievementItem(
                    id=ach["id"],
                    name=ach["name"],
                    description=ach["description"],
                    category=ach.get("category", "racing"),
                    trigger=trigger,
                    threshold=threshold,
                    permanent=ach.get("permanent", True),
                    credential_policy=ach.get("credential_policy", "off_chain"),
                    icon=ach.get("icon", "🏆"),
                    unlocked=is_unlocked,
                    unlocked_at=unlocked_info["unlocked_at"] if unlocked_info else None,
                    progress=progress,
                    credential_status=unlocked_info["credential_status"] if unlocked_info else "OFF_CHAIN",
                    credential_asset_id=unlocked_info["credential_asset_id"] if unlocked_info else None,
                    issuance_tx_id=unlocked_info["issuance_tx_id"] if unlocked_info else None
                )
                result.append(item)

            return result

    def evaluate_and_unlock(
        self,
        wallet_address: str,
        source_event_id: str,
        tournament_app_id: Optional[int] = None,
        result_hash: Optional[str] = None
    ) -> List[str]:
        """
        Evaluates achievement rules for the player and unlocks any newly achieved milestones.
        Enforces idempotency via UNIQUE(wallet_address, achievement_id).
        """
        achievements = self.get_player_achievements(wallet_address)
        newly_unlocked = []
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            for ach in achievements:
                if not ach.unlocked and ach.progress >= ach.threshold:
                    # Unlock achievement!
                    policy = ach.credential_policy
                    initial_status = "ELIGIBLE" if policy == "on_chain_badge" else "OFF_CHAIN"

                    conn.execute("""
                        INSERT INTO player_achievements (
                            wallet_address, achievement_id, unlocked_at,
                            source_event_id, credential_status
                        ) VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(wallet_address, achievement_id) DO NOTHING;
                    """, (wallet_address, ach.id, now_iso, source_event_id, initial_status))

                    newly_unlocked.append(ach.id)
                    logger.info(f"🎉 Achievement Unlocked for {wallet_address[:8]}...: {ach.name} ({ach.id})")

            # Update achievement_count in profile
            total_unlocked = conn.execute("""
                SELECT COUNT(*) as cnt FROM player_achievements WHERE wallet_address = ?;
            """, (wallet_address,)).fetchone()["cnt"]

            conn.execute("""
                UPDATE player_profiles 
                SET achievement_count = ?, updated_at = ? 
                WHERE wallet_address = ?;
            """, (total_unlocked, now_iso, wallet_address))
            conn.commit()

        # Handle on-chain credential issuance outside of the first DB transaction
        if "TOURNAMENT_CHAMPION" in newly_unlocked and tournament_app_id and result_hash:
            credential_service.issue_tournament_champion_badge(
                wallet_address=wallet_address,
                tournament_app_id=tournament_app_id,
                result_hash=result_hash
            )

        return newly_unlocked

achievement_service = AchievementService()
