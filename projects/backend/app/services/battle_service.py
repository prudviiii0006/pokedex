"""
AlgoCreatures — Battle Engine & Arena Combat Simulation
Module: services/battle_service.py
======================================================
Deterministic, stat-based turn combat engine featuring elemental type advantages,
arena environmental modifiers, combat strategies, and verified XP progression.
"""

import uuid
import json
import random
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException, status

from backend.app.core.database import get_db
from backend.rewards.creature_pool import creature_pool, CANONICAL_CREATURES
from backend.app.services.nft_service import nft_service

logger = logging.getLogger("algocreatures.battle_service")

# 1. Arena Environmental Modifiers
ARENAS: Dict[str, Dict[str, Any]] = {
    "volcano": {
        "id": "volcano",
        "name": "Volcano Colosseum",
        "theme": "Magma & Ash",
        "favored_type": "Fire",
        "disfavored_type": "Ice",
        "attack_modifier": 1.20,
        "defense_modifier": 0.90,
        "speed_modifier": 1.05,
        "description": "Scorching volcanic crater where Fire attacks deal +20% damage while Ice defenses melt."
    },
    "ocean": {
        "id": "ocean",
        "name": "Ocean Temple",
        "theme": "Deep Abyssal Water",
        "favored_type": "Water",
        "disfavored_type": "Fire",
        "attack_modifier": 0.95,
        "defense_modifier": 1.20,
        "speed_modifier": 1.00,
        "description": "Ancient submerged ruins where Water creatures enjoy +20% defense and extra endurance."
    },
    "sylvan": {
        "id": "sylvan",
        "name": "Sylvan Sanctuary",
        "theme": "Primordial Forest",
        "favored_type": "Grass",
        "disfavored_type": "Electric",
        "attack_modifier": 1.00,
        "defense_modifier": 1.20,
        "speed_modifier": 0.95,
        "description": "Dense ancient canopy bolstering Grass resilience by +20% while dampening electric arcs."
    },
    "thunder": {
        "id": "thunder",
        "name": "Thunder Ridge",
        "theme": "Storm Peaks",
        "favored_type": "Electric",
        "disfavored_type": "Earth",
        "attack_modifier": 1.15,
        "defense_modifier": 0.95,
        "speed_modifier": 1.25,
        "description": "High-altitude storm peak accelerating Electric creature speed and critical strike probability."
    },
    "glacier": {
        "id": "glacier",
        "name": "Glacier Basin",
        "theme": "Sub-Zero Permafrost",
        "favored_type": "Ice",
        "disfavored_type": "Grass",
        "attack_modifier": 1.05,
        "defense_modifier": 1.25,
        "speed_modifier": 0.90,
        "description": "Freezing tundra granting +25% armor to Ice species while slowing botanical growth."
    }
}

# 2. Combat Strategies
STRATEGIES: Dict[str, Dict[str, Any]] = {
    "aggressive": {
        "id": "aggressive",
        "name": "Aggressive Rush",
        "attack_bonus": 1.15,
        "defense_bonus": 0.90,
        "speed_bonus": 1.05,
        "description": "All-out offensive onslaught dealing +15% damage at the cost of -10% defense."
    },
    "balanced": {
        "id": "balanced",
        "name": "Balanced Tactician",
        "attack_bonus": 1.00,
        "defense_bonus": 1.00,
        "speed_bonus": 1.00,
        "description": "Standard disciplined stance maintaining equilibrium across offensive and defensive lines."
    },
    "defensive": {
        "id": "defensive",
        "name": "Iron Bastion",
        "attack_bonus": 0.90,
        "defense_bonus": 1.20,
        "speed_bonus": 0.95,
        "description": "Fortified defensive posture mitigating incoming strikes while waiting for counter-opportunities."
    },
    "special": {
        "id": "special",
        "name": "Aether Surge",
        "attack_bonus": 1.10,
        "defense_bonus": 1.05,
        "speed_bonus": 1.15,
        "description": "Channels elemental power to maximize speed and initiative bursts."
    }
}

