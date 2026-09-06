"""
AlgoRacers — Session 16: Player Stats Service
Module: services/player_stats_service.py
============================================
Derives verified player statistics from raw game and blockchain records.
"""

from typing import Dict, Any
from backend.app.core.database import get_db
from backend.app.models.profile import PlayerStats

class PlayerStatsService:
    def get_player_stats(self, wallet_address: str) -> PlayerStats:
        """Derives aggregated statistics from trusted database event records."""
        with get_db() as conn:
            # 1. Races stats
            race_rows = conn.execute("""
                SELECT position, circuit_id FROM races 
                WHERE wallet_address = ?;
            """, (wallet_address,)).fetchall()

            races_completed = len(race_rows)
            wins = sum(1 for r in race_rows if r["position"] == 1)
            podiums = sum(1 for r in race_rows if r["position"] in [1, 2, 3])

            # 2. Tournament stats
            tourn_entered = conn.execute("""
                SELECT COUNT(*) as cnt FROM tournament_participants 
                WHERE wallet_address = ?;
            """, (wallet_address,)).fetchone()["cnt"]

            # Tournaments won (where user is marked winner in finalized tournament)
            tourn_won = 0
            finalized_tourns = conn.execute("""
                SELECT t.app_id, t.off_chain_result FROM tournaments t
                JOIN tournament_participants tp ON t.app_id = tp.app_id
                WHERE tp.wallet_address = ? AND t.status = 'FINALIZED';
            """, (wallet_address,)).fetchall()

            import json
            for t in finalized_tourns:
                if t["off_chain_result"]:
                    try:
                        res = json.loads(t["off_chain_result"])
                        if res.get("winner_wallet") == wallet_address:
                            tourn_won += 1
                    except Exception:
                        pass

            # 3. Drivers owned
            drivers_owned = conn.execute("""
                SELECT COUNT(DISTINCT asset_id) as cnt FROM purchases 
                WHERE wallet_address = ? AND status = 'DELIVERED';
            """, (wallet_address,)).fetchone()["cnt"]

            win_rate = round(wins / races_completed, 3) if races_completed > 0 else 0.0
            podium_rate = round(podiums / races_completed, 3) if races_completed > 0 else 0.0

            return PlayerStats(
                races_completed=races_completed,
                wins=wins,
                podiums=podiums,
                tournaments_entered=tourn_entered,
                tournaments_won=tourn_won,
                drivers_owned=drivers_owned,
                win_rate=win_rate,
                podium_rate=podium_rate
            )

player_stats_service = PlayerStatsService()
