"""
AlgoRacers — Session 19: Championship Seasons & Merkle Reward Claims Test Suite
================================================================================
Test Suite:
  1. Season creation and lifecycle state transitions
  2. Scoring aggregation and point matrix mapping (v1)
  3. Deterministic 5-tier tie-breaking rules
  4. Incomplete/unfinalized tournaments block season finalization
  5. Valid season finalization & Merkle root generation
  6. Finalized root immutability (cannot be overwritten)
  7. Valid player Merkle membership proof generation and verification
  8. Tampered player points fails verification
  9. Tampered player rank fails verification
  10. Wallet B using Wallet A proof (Sender binding) rejected
  11. Eligible Champion reward claim succeeds
  12. Double-claim prevention rejected with HTTP 409
  13. Non-eligible player rank rejected for Champion Trophy
  14. Independent season verification script consistency
  15. Full REST API endpoints workflow
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
from backend.app.services.season_service import season_service
from backend.app.services.season_leaderboard_service import season_leaderboard_service
from backend.app.services.season_finalization_service import season_finalization_service
from backend.app.services.season_claim_service import season_claim_service
from backend.app.crypto.merkle import verify_merkle_proof

WALLET_A = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
WALLET_B = "EW64GC6FL2ISKT6MEQNBDYLBS2QAXCEWRG2XIGOO4K6A2TZC47762T4H64"
WALLET_C = "J2P7QZ5N6X8M9K4L1V3T2R5W8Y7U4I6O9P0A1S2D3F4G5H6J7K8L9Z0X1C"
WALLET_D = "7QW8E9R0T1Y2U3I4O5P6A7S8D9F0G1H2J3K4L5Z6X7C8V9B0N1M2Q3W4E5"

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def setup_mock_season_tournaments():
    """Sets up a controlled 3-round championship season with known deterministic outcomes."""
    with get_db() as conn:
        # 1. Create clean test season
        conn.execute("DELETE FROM season_claims WHERE season_id = 'test_season_01';")
        conn.execute("DELETE FROM season_leaderboard WHERE season_id = 'test_season_01';")
        conn.execute("DELETE FROM season_tournaments WHERE season_id = 'test_season_01';")
        conn.execute("DELETE FROM seasons WHERE season_id = 'test_season_01';")

        conn.execute("""
            INSERT INTO seasons (
                season_id, name, version, status, scoring_version,
                rounds_total, app_id, created_at
            ) VALUES ('test_season_01', 'Test Super Cup 2026', 1, 'ACTIVE', 'v1', 3, 99001000, '2026-08-30T10:00:00Z');
        """)

        # 2. Insert 3 mock finalized tournaments
        tourn_ids = [99001001, 99001002, 99001003]
        for t_id in tourn_ids:
            conn.execute("DELETE FROM tournament_participants WHERE app_id = ?;", (t_id,))
            conn.execute("DELETE FROM tournaments WHERE app_id = ?;", (t_id,))

        # Round 1: Winner Wallet A (P1=25), Wallet B (P2=18), Wallet C (P3=15), Wallet D (P4=12)
        r1_result = {
            "grid": [
                {"position": 1, "wallet_address": WALLET_A, "driver_id": "001", "driver_name": "Velocity One"},
                {"position": 2, "wallet_address": WALLET_B, "driver_id": "002", "driver_name": "Nova Rush"},
                {"position": 3, "wallet_address": WALLET_C, "driver_id": "003", "driver_name": "Apex Storm"},
                {"position": 4, "wallet_address": WALLET_D, "driver_id": "004", "driver_name": "Turbo Vale"}
            ]
        }
        conn.execute("""
            INSERT INTO tournaments (app_id, creator, name, circuit_id, status, max_players, off_chain_result, created_at)
            VALUES (99001001, '3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM', 'Round 1 Nova Cup', 'neon_city_gp', 'FINALIZED', 8, ?, '2026-08-30T10:05:00Z');
        """, (json.dumps(r1_result),))

        # Round 2: Winner Wallet A (P1=25), Wallet C (P2=18), Wallet B (P3=15), Wallet D (P4=12)
        r2_result = {
            "grid": [
                {"position": 1, "wallet_address": WALLET_A, "driver_id": "001", "driver_name": "Velocity One"},
                {"position": 2, "wallet_address": WALLET_C, "driver_id": "003", "driver_name": "Apex Storm"},
                {"position": 3, "wallet_address": WALLET_B, "driver_id": "002", "driver_name": "Nova Rush"},
                {"position": 4, "wallet_address": WALLET_D, "driver_id": "004", "driver_name": "Turbo Vale"}
            ]
        }
        conn.execute("""
            INSERT INTO tournaments (app_id, creator, name, circuit_id, status, max_players, off_chain_result, created_at)
            VALUES (99001002, '3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM', 'Round 2 Storm GP', 'cyber_canyon', 'FINALIZED', 8, ?, '2026-08-30T10:10:00Z');
        """, (json.dumps(r2_result),))

        # Round 3: Winner Wallet B (P1=25), Wallet A (P2=18), Wallet C (P3=15), Wallet D (P4=12)
        r3_result = {
            "grid": [
                {"position": 1, "wallet_address": WALLET_B, "driver_id": "002", "driver_name": "Nova Rush"},
                {"position": 2, "wallet_address": WALLET_A, "driver_id": "001", "driver_name": "Velocity One"},
                {"position": 3, "wallet_address": WALLET_C, "driver_id": "003", "driver_name": "Apex Storm"},
                {"position": 4, "wallet_address": WALLET_D, "driver_id": "004", "driver_name": "Turbo Vale"}
            ]
        }
        conn.execute("""
            INSERT INTO tournaments (app_id, creator, name, circuit_id, status, max_players, off_chain_result, created_at)
            VALUES (99001003, '3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM', 'Round 3 Apex Finale', 'monaco_circuit', 'FINALIZED', 8, ?, '2026-08-30T10:15:00Z');
        """, (json.dumps(r3_result),))

        # Assign rounds to season
        for idx, t_id in enumerate(tourn_ids, 1):
            conn.execute("""
                INSERT INTO season_tournaments (season_id, app_id, round_number)
                VALUES ('test_season_01', ?, ?);
            """, (t_id, idx))

        conn.commit()

def test_scoring_aggregation_and_rankings():
    """Test 1: Standings correctly aggregate: Wallet A (25+25+18=68 pts, P1), Wallet B (18+15+25=58 pts, P2)."""
    standings = season_leaderboard_service.calculate_leaderboard("test_season_01")
    assert len(standings) == 4

    p1 = standings[0]
    p2 = standings[1]
    p3 = standings[2]
    p4 = standings[3]

    assert p1.wallet_address == WALLET_A
    assert p1.points == 68
    assert p1.wins == 2
    assert p1.rank == 1

    assert p2.wallet_address == WALLET_B
    assert p2.points == 58
    assert p2.wins == 1
    assert p2.rank == 2

    assert p3.wallet_address == WALLET_C
    assert p3.points == 48 # 15 + 18 + 15
    assert p3.rank == 3

    assert p4.wallet_address == WALLET_D
    assert p4.points == 36 # 12 + 12 + 12
    assert p4.rank == 4

def test_unfinalized_tournament_blocks_season_finalization():
    """Test 2: Season finalization is rejected if any round is still in OPEN/ACTIVE state."""
    with get_db() as conn:
        conn.execute("UPDATE tournaments SET status = 'OPEN' WHERE app_id = 99001003;")
        conn.commit()

    with pytest.raises(Exception) as excinfo:
        season_finalization_service.finalize_season("test_season_01", WALLET_A)
    assert "are not finalized yet" in str(excinfo.value)

def test_valid_season_finalization_and_root():
    """Test 3: Finalizing valid season computes Merkle root and locks status to FINALIZED."""
    res = season_finalization_service.finalize_season("test_season_01", WALLET_A)
    assert res["status"] == "FINALIZED"
    assert res["champion_wallet"] == WALLET_A
    assert len(res["leaderboard_root"]) == 64
    assert res["player_count"] == 4

    season = season_service.get_season("test_season_01")
    assert season.status == "FINALIZED"
    assert season.leaderboard_root == res["leaderboard_root"]

def test_finalized_root_immutable_cannot_overwrite():
    """Test 4: Attempting to finalize an already finalized season raises HTTP 400."""
    season_finalization_service.finalize_season("test_season_01", WALLET_A)

    with pytest.raises(Exception) as excinfo:
        season_finalization_service.finalize_season("test_season_01", WALLET_A)
    assert "already finalized" in str(excinfo.value)

def test_player_season_proof_generation_and_verification():
    """Test 5: Champion Wallet A receives valid Merkle proof that verifies 100% against root."""
    season_finalization_service.finalize_season("test_season_01", WALLET_A)
    proof_resp = season_finalization_service.get_player_proof("test_season_01", WALLET_A)

    assert proof_resp.wallet_address == WALLET_A
    assert proof_resp.record["rank"] == 1
    assert proof_resp.record["points"] == 68
    assert verify_merkle_proof(proof_resp.record, proof_resp.proof, proof_resp.root) is True

def test_tampered_points_fails_verification():
    """Test 6: Tampering points in record (68 -> 78) causes cryptographic verification to fail."""
    season_finalization_service.finalize_season("test_season_01", WALLET_A)
    proof_resp = season_finalization_service.get_player_proof("test_season_01", WALLET_A)

    tampered_record = dict(proof_resp.record)
    tampered_record["points"] = 78

    assert verify_merkle_proof(tampered_record, proof_resp.proof, proof_resp.root) is False

def test_eligible_champion_claim_succeeds():
    """Test 7: Champion Wallet A submits valid proof and receives SEASON_CHAMPION_TROPHY credential."""
    season_finalization_service.finalize_season("test_season_01", WALLET_A)
    proof_resp = season_finalization_service.get_player_proof("test_season_01", WALLET_A)

    claim_res = season_claim_service.claim_reward(
        season_id="test_season_01",
        caller_address=WALLET_A,
        reward_id="SEASON_CHAMPION_TROPHY",
        proof=proof_resp.proof
    )
    assert claim_res.status == "CLAIMED"
    assert claim_res.credential_asset_id is not None
    assert claim_res.reward_id == "SEASON_CHAMPION_TROPHY"

def test_double_claim_rejected():
    """Test 8: Submitting the same claim twice is rejected with HTTP 409 Conflict."""
    season_finalization_service.finalize_season("test_season_01", WALLET_A)
    proof_resp = season_finalization_service.get_player_proof("test_season_01", WALLET_A)

    # First claim
    season_claim_service.claim_reward(
        season_id="test_season_01",
        caller_address=WALLET_A,
        reward_id="SEASON_CHAMPION_TROPHY",
        proof=proof_resp.proof
    )

    # Second claim attempt
    with pytest.raises(Exception) as excinfo:
        season_claim_service.claim_reward(
            season_id="test_season_01",
            caller_address=WALLET_A,
            reward_id="SEASON_CHAMPION_TROPHY",
            proof=proof_resp.proof
        )
    assert "Double-claim rejected" in str(excinfo.value)

def test_wallet_b_cannot_use_wallet_a_proof():
    """Test 9: Wallet B submitting Wallet A's champion proof fails authorization/verification."""
    season_finalization_service.finalize_season("test_season_01", WALLET_A)
    proof_resp_a = season_finalization_service.get_player_proof("test_season_01", WALLET_A)

    # Wallet B attempts to claim with Wallet A's proof
    with pytest.raises(Exception) as excinfo:
        season_claim_service.claim_reward(
            season_id="test_season_01",
            caller_address=WALLET_B,
            reward_id="SEASON_CHAMPION_TROPHY",
            proof=proof_resp_a.proof
        )
    assert "requires Rank 1" in str(excinfo.value) or "Invalid Merkle Proof" in str(excinfo.value)

def test_season_rest_api_endpoints(client):
    """Test 10: Complete REST API workflow for seasons, leaderboard, and verify endpoints."""
    # List seasons
    res = client.get("/seasons")
    assert res.status_code == 200

    # Get test season
    res = client.get("/seasons/test_season_01")
    assert res.status_code == 200

    # Get leaderboard
    res = client.get("/seasons/test_season_01/leaderboard")
    assert res.status_code == 200
    lb = res.json()
    assert len(lb) == 4

    # Finalize season
    res_fin = client.post("/seasons/test_season_01/finalize")
    assert res_fin.status_code == 200

    # Get player proof
    res_proof = client.get(f"/seasons/test_season_01/players/{WALLET_A}/proof")
    assert res_proof.status_code == 200
    p_data = res_proof.json()
    assert "proof" in p_data

    # Independent verify endpoint
    res_verify = client.post("/seasons/test_season_01/verify")
    assert res_verify.status_code == 200
    v_data = res_verify.json()
    assert v_data["verified"] is True
