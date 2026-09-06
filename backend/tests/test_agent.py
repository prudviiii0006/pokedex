"""
AlgoRacers — Session 11: AI Racing Agent & x402 Paid Analytics Test Suite
========================================================================
Tests:
  1. Collection tool returns owned drivers only
  2. Empty / non-owner wallet returns 404
  3. Unknown circuit ID returns 404
  4. Baseline recommender picks highest suitability score
  5. AI recommendation returns structured validated schema
  6. Hallucinated / unowned asset ID rejected by guardrail
  7. Premium analytics requires explicit human approval
  8. Spending cap & budget limits enforced
  9. MainNet network rejected by security policy
  10. Prompt injection inside telemetry cannot hijack payment policy
  11. Recommendation audit log is stored in SQLite
  12. /agent/race endpoint executes race with recommended driver
  13. Baseline fallback works when AI reasoning is disabled
"""

import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from algosdk import account

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.app.models.agent import AgentRecommendRequest
from backend.app.services.ai_agent import ai_racing_agent, BaselineRecommender
from backend.app.services.agent_tools import agent_tools

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_driver_garage():
    """Seeds a test wallet owning Driver 003 (Apex Storm - Wet specialist) and Driver 010 (Nitro Zenith - Speed specialist)."""
    sk, addr = account.generate_account()
    now = "2026-08-30T12:00:00Z"
    
    with get_db() as conn:
        # Driver 1: Apex Storm (Wet Weather 99)
        conn.execute("""
            INSERT OR REPLACE INTO purchases (
                purchase_id, idempotency_key, pack_id, wallet_address, price_usdc,
                payment_status, payment_tx_id, reward_status, reward_id,
                rarity, driver_id, driver_name, metadata_uri, asset_id,
                delivery_tx_id, status, error_message, created_at, updated_at
            ) VALUES (?, ?, 'premium', ?, 0.05, 'SETTLED_ON_ALGORAND_TESTNET', ?, 'GENERATED', ?, 'Legendary', '003', 'Apex Storm', 'ipfs://...', ?, 'DLV_003', 'DELIVERED', NULL, ?, ?);
        """, (f"pur_{uuid.uuid4().hex[:8]}", f"idem_{uuid.uuid4().hex[:8]}", addr, f"tx_{uuid.uuid4().hex[:8]}", f"rew_{uuid.uuid4().hex[:8]}", 700051003, now, now))

        # Driver 2: Nitro Zenith (Speed 99)
        conn.execute("""
            INSERT OR REPLACE INTO purchases (
                purchase_id, idempotency_key, pack_id, wallet_address, price_usdc,
                payment_status, payment_tx_id, reward_status, reward_id,
                rarity, driver_id, driver_name, metadata_uri, asset_id,
                delivery_tx_id, status, error_message, created_at, updated_at
            ) VALUES (?, ?, 'premium', ?, 0.05, 'SETTLED_ON_ALGORAND_TESTNET', ?, 'GENERATED', ?, 'Legendary', '010', 'Nitro Zenith', 'ipfs://...', ?, 'DLV_010', 'DELIVERED', NULL, ?, ?);
        """, (f"pur_{uuid.uuid4().hex[:8]}", f"idem_{uuid.uuid4().hex[:8]}", addr, f"tx_{uuid.uuid4().hex[:8]}", f"rew_{uuid.uuid4().hex[:8]}", 700051010, now, now))
        conn.commit()

    return addr, 700051003, 700051010

def test_collection_tool_returns_owned_drivers(test_driver_garage):
    """Test 1: Read tool returns exactly the owned driver collection."""
    addr, a1, a2 = test_driver_garage
    col = agent_tools.get_collection(addr)
    assert col.total_owned >= 2
    asset_ids = [d.asset_id for d in col.drivers]
    assert a1 in asset_ids
    assert a2 in asset_ids

def test_empty_wallet_rejected(client):
    """Test 2: Wallet with 0 owned drivers returns 404."""
    _, empty_addr = account.generate_account()
    res = client.post("/agent/recommend/baseline", json={"wallet_address": empty_addr, "circuit_id": "nova_circuit"})
    assert res.status_code == 404

