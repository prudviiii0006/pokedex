"""
AlgoRacers — Session 13: Authentication Service
Module: services/auth_service.py
===============================================
Handles challenge lifecycle, atomic replay defense, cryptographic verification,
and session management.
"""

from datetime import datetime, timedelta, timezone
import secrets
import logging
from typing import Optional, Dict, Any

from fastapi import HTTPException, status
from algosdk import encoding

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.security import generate_secure_nonce, verify_algorand_signature
from backend.app.models.auth import ChallengeResponse, AuthResponse

logger = logging.getLogger("algoracers.auth")

class AuthService:
    def __init__(self):
        self.challenge_ttl_seconds = 300  # 5 minutes
        self.session_ttl_hours = 24       # 24 hours
        self.default_domain = "algoracers.app"
        self.network = "algorand-testnet"

    def create_challenge(self, wallet_address: str) -> ChallengeResponse:
        """
        Creates a short-lived, domain-bound, cryptographically random authentication challenge.
        """
        # 1. Validate Algorand Address
        if not wallet_address or not encoding.is_valid_address(wallet_address):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Algorand wallet address format: '{wallet_address}'"
            )

        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=self.challenge_ttl_seconds)
        issued_at_iso = now.isoformat()
        expires_at_iso = expires.isoformat()

        challenge_id = f"chal_{secrets.token_hex(8)}"
        nonce = generate_secure_nonce(16)

        # 2. Construct Human-Readable, Structured Challenge Message
        message_text = (
            f"Sign in to AlgoRacers\n"
            f"Address: {wallet_address}\n"
            f"Nonce: {nonce}\n"
            f"Domain: {self.default_domain}\n"
            f"Network: {self.network}\n"
            f"Issued At: {issued_at_iso}\n"
            f"Expires At: {expires_at_iso}"
        )

        # 3. Store in SQLite
        with get_db() as conn:
            conn.execute("""
                INSERT INTO auth_challenges (
                    challenge_id, wallet_address, nonce, domain, network,
                    message_text, issued_at, expires_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING');
            """, (
                challenge_id, wallet_address, nonce, self.default_domain,
                self.network, message_text, issued_at_iso, expires_at_iso
            ))
            conn.commit()

        logger.info(f"🔑 Created auth challenge {challenge_id} for wallet {wallet_address[:8]}... (expires in 5m)")

        return ChallengeResponse(
            challenge_id=challenge_id,
            wallet_address=wallet_address,
            nonce=nonce,
            domain=self.default_domain,
            network=self.network,
            message=message_text,
            issued_at=issued_at_iso,
            expires_at=expires_at_iso
        )

    def verify_challenge(self, challenge_id: str, wallet_address: str, signature: str) -> AuthResponse:
        """
        Verifies ed25519 signature over original stored challenge, prevents replays atomically,
        and provisions a new user session.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        with get_db() as conn:
            # 1. Retrieve Original Stored Challenge (Atomic read)
            row = conn.execute("""
                SELECT * FROM auth_challenges WHERE challenge_id = ?;
            """, (challenge_id,)).fetchone()

            if not row:
                logger.warning(f"Auth verification failed: Unknown challenge ID '{challenge_id}'")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Authentication challenge not found."
                )

            challenge = dict(row)

            # 2. Check Wallet Match
            if challenge["wallet_address"] != wallet_address:
                logger.warning(f"Auth verification mismatch: Challenge for {challenge['wallet_address']}, submitted by {wallet_address}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Signer address does not match challenge target address."
                )

            # 3. Check Single-Use / Status
            if challenge["status"] != "PENDING":
                logger.warning(f"Replay attack blocked: Challenge {challenge_id} already in status '{challenge['status']}'")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Challenge has already been {challenge['status'].lower()}. Replay rejected."
                )

            # 4. Check Expiration
            if now_iso > challenge["expires_at"]:
                conn.execute("""
                    UPDATE auth_challenges SET status = 'EXPIRED' WHERE challenge_id = ?;
                """, (challenge_id,))
                conn.commit()
                logger.warning(f"Auth verification failed: Challenge {challenge_id} expired at {challenge['expires_at']}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication challenge has expired. Please request a new challenge."
                )

            # 5. Cryptographic ed25519 Verification
            is_valid = verify_algorand_signature(
                wallet_address=wallet_address,
                message=challenge["message_text"],
                signature_str=signature
            )

            if not is_valid:
                logger.warning(f"Invalid signature submitted for challenge {challenge_id} / wallet {wallet_address[:8]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid cryptographic signature. Private key ownership verification failed."
                )

            # 6. Atomically Mark Challenge as USED (Replay Prevention)
            conn.execute("""
                UPDATE auth_challenges 
                SET status = 'USED', used_at = ? 
                WHERE challenge_id = ? AND status = 'PENDING';
            """, (now_iso, challenge_id))

            # 7. Provision High-Entropy Authenticated Session
            session_id = f"sess_{secrets.token_hex(24)}"
            session_expires = now + timedelta(hours=self.session_ttl_hours)
            session_expires_iso = session_expires.isoformat()

            conn.execute("""
                INSERT INTO sessions (
                    session_id, wallet_address, created_at, expires_at, last_seen_at, is_active
                ) VALUES (?, ?, ?, ?, ?, 1);
            """, (
                session_id, wallet_address, now_iso, session_expires_iso, now_iso
            ))
            conn.commit()

        logger.info(f"✅ Successfully authenticated wallet {wallet_address[:8]}... (Session: {session_id[:12]}...)")

        return AuthResponse(
            authenticated=True,
            wallet_address=wallet_address,
            session_id=session_id,
            expires_at=session_expires_iso,
            message="Cryptographic ownership proven. Authenticated session created."
        )

    def logout(self, session_id: str) -> bool:
        """Revokes an active session."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE sessions 
                SET is_active = 0, revoked_at = ? 
                WHERE session_id = ?;
            """, (now_iso, session_id))
            conn.commit()
        logger.info(f"🔒 Revoked session {session_id[:12]}...")
        return True

auth_service = AuthService()
