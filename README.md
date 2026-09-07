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

## x402 Algorand TestNet Payment Protocol

AlgoRacers integrates native **x402 V2 Algorand TestNet USDC micropayments** to protect premium tactical data and Grand Prix circuit intelligence without requiring web3 logins or subscription models.

### Architecture Flow

```text
Frontend / Wallet
       ↓
Protected AlgoRacers API
       ↓
HTTP 402
       ↓
x402 payment
       ↓
Algorand TestNet USDC
       ↓
x402 facilitator
       ↓
Payment receiver
       ↓
AlgoRacers API
```

### Protected Endpoint & Parameters

| Parameter | Value |
| :--- | :--- |
| **Protected Endpoint** | `GET /api/v1/premium-analysis` (alias: `GET /premium-analysis`) |
| **Resource Title** | Apex Grand Prix — Sector Telemetry & Pit Delta Intelligence |
| **Payment Asset** | TestNet USDC (`ASA ID: 10458941`) |
| **Price** | `$0.01 TestNet USDC` (`10,000` micro-units) |
| **Payment Scheme** | `exact` |
| **Network (CAIP-2)** | `algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=` |
| **Payment Receiver (`payTo`)** | `GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4` |
| **Facilitator URL** | `https://facilitator.goplausible.xyz` |

### Environment Variables

Ensure your backend `.env` contains the following:

```env
ALGORAND_NETWORK=testnet
ALGOD_ADDRESS=https://testnet-api.algonode.cloud
ALGOD_TOKEN=
INDEXER_ADDRESS=https://testnet-idx.algonode.cloud
INDEXER_TOKEN=

PAYMENT_RECEIVER_ADDRESS=GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4
TREASURY_ADDRESS=GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4
MINTER_ADDRESS=3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM

X402_FACILITATOR_URL=https://facilitator.goplausible.xyz
X402_PAY_TO=GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4
X402_PAYMENT_ASSET=10458941
FASTAPI_BASE_URL=http://localhost:8000
```

### How to Start the Project

1. **Start FastAPI Backend**:
```bash
cd projects/backend
PYTHONPATH=. python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

2. **Start React Frontend**:
```bash
cd projects/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

### How to Test the x402 Flow

1. **Run Automated Test Suite (188+ tests)**:
```bash
pytest projects/backend/tests/test_x402_payments.py -v
```

2. **Run End-to-End Verification Script**:
```bash
python3 projects/backend/scripts/test_x402_payment.py
```

### Protocol Execution Details

1. **Client requests protected resource**:
   - `GET /api/v1/premium-analysis`
2. **Server responds with HTTP 402**:
   - Status: `402 Payment Required`
   - Headers: `payment-required: <base64-challenge>`, `WWW-Authenticate: x402`
3. **Client creates payment proof**:
   - Signs TestNet USDC transaction (Asset ID `10458941`, amount `10000`, receiver `GZSTVC3KHF3QQ77CCQFHXL3CYFCM4ANFRJOIC3TUHQKI2STM25BC7IAZU4`).
4. **Client retries with payment signature**:
   - `GET /api/v1/premium-analysis` with header `payment-signature: <base64-payload>`
5. **Server verifies, settles & enforces replay protection**:
   - Verifies via GoPlausible Facilitator & Algorand TestNet ledger.
   - Enforces single-use transaction ID via SQLite settlement ledger (`x402_settlements`).
6. **Server returns HTTP 200 OK**:
   - Headers: `payment-response: <base64-receipt>`
   - Body: Unlocked telemetry & tactical AI insight response.