# 3. Type Advantage Multiplier Table
TYPE_ADVANTAGES: Dict[str, List[str]] = {
    "Fire": ["Grass", "Ice"],
    "Water": ["Fire", "Earth"],
    "Grass": ["Water", "Earth"],
    "Electric": ["Water", "Light"],
    "Earth": ["Electric", "Fire"],
    "Ice": ["Grass", "Earth"],
    "Dark": ["Light"],
    "Light": ["Dark"]
}

# XP Level Thresholds
LEVEL_THRESHOLDS = [
    (1, 0, "Rookie"),
    (2, 150, "Bronze"),
    (3, 350, "Silver"),     # Stage 2 Evolution Eligible
    (4, 650, "Gold"),
    (5, 1050, "Platinum"),  # Stage 3 Evolution Eligible
    (6, 1550, "Diamond"),
    (7, 2200, "Mythic Apex")
]

def calculate_level_from_xp(xp: int) -> Tuple[int, str, int, int]:
    """Returns (current_level, title, current_level_xp, next_level_xp)."""
    current_level = 1
    title = "Rookie"
    next_xp = 150

    for idx, (lvl, threshold, t) in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            current_level = lvl
            title = t
            if idx + 1 < len(LEVEL_THRESHOLDS):
                next_xp = LEVEL_THRESHOLDS[idx + 1][1]
            else:
                next_xp = threshold + 1000

    return current_level, title, xp, next_xp

