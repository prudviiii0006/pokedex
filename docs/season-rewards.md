# AlgoRacers — Merkle Proof Reward Claims & Security Specification

---

## 1. Proof-Based Claim Security Pipeline

```text
┌────────────────────────────────────────────────────────┐
│ 1. Sender Binding:                                     │
│    Txn.sender MUST equal record.wallet_address.        │
│                                                        │
│ 2. Cryptographic Proof:                                │
│    verify_merkle_proof(record, proof, leaderboard_root)│
│                                                        │
│ 3. Rank Eligibility:                                   │
│    SEASON_CHAMPION_TROPHY -> Rank == 1                 │
│    SEASON_PODIUM_BADGE    -> Rank <= 3                 │
│                                                        │
│ 4. Double-Claim Prevention:                            │
│    UNIQUE(season_id, wallet_address, reward_id)       │
└────────────────────────────────────────────────────────┘
```
