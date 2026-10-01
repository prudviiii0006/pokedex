"""
AlgoCreatures — Peer-to-Peer Trading Service
Module: services/trade_service.py
=========================================
Coordinates atomic creature card trades between player wallets.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
import algosdk

from backend.app.core.database import get_db
from backend.app.services.nft_service import nft_service

logger = logging.getLogger("algocreatures.trade_service")

class TradeService:
    def create_trade(
        self,
        initiator_wallet: str,
        initiator_asset_id: int,
        counterparty_wallet: Optional[str] = None,
        counterparty_asset_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Creates an open trade offer for a creature card."""
        # 1. Strict On-Chain Ownership Verification
        if not nft_service.wallet_owns_asset(initiator_wallet, initiator_asset_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not own the offered Pokémon NFT on-chain (Asset #{initiator_asset_id})."
            )

        with get_db() as conn:
            # Verify initiator owns the card
            owned = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
                (initiator_asset_id, initiator_wallet)
            ).fetchone()

            if not owned:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Wallet {initiator_wallet} does not own Creature Asset #{initiator_asset_id}."
                )

            trade_id = f"trd_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()

            conn.execute("""
                INSERT INTO trades (
                    trade_id, initiator_wallet, initiator_asset_id,
                    counterparty_wallet, counterparty_asset_id, status, created_at, settled_at
                ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, NULL);
            """, (
                trade_id, initiator_wallet, initiator_asset_id,
                counterparty_wallet, counterparty_asset_id, now
            ))
            conn.commit()

            return {
                "trade_id": trade_id,
                "initiator_wallet": initiator_wallet,
                "offered_asset": {
                    "asset_id": owned["asset_id"],
                    "name": owned["name"],
                    "type": owned["primary_type"],
                    "rarity": owned["rarity"],
                    "level": owned["level"]
                },
                "status": "OPEN",
                "created_at": now
            }

    def list_trades(self, status_filter: str = "OPEN") -> List[Dict[str, Any]]:
        """Lists active trading offers."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = ? ORDER BY CASE WHEN featured_until IS NOT NULL AND featured_until > datetime('now') THEN 0 ELSE 1 END, created_at DESC",
                (status_filter,)
            ).fetchall()
            trades = []
            now_str = datetime.now(timezone.utc).isoformat()
            for r in rows:
                c1 = conn.execute("SELECT * FROM owned_creatures WHERE asset_id = ?", (r["initiator_asset_id"],)).fetchone()
                c2 = conn.execute("SELECT * FROM owned_creatures WHERE asset_id = ?", (r["counterparty_asset_id"],)).fetchone() if r["counterparty_asset_id"] else None

                is_featured = bool(r["featured_until"] and r["featured_until"] > now_str)

                trades.append({
                    "trade_id": r["trade_id"],
                    "initiator_wallet": r["initiator_wallet"],
                    "offered_asset": {
                        "asset_id": c1["asset_id"],
                        "name": c1["name"],
                        "primary_type": c1["primary_type"],
                        "rarity": c1["rarity"],
                        "level": c1["level"]
                    } if c1 else {"asset_id": r["initiator_asset_id"]},
                    "counterparty_wallet": r["counterparty_wallet"],
                    "requested_asset": {
                        "asset_id": c2["asset_id"],
                        "name": c2["name"],
                        "primary_type": c2["primary_type"],
                        "rarity": c2["rarity"],
                        "level": c2["level"]
                    } if c2 else None,
                    "status": r["status"],
                    "is_featured": is_featured,
                    "featured_until": r["featured_until"],
                    "created_at": r["created_at"]
                })
            return trades

    def feature_trade(
        self,
        trade_id: str,
        wallet_address: str,
        duration_hours: int = 24
    ) -> Dict[str, Any]:
        """Marks an open trade offer as featured for the configured duration (24 hours)."""
        from datetime import timedelta
        with get_db() as conn:
            trade = conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,)).fetchone()
            if not trade or trade["status"] != "OPEN":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade offer not found or no longer open.")

            if trade["initiator_wallet"] != wallet_address:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the trade creator can feature this listing."
                )

            now_dt = datetime.now(timezone.utc)
            featured_until_dt = now_dt + timedelta(hours=duration_hours)
            featured_until = featured_until_dt.isoformat()

            conn.execute(
                "UPDATE trades SET featured_until = ? WHERE trade_id = ?",
                (featured_until, trade_id)
            )
            conn.commit()
            logger.info(f"⭐ Trade {trade_id} FEATURED until {featured_until} by {wallet_address}")

            return {
                "success": True,
                "trade_id": trade_id,
                "is_featured": True,
                "featured_until": featured_until,
                "duration_hours": duration_hours,
                "status": trade["status"]
            }

    def smart_match(self, wallet_address: str) -> Dict[str, Any]:
        """
        Analyzes user's collection against open marketplace trades.
        Identifies missing species/types in user collection and matches them
        with open listings. Does NOT modify card ownership.
        """
        with get_db() as conn:
            user_creatures = conn.execute(
                "SELECT * FROM owned_creatures WHERE wallet_address = ?",
                (wallet_address,)
            ).fetchall()

            owned_template_ids = {c["template_id"].lower() for c in user_creatures}
            owned_types = {c["primary_type"].lower() for c in user_creatures}

            open_trades = conn.execute(
                "SELECT * FROM trades WHERE status = 'OPEN' AND initiator_wallet != ?",
                (wallet_address,)
            ).fetchall()

            matches = []
            for t in open_trades:
                offered_card = conn.execute(
                    "SELECT * FROM owned_creatures WHERE asset_id = ?",
                    (t["initiator_asset_id"],)
                ).fetchone()

                if not offered_card:
                    continue

                card_tmpl = offered_card["template_id"].lower()
                card_type = offered_card["primary_type"].lower()

                # Calculate match score & synergy reasons
                synergy_reasons = []
                match_score = 60

                if card_tmpl not in owned_template_ids:
                    synergy_reasons.append(f"Uncollected Species: {offered_card['name']} will unlock a new Pokédex entry!")
                    match_score += 25

                if card_type not in owned_types:
                    synergy_reasons.append(f"Missing Element: Strengthens your elemental coverage with {offered_card['primary_type']}-type.")
                    match_score += 15

                if offered_card["rarity"] in ["Epic", "Legendary"]:
                    synergy_reasons.append(f"High-Tier Rarity: {offered_card['rarity']} asset with superior base attributes.")
                    match_score += 10

                if t["featured_until"] and t["featured_until"] > datetime.now(timezone.utc).isoformat():
                    synergy_reasons.append("Featured Priority Listing: Verified active community offer.")
                    match_score += 5

                # Check what user could offer in return
                suggested_give_cards = []
                for uc in user_creatures:
                    # If user has multiple of the same template or different rarity
                    suggested_give_cards.append({
                        "asset_id": uc["asset_id"],
                        "name": uc["name"],
                        "primary_type": uc["primary_type"],
                        "rarity": uc["rarity"],
                        "level": uc["level"]
                    })

                matches.append({
                    "trade_id": t["trade_id"],
                    "initiator_wallet": t["initiator_wallet"],
                    "match_score": min(match_score, 100),
                    "synergy_reasons": synergy_reasons if synergy_reasons else ["Balanced level and rarity trade opportunity."],
                    "offered_creature": {
                        "asset_id": offered_card["asset_id"],
                        "name": offered_card["name"],
                        "primary_type": offered_card["primary_type"],
                        "rarity": offered_card["rarity"],
                        "level": offered_card["level"],
                        "hp": offered_card["hp"],
                        "attack": offered_card["attack"],
                        "defense": offered_card["defense"]
                    },
                    "suggested_user_assets": suggested_give_cards[:3]
                })

            # Sort by match score descending
            matches.sort(key=lambda m: m["match_score"], reverse=True)

            return {
                "wallet_address": wallet_address,
                "total_owned_cards": len(user_creatures),
                "total_open_trades_analyzed": len(open_trades),
                "recommended_matches_count": len(matches),
                "matches": matches[:10],
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }

    def accept_trade(
        self,
        trade_id: str,
        counterparty_wallet: str,
        counterparty_asset_id: int
    ) -> Dict[str, Any]:
        """Accepts and executes an atomic card swap between two wallets."""
        with get_db() as conn:
            trade = conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,)).fetchone()
            if not trade or trade["status"] != "OPEN":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trade offer not found or no longer open.")

            if trade["initiator_wallet"] == counterparty_wallet:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot trade with yourself.")

            # Strict On-Chain Ownership Verification for both parties
            if not nft_service.wallet_owns_asset(trade["initiator_wallet"], trade["initiator_asset_id"]):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Initiator no longer owns Asset #{trade['initiator_asset_id']} on-chain."
                )
            if not nft_service.wallet_owns_asset(counterparty_wallet, counterparty_asset_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Counterparty does not own Asset #{counterparty_asset_id} on-chain."
                )

            # Verify counterparty ownership
            c2 = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
                (counterparty_asset_id, counterparty_wallet)
            ).fetchone()
            if not c2:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Counterparty does not own Asset #{counterparty_asset_id}.")

            # Swap ownership atomically in database
            now = datetime.now(timezone.utc).isoformat()

            conn.execute(
                "UPDATE owned_creatures SET wallet_address = ?, updated_at = ? WHERE asset_id = ?",
                (counterparty_wallet, now, trade["initiator_asset_id"])
            )
            conn.execute(
                "UPDATE owned_creatures SET wallet_address = ?, updated_at = ? WHERE asset_id = ?",
                (trade["initiator_wallet"], now, counterparty_asset_id)
            )

            # Update trade state
            conn.execute(
                "UPDATE trades SET counterparty_wallet = ?, counterparty_asset_id = ?, status = 'SETTLED', settled_at = ? WHERE trade_id = ?",
                (counterparty_wallet, counterparty_asset_id, now, trade_id)
            )

            conn.commit()
            logger.info(f"🤝 Trade {trade_id} SETTLED! Card #{trade['initiator_asset_id']} <-> Card #{counterparty_asset_id}")

            return {
                "success": True,
                "trade_id": trade_id,
                "status": "SETTLED",
                "swapped_assets": [trade["initiator_asset_id"], counterparty_asset_id],
                "settled_at": now
            }

trade_service = TradeService()
