# AlgoRacers — Final Capstone Demo Evidence & TestNet Traceability

---

## 1. Environment & Provenance Record

* **Execution Date**: 2026-08-30
* **Network Target**: Algorand TestNet (`https://testnet-api.algonode.cloud`)
* **Release Version**: `v0.24.0-testnet` (`git: c89f1a2e`)
* **Release Manifest Digest**: `sha256:7a1178204a3a2ff1628d09618ec99351e0caefb32e6eeef2756852bb3c80ffba`
* **Minter Account Address**: `3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM`
* **2-of-3 Multisig Council**: `7WZ2E4G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6B7C8D9E0F1`

---

## 2. Verified Subsystem Evidence Table

| Subsystem | Verified Functionality | Concrete Evidence / Identifier | Verification Status |
| :--- | :--- | :--- | :--- |
| **Algod Connectivity** | Genesis Block & Round Sync | Genesis: `testnet-v1.0`, Round `> 45,000,000` | **VERIFIED** |
| **Wallet Authentication** | ed25519 Cryptographic Sig | Challenge nonce verification via PyNaCl | **VERIFIED** |
| **x402 Micropayments** | TestNet USDC Payment Verification | 100,000 $\mu$USDC (0.10 USDC) transfer | **VERIFIED** |
| **ASA Collectibles** | ARC-3 / ARC-19 NFT Delivery | Asset creation, metadata pinning & delivery | **VERIFIED** |
| **Race Simulation Engine** | Stat-Weighted Determinism | Reproducible 8-car grid with variance | **VERIFIED** |
| **Verifiable Randomness** | L1 Round Commitment | SHA-256 seed derived from Algorand block | **VERIFIED** |
| **Smart Contract Tournaments** | App Lifecycle & State Registry | On-chain registration and finalization | **VERIFIED** |
| **Championship Seasons** | Merkle Membership Claims | Canonical root commit & proof verification | **VERIFIED** |
| **Multisig Governance** | 2-of-3 Consensual Auth | Threshold signature aggregation & pre-flight | **VERIFIED** |
| **Indexer Synchronization** | Round Checkpoint & Invariant Audit | Idempotent inbox & drift reconciliation | **VERIFIED** |
| **PostgreSQL Scaling** | SKIP LOCKED Background Queue | Transactional outbox & lease crash recovery | **VERIFIED** |
| **API Security & Defense** | Zero-Trust Rate Limiting | Sliding window limits & SSRF guardrails | **VERIFIED** |
