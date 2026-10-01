"""
AlgoCreatures — Species Index & Creature Catalog Endpoints
Module: api/v1/endpoints/creatures.py
==========================================================
Public endpoints for querying the canonical 24 species, elements, and stats.
"""

from typing import List, Optional
from fastapi import APIRouter, Path, Query, Request, Response, HTTPException, status
from backend.rewards.creature_pool import creature_pool, CANONICAL_CREATURES, FACTIONS

router = APIRouter()

@router.get(
    "/creatures",
    summary="Get All Creature Species",
    description="Returns the full canonical catalog of 24 original elemental species across all 8 factions."
)
async def list_creatures(element: Optional[str] = None, rarity: Optional[str] = None):
    creatures = list(CANONICAL_CREATURES)
    if element:
        creatures = [c for c in creatures if c.primary_type.lower() == element.lower()]
    if rarity:
        creatures = [c for c in creatures if c.rarity.lower() == rarity.lower()]
    return [
        {
            "id": c.id,
            "index_number": c.index_number,
            "name": c.name,
            "primary_type": c.primary_type,
            "secondary_type": c.secondary_type,
            "faction": c.faction,
            "rarity": c.rarity,
            "evolution_family": c.evolution_family,
            "evolution_stage": c.evolution_stage,
            "next_evolution_id": c.next_evolution_id,
            "description": c.description,
            "image": c.image,
            "base_stats": c.stats
        }
        for c in creatures
    ]

