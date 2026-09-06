"""
AlgoRacers — Session 20: Protocol-Native Algorand Multisig Engine
Module: blockchain/governance/multisig.py
================================================================
Provides protocol-level 2-of-3 multisig account generation,
ordered signer verification, partial signature aggregation,
and transaction threshold assembly using official Algorand SDK.
"""

from typing import List, Dict, Any, Optional, Tuple
from algosdk import account, mnemonic
from algosdk.transaction import (
    Multisig, MultisigTransaction, Transaction, PaymentTxn, ApplicationCallTxn,
    OnComplete, SuggestedParams
)

class MultisigGovernanceEngine:
    def __init__(self, version: int = 1, threshold: int = 2, signers: Optional[List[str]] = None):
        self.version = version
        self.threshold = threshold
        # Canonical ordered list of public Algorand addresses
        self.signers = signers or [
            "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",  # Signer A (Operations)
            "6ZIJOSUKH5HY6OK3GLLAP4AAV6GMOJDIECUI7VSQLRQFFWB2LGD6BI5MII",  # Signer B (Security Council)
            "MPZ7KZHZDGCQV6HSTOC2YQ2JMZMXBRVPUPSAQAVDZG2VUX62N2B2FI7TZA"   # Signer C (Recovery Operator)
        ]
        self.multisig = Multisig(
            version=self.version,
            threshold=self.threshold,
            addresses=self.signers
        )

    @property
    def address(self) -> str:
        """Returns the deterministic protocol-derived multisig account address."""
        return self.multisig.address()

    def verify_signer_ordering(self, addresses: List[str]) -> bool:
        """Verifies if a given address list matches the exact configured signer ordering."""
        return self.signers == addresses

    def create_multisig_transaction(self, txn: Transaction) -> MultisigTransaction:
        """Wraps a base unsigned Transaction into a native MultisigTransaction."""
        return MultisigTransaction(txn, self.multisig)

    def sign_transaction(
        self,
        msig_txn: MultisigTransaction,
        signer_private_key: str
    ) -> MultisigTransaction:
        """Applies a signature from an authorized signer to the multisig transaction."""
        signer_addr = account.address_from_private_key(signer_private_key)
        if signer_addr not in self.signers:
            raise ValueError(f"Unauthorized signer address: '{signer_addr}'. Not in multisig group.")

        msig_txn.sign(signer_private_key)
        return msig_txn

    def count_valid_signatures(self, msig_txn: MultisigTransaction) -> int:
        """Counts how many valid signatures have been collected on the multisig transaction."""
        sig_count = 0
        if hasattr(msig_txn, "multisig") and msig_txn.multisig:
            for s in msig_txn.multisig.subsigs:
                if s.signature is not None:
                    sig_count += 1
        return sig_count

    def is_threshold_satisfied(self, msig_txn: MultisigTransaction) -> bool:
        """Checks if the collected signature count meets or exceeds the required threshold."""
        return self.count_valid_signatures(msig_txn) >= self.threshold

# Default 2-of-3 Governance Council
governance_engine = MultisigGovernanceEngine()
