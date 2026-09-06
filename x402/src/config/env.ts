import dotenv from "dotenv";
import { z } from "zod";

dotenv.config();

const envSchema = z.object({
  PORT: z.coerce.number().default(4020),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  FASTAPI_BASE_URL: z.string().url().default("http://127.0.0.1:8000"),
  FACILITATOR_URL: z.string().url().default("https://facilitator.goplausible.xyz"),
  ALGORAND_NETWORK: z.enum(["testnet", "algorand-testnet"]).default("testnet"),
  ALGORAND_TESTNET_CAIP2: z.string().default("algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOKE="),
  TESTNET_USDC_ASSET_ID: z.coerce.number().default(10458941),
  PAYMENT_RECEIVER_ADDRESS: z.string().min(58).max(58).default("3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM"),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error("❌ Invalid x402 Environment Configuration:", parsed.error.format());
  throw new Error("Invalid x402 Environment Configuration");
}

export const env = parsed.data;

// Strict Safeguard: Assert Algorand TestNet only
if (env.ALGORAND_NETWORK !== "testnet" && env.ALGORAND_NETWORK !== "algorand-testnet") {
  throw new Error(
    `🚨 CRITICAL SECURITY ERROR: x402 service configured for '${env.ALGORAND_NETWORK}'. Only Algorand TestNet is permitted.`
  );
}
