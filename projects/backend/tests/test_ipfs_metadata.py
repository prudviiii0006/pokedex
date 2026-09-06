"""
AlgoRacers — Session 17: IPFS, Content Addressing & Metadata Integrity Tests
============================================================================
Test Suite:
  1. Cryptographic hashing & avalanche effect
  2. Deterministic CIDv1 base32 generation
  3. Canonical JSON serialization (key order independence)
  4. Metadata schema validation (positive & negative cases)
  5. Manifest integrity & CID consistency
  6. Multi-gateway URL resolution
  7. Tamper detection on modified metadata bytes
  8. NFT minting pipeline ARC-3 URI integration
"""

import sys
import json
import hashlib
from pathlib import Path
import pytest

cand_root = Path(__file__).resolve().parent.parent.parent.parent
root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from blockchain.scripts.cid_utils import compute_cid_v1, canonical_json_bytes, verify_cid
from blockchain.scripts.build_metadata import validate_metadata_schema
from backend.app.services.ipfs_utils import resolve_ipfs_gateway_url, compute_sha256_hex
from backend.app.services.metadata_service import metadata_service

def test_sha256_cryptographic_properties():
    """Test 1: SHA-256 is deterministic and exhibits avalanche effect on one-byte change."""
    t1 = b"AlgoRacers"
    t2 = b"algoracers"

    h1 = hashlib.sha256(t1).hexdigest()
    h2 = hashlib.sha256(t2).hexdigest()

    assert h1 != h2
    assert len(h1) == 64
    # Deterministic check
    assert hashlib.sha256(t1).hexdigest() == h1

def test_deterministic_cidv1_generation():
    """Test 2: Deterministic CIDv1 base32 computation."""
    content = b'{"name":"Velocity One","rarity":"Rare"}'
    cid1 = compute_cid_v1(content)
    cid2 = compute_cid_v1(content)

    assert cid1 == cid2
    assert cid1.startswith("bafkre")
    assert verify_cid(content, cid1) is True

def test_canonical_json_key_order_independence():
    """Test 3: Dictionary key order does not alter canonical serialized bytes or CID."""
    d1 = {"name": "Nova Rush", "rarity": "Epic", "speed": 94}
    d2 = {"speed": 94, "name": "Nova Rush", "rarity": "Epic"}

    b1 = canonical_json_bytes(d1)
    b2 = canonical_json_bytes(d2)

    assert b1 == b2
    assert compute_cid_v1(b1) == compute_cid_v1(b2)

def test_metadata_schema_validation_accepts_valid():
    """Test 4: Valid ARC-3 metadata passes schema validation."""
    valid_meta = {
        "name": "AlgoRacer #001",
        "description": "Velocity One",
        "image": "ipfs://bafkreia3vnoeexpsbnilmcjrjtsd3bomvsbk4h7ufmgnugypcrfqoooj4u",
        "image_mimetype": "image/png",
        "properties": {
            "driver_id": "001",
            "driver_name": "Velocity One",
            "team": "Apex Pulse Racing",
            "generation": "Genesis (Gen 0)",
            "season": "2026"
        },
        "attributes": [
            {"trait_type": "Rarity", "value": "Rare"},
            {"trait_type": "Speed", "value": 91},
            {"trait_type": "Qualifying", "value": 88},
            {"trait_type": "Racecraft", "value": 87},
            {"trait_type": "Overtaking", "value": 85},
            {"trait_type": "Wet Weather", "value": 80},
            {"trait_type": "Consistency", "value": 84}
        ]
    }
    # Should not raise
    validate_metadata_schema(valid_meta, "driver_001.json")

def test_metadata_schema_validation_rejects_invalid_rarity():
    """Test 5: Invalid rarity enum is rejected."""
    invalid_meta = {
        "name": "Hacked Driver",
        "description": "Exploit attempt",
        "image": "ipfs://bafkreihack",
        "image_mimetype": "image/png",
        "properties": {
            "driver_id": "999",
            "driver_name": "Hacked",
            "team": "Dark Team",
            "generation": "Gen 0",
            "season": "2026"
        },
        "attributes": [
            {"trait_type": "Rarity", "value": "SUPER_DUPER_SECRET_RARITY"},
            {"trait_type": "Speed", "value": 90}
        ]
    }
    with pytest.raises(ValueError, match="Invalid or missing Rarity trait"):
        validate_metadata_schema(invalid_meta, "driver_hack.json")

def test_metadata_schema_validation_rejects_out_of_bounds_stats():
    """Test 6: Stat > 100 is rejected."""
    invalid_meta = {
        "name": "Overpowered Driver",
        "description": "Exploit attempt",
        "image": "ipfs://bafkreihack",
        "image_mimetype": "image/png",
        "properties": {
            "driver_id": "999",
            "driver_name": "OP",
            "team": "Team",
            "generation": "Gen 0",
            "season": "2026"
        },
        "attributes": [
            {"trait_type": "Rarity", "value": "Legendary"},
            {"trait_type": "Speed", "value": 150},
            {"trait_type": "Qualifying", "value": 88},
            {"trait_type": "Racecraft", "value": 87},
            {"trait_type": "Overtaking", "value": 85},
            {"trait_type": "Wet Weather", "value": 80},
            {"trait_type": "Consistency", "value": 84}
        ]
    }
    with pytest.raises(ValueError, match="Invalid stat 'Speed'"):
        validate_metadata_schema(invalid_meta, "driver_op.json")

def test_manifest_integrity_and_cids():
    """Test 7: Collection manifest contains all 22 drivers with valid metadata CIDs."""
    manifest_path = root_dir / "blockchain" / "metadata" / "manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert len(manifest["drivers"]) == 22
    for driver_key, d_info in manifest["drivers"].items():
        assert d_info["metadata_cid"].startswith("bafkre")
        assert d_info["image_cid"].startswith("bafkre")
        assert d_info["metadata_uri"].endswith("#arc3")

def test_multi_gateway_url_resolution():
    """Test 8: IPFS URI resolution to HTTP gateways."""
    uri = "ipfs://bafkreia3vnoeexpsbnilmcjrjtsd3bomvsbk4h7ufmgnugypcrfqoooj4u#arc3"
    url = resolve_ipfs_gateway_url(uri)
    assert url.startswith("https://ipfs.io/ipfs/bafkreia3vnoeexpsbnilmcjrjtsd3bomvsbk4h7ufmgnugypcrfqoooj4u")

def test_tamper_detection_on_metadata_bytes():
    """Test 9: Modifying a single character in metadata produces a different CID."""
    original_meta = {"name": "Velocity One", "rarity": "Rare"}
    tampered_meta = {"name": "Velocity Two", "rarity": "Rare"}

    b_orig = canonical_json_bytes(original_meta)
    b_tamp = canonical_json_bytes(tampered_meta)

    cid_orig = compute_cid_v1(b_orig)
    cid_tamp = compute_cid_v1(b_tamp)

    assert cid_orig != cid_tamp
    assert verify_cid(b_tamp, cid_orig) is False

def test_metadata_service_arc3_uri():
    """Test 10: MetadataService returns valid canonical ARC-3 URI for templates."""
    uri = metadata_service.get_canonical_arc3_uri("001")
    assert uri.startswith("ipfs://bafkre")
    assert uri.endswith("#arc3")
