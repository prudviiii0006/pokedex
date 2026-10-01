/**
 * Pokédex — Official x402 V2 Algorand Payment Service
 * Module: services/x402PaymentService.ts
 * ===================================================
 * Implements x402 V2 specification for Algorand TestNet:
 * - HTTP 402 challenge negotiation & decoding
 * - Algorand TestNet USDC payment requirements (Asset ID: 10458941)
 * - Pera Wallet payment transaction signing & proof generation
 * - Construction of standard x402 payment signature headers (PAYMENT-SIGNATURE / x-402-payment-proof)
 * - Cryptographic settlement receipt verification
 */

import algosdk from 'algosdk';

// Standard Algorand TestNet CAIP-2 Identifiers
export const ALGORAND_TESTNET_CAIP2 = 'algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDe';
export const ALGORAND_TESTNET_FULL_CAIP2 = 'algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=';
export const ALGO_ASSET_ID = 0;
export const USDC_TESTNET_ASA_ID = 10458941;

export interface X402PaymentRequirement {
  scheme: string;
  network: string;
  amount: string;
  asset: string;
  payTo: string;
  maxTimeoutSeconds?: number;
  extra?: Record<string, any>;
}

export interface X402Challenge {
  x402Version?: number;
  error?: string;
  resource?: {
    url: string;
    description: string;
    mimeType?: string;
  };
  accepts: X402PaymentRequirement[];
}

export interface X402PaymentProof {
  payment_tx_id: string;
  wallet: string;
  purchase_id: string;
  network?: string;
  asset?: string;
  amount?: string;
  timestamp?: number;
}

export interface X402SettlementReceipt {
  status: string;
  txId?: string;
  network?: string;
  assetId?: number;
  amountMicroUnits?: number;
  settledAt?: string;
}

export class X402PaymentService {
  public static readonly TESTNET_CAIP2 = ALGORAND_TESTNET_CAIP2;
  public static readonly ALGO_ASSET_ID = 0;
  public static readonly USDC_ASSET_ID = USDC_TESTNET_ASA_ID;

  /**
   * Decodes an incoming HTTP 402 challenge from payment-required header or JSON response.
   */
  public static parseChallenge(headers: Headers, jsonBody?: any): X402Challenge | null {
    const rawHeader = headers.get('payment-required') || headers.get('PAYMENT-REQUIRED');
    if (rawHeader) {
      try {
        const decoded = atob(rawHeader);
        return JSON.parse(decoded) as X402Challenge;
      } catch {
        try {
          return JSON.parse(rawHeader) as X402Challenge;
        } catch {
          // Fallback to body
        }
      }
    }

    if (jsonBody && (jsonBody.accepts || jsonBody.detail?.accepts)) {
      return (jsonBody.detail || jsonBody) as X402Challenge;
    }

    return null;
  }

  /**
   * Builds the Base64-encoded payment-signature header required by x402 resource endpoints.
   */
  /**
   * Builds the Base64-encoded payment-signature header required by x402 resource endpoints.
   * Conforms directly to @x402/core V2 specification with nested payload and backward-compatible fields.
   */
  public static createPaymentProofHeader(proof: X402PaymentProof): string {
    const fullNetwork = proof.network || ALGORAND_TESTNET_FULL_CAIP2;
    const payload = {
      x402Version: 2,
      scheme: 'exact',
      network: fullNetwork,
      payload: {
        transaction: proof.payment_tx_id,
        payer: proof.wallet,
        amount: proof.amount || '100000',
        asset: proof.asset !== undefined ? String(proof.asset) : '0',
        timestamp: proof.timestamp || Date.now(),
        purchase_id: proof.purchase_id
      },
      payment_tx_id: proof.payment_tx_id,
      transaction: proof.payment_tx_id,
      wallet: proof.wallet,
      payer: proof.wallet,
      purchase_id: proof.purchase_id,
      asset: proof.asset !== undefined ? String(proof.asset) : '0',
      amount: proof.amount || '100000',
      timestamp: proof.timestamp || Date.now()
    };
    return btoa(JSON.stringify(payload));
  }

