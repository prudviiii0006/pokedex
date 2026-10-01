"""
Pokédex — Mandatory Pera Payment & Security Gate Test Suite (Native ALGO)
========================================================================
Strict invariant tests:
  1. Purchase creation initializes in UNPAID state with reward_status='NOT_STARTED', NULL reward_id, and NULL creature_id.
  2. Unpaid purchases reject complete endpoint with HTTP 402 Payment Required.
  3. Unpaid purchases reject claim endpoint with HTTP 402 Payment Required.
  4. Payment requirement amount matches server authoritative pack prices (Basic: 100000 microAlgos, Premium: 500000 microAlgos).
  5. Exact amount verification: Wrong amounts (underpayment/overpayment) are strictly rejected.
  6. x402 payment settles on Algorand TestNet in native ALGO and only THEN generates reward and mints NFT.
  7. Idempotency: Duplicate payment confirmations return the exact same Pokémon without re-rolling.
  8. Replay attack: Reusing the same payment_tx_id across different purchases is rejected with HTTP 409 Conflict.
"""

import sys
import json
import base64
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.models.purchase import PurchaseStatus

TEST_WALLET = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"

@pytest.fixture
def client():
    return TestClient(app)

def test_purchase_creation_has_no_reward_or_pokemon(client):
    """Test 1: Newly created purchase has NULL reward, NULL creature, and UNPAID status."""
    res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": TEST_WALLET,
        "idempotency_key": f"idem_{uuid.uuid4().hex}"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == PurchaseStatus.PAYMENT_REQUIRED.value
    assert data["payment_status"] == "UNPAID"
    assert data["reward_status"] == "NOT_STARTED"
    assert data["reward_id"] is None
    assert data["creature_id"] is None
    assert data["creature_name"] is None
    assert data["asset_id"] is None
    assert data["price_algo"] == 0.1
    assert data["amount_microalgo"] == 100000
    assert data["currency"] == "ALGO"

def test_direct_complete_without_payment_rejected(client):
    """Test 2: Direct call to /purchases/{id}/complete without payment is rejected with 402."""
    create_res = client.post("/purchases", json={
        "pack_id": "premium",
        "wallet_address": TEST_WALLET
    })
    assert create_res.status_code == 200
    purchase_id = create_res.json()["purchase_id"]

    complete_res = client.post(f"/purchases/{purchase_id}/complete")
    assert complete_res.status_code == 402
    assert "payment not confirmed" in complete_res.json()["detail"].lower()

def test_claim_without_payment_rejected(client):
    """Test 3: Calling claim on an unpaid purchase is rejected with 402."""
    create_res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": TEST_WALLET
    })
    purchase_id = create_res.json()["purchase_id"]

    claim_res = client.post(f"/purchases/{purchase_id}/claim")
    assert claim_res.status_code == 402
    assert "payment not confirmed" in claim_res.json()["detail"].lower()

def test_server_authoritative_pack_pricing(client):
    """Test 4: Backend enforces exact server pricing for basic (100000 microAlgos / 0.1 ALGO) and premium (500000 microAlgos / 0.5 ALGO)."""
    # Basic Pack
    res_basic = client.post("/purchases", json={"pack_id": "basic", "wallet_address": TEST_WALLET})
    pid_basic = res_basic.json()["purchase_id"]
    pay_basic = client.post(f"/pay/purchases/{pid_basic}")
    assert pay_basic.status_code == 402
    chal_basic = json.loads(base64.b64decode(pay_basic.headers["payment-required"]).decode("utf-8"))
    assert chal_basic["accepts"][0]["amount"] == "100000"
    assert chal_basic["accepts"][0]["currency"] == "ALGO"
    assert chal_basic["accepts"][0]["asset"] == "0"

    # Premium Pack
    res_prem = client.post("/purchases", json={"pack_id": "premium", "wallet_address": TEST_WALLET})
    pid_prem = res_prem.json()["purchase_id"]
    pay_prem = client.post(f"/pay/purchases/{pid_prem}")
    assert pay_prem.status_code == 402
    chal_prem = json.loads(base64.b64decode(pay_prem.headers["payment-required"]).decode("utf-8"))
    assert chal_prem["accepts"][0]["amount"] == "500000"
    assert chal_prem["accepts"][0]["currency"] == "ALGO"
    assert chal_prem["accepts"][0]["asset"] == "0"

