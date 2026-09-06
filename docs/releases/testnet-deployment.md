# AlgoRacers — TestNet Deployment Runbook

---

## 1. Step-by-Step Deployment Procedure

1. **Verify CI Quality Gates**: Ensure all automated GitHub Actions checks are green.
2. **Generate Release Manifest**: Execute `python backend/scripts/generate_release_manifest.py` and inspect artifact digests.
3. **Database Snapshot**: Run `python backend/scripts/backup_db.py` to create a pre-release backup.
4. **Deploy Backend & Workers**: Deploy the immutable container image matching the manifest digest.
5. **Contract Upgrades (If Applicable)**: Submit a governance proposal (`GOV-XXX`). Require 2-of-3 Multisig Council signatures before execution.
6. **Run Smoke Tests**: Execute `python backend/scripts/verify_release.py`.
7. **Run Post-Deploy Audit**: Execute `python backend/scripts/audit_release.py` to verify zero configuration drift.