class BattleService:
    def get_arenas(self) -> List[Dict[str, Any]]:
        return list(ARENAS.values())

    def get_strategies(self) -> List[Dict[str, Any]]:
        return list(STRATEGIES.values())

    def execute_battle(
        self,
        wallet_address: str,
        player_asset_id: int,
        arena_id: str = "volcano",
        strategy_id: str = "balanced",
        is_premium: bool = False,
        bonus_xp: int = 50
    ) -> Dict[str, Any]:
        """
        Executes a turn-based combat encounter between player's owned creature and a worthy opponent.
        Calculates damage, critical strikes, type advantage, awards XP, and records battle in DB.
        """
        arena = ARENAS.get(arena_id.lower(), ARENAS["volcano"])
        strat = STRATEGIES.get(strategy_id.lower(), STRATEGIES["balanced"])

        # Strict On-Chain Ownership Verification
        if not nft_service.wallet_owns_asset(wallet_address, player_asset_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not own this Pokémon NFT on-chain (Asset #{player_asset_id})."
            )

        with get_db() as conn:
            # 1. Fetch player's owned creature
            player_row = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
                (player_asset_id, wallet_address)
            ).fetchone()

            if not player_row:
                # Fallback: check purchases table if owned_creatures was not populated
                purch_row = conn.execute(
                    "SELECT * FROM purchases WHERE asset_id = ? AND wallet_address = ?",
                    (player_asset_id, wallet_address)
                ).fetchone()
                if not purch_row:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Creature card with Asset #{player_asset_id} not found in wallet {wallet_address}."
                    )
                
                # Auto-register into owned_creatures
                c_tmpl = creature_pool.get_creature(purch_row["creature_id"] or purch_row["driver_id"]) or CANONICAL_CREATURES[0]
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO owned_creatures (
                        asset_id, wallet_address, template_id, name, primary_type, secondary_type,
                        faction, rarity, level, xp, hp, attack, defense, speed, stamina,
                        battle_wins, battle_losses, evolution_stage, mint_tx, purchase_id, acquired_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?);
                """, (
                    player_asset_id, wallet_address, c_tmpl.id, c_tmpl.name, c_tmpl.primary_type,
                    c_tmpl.secondary_type, c_tmpl.faction, c_tmpl.rarity,
                    c_tmpl.base_hp, c_tmpl.base_attack, c_tmpl.base_defense, c_tmpl.base_speed, c_tmpl.base_stamina,
                    c_tmpl.evolution_stage, f"tx_mint_{player_asset_id}", purch_row["purchase_id"], now, now
                ))
                conn.commit()
                player_row = conn.execute("SELECT * FROM owned_creatures WHERE asset_id = ?", (player_asset_id,)).fetchone()

            # 2. Pick a balanced opponent
            opponents = [c for c in CANONICAL_CREATURES if c.id != player_row["template_id"]]
            opponent = random.choice(opponents) if opponents else CANONICAL_CREATURES[0]

            # 3. Calculate Effective Stats
            p_type = player_row["primary_type"]
            o_type = opponent.primary_type

            # Type multiplier
            p_type_mult = 1.35 if o_type in TYPE_ADVANTAGES.get(p_type, []) else (0.80 if p_type in TYPE_ADVANTAGES.get(o_type, []) else 1.0)
            o_type_mult = 1.35 if p_type in TYPE_ADVANTAGES.get(o_type, []) else (0.80 if o_type in TYPE_ADVANTAGES.get(p_type, []) else 1.0)

            # Arena bonus
            p_arena_mult = arena["attack_modifier"] if p_type == arena["favored_type"] else (arena["defense_modifier"] if p_type == arena["disfavored_type"] else 1.0)
            o_arena_mult = arena["attack_modifier"] if o_type == arena["favored_type"] else (arena["defense_modifier"] if o_type == arena["disfavored_type"] else 1.0)

            # Level stat scaling
            lvl_bonus = 1.0 + (player_row["level"] - 1) * 0.08

            p_atk = int(player_row["attack"] * lvl_bonus * strat["attack_bonus"] * p_arena_mult * p_type_mult)
            p_def = int(player_row["defense"] * lvl_bonus * strat["defense_bonus"])
            p_spd = int(player_row["speed"] * lvl_bonus * strat["speed_bonus"])
            p_hp = int(player_row["hp"] * lvl_bonus * 1.5)

            o_atk = int(opponent.base_attack * o_arena_mult * o_type_mult)
            o_def = int(opponent.base_defense)
            o_spd = int(opponent.base_speed)
            o_hp = int(opponent.base_hp * 1.5)

            # 4. Simulate Combat Rounds
            rounds_log = []
            cur_p_hp = p_hp
            cur_o_hp = o_hp
            player_won = False

            for round_num in range(1, 10):
                # Speed initiative
                first_attacker = "PLAYER" if p_spd >= o_spd else "OPPONENT"

                # Round action 1
                if first_attacker == "PLAYER":
                    dmg = max(12, int(p_atk * random.uniform(0.85, 1.15) - (o_def * 0.4)))
                    cur_o_hp = max(0, cur_o_hp - dmg)
                    rounds_log.append({
                        "round": round_num,
                        "turn": 1,
                        "attacker": player_row["name"],
                        "target": opponent.name,
                        "action": f"{player_row['name']} strikes with {strat['name']} dealing {dmg} damage!",
                        "damage": dmg,
                        "opponent_hp_left": cur_o_hp,
                        "player_hp_left": cur_p_hp
                    })
                    if cur_o_hp == 0:
                        player_won = True
                        break

                    # Counter attack
                    o_dmg = max(10, int(o_atk * random.uniform(0.85, 1.15) - (p_def * 0.4)))
                    cur_p_hp = max(0, cur_p_hp - o_dmg)
                    rounds_log.append({
                        "round": round_num,
                        "turn": 2,
                        "attacker": opponent.name,
                        "target": player_row["name"],
                        "action": f"{opponent.name} counters dealing {o_dmg} damage!",
                        "damage": o_dmg,
                        "opponent_hp_left": cur_o_hp,
                        "player_hp_left": cur_p_hp
                    })
                    if cur_p_hp == 0:
                        player_won = False
                        break
                else:
                    o_dmg = max(10, int(o_atk * random.uniform(0.85, 1.15) - (p_def * 0.4)))
                    cur_p_hp = max(0, cur_p_hp - o_dmg)
                    rounds_log.append({
                        "round": round_num,
                        "turn": 1,
                        "attacker": opponent.name,
                        "target": player_row["name"],
                        "action": f"{opponent.name} attacks first dealing {o_dmg} damage!",
                        "damage": o_dmg,
                        "opponent_hp_left": cur_o_hp,
                        "player_hp_left": cur_p_hp
                    })
                    if cur_p_hp == 0:
                        player_won = False
                        break

                    dmg = max(12, int(p_atk * random.uniform(0.85, 1.15) - (o_def * 0.4)))
                    cur_o_hp = max(0, cur_o_hp - dmg)
                    rounds_log.append({
                        "round": round_num,
                        "turn": 2,
                        "attacker": player_row["name"],
                        "target": opponent.name,
                        "action": f"{player_row['name']} retaliates dealing {dmg} damage!",
                        "damage": dmg,
                        "opponent_hp_left": cur_o_hp,
                        "player_hp_left": cur_p_hp
                    })
                    if cur_o_hp == 0:
                        player_won = True
                        break

            if cur_p_hp > 0 and cur_o_hp > 0:
                player_won = cur_p_hp >= cur_o_hp

            winner = "PLAYER" if player_won else "OPPONENT"

            # 5. Award XP and update records
            base_xp = 100 if player_won else 25
            type_bonus_xp = 25 if p_type_mult > 1.0 and player_won else 0
            premium_bonus_xp = bonus_xp if is_premium else 0
            total_xp_gained = base_xp + type_bonus_xp + premium_bonus_xp

            new_total_xp = player_row["xp"] + total_xp_gained
            new_level, level_title, _, next_lvl_xp = calculate_level_from_xp(new_total_xp)
            did_level_up = 1 if new_level > player_row["level"] else 0

            # Update owned_creatures
            conn.execute("""
                UPDATE owned_creatures
                SET xp = ?, level = ?, 
                    battle_wins = battle_wins + ?,
                    battle_losses = battle_losses + ?,
                    updated_at = ?
                WHERE asset_id = ?;
            """, (
                new_total_xp, new_level,
                1 if player_won else 0,
                0 if player_won else 1,
                datetime.now(timezone.utc).isoformat(),
                player_asset_id
            ))

            # Record battle in database
            battle_id = f"bat_{uuid.uuid4().hex[:12]}"
            conn.execute("""
                INSERT INTO battles (
                    battle_id, wallet_address, player_asset_id, player_creature_name,
                    opponent_template_id, opponent_creature_name, arena_id, strategy,
                    winner, player_xp_gained, level_up, new_level, is_premium, bonus_xp,
                    rounds_log_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                battle_id, wallet_address, player_asset_id, player_row["name"],
                opponent.id, opponent.name, arena["id"], strat["id"],
                winner, total_xp_gained, did_level_up, new_level,
                1 if is_premium else 0, premium_bonus_xp,
                json.dumps(rounds_log), datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()

            return {
                "battle_id": battle_id,
                "winner": winner,
                "player_won": player_won,
                "is_premium": is_premium,
                "bonus_xp": premium_bonus_xp,
                "arena": arena,
                "strategy": strat,
                "player": {
                    "asset_id": player_asset_id,
                    "name": player_row["name"],
                    "primary_type": p_type,
                    "level": new_level,
                    "level_title": level_title,
                    "xp_gained": total_xp_gained,
                    "total_xp": new_total_xp,
                    "next_level_xp": next_lvl_xp,
                    "level_up": bool(did_level_up),
                    "starting_hp": p_hp,
                    "final_hp": cur_p_hp
                },
                "opponent": {
                    "template_id": opponent.id,
                    "name": opponent.name,
                    "primary_type": o_type,
                    "faction": opponent.faction,
                    "rarity": opponent.rarity,
                    "starting_hp": o_hp,
                    "final_hp": cur_o_hp
                },
                "rounds": rounds_log,
                "executed_at": datetime.now(timezone.utc).isoformat()
            }

    def get_battle_history(self, wallet_address: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves past battle encounters for a player wallet."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM battles WHERE wallet_address = ? ORDER BY created_at DESC LIMIT ?",
                (wallet_address, limit)
            ).fetchall()
            history = []
            for r in rows:
                history.append({
                    "battle_id": r["battle_id"],
                    "player_asset_id": r["player_asset_id"],
                    "player_creature_name": r["player_creature_name"],
                    "opponent_creature_name": r["opponent_creature_name"],
                    "arena_id": r["arena_id"],
                    "strategy": r["strategy"],
                    "winner": r["winner"],
                    "player_xp_gained": r["player_xp_gained"],
                    "level_up": bool(r["level_up"]),
                    "new_level": r["new_level"],
                    "rounds": json.loads(r["rounds_log_json"]),
                    "created_at": r["created_at"]
                })
            return history

battle_service = BattleService()
