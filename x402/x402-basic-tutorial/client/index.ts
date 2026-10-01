import { config } from "dotenv";
import { x402Client, wrapFetchWithPayment, x402HTTPClient } from "@x402/fetch";
import { toClientAvmSigner, ExactAvmScheme, ALGORAND_TESTNET_CAIP2 } from "@x402/avm";
import {
    ed25519SigningKeyFromWrappedSecret,
    type WrappedEd25519Seed,
} from "@algorandfoundation/algokit-utils/crypto";
import { seedFromMnemonic } from "@algorandfoundation/algokit-utils/algo25";

config();

const avmMnemonic = process.env.AVM_MNEMONIC as string;

if (!avmMnemonic) {
    throw new Error(
        "Missing AVM_MNEMONIC environment variable. Please add it to your .env file.",
    );
}

// Choose your resource server by uncommenting one of these:
const url = "http://localhost:4021/weather";  // Local resource server
// const url = "https://your-deployed-server.com/weather";  // Hosted resource server

async function main(): Promise<void> {
    const secretKey = await getSecretKeyFromMnemonic(avmMnemonic);
    const avmSigner = toClientAvmSigner(secretKey);
    const client = new x402Client();

    client.register(ALGORAND_TESTNET_CAIP2, new ExactAvmScheme(avmSigner));
    console.info(`AVM signer: ${avmSigner.address}`);

    const fetchWithPayment = wrapFetchWithPayment(fetch, client);
    const response = await fetchWithPayment(url, { method: "GET" });

    if (response.ok) {
        const paymentResponse = new x402HTTPClient(client).getPaymentSettleResponse((name) =>
            response.headers.get(name),
        );
        console.log("\n💳 Payment confirmed:", JSON.stringify(paymentResponse, null, 2));

        const body = await response.json();
        console.log("\n✅ Resource received:", JSON.stringify(body, null, 2));
    } else {
        console.error("❌ Request failed:", response.status);
        const error = await response.json();
        console.error(error);
    }
}

async function getSecretKeyFromMnemonic(avmMnemonic: string): Promise<string> {
    const seed = seedFromMnemonic(avmMnemonic);
    const seedCopy = new Uint8Array(seed);
    const wrappedSeed: WrappedEd25519Seed = {
        unwrapEd25519Seed: async () => seed,
        wrapEd25519Seed: async () => {},
    };
    const wrappedSecret = await ed25519SigningKeyFromWrappedSecret(wrappedSeed);

    return Buffer.concat([
        Buffer.from(seedCopy),
        Buffer.from(wrappedSecret.ed25519Pubkey),
    ]).toString("base64");
}

main().catch((error: Error) => {
    console.error("Error:", error.message);
    process.exit(1);
});
