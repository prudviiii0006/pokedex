# AlgoRacers — Smart Contract Upgrade & Deletion Policy

---

## 1. Contract-by-Contract Immutability vs Upgradeability

| Smart Contract | Policy | Deletable? | Authorization Mechanism |
| :--- | :--- | :--- | :--- |
| **Collection Registry** | **IMMUTABLE** | **NO** | Permanent Genesis L1 metadata anchor. |
| **Season Registry** | **IMMUTABLE** | **NO** | Historical season roots must remain permanent. |
| **Tournament Smart Contract** | **UPGRADEABLE** | **DEV ONLY** | Requires 2-of-3 Multisig bytecode hash review. |
| **NFT Minter & Delivery** | **IMMUTABLE** | **NO** | Non-custodial ASA opt-in & transfer logic. |

---

## 2. Supply-Chain & Bytecode Verification

Before signers approve `UpdateApplication`:
1. Compile TEAL approval and clear state programs from audited source.
2. Compute SHA-256 digest of both programs.
3. Compare against the bytecode hash committed in the Governance Proposal.
4. Verify zero unexpected `rekey_to` or `close_remainder_to` fields.
