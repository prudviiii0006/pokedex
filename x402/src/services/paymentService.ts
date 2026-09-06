import { env } from "../config/env.js";

export interface TrustedPurchaseInfo {
  purchase_id: string;
  pack_id: string;
  wallet_address: string;
  price_usdc: number;
  currency: string;
  status: string;
  payment_status: string;
}

export interface PaymentChallengeResponse {
  error: "payment_required";
  message: string;
  protocol: "x402/2.0";
  payment_requirements: {
    scheme: "exact";
    network: string;
    asset: string;
    asset_id: number;
    amount: number;
    amount_units: string;
    payTo: string;
    resource: string;
    facilitator: string;
    purchase_id: string;
    expiration_seconds: number;
  };
}

export class PaymentService {
  private fastapiBaseUrl: string;

  constructor() {
    this.fastapiBaseUrl = env.FASTAPI_BASE_URL.replace(/\/+$/, "");
  }

  /**
   * Fetches trusted purchase and pricing requirements directly from FastAPI.
   * x402 never decides prices or creates packs.
   */
  async getPurchaseDetails(purchaseId: string): Promise<TrustedPurchaseInfo> {
    const url = `${this.fastapiBaseUrl}/purchases/${encodeURIComponent(purchaseId)}`;
    
    try {
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Purchase '${purchaseId}' not found in FastAPI backend.`);
        }
        throw new Error(`FastAPI returned HTTP ${response.status} when querying purchase.`);
      }

      const data = (await response.json()) as any;
      return {
        purchase_id: data.purchase_id,
        pack_id: data.pack_id,
        wallet_address: data.wallet_address,
        price_usdc: Number(data.price_usdc),
        currency: data.currency || "USDC",
        status: data.status,
        payment_status: data.payment_status || "UNPAID",
      };
    } catch (err: any) {
      // If purchase record is not yet initialized, attempt to query pack pricing from FastAPI
      throw new Error(`Failed to fetch trusted payment requirements from FastAPI: ${err.message}`);
    }
  }

  /**
   * Constructs an official x402 V2 Algorand TestNet payment challenge.
   */
  buildPaymentChallenge(
    purchase: TrustedPurchaseInfo,
    resourcePath: string
  ): PaymentChallengeResponse {
    const microUnits = Math.round(purchase.price_usdc * 1_000_000);

    return {
      error: "payment_required",
      message: `Access to resource requires payment of ${purchase.price_usdc} USDC on Algorand TestNet.`,
      protocol: "x402/2.0",
      payment_requirements: {
        scheme: "exact",
        network: env.ALGORAND_TESTNET_CAIP2,
        asset: "USDC",
        asset_id: env.TESTNET_USDC_ASSET_ID,
        amount: purchase.price_usdc,
        amount_units: `${microUnits} microUSDC (ASA ID: ${env.TESTNET_USDC_ASSET_ID})`,
        payTo: env.PAYMENT_RECEIVER_ADDRESS,
        resource: resourcePath,
        facilitator: env.FACILITATOR_URL,
        purchase_id: purchase.purchase_id,
        expiration_seconds: 300,
      },
    };
  }

  /**
   * Forwards settlement verification and fulfillment request to FastAPI.
   * FastAPI handles RewardEngine, NFT minting, and database updates.
   */
  async notifyFastAPISettlement(
    purchase: TrustedPurchaseInfo,
    paymentProof: string,
    authorization?: string
  ): Promise<any> {
    const url = `${this.fastapiBaseUrl}/packs/${encodeURIComponent(purchase.pack_id)}/purchase`;

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-402-Payment-Proof": paymentProof,
    };

    if (authorization) {
      headers["Authorization"] = authorization;
    }

    const res = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        wallet_address: purchase.wallet_address,
        idempotency_key: `x402_${purchase.purchase_id}`,
      }),
    });

    if (!res.ok) {
      const err = (await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))) as any;
      throw new Error(err?.detail || `FastAPI failed to process payment settlement (HTTP ${res.status})`);
    }

    return await res.json();
  }
}

export const paymentService = new PaymentService();
