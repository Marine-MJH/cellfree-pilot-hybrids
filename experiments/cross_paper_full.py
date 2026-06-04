"""Cross-paper figure with paper-faithful multi-antenna SE.

Two settings:
- Mussbah: K=30, L=100, N=8, 5 GHz, τ_c=100. **Result reused from
  mussbah_fig1_full_summary_200setups.csv** (200 setup × 20 ch samples).
- Gao: K=200, L=500, N=8, 1.9 GHz, τ_c=200. **Run here** (100 setup × 10
  ch samples for compute budget; same paper-faithful SE module).

Output: side-by-side bar chart of P5 SE per algorithm in each setting.
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


def run_setting(config: SimulationConfig, setups: int, ch_samples: int, tau_p: int, delta: float, base_seed: int) -> pd.DataFrame:
    topology_rng = np.random.default_rng(base_seed)
    records: list[dict] = []
    for r in range(setups):
        if (r + 1) % 10 == 0:
            print(f"    setup {r+1}/{setups}", flush=True)
        net = Network.random(config, topology_rng)
        channel_seed = base_seed + 100_000 + r * 13
        schemes = build_schemes(base_seed + 1000 * r, delta)
        for name in SCHEME_ORDER:
            pilots = schemes[name].assign(net, tau_p)
            channel_rng = np.random.default_rng(channel_seed)
            se_per_ue = mussbah_uplink_se(
                net, pilots,
                n_channel_samples=ch_samples,
                delta=delta,
                rician_k_db=10.0,
                one_ring_radius_m=30.0,
                rng=channel_rng,
            )
            for ue_se in se_per_ue:
                records.append({"setup": r, "scheme": name, "se_bps_per_hz": float(ue_se)})
    return pd.DataFrame(records)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("scheme")["se_bps_per_hz"]
        .agg(
            p5_se=lambda x: float(np.percentile(x, 5)),
            median_se="median",
            mean_se="mean",
        )
        .reset_index()
        .set_index("scheme")
        .loc[SCHEME_ORDER]
        .reset_index()
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gao-setups", type=int, default=100)
    parser.add_argument("--gao-channel-samples", type=int, default=10)
    parser.add_argument("--delta", type=float, default=0.95)
    parser.add_argument("--tau-p", type=int, default=10)
    parser.add_argument("--num-antennas", type=int, default=8)
    parser.add_argument("--seed", type=int, default=8)
    parser.add_argument("--out-suffix", type=str, default="")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / "figures"

    # Reuse Mussbah setting results (100 setups × 10 ch with all 9 schemes including Hybrid#4)
    mussbah_summary_path = out_dir / "mussbah_fig1_full_summary_h4.csv"
    if mussbah_summary_path.exists():
        summary_mussbah = pd.read_csv(mussbah_summary_path)
        # Rename column to p5_se if needed (h3_compare uses p5_se already)
        summary_mussbah = summary_mussbah.set_index("scheme").loc[SCHEME_ORDER].reset_index()
        print(f"Reusing Mussbah setting from {mussbah_summary_path}")
    else:
        raise SystemExit("Mussbah setting results not found. Run mussbah_fig1_full.py first.")

    # Run Gao setting paper-faithful SE
    print(f"\n[Gao setting] L=500, K=200, N=8, 1.9 GHz, τ_c=200, {args.gao_setups} setups × {args.gao_channel_samples} ch samples")
    cfg_gao = SimulationConfig(
        num_aps=500,
        num_ues=200,
        tau_p=args.tau_p,
        bandwidth_hz=20e6,
        carrier_frequency_mhz=1900.0,
        tau_c=200,
        num_antennas_per_ap=args.num_antennas,
        one_ring_radius_m=30.0,
        pathloss_model="umi3gpp",  # paper-faithful Mussbah-like channel
        ue_height_m=1.5,
        random_seed=args.seed,
    )
    df_gao = run_setting(cfg_gao, args.gao_setups, args.gao_channel_samples, args.tau_p, args.delta, args.seed)
    df_gao.to_csv(out_dir / f"cross_paper_full_gao_raw{args.out_suffix}.csv", index=False)
    summary_gao = summarise(df_gao)
    summary_gao.to_csv(out_dir / f"cross_paper_full_gao_summary{args.out_suffix}.csv", index=False)

    # Combined print
    print("\n=== Mussbah setting (reused) ===")
    print(summary_mussbah.to_string(index=False))
    print("\n=== Gao setting (paper-faithful SE) ===")
    print(summary_gao.to_string(index=False))

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    for ax, summary, title in [
        (axes[0], summary_mussbah, "Mussbah setting (K=30, L=100, 200 setups × 20 ch)"),
        (axes[1], summary_gao, f"Gao setting (K=200, L=500, {args.gao_setups} setups × {args.gao_channel_samples} ch)"),
    ]:
        names = summary["scheme"].tolist()
        p5 = summary["p5_se"].values
        colors_list = [SCHEME_COLORS.get(n, "black") for n in names]
        ax.bar(range(len(names)), p5, color=colors_list, edgecolor="black", linewidth=0.6)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("P5 per-UE SE [bit/s/Hz/user]")
        ax.set_title(title, fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")
        random_p5 = float(summary.loc[summary["scheme"] == "Random", "p5_se"].iloc[0])
        ax.axhline(random_p5, color="gray", linestyle="--", linewidth=0.8)
        for i, (name, v) in enumerate(zip(names, p5)):
            if name == "Random":
                continue
            pct = 100.0 * (v - random_p5) / random_p5
            ax.text(i, v + 0.005 * max(p5), f"{pct:+.2f}%", ha="center", fontsize=8)

    fig.suptitle(
        f"Cross-paper paper-faithful SE — N={args.num_antennas} antennas, "
        f"one-ring 30 m + Rician 10 dB + MMSE + MRC, τ_p={args.tau_p}",
        fontsize=11,
    )
    fig.tight_layout()
    plot_path = out_dir / f"cross_paper_full{args.out_suffix}.png"
    fig.savefig(plot_path, dpi=200)
    print(f"\nPlot → {plot_path}")


if __name__ == "__main__":
    main()
