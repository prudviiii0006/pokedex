"""
Pokédex — Algorand Standard Assets (ASAs)
Script: asset_opt_in.py
=======================================================
Demonstrates the Algorand Asset Opt-in mechanism:
An account CANNOT receive an ASA until it explicitly opts in.
Opt-in is an AssetTransferTxn of 0 units sent from the account to itself.
Increases the account's Minimum Balance Requirement (MBR) by 0.1 ALGO.
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
    print("⚡  POKÉDEX — ASSET OPT-IN (ZERO-AMOUNT SELF TRANSFER)")
    print("=" * 65)

    if len(sys.argv) < 2:
        print("❌ Error: Asset ID required.")
        print("Usage: python asset_opt_in.py <ASSET_ID> [RECEIVER_MNEMONIC]")
        return

    asset_id = int(sys.argv[1])
    client = get_algod_client()

    # 1. Determine Account to Opt In
    # If a second argument is given, use it as mnemonic.
    # Otherwise, check TESTNET_RECEIVER_MNEMONIC in .env or generate a funded ephemeral test receiver.
    if len(sys.argv) > 2:
        opt_mnemonic = sys.argv[2].strip()
        opt_pk = mnemonic.to_private_key(opt_mnemonic)
        opt_addr = account.address_from_private_key(opt_pk)
    else:
        # Check if we have TESTNET_RECEIVER_MNEMONIC in .env, otherwise generate one
        recv_mn = os.getenv("TESTNET_RECEIVER_MNEMONIC", "").strip()
        if recv_mn:
            opt_pk = mnemonic.to_private_key(recv_mn)
            opt_addr = account.address_from_private_key(opt_pk)
        else:
            print("[*] Generating a new receiver account for opt-in demonstration...")
            opt_pk, opt_addr = account.generate_account()
            passphrase = mnemonic.from_private_key(opt_pk)
            print(f"📍 New Receiver Address: {opt_addr}")
            print(f"🔑 Passphrase: {passphrase}")
            print("\n⚠️  Note: This new receiver must have at least 0.2 ALGO to cover MBR + fee before opting in.")
            print(f"👉 Dispenser: https://bank.testnet.algorand.network (Fund: {opt_addr})")
            
            # Save receiver to .env for subsequent scripts
            with open(env_path, "a") as f:
                f.write(f'\nTESTNET_RECEIVER_ADDRESS="{opt_addr}"\n')
                f.write(f'TESTNET_RECEIVER_MNEMONIC="{passphrase}"\n')
            print("💾 Saved TESTNET_RECEIVER credentials to backend/.env")

    print(f"\n[Opt-in Account Details]")
    print(f"   Address:  {opt_addr}")
    print(f"   Asset ID: {asset_id}")

    # Check account balance
    try:
        acct_info = client.account_info(opt_addr)
        balance = acct_info.get("amount", 0)
    except Exception:
        balance = 0

    print(f"   Balance:  {balance:,} microALGOs ({balance / 1_000_000:.6f} ALGO)")
    if balance < 101_000:
        print("\n⚠️  Insufficient ALGO! Account needs at least 0.2 ALGO to hold an asset (0.1 MBR + 0.1 asset MBR + fee).")
        print(f"👉 Please fund: {opt_addr}")
        return

    # 2. Verify Asset Existence on Algod
    try:
        asset_info = client.asset_info(asset_id)
        asset_name = asset_info.get("params", {}).get("name", "Unknown")
        print(f"   Target Asset Name: {asset_name}")
    except Exception as e:
        print(f"❌ Asset ID {asset_id} not found on TestNet: {e}")
        return

    # 3. Check if already opted in
    existing_assets = acct_info.get("assets", [])
    already_opted = any(a.get("asset-id") == asset_id for a in existing_assets)
    if already_opted:
        print(f"\n✅ Account {opt_addr} is ALREADY opted into Asset ID #{asset_id}!")
        return

    # 4. Construct Opt-In Transaction (0-amount transfer to self)
    sp = client.suggested_params()

    print("\n[*] Constructing AssetTransferTxn (Opt-In):")
    print(f"   • Sender:   {opt_addr}")
    print(f"   • Receiver: {opt_addr} (Self)")
    print(f"   • Amount:   0")
    print(f"   • Asset ID: {asset_id}")

    opt_in_txn = transaction.AssetTransferTxn(
        sender=opt_addr,
        sp=sp,
        receiver=opt_addr,
        amt=0,
        index=asset_id
    )

    # 5. Sign Transaction
    signed_opt_in = opt_in_txn.sign(opt_pk)

    # 6. Submit to TestNet
    txid = client.send_transaction(signed_opt_in)
    print(f"\n🚀 Opt-In transaction submitted! TXID: {txid}")

    # 7. Wait for Confirmation
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)
    confirmed_round = confirmed_txn.get("confirmed-round")

    print(f"\n🎉 OPT-IN CONFIRMED in Round #{confirmed_round}!")
    print(f"   Account {opt_addr} is now eligible to receive Asset #{asset_id} ({asset_name}).")

    print("\n🔗 Verification Link:")
    print(f"👉 https://testnet.explorer.perawallet.app/tx/{txid}")
    print("=" * 65)

if __name__ == "__main__":
    main()
