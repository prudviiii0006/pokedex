# AlgoRacers — Key Management & Operational Security Policy

---

## 1. Independent Security Domains Principle

* **Zero Shared Secrets**: Signer keys MUST NOT reside on the same host, database, or `.env` file.
* **Environment Separation**: LocalNet, TestNet, and future production signers use mutually disjoint key pairs.
* **No Server-Side Storing of Council Keys**: Backend REST coordinator only prepares unsigned proposals and collects partial signatures.

---

## 2. Algorand Rekeying vs. Direct Multisig

```text
┌────────────────────────────────────────────────────────┐
│ DIRECT MULTISIG ADMIN:                                 │
│ Contract stores Multisig address as admin.             │
│ Transacting requires 2-of-3 signatures directly.       │
│ Preferred for transparent, stateless access control.  │
└────────────────────────────────────────────────────────┘
                           vs.
┌────────────────────────────────────────────────────────┐
│ REKEYED ACCOUNT:                                       │
│ Account address stays A, authorized by auth-addr M.    │
│ Rekeying is NOT recursive (A->B, B->C does not mean A  │
│ is authorized by C). Pre-flight checks must verify.   │
└────────────────────────────────────────────────────────┘
```
