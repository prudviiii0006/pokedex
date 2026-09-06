# AlgoRacers — Rollback, Roll-Forward & Disaster Recovery Runbook

---

## 1. Classification of Changes & Recovery Strategies

| Change Category | Rollback Feasible? | Recovery Strategy |
| :--- | :--- | :--- |
| **Stateless API Backend** | **Yes** | Re-deploy previous container image digest immediately. |
| **Backward-Compatible DB** | **Yes** | Re-deploy previous backend image (old code ignores new columns). |
| **Breaking DB Migration** | **No** | Forward-fix with remedial migration or restore pre-deploy backup. |
| **Published Merkle Root** | **No** | Blockchain-irreversible. Submit corrective governance proposal. |
| **Minted NFT / Claim** | **No** | Blockchain-irreversible. Correct state via new on-chain transaction. |

---

## 2. Emergency Incident Response Procedure

1. **Detect**: Monitor `/health`, `/ready`, and API 5xx error spikes via automated alerting.
2. **Halt**: Stop background worker pools and pause active pack sales if payment integrity is impacted.
3. **Assess**: Determine if failure is stateless (API bug) or stateful (database / contract).
4. **Execute**: For stateless bugs, rollback container image. For stateful/blockchain errors, deploy roll-forward fix.
