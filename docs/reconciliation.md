# AlgoRacers — Blockchain State Reconciliation & Drift Recovery Specification

---

## 1. Incremental Subscriber vs. Periodic Reconciler

```text
┌────────────────────────────────────────────────────────┐
│ CHAIN SUBSCRIBER:                                      │
│ • Incremental event processing per round.              │
│ • Follows live block progression.                      │
└────────────────────────────────────────────────────────┘
                           +
┌────────────────────────────────────────────────────────┐
│ BLOCKCHAIN RECONCILER:                                 │
│ • Periodic independent state audit.                    │
│ • Compares cached SQLite tables against Algorand L1.   │
│ • Detects drift (e.g. transfers outside our frontend). │
│ • Can run in AUDIT / REPORT ONLY or REPAIR mode.       │
└────────────────────────────────────────────────────────┘
```

---

## 2. External Transfer Discovery

When a user transfers an AlgoRacers NFT directly inside Pera Wallet without using our UI:
1. Algorand L1 records the `axfer` transaction.
2. The Indexer / Subscriber catches the transfer in the next polling window.
3. The Reconciler independently confirms that the on-chain holder has changed.
4. The database projection updates `current_owner` to the recipient wallet.
