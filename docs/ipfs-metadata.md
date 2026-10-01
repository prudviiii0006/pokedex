# Pokédex — IPFS, Content Addressing & Metadata Integrity Specification

---

## 1. Content Addressing vs. Location Addressing

```text
┌───────────────────────────────────────────────┐
│              LOCATION ADDRESSING              │
│ https://example.com/pokemon1.json             │
│ • "Fetch whatever file currently lives here"  │
│ • Vulnerability: Host can alter stats or image│
│   without changing the URL!                   │
└───────────────────────────────────────────────┘
                       vs.
┌───────────────────────────────────────────────┐
│              CONTENT ADDRESSING               │
│ ipfs://bafkreia3vnoeexpsbnilmcjrjtsd3bomvs... │
│ • "Fetch content whose SHA-256 matches CID"   │
│ • Immutability: If a single byte changes, the │
│   CID changes completely (Avalanche Effect).  │
└───────────────────────────────────────────────┘
```

---

## 2. Cryptographic Content Identifiers (CIDv1)

Pokédex uses **CIDv1 Base32** (`bafk...`):

$$\text{Digest} = \text{SHA256}(\text{Canonical Bytes})$$
$$\text{Multihash} = \text{0x12 (SHA-256)} \;\|\; \text{0x20 (32 bytes)} \;\|\; \text{Digest}$$
$$\text{CIDv1} = \text{0x01 (v1)} \;\|\; \text{0x55 (Raw Codec)} \;\|\; \text{Multihash}$$
$$\text{Encoded} = \text{"b"} + \text{Base32}(\text{CIDv1})$$

---

## 3. Dependency Chain & Metadata Provenance

```text
                  DRIVER IMAGE ASSET
                           │
                           ▼
                    IPFS PINNING
                           │
                       IMAGE CID
                           │
                           ▼
               CANONICAL METADATA JSON
             (References ipfs://IMAGE_CID)
                           │
                           ▼
                    IPFS PINNING
                           │
                     METADATA CID
                           │
                           ▼
                  ALGORAND ASA / NFT
            (URL: ipfs://METADATA_CID#arc3)
```

---

## 4. Multi-Gateway Architecture & Fallback

* **Canonical URI**: `ipfs://<CID>` (or `ipfs://<CID>#arc3` for ARC-3 compliance).
* **Public Gateways**:
  1. `https://ipfs.io/ipfs/<CID>`
  2. `https://dweb.link/ipfs/<CID>`
  3. `https://cloudflare-ipfs.com/ipfs/<CID>`
  4. `https://gateway.pinata.cloud/ipfs/<CID>`

If one gateway is temporarily unavailable, the client simply falls back to the next gateway. **Integrity is decoupled from availability**.
