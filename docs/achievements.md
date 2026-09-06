# AlgoRacers — Achievement Catalog & On-Chain Credential Specification

---

## 1. Achievement Catalog & Rules

| Achievement ID | Name | Category | Trigger Type | Threshold | Credential Policy |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `FIRST_GRID` | First Grid Entry | Racing | `COUNT_RACES` | 1 | Off-Chain |
| `FIRST_PODIUM` | First Podium | Racing | `COUNT_PODIUMS` | 1 | Off-Chain |
| `FIRST_VICTORY` | First Victory | Racing | `COUNT_WINS` | 1 | Off-Chain |
| `TEN_RACES` | Track Veteran | Racing | `COUNT_RACES` | 10 | Off-Chain |
| `WET_WEATHER_MASTER`| Wet Weather Master | Mastery | `COUNT_WET_WINS` | 3 | Off-Chain |
| `TOURNAMENT_ROOKIE` | Tournament Rookie | Competitive | `COUNT_TOURNAMENTS_ENTERED` | 1 | Off-Chain |
| `TOURNAMENT_CHAMPION`| Tournament Champion | Competitive | `COUNT_TOURNAMENTS_WON` | 1 | **On-Chain Badge (ARC-71)** |
| `GARAGE_BUILDER` | Garage Builder | Collection | `OWNERSHIP_COUNT` | 3 | Off-Chain (State-based) |
| `LEGEND_COLLECTOR` | Legend Collector | Collection | `OWN_RARITY` | 1 | Off-Chain (State-based) |

---

## 2. On-Chain Credential Architecture (ARC-71 Non-Transferable ASA)

```text
                  VERIFIED TOURNAMENT
                           │
                 Winner confirmed on-chain
                           │
                           ▼
                  ACHIEVEMENT ENGINE
                           │
               TOURNAMENT_CHAMPION unlocked
                           │
                           ▼
                  CREDENTIAL SERVICE
                           │
             Mint ARC-71 Non-Transferable ASA
             (Clawback/Freeze locked to recipient)
                           │
                           ▼
                     WINNER WALLET
```

### Why Non-Transferable Badges Matter:
If achievement badges were standard transferable ASAs, a champion could sell their badge on a secondary marketplace, allowing unranked players to pose as champions and destroying credential authenticity.

---

## 3. Public Verification Endpoint

`GET /achievements/{achievement_id}/verify?wallet={wallet_address}`

Audits the achievement record, source event ID, and on-chain credential state, returning a verified status response.
