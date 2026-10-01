"""
AlgoCreatures — Purchase Models
Module: models/purchase.py
==============================
Pydantic schemas and State Machine definitions for AlgoCreatures pack purchases.
"""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class PurchaseStatus(str, Enum):
    CREATED = "CREATED"
    PAYMENT_REQUIRED = "PAYMENT_REQUIRED"
    PAID = "PAID"
    REWARD_GENERATED = "REWARD_GENERATED"
    NFT_MINTED = "NFT_MINTED"
    WAITING_FOR_OPT_IN = "WAITING_FOR_OPT_IN"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"

class PurchaseCreateRequest(BaseModel):
    wallet_address: str = Field(
        ..., 
        examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"],
        description="Public 58-character Algorand wallet address of the buyer"
    )
    idempotency_key: Optional[str] = Field(
        None, 
        examples=["idem_9a8b7c6d5e4f"],
        description="Client-generated unique UUID preventing duplicate purchase processing on network retries"
    )

class PurchaseResponse(BaseModel):
    purchase_id: str = Field(..., examples=["pur_f47ac10b58cc"])
    idempotency_key: Optional[str] = Field(None, examples=["idem_9a8b7c6d5e4f"])
    pack_id: str = Field(..., examples=["basic"])
    wallet_address: str = Field(..., examples=["3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"])
    price_algo: float = Field(..., examples=[0.1], description="Authoritative pack price in native ALGO")
    amount_microalgo: int = Field(..., examples=[100000], description="Authoritative price in microAlgos (1 ALGO = 1,000,000 microAlgos)")
    amount_algo_display: Optional[str] = Field(None, examples=["0.1 ALGO"])
    price_usdc: Optional[float] = Field(None, examples=[0.1], description="Backward compatibility alias for price_algo")
    currency: str = Field("ALGO", examples=["ALGO"])
    paid: bool = Field(False, examples=[True], description="Whether purchase payment has been verified and settled")
    x402_status: Optional[str] = Field("x402 Payment Successful", examples=["x402 Payment Successful"], description="Status confirmation of x402 protocol payment")
    
    # State tracking
    status: PurchaseStatus = Field(..., examples=[PurchaseStatus.DELIVERED])
    payment_status: str = Field(..., examples=["SETTLED_ON_ALGORAND_TESTNET"])
    payment_tx_id: Optional[str] = Field(None, examples=["Q6VNAESJECE6IPQJ5FDGW73DSMXJMLYW4CG4C6XCTXE33QI7EWUQ"])
    
    # Creature Reward tracking
    reward_status: str = Field(..., examples=["GENERATED"])
    reward_id: Optional[str] = Field(None, examples=["rew_e2d48ce6f7ed"])
    rarity: Optional[str] = Field(None, examples=["Rare"])
    creature_id: Optional[str] = Field(None, examples=["emberling"])
    creature_name: Optional[str] = Field(None, examples=["Emberling"])
    creature_type: Optional[str] = Field(None, examples=["Fire"])

    # Backward compatibility fields
    driver_id: Optional[str] = Field(None, examples=["emberling"])
    driver_name: Optional[str] = Field(None, examples=["Emberling"])
    
    # NFT tracking
    metadata_uri: Optional[str] = Field(None, examples=["ipfs://bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t/creature_001.json"])
    asset_id: Optional[int] = Field(None, examples=[742199042])
    nft_mint_tx_id: Optional[str] = Field(None, examples=["MINT_TX_123456789"])
    delivery_tx_id: Optional[str] = Field(None, examples=["DLV_TX_987654321"])
    mint_round: Optional[int] = Field(None, examples=[43128901])
    ownership_verified: Optional[bool] = Field(None, examples=[True])
    explorer_url: Optional[str] = Field(None, examples=["https://testnet.explorer.perawallet.app/asset/742199042/"])
    
    # Structured Traceability
    reward: Optional[Dict[str, Any]] = None
    nft: Optional[Dict[str, Any]] = None

    error_message: Optional[str] = None
    created_at: str
    updated_at: str
