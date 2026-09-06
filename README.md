# AlgoRacers 🏎️⚡

**Collect. Fuse. Trade. Race.**

AlgoRacers is a high-performance Algorand Web3 collectible racing game and decentralized application, structured as an official **AlgoKit Workspace** following the latest Algorand Developer Portal best practices.

---

## AlgoKit Workspace

The repository is managed by **AlgoKit** (`v2.0+`) as a multi-project workspace. The root configuration file `.algokit.toml` organizes subprojects under the `projects/` directory:

- **`projects/smart-contracts/`**: Algorand Python (`algopy`) smart contracts built with Puya and deployed via AlgoKit deploy scripts.
- **`projects/frontend/`**: React 18 + TypeScript + Vite motorsport dashboard with Pera Wallet integration.
- **`projects/backend/`**: FastAPI backend managing the game loop, race engine, NFT metadata verification, and database persistence.
- **`projects/x402/`**: Standalone x402 V2 payment service for Algorand TestNet USDC micropayments.

---

## Project Structure

```text
algoracers/
├── .algokit.toml              # Root AlgoKit workspace configuration
├── .gitignore
├── .env.example
├── README.md
│
├── projects/
│   ├── smart-contracts/      # AlgoKit Python smart contract project
│   │   ├── .algokit.toml     # Contract project configuration
│   │   ├── pyproject.toml    # Python dependencies (algorand-python, puyapy, algokit-utils)
│   │   ├── smart_contracts/
│   │   │   ├── algoracers_registry/
│   │   │   │   ├── contract.py        # Algorand Python ARC-4 contract
│   │   │   │   └── deploy_config.py   # Deployment logic
│   │   │   └── artifacts/             # Generated TEAL, ARC-56 JSON, typed clients
│   │   └── README.md
│   │
│   ├── frontend/             # React + TypeScript + Vite web client
│   │   ├── .algokit.toml     # Frontend project configuration
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── src/              # Dashboard, Pera Wallet, UI components
│   │   └── .env.example
│   │
│   ├── backend/              # FastAPI game backend
│   │   ├── .algokit.toml     # Backend project configuration
│   │   ├── requirements.txt
│   │   ├── app/              # Routes, services, database models
│   │   ├── rewards/          # Driver pool & reward engine
│   │   ├── scripts/          # Chain sync & verification scripts
│   │   ├── tests/            # Pytest test suite (188 tests)
│   │   └── .env.example
│   │
│   └── x402/                 # Standalone x402 V2 payment service
│       ├── package.json
│       ├── tsconfig.json
│       ├── src/              # Payment routes & verification
│       └── .env.example
│
├── blockchain/               # Collection metadata, ARC-3 schemas & assets
│   ├── metadata/
│   └── scripts/
│
└── docs/                     # Architectural specifications & test vectors
```

---

## Prerequisites

- **Python**: `3.12+` or `3.14+`
- **Node.js**: `v20+` & `npm` / `pnpm`
- **AlgoKit CLI**: `v2.0.0+` (`brew install algorandfoundation/tap/algokit` or `pipx install algokit`)
- **Docker**: Docker Desktop or Docker Engine (required for LocalNet)

---

## Bootstrap

To verify workspace discovery and project registration:

```bash
# Verify AlgoKit installation
algokit --version

# List registered subprojects in workspace
algokit project list
```

---

## LocalNet

Start the local Algorand development environment (Algod + Indexer + Conduit):

```bash
# Start LocalNet containers
algokit localnet start

# Inspect health and status
algokit localnet status

# Open Algorand Lorer / Explore UI
algokit explore

# Stop LocalNet when finished
algokit localnet stop
```

LocalNet default endpoints:
- **Algod**: `http://localhost:4001` (Token: `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`)
- **Indexer**: `http://localhost:8980`

---

## Build Smart Contracts

Compile all Algorand Python smart contracts to TEAL using Puya:

```bash
# Build contracts across workspace
algokit project run build

# Or directly in smart-contracts project
cd projects/smart-contracts
poetry run python -m smart_contracts build
```

---

## Generated Artifacts

Compiling smart contracts outputs deterministic build artifacts to `projects/smart-contracts/smart_contracts/artifacts/<contract_name>/`:

| Artifact | Description |
| :--- | :--- |
| `*.approval.teal` | AVM bytecode assembly for application approval logic. |
| `*.clear.teal` | AVM bytecode assembly for application clear state logic. |
| `*.arc56.json` | ARC-56 application specification including ABI methods, events, and storage schema. |
| `*.puya.map` | Source mapping between Algorand Python source lines and generated TEAL opcodes. |
| `*_client.py` | Strongly-typed Python client generated from ARC-56 spec for type-safe deployments and calls. |

> [!IMPORTANT]
> Generated artifacts should be treated as build output. Never manually edit generated TEAL or typed client files to alter business logic; modify the Algorand Python source contract and rebuild.

---

## Deploy LocalNet

Deploy the compiled smart contract to LocalNet using the generated deployment configuration:

```bash
# Deploy to LocalNet
algokit project deploy localnet

# Or inside smart-contracts project
cd projects/smart-contracts
poetry run python -m smart_contracts deploy
```

---

## Run FastAPI

Start the backend API server:

```bash
cd projects/backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Run test suite:

```bash
cd projects/backend
python3 -m pytest tests
```

---

## Run Frontend

Start the React + TypeScript frontend development server:

```bash
cd projects/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Build for production:

```bash
cd projects/frontend
npm run build
```

---

## x402 Status

The x402 payment module is maintained as an isolated service in `projects/x402/`:
- **Current State**: Structural foundation created with official `@x402/avm` and `@x402/core` packages.
- **Role**: Handles Algorand TestNet USDC payment requirements via HTTP 402 Payment Required status.
- **Migration Note**: Kept isolated as a standalone workspace component. Integration can be resumed after workspace verification.

---

## TestNet Parameters & Configuration

| Parameter | Value |
| :--- | :--- |
| **Algorand Network** | TestNet (`https://testnet-api.algonode.cloud`) |
| **Payment Receiver (Treasury)** | `3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM` |
| **Minter / Operator Account** | `3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM` |
| **TestNet USDC ASA ID** | `10458941` (6 Decimals, 1 USDC = 1,000,000 $\mu$USDC) |
| **x402 Facilitator URL** | `https://facilitator.goplausible.xyz` |

To configure projects for Algorand TestNet:
1. Update `projects/backend/.env` with `ALGOD_ADDRESS=https://testnet-api.algonode.cloud`, `TREASURY_ADDRESS=3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM`, and `X402_PAY_TO=3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM`.
2. Update `projects/x402/.env` with `PAYMENT_RECEIVER_ADDRESS=3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM`.
3. Update `projects/frontend/.env` with `VITE_NETWORK=testnet` and `VITE_PAYMENT_RECEIVER_ADDRESS=3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM`.

