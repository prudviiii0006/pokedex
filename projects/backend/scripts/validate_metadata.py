"""
AlgoRacers — Session 3: NFT Metadata Validator
Script: validate_metadata.py
=============================================
Validates all ARC-3 metadata JSON files in `blockchain/metadata/`.
Checks:
  1. Valid JSON syntax
  2. Core ARC-3 fields (name, description, image, attributes)
  3. Valid rarity tiers (Common, Rare, Epic, Legendary)
  4. Complete 6-attribute stat suites (Speed, Qualifying, Racecraft, Overtaking, Wet Weather, Consistency)
  5. Attribute values within allowed range (0 - 100)
  6. Uniqueness of driver names and IDs
"""

import json
import sys
from pathlib import Path

VALID_RARITIES = {"Common", "Rare", "Epic", "Legendary"}
REQUIRED_STATS = {"Speed", "Qualifying", "Racecraft", "Overtaking", "Wet Weather", "Consistency"}

def validate_file(file_path: Path, seen_ids: set, seen_names: set) -> list:
    errors = []
    
    # 1. JSON Parse Check
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Invalid JSON syntax: {e}"]

    # 2. Required Top-Level Fields
    for field in ["name", "description", "image", "attributes"]:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: '{field}'")

    # 3. Properties Check
    props = data.get("properties", {})
    driver_id = props.get("driver_id")
    driver_name = props.get("driver_name")

    if not driver_id:
        errors.append("Missing 'properties.driver_id'")
    elif driver_id in seen_ids:
        errors.append(f"Duplicate driver_id found: '{driver_id}'")
    else:
        seen_ids.add(driver_id)

    if not driver_name:
        errors.append("Missing 'properties.driver_name'")
    elif driver_name in seen_names:
        errors.append(f"Duplicate driver_name found: '{driver_name}'")
    else:
        seen_names.add(driver_name)

    # 4. Attributes Check
    attributes = data.get("attributes", [])
    if not isinstance(attributes, list) or len(attributes) == 0:
        errors.append("'attributes' must be a non-empty list")
        return errors

    attr_dict = {}
    for attr in attributes:
        if not isinstance(attr, dict) or "trait_type" not in attr or "value" not in attr:
            errors.append(f"Malformed attribute item: {attr}")
            continue
        attr_dict[attr["trait_type"]] = attr["value"]

    # Check Rarity
    rarity = attr_dict.get("Rarity")
    if not rarity:
        errors.append("Missing 'Rarity' attribute")
    elif rarity not in VALID_RARITIES:
        errors.append(f"Invalid rarity '{rarity}'. Must be one of {VALID_RARITIES}")

    # Check All 6 Required Stats
    for stat in REQUIRED_STATS:
        if stat not in attr_dict:
            errors.append(f"Missing required stat: '{stat}'")
        else:
            val = attr_dict[stat]
            if not isinstance(val, (int, float)) or not (0 <= val <= 100):
                errors.append(f"Stat '{stat}' value '{val}' is outside valid range (0 - 100)")

    return errors

def main():
    print("=" * 65)
    print("🏎️  ALGORACERS — ARC-3 METADATA VALIDATOR")
    print("=" * 65)

    cand_root = Path(__file__).resolve().parent.parent.parent.parent
    root_dir = cand_root if (cand_root / "blockchain").exists() else Path(__file__).resolve().parent.parent.parent
    metadata_dir = root_dir / "blockchain" / "metadata"
    json_files = sorted(list(metadata_dir.glob("driver_*.json")))

    if not json_files:
        print(f"❌ No JSON files found in {metadata_dir}")
        sys.exit(1)

    print(f"[*] Found {len(json_files)} metadata files to validate in:\n    {metadata_dir}\n")

    seen_ids = set()
    seen_names = set()
    total_errors = 0

    for file_path in json_files:
        errs = validate_file(file_path, seen_ids, seen_names)
        if not errs:
            print(f"  ✅ PASS: {file_path.name}")
        else:
            total_errors += len(errs)
            print(f"  ❌ FAIL: {file_path.name}")
            for err in errs:
                print(f"     ↳ Error: {err}")

    print("\n" + "=" * 65)
    if total_errors == 0:
        print(f"🎉 ALL {len(json_files)} METADATA FILES PASSED VALIDATION PERFECTLY!")
    else:
        print(f"⚠️  VALIDATION FAILED: {total_errors} error(s) detected across collection.")
        sys.exit(1)
    print("=" * 65)

if __name__ == "__main__":
    main()
