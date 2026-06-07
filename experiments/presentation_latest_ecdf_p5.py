"""Generate latest six-method eCDF and 95%-likely throughput figures.

The latest presentation comparison uses the MJH environment-fixed simulator.
Five methods come from the default weighted-threshold configuration
(`edge_threshold=10`), while Mussbah Beam Graph is recovered by running the same
`Proposed` scheme with `edge_threshold=0`.
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
OUT_DIR = FIG_DIR / "presentation_6method"
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

PRESENTATION_ORDER = [
    "random",
    "gao",
    "mussbah",
    "topn",
    "beam_weighted",
    "beam_resource",
]


def make_cfg(
    args: argparse.Namespace,
    edge_threshold: float,
    k: int | None = None,
    seed_offset: int = 0,
) -> sim.SimConfig:
    return sim.SimConfig(
        L=args.L,
        K=args.K if k is None else int(k),
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


def method_lookup() -> dict[str, dict[str, object]]:
    methods = BASE_METHODS + [MUSSBAH_METHOD]
    return {str(m["method_id"]): m for m in methods}


def run_ecdf_metrics(args: argparse.Namespace) -> pd.DataFrame:
    base_cfg = make_cfg(
        args,
        edge_threshold=args.edge_threshold,
        k=args.K,
        seed_offset=args.ecdf_seed_offset,
    )
    base_metrics = sim.run_simulation(
        base_cfg,
        args.setups,
        [str(m["scheme"]) for m in BASE_METHODS],
        verbose=not args.quiet,
        workers=args.workers,
    )

    mussbah_cfg = make_cfg(
        args,
        edge_threshold=args.mussbah_edge_threshold,
        k=args.K,
        seed_offset=args.ecdf_seed_offset,
    )
    mussbah_metrics = sim.run_simulation(
        mussbah_cfg,
        args.setups,
        [str(MUSSBAH_METHOD["scheme"])],
        verbose=not args.quiet,
        workers=args.workers,
    )

    rows = []
    for method in BASE_METHODS:
        metric = base_metrics[str(method["scheme"])]
        throughput_mbps = metric.all_se_values * base_cfg.bandwidth_hz / 1e6
        for value in throughput_mbps:
            rows.append(
                {
                    "K": args.K,
                    "method_id": method["method_id"],
                    "label": method["label"],
                    "throughput_mbps": float(value),
                    "se_bps_per_hz": float(value * 1e6 / base_cfg.bandwidth_hz),
                }
            )

    metric = mussbah_metrics[str(MUSSBAH_METHOD["scheme"])]
    throughput_mbps = metric.all_se_values * mussbah_cfg.bandwidth_hz / 1e6
    for value in throughput_mbps:
        rows.append(
            {
                "K": args.K,
                "method_id": MUSSBAH_METHOD["method_id"],
                "label": MUSSBAH_METHOD["label"],
                "throughput_mbps": float(value),
                "se_bps_per_hz": float(value * 1e6 / mussbah_cfg.bandwidth_hz),
            }
        )

    return pd.DataFrame(rows)


def plot_ecdf(raw: pd.DataFrame, out_file: Path) -> None:
    lookup = method_lookup()
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    for method_id in PRESENTATION_ORDER:
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
    ax.set_title("eCDF of per-UE throughput, K=50")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.4, loc="best", framealpha=0.92)
    fig.tight_layout(pad=0.8)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def build_p5_from_latest_csv(args: argparse.Namespace) -> pd.DataFrame:
    source = OUT_DIR / "presentation_mjh_6method_k_sweep.csv"
    if not source.exists():
        raise FileNotFoundError(f"{source} not found. Run presentation_make_clean_figures.py first.")

    df = pd.read_csv(source)
    bandwidth_hz = make_cfg(args, edge_threshold=args.edge_threshold).bandwidth_hz
    out = df[["K", "method_id", "label", "likely95SE"]].copy()
    out["p5_throughput_mbps"] = out["likely95SE"].astype(float) * bandwidth_hz / 1e6
    return out


def plot_p5_vs_k(p5: pd.DataFrame, out_file: Path) -> None:
    lookup = method_lookup()
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method_id in PRESENTATION_ORDER:
        method = lookup[method_id]
        sub = p5[p5["method_id"] == method_id].sort_values("K")
        if sub.empty:
            continue
        ax.plot(
            sub["K"],
            sub["p5_throughput_mbps"],
            marker="o",
            markersize=5.3,
            color=str(method["color"]),
            linestyle=str(method["linestyle"]),
            linewidth=float(method["linewidth"]),
            label=str(method["label"]),
        )
    ax.set_xlabel("Number of users K")
    ax.set_ylabel("95%-likely per-UE throughput [Mbit/s]")
    ax.set_title("95%-likely per-UE throughput under increasing user load")
    ax.set_xticks(sorted(p5["K"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.2, loc="best", framealpha=0.92, ncols=2)
    fig.tight_layout(pad=0.7)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Latest presentation eCDF and P5 throughput figures")
    parser.add_argument("--setups", type=int, default=200)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--K", type=int, default=50)
    parser.add_argument("--L", type=int, default=200)
    parser.add_argument("--N", type=int, default=8)
    parser.add_argument("--fc-ghz", type=float, default=3.0)
    parser.add_argument("--tau-c", type=int, default=150)
    parser.add_argument("--baseline-tau-p", type=int, default=15)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--ecdf-seed-offset",
        type=int,
        default=5000,
        help="Seed offset for the eCDF run. Default 5000 matches K=50 in the default K sweep.",
    )
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
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = run_ecdf_metrics(args)
    raw_path = OUT_DIR / "presentation_latest_6method_ecdf_k50_raw.csv"
    raw.to_csv(raw_path, index=False)

    ecdf_path = OUT_DIR / "presentation_latest_6method_ecdf_throughput_k50.png"
    plot_ecdf(raw, ecdf_path)

    p5 = build_p5_from_latest_csv(args)
    p5_path = OUT_DIR / "presentation_latest_6method_p5_throughput_vs_k.csv"
    p5.to_csv(p5_path, index=False)

    p5_fig_path = OUT_DIR / "presentation_latest_6method_p5_throughput_vs_k.png"
    plot_p5_vs_k(p5, p5_fig_path)

    print(raw_path)
    print(ecdf_path)
    print(p5_path)
    print(p5_fig_path)


if __name__ == "__main__":
    main()
