"""
AlgoRacers — Pack Purchases & NFT Delivery Endpoints
Module: api/v1/endpoints/purchases.py
=====================================================
REST endpoints for initiating pack purchases, fast checkout,
checking status, claiming NFT deliveries, and querying user purchase history.
"""

import json
import base64
from typing import List, Optional
from fastapi import APIRouter, Body, Path, HTTPException, status, Request, Response
from pydantic import BaseModel, Field
from backend.app.models.purchase import PurchaseCreateRequest, PurchaseResponse, PurchaseStatus
from backend.app.services.purchase_service import purchase_service
from backend.app.services.x402_service import x402_service

router = APIRouter()

class PurchaseIntentRequest(BaseModel):
    pack_id: str = Field(..., examples=["basic"], description="Pack identifier ('basic' or 'premium')")
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    idempotency_key: Optional[str] = Field(None, examples=["idem_9a8b7c6d5e4f"])

class PaymentConfirmationRequest(BaseModel):
    payment_tx_id: Optional[str] = None

@router.post(
    "/purchases",
    response_model=PurchaseResponse,
    summary="Create Purchase Intent",
    description="Initializes a pack purchase intent in PAYMENT_REQUIRED state, returning the unique purchase_id and price."
)
async def create_purchase(body: PurchaseIntentRequest = Body(...)):
    return purchase_service.create_or_resume_purchase(
        pack_id=body.pack_id,
        wallet_address=body.wallet_address,
        idempotency_key=body.idempotency_key
    )

@router.post(
    "/pay/purchases/{purchase_id}",
    response_model=PurchaseResponse,
    summary="x402 Pack Purchase Payment Resource",
    description="x402 protected resource endpoint for settling pack purchases using Algorand TestNet USDC."
)
async def pay_for_purchase(
    request: Request,
    response: Response,
    purchase_id: str = Path(..., examples=["pur_f47ac10b58cc"])
):
    purchase = purchase_service.get_purchase(purchase_id)
    
    # If already confirmed/delivered, return immediately
    if purchase.status not in [PurchaseStatus.PAYMENT_REQUIRED, PurchaseStatus.CREATED]:
        return purchase

    # Determine required price in micro-USDC (6 decimals)
    amount_micro_usdc = int(purchase.price_usdc * 1_000_000)
    resource_url = str(request.url)
    description = f"AlgoRacers Pack Purchase — {purchase.pack_id.capitalize()} Pack ({purchase.purchase_id})"

    payment_header = (
        request.headers.get("payment-signature") or 
        request.headers.get("PAYMENT-SIGNATURE") or 
        request.headers.get("x-402-payment-proof") or 
        request.headers.get("x-payment")
    )

    if not payment_header:
        challenge = x402_service.generate_challenge(
            resource_url=resource_url,
            description=description,
            amount_micro_usdc=amount_micro_usdc
        )
        b64_challenge = base64.b64encode(json.dumps(challenge).encode('utf-8')).decode('utf-8')
        
        headers = {
            "payment-required": b64_challenge,
            "WWW-Authenticate": "x402",
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "*, payment-required, payment-response, WWW-Authenticate"
        }
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=challenge,
            headers=headers
        )

    # Verify & Settle payment
    receipt = x402_service.verify_and_settle(
        payment_header=payment_header,
        resource_url=resource_url,
        required_amount_micro_usdc=amount_micro_usdc
    )

    b64_receipt = base64.b64encode(json.dumps(receipt).encode('utf-8')).decode('utf-8')
    response.headers["payment-response"] = b64_receipt

    # Confirm purchase payment and trigger reward engine & NFT minting
    confirmed_purchase = purchase_service.confirm_purchase_payment(
        purchase_id=purchase_id,
        payment_tx_id=receipt.get("transaction")
    )
    return confirmed_purchase

