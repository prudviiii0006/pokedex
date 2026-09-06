"""
AlgoRacers — Session 18: Merkle Trees & Dataset Commitments Test Suite
======================================================================
Test Suite:
  1. Leaf & node hashing domain separation
  2. Canonical key sorting determinism
  3. Duplicate record key rejection
  4. Odd leaf count promotion
  5. Single leaf tree handling
  6. Empty tree handling
  7. Valid proof generation and verification
  8. Tampered leaf detection
  9. Tampered sibling hash detection
  10. Flipped sibling direction detection
  11. 1,000-leaf scalability benchmark
  12. Test vectors consistency
  13. REST API proof retrieval and verification endpoints
"""

import sys
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.crypto.merkle import MerkleTree, hash_leaf, hash_node, verify_merkle_proof
from backend.app.services.collection_registry_service import collection_registry_service

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_4_driver_records():
    return [
        {"driver_id": "001", "name": "Velocity One", "rarity": "Rare"},
        {"driver_id": "002", "name": "Nova Rush", "rarity": "Epic"},
        {"driver_id": "003", "name": "Apex Storm", "rarity": "Legendary"},
        {"driver_id": "004", "name": "Turbo Vale", "rarity": "Common"}
    ]

def test_merkle_hashing_domain_separation():
    """Test 1: Leaf and node hashes utilize distinct domain prefixes."""
    rec = {"driver_id": "001", "name": "Velocity One"}
    l_hash = hash_leaf(rec)
    n_hash = hash_node(l_hash, l_hash)

    assert len(l_hash) == 32
    assert len(n_hash) == 32
    assert l_hash != n_hash

def test_canonical_sorting_and_determinism(sample_4_driver_records):
    """Test 2: Input order does not change Merkle root due to canonical key sorting."""
    records_shuffled = list(reversed(sample_4_driver_records))

    tree1 = MerkleTree(sample_4_driver_records, key_field="driver_id")
    tree2 = MerkleTree(records_shuffled, key_field="driver_id")

    assert tree1.root_hex == tree2.root_hex

def test_duplicate_key_rejection(sample_4_driver_records):
    """Test 3: Duplicate driver IDs are rejected with ValueError."""
    dupe_records = sample_4_driver_records + [{"driver_id": "001", "name": "Dupe"}]
    with pytest.raises(ValueError, match="Duplicate record key detected"):
        MerkleTree(dupe_records, key_field="driver_id")

def test_odd_leaf_count_promotion():
    """Test 4: Odd number of leaves (5) promotes unpaired node to next level cleanly."""
    records_5 = [
        {"driver_id": "001", "val": 1},
        {"driver_id": "002", "val": 2},
        {"driver_id": "003", "val": 3},
        {"driver_id": "004", "val": 4},
        {"driver_id": "005", "val": 5}
    ]
    tree = MerkleTree(records_5, key_field="driver_id")
    assert tree.root_hex is not None
    assert len(tree.root_hex) == 64

    # Verify all 5 proofs
    for r in records_5:
        proof = tree.generate_proof(r["driver_id"])
        assert verify_merkle_proof(r, proof, tree.root_hex) is True

def test_single_leaf_tree():
    """Test 5: Single-leaf tree root equals leaf hash."""
    rec = {"driver_id": "001", "name": "Solo Driver"}
    tree = MerkleTree([rec], key_field="driver_id")
    expected_leaf_hash = hash_leaf(rec).hex()

    assert tree.root_hex == expected_leaf_hash
    proof = tree.generate_proof("001")
    assert proof == []
    assert verify_merkle_proof(rec, proof, tree.root_hex) is True

def test_empty_tree_handling():
    """Test 6: Empty dataset returns 32 zero bytes."""
    tree = MerkleTree([], key_field="driver_id")
    assert tree.root_hex == "00" * 32

def test_valid_proof_verification_passes(sample_4_driver_records):
    """Test 7: Valid membership proof verifies 100% against root."""
    tree = MerkleTree(sample_4_driver_records, key_field="driver_id")
    target = sample_4_driver_records[2] # 003

    proof = tree.generate_proof("003")
    assert len(proof) == 2
    assert verify_merkle_proof(target, proof, tree.root_hex) is True

def test_tampered_leaf_fails(sample_4_driver_records):
    """Test 8: Altering a field in the record causes proof verification to fail."""
    tree = MerkleTree(sample_4_driver_records, key_field="driver_id")
    target = sample_4_driver_records[0] # 001
    proof = tree.generate_proof("001")

    tampered_target = dict(target)
    tampered_target["rarity"] = "Legendary" # Modified field

    assert verify_merkle_proof(tampered_target, proof, tree.root_hex) is False

def test_tampered_sibling_hash_fails(sample_4_driver_records):
    """Test 9: Modifying a sibling hash in the proof causes verification to fail."""
    tree = MerkleTree(sample_4_driver_records, key_field="driver_id")
    target = sample_4_driver_records[0]
    proof = tree.generate_proof("001")

    tampered_proof = [dict(p) for p in proof]
    orig_h = tampered_proof[0]["hash"]
    tampered_proof[0]["hash"] = ("0" if orig_h[0] != "0" else "1") + orig_h[1:]

    assert verify_merkle_proof(target, tampered_proof, tree.root_hex) is False

def test_flipped_sibling_position_fails(sample_4_driver_records):
    """Test 10: Flipping sibling direction (left -> right) causes verification to fail."""
    tree = MerkleTree(sample_4_driver_records, key_field="driver_id")
    target = sample_4_driver_records[0]
    proof = tree.generate_proof("001")

    tampered_proof = [dict(p) for p in proof]
    tampered_proof[0]["position"] = "left" if tampered_proof[0]["position"] == "right" else "right"

    assert verify_merkle_proof(target, tampered_proof, tree.root_hex) is False

def test_1000_leaf_scale_benchmark():
    """Test 11: 1,000-leaf dataset builds rapidly and produces O(log n) ~10-step proofs."""
    records_1000 = [{"driver_id": f"D_{i:04d}", "val": i * 10} for i in range(1000)]
    tree = MerkleTree(records_1000, key_field="driver_id")

    proof_sample = tree.generate_proof("D_0542")
    assert proof_sample is not None
    assert len(proof_sample) <= 11  # log2(1000) ~ 9.96
    assert verify_merkle_proof(records_1000[542], proof_sample, tree.root_hex) is True

def test_cross_language_test_vectors():
    """Test 12: Exported test vectors in merkle-test-vectors.json verify correctly."""
    v_path = root_dir / "docs" / "merkle-test-vectors.json"
    assert v_path.exists()

    with open(v_path, "r", encoding="utf-8") as f:
        vec_data = json.load(f)

    sample = vec_data["sample_proof_driver_001"]
    assert verify_merkle_proof(sample["record"], sample["proof"], sample["expected_root"]) is True

def test_rest_api_proof_and_verify_endpoints(client):
    """Test 13: REST endpoints GET /collections/.../proof and POST /collections/verify."""
    # 1. Retrieve proof for Driver #001
    res = client.get("/collections/drivers/1/drivers/001/proof")
    assert res.status_code == 200
    p_data = res.json()
    assert "proof" in p_data
    assert "root" in p_data
    assert p_data["driver_id"] == "001"

    # 2. Verify via POST endpoint
    verify_res = client.post("/collections/verify", json={
        "record": p_data["record"],
        "proof": p_data["proof"],
        "root": p_data["root"]
    })
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["verified"] is True
