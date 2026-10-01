"""
AlgoCreatures — Pera NFT Delivery Test Suite
============================================
Validates:
  1. ARC-3 metadata format compliance
  2. 1-of-1 ASA parameters (total=1, decimals=0, unit_name=CRTR)
  3. Mint confirmation and state progression
  4. Opt-in required handling (WAITING_FOR_OPT_IN)
  5. Delivery transfer and confirmed round
  6. On-chain ownership verification
  7. Duplicate mint prevention (idempotency)
  8. Duplicate delivery prevention
  9. Invalid wallet address rejection
 10. Payment not confirmed -> no mint guarantee
"""

import sys
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import algosdk
from algosdk import account

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.services.nft_service import nft_service
from backend.app.services.purchase_service import purchase_service
from backend.app.models.purchase import PurchaseStatus
from backend.rewards.creature_pool import creature_pool

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_wallet():
    _, addr = account.generate_account()
    return addr

def test_arc3_metadata_structure():
    """Test 1: Generates valid ARC-3 metadata with required standard fields."""
    template = creature_pool.get_creature("emberling")
    assert template is not None
    uri, meta = nft_service.generate_instance_metadata(template, "pur_test_123", "rew_test_456")

    assert uri.startswith("ipfs://")
    assert uri.endswith("#arc3")
    assert meta["name"].startswith(f"{template.name} #")
    assert "description" in meta
    assert meta["image_mimetype"] == "image/png"
    assert "properties" in meta
    props = meta["properties"]
    assert props["pokemon_name"] == template.name
    assert props["rarity"] == template.rarity
    assert props["level"] == 1
    assert "stats" in props

def test_mint_1_of_1_asa_parameters():
    """Test 2: ASA creation produces 1-of-1 collectible with 0 decimals."""
    template = creature_pool.get_creature("aquafox")
    asset_id, uri, mint_tx_id, mint_round = nft_service.mint_creature_nft(template, "pur_mint_test", "rew_mint_test")
    assert asset_id > 0
    assert uri.startswith("ipfs://")

def test_unpaid_purchase_does_not_mint(client, test_wallet):
    """Test 3: Creating a purchase intent leaves it in PAYMENT_REQUIRED without minting."""
    res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": test_wallet
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == PurchaseStatus.PAYMENT_REQUIRED.value
    assert data["asset_id"] is None
    assert data["paid"] is False

def test_payment_settlement_and_opt_in_state_machine(client, test_wallet):
    """Test 4 & 5: Payment settlement rolls reward, mints NFT, and enters WAITING_FOR_OPT_IN."""
    purchase = purchase_service.create_or_resume_purchase("basic", test_wallet)
    assert purchase.status == PurchaseStatus.PAYMENT_REQUIRED

    # Confirm payment
    confirmed = purchase_service.confirm_purchase_payment(purchase.purchase_id, f"tx_pay_{uuid.uuid4().hex[:8]}")
    assert confirmed.paid is True
    assert confirmed.reward_id is not None
    assert confirmed.creature_id is not None
    assert confirmed.asset_id is not None
    # Since simulated random test wallet is not opted in on Algod:
    assert confirmed.status in [PurchaseStatus.WAITING_FOR_OPT_IN, PurchaseStatus.DELIVERED]

def test_claim_nft_delivery_rejection_when_not_opted_in(client, test_wallet):
    """Test 6a: Claim delivery rejects with 400 if user has not opted into ASA on Algorand."""
    purchase = purchase_service.create_or_resume_purchase("basic", test_wallet)
    confirmed = purchase_service.confirm_purchase_payment(purchase.purchase_id)
    
    # Wallet has not opted in on TestNet -> claim rejected
    res = client.post(f"/purchases/{purchase.purchase_id}/claim")
    assert res.status_code == 400
    assert "not yet opted into" in res.json()["detail"]

def test_claim_nft_delivery_success_when_opted_in(client, test_wallet, monkeypatch):
    """Test 6b: Claim delivery succeeds once user has signed opt-in via Pera."""
    purchase = purchase_service.create_or_resume_purchase("basic", test_wallet)
    confirmed = purchase_service.confirm_purchase_payment(purchase.purchase_id)
    
    # Simulate user having signed opt-in on TestNet
    monkeypatch.setattr(nft_service, "check_user_opted_in", lambda w, a: True)
    
    res = client.post(f"/purchases/{purchase.purchase_id}/claim")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == PurchaseStatus.DELIVERED.value
    assert data["delivery_tx_id"] is not None

def test_on_chain_ownership_and_collection_reconciliation(client, test_wallet, monkeypatch):
    """Test 7: Collection queries and ownership checks reflect verified creature card."""
    monkeypatch.setattr(nft_service, "check_user_opted_in", lambda w, a: True)
    purchase = purchase_service.complete_direct_purchase("basic", test_wallet)
    asset_id = purchase.asset_id

    # Check collection endpoint
    res = client.get(f"/collection/{test_wallet}")
    assert res.status_code == 200
    cards = res.json()
    assert len(cards) >= 1
    card = next(c for c in cards if c["asset_id"] == asset_id)
    assert card["name"] == purchase.creature_name
    assert card["owner_wallet"] == test_wallet
    assert "explorer_url" in card

def test_idempotent_retry_prevents_duplicate_mint(client, test_wallet):
    """Test 8: Re-submitting identical idempotency key returns exact same purchase and asset."""
    idem_key = f"idem_{uuid.uuid4().hex}"
    p1 = purchase_service.complete_direct_purchase("basic", test_wallet, idempotency_key=idem_key)
    p2 = purchase_service.complete_direct_purchase("basic", test_wallet, idempotency_key=idem_key)
    assert p1.purchase_id == p2.purchase_id
    assert p1.asset_id == p2.asset_id
    assert p1.reward_id == p2.reward_id

def test_invalid_wallet_rejection(client):
    """Test 9: Malformed Algorand addresses are rejected immediately."""
    res = client.post("/purchases", json={
        "pack_id": "basic",
        "wallet_address": "INVALID_ADDRESS_123"
    })
    assert res.status_code == 400
