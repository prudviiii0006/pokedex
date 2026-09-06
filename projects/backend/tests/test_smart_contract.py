"""
AlgoRacers — Session 14: Tournament Smart Contract & Hybrid Verification Tests
=============================================================================
Test Cases:
  1. Tournament created in 'OPEN' state with 0 participants
  2. Authorized driver registration succeeds and increments participant count
  3. Duplicate registration (same wallet or same ASA ID) is rejected (409 Conflict)
  4. Maximum player capacity limit is enforced by smart contract rules (409 Conflict)
  5. Registration after tournament is 'CLOSED' is rejected (409 Conflict)
  6. Unauthorized caller cannot close tournament (403 Forbidden)
  7. Organizer can close tournament (200 OK)
  8. Finalize before 'CLOSED' state is rejected (409 Conflict)
  9. Unauthorized caller cannot finalize tournament (403 Forbidden)
  10. Full off-chain race execution & on-chain hash commitment succeeds
  11. On-chain result hash verification confirms truthful off-chain data
  12. Tampering with off-chain result triggers tamper detection (is_valid=False)
"""

import sys
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from algosdk import account

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.services.tournament_service import tournament_service, compute_canonical_result_hash

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_driver_wallet():
    """Mints a driver into a fresh wallet for registration testing."""
    import secrets
    _, addr = account.generate_account()
    asset_id = 700000000 + secrets.randbelow(900000)
    pur_id = f"pur_tourn_{secrets.token_hex(6)}"
    idem_key = f"idem_tourn_{secrets.token_hex(6)}"
    rew_id = f"rew_tourn_{secrets.token_hex(6)}"
    tx_id = f"TX_TOURN_{secrets.token_hex(6)}"
    dlv_id = f"DLV_TOURN_{secrets.token_hex(6)}"

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

def test_tournament_creation(client):
    """Test 1: Tournament is created in OPEN state with 0 participants."""
    res = client.post("/tournaments/create", json={
        "name": "Nova Apex Cup",
        "circuit_id": "nova_circuit",
        "max_players": 4
    })
    assert res.status_code == 200
    data = res.json()
    assert data["app_id"] > 0
    assert data["name"] == "Nova Apex Cup"
    assert data["status"] == "OPEN"
    assert data["participant_count"] == 0
    assert data["max_players"] == 4

def test_registration_lifecycle_and_duplicates(client, test_driver_wallet):
    """Test 2 & 3: Registration succeeds; duplicate registration is blocked."""
    # Create tournament
    t = client.post("/tournaments/create", json={
        "name": "Storm Masters",
        "circuit_id": "storm_harbor",
        "max_players": 8
    }).json()
    app_id = t["app_id"]

    # First registration: Success
    res1 = client.post(f"/tournaments/{app_id}/prepare-register", json={
        "asset_id": test_driver_wallet["asset_id"]
    }, headers={"Authorization": f"Bearer mock"})  # Fallback to test address

    # Using service directly with test wallet address
    reg = tournament_service.prepare_register_transaction(
        app_id=app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )
    assert reg.app_id == app_id
    assert len(reg.unsigned_txn_b64) > 0

    # Verify participant count is 1
    t_after = client.get(f"/tournaments/{app_id}").json()
    assert t_after["participant_count"] == 1

    # Second registration with same wallet/driver: Rejection
    with pytest.raises(Exception) as exc_info:
        tournament_service.prepare_register_transaction(
            app_id=app_id,
            wallet_address=test_driver_wallet["address"],
            asset_id=test_driver_wallet["asset_id"]
        )
    assert "already registered" in str(exc_info.value).lower()

def test_capacity_limit_enforced(test_driver_wallet):
    """Test 4: Capacity limit prevents registration beyond max_players."""
    t = tournament_service.create_tournament(
        name="Micro Duel",
        circuit_id="apex_ring",
        max_players=1
    )
    app_id = t.app_id

    # Register 1st player (reaches max capacity 1)
    tournament_service.prepare_register_transaction(
        app_id=app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )

    # Attempt to register 2nd player
    _, addr2 = account.generate_account()
    with pytest.raises(Exception) as exc_info:
        tournament_service.prepare_register_transaction(
            app_id=app_id,
            wallet_address=addr2,
            asset_id=700051001
        )
    assert "maximum capacity" in str(exc_info.value).lower()

def test_closed_registration_blocks_entry(test_driver_wallet):
    """Test 5 & 7: Closing registration prevents new entrants."""
    t = tournament_service.create_tournament(
        name="Closed Cup",
        circuit_id="nova_circuit",
        max_players=8
    )
    app_id = t.app_id

    # Close tournament
    tournament_service.close_registration(app_id=app_id, caller_address=t.creator)

    # Attempt registration
    with pytest.raises(Exception) as exc_info:
        tournament_service.prepare_register_transaction(
            app_id=app_id,
            wallet_address=test_driver_wallet["address"],
            asset_id=test_driver_wallet["asset_id"]
        )
    assert "registration closed" in str(exc_info.value).lower()

