"""
AlgoRacers — Session 9: x402 Purchase Pipeline
Module: api/v1/endpoints/purchases.py
=============================================
REST endpoints for initiating pack purchases, checking status,
claiming NFT deliveries, and querying user purchase history.
"""

from typing import List, Optional
from fastapi import APIRouter, Header, Body, Path, HTTPException, status
from backend.app.models.purchase import PurchaseCreateRequest, PurchaseResponse
from backend.app.services.purchase_service import purchase_service

router = APIRouter()

@router.post(
    "/packs/{pack_id}/purchase",
    response_model=PurchaseResponse,
    summary="Purchase Collectible Pack (x402 Guarded)",
    description="Initiates or completes a pack purchase. If unpaid, returns HTTP 402 challenge. If payment is verified, executes RewardEngine, mints 1-of-1 NFT, and delivers to wallet."
)
async def purchase_pack(
    pack_id: str = Path(..., examples=["basic"], description="Pack identifier ('basic' or 'premium')"),
    body: PurchaseCreateRequest = Body(...),
    x_402_payment_proof: Optional[str] = Header(None, alias="X-402-Payment-Proof"),
    authorization: Optional[str] = Header(None)
):
    return purchase_service.process_purchase_pipeline(
        pack_id=pack_id,
        wallet_address=body.wallet_address,
        idempotency_key=body.idempotency_key,
        x_402_payment_proof=x_402_payment_proof,
        authorization=authorization
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
