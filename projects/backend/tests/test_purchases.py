"""
AlgoRacers — Pack Purchase Pipeline & NFT Delivery Test Suite
=============================================================
Tests:
  1. Invalid pack returns 400 Bad Request
  2. Invalid wallet address returns 400 Bad Request
  3. Direct purchase executes RewardEngine, mints NFT, and updates state
  4. Idempotency: Retrying with same idempotency_key returns identical purchase without re-rolling
  5. Purchase status endpoint returns sanitized tracking fields with zero secrets
  6. User purchase history endpoint lists past purchases
  7. Direct fast checkout via /purchases/direct works end-to-end
"""

import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import algosdk
from algosdk import account

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.models.purchase import PurchaseStatus

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def buyer_account():
    sk, addr = account.generate_account()
    return sk, addr

def test_invalid_pack_rejected(client, buyer_account):
    """Test 1: Invalid pack name returns 400 Bad Request."""
    _, addr = buyer_account
    res = client.post("/packs/galactic_hyper_pack/purchase", json={"wallet_address": addr})
    assert res.status_code == 400
    assert "invalid pack" in res.json()["detail"].lower()

def test_invalid_wallet_rejected(client):
    """Test 2: Malformed Algorand address returns 400 Bad Request."""
    res = client.post("/packs/basic/purchase", json={"wallet_address": "NOT_A_VALID_ALGORAND_ADDRESS_123"})
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"].lower()

def test_successful_direct_purchase_pipeline(client, buyer_account):
    """Test 3: Full purchase pipeline executes reward -> mint -> delivery."""
    _, addr = buyer_account
    
    res = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": f"idem_{uuid.uuid4().hex}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in [PurchaseStatus.DELIVERED.value, PurchaseStatus.WAITING_FOR_OPT_IN.value]
    assert data["payment_status"] == "SETTLED_ON_ALGORAND_TESTNET"
    assert data["reward_status"] == "GENERATED"
    assert data["driver_name"] is not None
    assert data["asset_id"] is not None
    assert data["reward_id"].startswith("rew_")

def test_idempotency_prevents_reroll(client, buyer_account):
    """Test 4: Retrying with same idempotency_key returns identical reward and asset."""
    _, addr = buyer_account
    idem_key = f"idem_{uuid.uuid4().hex}"

    # 1. First execution
    res1 = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": idem_key}
    )
    assert res1.status_code == 200
    d1 = res1.json()

    # 2. Duplicate retry with same idempotency_key
    res2 = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": idem_key}
    )
    assert res2.status_code == 200
    d2 = res2.json()

    # Must match 100% identically!
    assert d1["purchase_id"] == d2["purchase_id"]
    assert d1["reward_id"] == d2["reward_id"]
    assert d1["driver_id"] == d2["driver_id"]
    assert d1["asset_id"] == d2["asset_id"]

def test_get_purchase_status(client, buyer_account):
    """Test 5: GET /purchases/{id} returns clean status with no secret leakage."""
    _, addr = buyer_account
    res = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr}
    )
    purchase_id = res.json()["purchase_id"]

    res_get = client.get(f"/purchases/{purchase_id}")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["purchase_id"] == purchase_id
    assert "mnemonic" not in res_get.text.lower()
    assert "private_key" not in res_get.text.lower()

def test_get_wallet_purchases(client, buyer_account):
    """Test 6: GET /wallets/{addr}/purchases lists all user purchases."""
    _, addr = buyer_account
    client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr}
    )

    res = client.get(f"/wallets/{addr}/purchases")
    assert res.status_code == 200
    purchases = res.json()
    assert isinstance(purchases, list)
    assert len(purchases) >= 1
    assert purchases[0]["wallet_address"] == addr

def test_direct_purchase_endpoint(client, buyer_account):
    """Test 7: Direct checkout endpoint executes fast pack drop."""
    _, addr = buyer_account
    res = client.post(
        "/purchases/direct",
        json={"pack_id": "premium", "wallet_address": addr, "idempotency_key": f"idem_{uuid.uuid4().hex}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["pack_id"] == "premium"
    assert data["driver_name"] is not None
    assert data["asset_id"] is not None
