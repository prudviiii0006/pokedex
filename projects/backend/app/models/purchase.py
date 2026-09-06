"""
AlgoRacers — Session 9: x402 Purchase Pipeline
Module: models/purchase.py
=============================================
Pydantic schemas and State Machine definitions for AlgoRacers pack purchases.
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
    price_usdc: float = Field(..., examples=[0.01])
    currency: str = Field("USDC")
    
    # State tracking
    status: PurchaseStatus = Field(..., examples=[PurchaseStatus.DELIVERED])
    payment_status: str = Field(..., examples=["SETTLED_ON_ALGORAND_TESTNET"])
    payment_tx_id: Optional[str] = Field(None, examples=["Q6VNAESJECE6IPQJ5FDGW73DSMXJMLYW4CG4C6XCTXE33QI7EWUQ"])
    
    # Reward tracking
    reward_status: str = Field(..., examples=["GENERATED"])
    reward_id: Optional[str] = Field(None, examples=["rew_e2d48ce6f7ed"])
    rarity: Optional[str] = Field(None, examples=["Rare"])
    driver_id: Optional[str] = Field(None, examples=["001"])
    driver_name: Optional[str] = Field(None, examples=["Max Verstappen"])
    
    # NFT tracking
    metadata_uri: Optional[str] = Field(None, examples=["ipfs://bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t/driver_001.json"])
    asset_id: Optional[int] = Field(None, examples=[742199042])
    delivery_tx_id: Optional[str] = Field(None, examples=["DLV_TX_987654321"])
    
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
