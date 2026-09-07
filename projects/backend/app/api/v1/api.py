"""
AlgoRacers — Session 24: Aggregated API Router
Module: api/v1/api.py
=============================================
Aggregates all API v1 routers including version & build provenance.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health, auth, packs, premium,
    purchases, circuits, races, agent,
    tournaments, profile, achievements, collections, seasons,
    governance, chain_status, activity, jobs, simulation, version,
    fusion, trading
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health & Readiness"])
api_router.include_router(version.router, tags=["Version & Build Provenance"])
api_router.include_router(auth.router, prefix="/auth", tags=["Wallet Authentication"])
api_router.include_router(packs.router, prefix="/packs", tags=["Packs & Rewards"])
api_router.include_router(premium.router, tags=["Premium Analytics"])
api_router.include_router(purchases.router, tags=["Purchases & NFT Delivery"])
api_router.include_router(circuits.router, tags=["Circuits"])
api_router.include_router(races.router, tags=["Racing & Leaderboard"])
api_router.include_router(fusion.router, tags=["Card Fusion Lab"])
api_router.include_router(trading.router, tags=["Trading Marketplace"])
api_router.include_router(agent.router, tags=["AI Racing Agent"])
api_router.include_router(tournaments.router, prefix="/tournaments", tags=["On-Chain Tournaments"])
api_router.include_router(profile.router, tags=["Player Profile & Progression"])
api_router.include_router(achievements.router, prefix="/achievements", tags=["Achievements"])
api_router.include_router(collections.router, prefix="/collections", tags=["Collection Commitments & Merkle Proofs"])
api_router.include_router(seasons.router, prefix="/seasons", tags=["Championship Seasons & Merkle Claims"])
api_router.include_router(governance.router, prefix="/governance", tags=["Multisig Governance & Privileged Controls"])
api_router.include_router(chain_status.router, prefix="/chain", tags=["Chain Synchronization & Health"])
api_router.include_router(activity.router, prefix="/activity", tags=["On-Chain Activity Feed"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Durable Background Jobs"])
api_router.include_router(simulation.router, prefix="/races", tags=["Batch Race Simulation"])
