"""
Pokédex — Algorand Fundamentals
Script: query_transaction.py
=============================================
Demonstrates querying historical blockchain data using the Algorand Indexer.
Algod vs Indexer:
  • Algod: Real-time node engine (processes blocks, holds active state, sends txns).
  • Indexer: Read-optimized search database (indexes history, timestamps, addresses, notes).
"""

import sys
import os
import base64
from pathlib import Path
from dotenv import load_dotenv
from algosdk.v2client import indexer

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

INDEXER_ADDRESS = os.getenv("INDEXER_ADDRESS", "https://testnet-idx.algonode.cloud")
INDEXER_TOKEN = os.getenv("INDEXER_TOKEN", "")

def get_indexer_client() -> indexer.IndexerClient:
    return indexer.IndexerClient(indexer_token=INDEXER_TOKEN, indexer_address=INDEXER_ADDRESS)

def main():
    print("=" * 65)
    print("⚡  POKÉDEX — QUERY BLOCKCHAIN VIA INDEXER")
    print("=" * 65)

    client = get_indexer_client()

    if len(sys.argv) < 2:
        # Default to checking transaction history for the .env sender address
        target_addr = os.getenv("TESTNET_SENDER_ADDRESS", "").strip()
        if not target_addr:
            print("Usage:")
            print("  python query_transaction.py --tx <TRANSACTION_ID>")
            print("  python query_transaction.py --account <ALGORAND_ADDRESS>")
            return
        query_type = "--account"
        query_val = target_addr
    else:
        if sys.argv[1] in ["--tx", "-t"]:
            query_type = "--tx"
            query_val = sys.argv[2]
        elif sys.argv[1] in ["--account", "-a"]:
            query_type = "--account"
            query_val = sys.argv[2]
        else:
            # Assume 52-char is txid, 58-char is address
            query_val = sys.argv[1]
            query_type = "--tx" if len(query_val) == 52 else "--account"

    if query_type == "--tx":
        print(f"\n🔍 Querying specific transaction ID: {query_val}")
        try:
            response = client.transaction(query_val)
            txn_data = response.get("transaction", {})
            
            print("\n📋 Indexed Transaction Details:")
            print(f"   • TXID:             {txn_data.get('id')}")
            print(f"   • Confirmed Round:  {txn_data.get('confirmed-round')}")
            print(f"   • Block Timestamp:  {txn_data.get('round-time')}")
            print(f"   • Transaction Type: {txn_data.get('tx-type')}")
            print(f"   • Sender:           {txn_data.get('sender')}")
            
            payment = txn_data.get("payment-transaction", {})
            if payment:
                print(f"   • Receiver:         {payment.get('receiver')}")
                print(f"   • Amount:           {payment.get('amount'):,} microALGOs ({payment.get('amount') / 1_000_000:.6f} ALGO)")
            
            print(f"   • Fee Paid:         {txn_data.get('fee'):,} microALGOs")
            
            note_b64 = txn_data.get("note")
            if note_b64:
                try:
                    note_text = base64.b64decode(note_b64).decode("utf-8")
                    print(f"   • Note:             {note_text}")
                except Exception:
                    print(f"   • Note (b64):       {note_b64}")

        except Exception as e:
            print(f"❌ Transaction not found or Indexer error: {e}")

    elif query_type == "--account":
        print(f"\n🔍 Querying recent transaction history for address:\n   {query_val}")
        try:
            response = client.search_transactions_by_address(query_val, limit=5)
            transactions = response.get("transactions", [])
            
            print(f"\n📜 Found {len(transactions)} recent transaction(s):")
            for idx, txn in enumerate(transactions, start=1):
                tx_type = txn.get("tx-type")
                tx_id = txn.get("id")
                round_num = txn.get("confirmed-round")
                payment = txn.get("payment-transaction", {})
                amt = payment.get("amount", 0) / 1_000_000 if payment else 0
                
                print(f"\n   [{idx}] Type: {tx_type.upper()} | Round #{round_num}")
                print(f"       TXID:   {tx_id}")
                print(f"       Sender: {txn.get('sender')}")
                if payment:
                    print(f"       To:     {payment.get('receiver')} ({amt:.6f} ALGO)")

        except Exception as e:
            print(f"❌ Account history query error: {e}")

    print("\n" + "=" * 65)
    print("💡 WHY INDEXER IS CRITICAL FOR POKÉDEX:")
    print("FastAPI uses the Indexer to search a trainer's transaction history,")
    print("verify past pack purchase receipts, and populate collection asset dashboards")
    print("without putting heavy search loads on the real-time Algod consensus node.")
    print("=" * 65)

if __name__ == "__main__":
    main()
