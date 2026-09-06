"""
AlgoRacers — Session 21: Blockchain Activity Feed Service
Module: services/activity_service.py
=========================================================
Aggregates and formats confirmed on-chain events into
user-facing activity feeds with explicit ON-CHAIN provenance.
"""

from typing import List, Dict, Any, Optional
from backend.app.core.database import get_db
from backend.app.chain.models import ActivityFeedItem

class ActivityService:
    def get_global_activity(self, limit: int = 20) -> List[ActivityFeedItem]:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM chain_events
                ORDER BY round_number DESC, created_at DESC
                LIMIT ?;
            """, (limit,)).fetchall()

            items = []
            for r in rows:
                items.append(self._format_event(r))
            return items

    def get_wallet_activity(self, wallet_address: str, limit: int = 20) -> List[ActivityFeedItem]:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM chain_events
                WHERE sender = ? OR receiver = ?
                ORDER BY round_number DESC, created_at DESC
                LIMIT ?;
            """, (wallet_address, wallet_address, limit)).fetchall()

            items = []
            for r in rows:
                items.append(self._format_event(r))
            return items

    def _format_event(self, row: Any) -> ActivityFeedItem:
        e_type = row["event_type"]
        tx_id = row["tx_id"]
        round_num = row["round_number"]
        asset_id = row["asset_id"]
        app_id = row["app_id"]
        sender = row["sender"]
        receiver = row["receiver"]

        title = e_type.replace("_", " ").title()
        desc = f"Confirmed in Round #{round_num} (Tx: {tx_id[:8]}...)"

        if e_type == "NFT_TRANSFERRED":
            title = f"🏎️ Driver NFT #{asset_id} Transferred"
            desc = f"Transferred to {receiver[:8]}... in Round #{round_num}"
        elif e_type == "TOURNAMENT_FINALIZED":
            title = f"🏆 Tournament #{app_id} Finalized"
            desc = f"Result hash committed to AVM in Round #{round_num}"
        elif e_type == "SEASON_FINALIZED":
            title = f"👑 Championship Season Finalized"
            desc = f"Merkle Root committed on Algorand in Round #{round_num}"
        elif e_type == "REWARD_CLAIMED":
            title = f"🎁 Season Trophy Claimed"
            desc = f"Claimed by {sender[:8]}... in Round #{round_num}"
        elif e_type == "GOVERNANCE_ACTION_EXECUTED":
            title = f"🏛️ Governance 2-of-3 Action Executed"
            desc = f"Executed by Council on App #{app_id} in Round #{round_num}"

        return ActivityFeedItem(
            event_id=row["event_id"],
            event_type=e_type,
            source="ON-CHAIN",
            title=title,
            description=desc,
            tx_id=tx_id,
            round_number=round_num,
            timestamp=row["created_at"],
            asset_id=asset_id,
            app_id=app_id,
            wallet_address=receiver or sender
        )

activity_service = ActivityService()
