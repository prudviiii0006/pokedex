# AlgoRacers — Independent Season Verification Specification

---

## 1. Multi-Layered Season Verification Pipeline

```text
┌────────────────────────────────────────────────────────┐
│ 1. DATA INTEGRITY:                                     │
│    • Verify IPFS Manifest CID matches bytes.           │
│    • Verify Merkle leaf hashes resolve to root.        │
│                                                        │
│ 2. SCORING CORRECTNESS:                                │
│    • Pull raw tournament result hashes.                │
│    • Re-run points aggregation under scoring_version.  │
│    • Re-apply tie-breaking rules.                      │
│    • Re-derive canonical Merkle root.                  │
│    • Compare recomputed root == on-chain committed root!│
└────────────────────────────────────────────────────────┘
```

---

## 2. Canonical Snapshot Leaf Encoding

$$\text{leaf\_data} = \text{"ALGORACERS_SEASON_LEADERBOARD_V1:"} + \text{canonical\_json}(\text{record})$$

Example Leaf Record:
```json
{
  "points": 68,
  "podiums": 3,
  "rank": 1,
  "season_id": "season_2026_01",
  "wallet_address": "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
  "wins": 2
}
```
