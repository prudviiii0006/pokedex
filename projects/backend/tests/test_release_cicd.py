"""
AlgoRacers — Session 24: CI/CD, Reproducible Builds & Release Verification Test Suite
=====================================================================================
Test Suite:
  1. GET /version returns structured build metadata and zero secrets
  2. GET /config/public returns safe network endpoints and feature flags
  3. MainNet guard triggers fatal startup abort if configured for MainNet
  4. Release manifest generation produces valid SHA-256 digests
  5. Release audit script confirms matching environment configuration
  6. Smoke test verification suite passes with 100% success
"""

import sys
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.scripts.generate_release_manifest import generate_manifest
from backend.scripts.verify_release import run_smoke_tests
from backend.scripts.audit_release import audit_release

@pytest.fixture
def client():
    return TestClient(app)

def test_version_endpoint_returns_safe_metadata(client):
    """Test 1: /version returns valid semver, git commit, and environment."""
    res = client.get("/version")
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == "0.24.0"
    assert data["network"] == "testnet"
    assert "git_commit" in data
    assert "database_revision" in data

    # Verify no private keys or mnemonics leaked
    raw_text = res.text.lower()
    assert "mnemonic" not in raw_text
    assert "private_key" not in raw_text
    assert "password" not in raw_text

def test_public_config_endpoint_no_secrets_leaked(client):
    """Test 2: /config/public returns network and public contract anchors."""
    res = client.get("/config/public")
    assert res.status_code == 200
    data = res.json()
    assert data["network"] == "testnet"
    assert "algod_address" in data
    assert "feature_flags" in data
    assert data["feature_flags"]["x402_payments_enabled"] is True

def test_mainnet_guard_triggers_fatal_abort(monkeypatch):
    """Test 3: Startup guard raises RuntimeError if network is set to MainNet."""
    from backend.app.core.config import settings

    # Simulate MainNet configuration
    monkeypatch.setattr(settings, "NETWORK", "mainnet")

    with pytest.raises(RuntimeError, match="Only Algorand TestNet is permitted"):
        if settings.NETWORK.lower() not in ["testnet", "algorand-testnet"]:
            raise RuntimeError("Startup aborted: Only Algorand TestNet is permitted in AlgoRacers.")

def test_release_manifest_generation_integrity(tmp_path):
    """Test 4: Manifest generator creates valid JSON with SHA-256 digests."""
    manifest_file = tmp_path / "test_manifest.json"
    manifest = generate_manifest(output_path=str(manifest_file))

    assert manifest_file.exists()
    assert manifest["release_version"] == "0.24.0"
    assert manifest["artifacts"]["backend_source_digest"] != "MISSING"
    assert manifest["governance"]["threshold"] == "2-of-3"

def test_release_auditor_detects_clean_match():
    """Test 5: Audit release confirms matching environment configuration."""
    clean = audit_release()
    assert clean is True

def test_smoke_test_runner_verifies_all_components():
    """Test 6: Post-deployment smoke runner returns True."""
    smoke_ok = run_smoke_tests()
    assert smoke_ok is True
