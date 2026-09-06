# AlgoRacers — Learning Roadmap (Sessions 0 to 12)

This document outlines the step-by-step master progression for building **AlgoRacers** from ground zero to a full-stack, blockchain-powered gaming application with autonomous agent micropayments.

---

## 🏁 Teaching Methodology (The 7-Step Cycle)
For every technical concept:
1. **Explain the concept first** (What is it in plain English?).
2. **Explain why it exists** (What problem does it solve on-chain/off-chain?).
3. **Show a minimal example** (Isolated code snippet).
4. **Hands-on Implementation** (You write and integrate the code).
5. **Deconstruct the code** (Line-by-line review).
6. **Test & Verify** (Assert state changes on-chain / via API).
7. **Abstract & Scale** (Move to next layer only after mastery).

---

## 🗺️ Master Curriculum

### 📍 Session 0 — Architecture & Environment Setup
- **Learning Objective**: Understand full-stack Web3 architecture and establish development environment.
- **Concepts**: Layer-1 vs. Layer-2, non-custodial custody, client-server-blockchain boundaries, x402 protocol concept.
- **Implementation Goal**: Monorepo scaffolding, environment verification, documentation baseline.
- **Expected Outcome**: Clean, organized repository and crystal-clear understanding of the system components.

---

### 📍 Session 1 — Algorand Fundamentals
- **Learning Objective**: Master Algorand account models, public/private keys, mnemonics, and Algod nodes.
- **Concepts**: Pure Proof of Stake (PPoS), Minimum Balance Requirement (MBR), microALGOs, genesis hashes, transaction parameters (fee, firstValid, lastValid).
- **Implementation Goal**: Python script to generate accounts, fund via TestNet dispenser, connect to Algod, query balance, and send first native ALGO payment.
- **Expected Outcome**: Ability to programmatically create and control Algorand accounts with confirmed on-chain transactions.

---

### 📍 Session 2 — Algorand Standard Assets (ASAs)
- **Learning Objective**: Understand layer-1 native assets, fungible vs. non-fungible tokens, and opt-in mechanics.
- **Concepts**: ASAs vs. ERC-20/721 smart contract tokens, Asset Config Transaction, Manager/Reserve/Freeze/Clawback addresses, Asset Opt-in (preventing token spam).
- **Implementation Goal**: Create a script to mint a fungible token (e.g., `$RACE` currency) and a unique collectible token, opt in a secondary account, and transfer the asset.
- **Expected Outcome**: Deep understanding of Algorand's built-in asset layer and opt-in security model.

---

### 📍 Session 3 — NFT Metadata & ARC Standards
- **Learning Objective**: Master ARC-0003 and ARC-0019 specifications for verifiable NFT metadata.
- **Concepts**: IPFS decentralized storage, CID hashing, `metadata_hash` field, ARC-3 JSON schema (attributes, properties, media), ARC-19 dynamic template URIs.
- **Implementation Goal**: Generate metadata JSON for a genesis driver (Speed, Stamina, Handling stats), compute SHA-256 asset hash, and mint a fully standard-compliant Driver ASA.
- **Expected Outcome**: Verifiable, wallet-compatible Driver NFT minting pipeline adhering to ecosystem standards.

---

### 📍 Session 4 — Pera Wallet Integration
- **Learning Objective**: Connect a frontend web application to Algorand using non-custodial wallet signers.
- **Concepts**: WalletConnect protocol, Pera Wallet SDK, session persistence, signing unsigned transaction bytes (`algosdk.Transaction`).
- **Implementation Goal**: Minimal frontend UI connecting to Pera Wallet, showing connected address/balance, and signing an on-chain opt-in transaction.
- **Expected Outcome**: Secure, non-custodial user authentication and transaction signing without backend custody.

---

### 📍 Session 5 — Pack & Reward System Architecture
- **Learning Objective**: Design secure off-chain pack generation and on-chain delivery mechanics.
- **Concepts**: Rarity tiering (Common, Rare, Legendary), pseudo-random vs. verifiable random distribution, MBR implications for multiple assets.
- **Implementation Goal**: Pack opening engine that rolls driver stats/rarity and prepares atomic asset opt-in/transfer transactions.
- **Expected Outcome**: Working pack simulator that outputs deterministic asset bundles ready for minting.

