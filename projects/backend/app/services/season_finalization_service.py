"""
AlgoRacers — Session 19: Season Finalization & Merkle Root Commitment
Module: services/season_finalization_service.py
=====================================================================
Builds canonical leaderboard snapshots, derives the season Merkle root,
and coordinates on-chain finalization.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import HTTPException, status
from backend.app.core.database import get_db
from backend.app.crypto.merkle import MerkleTree, hash_leaf, verify_merkle_proof
from backend.app.services.ipfs_utils import compute_cid_v1, canonical_json_bytes
from backend.app.services.season_leaderboard_service import season_leaderboard_service
from backend.app.models.season import SeasonPlayerProofResponse

logger = logging.getLogger("algoracers.seasons.finalization")

class SeasonFinalizationService:
    def finalize_season(self, season_id: str, caller_address: str) -> Dict[str, Any]:
        """
        Finalizes a championship season:
          1. Verifies all assigned tournaments are FINALIZED
          2. Generates canonical leaderboard snapshot
          3. Builds Merkle tree & derives season root
          4. Commits root & sets status to FINALIZED (Never overwritable)
        """
        with get_db() as conn:
            season = conn.execute("SELECT * FROM seasons WHERE season_id = ?;", (season_id,)).fetchone()
            if not season:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Season '{season_id}' not found.")

            if season["status"] == "FINALIZED":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Season '{season_id}' is already finalized. Overwriting roots is forbidden.")

            # Check tournaments
            tourn_rows = conn.execute("""
                SELECT st.app_id, st.round_number, t.status
                FROM season_tournaments st
                LEFT JOIN tournaments t ON st.app_id = t.app_id
                WHERE st.season_id = ?;
            """, (season_id,)).fetchall()

            if not tourn_rows:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot finalize season with zero registered tournament rounds.")

            unfinalized = [r["app_id"] for r in tourn_rows if r["status"] != "FINALIZED"]
            if unfinalized:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot finalize season: Tournament rounds {unfinalized} are not finalized yet."
                )

        # 2. Compute official final leaderboard
        standings = season_leaderboard_service.calculate_leaderboard(season_id)
        if not standings:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No eligible player results found to build leaderboard.")

        # 3. Canonical Snapshot Records
        canonical_records = []
        for s in standings:
            canonical_records.append({
                "season_id": season_id,
                "wallet_address": s.wallet_address,
                "rank": s.rank,
                "points": s.points,
                "wins": s.wins,
                "podiums": s.podiums
            })

        # 4. Construct Merkle Tree
        tree = MerkleTree(canonical_records, key_field="wallet_address")
        root_hex = tree.root_hex
        champion_wallet = standings[0].wallet_address

        # 5. Build & Pin IPFS Manifest
        manifest = {
            "season_id": season_id,
            "season_name": season["name"],
            "scoring_version": season["scoring_version"],
            "tree_scheme": "ALGORACERS_SEASON_LEADERBOARD_V1",
            "leaderboard_root": root_hex,
            "player_count": len(canonical_records),
            "finalized_at": datetime.now(timezone.utc).isoformat(),
            "players": canonical_records
        }
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_cid = compute_cid_v1(manifest_bytes)

        # 6. Commit to database
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute("""
                UPDATE seasons
                SET status = 'FINALIZED',
                    leaderboard_root = ?,
                    manifest_cid = ?,
                    player_count = ?,
                    champion_wallet = ?,
                    finalized_at = ?
                WHERE season_id = ?;
            """, (root_hex, manifest_cid, len(canonical_records), champion_wallet, now_iso, season_id))

            # Store final ranks in season_leaderboard
            for s in standings:
                conn.execute("""
                    INSERT INTO season_leaderboard (
                        season_id, wallet_address, driver_id, driver_name,
                        rank, points, wins, podiums, tournaments_entered, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(season_id, wallet_address) DO UPDATE SET
                        rank = excluded.rank,
                        points = excluded.points,
                        wins = excluded.wins,
                        podiums = excluded.podiums,
                        tournaments_entered = excluded.tournaments_entered,
                        updated_at = excluded.updated_at;
                """, (season_id, s.wallet_address, s.driver_id, s.driver_name, s.rank, s.points, s.wins, s.podiums, s.tournaments_entered, now_iso))

            conn.commit()

        logger.info(f"🏆 Finalized Season '{season_id}'! Champion: {champion_wallet[:8]}... | Root: {root_hex[:16]}... | CID: {manifest_cid[:16]}...")
        return {
            "season_id": season_id,
            "status": "FINALIZED",
            "leaderboard_root": root_hex,
            "manifest_cid": manifest_cid,
            "player_count": len(canonical_records),
            "champion_wallet": champion_wallet,
            "finalized_at": now_iso
        }

    def get_player_proof(self, season_id: str, wallet_address: str) -> SeasonPlayerProofResponse:
        """Generates Merkle membership proof for player standing in a season."""
        standings = season_leaderboard_service.calculate_leaderboard(season_id)
        player_entry = next((s for s in standings if s.wallet_address == wallet_address), None)

        if not player_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player '{wallet_address}' has no recorded participation in season '{season_id}'."
            )

        with get_db() as conn:
            season = conn.execute("SELECT * FROM seasons WHERE season_id = ?;", (season_id,)).fetchone()
            if not season:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Season '{season_id}' not found.")

        canonical_records = []
        for s in standings:
            canonical_records.append({
                "season_id": season_id,
                "wallet_address": s.wallet_address,
                "rank": s.rank,
                "points": s.points,
                "wins": s.wins,
                "podiums": s.podiums
            })

        tree = MerkleTree(canonical_records, key_field="wallet_address")
        proof = tree.generate_proof(wallet_address) or []
        record = next(r for r in canonical_records if r["wallet_address"] == wallet_address)
        leaf_hash_hex = hash_leaf(record).hex()

        is_final = (season["status"] == "FINALIZED")
        root_hex = season["leaderboard_root"] if is_final and season["leaderboard_root"] else tree.root_hex

        return SeasonPlayerProofResponse(
            season_id=season_id,
            wallet_address=wallet_address,
            record=record,
            leaf_hash=leaf_hash_hex,
            proof=proof,
            root=root_hex,
            manifest_cid=season["manifest_cid"],
            status=season["status"],
            is_finalized=is_final
        )

season_finalization_service = SeasonFinalizationService()
