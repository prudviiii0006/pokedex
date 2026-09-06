# AlgoRacers — Deterministic Race Engine v1 Specification

---

## 1. Overview & Mathematical Determinism

`DeterministicRaceEngineV1` is the canonical, open-source racing simulation algorithm for AlgoRacers tournaments. Given the exact same inputs (master seed, participant set, circuit), it executes with **100% deterministic reproducibility across any computing platform**.

---

## 2. Canonical Participant Ordering

To eliminate database non-determinism, participants are sorted strictly by `asset_id` ascending before seed derivation or grid assignment:

$$\text{Canonical Order} = \text{sort}([\text{Driver}_1, \dots, \text{Driver}_n], \text{key}=\lambda d: d.\text{asset\_id})$$

---

## 3. Performance & Score Formulas

### 1. Base Score (Circuit-Weighted)
$$\text{Base Score} = \sum_{s \in \text{Stats}} \text{driver}[s] \times \text{circuit\_weight}[s]$$

### 2. Deterministic Variance (Sub-Seed Uniform Mapping)
$$\text{uint64\_val} = \text{int.from\_bytes}(\text{SHA256}(\text{master\_seed} + \text{asset\_id} + \text{"variance"})[:8], \text{"big"})$$
$$\text{normalized} = \frac{\text{uint64\_val}}{2^{64} - 1}$$
$$\text{Variance} = -2.5 + (\text{normalized} \times 5.0)$$

### 3. Final Score & Lap Time
$$\text{Final Score} = \text{round}(\text{Base Score} + \text{Variance}, 2)$$
$$\text{Lap Time (seconds)} = \text{round}(85.0 - (\text{Final Score} \times 0.2), 3)$$

---

## 4. Championship Points Distribution

| Position | Points | Result Category |
| :---: | :---: | :--- |
| **P1** | 25 | Winner (P1) |
| **P2** | 18 | Podium (P2) |
| **P3** | 15 | Podium (P3) |
| **P4** | 12 | Top 5 (P4) |
| **P5** | 10 | Top 5 (P5) |
| **P6** | 8 | Midfield (P6) |
| **P7** | 6 | Midfield (P7) |
| **P8** | 4 | Backmarker (P8) |
