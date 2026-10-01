# Pokédex — Comprehensive System Architecture & Threat Model

---

## 1. System Context & Component Interaction

```text
                          PLAYER
                            │
                            ▼
                       FRONTEND (React/TypeScript)
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
             PERA WALLET            FASTAPI (Async Backend)
                 │                     │
                 │          ┌──────────┼──────────┐
                 │          ▼          ▼          ▼
                 │      AUTH/API   SERVICES   POSTGRESQL
                 │                     │          │
                 │                     │      JOBS/OUTBOX
                 │                     │          │
                 │                     ▼          ▼
                 │                 ALGORAND    WORKERS (SKIP LOCKED)
                 │                     │
                 │          ┌──────────┼──────────┐
                 │          ▼          ▼          ▼
                 │        ALGOD      INDEXER    IPFS
                 │
                 └──────────────► ALGORAND TESTNET
```

---

## 2. Subsystem Authority & Source of Truth

| Domain | Authoritative System | Persistence / Proof Layer | Invariant Enforcement |
| :--- | :--- | :--- | :--- |
| **Driver Collectibles** | **Algorand L1** | ASA Holding / Ledger Balance | On-chain asset ownership checks |
| **Packs & Rewards** | **Backend PostgreSQL** | SQLite/Postgres `purchases` table | Server-side RNG & Idempotency key |
| **Micropayments** | **Algorand L1 (USDC)** | x402 Signed PayTxn Evidence | L1 transaction verification |
| **Race Mechanics** | **Deterministic Engine** | Server-side Stat-Weighted Eval | Off-chain simulation with seed |
| **Tournaments** | **Algorand Smart Contract** | ARC-56 App State & Box Storage | On-chain capacity & registration |
| **Randomness** | **Algorand Randomness Beacon** | Round-specific VRF output | Deterministic sub-seed derivation |
| **Championships** | **Merkle Tree Proofs** | On-chain Root Commitments | Cryptographic inclusion proofs |
| **Admin Controls** | **Multisig Council** | 2-of-3 Threshold Account | On-chain multisig verification |
| **Event Ingestion** | **Indexer / Subscriber** | `chain_events` Inbox & Checkpoints| Idempotent subscriber cursor |
| **Durable Jobs** | **PostgreSQL Job Queue** | `jobs` table (`SKIP LOCKED`) | Lease expiration & retry policy |