@router.get(
    "/internal/purchases/{purchase_id}/payment-requirements",
    summary="Get Internal Payment Requirements",
    description="Trusted internal endpoint to fetch price, asset, network, and payTo requirements."
)
async def get_internal_payment_requirements(
    purchase_id: str = Path(..., examples=["pur_f47ac10b58cc"])
):
    purchase = purchase_service.get_purchase(purchase_id)
    micro_units = int(purchase.price_usdc * 1_000_000)
    return {
        "purchase_id": purchase.purchase_id,
        "pack_id": purchase.pack_id,
        "wallet_address": purchase.wallet_address,
        "amount": purchase.price_usdc,
        "price_usdc": purchase.price_usdc,
        "price": f"${purchase.price_usdc}",
        "amount_micro_usdc": micro_units,
        "network": "algorand-testnet",
        "network_caip2": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        "asset": "USDC",
        "asset_id": 10458941,
        "pay_to": "GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4",
        "status": purchase.status.value
    }

@router.post(
    "/internal/purchases/{purchase_id}/payment-confirmed",
    response_model=PurchaseResponse,
    summary="Confirm Payment (Internal Gateway)",
    description="Called after on-chain TestNet payment is confirmed to transition state to PAID, trigger RewardEngine, and mint NFT."
)
async def internal_confirm_payment(
    purchase_id: str = Path(..., examples=["pur_f47ac10b58cc"]),
    body: Optional[PaymentConfirmationRequest] = Body(None)
):
    payment_tx = body.payment_tx_id if body else None
    return purchase_service.confirm_purchase_payment(purchase_id, payment_tx_id=payment_tx)

@router.post(
    "/purchases/direct",
    response_model=PurchaseResponse,
    summary="Direct Pack Purchase (Fast Checkout)",
    description="Directly purchases a pack, drops 2026 F1 driver card, and mints 1-of-1 ARC-3 NFT."
)
async def direct_purchase_pack(body: PurchaseIntentRequest = Body(...)):
    return purchase_service.complete_direct_purchase(
        pack_id=body.pack_id,
        wallet_address=body.wallet_address,
        idempotency_key=body.idempotency_key
    )

@router.post(
    "/purchases/{purchase_id}/complete",
    response_model=PurchaseResponse,
    summary="Complete Pack Purchase",
    description="Completes an initiated purchase intent, rolling rewards and minting NFT."
)
async def complete_purchase_intent(
    purchase_id: str = Path(..., examples=["pur_f47ac10b58cc"])
):
    purchase = purchase_service.get_purchase(purchase_id)
    return purchase_service.complete_direct_purchase(
        pack_id=purchase.pack_id,
        wallet_address=purchase.wallet_address,
        idempotency_key=purchase.idempotency_key
    )

@router.post(
    "/packs/{pack_id}/purchase",
    response_model=PurchaseResponse,
    summary="Purchase Collectible Pack",
    description="Purchases a pack, executes RewardEngine, mints 1-of-1 NFT, and delivers to wallet."
)
async def purchase_pack(
    pack_id: str = Path(..., examples=["basic"], description="Pack identifier ('basic' or 'premium')"),
    body: PurchaseCreateRequest = Body(...)
):
    return purchase_service.complete_direct_purchase(
        pack_id=pack_id,
        wallet_address=body.wallet_address,
        idempotency_key=body.idempotency_key
    )

@router.get(
    "/purchases/{purchase_id}",
    response_model=PurchaseResponse,
    summary="Get Purchase Status",
    description="Retrieves current state of a purchase (PAID, REWARD_GENERATED, NFT_MINTED, WAITING_FOR_OPT_IN, DELIVERED)."
)
async def get_purchase(
    purchase_id: str = Path(..., examples=["pur_f47ac10b58cc"])
):
    return purchase_service.get_purchase(purchase_id)

@router.post(
    "/purchases/{purchase_id}/claim",
    response_model=PurchaseResponse,
    summary="Claim NFT Delivery",
    description="Triggers NFT asset transfer after the buyer has approved opt-in via Pera Wallet."
)
async def claim_delivery(
    purchase_id: str = Path(..., examples=["pur_f47ac10b58cc"])
):
    return purchase_service.claim_nft_delivery(purchase_id)

@router.get(
    "/wallets/{wallet_address}/purchases",
    response_model=List[PurchaseResponse],
    summary="Get Wallet Purchase History",
    description="Retrieves all past pack purchases and collectible NFTs minted for a specific wallet address."
)
async def get_wallet_purchases(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return purchase_service.get_user_purchases(wallet_address)

