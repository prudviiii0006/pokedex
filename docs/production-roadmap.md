# AlgoRacers — Production Readiness & Architecture Roadmap

This document outlines the necessary infrastructure, architectural, and security evolutions required before deploying an application like AlgoRacers to Algorand MainNet.

---

## 1. Key Management & Custody
- **Current State**: Server holds a local TestNet minter account in `backend/.env`.
- **Production Target**:
  - Integrate **AWS KMS** or **HashiCorp Vault** for transaction signing.
  - Implement **multi-signature approval** for pack contract admin functions.

---

## 2. Wallet Authentication
- **Current State**: Client sends public wallet address in request body.
- **Production Target**:
  - Implement **ARC-0014 (Sign-In with Algorand)**.
  - Server issues a time-bounded cryptographic challenge (`nonce`); wallet signs the challenge to prove ownership.

---

## 3. Database & Concurrency
- **Current State**: Local file-based SQLite database with WAL mode.
- **Production Target**:
  - Migrate to **Managed PostgreSQL** with connection pooling.
  - Implement **Redis** for distributed rate-limiting and lock management during high-traffic drops.

---

## 4. Smart Contract Tournaments
- **Current State**: 8-car Grand Prix simulations executed off-chain in FastAPI.
- **Production Target**:
  - Deploy **PyTeal / Beaker Smart Contracts** for competitive tournaments with on-chain escrow, Verifiable Random Function (VRF) randomness, and prize pools.
