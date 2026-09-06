# AlgoRacers — API Security & Adversarial Threat Model

---

## 1. Core Security Principle: Never Trust the Client

```text
INTERNET
   │
   ▼
ATTACKER (Flooding, Replay, Spoofed Wallet, SSRF, Traversal)
   │
   ▼
REQUEST BOUNDARY (1MB Request Size Limit)
   │
   ▼
SECURITY HEADERS (CSP, nosniff, DENY, X-Request-ID)
   │
   ▼
RATE LIMITING (Sliding Window per IP/Wallet)
   │
   ▼
AUTHENTICATION (Session ed25519 Signature Verification)
   │
   ▼
AUTHORIZATION & ON-CHAIN OWNERSHIP (ASA holding, Multisig Governance)
   │
   ▼
INPUT HARDENING (Checksum validation, Safe CID, Identifier regex)
   │
   ▼
BUSINESS LOGIC & PERSISTENCE (Idempotent state machine)
```

---

## 2. STRIDE Threat Matrix for AlgoRacers

| STRIDE Category | Attack Scenario | Defensive Control |
| :--- | :--- | :--- |
| **Spoofing** | Attacker claims to be Wallet A in JSON request body. | Session challenge requires ed25519 signature verified against Algorand base32 public key. |
| **Tampering** | Replaying idempotency key with altered circuit/driver parameters. | Request payload SHA-256 fingerprint matching rejects altered parameters. |
| **Repudiation** | User claims they did not initiate a season reward claim. | Proof verification ties claim to on-chain authenticated transaction. |
| **Information Disclosure** | Path traversal (`../../.env`) or error stack trace exposure. | Strict identifier allowlist (`SAFE_IDENTIFIER_REGEX`) + sanitized global exception handler. |
| **Denial of Service** | Flooding auth challenge endpoints or sending 500MB JSON. | Sliding window rate limiting + 1MB max body limit (`HTTP 413`). |
| **Elevation of Privilege** | User submits `FINALIZE_SEASON` or contract update proposal. | 2-of-3 Multisig Governance Council authority enforced on-chain. |
