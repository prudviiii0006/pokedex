# AlgoRacers — Multisig Governance & Privileged Access Control Model

---

## 1. Threat Model & Single-Key Risk Mitigation

```text
┌────────────────────────────────────────────────────────┐
│ SINGLE-KEY RISK:                                       │
│ • 1 Private Key controls season roots & contracts.     │
│ • Key theft = Complete application compromise.         │
└────────────────────────────────────────────────────────┘
                           vs.
┌────────────────────────────────────────────────────────┐
│ PROTOCOL-NATIVE 2-OF-3 MULTISIG:                       │
│ • 3 Independent Signers (Operations, Security, Backup) │
│ • Threshold = 2 signatures required.                   │
│ • 1 compromised key alone is powerless.                │
│ • Consensus-enforced on Algorand L1 directly.          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Privileged Operations Authority Matrix

| Operation | Previous Authority | New Governance Authority | Security Rationale |
| :--- | :--- | :--- | :--- |
| **Publish Collection Merkle Root** | Single Developer Key | **2-of-3 Multisig Council** | Root fixes immutable collection hash & stats. |
| **Finalize Championship Season** | Single Backend Key | **2-of-3 Multisig Council** | Finalizes season rankings & enables NFT claims. |
| **Emergency System Pause / Resume** | Single Admin Key | **2-of-3 Multisig Council** | Fast containment without unilateral takeover. |
| **Admin Key Rotation** | Deployer Account | **2-of-3 Multisig Council** | Prevents rogue admin lockout. |
| **Contract Code Upgrade** | Single Admin Key | **2-of-3 Multisig Council** | Highest privilege; bytecode hash pre-verified. |
| **Normal Gameplay / Pack Purchase** | User Wallet | **User Wallet (Direct Pera)** | Least privilege; users own their gameplay. |

---

## 3. 2-of-3 Governance Council Configuration

* **Protocol Version**: `1`
* **Threshold**: `2`
* **Signer A (Operations)**: `3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM`
* **Signer B (Security Council)**: `6ZIJOSUKH5HY6OK3GLLAP4AAV6GMOJDIECUI7VSQLRQFFWB2LGD6BI5MII`
* **Signer C (Recovery Operator)**: `MPZ7KZHZDGCQV6HSTOC2YQ2JMZMXBRVPUPSAQAVDZG2VUX62N2B2FI7TZA`
* **Multisig Account Address**: `7WZ2NDYPKXU2Q7EMVHG4F53RWZRK4JA7YA26ZPGQXVZOR7UHWYIZOB3INA`
