"""
AlgoRacers — Session 2: Algorand Standard Assets (ASAs) & NFTs
Script: create_driver_nft.py
==============================================================
Mints the first 1-of-1 AlgoRacers Driver NFT on Algorand TestNet:
  • Name: AlgoRacer #001
  • Unit: AR001
  • Driver Identity: "Velocity One"
  • Rarity: Rare
  • Total Supply: 1 unit
  • Decimals: 0
Demonstrates how a 1-of-1 ASA acts as a pure layer-1 non-fungible collectible.
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
    print("🏎️  ALGORACERS — MINT 1-OF-1 DRIVER NFT (ASA)")
    print("=" * 65)

    client = get_algod_client()

    # 1. Load Creator Account
    sender_mn = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    if not sender_mn:
        print("❌ Error: TESTNET_SENDER_MNEMONIC not found in backend/.env")
        return

    creator_pk = mnemonic.to_private_key(sender_mn)
    creator_addr = account.address_from_private_key(creator_pk)

    print(f"\n[Step 1: Creator / Minting Authority]")
    print(f"   Address: {creator_addr}")

    # Check balance
    try:
        acct_info = client.account_info(creator_addr)
        balance = acct_info.get("amount", 0)
    except Exception:
        balance = 0

    if balance < 200_000:
        print("\n⚠️  Insufficient balance to mint NFT (needs min 0.2 ALGO for MBR + fee).")
        print(f"👉 Please fund: {creator_addr}")
        return

    # 2. Suggested Params
    sp = client.suggested_params()

    # 3. Define 1-of-1 NFT Parameters
    asset_name = "AlgoRacer #001"
    unit_name = "AR001"
    total_supply = 1    # EXACTLY 1 UNIT -> Non-fungible (Unique collectible)
    decimals = 0        # 0 DECIMALS -> Indivisible (Cannot be split into fractions)
    metadata_url = "https://algoracers.io/metadata/driver_001.json#arc3"

    print("\n[Step 2: Constructing 1-of-1 NFT AssetConfigTxn]")
    print(f"   • Asset Name:     {asset_name}")
    print(f"   • Unit Name:      {unit_name}")
    print(f"   • Total Supply:   {total_supply} (Pure 1-of-1)")
    print(f"   • Decimals:       {decimals} (Indivisible)")
    print(f"   • Driver:         Velocity One")
    print(f"   • Rarity:         Rare")
    print(f"   • Metadata URL:   {metadata_url}")
    print(f"   • Manager:        {creator_addr}")

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
        freeze=None,      # Leaving freeze and clawback None for true decentralized ownership!
        clawback=None,
        url=metadata_url
    )

    # 4. Sign Transaction
    signed_txn = txn.sign(creator_pk)

    # 5. Broadcast to TestNet
    txid = client.send_transaction(signed_txn)
    print(f"\n🚀 Minting transaction submitted! TXID: {txid}")

    # 6. Wait for Confirmation
    print("\n[*] Awaiting block finality on TestNet (~2.9s)...")
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)

    driver_nft_id = confirmed_txn.get("asset-index")
    confirmed_round = confirmed_txn.get("confirmed-round")

    print(f"\n🎉 DRIVER NFT MINTED ON-CHAIN in Round #{confirmed_round}!")
    print(f"   📍 DRIVER NFT ASSET ID: {driver_nft_id}")

    # 7. Query On-Chain Parameters
    nft_info = client.asset_info(driver_nft_id)
    params = nft_info.get("params", {})

    print("\n" + "-" * 65)
    print("🏆 On-Chain NFT Verification:")
    print(f"   • Asset ID:    {driver_nft_id}")
    print(f"   • Name:        {params.get('name')}")
    print(f"   • Unit:        {params.get('unit-name')}")
    print(f"   • Total:       {params.get('total')} (Unique)")
    print(f"   • Decimals:    {params.get('decimals')}")
    print(f"   • Creator:     {params.get('creator')}")
    print(f"   • URL:         {params.get('url')}")
    print("-" * 65)

    # Save to .env for easy testing
    with open(env_path, "a") as f:
        f.write(f'DRIVER_001_ASSET_ID="{driver_nft_id}"\n')

    print(f"\n💾 Saved DRIVER_001_ASSET_ID={driver_nft_id} to backend/.env")
    print("\n🔗 TestNet Explorer Verification:")
    print(f"👉 https://testnet.explorer.perawallet.app/asset/{driver_nft_id}")
    print(f"👉 https://lora.algokit.io/testnet/asset/{driver_nft_id}")
    print("=" * 65)

if __name__ == "__main__":
    main()
