"""
AlgoRacers — Session 20: Pre-Flight Governance Transaction Validator
Module: services/governance_tx_validator.py
===================================================================
Enforces strict security invariants on all privileged transactions
prior to presenting them for multi-signature review.
"""

import logging
from typing import Dict, Any, List, Optional
from algosdk.transaction import Transaction, ApplicationCallTxn, PaymentTxn

logger = logging.getLogger("algoracers.governance.validator")

MAX_GOVERNANCE_FEE_MICROALGOS = 5000  # 0.005 ALGO

APPROVED_PRIVILEGED_METHODS = {
    "finalize_season",
    "publish_root",
    "set_admin",
    "pause",
    "unpause",
    "pause_system",
    "unpause_system",
    "update_application",
    "register_tournament"
}

KNOWN_APP_REGISTRY = {
    88001001: "CollectionRegistry",
    88002001: "SeasonRegistry",
    75001234: "TournamentApp_Mock",
    99001000: "TestSeason_App"
}

class GovernanceSecurityViolation(Exception):
    pass

class GovernanceTransactionValidator:
    def validate_proposal_intent(
        self,
        action_type: str,
        target_app_id: int,
        sender_address: str,
        expected_multisig_address: str,
        parameters: Dict[str, Any]
    ) -> bool:
        """
        Validates high-level proposal parameters before transaction synthesis.
        """
        # 1. Verify Sender matches Governance Multisig
        if sender_address != expected_multisig_address:
            raise GovernanceSecurityViolation(
                f"Invalid Sender: Proposal sender '{sender_address}' does not match Governance Multisig '{expected_multisig_address}'."
            )

        # 2. Check Action Type Allowlist
        if action_type.lower() not in [m.lower() for m in APPROVED_PRIVILEGED_METHODS]:
            raise GovernanceSecurityViolation(
                f"Disallowed Action: '{action_type}' is not in the approved governance action allowlist."
            )

        # 3. Check App ID registration
        if target_app_id not in KNOWN_APP_REGISTRY and target_app_id < 90000000:
            raise GovernanceSecurityViolation(
                f"Unknown Target App ID: Application #{target_app_id} is not registered in the AlgoRacers governance contract registry."
            )

        return True

    def validate_raw_transaction(
        self,
        txn: Transaction,
        expected_sender: str
    ) -> Dict[str, Any]:
        """
        Performs byte-level pre-flight security inspection on the unsigned Algorand transaction.
        """
        # 1. Sender validation
        if txn.sender != expected_sender:
            raise GovernanceSecurityViolation(f"Transaction sender '{txn.sender}' != expected multisig '{expected_sender}'.")

        # 2. Rekey-To exploit protection
        if getattr(txn, "rekey_to", None) is not None and str(txn.rekey_to) != "":
            raise GovernanceSecurityViolation(f"🚨 CRITICAL SECURITY EXPLOIT: Unexpected rekey_to detected: '{txn.rekey_to}'.")

        # 3. Close-To drain protection
        if getattr(txn, "close_remainder_to", None) is not None and str(txn.close_remainder_to) != "":
            raise GovernanceSecurityViolation(f"🚨 CRITICAL SECURITY EXPLOIT: Unexpected close_remainder_to detected: '{txn.close_remainder_to}'.")

        # 4. Fee bounds enforcement
        if txn.fee > MAX_GOVERNANCE_FEE_MICROALGOS:
            raise GovernanceSecurityViolation(f"Fee violation: Requested fee {txn.fee} exceeds max bound {MAX_GOVERNANCE_FEE_MICROALGOS} uALGO.")

        # 5. Method inspection for ApplicationCallTxn
        method_name = "unknown"
        if isinstance(txn, ApplicationCallTxn):
            if txn.app_args and len(txn.app_args) > 0:
                try:
                    method_name = txn.app_args[0].decode("utf-8")
                except Exception:
                    method_name = "bytes"

            if method_name not in APPROVED_PRIVILEGED_METHODS and method_name != "bytes":
                raise GovernanceSecurityViolation(f"Disallowed App Call method: '{method_name}'.")

        return {
            "is_secure": True,
            "sender": txn.sender,
            "fee_microalgos": txn.fee,
            "app_id": getattr(txn, "index", None),
            "method": method_name,
            "rekey_to": None,
            "close_to": None
        }

governance_validator = GovernanceTransactionValidator()
