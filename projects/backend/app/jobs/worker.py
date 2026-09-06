"""
AlgoRacers — Session 22: Background Job Worker
Module: jobs/worker.py
==============================================
Pulls jobs from PostgreSQL/SQLite job queue and executes idempotent domain handlers.
"""

import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional

from backend.app.core.database import get_db
from backend.app.jobs.queue import job_queue
from backend.app.services.race_engine import RaceEngine

logger = logging.getLogger("algoracers.jobs.worker")

class JobWorker:
    def __init__(self, worker_id: Optional[str] = None):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {
            "MINT_NFT": self._handle_mint_nft,
            "DELIVER_NFT": self._handle_deliver_nft,
            "PIN_METADATA": self._handle_pin_metadata,
            "RECONCILE_CHAIN": self._handle_reconcile_chain,
            "RACE_SIMULATION_BATCH": self._handle_race_simulation_batch
        }

    def process_one_job(self) -> bool:
        """Claims and executes a single job. Returns True if a job was executed."""
        job = job_queue.claim_next_job(self.worker_id)
        if not job:
            return False

        job_id = job["job_id"]
        job_type = job["job_type"]
        payload = job["payload"]

        logger.info(f"⚙️ Worker [{self.worker_id}] executing job #{job_id} [{job_type}]")

        handler = self.handlers.get(job_type)
        if not handler:
            job_queue.mark_failed(job_id, f"Unknown job type '{job_type}'")
            return True

        try:
            handler(payload)
            job_queue.mark_succeeded(job_id)
        except Exception as e:
            logger.error(f"❌ Error processing job #{job_id}: {e}", exc_info=True)
            job_queue.mark_failed(job_id, str(e))

        return True

    def _handle_mint_nft(self, payload: Dict[str, Any]):
        purchase_id = payload.get("purchase_id")
        logger.info(f"🔨 [JOB] Minting NFT for Purchase #{purchase_id}")

    def _handle_deliver_nft(self, payload: Dict[str, Any]):
        purchase_id = payload.get("purchase_id")
        logger.info(f"🚚 [JOB] Delivering NFT for Purchase #{purchase_id}")

    def _handle_pin_metadata(self, payload: Dict[str, Any]):
        cid = payload.get("cid")
        logger.info(f"📌 [JOB] Pinning IPFS CID: {cid}")

    def _handle_reconcile_chain(self, payload: Dict[str, Any]):
        logger.info(f"🔍 [JOB] Running periodic chain reconciliation")

    def _handle_race_simulation_batch(self, payload: Dict[str, Any]):
        """
        Executes a deterministic batch of race simulations and updates progress.
        """
        batch_id = payload["batch_id"]
        circuit_id = payload["circuit_id"]
        driver_id = payload["driver_id"]
        sim_count = payload["simulations_count"]

        engine = RaceEngine()
        results = []

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("UPDATE race_simulation_batches SET status = 'RUNNING', updated_at = ? WHERE batch_id = ?;", (now_iso, batch_id))
            conn.commit()

        from backend.app.services.circuit_service import circuit_service
        try:
            circuit = circuit_service.get_circuit(circuit_id)
        except Exception:
            circuit = circuit_service.list_circuits()[0]
        driver = engine.reward_engine.driver_pool.get_driver_by_id(driver_id) or engine.reward_engine.driver_pool.get_all_drivers()[0]

        for i in range(sim_count):
            res = engine.simulate_multi_car_race(
                player_driver=driver,
                circuit=circuit,
                player_wallet="SIMULATION_WALLET_ADDRESS_58_CHARS_DUMMY_FOR_BATCH_SIM",
                player_asset_id=0,
                seed=i
            )
            results.append({
                "iteration": i + 1,
                "position": res.position,
                "final_score": res.final_score,
                "points": res.points
            })

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE race_simulation_batches
                SET status = 'COMPLETED',
                    completed_count = ?,
                    results_json = ?,
                    updated_at = ?
                WHERE batch_id = ?;
            """, (sim_count, json.dumps(results), now_iso, batch_id))
            conn.commit()

        logger.info(f"🏁 [JOB] Completed {sim_count} race simulations for Batch #{batch_id}")

job_worker = JobWorker()
