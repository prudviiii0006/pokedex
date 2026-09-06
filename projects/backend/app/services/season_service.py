"""
AlgoRacers — Session 19: Season Management Service
Module: services/season_service.py
==================================================
Manages season lifecycles (DRAFT -> OPEN -> ACTIVE -> CLOSING -> FINALIZED),
tournament membership assignment, and season state queries.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import HTTPException, status
from backend.app.core.database import get_db
from backend.app.models.season import SeasonDetails

logger = logging.getLogger("algoracers.seasons")

class SeasonService:
    def __init__(self):
        self.bootstrap_default_season()

    def bootstrap_default_season(self):
        """Initializes default Season 1 ('season_2026_01') if it doesn't exist."""
        try:
            with get_db() as conn:
                existing = conn.execute("SELECT season_id FROM seasons WHERE season_id = 'season_2026_01';").fetchone()
                if not existing:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    conn.execute("""
                        INSERT INTO seasons (
                            season_id, name, version, status, scoring_version,
                            rounds_total, app_id, created_at
                        ) VALUES ('season_2026_01', 'Neon Championship 2026', 1, 'ACTIVE', 'v1', 4, 88002001, ?);
                    """, (now_iso,))
                    conn.commit()
                    logger.info("🏁 Bootstrapped default Championship Season 'season_2026_01' (ACTIVE)")
        except Exception as e:
            logger.warning(f"Season bootstrap notice: {e}")

    def get_season(self, season_id: str) -> SeasonDetails:
        with get_db() as conn:
            season = conn.execute("SELECT * FROM seasons WHERE season_id = ?;", (season_id,)).fetchone()
            if not season:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Season '{season_id}' not found.")

            tourns = conn.execute("""
                SELECT st.app_id, st.round_number, st.processed_at, t.name, t.circuit_id, t.status, t.winner_asset_id
                FROM season_tournaments st
                LEFT JOIN tournaments t ON st.app_id = t.app_id
                WHERE st.season_id = ?
                ORDER BY st.round_number ASC;
            """, (season_id,)).fetchall()

            rounds_completed = sum(1 for t in tourns if t["status"] == "FINALIZED")
            player_cnt = conn.execute("""
                SELECT COUNT(DISTINCT tp.wallet_address) as cnt
                FROM season_tournaments st
                JOIN tournament_participants tp ON st.app_id = tp.app_id
                WHERE st.season_id = ?;
            """, (season_id,)).fetchone()["cnt"]

            return SeasonDetails(
                season_id=season["season_id"],
                name=season["name"],
                version=season["version"],
                status=season["status"],
                scoring_version=season["scoring_version"],
                rounds_total=season["rounds_total"],
                rounds_completed=rounds_completed,
                player_count=season["player_count"] if season["status"] == "FINALIZED" else player_cnt,
                leaderboard_root=season["leaderboard_root"],
                manifest_cid=season["manifest_cid"],
                app_id=season["app_id"],
                champion_wallet=season["champion_wallet"],
                created_at=season["created_at"],
                finalized_at=season["finalized_at"],
                tournaments=[dict(t) for t in tourns]
            )

    def list_seasons(self) -> List[SeasonDetails]:
        with get_db() as conn:
            rows = conn.execute("SELECT season_id FROM seasons ORDER BY created_at DESC;").fetchall()
            return [self.get_season(r["season_id"]) for r in rows]

    def create_season(
        self,
        season_id: str,
        name: str,
        rounds_total: int = 4,
        scoring_version: str = "v1"
    ) -> SeasonDetails:
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO seasons (
                    season_id, name, version, status, scoring_version,
                    rounds_total, created_at
                ) VALUES (?, ?, 1, 'OPEN', ?, ?, ?);
            """, (season_id, name, scoring_version, rounds_total, now_iso))
            conn.commit()

        logger.info(f"✨ Created new Season '{season_id}' ({name})")
        return self.get_season(season_id)

    def add_tournament_to_season(
        self,
        season_id: str,
        app_id: int,
        round_number: int
    ) -> Dict[str, Any]:
        with get_db() as conn:
            season = conn.execute("SELECT status FROM seasons WHERE season_id = ?;", (season_id,)).fetchone()
            if not season:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Season '{season_id}' not found.")

            if season["status"] in ["CLOSING", "FINALIZED"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot add tournaments to season in '{season['status']}' state.")

            conn.execute("""
                INSERT INTO season_tournaments (season_id, app_id, round_number)
                VALUES (?, ?, ?)
                ON CONFLICT(season_id, app_id) DO NOTHING;
            """, (season_id, app_id, round_number))
            conn.commit()

        logger.info(f"📌 Added Tournament #{app_id} as Round {round_number} to Season '{season_id}'")
        return {"season_id": season_id, "app_id": app_id, "round_number": round_number}

season_service = SeasonService()
