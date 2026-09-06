# AlgoRacers — Emergency Response & Governance Incident Checklist

---

## 1. Emergency Pause Scope

* **Permitted During Pause**:
  - Halting creation of new tournaments
  - Halting season finalizations
  - Halting credential claims during active vulnerability investigation
* **UNPAUSABLE Invariants**:
  - Historical tournament records remain inspectable
  - Public Merkle proof verification remains functional
  - IPFS content addressing remains immutable

---

## 2. Compromised Signer Playbook (e.g. Signer A)

1. **Immediate Quarantine**: Council members B and C reject all pending proposals signed by A.
2. **Derive Replacement Multisig**: Form new 2-of-3 Council `[Signer B, Signer C, Signer D]`.
3. **Execute Admin Migration**: Signers B and C use remaining 2-of-3 authority to transfer contract admin to the new multisig.
4. **Publish Incident Report**: Document the root cause and transparently verify new on-chain authority.
