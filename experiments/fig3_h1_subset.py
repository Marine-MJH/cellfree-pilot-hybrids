"""Subset of TopAP variants + key baselines for fast iteration.

Used to compare Hybrid #1 + N-bisection (the *fixed* version, after
moving to quota-free real-chromatic termination) against fixed-N TopAP
and the strongest baselines. Fractional power only, 100 MC, 5-scheme
subset → ~6 min wall-clock vs ~26 min for the full sensitivity sweep.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SimulationConfig
from src.metrics import likely_95, per_ue_throughput_bps
from src.network import Network
from src.pilot_schemes import (
    GraphColoringPilotAssignment,
    HybridGaoColoringPilotAssignment,
    MatchingBasedPilotAssignment,
    StructuredPilotAccessAssignment,
    TopAPGraphColoringPilotAssignment,
)
from src.power_control import FractionalPowerControl


def build_schemes(seed: int):
    return [
        ("Gao matching", MatchingBasedPilotAssignment(seed=seed + 2)),
        ("Graph coloring (full)", GraphColoringPilotAssignment(seed=seed + 3)),
        ("Structured access (full)", StructuredPilotAccessAssignment(seed=seed + 4)),
        ("TopAP (N=5)", TopAPGraphColoringPilotAssignment(seed=seed + 5, top_n=5)),
        ("TopAP (N=10)", TopAPGraphColoringPilotAssignment(seed=seed + 6, top_n=10)),
        ("TopAP (bisect)", TopAPGraphColoringPilotAssignment(seed=seed + 7, bisect=True, top_n=10)),
        ("H2 Gao+greedy", HybridGaoColoringPilotAssignment(seed=seed + 8)),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--realizations", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tau-values", type=int, nargs="+", default=[10, 15, 20, 25, 30])
    parser.add_argument("--out-suffix", type=str, default="_100mc_h1bisect2_s42")
    args = parser.parse_args()

    base_config = SimulationConfig(num_aps=500, num_ues=200, tau_p=20, random_seed=args.seed)
    power_control = FractionalPowerControl(alpha=0.5)
    rng = np.random.default_rng(args.seed)

    records: list[dict[str, float | int | str]] = []
    raw_records: list[dict[str, float | int | str]] = []
    for tau_p in args.tau_values:
        for r in range(args.realizations):
            network = Network.random(base_config, rng)
            for name, scheme in build_schemes(args.seed + 1000 * r):
                pilots = scheme.assign(network, tau_p)
                serving = scheme.serving_matrix(network)
                powers = power_control.compute(network, pilots, serving_mask=serving)
                throughputs = per_ue_throughput_bps(
                    network, pilots, powers, tau_p, serving_mask=serving
                )
                for tp in throughputs:
                    raw_records.append(
                        {
                            "tau_p": tau_p,
                            "realization": r,
                            "scheme": name,
                            "throughput_mbps": float(tp) / 1e6,
                        }
                    )
                records.append(
                    {
                        "tau_p": tau_p,
                        "realization": r,
                        "scheme": name,
                        "p5_mbps": float(likely_95(throughputs)) / 1e6,
                    }
                )

    raw_frame = pd.DataFrame(raw_records)
    frame = pd.DataFrame(records)

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)
    raw_frame.to_csv(out_dir / f"fig3_h1_subset_raw{args.out_suffix}.csv", index=False)

    summary = (
        raw_frame.groupby(["tau_p", "scheme"])["throughput_mbps"]
        .agg(p5_mbps=lambda x: np.percentile(x, 5), median_mbps="median")
        .reset_index()
    )
    summary_path = out_dir / f"fig3_h1_subset_summary{args.out_suffix}.csv"
    summary.to_csv(summary_path, index=False)
    print(f"Summary → {summary_path}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
