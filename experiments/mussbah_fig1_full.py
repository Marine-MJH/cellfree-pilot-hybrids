"""Mussbah Fig.1 paper-faithful reproduce (option A).

Uses ``src/mussbah_se.py`` Monte-Carlo SE (beam-subspace MMSE + MRC,
one-ring NLoS covariance + Rician LoS, K=10 dB). All algorithms evaluated
on the *same* channel samples within each setup (deterministic seeding)
so the only thing varying between algorithms is the pilot assignment.

Setting (Mussbah paper):
- L=100, K=30, N=8, area 1 km², carrier 5 GHz, B 20 MHz, τ_c=100
- one-ring radius 30 m, Rician K=10 dB
- δ=0.95
- Pilot τ_p=10 (fixed for all baselines, Mussbah adapts internally via Dsatur)
- 200 setups (paper default), n_channel_samples=20 per setup

Schemes: Random, Gao matching, GC (Liu), Structured (Chen), Mussbah,
TopAP (bisect), H2 Gao+greedy.
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
        # Mussbah with adaptive τ_p (paper §V.A): chromatic colors returned
        # raw so the SE formula sees actual distinct-pilot count.
        "Mussbah": BeamDomainPilotAssignment(
            seed=seed_base + 5, delta=delta, adaptive_tau_p=True
        ),
        "TopAP (bisect)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 6, bisect=True, top_n=10
        ),
        "H2 Gao+greedy": HybridGaoColoringPilotAssignment(seed=seed_base + 7),
        # Hybrid #3: TopAP element-domain conflict + adaptive τ_p (Mussbah-style
        # mechanism on a different conflict graph). N=8 chosen because the
        # element-domain chromatic ≈ 8.5 in this setting — fewer pilots than
        # Mussbah's beam-domain chromatic 11.7.
        "Hybrid#3 (TopAP N=8 adaptive)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 8, bisect=False, top_n=8, adaptive_tau_p=True
        ),
        "Hybrid#4 (TopAP+greedy)": Hybrid4TopAPGreedyPilotAssignment(
            seed=seed_base + 9, top_n=10
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setups", type=int, default=200)
    parser.add_argument("--channel-samples", type=int, default=20)
    parser.add_argument("--tau-p", type=int, default=10)
    parser.add_argument("--delta", type=float, default=0.95)
    parser.add_argument("--rician-k-db", type=float, default=10.0)
    parser.add_argument("--one-ring-radius", type=float, default=30.0)
    parser.add_argument("--num-antennas", type=int, default=8)
    parser.add_argument("--num-aps", type=int, default=100)
    parser.add_argument("--num-ues", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--beam-detection-snr-db", type=float, default=0.0,
                        help="SNR threshold for beam detection (paper §V 'SNR > 0' "
                             "— empirically +6dB matches paper chromatic).")
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
        pathloss_model="umi3gpp",  # 3GPP TR 38.901 UMi (paper-faithful)
        ue_height_m=1.5,
        beam_detection_snr_db=args.beam_detection_snr_db,
        random_seed=args.seed,
    )
    topology_rng = np.random.default_rng(args.seed)

    se_records: list[dict] = []  # per-UE per-setup per-scheme

    for r in range(args.setups):
        if not args.no_progress and (r + 1) % 10 == 0:
            print(f"  setup {r+1}/{args.setups}", flush=True)

        net = Network.random(config, topology_rng)
        channel_seed = args.seed + 100_000 + r * 13

        schemes = build_schemes(args.seed + 1000 * r, args.delta)
        for name in SCHEME_ORDER:
            pilots = schemes[name].assign(net, args.tau_p)
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
            for ue_se in se_per_ue:
                se_records.append(
                    {"setup": r, "scheme": name, "se_bps_per_hz": float(ue_se)}
                )

    df = pd.DataFrame(se_records)

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)
    df.to_csv(out_dir / f"mussbah_fig1_full_raw{args.out_suffix}.csv", index=False)

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
    summary.to_csv(out_dir / f"mussbah_fig1_full_summary{args.out_suffix}.csv", index=False)

    # vs Random improvement (paper-style)
    rand_p5 = float(summary.loc[summary["scheme"] == "Random", "p5_se"].iloc[0])
    summary["vs_random_pct"] = 100.0 * (summary["p5_se"] - rand_p5) / rand_p5
    print(f"\n=== Mussbah Fig.1 reproduce ({args.setups} setups, {args.channel_samples} ch samples) ===")
    print(summary.to_string(index=False))

    # eCDF plot
    plt.figure(figsize=(9, 5.5))
    for name in SCHEME_ORDER:
        sub = df[df["scheme"] == name]["se_bps_per_hz"].sort_values().to_numpy()
        cdf = np.arange(1, len(sub) + 1) / len(sub)
        plt.plot(sub, cdf, label=name, color=SCHEME_COLORS.get(name, "black"), linewidth=1.6)
    plt.xlabel("Per-UE SE [bit/s/Hz/user]")
    plt.ylabel("eCDF")
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8, loc="lower right")
    plt.title(
        f"Mussbah Fig.1 paper-faithful: K={args.num_ues}, N={args.num_antennas}, "
        f"L={args.num_aps}, {args.setups} setups × {args.channel_samples} ch samples"
    )
    plt.tight_layout()
    plt.savefig(out_dir / f"mussbah_fig1_full_cdf{args.out_suffix}.png", dpi=200)
    print(f"Plot → {out_dir / f'mussbah_fig1_full_cdf{args.out_suffix}.png'}")


if __name__ == "__main__":
    main()
