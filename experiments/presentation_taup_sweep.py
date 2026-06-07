"""tau_p_design sweep on the K=50, L=200 common-ground environment.

Complements ``presentation_main_compare.py``: instead of a single
tau_p_design=15, we sweep tau_p_design across a range to show the
*unimodality* of fixed schemes (Random / GC / Structured) and the
*robustness* of adaptive schemes (Mussbah, MJH variants, Hybrid#3)
to the tau_p budget.

Outputs (MJH style, figures/):
    sweep_taup_avg_se_vs_taup.png         (line+marker, mean SE)
    sweep_taup_avg_ee_vs_taup.png         (line+marker, EE proxy)
    sweep_taup_p5_vs_taup.png             (line+marker, 5%-likely SE)
    sweep_taup_tau_actual_vs_taup.png     (line+marker, mean tau_p_actual)
    sweep_taup_pilot_box.png              (per-scheme tau_p_actual distribution)
    sweep_taup_summary.csv                (long-form table)
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

from experiments.presentation_main_compare import (
    SCHEME_ORDER,
    SCHEME_COLORS,
    build_schemes,
    compute_ee,
)


def run_sweep(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = SimulationConfig(
        num_aps=args.num_aps,
        num_ues=args.num_ues,
        tau_p=args.tau_p_list[0],  # overridden per iteration
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
    setup_records: list[dict] = []
    ue_records: list[dict] = []

    for tau_p in args.tau_p_list:
        print(f"\n######## tau_p_design = {tau_p} ########")
        topology_rng = np.random.default_rng(args.seed + tau_p)
        for r in range(args.setups):
            if not args.no_progress and (r + 1) % max(args.setups // 5, 1) == 0:
                print(f"  setup {r+1}/{args.setups}", flush=True)
            net = Network.random(config, topology_rng)
            channel_seed = args.seed + 100_000 + tau_p * 1000 + r * 13
            schemes = build_schemes(
                args.seed + 1000 * r + 7 * tau_p,
                args.delta,
                args.weight_threshold,
                args.top_n,
            )
            for name in SCHEME_ORDER:
                scheme = schemes[name]
                pilots = scheme.assign(net, tau_p)
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
                setup_records.append({
                    "tau_p_design": tau_p,
                    "setup": r,
                    "scheme": name,
                    "sum_se": sum_se,
                    "mean_se": float(np.mean(se_per_ue)),
                    "p5_se": float(np.percentile(se_per_ue, 5)),
                    "tau_p_actual": tau_p_actual,
                    "ee_bps_per_hz_per_watt": ee,
                })
                for ue_idx, ue_se in enumerate(se_per_ue):
                    ue_records.append({
                        "tau_p_design": tau_p,
                        "setup": r,
                        "ue": ue_idx,
                        "scheme": name,
                        "se_bps_per_hz": float(ue_se),
                        "tau_p_actual": tau_p_actual,
                    })

    setup_df = pd.DataFrame(setup_records)
    ue_df = pd.DataFrame(ue_records)
    return setup_df, ue_df


def summarise(setup_df: pd.DataFrame, ue_df: pd.DataFrame) -> pd.DataFrame:
    se_summary = (
        ue_df.groupby(["tau_p_design", "scheme"])
        .agg(
            p5_se=("se_bps_per_hz", lambda x: float(np.percentile(x, 5))),
            mean_se=("se_bps_per_hz", "mean"),
        )
        .reset_index()
    )
    setup_summary = (
        setup_df.groupby(["tau_p_design", "scheme"])
        .agg(
            mean_tau_p_actual=("tau_p_actual", "mean"),
            mean_ee=("ee_bps_per_hz_per_watt", "mean"),
        )
        .reset_index()
    )
    summary = se_summary.merge(setup_summary, on=["tau_p_design", "scheme"])
    return summary


# ---------------------------------------------------------------------------
# MJH-style plots (figsize 7.2x5.0, marker='o', lw=2.0, grid alpha 0.3)
# ---------------------------------------------------------------------------
def plot_sweep_line(
    summary: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    out_path: Path,
    tau_p_list: list[int],
) -> None:
    plt.figure(figsize=(7.6, 5.2))
    for name in SCHEME_ORDER:
        sub = summary[summary["scheme"] == name].sort_values("tau_p_design")
        if len(sub) != len(tau_p_list):
            continue
        plt.plot(
            sub["tau_p_design"].to_numpy(),
            sub[metric].to_numpy(),
            marker="o",
            linewidth=2.0,
            color=SCHEME_COLORS.get(name, "black"),
            label=name,
        )
    plt.xlabel(r"Design pilot budget $\tau_p^{\rm design}$")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.title(title)
    plt.legend(fontsize=7.5, loc="best", ncol=2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path.name}")


def plot_pilot_box(
    setup_df: pd.DataFrame,
    out_path: Path,
    title: str,
) -> None:
    """MJH-style box plot of tau_p_actual aggregated across all tau_p_design,
    one box per scheme."""
    data = []
    labels = []
    for name in SCHEME_ORDER:
        vals = setup_df[setup_df["scheme"] == name]["tau_p_actual"].to_numpy(dtype=float)
        if vals.size == 0:
            continue
        data.append(vals)
        labels.append(name)
    width = max(7.2, 0.55 * len(labels) + 2.0)
    plt.figure(figsize=(width, 5.2))
    positions = np.arange(1, len(labels) + 1)
    bp = plt.boxplot(data, positions=positions, tick_labels=labels, showmeans=True,
                     patch_artist=True,
                     meanprops=dict(marker="D", markerfacecolor="white",
                                    markeredgecolor="black", markersize=5))
    for patch, name in zip(bp["boxes"], labels):
        patch.set_facecolor(SCHEME_COLORS.get(name, "#888888"))
        patch.set_alpha(0.55)
    plt.ylabel(r"Actual pilot count $\tau_p^{\rm actual}$")
    plt.xlabel("Scheme")
    plt.title(title)
    plt.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved {out_path.name}")


# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--setups", type=int, default=100)
    parser.add_argument("--channel-samples", type=int, default=10)
    parser.add_argument("--tau-p-list", type=int, nargs="+",
                        default=[3, 5, 7, 9, 11, 13, 15, 18, 22])
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
    parser.add_argument("--out-suffix", type=str, default="_taup_sweep")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)

    print(
        f"\n[presentation_taup_sweep] L={args.num_aps}, K={args.num_ues}, N={args.num_antennas}, "
        f"fc={args.carrier_frequency_mhz/1000:.1f} GHz, tau_c={args.tau_c}\n"
        f"  beam-detect-snr-db={args.beam_detection_snr_db}, weight-threshold={args.weight_threshold}\n"
        f"  tau_p_list={args.tau_p_list}, {args.setups} setups x {args.channel_samples} ch samples"
    )

    setup_df, ue_df = run_sweep(args)
    summary = summarise(setup_df, ue_df)

    suffix = args.out_suffix
    setup_path = out_dir / f"sweep_taup_setup{suffix}.csv"
    ue_path = out_dir / f"sweep_taup_raw{suffix}.csv"
    summary_path = out_dir / f"sweep_taup_summary{suffix}.csv"
    setup_df.to_csv(setup_path, index=False)
    ue_df.to_csv(ue_path, index=False)
    summary.to_csv(summary_path, index=False)

    print("\n=== Summary (mean SE) ===")
    pivot_se = summary.pivot(index="scheme", columns="tau_p_design", values="mean_se").loc[SCHEME_ORDER]
    print(pivot_se.round(3).to_string())

    title_suffix = (
        f"K={args.num_ues}, L={args.num_aps}, N={args.num_antennas}, "
        f"τ_c={args.tau_c}, β-det={args.beam_detection_snr_db:.0f} dB, wt={args.weight_threshold:.0f}"
    )
    plot_sweep_line(
        summary, "mean_se",
        "Average SE [bit/s/Hz/user]",
        f"Mean per-UE SE vs design τ_p ({title_suffix})",
        out_dir / f"sweep_taup_avg_se_vs_taup{suffix}.png",
        args.tau_p_list,
    )
    plot_sweep_line(
        summary, "mean_ee",
        "EE proxy [bit/s/Hz/W]",
        f"EE proxy vs design τ_p ({title_suffix})",
        out_dir / f"sweep_taup_avg_ee_vs_taup{suffix}.png",
        args.tau_p_list,
    )
    plot_sweep_line(
        summary, "p5_se",
        "5%-likely per-UE SE [bit/s/Hz/user]",
        f"5%-likely SE vs design τ_p ({title_suffix})",
        out_dir / f"sweep_taup_p5_vs_taup{suffix}.png",
        args.tau_p_list,
    )
    plot_sweep_line(
        summary, "mean_tau_p_actual",
        r"Mean $\tau_p^{\rm actual}$",
        f"Actual pilot count vs design τ_p ({title_suffix})",
        out_dir / f"sweep_taup_tau_actual_vs_taup{suffix}.png",
        args.tau_p_list,
    )
    plot_pilot_box(
        setup_df,
        out_dir / f"sweep_taup_pilot_box{suffix}.png",
        title=f"τ_p_actual distribution across all design τ_p ({title_suffix})",
    )

    print(f"\nSetup CSV -> {setup_path.name}")
    print(f"Raw CSV -> {ue_path.name}")
    print(f"Summary CSV -> {summary_path.name}")


if __name__ == "__main__":
    main()
