# AlgoRacers 🏎️⚡
**Collect. Fuse. Trade. Race.**

AlgoRacers is an Algorand TestNet collectible racing-card application built around a simple, high-velocity core game loop:

```
                 CONNECT WALLET (Pera)
                           │
                           ▼
                      PACK STORE
                           │
                   x402 USDC Payment
                           │
                           ▼
                   DRIVER NFT CARD
                           │
                           ▼
                       MY GARAGE
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
             RACE        TRADE         FUSE
                           │            │
                           │         5 × EPIC
                           │            ↓
                           │         PREMIUM
                           │
                           └────────────┐
                                        ▼
                                    MY GARAGE
```

---

## 🎮 Core Game Loop

1. **CONNECT**: Non-custodial Algorand TestNet connection via **Pera Wallet**.
2. **BUY PACKS (x402 USDC)**: Purchase **Basic** or **Premium** packs using the **x402 Payment Required** micropayment standard with Algorand TestNet USDC.
3. **MY GARAGE**: View and manage owned ARC-3 / ARC-19 driver collectible NFTs with server-authoritative racing telemetry (Speed, Racecraft, Qualifying, Wet Weather). Filter by rarity (`COMMON`, `RARE`, `EPIC`, `PREMIUM`).
4. **FUSION LAB (5 Epics → 1 Premium)**: Forge five Epic driver cards into one ultra-rare, server-verified **Premium** driver NFT.
5. **TRADING MARKET**: Non-custodial, 1-for-1 card trading secured via **Algorand Atomic Transaction Groups** where both NFT transfers succeed in the same block round or fail completely.
6. **RACE & TELEMETRY**: Enter 8-car Grand Prix simulations on diverse circuits (Nova Circuit, Suzuka Wet, Marina Night, Monza Speed Ring) with stat-weighted performance scoring and optional AI Garage Coach advice.
7. **ACTIVITY**: Live chronological record of purchases, fusions, trades, and race finishes.

---

## 🏗️ System Architecture

```text
                       PLAYER
                          │
                          ▼
                 REACT FRONTEND (Vite / TypeScript)
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
           PERA WALLET          FASTAPI BACKEND
                │                   │
                │       ┌───────────┼───────────┐
                │       ▼           ▼           ▼
                │     x402       DATABASE    GAME LOGIC
                │   PAYMENT     (SQLite/WAL)    │
                │       │                       │
                │       ▼                ┌──────┼──────┐
                │  FACILITATOR           ▼      ▼      ▼
                │       │              REWARD FUSION  RACE
                │       ▼                       │
                └──── ALGORAND ◄───────────────┤
                       │                        │
                       ├──── NFT OWNERSHIP      │
                       ├──── NFT TRANSFERS      │
                       └──── ATOMIC TRADES ◄────┘
```

---

## 💎 Card Rarity Model

| Rarity | Supply Tier | Description | Source |
| :--- | :--- | :--- | :--- |
| **COMMON** | Baseline | Foundation tier drivers for circuit entry | Basic Packs |
| **RARE** | Mid-Tier | Enhanced attributes across technical circuits | Basic & Premium Packs |
| **EPIC** | High-Tier | Elite performance; key ingredient for fusion | Premium Packs & Market |
| **PREMIUM** | Apex Tier | 1-of-1 forged drivers with guaranteed 90+ ratings | **Fusion Lab (5 Epics)** |

---

## ⚡ Fusion & Burn Semantics

* **Server-Authoritative Validation**: The FastAPI backend independently verifies that the user owns 5 distinct, uncommitted Epic cards before creating a fusion session.
* **Burn Architecture**: The player signs transfers of the 5 Epic ASAs back to the AlgoRacers fusion vault / creator address (`minter_addr`). The backend verifies the confirmed transaction group, executes the ASA destruction sequence, and mints 1 new 1-of-1 Premium driver NFT directly to the user's wallet.
* **Idempotency & Safe Recovery**: Every fusion is tracked with a UUID idempotency key. In the event of network lag or timeouts, pending rewards remain persisted as recoverable obligations.

---

## 🔄 Atomic Trading Architecture

* **1-for-1 Card Swaps**: Direct asset-for-asset trading without intermediate escrow or third-party custody.
* **Algorand Atomic Groups**: Trade settlement is constructed as a 2-transaction atomic group:
  * Tx 1: Asset A ($Wallet_A \to Wallet_B$)
  * Tx 2: Asset B ($Wallet_B \to Wallet_A$)
* **Live Ownership Checks**: Trade execution re-verifies live ledger ownership at acceptance time to eliminate front-running and stale offers.

---

## 💳 x402 Micropayment Integration

* **Endpoint Protection**: Pack purchases return `HTTP 402 Payment Required` specifying TestNet USDC asset parameters, amount, and recipient address.
* **Transaction Settlement**: The user signs the payment transaction in Pera Wallet; the settlement is verified by the payment service, preventing replay attacks and duplicate claims.

---

## 📁 Repository Structure

```text
algoracers/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # FastAPI routes (packs, fusion, trading, race, auth, garage)
│   │   ├── core/              # Database schema (SQLite WAL), security, rate limiter
│   │   ├── models/            # Pydantic models (fusion, trading, packs, drivers)
│   │   └── services/          # Core engines (FusionService, TradingService, RewardEngine, NFTService, RaceEngine)
│   └── tests/                 # 188 automated test suite across 22 test files (100% passing)
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Clean 7-view motorsport dashboard
│   │   ├── wallet/pera.ts     # Non-custodial Pera Wallet connector & Algod client
│   │   └── index.css          # Dark motorsport design system
│   └── package.json
└── README.md
```

---

## 🧪 Automated Test Suite

Run the full verification suite (188 tests):
```bash
# Run backend pytest suite
python3 -m pytest backend/tests -v
```

---

## 📜 Experimental & Archival Features

Prior learning sessions explored advanced blockchain and enterprise patterns, which remain tested in the backend suite but are removed from the primary player UI:
* 2-of-3 Multisig Governance Council
* Merkle-Tree Tournament Season Claims
* Smart-Contract ARC-56 Tournaments
* Zero-Trust Developer Provenance & SRE Telemetry
