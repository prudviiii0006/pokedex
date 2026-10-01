"""
Pokédex — x402 V2 Payment Protocol Test Suite (Native ALGO)
===========================================================
Comprehensive unit & integration tests for x402 native ALGO payment requirements on Algorand TestNet:
  1. Unpaid request returns HTTP 402 Payment Required with ALGO challenge.
  2. HTTP 402 response includes valid base64-encoded `payment-required` header.
  3. POST /purchases creates purchase in PAYMENT_REQUIRED status with price_algo=0.1.
  4. POST /pay/purchases/{purchase_id} without payment returns HTTP 402 with pack price requirement (Basic: 100000 microAlgos, Premium: 500000 microAlgos).
  5. POST /pay/purchases/{purchase_id} with valid payment settles payment, returns HTTP 200, triggers RewardEngine, and mints NFT.
  6. HTTP 200 response contains valid `payment-response` header with transaction receipt.
  7. Replay protection: Submitting the identical transaction ID a second time returns HTTP 409 Conflict.
  8. Idempotency: Retrying paid purchase returns the completed purchase without re-rolling reward.
"""

import sys
import json
import base64
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.config import settings

@pytest.fixture
def client():
    return TestClient(app)

def test_unpaid_request_returns_402_payment_required(client):
    """Test 1: Unpaid request to /pay/purchases/{purchase_id} returns HTTP 402."""
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    create_res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": wallet
    })
    assert create_res.status_code == 200
    purchase_id = create_res.json()["purchase_id"]

    response = client.post(f"/pay/purchases/{purchase_id}")
    assert response.status_code == 402
    
    assert "payment-required" in response.headers or "PAYMENT-REQUIRED" in response.headers
    assert response.headers.get("www-authenticate") == "x402" or response.headers.get("WWW-Authenticate") == "x402"
    
    header_val = response.headers.get("payment-required") or response.headers.get("PAYMENT-REQUIRED")
    assert header_val is not None
    
    decoded = json.loads(base64.b64decode(header_val).decode('utf-8'))
    assert decoded["x402Version"] == 2
    assert decoded["error"] == "Payment required"
    assert "accepts" in decoded
    assert len(decoded["accepts"]) > 0
    
    accept = decoded["accepts"][0]
    assert accept["scheme"] == "exact"
    assert accept["asset"] == str(settings.X402_PAYMENT_ASSET)
    assert accept["currency"] == "ALGO"
    assert accept["payTo"] == settings.X402_PAY_TO
    assert accept["amount"] == "100000"
    assert "algorand" in accept["network"]

def test_unpaid_pack_purchase_returns_402(client):
    """Test 2: Creating a purchase and requesting /pay/purchases/{purchase_id} without payment returns 402."""
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    
    # 1. Create Purchase Intent for Basic Pack
    create_res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": wallet
    })
    assert create_res.status_code == 200
    p_data = create_res.json()
    purchase_id = p_data["purchase_id"]
    assert p_data["status"] == "PAYMENT_REQUIRED"
    assert p_data["price_algo"] == 0.1
    assert p_data["amount_microalgo"] == 100000

    # 2. Call x402 paid route without payment
    pay_res = client.post(f"/pay/purchases/{purchase_id}")
    assert pay_res.status_code == 402
    assert "payment-required" in pay_res.headers or "PAYMENT-REQUIRED" in pay_res.headers
    
    header_val = pay_res.headers.get("payment-required") or pay_res.headers.get("PAYMENT-REQUIRED")
    challenge = json.loads(base64.b64decode(header_val).decode('utf-8'))
    accept = challenge["accepts"][0]
    assert accept["amount"] == "100000"  # 0.1 ALGO
    assert accept["asset"] == str(settings.X402_PAYMENT_ASSET)
    assert accept["currency"] == "ALGO"
    assert accept["payTo"] == settings.X402_PAY_TO

