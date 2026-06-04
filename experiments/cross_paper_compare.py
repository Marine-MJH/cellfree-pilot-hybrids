"""Cross-paper comparison: same algorithms on Mussbah (small) and Gao (large)
settings, both with multi-antenna (N=8) + one-ring channel.

Settings (both with N=8 antennas per AP, one-ring radius 30 m,
area 1 km² with wraparound, δ=0.95):

- **Mussbah setting**: L=100, K=30, carrier 5 GHz, τ_c=100, τ_p=10, 200 MC
- **Gao setting**: L=500, K=200, carrier 1.9 GHz, τ_c=200, τ_p=10, 100 MC

Algorithms: Random, Gao matching, GC (Liu), Structured (Chen), Mussbah,
TopAP (bisect), H2 Gao+greedy.

Simplification (carried over from mussbah_fig1_simplified.py):
- SE formula = single-antenna SINR on beam-flattened virtual network.
- Mussbah Eq.(9) multi-antenna MRC SE not yet implemented (option A2).

Output: side-by-side bar chart of P5 throughput per algorithm in each setting.
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
from src.power_control import FractionalPowerControl


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


def run_setting(config: SimulationConfig, n_realizations: int, tau_p: int, delta: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    power = FractionalPowerControl(alpha=0.5)
    rows: list[dict] = []
    for r in range(n_realizations):
        if (r + 1) % 20 == 0:
            print(f"    realization {r+1}/{n_realizations}", flush=True)
        net_orig = Network.random(config, rng)
        net_flat = net_orig.beam_flattened()
        schemes = build_schemes(seed + 1000 * r, delta)
        for name in SCHEME_ORDER:
            scheme = schemes[name]
            target_net = net_orig if name == "Mussbah" else net_flat
            pilots = scheme.assign(target_net, tau_p)
            serving = net_flat.all_serving_mask()
            powers = power.compute(net_flat, pilots, serving_mask=serving)
            throughputs = per_ue_throughput_bps(
                net_flat, pilots, powers, tau_p, serving_mask=serving
            )
            for tp in throughputs:
                rows.append({"realization": r, "scheme": name, "throughput_mbps": float(tp) / 1e6})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mussbah-realizations", type=int, default=200)
    parser.add_argument("--gao-realizations", type=int, default=100)
    parser.add_argument("--tau-p", type=int, default=10)
    parser.add_argument("--delta", type=float, default=0.95)
    parser.add_argument("--num-antennas", type=int, default=8)
    parser.add_argument("--one-ring-radius", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out-suffix", type=str, default="")
    args = parser.parse_args()

    print("[Setting 1] Mussbah: L=100, K=30, N=8, 5 GHz, τ_c=100")
    cfg_mussbah = SimulationConfig(
        num_aps=100,
        num_ues=30,
        tau_p=args.tau_p,
        bandwidth_hz=20e6,
        carrier_frequency_mhz=5000.0,
        tau_c=100,
        num_antennas_per_ap=args.num_antennas,
        one_ring_radius_m=args.one_ring_radius,
        random_seed=args.seed,
    )
    df_mussbah = run_setting(cfg_mussbah, args.mussbah_realizations, args.tau_p, args.delta, args.seed)

    print("\n[Setting 2] Gao: L=500, K=200, N=8, 1.9 GHz, τ_c=200")
    cfg_gao = SimulationConfig(
        num_aps=500,
        num_ues=200,
        tau_p=args.tau_p,
        bandwidth_hz=20e6,
        carrier_frequency_mhz=1900.0,
        tau_c=200,
        num_antennas_per_ap=args.num_antennas,
        one_ring_radius_m=args.one_ring_radius,
        random_seed=args.seed + 1,
    )
    df_gao = run_setting(cfg_gao, args.gao_realizations, args.tau_p, args.delta, args.seed + 1)

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)

    def summarise(df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.groupby("scheme")["throughput_mbps"]
            .agg(p5_mbps=lambda x: float(np.percentile(x, 5)),
                 median_mbps="median",
                 mean_mbps="mean")
            .reset_index()
            .set_index("scheme")
            .loc[SCHEME_ORDER]
            .reset_index()
        )

    summary_mussbah = summarise(df_mussbah)
    summary_gao = summarise(df_gao)
    summary_mussbah.to_csv(out_dir / f"cross_paper_mussbah_summary{args.out_suffix}.csv", index=False)
    summary_gao.to_csv(out_dir / f"cross_paper_gao_summary{args.out_suffix}.csv", index=False)
    df_mussbah.to_csv(out_dir / f"cross_paper_mussbah_raw{args.out_suffix}.csv", index=False)
    df_gao.to_csv(out_dir / f"cross_paper_gao_raw{args.out_suffix}.csv", index=False)

    print("\nMussbah setting:")
    print(summary_mussbah.to_string(index=False))
    print("\nGao setting:")
    print(summary_gao.to_string(index=False))

    # Side-by-side bar chart
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    for ax, summary, title in [
        (axes[0], summary_mussbah, f"Mussbah setting (K=30, L=100, {args.mussbah_realizations} MC)"),
        (axes[1], summary_gao, f"Gao setting (K=200, L=500, {args.gao_realizations} MC)"),
    ]:
        names = summary["scheme"].tolist()
        p5 = summary["p5_mbps"].values
        bar_colors = [SCHEME_COLORS.get(n, "black") for n in names]
        bars = ax.bar(range(len(names)), p5, color=bar_colors, edgecolor="black", linewidth=0.6)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("P5 per-UE throughput [Mbit/s]")
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")
        # Random baseline reference line
        random_p5 = float(summary.loc[summary["scheme"] == "Random", "p5_mbps"].iloc[0])
        ax.axhline(random_p5, color="gray", linestyle="--", linewidth=0.8)
        # Annotate Δ vs Random as percent
        for i, (name, v) in enumerate(zip(names, p5)):
            if name == "Random":
                continue
            pct = 100.0 * (v - random_p5) / random_p5
            ax.text(i, v + 0.02 * max(p5), f"{pct:+.1f}%", ha="center", fontsize=8)

    fig.suptitle(
        f"Cross-paper algorithm comparison — N={args.num_antennas} antennas, "
        f"one-ring r=30 m, τ_p={args.tau_p}",
        fontsize=11,
    )
    fig.tight_layout()
    plot_path = out_dir / f"cross_paper_compare{args.out_suffix}.png"
    fig.savefig(plot_path, dpi=200)
    print(f"\nPlot → {plot_path}")


if __name__ == "__main__":
    main()
