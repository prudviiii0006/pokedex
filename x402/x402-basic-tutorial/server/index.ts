import { config } from "dotenv";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactAvmScheme } from "@x402/avm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { declareDiscoveryExtension, bazaarResourceServerExtension } from "@x402-avm/extensions";
import type { ResourceServerExtension } from "@x402/core/types";
import { Hono } from "hono";
import { serve } from "@hono/node-server";
import { ALGORAND_TESTNET_CAIP2, USDC_TESTNET_ASA_ID } from "@x402/avm";

config();

const avmAddress = process.env.AVM_ADDRESS;
if (!avmAddress) {
    console.error("Missing AVM_ADDRESS environment variable");
    process.exit(1);
}

const facilitatorUrl = process.env.FACILITATOR_URL;
if (!facilitatorUrl) {
    console.error("Missing FACILITATOR_URL environment variable");
    process.exit(1);
}

const facilitatorClient = new HTTPFacilitatorClient({ url: facilitatorUrl });
const server = new x402ResourceServer(facilitatorClient)
    .register(ALGORAND_TESTNET_CAIP2, new ExactAvmScheme());

// Register Bazaar discovery extension
server.registerExtension(bazaarResourceServerExtension as unknown as ResourceServerExtension);

const weatherDiscovery = declareDiscoveryExtension({
    output: {
        example: {
            weather: "sunny",
            temperature: 70,
            timestamp: new Date().toISOString(),
            paidVia: "x402 / USDC Algorand Testnet",
        },
    },
});

const app = new Hono();

app.use(
    paymentMiddleware(
        {
            "GET /weather": {
                accepts: [
                    {
                        scheme: "exact",
                        price: "$0.005",
                        network: ALGORAND_TESTNET_CAIP2,
                        payTo: avmAddress,
                        extra: { asset: USDC_TESTNET_ASA_ID },
                    },
                ],
                description: "Weather data access",
                mimeType: "application/json",
                extensions: weatherDiscovery,
            },
        },
        server,
    ),
);

app.get("/weather", (c) => {
    return c.json({
        weather: "sunny",
        temperature: 70,
        timestamp: new Date().toISOString(),
    });
});

serve(
    {
        fetch: app.fetch,
        port: 4021,
    },
    () => {
        console.log("x402 Resource Server listening at http://localhost:4021");
    },
);
