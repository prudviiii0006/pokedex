"""
AlgoCreatures — Collection & Deck Management Endpoints
Module: api/v1/endpoints/collection.py
======================================================
Endpoints for querying owned creature cards, battle statistics, and card details.
"""

from typing import List
from fastapi import APIRouter, Path, HTTPException, status
from backend.app.services.purchase_service import purchase_service
from backend.app.core.database import get_db

router = APIRouter()

@router.get(
    "/collection/{wallet_address}",
    summary="Get Wallet Creature Collection",
    description="Returns all owned creature cards with dynamic levels, XP, and stats for a given wallet."
)
async def get_wallet_collection(wallet_address: str = Path(..., description="Algorand 58-character public address")):
    return purchase_service.get_wallet_collection(wallet_address)

@router.get(
    "/collection/card/{asset_id}",
    summary="Get Single Card Details",
    description="Returns detailed progression and battle history for a specific owned creature card."
)
async def get_card_detail(asset_id: int = Path(..., description="Algorand ASA Asset ID")):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM owned_creatures WHERE asset_id = ?", (asset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Card Asset #{asset_id} not found.")
        return dict(row)

# Backward compatibility alias
@router.get("/wallets/{wallet_address}/drivers", include_in_schema=False)
async def get_wallet_drivers_compat(wallet_address: str = Path(...)):
    return purchase_service.get_wallet_collection(wallet_address)

@router.get("/wallets/{wallet_address}/purchases", summary="Get User Purchase History")
async def get_wallet_purchases(wallet_address: str = Path(...)):
    return purchase_service.get_user_purchases(wallet_address)

@router.post(
    "/collection/{wallet_address}/dev-reset",
    summary="Development Only: Reset Wallet Collection",
    description="One-time development cleanup: resets owned creature records, trade state, and purchase cache for the specified wallet."
)
@router.post(
    "/wallets/{wallet_address}/dev-reset",
    summary="Development Only: Reset Wallet Collection",
    include_in_schema=False
)
async def dev_reset_wallet_collection(
    wallet_address: str = Path(..., description="Algorand 58-character public address")
):
    return purchase_service.reset_wallet_collection(wallet_address)

