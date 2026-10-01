# Pokédex ✨⚔️
**COLLECT. BATTLE. EVOLVE. TRADE.**

*YOUR POKÉMON. YOUR COLLECTION. YOUR JOURNEY.*

Pokédex is a decentralized Pokémon digital collectible and arena battle application built on the **Algorand Blockchain**, featuring instant **x402 TestNet USDC micropayments**, official **PokéAPI v2 artwork integration**, canonical **ARC-3 NFT evolutions**, elemental turn-based combat, and trustless peer-to-peer card swaps.

---

## ⚠️ Educational & Portfolio Project Disclaimer

> **IMPORTANT**: This is an unofficial educational/portfolio project. Pokémon and Pokémon character names are trademarks of their respective rights holders. This project is not affiliated with or endorsed by Nintendo, Game Freak, or The Pokémon Company.

---

## 🌟 System Overview & Game Loop

Pokédex pairs high-speed, deterministic blockchain mechanics on Algorand with canonical Pokémon data from PokéAPI v2:

```text
CONNECT WALLET (Pera QR)
        ↓
CHOOSE BOOSTER PACK (Basic $0.01 / Premium $0.05 USDC)
        ↓
X402 TESTNET USDC PAYMENT (HTTP 402 Settlement)
        ↓
INTERACTIVE PACK REVEAL (Silhouette → Type → Rarity → Artwork)
        ↓
POKÉMON REWARD GENERATED (Backend-Authoritative Odds)
        ↓
ARC-3 NFT MINTED ON ALGORAND (Unit: PKDX)
        ↓
TRAINER COLLECTION (Manage stats, XP & levels)
        ↓
ELEMENTAL ARENA BATTLE (5 Arenas, 3 Combat Stances)
        ↓
EARN COMBAT XP & LEVEL UP (Level 1 to Level 7+ Apex)
        ↓
CANONICAL EVOLUTION (Stage 1 → Stage 2 → Stage 3)
        ↓
PEER-TO-PEER TRADING POST (Card-for-Card Swaps)
```

---

## 🏗️ Architecture & Component Flow

```text
                         USER / TRAINER
                               │
                               ▼
                   REACT + TYPESCRIPT CLIENT
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
              PERA WALLET               FASTAPI
             (QR Connect)                  │
                   │            ┌──────────┼──────────┐
                   │            ▼          ▼          ▼
                   │         DATABASE    BATTLE     NFT MINT
                   │         (SQLite)    ENGINE     SERVICE
                   ▼                       │          │
              X402 CLIENT                  │          │
                   │                       │          │
                   ▼                       │          │
              X402 SERVER                  │          │
                   │                       │          │
                   ▼                       │          │
              FACILITATOR                  │          │
                   │                       │          │
                   ▼                       ▼          ▼
            ALGORAND TESTNET ────► USDC PAYMENT CONFIRMED
                                           │
                                           ▼
                                    POKÉMON REWARD
                                           │
                                           ▼
                                    ARC-3 NFT MINTED
                                           │
                                           ▼
                                   TRAINER COLLECTION
                                           │
                        ┌──────────────────┼──────────────────┐
                        ▼                  ▼                  ▼
                   ARENA BATTLE        EVOLUTION            TRADE
                    (XP + Wins)      (Dynamic NFT)       (Atomic Swap)
```

---

## 🐉 Canonical Pokémon Species Roster

Pokédex features **24 canonical Pokémon species** across **8 distinct elemental lines** with official artwork from PokéAPI:

