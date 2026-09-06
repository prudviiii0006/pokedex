"""
AlgoRacers — Session 13: Wallet Authentication & Cryptographic Verification Tests
================================================================================
Test Cases:
  1. Valid wallet address receives structured challenge (200 OK)
  2. Malformed wallet address is rejected (400 Bad Request)
  3. Challenge contains domain, network, unique nonce, and short expiration
  4. Real ed25519 signature over challenge succeeds and provisions session (200 OK)
  5. Invalid/tampered signature is rejected (401 Unauthorized)
  6. Signature from wrong wallet address is rejected (403 Forbidden)
  7. Expired challenge is rejected (401 Unauthorized)
  8. Replaying used challenge is rejected (409 Conflict)
  9. GET /auth/me returns wallet with valid session, 401 without
  10. POST /auth/logout revokes session in SQLite
  11. Authenticated session prevents request body wallet identity spoofing
"""

import sys
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from algosdk import account, encoding
import nacl.signing

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_wallet():
    """Generates a fresh test Algorand keypair."""
    sk, addr = account.generate_account()
    return {"sk": sk, "address": addr}

def sign_challenge_message(private_key_b64: str, message: str) -> str:
    """Helper to generate standard ed25519 signature over challenge UTF-8 bytes."""
    raw_sk = encoding.decode_address(private_key_b64) if len(private_key_b64) == 58 else base64.b64decode(private_key_b64)
    # Algorand private key is 64 bytes (32 seed + 32 pubkey)
    signing_key = nacl.signing.SigningKey(raw_sk[:32])
    signed = signing_key.sign(message.encode("utf-8"))
    return base64.b64encode(signed.signature).decode("utf-8")

def test_challenge_generation_valid(client, test_wallet):
    """Test 1: Valid wallet address receives structured challenge."""
    response = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]})
    assert response.status_code == 200
    data = response.json()
    assert "challenge_id" in data
    assert data["wallet_address"] == test_wallet["address"]
    assert len(data["nonce"]) == 32  # 16 bytes hex = 32 chars
    assert data["domain"] == "algoracers.app"
    assert data["network"] == "algorand-testnet"
    assert "Sign in to AlgoRacers" in data["message"]
    assert "Expires At" in data["message"]

def test_challenge_generation_invalid_address(client):
    """Test 2: Malformed wallet address is rejected."""
    response = client.post("/auth/challenge", json={"wallet_address": "NOT_AN_ALGORAND_ADDRESS"})
    assert response.status_code == 400
    assert "invalid algorand" in response.json()["detail"].lower()

def test_valid_signature_verification_and_session(client, test_wallet):
    """Test 4: Real ed25519 signature succeeds and creates session."""
    # 1. Request challenge
    chal_res = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]})
    chal = chal_res.json()

    # 2. Sign challenge text locally
    sig = sign_challenge_message(test_wallet["sk"], chal["message"])

    # 3. Submit verification
    verify_res = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": test_wallet["address"],
        "signature": sig
    })

    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["authenticated"] is True
    assert data["wallet_address"] == test_wallet["address"]
    assert data["session_id"].startswith("sess_")
    assert "algoracers_session" in verify_res.cookies

def test_invalid_signature_rejected(client, test_wallet):
    """Test 5: Tampered signature is rejected."""
    chal_res = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]})
    chal = chal_res.json()

    fake_sig = base64.b64encode(b"0" * 64).decode("utf-8")

    verify_res = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": test_wallet["address"],
        "signature": fake_sig
    })

    assert verify_res.status_code == 401
    assert "invalid cryptographic signature" in verify_res.json()["detail"].lower()

def test_wrong_wallet_rejected(client, test_wallet):
    """Test 6: Signature from Wallet B for Challenge of Wallet A is rejected."""
    _, other_addr = account.generate_account()

    chal_res = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]})
    chal = chal_res.json()

    sig = sign_challenge_message(test_wallet["sk"], chal["message"])

    verify_res = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": other_addr,
        "signature": sig
    })

    assert verify_res.status_code == 403
    assert "does not match" in verify_res.json()["detail"].lower()

