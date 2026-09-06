# AlgoRacers — Driver Metadata Specification (ARC-0003 Standard)

This document defines the official metadata schema and architecture for collectible **AlgoRacers Driver NFTs** on the Algorand blockchain.

---

## 1. Schema Overview

AlgoRacers metadata complies with the **ARC-0003 (ARC-3)** standard. Under ARC-3, the on-chain ASA URL points to a JSON file hosted on decentralized storage (IPFS), and the on-chain `metadata_hash` matches the 32-byte SHA-256 digest of that JSON file.

### Complete JSON Schema:

```json
{
  "name": "AlgoRacer #001",
  "description": "Velocity One — A genesis Tier-1 driver for the AlgoRacers Grand Prix. Engineered for high-speed circuits and aggressive cornering.",
  "image": "ipfs://bafybeic527p2j4f2e5z7e7t6c5b2r4n3k6l5o4p3q2r1s0t/driver_001.png",
  "image_mimetype": "image/png",
  "image_integrity": "sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=",
  "external_url": "https://algoracers.io/garage/001",
  "properties": {
    "driver_id": "001",
    "driver_name": "Velocity One",
    "team": "Apex Pulse Racing",
    "generation": "Genesis (Gen 0)",
    "season": "2026"
  },
  "attributes": [
    {
      "trait_type": "Rarity",
      "value": "Rare"
    },
    {
      "trait_type": "Speed",
      "value": 91
    },
    {
      "trait_type": "Qualifying",
      "value": 88
    },
    {
      "trait_type": "Racecraft",
      "value": 87
    },
    {
      "trait_type": "Overtaking",
      "value": 85
    },
    {
      "trait_type": "Wet Weather",
      "value": 80
    },
    {
      "trait_type": "Consistency",
      "value": 84
    },
    {
      "trait_type": "Special Ability",
      "value": "Overdrive Slipstream"
    }
  ]
}
```

---

## 2. Field-by-Field Breakdown

| Field | Type | Description |
| :--- | :--- | :--- |
| `name` | `string` | Human-readable title displayed in wallets, marketplaces, and game UIs. |
| `description` | `string` | Narrative backstory, lore, and driver profile. |
| `image` | `string` | Content-addressed URI (`ipfs://<CID>/image.png`) pointing to driver artwork. |
| `image_mimetype`| `string` | MIME type for rendering (e.g. `image/png`, `image/webp`). |
| `image_integrity`| `string` | Optional SRI hash verifying media file integrity. |
| `external_url` | `string` | Web portal link for deeper game telemetry and leaderboards. |
| `properties` | `object` | Key-value dictionary containing static collectible metadata. |
| `attributes` | `array` | List of `{ trait_type, value }` objects representing verifiable in-game stats. |

---

## 3. Rarity Tiers & Probabilities

AlgoRacers divides collectibles into 4 standard rarity tiers:

| Tier | Base Stat Range | Pack Drop Rate | Collectible Significance |
| :--- | :--- | :--- | :--- |
| **Common** | 60 – 74 | **60%** | Reliable foundation drivers for regional circuits. |
| **Rare** | 75 – 84 | **25%** | Competitive drivers with specialized track affinities. |
| **Epic** | 85 – 93 | **12%** | Championship contenders with high consistency and racecraft. |
| **Legendary** | 94 – 99 | **3%** | Ultra-rare apex drivers with maximum stats and special abilities. |

$$\sum \text{Probabilities} = 60\% + 25\% + 12\% + 3\% = 100\%$$
