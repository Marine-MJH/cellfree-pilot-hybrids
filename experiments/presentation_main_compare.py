"""Presentation headline comparison: eCDF + mean SE + EE + pilot box.

Common-ground multi-antenna environment (E4):
    L=200, K=50, N=8, fc=3 GHz, tau_c=150, tau_p_design=15

User-tunable headline knobs:
    --beam-detection-snr-db 20    (MJH/Mussbah beam-report SNR threshold)
    --weight-threshold 10         (MJH weighted-threshold)
    --top-n 10                    (TopAP family)

Schemes compared (12 total):
    Baselines:               Random, Gao matching, GC (Liu), Structured (Chen)
    Mussbah family:          Mussbah, MJH weighted-count default, MJH weighted-count strict,
                             MJH weighted-power, MJH beam-resource matching
    TopAP/Hybrid family:     TopAP (bisect), Hybrid#3 (TopAP N=8 adaptive),
                             Hybrid#4 (TopAP+greedy)

Outputs (figures/):
    presentation_main_raw{suffix}.csv         (per-UE SE long-form)
    presentation_main_summary{suffix}.csv     (per-scheme aggregated)
    presentation_main_ecdf{suffix}.png        (eCDF of per-UE SE)
    presentation_main_mean_se{suffix}.png     (bar: mean SE per scheme)
    presentation_main_ee{suffix}.png          (bar: EE per scheme — ref12-rf proxy)
    presentation_main_pilot_box{suffix}.png   (box: tau_p_actual per scheme)
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
    BeamResourceMatchingPilotAssignment,
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
    "MJH weighted-count default",
    "MJH weighted-count strict",
    "MJH weighted-power",
    "MJH beam-resource matching",
    "TopAP (bisect)",
    "Hybrid#3 (TopAP N=8 adaptive)",
    "Hybrid#4 (TopAP+greedy)",
]

SCHEME_COLORS = {
    "Random": "#888888",
    "Gao matching": "#0072bd",
    "GC (Liu)": "#2ca02c",
    "Structured (Chen)": "#d6275f",
    "Mussbah": "#ff7f0e",
    "MJH weighted-count default": "#fdae61",
    "MJH weighted-count strict": "#d73027",
    "MJH weighted-power": "#b15928",
    "MJH beam-resource matching": "#4f00b3",
    "TopAP (bisect)": "#9467bd",
    "Hybrid#3 (TopAP N=8 adaptive)": "#e377c2",
    "Hybrid#4 (TopAP+greedy)": "#8c564b",
}

# Scheme category (for EE active-resource estimation)
BEAM_AWARE = {
    "Mussbah",
    "MJH weighted-count default",
    "MJH weighted-count strict",
    "MJH weighted-power",
    "MJH beam-resource matching",
}
TOPAP_FAMILY = {
    "TopAP (bisect)": ("n_used_", 10),
    "Hybrid#3 (TopAP N=8 adaptive)": ("n_used_", 8),
    "Hybrid#4 (TopAP+greedy)": ("top_n", 10),
}


def build_schemes(seed_base: int, delta: float, weight_threshold: float, top_n: int) -> dict:
    return {
        "Random": RandomPilotAssignment(seed=seed_base + 1),
        "Gao matching": MatchingBasedPilotAssignment(seed=seed_base + 2),
        "GC (Liu)": GraphColoringPilotAssignment(seed=seed_base + 3),
        "Structured (Chen)": StructuredPilotAccessAssignment(seed=seed_base + 4),
        "Mussbah": BeamDomainPilotAssignment(
            seed=seed_base + 5, delta=delta, adaptive_tau_p=True
        ),
        "MJH weighted-count default": WeightedBeamThresholdPilotAssignment(
            seed=seed_base + 6, delta=delta,
            variant="weighted-count", w_aa=2.0, w_am=1.0, threshold=0.0,
            adaptive_tau_p=True,
        ),
        "MJH weighted-count strict": WeightedBeamThresholdPilotAssignment(
            seed=seed_base + 7, delta=delta,
            variant="weighted-count", w_aa=2.0, w_am=1.0,
            threshold=float(weight_threshold),
            adaptive_tau_p=True,
        ),
        "MJH weighted-power": WeightedBeamThresholdPilotAssignment(
            seed=seed_base + 8, delta=delta,
            variant="weighted-power", w_aa=2.0, w_am=1.0, threshold=0.0,
            adaptive_tau_p=True,
        ),
        "MJH beam-resource matching": BeamResourceMatchingPilotAssignment(
            seed=seed_base + 9, delta=delta, baseline_tau_p=10, adaptive_tau_p=True,
        ),
        "TopAP (bisect)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 10, bisect=True, top_n=top_n
        ),
        "Hybrid#3 (TopAP N=8 adaptive)": TopAPGraphColoringPilotAssignment(
            seed=seed_base + 11, bisect=False, top_n=8, adaptive_tau_p=True
        ),
        "Hybrid#4 (TopAP+greedy)": Hybrid4TopAPGreedyPilotAssignment(
            seed=seed_base + 12, top_n=top_n
        ),
    }


# ---------------------------------------------------------------------------
# EE proxy (teammate's ref12-rf model — common across schemes)
# ---------------------------------------------------------------------------
P_USER_W = 0.1
P_FIX_W = 0.825
P_RF_W = 0.04
PA_ETA = 0.3
P_DATA_W = 0.1  # max uplink data power per UE (assume full power)


def estimate_active_resources(name: str, scheme, network: Network) -> tuple[int, int]:
    """Return (n_active_AP, n_active_RF_chains). Heuristic per scheme family."""
    L = int(network.num_aps)
    N = int(network.num_antennas_per_ap)
    K = int(network.num_ues)

    if name in BEAM_AWARE:
        b_active, _ = network.beam_info(delta=0.95)
        beam_active = b_active.any(axis=1)  # (L*N,)
        beam_active_LN = beam_active.reshape(L, N)
        ap_active_mask = beam_active_LN.any(axis=1)
        n_active_ap = int(ap_active_mask.sum())
        n_active_rf = int(beam_active.sum())
        return n_active_ap, n_active_rf

    if name in TOPAP_FAMILY:
        attr, fallback_top_n = TOPAP_FAMILY[name]
        top_n_used = getattr(scheme, attr, None)
        if top_n_used is None or top_n_used <= 0:
            top_n_used = fallback_top_n
        # Exact union of per-UE top-N APs from large-scale fading
        beta = network.beta  # (K, L)
        top_n_used = max(1, min(int(top_n_used), L))
        top_idx = np.argsort(beta, axis=1)[:, -top_n_used:]
        unique_aps = np.unique(top_idx.ravel())
        n_active_ap = int(unique_aps.size)
        n_active_rf = n_active_ap * N
        return n_active_ap, n_active_rf

    # Baselines: all APs active, all RF chains hot
    return L, L * N


def compute_ee(name: str, scheme, network: Network, sum_se_bps_per_hz_per_setup: float) -> float:
    """EE = mean(sum_SE) / P_total. ref12-rf model. sum_SE is per-Hz spectral efficiency
    summed over UEs."""
    n_ap, n_rf = estimate_active_resources(name, scheme, network)
    K = int(network.num_ues)
    N = int(network.num_antennas_per_ap)
    p_tx = K * P_DATA_W / PA_ETA
    p_ap_base = max(P_FIX_W - N * P_RF_W, 0.0)
    p_ap_total = n_ap * p_ap_base + n_rf * P_RF_W
    p_total = p_tx + K * P_USER_W + p_ap_total
    return sum_se_bps_per_hz_per_setup / max(p_total, 1e-12)


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
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
    setup_ee_records: list[dict] = []

    for r in range(args.setups):
        if not args.no_progress and (r + 1) % 10 == 0:
            print(f"  setup {r+1}/{args.setups}", flush=True)

        net = Network.random(config, topology_rng)
        channel_seed = args.seed + 100_000 + r * 13
        schemes = build_schemes(
            args.seed + 1000 * r, args.delta, args.weight_threshold, args.top_n
        )

        for name in SCHEME_ORDER:
            scheme = schemes[name]
            pilots = scheme.assign(net, args.tau_p)
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
            sum_se = float(np.sum(se_per_ue))
            ee = compute_ee(name, scheme, net, sum_se)
            n_ap, n_rf = estimate_active_resources(name, scheme, net)
            setup_ee_records.append({
                "setup": r,
                "scheme": name,
                "sum_se": sum_se,
                "mean_se": float(np.mean(se_per_ue)),
                "tau_p_actual": tau_p_actual,
                "n_active_ap": n_ap,
                "n_active_rf": n_rf,
                "ee_bps_per_hz_per_watt": ee,
            })
            for ue_idx, ue_se in enumerate(se_per_ue):
                records.append({
                    "setup": r,
                    "ue": ue_idx,
                    "scheme": name,
                    "se_bps_per_hz": float(ue_se),
                    "tau_p_actual": tau_p_actual,
                })

    raw_df = pd.DataFrame(records)
    setup_df = pd.DataFrame(setup_ee_records)
    return raw_df, setup_df


def summarise(raw_df: pd.DataFrame, setup_df: pd.DataFrame) -> pd.DataFrame:
    se_summary = (
        raw_df.groupby("scheme")
        .agg(
            p5_se=("se_bps_per_hz", lambda x: float(np.percentile(x, 5))),
            median_se=("se_bps_per_hz", "median"),
            mean_se=("se_bps_per_hz", "mean"),
        )
        .reset_index()
    )
    setup_summary = (
        setup_df.groupby("scheme")
        .agg(
            mean_tau_p=("tau_p_actual", "mean"),
            median_tau_p=("tau_p_actual", "median"),
            p25_tau_p=("tau_p_actual", lambda x: float(np.percentile(x, 25))),
            p75_tau_p=("tau_p_actual", lambda x: float(np.percentile(x, 75))),
            min_tau_p=("tau_p_actual", "min"),
            max_tau_p=("tau_p_actual", "max"),
            mean_n_active_ap=("n_active_ap", "mean"),
            mean_n_active_rf=("n_active_rf", "mean"),
            mean_ee=("ee_bps_per_hz_per_watt", "mean"),
        )
        .reset_index()
    )
    summary = se_summary.merge(setup_summary, on="scheme")
    summary = summary.set_index("scheme").loc[SCHEME_ORDER].reset_index()
    rnd_mean = float(summary.loc[summary["scheme"] == "Random", "mean_se"].iloc[0])
    rnd_p5 = float(summary.loc[summary["scheme"] == "Random", "p5_se"].iloc[0])
    rnd_ee = float(summary.loc[summary["scheme"] == "Random", "mean_ee"].iloc[0])
    summary["mean_vs_random_pct"] = 100.0 * (summary["mean_se"] - rnd_mean) / rnd_mean
    summary["p5_vs_random_pct"] = 100.0 * (summary["p5_se"] - rnd_p5) / rnd_p5
    summary["ee_vs_random_pct"] = 100.0 * (summary["mean_ee"] - rnd_ee) / rnd_ee
    return summary


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_ecdf(raw_df: pd.DataFrame, args: argparse.Namespace, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    for name in SCHEME_ORDER:
        vals = raw_df[raw_df["scheme"] == name]["se_bps_per_hz"].sort_values().to_numpy()
        if vals.size == 0:
            continue
        cdf = np.arange(1, len(vals) + 1) / len(vals)
        lw = 1.9 if name in {"MJH beam-resource matching", "Hybrid#3 (TopAP N=8 adaptive)", "MJH weighted-count strict"} else 1.3
        ax.plot(vals, cdf, label=name, color=SCHEME_COLORS.get(name, "black"), linewidth=lw)
    ax.set_xlabel("Per-UE SE [bit/s/Hz]")
    ax.set_ylabel("eCDF")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.0, loc="lower right", ncol=1)
    ax.set_title(
        f"eCDF of per-UE SE (E4, beam-SNR={args.beam_detection_snr_db:.0f} dB, "
        f"weight-thr={args.weight_threshold:.0f})"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_mean_se(summary: pd.DataFrame, args: argparse.Namespace, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    names = summary["scheme"].tolist()
    means = summary["mean_se"].to_numpy()
    colors = [SCHEME_COLORS.get(n, "black") for n in names]
    bars = ax.bar(range(len(names)), means, color=colors)
    for i, (n, m) in enumerate(zip(names, means)):
        pct = summary["mean_vs_random_pct"].iloc[i]
        ax.text(i, m + 0.05, f"{m:.2f}\n({pct:+.1f}%)", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Mean per-UE SE [bit/s/Hz]")
    ax.set_title(
        f"Mean per-UE SE — averaged over {args.num_ues} UEs and "
        f"{args.setups}×{args.channel_samples} MC realisations\n"
        f"(% vs Random shown below value)"
    )
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(means) * 1.18)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_ee(summary: pd.DataFrame, args: argparse.Namespace, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    names = summary["scheme"].tolist()
    ee = summary["mean_ee"].to_numpy()
    colors = [SCHEME_COLORS.get(n, "black") for n in names]
    bars = ax.bar(range(len(names)), ee, color=colors)
    for i, (n, e) in enumerate(zip(names, ee)):
        pct = summary["ee_vs_random_pct"].iloc[i]
        ax.text(i, e + max(ee) * 0.01, f"{e:.3f}\n({pct:+.1f}%)", ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("EE [bit/s/Hz / W]  (ref12-rf proxy)")
    ax.set_title(
        f"Energy Efficiency proxy — sum_SE / P_total (ref12-rf model)\n"
        f"P = K·p_user + ΣAP·p_ap_base + ΣRF·p_rf + K·p_data/η"
    )
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(ee) * 1.18)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def plot_pilot_box(setup_df: pd.DataFrame, args: argparse.Namespace, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    data = [
        setup_df[setup_df["scheme"] == name]["tau_p_actual"].to_numpy()
        for name in SCHEME_ORDER
    ]
    colors = [SCHEME_COLORS.get(n, "black") for n in SCHEME_ORDER]
    bp = ax.boxplot(
        data,
        labels=SCHEME_ORDER,
        patch_artist=True,
        showmeans=True,
        meanprops=dict(marker="D", markerfacecolor="white", markeredgecolor="black", markersize=5),
    )
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
    for i, name in enumerate(SCHEME_ORDER):
        mean = float(np.mean(data[i])) if len(data[i]) else 0.0
        ax.text(i + 1, mean, f"  {mean:.1f}", va="center", ha="left", fontsize=7.5, color="black")
    ax.axhline(args.tau_p, color="#444444", linestyle="--", linewidth=0.8,
               label=f"τ_p_design = {args.tau_p}")
    ax.set_xticklabels(SCHEME_ORDER, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("τ_p actual (chromatic number)")
    ax.set_title(
        f"Actual pilot count distribution across {args.setups} setups\n"
        f"(Mean shown as diamond; design τ_p = {args.tau_p} dashed)"
    )
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
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
    parser.add_argument("--beam-detection-snr-db", type=float, default=20.0)
    parser.add_argument("--weight-threshold", type=float, default=10.0)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--out-suffix", type=str, default="_main")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)

    print(
        f"\n[presentation_main_compare] L={args.num_aps}, K={args.num_ues}, N={args.num_antennas}, "
        f"fc={args.carrier_frequency_mhz/1000:.1f} GHz, tau_c={args.tau_c}, tau_p_design={args.tau_p}\n"
        f"  beam-detect-snr-db={args.beam_detection_snr_db}, weight-threshold={args.weight_threshold}, "
        f"top-n={args.top_n}\n"
        f"  {args.setups} setups x {args.channel_samples} channel samples"
    )

    raw_df, setup_df = run(args)
    suffix = args.out_suffix
    raw_path = out_dir / f"presentation_main_raw{suffix}.csv"
    setup_path = out_dir / f"presentation_main_setup{suffix}.csv"
    raw_df.to_csv(raw_path, index=False)
    setup_df.to_csv(setup_path, index=False)

    summary = summarise(raw_df, setup_df)
    summary_path = out_dir / f"presentation_main_summary{suffix}.csv"
    summary.to_csv(summary_path, index=False)

    print("\n=== presentation_main_compare summary ===")
    cols_show = [
        "scheme", "p5_se", "mean_se", "mean_vs_random_pct",
        "mean_tau_p", "mean_n_active_rf", "mean_ee", "ee_vs_random_pct",
    ]
    print(summary[cols_show].to_string(index=False))

    plot_ecdf(raw_df, args, out_dir / f"presentation_main_ecdf{suffix}.png")
    plot_mean_se(summary, args, out_dir / f"presentation_main_mean_se{suffix}.png")
    plot_ee(summary, args, out_dir / f"presentation_main_ee{suffix}.png")
    plot_pilot_box(setup_df, args, out_dir / f"presentation_main_pilot_box{suffix}.png")

    print(f"\nRaw -> {raw_path}")
    print(f"Setup -> {setup_path}")
    print(f"Summary -> {summary_path}")
    print(f"Figures -> presentation_main_{{ecdf,mean_se,ee,pilot_box}}{suffix}.png")


if __name__ == "__main__":
    main()
