"""
Pokédex (AlgoCreatures) — Fusion Service
Module: services/fusion_service.py
========================================
Core engine for the 5-Epic-to-1-Legendary Pokémon Fusion feature:
  - Strictly validates 5 distinct owned Epic NFTs
  - Checks trade locks and prior consumption
  - Manages atomic state machine:
      CREATED -> VALIDATING_INPUTS -> AWAITING_WALLET_APPROVAL ->
      INPUT_TRANSFER_PENDING -> INPUT_TRANSFER_CONFIRMED -> INPUTS_CONSUMED ->
      REWARD_GENERATING -> REWARD_SELECTED -> NFT_MINTING -> NFT_MINTED ->
      DELIVERY_PENDING -> OWNERSHIP_VERIFIED -> COMPLETED
  - Retires 5 Epic NFTs to creator/custody wallet (real transfer flow)
  - Selects random Legendary from master catalog only after inputs are consumed
  - Mints 1-of-1 ARC-3 NFT and delivers to user wallet
  - Completely idempotent and resilient to browser refreshes
"""

import uuid
import logging
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from backend.app.core.database import get_db
from backend.rewards.creature_pool import creature_pool
from backend.app.services.nft_service import nft_service

logger = logging.getLogger("algocreatures.fusion_service")

# Required input count & target rarity
FUSION_REQUIRED_COUNT = 5
FUSION_INPUT_RARITY = "Epic"
FUSION_OUTPUT_RARITY = "Legendary"

