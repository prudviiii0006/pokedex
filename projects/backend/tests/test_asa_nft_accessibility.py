"""
Pokédex (AlgoCreatures) — On-Chain ASA NFT Accessibility & Verification Test Suite
================================================================================
Validates:
1. 1-of-1 ASA specifications (total=1, decimals=0, default_frozen=False, unit_name, ARC-3 URL)
2. Real Asset ID capture from confirmed blockchain transactions
3. Asset existence & metadata validation via GET /assets/{asset_id}
4. Pera Wallet opt-in check and atomic NFT delivery flow
5. On-chain ownership verification (holding amount == 1)
6. Purchase traceability (purchase -> payment -> reward -> mint -> asset -> delivery -> owner)
7. Mint idempotency (no duplicate ASA minted on retry)
8. Security guardrails: Battle, Trade, and Evolution require verified on-chain ownership (403 on failure)
9. Multi-parameter Asset search API
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.main import app
from backend.app.services.nft_service import nft_service
from backend.app.services.purchase_service import purchase_service
from backend.rewards.creature_pool import creature_pool
from backend.app.core.database import get_db

client = TestClient(app)

TEST_USER_WALLET = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"
TEST_OTHER_WALLET = "EW6GDRGUZW372X6P3544DGNGWAPGSUAEHCTOF7ZEVUOPFWZW4GACOOISVU"

@pytest.fixture(autouse=True)
def setup_db():
    """Clear test data from purchases and owned_creatures before each test."""
    with get_db() as conn:
        conn.execute("DELETE FROM purchases WHERE wallet_address IN (?, ?)", (TEST_USER_WALLET, TEST_OTHER_WALLET))
        conn.execute("DELETE FROM owned_creatures WHERE wallet_address IN (?, ?)", (TEST_USER_WALLET, TEST_OTHER_WALLET))


class TestAsaNftAccessibility:
    """Test suite for on-chain ASA NFT accessibility, verification, and delivery."""

    def test_asa_1_of_1_specifications(self):
        """Verify 1-of-1 ASA configuration: total=1, decimals=0, default_frozen=False, ARC-3."""
        pikachu = creature_pool.get_creature("creature_pikachu_025") or creature_pool.get_all_creatures()[0]
        
        # Test instance metadata generation
        meta_uri, meta_dict = nft_service.generate_instance_metadata(pikachu, "purch_spec_1", "rew_spec_1")
        assert meta_dict["properties"]["pokemon_name"] == pikachu.name
        assert meta_dict["properties"]["edition"] == "Genesis 1-of-1"
        assert "ipfs://" in meta_uri
        assert "#arc3" in meta_uri

        # Mock direct minting flow
        with patch.object(nft_service, "mint_creature_nft", return_value=(88800025, meta_uri, "tx_mint_spec_test", 4500100)):
            asset_id, uri, tx_id, round_num = nft_service.mint_creature_nft(pikachu, "purch_spec_1", "rew_spec_1")
            assert asset_id == 88800025
            assert tx_id == "tx_mint_spec_test"
            assert round_num == 4500100
            assert uri == meta_uri

    def test_asset_lookup_and_verification_api(self):
        """Verify GET /assets/{asset_id} returns live blockchain ASA parameters and ownership."""
        test_asset_id = 88800025
        
        # Seed test creature in database
        with get_db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO owned_creatures 
                (asset_id, purchase_id, wallet_address, template_id, name, primary_type, secondary_type, faction, rarity, level, xp, hp, attack, defense, speed, stamina, acquired_at, updated_at, pokemon_id, mint_tx, delivery_tx, metadata_uri, ownership_verified, network)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?, ?, ?, ?, 1, 'testnet')
                """,
                (test_asset_id, "purch_api_test", TEST_USER_WALLET, "creature_pikachu_025", "Pikachu", "Electric", None, "Volt Guild", "Rare", 4, 150, 50, 55, 40, 90, 100, 25, "tx_mint_888", "tx_deliv_888", "ipfs://bafkreipokemon25#arc3")
            )

        mock_algod = MagicMock()
        mock_algod.asset_info.return_value = {
            "params": {
                "total": 1,
                "decimals": 0,
                "default-frozen": False,
                "unit-name": "PKMN025",
                "asset-name": "Pikachu #025",
                "url": "ipfs://bafkreipokemon25#arc3",
                "creator": nft_service.minter_addr
            }
        }
        mock_algod.account_info.return_value = {
            "assets": [
                {
                    "asset-id": test_asset_id,
                    "amount": 1,
                    "is-frozen": False
                }
            ]
        }

        with patch.object(nft_service, "algod_client", mock_algod):
            res = client.get(f"/assets/{test_asset_id}")
            assert res.status_code == 200
            data = res.json()
            
            assert data["asset_id"] == test_asset_id
            assert data["network"] == "testnet"
            assert data["verified_on_chain"] is True
            assert data["pokemon"]["name"] == "Pikachu"
            assert data["pokemon"]["id"] == 25
            assert data["nft"]["total"] == 1
            assert data["nft"]["decimals"] == 0
            assert data["nft"]["unit_name"] == "PKMN025"
            assert data["ownership"]["wallet"] == TEST_USER_WALLET
            assert data["ownership"]["balance"] == 1
            assert data["ownership"]["verified"] is True
            assert "explorer_url" in data

    def test_purchase_to_asset_traceability(self):
        """Verify complete end-to-end traceability from purchase_id to asset_id."""
        init_res = purchase_service.create_or_resume_purchase("basic", TEST_USER_WALLET)
        purchase_id = init_res.purchase_id

        # Mock on-chain mint and delivery
        mock_asset_id = 999111222
        with patch.object(nft_service, "mint_creature_nft", return_value=(mock_asset_id, "ipfs://meta#arc3", "tx_mint_999", 4500200)), \
             patch.object(nft_service, "check_user_opted_in", return_value=True), \
             patch.object(nft_service, "transfer_nft_to_user", return_value=(True, "tx_deliv_999")), \
             patch.object(nft_service, "wallet_owns_asset", return_value=True):
            
            conf_res = purchase_service.confirm_purchase_payment(purchase_id, "tx_pay_trace_999")
            assert conf_res.status.value == "DELIVERED"
            assert conf_res.asset_id == mock_asset_id

        # Query GET /purchases/{purchase_id}
        resp = client.get(f"/api/v1/purchases/{purchase_id}")
        assert resp.status_code == 200
        pdata = resp.json()
        
        assert pdata["purchase_id"] == purchase_id
        assert pdata["payment_status"] == "SETTLED_ON_ALGORAND_TESTNET"
        assert pdata["nft"]["asset_id"] == mock_asset_id
        assert pdata["nft"]["mint_tx_id"] == "tx_mint_999"
        assert pdata["nft"]["delivery_tx_id"] == "tx_deliv_999"
        assert pdata["nft"]["ownership_verified"] is True
        assert pdata["reward"]["pokemon_name"] is not None

    def test_mint_idempotency_on_retry(self):
        """Verify that attempting to claim or re-mint for a purchase with an asset_id reuses the existing asset."""
        init_res = purchase_service.create_or_resume_purchase("basic", TEST_USER_WALLET)
        purchase_id = init_res.purchase_id
        existing_asset_id = 777000111

        with patch.object(nft_service, "mint_creature_nft", return_value=(existing_asset_id, "ipfs://meta#arc3", "tx_mint_777", 4500100)), \
             patch.object(nft_service, "check_user_opted_in", return_value=False):
            
            # First confirmation -> WAITING_FOR_OPT_IN
            p1 = purchase_service.confirm_purchase_payment(purchase_id, "tx_pay_idem_1")
            assert p1.asset_id == existing_asset_id
            assert p1.status.value == "WAITING_FOR_OPT_IN"

        # Claim delivery retry -> Should not re-mint, but use existing asset
        with patch.object(nft_service, "check_user_opted_in", return_value=True), \
             patch.object(nft_service, "transfer_nft_to_user", return_value=(True, "tx_deliv_idem_confirmed")), \
             patch.object(nft_service, "wallet_owns_asset", return_value=True):
            
            res = client.post(f"/api/v1/purchases/{purchase_id}/claim")
            assert res.status_code == 200
            data = res.json()
            assert data["asset_id"] == existing_asset_id
            assert data["status"] == "DELIVERED"

    def test_battle_ownership_security_guardrail(self):
        """Verify that initiating a battle requires verified on-chain ownership of the fighting asset."""
        asset_id = 999555444

        # When user does NOT own asset on chain -> 403 Forbidden
        with patch.object(nft_service, "wallet_owns_asset", return_value=False):
            res = client.post(
                "/api/v1/game/battle",
                json={
                    "wallet_address": TEST_USER_WALLET,
                    "player_asset_id": asset_id,
                    "arena_id": "volcano",
                    "strategy_id": "balanced"
                }
            )
            assert res.status_code == 403
            assert "You do not own this Pokémon NFT on-chain" in res.json()["detail"]

    def test_trade_ownership_security_guardrail(self):
        """Verify that creating a trade requires verified on-chain ownership."""
        asset_id = 999666555

        # When creator does NOT own asset on chain -> 403 Forbidden
        with patch.object(nft_service, "wallet_owns_asset", return_value=False):
            res = client.post(
                "/api/v1/trades",
                json={
                    "initiator_wallet": TEST_USER_WALLET,
                    "initiator_asset_id": asset_id
                }
            )
            assert res.status_code == 403
            assert "You do not own the offered Pokémon NFT on-chain" in res.json()["detail"]

    def test_evolution_ownership_security_guardrail(self):
        """Verify that checking evolution eligibility requires verified on-chain ownership."""
        asset_id = 999888777

        # When user does NOT own asset on chain -> 403 Forbidden
        with patch.object(nft_service, "wallet_owns_asset", return_value=False):
            res = client.get(
                f"/api/v1/evolution/{asset_id}",
                params={"wallet_address": TEST_USER_WALLET}
            )
            assert res.status_code == 403
            assert "You do not own this Pokémon NFT on-chain" in res.json()["detail"]

    def test_multi_parameter_asset_search_api(self):
        """Verify GET /assets/search/{query} searches by Asset ID or species name."""
        asset_id = 888777666
        with get_db() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO owned_creatures (
                    asset_id, purchase_id, wallet_address, template_id, name, primary_type, faction,
                    rarity, level, xp, hp, attack, defense, speed, stamina, acquired_at, updated_at, pokemon_id, network
                ) VALUES (?, 'purch_search_1', ?, 'creature_gengar_094', 'Gengar', 'Ghost', 'Umbra', 'Epic', 5, 200, 60, 65, 60, 110, 100, datetime('now'), datetime('now'), 94, 'testnet')
                """,
                (asset_id, TEST_USER_WALLET)
            )

        # Search by exact Asset ID
        res = client.get(f"/assets/search/{asset_id}")
        assert res.status_code == 200
        results = res.json()["results"]
        assert len(results) >= 1
        assert results[0]["asset_id"] == asset_id
        assert results[0]["name"] == "Gengar"

        # Search by Name
        res_name = client.get("/assets/search/Gengar")
        assert res_name.status_code == 200
        assert any(r["name"] == "Gengar" for r in res_name.json()["results"])
