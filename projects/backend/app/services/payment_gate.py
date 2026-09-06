"""
AlgoRacers — Session 8: Real x402 Payments on Algorand TestNet
Module: services/payment_gate.py
=============================================================
Unified x402 Payment Gate with Algorand Layer-1 AVM Verification and Settlement.
Handles:
  1. 402 Challenge generation specifying TestNet USDC (Asset ID 10458941)
  2. Cryptographic transaction verification (AVM Ed25519 signatures & ASA params)
  3. Layer-1 blockchain settlement on Algorand TestNet
  4. Nonce / TxID replay protection
"""

import json
import base64
from datetime import datetime, timezone
from typing import Optional, Dict, Set
from fastapi import Header, HTTPException, status

from backend.app.core.config import settings
from backend.app.models.x402 import (
    PaymentRequirement,
    PaymentRequiredResponse,
    MockPaymentProof
)
from backend.app.services.x402_avm import (
    avm_engine, 
    TESTNET_USDC_ASSET_ID, 
    DEFAULT_TREASURY_RECIPIENT
)

class PaymentGateService:
    def __init__(self):
        # In-memory record of used nonces / TxIDs to prevent double-spending & replay attacks
        self.used_tx_ids: Set[str] = set()

    def build_payment_challenge(
        self, 
        resource_path: str, 
        amount: float = 0.01, 
        asset: str = "USDC"
    ) -> PaymentRequiredResponse:
        """Constructs the official Algorand TestNet x402 challenge envelope."""
        micro_units = int(amount * 1_000_000)
        requirements = PaymentRequirement(
            scheme="exact_payment",
            network="algorand-testnet",
            asset=asset,
            amount=amount,
            amount_units=f"{micro_units} microUSDC (ASA ID: {TESTNET_USDC_ASSET_ID})",
            recipient=DEFAULT_TREASURY_RECIPIENT,
            resource=resource_path,
            expiration_seconds=300
        )
        return PaymentRequiredResponse(
            error="payment_required",
            message=f"Access to '{resource_path}' requires {amount} {asset} on Algorand TestNet.",
            payment_requirements=requirements,
            protocol="x402/1.0",
            mode="algorand_testnet_avm"
        )

    def raise_402_challenge(self, resource_path: str, amount: float = 0.01, asset: str = "USDC") -> None:
        """Raises a FastAPI HTTPException with HTTP 402 and WWW-Authenticate headers."""
        challenge = self.build_payment_challenge(resource_path, amount, asset)
        challenge_b64 = base64.b64encode(json.dumps(challenge.model_dump()).encode("utf-8")).decode("utf-8")
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=challenge.model_dump(),
            headers={
                "WWW-Authenticate": f'x402 realm="AlgoRacers", network="algorand-testnet", asset="{asset}", asset_id="{TESTNET_USDC_ASSET_ID}", amount="{amount}", recipient="{DEFAULT_TREASURY_RECIPIENT}"',
                "X-402-Protocol": "2.0",
                "X-402-Network": "algorand-testnet",
                "X-402-Asset-ID": str(TESTNET_USDC_ASSET_ID),
                "PAYMENT-REQUIRED": challenge_b64,
                "Access-Control-Expose-Headers": "WWW-Authenticate, X-402-Protocol, X-402-Network, X-402-Asset-ID, PAYMENT-REQUIRED, PAYMENT-RESPONSE"
            }
        )

    def verify_and_settle_payment(
        self,
        resource_path: str,
        required_amount_usdc: float = 0.01,
        x_402_payment_proof: Optional[str] = None,
        authorization: Optional[str] = None,
        settle_on_chain: bool = True
    ) -> Dict[str, str]:
        """
        Unified verification & settlement engine.
        Accepts:
          A. Real Algorand signed transaction (base64 encoded or inside JSON)
          B. Mock development proof (for unit tests / mock mode)
        """
        raw_proof = x_402_payment_proof or authorization
        if not raw_proof:
            self.raise_402_challenge(resource_path, required_amount_usdc)

        # Normalize prefix
        if raw_proof.startswith("x402 "):
            raw_proof = raw_proof[5:].strip()
        elif raw_proof.startswith("Bearer "):
            raw_proof = raw_proof[7:].strip()

        required_micro_usdc = int(required_amount_usdc * 1_000_000)

        # -------------------------------------------------------------
        # BRANCH A: REAL ALGORAND SIGNED TRANSACTION
        # -------------------------------------------------------------
        if raw_proof.startswith("algorand:") or "signed_txn" in raw_proof:
            # Extract raw base64 transaction string
            signed_b64 = raw_proof.replace("algorand:", "").strip()
            if signed_b64.startswith("{"):
                try:
                    payload = json.loads(signed_b64)
                    signed_b64 = payload.get("signed_txn", signed_b64)
                except Exception:
                    pass

            # 1. VERIFY
            valid, msg, txn_info = avm_engine.verify_payment_transaction(
                signed_b64, 
                required_micro_usdc
            )
            if not valid:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

            tx_id = txn_info["tx_id"]

            # Replay Protection Check
            if tx_id in self.used_tx_ids:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Replay attack detected: Transaction ID '{tx_id}' has already been redeemed."
                )

            # 2. SETTLE ON-CHAIN
            confirmed_round = 0
            if settle_on_chain and "raw_bytes" in txn_info:
                settled, s_msg, s_info = avm_engine.settle_payment_on_chain(txn_info["raw_bytes"])
                if not settled:
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=s_msg)
                confirmed_round = s_info.get("confirmed_round", 0)

            # Record spent transaction ID
            self.used_tx_ids.add(tx_id)

            return {
                "receipt_id": f"rcpt_{tx_id[:12]}",
                "payer": txn_info["sender"],
                "settled_amount": f"{txn_info['amount_usdc']} USDC",
                "asset_id": str(TESTNET_USDC_ASSET_ID),
                "recipient": txn_info["receiver"],
                "tx_id": tx_id,
                "confirmed_round": str(confirmed_round),
                "explorer_url": f"https://testnet.explorer.perawallet.app/tx/{tx_id}",
                "resource": resource_path,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "verification_status": "SETTLED_ON_ALGORAND_TESTNET"
            }

        # -------------------------------------------------------------
        # BRANCH B: MOCK LEARNING PROOF (FOR BACKWARD COMPATIBILITY / TESTS)
        # -------------------------------------------------------------
        proof_dict = None
        try:
            if raw_proof.startswith("{"):
                proof_dict = json.loads(raw_proof)
            else:
                try:
                    decoded = base64.b64decode(raw_proof).decode("utf-8")
                    proof_dict = json.loads(decoded)
                except Exception:
                    # Fallback for plain tokens
                    proof_dict = {
                        "client_address": raw_proof.split("_")[2] if len(raw_proof.split("_")) > 2 else DEFAULT_TREASURY_RECIPIENT,
                        "amount": required_amount_usdc,
                        "asset": "USDC",
                        "nonce": raw_proof,
                        "signature": "sig_auto_fallback"
                    }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Malformed x402 payment proof: Unable to parse payload ({str(e)})"
            )

        try:
            proof = MockPaymentProof(**proof_dict)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid x402 payment proof structure: {str(e)}"
            )

        if proof.amount < required_amount_usdc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient payment authorized: required {required_amount_usdc} USDC, received {proof.amount} USDC."
            )

        if proof.nonce in self.used_tx_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Replay attack detected: Payment proof nonce '{proof.nonce}' has already been redeemed."
            )

        self.used_tx_ids.add(proof.nonce)

        return {
            "receipt_id": f"rcpt_{proof.nonce[:8]}",
            "payer": proof.client_address,
            "settled_amount": f"{proof.amount} {proof.asset}",
            "asset_id": str(TESTNET_USDC_ASSET_ID),
            "recipient": DEFAULT_TREASURY_RECIPIENT,
            "tx_id": proof.nonce,
            "confirmed_round": "mock_round",
            "explorer_url": f"https://testnet.explorer.perawallet.app/tx/{proof.nonce}",
            "resource": resource_path,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "verification_status": "VERIFIED_MOCK_PROOF"
        }

payment_gate = PaymentGateService()
