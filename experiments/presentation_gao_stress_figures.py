"""Generate six-method figures in a Gao-stress environment.

This is not the main common-ground presentation setting. It intentionally uses
fewer APs and a smaller design pilot budget so Gao-style AP matching becomes
binding instead of collapsing to the Random serving set.
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


def make_cfg(args: argparse.Namespace, k: int, edge_threshold: float, seed_offset: int) -> sim.SimConfig:
    return sim.SimConfig(
        L=args.L,
        K=int(k),
        N=args.N,
        fc_ghz=args.fc_ghz,
        tau_c=args.tau_c,
        baseline_tau_p=args.baseline_tau_p,
        seed=args.seed + seed_offset,
        w_aa=args.w_aa,
        w_ai=args.w_ai,
        w_ia=args.w_ia,
        edge_threshold=edge_threshold,
        power_control=args.power_control,
    )


def metric_row(
    cfg: sim.SimConfig,
    k: int,
    method: dict[str, object],
    metric: sim.SchemeMetrics,
) -> dict[str, object]:
    return {
        "K": int(k),
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
    k: int,
    method: dict[str, object],
    metric: sim.SchemeMetrics,
) -> None:
    throughput = metric.all_se_values * cfg.bandwidth_hz / 1e6
    for value in throughput:
        rows.append(
            {
                "K": int(k),
                "method_id": method["method_id"],
                "label": method["label"],
                "throughput_mbps": float(value),
                "se_bps_per_hz": float(value * 1e6 / cfg.bandwidth_hz),
            }
        )


def run_stress(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    ecdf_rows: list[dict[str, object]] = []

    for idx, k in enumerate(args.K_list):
        seed_offset = 1000 * idx
        print(f"\n######## Gao-stress K={k} ########", flush=True)
        base_cfg = make_cfg(args, k, args.edge_threshold, seed_offset)
        base_metrics = sim.run_simulation(
            base_cfg,
            args.setups,
            [str(m["scheme"]) for m in BASE_METHODS],
            verbose=not args.quiet,
            workers=args.workers,
        )
        sim.print_metrics_table(base_metrics, base_cfg)

        mussbah_cfg = make_cfg(args, k, args.mussbah_edge_threshold, seed_offset)
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
            summary_rows.append(metric_row(base_cfg, k, method, metric))
            if int(k) == int(args.ecdf_K):
                append_ecdf_rows(ecdf_rows, base_cfg, k, method, metric)

        metric = mussbah_metrics[str(MUSSBAH_METHOD["scheme"])]
        summary_rows.append(metric_row(mussbah_cfg, k, MUSSBAH_METHOD, metric))
        if int(k) == int(args.ecdf_K):
            append_ecdf_rows(ecdf_rows, mussbah_cfg, k, MUSSBAH_METHOD, metric)

    return pd.DataFrame(summary_rows), pd.DataFrame(ecdf_rows)


def plot_line(
    df: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    out_file: Path,
) -> None:
    lookup = methods_by_id()
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method_id in METHOD_ORDER:
        method = lookup[method_id]
        sub = df[df["method_id"] == method_id].sort_values("K")
        if sub.empty:
            continue
        ax.plot(
            sub["K"],
            sub[metric],
            marker="o",
            markersize=5.3,
            linewidth=float(method["linewidth"]),
            color=str(method["color"]),
            linestyle=str(method["linestyle"]),
            alpha=0.94,
            label=str(method["label"]),
        )
    ax.set_xlabel("Number of users K")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, pad=6)
    ax.set_xticks(sorted(df["K"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.2, loc="best", framealpha=0.92, ncols=2)
    fig.tight_layout(pad=0.7)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def plot_ecdf(raw: pd.DataFrame, ecdf_k: int, out_file: Path) -> None:
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
    ax.set_title(f"eCDF of per-UE throughput, Gao-stress K={ecdf_k}")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.4, loc="best", framealpha=0.92)
    fig.tight_layout(pad=0.8)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def write_environment(args: argparse.Namespace, out_dir: Path) -> None:
    text = "\n".join(
        [
            "# Gao-Stress Presentation Figures",
            "",
            "Purpose: make Gao-style AP matching binding instead of letting it collapse to Random.",
            "",
            f"- L = {args.L}",
            f"- N = {args.N}",
            f"- K-list = {' '.join(str(k) for k in args.K_list)}",
            f"- eCDF K = {args.ecdf_K}",
            f"- baseline tau_p = {args.baseline_tau_p}",
            f"- setups = {args.setups}",
            f"- workers = {args.workers}",
            f"- edge_threshold = {args.edge_threshold}",
            f"- Mussbah edge_threshold = {args.mussbah_edge_threshold}",
            f"- bandwidth = {sim.SimConfig().bandwidth_hz / 1e6:.1f} MHz",
            "",
        ]
    )
    (out_dir / "README.md").write_text(text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gao-stress six-method presentation figures")
    parser.add_argument("--outdir", default=str(FIG_DIR / "presentation_gao_stress_L100_tau3"))
    parser.add_argument("--setups", type=int, default=200)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--L", type=int, default=100)
    parser.add_argument("--N", type=int, default=8)
    parser.add_argument("--K-list", type=int, nargs="+", default=[25, 30, 35, 40, 45, 50])
    parser.add_argument("--ecdf-K", type=int, default=45)
    parser.add_argument("--fc-ghz", type=float, default=3.0)
    parser.add_argument("--tau-c", type=int, default=150)
    parser.add_argument("--baseline-tau-p", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--w-aa", type=float, default=2.0)
    parser.add_argument("--w-ai", type=float, default=1.0)
    parser.add_argument("--w-ia", type=float, default=1.0)
    parser.add_argument("--edge-threshold", type=float, default=10.0)
    parser.add_argument("--mussbah-edge-threshold", type=float, default=0.0)
    parser.add_argument("--power-control", choices=["full", "maxmin"], default="full")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary, ecdf_raw = run_stress(args)
    summary_path = out_dir / "gao_stress_6method_summary.csv"
    ecdf_raw_path = out_dir / f"gao_stress_6method_ecdf_k{args.ecdf_K}_raw.csv"
    summary.to_csv(summary_path, index=False)
    ecdf_raw.to_csv(ecdf_raw_path, index=False)
    write_environment(args, out_dir)

    plot_line(
        summary,
        "avgSE",
        "Average SE [bit/s/Hz/user]",
        "Average SE under Gao-stress resource constraint",
        out_dir / "gao_stress_avg_se_vs_k.png",
    )
    plot_line(
        summary,
        "avgEE",
        "Average EE [bit/s/Hz/W]",
        "Average EE under Gao-stress resource constraint",
        out_dir / "gao_stress_avg_ee_vs_k.png",
    )
    plot_line(
        summary,
        "avgTauP",
        r"Average actual pilot count $\tau_p$",
        "Average pilot count under Gao-stress resource constraint",
        out_dir / "gao_stress_pilot_count_vs_k.png",
    )
    plot_line(
        summary,
        "p5ThroughputMbps",
        "95%-likely per-UE throughput [Mbit/s]",
        "95%-likely throughput under Gao-stress resource constraint",
        out_dir / "gao_stress_p5_throughput_vs_k.png",
    )
    plot_ecdf(ecdf_raw, args.ecdf_K, out_dir / f"gao_stress_ecdf_throughput_k{args.ecdf_K}.png")

    for path in [
        summary_path,
        ecdf_raw_path,
        out_dir / "gao_stress_avg_se_vs_k.png",
        out_dir / "gao_stress_avg_ee_vs_k.png",
        out_dir / "gao_stress_pilot_count_vs_k.png",
        out_dir / "gao_stress_p5_throughput_vs_k.png",
        out_dir / f"gao_stress_ecdf_throughput_k{args.ecdf_K}.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
