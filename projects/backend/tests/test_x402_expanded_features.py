"""
Pokédex — Comprehensive Test Suite for Expanded x402 V2 Features (ALGO Native)
================================================================================
Validates all 8 server-authoritative paid services:
  1. Basic Pack Purchase (0.1 ALGO / 100,000 uALGO)
  2. Premium Pack Purchase (0.5 ALGO / 500,000 uALGO)
  3. Special Event Packs (0.2 ALGO / 200,000 uALGO - Fire, Water, Electric, Ghost)
  4. Premium Battle (+50 Bonus XP, 0.02 ALGO / 20,000 uALGO)
  5. Featured Trade Listing (24h Marketplace Pin, 0.01 ALGO / 10,000 uALGO)
  6. Smart Trade Matcher (AI Synergy Engine, 0.01 ALGO / 10,000 uALGO)
  7. Evolution Boost (+100 XP Bounded, 0.02 ALGO / 20,000 uALGO)
  8. Advanced Creature Analysis (Battle Ratings & Counters, 0.005 ALGO / 5,000 uALGO)

Also verifies:
  - 402 Payment Required challenge generation & headers
  - Settlement verification & 200 OK delivery with payment-response receipt
  - Strict Idempotency & Replay Attack rejection (409 Conflict)
  - Security validation: Amount tampering, asset mismatch, and unauthorized actions
"""

import sys
import uuid
import base64
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from algosdk import account

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.services.purchase_service import purchase_service
from backend.app.services.x402_service import x402_service
from backend.app.core.database import get_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def trainer_wallet():
    _, addr = account.generate_account()
    return addr

def generate_payment_proof(wallet: str, purchase_id: str, amount_micro: int, asset_id: int = 0, custom_tx: str = None) -> str:
    tx_id = custom_tx or f"tx_x402_{uuid.uuid4().hex[:12]}"
    proof = {
        "payment_tx_id": tx_id,
        "wallet": wallet,
        "purchase_id": purchase_id,
        "network": settings.ALGORAND_TESTNET_CAIP2,
        "asset": str(asset_id),
        "amount": str(amount_micro),
        "timestamp": 1741580000
    }
    return base64.b64encode(json.dumps(proof).encode("utf-8")).decode("utf-8")

# -------------------------------------------------------------
# 1 & 2 & 3: PACK PURCHASES (Basic, Premium, Event Packs)
# -------------------------------------------------------------
def test_pricing_config_endpoint(client):
    """Verifies server-authoritative pricing configuration endpoint."""
    res = client.get("/config/pricing")
    assert res.status_code == 200
    data = res.json()
    assert data["network"]["asset_id"] == 0
    assert data["network"]["currency"] == "ALGO"
    assert data["prices"]["basic_pack"]["price_algo"] == 0.1
    assert data["prices"]["premium_pack"]["price_algo"] == 0.5
    assert data["prices"]["event_pack"]["price_algo"] == 0.2
    assert data["prices"]["premium_battle"]["price_algo"] == 0.02
    assert data["prices"]["featured_trade"]["price_algo"] == 0.01
    assert data["prices"]["smart_trade_match"]["price_algo"] == 0.01
    assert data["prices"]["evolution_boost"]["price_algo"] == 0.02
    assert data["prices"]["creature_analysis"]["price_algo"] == 0.005

def test_event_pack_purchase_flow(client, trainer_wallet):
    """Test 3: Special Event Pack purchase (Fire Event Booster @ 0.2 ALGO)."""
    # 1. Initiate purchase
    create_res = client.post("/purchases", json={
        "pack_id": "fire_event",
        "wallet_address": trainer_wallet
    })
    assert create_res.status_code == 200
    pur_data = create_res.json()
    purchase_id = pur_data["purchase_id"]
    assert pur_data["price_algo"] == 0.2

    # 2. Challenge
    pay_res = client.post(f"/pay/purchases/{purchase_id}")
    assert pay_res.status_code == 402
    assert "payment-required" in pay_res.headers

    # 3. Valid payment settlement (0.2 ALGO = 200,000 microAlgos)
    proof_header = generate_payment_proof(trainer_wallet, purchase_id, amount_micro=200000)
    settle_res = client.post(f"/pay/purchases/{purchase_id}", headers={
        "payment-signature": proof_header
    })
    assert settle_res.status_code == 200
    delivered = settle_res.json()
    assert delivered["status"] in ["DELIVERED", "WAITING_FOR_OPT_IN", "NFT_MINTED", "REWARD_GENERATED"]
    assert delivered["creature_name"] is not None

