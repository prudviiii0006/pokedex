#!/usr/bin/env python3
"""
AlgoRacers — Session 16: Profile Rebuild & Audit CLI Tool
Module: backend/scripts/rebuild_player_profile.py
========================================================
Usage: python rebuild_player_profile.py <wallet_address> [api_url]
"""

import sys
try:
    import httpx
except ImportError:
    print("Error: 'httpx' is required. Run 'pip install httpx'.")
    sys.exit(1)

def rebuild_profile(wallet_address: str, api_url: str = "http://localhost:8000"):
    print("=" * 75)
    print(f"🏎️  ALGORACERS — PROFILE REBUILD & LEDGER AUDIT")
    print(f"👤 Target Wallet: {wallet_address}")
    print("=" * 75)

    try:
        res = httpx.post(f"{api_url}/profile/reconcile", json={"wallet_address": wallet_address}, timeout=10.0)
        if res.status_code != 200:
            print(f"❌ API Error: HTTP {res.status_code} - {res.text}")
            sys.exit(1)

        data = res.json()
        print(f"📊 RECONCILIATION REPORT:")
        print(f"  • Drift Detected:          {data.get('drift_detected')}")
        print(f"  • Cached XP:               {data.get('cached_xp')} XP")
        print(f"  • Recalculated Ledger XP:  {data.get('recalculated_xp')} XP (Level {data.get('recalculated_level')})")
        print(f"  • Competitive Reputation:  {data.get('recalculated_reputation')} Rating")
        print(f"  • Unlocked Achievements:   {data.get('achievements_unlocked_count')}")
        print(f"  • Status:                  {data.get('message')}")
        print("=" * 75)
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rebuild_player_profile.py <wallet_address> [api_url]")
        sys.exit(1)

    target_wallet = sys.argv[1]
    target_api = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    rebuild_profile(target_wallet, target_api)
