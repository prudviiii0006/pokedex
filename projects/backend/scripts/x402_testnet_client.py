"""
AlgoRacers — Session 8: Real x402 Payments on Algorand TestNet
Script: x402_testnet_client.py
==============================================================
Autonomous Python client executing real Algorand TestNet x402 payments:
  1. Requests GET /premium-analysis -> Receives HTTP 402 Payment Required
  2. Parses Algorand TestNet payment requirements (Asset ID 10458941, Amount: 0.01 USDC, Recipient)
  3. Queries Algod for suggested transaction parameters
  4. Builds and signs an Algorand AssetTransfer transaction locally
  5. Retries request with `X-402-Payment-Proof: algorand:<signed_txn_b64>`
  6. Server verifies signature, settles on TestNet, and returns HTTP 200 OK with live on-chain TXID!
"""

import sys
import json
import base64
import httpx
import algosdk
from algosdk.v2client import algod
from algosdk import transaction, account, encoding, mnemonic

ALGOD_SERVER = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""
API_BASE_URL = "http://localhost:8000"
if len(sys.argv) > 1:
    API_BASE_URL = sys.argv[1]

# Demo TestNet Payer Account (Generated for client testing)
DEMO_PAYER_MNEMONIC = "friend panda umbrella balance supreme hip turkey invite awesome humble note dial wrong begin blade under victory prevent tribe nothing alcohol comic little above decide"

def main():
    print("=" * 70)
    print("🏎️  ALGORACERS — REAL ALGORAND TESTNET x402 PAYMENT CLIENT")
    print("=" * 70)

    # 1. Derive Payer Account
    payer_sk = mnemonic.to_private_key(DEMO_PAYER_MNEMONIC)
    payer_address = account.address_from_private_key(payer_sk)
    print(f"👤 Payer Public Address:  {payer_address}")

    client = httpx.Client(base_url=API_BASE_URL, timeout=30.0)

    # -------------------------------------------------------------
    # STEP 1: INITIAL UNPAID REQUEST
    # -------------------------------------------------------------
    print("\n[Step 1: Requesting Protected Resource (Unpaid)]...")
    res = client.get("/premium-analysis")
    print(f"   HTTP Status: {res.status_code} {res.reason_phrase}")

    if res.status_code != 402:
        print(f"❌ Expected 402 Payment Required, received: {res.status_code}")
        return

    # -------------------------------------------------------------
    # STEP 2: PARSE ALGORAND PAYMENT REQUIREMENTS
    # -------------------------------------------------------------
    print("\n[Step 2: Parsing x402 Algorand Payment Requirements]...")
    challenge = res.json().get("detail", res.json())
    reqs = challenge.get("payment_requirements", {})

    network = reqs.get("network")
    asset = reqs.get("asset")
    amount_usdc = reqs.get("amount")
    recipient = reqs.get("recipient")
    resource = reqs.get("resource")

    print(f"   • Network:     {network}")
    print(f"   • Resource:    {resource}")
    print(f"   • Price:       {amount_usdc} {asset}")
    print(f"   • Units:       {reqs.get('amount_units')}")
    print(f"   • Recipient:   {recipient}")

    # -------------------------------------------------------------
    # STEP 3: CONSTRUCT & SIGN ALGORAND ASA PAYMENT TRANSACTION
    # -------------------------------------------------------------
    print("\n[Step 3: Building & Signing Algorand AssetTransfer Transaction Locally]...")
    algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_SERVER)
    params = algod_client.suggested_params()

    micro_usdc = int(amount_usdc * 1_000_000)
    usdc_asset_id = 10458941

    # Create Asset Transfer Transaction (ASA Payment)
    unsigned_txn = transaction.AssetTransferTxn(
        sender=payer_address,
        sp=params,
        receiver=recipient,
        amt=micro_usdc,
        index=usdc_asset_id,
        note=b"AlgoRacers x402: Premium Analysis"
    )

    # Sign locally (Private key never leaves the client!)
    signed_txn = unsigned_txn.sign(payer_sk)
    signed_b64 = encoding.msgpack_encode(signed_txn)

    print(f"   • Asset ID:    {usdc_asset_id} (TestNet USDC)")
    print(f"   • MicroUSDC:   {micro_usdc}")
    print(f"   • Fee:         {params.fee} microALGOs")
    print(f"   • Local TxID:  {signed_txn.get_txid()}")
    print("   🔒 Signed locally with client Ed25519 key.")

    # -------------------------------------------------------------
    # STEP 4: SUBMIT REQUEST WITH ALGORAND PAYMENT PROOF
    # -------------------------------------------------------------
    print("\n[Step 4: Retrying GET /premium-analysis with Signed Algorand Transaction]...")
    headers = {
        "X-402-Payment-Proof": f"algorand:{signed_b64}"
    }

    res_paid = client.get("/premium-analysis", headers=headers)
    print(f"   HTTP Status: {res_paid.status_code} {res_paid.reason_phrase}")

    if res_paid.status_code == 200:
        data = res_paid.json()
        print("\n🎉 ACCESS GRANTED! 200 OK — Premium Resource Unlocked:")
        print(f"   • Title:       {data.get('title')}")
        print(f"   • Circuit:     {data.get('circuit')}")
        print(f"   • Conditions:  {data.get('track_conditions')}")
        print(f"   • AI Insights: {data.get('tactical_ai_insights')}")
        print("\n   [On-Chain Algorand Payment Receipt]:")
        for k, v in data.get("payment_receipt", {}).items():
            print(f"     ↳ {k}: {v}")
    else:
        print(f"❌ Payment verification failed: {res_paid.text}")
        return

    # -------------------------------------------------------------
    # STEP 5: TEST REPLAY PROTECTION
    # -------------------------------------------------------------
    print("\n[Step 5: Testing Replay Attack on Algorand Transaction ID]...")
    res_replay = client.get("/premium-analysis", headers=headers)
    print(f"   HTTP Status: {res_replay.status_code} {res_replay.reason_phrase}")
    print(f"   Detail:      {res_replay.json().get('detail')}")
    if res_replay.status_code == 409:
        print("   ✅ Replay attack successfully blocked by Algorand TxID uniqueness check!")
    print("=" * 70)

if __name__ == "__main__":
    main()
