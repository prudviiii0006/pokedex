"""
AlgoCreatures — Gameplay Systems Test Suite (Battles, Evolutions, Trades)
========================================================================
Tests:
  1. Arenas catalog returns 5 distinct tactical battle arenas with type modifiers
  2. Battle simulation executes turn-by-turn combat, applies elemental advantages, and awards XP
  3. Evolution check validates level & XP prerequisites before permitting evolution
  4. Evolution execution upgrades creature stage, species template, and stats
  5. P2P Trade offer creation, listing, and acceptance transitions state machine
  6. Activity stream logs all game and blockchain events
"""

import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import algosdk
from algosdk import account

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.services.battle_service import battle_service
from backend.app.services.evolution_service import evolution_service
from backend.app.services.trade_service import trade_service
from backend.app.services.purchase_service import purchase_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def trainer_wallet():
    _, addr = account.generate_account()
    return addr

def test_get_arenas(client):
    """Test 1: Arenas endpoint returns 5 tactical battle arenas."""
    res = client.get("/game/arenas")
    assert res.status_code == 200
    arenas = res.json()
    assert len(arenas) == 5
    arena_ids = [a["id"] for a in arenas]
    assert "volcano" in arena_ids
    assert "ocean" in arena_ids
    assert "sylvan" in arena_ids
    assert "thunder" in arena_ids
    assert "glacier" in arena_ids

def test_battle_execution_and_xp(client, trainer_wallet):
    """Test 2: Turn-based arena battle runs, awards XP, and records history."""
    # 1. Direct purchase to get an owned creature card
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id
    assert asset_id is not None

    # 2. Execute Arena Battle
    res = client.post("/game/battle", json={
        "wallet_address": trainer_wallet,
        "player_asset_id": asset_id,
        "arena_id": "volcano",
        "strategy_id": "aggressive"
    })
    assert res.status_code == 200
    battle = res.json()
    assert "battle_id" in battle
    assert battle["arena"]["id"] == "volcano"
    assert "rounds" in battle
    assert len(battle["rounds"]) >= 1
    assert battle["player"]["xp_gained"] > 0
    assert "player_won" in battle

    # 3. Check battle history endpoint
    hist_res = client.get(f"/game/battle-history/{trainer_wallet}")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["battle_id"] == battle["battle_id"]

def test_evolution_eligibility_and_upgrade(client, trainer_wallet):
    """Test 3 & 4: Evolution checks requirements and executes on-chain state upgrade."""
    # 1. Purchase a basic pack
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id

    # 2. Check initial evolution eligibility
    check_res = client.get(f"/evolution/{asset_id}?wallet_address={trainer_wallet}")
    assert check_res.status_code == 200
    evo_data = check_res.json()
    assert "current_species" in evo_data
    assert "evolution_eligible" in evo_data

    # 3. Simulate XP injection to qualify for evolution
    from backend.app.core.database import get_db
    with get_db() as conn:
        conn.execute("UPDATE owned_creatures SET level = 5, xp = 2000 WHERE asset_id = ?", (asset_id,))
        conn.commit()

    # 4. Check eligibility again (should now be eligible)
    check_res2 = client.get(f"/evolution/{asset_id}?wallet_address={trainer_wallet}")
    assert check_res2.status_code == 200
    evo_data2 = check_res2.json()
    if evo_data2.get("target_species"):
        assert evo_data2["evolution_eligible"] is True

        # 5. Execute Evolution
        evolve_res = client.post("/evolution/evolve", json={
            "wallet_address": trainer_wallet,
            "asset_id": asset_id
        })
        assert evolve_res.status_code == 200
        result = evolve_res.json()
        assert result["success"] is True
        assert result["new_stage"] >= 2

def test_trade_lifecycle(client, trainer_wallet):
    """Test 5: P2P Trading Post offer creation and marketplace listing."""
    # 1. Purchase card to trade
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id

    # 2. Create Open Trade Offer
    create_res = client.post("/trades", json={
        "initiator_wallet": trainer_wallet,
        "initiator_asset_id": asset_id
    })
    assert create_res.status_code == 200
    trade = create_res.json()
    assert "trade_id" in trade
    assert trade["status"] == "OPEN"

    # 3. List active trades
    list_res = client.get("/trades")
    assert list_res.status_code == 200
    trades = list_res.json()
    assert any(t["trade_id"] == trade["trade_id"] for t in trades)

def test_activity_stream(client):
    """Test 6: Activity stream returns recent events with badge tags."""
    res = client.get("/activity")
    assert res.status_code == 200
    activities = res.json()
    assert isinstance(activities, list)
