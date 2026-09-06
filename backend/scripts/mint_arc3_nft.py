"""
AlgoRacers — Session 3: NFT Metadata & ARC-3 Minting
Script: mint_arc3_nft.py
====================================================
Mints an ARC-3 compliant Driver NFT on Algorand TestNet:
  1. Reads `blockchain/metadata/driver_001.json`
  2. Computes the 32-byte SHA-256 `metadata_hash` of the JSON file
  3. Constructs `AssetConfigTxn` with:
     • URL: `ipfs://<CID>#arc3` (The `#arc3` fragment declares standard compliance)
     • Metadata Hash: 32-byte SHA-256 digest
     • Total: 1, Decimals: 0
  4. Confirms on TestNet and displays verification steps
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")

def get_algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(algod_token=ALGOD_TOKEN, algod_address=ALGOD_ADDRESS)

def compute_json_sha256(file_path: Path) -> bytes:
    """Computes the 32-byte SHA-256 digest of a file."""
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    return hashlib.sha256(file_bytes).digest()

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — MINT ARC-3 COMPLIANT DRIVER NFT")
    print("=" * 65)

    metadata_path = Path(__file__).resolve().parent.parent.parent / "blockchain" / "metadata" / "driver_001.json"
    if not metadata_path.exists():
        print(f"❌ Error: Metadata file not found at {metadata_path}")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # 1. Compute 32-byte SHA-256 Metadata Hash
    meta_hash = compute_json_sha256(metadata_path)
    meta_hash_hex = meta_hash.hex()

    print(f"\n[Step 1: Computed ARC-3 Metadata Hash]")
    print(f"   • File:              {metadata_path.name}")
    print(f"   • SHA-256 (Hex):     {meta_hash_hex}")
    print(f"   • Byte Length:       {len(meta_hash)} bytes (Matches Algorand 32-byte field)")

    # 2. Setup Algod Client & Creator Account
    client = get_algod_client()
    sender_mn = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    if not sender_mn:
        print("❌ Error: TESTNET_SENDER_MNEMONIC not found in backend/.env")
        return

    creator_pk = mnemonic.to_private_key(sender_mn)
    creator_addr = account.address_from_private_key(creator_pk)

    # 3. Check Balance
    try:
        balance = client.account_info(creator_addr).get("amount", 0)
    except Exception:
        balance = 0

    if balance < 200_000:
        print(f"⚠️  Insufficient balance in {creator_addr}. Fund at https://bank.testnet.algorand.network")
        return

    # 4. Construct ARC-3 AssetConfigTxn
    sp = client.suggested_params()

    # In ARC-3, the URL must end with `#arc3` or be an IPFS CID
    ipfs_cid = "bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t"
    arc3_url = f"ipfs://{ipfs_cid}/driver_001.json#arc3"

    driver_name = meta.get("name", "AlgoRacer #001")
    unit_name = "AR001"

    print("\n[Step 2: Constructing ARC-3 AssetConfigTxn]")
    print(f"   • Asset Name:        {driver_name}")
    print(f"   • Unit Name:         {unit_name}")
    print(f"   • Total Supply:      1 (1-of-1 NFT)")
    print(f"   • Decimals:          0 (Indivisible)")
    print(f"   • Metadata URL:      {arc3_url}")
    print(f"   • Metadata Hash:     Attached (32 bytes)")

    txn = transaction.AssetConfigTxn(
        sender=creator_addr,
        sp=sp,
        total=1,
        decimals=0,
        default_frozen=False,
        unit_name=unit_name,
        asset_name=driver_name,
        manager=creator_addr,
        reserve=creator_addr,
        freeze=None,
        clawback=None,
        url=arc3_url,
        metadata_hash=meta_hash
    )

    # 5. Sign and Broadcast
    print("\n[Step 3: Signing & Submitting to TestNet]")
    signed_txn = txn.sign(creator_pk)
    txid = client.send_transaction(signed_txn)
    print(f"   🚀 Submitted! TXID: {txid}")

    # 6. Await Confirmation
    print("\n[Step 4: Awaiting Round Finality...]")
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)
    asset_id = confirmed_txn.get("asset-index")
    confirmed_round = confirmed_txn.get("confirmed-round")

    print(f"\n🎉 ARC-3 DRIVER NFT MINTED ON TESTNET in Round #{confirmed_round}!")
    print(f"   📍 ASSET ID: {asset_id}")

    # 7. Query On-Chain Parameters to Confirm Hash Storage
    asset_info = client.asset_info(asset_id)
    params = asset_info.get("params", {})

    print("\n" + "-" * 65)
    print("📋 On-Chain ARC-3 Verification:")
    print(f"   • Asset ID:        {asset_id}")
    print(f"   • Creator:         {params.get('creator')}")
    print(f"   • URL:             {params.get('url')}")
    print(f"   • On-Chain Hash:   {params.get('metadata-hash')}")
    print("-" * 65)

    print("\n🔗 TestNet Explorer Verification:")
    print(f"👉 https://testnet.explorer.perawallet.app/asset/{asset_id}")
    print(f"👉 https://lora.algokit.io/testnet/asset/{asset_id}")
    print("=" * 65)

if __name__ == "__main__":
    main()
