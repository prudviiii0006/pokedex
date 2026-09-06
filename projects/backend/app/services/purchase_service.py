"""
AlgoRacers — Session 9: x402 Purchase Pipeline
Module: services/purchase_service.py
=============================================
Orchestrates the complete Purchase -> x402 Payment -> Reward Engine -> NFT Mint -> Delivery pipeline.
Enforces strict idempotency, state machine transitions, and database unique constraints.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
import algosdk

from backend.app.core.database import get_db
from backend.app.models.purchase import PurchaseResponse, PurchaseStatus
from backend.app.services.payment_gate import payment_gate
from backend.app.services.nft_service import nft_service
from backend.rewards.engine import RewardEngine
from backend.app.core.config import settings

logger = logging.getLogger("algoracers.purchase_service")

# TestNet Pack Pricing (USDC)
PACK_PRICING = {
    "basic": 0.01,    # 10,000 microUSDC
    "premium": 0.05   # 50,000 microUSDC
}

class PurchaseService:
    def __init__(self):
        self.reward_engine = RewardEngine(
            packs_config_path=settings.PACKS_CONFIG_PATH,
            metadata_dir=settings.METADATA_DIR
        )

    def _row_to_response(self, row: Any) -> PurchaseResponse:
        return PurchaseResponse(
            purchase_id=row["purchase_id"],
            idempotency_key=row["idempotency_key"],
            pack_id=row["pack_id"],
            wallet_address=row["wallet_address"],
            price_usdc=row["price_usdc"],
            currency="USDC",
            status=PurchaseStatus(row["status"]),
            payment_status=row["payment_status"],
            payment_tx_id=row["payment_tx_id"],
            reward_status=row["reward_status"],
            reward_id=row["reward_id"],
            rarity=row["rarity"],
            driver_id=row["driver_id"],
            driver_name=row["driver_name"],
            metadata_uri=row["metadata_uri"],
            asset_id=row["asset_id"],
            delivery_tx_id=row["delivery_tx_id"],
            error_message=row["error_message"],
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
            # 1. IDEMPOTENCY CHECK: If idempotency_key already exists, return existing purchase!
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
                    rarity, driver_id, driver_name, metadata_uri, asset_id,
                    delivery_tx_id, status, error_message, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL, ?, NULL, ?, ?);
            """, (
                purchase_id, idempotency_key, pack_key, wallet_address, price,
                "UNPAID", "NOT_STARTED", PurchaseStatus.PAYMENT_REQUIRED.value, now, now
            ))
            conn.commit()

            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            return self._row_to_response(row)

    def process_purchase_pipeline(
        self,
        pack_id: str,
        wallet_address: str,
        idempotency_key: Optional[str] = None,
        x_402_payment_proof: Optional[str] = None,
        authorization: Optional[str] = None
    ) -> PurchaseResponse:
        """
        FULL PIPELINE:
          1. Create/Resume Purchase Intent
          2. Check for x402 payment proof (if absent, raises 402 challenge)
          3. Settle Payment on Algorand TestNet
          4. Trigger RewardEngine (Exactly-once)
          5. Mint 1-of-1 NFT (Exactly-once)
          6. Deliver or transition to WAITING_FOR_OPT_IN
        """
        # 1. Create or retrieve existing purchase
        purchase = self.create_or_resume_purchase(pack_id, wallet_address, idempotency_key)
        purchase_id = purchase.purchase_id
        price_usdc = purchase.price_usdc

        # 2. Check if already fulfilled (IDEMPOTENCY GUARD)
        if purchase.status in [PurchaseStatus.DELIVERED, PurchaseStatus.WAITING_FOR_OPT_IN]:
            logger.info(f"✅ Purchase {purchase_id} is already in state {purchase.status.value}. Returning existing record.")
            return purchase

        # 3. PAYMENT VERIFICATION & SETTLEMENT
        if not (x_402_payment_proof or authorization):
            # No payment proof provided -> Raise HTTP 402 Payment Required
            payment_gate.raise_402_challenge(
                resource_path=f"/packs/{pack_id}/purchase",
                amount=price_usdc,
                asset="USDC"
            )

        # Verify payment
        receipt = payment_gate.verify_and_settle_payment(
            resource_path=f"/packs/{pack_id}/purchase",
            required_amount_usdc=price_usdc,
            x_402_payment_proof=x_402_payment_proof,
            authorization=authorization,
            settle_on_chain=False  # Handled transparently
        )
        payment_tx_id = receipt["tx_id"]

        with get_db() as conn:
            now = datetime.now(timezone.utc).isoformat()

            # Check if payment_tx_id was already bound to ANOTHER purchase
            existing_tx = conn.execute(
                "SELECT purchase_id FROM purchases WHERE payment_tx_id = ? AND purchase_id != ?",
                (payment_tx_id, purchase_id)
            ).fetchone()
            if existing_tx:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Payment transaction '{payment_tx_id}' was already redeemed for purchase '{existing_tx['purchase_id']}'."
                )

            # Update to PAID
            conn.execute("""
                UPDATE purchases 
                SET payment_status = ?, payment_tx_id = ?, status = ?, updated_at = ?
                WHERE purchase_id = ?;
            """, ("SETTLED_ON_ALGORAND_TESTNET", payment_tx_id, PurchaseStatus.PAID.value, now, purchase_id))
            conn.commit()

            # 4. REWARD GENERATION (EXACTLY ONCE)
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if not row["reward_id"]:
                reward_res = self.reward_engine.open_pack(pack_id, purchase_id=purchase_id)
                driver = reward_res.driver
                
                conn.execute("""
                    UPDATE purchases
                    SET reward_status = 'GENERATED', reward_id = ?, rarity = ?, driver_id = ?, driver_name = ?, status = ?, updated_at = ?
                    WHERE purchase_id = ?;
                """, (
                    reward_res.reward_id, reward_res.rarity, driver.id, driver.name,
                    PurchaseStatus.REWARD_GENERATED.value, datetime.now(timezone.utc).isoformat(), purchase_id
                ))
                conn.commit()
            else:
                # Reuse existing reward!
                driver = self.reward_engine.pool.get_driver_by_id(row["driver_id"])

            # 5. NFT MINTING (EXACTLY ONCE)
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if not row["asset_id"]:
                asset_id, metadata_uri = nft_service.mint_driver_nft(
                    template=driver,
                    purchase_id=purchase_id,
                    reward_id=row["reward_id"]
                )
                conn.execute("""
                    UPDATE purchases
                    SET asset_id = ?, metadata_uri = ?, status = ?, updated_at = ?
                    WHERE purchase_id = ?;
                """, (
                    asset_id, metadata_uri, PurchaseStatus.NFT_MINTED.value,
                    datetime.now(timezone.utc).isoformat(), purchase_id
                ))
                conn.commit()
            else:
                asset_id = row["asset_id"]

            # 6. DELIVERY & OPT-IN CHECK
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            if row["status"] != PurchaseStatus.DELIVERED.value:
                # Check if user wallet has opted into asset_id
                user_opted_in = nft_service.check_user_opted_in(wallet_address, asset_id)
                if user_opted_in:
                    delivery_tx = nft_service.transfer_nft_to_user(wallet_address, asset_id)
                    conn.execute("""
                        UPDATE purchases
                        SET delivery_tx_id = ?, status = ?, updated_at = ?
                        WHERE purchase_id = ?;
                    """, (delivery_tx, PurchaseStatus.DELIVERED.value, datetime.now(timezone.utc).isoformat(), purchase_id))
                    conn.commit()
                else:
                    conn.execute("""
                        UPDATE purchases
                        SET status = ?, updated_at = ?
                        WHERE purchase_id = ?;
                    """, (PurchaseStatus.WAITING_FOR_OPT_IN.value, datetime.now(timezone.utc).isoformat(), purchase_id))
                    conn.commit()

            final_row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            return self._row_to_response(final_row)

    def claim_nft_delivery(self, purchase_id: str) -> PurchaseResponse:
        """
        Called after the user signs the NFT opt-in transaction through Pera Wallet.
        Re-verifies on-chain opt-in status and transfers the NFT instance.
        """
        purchase = self.get_purchase(purchase_id)
        if purchase.status == PurchaseStatus.DELIVERED:
            return purchase

        if not purchase.asset_id:
            raise HTTPException(status_code=400, detail="NFT has not yet been minted for this purchase.")

        # Check on-chain opt-in
        opted_in = nft_service.check_user_opted_in(purchase.wallet_address, purchase.asset_id)
        if not opted_in:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Wallet '{purchase.wallet_address}' has not yet opted into Asset ID {purchase.asset_id}. Please approve opt-in in Pera Wallet."
            )

        delivery_tx = nft_service.transfer_nft_to_user(purchase.wallet_address, purchase.asset_id)
        with get_db() as conn:
            conn.execute("""
                UPDATE purchases
                SET delivery_tx_id = ?, status = ?, updated_at = ?
                WHERE purchase_id = ?;
            """, (delivery_tx, PurchaseStatus.DELIVERED.value, datetime.now(timezone.utc).isoformat(), purchase_id))
            conn.commit()
            row = conn.execute("SELECT * FROM purchases WHERE purchase_id = ?", (purchase_id,)).fetchone()
            return self._row_to_response(row)

purchase_service = PurchaseService()
