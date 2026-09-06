"""
AlgoRacers — Session 20: Governance REST Endpoints
Module: api/v1/endpoints/governance.py
==================================================
Public and council REST endpoints for:
  - Inspecting Governance Council configuration and multisig threshold
  - Creating, reviewing, signing, and executing 2-of-3 governance proposals
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Path, Body, HTTPException, status, Depends
from backend.app.models.governance import (
    GovernanceConfigResponse, GovernanceProposalDetail,
    CreateProposalRequest, SignProposalRequest, ExecuteProposalResponse
)
from backend.app.services.governance_service import governance_service
from backend.app.core.security import get_optional_wallet

router = APIRouter()

@router.get(
    "/config",
    response_model=GovernanceConfigResponse,
    summary="Get Governance Configuration",
    description="Returns the protocol-native 2-of-3 multisig address, council signers, upgrade policies, and pause status."
)
async def get_governance_config():
    return governance_service.get_governance_config()

@router.get(
    "/proposals",
    response_model=List[GovernanceProposalDetail],
    summary="List Governance Proposals",
    description="Lists all past, active, and pending multisig governance proposals."
)
async def list_proposals():
    return governance_service.list_proposals()

@router.post(
    "/proposals",
    response_model=GovernanceProposalDetail,
    summary="Create Governance Proposal",
    description="Drafts a new privileged governance action and validates pre-flight security invariants."
)
async def create_proposal(
    body: CreateProposalRequest = Body(...),
    authenticated_wallet: Optional[str] = Depends(get_optional_wallet)
):
    return governance_service.create_proposal(
        action_type=body.action_type,
        target_app_id=body.target_app_id,
        parameters=body.parameters,
        creator_wallet=authenticated_wallet
    )

@router.get(
    "/proposals/{proposal_id}",
    response_model=GovernanceProposalDetail,
    summary="Get Proposal Details",
    description="Returns detailed status, parameter breakdown, and collected signatures for a proposal."
)
async def get_proposal(
    proposal_id: str = Path(..., examples=["GOV-A1B2C3-finalize_season"])
):
    return governance_service.get_proposal(proposal_id)

@router.post(
    "/proposals/{proposal_id}/sign",
    response_model=GovernanceProposalDetail,
    summary="Sign Governance Proposal",
    description="Submits a partial signature from an authorized 2-of-3 council member."
)
async def sign_proposal(
    proposal_id: str = Path(..., examples=["GOV-A1B2C3-finalize_season"]),
    body: SignProposalRequest = Body(...)
):
    return governance_service.sign_proposal(
        proposal_id=proposal_id,
        signer_address=body.signer_address,
        signature_hex=body.signature_hex
    )

@router.post(
    "/proposals/{proposal_id}/execute",
    response_model=ExecuteProposalResponse,
    summary="Execute Governance Action",
    description="Broadcasts and executes the privileged action once the 2-of-3 signature threshold is reached."
)
async def execute_proposal(
    proposal_id: str = Path(..., examples=["GOV-A1B2C3-finalize_season"])
):
    return governance_service.execute_proposal(proposal_id)
