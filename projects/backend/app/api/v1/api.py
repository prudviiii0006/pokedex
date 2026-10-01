"""
AlgoCreatures — Core API Router
Module: api/v1/api.py
===============================
Aggregates API v1 routers: Health, Version, Packs, Purchases, Creatures, Collection, Battles, Evolutions, Trades, and Activity.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    health, packs, purchases, version,
    creatures, collection, battles, evolution, trades, activity, pricing, assets, fusion
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health & Readiness"])
api_router.include_router(version.router, tags=["Version & Build Provenance"])
api_router.include_router(pricing.router, tags=["Authoritative Pricing & Config"])
api_router.include_router(packs.router, prefix="/packs", tags=["Packs & Rewards"])
api_router.include_router(purchases.router, tags=["Purchases & NFT Delivery"])
api_router.include_router(creatures.router, tags=["Creatures & Species Index"])
api_router.include_router(assets.router, tags=["On-Chain ASA NFT Verification"])
api_router.include_router(collection.router, tags=["Collection & Deck Management"])
api_router.include_router(battles.router, tags=["Arena Battles & Combat Engine"])
api_router.include_router(evolution.router, tags=["Creature Evolution Chamber"])
api_router.include_router(fusion.router, prefix="/fusion", tags=["Pokémon Fusion Chamber"])
api_router.include_router(trades.router, tags=["Peer-to-Peer Card Trading"])
api_router.include_router(activity.router, tags=["Activity & Live Feed"])