@router.get(
    "/creatures/{creature_id}",
    summary="Get Species Details",
    description="Returns detailed stats, evolution tree, and elemental attributes for a specific creature species."
)
async def get_creature(creature_id: str = Path(..., description="Species ID (e.g. 'emberling')")):
    c = creature_pool.get_creature(creature_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Species '{creature_id}' not found.")
    return {
        "id": c.id,
        "index_number": c.index_number,
        "name": c.name,
        "primary_type": c.primary_type,
        "secondary_type": c.secondary_type,
        "faction": c.faction,
        "rarity": c.rarity,
        "evolution_family": c.evolution_family,
        "evolution_stage": c.evolution_stage,
        "next_evolution_id": c.next_evolution_id,
        "description": c.description,
        "image": c.image,
        "base_stats": c.stats
    }

@router.get("/factions", summary="List Elemental Factions")
async def list_factions():
    return list(FACTIONS.values())

@router.get(
    "/creatures/{asset_id}/analysis",
    summary="Advanced Tactical Pokémon Analysis (x402 Protected)",
    description="x402 protected endpoint: Unlocks deep tactical battle ratings, counter-matchups, arena synergies, and strategic recommendations."
)
async def get_creature_analysis(
    request: Request,
    response: Response,
    asset_id: str = Path(..., description="Algorand ASA ID or Species ID (e.g. '742199042' or 'emberling')"),
    wallet_address: Optional[str] = Query(None, description="Trainer Wallet Address for personalized deck telemetry")
):
    import base64
    import json
    from decimal import Decimal
    from backend.app.services.x402_service import x402_service
    from backend.app.core.config import settings
    from backend.app.core.database import get_db

    resource_url = str(request.url)
    algo_price = getattr(settings, "CREATURE_ANALYSIS_PRICE_ALGO", 0.005)
    amount_microalgos = int(Decimal(str(algo_price)) * Decimal("1000000"))
    description = f"Pokédex Advanced Tactical Analysis for #{asset_id}"

    payment_header = (
        request.headers.get("payment-signature") or 
        request.headers.get("PAYMENT-SIGNATURE") or 
        request.headers.get("x-402-payment-proof") or 
        request.headers.get("x-payment")
    )

    if not payment_header:
        challenge = x402_service.generate_challenge(
            resource_url=resource_url,
            description=description,
            amount_microalgos=amount_microalgos
        )
        b64_challenge = base64.b64encode(json.dumps(challenge).encode('utf-8')).decode('utf-8')
        headers = {
            "payment-required": b64_challenge,
            "WWW-Authenticate": "x402",
            "Cache-Control": "no-store",
            "Access-Control-Expose-Headers": "*, payment-required, payment-response, WWW-Authenticate"
        }
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=challenge,
            headers=headers
        )

    receipt = x402_service.verify_and_settle(
        payment_header=payment_header,
        resource_url=resource_url,
        required_amount_microalgos=amount_microalgos
    )
    b64_receipt = base64.b64encode(json.dumps(receipt).encode('utf-8')).decode('utf-8')
    response.headers["payment-response"] = b64_receipt

    # Resolve creature details from database or species pool
    creature_name = "Unknown"
    primary_type = "Fire"
    secondary_type = None
    rarity = "Common"
    level = 1
    xp = 0
    stats = {"HP": 75, "Attack": 75, "Defense": 75, "Speed": 75, "Stamina": 75}
    is_owned_card = False

    try:
        numeric_asset_id = int(asset_id)
    except ValueError:
        numeric_asset_id = None

    if numeric_asset_id is not None:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM owned_creatures WHERE asset_id = ?", (numeric_asset_id,)).fetchone()
            if row:
                is_owned_card = True
                creature_name = row["name"]
                primary_type = row["primary_type"]
                secondary_type = row["secondary_type"]
                rarity = row["rarity"]
                level = row["level"]
                xp = row["xp"]
                stats = {
                    "HP": row["hp"],
                    "Attack": row["attack"],
                    "Defense": row["defense"],
                    "Speed": row["speed"],
                    "Stamina": row["stamina"]
                }
            else:
                tmpl = creature_pool.get_creature(str(numeric_asset_id))
                if tmpl:
                    creature_name = tmpl.name
                    primary_type = tmpl.primary_type
                    secondary_type = tmpl.secondary_type
                    rarity = tmpl.rarity
                    stats = tmpl.stats
    else:
        tmpl = creature_pool.get_creature(asset_id)
        if tmpl:
            creature_name = tmpl.name
            primary_type = tmpl.primary_type
            secondary_type = tmpl.secondary_type
            rarity = tmpl.rarity
            stats = tmpl.stats
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Creature #{asset_id} not found.")

    # Calculate Battle Rating (0-100)
    raw_score = (stats["HP"] + stats["Attack"] * 1.2 + stats["Defense"] + stats["Speed"] * 1.1 + stats["Stamina"]) / 5.5
    rarity_bonus = {"Common": 0, "Rare": 6, "Epic": 12, "Legendary": 18}.get(rarity, 0)
    level_bonus = level * 2.5
    battle_rating = min(99.8, round(raw_score * 0.7 + rarity_bonus + level_bonus, 1))

    # Elemental matchups
    type_key = primary_type.capitalize()
    arena_map = {
        "Fire": {"best_arena": "Volcanic Caldera (volcano)", "arena_id": "volcano", "multiplier": "+25% Attack Surge"},
        "Water": {"best_arena": "Abyssal Trench (ocean)", "arena_id": "ocean", "multiplier": "+25% Defense & Hydro Regeneration"},
        "Grass": {"best_arena": "Ancient Redwood Sanctuary (sylvan)", "arena_id": "sylvan", "multiplier": "+30% Recovery & Stamina"},
        "Electric": {"best_arena": "High-Voltage Power Core (thunder)", "arena_id": "thunder", "multiplier": "+35% Critical Strike Probability"},
        "Ice": {"best_arena": "Sub-Zero Permafrost (glacier)", "arena_id": "glacier", "multiplier": "+25% Freeze Chance & Evasion"},
        "Earth": {"best_arena": "Subterranean Basin (volcano)", "arena_id": "volcano", "multiplier": "+20% Impact Absorption"},
        "Dark": {"best_arena": "Shadow Rift (glacier)", "arena_id": "glacier", "multiplier": "+25% Shadow Stealth"},
        "Light": {"best_arena": "Celestial Stratosphere (thunder)", "arena_id": "thunder", "multiplier": "+25% Solar Aura"}
    }
    arena_info = arena_map.get(type_key, arena_map["Fire"])

    strong_map = {
        "Fire": ["Grass", "Ice", "Bug"],
        "Water": ["Fire", "Earth", "Rock"],
        "Grass": ["Water", "Earth", "Ground"],
        "Electric": ["Water", "Flying"],
        "Ice": ["Grass", "Dragon", "Ground"],
        "Earth": ["Electric", "Fire", "Poison"],
        "Dark": ["Psychic", "Ghost"],
        "Light": ["Dark", "Dragon"]
    }
    weak_map = {
        "Fire": ["Water", "Earth", "Rock"],
        "Water": ["Electric", "Grass"],
        "Grass": ["Fire", "Ice", "Flying"],
        "Electric": ["Earth", "Ground"],
        "Ice": ["Fire", "Fighting", "Steel"],
        "Earth": ["Water", "Grass", "Ice"],
        "Dark": ["Fighting", "Light"],
        "Light": ["Dark"]
    }

    strong_against = strong_map.get(type_key, ["Standard Types"])
    weak_against = weak_map.get(type_key, ["Opposite Elements"])

    # Strategy recommendation
    if stats["Attack"] >= stats["Defense"] and stats["Attack"] >= stats["Speed"]:
        recommended_strategy = "aggressive"
        strat_reason = f"High base Attack ({stats['Attack']}) maximizes alpha turn-1 knockout probability."
    elif stats["Defense"] >= stats["Attack"] and stats["Defense"] >= stats["Speed"]:
        recommended_strategy = "defensive"
        strat_reason = f"Superior Defense ({stats['Defense']}) and HP ({stats['HP']}) outlast high-tempo assault teams."
    elif stats["Speed"] >= stats["Attack"]:
        recommended_strategy = "aggressive"
        strat_reason = f"Speed priority ({stats['Speed']}) guarantees turn-order initiative across all arenas."
    else:
        recommended_strategy = "balanced"
        strat_reason = f"Harmonious stat profile affords fluid tactical versatility against unknown matchups."

    # Evolution readiness
    evolution_readiness = {
        "current_level": level,
        "current_xp": xp,
        "can_evolve": level >= 3 or xp >= 350,
        "next_threshold": "350 XP (Stage 2)" if level < 3 else ("1050 XP (Stage 3 Apex)" if level < 5 else "Maximum Apex Achieved")
    }

    # Record in payment records
    user_w = wallet_address or receipt.get("payer", "anonymous_trainer")
    x402_service.record_payment(
        wallet_address=user_w,
        resource_type="CREATURE_ANALYSIS",
        resource_id=str(asset_id),
        amount_microalgos=amount_microalgos,
        payment_tx_id=receipt.get("transaction")
    )

    return {
        "asset_id": asset_id,
        "creature_name": creature_name,
        "primary_type": primary_type,
        "secondary_type": secondary_type,
        "rarity": rarity,
        "battle_rating": battle_rating,
        "best_arena": arena_info["best_arena"],
        "best_arena_id": arena_info["arena_id"],
        "arena_advantage_multiplier": arena_info["multiplier"],
        "strong_against": strong_against,
        "weak_against": weak_against,
        "evolution_readiness": evolution_readiness,
        "recommended_strategy": recommended_strategy,
        "strategy_reasoning": strat_reason,
        "stats_profile": stats,
        "tactical_summary": f"{creature_name} is a Tier-{rarity} {primary_type} combatant with a {battle_rating}/100 battle rating. Dominates {', '.join(strong_against)} in {arena_info['best_arena']} with {recommended_strategy.upper()} strategy."
    }

