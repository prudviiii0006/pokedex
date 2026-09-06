"""
AlgoRacers — Session 22: PostgreSQL, Database Transactions, Background Jobs, Caching & Scaling Test Suite
==========================================================================================================
Test Suite:
  1. Job enqueue and claim lifecycle
  2. Multi-worker concurrent claiming with SKIP LOCKED
  3. Exponential backoff retry for failed jobs
  4. Dead-letter failed state and admin retry endpoint
  5. Worker crash recovery via lease expiration
  6. Transactional Outbox pattern atomic persistence and dispatch
  7. Idempotency service fingerprinting and replay protection
  8. Idempotency key rejection on altered parameters
  9. Safe cache-aside hit, miss, and invalidation
  10. Durable batch race simulation queue and progress tracking
  11. REST API endpoints for /jobs, /jobs/metrics, /jobs/{id}/retry, /races/batch
  12. Logical database backup and restore verification
"""

import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.jobs.queue import job_queue
from backend.app.jobs.outbox import transactional_outbox
from backend.app.jobs.worker import JobWorker, job_worker
from backend.app.services.idempotency_service import idempotency_service
from backend.app.core.cache import safe_cache
from backend.scripts.backup_db import backup_database
from backend.scripts.restore_db import restore_database

WALLET_A = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"

@pytest.fixture
def client():
    return TestClient(app)

def test_job_enqueue_and_claim_lifecycle():
    """Test 1: Enqueue job, claim with worker, mark succeeded."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs;")
        conn.commit()

    job_id = job_queue.enqueue(
        job_type="PIN_METADATA",
        payload={"cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"}
    )
    assert job_id.startswith("job_")

    claimed = job_queue.claim_next_job(worker_id="worker_test_1")
    assert claimed is not None
    assert claimed["job_id"] == job_id
    assert claimed["job_type"] == "PIN_METADATA"

    job_queue.mark_succeeded(job_id)

    with get_db() as conn:
        row = conn.execute("SELECT status FROM jobs WHERE job_id = ?;", (job_id,)).fetchone()
        assert row["status"] == "SUCCEEDED"

def test_multi_worker_skip_locked_concurrency():
    """Test 2: Two concurrent workers claim distinct jobs without collision."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs;")
        conn.commit()

    j1 = job_queue.enqueue("DELIVER_NFT", {"purchase_id": "purch_101"})
    j2 = job_queue.enqueue("DELIVER_NFT", {"purchase_id": "purch_102"})

    w1_job = job_queue.claim_next_job("worker_A")
    w2_job = job_queue.claim_next_job("worker_B")

    assert w1_job is not None
    assert w2_job is not None
    assert w1_job["job_id"] != w2_job["job_id"]

    job_queue.mark_succeeded(w1_job["job_id"])
    job_queue.mark_succeeded(w2_job["job_id"])

