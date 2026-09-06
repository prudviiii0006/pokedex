import { wrapFetchWithPayment, x402Client } from "@x402/fetch";
import { ExactAvmScheme, toClientAvmSigner, ALGORAND_TESTNET_CAIP2 } from "@x402/avm";
import algosdk from "algosdk";
import dotenv from "dotenv";

dotenv.config({ path: "../backend/.env" });
dotenv.config();

async function main() {
  console.log("--------------------------------------------------");
  console.log("Testing Official @x402/fetch Client against :4021");
  console.log("--------------------------------------------------");

  const mnemonic = process.env.TESTNET_SENDER_MNEMONIC;
  if (!mnemonic) {
    console.log("No mnemonic found in environment, using generated account.");
    return;
  }
  const testAccount = algosdk.mnemonicToSecretKey(mnemonic);
  console.log("Payer Address:", testAccount.addr);

  const TESTNET_NETWORK = "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=";
  const signer = toClientAvmSigner(testAccount.sk);

  const client = new x402Client()
    .register(ALGORAND_TESTNET_CAIP2, new ExactAvmScheme(signer))
    .register(TESTNET_NETWORK as any, new ExactAvmScheme(signer))
    .register("algorand:*" as any, new ExactAvmScheme(signer));

  const fetchWithPayment = wrapFetchWithPayment(fetch, client);

  console.log("Sending initial GET http://localhost:4021/test-payment...");
  const initRes = await fetch("http://localhost:4021/test-payment");
  console.log("Init response status:", initRes.status);
  const payReqHeader = initRes.headers.get("payment-required");
  console.log("payment-required header:", payReqHeader);

  if (payReqHeader) {
    const decoded = JSON.parse(Buffer.from(payReqHeader, "base64").toString("utf-8"));
    console.log("Decoded challenge:", JSON.stringify(decoded, null, 2));

    try {
      const paymentPayload = await client.createPaymentPayload(decoded as any);
      console.log("Generated Payment Payload:", JSON.stringify(paymentPayload, null, 2));

      const b64Signature = Buffer.from(JSON.stringify(paymentPayload)).toString("base64");
      console.log("\nRetrying with PAYMENT-SIGNATURE header...");
      const paidRes = await fetch("http://localhost:4021/test-payment", {
        headers: {
          "PAYMENT-SIGNATURE": b64Signature
        }
      });
      console.log("Paid response status:", paidRes.status);
      console.log("Paid response headers:", Object.fromEntries(paidRes.headers.entries()));
      console.log("Paid response body:", await paidRes.text());
    } catch (err: any) {
      console.error("createPaymentPayload error:", err);
    }
  }
}

main();
