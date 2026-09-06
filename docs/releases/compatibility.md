# AlgoRacers — Cross-Version Compatibility & Migration Guidelines

---

## 1. Expand / Contract Deployment Pattern

To ensure zero-downtime rolling deployments without breaking active API instances or background workers:

```text
Phase 1 (Expand):
  • Apply additive, nullable database migration.
  • Old code and new code both run safely against the database.

Phase 2 (Deploy):
  • Deploy new backend API and background worker image.
  • Code begins writing to new columns and processing versioned jobs.

Phase 3 (Contract):
  • Backfill legacy rows.
  • Apply non-null constraint and drop deprecated columns in subsequent release.
```

---

## 2. Race Engine & Scoring Immutability

* Historical verified tournament results remain permanently tied to the exact engine version (`v1.0.0`) used during their simulation.
* Releasing Race Engine `v2.0.0` updates future races without recalculating historical results.
