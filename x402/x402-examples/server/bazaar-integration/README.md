# x402 Bazaar Integration Example

**Role:** Resource server demonstrating GoPlausible Bazaar discovery catalog integration.

## What It Does

This server shows how to:
1. Declare discovery metadata per endpoint.
2. Register the Bazaar extension to enrich 402 responses.
3. Expose endpoints to the public discovery marketplace.

After a real payment settles against a public URL, endpoints are automatically cataloged in the [Bazaar](https://facilitator.goplausible.xyz/discovery/resources) so agents and buyers can autonomously discover and call them.

## Structure

Three paid endpoints with discovery metadata:

| Endpoint | Method | Price | Pattern | Example |
|----------|--------|-------|---------|---------|
| `/weather` | GET | $0.001 | GET with output schema | City, temperature, condition |
| `/forecast` | GET | $0.005 | GET returning array | 5-day forecast data |
| `/analyze` | POST | $0.002 | POST with input + output schema | Text sentiment analysis |

Plus `/health` (free, no payment required).

## Quick Start

### Installation

```bash
pnpm install
```

### Configuration

Create `.env`:
```
AVM_ADDRESS=your_algorand_address_here
FACILITATOR_URL=http://localhost:4022
PORT=4021
```

### Run

```bash
pnpm start
```

Runs at `http://localhost:4021`.

## Verify Locally

Check that the 402 response includes Bazaar discovery metadata:

```bash
curl -s -D - http://localhost:4021/weather 2>&1 | grep '^payment-required:' | sed 's/payment-required: //' | base64 -d | jq '.extensions.bazaar'
```

You should see:
```json
{
  "info": { "input": {...}, "output": {...} },
  "schema": { "properties": {...} }
}
```

## Deploy & List

1. **Deploy to public URL** (e.g., Railway, Vercel, Fly.io)
   - Set environment variables on the hosted service
   - Ensure the facilitator can reach the public deployment

2. **Settle a real payment per endpoint** against your public URL
   ```bash
   cd ../client/fetch && SELLER_URL=https://<your-app> pnpm start
   ```
   Each settlement adds that endpoint to the Bazaar catalog.

3. **Verify listing:**
   ```bash
   curl 'https://facilitator.goplausible.xyz/discovery/resources?limit=100' \
     | jq '.[] | select(.resourceUrl | contains("<your-app>"))'
   ```

## Environment

| Variable | Description | Example |
| --- | --- | --- |
| `AVM_ADDRESS` | Algorand address receiving payments | `T24X7CCVMN...` |
| `FACILITATOR_URL` | Facilitator service endpoint | `http://localhost:4022` |
| `PORT` | HTTP port for this server | `4021` |

## Full Local End-to-End

Start each in a separate terminal:

```bash
# Terminal 1: Facilitator
cd ../facilitator/basic
pnpm install && pnpm start

# Terminal 2: Bazaar server
cd server/bazaar-integration
pnpm install && pnpm start

# Terminal 3: Client (makes payments)
cd ../client/fetch
pnpm install && pnpm start
```
