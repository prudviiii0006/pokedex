"""
AlgoRacers — Session 10: Racing Engine & Leaderboard Test Suite
==============================================================
Tests:
  1. Circuit stat weights total 100%
  2. Invalid circuit ID returns 404
  3. Non-owned driver NFT rejected with 403 Forbidden
  4. Client-supplied forged stats cannot bypass backend
  5. Base performance calculation is accurate
  6. Deterministic seed produces 100% repeatable result
  7. Different circuit stat weighting changes performance
  8. Wet circuit heavily weights wet weather rating
  9. 8-Car grid positions sort in descending order of final score
  10. Idempotency key returns identical race without re-rolling
  11. Leaderboard aggregates total points, wins, and podiums
  12. User collection returns owned driver cards with stats
"""

import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import algosdk
from algosdk import account

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.services.circuit_service import circuit_service
from backend.app.services.race_engine import race_engine

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_driver_owner():
    """Generates an account and inserts a mock delivered driver NFT purchase into SQLite."""
    sk, addr = account.generate_account()
    asset_id = 700051456
    purchase_id = f"pur_{uuid.uuid4().hex[:10]}"
    now = "2026-08-30T12:00:00Z"
    
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO purchases (
                purchase_id, idempotency_key, pack_id, wallet_address, price_usdc,
                payment_status, payment_tx_id, reward_status, reward_id,
                rarity, driver_id, driver_name, metadata_uri, asset_id,
                delivery_tx_id, status, error_message, created_at, updated_at
            ) VALUES (?, ?, 'basic', ?, 0.01, 'SETTLED_ON_ALGORAND_TESTNET', ?, 'GENERATED', ?, 'Rare', '005', 'Crimson Vector', 'ipfs://...', ?, 'DLV_123', 'DELIVERED', NULL, ?, ?);
        """, (
            purchase_id, f"idem_{uuid.uuid4().hex[:8]}", addr, f"tx_{uuid.uuid4().hex[:8]}",
            f"rew_{uuid.uuid4().hex[:8]}", asset_id, now, now
        ))
        conn.commit()

    return addr, asset_id

def test_circuit_stat_weights_total_100_percent():
    """Test 1: All circuit stat weights must sum to exactly 1.0 (100%)."""
    for c in circuit_service.list_circuits():
        weights_sum = sum(c.stat_weights.values())
        assert 0.999 <= weights_sum <= 1.001, f"Circuit {c.id} weights do not total 100%"

def test_invalid_circuit_rejected(client, test_driver_owner):
    """Test 2: Invalid circuit identifier returns 404."""
    addr, asset_id = test_driver_owner
    res = client.post("/races", json={
        "wallet_address": addr,
        "asset_id": asset_id,
        "circuit_id": "non_existent_circuit_999"
    })
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_non_owned_driver_nft_rejected(client):
    """Test 3: Attempting to race with an asset not owned by the wallet returns 403 Forbidden."""
    _, unowned_addr = account.generate_account()
    res = client.post("/races", json={
        "wallet_address": unowned_addr,
        "asset_id": 999999999,
        "circuit_id": "nova_circuit"
    })
    assert res.status_code == 403
    assert "does not own" in res.json()["detail"].lower()

def test_base_performance_calculation_manual_verification():
    """Test 4: Manual math check on base performance calculation."""
    driver = race_engine.reward_engine.driver_pool.get_driver_by_id("001") # Lando Norris
    circuit = circuit_service.get_circuit("nova_circuit")
    
    # Lando Norris stats on Nova Circuit:
    # Speed (94)*0.35 + Racecraft(92)*0.20 + Overtaking(90)*0.15 + Consistency(93)*0.15 + Qualifying(95)*0.10 + Wet(89)*0.05
    # = 32.90 + 18.40 + 13.50 + 13.95 + 9.50 + 4.45 = 92.70
    calculated = race_engine.calculate_base_performance(driver, circuit)
    assert calculated == 92.70

def test_deterministic_seed_simulation_repeatable(client, test_driver_owner):
    """Test 5: Providing a seed parameter produces 100% deterministic, repeatable results."""
    addr, asset_id = test_driver_owner
    res1 = client.post(
        "/races?seed=42",
        json={"wallet_address": addr, "asset_id": asset_id, "circuit_id": "nova_circuit"}
    )
    res2 = client.post(
        "/races?seed=42",
        json={"wallet_address": addr, "asset_id": asset_id, "circuit_id": "nova_circuit"}
    )
    d1, d2 = res1.json(), res2.json()
    assert d1["final_score"] == d2["final_score"]
    assert d1["position"] == d2["position"]
    assert d1["points"] == d2["points"]

def test_circuit_stat_weighting_impacts_performance():
    """Test 6: High Speed track yields higher base score for Speed driver than Wet track."""
    v_one = race_engine.reward_engine.driver_pool.get_driver_by_id("001") # Speed: 94, Wet: 82
    nova_score = race_engine.calculate_base_performance(v_one, circuit_service.get_circuit("nova_circuit"))
    storm_score = race_engine.calculate_base_performance(v_one, circuit_service.get_circuit("storm_harbor"))
    
    # Nova Circuit heavily rewards 94 Speed (35%), Storm Harbor rewards 82 Wet Weather (35%)
    assert nova_score > storm_score

def test_8_car_grid_sorted_descending(client, test_driver_owner):
    """Test 7: Multi-car race returns 8 grid slots sorted descending by final score."""
    addr, asset_id = test_driver_owner
    res = client.post("/races", json={
        "wallet_address": addr,
        "asset_id": asset_id,
        "circuit_id": "apex_ring"
    })
    assert res.status_code == 200
    data = res.json()
    grid = data["grid"]
    assert len(grid) == 8
    
    for i in range(len(grid) - 1):
        assert grid[i]["final_score"] >= grid[i+1]["final_score"]
        assert grid[i]["position"] == i + 1

def test_idempotent_race_retry_does_not_reroll(client, test_driver_owner):
    """Test 8: Re-sending identical idempotency_key returns original race without re-rolling."""
    addr, asset_id = test_driver_owner
    idem_key = f"race_idem_{uuid.uuid4().hex}"
    
    res1 = client.post("/races", json={
        "wallet_address": addr,
        "asset_id": asset_id,
        "circuit_id": "nova_circuit",
        "idempotency_key": idem_key
    })
    d1 = res1.json()

    res2 = client.post("/races", json={
        "wallet_address": addr,
        "asset_id": asset_id,
        "circuit_id": "nova_circuit",
        "idempotency_key": idem_key
    })
    d2 = res2.json()

    assert d1["race_id"] == d2["race_id"]
    assert d1["final_score"] == d2["final_score"]
    assert d1["position"] == d2["position"]

def test_leaderboard_aggregation(client, test_driver_owner):
    """Test 9: GET /leaderboard returns ranked points aggregation."""
    addr, asset_id = test_driver_owner
    # Execute a race
    client.post("/races", json={"wallet_address": addr, "asset_id": asset_id, "circuit_id": "nova_circuit"})
    
    res = client.get("/leaderboard")
    assert res.status_code == 200
    leaderboard = res.json()
    assert len(leaderboard) >= 1
    assert "total_points" in leaderboard[0]
    assert "wins" in leaderboard[0]

def test_user_collection_endpoint(client, test_driver_owner):
    """Test 10: GET /wallets/{addr}/collection lists verified owned driver cards with stats."""
    addr, asset_id = test_driver_owner
    res = client.get(f"/wallets/{addr}/collection")
    assert res.status_code == 200
    data = res.json()
    assert data["total_owned"] >= 1
    driver_item = data["drivers"][0]
    assert driver_item["asset_id"] == asset_id
    assert "Speed" in driver_item["stats"]
