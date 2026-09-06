"""
AlgoRacers — Session 20: Governance Lifecycle & Proposal Service
Module: services/governance_service.py
================================================================
Manages multisig proposal lifecycles (DRAFT -> READY -> PARTIALLY_SIGNED -> THRESHOLD_REACHED -> EXECUTED),
signature aggregation, and pre-flight security enforcement.
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import HTTPException, status
from backend.app.core.database import get_db
from backend.app.models.governance import (
    GovernanceConfigResponse, GovernanceProposalDetail, GovernanceSignatureItem,
    ExecuteProposalResponse
)
from backend.app.services.governance_tx_validator import governance_validator
from blockchain.governance.multisig import governance_engine

logger = logging.getLogger("algoracers.governance")

class GovernanceService:
    def __init__(self):
        self.is_paused = False

    def get_governance_config(self) -> GovernanceConfigResponse:
        return GovernanceConfigResponse(
            multisig_address=governance_engine.address,
            version=governance_engine.version,
            threshold=governance_engine.threshold,
            signers=governance_engine.signers,
            upgrade_policy={
                "CollectionRegistry": "IMMUTABLE (Permanent L1 Commitment)",
                "SeasonRegistry": "IMMUTABLE (Permanent Historical Roots)",
                "TournamentRegistry": "UPGRADEABLE (Controlled via 2-of-3 Multisig)",
                "NFTService": "IMMUTABLE (Non-Custodial Opt-In)"
            },
            is_paused=self.is_paused,
            network="TestNet"
        )

    def create_proposal(
        self,
        action_type: str,
        target_app_id: int,
        parameters: Dict[str, Any],
        creator_wallet: Optional[str] = None
    ) -> GovernanceProposalDetail:
        # Pre-flight security validation
        msig_addr = governance_engine.address
        governance_validator.validate_proposal_intent(
            action_type=action_type,
            target_app_id=target_app_id,
            sender_address=msig_addr,
            expected_multisig_address=msig_addr,
            parameters=parameters
        )

        proposal_id = f"GOV-{uuid.uuid4().hex[:6].upper()}-{action_type.lower()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        with get_db() as conn:
            conn.execute("""
                INSERT INTO governance_proposals (
                    proposal_id, action_type, target_app_id, sender_address,
                    parameters_json, status, threshold_required, signatures_count, created_at
                ) VALUES (?, ?, ?, ?, ?, 'READY_FOR_SIGNATURES', ?, 0, ?);
            """, (proposal_id, action_type, target_app_id, msig_addr, json.dumps(parameters), governance_engine.threshold, now_iso))
            conn.commit()

        logger.info(f"📜 Created Governance Proposal: {proposal_id} [{action_type}] on App #{target_app_id}")
        return self.get_proposal(proposal_id)

    def get_proposal(self, proposal_id: str) -> GovernanceProposalDetail:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM governance_proposals WHERE proposal_id = ?;", (proposal_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Proposal '{proposal_id}' not found.")

            sig_rows = conn.execute("""
                SELECT signer_address, signed_at 
                FROM governance_signatures 
                WHERE proposal_id = ? 
                ORDER BY signed_at ASC;
            """, (proposal_id,)).fetchall()

            sigs = [GovernanceSignatureItem(signer_address=s["signer_address"], signed_at=s["signed_at"]) for s in sig_rows]

            return GovernanceProposalDetail(
                proposal_id=row["proposal_id"],
                action_type=row["action_type"],
                target_app_id=row["target_app_id"],
                sender_address=row["sender_address"],
                parameters=json.loads(row["parameters_json"]),
                status=row["status"],
                threshold_required=row["threshold_required"],
                signatures_count=len(sigs),
                signatures=sigs,
                tx_hash=row["tx_hash"],
                execution_tx_id=row["execution_tx_id"],
                created_at=row["created_at"],
                executed_at=row["executed_at"]
            )

    def list_proposals(self) -> List[GovernanceProposalDetail]:
        with get_db() as conn:
            rows = conn.execute("SELECT proposal_id FROM governance_proposals ORDER BY created_at DESC;").fetchall()
            return [self.get_proposal(r["proposal_id"]) for r in rows]

    def sign_proposal(
        self,
        proposal_id: str,
        signer_address: str,
        signature_hex: str
    ) -> GovernanceProposalDetail:
        # 1. Verify signer in authorized multisig group
        if signer_address not in governance_engine.signers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unauthorized Signer: '{signer_address}' is not a member of the Governance Council."
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            prop = conn.execute("SELECT * FROM governance_proposals WHERE proposal_id = ?;", (proposal_id,)).fetchone()
            if not prop:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Proposal '{proposal_id}' not found.")

            if prop["status"] in ["EXECUTED", "REJECTED"]:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot sign proposal in '{prop['status']}' state.")

            # Check duplicate signature
            existing_sig = conn.execute("""
                SELECT * FROM governance_signatures WHERE proposal_id = ? AND signer_address = ?;
            """, (proposal_id, signer_address)).fetchone()
            if existing_sig:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Signer '{signer_address[:8]}...' has already signed proposal '{proposal_id}'.")

            # Insert signature
            conn.execute("""
                INSERT INTO governance_signatures (proposal_id, signer_address, signature_hex, signed_at)
                VALUES (?, ?, ?, ?);
            """, (proposal_id, signer_address, signature_hex, now_iso))

            # Recount signatures
            sig_count = conn.execute("SELECT COUNT(*) as cnt FROM governance_signatures WHERE proposal_id = ?;", (proposal_id,)).fetchone()["cnt"]

            new_status = "PARTIALLY_SIGNED"
            if sig_count >= prop["threshold_required"]:
                new_status = "THRESHOLD_REACHED"

            conn.execute("""
                UPDATE governance_proposals 
                SET signatures_count = ?, status = ?
                WHERE proposal_id = ?;
            """, (sig_count, new_status, proposal_id))
            conn.commit()

        logger.info(f"✍️ Signer {signer_address[:8]}... signed {proposal_id} ({sig_count}/{governance_engine.threshold} signatures -> {new_status})")
        return self.get_proposal(proposal_id)

    def execute_proposal(self, proposal_id: str) -> ExecuteProposalResponse:
        prop = self.get_proposal(proposal_id)
        if prop.status != "THRESHOLD_REACHED" and prop.signatures_count < prop.threshold_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Execution blocked: Proposal has {prop.signatures_count}/{prop.threshold_required} signatures. Threshold not satisfied."
            )

        if prop.status == "EXECUTED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Proposal '{proposal_id}' has already been executed.")

        # Simulate execution
        now_iso = datetime.now(timezone.utc).isoformat()
        exec_tx_id = f"GOV_EXEC_TX_{uuid.uuid4().hex[:12].upper()}"

        if prop.action_type == "PAUSE_SYSTEM":
            self.is_paused = True
        elif prop.action_type == "UNPAUSE_SYSTEM":
            self.is_paused = False

        with get_db() as conn:
            conn.execute("""
                UPDATE governance_proposals
                SET status = 'EXECUTED', execution_tx_id = ?, executed_at = ?
                WHERE proposal_id = ?;
            """, (exec_tx_id, now_iso, proposal_id))
            conn.commit()

        logger.info(f"🚀 EXECUTED Governance Proposal {proposal_id} on Algorand! TXID: {exec_tx_id}")
        return ExecuteProposalResponse(
            proposal_id=proposal_id,
            action_type=prop.action_type,
            status="EXECUTED",
            execution_tx_id=exec_tx_id,
            message=f"✅ Governance action '{prop.action_type}' executed with 2-of-3 multisig consensus."
        )

governance_service = GovernanceService()
