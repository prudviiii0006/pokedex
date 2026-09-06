"""
AlgoRacers — Session 20: Governance Models & Schemas
Module: models/governance.py
====================================================
Pydantic schemas for multisig governance configuration,
proposal lifecycle tracking, signatures, and execution reports.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class GovernanceConfigResponse(BaseModel):
    multisig_address: str = Field(..., examples=["VAY3X..."])
    version: int = Field(1, examples=[1])
    threshold: int = Field(2, examples=[2])
    signers: List[str] = Field(..., examples=[["3VZQ...N2PM", "6ZIJ...5MII", "MPZ7...7TZA"]])
    upgrade_policy: Dict[str, str]
    is_paused: bool = Field(False)
    network: str = Field("TestNet")

class GovernanceSignatureItem(BaseModel):
    signer_address: str
    signed_at: str

class GovernanceProposalDetail(BaseModel):
    proposal_id: str = Field(..., examples=["GOV-001-season-finalization"])
    action_type: str = Field(..., examples=["FINALIZE_SEASON", "PUBLISH_ROOT", "PAUSE_SYSTEM"])
    target_app_id: int = Field(..., examples=[88002001])
    sender_address: str
    parameters: Dict[str, Any]
    status: str = Field("DRAFT", examples=["DRAFT", "READY_FOR_SIGNATURES", "PARTIALLY_SIGNED", "THRESHOLD_REACHED", "EXECUTED", "REJECTED"])
    threshold_required: int = Field(2, examples=[2])
    signatures_count: int = Field(0, examples=[1])
    signatures: List[GovernanceSignatureItem] = Field(default_factory=list)
    tx_hash: Optional[str] = None
    execution_tx_id: Optional[str] = None
    created_at: str
    executed_at: Optional[str] = None

class CreateProposalRequest(BaseModel):
    action_type: str = Field(..., examples=["FINALIZE_SEASON", "PUBLISH_ROOT", "PAUSE_SYSTEM"])
    target_app_id: int = Field(..., examples=[88002001])
    parameters: Dict[str, Any]

class SignProposalRequest(BaseModel):
    signer_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    signature_hex: str = Field(..., examples=["a1b2c3d4..."])

class ExecuteProposalResponse(BaseModel):
    proposal_id: str
    action_type: str
    status: str
    execution_tx_id: str
    message: str