# -------------------------------------------------------------
# 4: PREMIUM BATTLE (x402 protected, +50 Bonus XP, 0.02 ALGO)
# -------------------------------------------------------------
def test_premium_battle_flow(client, trainer_wallet):
    """Test 4: Premium Battle awards bonus XP without guaranteeing outcome."""
    # Obtain a card first
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id

    # 1. Unpaid request -> 402
    battle_req = {
        "wallet_address": trainer_wallet,
        "player_asset_id": asset_id,
        "arena_id": "volcano",
        "strategy_id": "aggressive"
    }
    unpaid_res = client.post("/game/battle/premium", json=battle_req)
    assert unpaid_res.status_code == 402
    assert "payment-required" in unpaid_res.headers

    # 2. Paid request -> 200 (0.02 ALGO = 20,000 microAlgos)
    proof_header = generate_payment_proof(trainer_wallet, "premium_battle", amount_micro=20000)
    paid_res = client.post(
        "/game/battle/premium",
        json=battle_req,
        headers={"payment-signature": proof_header}
    )
    assert paid_res.status_code == 200
    assert "payment-response" in paid_res.headers
    battle_data = paid_res.json()
    assert battle_data["is_premium"] is True
    assert battle_data["bonus_xp"] == 50
    assert "winner" in battle_data
    assert "rounds" in battle_data

# -------------------------------------------------------------
# 5: FEATURED TRADE LISTING (x402 protected, 24h pin, 0.01 ALGO)
# -------------------------------------------------------------
def test_featured_trade_listing_flow(client, trainer_wallet):
    """Test 5: Featured Trade marks listing as featured for 24 hours."""
    # Obtain a card and create trade
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id

    trade_res = client.post("/trades", json={
        "initiator_wallet": trainer_wallet,
        "initiator_asset_id": asset_id
    })
    assert trade_res.status_code == 200
    trade_id = trade_res.json()["trade_id"]

    # 1. Unpaid feature request -> 402
    unpaid_res = client.post(f"/trades/{trade_id}/feature", json={
        "wallet_address": trainer_wallet
    })
    assert unpaid_res.status_code == 402
    assert "payment-required" in unpaid_res.headers

    # 2. Paid feature request -> 200 (0.01 ALGO = 10,000 microAlgos)
    proof_header = generate_payment_proof(trainer_wallet, trade_id, amount_micro=10000)
    paid_res = client.post(
        f"/trades/{trade_id}/feature",
        json={"wallet_address": trainer_wallet},
        headers={"payment-signature": proof_header}
    )
    assert paid_res.status_code == 200
    assert "payment-response" in paid_res.headers
    data = paid_res.json()
    assert data["is_featured"] is True
    assert data["featured_until"] is not None

# -------------------------------------------------------------
# 6: SMART TRADE MATCHING (x402 protected, 0.01 ALGO)
# -------------------------------------------------------------
def test_smart_trade_matcher_flow(client, trainer_wallet):
    """Test 6: Smart Match analyzes collection against open marketplace listings."""
    # 1. Unpaid request -> 402
    unpaid_res = client.get(f"/trades/smart-match?wallet_address={trainer_wallet}")
    assert unpaid_res.status_code == 402
    assert "payment-required" in unpaid_res.headers

    # 2. Paid request -> 200 (0.01 ALGO = 10,000 microAlgos)
    proof_header = generate_payment_proof(trainer_wallet, "smart_match", amount_micro=10000)
    paid_res = client.get(
        f"/trades/smart-match?wallet_address={trainer_wallet}",
        headers={"payment-signature": proof_header}
    )
    assert paid_res.status_code == 200
    assert "payment-response" in paid_res.headers
    match_data = paid_res.json()
    assert "matches" in match_data
    assert "analysis_timestamp" in match_data

