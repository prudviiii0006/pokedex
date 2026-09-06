"""
AlgoRacers — Session 8: Algorand TestNet x402 Integration Test
Script: testnet_x402_integration.py
==============================================================
Explicit TestNet Integration Test (Part 26):
  1. Records initial Payer & Receiver TestNet balances
  2. Queries paid endpoint GET /premium-analysis -> Receives 402 Payment Required
  3. Parses Algorand TestNet requirements (0.01 USDC, ASA ID 10458941)
  4. Builds & signs Algorand AssetTransfer transaction
  5. Submits signed payload in `X-402-Payment-Proof` header
  6. Receives HTTP 200 OK with confirmed on-chain receipt and telemetry
  7. Audits transaction ID and explorer link
"""

import sys
import json
import httpx
import algosdk
from algosdk.v2client import algod
from algosdk import transaction, account, encoding, mnemonic

ALGOD_SERVER = "https://testnet-api.algonode.cloud"
ALGOD_TOKEN = ""
API_BASE_URL = "http://localhost:8000"
if len(sys.argv) > 1:
    API_BASE_URL = sys.argv[1]

TESTNET_USDC_ASSET_ID = 10458941
DEMO_PAYER_MNEMONIC = "friend panda umbrella balance supreme hip turkey invite awesome humble note dial wrong begin blade under victory prevent tribe nothing alcohol comic little above decide"
RECEIVER_TREASURY_ADDR = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"

def fetch_account_balances(algod_client, address):
    try:
        info = algod_client.account_info(address)
        algo_balance = info.get("amount", 0) / 1_000_000
        assets = {a["asset-id"]: a["amount"] for a in info.get("assets", [])}
        usdc_micro = assets.get(TESTNET_USDC_ASSET_ID, 0)
        return algo_balance, usdc_micro / 1_000_000, TESTNET_USDC_ASSET_ID in assets
    except Exception as e:
        return 0.0, 0.0, False

def main():
    print("=" * 75)
    print("🧪 ALGORACERS — OFFICIAL ALGORAND TESTNET x402 INTEGRATION TEST")
    print("=" * 75)

    algod_client = algod.AlgodClient(ALGOD_TOKEN, ALGOD_SERVER)

    # 1. Setup Payer & Receiver
    payer_sk = mnemonic.to_private_key(DEMO_PAYER_MNEMONIC)
    payer_addr = account.address_from_private_key(payer_sk)

    print("\n[Step 1: Auditing Initial TestNet Account Balances]...")
    p_algo, p_usdc, p_opt = fetch_account_balances(algod_client, payer_addr)
    r_algo, r_usdc, r_opt = fetch_account_balances(algod_client, RECEIVER_TREASURY_ADDR)

    print(f"   👤 Payer Address:    {payer_addr}")
    print(f"      • ALGO Balance:   {p_algo:.4f} ALGO")
    print(f"      • USDC Balance:   {p_usdc:.2f} USDC (Opted in: {p_opt})")

    print(f"\n   🏦 Receiver Treasury: {RECEIVER_TREASURY_ADDR}")
    print(f"      • ALGO Balance:   {r_algo:.4f} ALGO")
    print(f"      • USDC Balance:   {r_usdc:.2f} USDC (Opted in: {r_opt})")

    # 2. Issue Unpaid Request to FastAPI
    client = httpx.Client(base_url=API_BASE_URL, timeout=30.0)
    print("\n[Step 2: Sending Unpaid GET /premium-analysis to Resource Server]...")
    res = client.get("/premium-analysis")
    print(f"   HTTP Status Code: {res.status_code} {res.reason_phrase}")

    if res.status_code != 402:
        print(f"❌ Expected 402, got {res.status_code}")
        return

    # 3. Parse Requirements
    challenge = res.json()["detail"]["payment_requirements"]
    print(f"\n[Step 3: Received x402 Challenge]:")
    print(f"   • Asset:        {challenge['asset']} (ASA ID: {TESTNET_USDC_ASSET_ID})")
    print(f"   • Amount:       {challenge['amount']} USDC ({challenge['amount_units']})")
    print(f"   • Recipient:    {challenge['recipient']}")
    print(f"   • Network:      {challenge['network']}")

    # 4. Build & Sign Algorand Transaction
    print("\n[Step 4: Signing Algorand AssetTransfer Payment Locally]...")
    params = algod_client.suggested_params()
    micro_amount = int(challenge['amount'] * 1_000_000)

    txn = transaction.AssetTransferTxn(
        sender=payer_addr,
        sp=params,
        receiver=challenge['recipient'],
        amt=micro_amount,
        index=TESTNET_USDC_ASSET_ID,
        note=b"AlgoRacers: Session 8 Integration"
    )
    stxn = txn.sign(payer_sk)
    signed_b64 = encoding.msgpack_encode(stxn)
    local_txid = stxn.get_txid()

    print(f"   • Local TxID:   {local_txid}")
    print(f"   • Signed Bytes: {len(signed_b64)} chars (Base64 Msgpack)")

    # 5. Submit with x402 Header
    print("\n[Step 5: Retrying GET /premium-analysis with Payment Proof]...")
    res_paid = client.get(
        "/premium-analysis",
        headers={"X-402-Payment-Proof": f"algorand:{signed_b64}"}
    )

    print(f"   HTTP Status Code: {res_paid.status_code} {res_paid.reason_phrase}")
    if res_paid.status_code == 200:
        data = res_paid.json()
        print("\n🎉 SUCCESS! HTTP 200 OK — Resource Unlocked via Algorand x402 Payment:")
        print(f"   • Grand Prix Title: {data['title']}")
        print(f"   • AI Insight:       {data['tactical_ai_insights']}")
        print("\n   [Confirmed Payment Receipt]:")
        for k, v in data["payment_receipt"].items():
            print(f"     ↳ {k}: {v}")
        print(f"\n   🔗 TestNet Explorer: {data['payment_receipt'].get('explorer_url')}")
    else:
        print(f"❌ Failed: {res_paid.text}")

    print("\n" + "=" * 75)
    print("✅ TESTNET INTEGRATION TEST COMPLETE")
    print("=" * 75)

if __name__ == "__main__":
    main()
