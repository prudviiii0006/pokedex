#!/usr/bin/env python3
"""
AlgoCreatures — Canonical Creature ARC-3 Metadata & Manifest Builder
Module: blockchain/scripts/build_creature_metadata.py
===================================================================
Generates deterministic ARC-3 metadata JSON for all 24 canonical elemental
creature species and outputs the complete collection manifest.json.
"""

import sys
import json
import hashlib
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "projects"))

from backend.rewards.creature_pool import CANONICAL_CREATURES, FACTIONS

METADATA_DIR = root_dir / "blockchain" / "metadata"
METADATA_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_PATH = METADATA_DIR / "manifest.json"

def generate_all_creature_metadata():
    print("=" * 70)
    print("✨ ALGOD CREATURES — ARC-3 CANONICAL METADATA BUILDER")
    print("=" * 70)

    manifest_creatures = {}

    for c in CANONICAL_CREATURES:
        idx_str = f"{c.index_number:03d}"
        filename = f"creature_{idx_str}.json"
        file_path = METADATA_DIR / filename

        raw_meta = {
            "name": f"{c.name} — AlgoCreatures Genesis (#{idx_str})",
            "description": f"{c.name} ({c.faction}) — {c.description}",
            "image": f"ipfs://bafybeicreaturesgenesis2026series1/creature_{idx_str}.png",
            "image_mimetype": "image/png",
            "external_url": f"https://algocreatures.io/species/{c.id}",
            "properties": {
                "species_id": c.id,
                "index_number": c.index_number,
                "species_name": c.name,
                "primary_type": c.primary_type,
                "secondary_type": c.secondary_type,
                "faction": c.faction,
                "rarity": c.rarity,
                "evolution_family": c.evolution_family,
                "evolution_stage": c.evolution_stage,
                "next_evolution_id": c.next_evolution_id,
                "generation": "Genesis Series 1",
                "standard": "ARC-3"
            },
            "attributes": [
                {"trait_type": "Primary Type", "value": c.primary_type},
                {"trait_type": "Faction", "value": c.faction},
                {"trait_type": "Rarity", "value": c.rarity},
                {"trait_type": "Evolution Stage", "value": f"Stage {c.evolution_stage}"},
                {"trait_type": "HP", "value": c.base_hp},
                {"trait_type": "Attack", "value": c.base_attack},
                {"trait_type": "Defense", "value": c.base_defense},
                {"trait_type": "Speed", "value": c.base_speed},
                {"trait_type": "Stamina", "value": c.base_stamina}
            ]
        }

        # Write canonical JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(raw_meta, f, indent=2)

        # Write slug alias
        slug_path = METADATA_DIR / f"creature_{c.id}.json"
        with open(slug_path, "w", encoding="utf-8") as f:
            json.dump(raw_meta, f, indent=2)

        sha256 = hashlib.sha256(json.dumps(raw_meta, sort_keys=True).encode("utf-8")).hexdigest()
        fake_cid = f"bafkreicreature{idx_str}"

        manifest_creatures[f"creature_{idx_str}"] = {
            "species_id": c.id,
            "index_number": c.index_number,
            "species_name": c.name,
            "primary_type": c.primary_type,
            "faction": c.faction,
            "rarity": c.rarity,
            "metadata_cid": fake_cid,
            "image_uri": f"ipfs://bafybeicreaturesgenesis2026series1/creature_{idx_str}.png",
            "sha256_hash": sha256,
            "metadata_uri": f"ipfs://{fake_cid}#arc3"
        }

        print(f"  ✅ Generated: {filename} [{c.rarity:9}] — {c.name} ({c.primary_type})")

    manifest = {
        "manifest_version": "2.0.0",
        "collection_name": "AlgoCreatures Genesis Elemental Collection",
        "season": "Genesis Series 1",
        "species_count": len(CANONICAL_CREATURES),
        "factions_count": len(FACTIONS),
        "manifest_cid": "bafkreimanifestalgocreaturesgenesis",
        "creatures": manifest_creatures
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n🎉 All 24 Creature ARC-3 metadata files and manifest.json created successfully!")
    print("=" * 70)

if __name__ == "__main__":
    generate_all_creature_metadata()
