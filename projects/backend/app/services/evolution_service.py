"""
AlgoCreatures — Dynamic NFT Evolution Service
Module: services/evolution_service.py
=============================================
Validates XP/Level milestones and executes on-chain state upgrades for creature cards.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

from backend.app.core.database import get_db
from backend.rewards.creature_pool import creature_pool
from backend.app.services.nft_service import nft_service

logger = logging.getLogger("algocreatures.evolution_service")

# Stage minimum levels
EVOLUTION_REQUIREMENTS = {
    2: {"min_level": 3, "min_xp": 350, "stage_name": "Stage 2 Evolution"},
    3: {"min_level": 5, "min_xp": 1050, "stage_name": "Stage 3 Apex Evolution"}
}

class EvolutionService:
    def check_evolution_eligibility(self, asset_id: int, wallet_address: str) -> Dict[str, Any]:
        """Queries whether an owned creature is ready to evolve."""
        # Strict On-Chain Ownership Verification
        if not nft_service.wallet_owns_asset(wallet_address, asset_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not own this Pokémon NFT on-chain (Asset #{asset_id})."
            )

        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
                (asset_id, wallet_address)
            ).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset #{asset_id} not found in collection.")

            current_template = creature_pool.get_creature(row["template_id"])
            if not current_template or not current_template.next_evolution_id:
                return {
                    "asset_id": asset_id,
                    "name": row["name"],
                    "current_species": {
                        "template_id": current_template.id if current_template else row["template_id"],
                        "name": current_template.name if current_template else row["name"],
                        "stage": current_template.evolution_stage if current_template else row["evolution_stage"],
                        "level": row["level"],
                        "xp": row["xp"],
                        "stats": {
                            "HP": row["hp"],
                            "Attack": row["attack"],
                            "Defense": row["defense"],
                            "Speed": row["speed"],
                            "Stamina": row["stamina"]
                        }
                    },
                    "evolution_eligible": False,
                    "reason": "Apex evolution already reached. Maximum form achieved!"
                }

            next_template = creature_pool.get_creature(current_template.next_evolution_id)
            target_stage = current_template.evolution_stage + 1
            req = EVOLUTION_REQUIREMENTS.get(target_stage, {"min_level": 3, "min_xp": 350})

            is_eligible = row["level"] >= req["min_level"] or row["xp"] >= req["min_xp"]

            return {
                "asset_id": asset_id,
                "current_species": {
                    "template_id": current_template.id,
                    "name": current_template.name,
                    "stage": current_template.evolution_stage,
                    "level": row["level"],
                    "xp": row["xp"],
                    "stats": {
                        "HP": row["hp"],
                        "Attack": row["attack"],
                        "Defense": row["defense"],
                        "Speed": row["speed"],
                        "Stamina": row["stamina"]
                    }
                },
                "target_species": {
                    "template_id": next_template.id,
                    "name": next_template.name,
                    "stage": target_stage,
                    "rarity": next_template.rarity,
                    "base_stats": next_template.stats
                } if next_template else None,
                "requirements": req,
                "evolution_eligible": is_eligible,
                "xp_progress": f"{row['xp']} / {req['min_xp']} XP"
            }

    def execute_evolution(self, asset_id: int, wallet_address: str) -> Dict[str, Any]:
        """
        Validates criteria and upgrades the owned creature card to its next evolution form.
        Updates stats, rarity, species name, and logs event in creature_evolutions.
        """
        eligibility = self.check_evolution_eligibility(asset_id, wallet_address)
        if not eligibility.get("evolution_eligible"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Creature does not yet meet evolution criteria: {eligibility.get('xp_progress')}"
            )

        target = eligibility["target_species"]
        target_template = creature_pool.get_creature(target["template_id"])
        current = eligibility["current_species"]

        now = datetime.now(timezone.utc).isoformat()
        evolution_id = f"evo_{uuid.uuid4().hex[:12]}"

        with get_db() as conn:
            # Upgrade stats in owned_creatures
            conn.execute("""
                UPDATE owned_creatures
                SET template_id = ?, name = ?, rarity = ?,
                    hp = ?, attack = ?, defense = ?, speed = ?, stamina = ?,
                    evolution_stage = ?, updated_at = ?
                WHERE asset_id = ? AND wallet_address = ?;
            """, (
                target_template.id, target_template.name, target_template.rarity,
                target_template.base_hp, target_template.base_attack, target_template.base_defense,
                target_template.base_speed, target_template.base_stamina,
                target["stage"], now, asset_id, wallet_address
            ))

            # Record evolution event
            conn.execute("""
                INSERT INTO creature_evolutions (
                    evolution_id, asset_id, wallet_address, from_template_id,
                    to_template_id, from_stage, to_stage, evolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                evolution_id, asset_id, wallet_address, current["template_id"],
                target_template.id, current["stage"], target["stage"], now
            ))

            conn.commit()

            logger.info(f"🧬 Evolution executed! Asset #{asset_id}: {current['name']} -> {target_template.name} ({target_template.rarity})")

            return {
                "success": True,
                "evolution_id": evolution_id,
                "asset_id": asset_id,
                "previous_form": current["name"],
                "evolved_form": target_template.name,
                "new_rarity": target_template.rarity,
                "new_stage": target["stage"],
                "new_stats": target_template.stats,
                "evolved_at": now
            }

    def boost_evolution(self, asset_id: int, wallet_address: str, boost_xp: int = 100) -> Dict[str, Any]:
        """
        Grants a bounded, server-authoritative XP boost (+100 XP) to accelerate evolution eligibility.
        Frontend cannot specify the XP amount. Strictly verifies ownership.
        """
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
                (asset_id, wallet_address)
            ).fetchone()
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Creature Asset #{asset_id} not owned by {wallet_address}."
                )

            current_xp = row["xp"]
            current_level = row["level"]
            new_xp = current_xp + boost_xp
            new_level = min(10, max(current_level, 1 + (new_xp // 200)))
            now = datetime.now(timezone.utc).isoformat()

            conn.execute("""
                UPDATE owned_creatures
                SET xp = ?, level = ?, updated_at = ?
                WHERE asset_id = ? AND wallet_address = ?;
            """, (new_xp, new_level, now, asset_id, wallet_address))
            conn.commit()

        # Check eligibility with new stats
        eligibility = self.check_evolution_eligibility(asset_id, wallet_address)

        logger.info(f"⚡ Evolution XP Boost applied! Asset #{asset_id}: +{boost_xp} XP (Total: {new_xp} XP, Lv {new_level})")

        return {
            "success": True,
            "asset_id": asset_id,
            "wallet_address": wallet_address,
            "creature_name": row["name"],
            "boost_applied_xp": boost_xp,
            "previous_xp": current_xp,
            "new_xp": new_xp,
            "previous_level": current_level,
            "new_level": new_level,
            "evolution_eligible": eligibility.get("evolution_eligible", False),
            "xp_progress": eligibility.get("xp_progress", f"{new_xp} XP"),
            "boosted_at": now
        }

evolution_service = EvolutionService()

