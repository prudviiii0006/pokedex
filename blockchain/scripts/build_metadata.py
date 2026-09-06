#!/usr/bin/env python3
"""
AlgoRacers — Session 17: Canonical Metadata & Manifest Builder
Module: blockchain/scripts/build_metadata.py
==============================================================
Validates driver templates, generates deterministic canonical JSON,
computes image & metadata CIDs, and creates the collection manifest.json.
"""

import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))

from blockchain.scripts.cid_utils import compute_cid_v1, canonical_json_bytes, compute_sha256

METADATA_DIR = root_dir / "blockchain" / "metadata"
GENERATED_DIR = METADATA_DIR / "generated"
MANIFEST_PATH = METADATA_DIR / "manifest.json"

REQUIRED_PROPERTIES = ["driver_id", "driver_name", "team", "generation", "season"]
VALID_RARITIES = ["Common", "Rare", "Epic", "Legendary"]
REQUIRED_STATS = ["Speed", "Qualifying", "Racecraft", "Overtaking", "Wet Weather", "Consistency"]

def validate_metadata_schema(data: Dict[str, Any], filename: str) -> None:
    """Strictly validates driver metadata against ARC-3 and AlgoRacers specifications."""
    if not data.get("name") or len(data["name"]) > 64:
        raise ValueError(f"[{filename}] Invalid or missing 'name'")
    if not data.get("description") or len(data["description"]) > 512:
        raise ValueError(f"[{filename}] Invalid or missing 'description'")
    if not data.get("image") or not data["image"].startswith("ipfs://"):
        raise ValueError(f"[{filename}] 'image' must be a valid 'ipfs://' URI")
    if data.get("image_mimetype") not in ["image/png", "image/webp", "image/jpeg"]:
        raise ValueError(f"[{filename}] Invalid 'image_mimetype'")

    props = data.get("properties", {})
    for p in REQUIRED_PROPERTIES:
        if p not in props:
            raise ValueError(f"[{filename}] Missing required property '{p}'")

    # Attributes check
    attrs = data.get("attributes", [])
    attr_map = {a.get("trait_type"): a.get("value") for a in attrs}

    rarity = attr_map.get("Rarity")
    if rarity not in VALID_RARITIES:
        raise ValueError(f"[{filename}] Invalid or missing Rarity trait: '{rarity}'")

    for stat in REQUIRED_STATS:
        val = attr_map.get(stat)
        if val is None or not isinstance(val, (int, float)) or not (0 <= val <= 100):
            raise ValueError(f"[{filename}] Invalid stat '{stat}': {val} (must be 0-100)")

def build_all_metadata() -> Dict[str, Any]:
    print("=" * 75)
    print("🏎️  ALGORACERS — CANONICAL IPFS METADATA & MANIFEST BUILDER")
    print(f"📁 Source Directory: {METADATA_DIR}")
    print("=" * 75)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(list(METADATA_DIR.glob("driver_*.json")))

    if not json_files:
        print(f"❌ No driver JSON files found in {METADATA_DIR}")
        sys.exit(1)

    manifest: Dict[str, Any] = {
        "collection_name": "AlgoRacers Genesis Drivers",
        "standard": "ARC-3",
        "cid_version": 1,
        "codec": "raw",
        "drivers": {}
    }

    for fpath in json_files:
        with open(fpath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        validate_metadata_schema(raw_data, fpath.name)
        driver_id = raw_data["properties"]["driver_id"]
        driver_name = raw_data["properties"]["driver_name"]
        rarity = next(a["value"] for a in raw_data["attributes"] if a["trait_type"] == "Rarity")

        # Mock deterministic image binary (or actual image file) to derive real image CID
        mock_image_bytes = f"AlgoRacers_Driver_Image_Asset_{driver_id}".encode("utf-8")
        image_cid = compute_cid_v1(mock_image_bytes)
        raw_data["image"] = f"ipfs://{image_cid}"

        # Canonicalize JSON
        canonical_bytes = canonical_json_bytes(raw_data)
        metadata_cid = compute_cid_v1(canonical_bytes)
        sha256_hex = hashlib.sha256(canonical_bytes).hexdigest()

        # Save to generated dir
        gen_path = GENERATED_DIR / f"driver_{driver_id}.json"
        with open(gen_path, "wb") as f_out:
            f_out.write(canonical_bytes)

        manifest["drivers"][f"driver_{driver_id}"] = {
            "driver_id": driver_id,
            "driver_name": driver_name,
            "rarity": rarity,
            "image_cid": image_cid,
            "image_uri": f"ipfs://{image_cid}",
            "metadata_cid": metadata_cid,
            "metadata_uri": f"ipfs://{metadata_cid}#arc3",
            "sha256_hash": sha256_hex,
            "byte_size": len(canonical_bytes)
        }

        print(f"✅ Driver #{driver_id} [{rarity:9}] {driver_name:18} -> CID: {metadata_cid[:20]}... (SHA-256: {sha256_hex[:12]}...)")

    # Compute collection manifest CID
    manifest_canonical = canonical_json_bytes(manifest)
    manifest_cid = compute_cid_v1(manifest_canonical)
    manifest["manifest_cid"] = manifest_cid

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f_man:
        json.dump(manifest, f_man, indent=2)

    print("-" * 75)
    print(f"🎉 Manifest successfully written to: {MANIFEST_PATH}")
    print(f"📦 Collection Manifest CID: {manifest_cid}")
    print("=" * 75)
    return manifest

if __name__ == "__main__":
    build_all_metadata()
