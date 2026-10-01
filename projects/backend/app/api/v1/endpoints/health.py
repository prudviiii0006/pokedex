"""
Pokédex — Health & Readiness Endpoints (MVP)
==============================================
Liveness (/health) and Readiness (/ready) probes.
"""

from fastapi import APIRouter, HTTPException, status
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.health import HealthResponse
from backend.rewards.creature_pool import CreaturePool

router = APIRouter()
_creature_pool = CreaturePool()

@router.get(
    "/health", 
    response_model=HealthResponse,
    summary="System Liveness Check",
    description="Returns the operating status, service name, version, and connected network."
)
async def get_health():
    return HealthResponse(
        status="ok",
        service="pokedex-api",
        version=settings.VERSION,
        network=settings.NETWORK
    )

@router.get(
    "/ready",
    summary="System Readiness Check",
    description="Verifies database integrity, TestNet network guardrails, and loaded assets."
)
async def get_readiness():
    # 1. Check TestNet Network Guard
    if settings.NETWORK.lower() not in ["testnet", "algorand-testnet"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Security Guardrail Triggered: Disallowed network '{settings.NETWORK}'."
        )

    # 2. Check Database Connectivity
    try:
        with get_db() as conn:
            conn.execute("SELECT 1;").fetchone()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {str(e)}"
        )

    # 3. Check Canonical Creature Pool
    try:
        creatures_count = len(_creature_pool.get_all_creatures())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Internal creature pool loading failed: {str(e)}"
        )

    return {
        "status": "ready",
        "database": "connected",
        "network": settings.NETWORK,
        "testnet_guard": "active",
        "creatures_loaded": creatures_count,
        "drivers_loaded": creatures_count
    }
