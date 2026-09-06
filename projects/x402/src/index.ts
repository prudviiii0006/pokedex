import { Hono } from "hono";
import { cors } from "hono/cors";
import { serve } from "@hono/node-server";
import { paymentMiddleware } from "@x402/hono";
import { x402ResourceServer, HTTPFacilitatorClient, RoutesConfig } from "@x402/core/server";
import { ExactAvmScheme } from "@x402/avm/exact/server";
import { ALGORAND_TESTNET_CAIP2, ALGORAND_TESTNET_GENESIS_HASH, USDC_TESTNET_ASA_ID } from "@x402/avm";
import { paymentService } from "./services/paymentService.js";
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

// Enable Global CORS for all origins and headers
app.use(
  "*",
  cors({
    origin: "*",
    allowHeaders: ["*"],
    allowMethods: ["GET", "POST", "OPTIONS", "HEAD", "PUT", "DELETE"],
    exposeHeaders: ["*", "PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "WWW-Authenticate"],
  })
);

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

// 5. Pack Purchase Flow Routes
app.get("/pay/requirements/:purchase_id", async (c) => {
  const purchaseId = c.req.param("purchase_id");
  try {
    const purchase = await paymentService.getPurchaseDetails(purchaseId);
    const challenge = paymentService.buildPaymentChallenge(purchase, c.req.url);
    c.header(
      "WWW-Authenticate",
      `x402 scheme="exact", network="${ALGORAND_TESTNET_CAIP2}", asset="USDC", asset_id="${USDC_TESTNET_ASA_ID}", amount="${purchase.price_usdc}", payTo="${avmAddress}"`
    );
    c.header("PAYMENT-REQUIRED", Buffer.from(JSON.stringify(challenge)).toString("base64"));
    return c.json(challenge, 402);
  } catch (err: any) {
    return c.json({ error: "invalid_request", message: err.message }, 400);
  }
});

app.post("/pay/purchases/:purchase_id", async (c) => {
  const purchaseId = c.req.param("purchase_id");
  const paymentProof =
    c.req.header("payment-signature") ||
    c.req.header("x-402-payment-proof") ||
    c.req.header("authorization");

  try {
    const purchase = await paymentService.getPurchaseDetails(purchaseId);

    // If unpaid, return official x402 402 challenge
    if (!paymentProof) {
      const challenge = paymentService.buildPaymentChallenge(purchase, c.req.url);
      c.header(
        "WWW-Authenticate",
        `x402 scheme="exact", network="${ALGORAND_TESTNET_CAIP2}", asset="USDC", asset_id="${USDC_TESTNET_ASA_ID}", amount="${purchase.price_usdc}", payTo="${avmAddress}"`
      );
      c.header("PAYMENT-REQUIRED", Buffer.from(JSON.stringify(challenge)).toString("base64"));
      return c.json(challenge, 402);
    }

    // Forward settlement confirmation to FastAPI
    const body = await c.req.json().catch(() => ({}));
    const confirmUrl = `${process.env.FASTAPI_BASE_URL || "http://127.0.0.1:8000"}/internal/purchases/${encodeURIComponent(purchaseId)}/payment-confirmed`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-402-Payment-Proof": paymentProof,
      "Payment-Signature": paymentProof,
    };
    if (c.req.header("authorization")) {
      headers["Authorization"] = c.req.header("authorization")!;
    }

    const res = await fetch(confirmUrl, {
      method: "POST",
      headers,
      body: JSON.stringify({
        payment_tx_id: body.payment_tx_id || "tx_x402_settled",
        payment_proof: paymentProof,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      return c.json(data, res.status as any);
    }

    c.header("PAYMENT-RESPONSE", Buffer.from(JSON.stringify({ status: "settled", purchase_id: purchaseId })).toString("base64"));
    return c.json({
      success: true,
      message: "x402 payment settled and pack fulfilled by FastAPI",
      purchase_id: purchaseId,
      receipt: data,
    }, 200);
  } catch (err: any) {
    return c.json({ error: "payment_failed", detail: err.message }, 400);
  }
});

app.post("/pay/packs/:pack_id", async (c) => {
  const packId = c.req.param("pack_id");
  const paymentProof =
    c.req.header("payment-signature") ||
    c.req.header("x-402-payment-proof") ||
    c.req.header("authorization");

  try {
    const body = await c.req.json().catch(() => ({}));
    const walletAddress = body.wallet_address || avmAddress;
    const idempotencyKey = body.idempotency_key || `x402_${Date.now()}_${packId}`;

    // If unpaid, return official x402 402 challenge
    if (!paymentProof) {
      const price = packId === "premium" ? 0.05 : 0.01;
      const microUnits = Math.round(price * 1_000_000);
      const challenge = {
        error: "payment_required",
        message: `Access to resource requires payment of ${price} USDC on Algorand TestNet.`,
        protocol: "x402/2.0",
        payment_requirements: {
          scheme: "exact",
          network: ALGORAND_TESTNET_CAIP2,
          asset: "USDC",
          asset_id: USDC_TESTNET_ASA_ID,
          amount: price,
          amount_units: `${microUnits} microUSDC (ASA ID: ${USDC_TESTNET_ASA_ID})`,
          payTo: avmAddress,
          resource: c.req.url,
          facilitator: facilitatorUrl,
          pack_id: packId,
          expiration_seconds: 300,
        },
      };

      c.header(
        "WWW-Authenticate",
        `x402 scheme="exact", network="${ALGORAND_TESTNET_CAIP2}", asset="USDC", asset_id="${USDC_TESTNET_ASA_ID}", amount="${price}", payTo="${avmAddress}"`
      );
      c.header("PAYMENT-REQUIRED", Buffer.from(JSON.stringify(challenge)).toString("base64"));
      return c.json(challenge, 402);
    }

    const url = `${process.env.FASTAPI_BASE_URL || "http://127.0.0.1:8000"}/packs/${encodeURIComponent(packId)}/purchase`;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-402-Payment-Proof": paymentProof,
      "Payment-Signature": paymentProof,
    };
    if (c.req.header("authorization")) {
      headers["Authorization"] = c.req.header("authorization")!;
    }

    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        wallet_address: walletAddress,
        idempotency_key: idempotencyKey,
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      return c.json(data, res.status as any);
    }

    c.header("PAYMENT-RESPONSE", Buffer.from(JSON.stringify({ status: "settled", pack_id: packId })).toString("base64"));
    return c.json({
      success: true,
      message: "x402 payment settled and pack fulfilled by FastAPI",
      receipt: data,
    }, 200);
  } catch (err: any) {
    return c.json({ error: "payment_failed", detail: err.message }, 400);
  }
});

// 6. Handler for /test-payment when paid
app.get("/test-payment", (c) => {
  return c.json({
    status: "success",
    message: "Payment verified by x402 V2! Resource unlocked.",
    unlocked_at: new Date().toISOString(),
  });
});

// 7. Start HTTP Server on port 4021
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