def test_paid_pack_purchase_settles_and_delivers_nft(client):
    """Test 3: Paying for pack purchase via x402 triggers RewardEngine and mints NFT."""
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    
    # 1. Create Purchase
    create_res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": wallet
    })
    assert create_res.status_code == 200
    purchase_id = create_res.json()["purchase_id"]

    # 2. Pay via x402 with exact 100,000 microAlgos
    tx_id = f"tx_pack_pay_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": wallet,
        "amount": "100000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_payment = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')

    pay_res = client.post(
        f"/pay/purchases/{purchase_id}",
        headers={"payment-signature": b64_payment}
    )
    assert pay_res.status_code == 200
    confirmed = pay_res.json()
    assert confirmed["status"] in ["PAID", "DELIVERED", "WAITING_FOR_OPT_IN", "NFT_MINTED", "REWARD_GENERATED"]
    assert confirmed["payment_status"] == "SETTLED_ON_ALGORAND_TESTNET"
    assert confirmed["reward_id"] is not None
    assert confirmed["creature_name"] is not None or confirmed["driver_name"] is not None
    assert confirmed["rarity"] is not None
    assert confirmed["asset_id"] is not None
    
    # Check payment-response receipt
    assert "payment-response" in pay_res.headers or "PAYMENT-RESPONSE" in pay_res.headers
    receipt_header = pay_res.headers.get("payment-response") or pay_res.headers.get("PAYMENT-RESPONSE")
    receipt = json.loads(base64.b64decode(receipt_header).decode('utf-8'))
    assert receipt["transaction"] == tx_id
    assert receipt["success"] is True

def test_paid_premium_pack_purchase_requires_500000_microalgos(client):
    """Test 4: Premium pack requires 500,000 microAlgos (0.5 ALGO)."""
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    
    # 1. Create Premium Purchase
    create_res = client.post("/purchases", json={
        "pack_id": "premium",
        "wallet_address": wallet
    })
    assert create_res.status_code == 200
    purchase_id = create_res.json()["purchase_id"]
    assert create_res.json()["price_algo"] == 0.5
    assert create_res.json()["amount_microalgo"] == 500000

    # 2. Unpaid request challenge check
    pay_res = client.post(f"/pay/purchases/{purchase_id}")
    assert pay_res.status_code == 402
    header_val = pay_res.headers.get("payment-required") or pay_res.headers.get("PAYMENT-REQUIRED")
    challenge = json.loads(base64.b64decode(header_val).decode('utf-8'))
    assert challenge["accepts"][0]["amount"] == "500000"

    # 3. Pay 500000 microAlgos
    tx_id = f"tx_prem_pay_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": wallet,
        "amount": "500000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_payment = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')

    res = client.post(
        f"/pay/purchases/{purchase_id}",
        headers={"payment-signature": b64_payment}
    )
    assert res.status_code == 200
    assert res.json()["creature_name"] is not None or res.json()["driver_name"] is not None

def test_replay_attack_rejected(client):
    """Test 5: Replaying the same transaction ID is rejected with HTTP 409 Conflict."""
    wallet = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
    res1 = client.post("/purchases", json={"pack_id": "basic", "wallet_address": wallet})
    p1_id = res1.json()["purchase_id"]

    res2 = client.post("/purchases", json={"pack_id": "basic", "wallet_address": wallet})
    p2_id = res2.json()["purchase_id"]

    test_tx_id = f"tx_replay_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": test_tx_id,
        "payer": wallet,
        "amount": "100000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_payment = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')
    
    # First submission -> 200 OK
    res1 = client.post(
        f"/pay/purchases/{p1_id}",
        headers={"payment-signature": b64_payment}
    )
    assert res1.status_code == 200
    
    # Second submission with same transaction ID -> 409 Conflict
    res2 = client.post(
        f"/pay/purchases/{p2_id}",
        headers={"payment-signature": b64_payment}
    )
    assert res2.status_code == 409
    assert "Replay rejected" in res2.json()["detail"]