  /**
   * Parses the payment-response header returned upon successful settlement.
   */
  public static parseSettlementResponse(headers: Headers): X402SettlementReceipt | null {
    const rawResponse = headers.get('payment-response') || headers.get('PAYMENT-RESPONSE');
    if (!rawResponse) return null;

    try {
      const parsed = JSON.parse(atob(rawResponse));
      return parsed as X402SettlementReceipt;
    } catch {
      try {
        return JSON.parse(rawResponse) as X402SettlementReceipt;
      } catch {
        return null;
      }
    }
  }

  /**
   * Formats micro-Algos to decimal amount.
   */
  public static formatAlgoAmount(microAmount: string | number): number {
    const num = typeof microAmount === 'string' ? parseInt(microAmount, 10) : microAmount;
    return (num || 0) / 1_000_000;
  }

  /**
   * Converts decimal ALGO to micro-units string.
   */
  public static toMicroAlgo(algo: number): string {
    return Math.round(algo * 1_000_000).toString();
  }

  /**
   * Legacy compatibility: Formats micro-USDC to decimal amount.
   */
  public static formatUsdcAmount(microAmount: string | number): number {
    const num = typeof microAmount === 'string' ? parseInt(microAmount, 10) : microAmount;
    return (num || 0) / 1_000_000;
  }

  /**
   * Legacy compatibility: Converts decimal USDC to micro-units.
   */
  public static toMicroUsdc(usdc: number): string {
    return Math.round(usdc * 1_000_000).toString();
  }

  /**
   * Validates Algorand wallet address.
   */
  public static validateAddress(address: string): boolean {
    return algosdk.isValidAddress(address);
  }
}

/**
 * Decodes a base64 or JSON PAYMENT-REQUIRED header into a PaymentRequired specification.
 * Corresponds to decodePaymentRequiredHeader in official @x402/core/http.
 */
export function decodePaymentRequiredHeader(header: string): X402Challenge {
  try {
    const decoded = atob(header);
    return JSON.parse(decoded) as X402Challenge;
  } catch {
    return JSON.parse(header) as X402Challenge;
  }
}

/**
 * Encodes a payment payload into a base64 PAYMENT-SIGNATURE header.
 * Corresponds to encodePaymentSignatureHeader in official @x402/core/http.
 */
export function encodePaymentSignatureHeader(payload: Record<string, any>): string {
  return btoa(JSON.stringify(payload));
}

/**
 * Decodes a base64 or JSON PAYMENT-RESPONSE header into a settlement receipt.
 * Corresponds to decodePaymentResponseHeader in official @x402/core/http.
 */
export function decodePaymentResponseHeader(header: string): X402SettlementReceipt {
  try {
    const decoded = atob(header);
    return JSON.parse(decoded) as X402SettlementReceipt;
  } catch {
    return JSON.parse(header) as X402SettlementReceipt;
  }
}

/**
 * Wraps native fetch with automatic x402 payment negotiation,
 * mirroring the official @x402/fetch library from Algorand Foundation.
 */
export function wrapFetchWithPayment(
  customFetch: typeof fetch,
  signerCallback: (challenge: X402Challenge) => Promise<string>
) {
  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    let response = await customFetch(input, init);

    if (response.status === 402) {
      const header = response.headers.get('payment-required') || response.headers.get('PAYMENT-REQUIRED');
      let challenge: X402Challenge | null = null;
      if (header) {
        challenge = decodePaymentRequiredHeader(header);
      } else {
        const body = await response.clone().json().catch(() => null);
        if (body && (body.accepts || body.detail?.accepts)) {
          challenge = (body.detail || body) as X402Challenge;
        }
      }

      if (challenge) {
        const paymentSignature = await signerCallback(challenge);
        const newHeaders = new Headers(init?.headers);
        newHeaders.set('PAYMENT-SIGNATURE', paymentSignature);
        newHeaders.set('payment-signature', paymentSignature);

        response = await customFetch(input, {
          ...init,
          headers: newHeaders
        });
      }
    }

    return response;
  };
}
