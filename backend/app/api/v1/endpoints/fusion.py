"""
AlgoRacers — Core Product Redesign: Fusion Endpoints
Module: api/v1/endpoints/fusion.py
===================================================
REST endpoints for initiating fusions, checking status, recovering rewards,
and listing wallet fusion history.
"""

from typing import List, Optional
from fastapi import APIRouter, Path, Body, HTTPException, status, Depends
from backend.app.models.fusion import (
    FusionInitiateRequest,
    FusionResponse
)
from backend.app.services.fusion_service import fusion_service
from backend.app.core.security import get_optional_wallet

router = APIRouter()

@router.post(
    "/fusions",
    response_model=FusionResponse,
    summary="Fuse 5 Epic Cards into 1 Premium Driver",
    description="Server-authoritatively verifies 5 distinct Epic cards owned by caller, consumes them, and mints 1 new 1-of-1 Premium driver NFT."
)
async def initiate_fusion(
    body: FusionInitiateRequest = Body(...),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    if authenticated_wallet:
        body.wallet_address = authenticated_wallet
    return fusion_service.process_fusion(body)

@router.get(
    "/fusions/{fusion_id}",
    response_model=FusionResponse,
    summary="Get Fusion Status",
    description="Retrieves current state and minted Premium card details for a fusion operation."
)
async def get_fusion(
    fusion_id: str = Path(..., examples=["fus_1a2b3c4d5e6f"])
):
    return fusion_service.get_fusion(fusion_id)

@router.post(
    "/fusions/{fusion_id}/recover",
    response_model=FusionResponse,
    summary="Recover Pending Fusion Reward",
    description="Retries Premium NFT minting/delivery for a fusion operation where input cards were consumed but output delivery was pending."
)
async def recover_fusion(
    fusion_id: str = Path(..., examples=["fus_1a2b3c4d5e6f"])
):
    return fusion_service.recover_pending_fusion(fusion_id)

@router.get(
    "/wallets/{wallet_address}/fusions",
    response_model=List[FusionResponse],
    summary="Get User Fusion History",
    description="Retrieves chronological history of all fusion operations executed by a wallet address."
)
async def get_wallet_fusions(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return fusion_service.get_user_fusions(wallet_address)
