"""
AlgoRacers — Session 21: Blockchain Activity Feed Endpoints
Module: api/v1/endpoints/activity.py
===========================================================
Provides public and wallet-specific feeds of confirmed on-chain events.
"""

from typing import List
from fastapi import APIRouter, Path, Query
from backend.app.chain.models import ActivityFeedItem
from backend.app.services.activity_service import activity_service

router = APIRouter()

@router.get(
    "",
    response_model=List[ActivityFeedItem],
    summary="Get Global Activity Feed",
    description="Returns the latest decoded on-chain events across all AlgoRacers smart contracts and ASAs."
)
async def get_global_activity(
    limit: int = Query(20, ge=1, le=100, description="Max items to return")
):
    return activity_service.get_global_activity(limit=limit)

@router.get(
    "/wallets/{wallet_address}",
    response_model=List[ActivityFeedItem],
    summary="Get Wallet Activity Feed",
    description="Returns on-chain transactions and events involving a specific player wallet."
)
async def get_wallet_activity(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"]),
    limit: int = Query(20, ge=1, le=100)
):
    return activity_service.get_wallet_activity(wallet_address=wallet_address, limit=limit)
