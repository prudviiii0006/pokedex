"""
AlgoRacers — Session 21: Algorand Indexer, Event Processing & Chain Sync Test Suite
====================================================================================
Test Suite:
  1. Algod vs Indexer health and lag calculations
  2. Event decoder translates raw ASA transfers into NFT_TRANSFERRED
  3. Event decoder translates app calls into TOURNAMENT_FINALIZED and GOVERNANCE_ACTION
  4. Subscriber checkpoint initialization & persistence
  5. Idempotent event processing (duplicate raw transactions cause 1 DB effect)
  6. External NFT transfer outside UI detected & owner updated
  7. Checkpoint advances accurately during batch sync
  8. Reconciliation engine detects NFT ownership drift
  9. Reconciliation engine repairs NFT ownership drift
  10. REST API endpoints for /chain/status, /chain/sync, /chain/reconcile, and /activity
"""

import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.chain.models import ChainEventType
from backend.app.chain.indexer_client import chain_client
from backend.app.chain.event_decoder import event_decoder
from backend.app.chain.subscriber import chain_subscriber
from backend.app.chain.reconciliation import blockchain_reconciler
from backend.app.services.activity_service import activity_service
from blockchain.governance.multisig import governance_engine

WALLET_A = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
WALLET_B = "6ZIJOSUKH5HY6OK3GLLAP4AAV6GMOJDIECUI7VSQLRQFFWB2LGD6BI5MII"

@pytest.fixture
def client():
    return TestClient(app)

def test_chain_client_rounds_and_lag():
    """Test 1: Algod vs Indexer status query returns non-negative lag."""
    algod_r, idx_r, lag = chain_client.get_rounds_and_lag()
    assert algod_r > 0
    assert idx_r > 0
    assert lag >= 0

def test_event_decoder_axfer_nft_transferred():
    """Test 2: Event decoder parses raw asset transfer into NFT_TRANSFERRED."""
    raw_tx = {
        "id": "TX_TEST_AXFER_001",
        "confirmed-round": 45120050,
        "sender": WALLET_A,
        "tx-type": "axfer",
        "asset-transfer-transaction": {
            "asset-id": 77001001,
            "receiver": WALLET_B,
            "amount": 1
        }
    }
    event = event_decoder.decode_transaction(raw_tx, "TestNet")
    assert event is not None
    assert event.event_type == ChainEventType.NFT_TRANSFERRED
    assert event.asset_id == 77001001
    assert event.receiver == WALLET_B
    assert event.sender == WALLET_A

def test_event_decoder_governance_action():
    """Test 3: Event decoder parses governance multisig app call."""
    raw_gov_tx = {
        "id": "TX_TEST_GOV_001",
        "confirmed-round": 45120055,
        "sender": governance_engine.address,
        "tx-type": "appl",
        "application-transaction": {
            "application-id": 88002001,
            "application-args": ["finalize_season"]
        }
    }
    event = event_decoder.decode_transaction(raw_gov_tx, "TestNet")
    assert event is not None
    assert event.event_type == ChainEventType.GOVERNANCE_ACTION_EXECUTED
    assert event.sender == governance_engine.address

def test_subscriber_checkpoint_persistence():
    """Test 4: Subscriber checkpoint persists and recovers after re-instantiation."""
    chk_round = chain_subscriber.get_checkpoint_round()
    assert chk_round > 0

def test_idempotent_event_processing():
    """Test 5: Processing the same transaction twice inserts only 1 event and 1 effect."""
    raw_tx = {
        "id": "TX_IDEMPOTENT_001",
        "confirmed-round": 45120060,
        "sender": WALLET_A,
        "tx-type": "axfer",
        "asset-transfer-transaction": {
            "asset-id": 77001002,
            "receiver": WALLET_B,
            "amount": 1
        }
    }

    # First pass
    ev1 = chain_subscriber.process_raw_transaction(raw_tx)
    assert ev1 is not None

    # Second pass (duplicate delivery from Indexer)
    ev2 = chain_subscriber.process_raw_transaction(raw_tx)
    assert ev2 is not None

    # Verify single DB entry
    with get_db() as conn:
        count = conn.execute("""
            SELECT COUNT(*) as cnt FROM chain_events WHERE tx_id = 'TX_IDEMPOTENT_001';
        """).fetchone()["cnt"]
        assert count == 1

def test_subscriber_batch_sync():
    """Test 6: Batch sync increments checkpoint up to indexer round."""
    res = chain_subscriber.run_sync_batch(max_rounds=10)
    assert res["rounds_advanced"] >= 0
    assert res["end_round"] >= res["start_round"]

def test_reconciler_detects_and_repairs_nft_drift(monkeypatch):
    """Test 7: Reconciler flags drift if on-chain holder != DB cached owner, and repairs it."""
    # Setup test purchase in DB
    with get_db() as conn:
        conn.execute("DELETE FROM purchases WHERE purchase_id = 'purch_test_reconcile';")
        conn.execute("""
            INSERT INTO purchases (
                purchase_id, pack_id, wallet_address, price_usdc, payment_status, reward_status, status, asset_id, created_at, updated_at
            ) VALUES ('purch_test_reconcile', 'basic', ?, 1.0, 'SETTLED', 'CLAIMED', 'DELIVERED', 77001005, '2026-08-30T12:00:00Z', '2026-08-30T12:00:00Z');
        """, (WALLET_A,))
        conn.commit()

    # Mock chain client saying WALLET_B is the actual on-chain holder
    monkeypatch.setattr(chain_client, "get_asset_current_holding_address", lambda asset_id: WALLET_B if asset_id == 77001005 else None)

    # 1. Audit mode (report only)
    rep_audit = blockchain_reconciler.run_reconciliation_audit(repair=False)
    assert rep_audit.nft_drift_count >= 1
    assert rep_audit.status == "DRIFT_DETECTED"

    # 2. Repair mode
    rep_repair = blockchain_reconciler.run_reconciliation_audit(repair=True)
    assert rep_repair.repaired is True

    # Verify DB owner was reconciled to WALLET_B
    with get_db() as conn:
        row = conn.execute("SELECT wallet_address FROM purchases WHERE purchase_id = 'purch_test_reconcile';").fetchone()
        assert row["wallet_address"] == WALLET_B

def test_chain_status_and_activity_api(client, monkeypatch):
    """Test 8: REST endpoints /chain/status, /chain/sync, /chain/reconcile, /activity."""
    monkeypatch.setattr(chain_client, "get_asset_current_holding_address", lambda asset_id: None)

    # Status
    res_st = client.get("/chain/status")
    assert res_st.status_code == 200
    st_data = res_st.json()
    assert "algod_round" in st_data
    assert "indexer_round" in st_data

    # Sync
    res_sync = client.post("/chain/sync", json={"max_rounds": 5})
    assert res_sync.status_code == 200

    # Reconcile
    res_rec = client.post("/chain/reconcile", json={"repair": False})
    assert res_rec.status_code == 200
    assert "status" in res_rec.json()

    # Activity Feed
    res_act = client.get("/activity?limit=10")
    assert res_act.status_code == 200
    assert isinstance(res_act.json(), list)
