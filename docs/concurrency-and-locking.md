# AlgoRacers — Concurrency Control, Locking & Idempotency

---

## 1. Concurrency Hazards & Defense-in-Depth

```text
┌────────────────────────────────────────────────────────┐
│ CONCURRENCY HAZARD (Double Mint / Double Reward):      │
│ Two API workers read status='PAID' concurrently.       │
│ Both execute NFT minting if naive check used.          │
└────────────────────────────────────────────────────────┘
                           vs.
┌────────────────────────────────────────────────────────┐
│ ATOMIC CONDITIONAL UPDATE:                             │
│ UPDATE purchases SET status='MINT_PENDING'             │
│ WHERE id=:id AND status='PAID';                        │
│ Affected rows = 1 (Winner proceeds; loser no-ops).     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Idempotency Key Fingerprint Protection

Every client mutation carries an `Idempotency-Key` header:
1. First request hashes parameters and reserves the key in `idempotency_records`.
2. Duplicate request with **identical parameters** receives the cached response.
3. Duplicate request with **altered parameters** is rejected with HTTP 400.
