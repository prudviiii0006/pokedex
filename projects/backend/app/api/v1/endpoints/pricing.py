"""
AlgoCreatures — Authoritative Pricing Configuration Endpoint
Module: api/v1/endpoints/pricing.py
============================================================
Exposes server-authoritative pricing for all free and x402-powered premium services.
"""

from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter()

@router.get(
    "/config/pricing",
    summary="Get Server Pricing Configuration",
    description="Returns authoritative prices, network details, and microAlgo requirements for all Pokémon services."
)
async def get_pricing_config():
    return {
        "currency": "ALGO",
        "network": {
            "name": "Algorand TestNet",
            "caip2": settings.ALGORAND_TESTNET_CAIP2,
            "currency": "ALGO",
            "asset_name": "ALGO",
            "asset_id": settings.X402_PAYMENT_ASSET,  # 0 for native ALGO
            "pay_to": settings.X402_PAY_TO,
            "facilitator_url": settings.X402_FACILITATOR_URL
        },
        "prices": {
            "basic_pack": {
                "currency": "ALGO",
                "price_algo": settings.BASIC_PACK_PRICE_ALGO,
                "amount_microalgo": int(settings.BASIC_PACK_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.BASIC_PACK_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.BASIC_PACK_PRICE_ALGO,
                "amount_micro_usdc": int(settings.BASIC_PACK_PRICE_ALGO * 1_000_000),
                "description": "Trainer Booster Pack (1 Digital Collectible)",
                "display": f"{settings.BASIC_PACK_PRICE_ALGO} ALGO"
            },
            "premium_pack": {
                "currency": "ALGO",
                "price_algo": settings.PREMIUM_PACK_PRICE_ALGO,
                "amount_microalgo": int(settings.PREMIUM_PACK_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.PREMIUM_PACK_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.PREMIUM_PACK_PRICE_ALGO,
                "amount_micro_usdc": int(settings.PREMIUM_PACK_PRICE_ALGO * 1_000_000),
                "description": "Premium Apex Pack (3 Digital Collectibles)",
                "display": f"{settings.PREMIUM_PACK_PRICE_ALGO} ALGO"
            },
            "event_pack": {
                "currency": "ALGO",
                "price_algo": settings.EVENT_PACK_PRICE_ALGO,
                "amount_microalgo": int(settings.EVENT_PACK_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.EVENT_PACK_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.EVENT_PACK_PRICE_ALGO,
                "amount_micro_usdc": int(settings.EVENT_PACK_PRICE_ALGO * 1_000_000),
                "description": "Special Event Element Booster Pack (2 Collectibles)",
                "display": f"{settings.EVENT_PACK_PRICE_ALGO} ALGO"
            },
            "premium_battle": {
                "currency": "ALGO",
                "price_algo": settings.PREMIUM_BATTLE_PRICE_ALGO,
                "amount_microalgo": int(settings.PREMIUM_BATTLE_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.PREMIUM_BATTLE_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.PREMIUM_BATTLE_PRICE_ALGO,
                "amount_micro_usdc": int(settings.PREMIUM_BATTLE_PRICE_ALGO * 1_000_000),
                "description": "Premium Tactical Battle (+50 Bonus Combat XP)",
                "display": f"{settings.PREMIUM_BATTLE_PRICE_ALGO} ALGO"
            },
            "featured_trade": {
                "currency": "ALGO",
                "price_algo": settings.FEATURED_TRADE_PRICE_ALGO,
                "amount_microalgo": int(settings.FEATURED_TRADE_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.FEATURED_TRADE_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.FEATURED_TRADE_PRICE_ALGO,
                "amount_micro_usdc": int(settings.FEATURED_TRADE_PRICE_ALGO * 1_000_000),
                "description": "Featured Trade Listing (24-Hour Marketplace Pin)",
                "display": f"{settings.FEATURED_TRADE_PRICE_ALGO} ALGO"
            },
            "smart_trade_match": {
                "currency": "ALGO",
                "price_algo": settings.SMART_MATCH_PRICE_ALGO,
                "amount_microalgo": int(settings.SMART_MATCH_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.SMART_MATCH_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.SMART_MATCH_PRICE_ALGO,
                "amount_micro_usdc": int(settings.SMART_MATCH_PRICE_ALGO * 1_000_000),
                "description": "Smart Trade Matcher (AI Portfolio Synergy Engine)",
                "display": f"{settings.SMART_MATCH_PRICE_ALGO} ALGO"
            },
            "evolution_boost": {
                "currency": "ALGO",
                "price_algo": settings.EVOLUTION_BOOST_PRICE_ALGO,
                "amount_microalgo": int(settings.EVOLUTION_BOOST_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.EVOLUTION_BOOST_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.EVOLUTION_BOOST_PRICE_ALGO,
                "amount_micro_usdc": int(settings.EVOLUTION_BOOST_PRICE_ALGO * 1_000_000),
                "description": "Instant Evolution XP Boost (+100 XP)",
                "display": f"{settings.EVOLUTION_BOOST_PRICE_ALGO} ALGO"
            },
            "creature_analysis": {
                "currency": "ALGO",
                "price_algo": settings.CREATURE_ANALYSIS_PRICE_ALGO,
                "amount_microalgo": int(settings.CREATURE_ANALYSIS_PRICE_ALGO * 1_000_000),
                "amount_microalgos": int(settings.CREATURE_ANALYSIS_PRICE_ALGO * 1_000_000),
                "price_usdc": settings.CREATURE_ANALYSIS_PRICE_ALGO,
                "amount_micro_usdc": int(settings.CREATURE_ANALYSIS_PRICE_ALGO * 1_000_000),
                "description": "Advanced Tactical Pokémon Analysis & Counter-Strategy",
                "display": f"{settings.CREATURE_ANALYSIS_PRICE_ALGO} ALGO"
            }
        },
        "packs": {
            "basic": {
                "name": "Basic Pack",
                "price_algo": settings.BASIC_PACK_PRICE_ALGO,
                "amount_microalgo": int(settings.BASIC_PACK_PRICE_ALGO * 1_000_000),
                "display": f"{settings.BASIC_PACK_PRICE_ALGO} ALGO"
            },
            "premium": {
                "name": "Premium Pack",
                "price_algo": settings.PREMIUM_PACK_PRICE_ALGO,
                "amount_microalgo": int(settings.PREMIUM_PACK_PRICE_ALGO * 1_000_000),
                "display": f"{settings.PREMIUM_PACK_PRICE_ALGO} ALGO"
            }
        },
        "free_features": [
            "Normal Pack Opening / Faucet Demonstration",
            "Standard Arena Battles",
            "Canonical Evolution Level Progression",
            "Standard Trade Offer Creation & Swaps",
            "Vault / Collection Browsing",
            "Self-Custody Pera Wallet NFT Claims & Transfers"
        ]
    }
