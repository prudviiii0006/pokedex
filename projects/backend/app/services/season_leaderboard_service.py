"""
AlgoRacers — Session 19: Season Leaderboard & Scoring Service
Module: services/season_leaderboard_service.py
=============================================================
Aggregates championship points from verified tournament results,
applies deterministic multi-tier tie-breakers, and produces official standings.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.app.core.database import get_db
from backend.app.models.season import SeasonLeaderboardEntry

logger = logging.getLogger("algoracers.seasons.leaderboard")

SCORING_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "season_scoring_v1.json"

class SeasonLeaderboardService:
    def __init__(self):
        self.scoring_config = self._load_scoring_config()

    def _load_scoring_config(self) -> Dict[str, Any]:
        try:
            with open(SCORING_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "version": "v1",
                "points_matrix": {"1": 25, "2": 18, "3": 15, "4": 12, "5": 10, "6": 8, "7": 6, "8": 4},
                "participation_points": 2
            }

    def calculate_leaderboard(self, season_id: str) -> List[SeasonLeaderboardEntry]:
        """
        Calculates deterministic standings for a season from eligible finalized tournaments.
        """
        points_map = self.scoring_config.get("points_matrix", {})
        part_points = self.scoring_config.get("participation_points", 2)

        with get_db() as conn:
            # 1. Fetch assigned tournaments for this season
            assigned_tourns = conn.execute("""
                SELECT st.app_id, st.round_number, t.status, t.off_chain_result, t.winner_asset_id
                FROM season_tournaments st
                JOIN tournaments t ON st.app_id = t.app_id
                WHERE st.season_id = ?
                ORDER BY st.round_number ASC;
            """, (season_id,)).fetchall()

            # Aggregate stats per wallet
            player_stats: Dict[str, Dict[str, Any]] = {}

            for at in assigned_tourns:
                # Only include FINALIZED tournaments
                if at["status"] != "FINALIZED" or not at["off_chain_result"]:
                    continue

                try:
                    result_data = json.loads(at["off_chain_result"])
                except Exception:
                    continue

                grid = result_data.get("grid", [])
                for car in grid:
                    wallet = car.get("wallet_address")
                    if not wallet or wallet.startswith("CPU_"):
                        continue

                    pos = car.get("position", 8)
                    pts = points_map.get(str(pos), part_points)
                    driver_id = car.get("driver_id", "001")
                    driver_name = car.get("driver_name", "Driver")

                    if wallet not in player_stats:
                        player_stats[wallet] = {
                            "wallet_address": wallet,
                            "driver_id": driver_id,
                            "driver_name": driver_name,
                            "points": 0,
                            "wins": 0,
                            "podiums": 0,
                            "finishes": [],
                            "tournaments_entered": 0
                        }

                    p_entry = player_stats[wallet]
                    p_entry["points"] += pts
                    p_entry["tournaments_entered"] += 1
                    p_entry["finishes"].append(pos)
                    if pos == 1:
                        p_entry["wins"] += 1
                    if pos in [1, 2, 3]:
                        p_entry["podiums"] += 1

            if not player_stats:
                return []

            # 2. Deterministic Tie-Breaking Sort Key:
            # 1. points (descending -> -pts)
            # 2. wins (descending -> -wins)
            # 3. podiums (descending -> -podiums)
            # 4. best finish (ascending -> min(finishes))
            # 5. wallet_address (ascending -> wallet)
            def sort_key(p: Dict[str, Any]) -> Tuple[int, int, int, int, str]:
                best_pos = min(p["finishes"]) if p["finishes"] else 99
                return (
                    -p["points"],
                    -p["wins"],
                    -p["podiums"],
                    best_pos,
                    p["wallet_address"]
                )

            sorted_players = sorted(player_stats.values(), key=sort_key)

            # 3. Build ranked entries
            results = []
            for rank_idx, p in enumerate(sorted_players, start=1):
                w = p["wallet_address"]
                disp_w = f"{w[:6]}...{w[-4:]}" if len(w) > 10 else w
                results.append(SeasonLeaderboardEntry(
                    wallet_address=w,
                    display_wallet=disp_w,
                    driver_id=p["driver_id"],
                    driver_name=p["driver_name"],
                    rank=rank_idx,
                    points=p["points"],
                    wins=p["wins"],
                    podiums=p["podiums"],
                    tournaments_entered=p["tournaments_entered"]
                ))

            return results

season_leaderboard_service = SeasonLeaderboardService()
