"""
AlgoRacers — Session 7: x402 Fundamentals
Script: demo_x402_client.py
=========================================
Demonstrates the client-side x402 challenge-response protocol:
  1. Client sends GET /premium-analysis -> Receives HTTP 402 Payment Required
  2. Client parses payment requirements (Amount, Asset, Recipient)
  3. Client generates mock payment authorization payload
  4. Client retries request with `X-402-Payment-Proof` header
  5. Server validates proof and returns HTTP 200 OK with premium telemetry
  6. Client attempts replay attack with same nonce -> Server rejects with 409 Conflict!
"""

import json
import uuid
import sys
import httpx

API_BASE_URL = "http://localhost:8000"
if len(sys.argv) > 1:
    API_BASE_URL = sys.argv[1]

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — x402 CLIENT CHALLENGE-RESPONSE PROTOCOL DEMO")
    print("=" * 65)

    client = httpx.Client(base_url=API_BASE_URL)

    # -------------------------------------------------------------
    # STEP 1: INITIAL UNPAID REQUEST
    # -------------------------------------------------------------
    print("\n[Step 1: Sending Initial Unpaid GET /premium-analysis]...")
    res = client.get("/premium-analysis")

    print(f"   HTTP Status Code: {res.status_code} {res.reason_phrase}")
    if res.status_code != 402:
        print(f"❌ Expected 402 Payment Required, received: {res.status_code}")
        return

    # -------------------------------------------------------------
    # STEP 2: PARSE PAYMENT REQUIREMENTS
    # -------------------------------------------------------------
    print("\n[Step 2: Parsing x402 Payment Requirements from Server]...")
    challenge_data = res.json()
    detail = challenge_data.get("detail", challenge_data)
    reqs = detail.get("payment_requirements", {})

    amount = reqs.get("amount")
    asset = reqs.get("asset")
    recipient = reqs.get("recipient")
    resource = reqs.get("resource")
    protocol = detail.get("protocol")

    print(f"   • Protocol:       {protocol}")
    print(f"   • Protected URI:  {resource}")
    print(f"   • Required Price: {amount} {asset}")
    print(f"   • Recipient:      {recipient}")
    print(f"   • Mode:           {detail.get('mode')}")

    # -------------------------------------------------------------
    # STEP 3: CONSTRUCT MOCK PAYMENT PROOF
    # -------------------------------------------------------------
    print("\n[Step 3: Constructing Mock Payment Proof Payload]...")
    nonce = f"tx_mock_{uuid.uuid4().hex[:12]}"
    proof_payload = {
        "client_address": "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
        "amount": amount,
        "asset": asset,
        "nonce": nonce,
        "signature": f"mock_sig_ed25519_{uuid.uuid4().hex[:16]}"
    }
    proof_json = json.dumps(proof_payload)
    print(f"   • Payer Address:  {proof_payload['client_address']}")
    print(f"   • Nonce / TxID:   {nonce}")
    print(f"   • Header Format:  X-402-Payment-Proof")

    # -------------------------------------------------------------
    # STEP 4: RETRY REQUEST WITH PAYMENT PROOF HEADER
    # -------------------------------------------------------------
    print("\n[Step 4: Retrying GET /premium-analysis with Payment Proof Header]...")
    headers = {"X-402-Payment-Proof": proof_json}
    res_paid = client.get("/premium-analysis", headers=headers)

    print(f"   HTTP Status Code: {res_paid.status_code} {res_paid.reason_phrase}")
    if res_paid.status_code == 200:
        data = res_paid.json()
        print("\n🎉 ACCESS GRANTED! 200 OK — Premium Telemetry Unlocked:")
        print(f"   • Title:      {data.get('title')}")
        print(f"   • Circuit:    {data.get('circuit')}")
        print(f"   • Conditions: {data.get('track_conditions')}")
        print(f"   • AI Insight: {data.get('tactical_ai_insights')}")
        print("\n   [Verified Payment Receipt issued by Server]:")
        for k, v in data.get("payment_receipt", {}).items():
            print(f"     ↳ {k}: {v}")
    else:
        print(f"❌ Failed to unlock: {res_paid.text}")
        return

    # -------------------------------------------------------------
    # STEP 5: DEMONSTRATE REPLAY ATTACK REJECTION
    # -------------------------------------------------------------
    print("\n[Step 5: Testing Replay Attack (Submitting Same Proof Twice)]...")
    res_replay = client.get("/premium-analysis", headers=headers)
    print(f"   HTTP Status Code: {res_replay.status_code} {res_replay.reason_phrase}")
    print(f"   Server Response:  {res_replay.json().get('detail')}")
    if res_replay.status_code == 409:
        print("   ✅ Replay attack successfully blocked by Payment Gate!")
    print("=" * 65)

if __name__ == "__main__":
    main()
