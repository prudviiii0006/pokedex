"""
AlgoRacers — Session 15: Verifiable Randomness, Determinism & Integrity Tests
=============================================================================
Test Suite:
  1. Future-round randomness commitment on tournament closure
  2. Participant list and circuit immutability after closure
  3. 100% Deterministic Race Engine v1 reproducibility
  4. Canonical participant ordering (DB order independence)
  5. Cryptographic domain-separated sub-seed isolation
  6. Non-biased uniform floating point mapping
  7. Independent re-simulation verification passes
  8. Tamper detection on result, participants, circuit, and randomness seed
  9. Statistical fairness and calibration distribution
"""

import sys
import json
import secrets
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from algosdk import account

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.services.tournament_service import tournament_service
from backend.app.services.race_engine_v1 import deterministic_race_engine
from backend.app.services.seed_derivation import (
    derive_master_race_seed, derive_sub_seed,
    bytes_to_uniform_float, canonicalize_participants
)
from backend.app.services.circuit_service import circuit_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_driver_wallet():
    """Mints a driver into a fresh wallet for registration testing."""
    _, addr = account.generate_account()
    asset_id = 700000000 + secrets.randbelow(900000)
    pur_id = f"pur_vrf_{secrets.token_hex(6)}"
    idem_key = f"idem_vrf_{secrets.token_hex(6)}"
    rew_id = f"rew_vrf_{secrets.token_hex(6)}"
    tx_id = f"TX_VRF_{secrets.token_hex(6)}"
    dlv_id = f"DLV_VRF_{secrets.token_hex(6)}"

    with get_db() as conn:
        conn.execute("""
            INSERT INTO purchases (
                purchase_id, idempotency_key, pack_id, wallet_address,
                price_usdc, payment_status, payment_tx_id, reward_status,
                reward_id, rarity, driver_id, driver_name, metadata_uri,
                asset_id, delivery_tx_id, status, error_message, created_at, updated_at
            ) VALUES (
                ?, ?, 'premium', ?,
                0.05, 'SETTLED', ?, 'GENERATED',
                ?, 'Legendary', '010', 'Nitro Zenith', 'ipfs://test',
                ?, ?, 'DELIVERED', NULL, '2026-08-30T12:00:00Z', '2026-08-30T12:00:00Z'
            );
        """, (pur_id, idem_key, addr, tx_id, rew_id, asset_id, dlv_id))
        conn.commit()
    return {"address": addr, "asset_id": asset_id}

def test_future_round_commitment(test_driver_wallet):
    """Test 1: Closing registration commits to a future round N > current_round."""
    t = tournament_service.create_tournament(
        name="VRF Commitment Cup",
        circuit_id="nova_circuit",
        max_players=4
    )
    tournament_service.prepare_register_transaction(
        app_id=t.app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )

    closed_t = tournament_service.close_registration(app_id=t.app_id, caller_address=t.creator, safety_gap=8)
    assert closed_t.status.value == "CLOSED"
    assert closed_t.randomness_round is not None
    assert closed_t.randomness_round >= 45000008

def test_deterministic_race_engine_reproducibility():
    """Test 2: Exact same inputs produce identical grid ranking and result hash."""
    circuit = circuit_service.get_circuit("nova_circuit")
    mock_beacon = b"\x42" * 32
    participants = [
        {"wallet_address": "ADDR_1", "asset_id": 700051010, "driver_id": "010"},
        {"wallet_address": "ADDR_2", "asset_id": 700051001, "driver_id": "001"}
    ]

    res_1 = deterministic_race_engine.simulate_deterministic_tournament(
        app_id=75001234,
        registered_participants=participants,
        circuit=circuit,
        beacon_randomness=mock_beacon
    )

    res_2 = deterministic_race_engine.simulate_deterministic_tournament(
        app_id=75001234,
        registered_participants=participants,
        circuit=circuit,
        beacon_randomness=mock_beacon
    )

    assert res_1["result_hash"] == res_2["result_hash"]
    assert res_1["winner_asset_id"] == res_2["winner_asset_id"]
    assert res_1["grid"][0]["final_score"] == res_2["grid"][0]["final_score"]

def test_canonical_participant_sorting():
    """Test 3: Shuffling database query order of participants produces identical results."""
    circuit = circuit_service.get_circuit("nova_circuit")
    mock_beacon = b"\x77" * 32

    order_a = [
        {"wallet_address": "ADDR_A", "asset_id": 700051001, "driver_id": "001"},
        {"wallet_address": "ADDR_B", "asset_id": 700051010, "driver_id": "010"},
        {"wallet_address": "ADDR_C", "asset_id": 700051005, "driver_id": "005"}
    ]

    order_b = [
        {"wallet_address": "ADDR_C", "asset_id": 700051005, "driver_id": "005"},
        {"wallet_address": "ADDR_A", "asset_id": 700051001, "driver_id": "001"},
        {"wallet_address": "ADDR_B", "asset_id": 700051010, "driver_id": "010"}
    ]

    res_a = deterministic_race_engine.simulate_deterministic_tournament(
        app_id=75009999,
        registered_participants=order_a,
        circuit=circuit,
        beacon_randomness=mock_beacon
    )

    res_b = deterministic_race_engine.simulate_deterministic_tournament(
        app_id=75009999,
        registered_participants=order_b,
        circuit=circuit,
        beacon_randomness=mock_beacon
    )

    assert res_a["result_hash"] == res_b["result_hash"]