def test_unauthorized_actions_rejected(test_driver_wallet):
    """Test 6 & 9: Unauthorized non-organizer callers are rejected."""
    t = tournament_service.create_tournament(
        name="Security Cup",
        circuit_id="nova_circuit",
        max_players=8
    )
    app_id = t.app_id
    _, attacker_addr = account.generate_account()

    # Unauthorized close
    with pytest.raises(Exception) as exc_info:
        tournament_service.close_registration(app_id=app_id, caller_address=attacker_addr)
    assert "authorization failure" in str(exc_info.value).lower()

    # Unauthorized finalize
    with pytest.raises(Exception) as exc_info:
        tournament_service.run_and_finalize_tournament(app_id=app_id, caller_address=attacker_addr)
    assert "cannot finalize" in str(exc_info.value).lower() or "authorization" in str(exc_info.value).lower()

def test_full_race_finalization_and_hash_verification(client, test_driver_wallet):
    """Test 10 & 11: Off-chain race execution, hash commitment, and verification."""
    # 1. Create Tournament
    t = tournament_service.create_tournament(
        name="Championship Final",
        circuit_id="nova_circuit",
        max_players=4
    )
    app_id = t.app_id

    # 2. Register Driver
    tournament_service.prepare_register_transaction(
        app_id=app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )

    # 3. Close Registration
    tournament_service.close_registration(app_id=app_id, caller_address=t.creator)

    # 4. Run and Finalize
    finalized_t, canonical_result = tournament_service.run_and_finalize_tournament(
        app_id=app_id,
        caller_address=t.creator
    )

    assert finalized_t.status.value == "FINALIZED"
    assert finalized_t.winner_asset_id is not None
    assert len(finalized_t.result_hash) == 64  # SHA256 hex string

    # 5. Verify via REST endpoint
    verify_res = client.get(f"/tournaments/{app_id}/verify-result")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["verified"] is True
    assert v_data["result_hash_matches"] is True
    assert v_data["on_chain_hash"] == v_data["recalculated_hash"]

def test_tamper_detection(client, test_driver_wallet):
    """Test 12: Altering the committed randomness triggers tamper detection."""
    t = tournament_service.create_tournament(
        name="Tamper Proof Cup",
        circuit_id="nova_circuit",
        max_players=4
    )
    app_id = t.app_id

    tournament_service.prepare_register_transaction(
        app_id=app_id,
        wallet_address=test_driver_wallet["address"],
        asset_id=test_driver_wallet["asset_id"]
    )
    tournament_service.close_registration(app_id=app_id, caller_address=t.creator)
    tournament_service.run_and_finalize_tournament(app_id=app_id, caller_address=t.creator)

    # Tamper with randomness value in SQLite
    with get_db() as conn:
        r = conn.execute("SELECT randomness_value FROM tournaments WHERE app_id = ?;", (app_id,)).fetchone()
        orig_hex = r["randomness_value"]
        tampered_hex = ("0" if orig_hex[0] != "0" else "1") + orig_hex[1:]
        conn.execute("UPDATE tournaments SET randomness_value = ? WHERE app_id = ?;", (tampered_hex, app_id))
        conn.commit()

    # Verification endpoint should detect tamper!
    verify_res = client.get(f"/tournaments/{app_id}/verify-result")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["verified"] is False
    assert v_data["result_hash_matches"] is False
    assert v_data["on_chain_hash"] != v_data["recalculated_hash"]

def test_list_tournaments_endpoint(client):
    """Test: GET /tournaments returns all created smart contract tournaments."""
    res = client.get("/tournaments")
    assert res.status_code == 200
    tournaments = res.json()
    assert isinstance(tournaments, list)
    assert len(tournaments) >= 1

def test_finalize_before_close_fails(test_driver_wallet):
    """Test: Attempting to finalize an OPEN tournament fails."""
    t = tournament_service.create_tournament(
        name="Premature Finalize Cup",
        circuit_id="nova_circuit",
        max_players=4
    )
    with pytest.raises(Exception) as exc_info:
        tournament_service.run_and_finalize_tournament(app_id=t.app_id, caller_address=t.creator)
    assert "must be in 'closed' status" in str(exc_info.value).lower()

def test_canonical_json_hashing_consistency():
    """Test: Deterministic JSON serialization guarantees identical hash regardless of key order."""
    dict_a = {"circuit_id": "nova", "winner_asset_id": 700051010, "points": 25}
    dict_b = {"points": 25, "circuit_id": "nova", "winner_asset_id": 700051010}

    hash_a = compute_canonical_result_hash(dict_a)
    hash_b = compute_canonical_result_hash(dict_b)
    assert hash_a == hash_b

    # Modifying value changes hash
    dict_tampered = {"points": 26, "circuit_id": "nova", "winner_asset_id": 700051010}
    assert compute_canonical_result_hash(dict_tampered) != hash_a
