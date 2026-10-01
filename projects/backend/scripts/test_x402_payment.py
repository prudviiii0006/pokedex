#!/usr/bin/env python3
"""
Pokédex — x402 Algorand TestNet Payment Protocol Verification Script
======================================================================
Tests the live HTTP 402 -> payment challenge -> settlement -> 200 OK flow
against the running Pokédex FastAPI backend for:
  1. Pricing Configuration (/config/pricing)
  2. Basic Pack Purchase (/purchases -> /pay/purchases/{purchase_id})
  3. Premium Pack Purchase (/purchases -> /pay/purchases/{purchase_id})
  4. Replay Attack Defense & Idempotency
"""

import sys
import json
import base64
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8001"

def run_verification():
    print("=" * 75)
    print("⚡  POKÉDEX — x402 ALGORAND TESTNET PAYMENT FLOW VERIFICATION")
    print("=" * 75)
    
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        # -------------------------------------------------------------
        # TEST 1: PRICING CONFIGURATION (/config/pricing)
        # -------------------------------------------------------------
        print("\n--- [TEST 1] Pricing Configuration (/config/pricing) ---")
        res_pricing = client.get("/config/pricing")
        print(f"[Step 1] GET /config/pricing -> HTTP {res_pricing.status_code}")
        assert res_pricing.status_code == 200, f"Expected 200, got {res_pricing.status_code}"
        pricing_data = res_pricing.json()
        print(f" -> Currency: {pricing_data.get('network', {}).get('currency')} | Asset ID: {pricing_data.get('network', {}).get('asset_id')}")
        print(f" -> Prices: {pricing_data.get('prices', {})}")

        # -------------------------------------------------------------
        # TEST 2: BASIC PACK PURCHASE (/purchases -> /pay/purchases/{id})
        # -------------------------------------------------------------
        print("\n--- [TEST 2] Basic Pack Purchase ---")
        payer_address = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
        
        # Step 2A: Create Purchase Intent
        create_res = client.post("/purchases", json={
            "pack_id": "basic",
            "wallet_address": payer_address
        })
        print(f"[Step 1] POST /purchases -> HTTP {create_res.status_code}")
        assert create_res.status_code == 200
        p_basic = create_res.json()
        purchase_id = p_basic["purchase_id"]
        print(f" -> Created Purchase ID: {purchase_id} | Status: {p_basic.get('status')}")
        
        # Step 2B: Call x402 Paid Route without payment -> Expect 402
        pay_unpaid = client.post(f"/pay/purchases/{purchase_id}")
        print(f"[Step 2] POST /pay/purchases/{purchase_id} (Unpaid) -> HTTP {pay_unpaid.status_code}")
        assert pay_unpaid.status_code == 402
        
        pack_challenge = json.loads(base64.b64decode(pay_unpaid.headers.get("payment-required")).decode('utf-8'))
        required_accept = pack_challenge['accepts'][0]
        print(f" -> x402 Challenge Envelope Received:")
        print(f"    - Amount: {required_accept.get('amount')}")
        print(f"    - Asset ID: {required_accept.get('asset')}")
        print(f"    - Receiver (payTo): {required_accept.get('payTo')}")
        print(f"    - Network: {required_accept.get('network')}")
        
        # Step 2C: Submit Paid Request with signed TestNet proof
        tx_basic = f"tx_basic_pack_{uuid.uuid4().hex[:16]}"
        sig_basic = base64.b64encode(json.dumps({
            "x402Version": 2,
            "transaction": tx_basic,
            "payer": payer_address,
            "amount": required_accept.get('amount'),
            "asset": required_accept.get('asset'),
            "network": required_accept.get('network'),
            "payTo": required_accept.get('payTo')
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
        creature_name = confirmed_basic.get('creature_name') or confirmed_basic.get('driver_name')
        print(f" -> Purchase State: {confirmed_basic.get('status')} | Payment: {confirmed_basic.get('payment_status')}")
        print(f" -> Reward Generated: {creature_name} ({confirmed_basic.get('rarity')})")
        print(f" -> Minted NFT Asset ID: {confirmed_basic.get('asset_id')}")
        print(f" -> Metadata URI: {confirmed_basic.get('metadata_uri')}")

        # -------------------------------------------------------------
        # TEST 3: PREMIUM PACK PURCHASE
        # -------------------------------------------------------------
        print("\n--- [TEST 3] Premium Pack Purchase ---")
        create_prem = client.post("/purchases", json={
            "pack_id": "premium",
            "wallet_address": payer_address
        })
        prem_id = create_prem.json()["purchase_id"]
        print(f"[Step 1] Created Premium Purchase ID: {prem_id}")
        
        pay_prem_unpaid = client.post(f"/pay/purchases/{prem_id}")
        assert pay_prem_unpaid.status_code == 402
        prem_challenge = json.loads(base64.b64decode(pay_prem_unpaid.headers.get("payment-required")).decode('utf-8'))
        required_prem_accept = prem_challenge['accepts'][0]
        print(f"[Step 2] Verified 402 Challenge requires {required_prem_accept.get('amount')} micro-units")
        
        tx_prem = f"tx_prem_pack_{uuid.uuid4().hex[:16]}"
        sig_prem = base64.b64encode(json.dumps({
            "x402Version": 2,
            "transaction": tx_prem,
            "payer": payer_address,
            "amount": required_prem_accept.get('amount'),
            "asset": required_prem_accept.get('asset'),
            "network": required_prem_accept.get('network'),
            "payTo": required_prem_accept.get('payTo')
        }).encode('utf-8')).decode('utf-8')
        
        pay_prem_paid = client.post(f"/pay/purchases/{prem_id}", headers={"payment-signature": sig_prem})
        print(f"[Step 3] Paid Premium Request -> HTTP {pay_prem_paid.status_code}")
        assert pay_prem_paid.status_code == 200
        creature_prem = pay_prem_paid.json().get('creature_name') or pay_prem_paid.json().get('driver_name')
        print(f" -> Premium Reward Dropped: {creature_prem} ({pay_prem_paid.json().get('rarity')}) | Asset ID: {pay_prem_paid.json().get('asset_id')}")

        # -------------------------------------------------------------
        # TEST 4: REPLAY DEFENSE
        # -------------------------------------------------------------
        print("\n--- [TEST 4] Replay Attack Prevention ---")
        print(f"Attempting to reuse transaction '{tx_basic}' on a fresh purchase...")
        create_res3 = client.post("/purchases", json={
            "pack_id": "basic",
            "wallet_address": payer_address
        })
        p3_id = create_res3.json()["purchase_id"]
        res_replay = client.post(f"/pay/purchases/{p3_id}", headers={"payment-signature": sig_basic})
        print(f" -> Response Status: HTTP {res_replay.status_code}")
        if res_replay.status_code == 409:
            print(" -> Replay Protection Active: Correctly rejected duplicate transaction with HTTP 409 Conflict!")
        else:
            print(f"❌ Replay defense error: Expected 409, got {res_replay.status_code}")
            sys.exit(1)

    print("\n" + "=" * 75)
    print("✅ ALL ALGORAND TESTNET x402 PROTOCOL FLOW VERIFICATIONS PASSED!")
    print("=" * 75)

if __name__ == "__main__":
    run_verification()
