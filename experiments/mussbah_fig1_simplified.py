"""Mussbah Fig.1-style *simplified* reproduce.

Settings (paper-faithful where applicable):
- L=100, K=30, N=8
- Area 1 km² with wraparound, carrier 5 GHz, B 20 MHz, τ_c=100
- 200 Monte Carlo setups
- Active beam threshold δ=0.95

Simplifications vs Mussbah paper:
- Channel model: our ULA + DFT geometric (single-path) instead of Rician + 3GPP UMa
  + one-ring spatial covariance.
- SE formula: single-antenna SINR (Gao Eq. 8) on the *beam-flattened* virtual network
  (each beam treated as one virtual single-antenna AP) instead of Mussbah Eq.(9-14)
  multi-antenna MRC closed-form.

This compares pilot-assignment algorithms — including Mussbah Algorithm 1 — under a
common surrogate metric. Algorithm-relative ordering and pilot-contamination effects
are captured; absolute SE numbers are *not* directly comparable to Mussbah Fig.1
because of the channel-model and SE-formula simplifications.

Algorithms compared:
- Random, Gao matching, GC (Liu 2020), Structured access (Chen 2021), Mussbah
  Algorithm 1, TopAP (bisect), H2 Gao+greedy.

Greedy (Ngo 2017) and WGF (Zeng 2021) — referenced in Mussbah Fig.1 — are not yet
implemented; they would be added in a paper-faithful reproduce (option A).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SimulationConfig
from src.metrics import likely_95, per_ue_throughput_bps
from src.network import Network
from src.pilot_schemes import (
    BeamDomainPilotAssignment,
    GraphColoringPilotAssignment,
    HybridGaoColoringPilotAssignment,
    MatchingBasedPilotAssignment,
    RandomPilotAssignment,
    StructuredPilotAccessAssignment,
    TopAPGraphColoringPilotAssignment,
)
from src.power_control import FractionalPowerControl, MaxMinPowerControl


SCHEME_ORDER = [
    "Random",
    "Gao matching",
    "GC (Liu)",
    "Structured (Chen)",
    "Mussbah",
    "TopAP (bisect)",
    "H2 Gao+greedy",
]

SCHEME_COLORS = {
    "Random": "#888888",
    "Gao matching": "#0072bd",
    "GC (Liu)": "#2ca02c",
    "Structured (Chen)": "#d6275f",
    "Mussbah": "#ff7f0e",
    "TopAP (bisect)": "#9467bd",
    "H2 Gao+greedy": "#17becf",
}


def build_schemes(seed_base: int, delta: float) -> dict:
    return {
        "Random": RandomPilotAssignment(seed=seed_base + 1),
        "Gao matching": MatchingBasedPilotAssignment(seed=seed_base + 2),
        "GC (Liu)": GraphColoringPilotAssignment(seed=seed_base + 3),
        "Structured (Chen)": StructuredPilotAccessAssignment(seed=seed_base + 4),
        "Mussbah": BeamDomainPilotAssignment(seed=seed_base + 5, delta=delta),
        "TopAP (bisect)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 6, bisect=True, top_n=10
        ),
        "H2 Gao+greedy": HybridGaoColoringPilotAssignment(seed=seed_base + 7),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--realizations", type=int, default=200)
    parser.add_argument("--tau-p", type=int, default=10)
    parser.add_argument("--delta", type=float, default=0.95)
    parser.add_argument("--num-antennas", type=int, default=8)
    parser.add_argument("--num-aps", type=int, default=100)
    parser.add_argument("--num-ues", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--one-ring-radius", type=float, default=30.0,
        help="Mussbah paper default 30 m. Set 0 for single-path geometric."
    )
    parser.add_argument(
        "--power", choices=["fractional", "max-min"], default="fractional",
        help="Paper uses max-min, but fractional is faster for an initial pass."
    )
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--out-suffix", type=str, default="")
    args = parser.parse_args()

    config = SimulationConfig(
        num_aps=args.num_aps,
        num_ues=args.num_ues,
        tau_p=args.tau_p,
        bandwidth_hz=20e6,
        carrier_frequency_mhz=5000.0,
        tau_c=100,
        num_antennas_per_ap=args.num_antennas,
        one_ring_radius_m=args.one_ring_radius,
        random_seed=args.seed,
    )
    rng = np.random.default_rng(args.seed)
    if args.power == "fractional":
        power = FractionalPowerControl(alpha=0.5)
    else:
        power = MaxMinPowerControl(max_iterations=25)

    raw_records: list[dict] = []
    realization_records: list[dict] = []
    for r in range(args.realizations):
        if not args.no_progress and (r + 1) % 20 == 0:
            print(f"  realization {r+1}/{args.realizations}")
        net_orig = Network.random(config, rng)
        net_flat = net_orig.beam_flattened()
        schemes = build_schemes(args.seed + 1000 * r, args.delta)
        for name in SCHEME_ORDER:
            scheme = schemes[name]
            target_net = net_orig if name == "Mussbah" else net_flat
            pilots = scheme.assign(target_net, args.tau_p)
            serving = net_flat.all_serving_mask()
            powers = power.compute(net_flat, pilots, serving_mask=serving)
            throughputs = per_ue_throughput_bps(
                net_flat, pilots, powers, args.tau_p, serving_mask=serving
            )
            for tp in throughputs:
                raw_records.append(
                    {
                        "realization": r,
                        "scheme": name,
                        "throughput_mbps": float(tp) / 1e6,
                    }
                )
            realization_records.append(
                {
                    "realization": r,
                    "scheme": name,
                    "p5_mbps": float(likely_95(throughputs)) / 1e6,
                    "mean_mbps": float(throughputs.mean()) / 1e6,
                }
            )

    raw_frame = pd.DataFrame(raw_records)
    rec_frame = pd.DataFrame(realization_records)

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)
    raw_path = out_dir / f"mussbah_fig1_simplified_raw{args.out_suffix}.csv"
    summary_path = out_dir / f"mussbah_fig1_simplified_summary{args.out_suffix}.csv"
    raw_frame.to_csv(raw_path, index=False)

    summary = (
        raw_frame.groupby("scheme")["throughput_mbps"]
        .agg(
            p5_mbps=lambda x: float(np.percentile(x, 5)),
            median_mbps="median",
            mean_mbps="mean",
        )
        .reset_index()
    )
    summary = summary.set_index("scheme").loc[SCHEME_ORDER].reset_index()
    summary.to_csv(summary_path, index=False)
    print(f"\nSummary → {summary_path}")
    print(summary.to_string(index=False))

    plt.figure(figsize=(9, 5.5))
    for name in SCHEME_ORDER:
        sub = (
            raw_frame[raw_frame["scheme"] == name]["throughput_mbps"]
            .sort_values()
            .to_numpy()
        )
        cdf = np.arange(1, len(sub) + 1) / len(sub)
        plt.plot(sub, cdf, label=name, color=SCHEME_COLORS.get(name, "black"), linewidth=1.6)
    plt.xlabel("Per-UE throughput [Mbit/s]")
    plt.ylabel("eCDF")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, loc="lower right")
    plt.title(
        f"Mussbah Fig.1-style (simplified): K={args.num_ues}, N={args.num_antennas}, "
        f"L={args.num_aps}, {args.realizations} MC, power={args.power}"
    )
    plt.tight_layout()
    plot_path = out_dir / f"mussbah_fig1_simplified_cdf{args.out_suffix}.png"
    plt.savefig(plot_path, dpi=200)
    print(f"Plot → {plot_path}")


if __name__ == "__main__":
    main()
