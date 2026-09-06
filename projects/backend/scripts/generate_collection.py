"""
AlgoRacers — 2026 F1 Grid Collection Metadata Generator
Script: generate_collection.py
============================================================
Generates deterministic, ARC-3 compliant metadata JSON files for AlgoRacers 2026 Formula 1 driver collectibles.
Outputs JSON files into `blockchain/metadata/driver_XXX.json` and updates `manifest.json`.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

CONSTRUCTORS = {
    "mclaren": {"id": "mclaren", "name": "McLaren"},
    "mercedes": {"id": "mercedes", "name": "Mercedes"},
    "ferrari": {"id": "ferrari", "name": "Ferrari"},
    "red_bull_racing": {"id": "red_bull_racing", "name": "Red Bull Racing"},
    "racing_bulls": {"id": "racing_bulls", "name": "Racing Bulls"},
    "aston_martin": {"id": "aston_martin", "name": "Aston Martin"},
    "haas": {"id": "haas", "name": "Haas F1 Team"},
    "audi": {"id": "audi", "name": "Audi"},
    "alpine": {"id": "alpine", "name": "Alpine"},
    "williams": {"id": "williams", "name": "Williams"},
    "cadillac": {"id": "cadillac", "name": "Cadillac"}
}

CANONICAL_2026_GRID = [
    # McLaren
    {
        "id": "lando_norris",
        "numeric_id": "001",
        "name": "Lando Norris",
        "code": "NOR",
        "number": 4,
        "constructor_id": "mclaren",
        "nationality": "United Kingdom",
        "rarity": "Epic",
        "desc": "Elite race winner with pinpoint qualifying speed and aggressive tire optimization.",
        "stats": {"Speed": 94, "Qualifying": 95, "Racecraft": 92, "Overtaking": 90, "Wet Weather": 89, "Consistency": 93}
    },
    {
        "id": "oscar_piastri",
        "numeric_id": "002",
        "name": "Oscar Piastri",
        "code": "PIA",
        "number": 81,
        "constructor_id": "mclaren",
        "nationality": "Australia",
        "rarity": "Rare",
        "desc": "Ice-cool tactician with relentless pace and unflappable racecraft under pressure.",
        "stats": {"Speed": 89, "Qualifying": 88, "Racecraft": 87, "Overtaking": 85, "Wet Weather": 82, "Consistency": 88}
    },
    # Mercedes
    {
        "id": "george_russell",
        "numeric_id": "003",
        "name": "George Russell",
        "code": "RUS",
        "number": 63,
        "constructor_id": "mercedes",
        "nationality": "United Kingdom",
        "rarity": "Epic",
        "desc": "Master qualifier capable of extracting maximum performance over single-lap shootouts.",
        "stats": {"Speed": 93, "Qualifying": 94, "Racecraft": 90, "Overtaking": 88, "Wet Weather": 87, "Consistency": 91}
    },
    {
        "id": "kimi_antonelli",
        "numeric_id": "004",
        "name": "Kimi Antonelli",
        "code": "ANT",
        "number": 12,
        "constructor_id": "mercedes",
        "nationality": "Italy",
        "rarity": "Rare",
        "desc": "Prodigious young talent featuring raw apex speed and lightning adaptability.",
        "stats": {"Speed": 86, "Qualifying": 85, "Racecraft": 82, "Overtaking": 84, "Wet Weather": 80, "Consistency": 81}
    },
    # Ferrari
    {
        "id": "charles_leclerc",
        "numeric_id": "005",
        "name": "Charles Leclerc",
        "code": "LEC",
        "number": 16,
        "constructor_id": "ferrari",
        "nationality": "Monaco",
        "rarity": "Epic",
        "desc": "Pole-position maestro known for breathtaking single-lap commitments and street circuit supremacy.",
        "stats": {"Speed": 95, "Qualifying": 97, "Racecraft": 91, "Overtaking": 89, "Wet Weather": 86, "Consistency": 88}
    },
    {
        "id": "lewis_hamilton",
        "numeric_id": "006",
        "name": "Lewis Hamilton",
        "code": "HAM",
        "number": 44,
        "constructor_id": "ferrari",
        "nationality": "United Kingdom",
        "rarity": "Legendary",
        "desc": "Seven-time champion bringing supreme wet-weather mastery, racecraft, and clutch Grand Prix instinct.",
        "stats": {"Speed": 97, "Qualifying": 95, "Racecraft": 98, "Overtaking": 96, "Wet Weather": 98, "Consistency": 96}
    },
    # Red Bull Racing
    {
        "id": "max_verstappen",
        "numeric_id": "007",
        "name": "Max Verstappen",
        "code": "VER",
        "number": 1,
        "constructor_id": "red_bull_racing",
        "nationality": "Netherlands",
        "rarity": "Legendary",
        "desc": "Relentless multi-time World Champion with peerless race pace, ferocious overtakes, and wet-weather brilliance.",
        "stats": {"Speed": 99, "Qualifying": 98, "Racecraft": 98, "Overtaking": 97, "Wet Weather": 99, "Consistency": 97}
    },
    {
        "id": "isack_hadjar",
        "numeric_id": "008",
        "name": "Isack Hadjar",
        "code": "HAD",
        "number": 6,
        "constructor_id": "red_bull_racing",
        "nationality": "France",
        "rarity": "Common",
        "desc": "Dynamic Red Bull junior graduate renowned for fearless corner entries and high energy.",
        "stats": {"Speed": 74, "Qualifying": 75, "Racecraft": 72, "Overtaking": 73, "Wet Weather": 69, "Consistency": 71}
    },
    # Racing Bulls
    {
        "id": "liam_lawson",
        "numeric_id": "009",
        "name": "Liam Lawson",
        "code": "LAW",
        "number": 30,
        "constructor_id": "racing_bulls",
        "nationality": "New Zealand",
        "rarity": "Common",
        "desc": "Gritty wheel-to-wheel fighter with proven adaptability across challenging race conditions.",
        "stats": {"Speed": 76, "Qualifying": 77, "Racecraft": 75, "Overtaking": 74, "Wet Weather": 72, "Consistency": 75}
    },
    {
        "id": "arvid_lindblad",
        "numeric_id": "010",
        "name": "Arvid Lindblad",
        "code": "LIN",
        "number": 41,
        "constructor_id": "racing_bulls",
        "nationality": "United Kingdom",
        "rarity": "Common",
        "desc": "High-potential rookie showcasing formidable race starts and swift development curve.",
        "stats": {"Speed": 71, "Qualifying": 72, "Racecraft": 70, "Overtaking": 69, "Wet Weather": 68, "Consistency": 70}
    },
    # Aston Martin
    {
        "id": "fernando_alonso",
        "numeric_id": "011",
        "name": "Fernando Alonso",
        "code": "ALO",
        "number": 14,
        "constructor_id": "aston_martin",
        "nationality": "Spain",
        "rarity": "Epic",
        "desc": "Veteran champion possessing supreme race reading, defensive wizardry, and tactical cunning.",
        "stats": {"Speed": 92, "Qualifying": 90, "Racecraft": 96, "Overtaking": 94, "Wet Weather": 92, "Consistency": 94}
    },
    {
        "id": "lance_stroll",
        "numeric_id": "012",
        "name": "Lance Stroll",
        "code": "STR",
        "number": 18,
        "constructor_id": "aston_martin",
        "nationality": "Canada",
        "rarity": "Common",
        "desc": "Specialist in chaotic weather and opening-lap surges across tricky track conditions.",
        "stats": {"Speed": 75, "Qualifying": 72, "Racecraft": 73, "Overtaking": 76, "Wet Weather": 78, "Consistency": 72}
    },
    # Haas F1 Team
    {
        "id": "esteban_ocon",
        "numeric_id": "013",
        "name": "Esteban Ocon",
        "code": "OCO",
        "number": 31,
        "constructor_id": "haas",
        "nationality": "France",
        "rarity": "Rare",
        "desc": "Tenacious Grand Prix winner renowned for defensive firmness and midfield resilience.",
        "stats": {"Speed": 84, "Qualifying": 83, "Racecraft": 85, "Overtaking": 82, "Wet Weather": 86, "Consistency": 84}
    },
    {
        "id": "oliver_bearman",
        "numeric_id": "014",
        "name": "Oliver Bearman",
        "code": "BEA",
        "number": 87,
        "constructor_id": "haas",
        "nationality": "United Kingdom",
        "rarity": "Common",
        "desc": "Fast, composed young contender with impressive technical racecraft and overtaking acumen.",
        "stats": {"Speed": 77, "Qualifying": 78, "Racecraft": 76, "Overtaking": 77, "Wet Weather": 73, "Consistency": 74}
    },
    # Audi
    {
        "id": "nico_hulkenberg",
        "numeric_id": "015",
        "name": "Nico Hulkenberg",
        "code": "HUL",
        "number": 27,
        "constructor_id": "audi",
        "nationality": "Germany",
        "rarity": "Rare",
        "desc": "Precision qualifier and veteran lead driver anchoring Audi's inaugural works campaign.",
        "stats": {"Speed": 85, "Qualifying": 88, "Racecraft": 84, "Overtaking": 81, "Wet Weather": 82, "Consistency": 85}
    },
    {
        "id": "gabriel_bortoleto",
        "numeric_id": "016",
        "name": "Gabriel Bortoleto",
        "code": "BOR",
        "number": 5,
        "constructor_id": "audi",
        "nationality": "Brazil",
        "rarity": "Common",
        "desc": "Formula junior champion bringing stellar corner balance and attacking momentum.",
        "stats": {"Speed": 73, "Qualifying": 74, "Racecraft": 72, "Overtaking": 71, "Wet Weather": 70, "Consistency": 72}
    },
    # Alpine
    {
        "id": "pierre_gasly",
        "numeric_id": "017",
        "name": "Pierre Gasly",
        "code": "GAS",
        "number": 10,
        "constructor_id": "alpine",
        "nationality": "France",
        "rarity": "Rare",
        "desc": "Grand Prix winner who thrives on extracting optimal tire life and converting podium chances.",
        "stats": {"Speed": 85, "Qualifying": 84, "Racecraft": 86, "Overtaking": 83, "Wet Weather": 84, "Consistency": 85}
    },
    {
        "id": "franco_colapinto",
        "numeric_id": "018",
        "name": "Franco Colapinto",
        "code": "COL",
        "number": 43,
        "constructor_id": "alpine",
        "nationality": "Argentina",
        "rarity": "Common",
        "desc": "Aggressive, high-speed talent with decisive overtaking bravery and strong fan following.",
        "stats": {"Speed": 75, "Qualifying": 76, "Racecraft": 74, "Overtaking": 75, "Wet Weather": 71, "Consistency": 73}
    },
    # Williams
    {
        "id": "carlos_sainz",
        "numeric_id": "019",
        "name": "Carlos Sainz",
        "code": "SAI",
        "number": 55,
        "constructor_id": "williams",
        "nationality": "Spain",
        "rarity": "Epic",
        "desc": "Smooth Operator combining razor-sharp strategic intellect with top-tier race execution.",
        "stats": {"Speed": 92, "Qualifying": 91, "Racecraft": 94, "Overtaking": 90, "Wet Weather": 88, "Consistency": 93}
    },
    {
        "id": "alexander_albon",
        "numeric_id": "020",
        "name": "Alexander Albon",
        "code": "ALB",
        "number": 23,
        "constructor_id": "williams",
        "nationality": "Thailand",
        "rarity": "Rare",
        "desc": "Williams team leader delivering stellar qualifying laps and resolute defensive driving.",
        "stats": {"Speed": 86, "Qualifying": 87, "Racecraft": 85, "Overtaking": 84, "Wet Weather": 81, "Consistency": 86}
    },
    # Cadillac
    {
        "id": "sergio_perez",
        "numeric_id": "021",
        "name": "Sergio Perez",
        "code": "PER",
        "number": 11,
        "constructor_id": "cadillac",
        "nationality": "Mexico",
        "rarity": "Rare",
        "desc": "Tire-whispering Grand Prix winner driving Cadillac's debut entry into Formula 1.",
        "stats": {"Speed": 87, "Qualifying": 84, "Racecraft": 89, "Overtaking": 88, "Wet Weather": 83, "Consistency": 86}
    },
    {
        "id": "valtteri_bottas",
        "numeric_id": "022",
        "name": "Valtteri Bottas",
        "code": "BOT",
        "number": 77,
        "constructor_id": "cadillac",
        "nationality": "Finland",
        "rarity": "Common",
        "desc": "Ten-time race winner providing veteran composure, high-speed consistency, and qualifying prowess.",
        "stats": {"Speed": 78, "Qualifying": 81, "Racecraft": 77, "Overtaking": 75, "Wet Weather": 76, "Consistency": 80}
    }
]

def build_driver_metadata(driver_def: dict, ipfs_cid: str = "bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t") -> dict:
    """Formats a driver dictionary into an ARC-3 compliant metadata structure."""
    driver_id = driver_def["id"]
    numeric_id = driver_def.get("numeric_id", "001")
    driver_name = driver_def["name"]
    rarity = driver_def["rarity"]
    stats = driver_def["stats"]
    constructor = CONSTRUCTORS.get(driver_def["constructor_id"], {"name": "Formula 1"})["name"]

    attributes = [{"trait_type": "Rarity", "value": rarity}]
    attributes.append({"trait_type": "Constructor", "value": constructor})
    attributes.append({"trait_type": "Number", "value": driver_def["number"]})
    attributes.append({"trait_type": "Nationality", "value": driver_def["nationality"]})
    for stat_name, stat_val in stats.items():
        attributes.append({"trait_type": stat_name, "value": stat_val})

    return {
        "name": f"{driver_name} — AlgoRacers 2026 (#{numeric_id})",
        "description": f"{driver_name} ({constructor}) — {driver_def['desc']}",
        "image": f"ipfs://{ipfs_cid}/driver_{numeric_id}.png",
        "image_mimetype": "image/png",
        "external_url": f"https://algoracers.io/garage/{driver_id}",
        "properties": {
            "driver_id": driver_id,
            "numeric_id": numeric_id,
            "driver_name": driver_name,
            "code": driver_def["code"],
            "number": driver_def["number"],
            "constructor_id": driver_def["constructor_id"],
            "constructor_name": constructor,
            "team": constructor,
            "nationality": driver_def["nationality"],
            "generation": "2026 Grid Series 1",
            "season": "2026"
        },
        "attributes": attributes
    }

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — GENERATE 2026 F1 GRID METADATA")
    print("=" * 65)

    dirs_to_update = [
        Path(__file__).resolve().parent.parent.parent.parent / "blockchain" / "metadata",
        Path(__file__).resolve().parent.parent.parent / "blockchain" / "metadata"
    ]
    for mdir in dirs_to_update:
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / "generated").mkdir(parents=True, exist_ok=True)

    manifest_drivers = {}

    print(f"[*] Generating {len(CANONICAL_2026_GRID)} ARC-3 driver metadata files...")

    for i, driver_def in enumerate(CANONICAL_2026_GRID):
        numeric_id = f"{i+1:03d}"
        driver_def["numeric_id"] = numeric_id
        meta = build_driver_metadata(driver_def)

        meta_json_str = json.dumps(meta, indent=2)
        meta_compact = json.dumps(meta, separators=(',', ':'))
        sha256 = hashlib.sha256(meta_compact.encode('utf-8')).hexdigest()

        for mdir in dirs_to_update:
            out_file_num = mdir / f"driver_{numeric_id}.json"
            out_file_slug = mdir / f"driver_{driver_def['id']}.json"
            gen_file_num = (mdir / "generated") / f"driver_{numeric_id}.json"
            gen_file_slug = (mdir / "generated") / f"driver_{driver_def['id']}.json"

            with open(out_file_num, "w", encoding="utf-8") as f:
                f.write(meta_json_str)
            with open(out_file_slug, "w", encoding="utf-8") as f:
                f.write(meta_json_str)
            with open(gen_file_num, "w", encoding="utf-8") as f:
                f.write(meta_compact)
            with open(gen_file_slug, "w", encoding="utf-8") as f:
                f.write(meta_compact)

        manifest_drivers[f"driver_{numeric_id}"] = {
            "driver_id": numeric_id,
            "slug_id": driver_def["id"],
            "driver_name": driver_def["name"],
            "constructor": meta["properties"]["constructor_name"],
            "rarity": driver_def["rarity"],
            "metadata_cid": f"bafkreidriver{numeric_id}",
            "image_cid": f"bafkreiimage{numeric_id}",
            "sha256_hash": sha256,
            "metadata_uri": f"ipfs://bafkreidriver{numeric_id}#arc3"
        }

        print(f"   ✅ Created: #{numeric_id} [{driver_def['code']}] {driver_def['name']} ({meta['properties']['constructor_name']} | {driver_def['rarity']})")

    manifest = {
        "manifest_version": "2.0.0",
        "collection_name": "AlgoRacers 2026 Formula 1 Grid Collection",
        "season": "2026",
        "driver_count": len(CANONICAL_2026_GRID),
        "constructor_count": len(CONSTRUCTORS),
        "manifest_cid": "bafkreimanifest2026f1grid",
        "drivers": manifest_drivers
    }

    for mdir in dirs_to_update:
        manifest_path = mdir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"💾 Manifest saved to: {manifest_path}")

    print("=" * 65)

if __name__ == "__main__":
    main()
