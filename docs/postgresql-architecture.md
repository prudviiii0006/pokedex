# AlgoRacers — PostgreSQL Relational Database Architecture

---

## 1. Why PostgreSQL & Multi-Process Scaling

```text
┌────────────────────────────────────────────────────────┐
│ SQLITE:                                                │
│ • Single-file embedded storage.                        │
│ • Excellent for local testing & single-process MVP.    │
│ • Single-writer concurrency limits.                    │
└────────────────────────────────────────────────────────┘
                           vs.
┌────────────────────────────────────────────────────────┐
│ POSTGRESQL:                                            │
│ • Multi-process client/server architecture.            │
│ • Row-level locking & SKIP LOCKED worker pools.        │
│ • High concurrent read/write throughput.               │
│ • Transactional Outbox pattern support.                │
└────────────────────────────────────────────────────────┘
```

---

## 2. Logical Data Domains

* **Auth Domain**: `auth_challenges`, `sessions`
* **Purchases & Rewards**: `purchases`, `rewards`
* **Racing & Circuits**: `races`, `race_simulation_batches`
* **Tournaments & Seasons**: `tournaments`, `seasons`, `season_claims`
* **Chain Sync & Invariant Audits**: `chain_checkpoints`, `chain_events`, `chain_sync_errors`, `deployment_registry`
* **Jobs & Outbox**: `jobs`, `outbox_events`, `idempotency_records`, `cache_entries`
