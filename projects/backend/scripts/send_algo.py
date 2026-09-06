"""
AlgoRacers — Session 1: Algorand Fundamentals
Script: send_algo.py
=============================================
Demonstrates the explicit 5-step transaction lifecycle:
  Step 1: Account Loading (Sender Private Key & Address)
  Step 2: Transaction Construction (PaymentTxn with Suggested Params)
  Step 3: Cryptographic Local Signing (Ed25519)
  Step 4: Submission to TestNet (Algod Broadcast)
  Step 5: Confirmation & State Verification (~2.9s Finality)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")

def get_algod_client() -> algod.AlgodClient:
    return algod.AlgodClient(algod_token=ALGOD_TOKEN, algod_address=ALGOD_ADDRESS)

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — EXPLICIT ALGORAND PAYMENT TRANSACTION")
    print("=" * 65)

    client = get_algod_client()

    # -------------------------------------------------------------
    # STEP 1: LOAD SENDER ACCOUNT SECURELY
    # -------------------------------------------------------------
    sender_mnemonic = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    if not sender_mnemonic:
        print("❌ Error: TESTNET_SENDER_MNEMONIC not found in backend/.env")
        print("Please run `python create_account.py` first and fund the account.")
        return

    sender_private_key = mnemonic.to_private_key(sender_mnemonic)
    sender_address = account.address_from_private_key(sender_private_key)

    print(f"\n[Step 1: Sender Account]")
    print(f"   Address: {sender_address}")

    # Check sender balance
    try:
        acct_info = client.account_info(sender_address)
        balance = acct_info.get("amount", 0)
    except Exception:
        balance = 0

    print(f"   Balance: {balance:,} microALGOs ({balance / 1_000_000:.6f} ALGO)")
    if balance < 200_000:
        print("\n⚠️  Insufficient balance to pay transaction amount + network fee!")
        print(f"👉 Please fund address at: https://bank.testnet.algorand.network")
        print(f"   Address: {sender_address}")
        return

    # Define Receiver (CLI argument or fresh demo target)
    if len(sys.argv) > 1:
        receiver_address = sys.argv[1].strip()
        print(f"\n[Receiver Account (Specified)]")
        print(f"   Address: {receiver_address}")
    else:
        _, receiver_address = account.generate_account()
        print(f"\n[Receiver Account (Ephemeral Demo Target)]")
        print(f"   Address: {receiver_address}")

    # -------------------------------------------------------------
    # STEP 2: QUERY SUGGESTED PARAMS & CONSTRUCT PAYMENTTXN
    # -------------------------------------------------------------
    print("\n[Step 2: Fetching Suggested Transaction Parameters]")
    sp = client.suggested_params()
    print(f"   • Fee:              {sp.fee} microALGO ({sp.fee / 1_000_000:.6f} ALGO)")
    print(f"   • First Valid Round: {sp.first}")
    print(f"   • Last Valid Round:  {sp.last} (Valid for {sp.last - sp.first} rounds)")
    print(f"   • Genesis ID:        {sp.gen}")
    print(f"   • Genesis Hash:      {sp.gh}")

    amount_to_send = 100_000  # 0.1 ALGO in microALGOs
    note_data = b"AlgoRacers: Session 1 Test Payment"

    print("\n[Constructing PaymentTxn Object]")
    txn = transaction.PaymentTxn(
        sender=sender_address,
        sp=sp,
        receiver=receiver_address,
        amt=amount_to_send,
        note=note_data
    )
    print("   ✅ Transaction object created in memory (unsigned).")

    # -------------------------------------------------------------
    # STEP 3: CRYPTOGRAPHICALLY SIGN THE TRANSACTION
    # -------------------------------------------------------------
    print("\n[Step 3: Signing Transaction Locally]")
    # Signing creates an Ed25519 signature of the transaction bytes.
    # The private key NEVER leaves your local machine.
    signed_txn = txn.sign(sender_private_key)
    print(f"   ✅ Signed! Signature length: {len(signed_txn.signature)} bytes")

    # -------------------------------------------------------------
    # STEP 4: SUBMIT RAW SIGNED TRANSACTION TO TESTNET
    # -------------------------------------------------------------
    print("\n[Step 4: Submitting Signed Transaction to Algod]")
    txid = client.send_transaction(signed_txn)
    print(f"   🚀 Submitted successfully!")
    print(f"   📍 Transaction ID (TXID): {txid}")

    # -------------------------------------------------------------
    # STEP 5: WAIT FOR CONSENSUS CONFIRMATION
    # -------------------------------------------------------------
    print("\n[Step 5: Waiting for Block Confirmation (~2.9s)]...")
    confirmed_txn = transaction.wait_for_confirmation(client, txid, wait_rounds=4)

    confirmed_round = confirmed_txn.get("confirmed-round")
    print(f"   🎉 TRANSACTION CONFIRMED in Round #{confirmed_round}!")

    print("\n" + "=" * 65)
    print("🔗 INDEPENDENT EXPLORER VERIFICATION:")
    print(f"👉 Pera Explorer:  https://testnet.explorer.perawallet.app/tx/{txid}")
    print(f"👉 Lora Explorer:  https://lora.algokit.io/testnet/transaction/{txid}")
    print("=" * 65)

if __name__ == "__main__":
    main()
