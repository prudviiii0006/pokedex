# AlgoRacers — Rate Limiting & Abuse Prevention Policy

---

## 1. Sliding Window Rate Limiting Tiers

| Scope / Endpoint | Rate Limit Threshold | Window | Keying Strategy | Violation Response |
| :--- | :--- | :--- | :--- | :--- |
| **Auth Challenge (`/auth/challenge`)** | **5 requests** | 60 sec | Per IP | `HTTP 429` (`Retry-After`) |
| **Purchases (`/packs/basic/purchase`)** | **10 requests** | 60 sec | Per Wallet | `HTTP 429` (`Retry-After`) |
| **Race Execution (`/races/start`)** | **20 requests** | 60 sec | Per Wallet | `HTTP 429` (`Retry-After`) |
| **Public Queries (`/circuits`, `/leaderboard`)**| **100 requests** | 60 sec | Per IP | `HTTP 429` (`Retry-After`) |

---

## 2. Mass Assignment & Server-Owned Fields

* **Client Provided**: `circuit_id`, `driver_id`, display preferences, `Idempotency-Key`.
* **Server & Chain Owned**: `purchase_status`, `payment_tx_id`, `rarity`, `asset_id`, `position`, `final_score`, `leaderboard_root`, `is_admin`.
* Client inputs attempting to override server-owned fields are discarded by strict Pydantic schemas.
