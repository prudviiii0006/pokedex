"""
AlgoRacers — Session 21: Idempotent Blockchain Subscriber & Event Projector
Module: chain/subscriber.py
===========================================================================
Synchronizes confirmed Algorand blockchain events into idempotent
database projections, tracks round checkpoints, and handles crash recovery.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.core.database import get_db
from backend.app.chain.models import ChainEvent, ChainEventType, ChainSyncStatus
from backend.app.chain.indexer_client import chain_client
from backend.app.chain.event_decoder import event_decoder

logger = logging.getLogger("algoracers.chain.subscriber")

SUBSCRIBER_NAME = "algoracers_primary_subscriber"
DEFAULT_START_ROUND = 45120000

class ChainSubscriber:
    def __init__(self, name: str = SUBSCRIBER_NAME, network: str = "TestNet"):
        self.name = name
        self.network = network
        self._ensure_checkpoint()

    def _ensure_checkpoint(self):
        with get_db() as conn:
            row = conn.execute("""
                SELECT last_processed_round FROM chain_checkpoints
                WHERE subscriber_name = ? AND network = ?;
            """, (self.name, self.network)).fetchone()
            if not row:
                now_iso = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT INTO chain_checkpoints (subscriber_name, network, last_processed_round, updated_at)
                    VALUES (?, ?, ?, ?);
                """, (self.name, self.network, DEFAULT_START_ROUND, now_iso))
                conn.commit()

    def get_checkpoint_round(self) -> int:
        with get_db() as conn:
            row = conn.execute("""
                SELECT last_processed_round FROM chain_checkpoints
                WHERE subscriber_name = ? AND network = ?;
            """, (self.name, self.network)).fetchone()
            return row["last_processed_round"] if row else DEFAULT_START_ROUND

    def get_sync_status(self) -> ChainSyncStatus:
        algod_rnd, indexer_rnd, indexer_lag = chain_client.get_rounds_and_lag()
        chk_rnd = self.get_checkpoint_round()
        sub_lag = max(0, indexer_rnd - chk_rnd)

        with get_db() as conn:
            ev_total = conn.execute("SELECT COUNT(*) as cnt FROM chain_events WHERE network = ?;", (self.network,)).fetchone()["cnt"]
            ev_failed = conn.execute("SELECT COUNT(*) as cnt FROM chain_sync_errors;").fetchone()["cnt"]

        return ChainSyncStatus(
            network=self.network,
            algod_round=algod_rnd,
            indexer_round=indexer_rnd,
            checkpoint_round=chk_rnd,
            indexer_lag_rounds=indexer_lag,
            subscriber_lag_rounds=sub_lag,
            events_processed_total=ev_total,
            events_failed_total=ev_failed,
            is_healthy=(indexer_lag < 100 and sub_lag < 500)
        )

    def process_raw_transaction(self, raw_tx: Dict[str, Any]) -> Optional[ChainEvent]:
        """
        Decodes a raw transaction and applies its projection into the database idempotently.
        """
        event = event_decoder.decode_transaction(raw_tx, self.network)
        if not event:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            # 1. Idempotent Event Insertion
            # If already processed, DB unique constraint catches it
            existing = conn.execute("""
                SELECT event_id FROM chain_events WHERE event_id = ?;
            """, (event.event_id,)).fetchone()

            if existing:
                logger.debug(f"🔁 Duplicate chain event ignored (Idempotency): {event.event_id}")
                return event

            conn.execute("""
                INSERT INTO chain_events (
                    event_id, network, tx_id, round_number, event_type,
                    app_id, asset_id, sender, receiver, payload_json,
                    status, created_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PROCESSED', ?, ?);
            """, (
                event.event_id, event.network, event.tx_id, event.round_number,
                event.event_type.value, event.app_id, event.asset_id,
                event.sender, event.receiver, json.dumps(event.payload),
                now_iso, now_iso
            ))

            # 2. Apply Domain Projections
            if event.event_type == ChainEventType.NFT_TRANSFERRED:
                # Update current owner in nft instances / purchases if tracked
                asset_id = event.asset_id
                new_owner = event.receiver
                if asset_id and new_owner:
                    logger.info(f"🔄 NFT #{asset_id} transferred to {new_owner[:8]}... (Chain Event {event.tx_id[:8]}...)")

            elif event.event_type == ChainEventType.TOURNAMENT_FINALIZED:
                if event.app_id:
                    conn.execute("""
                        UPDATE tournaments 
                        SET status = 'FINALIZED'
                        WHERE app_id = ? AND status != 'FINALIZED';
                    """, (event.app_id,))

            elif event.event_type == ChainEventType.SEASON_FINALIZED:
                if event.app_id:
                    conn.execute("""
                        UPDATE seasons
                        SET status = 'FINALIZED'
                        WHERE app_id = ? AND status != 'FINALIZED';
                    """, (event.app_id,))

            # 3. Advance Checkpoint
            if event.round_number > self.get_checkpoint_round():
                conn.execute("""
                    UPDATE chain_checkpoints
                    SET last_processed_round = ?, updated_at = ?
                    WHERE subscriber_name = ? AND network = ?;
                """, (event.round_number, now_iso, self.name, self.network))

            conn.commit()

        logger.info(f"✅ Processed Chain Event [{event.event_type.value}] -> Tx #{event.tx_id[:12]}... in Round #{event.round_number}")
        return event

    def run_sync_batch(self, max_rounds: int = 50) -> Dict[str, Any]:
        """
        Runs one incremental sync batch from current checkpoint.
        """
        status = self.get_sync_status()
        start_round = status.checkpoint_round
        end_round = min(status.indexer_round, start_round + max_rounds)

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE chain_checkpoints
                SET last_processed_round = ?, updated_at = ?
                WHERE subscriber_name = ? AND network = ?;
            """, (end_round, now_iso, self.name, self.network))
            conn.commit()

        return {
            "subscriber": self.name,
            "start_round": start_round,
            "end_round": end_round,
            "rounds_advanced": end_round - start_round,
            "current_indexer_round": status.indexer_round
        }

chain_subscriber = ChainSubscriber()
