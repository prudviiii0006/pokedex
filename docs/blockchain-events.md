# AlgoRacers — Blockchain Event Catalog & Identity Specification

---

## 1. Supported On-Chain Domain Events

| Event Type | Source Transaction | Payload Parameters | Projection Effect |
| :--- | :--- | :--- | :--- |
| `NFT_TRANSFERRED` | `axfer` (ASA transfer) | `asset_id, sender, receiver, amount` | Updates cached owner & tracks external transfers. |
| `NFT_MINTED` | `acfg` (ASA creation) | `asset_id, creator, unit_name` | Reconciles new collectible mints. |
| `TOURNAMENT_FINALIZED` | `appl` (`finalize_race`) | `app_id, result_hash, winner_asset_id` | Marks tournament finalized in SQLite. |
| `SEASON_FINALIZED` | `appl` (`finalize_season`) | `app_id, leaderboard_root, manifest_cid` | Permanently locks season standings. |
| `REWARD_CLAIMED` | `appl` (`claim_reward`) | `app_id, claimer, reward_id` | Delivers trophy credential & marks claimed. |
| `GOVERNANCE_ACTION_EXECUTED` | `appl` (multisig sender) | `app_id, method, council_address` | High-severity security log entry. |

---

## 2. Event Identity & Idempotency Rule

$$\text{chain\_event\_id} = \text{"chain_evt_" + network + "_" + tx_id + "_" + event_type}$$

Database unique constraint: `UNIQUE(network, tx_id, event_type)` ensures duplicate deliveries from Indexer polling result in zero duplicate database effects.
