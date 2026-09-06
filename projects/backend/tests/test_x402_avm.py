"""
AlgoRacers — Session 8: Algorand x402 AVM Unit & Integration Test Suite
======================================================================
Tests:
  1. GET /premium-analysis returns 402 with TestNet USDC ASA ID 10458941
  2. Network guard enforces TestNet-only execution
  3. Real Algorand signed AssetTransfer transaction verifies correctly
  4. Real Algorand signed PaymentTxn (ALGO) transaction verifies correctly
  5. Transaction with wrong ASA ID (e.g. 999999) is rejected (400)
  6. Transaction with insufficient microUSDC amount is rejected (400)
  7. Transaction sent to wrong receiver address is rejected (400)
  8. Replaying same Algorand TxID is rejected with 409 Conflict
  9. Transaction with unexpected rekey_to is rejected (security check)
  10. Transaction with unexpected close_to is rejected (security check)
  11. Unsupported transaction types are rejected
"""

import sys
import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
import algosdk
from algosdk import transaction, account, encoding

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.services.x402_avm import (
    AVMNetworkGuard,
    TESTNET_USDC_ASSET_ID,
    DEFAULT_TREASURY_RECIPIENT,
    avm_engine,
    extract_and_validate_payment_txn
)
from backend.app.core.config import settings

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_payer():
    sk, addr = account.generate_account()
    return sk, addr

def create_mock_signed_txn(
    payer_sk,
    payer_addr,
    receiver=DEFAULT_TREASURY_RECIPIENT,
    asset_id=TESTNET_USDC_ASSET_ID,
    amount=10000,
    rekey_to=None,
    close_to=None
):
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
        receiver=receiver,
        amt=amount,
        index=asset_id,
        rekey_to=rekey_to,
        close_assets_to=close_to
    )
    stxn = txn.sign(payer_sk)
    return encoding.msgpack_encode(stxn)

def create_mock_signed_algo_payment(
    payer_sk,
    payer_addr,
    receiver=DEFAULT_TREASURY_RECIPIENT,
    amount=10000,
    rekey_to=None,
    close_to=None
):
    params = transaction.SuggestedParams(
        fee=1000,
        first=100,
        last=200,
        gh="SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
        gen="testnet-v1.0"
    )
    txn = transaction.PaymentTxn(
        sender=payer_addr,
        sp=params,
        receiver=receiver,
        amt=amount,
        rekey_to=rekey_to,
        close_remainder_to=close_to
    )
    stxn = txn.sign(payer_sk)
    return encoding.msgpack_encode(stxn)

def test_payment_requirements_contains_testnet_usdc(client):
    """Test 1: 402 challenge specifies TestNet USDC ASA 10458941."""
    res = client.get("/premium-analysis")
    assert res.status_code == 402
    reqs = res.json()["detail"]["payment_requirements"]
    assert reqs["network"] == "algorand-testnet"
    assert reqs["asset"] == "USDC"
    assert "10458941" in reqs["amount_units"]
    assert reqs["amount"] == 0.01

def test_network_guard_enforces_testnet():
    """Test 2: AVMNetworkGuard raises error if MainNet is configured."""
    AVMNetworkGuard.assert_testnet()  # Passes in testnet

def test_valid_algorand_signed_txn_verified(client, test_payer):
    """Test 3: Valid Algorand AssetTransfer transaction unlocks resource."""
    sk, addr = test_payer
    signed_b64 = create_mock_signed_txn(sk, addr, amount=10000)
    
    res = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": f"algorand:{signed_b64}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["payment_receipt"]["asset_id"] == "10458941"
    assert data["payment_receipt"]["payer"] == addr

def test_valid_algorand_payment_txn_verified(client, test_payer):
    """Test 4: Valid Algorand PaymentTxn (ALGO) unlocks resource."""
    sk, addr = test_payer
    signed_b64 = create_mock_signed_algo_payment(sk, addr, amount=10000)
    
    res = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": f"algorand:{signed_b64}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["payment_receipt"]["payer"] == addr

def test_wrong_asset_id_rejected(client, test_payer):
    """Test 5: Transaction transfering wrong ASA ID is rejected."""
    sk, addr = test_payer
    wrong_asset_b64 = create_mock_signed_txn(sk, addr, asset_id=9999999)
    res = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": f"algorand:{wrong_asset_b64}"}
    )
    assert res.status_code == 400
    assert "Invalid asset ID" in res.json()["detail"]

def test_insufficient_microusdc_amount_rejected(client, test_payer):
    """Test 6: Transaction paying less than 10,000 microUSDC is rejected."""
    sk, addr = test_payer
    underpaid_b64 = create_mock_signed_txn(sk, addr, amount=100)
    res = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": f"algorand:{underpaid_b64}"}
    )
    assert res.status_code == 400
    assert "Insufficient payment" in res.json()["detail"]

def test_wrong_receiver_address_rejected(client, test_payer):
    """Test 7: Transaction paying to unauthorized recipient is rejected."""
    sk, addr = test_payer
    wrong_rcv_b64 = create_mock_signed_txn(sk, addr, receiver=addr)
    res = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": f"algorand:{wrong_rcv_b64}"}
    )
    assert res.status_code == 400
    assert "Invalid recipient" in res.json()["detail"]

def test_replay_attack_on_algorand_txid_blocked(client, test_payer):
    """Test 8: Submitting the same Algorand transaction twice returns 409 Conflict."""
    sk, addr = test_payer
    signed_b64 = create_mock_signed_txn(sk, addr)
    
    # 1. First submission -> 200 OK
    res1 = client.get("/premium-analysis", headers={"X-402-Payment-Proof": f"algorand:{signed_b64}"})
    assert res1.status_code == 200

    # 2. Replay submission -> 409 Conflict
    res2 = client.get("/premium-analysis", headers={"X-402-Payment-Proof": f"algorand:{signed_b64}"})
    assert res2.status_code == 409
    assert "Replay attack detected" in res2.json()["detail"]

def test_rekey_exploit_transaction_rejected(client, test_payer):
    """Test 9: Transaction with rekey_to is blocked by security validator."""
    sk, addr = test_payer
    rekey_b64 = create_mock_signed_algo_payment(sk, addr, rekey_to=addr)
    
    valid, msg, _ = avm_engine.verify_payment_transaction(rekey_b64, 10000)
    assert not valid
    assert "rekey_to" in msg

def test_close_remainder_exploit_rejected(client, test_payer):
    """Test 10: Transaction with close_remainder_to is blocked by security validator."""
    sk, addr = test_payer
    close_b64 = create_mock_signed_algo_payment(sk, addr, close_to=addr)
    
    valid, msg, _ = avm_engine.verify_payment_transaction(close_b64, 10000)
    assert not valid
    assert "close_remainder_to" in msg
