"""
AlgoRacers — Core Product Redesign: Trading Endpoints
Module: api/v1/endpoints/trading.py
====================================================
REST endpoints for browsing available trades, creating card-for-card offers,
accepting trades via atomic swap, cancelling offers, and inspecting trade state.
"""

from typing import List, Optional
from fastapi import APIRouter, Path, Query, Body, HTTPException, status, Depends
from backend.app.models.trading import (
    CreateTradeRequest,
    AcceptTradeRequest,
    TradeOfferResponse
)
from backend.app.services.trading_service import trading_service
from backend.app.core.security import get_optional_wallet

router = APIRouter()

@router.get(
    "/trades",
    response_model=List[TradeOfferResponse],
    summary="List Open Trades in Marketplace",
    description="Retrieves active, unexpired 1-for-1 trade offers created by players."
)
async def list_trades(
    exclude_wallet: Optional[str] = Query(None, description="Exclude offers created by this wallet")
):
    return trading_service.get_open_trades(exclude_wallet=exclude_wallet)

@router.post(
    "/trades",
    response_model=TradeOfferResponse,
    summary="Create 1-for-1 Trade Offer",
    description="Lists an owned driver card in the marketplace in exchange for a requested target card."
)
async def create_trade(
    body: CreateTradeRequest = Body(...),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    if authenticated_wallet:
        body.creator_wallet = authenticated_wallet
    return trading_service.create_trade_offer(body)

@router.get(
    "/trades/{trade_id}",
    response_model=TradeOfferResponse,
    summary="Get Trade Offer Details",
    description="Retrieves state, cards, and execution details for a specific trade offer."
)
async def get_trade(
    trade_id: str = Path(..., examples=["trd_1a2b3c4d5e6f"])
):
    return trading_service.get_trade(trade_id)

@router.post(
    "/trades/{trade_id}/accept",
    response_model=TradeOfferResponse,
    summary="Accept Trade Offer (Atomic Swap)",
    description="Re-verifies on-chain ownership of both cards, locks state, and completes atomic card swap."
)
async def accept_trade(
    trade_id: str = Path(..., examples=["trd_1a2b3c4d5e6f"]),
    body: AcceptTradeRequest = Body(...),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    if authenticated_wallet:
        body.acceptor_wallet = authenticated_wallet
    return trading_service.accept_trade_offer(trade_id, body)

@router.post(
    "/trades/{trade_id}/cancel",
    response_model=TradeOfferResponse,
    summary="Cancel Open Trade Offer",
    description="Cancels an open trade offer and unlocks the offered card for racing and fusion."
)
async def cancel_trade(
    trade_id: str = Path(..., examples=["trd_1a2b3c4d5e6f"]),
    wallet_address: str = Query(..., description="Creator wallet address requesting cancellation"),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    caller = authenticated_wallet if authenticated_wallet else wallet_address
    return trading_service.cancel_trade_offer(trade_id, caller)

@router.get(
    "/wallets/{wallet_address}/trades",
    response_model=List[TradeOfferResponse],
    summary="Get User Trade History",
    description="Retrieves all trade offers created or accepted by a specific wallet address."
)
async def get_wallet_trades(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return trading_service.get_user_trades(wallet_address)
