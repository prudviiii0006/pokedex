"""
AlgoRacers — Session 7: x402 Protocol Test Suite
================================================
Tests:
  1. GET /premium-analysis without payment returns 402 Payment Required
  2. 402 challenge contains structured payment requirements & WWW-Authenticate header
  3. Insufficient payment amount is rejected
  4. Malformed payment proof JSON returns 400 Bad Request
  5. Valid mock payment proof returns 200 OK with premium telemetry
  6. Replaying the same nonce returns 409 Conflict
  7. Free endpoints (/health, /packs) remain 100% accessible without payment
  8. Error responses do not leak server secrets or internal paths
"""

import json
import uuid
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.services.payment_gate import payment_gate

@pytest.fixture
def client():
    return TestClient(app)

def test_unpaid_request_returns_402(client):
    """Test 1: Requesting protected resource without proof returns HTTP 402."""
    response = client.get("/premium-analysis")
    assert response.status_code == 402
    data = response.json()
    detail = data.get("detail", data)
    assert detail["error"] == "payment_required"
    assert "payment_requirements" in detail
    assert detail["payment_requirements"]["amount"] == 0.01
    assert detail["payment_requirements"]["asset"] == "USDC"
    assert "WWW-Authenticate" in response.headers

def test_insufficient_payment_amount_rejected(client):
    """Test 2: Authorizing less than required price returns 402."""
    underpaid_proof = {
        "client_address": "TEST_ADDR",
        "amount": 0.001,  # Required is 0.01
        "asset": "USDC",
        "nonce": f"nonce_{uuid.uuid4().hex}",
        "signature": "mock_sig"
    }
    response = client.get(
        "/premium-analysis", 
        headers={"X-402-Payment-Proof": json.dumps(underpaid_proof)}
    )
    assert response.status_code == 402
    assert "Insufficient payment" in response.json()["detail"]

def test_malformed_proof_json_returns_400(client):
    """Test 3: Malformed JSON in payment proof header returns 400."""
    response = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": "{malformed_json_not_valid_syntax"}
    )
    assert response.status_code == 400
    assert "Malformed x402 payment proof" in response.json()["detail"]

def test_valid_mock_proof_returns_200(client):
    """Test 4: Valid mock payment proof unlocks premium resource."""
    valid_proof = {
        "client_address": "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
        "amount": 0.01,
        "asset": "USDC",
        "nonce": f"nonce_{uuid.uuid4().hex}",
        "signature": "valid_mock_sig"
    }
    response = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": json.dumps(valid_proof)}
    )
    assert response.status_code == 200
    data = response.json()
    assert "Apex Grand Prix" in data["title"]
    assert len(data["driver_telemetry"]) > 0
    assert "payment_receipt" in data
    assert data["payment_receipt"]["verification_status"] == "VERIFIED_MOCK_PROOF"

def test_replay_attack_returns_409(client):
    """Test 5: Submitting the same payment proof nonce twice is rejected."""
    reused_nonce = f"nonce_{uuid.uuid4().hex}"
    proof = {
        "client_address": "TEST_ADDR",
        "amount": 0.50,
        "asset": "USDC",
        "nonce": reused_nonce,
        "signature": "sig"
    }
    # First submission -> 200 OK
    res1 = client.get("/premium-analysis", headers={"X-402-Payment-Proof": json.dumps(proof)})
    assert res1.status_code == 200

    # Second submission (Replay) -> 409 Conflict
    res2 = client.get("/premium-analysis", headers={"X-402-Payment-Proof": json.dumps(proof)})
    assert res2.status_code == 409
    assert "Replay attack detected" in res2.json()["detail"]

def test_free_endpoints_unaffected(client):
    """Test 6: Free public endpoints require zero payment headers."""
    assert client.get("/health").status_code == 200
    assert client.get("/packs").status_code == 200
    assert client.get("/packs/basic").status_code == 200

def test_no_server_secrets_leaked(client):
    """Test 7: Challenge and receipt envelopes do not leak server secrets."""
    res_402 = client.get("/premium-analysis")
    assert "mnemonic" not in res_402.text.lower()
    assert "private_key" not in res_402.text.lower()
