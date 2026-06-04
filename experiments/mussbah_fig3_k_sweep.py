"""Mussbah paper Fig.3 (SE/EE vs K) sweep — paper-faithful environment.

Paper §V.B: K ∈ {25, 30, 35, 40, 45} with N=8 antennas per AP, otherwise
same setup as Fig.1. Paper Fig.3a shows Mussbah's SE advantage *grows*
with K (more pilot contamination → more room for active-beam-aware
assignment). Paper §V.B: "for K=25 the proposed scheme significantly
improves the EE by 64% compared to the GC".

Used to test whether Mussbah's near-zero advantage in our Fig.1 reproduce
(K=30, +1.6% vs Random) is K-density-dependent.
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
from src.mussbah_se import mussbah_uplink_se
from src.network import Network
from src.pilot_schemes import (
    BeamDomainPilotAssignment,
    GraphColoringPilotAssignment,
    Hybrid4TopAPGreedyPilotAssignment,
    HybridGaoColoringPilotAssignment,
    MatchingBasedPilotAssignment,
    RandomPilotAssignment,
    StructuredPilotAccessAssignment,
    TopAPGraphColoringPilotAssignment,
)


SCHEME_ORDER = [
    "Random",
    "Gao matching",
    "GC (Liu)",
    "Structured (Chen)",
    "Mussbah",
    "TopAP (bisect)",
    "H2 Gao+greedy",
    "Hybrid#3 (TopAP N=8 adaptive)",
    "Hybrid#4 (TopAP+greedy)",
]

SCHEME_COLORS = {
    "Random": "#888888",
    "Gao matching": "#0072bd",
    "GC (Liu)": "#2ca02c",
    "Structured (Chen)": "#d6275f",
    "Mussbah": "#ff7f0e",
    "TopAP (bisect)": "#9467bd",
    "H2 Gao+greedy": "#17becf",
    "Hybrid#3 (TopAP N=8 adaptive)": "#e377c2",
    "Hybrid#4 (TopAP+greedy)": "#8c564b",
}


def build_schemes(seed_base: int, delta: float) -> dict:
    return {
        "Random": RandomPilotAssignment(seed=seed_base + 1),
        "Gao matching": MatchingBasedPilotAssignment(seed=seed_base + 2),
        "GC (Liu)": GraphColoringPilotAssignment(seed=seed_base + 3),
        "Structured (Chen)": StructuredPilotAccessAssignment(seed=seed_base + 4),
        "Mussbah": BeamDomainPilotAssignment(
            seed=seed_base + 5, delta=delta, adaptive_tau_p=True
        ),
        "TopAP (bisect)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 6, bisect=True, top_n=10
        ),
        "H2 Gao+greedy": HybridGaoColoringPilotAssignment(seed=seed_base + 7),
        "Hybrid#3 (TopAP N=8 adaptive)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 8, bisect=False, top_n=8, adaptive_tau_p=True
        ),
        "Hybrid#4 (TopAP+greedy)": Hybrid4TopAPGreedyPilotAssignment(
            seed=seed_base + 9, top_n=10
        ),
    }


def run_one_k(k: int, args) -> pd.DataFrame:
    config = SimulationConfig(
        num_aps=args.num_aps,
        num_ues=k,
        tau_p=args.tau_p,
        bandwidth_hz=20e6,
        carrier_frequency_mhz=5000.0,
        tau_c=100,
        num_antennas_per_ap=args.num_antennas,
        one_ring_radius_m=args.one_ring_radius,
        pathloss_model="umi3gpp",
        ue_height_m=1.5,
        random_seed=args.seed,
    )
    topology_rng = np.random.default_rng(args.seed)
    records: list[dict] = []
    for r in range(args.setups):
        if (r + 1) % 10 == 0:
            print(f"  K={k} setup {r+1}/{args.setups}", flush=True)
        net = Network.random(config, topology_rng)
        channel_seed = args.seed + 100_000 + r * 13
        schemes = build_schemes(args.seed + 1000 * r, args.delta)
        for name in SCHEME_ORDER:
            pilots = schemes[name].assign(net, args.tau_p)
            channel_rng = np.random.default_rng(channel_seed)
            se_per_ue = mussbah_uplink_se(
                net, pilots,
                n_channel_samples=args.channel_samples,
                delta=args.delta,
                rician_k_db=10.0,
                one_ring_radius_m=args.one_ring_radius,
                rng=channel_rng,
            )
            for ue_se in se_per_ue:
                records.append({"K": k, "setup": r, "scheme": name, "se_bps_per_hz": float(ue_se)})
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setups", type=int, default=50)
    parser.add_argument("--channel-samples", type=int, default=10)
    parser.add_argument("--tau-p", type=int, default=10)
    parser.add_argument("--delta", type=float, default=0.95)
    parser.add_argument("--num-antennas", type=int, default=8)
    parser.add_argument("--num-aps", type=int, default=100)
    parser.add_argument("--one-ring-radius", type=float, default=30.0)
    parser.add_argument("--k-values", type=int, nargs="+", default=[25, 30, 35, 40, 45])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out-suffix", type=str, default="")
    args = parser.parse_args()

    dfs = []
    for k in args.k_values:
        print(f"\n[K = {k}]")
        dfs.append(run_one_k(k, args))
    df = pd.concat(dfs, ignore_index=True)

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir / f"mussbah_fig3_k_sweep_raw{args.out_suffix}.csv", index=False)

    summary = (
        df.groupby(["K", "scheme"])["se_bps_per_hz"]
        .agg(
            p5_se=lambda x: float(np.percentile(x, 5)),
            mean_se="mean",
        )
        .reset_index()
    )
    summary.to_csv(out_dir / f"mussbah_fig3_k_sweep_summary{args.out_suffix}.csv", index=False)
    print("\n=== Summary ===")
    print(summary.to_string(index=False))

    # Plot: mean SE vs K per scheme (paper Fig.3a style)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, metric, ylabel, title in [
        (axes[0], "mean_se", "Mean SE [bit/s/Hz/user]", "Average SE vs K"),
        (axes[1], "p5_se", "P5 SE [bit/s/Hz/user]", "95%-likely SE vs K"),
    ]:
        for name in SCHEME_ORDER:
            sub = summary[summary["scheme"] == name].sort_values("K")
            ax.plot(sub["K"], sub[metric], marker="o", label=name,
                    color=SCHEME_COLORS.get(name, "black"), linewidth=1.6)
        ax.set_xlabel("Number of users K")
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    fig.suptitle(
        f"Mussbah Fig.3 K-sweep (paper-faithful UMi + adaptive τ_p), "
        f"N={args.num_antennas}, {args.setups} setups × {args.channel_samples} ch samples",
        fontsize=11,
    )
    fig.tight_layout()
    plot_path = out_dir / f"mussbah_fig3_k_sweep{args.out_suffix}.png"
    fig.savefig(plot_path, dpi=200)
    print(f"\nPlot → {plot_path}")


if __name__ == "__main__":
    main()
