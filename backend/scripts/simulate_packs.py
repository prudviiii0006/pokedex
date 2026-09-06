import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from collections import Counter
from backend.rewards.engine import RewardEngine

def run_simulation(engine: RewardEngine, pack_id: str, count: int) -> dict:
    pack = engine.packs.get(pack_id)
    if not pack:
        print(f"❌ Error: Unknown pack '{pack_id}'")
        return {}

    counts = Counter()
    driver_counts = Counter()

    for _ in range(count):
        reward = engine.open_pack(pack_id)
        counts[reward.rarity] += 1
        driver_counts[reward.driver.name] += 1

    print("=" * 65)
    print(f"📊 PACK SIMULATION RESULTS: {pack.name.upper()}")
    print(f"   Total Openings: {count:,}")
    print("=" * 65)
    print(f"{'Rarity':<12} | {'Expected %':<12} | {'Observed Count':<16} | {'Observed %':<12} | {'Delta':<8}")
    print("-" * 65)

    ordered_rarities = ["Common", "Rare", "Epic", "Legendary"]
    for r in ordered_rarities:
        expected_pct = pack.rarities.get(r, 0.0)
        obs_count = counts.get(r, 0)
        obs_pct = (obs_count / count) * 100.0
        delta = obs_pct - expected_pct
        sign = "+" if delta > 0 else ""
        print(f"{r:<12} | {expected_pct:>9.1f}% | {obs_count:>14,} | {obs_pct:>10.2f}% | {sign}{delta:>6.2f}%")

    print("-" * 65)
    print("\n🏎️ Top 3 Most Frequent Drivers Rolled:")
    for driver_name, d_count in driver_counts.most_common(3):
        print(f"   • {driver_name:<20}: {d_count:,} times ({d_count/count*100:.1f}%)")

    return dict(counts)

def main():
    engine = RewardEngine()

    if len(sys.argv) < 2 or sys.argv[1] == "compare":
        # Run comparative benchmark
        print("\n" + "#" * 65)
        print("🏁 COMPARATIVE MONTE CARLO EXPERIMENT (100 vs 1,000 vs 10,000)")
        print("#" * 65 + "\n")

        for sample_size in [100, 1000, 10000]:
            print(f"\n--- SAMPLE SIZE: {sample_size:,} PACKS ---")
            run_simulation(engine, "basic", sample_size)
            print()
            run_simulation(engine, "premium", sample_size)
            print()
    else:
        pack_type = sys.argv[1].lower()
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
        run_simulation(engine, pack_type, count)

if __name__ == "__main__":
    main()
