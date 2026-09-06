"""
AlgoRacers — Session 17: Metadata Service
Module: services/metadata_service.py
========================================
Manages canonical driver metadata resolution, ARC-3 URI formatting,
and manifest validation for the NFT minting pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from backend.app.services.ipfs_utils import compute_cid_v1, canonical_json_bytes

logger = logging.getLogger("algoracers.metadata")

MANIFEST_PATH = Path(__file__).resolve().parent.parent.parent.parent / "blockchain" / "metadata" / "manifest.json"
GENERATED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "blockchain" / "metadata" / "generated"

class MetadataService:
    def __init__(self):
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict[str, Any]:
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Manifest not loaded at startup: {e}")
            return {"drivers": {}}

    def get_driver_metadata_info(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """Returns the canonical IPFS manifest record for a given driver ID."""
        key = f"driver_{driver_id}"
        return self.manifest.get("drivers", {}).get(key)

    def get_canonical_arc3_uri(self, driver_id: str) -> str:
        """Returns the canonical ARC-3 IPFS URI for an ASA asset creation."""
        info = self.get_driver_metadata_info(driver_id)
        if info and "metadata_uri" in info:
            return info["metadata_uri"]
        return f"ipfs://bafkreidriver{driver_id}#arc3"

    def get_driver_metadata_json(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """Reads and returns the canonical driver metadata JSON."""
        gen_path = GENERATED_DIR / f"driver_{driver_id}.json"
        if gen_path.exists():
            with open(gen_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

metadata_service = MetadataService()
