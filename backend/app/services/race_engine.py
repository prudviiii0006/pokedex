"""
AlgoRacers — Session 10: Racing Mechanics & Leaderboard
Module: services/race_engine.py
======================================================
Core simulation service coordinating:
  1. Server-side NFT ownership verification
  2. Stat-weighted performance calculation
  3. Controlled randomness & multi-car grid simulation
  4. Race result persistence & idempotency
  5. Leaderboard scoring & wallet collection queries
"""

import json
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from fastapi import HTTPException, status
import algosdk

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.race import (
    Circuit, 
    RaceResponse, 
    GridParticipant, 
    LeaderboardEntry, 
    UserCollectionResponse, 
    OwnedDriverItem
)
from backend.app.services.circuit_service import circuit_service
from backend.rewards.engine import RewardEngine
from backend.rewards.models import DriverTemplate

logger = logging.getLogger("algoracers.race_engine")

POINTS_DISTRIBUTION = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4
}

class RaceEngine:
    def __init__(self):
        self.reward_engine = RewardEngine(
            packs_config_path=settings.PACKS_CONFIG_PATH,
            metadata_dir=settings.METADATA_DIR
        )

    def get_result_category(self, position: int) -> str:
        if position == 1:
            return "Winner (P1)"
        elif position in [2, 3]:
            return f"Podium (P{position})"
        elif position in [4, 5]:
            return f"Top 5 (P{position})"
        elif position in [6, 7]:
            return f"Midfield (P{position})"
        else:
            return f"Backmarker (P{position})"

    def verify_driver_ownership(self, wallet_address: str, asset_id: int) -> DriverTemplate:
        """
        STAGE 1: Server-side ownership verification.
        Never trust client claims about owning an asset or custom stat values!
        Checks database purchase records and returns verified DriverTemplate.
        """
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Algorand 58-character public wallet address."
            )

        with get_db() as conn:
            # 1. Check card_ownership_records (overrides from trades/fusions)
            card_row = conn.execute("SELECT * FROM card_ownership_records WHERE asset_id = ?", (asset_id,)).fetchone()
            if card_row:
                if card_row["current_owner"] != wallet_address:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Wallet '{wallet_address}' does not own Driver NFT with Asset ID #{asset_id}."
                    )
                if card_row["status"] == "CONSUMED_FUSION":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Driver NFT #{asset_id} has been consumed in a fusion and cannot be raced."
                    )
                driver = self.reward_engine.driver_pool.get_driver_by_id(card_row["driver_id"])
                if driver:
                    return driver

            # 2. Check fusion outputs
            fusion_row = conn.execute(
                "SELECT * FROM fusion_operations WHERE output_asset_id = ? AND wallet_address = ?",
                (asset_id, wallet_address)
            ).fetchone()
            if fusion_row and fusion_row["premium_driver_id"]:
                driver = self.reward_engine.driver_pool.get_driver_by_id(fusion_row["premium_driver_id"])
                if driver:
                    return driver

            # 3. Check purchases table
            row = conn.execute(
                "SELECT * FROM purchases WHERE wallet_address = ? AND asset_id = ?",
                (wallet_address, asset_id)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Wallet '{wallet_address}' does not own Driver NFT with Asset ID #{asset_id}."
                )

            # Check if this purchased card was consumed in a fusion
            consumed_row = conn.execute(
                "SELECT fusion_id FROM fusion_inputs WHERE asset_id = ?",
                (asset_id,)
            ).fetchone()
            if consumed_row:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Driver NFT #{asset_id} has been consumed in fusion '{consumed_row['fusion_id']}' and cannot be raced."
                )

            driver_id = row["driver_id"]
            driver = self.reward_engine.driver_pool.get_driver_by_id(driver_id)
            if not driver:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Driver template '{driver_id}' not found in game configuration."
                )
            return driver

    def calculate_base_performance(self, driver: DriverTemplate, circuit: Circuit) -> float:
        """
        STAGE 2: Stat-weighted performance calculation.
        Computes the weighted sum of driver stats based on circuit demands.
        """
        score = 0.0
        for stat_name, weight in circuit.stat_weights.items():
            stat_value = driver.stats.get(stat_name, 70)
            score += stat_value * weight
        return round(score, 2)

    def generate_performance_analysis(
        self, 
        driver: DriverTemplate, 
        circuit: Circuit, 
        base_score: float, 
        position: int
    ) -> str:
        """Rule-based natural language explanation of race outcome."""
        top_circuit_stat = max(circuit.stat_weights.items(), key=lambda x: x[1])[0]
        driver_top_stat_val = driver.stats.get(top_circuit_stat, 70)

        if position == 1:
            return (
                f"🏆 Flawless victory for {driver.name}! On {circuit.name} ({circuit.track_type}), "
                f"their dominant {top_circuit_stat} rating ({driver_top_stat_val}) provided decisive lap-time superiority."
            )
        elif position <= 3:
            return (
                f"🥈 Stellar podium finish (P{position}) for {driver.name}. Balanced performance across "
                f"{circuit.track_type} sectors with strong consistency ({driver.stats.get('Consistency', 75)})."
            )
        elif position <= 5:
            return (
                f"Solid Top 5 finish (P{position}). Strong baseline speed, but high overtaking difficulty on "
                f"{circuit.name} limited further forward progress."
            )
        else:
            return (
                f"Tough outing (P{position}). {circuit.name}'s {circuit.weather} conditions exposed lower "
                f"{top_circuit_stat} rating ({driver_top_stat_val}) against elite competition."
            )

    def simulate_multi_car_race(
        self,
        player_driver: DriverTemplate,
        circuit: Circuit,
        player_wallet: str,
        player_asset_id: int,
        idempotency_key: Optional[str] = None,
        seed: Optional[int] = None
    ) -> RaceResponse:
        """
        STAGE 3: Complete 8-Car Grid Simulation.
        Enforces idempotency, calculates base scores + controlled variance,
        ranks grid, updates points, and persists result in SQLite.
        """
        # 1. IDEMPOTENCY CHECK
        if idempotency_key:
            with get_db() as conn:
                existing = conn.execute(
                    "SELECT * FROM races WHERE idempotency_key = ?",
                    (idempotency_key,)
                ).fetchone()
                if existing:
                    logger.info(f"🔄 Idempotent race retry detected for key '{idempotency_key}'. Returning race {existing['race_id']}.")
                    grid_data = json.loads(existing["grid_results"])
                    return RaceResponse(
                        race_id=existing["race_id"],
                        idempotency_key=existing["idempotency_key"],
                        wallet_address=existing["wallet_address"],
                        asset_id=existing["asset_id"],
                        driver_id=existing["driver_id"],
                        driver_name=existing["driver_name"],
                        circuit_id=existing["circuit_id"],
                        circuit_name=existing["circuit_name"],
                        base_score=existing["base_score"],
                        variance=existing["variance"],
                        final_score=existing["final_score"],
                        position=existing["position"],
                        points=existing["points"],
                        result_category=existing["result_category"],
                        analysis=existing["analysis"],
                        grid=[GridParticipant(**g) for g in grid_data],
                        created_at=existing["created_at"]
                    )

        # 2. Setup RNG generator (deterministic if seed provided for testing)
        rng = random.Random(seed) if seed is not None else random.Random()

        # 3. Select 7 CPU Opponents from Pool
        all_templates = self.reward_engine.driver_pool.get_all_drivers()
        cpu_candidates = [d for d in all_templates if d.id != player_driver.id]
        if len(cpu_candidates) < 7:
            cpu_opponents = (cpu_candidates * 2)[:7]
        else:
            cpu_opponents = rng.sample(cpu_candidates, 7)

        # 4. Compute Performance for all 8 Drivers
        grid_entries = []

        # Player
        p_base = self.calculate_base_performance(player_driver, circuit)
        p_var = round(rng.uniform(-2.5, 2.5), 2)
        p_final = round(p_base + p_var, 2)
        grid_entries.append({
            "driver_name": player_driver.name,
            "team": player_driver.team,
            "rarity": player_driver.rarity,
            "is_player": True,
            "base_score": p_base,
            "variance": p_var,
            "final_score": p_final
        })

        # CPUs
        for cpu in cpu_opponents:
            c_base = self.calculate_base_performance(cpu, circuit)
            c_var = round(rng.uniform(-2.5, 2.5), 2)
            c_final = round(c_base + c_var, 2)
            grid_entries.append({
                "driver_name": cpu.name,
                "team": cpu.team,
                "rarity": cpu.rarity,
                "is_player": False,
                "base_score": c_base,
                "variance": c_var,
                "final_score": c_final
            })

        # 5. Sort Descending by Final Score
        grid_entries.sort(key=lambda x: x["final_score"], reverse=True)

        # 6. Assign Positions & Points
        final_grid: List[GridParticipant] = []
        player_position = 8
        player_points = 0
        player_base_score = p_base
        player_variance = p_var
        player_final_score = p_final

        for idx, entry in enumerate(grid_entries, start=1):
            pts = POINTS_DISTRIBUTION.get(idx, 0)
            participant = GridParticipant(
                position=idx,
                driver_name=entry["driver_name"],
                team=entry["team"],
                rarity=entry["rarity"],
                is_player=entry["is_player"],
                base_score=entry["base_score"],
                variance=entry["variance"],
                final_score=entry["final_score"],
                points=pts
            )
            final_grid.append(participant)

            if entry["is_player"]:
                player_position = idx
                player_points = pts

        # 7. Generate Result Metadata
        race_id = f"race_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        result_cat = self.get_result_category(player_position)
        analysis_text = self.generate_performance_analysis(
            player_driver, circuit, player_base_score, player_position
        )

        # 8. Persist in SQLite
        grid_json = json.dumps([p.model_dump() for p in final_grid])
        with get_db() as conn:
            conn.execute("""
                INSERT INTO races (
                    race_id, idempotency_key, wallet_address, asset_id,
                    driver_id, driver_name, circuit_id, circuit_name,
                    base_score, variance, final_score, position, points,
                    result_category, grid_results, analysis, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                race_id, idempotency_key, player_wallet, player_asset_id,
                player_driver.id, player_driver.name, circuit.id, circuit.name,
                player_base_score, player_variance, player_final_score,
                player_position, player_points, result_cat, grid_json,
                analysis_text, now
            ))
            conn.commit()

        # Session 16: Event-Driven Progression & Achievements
        try:
            from backend.app.services.progression_service import progression_service
            from backend.app.services.achievement_service import achievement_service
            progression_service.process_race_xp(player_wallet, race_id, player_position)
            achievement_service.evaluate_and_unlock(player_wallet, source_event_id=race_id)
        except Exception as e:
            logger.error(f"Failed to process progression for race {race_id}: {e}")

        return RaceResponse(
            race_id=race_id,
            idempotency_key=idempotency_key,
            wallet_address=player_wallet,
            asset_id=player_asset_id,
            driver_id=player_driver.id,
            driver_name=player_driver.name,
            circuit_id=circuit.id,
            circuit_name=circuit.name,
            base_score=player_base_score,
            variance=player_variance,
            final_score=player_final_score,
            position=player_position,
            points=player_points,
            result_category=result_cat,
            analysis=analysis_text,
            grid=final_grid,
            created_at=now
        )

    def get_race(self, race_id: str) -> RaceResponse:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM races WHERE race_id = ?", (race_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Race '{race_id}' not found.")
            grid_data = json.loads(row["grid_results"])
            return RaceResponse(
                race_id=row["race_id"],
                idempotency_key=row["idempotency_key"],
                wallet_address=row["wallet_address"],
                asset_id=row["asset_id"],
                driver_id=row["driver_id"],
                driver_name=row["driver_name"],
                circuit_id=row["circuit_id"],
                circuit_name=row["circuit_name"],
                base_score=row["base_score"],
                variance=row["variance"],
                final_score=row["final_score"],
                position=row["position"],
                points=row["points"],
                result_category=row["result_category"],
                analysis=row["analysis"],
                grid=[GridParticipant(**g) for g in grid_data],
                created_at=row["created_at"]
            )

    def get_leaderboard(self, limit: int = 20) -> List[LeaderboardEntry]:
        """Aggregates race points, wins, and podiums by wallet address."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT 
                    wallet_address,
                    COUNT(*) as total_races,
                    SUM(CASE WHEN position = 1 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN position <= 3 THEN 1 ELSE 0 END) as podiums,
                    SUM(points) as total_points
                FROM races
                GROUP BY wallet_address
                ORDER BY total_points DESC, wins DESC, podiums DESC
                LIMIT ?;
            """, (limit,)).fetchall()

            leaderboard = []
            for rank, r in enumerate(rows, start=1):
                addr = r["wallet_address"]
                display = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 10 else addr
                leaderboard.append(LeaderboardEntry(
                    rank=rank,
                    wallet_address=addr,
                    display_wallet=display,
                    total_races=r["total_races"],
                    wins=r["wins"],
                    podiums=r["podiums"],
                    total_points=r["total_points"]
                ))
            return leaderboard

    def get_wallet_races(self, wallet_address: str) -> List[RaceResponse]:
        """Retrieves individual race history for a wallet."""
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(status_code=400, detail="Invalid Algorand address.")
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM races WHERE wallet_address = ? ORDER BY created_at DESC",
                (wallet_address,)
            ).fetchall()
            res = []
            for r in rows:
                grid_data = json.loads(r["grid_results"])
                res.append(RaceResponse(
                    race_id=r["race_id"],
                    idempotency_key=r["idempotency_key"],
                    wallet_address=r["wallet_address"],
                    asset_id=r["asset_id"],
                    driver_id=r["driver_id"],
                    driver_name=r["driver_name"],
                    circuit_id=r["circuit_id"],
                    circuit_name=r["circuit_name"],
                    base_score=r["base_score"],
                    variance=r["variance"],
                    final_score=r["final_score"],
                    position=r["position"],
                    points=r["points"],
                    result_category=r["result_category"],
                    analysis=r["analysis"],
                    grid=[GridParticipant(**g) for g in grid_data],
                    created_at=r["created_at"]
                ))
            return res

    def get_wallet_collection(self, wallet_address: str) -> UserCollectionResponse:
        """Queries all owned AlgoRacers driver NFTs for a user with their stats."""
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(status_code=400, detail="Invalid Algorand address.")

        with get_db() as conn:
            # 1. Fetch consumed asset IDs
            consumed_rows = conn.execute("SELECT asset_id FROM fusion_inputs").fetchall()
            consumed_set = {r["asset_id"] for r in consumed_rows}

            # 2. Fetch explicitly recorded cards (from trades, fusions, or status changes)
            ownership_rows = conn.execute(
                "SELECT * FROM card_ownership_records WHERE current_owner = ?",
                (wallet_address,)
            ).fetchall()

            cards_by_asset: Dict[int, OwnedDriverItem] = {}

            for r in ownership_rows:
                if r["status"] == "CONSUMED_FUSION" or r["asset_id"] in consumed_set:
                    continue
                driver = self.reward_engine.driver_pool.get_driver_by_id(r["driver_id"])
                if driver:
                    rarity_display = "PREMIUM" if (r["rarity"].upper() in ["PREMIUM", "LEGENDARY"] or r["origin_type"] == "FUSION_OUTPUT") else driver.rarity
                    cards_by_asset[r["asset_id"]] = OwnedDriverItem(
                        asset_id=r["asset_id"],
                        purchase_id=f"rec_{r['asset_id']}",
                        driver_id=driver.id,
                        name=driver.name,
                        team=driver.team,
                        rarity=rarity_display,
                        description=driver.description,
                        image=driver.image,
                        stats=driver.stats
                    )

            # 3. Fetch fusion outputs for this wallet
            fusion_rows = conn.execute(
                "SELECT * FROM fusion_operations WHERE wallet_address = ? AND output_asset_id IS NOT NULL AND status = 'COMPLETED'",
                (wallet_address,)
            ).fetchall()
            for r in fusion_rows:
                aid = r["output_asset_id"]
                if aid not in cards_by_asset and aid not in consumed_set:
                    driver = self.reward_engine.driver_pool.get_driver_by_id(r["premium_driver_id"])
                    if driver:
                        cards_by_asset[aid] = OwnedDriverItem(
                            asset_id=aid,
                            purchase_id=r["fusion_id"],
                            driver_id=driver.id,
                            name=r["premium_driver_name"] or driver.name,
                            team=r["premium_driver_team"] or driver.team,
                            rarity="PREMIUM",
                            description=driver.description,
                            image=driver.image,
                            stats=driver.stats
                        )

            # 4. Fetch initial pack purchases
            purchase_rows = conn.execute(
                "SELECT * FROM purchases WHERE wallet_address = ? AND asset_id IS NOT NULL ORDER BY created_at DESC",
                (wallet_address,)
            ).fetchall()

            for r in purchase_rows:
                aid = r["asset_id"]
                # If card is not yet in cards_by_asset and not consumed and not traded away
                if aid not in cards_by_asset and aid not in consumed_set:
                    # Verify it wasn't traded away to someone else
                    traded_row = conn.execute(
                        "SELECT current_owner FROM card_ownership_records WHERE asset_id = ?",
                        (aid,)
                    ).fetchone()
                    if traded_row and traded_row["current_owner"] != wallet_address:
                        continue
                    if traded_row and traded_row["status"] == "CONSUMED_FUSION":
                        continue

                    driver = self.reward_engine.driver_pool.get_driver_by_id(r["driver_id"])
                    if driver:
                        rarity_display = "PREMIUM" if (driver.rarity.upper() in ["PREMIUM", "LEGENDARY"]) else driver.rarity
                        cards_by_asset[aid] = OwnedDriverItem(
                            asset_id=aid,
                            purchase_id=r["purchase_id"],
                            driver_id=driver.id,
                            name=driver.name,
                            team=driver.team,
                            rarity=rarity_display,
                            description=driver.description,
                            image=driver.image,
                            stats=driver.stats
                        )

            owned_drivers = list(cards_by_asset.values())

            return UserCollectionResponse(
                wallet_address=wallet_address,
                total_owned=len(owned_drivers),
                drivers=owned_drivers
            )

race_engine = RaceEngine()
