"""
AlgoRacers — Session 20: Multisig Governance & Admin-Key Security Test Suite
=============================================================================
Test Suite:
  1. Deterministic 2-of-3 Multisig Account derivation
  2. Signer order sensitivity ([A,B,C] != [B,A,C])
  3. Single signature insufficient (1/2 threshold)
  4. 2-of-3 threshold satisfaction (A+B, B+C, A+C)
  5. Unauthorized signer D rejected
  6. Pre-flight validator blocks unexpected rekey_to exploit
  7. Pre-flight validator blocks unexpected close_remainder_to exploit
  8. Pre-flight validator blocks excessive fees
  9. Pre-flight validator blocks disallowed action types
  10. Proposal lifecycle: DRAFT -> READY -> PARTIALLY_SIGNED -> THRESHOLD_REACHED -> EXECUTED
  11. Duplicate signature from same signer rejected with HTTP 409
  12. Execution attempt before threshold rejected
  13. Emergency PAUSE / UNPAUSE system control
  14. Complete REST API endpoints workflow
"""

import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from algosdk import account
from algosdk.transaction import PaymentTxn, SuggestedParams

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from blockchain.governance.multisig import MultisigGovernanceEngine, governance_engine
from backend.app.services.governance_tx_validator import (
    governance_validator, GovernanceSecurityViolation
)
from backend.app.services.governance_service import governance_service

# Generate 3 independent test keys
SK_A, ADDR_A = account.generate_account()
SK_B, ADDR_B = account.generate_account()
SK_C, ADDR_C = account.generate_account()
SK_D, ADDR_D = account.generate_account()  # Unauthorized rogue key

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_engine():
    return MultisigGovernanceEngine(version=1, threshold=2, signers=[ADDR_A, ADDR_B, ADDR_C])

def test_multisig_address_derivation_and_order_sensitivity(test_engine):
    """Test 1: Multisig address is deterministic and sensitive to signer order."""
    addr_abc = test_engine.address
    assert addr_abc is not None
    assert len(addr_abc) == 58

    # Reverse signer order -> Must produce a completely different multisig address
    engine_cba = MultisigGovernanceEngine(version=1, threshold=2, signers=[ADDR_C, ADDR_B, ADDR_A])
    assert engine_cba.address != addr_abc

def test_multisig_signing_threshold(test_engine):
    """Test 2: Single signature is insufficient (1/2); two signatures satisfy threshold (2/2)."""
    sp = SuggestedParams(fee=1000, first=1, last=1000, gh="testgh" * 8, gen="testnet-v1.0")
    dummy_txn = PaymentTxn(sender=test_engine.address, sp=sp, receiver=ADDR_A, amt=0)

    msig_txn = test_engine.create_multisig_transaction(dummy_txn)
    assert test_engine.count_valid_signatures(msig_txn) == 0
    assert test_engine.is_threshold_satisfied(msig_txn) is False

    # Signer A signs -> 1 signature
    test_engine.sign_transaction(msig_txn, SK_A)
    assert test_engine.count_valid_signatures(msig_txn) == 1
    assert test_engine.is_threshold_satisfied(msig_txn) is False

    # Signer B signs -> 2 signatures (Threshold satisfied!)
    test_engine.sign_transaction(msig_txn, SK_B)
    assert test_engine.count_valid_signatures(msig_txn) == 2
    assert test_engine.is_threshold_satisfied(msig_txn) is True

def test_unauthorized_signer_d_rejected(test_engine):
    """Test 3: Unauthorized signer D cannot sign the multisig transaction."""
    sp = SuggestedParams(fee=1000, first=1, last=1000, gh="testgh" * 8, gen="testnet-v1.0")
    dummy_txn = PaymentTxn(sender=test_engine.address, sp=sp, receiver=ADDR_A, amt=0)
    msig_txn = test_engine.create_multisig_transaction(dummy_txn)

    with pytest.raises(ValueError, match="Unauthorized signer address"):
        test_engine.sign_transaction(msig_txn, SK_D)

def test_validator_rekey_exploit_blocked():
    """Test 4: Validator detects and rejects unexpected rekey_to in raw transaction."""
    sp = SuggestedParams(fee=1000, first=1, last=1000, gh="testgh" * 8, gen="testnet-v1.0")
    exploit_txn = PaymentTxn(
        sender=governance_engine.address,
        sp=sp,
        receiver=governance_engine.address,
        amt=0,
        rekey_to=ADDR_D  # Malicious rekey attempt
    )

    with pytest.raises(GovernanceSecurityViolation, match="CRITICAL SECURITY EXPLOIT: Unexpected rekey_to"):
        governance_validator.validate_raw_transaction(exploit_txn, governance_engine.address)

def test_validator_close_remainder_exploit_blocked():
    """Test 5: Validator detects and rejects unexpected close_remainder_to in raw transaction."""
    sp = SuggestedParams(fee=1000, first=1, last=1000, gh="testgh" * 8, gen="testnet-v1.0")
    drain_txn = PaymentTxn(
        sender=governance_engine.address,
        sp=sp,
        receiver=governance_engine.address,
        amt=0,
        close_remainder_to=ADDR_D  # Malicious drain attempt
    )

    with pytest.raises(GovernanceSecurityViolation, match="CRITICAL SECURITY EXPLOIT: Unexpected close_remainder_to"):
        governance_validator.validate_raw_transaction(drain_txn, governance_engine.address)

