"""
AlgoRacers — Session 6: FastAPI Backend
Module: core/config.py
======================================
Application configuration and environment settings.
Differentiates between public configuration and server-only secrets.
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables
# Resolve workspace root (5 levels up from app/core/config.py)
root_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
backend_dir = Path(__file__).resolve().parent.parent.parent
env_path = root_dir / ".env"
backend_env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv(dotenv_path=backend_env_path)

class Settings:
    PROJECT_NAME: str = "AlgoRacers API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Public Configuration (Safe to share with client)
    ALGOD_SERVER: str = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
    ALGOD_ADDRESS: str = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
    ALGOD_TOKEN: str = os.getenv("ALGOD_TOKEN", "")
    INDEXER_SERVER: str = os.getenv("INDEXER_ADDRESS", "https://testnet-idx.algonode.cloud")
    INDEXER_TOKEN: str = os.getenv("INDEXER_TOKEN", "")
    MINTER_ADDRESS: str = os.getenv("MINTER_ADDRESS", "GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4")
    TREASURY_ADDRESS: str = os.getenv("TREASURY_ADDRESS", "GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4")
    PAYMENT_RECEIVER_ADDRESS: str = os.getenv("PAYMENT_RECEIVER_ADDRESS", TREASURY_ADDRESS)
    NETWORK: str = "testnet"

    # x402 Protocol Configuration (Algorand TestNet ONLY)
    X402_FACILITATOR_URL: str = os.getenv("X402_FACILITATOR_URL", "https://facilitator.goplausible.xyz")
    X402_PAY_TO: str = os.getenv("X402_PAY_TO", os.getenv("PAYMENT_RECEIVER_ADDRESS", "GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4"))
    X402_PAYMENT_ASSET: int = int(os.getenv("X402_PAYMENT_ASSET", "10458941"))
    ALGORAND_TESTNET_CAIP2: str = "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI="
    
    # Allowed CORS Origins (Restricted for security)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # File System Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PACKS_CONFIG_PATH: Path = BASE_DIR / "data" / "packs.json"
    METADATA_DIR: Path = root_dir / "blockchain" / "metadata"

    # Server Secrets (Never expose over API endpoints)
    # SERVER_PRIVATE_KEY / ESCROW_MNEMONIC = os.getenv("ESCROW_MNEMONIC")

settings = Settings()
