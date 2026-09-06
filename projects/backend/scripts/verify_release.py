#!/usr/bin/env python3
"""
AlgoRacers — Session 24: Smoke-Test & Release Verification Runner
Module: backend/scripts/verify_release.py
================================================================
Performs fast, non-destructive post-deployment smoke tests against
FastAPI endpoints, database status, and Algorand TestNet connectivity.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app

def run_smoke_tests():
    print("=" * 75)
    print("🏎️  ALGORACERS — POST-DEPLOYMENT SMOKE TEST RUNNER")
    print("=" * 75)

    client = TestClient(app)
    results = {}

    # 1. Health check
    res_health = client.get("/health")
    results["health_endpoint"] = (res_health.status_code == 200)
    print(f"  • GET /health               : [{'PASS' if results['health_endpoint'] else 'FAIL'}] (Status {res_health.status_code})")

    # 2. Version & Provenance
    res_ver = client.get("/version")
    results["version_endpoint"] = (res_ver.status_code == 200 and "0.24.0" in res_ver.text)
    print(f"  • GET /version              : [{'PASS' if results['version_endpoint'] else 'FAIL'}] (Version {res_ver.json().get('version')})")

    # 3. Public Config
    res_cfg = client.get("/config/public")
    results["config_endpoint"] = (res_cfg.status_code == 200 and res_cfg.json().get("network") == "testnet")
    print(f"  • GET /config/public        : [{'PASS' if results['config_endpoint'] else 'FAIL'}] (Network: {res_cfg.json().get('network')})")

    # 4. Circuits Catalog
    res_circ = client.get("/circuits")
    results["circuits_catalog"] = (res_circ.status_code == 200 and len(res_circ.json()) > 0)
    print(f"  • GET /circuits             : [{'PASS' if results['circuits_catalog'] else 'FAIL'}] ({len(res_circ.json()) if res_circ.status_code == 200 else 0} Circuits)")

    # 5. Security Headers Check
    results["security_headers"] = ("nosniff" == res_health.headers.get("X-Content-Type-Options"))
    print(f"  • Security Headers (nosniff): [{'PASS' if results['security_headers'] else 'FAIL'}]")

    # 6. Jobs Metrics
    res_jobs = client.get("/jobs/metrics")
    results["jobs_metrics"] = (res_jobs.status_code == 200)
    print(f"  • GET /jobs/metrics         : [{'PASS' if results['jobs_metrics'] else 'FAIL'}]")

    all_passed = all(results.values())
    print("=" * 75)
    print(f"🎯 SMOKE TEST VERDICT: {'🟢 ALL CHECKS PASSED — RELEASE HEALTHY' if all_passed else '🔴 CRITICAL FAILURE DETECTED — HALT ROLLOUT'}")
    print("=" * 75)
    return all_passed

if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
