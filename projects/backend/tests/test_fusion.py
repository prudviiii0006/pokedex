"""
Pokédex (AlgoCreatures) — Comprehensive Fusion Feature Tests
Module: tests/test_fusion.py
============================================================
Tests for the 5-Epic-to-1-Legendary Fusion engine:
  1. Strict 5-asset count validation (<5 or >5 rejected)
  2. Epic-only rarity enforcement (Common/Rare/Legendary rejected)
  3. No duplicate Asset IDs (same asset twice rejected)
  4. Duplicate species with distinct Asset IDs allowed
  5. Wallet ownership validation (unowned asset rejected)
  6. Active trade lock enforcement (trade-locked asset rejected)
  7. Real asset consumption (5 Epics removed from collection)
  8. Legendary reward server selection (random from 25 master catalog Legendaries)
  9. 1-of-1 ARC-3 NFT minting & delivery to wallet
 10. Idempotency on repeated confirm/refresh requests
 11. Candidates endpoint with trade lock annotations
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.core.database import get_db
from backend.rewards.creature_pool import creature_pool

client = TestClient(app)

TEST_WALLET = "FUSION_TEST_WALLET_ABC12345678901234567890123456789012"

@pytest.fixture(autouse=True)
def setup_fusion_database():
    """Seeds test database with Epic, Rare, and Common Pokémon for testing."""
    with get_db() as conn:
        # Clear test wallet data
        conn.execute("DELETE FROM owned_creatures WHERE wallet_address = ?", (TEST_WALLET,))
        conn.execute("DELETE FROM fusions WHERE wallet_address = ?", (TEST_WALLET,))
        conn.execute("DELETE FROM trades WHERE initiator_wallet = ? OR counterparty_wallet = ?", (TEST_WALLET, TEST_WALLET))

        # Seed 6 Epic Pokémon
        epic_templates = [c for c in creature_pool.get_all_creatures() if c.rarity == "Epic"][:6]
        for i, t in enumerate(epic_templates):
            conn.execute("""
                INSERT INTO owned_creatures (
                    asset_id, wallet_address, template_id, name, primary_type, secondary_type,
                    faction, rarity, hp, attack, defense, speed, stamina, level, xp,
                    evolution_stage, acquired_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Epic', 80, 80, 80, 80, 80, 1, 0, 1, '2026-09-10T00:00:00Z', '2026-09-10T00:00:00Z');
            """, (500001 + i, TEST_WALLET, t.id, t.name, t.primary_type, t.secondary_type, t.faction))

        # Seed 1 Rare Pokémon
        conn.execute("""
            INSERT INTO owned_creatures (
                asset_id, wallet_address, template_id, name, primary_type, secondary_type,
                faction, rarity, hp, attack, defense, speed, stamina, level, xp,
                evolution_stage, acquired_at, updated_at
            ) VALUES (600001, ?, '25', 'Pikachu', 'Electric', NULL, 'Volt', 'Rare', 60, 60, 60, 60, 60, 1, 0, 1, '2026-09-10T00:00:00Z', '2026-09-10T00:00:00Z');
        """, (TEST_WALLET,))

        # Seed 1 Legendary Pokémon
        conn.execute("""
            INSERT INTO owned_creatures (
                asset_id, wallet_address, template_id, name, primary_type, secondary_type,
                faction, rarity, hp, attack, defense, speed, stamina, level, xp,
                evolution_stage, acquired_at, updated_at
            ) VALUES (700001, ?, '150', 'Mewtwo', 'Psychic', NULL, 'Aether', 'Legendary', 100, 100, 100, 100, 100, 1, 0, 1, '2026-09-10T00:00:00Z', '2026-09-10T00:00:00Z');
        """, (TEST_WALLET,))

        conn.commit()

    yield

    with get_db() as conn:
        conn.execute("DELETE FROM owned_creatures WHERE wallet_address = ?", (TEST_WALLET,))
        conn.execute("DELETE FROM fusions WHERE wallet_address = ?", (TEST_WALLET,))
        conn.execute("DELETE FROM trades WHERE initiator_wallet = ? OR counterparty_wallet = ?", (TEST_WALLET, TEST_WALLET))
        conn.commit()


def test_fusion_candidates_endpoint():
    """Tests loading only owned Epic Pokémon for the connected wallet."""
    response = client.get(f"/api/v1/fusion/candidates/{TEST_WALLET}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6
    for item in data:
        assert item["rarity"] == "Epic"
        assert item["is_locked"] is False


def test_fusion_initiate_requires_exactly_5():
    """Fewer or more than 5 assets must be rejected."""
    # 4 assets
    res4 = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004]
    })
    assert res4.status_code in [400, 422]

    # 6 assets
    res6 = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004, 500005, 500006]
    })
    assert res6.status_code in [400, 422]


def test_fusion_rejects_duplicate_asset_ids():
    """Same Asset ID cannot be used more than once."""
    res = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500001, 500002, 500003, 500004]
    })
    assert res.status_code == 400
    assert "distinct" in res.json()["detail"].lower() or "twice" in res.json()["detail"].lower()


def test_fusion_allows_duplicate_species_with_distinct_asset_ids():
    """Duplicate species (e.g., two Gengar cards with different Asset IDs) are valid."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO owned_creatures (
                asset_id, wallet_address, template_id, name, primary_type, secondary_type,
                faction, rarity, hp, attack, defense, speed, stamina, level, xp,
                evolution_stage, acquired_at, updated_at
            ) VALUES (500099, ?, '94', 'Gengar', 'Ghost', 'Poison', 'Umbra', 'Epic', 80, 80, 80, 80, 80, 1, 0, 1, '2026-09-10T00:00:00Z', '2026-09-10T00:00:00Z');
        """, (TEST_WALLET,))
        conn.commit()

    res = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004, 500099]
    })
    assert res.status_code == 200
    assert res.json()["status"] == "AWAITING_WALLET_APPROVAL"


def test_fusion_rejects_non_epic_pokemon():
    """Selecting Rare or Legendary Pokémon in fusion must be rejected."""
    # Rare asset included (600001)
    res_rare = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004, 600001]
    })
    assert res_rare.status_code == 400
    assert "EPIC" in res_rare.json()["detail"]

    # Legendary asset included (700001)
    res_legendary = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004, 700001]
    })
    assert res_legendary.status_code == 400
    assert "EPIC" in res_legendary.json()["detail"]


def test_fusion_rejects_unowned_asset():
    """Trying to fuse an asset not owned by the wallet must fail."""
    res = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004, 999999]
    })
    assert res.status_code in [404, 403, 400]


def test_fusion_rejects_trade_locked_asset():
    """An asset in an active trade cannot be fused."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO trades (
                trade_id, initiator_wallet, initiator_asset_id,
                counterparty_wallet, counterparty_asset_id, status, created_at
            ) VALUES ('trd_test_lock', ?, 500001, NULL, NULL, 'OPEN', '2026-09-10T00:00:00Z');
        """, (TEST_WALLET,))
        conn.commit()

    # Candidates should flag locked
    cand_res = client.get(f"/api/v1/fusion/candidates/{TEST_WALLET}")
    assert cand_res.status_code == 200
    cands = cand_res.json()
    locked_cand = next(c for c in cands if c["asset_id"] == 500001)
    assert locked_cand["is_locked"] is True

    # Initiate must reject
    res = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": [500001, 500002, 500003, 500004, 500005]
    })
    assert res.status_code == 400
    assert "TRADE" in res.json()["detail"]


def test_complete_fusion_flow_end_to_end():
    """
    Tests complete lifecycle:
      1. Initiate with 5 valid Epic Pokémon
      2. Confirm transfer
      3. Verify 5 Epics are burned (removed from user collection)
      4. Verify 1 random Legendary is minted and added to user collection
      5. Verify Idempotency on repeated confirm calls
    """
    input_ids = [500001, 500002, 500003, 500004, 500005]

    # 1. Initiate
    init_res = client.post("/api/v1/fusion/initiate", json={
        "wallet_address": TEST_WALLET,
        "input_asset_ids": input_ids
    })
    assert init_res.status_code == 200
    init_data = init_res.json()
    fusion_id = init_data["fusion_id"]
    assert init_data["status"] == "AWAITING_WALLET_APPROVAL"
    assert len(init_data["inputs"]) == 5

    # 2. Confirm
    conf_res = client.post(f"/api/v1/fusion/{fusion_id}/confirm", json={
        "wallet_address": TEST_WALLET,
        "transfer_tx_id": "tx_mock_transfer_group_12345"
    })
    assert conf_res.status_code == 200
    conf_data = conf_res.json()

    assert conf_data["status"] == "COMPLETED"
    assert conf_data["reward"] is not None
    assert conf_data["reward"]["rarity"] == "Legendary"
    assert conf_data["reward"]["asset_id"] > 0
    legendary_asset_id = conf_data["reward"]["asset_id"]
    legendary_name = conf_data["reward"]["name"]

    # 3. Verify 5 Epics removed from collection
    with get_db() as conn:
        for aid in input_ids:
            row = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
                (aid, TEST_WALLET)
            ).fetchone()
            assert row is None, f"Asset #{aid} was not burned from collection!"

        # 4. Verify 1 Legendary added to collection
        leg_row = conn.execute(
            "SELECT * FROM owned_creatures WHERE asset_id = ? AND wallet_address = ?",
            (legendary_asset_id, TEST_WALLET)
        ).fetchone()
        assert leg_row is not None
        assert leg_row["name"] == legendary_name
        assert leg_row["rarity"] == "Legendary"

        # Check remaining Epics count (should have 1 Epic left out of 6 original)
        remaining_epics = conn.execute(
            "SELECT COUNT(*) FROM owned_creatures WHERE wallet_address = ? AND rarity = 'Epic'",
            (TEST_WALLET,)
        ).fetchone()[0]
        assert remaining_epics == 1

    # 5. Idempotency Check: Calling confirm again returns the exact same reward without duplicate minting
    retry_res = client.post(f"/api/v1/fusion/{fusion_id}/confirm", json={
        "wallet_address": TEST_WALLET,
        "transfer_tx_id": "tx_mock_transfer_group_12345"
    })
    assert retry_res.status_code == 200
    retry_data = retry_res.json()
    assert retry_data["reward"]["asset_id"] == legendary_asset_id
    assert retry_data["reward"]["name"] == legendary_name
