"""
Pokédex — Cryptographic Security & Session Verification
Module: core/security.py
=====================================================================
Cryptographic ed25519 signature verification against Algorand base32 addresses,
secure nonce generation, and FastAPI session authentication dependencies.
"""

import base64
import binascii
import secrets
from datetime import datetime, timezone
from typing import Optional
import logging

from fastapi import Request, Header, HTTPException, status, Depends
from algosdk import encoding
import nacl.signing
import nacl.exceptions

from backend.app.core.database import get_db

logger = logging.getLogger("pokedex.security")

def generate_secure_nonce(length_bytes: int = 16) -> str:
    """Generates a cryptographically secure random hexadecimal nonce."""
    return secrets.token_hex(length_bytes)

def verify_algorand_signature(wallet_address: str, message: str, signature_str: str) -> bool:
    """
    Cryptographically verifies an ed25519 signature against an Algorand public address.
    
    Mental Model:
      1. Decode 58-character Algorand base32 address into 32-byte raw public key.
      2. Decode base64 or hex signature into 64-byte raw ed25519 signature.
      3. Verify signature over message UTF-8 bytes using ed25519 VerifyKey.
    """
    try:
        # 1. Decode 32-byte public key from Algorand address
        public_key_bytes = encoding.decode_address(wallet_address)
        if len(public_key_bytes) != 32:
            logger.warning(f"Invalid public key length ({len(public_key_bytes)} bytes) for {wallet_address}")
            return False

        # 2. Decode signature (try base64 first, then hex)
        signature_bytes = None
        try:
            signature_bytes = base64.b64decode(signature_str)
        except Exception:
            try:
                signature_bytes = binascii.unhexlify(signature_str)
            except Exception:
                pass

        if not signature_bytes or len(signature_bytes) != 64:
            logger.warning(f"Invalid ed25519 signature format or length ({len(signature_bytes) if signature_bytes else 0} bytes)")
            return False

        # 3. Cryptographic ed25519 Verification via PyNaCl
        verify_key = nacl.signing.VerifyKey(public_key_bytes)
        message_bytes = message.encode("utf-8")
        
        # Verify will raise BadSignatureError if invalid
        verify_key.verify(message_bytes, signature_bytes)
        return True

    except nacl.exceptions.BadSignatureError:
        logger.warning(f"Cryptographic signature mismatch for wallet {wallet_address}")
        return False
    except Exception as e:
        logger.error(f"Unexpected signature verification error for {wallet_address}: {e}")
        return False

def get_session_from_request(request: Request, authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """Extracts and validates session token from Cookie or Bearer header."""
    session_id = None
    
    # 1. Try Authorization header
    if authorization and authorization.startswith("Bearer "):
        session_id = authorization.split("Bearer ", 1)[1].strip()
    
    # 2. Fallback to HttpOnly Cookie
    if not session_id:
        session_id = request.cookies.get("pokedex_session")

    if not session_id:
        return None

    # 3. Lookup in SQLite
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        row = conn.execute("""
            SELECT * FROM sessions 
            WHERE session_id = ? AND is_active = 1 AND expires_at > ?;
        """, (session_id, now_iso)).fetchone()

        if not row:
            return None

        # Update last_seen_at
        conn.execute("""
            UPDATE sessions SET last_seen_at = ? WHERE session_id = ?;
        """, (now_iso, session_id))
        conn.commit()

        return dict(row)

def get_current_wallet(request: Request, authorization: Optional[str] = Header(None)) -> str:
    """
    FastAPI Dependency: Enforces authenticated session and returns verified wallet address.
    Raises HTTP 401 Unauthorized if missing, expired, or revoked.
    """
    session = get_session_from_request(request, authorization)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Valid session not found or expired. Please sign in with Pera Wallet.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return session["wallet_address"]

def get_optional_wallet(request: Request, authorization: Optional[str] = Header(None)) -> Optional[str]:
    """FastAPI Dependency: Returns authenticated wallet address if present, otherwise None."""
    session = get_session_from_request(request, authorization)
    return session["wallet_address"] if session else None
