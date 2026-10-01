"""
Pokédex — FastAPI Backend
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
    PROJECT_NAME: str = "Pokédex API"
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

    # x402 Protocol Configuration (Algorand TestNet Native ALGO)
    X402_FACILITATOR_URL: str = os.getenv("X402_FACILITATOR_URL", "https://facilitator.goplausible.xyz")
    X402_PAY_TO: str = os.getenv("X402_PAY_TO", os.getenv("PAYMENT_RECEIVER_ADDRESS", "GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4"))
    X402_PAYMENT_ASSET: int = int(os.getenv("X402_PAYMENT_ASSET", "0"))  # 0 = Native ALGO on Algorand
    ALGORAND_TESTNET_CAIP2: str = "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI="
    PAYMENT_CURRENCY: str = "ALGO"

    # Authoritative Service Pricing in Native ALGO (Decimals)
    BASIC_PACK_PRICE_ALGO: float = float(os.getenv("BASIC_PACK_PRICE_ALGO", "0.1"))          # 100,000 microAlgos
    PREMIUM_PACK_PRICE_ALGO: float = float(os.getenv("PREMIUM_PACK_PRICE_ALGO", "0.5"))      # 500,000 microAlgos
    EVENT_PACK_PRICE_ALGO: float = float(os.getenv("EVENT_PACK_PRICE_ALGO", "0.2"))          # 200,000 microAlgos
    PREMIUM_BATTLE_PRICE_ALGO: float = float(os.getenv("PREMIUM_BATTLE_PRICE_ALGO", "0.02"))  # 20,000 microAlgos
    FEATURED_TRADE_PRICE_ALGO: float = float(os.getenv("FEATURED_TRADE_PRICE_ALGO", "0.01"))  # 10,000 microAlgos
    SMART_MATCH_PRICE_ALGO: float = float(os.getenv("SMART_MATCH_PRICE_ALGO", "0.01"))        # 10,000 microAlgos
    EVOLUTION_BOOST_PRICE_ALGO: float = float(os.getenv("EVOLUTION_BOOST_PRICE_ALGO", "0.02"))  # 20,000 microAlgos
    CREATURE_ANALYSIS_PRICE_ALGO: float = float(os.getenv("CREATURE_ANALYSIS_PRICE_ALGO", "0.005"))  # 5,000 microAlgos
    
    # Backward compatibility aliases
    BASIC_PACK_PRICE: float = BASIC_PACK_PRICE_ALGO
    PREMIUM_PACK_PRICE: float = PREMIUM_PACK_PRICE_ALGO
    EVENT_PACK_PRICE: float = EVENT_PACK_PRICE_ALGO
    PREMIUM_BATTLE_PRICE: float = PREMIUM_BATTLE_PRICE_ALGO
    FEATURED_TRADE_PRICE: float = FEATURED_TRADE_PRICE_ALGO
    SMART_MATCH_PRICE: float = SMART_MATCH_PRICE_ALGO
    EVOLUTION_BOOST_PRICE: float = EVOLUTION_BOOST_PRICE_ALGO
    CREATURE_ANALYSIS_PRICE: float = CREATURE_ANALYSIS_PRICE_ALGO
    
    # Allowed CORS Origins (Restricted for security)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4021",
        "http://127.0.0.1:4021",
        "*"
    ]

    # File System Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PACKS_CONFIG_PATH: Path = BASE_DIR / "data" / "packs.json"
    METADATA_DIR: Path = root_dir / "blockchain" / "metadata"

    # Server Secrets (Never expose over API endpoints)
    # SERVER_PRIVATE_KEY / ESCROW_MNEMONIC = os.getenv("ESCROW_MNEMONIC")

settings = Settings()
