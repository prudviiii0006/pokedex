import { config } from "dotenv";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactAvmScheme } from "@x402/avm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { declareDiscoveryExtension, bazaarResourceServerExtension } from "@x402-avm/extensions";
import type { ResourceServerExtension } from "@x402/core/types";
import { Hono } from "hono";
import { serve } from "@hono/node-server";

config();

const avmAddress = process.env.AVM_ADDRESS;
if (!avmAddress) {
    console.error("Missing required environment variables");
    process.exit(1);
}

const facilitatorUrl = process.env.FACILITATOR_URL;
if (!facilitatorUrl) {
    console.error("❌ FACILITATOR_URL environment variable is required");
    process.exit(1);
}

const port = Number(process.env.PORT ?? 4021);
const NETWORK_CAIP2 = "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=" as const;

const facilitatorClient = new HTTPFacilitatorClient({ url: facilitatorUrl });

// Initialize Resource Server
const server = new x402ResourceServer(facilitatorClient)
    .register(NETWORK_CAIP2, new ExactAvmScheme());

// Register Bazaar discovery extension
// This extension enriches all 402 responses with discovery metadata
server.registerExtension(bazaarResourceServerExtension as unknown as ResourceServerExtension);

// Define discovery metadata for each endpoint
const weatherDiscovery = declareDiscoveryExtension({
    output: {
        example: {
            city: "San Francisco",
            temperature: 64,
            condition: "Partly Cloudy",
            humidity: 72,
            timestamp: new Date().toISOString(),
            paidVia: "x402 / USDC Algorand Testnet",
        },
    },
});

const forecastDiscovery = declareDiscoveryExtension({
    output: {
        example: {
            city: "San Francisco",
            forecast: [
                { day: "Mon", high: 68, low: 55, condition: "Sunny" },
                { day: "Tue", high: 66, low: 54, condition: "Cloudy" },
            ],
            timestamp: new Date().toISOString(),
        },
    },
});

const analyzeDiscovery = declareDiscoveryExtension({
    bodyType: "json",
    input: { text: "Sample text to analyze" },
    inputSchema: {
        type: "object",
        properties: { text: { type: "string", description: "Text to analyze" } },
        required: ["text"],
    },
    output: {
        example: {
            sentiment: "positive",
            confidence: 0.92,
            keywords: ["great", "amazing"],
            timestamp: new Date().toISOString(),
        },
    },
});

const app = new Hono();

// Payment middleware with Bazaar discovery metadata per route
app.use(
    paymentMiddleware(
        {
            "GET /weather": {
                accepts: [
                    {
                        scheme: "exact",
                        price: "$0.001",
                        network: NETWORK_CAIP2,
                        payTo: avmAddress,
                    },
                ],
                description: "Current weather for a random city",
                mimeType: "application/json",
                extensions: weatherDiscovery,
            },
            "GET /forecast": {
                accepts: [
                    {
                        scheme: "exact",
                        price: "$0.005",
                        network: NETWORK_CAIP2,
                        payTo: avmAddress,
                    },
                ],
                description: "5-day weather forecast",
                mimeType: "application/json",
                extensions: forecastDiscovery,
            },
            "POST /analyze": {
                accepts: [
                    {
                        scheme: "exact",
                        price: "$0.002",
                        network: NETWORK_CAIP2,
                        payTo: avmAddress,
                    },
                ],
                description: "Analyze sentiment of provided text",
                mimeType: "application/json",
                extensions: analyzeDiscovery,
            },
        },
        server,
    ),
);

// GET /weather endpoint
app.get("/weather", (c) => {
    return c.json({
        city: "San Francisco",
        temperature: 64,
        condition: "Partly Cloudy",
        humidity: 72,
        timestamp: new Date().toISOString(),
    });
});

// GET /forecast endpoint
app.get("/forecast", (c) => {
    return c.json({
        city: "San Francisco",
        forecast: [
            { day: "Mon", high: 68, low: 55, condition: "Sunny" },
            { day: "Tue", high: 66, low: 54, condition: "Cloudy" },
            { day: "Wed", high: 65, low: 53, condition: "Rainy" },
            { day: "Thu", high: 70, low: 56, condition: "Sunny" },
            { day: "Fri", high: 72, low: 58, condition: "Sunny" },
        ],
        timestamp: new Date().toISOString(),
    });
});

// POST /analyze endpoint
app.post("/analyze", async (c) => {
    const body = await c.req.json<{ text: string }>();
    if (!body.text) {
        return c.json({ error: "Missing 'text' field" }, 400);
    }

    // Simple sentiment analysis (mock)
    const text = body.text.toLowerCase();
    const positiveWords = ["great", "amazing", "excellent", "good", "wonderful"];
    const negativeWords = ["bad", "terrible", "awful", "horrible", "poor"];
    const posCount = positiveWords.filter((w) => text.includes(w)).length;
    const negCount = negativeWords.filter((w) => text.includes(w)).length;

    const sentiment = posCount > negCount ? "positive" : negCount > posCount ? "negative" : "neutral";

    return c.json({
        sentiment,
        confidence: 0.85,
        keywords: text.split(/\s+/).filter((w) => w.length > 3),
        timestamp: new Date().toISOString(),
    });
});

// Health check endpoint (no payment required)
app.get("/health", (c) => {
    return c.json({ status: "healthy", bazaar: "enabled" });
});

serve(
    {
        fetch: app.fetch,
        port,
    },
    () => {
        console.log(`✓ Bazaar-enabled resource server listening at http://localhost:${port}`);
        console.log(`  - GET  /weather   ($0.001 USDC) — Current weather`);
        console.log(`  - GET  /forecast  ($0.005 USDC) — 5-day forecast`);
        console.log(`  - POST /analyze   ($0.002 USDC) — Text sentiment analysis`);
        console.log(`  - GET  /health    (free) — Health check`);
        console.log(`\n📚 To verify Bazaar metadata in 402 response:`);
        console.log(`  curl -s -D - http://localhost:${port}/weather 2>&1 | grep -A 5 'payment-required'`);
    },
);
