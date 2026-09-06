"""
AlgoRacers — Session 3: NFT Metadata & Collection Generation
Script: generate_collection.py
============================================================
Generates deterministic, ARC-3 compliant metadata JSON files for AlgoRacers driver collectibles.
Outputs JSON files into `blockchain/metadata/driver_XXX.json`.
"""

import json
import os
import sys
from pathlib import Path

# Base roster of fictional AlgoRacers drivers
PREDEFINED_ROSTER = [
    {
        "id": "001",
        "name": "Velocity One",
        "team": "Apex Pulse Racing",
        "rarity": "Rare",
        "desc": "Engineered for high-speed circuits and aggressive cornering.",
        "stats": {"Speed": 91, "Qualifying": 88, "Racecraft": 87, "Overtaking": 85, "Wet Weather": 80, "Consistency": 84}
    },
    {
        "id": "002",
        "name": "Nova Rush",
        "team": "Quantum Motorsport",
        "rarity": "Epic",
        "desc": "Master of street circuits with lightning-fast reflex times.",
        "stats": {"Speed": 93, "Qualifying": 95, "Racecraft": 91, "Overtaking": 90, "Wet Weather": 86, "Consistency": 89}
    },
    {
        "id": "003",
        "name": "Apex Storm",
        "team": "Veloce Vanguard",
        "rarity": "Legendary",
        "desc": "A legendary Grand Prix champion with unmatched wet-weather mastery.",
        "stats": {"Speed": 97, "Qualifying": 98, "Racecraft": 96, "Overtaking": 95, "Wet Weather": 99, "Consistency": 97}
    },
    {
        "id": "004",
        "name": "Turbo Vale",
        "team": "Ignite Syndicate",
        "rarity": "Common",
        "desc": "A rising rookie known for brave late-braking maneuvers.",
        "stats": {"Speed": 72, "Qualifying": 69, "Racecraft": 71, "Overtaking": 74, "Wet Weather": 66, "Consistency": 68}
    },
    {
        "id": "005",
        "name": "Crimson Vector",
        "team": "Apex Pulse Racing",
        "rarity": "Rare",
        "desc": "A calculating tactician with outstanding tire management.",
        "stats": {"Speed": 82, "Qualifying": 80, "Racecraft": 84, "Overtaking": 81, "Wet Weather": 78, "Consistency": 85}
    },
    {
        "id": "006",
        "name": "Neon Racer",
        "team": "Synthwave GP",
        "rarity": "Common",
        "desc": "Night race specialist thriving under circuit floodlights.",
        "stats": {"Speed": 73, "Qualifying": 74, "Racecraft": 70, "Overtaking": 68, "Wet Weather": 67, "Consistency": 71}
    },
    {
        "id": "007",
        "name": "Phantom Speed",
        "team": "Veloce Vanguard",
        "rarity": "Epic",
        "desc": "An elusive qualifier capable of setting track sector records.",
        "stats": {"Speed": 94, "Qualifying": 96, "Racecraft": 88, "Overtaking": 91, "Wet Weather": 85, "Consistency": 90}
    },
    {
        "id": "008",
        "name": "Orbit Blaze",
        "team": "Quantum Motorsport",
        "rarity": "Common",
        "desc": "A solid mid-field contender with exceptional race start reaction times.",
        "stats": {"Speed": 70, "Qualifying": 72, "Racecraft": 69, "Overtaking": 71, "Wet Weather": 65, "Consistency": 73}
    },
    {
        "id": "009",
        "name": "Silver Torque",
        "team": "Ignite Syndicate",
        "rarity": "Rare",
        "desc": "A defensive wall on narrow tracks who rarely concedes positions.",
        "stats": {"Speed": 81, "Qualifying": 79, "Racecraft": 86, "Overtaking": 77, "Wet Weather": 82, "Consistency": 83}
    },
    {
        "id": "010",
        "name": "Nitro Zenith",
        "team": "Synthwave GP",
        "rarity": "Legendary",
        "desc": "An apex racer boasting flawless throttle modulation and raw speed.",
        "stats": {"Speed": 99, "Qualifying": 97, "Racecraft": 95, "Overtaking": 98, "Wet Weather": 94, "Consistency": 96}
    }
]

def build_driver_metadata(driver_def: dict, ipfs_cid: str = "bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t") -> dict:
    """Formats a driver dictionary into an ARC-3 compliant metadata structure."""
    driver_id = driver_def["id"]
    driver_name = driver_def["name"]
    rarity = driver_def["rarity"]
    stats = driver_def["stats"]

    attributes = [{"trait_type": "Rarity", "value": rarity}]
    for stat_name, stat_val in stats.items():
        attributes.append({"trait_type": stat_name, "value": stat_val})

    return {
        "name": f"AlgoRacer #{driver_id}",
        "description": f"{driver_name} — {driver_def['desc']}",
        "image": f"ipfs://{ipfs_cid}/driver_{driver_id}.png",
        "image_mimetype": "image/png",
        "external_url": f"https://algoracers.io/garage/{driver_id}",
        "properties": {
            "driver_id": driver_id,
            "driver_name": driver_name,
            "team": driver_def["team"],
            "generation": "Genesis (Gen 0)",
            "season": "2026"
        },
        "attributes": attributes
    }

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — GENERATE DRIVER COLLECTION METADATA")
    print("=" * 65)

    metadata_dir = Path(__file__).resolve().parent.parent.parent / "blockchain" / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    count = len(PREDEFINED_ROSTER)
    if len(sys.argv) > 1:
        try:
            count = min(int(sys.argv[1]), len(PREDEFINED_ROSTER))
        except ValueError:
            pass

    print(f"[*] Generating {count} ARC-3 driver metadata files...")

    for i in range(count):
        driver_def = PREDEFINED_ROSTER[i]
        meta = build_driver_metadata(driver_def)
        out_file = metadata_dir / f"driver_{driver_def['id']}.json"

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"   ✅ Created: {out_file.name} -> {meta['name']} ({driver_def['name']} | {driver_def['rarity']})")

    print(f"\n💾 Collection saved to: {metadata_dir}")
    print("=" * 65)

if __name__ == "__main__":
    main()
