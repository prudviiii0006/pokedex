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

## 📁 Repository Structure

```text
pokedex/
├── projects/
│   ├── frontend/            # React + Vite + TypeScript web application
│   ├── backend/             # FastAPI REST API, reward engine, database & test suite
│   └── smart-contracts/     # AlgoKit Python smart contracts (PokedexRegistry)
├── blockchain/
│   ├── metadata/            # ARC-3 JSON metadata for Pokémon collectibles
│   └── scripts/             # CID computation, IPFS metadata & verification tools
├── docs/
│   ├── architecture.md      # System architecture and data flow
│   ├── final-architecture.md# Complete end-to-end component specifications
│   ├── ipfs-metadata.md     # IPFS content addressing and metadata standards
│   ├── security.md          # Input guards, rate limiting, and replay defense
│   └── reference/           # Reference examples and educational tutorials
└── package.json             # Root unified workspace runner
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

### Quick Start with Root Commands
From the workspace root:

```bash
# 1. Start Pokédex Backend (Port 8001)
npm run backend:start

# 2. Start Pokédex Frontend (Port 5173)
npm run frontend:dev

# 3. Run Backend Test Suite (110 tests)
npm run test:backend
```

### Manual Directory Setup

#### 1. Backend Server Setup
```bash
cd projects/backend
pip install -r requirements.txt
npm start    # Launches uvicorn on port 8001
```

#### 2. Frontend Application Setup
```bash
cd projects/frontend
npm install
npm run dev  # Launches Vite dev server on port 5173
```

#### 3. Run Test Suite
```bash
cd projects/backend
pytest -v
```

---

## 🌐 Production & Cloud Deployment Guide

Pokédex is architected for seamless multi-platform cloud deployment:

### 1. Frontend Deployment (Vercel / Netlify)
- **Framework Preset**: Vite
- **Root Directory**: `projects/frontend` (or keep `./` with the included [`vercel.json`](file:///Users/prudvi/programming%20/projects/pokedex/projects/frontend/vercel.json))
- **Build Command**: `npm run build` (or `npm --prefix projects/frontend run build`)
- **Output Directory**: `dist` (or `projects/frontend/dist`)
- **Environment Variables**:
  - `VITE_API_BASE_URL`: URL of your deployed backend (e.g. `https://pokedex-api.onrender.com` or `http://localhost:8001`)
  - `VITE_NETWORK`: `testnet`
  - `VITE_ALGOD_NODE`: `https://testnet-api.algonode.cloud`
  - `VITE_INDEXER_NODE`: `https://testnet-idx.algonode.cloud`

### 2. Backend Container Deployment (Docker / Railway / Render / Fly.io)
The repository includes a production-ready multi-platform [`Dockerfile`](file:///Users/prudvi/programming%20/projects/pokedex/Dockerfile) with dynamic `$PORT` handling and healthchecks:

```bash
# Build the container
docker build -t pokedex-backend .

# Run the container
docker run -p 8001:8000 -e PORT=8000 -e NETWORK=testnet pokedex-backend
```

Or deploy both backend and persistent volume with **Docker Compose**:
```bash
docker compose up -d
```

### 3. Key Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `NETWORK` | Algorand network target | `testnet` |
| `PORT` | ASGI server port | `8000` (or `8001` local) |
| `ALGOD_ADDRESS` | Algorand node RPC endpoint | `https://testnet-api.algonode.cloud` |
| `INDEXER_ADDRESS` | Algorand Indexer RPC endpoint | `https://testnet-idx.algonode.cloud` |
| `PAYMENT_RECEIVER_ADDRESS`| Algorand TestNet treasury account | `3VZQZ4J4YRJBI...` |
| `VITE_API_BASE_URL` | Frontend API backend endpoint | `http://127.0.0.1:8001` |

---

## 🔒 Security & Provenance Guardrails

- **Backend-Authoritative RNG**: Stats, rarities, battle outcomes, and evolution thresholds are strictly calculated and validated on the backend.
- **x402 Replay Protection**: Payment transaction hashes are uniquely recorded to prevent duplicate claims.
- **Idempotent Minting**: Retrying a purchase returns the identical minted card without double-charging or re-rolling.
- **TestNet Sandbox**: Bounded to Algorand TestNet (`CAIP-2: algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=`).

---

**Built with ❤️ on Algorand.**
