"""
AlgoRacers — Session 18: Collection Registry & Merkle Proof Endpoints
Module: api/v1/endpoints/collections.py
=====================================================================
Provides public REST endpoints for:
  - Retrieving Merkle membership proofs for individual drivers
  - Verifying Merkle inclusion proofs against committed roots
  - Inspecting versioned on-chain collection roots
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Path, Body, HTTPException, status
from backend.app.services.collection_registry_service import collection_registry_service

router = APIRouter()

class MerkleProofResponse(BaseModel):
    collection_id: str
    version: int
    driver_id: str
    record: Dict[str, Any]
    leaf_hash: str
    proof: List[Dict[str, str]]
    root: str
    algorithm: str
    tree_scheme: str
    manifest_cid: str

class MerkleVerifyRequest(BaseModel):
    record: Dict[str, Any]
    proof: List[Dict[str, str]]
    root: str

class MerkleVerifyResponse(BaseModel):
    verified: bool
    record_key: Optional[str]
    root: str
    message: str

@router.get(
    "/{collection_id}/{version}/drivers/{driver_id}/proof",
    response_model=MerkleProofResponse,
    summary="Get Merkle Membership Proof",
    description="Returns the cryptographic leaf hash, sibling proof path, and collection root for a specific driver."
)
async def get_driver_merkle_proof(
    collection_id: str = Path(..., examples=["drivers"]),
    version: int = Path(..., examples=[1]),
    driver_id: str = Path(..., examples=["001"])
):
    proof_data = collection_registry_service.get_driver_proof(driver_id, collection_id, version)
    if not proof_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver #{driver_id} not found in collection '{collection_id}' v{version}."
        )
    return MerkleProofResponse(**proof_data)

@router.post(
    "/verify",
    response_model=MerkleVerifyResponse,
    summary="Verify Merkle Proof",
    description="Independently verifies that a canonical driver record belongs to the committed Merkle root."
)
async def verify_merkle_proof_endpoint(
    body: MerkleVerifyRequest = Body(...)
):
    is_valid = collection_registry_service.verify_proof(body.record, body.proof, body.root)
    driver_id = body.record.get("driver_id", "unknown")

    return MerkleVerifyResponse(
        verified=is_valid,
        record_key=f"driver_{driver_id}",
        root=body.root,
        message="✅ Cryptographic Merkle Membership Verified." if is_valid else "🚨 INVALID PROOF: Leaf does not match root."
    )

@router.get(
    "/{collection_id}/{version}/root",
    summary="Get Collection Root Commitment",
    description="Returns the on-chain committed Merkle root and manifest CID for a collection version."
)
async def get_collection_root(
    collection_id: str = Path(..., examples=["drivers"]),
    version: int = Path(..., examples=[1])
):
    info = collection_registry_service.get_collection_root_info(collection_id, version)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection '{collection_id}' v{version} not found."
        )
    return info
