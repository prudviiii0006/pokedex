# AlgoRacers — Algorand Smart Contracts & On-Chain Tournament Architecture

---

## 1. Why Smart Contracts in AlgoRacers?

In previous sessions, tournament status and registrations were managed exclusively by FastAPI in SQLite. While high-performance, backend-only state requires total trust in the server operator.

By introducing the **On-Chain Tournament Registry Smart Contract** on the Algorand Virtual Machine (AVM v8), key lifecycle and integrity rules are enforced directly by consensus:

```text
┌────────────────────────────────────────┐       ┌────────────────────────────────────────┐
│         SERVER-ONLY ENFORCEMENT        │       │      SMART-CONTRACT ENFORCEMENT        │
│ • "Trust our server that registration  │       │ • Smart contract rejects registration  │
│    closed at 12:00."                   │  vs.  │    after CLOSED state on-chain.        │
│ • Database state can be edited easily. │       │ • Immutable state transitions on AVM.  │
│ • Zero public cryptographic audit trail│       │ • Result hash committed to blockchain. │
└────────────────────────────────────────┘       └────────────────────────────────────────┘
```

---

## 2. Hybrid On-Chain / Off-Chain Architecture

| Feature | Execution Layer | Rationale |
| :--- | :--- | :--- |
| **Tournament State Machine** | **On-Chain (AVM)** | Enforces strict `OPEN` $\to$ `CLOSED` $\to$ `FINALIZED` lifecycle. |
| **Participant Registration Limit** | **On-Chain (AVM)** | Enforces hard capacity caps (e.g. max 8 players). |
| **Race Result Commitment** | **On-Chain (AVM)** | SHA-256 canonical result hash committed permanently to Global State. |
| **Multi-Car Physics Simulation** | **Off-Chain (FastAPI)** | High-compute stat weighting, tire wear, and controlled variance off-chain. |
| **AI Driver Coaching** | **Off-Chain (FastAPI)** | Natural language heuristics and telemetry synthesis. |
| **x402 Micropayments** | **Off-Chain / Layer-1**| HTTP 402 challenge/response with TestNet USDC settlement. |

---

## 3. Smart Contract State & Storage Layout

### Global State:
* `creator` (bytes, 32 bytes): Organizer public address authorized to close/finalize.
* `status` (bytes): Current lifecycle state (`"OPEN"`, `"CLOSED"`, `"FINALIZED"`).
* `max_players` (uint64): Maximum driver capacity.
* `participants` (uint64): Current registered driver count.
* `circuit_id` (bytes): Target racing circuit identifier (`"nova_circuit"`).
* `winner` (uint64): Winner ASA ID recorded upon finalization.
* `result_hash` (bytes): 64-character SHA-256 hex digest of the canonical off-chain race result.

### Box Storage:
* Box Key: `txn.Sender` (32-byte participant address) storing `asset_id` (8 bytes), ensuring on-chain single-entry uniqueness.

---

## 4. Cryptographic Result Hash & Tamper Verification

$$\text{Canonical JSON} = \text{json.dumps}(\text{result\_dict}, \text{sort\_keys}=\text{True}, \text{separators}=(',', ':'))$$
$$\text{Result Hash} = \text{SHA256}(\text{Canonical JSON})$$

```text
FastAPI Simulation ──> Canonical JSON ──> SHA-256 Hash ──> Smart Contract Finalize
                                                                 │
Client Verification <── GET /tournaments/{id}/verify-result <───┘
```

If any score or position is modified in the database, `SHA256(Tampered JSON) != on_chain_hash`, triggering immediate tamper detection.
