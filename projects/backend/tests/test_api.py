"""
AlgoRacers — Session 6: FastAPI Backend Integration Test Suite
=============================================================
Tests:
  1. GET /health returns 200 OK and service metadata
  2. GET /packs returns list of available packs
  3. GET /packs/basic returns single pack schema
  4. GET /packs/invalid returns 404 Not Found
  5. POST /packs/basic/simulate returns valid Driver reward
  6. POST /packs/premium/simulate returns valid Driver reward
  7. POST /packs/invalid/simulate returns 404 Not Found
  8. Versioned route /api/v1/packs mirrors root packs
  9. OpenAPI schema is generated and accessible
  10. Invalid request body returns 422 Unprocessable Entity
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_health(client):
    """Test 1: Health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "algoracers-api"
    assert "version" in data
    assert data["network"] == "testnet"
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers

def test_get_readiness_probe(client):
    """Test: Readiness probe verifies database and TestNet guardrails."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert data["testnet_guard"] == "active"
    assert data["drivers_loaded"] >= 10
    assert data["circuits_loaded"] >= 3

def test_get_packs(client):
    """Test 2: GET /packs returns all pack configs."""
    response = client.get("/packs")
    assert response.status_code == 200
    packs = response.json()
    assert isinstance(packs, list)
    assert len(packs) >= 2
    pack_ids = [p["id"] for p in packs]
    assert "basic" in pack_ids
    assert "premium" in pack_ids

def test_get_single_pack(client):
    """Test 3: GET /packs/basic returns specific pack configuration."""
    response = client.get("/packs/basic")
    assert response.status_code == 200
    pack = response.json()
    assert pack["id"] == "basic"
    assert pack["price"] == 2.0
    assert pack["currency"] == "USDC"
    assert "Common" in pack["rarities"]
    assert pack["rarities"]["Common"] == 65.0

def test_get_invalid_pack_404(client):
    """Test 4: Requesting unknown pack returns 404 Not Found."""
    response = client.get("/packs/hyper_turbo_999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_post_simulate_basic(client):
    """Test 5: POST /packs/basic/simulate returns simulated reward."""
    response = client.post("/packs/basic/simulate", json={"wallet_address": "TEST_ADDR"})
    assert response.status_code == 200
    reward = response.json()
    assert "reward_id" in reward
    assert reward["pack_id"] == "basic"
    assert reward["rarity"] in ["Common", "Rare", "Epic", "Legendary"]
    assert reward["is_simulation"] is True
    assert "driver" in reward
    assert reward["driver"]["id"] != ""
    assert "Speed" in reward["driver"]["stats"]

def test_post_simulate_premium(client):
    """Test 6: POST /packs/premium/simulate returns simulated reward."""
    response = client.post("/packs/premium/simulate")
    assert response.status_code == 200
    reward = response.json()
    assert reward["pack_id"] == "premium"
    assert reward["rarity"] in ["Common", "Rare", "Epic", "Legendary"]

def test_post_simulate_invalid_pack_404(client):
    """Test 7: Simulating unknown pack returns 404."""
    response = client.post("/packs/non_existent_pack/simulate")
    assert response.status_code == 404

def test_api_v1_versioned_routes(client):
    """Test 8: Versioned /api/v1/packs endpoint works identically."""
    response = client.get("/api/v1/packs")
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_openapi_schema_generated(client):
    """Test 9: OpenAPI schema JSON is served and contains paths."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/health" in schema["paths"]
    assert "/packs" in schema["paths"]
    assert "/packs/{pack_id}/simulate" in schema["paths"]

def test_invalid_request_body_validation(client):
    """Test 10: Malformed input returns 422 Unprocessable Entity."""
    # Sending wrong type (integer instead of string for wallet_address dict)
    response = client.post("/packs/basic/simulate", json={"wallet_address": {"invalid": 123}})
    assert response.status_code == 422
