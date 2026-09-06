# AlgoRacers — Player Progression, XP Ledger & Competitive Reputation Specification

---

## 1. Core Architectural Separation

```text
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│  PLAYER STATS   │   │   PROGRESSION   │   │   REPUTATION    │   │  ACHIEVEMENTS   │
│  races: 42      │   │   XP: 2,450     │   │   Elo: 1,064    │   │  7 Unlocked     │
│  wins: 7        │   │   Level: 12     │   │   Tier: Gold    │   │  1 On-Chain     │
└─────────────────┘   └─────────────────┘   └─────────────────┘   └─────────────────┘
```

| Concept | Authority Layer | Storage Layer | Description |
| :--- | :--- | :--- | :--- |
| **Player Stats** | Derived from records | SQLite `races`, `tournaments` | Aggregated race counts, win rates, podiums. |
| **XP & Level** | Application Event Engine | SQLite `progression_events` Ledger | Participation and gameplay experience points. |
| **Competitive Reputation** | Verified Tournament Engine | SQLite `reputation_events` Ledger | Elo-style competitive ranking score and tier. |
| **Achievements** | Rule-Based Engine | SQLite `player_achievements` | Milestone accomplishments (permanent and state-based). |
| **On-Chain Credential** | Algorand Layer-1 | Algorand ASA / ARC-71 Badge | Non-transferable cryptographic badge for prestigious wins. |

---

## 2. XP Rules & Deterministic Level Formula

### XP Balance Matrix (`backend/data/progression.json`):
* **Race Completion**: $+20\text{ XP}$
* **Podium Finish (P2/P3)**: $+15\text{ Bonus XP}$
* **Grand Prix Victory (P1)**: $+25\text{ Bonus XP}$
* **Tournament Participation**: $+40\text{ XP}$
* **Tournament Championship Victory**: $+100\text{ Bonus XP}$

### Deterministic Level Formula:
$$\text{Level}(XP) = 1 + \left\lfloor \sqrt{\frac{XP}{50}} \right\rfloor$$
$$\text{XP Threshold for Level } L = 50 \times (L - 1)^2$$
$$\text{Next Level Threshold } (L+1) = 50 \times L^2$$

---

## 3. Strict Idempotency & Progression Audit Ledger

$$\text{UNIQUE}(\text{source\_type}, \text{source\_id}, \text{wallet\_address})$$

Every XP grant is appended to `progression_events`. If a race result or tournament retry is processed multiple times, duplicate XP is blocked at the database constraint level.

---

## 4. Competitive Elo Reputation System

* Initial Baseline: $1000\text{ Rating}$ ($K = 32$).
* Calculated **exclusively on verified tournaments** with committed VRF randomness:
  - **P1 (Winner)**: $+32$
  - **P2 (Podium)**: $+16$
  - **P3 (Podium)**: $+8$
  - **P4–P5 (Top 5)**: $0$
  - **P6–P8 (Midfield/Backmarker)**: $-8\text{ to }-16$

### Competitive Rank Tiers:
* $\ge 1400$: **Master**
* $\ge 1200$: **Diamond**
* $\ge 1100$: **Platinum**
* $\ge 1000$: **Gold**
* $\ge 900$: **Silver**
* $< 900$: **Bronze**