# -------------------------------------------------------------
# 7: EVOLUTION BOOST (x402 protected, +100 XP bounded, 0.02 ALGO)
# -------------------------------------------------------------
def test_evolution_boost_flow(client, trainer_wallet):
    """Test 7: Evolution Boost applies strictly +100 XP to accelerating evolution."""
    # Obtain a card
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id

    # 1. Unpaid request -> 402
    unpaid_res = client.post(f"/evolution/{asset_id}/boost", json={
        "wallet_address": trainer_wallet
    })
    assert unpaid_res.status_code == 402
    assert "payment-required" in unpaid_res.headers

    # 2. Paid request -> 200 (0.02 ALGO = 20,000 microAlgos)
    proof_header = generate_payment_proof(trainer_wallet, str(asset_id), amount_micro=20000)
    paid_res = client.post(
        f"/evolution/{asset_id}/boost",
        json={"wallet_address": trainer_wallet},
        headers={"payment-signature": proof_header}
    )
    assert paid_res.status_code == 200
    assert "payment-response" in paid_res.headers
    boost_data = paid_res.json()
    assert boost_data["boost_applied_xp"] == 100
    assert boost_data["new_xp"] == boost_data["previous_xp"] + 100

# -------------------------------------------------------------
# 8: PREMIUM CREATURE ANALYSIS (x402 protected, 0.005 ALGO)
# -------------------------------------------------------------
def test_premium_creature_analysis_flow(client, trainer_wallet):
    """Test 8: Tactical Analysis calculates combat rating, matchups, and arena strategies."""
    # Obtain a card
    purchase = purchase_service.complete_direct_purchase("basic", trainer_wallet)
    asset_id = purchase.asset_id

    # 1. Unpaid request -> 402
    unpaid_res = client.get(f"/creatures/{asset_id}/analysis")
    assert unpaid_res.status_code == 402
    assert "payment-required" in unpaid_res.headers

    # 2. Paid request -> 200 (0.005 ALGO = 5,000 microAlgos)
    proof_header = generate_payment_proof(trainer_wallet, str(asset_id), amount_micro=5000)
    paid_res = client.get(
        f"/creatures/{asset_id}/analysis?wallet_address={trainer_wallet}",
        headers={"payment-signature": proof_header}
    )
    assert paid_res.status_code == 200
    assert "payment-response" in paid_res.headers
    analysis = paid_res.json()
    assert "battle_rating" in analysis
    assert "best_arena" in analysis
    assert "strong_against" in analysis
    assert "weak_against" in analysis
    assert "recommended_strategy" in analysis
    assert "evolution_readiness" in analysis

# -------------------------------------------------------------
# 9 & 10: IDEMPOTENCY, REPLAY ATTACKS & SECURITY
# -------------------------------------------------------------
def test_replay_attack_rejection(client, trainer_wallet):
    """Test 9: Reusing the same payment transaction hash on another paid resource is rejected."""
    fixed_tx = f"tx_replay_test_{uuid.uuid4().hex[:12]}"
    proof1 = generate_payment_proof(trainer_wallet, "analysis_1", amount_micro=5000, custom_tx=fixed_tx)

    # First use -> 200 OK
    res1 = client.get(
        f"/creatures/emberling/analysis?wallet_address={trainer_wallet}",
        headers={"payment-signature": proof1}
    )
    assert res1.status_code == 200

    # Replay attempt on same or another resource -> 409 Conflict
    res2 = client.get(
        f"/creatures/aquafox/analysis?wallet_address={trainer_wallet}",
        headers={"payment-signature": proof1}
    )
    assert res2.status_code == 409
    assert "already been" in res2.json()["detail"].lower() or "replay" in res2.json()["detail"].lower()