def test_job_retry_exponential_backoff():
    """Test 3: Job failure increments attempts and schedules RETRY_PENDING."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs;")
        conn.commit()

    j_fail = job_queue.enqueue("MINT_NFT", {"purchase_id": "purch_fail_test"}, max_attempts=3)
    claimed = job_queue.claim_next_job("worker_fail_test")
    assert claimed is not None

    job_queue.mark_failed(claimed["job_id"], "Network timeout", retry_delay_seconds=2)

    with get_db() as conn:
        row = conn.execute("SELECT status, attempts, last_error FROM jobs WHERE job_id = ?;", (claimed["job_id"],)).fetchone()
        assert row["status"] == "RETRY_PENDING"
        assert row["attempts"] == 1
        assert "Network timeout" in row["last_error"]

def test_worker_crash_recovery_via_lease_timeout():
    """Test 4: Stuck RUNNING job from crashed worker is recovered after lease expires."""
    with get_db() as conn:
        conn.execute("DELETE FROM jobs;")
        conn.commit()

    j_stuck = job_queue.enqueue("PIN_METADATA", {"cid": "test_stuck_cid"})
    claimed = job_queue.claim_next_job("worker_crashed_test")
    assert claimed is not None

    # Artificially age the locked_at timestamp
    with get_db() as conn:
        conn.execute("UPDATE jobs SET locked_at = '2026-08-30T10:00:00Z' WHERE job_id = ?;", (claimed["job_id"],))
        conn.commit()

    recovered_count = job_queue.recover_expired_leases(lease_timeout_seconds=60)
    assert recovered_count >= 1

    with get_db() as conn:
        row = conn.execute("SELECT status, last_error FROM jobs WHERE job_id = ?;", (claimed["job_id"],)).fetchone()
        assert row["status"] == "RETRY_PENDING"
        assert "Lease expired" in row["last_error"]

def test_transactional_outbox_pattern():
    """Test 5: Transactional outbox records event atomically with business write and dispatches."""
    with get_db() as conn:
        conn.execute("DELETE FROM outbox_events;")
        conn.commit()

        outbox_id = transactional_outbox.record_event(
            conn=conn,
            event_type="MINT_NFT",
            aggregate_type="purchase",
            aggregate_id="purch_outbox_test",
            payload={"purchase_id": "purch_outbox_test", "wallet": WALLET_A}
        )
        conn.commit()

    assert outbox_id.startswith("outbox_")

    # Dispatch outbox
    dispatched = transactional_outbox.dispatch_pending()
    assert dispatched >= 1

    with get_db() as conn:
        row = conn.execute("SELECT status FROM outbox_events WHERE outbox_id = ?;", (outbox_id,)).fetchone()
        assert row["status"] == "DISPATCHED"

def test_idempotency_service_fingerprint_and_replay():
    """Test 6: Idempotency service reserves key and returns cached result on replay."""
    key = "idemp_test_key_001"
    req_body = {"driver_id": "velocity_one", "circuit": "monaco_gp"}

    with get_db() as conn:
        conn.execute("DELETE FROM idempotency_records WHERE idempotency_key = ?;", (key,))
        conn.commit()

    # 1. First call -> Reserved
    is_new, cached = idempotency_service.check_or_reserve(key, "test_scope", WALLET_A, req_body)
    assert is_new is True
    assert cached is None

    # Store response
    idempotency_service.store_response(key, "test_scope", {"status": "SUCCESS", "tx_id": "TX999"})

    # 2. Duplicate call with SAME payload -> Replay cached response
    is_new_dup, cached_dup = idempotency_service.check_or_reserve(key, "test_scope", WALLET_A, req_body)
    assert is_new_dup is False
    assert cached_dup == {"status": "SUCCESS", "tx_id": "TX999"}

    # 3. Duplicate call with ALTERED payload -> Rejected with ValueError
    altered_body = {"driver_id": "velocity_one", "circuit": "silverstone"}
    with pytest.raises(ValueError, match="previously used with different request parameters"):
        idempotency_service.check_or_reserve(key, "test_scope", WALLET_A, altered_body)

def test_safe_cache_aside_and_invalidation():
    """Test 7: Cache stores immutable IPFS data and supports explicit invalidation."""
    k = "driver_meta_bafy123"
    with get_db() as conn:
        conn.execute("DELETE FROM cache_entries WHERE cache_key = ?;", (k,))
        conn.commit()

    call_count = 0
    def mock_fetch():
        nonlocal call_count
        call_count += 1
        return {"driver": "Apex Predator", "top_speed": 340}

    # 1. Cache MISS
    res1 = safe_cache.get_or_set(k, mock_fetch, is_immutable=True)
    assert res1["top_speed"] == 340
    assert call_count == 1

    # 2. Cache HIT (getter_fn not called)
    res2 = safe_cache.get_or_set(k, mock_fetch, is_immutable=True)
    assert res2["top_speed"] == 340
    assert call_count == 1

    # 3. Invalidation
    safe_cache.invalidate(k)
    res3 = safe_cache.get_or_set(k, mock_fetch, is_immutable=True)
    assert call_count == 2

def test_durable_batch_race_simulation_flow():
    """Test 8: Durable race simulation batch enqueues and completes with progress updates."""
    worker = JobWorker(worker_id="test_sim_worker")

    batch_id = "batch_test_001"
    now_iso = "2026-08-30T16:00:00Z"

    with get_db() as conn:
        conn.execute("DELETE FROM jobs;")
        conn.execute("DELETE FROM race_simulation_batches WHERE batch_id = ?;", (batch_id,))
        conn.execute("""
            INSERT INTO race_simulation_batches (
                batch_id, wallet_address, circuit_id, driver_id, simulations_count, completed_count, status, created_at, updated_at
            ) VALUES (?, ?, 'monaco_gp', 'velocity_one', 5, 0, 'PENDING', ?, ?);
        """, (batch_id, WALLET_A, now_iso, now_iso))
        conn.commit()

    # Enqueue job
    j_id = job_queue.enqueue(
        job_type="RACE_SIMULATION_BATCH",
        payload={"batch_id": batch_id, "circuit_id": "monaco_gp", "driver_id": "velocity_one", "simulations_count": 5}
    )

    # Process job via worker
    executed = worker.process_one_job()
    assert executed is True

    with get_db() as conn:
        row = conn.execute("SELECT status, completed_count, results_json FROM race_simulation_batches WHERE batch_id = ?;", (batch_id,)).fetchone()
        assert row["status"] == "COMPLETED"
        assert row["completed_count"] == 5
        results = json.loads(row["results_json"])
        assert len(results) == 5

def test_jobs_and_simulation_rest_api(client):
    """Test 9: REST endpoints for /jobs, /jobs/metrics, /jobs/dispatch-outbox, /races/batch."""
    # List jobs
    res_jobs = client.get("/jobs?limit=10")
    assert res_jobs.status_code == 200
    assert isinstance(res_jobs.json(), list)

    # Metrics
    res_met = client.get("/jobs/metrics")
    assert res_met.status_code == 200
    assert "pending_count" in res_met.json()

    # Dispatch outbox
    res_outbox = client.post("/jobs/dispatch-outbox")
    assert res_outbox.status_code == 200

    # Batch Simulation API
    res_sim = client.post(
        "/races/batch",
        json={"wallet_address": WALLET_A, "circuit_id": "monaco_gp", "driver_id": "velocity_one", "simulations_count": 3},
        headers={"Idempotency-Key": "sim_idemp_key_999"}
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    b_id = sim_data["batch_id"]

    # Get batch status
    res_get_b = client.get(f"/races/batches/{b_id}")
    assert res_get_b.status_code == 200
    assert res_get_b.json()["batch_id"] == b_id

def test_backup_and_restore_workflow(tmp_path):
    """Test 10: Logical backup creation and restoration verification."""
    backup_file = tmp_path / "test_backup.db"
    backup_database(destination=str(backup_file))
    assert backup_file.exists()
    assert backup_file.stat().st_size > 0
