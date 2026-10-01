"""
AlgoCreatures — Global Activity Stream Endpoints
Module: api/v1/endpoints/activity.py
================================================
Aggregates live blockchain & game events: pack purchases, NFT mints, battles, evolutions, and trades.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Query
from backend.app.core.database import get_db

router = APIRouter()

@router.get("/activity", summary="Get Live Activity Feed")
async def get_activity_feed(limit: int = Query(30, ge=1, le=100)):
    """Returns a unified timeline of recent platform events."""
    events: List[Dict[str, Any]] = []

    with get_db() as conn:
        # 1. Purchases / Mints
        purchases = conn.execute("""
            SELECT purchase_id, wallet_address, pack_id, creature_name, creature_type, rarity, asset_id, status, created_at
            FROM purchases
            WHERE status IN ('DELIVERED', 'WAITING_FOR_OPT_IN', 'NFT_MINTED')
            ORDER BY created_at DESC LIMIT ?;
        """, (limit,)).fetchall()

        for p in purchases:
            name = p["creature_name"] or "Creature"
            events.append({
                "type": "PACK_OPENED",
                "title": f"🎉 {p['rarity'] or 'Rare'} {name} Minted!",
                "description": f"Wallet {p['wallet_address'][:6]}...{p['wallet_address'][-4:]} opened a {p['pack_id'].title()} Pack and unlocked {name} (Asset #{p['asset_id']}).",
                "timestamp": p["created_at"],
                "badge": p["rarity"] or "Common",
                "badge_color": "#FFCC00" if p["rarity"] == "Legendary" else ("#AA44FF" if p["rarity"] == "Epic" else "#3399FF")
            })

        # 2. Battles
        battles = conn.execute("""
            SELECT battle_id, wallet_address, player_creature_name, opponent_creature_name, arena_id, winner, player_xp_gained, created_at
            FROM battles
            ORDER BY created_at DESC LIMIT ?;
        """, (limit,)).fetchall()

        for b in battles:
            events.append({
                "type": "BATTLE_COMPLETE",
                "title": f"⚔️ {b['player_creature_name']} vs {b['opponent_creature_name']}",
                "description": f"Battle in {b['arena_id'].title()} Colosseum: Winner was {b['winner']} (+{b['player_xp_gained']} XP awarded).",
                "timestamp": b["created_at"],
                "badge": "Battle",
                "badge_color": "#44BB44" if b["winner"] == "PLAYER" else "#FF4444"
            })

        # 3. Evolutions
        evolutions = conn.execute("""
            SELECT evolution_id, wallet_address, from_template_id, to_template_id, from_stage, to_stage, evolved_at
            FROM creature_evolutions
            ORDER BY evolved_at DESC LIMIT ?;
        """, (limit,)).fetchall()

        for e in evolutions:
            events.append({
                "type": "EVOLUTION",
                "title": f"🧬 Evolution to Stage {e['to_stage']} Completed!",
                "description": f"Wallet {e['wallet_address'][:6]}...{e['wallet_address'][-4:]} evolved {e['from_template_id'].title()} into {e['to_template_id'].title()}.",
                "timestamp": e["evolved_at"],
                "badge": "Evolution",
                "badge_color": "#FF8800"
            })

    # Sort all events chronologically descending
    events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return events[:limit]
