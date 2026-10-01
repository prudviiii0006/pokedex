"""
Pokédex Clean MVP Pipeline & Security Test Suite
==============================================================
Covers all requirements specified in Phase 22:
  1. wallet address validation
  2. pack exists
  3. server price authority
  4. unpaid -> 402
  5. valid payment -> 200
  6. wrong amount -> reject (402/400)
  7. wrong asset -> reject (400)
  8. duplicate payment (replay) -> reject (409)
  9. duplicate purchase -> same logical purchase (idempotency)
 10. payment confirmed -> reward generated
 11. one reward -> one NFT
 12. no mint before payment
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

VALID_BUYER = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
INVALID_BUYER = "NOT_A_VALID_ALGORAND_WALLET_ADDRESS"

@pytest.fixture
def client():
    return TestClient(app)

# 1. Wallet Address Validation
def test_wallet_address_validation(client):
    """Test 1: Malformed wallet address is rejected with 400 Bad Request."""
    res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": INVALID_BUYER
    })
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"].lower()

# 2. Pack Exists Validation
def test_pack_exists_validation(client):
    """Test 2: Non-existent pack is rejected with 400 Bad Request."""
    res = client.post("/purchases", json={
        "pack_id": "super_non_existent_pack_99",
        "wallet_address": VALID_BUYER
    })
    assert res.status_code == 400
    assert "invalid pack" in res.json()["detail"].lower()

# 3. Server Price Authority
def test_server_price_authority(client):
    """Test 3: Server dictates pack pricing (Basic = 0.1 ALGO / 100000 microAlgos, Premium = 0.5 ALGO / 500000 microAlgos)."""
    # Basic Pack
    res_basic = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": VALID_BUYER
    })
    assert res_basic.status_code == 200
    assert res_basic.json()["price_algo"] == 0.1
    
    # Premium Pack
    res_premium = client.post("/purchases", json={
        "pack_id": "premium",
        "wallet_address": VALID_BUYER
    })
    assert res_premium.status_code == 200
    assert res_premium.json()["price_algo"] == 0.5

# 4. Unpaid -> 402 Payment Required
def test_unpaid_request_returns_402(client):
    """Test 4: Requesting paid purchase resource without x402 payment returns HTTP 402 with valid challenge."""
    res_create = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": VALID_BUYER
    })
    purchase_id = res_create.json()["purchase_id"]

    # Call /pay/purchases/{purchase_id} with no payment header
    res_pay = client.post(f"/pay/purchases/{purchase_id}")
    assert res_pay.status_code == 402
    assert "payment-required" in res_pay.headers or "PAYMENT-REQUIRED" in res_pay.headers
    
    header_val = res_pay.headers.get("payment-required") or res_pay.headers.get("PAYMENT-REQUIRED")
    challenge = json.loads(base64.b64decode(header_val).decode('utf-8'))
    assert challenge["x402Version"] == 2
    assert challenge["accepts"][0]["amount"] == "100000"
    assert challenge["accepts"][0]["asset"] == str(settings.X402_PAYMENT_ASSET)
    assert challenge["accepts"][0]["payTo"] == settings.X402_PAY_TO

# 5. Valid Payment -> 200 OK
def test_valid_payment_returns_200(client):
    """Test 5: Submitting valid x402 payment returns HTTP 200 and receipt."""
    res_create = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": VALID_BUYER
    })
    purchase_id = res_create.json()["purchase_id"]

    tx_id = f"tx_valid_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": VALID_BUYER,
        "amount": "100000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_sig = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')

    res_pay = client.post(
        f"/pay/purchases/{purchase_id}",
        headers={"payment-signature": b64_sig}
    )
    assert res_pay.status_code == 200
    data = res_pay.json()
    assert data["paid"] is True
    assert data["payment_status"] == "SETTLED_ON_ALGORAND_TESTNET"
    assert data["reward_id"] is not None
    assert data["driver_name"] is not None
    assert data["asset_id"] is not None

# 6. Wrong Amount -> Reject
def test_wrong_amount_rejected(client):
    """Test 6: Underpaying returns HTTP 402 with insufficient amount error."""
    res_create = client.post("/purchases", json={
        "pack_id": "premium",  # Requires 500,000 microAlgos
        "wallet_address": VALID_BUYER
    })
    purchase_id = res_create.json()["purchase_id"]

    # Try to pay only 100,000 (Basic price) for Premium
    tx_id = f"tx_underpay_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": VALID_BUYER,
        "amount": "100000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_sig = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')

    res_pay = client.post(
        f"/pay/purchases/{purchase_id}",
        headers={"payment-signature": b64_sig}
    )
    assert res_pay.status_code == 402
    assert "exact payment required" in res_pay.json()["detail"].lower() or "insufficient" in res_pay.json()["detail"].lower()

# 7. Wrong Asset -> Reject
def test_wrong_asset_rejected(client):
    """Test 7: Paying with non-whitelisted ASA ID returns HTTP 400."""
    res_create = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": VALID_BUYER
    })
    purchase_id = res_create.json()["purchase_id"]

    # Pay with wrong ASA (e.g. 99999999)
    tx_id = f"tx_wrong_asset_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": VALID_BUYER,
        "amount": "100000",
        "asset": "99999999",
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_sig = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')

    res_pay = client.post(
        f"/pay/purchases/{purchase_id}",
        headers={"payment-signature": b64_sig}
    )
    assert res_pay.status_code == 400
    assert "asset" in res_pay.json()["detail"].lower()

# 8. Duplicate Payment -> Reject (Replay Attack Protection)
def test_duplicate_payment_rejected(client):
    """Test 8: Submitting the identical transaction ID a second time is rejected with HTTP 409 Conflict."""
    res1 = client.post("/purchases", json={"pack_id": "basic", "wallet_address": VALID_BUYER})
    p1_id = res1.json()["purchase_id"]

    res2 = client.post("/purchases", json={"pack_id": "basic", "wallet_address": VALID_BUYER})
    p2_id = res2.json()["purchase_id"]

    reused_tx = f"tx_replay_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": reused_tx,
        "payer": VALID_BUYER,
        "amount": "100000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_sig = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')

    # 1. First purchase succeeds
    pay1 = client.post(f"/pay/purchases/{p1_id}", headers={"payment-signature": b64_sig})
    assert pay1.status_code == 200

    # 2. Second purchase reusing same tx_id fails with 409 Conflict
    pay2 = client.post(f"/pay/purchases/{p2_id}", headers={"payment-signature": b64_sig})
    assert pay2.status_code == 409
    assert "Replay rejected" in pay2.json()["detail"]

# 9. Duplicate Purchase -> Same Logical Purchase (Idempotency)
def test_duplicate_purchase_idempotency(client):
    """Test 9: Passing the same idempotency_key returns the existing purchase."""
    idem_key = f"idem_{uuid.uuid4().hex}"
    
    res1 = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": VALID_BUYER,
        "idempotency_key": idem_key
    })
    assert res1.status_code == 200
    p1 = res1.json()

    # Duplicate call with same key
    res2 = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": VALID_BUYER,
        "idempotency_key": idem_key
    })
    assert res2.status_code == 200
    p2 = res2.json()

    assert p1["purchase_id"] == p2["purchase_id"]

# 10. Payment Confirmed -> Reward Generated
def test_payment_confirmed_generates_reward(client):
    """Test 10: Reward is only generated and attached after payment is verified."""
    res_create = client.post("/purchases", json={"pack_id": "basic", "wallet_address": VALID_BUYER})
    p_id = res_create.json()["purchase_id"]
    
    # Check status before payment: no reward yet
    check1 = client.get(f"/purchases/{p_id}").json()
    assert check1["reward_id"] is None
    assert check1["driver_name"] is None
    assert check1["paid"] is False

    # Pay
    tx_id = f"tx_rew_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": VALID_BUYER,
        "amount": "100000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_sig = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')
    res_pay = client.post(f"/pay/purchases/{p_id}", headers={"payment-signature": b64_sig})
    assert res_pay.status_code == 200

    # Check status after payment: reward generated
    check2 = client.get(f"/purchases/{p_id}").json()
    assert check2["reward_id"] is not None
    assert check2["driver_name"] is not None
    assert check2["paid"] is True

# 11. One Reward -> One NFT
def test_one_reward_one_nft(client):
    """Test 11: Each paid purchase generates exactly 1 reward and 1 NFT ASA."""
    res_create = client.post("/purchases", json={"pack_id": "premium", "wallet_address": VALID_BUYER})
    p_id = res_create.json()["purchase_id"]

    tx_id = f"tx_nft_{uuid.uuid4().hex[:16]}"
    payment_payload = {
        "x402Version": 2,
        "transaction": tx_id,
        "payer": VALID_BUYER,
        "amount": "500000",
        "asset": str(settings.X402_PAYMENT_ASSET),
        "network": settings.ALGORAND_TESTNET_CAIP2
    }
    b64_sig = base64.b64encode(json.dumps(payment_payload).encode('utf-8')).decode('utf-8')
    res_pay = client.post(f"/pay/purchases/{p_id}", headers={"payment-signature": b64_sig})
    assert res_pay.status_code == 200
    data = res_pay.json()
    
    assert data["asset_id"] is not None
    assert isinstance(data["asset_id"], int)
    assert data["asset_id"] > 0
    assert data["nft_mint_tx_id"] is not None

# 12. No Mint Before Payment
def test_no_mint_before_payment(client):
    """Test 12: An unpaid purchase has asset_id = None and mint_tx = None."""
    res_create = client.post("/purchases", json={"pack_id": "basic", "wallet_address": VALID_BUYER})
    p_id = res_create.json()["purchase_id"]
    
    status = client.get(f"/purchases/{p_id}").json()
    assert status["asset_id"] is None
    assert status["nft_mint_tx_id"] is None
    assert status["status"] == "PAYMENT_REQUIRED"
