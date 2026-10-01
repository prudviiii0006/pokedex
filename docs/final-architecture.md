# Pokédex — Final System Architecture

```text
                                  USER BROWSER
                                       │
                                       ▼
                        ┌─────────────────────────────┐
                        │     Pokédex Frontend UI     │
                        │    (React + TypeScript)     │
                        └──────────────┬──────────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        │     Pera Wallet Connector   │
                        │   (Non-Custodial Signer)    │
                        └──────────────┬──────────────┘
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │       FastAPI REST Service        │
                     │  (Observability + TestNet Guard)  │
                     └─────────────────┬─────────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│  x402 Protocol   │          │   Race Engine    │          │  AI Race Coach   │
│ Purchase Handler │          │  (8-Car Multi)   │          │  (Constrained)   │
└────────┬─────────┘          └────────┬─────────┘          └────────┬─────────┘
         │                             │                             │
         │ Verify & Settle             │ Owned Driver Lookup         │ Telemetry Payment
         ▼                             ▼                             ▼
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│ x402 Facilitator │          │  SQLite Database │          │ x402 Telemetry   │
│ (AVM Ed25519)    │          │ (Races & Audits) │          │ ($0.01 TestNet)  │
└────────┬─────────┘          └──────────────────┘          └──────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ALGORAND TESTNET LAYER-1                              │
│  • USDC Payment Verification (ASA #10458941)                                 │
│  • ARC-3 Driver NFT Minting & Delivery                                       │
│  • Immutable Ownership Ledger                                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Trust Boundaries & Component Responsibilities

1. **User Client (Untrusted)**:
   - Initiates wallet connection and signs transactions locally.
   - Cannot self-declare stats, NFT ownership, or payment status.

2. **FastAPI Application (Trusted Logic)**:
   - Validates all request payloads using Pydantic.
   - Enforces spending caps, idempotency keys, and TestNet guards.
   - Executes 8-car Grand Prix simulations off-chain.

3. **Algorand TestNet (Decentralized Ground Truth)**:
   - Maintains definitive ledger of ASA balances and NFT holdings.
   - Verifies ed25519 cryptographic signatures on payment transactions.
