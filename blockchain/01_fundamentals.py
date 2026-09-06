"""
AlgoRacers — Session 1: Algorand Fundamentals
=============================================
This script demonstrates the complete fundamental lifecycle of an Algorand transaction:
  1. Account Generation & Key Derivation (Ed25519)
  2. Algod Client Connection (TestNet)
  3. Balance Verification (MicroALGOs & Minimum Balance Requirement)
  4. Suggested Transaction Parameters (Fee, First/Last Valid Rounds, Genesis ID)
  5. Payment Transaction Construction (PaymentTxn)
  6. Cryptographic Transaction Signing (Ed25519 Signature)
  7. Network Broadcast & Awaiting Round Confirmation
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from algosdk import account, mnemonic, transaction
from algosdk.v2client import algod

# 1. Load environment variables safely
# Looks for .env in the project root or current working directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# 2. Configure Algorand TestNet Node connection
# We use public, free-tier TestNet endpoints provided by Algonode (no API key required)
ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")

def get_algod_client() -> algod.AlgodClient:
    """Initializes and returns an Algod client connected to Algorand TestNet."""
    return algod.AlgodClient(algod_token=ALGOD_TOKEN, algod_address=ALGOD_ADDRESS)

def load_or_generate_account():
    """
    Loads account from TESTNET_SENDER_MNEMONIC environment variable if present.
    Otherwise, securely generates a new keypair in memory.
    """
    saved_mnemonic = os.getenv("TESTNET_SENDER_MNEMONIC", "").strip()
    
    if saved_mnemonic:
        print("[*] Loading account from environment variable (TESTNET_SENDER_MNEMONIC)...")
        private_key = mnemonic.to_private_key(saved_mnemonic)
        address = account.address_from_private_key(private_key)
        return private_key, address, False
    else:
        print("[*] Generating a new ephemeral TestNet account...")
        private_key, address = account.generate_account()
        passphrase = mnemonic.from_private_key(private_key)
        return private_key, address, passphrase

def check_balance(client: algod.AlgodClient, address: str) -> int:
    """Queries the Algod node for the account balance in microALGOs."""
    try:
        account_info = client.account_info(address)
        return account_info.get("amount", 0)
    except Exception as e:
        # If the account has never received funds, it may not exist on ledger yet
        return 0

def main():
    print("=" * 60)
    print("🏎️  ALGORACERS — SESSION 1: ALGORAND FUNDAMENTALS")
    print("=" * 60)

    # Step 1: Connect to Algod (TestNet Node)
    algod_client = get_algod_client()
    try:
        status = algod_client.status()
        print(f"✅ Connected to Algorand TestNet via Algod!")
        print(f"   Current Block / Last Round: {status.get('last-round')}")
    except Exception as e:
        print(f"❌ Failed to connect to Algod: {e}")
        return

    # Step 2: Account Setup (Sender & Receiver)
    sender_pk, sender_addr, is_new_account = load_or_generate_account()
    print(f"\n[Sender Account]")
    print(f"   Address: {sender_addr}")

    # Generate a fresh receiver address for demonstration
    _, receiver_addr = account.generate_account()
    print(f"\n[Receiver Account (Generated Demo Target)]")
    print(f"   Address: {receiver_addr}")

    # Step 3: Check Sender Balance
    balance_microalgos = check_balance(algod_client, sender_addr)
    balance_algos = balance_microalgos / 1_000_000

    print(f"\n[Account Balance Check]")
    print(f"   Current Balance: {balance_microalgos:,} microALGOs ({balance_algos:.6f} ALGO)")

    # Minimum Balance Requirement check (Accounts need min 0.1 ALGO + fees)
    if balance_microalgos < 200_000:
        print("\n" + "⚠️ " * 15)
        print("INSUFFICIENT BALANCE TO EXECUTE TRANSACTION ON TESTNET")
        print("=" * 60)
        print(f"Please fund the sender address using the Algorand TestNet Dispenser:")
        print(f"👉 Address: {sender_addr}")
        print(f"👉 Dispenser URL: https://bank.testnet.algorand.network")
        print(f"👉 Alternative Dispenser: https://dispenser.testnet.aws.algodev.network")
        print("=" * 60)
        
        if is_new_account:
            print("\n💡 TIP: To reuse this account across runs, copy this 25-word mnemonic")
            print("   and add it to your .env file as TESTNET_SENDER_MNEMONIC:")
            print(f"\n   \"{is_new_account}\"\n")
        return

    # Step 4: Fetch Suggested Transaction Parameters from Algod
    print("\n[*] Fetching suggested transaction parameters from TestNet...")
    sp = algod_client.suggested_params()
    print(f"   - Network Fee: {sp.fee} microALGOs ({sp.fee / 1_000_000:.6f} ALGO)")
    print(f"   - First Valid Round: {sp.first}")
    print(f"   - Last Valid Round:  {sp.last}")
    print(f"   - Genesis ID:        {sp.gen}")

    # Step 5: Build Payment Transaction
    # Send 0.1 ALGO (100,000 microALGOs) to the receiver
    amount_to_send = 100_000  # 0.1 ALGO in microALGOs
    note_payload = b"AlgoRacers: Session 1 Test Payment"

    print(f"\n[*] Constructing PaymentTxn:")
    print(f"   From:   {sender_addr}")
    print(f"   To:     {receiver_addr}")
    print(f"   Amount: {amount_to_send:,} microALGOs (0.1 ALGO)")
    print(f"   Note:   {note_payload.decode('utf-8')}")

    txn = transaction.PaymentTxn(
        sender=sender_addr,
        sp=sp,
        receiver=receiver_addr,
        amt=amount_to_send,
        note=note_payload
    )

    # Step 6: Cryptographically Sign the Transaction
    print("\n[*] Signing transaction using Sender Private Key...")
    signed_txn = txn.sign(sender_pk)
    print(f"   ✅ Transaction signed locally. Raw signature attached.")

    # Step 7: Broadcast Transaction to Algorand TestNet
    print("\n[*] Broadcasting raw signed transaction to Algorand TestNet...")
    tx_id = algod_client.send_transaction(signed_txn)
    print(f"   🚀 Broadcasted! Transaction ID (TXID): {tx_id}")

    # Step 8: Await Consensus Confirmation
    print(f"\n[*] Waiting for block confirmation on TestNet (~2.9 - 4 seconds)...")
    confirmed_txn = transaction.wait_for_confirmation(algod_client, tx_id, 4)

    confirmed_round = confirmed_txn.get("confirmed-round", 0)
    print(f"   🎉 TRANSACTION CONFIRMED in Round / Block #{confirmed_round}!")

    # Step 9: Verify Final Balances
    sender_new_balance = check_balance(algod_client, sender_addr)
    receiver_new_balance = check_balance(algod_client, receiver_addr)

    print("\n[Updated Ledger Balances]")
    print(f"   Sender:   {sender_new_balance:,} microALGOs (Spent: {amount_to_send + sp.fee:,} microALGOs incl fee)")
    print(f"   Receiver: {receiver_new_balance:,} microALGOs")

    print("\n[Block Explorer Verification]")
    print(f"   View on Pera Explorer:")
    print(f"   👉 https://testnet.explorer.perawallet.app/tx/{tx_id}")
    print(f"   View on Lora (Dappflow):")
    print(f"   👉 https://lora.algokit.io/testnet/transaction/{tx_id}")

if __name__ == "__main__":
    main()
