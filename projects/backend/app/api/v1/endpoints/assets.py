"""
Pokédex (AlgoCreatures) — On-Chain ASA NFT Verification & Asset Access Endpoints
Module: api/v1/endpoints/assets.py
=================================================================================
Exposes live blockchain-verified asset endpoints:
  - GET /assets/{asset_id}: Live ASA configuration, ownership, and metadata lookup
  - GET /assets/search/{query}: Multi-parameter search by Asset ID, species name, or number
  - GET /assets/{asset_id}/opt-in-status: Live Pera Wallet opt-in check
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Path, Query, HTTPException, status
from pydantic import BaseModel, Field

from backend.app.services.nft_service import nft_service
from backend.rewards.creature_pool import creature_pool
from backend.app.core.database import get_db

router = APIRouter()

class PokemonAssetResponse(BaseModel):
    asset_id: int = Field(..., examples=[742199042])
    network: str = Field("testnet", examples=["testnet"])
    explorer_url: str = Field(..., examples=["https://testnet.explorer.perawallet.app/asset/742199042/"])
    pokemon: Dict[str, Any]
    nft: Dict[str, Any]
    ownership: Dict[str, Any]
    verified_on_chain: bool = Field(True, examples=[True])

@router.get(
    "/assets/{asset_id}",
    response_model=PokemonAssetResponse,
    summary="Get On-Chain Pokémon NFT Asset Detail",
    description="Queries Algorand TestNet and local ledger to return verified ASA parameters, Pokémon stats, and wallet ownership."
)
async def get_asset_detail(asset_id: int = Path(..., description="Algorand ASA Asset ID")):
    # 1. Query blockchain ASA parameters
    is_valid, asa_params, fail_reason = nft_service.verify_asset(asset_id)
    if not is_valid and not asa_params:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=fail_reason or f"Asset #{asset_id} was not found on Algorand TestNet."
        )

    # 2. Query local card ledger for Pokémon stats
    with get_db() as conn:
        row = conn.execute("SELECT * FROM owned_creatures WHERE asset_id = ?", (asset_id,)).fetchone()
        
    owner_wallet = row["wallet_address"] if row else (asa_params.get("creator") or nft_service.minter_addr)
    
    # 3. Live On-Chain ownership check
    owns = nft_service.wallet_owns_asset(owner_wallet, asset_id)
    minter_holds = nft_service.wallet_owns_asset(nft_service.minter_addr, asset_id)

    if row:
        c_tmpl = creature_pool.get_creature(row["template_id"])
        pokemon_data = {
            "id": row["pokemon_id"] or (int(c_tmpl.index_number) if c_tmpl and str(c_tmpl.index_number).isdigit() else 1),
            "template_id": row["template_id"],
            "name": row["name"],
            "image": c_tmpl.image if c_tmpl else f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{row['asset_id'] % 151 + 1}.png",
            "primary_type": row["primary_type"],
            "secondary_type": row["secondary_type"],
            "faction": row["faction"],
            "rarity": row["rarity"],
            "level": row["level"],
            "xp": row["xp"],
            "stats": {
                "hp": row["hp"],
                "attack": row["attack"],
                "defense": row["defense"],
                "speed": row["speed"],
                "stamina": row["stamina"]
            },
            "battle_wins": row["battle_wins"],
            "battle_losses": row["battle_losses"],
            "evolution_stage": row["evolution_stage"]
        }
        mint_tx = row["mint_tx"] or f"tx_mint_{asset_id}"
        delivery_tx = row["delivery_tx"]
        meta_uri = row["metadata_uri"] or asa_params.get("url", "")
    else:
        # Reconstruct from ASA params
        pokemon_data = {
            "id": asset_id % 151 + 1,
            "template_id": "genesis_creature",
            "name": asa_params.get("asset_name") or f"Pokémon #{asset_id}",
            "image": f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{asset_id % 151 + 1}.png",
            "primary_type": "Normal",
            "secondary_type": None,
            "faction": "Wild",
            "rarity": "Common",
            "level": 1,
            "xp": 0,
            "stats": {"hp": 60, "attack": 60, "defense": 60, "speed": 60, "stamina": 60},
            "battle_wins": 0,
            "battle_losses": 0,
            "evolution_stage": 1
        }
        mint_tx = f"tx_mint_{asset_id}"
        delivery_tx = None
        meta_uri = asa_params.get("url", "")

    nft_data = {
        "asset_id": asset_id,
        "total": asa_params.get("total", 1),
        "decimals": asa_params.get("decimals", 0),
        "default_frozen": asa_params.get("default_frozen", False),
        "unit_name": asa_params.get("unit_name", "PKMN"),
        "asset_name": asa_params.get("asset_name", pokemon_data["name"]),
        "metadata_uri": meta_uri,
        "mint_tx_id": mint_tx,
        "delivery_tx_id": delivery_tx,
        "creator": asa_params.get("creator", nft_service.minter_addr),
        "manager": asa_params.get("manager", nft_service.minter_addr),
        "reserve": asa_params.get("reserve", nft_service.minter_addr)
    }

    ownership_data = {
        "wallet": owner_wallet,
        "balance": 1 if owns else (0 if not minter_holds else 0),
        "verified": owns,
        "in_minter_holding": minter_holds and not owns,
        "delivery_status": "DELIVERED" if owns else ("WAITING_FOR_OPT_IN" if minter_holds else "UNKNOWN")
    }

    return PokemonAssetResponse(
        asset_id=asset_id,
        network="testnet",
        explorer_url=f"https://testnet.explorer.perawallet.app/asset/{asset_id}/",
        pokemon=pokemon_data,
        nft=nft_data,
        ownership=ownership_data,
        verified_on_chain=is_valid
    )

@router.get(
    "/assets/search/{query}",
    summary="Search Pokémon NFTs by Asset ID or Name",
    description="Finds Pokémon NFTs matching an Asset ID, species name, or Pokémon index number."
)
async def search_assets(query: str = Path(..., description="Asset ID, name, or number")):
    q = query.strip()
    results = []
    
    with get_db() as conn:
        # 1. If numeric, search exact Asset ID or index
        if q.isdigit():
            aid = int(q)
            rows = conn.execute(
                "SELECT * FROM owned_creatures WHERE asset_id = ? OR pokemon_id = ?",
                (aid, aid)
            ).fetchall()
            for r in rows:
                results.append(dict(r))
        
        # 2. Text match on name or template_id
        text_rows = conn.execute(
            "SELECT * FROM owned_creatures WHERE name LIKE ? OR template_id LIKE ? LIMIT 20",
            (f"%{q}%", f"%{q}%")
        ).fetchall()
        for r in text_rows:
            if not any(res["asset_id"] == r["asset_id"] for res in results):
                results.append(dict(r))

    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "asset_id": r["asset_id"],
                "name": r["name"],
                "primary_type": r["primary_type"],
                "rarity": r["rarity"],
                "level": r["level"],
                "owner_wallet": r["wallet_address"],
                "explorer_url": f"https://testnet.explorer.perawallet.app/asset/{r['asset_id']}/"
            }
            for r in results
        ]
    }

@router.get(
    "/assets/{asset_id}/opt-in-status",
    summary="Check Pera Wallet Opt-In Status",
    description="Checks whether a given wallet address has opted into the ASA on Algorand TestNet."
)
async def check_opt_in_status(
    asset_id: int = Path(...),
    wallet: str = Query(..., description="Algorand 58-character public address")
):
    opted_in = nft_service.check_user_opted_in(wallet, asset_id)
    owns = nft_service.wallet_owns_asset(wallet, asset_id)
    return {
        "asset_id": asset_id,
        "wallet_address": wallet,
        "opted_in": opted_in,
        "owns_asset": owns,
        "network": "testnet"
    }
