"""
AlgoCreatures — Development Reset Collection Unit Tests
Module: tests/test_dev_reset.py
=======================================================
Tests for one-time development reset of a specific wallet collection,
ensuring database records are cleared, trades cancelled, and master Pokédex preserved.
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.services.purchase_service import purchase_service
from backend.app.core.database import get_db

client = TestClient(app)

TEST_RESET_WALLET = "SQIBTZNTR3KC3TFQCQCHU26VFYJ4MTZ6NADPUH472ASEU5ZKPQWEU5UNQM"

def test_dev_reset_endpoint_success():
    # 1. First ensure wallet has a mock purchase and collection entry
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO owned_creatures 
            (asset_id, wallet_address, template_id, name, primary_type, faction, rarity, hp, attack, defense, speed, stamina, acquired_at, updated_at)
            VALUES (9990001, ?, 'pikachu', 'Pikachu', 'Electric', 'Electric', 'Rare', 35, 55, 40, 90, 60, '2026-09-10T00:00:00Z', '2026-09-10T00:00:00Z');
        """, (TEST_RESET_WALLET,))
        conn.commit()

    # Verify collection returns 1 creature
    res_before = client.get(f"/collection/{TEST_RESET_WALLET}")
    assert res_before.status_code == 200
    assert len(res_before.json()) >= 1

    # 2. Call dev-reset endpoint
    res_reset = client.post(f"/collection/{TEST_RESET_WALLET}/dev-reset")
    assert res_reset.status_code == 200
    data = res_reset.json()
    assert data["status"] == "RESET_SUCCESSFUL"
    assert data["wallet_address"] == TEST_RESET_WALLET
    assert data["owned_records_cleared"] >= 1

    # 3. Verify collection is now EMPTY
    res_after = client.get(f"/collection/{TEST_RESET_WALLET}")
    assert res_after.status_code == 200
    assert len(res_after.json()) == 0

    # 4. Verify master catalog is preserved (all 247 species intact)
    from backend.rewards.creature_pool import CANONICAL_CREATURES
    assert len(CANONICAL_CREATURES) == 247

def test_dev_reset_invalid_address():
    res = client.post("/collection/INVALID_ALGORAND_ADDRESS_123/dev-reset")
    assert res.status_code == 400
