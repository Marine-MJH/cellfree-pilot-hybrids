"""Run N-sweep six-method presentation comparison.

This keeps the presentation_6method setting fixed, holds K=50, and sweeps the
number of AP antennas N from 1 to 8.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = PROJECT_ROOT / "figures"
MJH_DIR = PROJECT_ROOT / "MJH"
sys.path.insert(0, str(MJH_DIR))

import all_schemes_ap_domain_hybrids_pilot_boxplot_env_fixed as sim  # noqa: E402


BASE_METHODS = [
    {
        "scheme": "Random",
        "method_id": "random",
        "label": "Random",
        "color": "#6f6f6f",
        "linestyle": "-",
        "linewidth": 2.3,
    },
    {
        "scheme": "GaoMatching",
        "method_id": "gao",
        "label": "Gao Matching",
        "color": "#1f78b4",
        "linestyle": ":",
        "linewidth": 2.0,
    },
    {
        "scheme": "H3TopAPAdaptive",
        "method_id": "topn",
        "label": "AP-Top-N (N=8)",
        "color": "#e7298a",
        "linestyle": "--",
        "linewidth": 2.4,
    },
    {
        "scheme": "Proposed",
        "method_id": "beam_weighted",
        "label": "Beam-Weighted Threshold",
        "color": "#d95f02",
        "linestyle": "--",
        "linewidth": 2.4,
    },
    {
        "scheme": "MatchingBeamAdaptive",
        "method_id": "beam_resource",
        "label": "Beam-Resource Matching",
        "color": "#7b3294",
        "linestyle": "--",
        "linewidth": 2.4,
    },
]

MUSSBAH_METHOD = {
    "scheme": "Proposed",
    "method_id": "mussbah",
    "label": "Mussbah Beam Graph",
    "color": "#009e73",
    "linestyle": "-.",
    "linewidth": 2.2,
}

METHOD_ORDER = ["random", "gao", "mussbah", "topn", "beam_weighted", "beam_resource"]


def methods_by_id() -> dict[str, dict[str, object]]:
    return {str(m["method_id"]): m for m in [*BASE_METHODS, MUSSBAH_METHOD]}


def make_cfg(args: argparse.Namespace, n_ant: int, edge_threshold: float, seed_offset: int) -> sim.SimConfig:
    return sim.SimConfig(
        L=args.L,
        K=args.K,
        N=int(n_ant),
        fc_ghz=args.fc_ghz,
        tau_c=args.tau_c,
        baseline_tau_p=args.baseline_tau_p,
        beam_detect_snr_db=args.beam_detect_snr_db,
        seed=args.seed + seed_offset,
        w_aa=args.w_aa,
        w_ai=args.w_ai,
        w_ia=args.w_ia,
        edge_threshold=edge_threshold,
        matching_resource_quota=args.matching_resource_quota,
        power_control=args.power_control,
        power_model=args.power_model,
        fronthaul_mode=args.fronthaul_mode,
    )


def metric_row(
    cfg: sim.SimConfig,
    n_ant: int,
    method: dict[str, object],
    metric: sim.SchemeMetrics,
) -> dict[str, object]:
    return {
        "N": int(n_ant),
        "K": int(cfg.K),
        "method_id": method["method_id"],
        "label": method["label"],
        "scheme": method["scheme"],
        "avgSE": metric.avg_se_per_user,
        "likely95SE": metric.likely95_se,
        "avgEE": metric.avg_ee,
        "avgTauP": metric.avg_tau_p,
        "avgRF": metric.avg_active_rf,
        "avgEdges": metric.avg_edges,
        "avgThroughputMbps": metric.avg_se_per_user * cfg.bandwidth_hz / 1e6,
        "p5ThroughputMbps": metric.likely95_se * cfg.bandwidth_hz / 1e6,
    }


def append_ecdf_rows(
    rows: list[dict[str, object]],
    cfg: sim.SimConfig,
    n_ant: int,
    method: dict[str, object],
    metric: sim.SchemeMetrics,
) -> None:
    throughput = metric.all_se_values * cfg.bandwidth_hz / 1e6
    for value in throughput:
        rows.append(
            {
                "N": int(n_ant),
                "K": int(cfg.K),
                "method_id": method["method_id"],
                "label": method["label"],
                "throughput_mbps": float(value),
                "se_bps_per_hz": float(value * 1e6 / cfg.bandwidth_hz),
            }
        )


def run_n_sweep(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    ecdf_rows: list[dict[str, object]] = []

    for idx, n_ant in enumerate(args.N_list):
        seed_offset = 1000 * idx
        print(f"\n######## N-sweep six-method N={n_ant} ########", flush=True)
        base_cfg = make_cfg(args, n_ant, args.edge_threshold, seed_offset)
        base_metrics = sim.run_simulation(
            base_cfg,
            args.setups,
            [str(m["scheme"]) for m in BASE_METHODS],
            verbose=not args.quiet,
            workers=args.workers,
        )
        sim.print_metrics_table(base_metrics, base_cfg)

        mussbah_cfg = make_cfg(args, n_ant, args.mussbah_edge_threshold, seed_offset)
        mussbah_metrics = sim.run_simulation(
            mussbah_cfg,
            args.setups,
            [str(MUSSBAH_METHOD["scheme"])],
            verbose=not args.quiet,
            workers=args.workers,
        )
        sim.print_metrics_table(mussbah_metrics, mussbah_cfg)

        for method in BASE_METHODS:
            metric = base_metrics[str(method["scheme"])]
            summary_rows.append(metric_row(base_cfg, n_ant, method, metric))
            if int(n_ant) == int(args.ecdf_N):
                append_ecdf_rows(ecdf_rows, base_cfg, n_ant, method, metric)

        metric = mussbah_metrics[str(MUSSBAH_METHOD["scheme"])]
        summary_rows.append(metric_row(mussbah_cfg, n_ant, MUSSBAH_METHOD, metric))
        if int(n_ant) == int(args.ecdf_N):
            append_ecdf_rows(ecdf_rows, mussbah_cfg, n_ant, MUSSBAH_METHOD, metric)

    return pd.DataFrame(summary_rows), pd.DataFrame(ecdf_rows)


def plot_line(df: pd.DataFrame, metric: str, ylabel: str, title: str, out_file: Path) -> None:
    lookup = methods_by_id()
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method_id in METHOD_ORDER:
        method = lookup[method_id]
        sub = df[df["method_id"] == method_id].sort_values("N")
        if sub.empty:
            continue
        ax.plot(
            sub["N"],
            sub[metric],
            marker="o",
            markersize=5.3,
            linewidth=float(method["linewidth"]),
            color=str(method["color"]),
            linestyle=str(method["linestyle"]),
            alpha=0.94,
            label=str(method["label"]),
        )
    ax.set_xlabel("Number of antennas per AP N")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, pad=6)
    ax.set_xticks(sorted(df["N"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.2, loc="best", framealpha=0.92, ncols=2)
    fig.tight_layout(pad=0.7)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def plot_ecdf(raw: pd.DataFrame, ecdf_n: int, out_file: Path) -> None:
    lookup = methods_by_id()
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    for method_id in METHOD_ORDER:
        method = lookup[method_id]
        vals = np.sort(raw.loc[raw["method_id"] == method_id, "throughput_mbps"].to_numpy(dtype=float))
        if vals.size == 0:
            continue
        y = np.arange(1, vals.size + 1, dtype=float) / vals.size
        ax.plot(
            vals,
            y,
            color=str(method["color"]),
            linestyle=str(method["linestyle"]),
            linewidth=float(method["linewidth"]),
            label=str(method["label"]),
        )
    ax.set_xlabel("Per-UE throughput [Mbit/s]")
    ax.set_ylabel("eCDF")
    ax.set_title(f"eCDF of per-UE throughput, K=50, N={ecdf_n}")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.4, loc="best", framealpha=0.92)
    fig.tight_layout(pad=0.8)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def write_environment(args: argparse.Namespace, out_dir: Path) -> None:
    text = "\n".join(
        [
            "# N-Sweep 6-Method Presentation Figures",
            "",
            "Purpose: keep the presentation_6method setting fixed, hold K=50, and sweep AP antenna count N from 1 to 8.",
            "",
            "Simulation setting:",
            "",
            f"- L = {args.L} APs",
            f"- K = {args.K} UEs",
            f"- N-list = {' '.join(str(n) for n in args.N_list)}",
            f"- eCDF N = {args.ecdf_N}",
            f"- tau_c = {args.tau_c}",
            f"- baseline/design tau_p = {args.baseline_tau_p}",
            f"- setups = {args.setups}",
            f"- workers = {args.workers}",
            f"- carrier = {args.fc_ghz} GHz",
            f"- beam_detect_snr_db = {args.beam_detect_snr_db}",
            f"- power_control = {args.power_control}",
            f"- power_model = {args.power_model}",
            f"- fronthaul_mode = {args.fronthaul_mode}",
            f"- weighted graph weights: w_aa = {args.w_aa}, w_ai = {args.w_ai}, w_ia = {args.w_ia}",
            f"- Beam-Weighted Threshold edge_threshold = {args.edge_threshold}",
            f"- Mussbah Beam Graph edge_threshold = {args.mussbah_edge_threshold}",
            f"- matching_resource_quota = {args.matching_resource_quota} (0 means baseline tau_p)",
            f"- seed = {args.seed}",
            "",
            "Methods:",
            "",
            "- Random",
            "- Gao Matching",
            "- Mussbah Beam Graph",
            "- AP-Top-N (N=8)",
            "- Beam-Weighted Threshold",
            "- Beam-Resource Matching",
            "",
            "Outputs:",
            "",
            "- n_sweep_6method_summary.csv",
            "- n_sweep_6method_ecdf_raw.csv",
            "- n_sweep_avg_se_vs_n.png",
            "- n_sweep_avg_ee_vs_n.png",
            "- n_sweep_pilot_count_vs_n.png",
            "- n_sweep_p5_throughput_vs_n.png",
            "- n_sweep_ecdf_throughput.png",
            "",
        ]
    )
    (out_dir / "README.md").write_text(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="N-sweep six-method presentation figures")
    parser.add_argument("--outdir", default=str(FIG_DIR / "presentation_n_sweep_6method"))
    parser.add_argument("--setups", type=int, default=200)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--L", type=int, default=200)
    parser.add_argument("--K", type=int, default=50)
    parser.add_argument("--N-list", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6, 7, 8])
    parser.add_argument("--ecdf-N", type=int, default=8)
    parser.add_argument("--fc-ghz", type=float, default=3.0)
    parser.add_argument("--tau-c", type=int, default=150)
    parser.add_argument("--baseline-tau-p", type=int, default=15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--beam-detect-snr-db", type=float, default=0.0)
    parser.add_argument("--w-aa", type=float, default=2.0)
    parser.add_argument("--w-ai", type=float, default=1.0)
    parser.add_argument("--w-ia", type=float, default=1.0)
    parser.add_argument("--edge-threshold", type=float, default=10.0)
    parser.add_argument("--mussbah-edge-threshold", type=float, default=0.0)
    parser.add_argument("--matching-resource-quota", type=int, default=0)
    parser.add_argument("--power-control", choices=["full", "maxmin"], default="full")
    parser.add_argument("--power-model", choices=["ref12-rf", "ref12-strict", "simple"], default="ref12-rf")
    parser.add_argument("--fronthaul-mode", choices=["all_users", "active_users", "active_rf"], default="active_users")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary, ecdf = run_n_sweep(args)
    summary_path = out_dir / "n_sweep_6method_summary.csv"
    ecdf_path = out_dir / "n_sweep_6method_ecdf_raw.csv"
    summary.to_csv(summary_path, index=False)
    ecdf.to_csv(ecdf_path, index=False)

    plot_line(
        summary,
        "avgSE",
        "Average SE [bit/s/Hz/user]",
        "Average SE under AP antenna sweep",
        out_dir / "n_sweep_avg_se_vs_n.png",
    )
    plot_line(
        summary,
        "avgEE",
        "Average EE [bit/s/Hz/W]",
        "Energy efficiency under AP antenna sweep",
        out_dir / "n_sweep_avg_ee_vs_n.png",
    )
    plot_line(
        summary,
        "avgTauP",
        r"Average actual pilot count $\tau_p$",
        "Average pilot count under AP antenna sweep",
        out_dir / "n_sweep_pilot_count_vs_n.png",
    )
    plot_line(
        summary,
        "p5ThroughputMbps",
        "95%-likely per-UE throughput [Mbit/s]",
        "95%-likely throughput under AP antenna sweep",
        out_dir / "n_sweep_p5_throughput_vs_n.png",
    )
    if not ecdf.empty:
        plot_ecdf(ecdf, args.ecdf_N, out_dir / "n_sweep_ecdf_throughput.png")
    write_environment(args, out_dir)

    for path in [
        out_dir / "README.md",
        summary_path,
        ecdf_path,
        out_dir / "n_sweep_avg_se_vs_n.png",
        out_dir / "n_sweep_avg_ee_vs_n.png",
        out_dir / "n_sweep_pilot_count_vs_n.png",
        out_dir / "n_sweep_p5_throughput_vs_n.png",
        out_dir / "n_sweep_ecdf_throughput.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
