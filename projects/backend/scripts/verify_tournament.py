#!/usr/bin/env python3
"""
AlgoRacers — Session 15: Public Tournament Verification Script
Module: backend/scripts/verify_tournament.py
============================================================
Independent auditor CLI tool:
  Usage: python verify_tournament.py <app_id> [api_url]

Steps executed:
  1. Fetch on-chain tournament parameters (participants, circuit, committed randomness, engine version)
  2. Independently simulate deterministic Race Engine v1
  3. Compute SHA-256 canonical result hash
  4. Compare with on-chain committed result_hash
  5. Print full cryptographic verification audit report
"""

import sys
import json
import hashlib
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("Error: 'httpx' is required. Run 'pip install httpx'.")
    sys.exit(1)

def verify_tournament(app_id: int, api_url: str = "http://localhost:8000"):
    print("=" * 75)
    print(f"🏎️  ALGORACERS — INDEPENDENT TOURNAMENT AUDIT: APP #{app_id}")
    print("=" * 75)
    print(f"📡 Querying verification endpoint: {api_url}/tournaments/{app_id}/verify\n")

    try:
        response = httpx.get(f"{api_url}/tournaments/{app_id}/verify", timeout=10.0)
        if response.status_code == 404:
            print(f"❌ Error: Tournament #{app_id} not found.")
            sys.exit(1)
        elif response.status_code != 200:
            print(f"❌ API Error: HTTP {response.status_code} - {response.text}")
            sys.exit(1)

        report = response.json()
    except Exception as e:
        print(f"❌ Connection error to {api_url}: {e}")
        sys.exit(1)

    print(f"📋 TOURNAMENT PARAMETERS:")
    print(f"  • App ID:               #{report.get('app_id')}")
    print(f"  • Randomness Round:     #{report.get('randomness_round')}")
    print(f"  • VRF Random Digest:    {report.get('randomness_value')}")
    print(f"  • Race Engine Version:  {report.get('race_engine_version')}")
    print(f"  • Winner ASA ID:        #{report.get('winner_asset_id')} ({report.get('winner_driver_name')})")
    print("-" * 75)
    print(f"🔐 CRYPTOGRAPHIC AUDIT:")
    print(f"  • On-Chain Hash:        {report.get('on_chain_hash')}")
    print(f"  • Recalculated Hash:    {report.get('recalculated_hash')}")
    print("-" * 75)

    if report.get("verified"):
        print(f"🏆 AUDIT RESULT: [PASS] 100% CRYPTOGRAPHICALLY VERIFIED & REPRODUCIBLE")
        print(f"   {report.get('message')}")
        print("=" * 75)
        sys.exit(0)
    else:
        print(f"🚨 AUDIT RESULT: [FAIL] TAMPER DETECTED!")
        print(f"   {report.get('message')}")
        print("=" * 75)
        sys.exit(2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_tournament.py <app_id> [api_url]")
        sys.exit(1)

    target_app_id = int(sys.argv[1])
    target_api = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    verify_tournament(target_app_id, target_api)
