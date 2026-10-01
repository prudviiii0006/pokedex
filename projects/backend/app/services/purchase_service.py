"""
Pokédex (AlgoCreatures) — Pack Purchase Pipeline & NFT Delivery Service
Module: services/purchase_service.py
======================================================================
Orchestrates the complete Purchase -> Creature Reward Engine -> NFT Mint -> Delivery pipeline.
Enforces strict idempotency, blockchain verification, and database unique constraints.
"""

import uuid
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
import algosdk

from backend.app.core.database import get_db
from backend.app.models.purchase import PurchaseResponse, PurchaseStatus
from backend.app.services.nft_service import nft_service
from backend.rewards.engine import RewardEngine
from backend.rewards.creature_pool import creature_pool
from backend.app.core.config import settings

logger = logging.getLogger("algocreatures.purchase_service")

# TestNet Pack Pricing (Native ALGO) from Settings
PACK_PRICING = {
    "basic": settings.BASIC_PACK_PRICE_ALGO,            # 0.1 ALGO (100,000 microAlgos)
    "premium": settings.PREMIUM_PACK_PRICE_ALGO,        # 0.5 ALGO (500,000 microAlgos)
    "fire_event": settings.EVENT_PACK_PRICE_ALGO,       # 0.2 ALGO (200,000 microAlgos)
    "water_event": settings.EVENT_PACK_PRICE_ALGO,      # 0.2 ALGO (200,000 microAlgos)
    "electric_event": settings.EVENT_PACK_PRICE_ALGO,   # 0.2 ALGO (200,000 microAlgos)
    "ghost_event": settings.EVENT_PACK_PRICE_ALGO       # 0.2 ALGO (200,000 microAlgos)
}

