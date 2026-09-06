import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { paymentMiddleware } from "@x402/hono";
import { x402ResourceServer, HTTPFacilitatorClient, RoutesConfig } from "@x402/core/server";
import { ExactAvmScheme } from "@x402/avm/exact/server";
import { ALGORAND_TESTNET_CAIP2, ALGORAND_TESTNET_GENESIS_HASH, USDC_TESTNET_ASA_ID } from "@x402/avm";
import dotenv from "dotenv";

dotenv.config();

const port = Number(process.env.PORT || 4021);
const facilitatorUrl = process.env.FACILITATOR_URL || "https://facilitator.goplausible.xyz";
const avmAddress = process.env.AVM_ADDRESS;

// Security Guardrail: Check for valid public address and fail closed if missing
if (!avmAddress) {
  console.error("🚨 CRITICAL ERROR: AVM_ADDRESS is required in environment.");
  process.exit(1);
}

// Security Guardrail: Assert Algorand TestNet ONLY (Fail closed on MainNet)
const networkConfig = process.env.ALGORAND_NETWORK || "testnet";
if (networkConfig !== "testnet" && networkConfig !== "algorand-testnet") {
  console.error(`🚨 CRITICAL SECURITY ERROR: Network '${networkConfig}' is not Algorand TestNet. Failing closed.`);
  process.exit(1);
}

const app = new Hono();

// 1. Health Check Endpoint (Unprotected)
app.get("/health", (c) => {
  return c.json({
    status: "ok",
    service: "algoracers-x402",
    network: "algorand-testnet",
  });
});

// Full CAIP-2 Genesis Identifier advertised by GoPlausible facilitator
const TESTNET_NETWORK = `algorand:${ALGORAND_TESTNET_GENESIS_HASH}` as const;

// 2. Setup x402 V2 Resource Server & Facilitator Client
const facilitatorClient = new HTTPFacilitatorClient({
  url: facilitatorUrl,
});

const resourceServer = new x402ResourceServer(facilitatorClient)
  .register(ALGORAND_TESTNET_CAIP2, new ExactAvmScheme())
  .register(TESTNET_NETWORK as any, new ExactAvmScheme())
  .register("algorand:*" as any, new ExactAvmScheme());

// 3. Define Protected Routes Configuration (Official x402 V2 Exact Scheme)
const routes: RoutesConfig = {
  "GET /test-payment": {
    accepts: [
      {
        scheme: "exact",
        network: TESTNET_NETWORK as any,
        payTo: avmAddress,
        price: "$0.001",
      },
    ],
    description: "AlgoRacers x402 V2 Test Payment",
    mimeType: "application/json",
  },
};

// 4. Apply Official x402 Payment Middleware
app.use(paymentMiddleware(routes, resourceServer));

// 5. Handler for /test-payment when paid
app.get("/test-payment", (c) => {
  return c.json({
    status: "success",
    message: "Payment verified by x402 V2! Resource unlocked.",
    unlocked_at: new Date().toISOString(),
  });
});

// 6. Start HTTP Server on port 4021
serve(
  {
    fetch: app.fetch,
    port: port,
  },
  (info) => {
    console.log("=".repeat(70));
    console.log("🏎️  ALGORACERS — OFFICIAL x402 V2 RESOURCE SERVER");
    console.log("=".repeat(70));
    console.log(`🌐 Server Port:       http://localhost:${info.port}`);
    console.log(`⛓️  Algorand Network:  TESTNET (${ALGORAND_TESTNET_CAIP2})`);
    console.log(`💰 Payment Asset:     TestNet USDC (ASA ID: ${USDC_TESTNET_ASA_ID})`);
    console.log(`🏦 Receiver Address:  ${avmAddress}`);
    console.log(`📡 Facilitator URL:   ${facilitatorUrl}`);
    console.log("=".repeat(70));
    console.log(`Ready: GET /health (200) | GET /test-payment (402 Protected)`);
  }
);

export default app;
