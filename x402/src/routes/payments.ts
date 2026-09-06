import { Router, Request, Response } from "express";
import { env } from "../config/env.js";
import { paymentService } from "../services/paymentService.js";

export const paymentRouter = Router();

/**
 * Health Check Endpoint
 * GET /health
 */
paymentRouter.get("/health", (_req: Request, res: Response) => {
  res.status(200).json({
    status: "ok",
    service: "algoracers-x402",
    version: "2.0.0",
    network: "testnet",
    caip2: env.ALGORAND_TESTNET_CAIP2,
    asset: "USDC",
    asset_id: env.TESTNET_USDC_ASSET_ID,
    facilitator: env.FACILITATOR_URL,
    receiver: env.PAYMENT_RECEIVER_ADDRESS,
    fastapi_target: env.FASTAPI_BASE_URL,
    timestamp: new Date().toISOString(),
  });
});

/**
 * Get Trusted x402 V2 Payment Requirements for a Purchase ID
 * GET /pay/requirements/:purchase_id
 */
paymentRouter.get("/pay/requirements/:purchase_id", async (req: Request, res: Response) => {
  const { purchase_id } = req.params;

  try {
    const purchase = await paymentService.getPurchaseDetails(purchase_id);
    const challenge = paymentService.buildPaymentChallenge(purchase, req.originalUrl);

    // Standard x402 V2 Response Headers
    res.setHeader(
      "WWW-Authenticate",
      `x402 scheme="exact", network="${env.ALGORAND_TESTNET_CAIP2}", asset="USDC", asset_id="${env.TESTNET_USDC_ASSET_ID}", amount="${purchase.price_usdc}", payTo="${env.PAYMENT_RECEIVER_ADDRESS}"`
    );
    res.setHeader("X-402-Version", "2.0");
    res.setHeader("X-402-Network", env.ALGORAND_TESTNET_CAIP2);
    res.setHeader("X-402-Asset-ID", String(env.TESTNET_USDC_ASSET_ID));

    return res.status(402).json(challenge);
  } catch (err: any) {
    return res.status(400).json({
      error: "invalid_request",
      message: err.message,
    });
  }
});

/**
 * Protected x402 Payment Route for Pack Purchase
 * POST /pay/packs/:purchase_id
 */
paymentRouter.post("/pay/packs/:purchase_id", async (req: Request, res: Response) => {
  const { purchase_id } = req.params;
  const paymentProof =
    (req.headers["x-402-payment-proof"] as string) ||
    (req.headers["payment-signature"] as string) ||
    (req.headers["authorization"] as string);

  try {
    // 1. Fetch trusted purchase metadata from FastAPI
    const purchase = await paymentService.getPurchaseDetails(purchase_id);

    // 2. If no payment proof is presented, issue HTTP 402 challenge
    if (!paymentProof) {
      const challenge = paymentService.buildPaymentChallenge(purchase, req.originalUrl);

      res.setHeader(
        "WWW-Authenticate",
        `x402 scheme="exact", network="${env.ALGORAND_TESTNET_CAIP2}", asset="USDC", asset_id="${env.TESTNET_USDC_ASSET_ID}", amount="${purchase.price_usdc}", payTo="${env.PAYMENT_RECEIVER_ADDRESS}"`
      );
      res.setHeader("X-402-Version", "2.0");
      res.setHeader("X-402-Network", env.ALGORAND_TESTNET_CAIP2);

      return res.status(402).json(challenge);
    }

    // 3. Forward settlement proof to FastAPI for server-authoritative fulfillment
    const fulfillmentReceipt = await paymentService.notifyFastAPISettlement(
      purchase,
      paymentProof,
      req.headers["authorization"] as string | undefined
    );

    return res.status(200).json({
      success: true,
      message: "x402 payment settled and pack fulfilled by FastAPI",
      purchase_id: purchase.purchase_id,
      receipt: fulfillmentReceipt,
    });
  } catch (err: any) {
    return res.status(400).json({
      error: "payment_failed",
      detail: err.message,
    });
  }
});