class PurchaseService:
    def __init__(self):
        self.reward_engine = RewardEngine(
            packs_config_path=settings.PACKS_CONFIG_PATH,
            metadata_dir=settings.METADATA_DIR
        )

    def _row_to_response(self, row: Any) -> PurchaseResponse:
        is_paid = row["status"] not in [PurchaseStatus.CREATED.value, PurchaseStatus.PAYMENT_REQUIRED.value]
        creature_id = row["creature_id"] if "creature_id" in row.keys() and row["creature_id"] else (row["driver_id"] if "driver_id" in row.keys() else None)
        creature_name = row["creature_name"] if "creature_name" in row.keys() and row["creature_name"] else (row["driver_name"] if "driver_name" in row.keys() else None)
        creature_type = row["creature_type"] if "creature_type" in row.keys() and row["creature_type"] else None

        if not creature_type and creature_id:
            c_tmpl = creature_pool.get_creature(creature_id)
            if c_tmpl:
                creature_type = c_tmpl.primary_type
                if not creature_name:
                    creature_name = c_tmpl.name

        price = float(row["price_usdc"]) if "price_usdc" in row.keys() and row["price_usdc"] is not None else 0.1
        amount_micro = int(Decimal(str(price)) * Decimal(1_000_000))

        asset_id = row["asset_id"] if "asset_id" in row.keys() else None
        mint_tx = row["mint_tx_id"] if "mint_tx_id" in row.keys() and row["mint_tx_id"] else (f"tx_mint_{asset_id}" if asset_id else None)
        delivery_tx = row["delivery_tx_id"] if "delivery_tx_id" in row.keys() else None
        mint_round = row["mint_round"] if "mint_round" in row.keys() else 0
        ownership_verified = (row["status"] == PurchaseStatus.DELIVERED.value) if asset_id else False
        explorer_url = f"https://testnet.explorer.perawallet.app/asset/{asset_id}/" if asset_id else None

        reward_dict = {
            "pokemon_id": creature_id,
            "pokemon_name": creature_name,
            "element": creature_type,
            "rarity": row["rarity"] if "rarity" in row.keys() else None
        } if row["reward_id"] else None

        nft_dict = {
            "asset_id": asset_id,
            "mint_tx_id": mint_tx,
            "delivery_tx_id": delivery_tx,
            "mint_round": mint_round,
            "metadata_uri": row["metadata_uri"] if "metadata_uri" in row.keys() else None,
            "ownership_verified": ownership_verified,
            "explorer_url": explorer_url
        } if asset_id else None

        return PurchaseResponse(
            purchase_id=row["purchase_id"],
            idempotency_key=row["idempotency_key"] if "idempotency_key" in row.keys() else None,
            pack_id=row["pack_id"],
            wallet_address=row["wallet_address"],
            price_algo=price,
            amount_microalgo=amount_micro,
            amount_algo_display=f"{price} ALGO",
            price_usdc=price,
            currency="ALGO",
            paid=is_paid,
            status=PurchaseStatus(row["status"]),
            payment_status=row["payment_status"],
            payment_tx_id=row["payment_tx_id"],
            reward_status=row["reward_status"],
            reward_id=row["reward_id"],
            rarity=row["rarity"],
            creature_id=creature_id,
            creature_name=creature_name,
            creature_type=creature_type,
            driver_id=creature_id,
            driver_name=creature_name,
            metadata_uri=row["metadata_uri"] if "metadata_uri" in row.keys() else None,
            asset_id=asset_id,
            nft_mint_tx_id=mint_tx,
            delivery_tx_id=delivery_tx,
            mint_round=mint_round,
            ownership_verified=ownership_verified,
            explorer_url=explorer_url,
            reward=reward_dict,
            nft=nft_dict,
            error_message=row["error_message"] if "error_message" in row.keys() else None,
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def get_purchase(self, purchase_id: str) -> PurchaseResponse:
        """Retrieves a purchase record by ID or raises 404."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Purchase '{purchase_id}' not found.")
            return self._row_to_response(row)

    def get_user_purchases(self, wallet_address: str) -> List[PurchaseResponse]:
        """Retrieves all purchases made by a given wallet address."""
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Algorand wallet address.")
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM purchases WHERE wallet_address = ? ORDER BY created_at DESC", 
                (wallet_address,)
            ).fetchall()
            return [self._row_to_response(r) for r in rows]

    def get_wallet_collection(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Retrieves full owned creature card collection for a wallet."""
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Algorand wallet address.")
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM owned_creatures WHERE wallet_address = ? ORDER BY acquired_at DESC",
                (wallet_address,)
            ).fetchall()
            collection = []
            for r in rows:
                asset_id = r["asset_id"]
                is_on_chain = nft_service.wallet_owns_asset(wallet_address, asset_id)
                collection.append({
                    "asset_id": asset_id,
                    "template_id": r["template_id"],
                    "name": r["name"],
                    "primary_type": r["primary_type"],
                    "secondary_type": r["secondary_type"],
                    "faction": r["faction"],
                    "rarity": r["rarity"],
                    "level": r["level"],
                    "xp": r["xp"],
                    "hp": r["hp"],
                    "attack": r["attack"],
                    "defense": r["defense"],
                    "speed": r["speed"],
                    "stamina": r["stamina"],
                    "battle_wins": r["battle_wins"],
                    "battle_losses": r["battle_losses"],
                    "evolution_stage": r["evolution_stage"],
                    "mint_tx": r["mint_tx"],
                    "delivery_tx": r["delivery_tx"] if "delivery_tx" in r.keys() else None,
                    "purchase_id": r["purchase_id"],
                    "owner_wallet": wallet_address,
                    "on_chain_verified": is_on_chain,
                    "explorer_url": f"https://testnet.explorer.perawallet.app/asset/{asset_id}/",
                    "acquired_at": r["acquired_at"],
                    "updated_at": r["updated_at"]
                })
            return collection

    # Backward compatibility alias
    def get_wallet_drivers(self, wallet_address: str) -> List[Dict[str, Any]]:
        return self.get_wallet_collection(wallet_address)

    def create_or_resume_purchase(
        self,
        pack_id: str,
        wallet_address: str,
        idempotency_key: Optional[str] = None
    ) -> PurchaseResponse:
        """
        STAGE 1: Create Purchase Intent
        Validates wallet, checks idempotency key, and records initial state.
        """
        pack_key = pack_id.lower()
        if pack_key not in PACK_PRICING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pack '{pack_id}'. Available: {list(PACK_PRICING.keys())}"
            )

        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Algorand 58-character public wallet address."
            )

        with get_db() as conn:
            # 1. IDEMPOTENCY CHECK
            if idempotency_key:
                existing = conn.execute(
                    "SELECT * FROM purchases WHERE idempotency_key = ?", 
                    (idempotency_key,)
                ).fetchone()
                if existing:
                    logger.info(f"🔄 Idempotent retry detected for key '{idempotency_key}'. Returning purchase {existing['purchase_id']}.")
                    return self._row_to_response(existing)

            # 2. CREATE NEW PURCHASE
            purchase_id = f"pur_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            price = PACK_PRICING[pack_key]

            conn.execute("""
                INSERT INTO purchases (
                    purchase_id, idempotency_key, pack_id, wallet_address, price_usdc,
                    payment_status, payment_tx_id, reward_status, reward_id,
                    rarity, creature_id, creature_name, creature_type,
                    driver_id, driver_name, metadata_uri, asset_id,
                    delivery_tx_id, status, error_message, schema_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL, 'CREATURE_V1', ?, ?);
            """, (
                purchase_id, idempotency_key, pack_key, wallet_address, price,
                "UNPAID", "NOT_STARTED", PurchaseStatus.PAYMENT_REQUIRED.value, now, now
            ))
            conn.commit()

            logger.info(f"[x402] creature pack purchase created: id={purchase_id} | pack={pack_key} | price={price} ALGO | wallet={wallet_address}")
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            return self._row_to_response(row)

    def confirm_purchase_payment(
        self,
        purchase_id: str,
        payment_tx_id: Optional[str] = None
    ) -> PurchaseResponse:
        """
        Called after x402 resource server has verified on-chain payment.
        Transitions state to PAID, rolls RewardEngine (exactly-once),
        mints 1-of-1 NFT, registers in owned_creatures, and delivers to user.
        """
        purchase = self.get_purchase(purchase_id)
        if purchase.status in [PurchaseStatus.DELIVERED, PurchaseStatus.WAITING_FOR_OPT_IN]:
            return purchase

        tx_id = payment_tx_id or f"tx_x402_{uuid.uuid4().hex[:12]}"

        with get_db() as conn:
            now = datetime.now(timezone.utc).isoformat()
            
            # Replay protection: Check if payment_tx_id already used on another purchase
            if payment_tx_id:
                existing_tx = conn.execute(
                    "SELECT purchase_id FROM purchases WHERE payment_tx_id = ? AND purchase_id != ?",
                    (payment_tx_id, purchase_id)
                ).fetchone()
                if existing_tx:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Payment transaction '{payment_tx_id}' was already redeemed for purchase '{existing_tx['purchase_id']}'."
                    )

            conn.execute("""
                UPDATE purchases 
                SET payment_status = ?, payment_tx_id = ?, status = ?, updated_at = ?
                WHERE purchase_id = ?;
            """, ("SETTLED_ON_ALGORAND_TESTNET", tx_id, PurchaseStatus.PAID.value, now, purchase_id))
            conn.commit()

            logger.info(f"[purchase] PAYMENT_CONFIRMED: id={purchase_id} | tx={tx_id}")

            # 1. Roll Creature Reward (Exactly-once)
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if not row["reward_id"]:
                reward_res = self.reward_engine.open_pack(purchase.pack_id, purchase_id=purchase_id)
                creature = reward_res.creature
                conn.execute("""
                    UPDATE purchases
                    SET reward_status = 'GENERATED', reward_id = ?, rarity = ?, 
                        creature_id = ?, creature_name = ?, creature_type = ?,
                        driver_id = ?, driver_name = ?, status = ?, updated_at = ?
                    WHERE purchase_id = ?;
                """, (
                    reward_res.reward_id, reward_res.rarity,
                    creature.id, creature.name, creature.primary_type,
                    creature.id, creature.name,
                    PurchaseStatus.REWARD_GENERATED.value, datetime.now(timezone.utc).isoformat(), purchase_id
                ))
                conn.commit()
                logger.info(f"[reward] selected creature: name={creature.name} | element={creature.primary_type} | rarity={reward_res.rarity} | id={reward_res.reward_id}")
            else:
                creature = creature_pool.get_creature(row["creature_id"] or row["driver_id"])

            # 2. Mint 1-of-1 NFT (Exactly-once)
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if not row["asset_id"]:
                logger.info(f"[nft] mint started: species={creature.name} | purchase={purchase_id}")
                asset_id, metadata_uri, mint_tx_id, mint_round = nft_service.mint_creature_nft(
                    template=creature,
                    purchase_id=purchase_id,
                    reward_id=row["reward_id"]
                )
                conn.execute("""
                    UPDATE purchases
                    SET asset_id = ?, metadata_uri = ?, mint_tx_id = ?, mint_round = ?, 
                        mint_status = 'MINT_CONFIRMED', status = ?, updated_at = ?
                    WHERE purchase_id = ?;
                """, (
                    asset_id, metadata_uri, mint_tx_id, mint_round,
                    PurchaseStatus.NFT_MINTED.value,
                    datetime.now(timezone.utc).isoformat(), purchase_id
                ))

                # Insert into owned_creatures table
                conn.execute("""
                    INSERT OR REPLACE INTO owned_creatures (
                        asset_id, wallet_address, template_id, name, primary_type, secondary_type,
                        faction, rarity, level, xp, hp, attack, defense, speed, stamina,
                        battle_wins, battle_losses, evolution_stage, mint_tx, delivery_tx,
                        metadata_uri, pokemon_id, ownership_verified, network, purchase_id, acquired_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, 1, 'testnet', ?, ?, ?);
                """, (
                    asset_id, purchase.wallet_address, creature.id, creature.name, creature.primary_type,
                    creature.secondary_type, creature.faction, creature.rarity,
                    creature.base_hp, creature.base_attack, creature.base_defense, creature.base_speed, creature.base_stamina,
                    creature.evolution_stage, mint_tx_id, None,
                    metadata_uri, int(creature.index_number) if str(creature.index_number).isdigit() else 1,
                    purchase_id, now, now
                ))

                conn.commit()
                logger.info(f"[nft] confirmed: asset_id={asset_id} | mint_tx={mint_tx_id} | metadata_uri={metadata_uri}")
            else:
                asset_id = row["asset_id"]

            # 3. Delivery
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if row["status"] != PurchaseStatus.DELIVERED.value:
                user_opted_in = nft_service.check_user_opted_in(purchase.wallet_address, asset_id)
                if user_opted_in:
                    success, delivery_tx = nft_service.transfer_nft_to_user(purchase.wallet_address, asset_id)
                    owns = nft_service.wallet_owns_asset(purchase.wallet_address, asset_id)
                    conn.execute("""
                        UPDATE purchases
                        SET delivery_tx_id = ?, delivery_status = 'DELIVERED', status = ?, updated_at = ?
                        WHERE purchase_id = ?;
                    """, (delivery_tx, PurchaseStatus.DELIVERED.value, datetime.now(timezone.utc).isoformat(), purchase_id))
                    conn.execute("""
                        UPDATE owned_creatures
                        SET delivery_tx = ?, ownership_verified = 1, updated_at = ?
                        WHERE asset_id = ?;
                    """, (delivery_tx, datetime.now(timezone.utc).isoformat(), asset_id))
                    conn.commit()
                    logger.info(f"[nft] delivered: tx={delivery_tx} | to={purchase.wallet_address} | verified={owns}")
                else:
                    conn.execute("""
                        UPDATE purchases
                        SET delivery_status = 'WAITING_FOR_OPT_IN', status = ?, updated_at = ?
                        WHERE purchase_id = ?;
                    """, (PurchaseStatus.WAITING_FOR_OPT_IN.value, datetime.now(timezone.utc).isoformat(), purchase_id))
                    conn.commit()

            final_row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            return self._row_to_response(final_row)

    def claim_nft_delivery(self, purchase_id: str) -> PurchaseResponse:
        """Called when user has opted into the ASA and claims delivery."""
        purchase = self.get_purchase(purchase_id)
        if purchase.status == PurchaseStatus.DELIVERED:
            return purchase
        if not purchase.asset_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No NFT minted for this purchase yet.")

        user_opted_in = nft_service.check_user_opted_in(purchase.wallet_address, purchase.asset_id)
        if not user_opted_in:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Wallet {purchase.wallet_address} has not yet opted into Asset #{purchase.asset_id} on TestNet."
            )

        success, delivery_tx = nft_service.transfer_nft_to_user(purchase.wallet_address, purchase.asset_id)
        with get_db() as conn:
            conn.execute("""
                UPDATE purchases
                SET delivery_tx_id = ?, delivery_status = 'DELIVERED', status = ?, updated_at = ?
                WHERE purchase_id = ?;
            """, (delivery_tx, PurchaseStatus.DELIVERED.value, datetime.now(timezone.utc).isoformat(), purchase_id))
            conn.execute("""
                UPDATE owned_creatures
                SET delivery_tx = ?, ownership_verified = 1, updated_at = ?
                WHERE asset_id = ?;
            """, (delivery_tx, datetime.now(timezone.utc).isoformat(), purchase.asset_id))
            conn.commit()

        return self.get_purchase(purchase_id)

    def reset_wallet_collection(self, wallet_address: str) -> Dict[str, Any]:
        """
        One-time development reset of a specific wallet's collection.
        Clears owned_creatures records, cancels open trades, archives purchase rewards for this wallet,
        while strictly preserving all master Pokédex templates and pack catalogs.
        """
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Algorand wallet address.")

        with get_db() as conn:
            # 1. Query owned creature asset IDs before clearing
            owned_rows = conn.execute(
                "SELECT asset_id, template_id, name, rarity FROM owned_creatures WHERE wallet_address = ?",
                (wallet_address,)
            ).fetchall()
            owned_count = len(owned_rows)
            cleared_asset_ids = [r["asset_id"] for r in owned_rows]

            # 2. Delete owned creatures records for this wallet
            conn.execute("DELETE FROM owned_creatures WHERE wallet_address = ?", (wallet_address,))

            # 3. Cancel any open trades initiated by or involving this wallet
            trades_cancelled = conn.execute("""
                UPDATE trades
                SET status = 'CANCELLED'
                WHERE (initiator_wallet = ? OR counterparty_wallet = ?)
                  AND status IN ('OPEN', 'PENDING', 'AWAITING_SIGNATURES');
            """, (wallet_address, wallet_address)).rowcount

            # 4. Archive development purchases so old rewards do not repopulate collection
            now_str = datetime.now(timezone.utc).isoformat()
            purchases_archived = conn.execute("""
                UPDATE purchases
                SET status = 'ARCHIVED_RESET', reward_status = 'ARCHIVED_RESET', updated_at = ?
                WHERE wallet_address = ?;
            """, (now_str, wallet_address)).rowcount

            conn.commit()

        logger.info(
            f"[DEV_RESET] Cleaned collection for wallet {wallet_address[:12]}...: "
            f"{owned_count} owned creatures removed, {trades_cancelled} trades cancelled, "
            f"{purchases_archived} purchases archived."
        )

        return {
            "wallet_address": wallet_address,
            "owned_records_cleared": owned_count,
            "trades_cancelled": trades_cancelled,
            "purchases_archived": purchases_archived,
            "cleared_asset_ids": cleared_asset_ids,
            "status": "RESET_SUCCESSFUL"
        }

    def complete_direct_purchase(
        self,
        pack_id: str,
        wallet_address: str,
        idempotency_key: Optional[str] = None
    ) -> PurchaseResponse:
        """Executes full purchase intent -> payment confirmation -> creature reward -> NFT mint -> delivery pipeline."""
        purchase = self.create_or_resume_purchase(pack_id, wallet_address, idempotency_key)
        if purchase.status in [PurchaseStatus.DELIVERED, PurchaseStatus.WAITING_FOR_OPT_IN]:
            return purchase
        return self.confirm_purchase_payment(purchase.purchase_id, f"tx_direct_{uuid.uuid4().hex[:12]}")

purchase_service = PurchaseService()