def test_exact_amount_verification_basic_pack(client):
    """Test 5: Basic pack requires exact 100,000 microAlgos. Underpayment & overpayment rejected."""
    # Underpayment: 90,000 microAlgos (0.09 ALGO) -> Reject
    res_under = client.post("/purchases", json={"pack_id": "basic", "wallet_address": TEST_WALLET})
    pid_under = res_under.json()["purchase_id"]
    proof_under = base64.b64encode(json.dumps({
        "transaction": f"tx_under_{uuid.uuid4().hex[:12]}",
        "payer": TEST_WALLET,
        "amount": "90000",
        "asset": "0"
    }).encode("utf-8")).decode("utf-8")
    under_res = client.post(f"/pay/purchases/{pid_under}", headers={"PAYMENT-SIGNATURE": proof_under})
    assert under_res.status_code == 402
    assert "exact payment required" in under_res.json()["detail"].lower()

    # Overpayment: 110,000 microAlgos (0.11 ALGO) -> Reject
    res_over = client.post("/purchases", json={"pack_id": "basic", "wallet_address": TEST_WALLET})
    pid_over = res_over.json()["purchase_id"]
    proof_over = base64.b64encode(json.dumps({
        "transaction": f"tx_over_{uuid.uuid4().hex[:12]}",
        "payer": TEST_WALLET,
        "amount": "110000",
        "asset": "0"
    }).encode("utf-8")).decode("utf-8")
    over_res = client.post(f"/pay/purchases/{pid_over}", headers={"PAYMENT-SIGNATURE": proof_over})
    assert over_res.status_code == 402
    assert "exact payment required" in over_res.json()["detail"].lower()

def test_exact_amount_verification_premium_pack(client):
    """Test 6: Premium pack requires exact 500,000 microAlgos. Underpayment & overpayment rejected."""
    # Underpayment: 490,000 microAlgos (0.49 ALGO) -> Reject
    res_under = client.post("/purchases", json={"pack_id": "premium", "wallet_address": TEST_WALLET})
    pid_under = res_under.json()["purchase_id"]
    proof_under = base64.b64encode(json.dumps({
        "transaction": f"tx_prem_under_{uuid.uuid4().hex[:12]}",
        "payer": TEST_WALLET,
        "amount": "490000",
        "asset": "0"
    }).encode("utf-8")).decode("utf-8")
    under_res = client.post(f"/pay/purchases/{pid_under}", headers={"PAYMENT-SIGNATURE": proof_under})
    assert under_res.status_code == 402
    assert "exact payment required" in under_res.json()["detail"].lower()

    # Overpayment: 510,000 microAlgos (0.51 ALGO) -> Reject
    res_over = client.post("/purchases", json={"pack_id": "premium", "wallet_address": TEST_WALLET})
    pid_over = res_over.json()["purchase_id"]
    proof_over = base64.b64encode(json.dumps({
        "transaction": f"tx_prem_over_{uuid.uuid4().hex[:12]}",
        "payer": TEST_WALLET,
        "amount": "510000",
        "asset": "0"
    }).encode("utf-8")).decode("utf-8")
    over_res = client.post(f"/pay/purchases/{pid_over}", headers={"PAYMENT-SIGNATURE": proof_over})
    assert over_res.status_code == 402
    assert "exact payment required" in over_res.json()["detail"].lower()

