"""
AlgoRacers — Session 18: Collection Registry & Merkle Proof Service
Module: services/collection_registry_service.py
===================================================================
Manages on-chain collection root commitments, proof generation,
and independent cryptographic membership verification.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.core.database import get_db
from backend.app.crypto.merkle import MerkleTree, hash_leaf, verify_merkle_proof

logger = logging.getLogger("algoracers.collection_registry")

def _resolve_manifest_path() -> Path:
    cand1 = Path(__file__).resolve().parent.parent.parent.parent.parent / "blockchain" / "metadata" / "manifest.json"
    cand2 = Path(__file__).resolve().parent.parent.parent.parent / "blockchain" / "metadata" / "manifest.json"
    return cand1 if cand1.exists() else cand2

MANIFEST_PATH = _resolve_manifest_path()

class CollectionRegistryService:
    def __init__(self):
        self.tree: Optional[MerkleTree] = None
        self.manifest: Dict[str, Any] = {}
        self.driver_records: List[Dict[str, Any]] = []
        self._load_and_initialize()

    def _load_and_initialize(self):
        try:
            if MANIFEST_PATH.exists():
                with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                    self.manifest = json.load(f)

                self.driver_records = []
                for k, v in sorted(self.manifest.get("drivers", {}).items()):
                    self.driver_records.append({
                        "driver_id": v["driver_id"],
                        "driver_name": v["driver_name"],
                        "rarity": v["rarity"],
                        "metadata_cid": v["metadata_cid"],
                        "image_cid": v["image_cid"],
                        "sha256_hash": v["sha256_hash"]
                    })

                if self.driver_records:
                    self.tree = MerkleTree(self.driver_records, key_field="driver_id")
                    root_hex = self.tree.root_hex
                    manifest_cid = self.manifest.get("manifest_cid", "bafkreimanifest")

                    # Register in SQLite cache
                    with get_db() as conn:
                        conn.execute("""
                            INSERT INTO collection_registries (
                                app_id, collection_id, version, collection_root,
                                leaf_count, manifest_cid, publisher, created_at
                            ) VALUES (?, 'drivers', 1, ?, ?, ?, '3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM', ?)
                            ON CONFLICT(collection_id, version) DO UPDATE SET
                                collection_root = excluded.collection_root,
                                leaf_count = excluded.leaf_count,
                                manifest_cid = excluded.manifest_cid;
                        """, (88001001, root_hex, len(self.driver_records), manifest_cid, datetime.now(timezone.utc).isoformat()))
                        conn.commit()

                    logger.info(f"🌳 Initialized Driver Collection v1 Merkle Tree: Root = {root_hex[:16]}... ({len(self.driver_records)} leaves)")
        except Exception as e:
            logger.error(f"Failed to initialize Merkle tree: {e}")

    def get_collection_root_info(self, collection_id: str = "drivers", version: int = 1) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            row = conn.execute("""
                SELECT * FROM collection_registries 
                WHERE collection_id = ? AND version = ?;
            """, (collection_id, version)).fetchone()
            if row:
                return dict(row)
        return None

    def get_driver_proof(self, driver_id: str, collection_id: str = "drivers", version: int = 1) -> Optional[Dict[str, Any]]:
        if not self.tree:
            self._load_and_initialize()

        if not self.tree:
            return None

        # Find record
        record = next((r for r in self.driver_records if r["driver_id"] == driver_id), None)
        if not record:
            return None

        proof = self.tree.generate_proof(driver_id)
        if proof is None:
            return None

        leaf_hash_hex = hash_leaf(record).hex()
        root_info = self.get_collection_root_info(collection_id, version)
        root_hex = root_info["collection_root"] if root_info else self.tree.root_hex
        manifest_cid = root_info["manifest_cid"] if root_info else self.manifest.get("manifest_cid", "")

        return {
            "collection_id": collection_id,
            "version": version,
            "driver_id": driver_id,
            "record": record,
            "leaf_hash": leaf_hash_hex,
            "proof": proof,
            "root": root_hex,
            "algorithm": "SHA-256",
            "tree_scheme": "ALGORACERS_LEAF_NODE_V1",
            "manifest_cid": manifest_cid
        }

    def verify_proof(
        self,
        record: Dict[str, Any],
        proof: List[Dict[str, str]],
        root_hex: str
    ) -> bool:
        return verify_merkle_proof(record, proof, root_hex)

collection_registry_service = CollectionRegistryService()
