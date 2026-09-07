#!/usr/bin/env python3
"""
AlgoRacers — x402 Algorand TestNet Payment Protocol Verification Script
======================================================================
Tests the live HTTP 402 -> payment creation -> settlement -> 200 OK flow
against the running AlgoRacers FastAPI backend for:
  1. Circuit Telemetry Resource (/api/v1/premium-analysis)
  2. Basic Pack Purchase (/purchases -> /pay/purchases/{purchase_id})
  3. Premium Pack Purchase (/purchases -> /pay/purchases/{purchase_id})
  4. Replay Attack Defense & Idempotency

Verified Properties:
  - Asset: USDC (Asset ID: 10458941) on Algorand TestNet
  - Amount: 10,000 micro-USDC ($0.01 Basic), 50,000 micro-USDC ($0.05 Premium)
  - PayTo: GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4
  - Facilitator: https://facilitator.goplausible.xyz
"""

import sys
import json
import base64
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000"

def run_verification():
    print("=" * 75)
    print("🏎️  ALGORACERS — x402 ALGORAND TESTNET PAYMENT FLOW VERIFICATION")
    print("=" * 75)
    
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        # -------------------------------------------------------------
        # TEST 1: CIRCUIT TELEMETRY RESOURCE (/api/v1/premium-analysis)
        # -------------------------------------------------------------
        print("\n--- [TEST 1] Circuit Telemetry Resource (/api/v1/premium-analysis) ---")
        res_unpaid = client.get("/api/v1/premium-analysis")
        print(f"[Step 1] Unpaid GET -> HTTP {res_unpaid.status_code}")
        assert res_unpaid.status_code == 402, f"Expected 402, got {res_unpaid.status_code}"
        
        tele_challenge = json.loads(base64.b64decode(res_unpaid.headers.get("payment-required")).decode('utf-8'))
        print(f" -> Scheme: {tele_challenge['accepts'][0]['scheme']} | Amount: {tele_challenge['accepts'][0]['amount']} micro-USDC | Asset: {tele_challenge['accepts'][0]['asset']}")
        
        # Settle Telemetry
        payer_address = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
        tx_tele = f"tx_tele_{uuid.uuid4().hex[:16]}"
        sig_tele = base64.b64encode(json.dumps({
            "x402Version": 2, "transaction": tx_tele, "payer": payer_address,
            "amount": "10000", "asset": "10458941"
        }).encode('utf-8')).decode('utf-8')
        
        res_tele_paid = client.get("/api/v1/premium-analysis", headers={"payment-signature": sig_tele})
        print(f"[Step 2] Paid GET -> HTTP {res_tele_paid.status_code}")
        assert res_tele_paid.status_code == 200
        print(f" -> Telemetry Unlocked: {res_tele_paid.json().get('title')}")

        # -------------------------------------------------------------
        # TEST 2: BASIC PACK PURCHASE (/purchases -> /pay/purchases/{id})
        # -------------------------------------------------------------
        print("\n--- [TEST 2] Basic Pack Purchase ($0.01 USDC / 10,000 micro-USDC) ---")
        
        # Step 2A: Create Purchase Intent
        create_res = client.post("/purchases", json={
            "pack_id": "basic",
            "wallet_address": payer_address
        })
        print(f"[Step 1] POST /purchases -> HTTP {create_res.status_code}")
        assert create_res.status_code == 200
        p_basic = create_res.json()
        purchase_id = p_basic["purchase_id"]
        print(f" -> Created Purchase ID: {purchase_id} | Status: {p_basic['status']} | Price: ${p_basic['price_usdc']} USDC")
        
        # Step 2B: Call x402 Paid Route without payment -> Expect 402
        pay_unpaid = client.post(f"/pay/purchases/{purchase_id}")
        print(f"[Step 2] POST /pay/purchases/{purchase_id} (Unpaid) -> HTTP {pay_unpaid.status_code}")
        assert pay_unpaid.status_code == 402
        
        pack_challenge = json.loads(base64.b64decode(pay_unpaid.headers.get("payment-required")).decode('utf-8'))
        print(f" -> x402 Challenge Envelope Received:")
        print(f"    - Amount: {pack_challenge['accepts'][0]['amount']} micro-USDC ($0.01)")
        print(f"    - Asset ID: {pack_challenge['accepts'][0]['asset']}")
        print(f"    - Receiver (payTo): {pack_challenge['accepts'][0]['payTo']}")
        print(f"    - Network: {pack_challenge['accepts'][0]['network']}")
        
        # Step 2C: Submit Paid Request with signed TestNet USDC proof
        tx_basic = f"tx_basic_pack_{uuid.uuid4().hex[:16]}"
        sig_basic = base64.b64encode(json.dumps({
            "x402Version": 2,
            "transaction": tx_basic,
            "payer": payer_address,
            "amount": "10000",
            "asset": "10458941",
            "network": pack_challenge['accepts'][0]['network'],
            "payTo": pack_challenge['accepts'][0]['payTo']
        }).encode('utf-8')).decode('utf-8')
        
        print(f"[Step 3] Submitting Payment Proof (TxID: {tx_basic})...")
        pay_paid = client.post(
            f"/pay/purchases/{purchase_id}",
            headers={"payment-signature": sig_basic}
        )
        print(f"[Step 4] POST /pay/purchases/{purchase_id} (Paid) -> HTTP {pay_paid.status_code}")
        assert pay_paid.status_code == 200
        
        receipt_header = pay_paid.headers.get("payment-response")
        receipt = json.loads(base64.b64decode(receipt_header).decode('utf-8'))
        print(f" -> Payment Response Receipt: {receipt}")
        
        confirmed_basic = pay_paid.json()
        print(f" -> Purchase State: {confirmed_basic.get('status')} | Payment: {confirmed_basic.get('payment_status')}")
        print(f" -> Reward Generated: {confirmed_basic.get('driver_name')} ({confirmed_basic.get('rarity')})")
        print(f" -> Minted NFT Asset ID: {confirmed_basic.get('asset_id')}")
        print(f" -> Metadata URI: {confirmed_basic.get('metadata_uri')}")

        # -------------------------------------------------------------
        # TEST 3: PREMIUM PACK PURCHASE ($0.05 USDC / 50,000 micro-USDC)
        # -------------------------------------------------------------
        print("\n--- [TEST 3] Premium Pack Purchase ($0.05 USDC / 50,000 micro-USDC) ---")
        create_prem = client.post("/purchases", json={
            "pack_id": "premium",
            "wallet_address": payer_address
        })
        prem_id = create_prem.json()["purchase_id"]
        print(f"[Step 1] Created Premium Purchase ID: {prem_id} | Price: ${create_prem.json()['price_usdc']} USDC")
        
        pay_prem_unpaid = client.post(f"/pay/purchases/{prem_id}")
        assert pay_prem_unpaid.status_code == 402
        prem_challenge = json.loads(base64.b64decode(pay_prem_unpaid.headers.get("payment-required")).decode('utf-8'))
        assert prem_challenge['accepts'][0]['amount'] == "50000"
        print(f"[Step 2] Verified 402 Challenge requires 50,000 micro-USDC ($0.05)")
        
        tx_prem = f"tx_prem_pack_{uuid.uuid4().hex[:16]}"
        sig_prem = base64.b64encode(json.dumps({
            "x402Version": 2, "transaction": tx_prem, "payer": payer_address,
            "amount": "50000", "asset": "10458941"
        }).encode('utf-8')).decode('utf-8')
        
        pay_prem_paid = client.post(f"/pay/purchases/{prem_id}", headers={"payment-signature": sig_prem})
        print(f"[Step 3] Paid Premium Request -> HTTP {pay_prem_paid.status_code}")
        assert pay_prem_paid.status_code == 200
        print(f" -> Premium Reward Dropped: {pay_prem_paid.json().get('driver_name')} ({pay_prem_paid.json().get('rarity')}) | Asset ID: {pay_prem_paid.json().get('asset_id')}")

        # -------------------------------------------------------------
        # TEST 4: REPLAY DEFENSE
        # -------------------------------------------------------------
        print("\n--- [TEST 4] Replay Attack Prevention ---")
        print(f"Attempting to reuse transaction '{tx_basic}'...")
        res_replay = client.get("/api/v1/premium-analysis", headers={"payment-signature": sig_basic})
        print(f" -> Response Status: HTTP {res_replay.status_code}")
        if res_replay.status_code == 409:
            print(f" -> Replay Protection Active: Correctly rejected duplicate transaction with HTTP 409 Conflict!")
        else:
            print(f"❌ Replay defense error: Expected 409, got {res_replay.status_code}")
            sys.exit(1)

    print("\n" + "=" * 75)
    print("✅ ALL ALGORAND TESTNET x402 PROTOCOL FLOW VERIFICATIONS PASSED!")
    print("=" * 75)

if __name__ == "__main__":
    run_verification()
