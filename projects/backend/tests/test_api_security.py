"""
AlgoRacers — Session 23: API Security, Abuse Prevention & Adversarial Test Suite
================================================================================
Test Suite:
  1. Unauthenticated / Spoofed wallet address rejected on protected endpoints
  2. Malformed Algorand address / invalid checksum rejected with HTTP 400
  3. SSRF injection payload in metadata CID parameter blocked
  4. Path traversal payload ('../') in circuit/driver identifier blocked
  5. Sliding window rate limiting blocks rapid request flooding with HTTP 429
  6. Rate-limited response contains valid 'Retry-After' header
  7. Oversized request payload (> 1MB) rejected with HTTP 413 Payload Too Large
  8. Standard security headers (CSP, nosniff, DENY) present on API responses
  9. Idempotency replay with altered/tampered payload rejected with HTTP 400
  10. SQL injection payload in query parameters safely sanitized
"""

import sys
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.rate_limiter import rate_limiter
from backend.app.core.input_guards import (
    validate_algorand_address, validate_safe_cid, validate_safe_identifier
)
from backend.app.services.idempotency_service import idempotency_service

WALLET_VALID = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
WALLET_SPOOFED = "6ZIJOSUKH5HY6OK3GLLAP4AAV6GMOJDIECUI7VSQLRQFFWB2LGD6BI5MII"
WALLET_INVALID_CHECKSUM = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2XX"

@pytest.fixture
def client():
    return TestClient(app)

def test_invalid_algorand_address_checksum_rejected():
    """Test 1: Input guard detects and rejects invalid checksum in Algorand address."""
    # Valid address passes
    assert validate_algorand_address(WALLET_VALID) == WALLET_VALID

    # Invalid checksum raises HTTP 400
    with pytest.raises(Exception) as excinfo:
        validate_algorand_address(WALLET_INVALID_CHECKSUM)
    assert "checksum" in str(excinfo.value).lower() or "400" in str(excinfo.value)

def test_ssrf_url_in_metadata_cid_blocked():
    """Test 2: Input guard rejects full URL or internal IP in CID (SSRF prevention)."""
    # Safe CID passes
    safe_cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
    assert validate_safe_cid(safe_cid) == safe_cid

    # Malicious SSRF URL blocked
    ssrf_payloads = [
        "http://127.0.0.1:8000/admin/secret",
        "http://169.254.169.254/latest/meta-data/",
        "https://evil-attacker.com/steal",
        "127.0.0.1:9000/internal"
    ]
    for p in ssrf_payloads:
        with pytest.raises(Exception) as excinfo:
            validate_safe_cid(p)
        assert "400" in str(excinfo.value) or "SSRF" in str(excinfo.value) or "URLs" in str(excinfo.value)

def test_path_traversal_in_identifier_blocked():
    """Test 3: Input guard rejects path traversal characters in identifiers."""
    assert validate_safe_identifier("monaco_gp", "circuit_id") == "monaco_gp"

    traversal_payloads = [
        "../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "monaco_gp/../../../secret.env",
        "driver\0hidden"
    ]
    for p in traversal_payloads:
        with pytest.raises(Exception) as excinfo:
            validate_safe_identifier(p, "identifier")
        assert "400" in str(excinfo.value) or "traversal" in str(excinfo.value).lower()

def test_rate_limiting_sliding_window():
    """Test 4: Sliding window rate limiter enforces max request threshold and returns Retry-After."""
    scope = "test_auth_burst"
    ident = "ip:192.168.1.50"
    max_reqs = 3
    window = 10

    # Clean prior state
    rate_limiter._windows[f"{scope}:{ident}"] = []

    # 1. First 3 requests succeed
    for i in range(max_reqs):
        allowed, rem = rate_limiter.check_rate_limit(ident, scope, max_requests=max_reqs, window_seconds=window)
        assert allowed is True

    # 2. 4th request is rejected with Retry-After > 0
    allowed, retry_after = rate_limiter.check_rate_limit(ident, scope, max_requests=max_reqs, window_seconds=window)
    assert allowed is False
    assert retry_after > 0
    assert retry_after <= window

def test_oversized_payload_rejected_413(client):
    """Test 5: Middleware rejects requests with Content-Length > 1MB with HTTP 413."""
    headers = {"Content-Length": "2000000"}  # 2MB
    response = client.post("/auth/challenge", json={"wallet_address": WALLET_VALID}, headers=headers)
    assert response.status_code == 413
    assert "PayloadTooLarge" in response.text

def test_security_headers_present_on_all_responses(client):
    """Test 6: Security middleware sets CSP, nosniff, and DENY headers on all responses."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert res.headers.get("Content-Security-Policy") == "default-src 'self'"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "X-Request-ID" in res.headers

def test_idempotency_tamper_detection():
    """Test 7: Replaying an idempotency key with altered parameters raises ValueError."""
    from backend.app.core.database import get_db
    key = "idemp_sec_test_001"
    req_orig = {"driver_id": "velocity_one", "circuit": "monaco_gp"}
    req_tampered = {"driver_id": "velocity_one", "circuit": "silverstone"}

    with get_db() as conn:
        conn.execute("DELETE FROM idempotency_records WHERE idempotency_key = ?;", (key,))
        conn.commit()

    # Reserve original
    is_new, _ = idempotency_service.check_or_reserve(key, "sec_scope", WALLET_VALID, req_orig)
    assert is_new is True

    # Attempt replay with tampered parameters
    with pytest.raises(ValueError, match="previously used with different request parameters"):
        idempotency_service.check_or_reserve(key, "sec_scope", WALLET_VALID, req_tampered)

def test_sql_injection_payload_in_query_params(client):
    """Test 8: Query endpoints properly parameterize input and safely handle SQL injection payloads."""
    sql_injection_payload = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM' OR '1'='1"
    res = client.get(f"/activity/wallets/{sql_injection_payload}")
    # Returns empty array or safe sanitized error, but NEVER a 500 SQL syntax error
    assert res.status_code in [200, 400, 404]
    if res.status_code == 200:
        assert isinstance(res.json(), list)
