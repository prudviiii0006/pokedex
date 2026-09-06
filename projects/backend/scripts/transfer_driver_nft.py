"""
AlgoRacers — Session 2: Algorand Standard Assets (ASAs) & NFTs
Script: transfer_driver_nft.py
==============================================================
Transfers the 1-of-1 Driver NFT from the creator/minter to an opted-in player wallet.
Verifies:
  1. Receiver has completed the opt-in transaction for the Driver NFT
  2. Exactly 1 unit is transferred via AssetTransferTxn
  3. Creator balance becomes 0; Receiver balance becomes 1
"""

import sys
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
    print("🏎️  ALGORACERS — TRANSFER 1-OF-1 DRIVER NFT")
    print("=" * 65)

    client = get_algod_client()

    # 1. Determine Driver NFT Asset ID
    if len(sys.argv) > 1:
        asset_id = int(sys.argv[1])
    else:
        env_nft_id = os.getenv("DRIVER_001_ASSET_ID", "").strip()
        if not env_nft_id:
            print("❌ Error: No Driver NFT Asset ID specified.")
            print("Usage: python transfer_driver_nft.py <NFT_ASSET_ID> [RECEIVER_ADDRESS]")
            return
        asset_id = int(env_nft_id)

    # 2. Load Creator Account
    sender_mn = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    if not sender_mn:
        print("❌ Error: TESTNET_SENDER_MNEMONIC not found in backend/.env")
        return

    creator_pk = mnemonic.to_private_key(sender_mn)
    creator_addr = account.address_from_private_key(creator_pk)

    # 3. Determine Receiver Address
    if len(sys.argv) > 2:
        receiver_addr = sys.argv[2].strip()
    else:
        receiver_addr = os.getenv("TESTNET_RECEIVER_ADDRESS", "").strip()

    if not receiver_addr:
        print("❌ Error: No receiver address specified.")
        print("Please provide a receiver address or run `asset_opt_in.py` first.")
        return

    print(f"\n[Transfer Specification]")
    print(f"   • Driver NFT ID:   {asset_id}")
    print(f"   • Current Owner:   {creator_addr} (Creator)")
    print(f"   • New Owner Target: {receiver_addr} (Player)")

    # 4. Check Receiver Opt-in
    try:
        recv_info = client.account_info(receiver_addr)
        assets = recv_info.get("assets", [])
        is_opted = any(a.get("asset-id") == asset_id for a in assets)
        if not is_opted:
            print(f"\n❌ Receiver has NOT opted into Driver NFT #{asset_id}!")
            print(f"👉 Run opt-in first: python asset_opt_in.py {asset_id}")
            return
    except Exception as e:
        print(f"❌ Error checking receiver account: {e}")
        return

    # 5. Construct AssetTransferTxn for exactly 1 unit
    sp = client.suggested_params()

    print("\n[*] Constructing 1-of-1 NFT AssetTransferTxn...")
    txn = transaction.AssetTransferTxn(
        sender=creator_addr,
        sp=sp,
        receiver=receiver_addr,
        amt=1,  # Transfer the single 1-of-1 unit
        index=asset_id,
        note=b"AlgoRacers: Driver #001 Collectible Delivery"
    )

    # 6. Sign and Submit
    signed_txn = txn.sign(creator_pk)
    txid = client.send_transaction(signed_txn)
    print(f"   🚀 Submitted! TXID: {txid}")

    # 7. Wait for Confirmation
    print("\n[*] Waiting for block confirmation...")
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)
    confirmed_round = confirmed_txn.get("confirmed-round")

    print(f"\n🎉 DRIVER NFT TRANSFERRED in Round #{confirmed_round}!")

    # 8. Verify On-Chain Balances
    creator_info = client.account_info(creator_addr)
    recv_info = client.account_info(receiver_addr)

    creator_holding = next((a.get("amount") for a in creator_info.get("assets", []) if a.get("asset-id") == asset_id), 0)
    recv_holding = next((a.get("amount") for a in recv_info.get("assets", []) if a.get("asset-id") == asset_id), 0)

    print("\n" + "-" * 65)
    print("🏆 Verifiable On-Chain Ownership Status:")
    print(f"   • Creator Balance:  {creator_holding} units (Transferred out)")
    print(f"   • Receiver Balance: {recv_holding} unit (New Sole Owner!)")
    print("-" * 65)

    print("\n🔗 TestNet Explorer Link:")
    print(f"👉 https://testnet.explorer.perawallet.app/tx/{txid}")
    print("=" * 65)

if __name__ == "__main__":
    main()
