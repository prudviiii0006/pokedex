"""
AlgoRacers — Session 2: Algorand Standard Assets (ASAs)
Script: transfer_asset.py
=======================================================
Transfers units of an ASA from creator/sender to an opted-in receiver account.
Demonstrates:
  1. Checking that the recipient has opted into the Asset ID
  2. Constructing an AssetTransferTxn
  3. Difference between PaymentTxn (ALGO) vs AssetTransferTxn (ASA)
  4. On-chain state verification
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
    print("🏎️  ALGORACERS — TRANSFER FUNGIBLE ASA (CREDITS)")
    print("=" * 65)

    if len(sys.argv) < 2:
        print("❌ Error: Asset ID required.")
        print("Usage: python transfer_asset.py <ASSET_ID> [RECEIVER_ADDRESS] [AMOUNT]")
        return

    asset_id = int(sys.argv[1])
    client = get_algod_client()

    # 1. Load Sender (Creator) Account
    sender_mn = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    if not sender_mn:
        print("❌ Error: TESTNET_SENDER_MNEMONIC not found in backend/.env")
        return

    sender_pk = mnemonic.to_private_key(sender_mn)
    sender_addr = account.address_from_private_key(sender_pk)

    # 2. Determine Receiver and Amount
    if len(sys.argv) > 2:
        receiver_addr = sys.argv[2].strip()
    else:
        receiver_addr = os.getenv("TESTNET_RECEIVER_ADDRESS", "").strip()

    if not receiver_addr:
        print("❌ Error: No receiver address specified.")
        print("Please provide a receiver address or run `asset_opt_in.py` first.")
        return

    amount_to_send = int(sys.argv[3]) if len(sys.argv) > 3 else 25

    print(f"\n[Transfer Details]")
    print(f"   • Asset ID:  {asset_id}")
    print(f"   • Sender:    {sender_addr}")
    print(f"   • Receiver:  {receiver_addr}")
    print(f"   • Amount:    {amount_to_send} units")

    # 3. Verify Receiver Opt-in Status on Algod
    print("\n[*] Verifying receiver opt-in status on Algod...")
    try:
        recv_info = client.account_info(receiver_addr)
        assets = recv_info.get("assets", [])
        is_opted_in = any(a.get("asset-id") == asset_id for a in assets)
        if not is_opted_in:
            print(f"\n❌ Receiver {receiver_addr} has NOT opted into Asset ID #{asset_id}!")
            print("   In Algorand, un-opted accounts CANNOT receive ASAs (prevents spam).")
            print(f"👉 Run: python asset_opt_in.py {asset_id}")
            return
        print("   ✅ Receiver is opted in and ready to receive.")
    except Exception as e:
        print(f"❌ Could not query receiver account: {e}")
        return

    # 4. Construct AssetTransferTxn
    sp = client.suggested_params()

    print("\n[*] Constructing AssetTransferTxn...")
    txn = transaction.AssetTransferTxn(
        sender=sender_addr,
        sp=sp,
        receiver=receiver_addr,
        amt=amount_to_send,
        index=asset_id,
        note=b"AlgoRacers: Session 2 Asset Transfer"
    )

    # 5. Sign Transaction Locally
    signed_txn = txn.sign(sender_pk)

    # 6. Broadcast to TestNet
    txid = client.send_transaction(signed_txn)
    print(f"   🚀 Submitted! TXID: {txid}")

    # 7. Wait for Confirmation
    print("\n[*] Waiting for Block Confirmation...")
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)
    confirmed_round = confirmed_txn.get("confirmed-round")

    print(f"\n🎉 ASA TRANSFER CONFIRMED in Round #{confirmed_round}!")

    # 8. Query updated asset balance of receiver
    updated_recv_info = client.account_info(receiver_addr)
    for a in updated_recv_info.get("assets", []):
        if a.get("asset-id") == asset_id:
            print(f"   📍 Receiver New Asset Balance: {a.get('amount')} units of Asset #{asset_id}")

    print("\n🔗 TestNet Explorer Link:")
    print(f"👉 https://testnet.explorer.perawallet.app/tx/{txid}")
    print("=" * 65)

if __name__ == "__main__":
    main()