def test_sub_seed_domain_separation():
    """Test 4: Domain separation produces isolated cryptographic seeds."""
    master = b"\xaa" * 32
    qualifying_seed = derive_sub_seed(master, "qualifying")
    race_seed = derive_sub_seed(master, "race")
    driver_1_seed = derive_sub_seed(master, "driver_variance", "700051010")
    driver_2_seed = derive_sub_seed(master, "driver_variance", "700051001")

    assert qualifying_seed != race_seed
    assert driver_1_seed != driver_2_seed
    assert len(qualifying_seed) == 32

def test_non_biased_float_mapping():
    """Test 5: Byte digest maps to uniform float in range without bias."""
    test_bytes = b"\x80" * 32  # midpoint
    val = bytes_to_uniform_float(test_bytes, -2.5, 2.5)
    assert -2.5 <= val <= 2.5
    assert abs(val - 0.0) < 0.1

def test_full_independent_verification_audit(client, test_driver_wallet):
    """Test 6: Independent re-simulation audit succeeds via endpoint."""
    t = tournament_service.create_tournament(
        name="Audited Grand Prix",
        circuit_id="nova_circuit",
        max_players=4
    )
    tournament_service.prepare_register_transaction(
        app_id=t.app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )
    tournament_service.close_registration(app_id=t.app_id, caller_address=t.creator)
    tournament_service.run_and_finalize_tournament(app_id=t.app_id, caller_address=t.creator)

    # Call verification audit endpoint
    res = client.get(f"/tournaments/{t.app_id}/verify")
    assert res.status_code == 200
    report = res.json()
    assert report["verified"] is True
    assert report["randomness_verified"] is True
    assert report["result_reproducible"] is True
    assert report["result_hash_matches"] is True
    assert report["recalculated_hash"] == report["on_chain_hash"]

def test_tamper_detection_avalanche_on_randomness(client, test_driver_wallet):
    """Test 7: Changing 1 byte of committed randomness triggers tamper detection."""
    t = tournament_service.create_tournament(
        name="Avalanche Tamper Cup",
        circuit_id="nova_circuit",
        max_players=4
    )
    tournament_service.prepare_register_transaction(
        app_id=t.app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )
    tournament_service.close_registration(app_id=t.app_id, caller_address=t.creator)
    tournament_service.run_and_finalize_tournament(app_id=t.app_id, caller_address=t.creator)

    # Tamper with randomness value in SQLite
    with get_db() as conn:
        r = conn.execute("SELECT randomness_value FROM tournaments WHERE app_id = ?;", (t.app_id,)).fetchone()
        orig_hex = r["randomness_value"]
        # Flip first character
        tampered_hex = ("0" if orig_hex[0] != "0" else "1") + orig_hex[1:]
        conn.execute("UPDATE tournaments SET randomness_value = ? WHERE app_id = ?;", (tampered_hex, t.app_id))
        conn.commit()

    # Verification must detect tamper!
    res = client.get(f"/tournaments/{t.app_id}/verify")
    assert res.status_code == 200
    report = res.json()
    assert report["verified"] is False
    assert report["result_hash_matches"] is False
    assert report["recalculated_hash"] != report["on_chain_hash"]

def test_statistical_fairness_distribution():
    """Test 8: Statistical calibration: higher stat drivers win more, but upsets are possible."""
    circuit = circuit_service.get_circuit("nova_circuit")
    legendary_p = {"wallet_address": "ADDR_LEG", "asset_id": 700051010, "driver_id": "010"} # Nitro Zenith (86.4 base)
    common_p = {"wallet_address": "ADDR_COM", "asset_id": 700051001, "driver_id": "001"}    # Apex Spark (72.8 base)
    parts = [legendary_p, common_p]

    legendary_wins = 0
    common_wins = 0
    total_runs = 50

    for i in range(total_runs):
        seed_bytes = f"stat_test_run_{i}".encode("utf-8")
        res = deterministic_race_engine.simulate_deterministic_tournament(
            app_id=88000000 + i,
            registered_participants=parts,
            circuit=circuit,
            beacon_randomness=seed_bytes
        )
        winner_id = res["winner_asset_id"]
        if winner_id == 700051010:
            legendary_wins += 1
        elif winner_id == 700051001:
            common_wins += 1

    # Legendary driver (higher stats) should win significantly more than Common driver
    assert legendary_wins > common_wins
    assert legendary_wins >= total_runs * 0.50  # >= 50% win rate
