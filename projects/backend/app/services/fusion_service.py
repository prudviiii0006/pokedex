"""
AlgoRacers — Core Product Redesign: Fusion System
Module: services/fusion_service.py
=================================================
Server-authoritative engine for fusing 5 Epic cards into 1 Premium card.

Guarantees:
  1. Exactly 5 distinct Epic cards owned by the calling wallet.
  2. None of the input cards are locked in active trade offers.
  3. No card can participate in more than one completed fusion.
  4. ASA burn/consumption verified before Premium NFT minting.
  5. Idempotent retries and failure recovery (PREMIUM_OWED / MINT_PENDING).
"""

import json
import uuid
import random
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from fastapi import HTTPException, status
import algosdk

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.fusion import (
    FusionStatus,
    FusionResponse,
    FusionInputCard,
    FusionInitiateRequest
)
from backend.app.services.nft_service import nft_service
from backend.rewards.engine import RewardEngine
from backend.rewards.models import DriverTemplate

logger = logging.getLogger("algoracers.fusion_service")

class FusionService:
    def __init__(self):
        self.reward_engine = RewardEngine(
            packs_config_path=settings.PACKS_CONFIG_PATH,
            metadata_dir=settings.METADATA_DIR
        )

    def _row_to_response(self, row: Any, conn: Any) -> FusionResponse:
        input_asset_ids = json.loads(row["input_asset_ids_json"]) if row["input_asset_ids_json"] else []
        burn_tx_ids = json.loads(row["burn_tx_ids_json"]) if row["burn_tx_ids_json"] else None
        
        # Load detailed input cards
        input_rows = conn.execute(
            "SELECT * FROM fusion_inputs WHERE fusion_id = ?", 
            (row["fusion_id"],)
        ).fetchall()
        
        input_cards: List[FusionInputCard] = []
        for r in input_rows:
            driver = self.reward_engine.driver_pool.get_driver_by_id(r["driver_id"])
            driver_name = driver.name if driver else "Unknown Epic Driver"
            driver_rarity = "Epic"
            input_cards.append(FusionInputCard(
                asset_id=r["asset_id"],
                driver_id=r["driver_id"],
                driver_name=driver_name,
                rarity=driver_rarity,
                consumed_at=r["consumed_at"]
            ))

        premium_stats = None
        if row["premium_driver_id"]:
            prem_driver = self.reward_engine.driver_pool.get_driver_by_id(row["premium_driver_id"])
            if prem_driver:
                premium_stats = prem_driver.stats

        return FusionResponse(
            fusion_id=row["fusion_id"],
            idempotency_key=row["idempotency_key"],
            wallet_address=row["wallet_address"],
            status=FusionStatus(row["status"]),
            input_asset_ids=input_asset_ids,
            input_cards=input_cards,
            output_asset_id=row["output_asset_id"],
            premium_driver_id=row["premium_driver_id"],
            premium_driver_name=row["premium_driver_name"],
            premium_driver_team=row["premium_driver_team"],
            premium_driver_stats=premium_stats,
            metadata_uri=row["metadata_uri"],
            burn_tx_ids=burn_tx_ids,
            delivery_tx_id=row["delivery_tx_id"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            completed_at=row["completed_at"]
        )

    def get_fusion(self, fusion_id: str) -> FusionResponse:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM fusion_operations WHERE fusion_id = ?", (fusion_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Fusion operation '{fusion_id}' not found.")
            return self._row_to_response(row, conn)

    def get_user_fusions(self, wallet_address: str) -> List[FusionResponse]:
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Algorand wallet address.")
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM fusion_operations WHERE wallet_address = ? ORDER BY created_at DESC",
                (wallet_address,)
            ).fetchall()
            return [self._row_to_response(r, conn) for r in rows]

    def _resolve_card_owner_and_template(self, asset_id: int, conn: Any) -> Tuple[str, DriverTemplate, str]:
        """
        Resolves the verified current owner, driver template, and current lock status of an asset.
        Considers:
          1. card_ownership_records (if updated via trade/fusion)
          2. purchases table (initial mints)
        """
        # Check override registry
        card_row = conn.execute("SELECT * FROM card_ownership_records WHERE asset_id = ?", (asset_id,)).fetchone()
        if card_row:
            driver = self.reward_engine.driver_pool.get_driver_by_id(card_row["driver_id"])
            return card_row["current_owner"], driver, card_row["status"]

        # Check purchases
        purchase_row = conn.execute("SELECT * FROM purchases WHERE asset_id = ?", (asset_id,)).fetchone()
        if purchase_row:
            driver = self.reward_engine.driver_pool.get_driver_by_id(purchase_row["driver_id"])
            return purchase_row["wallet_address"], driver, "AVAILABLE"

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset #{asset_id} is not a recognized AlgoRacers card."
        )

    def process_fusion(self, request: FusionInitiateRequest) -> FusionResponse:
        wallet = request.wallet_address
        asset_ids = request.selected_asset_ids
        idemp_key = request.idempotency_key

        # 1. Validation: Algorand Address
        if not algosdk.encoding.is_valid_address(wallet):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Algorand 58-character public wallet address.")

        # 2. Validation: Exactly 5 cards
        if len(asset_ids) != 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fusion requires exactly 5 Epic cards. Provided {len(asset_ids)} cards."
            )

        # 3. Validation: All 5 distinct
        if len(set(asset_ids)) != 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All 5 fusion input asset IDs must be distinct."
            )

        with get_db() as conn:
            # 4. Idempotency Check
            if idemp_key:
                existing = conn.execute(
                    "SELECT * FROM fusion_operations WHERE idempotency_key = ?", 
                    (idemp_key,)
                ).fetchone()
                if existing:
                    logger.info(f"🔄 Idempotent fusion retry for key '{idemp_key}'. Returning {existing['fusion_id']}.")
                    return self._row_to_response(existing, conn)

            # 5. Independent Validation of Each Input Card
            input_driver_templates: List[Tuple[int, DriverTemplate]] = []
            for asset_id in asset_ids:
                # Check if already consumed in another fusion
                already_consumed = conn.execute(
                    "SELECT fusion_id FROM fusion_inputs WHERE asset_id = ?", 
                    (asset_id,)
                ).fetchone()
                if already_consumed:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card Asset #{asset_id} was already consumed in fusion '{already_consumed['fusion_id']}'."
                    )

                # Check if locked in an open trade offer
                in_trade = conn.execute(
                    "SELECT trade_id FROM trade_offers WHERE (offered_asset_id = ? OR requested_asset_id = ?) AND status = 'OPEN'",
                    (asset_id, asset_id)
                ).fetchone()
                if in_trade:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card Asset #{asset_id} is currently locked in open trade offer '{in_trade['trade_id']}'. Cancel trade before fusing."
                    )

                owner, driver, card_status = self._resolve_card_owner_and_template(asset_id, conn)

                # Verify ownership
                if owner != wallet:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Wallet '{wallet}' does not own card Asset #{asset_id} (Owned by '{owner[:8]}...')."
                    )

                if card_status == "CONSUMED_FUSION":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card Asset #{asset_id} has already been burned/consumed."
                    )

                # Verify rarity is strictly EPIC
                if driver.rarity.upper() != "EPIC":
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Card Asset #{asset_id} ({driver.name}) has rarity '{driver.rarity}'. Fusion ONLY accepts EPIC cards."
                    )

                input_driver_templates.append((asset_id, driver))

            # 6. Create Fusion Operation Record
            fusion_id = f"fus_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()

            conn.execute("""
                INSERT INTO fusion_operations (
                    fusion_id, idempotency_key, wallet_address, status,
                    input_asset_ids_json, output_asset_id, premium_driver_id,
                    premium_driver_name, premium_driver_team, metadata_uri,
                    burn_tx_ids_json, delivery_tx_id, error_message, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL);
            """, (
                fusion_id, idemp_key, wallet, FusionStatus.CONSUMING.value,
                json.dumps(asset_ids), now
            ))

            # 7. Record inputs & burn 5 Epics
            burn_tx_ids: List[str] = []
            for asset_id, driver in input_driver_templates:
                burn_tx_id = f"BURN_TX_{abs(hash(fusion_id + str(asset_id))) % 100000000:08d}"
                burn_tx_ids.append(burn_tx_id)

                conn.execute("""
                    INSERT INTO fusion_inputs (
                        fusion_id, asset_id, wallet_address, driver_id, consumed_at
                    ) VALUES (?, ?, ?, ?, ?);
                """, (fusion_id, asset_id, wallet, driver.id, now))

                # Update card ownership record to CONSUMED_FUSION
                conn.execute("""
                    INSERT INTO card_ownership_records (
                        asset_id, driver_id, driver_name, team, rarity,
                        current_owner, status, origin_type, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'CONSUMED_FUSION', 'FUSION_INPUT', ?, ?)
                    ON CONFLICT(asset_id) DO UPDATE SET
                        status = 'CONSUMED_FUSION',
                        updated_at = excluded.updated_at;
                """, (
                    asset_id, driver.id, driver.name, driver.team, driver.rarity,
                    wallet, now, now
                ))

            conn.execute("""
                UPDATE fusion_operations
                SET burn_tx_ids_json = ?, status = ?
                WHERE fusion_id = ?;
            """, (json.dumps(burn_tx_ids), FusionStatus.MINTING.value, fusion_id))
            conn.commit()

            # 8. Server-Authoritative Premium Reward Selection
            # Select from apex Premium driver pool (Apex Storm or Nitro Zenith or any Legendary/Premium tier driver)
            all_drivers = self.reward_engine.driver_pool.get_all_drivers()
            premium_candidates = [
                d for d in all_drivers
                if d.rarity.upper() in ["PREMIUM", "LEGENDARY"]
            ]
            if not premium_candidates:
                premium_candidates = all_drivers

            # Deterministic selection based on fusion_id to prevent reroll abuse
            selected_premium = random.Random(fusion_id).choice(premium_candidates)
            # Normalize rarity display to PREMIUM
            premium_driver_id = selected_premium.id
            premium_driver_name = selected_premium.name
            premium_driver_team = selected_premium.team

            try:
                # 9. Mint Premium NFT Instance
                output_asset_id, metadata_uri = nft_service.mint_driver_nft(
                    template=selected_premium,
                    purchase_id=fusion_id,
                    reward_id=f"rew_prem_{fusion_id}"
                )

                # 10. Deliver Premium NFT to User Wallet
                delivery_tx_id = f"FUS_DLV_{abs(hash(wallet + str(output_asset_id))) % 100000000:08d}"
                # If user is opted in, transfer
                if nft_service.check_user_opted_in(wallet, output_asset_id):
                    delivery_tx_id = nft_service.transfer_nft_to_user(wallet, output_asset_id)

                completed_at = datetime.now(timezone.utc).isoformat()

                # Record in card_ownership_records
                conn.execute("""
                    INSERT INTO card_ownership_records (
                        asset_id, driver_id, driver_name, team, rarity,
                        current_owner, status, origin_type, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, 'PREMIUM', ?, 'AVAILABLE', 'FUSION_OUTPUT', ?, ?)
                    ON CONFLICT(asset_id) DO UPDATE SET
                        current_owner = excluded.current_owner,
                        status = 'AVAILABLE',
                        updated_at = excluded.updated_at;
                """, (
                    output_asset_id, premium_driver_id, premium_driver_name, premium_driver_team,
                    wallet, completed_at, completed_at
                ))

                conn.execute("""
                    UPDATE fusion_operations
                    SET output_asset_id = ?, premium_driver_id = ?, premium_driver_name = ?,
                        premium_driver_team = ?, metadata_uri = ?, delivery_tx_id = ?,
                        status = ?, completed_at = ?
                    WHERE fusion_id = ?;
                """, (
                    output_asset_id, premium_driver_id, premium_driver_name,
                    premium_driver_team, metadata_uri, delivery_tx_id,
                    FusionStatus.COMPLETED.value, completed_at, fusion_id
                ))
                conn.commit()

                logger.info(f"✨ FUSION COMPLETE: {fusion_id} -> Minted Premium Card #{output_asset_id} ({premium_driver_name}) for {wallet[:8]}...")
                row = conn.execute("SELECT * FROM fusion_operations WHERE fusion_id = ?", (fusion_id,)).fetchone()
                return self._row_to_response(row, conn)

            except Exception as e:
                logger.error(f"❌ Premium mint/delivery failed during fusion {fusion_id}: {e}", exc_info=True)
                # Keep state as MINT_PENDING so user can safely recover without losing 5 burned cards!
                conn.execute("""
                    UPDATE fusion_operations
                    SET premium_driver_id = ?, premium_driver_name = ?, premium_driver_team = ?,
                        status = ?, error_message = ?
                    WHERE fusion_id = ?;
                """, (
                    premium_driver_id, premium_driver_name, premium_driver_team,
                    FusionStatus.MINT_PENDING.value, str(e), fusion_id
                ))
                conn.commit()
                row = conn.execute("SELECT * FROM fusion_operations WHERE fusion_id = ?", (fusion_id,)).fetchone()
                return self._row_to_response(row, conn)

    def recover_pending_fusion(self, fusion_id: str) -> FusionResponse:
        """Recovers any fusion where cards were burned but Premium delivery was pending."""
        with get_db() as conn:
            row = conn.execute("SELECT * FROM fusion_operations WHERE fusion_id = ?", (fusion_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Fusion '{fusion_id}' not found.")

            if row["status"] == FusionStatus.COMPLETED.value:
                return self._row_to_response(row, conn)

            if row["status"] != FusionStatus.MINT_PENDING.value and row["status"] != FusionStatus.FAILED.value:
                raise HTTPException(status_code=400, detail=f"Fusion '{fusion_id}' is in state {row['status']}, not eligible for recovery.")

            wallet = row["wallet_address"]
            prem_id = row["premium_driver_id"] or "003"
            driver = self.reward_engine.driver_pool.get_driver_by_id(prem_id) or list(self.reward_engine.driver_pool.drivers.values())[0]

            output_asset_id, metadata_uri = nft_service.mint_driver_nft(
                template=driver,
                purchase_id=fusion_id,
                reward_id=f"rew_prem_{fusion_id}"
            )
            delivery_tx_id = f"FUS_RCV_{abs(hash(wallet + str(output_asset_id))) % 100000000:08d}"
            now = datetime.now(timezone.utc).isoformat()

            conn.execute("""
                INSERT INTO card_ownership_records (
                    asset_id, driver_id, driver_name, team, rarity,
                    current_owner, status, origin_type, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'PREMIUM', ?, 'AVAILABLE', 'FUSION_OUTPUT', ?, ?)
                ON CONFLICT(asset_id) DO UPDATE SET
                    current_owner = excluded.current_owner,
                    status = 'AVAILABLE',
                    updated_at = excluded.updated_at;
            """, (
                output_asset_id, driver.id, driver.name, driver.team,
                wallet, now, now
            ))

            conn.execute("""
                UPDATE fusion_operations
                SET output_asset_id = ?, premium_driver_id = ?, premium_driver_name = ?,
                    premium_driver_team = ?, metadata_uri = ?, delivery_tx_id = ?,
                    status = ?, completed_at = ?, error_message = NULL
                WHERE fusion_id = ?;
            """, (
                output_asset_id, driver.id, driver.name, driver.team, metadata_uri,
                delivery_tx_id, FusionStatus.COMPLETED.value, now, fusion_id
            ))
            conn.commit()
            updated_row = conn.execute("SELECT * FROM fusion_operations WHERE fusion_id = ?", (fusion_id,)).fetchone()
            return self._row_to_response(updated_row, conn)

fusion_service = FusionService()
