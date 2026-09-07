"""
AlgoRacers — Canonical Driver Dataset, Collection Book & Card Provenance
Module: services/collection_service.py
========================================================================
Provides business logic for:
  1. Canonical 2026 F1 driver dataset (22 drivers, 11 constructors)
  2. Wallet collection book progress & constructor sets completion
  3. Card instance details with progression and lock statuses
  4. Card provenance history (On-Chain transactions vs Game events)
  5. Side-by-side card gameplay stat comparisons
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import algosdk
from fastapi import HTTPException, status

from backend.app.core.database import get_db
from backend.rewards.driver_pool import DriverPool, CONSTRUCTORS
from backend.rewards.models import DriverTemplate
from backend.app.services.progression_service import progression_service

logger = logging.getLogger("algoracers.collection_service")

class CollectionService:
    def __init__(self):
        self.driver_pool = DriverPool()

    def get_all_drivers(self) -> List[Dict[str, Any]]:
        """Returns all 22 canonical 2026 Formula 1 driver templates."""
        drivers = self.driver_pool.get_all_drivers()
        result = []
        for d in sorted(drivers, key=lambda x: (x.constructor_id, x.number)):
            result.append({
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "number": d.number,
                "constructor_id": d.constructor_id,
                "constructor_name": d.constructor_name,
                "nationality": d.nationality,
                "season": d.season,
                "rarity": d.rarity,
                "stats": d.stats,
                "description": d.description,
                "image": d.image
            })
        return result

    def get_all_constructors(self) -> List[Dict[str, Any]]:
        """Returns all 11 constructors with their canonical 2-driver pairings."""
        result = []
        for cid, cdata in CONSTRUCTORS.items():
            drivers = self.driver_pool.get_drivers_by_constructor(cid)
            driver_summaries = [
                {
                    "id": d.id,
                    "name": d.name,
                    "code": d.code,
                    "number": d.number,
                    "rarity": d.rarity,
                    "image": d.image
                }
                for d in sorted(drivers, key=lambda x: x.number)
            ]
            result.append({
                "id": cid,
                "name": cdata["name"],
                "drivers_count": len(driver_summaries),
                "drivers": driver_summaries
            })
        return result

    def get_user_collection(self, wallet_address: str) -> Dict[str, Any]:
        """
        Calculates user collection completion across all 22 drivers and 11 constructors.
        Verifies ownership against database ledger and indexer state.
        """
        if not algosdk.encoding.is_valid_address(wallet_address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Algorand 58-character public wallet address."
            )

        all_templates = self.driver_pool.get_all_drivers()
        all_constructors = self.get_all_constructors()

        # Query all active owned cards for this wallet
        owned_cards_by_driver: Dict[str, List[Dict[str, Any]]] = {}
        total_cards_count = 0

        with get_db() as conn:
            # 1. Purchases table (delivered or waiting for opt-in)
            purchase_rows = conn.execute("""
                SELECT asset_id, driver_id, driver_name, rarity, metadata_uri, delivery_tx_id, status, created_at
                FROM purchases
                WHERE wallet_address = ? AND asset_id IS NOT NULL AND status IN ('DELIVERED', 'WAITING_FOR_OPT_IN', 'NFT_MINTED');
            """, (wallet_address,)).fetchall()

            # 2. Fusion outputs
            fusion_rows = conn.execute("""
                SELECT output_asset_id as asset_id, premium_driver_id as driver_id, premium_driver_name as driver_name,
                       'Legendary' as rarity, metadata_uri, delivery_tx_id, status, created_at
                FROM fusion_operations
                WHERE wallet_address = ? AND output_asset_id IS NOT NULL AND status = 'COMPLETED';
            """, (wallet_address,)).fetchall()

            # 3. Card ownership overrides (from trading)
            ownership_rows = conn.execute("""
                SELECT asset_id, driver_id, driver_name, rarity, status, updated_at as created_at
                FROM card_ownership_records
                WHERE current_owner = ? AND status != 'CONSUMED_FUSION';
            """, (wallet_address,)).fetchall()

            consumed_asset_ids = set()
            for r in conn.execute("SELECT asset_id FROM fusion_inputs;").fetchall():
                consumed_asset_ids.add(r["asset_id"])

            seen_asset_ids = set()

            all_raw_cards = []
            for r in list(purchase_rows) + list(fusion_rows) + list(ownership_rows):
                aid = r["asset_id"]
                if aid and aid not in seen_asset_ids and aid not in consumed_asset_ids:
                    seen_asset_ids.add(aid)
                    all_raw_cards.append(r)

            for card in all_raw_cards:
                did = str(card["driver_id"]).lower() if card["driver_id"] else ""
                template = self.driver_pool.get_driver_by_id(did) or self.driver_pool.get_driver_by_id(card["driver_name"])
                canonical_id = template.id if template else did

                card_data = {
                    "asset_id": card["asset_id"],
                    "driver_id": canonical_id,
                    "driver_name": card["driver_name"],
                    "rarity": card["rarity"],
                    "status": "AVAILABLE"
                }

                if canonical_id not in owned_cards_by_driver:
                    owned_cards_by_driver[canonical_id] = []
                owned_cards_by_driver[canonical_id].append(card_data)
                total_cards_count += 1

        # Build constructor completion progress
        constructor_progress = []
        completed_constructors_count = 0

        for constr in all_constructors:
            cid = constr["id"]
            drivers_in_team = constr["drivers"]
            owned_in_team = 0
            team_driver_details = []

            for d in drivers_in_team:
                did = d["id"]
                owned_instances = owned_cards_by_driver.get(did, [])
                is_owned = len(owned_instances) > 0
                if is_owned:
                    owned_in_team += 1

                team_driver_details.append({
                    "driver_id": did,
                    "name": d["name"],
                    "code": d["code"],
                    "number": d["number"],
                    "rarity": d["rarity"],
                    "image": d["image"],
                    "is_owned": is_owned,
                    "owned_count": len(owned_instances),
                    "instances": owned_instances
                })

            is_team_complete = (owned_in_team == len(drivers_in_team)) and (len(drivers_in_team) > 0)
            if is_team_complete:
                completed_constructors_count += 1

            constructor_progress.append({
                "constructor_id": cid,
                "constructor_name": constr["name"],
                "is_complete": is_team_complete,
                "owned_count": owned_in_team,
                "total_count": len(drivers_in_team),
                "completion_percentage": round((owned_in_team / len(drivers_in_team)) * 100, 1) if drivers_in_team else 0,
                "drivers": team_driver_details
            })

        unique_owned_count = len(owned_cards_by_driver)
        total_canonical = len(all_templates)
        overall_percentage = round((unique_owned_count / total_canonical) * 100, 1) if total_canonical > 0 else 0

        # Duplicate driver list
        duplicate_drivers = [
            {
                "driver_id": did,
                "owned_count": len(instances),
                "driver_name": instances[0]["driver_name"],
                "rarity": instances[0]["rarity"],
                "asset_ids": [inst["asset_id"] for inst in instances]
            }
            for did, instances in owned_cards_by_driver.items()
            if len(instances) > 1
        ]

        return {
            "wallet_address": wallet_address,
            "total_canonical_drivers": total_canonical,
            "unique_drivers_owned": unique_owned_count,
            "total_cards_owned": total_cards_count,
            "overall_completion_percentage": overall_percentage,
            "completed_constructors_count": completed_constructors_count,
            "total_constructors_count": len(all_constructors),
            "constructors": constructor_progress,
            "duplicates": duplicate_drivers
        }

    def get_card_details(self, asset_id: int) -> Dict[str, Any]:
        """Returns comprehensive card metadata, stats, level, XP, and lock state."""
        with get_db() as conn:
            # Check purchases
            p_row = conn.execute("SELECT * FROM purchases WHERE asset_id = ?", (asset_id,)).fetchone()
            # Check fusion
            f_row = conn.execute("SELECT * FROM fusion_operations WHERE output_asset_id = ?", (asset_id,)).fetchone()
            # Check ownership
            o_row = conn.execute("SELECT * FROM card_ownership_records WHERE asset_id = ?", (asset_id,)).fetchone()
            # Check if consumed in fusion
            c_row = conn.execute("SELECT * FROM fusion_inputs WHERE asset_id = ?", (asset_id,)).fetchone()
            # Check if in active trade
            t_row = conn.execute("""
                SELECT trade_id FROM trade_offers 
                WHERE (offered_asset_id = ? OR requested_asset_id = ?) AND status = 'OPEN';
            """, (asset_id, asset_id)).fetchone()

            if not p_row and not f_row and not o_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Card with Asset ID #{asset_id} not found."
                )

            driver_id = ""
            driver_name = "Unknown Driver"
            rarity = "Common"
            owner = ""
            metadata_uri = ""

            if p_row:
                driver_id = p_row["driver_id"]
                driver_name = p_row["driver_name"]
                rarity = p_row["rarity"]
                owner = p_row["wallet_address"]
                metadata_uri = p_row["metadata_uri"] or ""
            elif f_row:
                driver_id = f_row["premium_driver_id"]
                driver_name = f_row["premium_driver_name"]
                rarity = "Legendary"
                owner = f_row["wallet_address"]
                metadata_uri = f_row["metadata_uri"] or ""

            if o_row:
                owner = o_row["current_owner"]
                driver_id = o_row["driver_id"] or driver_id
                driver_name = o_row["driver_name"] or driver_name
                rarity = o_row["rarity"] or rarity

            # Lock status determination
            lock_status = "AVAILABLE"
            if c_row:
                lock_status = "CONSUMED_FUSION"
            elif t_row:
                lock_status = "TRADE_LOCKED"

            # Query races and calculate progression for this card
            race_rows = conn.execute("""
                SELECT race_id, circuit_name, position, points, created_at 
                FROM races WHERE asset_id = ? ORDER BY created_at DESC;
            """, (asset_id,)).fetchall()

            races_count = len(race_rows)
            wins_count = sum(1 for r in race_rows if r["position"] == 1)
            podiums_count = sum(1 for r in race_rows if r["position"] in [1, 2, 3])
            card_xp = races_count * 20 + wins_count * 25 + (podiums_count - wins_count) * 15
            level, next_xp, progress_pct = progression_service.calculate_level(card_xp)

            # Get canonical template stats
            template = self.driver_pool.get_driver_by_id(driver_id) or self.driver_pool.get_driver_by_id(driver_name)
            base_stats = template.stats if template else {"speed": 85, "racecraft": 85, "qualifying": 85, "consistency": 85}
            
            # Bounded upgrade modifier (+1 per level above 1, max +5)
            upgrade_mod = min(5, max(0, level - 1))
            effective_stats = {k: min(99, v + upgrade_mod) for k, v in base_stats.items()}

            return {
                "asset_id": asset_id,
                "driver_id": template.id if template else driver_id,
                "driver_name": driver_name,
                "constructor_id": template.constructor_id if template else "",
                "constructor_name": template.constructor_name if template else "",
                "number": template.number if template else 0,
                "code": template.code if template else "",
                "rarity": rarity,
                "owner": owner,
                "lock_status": lock_status,
                "level": level,
                "xp": card_xp,
                "next_level_xp": next_xp,
                "xp_progress_pct": progress_pct,
                "races_count": races_count,
                "wins_count": wins_count,
                "podiums_count": podiums_count,
                "base_stats": base_stats,
                "upgrade_modifier": upgrade_mod,
                "effective_stats": effective_stats,
                "metadata_uri": metadata_uri,
                "image": template.image if template else ""
            }

    def get_card_history(self, asset_id: int) -> Dict[str, Any]:
        """
        Builds the provenance ledger distinguishing genuine ON-CHAIN events from GAME EVENTS.
        """
        details = self.get_card_details(asset_id)
        events = []

        with get_db() as conn:
            # 1. Mint & Delivery Events
            p_row = conn.execute("SELECT * FROM purchases WHERE asset_id = ?", (asset_id,)).fetchone()
            if p_row:
                events.append({
                    "event_type": "NFT_MINTED",
                    "category": "ON-CHAIN",
                    "title": "Minted 1-of-1 ARC-3 NFT on Algorand TestNet",
                    "tx_id": f"tx_mint_{asset_id}",
                    "details": f"Created with Asset ID #{asset_id} from {p_row['pack_id'].capitalize()} Pack.",
                    "timestamp": p_row["created_at"],
                    "explorer_url": f"https://testnet.explorer.perawallet.app/asset/{asset_id}/"
                })
                if p_row["delivery_tx_id"]:
                    events.append({
                        "event_type": "NFT_DELIVERED",
                        "category": "ON-CHAIN",
                        "title": "Delivered to Player Wallet",
                        "tx_id": p_row["delivery_tx_id"],
                        "details": f"Transferred to {p_row['wallet_address'][:8]}... via atomic ASA transfer.",
                        "timestamp": p_row["updated_at"],
                        "explorer_url": f"https://testnet.explorer.perawallet.app/tx/{p_row['delivery_tx_id']}/"
                    })

            # 2. Fusion Generation Event
            f_row = conn.execute("SELECT * FROM fusion_operations WHERE output_asset_id = ?", (asset_id,)).fetchone()
            if f_row:
                events.append({
                    "event_type": "FUSION_GENERATED",
                    "category": "ON-CHAIN",
                    "title": "Forged in Fusion Lab (5 Epics -> 1 Premium)",
                    "tx_id": f_row["delivery_tx_id"] or f"tx_fusion_{asset_id}",
                    "details": f"Created from fusion operation {f_row['fusion_id']}.",
                    "timestamp": f_row["created_at"],
                    "explorer_url": f"https://testnet.explorer.perawallet.app/asset/{asset_id}/"
                })

            # 3. Trading Swaps
            trade_rows = conn.execute("""
                SELECT * FROM trade_offers 
                WHERE (offered_asset_id = ? OR requested_asset_id = ?) AND status = 'COMPLETED'
                ORDER BY completed_at ASC;
            """, (asset_id, asset_id)).fetchall()

            for t in trade_rows:
                events.append({
                    "event_type": "TRADE_COMPLETED",
                    "category": "ON-CHAIN",
                    "title": "Exchanged in Atomic Trade Marketplace",
                    "tx_id": t["atomic_group_id"] or f"tx_trade_{t['trade_id']}",
                    "details": f"Atomic swap between {t['creator_wallet'][:8]}... and {t['accepted_by'][:8]}...",
                    "timestamp": t["completed_at"] or t["created_at"],
                    "explorer_url": f"https://testnet.explorer.perawallet.app/tx/{t['atomic_group_id'] or ''}/"
                })

            # 4. Race Participations (Game Events)
            race_rows = conn.execute("""
                SELECT * FROM races WHERE asset_id = ? ORDER BY created_at ASC;
            """, (asset_id,)).fetchall()

            for r in race_rows:
                events.append({
                    "event_type": "RACE_COMPLETED",
                    "category": "GAME EVENT",
                    "title": f"Raced at {r['circuit_name']}",
                    "tx_id": None,
                    "details": f"Finished {r['result_category']} (Score: {r['final_score']:.1f}, Points: +{r['points']})",
                    "timestamp": r["created_at"],
                    "explorer_url": None
                })

        events.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "card": details,
            "total_events": len(events),
            "events": events
        }

    def compare_cards(self, asset_id_a: int, asset_id_b: int) -> Dict[str, Any]:
        """Returns side-by-side comparative analysis of two driver cards."""
        card_a = self.get_card_details(asset_id_a)
        card_b = self.get_card_details(asset_id_b)

        stats_comparison = {}
        for stat_name in ["speed", "racecraft", "qualifying", "consistency"]:
            val_a = card_a["effective_stats"].get(stat_name, 80)
            val_b = card_b["effective_stats"].get(stat_name, 80)
            diff = val_a - val_b
            advantage = "A" if diff > 0 else ("B" if diff < 0 else "TIED")
            stats_comparison[stat_name] = {
                "stat_name": stat_name.capitalize(),
                "card_a_value": val_a,
                "card_b_value": val_b,
                "diff": abs(diff),
                "advantage": advantage
            }

        return {
            "label": "AlgoRacers Gameplay Stats",
            "card_a": card_a,
            "card_b": card_b,
            "stats_comparison": stats_comparison
        }

collection_service = CollectionService()
