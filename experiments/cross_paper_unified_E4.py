"""Common-ground multi-antenna unified cross-paper benchmark (E4).

This is not a Gao-paper or Mussbah-paper reproduction environment. It is a
common-ground stress benchmark where all 9 schemes can run in the same
multi-antenna system and are evaluated with the same Mussbah-style MC SE.

Default E4 spec:
- L=200 APs, K=50 UEs, N=8 antennas/AP
- carrier 3 GHz, bandwidth 20 MHz, tau_c=150
- 3GPP UMi path loss, one-ring radius 30 m, Rician K=10 dB
- random AP ULA orientation, tau_p_design=15
- 200 setups x 20 small-scale channel samples

Outputs:
- figures/cross_paper_unified_E4_raw_E4.csv
- figures/cross_paper_unified_E4_summary_E4.csv
- figures/cross_paper_unified_E4_cdf_E4.png
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
    WeightedBeamThresholdPilotAssignment,
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
    "MJH weighted-count default",
    "MJH weighted-count strict",
    "MJH weighted-power",
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
    "MJH weighted-count default": "#fdae61",
    "MJH weighted-count strict": "#d73027",
    "MJH weighted-power": "#b15928",
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
        # MJH teammate's weighted-threshold variants (PRESENTATION_PLAN.md §7)
        "MJH weighted-count default": WeightedBeamThresholdPilotAssignment(
            seed=seed_base + 10, delta=delta,
            variant="weighted-count", w_aa=2.0, w_am=1.0, threshold=0.0,
            adaptive_tau_p=True,
        ),
        "MJH weighted-count strict": WeightedBeamThresholdPilotAssignment(
            seed=seed_base + 11, delta=delta,
            variant="weighted-count", w_aa=2.0, w_am=1.0, threshold=3.0,
            adaptive_tau_p=True,
        ),
        "MJH weighted-power": WeightedBeamThresholdPilotAssignment(
            seed=seed_base + 12, delta=delta,
            variant="weighted-power", w_aa=2.0, w_am=1.0, threshold=0.0,
            adaptive_tau_p=True,
        ),
    }


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("scheme")
        .agg(
            p5_se=("se_bps_per_hz", lambda x: float(np.percentile(x, 5))),
            median_se=("se_bps_per_hz", "median"),
            mean_se=("se_bps_per_hz", "mean"),
            mean_tau_p_actual=("tau_p_actual", "mean"),
            min_tau_p_actual=("tau_p_actual", "min"),
            max_tau_p_actual=("tau_p_actual", "max"),
        )
        .reset_index()
        .set_index("scheme")
        .loc[SCHEME_ORDER]
        .reset_index()
    )
    random_mean = float(summary.loc[summary["scheme"] == "Random", "mean_se"].iloc[0])
    random_p5 = float(summary.loc[summary["scheme"] == "Random", "p5_se"].iloc[0])
    summary["mean_vs_random_pct"] = 100.0 * (summary["mean_se"] - random_mean) / random_mean
    summary["p5_vs_random_pct"] = 100.0 * (summary["p5_se"] - random_p5) / random_p5
    return summary


def run_e4(args: argparse.Namespace) -> pd.DataFrame:
    config = SimulationConfig(
        num_aps=args.num_aps,
        num_ues=args.num_ues,
        tau_p=args.tau_p,
        tau_c=args.tau_c,
        bandwidth_hz=20e6,
        carrier_frequency_mhz=args.carrier_frequency_mhz,
        num_antennas_per_ap=args.num_antennas,
        one_ring_radius_m=args.one_ring_radius,
        pathloss_model="umi3gpp",
        ue_height_m=1.5,
        ap_orientation=args.ap_orientation,
        beam_detection_snr_db=args.beam_detection_snr_db,
        random_seed=args.seed,
    )
    topology_rng = np.random.default_rng(args.seed)
    records: list[dict] = []

    for r in range(args.setups):
        if not args.no_progress and (r + 1) % 10 == 0:
            print(f"  setup {r+1}/{args.setups}", flush=True)

        net = Network.random(config, topology_rng)
        channel_seed = args.seed + 100_000 + r * 13
        schemes = build_schemes(args.seed + 1000 * r, args.delta)

        for name in SCHEME_ORDER:
            pilots = schemes[name].assign(net, args.tau_p)
            tau_p_actual = int(pilots.max()) + 1 if pilots.size else 0
            channel_rng = np.random.default_rng(channel_seed)
            se_per_ue = mussbah_uplink_se(
                net,
                pilots,
                n_channel_samples=args.channel_samples,
                delta=args.delta,
                rician_k_db=args.rician_k_db,
                one_ring_radius_m=args.one_ring_radius,
                rng=channel_rng,
            )
            for ue_idx, ue_se in enumerate(se_per_ue):
                records.append(
                    {
                        "setup": r,
                        "ue": ue_idx,
                        "scheme": name,
                        "se_bps_per_hz": float(ue_se),
                        "tau_p_design": args.tau_p,
                        "tau_p_actual": tau_p_actual,
                    }
                )

    return pd.DataFrame(records)


def plot_cdf(df: pd.DataFrame, summary: pd.DataFrame, args: argparse.Namespace, out_path: Path) -> None:
    plt.figure(figsize=(9.5, 5.8))
    for name in SCHEME_ORDER:
        sub = df[df["scheme"] == name]["se_bps_per_hz"].sort_values().to_numpy()
        cdf = np.arange(1, len(sub) + 1) / len(sub)
        plt.plot(
            sub,
            cdf,
            label=name,
            color=SCHEME_COLORS.get(name, "black"),
            linewidth=1.7 if name in {"Mussbah", "Hybrid#3 (TopAP N=8 adaptive)", "Hybrid#4 (TopAP+greedy)"} else 1.3,
        )
    plt.xlabel("Per-UE SE [bit/s/Hz/user]")
    plt.ylabel("eCDF")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7.5, loc="lower right")
    plt.title(
        "E4 unified common-ground benchmark: "
        f"K={args.num_ues}, L={args.num_aps}, N={args.num_antennas}, "
        f"fc={args.carrier_frequency_mhz/1000:.1f} GHz, tau_c={args.tau_c}, "
        f"tau_p_design={args.tau_p}"
    )

    random_p5 = float(summary.loc[summary["scheme"] == "Random", "p5_se"].iloc[0])
    plt.axvline(random_p5, color="#777777", linestyle="--", linewidth=0.8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setups", type=int, default=200)
    parser.add_argument("--channel-samples", type=int, default=20)
    parser.add_argument("--tau-p", type=int, default=15)
    parser.add_argument("--tau-c", type=int, default=150)
    parser.add_argument("--delta", type=float, default=0.95)
    parser.add_argument("--rician-k-db", type=float, default=10.0)
    parser.add_argument("--one-ring-radius", type=float, default=30.0)
    parser.add_argument("--num-antennas", type=int, default=8)
    parser.add_argument("--num-aps", type=int, default=200)
    parser.add_argument("--num-ues", type=int, default=50)
    parser.add_argument("--carrier-frequency-mhz", type=float, default=3000.0)
    parser.add_argument("--ap-orientation", choices=["fixed", "random"], default="random")
    parser.add_argument("--beam-detection-snr-db", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--out-suffix", type=str, default="_E4")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)

    print(
        "\n[E4 unified common-ground] "
        f"L={args.num_aps}, K={args.num_ues}, N={args.num_antennas}, "
        f"fc={args.carrier_frequency_mhz/1000:.1f} GHz, tau_c={args.tau_c}, "
        f"tau_p_design={args.tau_p}, {args.setups} setups x {args.channel_samples} ch samples"
    )
    df = run_e4(args)
    raw_path = out_dir / f"cross_paper_unified_E4_raw{args.out_suffix}.csv"
    df.to_csv(raw_path, index=False)

    summary = summarise(df)
    summary_path = out_dir / f"cross_paper_unified_E4_summary{args.out_suffix}.csv"
    summary.to_csv(summary_path, index=False)

    print("\n=== E4 unified common-ground summary ===")
    print(summary.to_string(index=False))

    cdf_path = out_dir / f"cross_paper_unified_E4_cdf{args.out_suffix}.png"
    plot_cdf(df, summary, args, cdf_path)
    print(f"\nRaw -> {raw_path}")
    print(f"Summary -> {summary_path}")
    print(f"CDF -> {cdf_path}")


if __name__ == "__main__":
    main()