def test_valid_x402_payment_settlement_grants_pokemon_and_nft(client):
    """Test 7: Valid signed x402 payment settles on TestNet and grants Pokémon + ARC-3 NFT."""
    create_res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": TEST_WALLET
    })
    purchase_id = create_res.json()["purchase_id"]

    tx_id = f"tx_pera_testnet_{uuid.uuid4().hex[:12]}"
    payment_proof = {
        "payment_tx_id": tx_id,
        "wallet": TEST_WALLET,
        "purchase_id": purchase_id,
        "network": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        "asset": "0",
        "amount": "100000"
    }
    b64_proof = base64.b64encode(json.dumps(payment_proof).encode("utf-8")).decode("utf-8")

    settle_res = client.post(
        f"/pay/purchases/{purchase_id}",
        headers={"PAYMENT-SIGNATURE": b64_proof}
    )
    assert settle_res.status_code == 200
    data = settle_res.json()
    assert data["payment_status"] == "SETTLED_ON_ALGORAND_TESTNET"
    assert data["payment_tx_id"] == tx_id
    assert data["reward_status"] == "GENERATED"
    assert data["reward_id"].startswith("rew_")
    assert data["creature_id"] is not None
    assert data["creature_name"] is not None
    assert data["asset_id"] is not None

def test_payment_idempotency_prevents_reroll(client):
    """Test 8: Submitting payment for an already-settled purchase returns the exact same reward."""
    create_res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": TEST_WALLET
    })
    purchase_id = create_res.json()["purchase_id"]

    tx_id = f"tx_pera_idem_{uuid.uuid4().hex[:12]}"
    proof = base64.b64encode(json.dumps({
        "payment_tx_id": tx_id,
        "wallet": TEST_WALLET,
        "purchase_id": purchase_id,
        "network": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        "asset": "0",
        "amount": "100000"
    }).encode("utf-8")).decode("utf-8")

    res1 = client.post(f"/pay/purchases/{purchase_id}", headers={"PAYMENT-SIGNATURE": proof})
    assert res1.status_code == 200
    d1 = res1.json()

    res2 = client.post(f"/pay/purchases/{purchase_id}", headers={"PAYMENT-SIGNATURE": proof})
    assert res2.status_code == 200
    d2 = res2.json()

    assert d1["reward_id"] == d2["reward_id"]
    assert d1["creature_id"] == d2["creature_id"]
    assert d1["asset_id"] == d2["asset_id"]

def test_replay_attack_rejected(client):
    """Test 9: Reusing an existing payment transaction on a new purchase returns 409 Conflict."""
    # 1. Purchase 1 settles
    res1 = client.post("/purchases", json={"pack_id": "basic", "wallet_address": TEST_WALLET})
    pid1 = res1.json()["purchase_id"]
    tx_id = f"tx_replay_{uuid.uuid4().hex[:12]}"
    proof1 = base64.b64encode(json.dumps({
        "payment_tx_id": tx_id,
        "wallet": TEST_WALLET,
        "purchase_id": pid1,
        "network": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        "asset": "0",
        "amount": "100000"
    }).encode("utf-8")).decode("utf-8")
    client.post(f"/pay/purchases/{pid1}", headers={"PAYMENT-SIGNATURE": proof1})

    # 2. Purchase 2 attempts to use same tx_id
    res2 = client.post("/purchases", json={"pack_id": "basic", "wallet_address": TEST_WALLET})
    pid2 = res2.json()["purchase_id"]
    proof2 = base64.b64encode(json.dumps({
        "payment_tx_id": tx_id,  # Same transaction!
        "wallet": TEST_WALLET,
        "purchase_id": pid2,
        "network": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        "asset": "0",
        "amount": "100000"
    }).encode("utf-8")).decode("utf-8")

    replay_res = client.post(f"/pay/purchases/{pid2}", headers={"PAYMENT-SIGNATURE": proof2})
    assert replay_res.status_code == 409
    assert "already been redeemed" in replay_res.json()["detail"].lower()
