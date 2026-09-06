# AlgoRacers — Algorand Indexer, Event Processing & Chain Sync Specification

---

## 1. Algod vs. Indexer Architecture

```text
┌────────────────────────────────────────────────────────┐
│ ALGOD (L1 Consensus Node):                             │
│ • Immediate Block Execution & Transaction Submission   │
│ • Instant Algorand Block Finality (No Reorg Waits)     │
│ • Authoritative live state                             │
└────────────────────────────────────────────────────────┘
                           vs.
┌────────────────────────────────────────────────────────┐
│ INDEXER (Searchable Historical Ledger):                │
│ • Historical searches (ASAs, accounts, apps, logs)     │
│ • Slight indexing lag (e.g. 1–2 rounds behind Algod)   │
│ • Queryable database derived from ledger               │
└────────────────────────────────────────────────────────┘
```

---

## 2. Chain Subscriber & Checkpoint Strategy

```text
  Algod (Round 1000) ──> Indexer (Round 998)
                             │
                             ▼
                    CHAIN SUBSCRIBER
                    (Reads Checkpoint #990)
                             │
                             ▼
                    EVENT DECODER
                             │
                             ▼
                    IDEMPOTENT HANDLERS
                    (UNIQUE constraint prevents duplicate effects)
                             │
                             ▼
                    DATABASE PROJECTIONS
                    (Advances Checkpoint to #998)
```

---

## 3. Algorand Finality vs. Ethereum Reorg Waiting

> [!IMPORTANT]
> **No Probabilistic Finality**:
> Unlike Ethereum or Bitcoin, Algorand's Byzantine Agreement consensus ensures **instant finality** upon inclusion in a block. There are no forks or reorganizations under normal operating conditions.
> Therefore, AlgoRacers does NOT require arbitrary multi-confirmation waits or rollback tables.
