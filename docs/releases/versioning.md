# AlgoRacers — Semantic Versioning & Release Provenance

---

## 1. Semantic Versioning Specification (`vMAJOR.MINOR.PATCH`)

* **MAJOR**: Breaking API schema, contract ABI incompatibility, or irreversible rule overhaul.
* **MINOR**: New game modes, circuits, drivers, or additive non-breaking database models.
* **PATCH**: Bug fixes, security patches, rate limit adjustments, or documentation updates.

---

## 2. Build Metadata & Public Version Discovery

Every deployment exposes `GET /version` and `GET /config/public`:
```json
{
  "version": "0.24.0",
  "git_commit": "c89f1a2e",
  "build_timestamp": "2026-08-30T18:00:00Z",
  "environment": "staging",
  "network": "testnet",
  "database_revision": "v24_postgres_security",
  "race_engine_version": "v1.0.0",
  "contract_version": "arc56_v2_multisig"
}
```
