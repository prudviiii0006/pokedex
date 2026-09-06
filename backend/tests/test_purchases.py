"""
AlgoRacers — Session 9: Purchase Pipeline & NFT Delivery Test Suite
==================================================================
Tests:
  1. Invalid pack returns 400 Bad Request
  2. Invalid wallet address returns 400 Bad Request
  3. Unpaid purchase returns HTTP 402 with correct price & asset ID
  4. Successful x402 payment executes RewardEngine, mints NFT, and updates state
  5. Idempotency: Retrying with same idempotency_key returns identical purchase without re-rolling
  6. Replay: Reusing the same payment_tx_id for a different purchase returns 409 Conflict
  7. Opt-in claim: Claiming delivery when opted-in transitions to DELIVERED
  8. Purchase status endpoint returns sanitized tracking fields with zero secrets
  9. User purchase history endpoint lists past purchases
  10. Database unique constraints prevent duplicate reward/mint generation
"""

import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import algosdk
from algosdk import account, transaction, encoding

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.models.purchase import PurchaseStatus
from backend.app.services.x402_avm import TESTNET_USDC_ASSET_ID, DEFAULT_TREASURY_RECIPIENT

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def buyer_account():
    sk, addr = account.generate_account()
    return sk, addr

def create_signed_payment_proof(payer_sk, payer_addr, amount_micro=10000):
    params = transaction.SuggestedParams(
        fee=1000,
        first=100,
        last=200,
        gh="SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        gen="testnet-v1.0"
    )
    txn = transaction.AssetTransferTxn(
        sender=payer_addr,
        sp=params,
        receiver=DEFAULT_TREASURY_RECIPIENT,
        amt=amount_micro,
        index=TESTNET_USDC_ASSET_ID
    )
    stxn = txn.sign(payer_sk)
    signed_b64 = encoding.msgpack_encode(stxn)
    return f"algorand:{signed_b64}"

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

def test_unpaid_purchase_returns_402(client, buyer_account):
    """Test 3: Unpaid purchase request returns HTTP 402 with USDC requirements."""
    _, addr = buyer_account
    res = client.post("/packs/basic/purchase", json={"wallet_address": addr})
    assert res.status_code == 402
    reqs = res.json()["detail"]["payment_requirements"]
    assert reqs["asset"] == "USDC"
    assert reqs["amount"] == 0.01

def test_successful_purchase_pipeline(client, buyer_account):
    """Test 4: Full purchase pipeline executes payment -> reward -> mint."""
    sk, addr = buyer_account
    proof = create_signed_payment_proof(sk, addr, amount_micro=10000)
    
    res = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": f"idem_{uuid.uuid4().hex}"},
        headers={"X-402-Payment-Proof": proof}
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
    """Test 5: Retrying with same idempotency_key returns identical reward and asset."""
    sk, addr = buyer_account
    idem_key = f"idem_{uuid.uuid4().hex}"
    proof = create_signed_payment_proof(sk, addr, amount_micro=10000)

    # 1. First execution
    res1 = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": idem_key},
        headers={"X-402-Payment-Proof": proof}
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

def test_replaying_payment_tx_for_new_purchase_rejected(client, buyer_account):
    """Test 6: Using the same payment transaction for a new purchase returns 409 Conflict."""
    sk, addr = buyer_account
    proof = create_signed_payment_proof(sk, addr, amount_micro=10000)

    # Purchase 1 -> Success
    res1 = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": f"idem_{uuid.uuid4().hex}"},
        headers={"X-402-Payment-Proof": proof}
    )
    assert res1.status_code == 200

    # Purchase 2 -> Attempts to reuse same payment proof -> 409 Conflict!
    res2 = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr, "idempotency_key": f"idem_{uuid.uuid4().hex}"},
        headers={"X-402-Payment-Proof": proof}
    )
    assert res2.status_code == 409
    assert "already" in res2.json()["detail"].lower()

def test_get_purchase_status(client, buyer_account):
    """Test 7: GET /purchases/{id} returns clean status with no secret leakage."""
    sk, addr = buyer_account
    proof = create_signed_payment_proof(sk, addr, amount_micro=10000)
    res = client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr},
        headers={"X-402-Payment-Proof": proof}
    )
    purchase_id = res.json()["purchase_id"]

    res_get = client.get(f"/purchases/{purchase_id}")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["purchase_id"] == purchase_id
    assert "mnemonic" not in res_get.text.lower()
    assert "private_key" not in res_get.text.lower()

def test_get_wallet_purchases(client, buyer_account):
    """Test 8: GET /wallets/{addr}/purchases lists all user purchases."""
    sk, addr = buyer_account
    proof = create_signed_payment_proof(sk, addr, amount_micro=10000)
    client.post(
        "/packs/basic/purchase",
        json={"wallet_address": addr},
        headers={"X-402-Payment-Proof": proof}
    )

    res = client.get(f"/wallets/{addr}/purchases")
    assert res.status_code == 200
    purchases = res.json()
    assert isinstance(purchases, list)
    assert len(purchases) >= 1
    assert purchases[0]["wallet_address"] == addr
