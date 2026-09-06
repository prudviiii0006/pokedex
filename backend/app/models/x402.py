"""
AlgoRacers — Session 7: x402 Fundamentals
Module: models/x402.py
======================================
Pydantic schemas for the x402 Payment Required protocol (Learning / Mock Mode).
Follows the official x402 HTTP challenge-response schema:
  - 402 response specifies network, recipient, amount, asset, resource, and scheme
  - Client submits payment proof via `X-402-Payment-Proof` or `Authorization` header
"""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field

class PaymentRequirement(BaseModel):
    scheme: str = Field("exact_payment", description="Payment scheme type")
    network: str = Field("algorand-testnet", description="Settlement network")
    asset: str = Field("USDC", description="Currency / Asset symbol")
    amount: float = Field(..., description="Required amount in asset units")
    amount_units: str = Field("micro-units", description="Base integer units representation")
    recipient: str = Field(..., description="Target merchant / game treasury address")
    resource: str = Field(..., description="URI path of the protected resource")
    expiration_seconds: int = Field(300, description="Validity window for the payment challenge")

class PaymentRequiredResponse(BaseModel):
    error: str = Field("payment_required", description="x402 error identifier")
    message: str = Field("Access to this resource requires payment settlement.", description="Human-readable description")
    payment_requirements: PaymentRequirement
    protocol: str = Field("x402/1.0", description="Protocol version")
    mode: str = Field("mock_learning_mode", description="Indicates development / mock payment simulation")

class MockPaymentProof(BaseModel):
    client_address: str = Field(..., description="Payer public address")
    amount: float = Field(..., description="Amount authorized")
    asset: str = Field("USDC", description="Asset currency")
    nonce: str = Field(..., description="Unique proof nonce / transaction ID")
    signature: str = Field(..., description="Mock cryptographic signature")

class CircuitTelemetry(BaseModel):
    sector_1_delta: str
    sector_2_delta: str
    sector_3_delta: str
    tire_wear_optima: str
    recommended_pit_lap: int

class PremiumAnalysisResponse(BaseModel):
    title: str
    circuit: str
    track_conditions: str
    driver_telemetry: List[Dict[str, str]]
    tactical_ai_insights: str
    unlocked_at: str
    payment_receipt: Dict[str, str]
