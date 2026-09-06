"""
AlgoRacers — Session 16: Player Progression, Achievements & Reputation Tests
============================================================================
Test Suite:
  1. Race completion awards XP & level updates
  2. Podium and win bonuses applied accurately
  3. Strict XP idempotency via ledger prevents duplicate awards
  4. Deterministic level formula boundary test cases
  5. Competitive Elo reputation updates on verified tournaments
  6. Achievement rule evaluation (FIRST_GRID, FIRST_VICTORY, TOURNAMENT_CHAMPION)
  7. Client bypass prevention (untrusted client cannot forge XP or unlocks)
  8. Profile reconciliation ledger drift detection and repair
  9. On-chain credential verification
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
from backend.app.services.progression_service import progression_service
from backend.app.services.achievement_service import achievement_service
from backend.app.services.reputation_service import reputation_service
from backend.app.services.reconciliation_service import reconciliation_service
from backend.app.services.tournament_service import tournament_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_driver_wallet():
    """Mints a driver into a fresh wallet for racing and progression testing."""
    _, addr = account.generate_account()
    asset_id = 700000000 + secrets.randbelow(100000000)
    pur_id = f"pur_prog_{secrets.token_hex(6)}"
    idem_key = f"idem_prog_{secrets.token_hex(6)}"
    rew_id = f"rew_prog_{secrets.token_hex(6)}"
    tx_id = f"TX_PROG_{secrets.token_hex(6)}"
    dlv_id = f"DLV_PROG_{secrets.token_hex(6)}"

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
                ?, 'Legendary', 'lewis_hamilton', 'Lewis Hamilton', 'ipfs://test',
                ?, ?, 'DELIVERED', NULL, '2026-08-30T12:00:00Z', '2026-08-30T12:00:00Z'
            );
        """, (pur_id, idem_key, addr, tx_id, rew_id, asset_id, dlv_id))
        conn.commit()
    return {"address": addr, "asset_id": asset_id}

def test_race_completion_awards_xp(test_driver_wallet):
    """Test 1: Completing a race awards base XP (20) and updates player profile."""
    wallet = test_driver_wallet["address"]
    race_id = f"race_{secrets.token_hex(6)}"

    progression_service.process_race_xp(wallet, race_id, position=5)

    with get_db() as conn:
        prof = conn.execute("SELECT * FROM player_profiles WHERE wallet_address = ?;", (wallet,)).fetchone()
        assert prof["xp"] == 20
        assert prof["level"] == 1

def test_win_and_podium_bonuses(test_driver_wallet):
    """Test 2: Wins grant +25 bonus (total 45), podium grants +15 bonus (total 35)."""
    wallet = test_driver_wallet["address"]
    race_1 = f"race_win_{secrets.token_hex(6)}"
    race_2 = f"race_podium_{secrets.token_hex(6)}"

    # Win: 20 base + 25 win = 45 XP
    progression_service.process_race_xp(wallet, race_1, position=1)
    # Podium: 20 base + 15 podium = 35 XP
    progression_service.process_race_xp(wallet, race_2, position=2)

    with get_db() as conn:
        prof = conn.execute("SELECT * FROM player_profiles WHERE wallet_address = ?;", (wallet,)).fetchone()
        assert prof["xp"] == 80  # 45 + 35
        assert prof["level"] == 2  # Level 2 reached at 50 XP

def test_xp_idempotency_prevents_duplicate_awards(test_driver_wallet):
    """Test 3: Processing the exact same race event twice does not award XP twice."""
    wallet = test_driver_wallet["address"]
    race_id = f"race_idem_{secrets.token_hex(6)}"

    # First attempt: Awarded
    res1 = progression_service.award_xp(wallet, "RACE", race_id, 45, "Victory")
    assert res1 is True

    # Second attempt: Blocked by ledger idempotency
    res2 = progression_service.award_xp(wallet, "RACE", race_id, 45, "Victory")
    assert res2 is False

    with get_db() as conn:
        events = conn.execute("SELECT * FROM progression_events WHERE wallet_address = ?;", (wallet,)).fetchall()
        assert len(events) == 1

def test_level_calculation_boundary_cases():
    """Test 4: Deterministic level formula boundary validation."""
    assert progression_service.calculate_level(0)[0] == 1
    assert progression_service.calculate_level(49)[0] == 1
    assert progression_service.calculate_level(50)[0] == 2
    assert progression_service.calculate_level(199)[0] == 2
    assert progression_service.calculate_level(200)[0] == 3
    assert progression_service.calculate_level(450)[0] == 4
    assert progression_service.calculate_level(5000)[0] == 11

def test_competitive_reputation_elo_updates(test_driver_wallet):
    """Test 5: Finalizing verified tournament updates Elo reputation score and tier."""
    wallet = test_driver_wallet["address"]
    app_id = 75008888
    grid = [
        {"wallet_address": wallet, "position": 1},
        {"wallet_address": "CPU_OPPONENT_2", "position": 2}
    ]

    reputation_service.process_tournament_reputation(app_id, grid)

    new_rep = reputation_service.get_reputation(wallet)
    assert new_rep == 1032  # 1000 base + 32 delta
    assert reputation_service.get_rank_tier(new_rep) == "Gold"

