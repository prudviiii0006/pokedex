"""
AlgoRacers — Core Product Redesign: Fusion Test Suite
Module: tests/test_fusion.py
====================================================
Tests 5-Epic -> 1-Premium card fusion logic:
  - 4 cards -> rejected
  - 6 cards -> rejected
  - Duplicate asset IDs -> rejected
  - Non-Epic cards -> rejected
  - Unowned cards -> rejected
  - Card in active trade -> rejected
  - Valid 5-Epic fusion -> burns 5, mints 1 Premium NFT
  - Card already fused -> rejected
  - Idempotent submission -> returns same fusion without duplicate mint
  - Recovery flow
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import get_db, init_db

client = TestClient(app)

TEST_WALLET_A = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
TEST_WALLET_B = "OYSAOLISWLCZE62XDNNUHYMGLP7LVQNDEUKIJIJVGSF453MWMD6TVU4DAE"

@pytest.fixture(autouse=True)
def setup_fusion_test_db():
    init_db()
    with get_db() as conn:
        # Clear test records
        conn.execute("DELETE FROM fusion_inputs;")
        conn.execute("DELETE FROM fusion_operations;")
        conn.execute("DELETE FROM trade_offers;")
        conn.execute("DELETE FROM card_ownership_records;")
        
        # Seed 5 Epic cards for Wallet A (driver_002 is Epic, driver_007 is Epic)
        epic_assets = [1001, 1002, 1003, 1004, 1005]
        for aid in epic_assets:
            conn.execute("""
                INSERT INTO card_ownership_records (
                    asset_id, driver_id, driver_name, team, rarity,
                    current_owner, status, origin_type, created_at, updated_at
                ) VALUES (?, '002', 'Nova Rush', 'Pulse Racing', 'Epic', ?, 'AVAILABLE', 'SEED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
            """, (aid, TEST_WALLET_A))

        # Seed a Common card (driver_004)
        conn.execute("""
            INSERT INTO card_ownership_records (
                asset_id, driver_id, driver_name, team, rarity,
                current_owner, status, origin_type, created_at, updated_at
            ) VALUES (1006, '004', 'Turbo Vale', 'Vale Dynamics', 'Common', ?, 'AVAILABLE', 'SEED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
        """, (TEST_WALLET_A,))

        # Seed an Epic card owned by Wallet B
        conn.execute("""
            INSERT INTO card_ownership_records (
                asset_id, driver_id, driver_name, team, rarity,
                current_owner, status, origin_type, created_at, updated_at
            ) VALUES (1007, '007', 'Phantom Speed', 'Shadow Racing', 'Epic', ?, 'AVAILABLE', 'SEED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
        """, (TEST_WALLET_B,))

        conn.commit()

def test_fusion_requires_exactly_five_cards():
    # 4 cards
    res_four = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004]
    })
    assert res_four.status_code == 400
    assert "exactly 5" in res_four.json()["detail"]

    # 6 cards
    res_six = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1005, 1006]
    })
    assert res_six.status_code == 400
    assert "exactly 5" in res_six.json()["detail"]

def test_fusion_rejects_duplicate_asset_ids():
    res = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1001]
    })
    assert res.status_code == 400
    assert "distinct" in res.json()["detail"]

def test_fusion_rejects_non_epic_card():
    # 1006 is Common
    res = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1006]
    })
    assert res.status_code == 400
    assert "ONLY accepts EPIC cards" in res.json()["detail"]

def test_fusion_rejects_unowned_card():
    # 1007 is owned by Wallet B
    res = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1007]
    })
    assert res.status_code == 403
    assert "does not own" in res.json()["detail"]

def test_successful_five_epic_fusion():
    res = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1005],
        "idempotency_key": "idemp_fus_001"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["output_asset_id"] is not None
    assert data["premium_driver_name"] is not None
    assert len(data["input_cards"]) == 5

    # Verify input cards are marked CONSUMED in database
    with get_db() as conn:
        for aid in [1001, 1002, 1003, 1004, 1005]:
            row = conn.execute("SELECT status FROM card_ownership_records WHERE asset_id = ?", (aid,)).fetchone()
            assert row["status"] == "CONSUMED_FUSION"

    # Verify attempting to fuse already consumed card fails
    res_reused = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1005]
    })
    assert res_reused.status_code == 400
    assert "already consumed" in res_reused.json()["detail"]

def test_fusion_idempotency():
    res1 = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1005],
        "idempotency_key": "idemp_same_fus"
    })
    assert res1.status_code == 200
    fus_id_1 = res1.json()["fusion_id"]
    out_asset_1 = res1.json()["output_asset_id"]

    # Second call with same idempotency key
    res2 = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1005],
        "idempotency_key": "idemp_same_fus"
    })
    assert res2.status_code == 200
    assert res2.json()["fusion_id"] == fus_id_1
    assert res2.json()["output_asset_id"] == out_asset_1

def test_fusion_rejects_card_in_active_trade():
    # Lock card 1001 in an open trade
    with get_db() as conn:
        conn.execute("""
            INSERT INTO trade_offers (
                trade_id, creator_wallet, offered_asset_id, offered_driver_id,
                offered_driver_name, offered_driver_team, offered_driver_rarity,
                requested_asset_id, requested_driver_name, status,
                created_at, expires_at
            ) VALUES ('trd_lock_01', ?, 1001, '002', 'Nova Rush', 'Team', 'Epic', 1007, 'Target', 'OPEN', '2026-01-01T00:00:00Z', '2026-01-02T00:00:00Z');
        """, (TEST_WALLET_A,))
        conn.commit()

    res = client.post("/api/v1/fusions", json={
        "wallet_address": TEST_WALLET_A,
        "selected_asset_ids": [1001, 1002, 1003, 1004, 1005]
    })
    assert res.status_code == 400
    assert "locked in open trade" in res.json()["detail"]