def test_expired_challenge_rejected(client, test_wallet):
    """Test 7: Expired challenge cannot be verified."""
    chal_res = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]})
    chal = chal_res.json()
    chal_id = chal["challenge_id"]

    # Manually expire in DB
    past_iso = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with get_db() as conn:
        conn.execute("UPDATE auth_challenges SET expires_at = ? WHERE challenge_id = ?;", (past_iso, chal_id))
        conn.commit()

    sig = sign_challenge_message(test_wallet["sk"], chal["message"])

    verify_res = client.post("/auth/verify", json={
        "challenge_id": chal_id,
        "wallet_address": test_wallet["address"],
        "signature": sig
    })

    assert verify_res.status_code == 401
    assert "expired" in verify_res.json()["detail"].lower()

def test_replayed_challenge_rejected(client, test_wallet):
    """Test 8: Replay attack with same challenge is blocked with 409 Conflict."""
    chal_res = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]})
    chal = chal_res.json()
    sig = sign_challenge_message(test_wallet["sk"], chal["message"])

    # First verify: succeeds
    res1 = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": test_wallet["address"],
        "signature": sig
    })
    assert res1.status_code == 200

    # Second verify (Replay): fails
    res2 = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": test_wallet["address"],
        "signature": sig
    })
    assert res2.status_code == 409
    assert "replay rejected" in res2.json()["detail"].lower()

def test_auth_me_and_logout(client, test_wallet):
    """Test 9 & 10: /auth/me returns identity; /auth/logout revokes it."""
    # 1. Unauthenticated /auth/me returns 401
    unauth_res = client.get("/auth/me")
    assert unauth_res.status_code == 401

    # 2. Authenticate
    chal = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]}).json()
    sig = sign_challenge_message(test_wallet["sk"], chal["message"])
    auth_res = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": test_wallet["address"],
        "signature": sig
    })
    session_id = auth_res.json()["session_id"]

    # 3. Authenticated /auth/me returns 200 with Bearer header
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {session_id}"})
    assert me_res.status_code == 200
    assert me_res.json()["wallet_address"] == test_wallet["address"]

    # 4. Logout
    logout_res = client.post("/auth/logout", headers={"Authorization": f"Bearer {session_id}"})
    assert logout_res.status_code == 200

    # 5. Subsequent /auth/me returns 401
    post_logout_res = client.get("/auth/me", headers={"Authorization": f"Bearer {session_id}"})
    assert post_logout_res.status_code == 401

def test_identity_spoofing_prevented_in_races(client, test_wallet):
    """Test 11: Caller cannot spoof another wallet address in body when session is active."""
    # Authenticate as test_wallet
    chal = client.post("/auth/challenge", json={"wallet_address": test_wallet["address"]}).json()
    sig = sign_challenge_message(test_wallet["sk"], chal["message"])
    auth_res = client.post("/auth/verify", json={
        "challenge_id": chal["challenge_id"],
        "wallet_address": test_wallet["address"],
        "signature": sig
    })
    session_id = auth_res.json()["session_id"]

    _, victim_wallet = account.generate_account()

    # Attempt to race with victim_wallet in body while authenticated as test_wallet
    # Backend uses test_wallet from session, checks test_wallet's ownership, fails because test_wallet owns 0 NFTs
    race_res = client.post("/races", json={
        "wallet_address": victim_wallet,
        "asset_id": 700051001,
        "circuit_id": "nova_circuit"
    }, headers={"Authorization": f"Bearer {session_id}"})

    assert race_res.status_code == 403
    # Confirms backend checked ownership for test_wallet (the authenticated identity), not victim_wallet!
    assert test_wallet["address"] in race_res.json()["detail"]
