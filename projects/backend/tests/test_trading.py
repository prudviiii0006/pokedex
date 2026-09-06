"""
AlgoRacers — Core Product Redesign: Trading Test Suite
Module: tests/test_trading.py
=====================================================
Tests 1-for-1 atomic card swaps:
  - Create trade offer (valid & invalid)
  - Ownership validation on creation and acceptance
  - Cancellation by creator
  - Rejection of double acceptance
  - Atomic ownership swap upon completion
  - Integration with Garage collection resolver
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.database import get_db, init_db

client = TestClient(app)

PLAYER_A = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
PLAYER_B = "OYSAOLISWLCZE62XDNNUHYMGLP7LVQNDEUKIJIJVGSF453MWMD6TVU4DAE"
PLAYER_C = "ZR6TPHBANVPUH6CT2I2AWGWFFJ4GTXVMP5DXOT3CLADCZOTLG7UVH53MI4"

@pytest.fixture(autouse=True)
def setup_trading_test_db():
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM trade_offers;")
        conn.execute("DELETE FROM card_ownership_records;")
        conn.execute("DELETE FROM fusion_inputs;")
        conn.execute("DELETE FROM fusion_operations;")

        # Player A owns Asset #2001 (Velocity One - Rare)
        conn.execute("""
            INSERT INTO card_ownership_records (
                asset_id, driver_id, driver_name, team, rarity,
                current_owner, status, origin_type, created_at, updated_at
            ) VALUES (2001, '001', 'Velocity One', 'Apex Pulse', 'Rare', ?, 'AVAILABLE', 'SEED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
        """, (PLAYER_A,))

        # Player B owns Asset #2002 (Nova Rush - Epic)
        conn.execute("""
            INSERT INTO card_ownership_records (
                asset_id, driver_id, driver_name, team, rarity,
                current_owner, status, origin_type, created_at, updated_at
            ) VALUES (2002, '002', 'Nova Rush', 'Pulse Racing', 'Epic', ?, 'AVAILABLE', 'SEED', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');
        """, (PLAYER_B,))

        conn.commit()

def test_create_trade_offer_validation():
    # 1. Player A cannot offer card they don't own (2002 is owned by Player B)
    res_unowned = client.post("/api/v1/trades", json={
        "creator_wallet": PLAYER_A,
        "offered_asset_id": 2002,
        "requested_asset_id": 2001
    })
    assert res_unowned.status_code == 403
    assert "does not own" in res_unowned.json()["detail"]

    # 2. Cannot offer and request same asset
    res_same = client.post("/api/v1/trades", json={
        "creator_wallet": PLAYER_A,
        "offered_asset_id": 2001,
        "requested_asset_id": 2001
    })
    assert res_same.status_code == 400
    assert "cannot be the same" in res_same.json()["detail"]

    # 3. Valid creation
    res_valid = client.post("/api/v1/trades", json={
        "creator_wallet": PLAYER_A,
        "offered_asset_id": 2001,
        "requested_asset_id": 2002,
        "notes": "Looking for Nova Rush Epic!"
    })
    assert res_valid.status_code == 200
    trade_data = res_valid.json()
    assert trade_data["status"] == "OPEN"
    assert trade_data["offered_asset_id"] == 2001
    assert trade_data["requested_asset_id"] == 2002

def test_cancel_trade_offer():
    # Create trade
    res_create = client.post("/api/v1/trades", json={
        "creator_wallet": PLAYER_A,
        "offered_asset_id": 2001,
        "requested_asset_id": 2002
    })
    trade_id = res_create.json()["trade_id"]

    # Player B cannot cancel Player A's trade
    res_bad_cancel = client.post(f"/api/v1/trades/{trade_id}/cancel?wallet_address={PLAYER_B}")
    assert res_bad_cancel.status_code == 403

    # Player A cancels their own trade
    res_cancel = client.post(f"/api/v1/trades/{trade_id}/cancel?wallet_address={PLAYER_A}")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Offered card is released back to AVAILABLE
    with get_db() as conn:
        row = conn.execute("SELECT status FROM card_ownership_records WHERE asset_id = 2001").fetchone()
        assert row["status"] == "AVAILABLE"

def test_successful_atomic_trade_acceptance():
    # 1. Player A creates offer (2001 for 2002)
    res_create = client.post("/api/v1/trades", json={
        "creator_wallet": PLAYER_A,
        "offered_asset_id": 2001,
        "requested_asset_id": 2002
    })
    trade_id = res_create.json()["trade_id"]

    # 2. Player A cannot accept their own trade
    res_self_accept = client.post(f"/api/v1/trades/{trade_id}/accept", json={
        "acceptor_wallet": PLAYER_A
    })
    assert res_self_accept.status_code == 400

    # 3. Third party Player C who doesn't own requested card cannot accept
    res_unowned_accept = client.post(f"/api/v1/trades/{trade_id}/accept", json={
        "acceptor_wallet": PLAYER_C
    })
    assert res_unowned_accept.status_code == 403

    # 4. Player B accepts the trade
    res_accept = client.post(f"/api/v1/trades/{trade_id}/accept", json={
        "acceptor_wallet": PLAYER_B
    })
    assert res_accept.status_code == 200
    data = res_accept.json()
    assert data["status"] == "COMPLETED"
    assert data["accepted_by"] == PLAYER_B
    assert data["atomic_group_id"] is not None

    # 5. Verify ownership swapped in database
    with get_db() as conn:
        row_2001 = conn.execute("SELECT current_owner, status FROM card_ownership_records WHERE asset_id = 2001").fetchone()
        row_2002 = conn.execute("SELECT current_owner, status FROM card_ownership_records WHERE asset_id = 2002").fetchone()
        
        # Asset 2001 is now owned by Player B
        assert row_2001["current_owner"] == PLAYER_B
        assert row_2001["status"] == "AVAILABLE"

        # Asset 2002 is now owned by Player A
        assert row_2002["current_owner"] == PLAYER_A
        assert row_2002["status"] == "AVAILABLE"

    # 6. Verify Garage collection endpoints reflect swapped ownership
    col_a = client.get(f"/api/v1/wallets/{PLAYER_A}/collection").json()
    col_b = client.get(f"/api/v1/wallets/{PLAYER_B}/collection").json()

    a_asset_ids = [d["asset_id"] for d in col_a["drivers"]]
    b_asset_ids = [d["asset_id"] for d in col_b["drivers"]]

    assert 2002 in a_asset_ids
    assert 2001 not in a_asset_ids
    assert 2001 in b_asset_ids
    assert 2002 not in b_asset_ids

    # 7. Cannot accept already completed trade
    res_repeat = client.post(f"/api/v1/trades/{trade_id}/accept", json={
        "acceptor_wallet": PLAYER_B
    })
    assert res_repeat.status_code == 409
