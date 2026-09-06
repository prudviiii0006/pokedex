# AlgoRacers — Wallet Authentication & Cryptographic Sessions Specification

---

## 1. Why Wallet Connection $\ne$ Authentication

In Web3 applications, connecting a non-custodial wallet (e.g. Pera Wallet) merely exposes the user's **public address** to the frontend. A public address is openly broadcast on the blockchain and can be queried or typed by anyone.

Treating an address in a request body as proof of identity creates a massive impersonation vulnerability:

$$\text{Attacker submits: } \{\text{"wallet\_address": "VictimAddress"}\} \implies \text{VIOLATION}$$

To establish genuine authentication, the backend requires cryptographic proof that the requester possesses the private key corresponding to that address.

---

## 2. Challenge-Response Authentication Protocol

```text
USER BROWSER                       FASTAPI BACKEND                      PERA WALLET
    │                                     │                                  │
    │ 1. POST /auth/challenge             │                                  │
    │    { wallet_address: "3VZQ..." }    │                                  │
    │────────────────────────────────────>│                                  │
    │                                     │ 2. Generate secure nonce (16 B)  │
    │                                     │    Create challenge (5m TTL)     │
    │                                     │    Store status: PENDING         │
    │ 3. Return ChallengeResponse         │                                  │
    │    { challenge_id, nonce, msg }     │                                  │
    │<────────────────────────────────────│                                  │
    │                                                                        │
    │ 4. Request user data signature                                         │
    │───────────────────────────────────────────────────────────────────────>│
    │                                                                        │
    │ 5. Return ed25519 signature bytes                                      │
    │<───────────────────────────────────────────────────────────────────────│
    │                                     │                                  │
    │ 6. POST /auth/verify                │                                  │
    │    { challenge_id, sig, address }   │                                  │
    │────────────────────────────────────>│                                  │
    │                                     │ 7. Fetch stored challenge        │
    │                                     │ 8. Check expiration & PENDING    │
    │                                     │ 9. Verify ed25519 signature      │
    │                                     │ 10. Mark challenge = USED        │
    │                                     │ 11. Create session (24h TTL)     │
    │ 12. AuthResponse + HttpOnly Cookie  │                                  │
    │<────────────────────────────────────│                                  │
```

---

## 3. Challenge Structure & Domain Separation

The authentication message is strictly bound to the application domain, network, unique random nonce, and expiration timestamp:

```text
Sign in to AlgoRacers
Address: 3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM
Nonce: 4f9a1c8b3e2d7a6f9b1c3e5a7d9b2c4e
Domain: algoracers.app
Network: algorand-testnet
Issued At: 2026-08-30T15:40:00Z
Expires At: 2026-08-30T15:45:00Z
```

### Why Domain & Network Binding Matter:
* **Anti-Phishing**: A malicious site cannot trick a user into signing a generic message and replay it on `algoracers.app`.
* **Network Isolation**: Prevents signing on TestNet from having any validity on MainNet.
* **Single-Use Nonce**: Protects against replay attacks; once verified, the challenge transitions from `PENDING` $\to$ `USED`.

---

## 4. Layered Security Architecture

| Security Layer | Responsibility | Mechanism |
| :--- | :--- | :--- |
| **Authentication** | "Who are you?" | ed25519 cryptographic signature over server challenge |
| **Authorization & Ownership** | "What are you allowed to do?" | Direct Algorand Layer-1 holding verification |
| **Payment Settlement** | "Did the required payment occur?" | x402 TestNet USDC transaction verification |

---

## 5. Replay & Spoofing Defenses

1. **Replay Attack Defense**: Re-submitting an already verified `challenge_id` fails with `HTTP 409 Conflict`.
2. **Identity Spoofing Defense**: Protected endpoints prioritize the wallet address stored in the verified session cookie over any client-provided `request.body.wallet_address`.
3. **Session Revocation**: Calling `POST /auth/logout` immediately marks the session as `is_active = 0` in SQLite.
