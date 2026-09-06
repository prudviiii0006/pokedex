# AlgoRacers — Durable Background Jobs & Transactional Outbox

---

## 1. Transactional Outbox Pattern

```text
HTTP Request
    │
    ▼
BEGIN DB TRANSACTION
    ├── Update Business State (`purchases.status = 'PAID'`)
    └── Insert Outbox Event (`MINT_NFT_REQUESTED`)
COMMIT
    │
    ▼
Outbox Dispatcher Relay
    └── Enqueues Durable Job
    │
    ▼
Background Worker Pool (`SELECT FOR UPDATE SKIP LOCKED`)
    └── Executes side effects (Algorand L1, IPFS Pin, Batch Simulation)
```

---

## 2. Worker Crash Recovery via Lease Timeout

When a worker claims a job, it sets `locked_at = now()`. If the worker crashes before marking the job `SUCCEEDED`, the lease expires after 120 seconds. The next worker loop resets the job back to `RETRY_PENDING`.