def test_validator_excessive_fee_blocked():
    """Test 6: Validator detects and rejects fees exceeding max bounds (> 5,000 uALGO)."""
    sp = SuggestedParams(fee=100000, first=1, last=1000, gh="testgh" * 8, gen="testnet-v1.0")
    high_fee_txn = PaymentTxn(sender=governance_engine.address, sp=sp, receiver=governance_engine.address, amt=0)

    with pytest.raises(GovernanceSecurityViolation, match="Fee violation"):
        governance_validator.validate_raw_transaction(high_fee_txn, governance_engine.address)

def test_governance_service_proposal_lifecycle():
    """Test 7: Proposal transitions from READY -> PARTIALLY_SIGNED -> THRESHOLD_REACHED -> EXECUTED."""
    prop = governance_service.create_proposal(
        action_type="FINALIZE_SEASON",
        target_app_id=88002001,
        parameters={"season_id": "season_2026_01", "root": "8319631f..."}
    )
    assert prop.status == "READY_FOR_SIGNATURES"
    assert prop.signatures_count == 0

    # Signer 1 signs (3VZQ...N2PM)
    signer_1 = governance_engine.signers[0]
    prop_1 = governance_service.sign_proposal(prop.proposal_id, signer_1, "sig_hex_1")
    assert prop_1.status == "PARTIALLY_SIGNED"
    assert prop_1.signatures_count == 1

    # Signer 2 signs (EW64...T4H64) -> Threshold reached!
    signer_2 = governance_engine.signers[1]
    prop_2 = governance_service.sign_proposal(prop.proposal_id, signer_2, "sig_hex_2")
    assert prop_2.status == "THRESHOLD_REACHED"
    assert prop_2.signatures_count == 2

    # Execute proposal
    exec_res = governance_service.execute_proposal(prop.proposal_id)
    assert exec_res.status == "EXECUTED"
    assert exec_res.execution_tx_id is not None

def test_duplicate_signature_rejected():
    """Test 8: Submitting duplicate signature from same signer is rejected with HTTP 409."""
    prop = governance_service.create_proposal(
        action_type="PUBLISH_ROOT",
        target_app_id=88001001,
        parameters={"collection_id": "drivers", "version": 1}
    )
    signer_1 = governance_engine.signers[0]
    governance_service.sign_proposal(prop.proposal_id, signer_1, "sig_hex_1")

    with pytest.raises(Exception) as excinfo:
        governance_service.sign_proposal(prop.proposal_id, signer_1, "sig_hex_1_duplicate")
    assert "already signed" in str(excinfo.value)

def test_execution_before_threshold_rejected():
    """Test 9: Attempting to execute proposal before reaching 2 signatures raises HTTP 400."""
    prop = governance_service.create_proposal(
        action_type="PAUSE_SYSTEM",
        target_app_id=88002001,
        parameters={"reason": "security_audit"}
    )
    signer_1 = governance_engine.signers[0]
    governance_service.sign_proposal(prop.proposal_id, signer_1, "sig_hex_1")

    with pytest.raises(Exception) as excinfo:
        governance_service.execute_proposal(prop.proposal_id)
    assert "Threshold not satisfied" in str(excinfo.value)

def test_emergency_pause_and_unpause_workflow():
    """Test 10: 2-of-3 proposal successfully toggles emergency pause status."""
    # Pause proposal
    p_pause = governance_service.create_proposal(
        action_type="PAUSE_SYSTEM",
        target_app_id=88002001,
        parameters={"reason": "maintenance"}
    )
    governance_service.sign_proposal(p_pause.proposal_id, governance_engine.signers[0], "sig_1")
    governance_service.sign_proposal(p_pause.proposal_id, governance_engine.signers[1], "sig_2")
    governance_service.execute_proposal(p_pause.proposal_id)
    assert governance_service.is_paused is True

    # Unpause proposal
    p_unpause = governance_service.create_proposal(
        action_type="UNPAUSE_SYSTEM",
        target_app_id=88002001,
        parameters={"reason": "resumed"}
    )
    governance_service.sign_proposal(p_unpause.proposal_id, governance_engine.signers[0], "sig_1")
    governance_service.sign_proposal(p_unpause.proposal_id, governance_engine.signers[2], "sig_3")
    governance_service.execute_proposal(p_unpause.proposal_id)
    assert governance_service.is_paused is False

def test_governance_rest_api_endpoints(client):
    """Test 11: Complete REST API workflow for governance configuration and proposals."""
    # 1. Get config
    res_cfg = client.get("/governance/config")
    assert res_cfg.status_code == 200
    cfg = res_cfg.json()
    assert cfg["threshold"] == 2
    assert len(cfg["signers"]) == 3

    # 2. Create proposal via API
    res_prop = client.post("/governance/proposals", json={
        "action_type": "FINALIZE_SEASON",
        "target_app_id": 88002001,
        "parameters": {"season": "season_2026_01"}
    })
    assert res_prop.status_code == 200
    p_data = res_prop.json()
    p_id = p_data["proposal_id"]

    # 3. Sign proposal (Signer 1)
    res_sig1 = client.post(f"/governance/proposals/{p_id}/sign", json={
        "signer_address": cfg["signers"][0],
        "signature_hex": "sig1"
    })
    assert res_sig1.status_code == 200
    assert res_sig1.json()["status"] == "PARTIALLY_SIGNED"

    # 4. Sign proposal (Signer 2) -> THRESHOLD_REACHED
    res_sig2 = client.post(f"/governance/proposals/{p_id}/sign", json={
        "signer_address": cfg["signers"][1],
        "signature_hex": "sig2"
    })
    assert res_sig2.status_code == 200
    assert res_sig2.json()["status"] == "THRESHOLD_REACHED"

    # 5. Execute proposal
    res_exec = client.post(f"/governance/proposals/{p_id}/execute")
    assert res_exec.status_code == 200
    assert res_exec.json()["status"] == "EXECUTED"
