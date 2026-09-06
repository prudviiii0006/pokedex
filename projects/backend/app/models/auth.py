"""
AlgoRacers — Session 13: Wallet Authentication
Module: models/auth.py
=============================================
Pydantic schemas for cryptographic challenge generation, signature verification,
and authenticated session management.
"""

from typing import Optional
from pydantic import BaseModel, Field

class ChallengeRequest(BaseModel):
    wallet_address: str = Field(
        ...,
        examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"],
        description="Public 58-character Algorand wallet address requesting an authentication challenge"
    )

class ChallengeResponse(BaseModel):
    challenge_id: str = Field(..., examples=["chal_a1b2c3d4e5f6"])
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    nonce: str = Field(..., examples=["4f9a1c8b3e2d7a6f9b1c3e5a7d9b2c4e"])
    domain: str = Field(..., examples=["algoracers.app"])
    network: str = Field(..., examples=["algorand-testnet"])
    message: str = Field(
        ...,
        examples=["Sign in to AlgoRacers\nAddress: 3VZQZ4...\nNonce: 4f9a...\nDomain: algoracers.app\nNetwork: algorand-testnet\nExpires: 2026-08-30T16:00:00Z"]
    )
    issued_at: str
    expires_at: str

class VerifyRequest(BaseModel):
    challenge_id: str = Field(..., examples=["chal_a1b2c3d4e5f6"])
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    signature: str = Field(
        ...,
        examples=["dGhpcyBpcyBhIG1vY2sgYmFzZTY0IHNpZ25hdHVyZSBmb3IgZXhhbXBsZQ=="],
        description="Base64 or Hex encoded ed25519 signature over the exact challenge message UTF-8 bytes"
    )

class AuthResponse(BaseModel):
    authenticated: bool = Field(True)
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    session_id: str = Field(..., examples=["sess_9f8e7d6c5b4a3a2b1c"])
    expires_at: str
    message: str = Field("Wallet authenticated successfully.")

class SessionMeResponse(BaseModel):
    authenticated: bool = Field(True)
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    session_id: str = Field(..., examples=["sess_9f8e7d6c5b4a3a2b1c"])
    expires_at: str
    created_at: str
