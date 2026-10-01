"""
Pokédex — FastAPI Backend
Module: api/v1/endpoints/packs.py
=================================
REST endpoints for inspecting pack configurations and simulating rewards.
"""

from typing import List, Optional
from fastapi import APIRouter, Path, Body
from backend.app.models.pack import PackResponse
from backend.app.models.reward import RewardResponse, SimulatePackRequest
from backend.app.services.pack_service import pack_service

router = APIRouter()

@router.get(
    "",
    response_model=List[PackResponse],
    summary="List Available Packs",
    description="Fetches all configured collectible pack tiers (Basic, Premium) with prices and probability distributions."
)
async def list_packs():
    return pack_service.get_all_packs()

@router.get(
    "/{pack_id}",
    response_model=PackResponse,
    summary="Get Pack Details",
    description="Retrieves configuration parameters and rarity tables for a specific pack."
)
async def get_pack(
    pack_id: str = Path(..., examples=["basic"], description="Pack identifier ('basic' or 'premium')")
):
    return pack_service.get_pack(pack_id)

@router.post(
    "/{pack_id}/simulate",
    response_model=RewardResponse,
    summary="Simulate Pack Opening (Development Only)",
    description="Generates an off-chain simulated driver drop using weighted random sampling. (No payment or NFT minting performed)."
)
async def simulate_pack_opening(
    pack_id: str = Path(..., examples=["premium"], description="Target pack identifier"),
    request_body: Optional[SimulatePackRequest] = Body(None)
):
    wallet_addr = request_body.wallet_address if request_body else None
    return pack_service.simulate_pack_opening(pack_id=pack_id, wallet_address=wallet_addr)
