# AlgoRacers — Driver Attributes & Game Mechanics Specification

This document details the 6 core gameplay attributes of AlgoRacers drivers, their valid numerical ranges, and how they will be used by our future deterministic race simulation engine.

---

## 1. The 6 Core Driver Attributes

Each driver NFT holds 6 primary attributes scored from **0 to 100** (with competitive genesis drivers typically scoring between 60 and 99).

```text
+-------------------+---------------------------------------------------------------+
| Attribute         | Formula & Racing Impact                                       |
+-------------------+---------------------------------------------------------------+
| 🏁 Speed          | Maximum straight-line velocity and engine power extraction.   |
| ⏱️ Qualifying     | Single-lap flying pace; determines grid start position.      |
| 🛡️ Racecraft      | Defensive positioning, tire conservation, and race pace.      |
| ⚡ Overtaking     | Probability of successful passing maneuvers in braking zones. |
| 🌧️ Wet Weather    | Penalty mitigation on slippery, rain-soaked track sectors.   |
| 🎯 Consistency    | Standard deviation reducer; prevents driver unforced errors.  |
+-------------------+---------------------------------------------------------------+
```

---

## 2. Detailed Attribute Definitions & Gameplay Simulation

### 1. `Speed` (Range: 0 – 100)
- **Definition**: Raw top speed and high-speed cornering commitment.
- **Future Engine Use**: Controls the lap time baseline on tracks with long straights (e.g. Monza or Spa equivalents). Higher speed reduces base sector lap times.

### 2. `Qualifying` (Range: 0 – 100)
- **Definition**: The driver's ability to put together a single flawless hot-lap on fresh tires.
- **Future Engine Use**: Before each Grand Prix, qualifying simulation runs:
  $$\text{Grid Score} = \text{Qualifying} \times 0.75 + \text{Speed} \times 0.25 + \text{RNG Modifier}$$
  Drivers are ordered on the starting grid based on Grid Score.

### 3. `Racecraft` (Range: 0 – 100)
- **Definition**: Tactical spatial awareness, defending against incoming attacks, and managing tire degradation across a 50-lap stint.
- **Future Engine Use**: When defending position against an overtaking attempt:
  $$\text{Defense Rating} = \text{Racecraft} \times 0.6 + \text{Consistency} \times 0.4$$

### 4. `Overtaking` (Range: 0 – 100)
- **Definition**: Aggression and precision in DRS zones and heavy braking corners.
- **Future Engine Use**: Evaluated when trailing within 1.0 second of the car ahead:
  $$\text{Pass Success Chance} = \frac{\text{Attacker.Overtaking}}{\text{Attacker.Overtaking} + \text{Defender.Racecraft}}$$

### 5. `Wet Weather` (Range: 0 – 100)
- **Definition**: Grip sensitivity, throttle modulation, and vision in low-traction monsoon conditions.
- **Future Engine Use**: In rain-affected race sessions, non-wet stats suffer a track-wetness penalty factor $(1 - \text{Wetness} \times (100 - \text{Wet Weather}) / 1000)$. High Wet Weather drivers dominate rainy races.

### 6. `Consistency` (Range: 0 – 100)
- **Definition**: Mental focus lap after lap without making mistakes, locking brakes, or spinning.
- **Future Engine Use**: Dictates the variance of lap time delta. A driver with 95 Consistency delivers lap times within $\pm 0.05\text{s}$, while a driver with 65 Consistency fluctuates by $\pm 0.45\text{s}$ with higher crash risks.

---

## 3. Stat Calculation by Rarity Tier

| Tier | Stat Floor | Stat Ceiling | Typical Stat Average |
| :--- | :--- | :--- | :--- |
| **Common** | 60 | 74 | ~67 |
| **Rare** | 75 | 84 | ~80 |
| **Epic** | 85 | 93 | ~89 |
| **Legendary** | 94 | 99 | ~96 |