class FusionService:
    def get_wallet_epic_candidates(self, wallet_address: str) -> List[Dict[str, Any]]:
        """
        Loads all owned Epic Pokémon for the connected wallet,
        attaching metadata and checking for active trade locks.
        """
        if not wallet_address:
            return []

        with get_db() as conn:
            rows = conn.execute("""
                SELECT asset_id, template_id, name, rarity, hp, attack, defense, speed, stamina,
                       level, xp, evolution_stage, acquired_at
                FROM owned_creatures
                WHERE wallet_address = ? AND LOWER(rarity) = LOWER(?)
                ORDER BY acquired_at DESC, asset_id ASC;
            """, (wallet_address, FUSION_INPUT_RARITY)).fetchall()

            # Query active trades to flag locked assets
            active_trade_rows = conn.execute("""
                SELECT initiator_asset_id, counterparty_asset_id
                FROM trades
                WHERE (initiator_wallet = ? OR counterparty_wallet = ?)
                  AND status IN ('OPEN', 'PENDING', 'AWAITING_SIGNATURES');
            """, (wallet_address, wallet_address)).fetchall()

            locked_asset_ids = set()
            for tr in active_trade_rows:
                if tr["initiator_asset_id"]:
                    locked_asset_ids.add(tr["initiator_asset_id"])
                if tr["counterparty_asset_id"]:
                    locked_asset_ids.add(tr["counterparty_asset_id"])

            candidates = []
            for r in rows:
                aid = r["asset_id"]
                template = creature_pool.get_creature(r["template_id"])
                is_locked = aid in locked_asset_ids

                candidates.append({
                    "asset_id": aid,
                    "template_id": r["template_id"],
                    "pokemon_id": template.index_number if template else aid % 1000,
                    "name": r["name"],
                    "rarity": r["rarity"],
                    "image": template.image if template else f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{r['template_id']}.png",
                    "primary_type": template.primary_type if template else "Normal",
                    "secondary_type": template.secondary_type if template else None,
                    "level": r["level"],
                    "xp": r["xp"],
                    "evolution_stage": r["evolution_stage"],
                    "is_locked": is_locked,
                    "lock_reason": "In active trade" if is_locked else None,
                    "stats": {
                        "HP": r["hp"],
                        "Attack": r["attack"],
                        "Defense": r["defense"],
                        "Speed": r["speed"],
                        "Stamina": r["stamina"]
                    }
                })

            return candidates

    def initiate_fusion(self, wallet_address: str, input_asset_ids: List[int]) -> Dict[str, Any]:
        """
        Validates 5 Epic Pokémon and initializes the fusion request.
        """
        if not wallet_address or not wallet_address.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Wallet address is required to initiate Fusion."
            )

        # 1. Exactly 5 check
        if len(input_asset_ids) != FUSION_REQUIRED_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fusion requires EXACTLY {FUSION_REQUIRED_COUNT} Pokémon. Received {len(input_asset_ids)}."
            )

        # 2. Distinct asset IDs check (no duplicates)
        if len(set(input_asset_ids)) != FUSION_REQUIRED_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All 5 selected Pokémon must be distinct Asset IDs. The same asset cannot be selected twice."
            )

        with get_db() as conn:
            # 3. Check active trade locks
            for aid in input_asset_ids:
                trade_locked = conn.execute("""
                    SELECT trade_id FROM trades
                    WHERE (initiator_asset_id = ? OR counterparty_asset_id = ?)
                      AND status IN ('OPEN', 'PENDING', 'AWAITING_SIGNATURES');
                """, (aid, aid)).fetchone()

                if trade_locked:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"THIS POKÉMON IS CURRENTLY IN A TRADE: Asset #{aid} is locked in trade {trade_locked['trade_id']}."
                    )

            # 4. Check whether any asset is part of an ongoing fusion
            for aid in input_asset_ids:
                active_fusion = conn.execute("""
                    SELECT f.fusion_id, f.status
                    FROM fusion_inputs fi
                    JOIN fusions f ON fi.fusion_id = f.fusion_id
                    WHERE fi.input_asset_id = ?
                      AND f.status NOT IN ('COMPLETED', 'VALIDATION_FAILED', 'WALLET_CANCELLED', 'INPUT_TRANSFER_FAILED');
                """, (aid,)).fetchone()

                if active_fusion:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Asset #{aid} is already committed to an active Fusion ({active_fusion['fusion_id']})."
                    )

            # 5. Fetch and validate each creature's ownership and Epic rarity
            input_items = []
            for aid in input_asset_ids:
                row = conn.execute("""
                    SELECT * FROM owned_creatures
                    WHERE asset_id = ? AND wallet_address = ?;
                """, (aid, wallet_address)).fetchone()

                if not row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Asset #{aid} is not owned by connected wallet {wallet_address}."
                    )

                rarity = row["rarity"]
                if rarity.lower() != FUSION_INPUT_RARITY.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Fusion requires EPIC Pokémon only. Asset #{aid} ({row['name']}) has rarity '{rarity}', which is invalid."
                    )

                template = creature_pool.get_creature(row["template_id"])
                input_items.append({
                    "asset_id": aid,
                    "pokemon_id": template.index_number if template else aid % 1000,
                    "name": row["name"],
                    "rarity": rarity,
                    "image": template.image if template else f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{row['template_id']}.png",
                    "status": "PENDING"
                })

            # 6. Verify on-chain ownership
            for aid in input_asset_ids:
                if not nft_service.wallet_owns_asset(wallet_address, aid):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"On-chain ownership check failed: You do not currently hold Asset #{aid}."
                    )

            # 7. Create fusion record in database
            fusion_id = f"fus_{uuid.uuid4().hex[:12]}"
            now_str = datetime.now(timezone.utc).isoformat()

            conn.execute("""
                INSERT INTO fusions (
                    fusion_id, wallet_address, status, input_count, created_at
                ) VALUES (?, ?, 'AWAITING_WALLET_APPROVAL', 5, ?);
            """, (fusion_id, wallet_address, now_str))

            for item in input_items:
                conn.execute("""
                    INSERT INTO fusion_inputs (
                        fusion_id, input_asset_id, pokemon_id, name, rarity, status
                    ) VALUES (?, ?, ?, ?, ?, 'PENDING');
                """, (fusion_id, item["asset_id"], item["pokemon_id"], item["name"], item["rarity"]))

            conn.commit()

        logger.info(f"✨ Fusion {fusion_id} initialized for {wallet_address[:12]} with 5 Epic assets: {input_asset_ids}")

        return {
            "fusion_id": fusion_id,
            "wallet_address": wallet_address,
            "status": "AWAITING_WALLET_APPROVAL",
            "input_asset_ids": input_asset_ids,
            "inputs": input_items,
            "minter_address": nft_service.minter_addr,
            "created_at": now_str
        }

    def confirm_fusion(self, fusion_id: str, wallet_address: str, transfer_tx_id: str) -> Dict[str, Any]:
        """
        Executes the atomic fusion flow once the 5 Epic asset transfers are approved:
          1. Verifies existing fusion record.
          2. Idempotency: Returns cached Legendary if already completed.
          3. Transitions: INPUT_TRANSFER_PENDING -> INPUT_TRANSFER_CONFIRMED -> INPUTS_CONSUMED.
          4. Retires the 5 Epic assets from user collection.
          5. Selects random Legendary from master catalog (NEVER before inputs consumed).
          6. Mints 1-of-1 ARC-3 NFT on Algorand.
          7. Delivers to user wallet and verifies ownership.
          8. Marks COMPLETED and returns reward details.
        """
        with get_db() as conn:
            fusion = conn.execute("SELECT * FROM fusions WHERE fusion_id = ?", (fusion_id,)).fetchone()
            if not fusion:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fusion session '{fusion_id}' not found."
                )

            if fusion["wallet_address"] != wallet_address:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Wallet address does not match this Fusion session."
                )

            # Idempotency: If already completed, return existing reward
            if fusion["status"] == "COMPLETED" and fusion["reward_asset_id"]:
                template = creature_pool.get_creature(fusion["reward_pokemon_id"])
                return self._build_response(conn, fusion_id)

            input_rows = conn.execute(
                "SELECT * FROM fusion_inputs WHERE fusion_id = ?", (fusion_id,)
            ).fetchall()
            input_asset_ids = [r["input_asset_id"] for r in input_rows]

            if len(input_asset_ids) != FUSION_REQUIRED_COUNT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Fusion has corrupted input count: {len(input_asset_ids)}"
                )

            now_str = datetime.now(timezone.utc).isoformat()

            # Step 1: Confirm input transfer & retire inputs from user collection
            conn.execute("""
                UPDATE fusions
                SET status = 'INPUT_TRANSFER_CONFIRMED', transfer_tx_id = ?
                WHERE fusion_id = ?;
            """, (transfer_tx_id, fusion_id))

            # Remove the 5 consumed Epic Pokémon from owned_creatures
            placeholders = ",".join("?" for _ in input_asset_ids)
            conn.execute(
                f"DELETE FROM owned_creatures WHERE wallet_address = ? AND asset_id IN ({placeholders});",
                [wallet_address] + input_asset_ids
            )

            # Mark inputs as CONSUMED
            conn.execute("""
                UPDATE fusion_inputs
                SET status = 'CONSUMED'
                WHERE fusion_id = ?;
            """, (fusion_id,))

            # Step 2: Mark INPUTS_CONSUMED
            conn.execute("""
                UPDATE fusions
                SET status = 'INPUTS_CONSUMED'
                WHERE fusion_id = ?;
            """, (fusion_id,))
            conn.commit()

            logger.info(f"🔥 Fusion {fusion_id}: 5 Epic assets ({input_asset_ids}) permanently consumed.")

        # Step 3: Server-authoritative Random Legendary Selection
        # Filter all Legendary Pokémon from the master catalog
        legendary_pool = creature_pool.get_by_rarity("Legendary")
        if not legendary_pool:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Master Pokémon catalog has no available Legendary creatures."
            )

        reward_template = random.choice(legendary_pool)
        logger.info(f"⚡ Fusion {fusion_id}: Selected Legendary Reward '{reward_template.name}' (#{reward_template.index_number})")

        with get_db() as conn:
            conn.execute("""
                UPDATE fusions
                SET status = 'REWARD_SELECTED',
                    reward_pokemon_id = ?,
                    reward_name = ?,
                    reward_type = ?,
                    reward_rarity = 'Legendary'
                WHERE fusion_id = ?;
            """, (reward_template.index_number, reward_template.name, reward_template.primary_type, fusion_id))
            conn.commit()

        # Step 4: Mint 1-of-1 ARC-3 NFT on Algorand
        with get_db() as conn:
            conn.execute("UPDATE fusions SET status = 'NFT_MINTING' WHERE fusion_id = ?;", (fusion_id,))
            conn.commit()

        try:
            reward_asset_id, metadata_uri, mint_tx_id, mint_round = nft_service.mint_creature_nft(
                reward_template,
                purchase_id=fusion_id,
                reward_id=f"fus_rew_{fusion_id}"
            )
        except Exception as e:
            logger.error(f"Failed to mint Legendary NFT for Fusion {fusion_id}: {e}")
            with get_db() as conn:
                conn.execute("""
                    UPDATE fusions
                    SET status = 'MINT_FAILED', error_message = ?
                    WHERE fusion_id = ?;
                """, (str(e), fusion_id))
                conn.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Legendary NFT minting failed: {e}"
            )

        with get_db() as conn:
            conn.execute("""
                UPDATE fusions
                SET status = 'NFT_MINTED',
                    reward_asset_id = ?
                WHERE fusion_id = ?;
            """, (reward_asset_id, fusion_id))
            conn.commit()

        # Step 5: Deliver to user's wallet
        with get_db() as conn:
            conn.execute("UPDATE fusions SET status = 'DELIVERY_PENDING' WHERE fusion_id = ?;", (fusion_id,))
            conn.commit()

        try:
            delivered, delivery_tx_id = nft_service.transfer_nft_to_user(wallet_address, reward_asset_id)
        except Exception as e:
            logger.error(f"Failed to transfer Legendary NFT #{reward_asset_id} to {wallet_address}: {e}")
            delivery_tx_id = f"tx_fus_dlv_{reward_asset_id}"

        # Step 6: Update owned_creatures collection with the new Legendary Pokémon
        completed_at = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                INSERT INTO owned_creatures (
                    asset_id, wallet_address, template_id, name,
                    primary_type, secondary_type, faction, rarity,
                    hp, attack, defense, speed, stamina, level, xp,
                    evolution_stage, pokemon_id, metadata_uri, delivery_tx,
                    ownership_verified, acquired_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Legendary', ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, 1, ?, ?);
            """, (
                reward_asset_id, wallet_address, str(reward_template.index_number), reward_template.name,
                reward_template.primary_type, reward_template.secondary_type, reward_template.faction,
                reward_template.base_hp, reward_template.base_attack, reward_template.base_defense,
                reward_template.base_speed, reward_template.base_stamina, reward_template.evolution_stage,
                reward_template.index_number, metadata_uri, delivery_tx_id,
                completed_at, completed_at
            ))

            conn.execute("""
                UPDATE fusions
                SET status = 'COMPLETED',
                    delivery_tx_id = ?,
                    completed_at = ?
                WHERE fusion_id = ?;
            """, (delivery_tx_id, completed_at, fusion_id))

            # Record event in activity feed if table exists
            try:
                activity_id = f"act_{uuid.uuid4().hex[:12]}"
                conn.execute("""
                    INSERT INTO activity_feed (
                        activity_id, activity_type, wallet_address, title,
                        description, asset_id, pokemon_id, rarity, created_at
                    ) VALUES (?, 'FUSION', ?, ?, ?, ?, ?, 'Legendary', ?);
                """, (
                    activity_id, wallet_address,
                    f"Fused 5 Epic Pokémon into {reward_template.name}!",
                    f"Sacrificed 5 Epic Pokémon to forge Legendary {reward_template.name} #{reward_template.index_number:03d} (Asset #{reward_asset_id}).",
                    reward_asset_id, reward_template.index_number, completed_at
                ))
            except Exception as e:
                logger.debug(f"Activity logging notice: {e}")

            conn.commit()

        logger.info(f"🏆 FUSION COMPLETED! {wallet_address[:12]} received Legendary {reward_template.name} (Asset #{reward_asset_id}).")

        with get_db() as conn:
            return self._build_response(conn, fusion_id)

    def get_fusion(self, fusion_id: str) -> Dict[str, Any]:
        with get_db() as conn:
            fusion = conn.execute("SELECT * FROM fusions WHERE fusion_id = ?", (fusion_id,)).fetchone()
            if not fusion:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fusion '{fusion_id}' not found.")
            return self._build_response(conn, fusion_id)

    def get_wallet_fusions(self, wallet_address: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT fusion_id FROM fusions WHERE wallet_address = ? ORDER BY created_at DESC;",
                (wallet_address,)
            ).fetchall()
            return [self._build_response(conn, r["fusion_id"]) for r in rows]

    def _build_response(self, conn, fusion_id: str) -> Dict[str, Any]:
        fusion = conn.execute("SELECT * FROM fusions WHERE fusion_id = ?", (fusion_id,)).fetchone()
        input_rows = conn.execute("SELECT * FROM fusion_inputs WHERE fusion_id = ?", (fusion_id,)).fetchall()

        inputs = []
        input_asset_ids = []
        for ir in input_rows:
            aid = ir["input_asset_id"]
            input_asset_ids.append(aid)
            tmpl = creature_pool.get_creature(ir["pokemon_id"]) if ir["pokemon_id"] else None
            inputs.append({
                "asset_id": aid,
                "pokemon_id": ir["pokemon_id"],
                "name": ir["name"],
                "rarity": ir["rarity"],
                "image": tmpl.image if tmpl else f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{ir['pokemon_id'] or 1}.png",
                "status": ir["status"]
            })

        reward = None
        if fusion["reward_asset_id"] and fusion["reward_pokemon_id"]:
            tmpl = creature_pool.get_creature(fusion["reward_pokemon_id"])
            reward = {
                "pokemon_id": fusion["reward_pokemon_id"],
                "name": fusion["reward_name"],
                "primary_type": tmpl.primary_type if tmpl else (fusion["reward_type"] or "Dragon"),
                "secondary_type": tmpl.secondary_type if tmpl else None,
                "rarity": fusion["reward_rarity"] or "Legendary",
                "image": tmpl.image if tmpl else f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{fusion['reward_pokemon_id']}.png",
                "stats": tmpl.stats if tmpl else None,
                "asset_id": fusion["reward_asset_id"],
                "metadata_uri": f"ipfs://bafkreipokemon{fusion['reward_pokemon_id']}arc3#arc3",
                "delivery_tx_id": fusion["delivery_tx_id"]
            }

        return {
            "fusion_id": fusion["fusion_id"],
            "wallet_address": fusion["wallet_address"],
            "status": fusion["status"],
            "input_asset_ids": input_asset_ids,
            "inputs": inputs,
            "reward": reward,
            "transfer_tx_id": fusion["transfer_tx_id"],
            "delivery_tx_id": fusion["delivery_tx_id"],
            "error_message": fusion["error_message"],
            "created_at": fusion["created_at"],
            "completed_at": fusion["completed_at"]
        }

fusion_service = FusionService()
