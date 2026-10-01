"""
Pokédex — Algorand Fundamentals
Script: create_account.py
=============================================
Generates a fresh Algorand TestNet development account.
Derives:
  1. Private Key (32-byte Ed25519 seed)
  2. 25-word Mnemonic Passphrase (human-readable backup)
  3. Public Address (58-character Base32 encoded public key + checksum)

Saves the mnemonic safely to `backend/.env` for local development.
"""

import os
from pathlib import Path
from algosdk import account, mnemonic

def main():
    print("=" * 65)
    print("⚡  POKÉDEX — GENERATE TESTNET DEVELOPMENT ACCOUNT")
    print("=" * 65)

    # 1. Generate an Ed25519 private key & derived public address
    private_key, address = account.generate_account()

    # 2. Convert the 32-byte private key into a standard 25-word mnemonic passphrase
    passphrase = mnemonic.from_private_key(private_key)

    print("\n✅ New Algorand Account Successfully Generated!")
    print(f"📍 Public Address (Public Key):\n   {address}")
    
    print("\n" + "🔒 " * 20)
    print("SECURITY NOTICE (TESTNET DEVELOPMENT ONLY):")
    print("- The 25-word mnemonic is the master key to this account.")
    print("- Anyone with these 25 words controls all assets in this account.")
    print("- This account is strictly for TESTNET. NEVER send real MainNet ALGO here.")
    print("🔒 " * 20)

    # 3. Store in backend/.env for convenient, secure local development
    env_path = Path(__file__).resolve().parent.parent / ".env"
    
    env_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            env_lines = f.readlines()

    # Filter out existing SENDER keys if regenerating
    env_lines = [
        line for line in env_lines 
        if not line.startswith("TESTNET_SENDER_MNEMONIC=") 
        and not line.startswith("TESTNET_SENDER_ADDRESS=")
    ]

    # Ensure node endpoints exist in .env
    has_algod = any(line.startswith("ALGOD_ADDRESS=") for line in env_lines)
    if not has_algod:
        env_lines.append("ALGOD_ADDRESS=https://testnet-api.algonode.cloud\n")
        env_lines.append("ALGOD_TOKEN=\n")
        env_lines.append("INDEXER_ADDRESS=https://testnet-idx.algonode.cloud\n")
        env_lines.append("INDEXER_TOKEN=\n")

    env_lines.append(f'TESTNET_SENDER_ADDRESS="{address}"\n')
    env_lines.append(f'TESTNET_SENDER_MNEMONIC="{passphrase}"\n')

    with open(env_path, "w") as f:
        f.writelines(env_lines)

    print(f"\n💾 Account saved securely to: {env_path}")
    print("   (Note: `backend/.env` is excluded from git via `.gitignore`)")

    print("\n👉 NEXT STEP: Fund your account on TestNet using the dispenser:")
    print(f"   Address: {address}")
    print("   Faucet:  https://bank.testnet.algorand.network")
    print("   Alt:     https://dispenser.testnet.aws.algodev.network")
    print("=" * 65)

if __name__ == "__main__":
    main()
