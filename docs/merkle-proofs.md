# AlgoRacers — Merkle Trees, Dataset Commitments & Scalable Proofs Specification

---

## 1. What a Merkle Tree Proves vs. Does NOT Prove

```text
┌────────────────────────────────────────────────────────┐
│                   WHAT IT PROVES                       │
│ • "Driver record #007 was part of the dataset          │
│    committed by Root R."                               │
│ • "The data has not been altered or substituted."      │
│ • "The root is anchored on Algorand Smart Contract."   │
└────────────────────────────────────────────────────────┘
                           vs.
┌────────────────────────────────────────────────────────┐
│                WHAT IT DOES NOT PROVE                  │
│ • It does NOT prove driver stats are balanced/fair.    │
│ • It does NOT prove the user currently owns the NFT.   │
│ • It does NOT prove metadata is hosted forever.        │
│ • It is NOT encryption (private data can be guessed).  │
└────────────────────────────────────────────────────────┘
```

---

## 2. 4-Leaf Merkle Tree Construction

```text
                              ROOT
                     H(Node_AB || Node_CD)
                           /        \
                          /          \
                     Node_AB        Node_CD
                   H(L_A || L_B)  H(L_C || L_D)
                     /      \        /      \
                    /        \      /        \
                  L_A        L_B  L_C        L_D
                  H(A)       H(B) H(C)       H(D)
                   │          │    │          │
                 Driver     Driver Driver   Driver
                  #001       #002   #003     #004
```

---

## 3. Cryptographic Hashing Scheme with Domain Separation

### 1. Leaf Hashing:
$$\text{leaf\_bytes} = \text{"ALGORACERS_LEAF_V1:"} + \text{canonical\_json}(\text{record})$$
$$\text{leaf\_hash} = \text{SHA256}(\text{leaf\_bytes})$$

### 2. Internal Node Hashing:
$$\text{node\_bytes} = \text{"ALGORACERS_NODE_V1:"} + \text{left\_hash} + \text{right\_hash}$$
$$\text{parent\_hash} = \text{SHA256}(\text{node\_bytes})$$

---

## 4. Scalability: $O(n)$ Dataset vs. $O(\log n)$ Proof Size

| Dataset Size ($n$) | On-Chain Storage | Merkle Proof Steps ($\log_2 n$) | Proof Size (bytes) |
| :---: | :---: | :---: | :---: |
| **10** | 32 bytes (Root) | 4 steps | ~130 B |
| **100** | 32 bytes (Root) | 7 steps | ~224 B |
| **1,000** | 32 bytes (Root) | 10 steps | ~320 B |
| **100,000** | 32 bytes (Root) | 17 steps | ~544 B |