---

### 📍 Session 6 — FastAPI Backend Integration
- **Learning Objective**: Build high-performance REST APIs bridging blockchain state with off-chain game state.
- **Concepts**: Async Python, Pydantic schemas, Algod/Indexer SDK integration, caching on-chain reads, background tasks for minting.
- **Implementation Goal**: FastAPI endpoints to `/drivers/my-garage`, `/packs/available`, and `/race/simulate`.
- **Expected Outcome**: Robust backend serving driver metadata, indexing user balances, and simulating races.

---

### 📍 Session 7 — x402 Protocol Fundamentals
- **Learning Objective**: Understand the HTTP 402 "Payment Required" specification for decentralized API monetisation.
- **Concepts**: HTTP status 402, `WWW-Authenticate` and `Authorization` headers, stateless invoice generation, payment receipts.
- **Implementation Goal**: Minimal FastAPI middleware intercepting protected endpoints and issuing 402 response headers with payment details.
- **Expected Outcome**: Standardized HTTP 402 challenge-response flow functioning in Python.

---

### 📍 Session 8 — x402 + Algorand Settlement
- **Learning Objective**: Bind x402 payment requirements directly to on-chain Algorand transactions.
- **Concepts**: Transaction confirmation verification via Algod/Indexer, round timeouts, preventing replay attacks via transaction ID tracking.
- **Implementation Goal**: FastAPI verification middleware that accepts an Algorand Transaction ID, validates payment recipient/amount on-chain, and unlocks the resource.
- **Expected Outcome**: Automated payment verification where on-chain ALGO/USDC transfers unlock API endpoints.

---

### 📍 Session 9 — End-to-End Purchase → Minting Pipeline
- **Learning Objective**: Connect Frontend, Pera Wallet, x402, and FastAPI into a seamless atomic pack purchase flow.
- **Concepts**: Atomic Transaction Groups (Group IDs), multi-transaction signing, atomic swap / mint upon payment receipt.
- **Implementation Goal**: Full user journey: User clicks "Buy Pack" -> x402 invoice generated -> Pera signs Payment + Opt-in -> FastAPI verifies -> Driver ASA transferred -> UI displays opening animation.
- **Expected Outcome**: Complete, friction-free decentralized purchase experience.

---

### 📍 Session 10 — Racing & Team Mechanics
- **Learning Objective**: Build an engaging, stat-driven racing simulation engine.
- **Concepts**: Stat weighted algorithms (Speed vs Handling on Curves, Stamina on Long Tracks), track conditions (Dry, Rain, Night), leaderboard tracking.
- **Implementation Goal**: Race simulation service where submitted driver ASAs compete, producing telemetry logs and distributing leaderboard points.
- **Expected Outcome**: Playable racing loop utilizing the driver attributes minted on-chain.

---

### 📍 Session 11 — Autonomous AI Agent + x402 Micropayments
- **Learning Objective**: Enable an autonomous software agent to hold an Algorand wallet, pay for API access via x402, and enter races.
- **Concepts**: Machine-to-machine commerce, autonomous agent key management, automated 402 handling, programmatic strategy execution.
- **Implementation Goal**: Standalone Python AI racer script that discovers race tracks, pays the entry fee via x402, races automatically, and analyzes performance.
- **Expected Outcome**: Fully autonomous agent interacting with AlgoRacers infrastructure without human intervention.

---

### 📍 Session 12 — Security, Testing, & TestNet Deployment
- **Learning Objective**: Harden smart contracts, secure backend endpoints, and deploy to Algorand TestNet.
- **Concepts**: Reentrancy, replay attack mitigation, rate limiting, key management best practices, continuous integration for blockchain tests.
- **Implementation Goal**: Comprehensive test suite (pytest + unit tests for transactions), environment configs for TestNet/MainNet, and deployment runbooks.
- **Expected Outcome**: Production-grade, thoroughly tested, and deployed AlgoRacers ecosystem.
