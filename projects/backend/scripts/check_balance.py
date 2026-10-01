"""
Pokédex — Algorand Fundamentals
Script: check_balance.py
=============================================
Queries the live on-chain account state from Algod.
Demonstrates:
  1. Connecting to the Algod REST client (TestNet)
  2. Querying `account_info(address)`
  3. Decoding microALGOs (1 ALGO = 1,000,000 microALGOs)
  4. Inspecting account Minimum Balance Requirement (MBR) and status
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from algosdk.v2client import algod

# Load environment variables from backend/.env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

ALGOD_ADDRESS = os.getenv("ALGOD_ADDRESS", "https://testnet-api.algonode.cloud")
ALGOD_TOKEN = os.getenv("ALGOD_TOKEN", "")

def get_algod_client() -> algod.AlgodClient:
    """Initializes and returns the Algod client."""
    return algod.AlgodClient(algod_token=ALGOD_TOKEN, algod_address=ALGOD_ADDRESS)

def main():
    print("=" * 65)
    print("⚡  POKÉDEX — CHECK TESTNET ACCOUNT BALANCE")
    print("=" * 65)

    # 1. Determine address to check (CLI argument or .env default)
    if len(sys.argv) > 1:
        target_address = sys.argv[1].strip()
    else:
        target_address = os.getenv("TESTNET_SENDER_ADDRESS", "").strip()

    if not target_address:
        print("❌ Error: No address provided.")
        print("Usage: python check_balance.py <ALGORAND_ADDRESS>")
        print("Or generate an account first using: python create_account.py")
        return

    # 2. Connect to Algod
    client = get_algod_client()
    try:
        status = client.status()
        current_round = status.get("last-round")
        print(f"📡 Connected to Algod TestNet Node! (Current Block/Round: #{current_round})")
    except Exception as e:
        print(f"❌ Failed to reach Algod node at {ALGOD_ADDRESS}: {e}")
        return

    print(f"\n🔍 Querying account: {target_address}")

    # 3. Query ledger state via Algod
    try:
        account_info = client.account_info(target_address)
    except Exception as e:
        # If an account has 0 transactions and 0 balance, it does not yet exist in ledger state
        print(f"\n⚠️  Account not found on-chain (or balance is 0 ALGO).")
        print(f"   Details: {e}")
        print("\n👉 To activate this account, fund it via the TestNet Dispenser:")
        print(f"   https://bank.testnet.algorand.network")
        return

    # 4. Parse balances and account metadata
    amount_microalgos = account_info.get("amount", 0)
    amount_algos = amount_microalgos / 1_000_000
    min_balance_microalgos = account_info.get("min-balance", 100_000)
    min_balance_algos = min_balance_microalgos / 1_000_000
    round_queried = account_info.get("round", current_round)

    print("\n" + "-" * 65)
    print(f"💰 Account Balance Summary (as of Round #{round_queried}):")
    print(f"   • Total Balance:       {amount_microalgos:,} microALGOs ({amount_algos:.6f} ALGO)")
    print(f"   • Minimum Balance:     {min_balance_microalgos:,} microALGOs ({min_balance_algos:.6f} ALGO)")
    print(f"   • Spendable Balance:   {max(0, amount_microalgos - min_balance_microalgos):,} microALGOs ({(max(0, amount_microalgos - min_balance_microalgos) / 1_000_000):.6f} ALGO)")
    print(f"   • Total Assets Held:   {len(account_info.get('assets', []))}")
    print(f"   • Total Apps Created:  {len(account_info.get('created-apps', []))}")
    print("-" * 65)

    print("\n💡 EXPLANATION OF RESPONSE:")
    print("1. `amount`: Total microALGOs credited to this public address.")
    print("2. `min-balance`: Minimum Balance Requirement (MBR). An account requires")
    print("   at least 0.1 ALGO (100,000 microALGOs) to exist on the Algorand ledger.")
    print("3. `spendable`: Balance above MBR that can be transferred or spent on fees.")
    print("=" * 65)

if __name__ == "__main__":
    main()