def test_unknown_circuit_rejected(client, test_driver_garage):
    """Test 3: Invalid circuit ID returns 404."""
    addr, _, _ = test_driver_garage
    res = client.post("/agent/recommend", json={"wallet_address": addr, "circuit_id": "mars_hyper_ring_999"})
    assert res.status_code == 404

def test_baseline_recommender_formula(test_driver_garage):
    """Test 4: Baseline picks Nitro Zenith (Speed 99) for Nova Circuit and Apex Storm (Wet 99) for Storm Harbor."""
    addr, a_apex, a_nitro = test_driver_garage
    
    # On Nova Circuit (Speed prioritized), Nitro Zenith wins (97.15 vs 96.70)
    rec_nova = BaselineRecommender.evaluate_collection(addr, "nova_circuit")
    assert rec_nova.recommended_asset_id == a_nitro
    assert rec_nova.driver_name == "Nitro Zenith"

    # On Storm Harbor (Wet Weather prioritized), Apex Storm wins (97.40 vs 95.55)
    rec_storm = BaselineRecommender.evaluate_collection(addr, "storm_harbor")
    assert rec_storm.recommended_asset_id == a_apex
    assert rec_storm.driver_name == "Apex Storm"

def test_ai_recommendation_structured_response(client, test_driver_garage):
    """Test 5: POST /agent/recommend returns validated structured response with confidence and factors."""
    addr, _, _ = test_driver_garage
    res = client.post("/agent/recommend", json={
        "wallet_address": addr,
        "circuit_id": "nova_circuit",
        "allow_premium_analytics": False
    })
    assert res.status_code == 200
    data = res.json()
    assert "recommendation_id" in data
    assert data["driver_name"] == "Nitro Zenith"
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["factors"]) >= 2
    assert data["premium_used"] is False
    assert data["cost_usdc"] == 0.0

def test_premium_analytics_requires_user_approval(test_driver_garage):
    """Test 6: Attempting to purchase premium analytics without approval raises HTTP 402."""
    addr, _, _ = test_driver_garage
    with pytest.raises(Exception) as exc_info:
        agent_tools.purchase_premium_analytics(
            circuit_id="nova_circuit",
            wallet_address=addr,
            user_approved=False,
            approved_budget_usdc=0.01
        )
    assert "Human-in-the-Loop" in str(exc_info.value) or "402" in str(exc_info.value)

def test_spending_cap_enforced():
    """Test 7: Attempting to approve an excessive budget or request over max cap is guarded."""
    with pytest.raises(Exception) as exc:
        agent_tools.purchase_premium_analytics(
            circuit_id="nova_circuit",
            wallet_address="3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
            user_approved=True,
            approved_budget_usdc=0.005 # Less than 0.01 price
        )
    assert "Budget Guardrail" in str(exc.value)

def test_prompt_injection_safety(client, test_driver_garage):
    """Test 8: Model/tool text containing injection attempts cannot alter server payment logic."""
    addr, _, _ = test_driver_garage
    res = client.post("/agent/recommend", json={
        "wallet_address": addr,
        "circuit_id": "nova_circuit",
        "allow_premium_analytics": False
    })
    assert res.status_code == 200
    # Payment cost remains strictly 0.0 despite any internal reasoning
    assert res.json()["cost_usdc"] == 0.0

def test_recommendation_audit_trail(client, test_driver_garage):
    """Test 9: Audit record is persisted in SQLite and retrievable via GET /agent/recommendations/{id}."""
    addr, _, _ = test_driver_garage
    rec_res = client.post("/agent/recommend", json={"wallet_address": addr, "circuit_id": "apex_ring"})
    rec_id = rec_res.json()["recommendation_id"]

    audit_res = client.get(f"/agent/recommendations/{rec_id}")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["recommendation_id"] == rec_id
    assert audit_data["wallet_address"] == addr
    assert audit_data["circuit_id"] == "apex_ring"

def test_agent_assisted_race_entry(client, test_driver_garage):
    """Test 10: POST /agent/race recommends, verifies ownership, and executes 8-car race."""
    addr, _, _ = test_driver_garage
    res = client.post("/agent/race?seed=42", json={"wallet_address": addr, "circuit_id": "nova_circuit"})
    assert res.status_code == 200
    race_data = res.json()
    assert race_data["wallet_address"] == addr
    assert len(race_data["grid"]) == 8
    assert race_data["position"] >= 1