| Element | Lineage | Color Accent | Stage 1 (Starter) | Stage 2 (Rising) | Stage 3 (Apex Sovereign) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Fire** | Charmander Line | `#FF4422` | Charmander (#004) | Charmeleon (#005) | Charizard (#006) |
| **Water** | Squirtle Line | `#3399FF` | Squirtle (#007) | Wartortle (#008) | Blastoise (#009) |
| **Grass** | Bulbasaur Line | `#44BB44` | Bulbasaur (#001) | Ivysaur (#002) | Venusaur (#003) |
| **Electric** | Pikachu Line | `#FFCC00` | Pichu (#172) | Pikachu (#025) | Raichu (#026) |
| **Rock/Ground** | Geodude Line | `#AA7744` | Geodude (#074) | Graveler (#075) | Golem (#076) |
| **Ice** | Snorunt Line | `#66DDFF` | Snorunt (#361) | Glalie (#362) | Froslass (#478) |
| **Ghost** | Gastly Line | `#8844AA` | Gastly (#092) | Haunter (#093) | Gengar (#094) |
| **Fairy** | Togepi Line | `#FFDD44` | Togepi (#175) | Togetic (#176) | Togekiss (#468) |

Plus iconic special species: **Lucario (#448)**, **Greninja (#658)**, **Mewtwo (#150)**, and **Rayquaza (#384)**.

---

## 📦 Booster Packs & x402 Micropayments

Booster packs are purchased using **TestNet USDC** (`ASA ID: 10458941`) via the **x402 Payment Protocol**:

- **Basic Booster Pack**: `$0.01 USDC` (10,000 micro-USDC)
  - *Odds*: 65% Common, 25% Rare, 9% Epic, 1% Legendary
- **Premium Apex Pack**: `$0.05 USDC` (50,000 micro-USDC)
  - *Odds*: 20% Common, 40% Rare, 30% Epic, 10% Legendary

### The x402 Payment Loop:
1. Client sends `POST /purchases` with wallet address and pack selection.
2. Server registers purchase intent and returns `402 Payment Required` challenge with payment parameters (`payTo`, `amount`, `asset`).
3. Pera Wallet signs the zero-cost asset transfer.
4. Client provides payment signature header to `POST /pay/purchases/{purchase_id}`.
5. Server verifies on-chain transaction finality via the Algorand facilitator.
6. Upon settlement, the Reward Engine rolls Pokémon species and triggers ARC-3 NFT minting.

---

## ⚔️ Elemental Battle Arena Engine

Trainers can deploy owned Pokémon into turn-based simulated combat across 5 arenas:

- **Volcano Colosseum** (+20% ATK, Fire Favored, Ice Disfavored)
- **Ocean Trench** (+25% DEF, Water Favored, Electric Disfavored)
- **Sylvan Glade** (+20% STM, Grass Favored, Fire Disfavored)
- **Thunder Peaks** (+25% SPD, Electric Favored, Ground Disfavored)
- **Glacial Rift** (+15% DEF, Ice Favored, Grass Disfavored)

---

## 🧬 Canonical Evolution Chamber

As Pokémon win battles and accumulate combat XP, they reach canonical evolution milestones:
- **Stage 1 → Stage 2 (Rising Form)**: Requires Level 3 and `350 XP`.
- **Stage 2 → Stage 3 (Apex Form)**: Requires Level 5 and `1,000 XP`.

Evolution permanently updates on-chain ARC-3 asset traits, boosts baseline stats, and upgrades rarity.

---

## 🔄 Peer-to-Peer Trading Post

The trustless trading station enables trainers to post card-for-card swap offers:
- Offer any owned Pokémon card on the open marketplace.
- Counterparties review Pokémon stats, element, and rarity before accepting.
- Instant ownership transfer recorded on the Algorand blockchain.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `3.12+` or `3.14+`
- **Node.js**: `v20+` with `npm` / `pnpm`
- **Pera Mobile Wallet** with Algorand TestNet enabled

### 1. Backend Server Setup
```bash
# Navigate to backend
cd projects/backend

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8000
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 2. Frontend Application Setup
```bash
# Navigate to frontend
cd projects/frontend

# Install dependencies
npm install

# Start Vite dev server on port 5173
npm run dev
```

### 3. Run Test Suite
```bash
cd projects/backend
pytest -v
```

---

## 🔒 Security & Provenance Guardrails

- **Backend-Authoritative RNG**: Stats, rarities, battle outcomes, and evolution thresholds are strictly calculated and validated on the backend.
- **x402 Replay Protection**: Payment transaction hashes are uniquely recorded to prevent duplicate claims.
- **Idempotent Minting**: Retrying a purchase returns the identical minted card without double-charging or re-rolling.
- **TestNet Sandbox**: Bounded to Algorand TestNet (`CAIP-2: algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=`).

---

**Built with ❤️ on Algorand.**
