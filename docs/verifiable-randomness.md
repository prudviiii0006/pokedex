# AlgoRacers — Verifiable Randomness, VRFs & Tournament Integrity Specification

---

## 1. The Core Trust Problem in Online Racing

In traditional gaming backends, races rely on server-side pseudo-random number generators:

$$\text{seed} = \text{random.random}() \implies \text{Simulate Race} \implies \text{Commit Result}$$

This architecture creates a severe **grinding/reroll vulnerability**:
* The server operator can simulate 100 private races with different seeds.
* The operator only commits the result of the seed that favors their preferred driver or sponsored team.
* Even if the server commits the final result hash to a smart contract, **the players cannot verify whether the seed was selected fairly**.

---

## 2. The Solution: Commit-First, Reveal-Later Architecture

AlgoRacers solves this using a **Commit-First, Reveal-Later Protocol** backed by the **Algorand Randomness Beacon** (AVM VRF):

```text
              TOURNAMENT CONTRACT
                       │
                Registration closes (Round R)
                       │
                       ▼
             Fixed participants locked
             Fixed circuit locked
             Fixed algorithm v1 locked
                       │
                       ▼
           Commit future round N = R + 8
                       │
                       ▼
            ALGORAND RANDOMNESS BEACON
                       │
             VRF output (32 bytes)
                       │
                       ▼
                MASTER SEED
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Qualifying       Race           Incidents
     sub-seed      sub-seed         sub-seeds
        │              │              │
        └──────────────┼──────────────┘
                       ▼
             DETERMINISTIC RACE ENGINE v1
                       │
                       ▼
                 FULL RESULT
                       │
                       ▼
                RESULT HASH
                       │
                       ▼
             ON-CHAIN FINALIZATION
```

---

## 3. Master Seed & Domain Separation

$$\text{seed\_material} = \text{"AlgoRacersMasterSeed\_v1:"} + \text{beacon\_randomness} + \text{app\_id} + \text{canonical\_participants} + \text{circuit\_id} + \text{"v1"}$$
$$\text{master\_race\_seed} = \text{SHA256}(\text{seed\_material})$$

### Domain-Separated Sub-Seeds:
1. **CPU Grid Selection**: $\text{SHA256}(\text{master\_seed} + \text{":cpu\_selection"})$
2. **Driver Variance**: $\text{SHA256}(\text{master\_seed} + \text{":driver\_variance:"} + \text{asset\_id})$

---

## 4. Public Independent Verification & Avalanche Effect

Any participant or third-party observer can independently audit a finalized tournament:

```bash
python backend/scripts/verify_tournament.py 75001234
```

1. Queries on-chain locked parameters (`participants`, `circuit_id`, `randomness_round`, `randomness_value`, `race_engine_version`).
2. Re-runs `DeterministicRaceEngineV1` from scratch using these exact inputs.
3. Computes the canonical SHA-256 result hash.
4. Compares against the smart contract's committed `result_hash`.

If a single byte of randomness, a participant's stat, or a driver position is altered, the SHA-256 **avalanche effect** guarantees that `recalculated_hash != on_chain_hash`.
