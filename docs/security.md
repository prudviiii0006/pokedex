# AlgoRacers — Security Specification & Threat Model

> [!WARNING]
> **Learning & TestNet Project Notice**:
> AlgoRacers is built as an educational demonstration of Algorand Layer-1 ASAs, the x402 payment protocol, and assistive AI agents. It operates exclusively on Algorand TestNet and has not undergone a formal third-party security audit.

---

## 1. Threat Matrix & Countermeasures

| Asset / Component | Threat Vector | Attack Scenario | Implemented Security Control |
| :--- | :--- | :--- | :--- |
| **x402 Payment Settlement** | Replay Attack | Submitting an old valid transaction ID to unlock multiple packs | Server stores unique `payment_tx_id` in SQLite; duplicates rejected with `HTTP 409 Conflict`. |
| **NFT Delivery** | Duplicate Minting | Double-clicking the purchase button | Idempotency keys lock purchase records; duplicate requests return existing NFT without re-minting. |
| **Race Simulation** | Stat Forgery | Client submits forged `speed: 100` | Frontend only supplies `asset_id`; backend verifies ownership on Algorand and loads trusted template stats. |
| **AI Agent Telemetry** | Prompt Injection | Malicious telemetry text contains instructions to drain funds | Model is never given wallet private keys. Spending is constrained in Python code ($0.01 max, TestNet USDC only). |
| **API Endpoints** | MainNet Leak | Production misconfiguration using real funds | Startup guardrail checks `settings.NETWORK` and aborts boot if MainNet is detected. |
| **Server Logs** | Secret Leakage | Logging user mnemonics or API tokens | Loggers sanitize inputs; Request ID correlation middleware strips authorization headers. |

---

## 2. Principle of Least Privilege in AI Agent Design

* **No Custodial Access**: The AI model has no access to signing keys, seed phrases, or raw blockchain accounts.
* **Human-in-the-Loop Consent**: The agent cannot purchase x402 telemetry without explicit checkbox authorization from the user.
* **Hardcoded Spending Caps**: Max payment per tool call is hardcoded at $0.01\text{ USDC}$ ($10,000\text{ microUSDC}$).
