#!/usr/bin/env python3
"""
AlgoRacers — Session 24: Release Audit & Configuration Drift Detector
Module: backend/scripts/audit_release.py
=====================================================================
Compares running server version & configuration against the official
release manifest to detect configuration drift or tampered artifacts.
"""

import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "release-manifest.json").exists() else Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app

def audit_release(manifest_path: str = None):
    print("=" * 75)
    print("🔍 ALGORACERS — RELEASE AUDIT & DRIFT DETECTOR")
    print("=" * 75)

    m_file = Path(manifest_path) if manifest_path else root_dir / "release-manifest.json"
    if not m_file.exists():
        print(f"❌ Release manifest not found at: {m_file}")
        sys.exit(1)

    with open(m_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    client = TestClient(app)
    ver_res = client.get("/version").json()

    drifts = []

    # 1. Compare Release Version
    if ver_res.get("version") == manifest.get("release_version"):
        print(f"  • Release Version:        MATCH ({ver_res.get('version')})")
    else:
        print(f"  • Release Version:        DRIFT (Server: {ver_res.get('version')} vs Manifest: {manifest.get('release_version')})")
        drifts.append("version_mismatch")

    # 2. Compare Git Commit
    if ver_res.get("git_commit") == manifest.get("git_commit"):
        print(f"  • Git Commit:             MATCH ({ver_res.get('git_commit')})")
    else:
        print(f"  • Git Commit:             DRIFT (Server: {ver_res.get('git_commit')} vs Manifest: {manifest.get('git_commit')})")
        drifts.append("git_commit_mismatch")

    # 3. Compare Network Target
    if ver_res.get("network") == manifest.get("network_target"):
        print(f"  • Network Target:         MATCH ({ver_res.get('network')})")
    else:
        print(f"  • Network Target:         DRIFT (Server: {ver_res.get('network')} vs Manifest: {manifest.get('network_target')})")
        drifts.append("network_mismatch")

    # 4. Compare DB Revision
    if ver_res.get("database_revision") == manifest.get("database_revision"):
        print(f"  • Database Revision:      MATCH ({ver_res.get('database_revision')})")
    else:
        print(f"  • Database Revision:      DRIFT (Server: {ver_res.get('database_revision')} vs Manifest: {manifest.get('database_revision')})")
        drifts.append("db_revision_mismatch")

    print("=" * 75)
    if not drifts:
        print("🟢 AUDIT RESULT: ZERO CONFIGURATION DRIFT — ENVIRONMENT VALIDATED")
    else:
        print(f"🔴 AUDIT RESULT: {len(drifts)} CONFIGURATION DRIFT(S) DETECTED")
    print("=" * 75)
    return len(drifts) == 0

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    success = audit_release(path)
    sys.exit(0 if success else 1)
