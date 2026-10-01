"""
Pokédex — Version & Public Configuration Endpoints
Module: api/v1/endpoints/version.py
================================================================
Exposes sanitized build provenance, version metadata, and public deployment configuration.
Never leaks server private keys, database passwords, or internal tokens.
"""

from typing import Dict, Any, List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.core.config import settings

router = APIRouter()

class VersionResponse(BaseModel):
    project_name: str = Field(..., examples=["Pokédex API"])
    version: str = Field("1.0.0", examples=["1.0.0"])
    git_commit: str = Field("c89f1a2e", examples=["c89f1a2e"])
    build_timestamp: str = Field("2026-08-30T18:00:00Z", examples=["2026-08-30T18:00:00Z"])
    environment: str = Field("staging", examples=["staging"])
    network: str = Field("testnet", examples=["testnet"])
    database_revision: str = Field("v24_postgres_security", examples=["v24_postgres_security"])
    race_engine_version: str = Field("v1.0.0", examples=["v1.0.0"])
    contract_version: str = Field("arc56_v2_multisig", examples=["arc56_v2_multisig"])

class PublicConfigResponse(BaseModel):
    network: str = Field("testnet", examples=["testnet"])
    algod_address: str = Field(..., examples=["https://testnet-api.algonode.cloud"])
    indexer_address: str = Field(..., examples=["https://testnet-idx.algonode.cloud"])
    minter_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    multisig_governance_address: str = Field("7WZ2E4G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6B7C8D9E0F1", examples=["7WZ2..."])
    feature_flags: Dict[str, bool] = Field(default_factory=lambda: {
        "pack_purchases_enabled": True,
        "batch_race_simulations_enabled": True,
        "governance_proposals_enabled": True,
        "chain_reconciliation_active": True
    })

@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Get System Version & Build Metadata",
    description="Returns reproducible build information, git commit, and environment configuration."
)
async def get_version():
    return VersionResponse(
        project_name=settings.PROJECT_NAME,
        version="0.24.0",
        git_commit="c89f1a2e",
        build_timestamp="2026-08-30T18:00:00Z",
        environment="staging",
        network=settings.NETWORK,
        database_revision="v24_postgres_security",
        race_engine_version="v1.0.0",
        contract_version="arc56_v2_multisig"
    )

@router.get(
    "/config/public",
    response_model=PublicConfigResponse,
    summary="Get Safe Public Deployment Configuration",
    description="Allows frontend and client applications to discover network parameters and contract anchors."
)
async def get_public_config():
    return PublicConfigResponse(
        network=settings.NETWORK,
        algod_address=settings.ALGOD_ADDRESS,
        indexer_address=settings.INDEXER_SERVER,
        minter_address=settings.MINTER_ADDRESS,
        multisig_governance_address="7WZ2E4G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6B7C8D9E0F1",
        feature_flags={
            "pack_purchases_enabled": True,
            "batch_race_simulations_enabled": True,
            "governance_proposals_enabled": True,
            "chain_reconciliation_active": True
        }
    )
