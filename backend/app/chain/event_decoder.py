"""
AlgoRacers — Session 21: Blockchain Event Decoder
Module: chain/event_decoder.py
=================================================
Transforms raw Algorand Indexer transactions and smart contract logs
into typed, versioned domain events (ChainEvent).
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from backend.app.chain.models import ChainEvent, ChainEventType
from blockchain.governance.multisig import governance_engine

logger = logging.getLogger("algoracers.chain.decoder")

class ChainEventDecoder:
    def decode_transaction(
        self,
        raw_tx: Dict[str, Any],
        network: str = "TestNet"
    ) -> Optional[ChainEvent]:
        """
        Translates a raw Algorand transaction from Indexer/Algod into a normalized ChainEvent.
        """
        try:
            tx_id = raw_tx.get("id") or raw_tx.get("tx-id") or raw_tx.get("txId")
            round_num = raw_tx.get("confirmed-round") or raw_tx.get("confirmedRound") or raw_tx.get("round", 0)
            sender = raw_tx.get("sender")
            tx_type = raw_tx.get("tx-type") or raw_tx.get("type")
            now_iso = datetime.now(timezone.utc).isoformat()

            if not tx_id:
                return None

            # 1. ASA Transfer Event (NFT_TRANSFERRED)
            if tx_type == "axfer" or "asset-transfer-transaction" in raw_tx:
                axfer = raw_tx.get("asset-transfer-transaction", {})
                asset_id = axfer.get("asset-id") or raw_tx.get("assetId")
                receiver = axfer.get("receiver") or raw_tx.get("receiver")
                amt = axfer.get("amount", 1)

                if asset_id and receiver and amt > 0:
                    event_id = f"chain_evt_{network}_{tx_id}_axfer"
                    return ChainEvent(
                        event_id=event_id,
                        network=network,
                        tx_id=tx_id,
                        round_number=round_num,
                        event_type=ChainEventType.NFT_TRANSFERRED,
                        asset_id=asset_id,
                        sender=sender,
                        receiver=receiver,
                        payload={"asset_id": asset_id, "amount": amt, "sender": sender, "receiver": receiver},
                        status="PROCESSED",
                        created_at=now_iso,
                        processed_at=now_iso
                    )

            # 2. Application Call Events
            if tx_type == "appl" or "application-transaction" in raw_tx:
                appl = raw_tx.get("application-transaction", {})
                app_id = appl.get("application-id") or raw_tx.get("applicationId") or raw_tx.get("app-id")
                app_args = appl.get("application-args", [])

                method = "unknown"
                if app_args and len(app_args) > 0:
                    try:
                        raw_arg0 = app_args[0]
                        if isinstance(raw_arg0, str):
                            # Try base64 decode if encoded
                            try:
                                method = base64.b64decode(raw_arg0).decode("utf-8")
                            except Exception:
                                method = raw_arg0
                    except Exception:
                        method = "unknown"

                # Check Governance Sender
                if sender == governance_engine.address:
                    event_id = f"chain_evt_{network}_{tx_id}_gov"
                    return ChainEvent(
                        event_id=event_id,
                        network=network,
                        tx_id=tx_id,
                        round_number=round_num,
                        event_type=ChainEventType.GOVERNANCE_ACTION_EXECUTED,
                        app_id=app_id,
                        sender=sender,
                        payload={"app_id": app_id, "method": method, "governance_council": sender},
                        status="PROCESSED",
                        created_at=now_iso,
                        processed_at=now_iso
                    )

                # Tournament Finalization Event
                if method in ["finalize_race", "finalize_tournament"]:
                    event_id = f"chain_evt_{network}_{tx_id}_tf"
                    return ChainEvent(
                        event_id=event_id,
                        network=network,
                        tx_id=tx_id,
                        round_number=round_num,
                        event_type=ChainEventType.TOURNAMENT_FINALIZED,
                        app_id=app_id,
                        sender=sender,
                        payload={"app_id": app_id, "method": method},
                        status="PROCESSED",
                        created_at=now_iso,
                        processed_at=now_iso
                    )

                # Season Finalization Event
                if method == "finalize_season":
                    event_id = f"chain_evt_{network}_{tx_id}_sf"
                    return ChainEvent(
                        event_id=event_id,
                        network=network,
                        tx_id=tx_id,
                        round_number=round_num,
                        event_type=ChainEventType.SEASON_FINALIZED,
                        app_id=app_id,
                        sender=sender,
                        payload={"app_id": app_id, "method": method},
                        status="PROCESSED",
                        created_at=now_iso,
                        processed_at=now_iso
                    )

                # Reward Claim Event
                if method == "claim_reward":
                    event_id = f"chain_evt_{network}_{tx_id}_rc"
                    return ChainEvent(
                        event_id=event_id,
                        network=network,
                        tx_id=tx_id,
                        round_number=round_num,
                        event_type=ChainEventType.REWARD_CLAIMED,
                        app_id=app_id,
                        sender=sender,
                        payload={"app_id": app_id, "claimer": sender},
                        status="PROCESSED",
                        created_at=now_iso,
                        processed_at=now_iso
                    )

            return None
        except Exception as e:
            logger.error(f"Event decoding error for tx {raw_tx.get('id')}: {e}")
            return None

event_decoder = ChainEventDecoder()
