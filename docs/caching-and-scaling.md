# AlgoRacers — Safe Caching, Invalidation & Horizontal Scaling

---

## 1. Safe Cache Candidates vs. Mutable Data

| Data Category | Caching Policy | Invalidation Trigger |
| :--- | :--- | :--- |
| **IPFS Metadata (by CID)** | **Aggressive (Indefinite TTL)** | Immutable content hash. |
| **Circuit & Pack Configs** | **Long TTL (24 hours)** | App redeployment. |
| **Finalized Season Roots** | **Indefinite TTL** | Immutable once finalized. |
| **Active NFT Ownership** | **DO NOT CACHE AGGRESSIVELY** | Short TTL / Invalidate on `NFT_TRANSFERRED`. |
| **Purchase Payment State** | **NEVER CACHE** | Real-time database query. |

---

## 2. Horizontal FastAPI Stateless Scaling

Multiple FastAPI API instances behind a load balancer share the central PostgreSQL database. No session or state mutation resides in local process memory.
