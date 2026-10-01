"""
Pokédex (AlgoCreatures) — Fusion Endpoints
Module: api/v1/endpoints/fusion.py
==========================================
REST API endpoints for the 5-Epic-to-1-Legendary Pokémon Fusion feature.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status, Path

from backend.app.models.fusion import (
    FusionInitiateRequest,
    FusionConfirmRequest,
    FusionResponse,
)
from backend.app.services.fusion_service import fusion_service

logger = logging.getLogger("algocreatures.api.fusion")

router = APIRouter()

@router.get("/candidates/{wallet_address}", response_model=List[Dict[str, Any]])
def get_fusion_candidates(wallet_address: str = Path(..., description="Connected Algorand wallet address")):
    """
    Returns all owned Epic Pokémon for the connected wallet that are available for Fusion.
    Flags any assets that are locked in active trades.
    """
    return fusion_service.get_wallet_epic_candidates(wallet_address)

@router.post("/initiate", response_model=Dict[str, Any])
def initiate_fusion(request: FusionInitiateRequest):
    """
    Validates exactly 5 Epic Pokémon owned by the wallet and initializes a Fusion session.
    Returns session ID and minter address for the Pera group transfer approval.
    """
    return fusion_service.initiate_fusion(
        wallet_address=request.wallet_address,
        input_asset_ids=request.input_asset_ids
    )

@router.post("/{fusion_id}/confirm", response_model=Dict[str, Any])
def confirm_fusion(
    fusion_id: str = Path(..., description="Fusion session ID"),
    request: FusionConfirmRequest = ...
):
    """
    Confirms the retirement transfer of the 5 Epic Pokémon, burns/removes them from the user's
    collection, randomly chooses a Legendary Pokémon from the master catalog, mints a 1-of-1
    ARC-3 NFT, and delivers it to the user's wallet.
    """
    return fusion_service.confirm_fusion(
        fusion_id=fusion_id,
        wallet_address=request.wallet_address,
        transfer_tx_id=request.transfer_tx_id
    )

@router.get("/{fusion_id}", response_model=Dict[str, Any])
def get_fusion_session(fusion_id: str = Path(..., description="Fusion session ID")):
    """
    Retrieves current state and reward data for a given Fusion session.
    """
    return fusion_service.get_fusion(fusion_id)

@router.get("/wallet/{wallet_address}", response_model=List[Dict[str, Any]])
def get_wallet_fusions(wallet_address: str = Path(..., description="Connected Algorand wallet address")):
    """
    Returns all historical and active Fusion sessions for a wallet.
    """
    return fusion_service.get_wallet_fusions(wallet_address)