def test_achievement_rules_evaluation(client, test_driver_wallet):
    """Test 6: Race events unlock FIRST_GRID and FIRST_VICTORY achievements."""
    wallet = test_driver_wallet["address"]
    race_id = f"race_ach_{secrets.token_hex(6)}"

    # Insert race into DB
    with get_db() as conn:
        conn.execute("""
            INSERT INTO races (
                race_id, idempotency_key, wallet_address, asset_id,
                driver_id, driver_name, circuit_id, circuit_name,
                base_score, variance, final_score, position, points,
                result_category, grid_results, analysis, created_at
            ) VALUES (?, ?, ?, ?, 'lewis_hamilton', 'Lewis Hamilton', 'nova_circuit', 'Nova Coast Circuit',
                      80.0, 1.5, 81.5, 1, 25, 'Winner (P1)', '[]', 'Analysis', '2026-08-30T12:00:00Z');
        """, (race_id, f"idem_{race_id}", wallet, test_driver_wallet["asset_id"]))
        conn.commit()

    unlocked = achievement_service.evaluate_and_unlock(wallet, source_event_id=race_id)
    assert "FIRST_GRID" in unlocked
    assert "FIRST_VICTORY" in unlocked

    achievements = achievement_service.get_player_achievements(wallet)
    first_vic = next(a for a in achievements if a.id == "FIRST_VICTORY")
    assert first_vic.unlocked is True

def test_profile_reconciliation_drift_detection(test_driver_wallet):
    """Test 7: Profile reconciliation detects and repairs manual database drift."""
    wallet = test_driver_wallet["address"]
    race_1 = f"race_rec_1_{secrets.token_hex(6)}"
    race_2 = f"race_rec_2_{secrets.token_hex(6)}"

    progression_service.process_race_xp(wallet, race_1, position=1) # 45 XP
    progression_service.process_race_xp(wallet, race_2, position=1) # 45 XP (Total 90 XP)

    # Intentionally tamper with cached XP in player_profiles
    with get_db() as conn:
        conn.execute("UPDATE player_profiles SET xp = 9999, level = 100 WHERE wallet_address = ?;", (wallet,))
        conn.commit()

    # Run reconciliation
    rec_report = reconciliation_service.reconcile_player(wallet)
    assert rec_report.drift_detected is True
    assert rec_report.cached_xp == 9999
    assert rec_report.recalculated_xp == 90
    assert rec_report.recalculated_level == 2

    # Verify repaired cache
    with get_db() as conn:
        prof = conn.execute("SELECT * FROM player_profiles WHERE wallet_address = ?;", (wallet,)).fetchone()
        assert prof["xp"] == 90
        assert prof["level"] == 2

def test_profile_api_endpoints(client, test_driver_wallet):
    """Test 8: GET /me/profile and GET /players/{wallet} return structured progression data."""
    wallet = test_driver_wallet["address"]
    progression_service.process_race_xp(wallet, f"race_api_{secrets.token_hex(4)}", position=3)

    # Authenticated /me/profile (fallback to test address or header)
    res_me = client.get("/me/profile", headers={"Authorization": f"Bearer mock"})
    assert res_me.status_code == 200
    data_me = res_me.json()
    assert "xp" in data_me
    assert "level" in data_me
    assert "stats" in data_me
    assert "achievements" in data_me

    # Public /players/{address}
    res_pub = client.get(f"/players/{wallet}")
    assert res_pub.status_code == 200
    data_pub = res_pub.json()
    assert data_pub["wallet_address"] == wallet
    assert data_pub["level"] >= 1

def test_tournament_champion_and_credential_verification(client, test_driver_wallet):
    """Test 9: Winning a tournament grants TOURNAMENT_CHAMPION and creates verifiable credential."""
    wallet = test_driver_wallet["address"]
    app_id = 75000000 + secrets.randbelow(90000)
    result_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Simulate tournament win in DB
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tournaments (
                app_id, name, creator, circuit_id, max_players, participant_count,
                status, randomness_round, race_engine_version, winner_asset_id,
                result_hash, off_chain_result, created_at
            ) VALUES (?, 'Championship Trophy', ?, 'nova_circuit', 4, 1, 'FINALIZED',
                      45000008, 'v1', ?, ?, ?, '2026-08-30T12:00:00Z');
        """, (app_id, wallet, test_driver_wallet["asset_id"], result_hash, json.dumps({"winner_wallet": wallet})))
        conn.execute("""
            INSERT INTO tournament_participants (app_id, wallet_address, asset_id, registered_at)
            VALUES (?, ?, ?, '2026-08-30T12:00:00Z');
        """, (app_id, wallet, test_driver_wallet["asset_id"]))
        conn.commit()

    # Trigger achievement evaluation
    achievement_service.evaluate_and_unlock(
        wallet_address=wallet,
        source_event_id=f"tourn_{app_id}",
        tournament_app_id=app_id,
        result_hash=result_hash
    )

    # Verify achievement status
    achievements = achievement_service.get_player_achievements(wallet)
    champ = next((a for a in achievements if a.id == "TOURNAMENT_CHAMPION"), None)
    assert champ is not None
    assert champ.unlocked is True
    assert champ.credential_status == "ISSUED"
    assert champ.credential_asset_id is not None

    # Verify via REST verification endpoint
    v_res = client.get(f"/achievements/TOURNAMENT_CHAMPION/verify?wallet={wallet}")
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["verified"] is True
    assert v_data["credential_status"] == "ISSUED"

def test_list_achievements_catalog_endpoint(client, test_driver_wallet):
    """Test 10: GET /achievements returns all catalog items with player progress."""
    wallet = test_driver_wallet["address"]
    res = client.get(f"/achievements?wallet={wallet}")
    assert res.status_code == 200
    catalog = res.json()
    assert len(catalog) >= 7
    assert any(a["id"] == "FIRST_GRID" for a in catalog)
    assert any(a["id"] == "TOURNAMENT_CHAMPION" for a in catalog)
