# AlgoRacers — Championship Seasons & Lifecycle Specification

---

## 1. Architectural Distinction: Race vs. Tournament vs. Season

```text
┌────────────────────────────────────────────────────────┐
│ RACE:        A single 8-car race simulation on a circuit.│
│ TOURNAMENT:  An on-chain competitive event with drivers.│
│ SEASON:      A championship series of verified rounds. │
└────────────────────────────────────────────────────────┘
```

---

## 2. Season Lifecycle State Machine

```text
  [ DRAFT ] ──────────> [ OPEN ] ──────────> [ ACTIVE ]
 (Configured)       (Rounds Added)       (Tournaments Running)
                                                   │
                                                   ▼
 [ FINALIZED ] <─────────────────────────── [ CLOSING ]
(Root Committed)                         (No New Rounds)
```

* **DRAFT**: Season is defined (scoring engine, total rounds).
* **OPEN**: Tournament rounds are assigned.
* **ACTIVE**: Players enter tournaments and compete.
* **CLOSING**: No additional tournament rounds may be added.
* **FINALIZED**: All tournament results verified, canonical snapshot generated, Merkle root permanently committed on Algorand.

---

## 3. Championship Points Matrix (`v1`)

Configured in [backend/data/season_scoring_v1.json](file:///Users/prudvi/Programming%20/projects/algoracers/backend/data/season_scoring_v1.json):

| Position | Championship Points |
| :---: | :---: |
| **P1 (1st)** | 25 |
| **P2 (2nd)** | 18 |
| **P3 (3rd)** | 15 |
| **P4 (4th)** | 12 |
| **P5 (5th)** | 10 |
| **P6 (6th)** | 8 |
| **P7 (7th)** | 6 |
| **P8 (8th)** | 4 |

---

## 4. Deterministic Multi-Tier Tie-Breaking Rules

When two or more players accumulate identical championship points, ties are broken strictly deterministically:
1. **Total Championship Points** (Descending)
2. **Total Race Wins** (Descending)
3. **Total Podium Finishes** (Descending)
4. **Best Individual Finish Position** (Ascending rank: e.g. P1 beats P2)
5. **Algorand Wallet Address** (Ascending Lexicographical byte order)
