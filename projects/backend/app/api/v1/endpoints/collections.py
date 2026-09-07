"""
AlgoRacers — Canonical Driver Dataset, Collection Book & Card Provenance Endpoints
Module: api/v1/endpoints/collections.py
=================================================================================
REST endpoints for:
  1. Canonical 2026 F1 driver dataset & constructors catalog
  2. Collection book progress & constructor sets completion
  3. Card instance details, progression levels & lock statuses
  4. Card provenance history ledger (On-Chain transactions vs Game events)
  5. Side-by-side card gameplay stats comparisons
  6. Cryptographic Merkle membership proofs
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Path, Query, Body, HTTPException, status
from backend.app.services.collection_registry_service import collection_registry_service
from backend.app.services.collection_service import collection_service

router = APIRouter()

# -----------------------------------------------------------------------------
# 1. CANONICAL DATASET & CONSTRUCTORS
# -----------------------------------------------------------------------------
@router.get(
    "/drivers",
    summary="Get 2026 Canonical Driver Dataset",
    description="Returns all 22 official 2026 Formula 1 driver templates with base gameplay stats, car numbers, and constructor IDs."
)
async def list_canonical_drivers():
    return collection_service.get_all_drivers()

@router.get(
    "/constructors",
    summary="Get Canonical Constructors Catalog",
    description="Returns all 11 Formula 1 constructors with their 2-driver pairings."
)
async def list_constructors():
    return collection_service.get_all_constructors()

# -----------------------------------------------------------------------------
# 2. WALLET COLLECTION BOOK & CONSTRUCTOR SETS
# -----------------------------------------------------------------------------
@router.get(
    "/collection/{wallet_address}",
    summary="Get Wallet Collection Book Progress",
    description="Calculates verified collection progress across all 22 drivers and 11 constructors for a wallet address."
)
async def get_user_collection(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    return collection_service.get_user_collection(wallet_address)

@router.get(
    "/collection/{wallet_address}/progress",
    summary="Get Collection Progress Summary",
    description="Returns high-level completion statistics and completed constructor set counts."
)
async def get_user_collection_progress(
    wallet_address: str = Path(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
):
    data = collection_service.get_user_collection(wallet_address)
    return {
        "wallet_address": data["wallet_address"],
        "total_canonical_drivers": data["total_canonical_drivers"],
        "unique_drivers_owned": data["unique_drivers_owned"],
        "total_cards_owned": data["total_cards_owned"],
        "overall_completion_percentage": data["overall_completion_percentage"],
        "completed_constructors_count": data["completed_constructors_count"],
        "total_constructors_count": data["total_constructors_count"]
    }

# -----------------------------------------------------------------------------
# 3. CARD INSTANCE, PROGRESSION & LOCK STATE
# -----------------------------------------------------------------------------
@router.get(
    "/cards/compare",
    summary="Compare Two Driver Cards",
    description="Side-by-side gameplay stats comparison between two owned driver card asset IDs."
)
async def compare_cards(
    asset_a: int = Query(..., description="First Asset ID to compare"),
    asset_b: int = Query(..., description="Second Asset ID to compare")
):
    return collection_service.compare_cards(asset_a, asset_b)

@router.get(
    "/cards/{asset_id}",
    summary="Get Card Instance Details",
    description="Retrieves metadata, effective gameplay stats, XP level, and lock status for an individual card."
)
async def get_card_details(
    asset_id: int = Path(..., examples=[700811779])
):
    return collection_service.get_card_details(asset_id)

@router.get(
    "/cards/{asset_id}/history",
    summary="Get Card Provenance History",
    description="Returns chronological provenance history ledger clearly distinguishing on-chain transactions from game events."
)
async def get_card_history(
    asset_id: int = Path(..., examples=[700811779])
):
    return collection_service.get_card_history(asset_id)

# -----------------------------------------------------------------------------
# 4. CRYPTOGRAPHIC MERKLE MEMBERSHIP PROOFS (PRESERVED & BACKWARD COMPATIBLE)
# -----------------------------------------------------------------------------
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
    "/collections/{collection_id}/{version}/drivers/{driver_id}/proof",
    response_model=MerkleProofResponse,
    summary="Get Merkle Membership Proof",
    description="Returns the cryptographic leaf hash, sibling proof path, and collection root for a specific driver."
)
@router.get(
    "/{collection_id}/{version}/drivers/{driver_id}/proof",
    response_model=MerkleProofResponse,
    include_in_schema=False
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
    "/collections/verify",
    response_model=MerkleVerifyResponse,
    summary="Verify Merkle Proof",
    description="Independently verifies that a canonical driver record belongs to the committed Merkle root."
)
@router.post(
    "/verify",
    response_model=MerkleVerifyResponse,
    include_in_schema=False
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
    "/collections/{collection_id}/{version}/root",
    summary="Get Collection Root Commitment",
    description="Returns the on-chain committed Merkle root and manifest CID for a collection version."
)
@router.get(
    "/{collection_id}/{version}/root",
    include_in_schema=False
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
