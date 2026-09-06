"""
AlgoRacers — Session 2: Algorand Standard Assets (ASAs)
Script: create_asset.py
=======================================================
Creates a fungible Layer-1 token on Algorand TestNet:
  • Name: AlgoRacer Credits
  • Unit: ARC
  • Total Supply: 1,000 units
  • Decimals: 0
Demonstrates AssetConfigTxn, asset ID extraction, and on-chain inspection.
"""

import os
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

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — CREATE FUNGIBLE ASSET (ASA)")
    print("=" * 65)

    client = get_algod_client()

    # 1. Load Creator Account
    sender_mnemonic = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    if not sender_mnemonic:
        print("❌ Error: TESTNET_SENDER_MNEMONIC not found in backend/.env")
        return

    creator_pk = mnemonic.to_private_key(sender_mnemonic)
    creator_addr = account.address_from_private_key(creator_pk)

    print(f"\n[Step 1: Creator Account]")
    print(f"   Address: {creator_addr}")

    # Check creator balance
    try:
        acct_info = client.account_info(creator_addr)
        balance = acct_info.get("amount", 0)
    except Exception:
        balance = 0

    print(f"   Balance: {balance:,} microALGOs ({balance / 1_000_000:.6f} ALGO)")
    if balance < 200_000:
        print("\n⚠️  Insufficient balance to create asset and pay MBR + fee!")
        print(f"👉 Please fund address at: https://bank.testnet.algorand.network")
        return

    # 2. Fetch Suggested Parameters
    sp = client.suggested_params()

    # 3. Define Asset Parameters & Construct AssetConfigTxn
    total_supply = 1000
    decimals = 0
    unit_name = "ARC"
    asset_name = "AlgoRacer Credits"
    asset_url = "https://algoracers.io/assets/arc.json"

    print("\n[Step 2: Constructing AssetConfigTxn]")
    print(f"   • Asset Name:    {asset_name}")
    print(f"   • Unit Name:     {unit_name}")
    print(f"   • Total Supply:  {total_supply:,}")
    print(f"   • Decimals:      {decimals}")
    print(f"   • URL:           {asset_url}")
    print(f"   • Manager:       {creator_addr}")

    # Construct the creation transaction
    txn = transaction.AssetConfigTxn(
        sender=creator_addr,
        sp=sp,
        total=total_supply,
        decimals=decimals,
        default_frozen=False,
        unit_name=unit_name,
        asset_name=asset_name,
        manager=creator_addr,
        reserve=creator_addr,
        freeze=creator_addr,
        clawback=creator_addr,
        url=asset_url
    )

    # 4. Sign Transaction Locally
    print("\n[Step 3: Signing Transaction]")
    signed_txn = txn.sign(creator_pk)

    # 5. Broadcast to Algod
    print("\n[Step 4: Submitting to TestNet]")
    txid = client.send_transaction(signed_txn)
    print(f"   🚀 Submitted! TXID: {txid}")

    # 6. Wait for Confirmation
    print("\n[Step 5: Waiting for Block Confirmation]...")
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)

    # 7. Extract the newly minted Asset ID
    asset_id = confirmed_txn.get("asset-index")
    confirmed_round = confirmed_txn.get("confirmed-round")
    print(f"\n🎉 ASSET CREATED SUCCESSFULLY in Round #{confirmed_round}!")
    print(f"   📍 ASSET ID: {asset_id}")

    # 8. Query Asset Configuration directly from Algod
    print("\n[Step 6: Querying On-Chain Asset State from Algod]")
    asset_info = client.asset_info(asset_id)
    params = asset_info.get("params", {})

    print("-" * 65)
    print("📋 On-Chain Asset Configuration:")
    print(f"   • Asset ID:    {asset_id}")
    print(f"   • Name:        {params.get('name')}")
    print(f"   • Unit:        {params.get('unit-name')}")
    print(f"   • Total:       {params.get('total'):,}")
    print(f"   • Decimals:    {params.get('decimals')}")
    print(f"   • Creator:     {params.get('creator')}")
    print(f"   • Manager:     {params.get('manager')}")
    print(f"   • Freeze:      {params.get('freeze')}")
    print(f"   • Clawback:    {params.get('clawback')}")
    print(f"   • URL:         {params.get('url')}")
    print("-" * 65)

    print("\n🔗 TestNet Explorer Link:")
    print(f"👉 https://testnet.explorer.perawallet.app/asset/{asset_id}")
    print(f"👉 https://lora.algokit.io/testnet/asset/{asset_id}")
    print("=" * 65)

if __name__ == "__main__":
    main()
