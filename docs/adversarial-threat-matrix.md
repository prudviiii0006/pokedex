# AlgoRacers — Adversarial Testing & Security Checklist

---

## 1. Adversarial Test Results Matrix

| Attack Vector | Simulated Payload / Action | Expected Result | Pass / Fail |
| :--- | :--- | :--- | :--- |
| **Address Checksum Tampering** | `3VZQ...N2XX` (Invalid checksum) | `HTTP 400 Bad Request` | **PASS** |
| **SSRF Injection via IPFS CID** | `http://169.254.169.254/latest/` | `HTTP 400 Bad Request` | **PASS** |
| **Path Traversal via Circuit ID** | `../../etc/passwd` | `HTTP 400 Bad Request` | **PASS** |
| **Volumetric Flood** | 10 rapid auth requests | `HTTP 429 Too Many Requests` | **PASS** |
| **Oversized Request Entity** | `Content-Length: 2MB` | `HTTP 413 Payload Too Large` | **PASS** |
| **Idempotency Parameter Tamper** | Same key + altered circuit ID | `HTTP 400 Bad Request` | **PASS** |
| **SQL Injection in Query Params** | `' OR '1'='1` in wallet query | Parameterized query (Safe) | **PASS** |

---

## 2. Production Security Checklist

- [x] ed25519 Cryptographic Wallet Signatures Enforced
- [x] Server-Side Algorand Asset Ownership Verified
- [x] Sliding-Window Rate Limiting with `Retry-After`
- [x] Security Headers (CSP, nosniff, DENY) Injected
- [x] Request Body Size Capped at 1MB
- [x] SSRF-Safe IPFS CID Validation
- [x] Path Traversal Defenses on All File Handlers
- [x] Zero Private Keys or Mnemonics in Logs/Database
- [x] 2-of-3 Multisig Admin Authorization Enforced
