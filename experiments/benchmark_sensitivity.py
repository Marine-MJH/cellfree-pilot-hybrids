"""Benchmark sensitivity study.

Quantitative test of two claims:

1. Liu 2020 / Chen 2021 *as we implemented them* (with full θ/δ bisection) are
   stronger than likely-naive reimplementations. If Gao paper's reference of
   [14] and [15] was naive (no bisection), Gao would beat them — recovering the
   paper's ordering. We test by including no-bisection variants alongside the
   full ones.
2. Gao matching suffers from cross-group pilot collisions that Liu/Chen avoid
   by construction. We measure pilot-collision strength directly via a
   contamination metric.

Run example:
    python experiments/benchmark_sensitivity.py --realizations 50 --no-progress
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _common import (
    PROJECT_ROOT,
    SimulationConfig,
    ensure_figures_dir,
)
from src.network import Network
from src.pilot_schemes import (
    GraphColoringPilotAssignment,
    MatchingBasedPilotAssignment,
    RandomPilotAssignment,
    StructuredPilotAccessAssignment,
    TopAPGraphColoringPilotAssignment,
    UpperBoundPilotAssignment,
)
from src.power_control import FractionalPowerControl
from src.metrics import likely_95, per_ue_throughput_bps


# ---------------------------------------------------------------------------
# Scheme variants
# ---------------------------------------------------------------------------
def build_schemes(seed: int):
    """Return a flat list of (name, scheme) including bisection on/off variants."""
    return [
        ("Upper bound", UpperBoundPilotAssignment(seed=seed + 1)),
        ("Gao matching", MatchingBasedPilotAssignment(seed=seed + 2)),
        # Liu 2020 — full implementation with θ-bisection (authors' MATLAB code)
        (
            "Graph coloring (full bisection)",
            GraphColoringPilotAssignment(seed=seed + 3),
        ),
        # Liu 2020 — naive variant: single iteration with fixed initial θ,
        # mirroring a paper-text-only reimplementation that drops the bisection
        # enhancement. We try a couple of fixed θ values to cover the range.
        (
            "Graph coloring (no bisection, θ=0.6)",
            GraphColoringPilotAssignment(seed=seed + 4, theta_init=0.6, max_bisection_iters=1),
        ),
        (
            "Graph coloring (no bisection, θ=0.9)",
            GraphColoringPilotAssignment(seed=seed + 5, theta_init=0.9, max_bisection_iters=1),
        ),
        # Chen 2021 — full with δ-bisection
        (
            "Structured access (full bisection)",
            StructuredPilotAccessAssignment(seed=seed + 6),
        ),
        # Chen 2021 — naive: fixed δ, single iteration
        (
            "Structured access (no bisection, δ=0.3)",
            StructuredPilotAccessAssignment(seed=seed + 7, delta_init=0.3, max_bisection_iters=1),
        ),
        (
            "Structured access (no bisection, δ=0.5)",
            StructuredPilotAccessAssignment(seed=seed + 8, delta_init=0.5, max_bisection_iters=1),
        ),
        # Hybrid #1 (Diagnosis.md §5.2) — Top-N strong-AP overlap conflict graph
        (
            "Top-AP coloring (N=10)",
            TopAPGraphColoringPilotAssignment(seed=seed + 10, top_n=10),
        ),
        (
            "Top-AP coloring (N=5)",
            TopAPGraphColoringPilotAssignment(seed=seed + 11, top_n=5),
        ),
        (
            "Top-AP coloring (N=3)",
            TopAPGraphColoringPilotAssignment(seed=seed + 12, top_n=3),
        ),
        # Hybrid #1 + N-bisection (Diagnosis.md §7 step A)
        (
            "Top-AP coloring (bisect)",
            TopAPGraphColoringPilotAssignment(seed=seed + 13, top_n=10, bisect=True),
        ),
        ("Random", RandomPilotAssignment(seed=seed + 9)),
    ]


# ---------------------------------------------------------------------------
# Contamination metric: total "shared-pilot β·β co-location"
# ---------------------------------------------------------------------------
def contamination_strength(network: Network, pilot_assignment: np.ndarray) -> float:
    """Sum over (m,m') with same pilot and m≠m' of Σ_k β_{mk} β_{m'k}.

    Higher = more pilot contamination potential. Independent of power
    control — purely about the *assignment quality*.
    """
    beta = network.beta  # (M, K)
    same_pilot = pilot_assignment[:, None] == pilot_assignment[None, :]
    np.fill_diagonal(same_pilot, False)
    # Compute the (M,M) co-location matrix C[m,m'] = Σ_k β_{mk} β_{m'k}
    # but only sum over same-pilot pairs to avoid the M² K cost.
    total = 0.0
    for pilot in np.unique(pilot_assignment):
        users = np.flatnonzero(pilot_assignment == pilot)
        if users.size < 2:
            continue
        sub_beta = beta[users]  # (g, K)
        co_loc = sub_beta @ sub_beta.T  # (g, g)
        np.fill_diagonal(co_loc, 0.0)
        total += float(co_loc.sum())
    return total


# ---------------------------------------------------------------------------
# Sweep over τ_p
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark sensitivity study")
    parser.add_argument("--realizations", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tau-values", type=int, nargs="+", default=[10, 20, 30])
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--out-suffix", type=str, default="")
    args = parser.parse_args()

    base_config = SimulationConfig(num_aps=500, num_ues=200, tau_p=20, random_seed=args.seed)
    power_control = FractionalPowerControl(alpha=0.5)

    records: list[dict[str, float | int | str]] = []
    rng = np.random.default_rng(args.seed)

    for tau_p in args.tau_values:
        if not args.no_progress:
            print(f"\n=== τ_p = {tau_p} ===")
        for r in range(args.realizations):
            network = Network.random(base_config, rng)
            for name, scheme in build_schemes(args.seed + 1000 * r):
                pilots = scheme.assign(network, tau_p)
                contam = contamination_strength(network, pilots)
                serving = scheme.serving_matrix(network)
                powers = power_control.compute(network, pilots, serving_mask=serving)
                throughputs = per_ue_throughput_bps(
                    network, pilots, powers, tau_p, serving_mask=serving
                )
                for tp in throughputs:
                    records.append(
                        {
                            "tau_p": tau_p,
                            "realization": r,
                            "scheme": name,
                            "throughput_mbps": float(tp) / 1e6,
                            "contamination": contam,
                        }
                    )
            if not args.no_progress and (r + 1) % 5 == 0:
                print(f"  realization {r+1}/{args.realizations} done")

    frame = pd.DataFrame(records)

    # --- Summary: P5 throughput and mean contamination per (τ_p, scheme) ---
    summary = (
        frame.groupby(["tau_p", "scheme"])
        .agg(
            p5_mbps=("throughput_mbps", lambda x: np.percentile(x, 5)),
            median_mbps=("throughput_mbps", "median"),
            mean_contamination=("contamination", "mean"),
        )
        .reset_index()
    )

    out_dir = ensure_figures_dir()
    summary_path = out_dir / f"benchmark_sensitivity_summary{args.out_suffix}.csv"
    summary.to_csv(summary_path, index=False)
    raw_path = out_dir / f"benchmark_sensitivity_raw{args.out_suffix}.csv"
    frame.to_csv(raw_path, index=False)
    print(f"\nSummary written to {summary_path}")
    print(f"Raw per-UE throughputs written to {raw_path} (for bootstrap CI)")
    print(summary.to_string(index=False))

    # --- Plot: P5 vs τ_p for each scheme ---
    plt.figure(figsize=(9, 5))
    scheme_colors = {
        "Upper bound": "#6a5acd",
        "Gao matching": "#0072bd",
        "Graph coloring (full bisection)": "#2ca02c",
        "Graph coloring (no bisection, θ=0.6)": "#7fbf7b",
        "Graph coloring (no bisection, θ=0.9)": "#c5e7b8",
        "Structured access (full bisection)": "#d6275f",
        "Structured access (no bisection, δ=0.3)": "#f08aa7",
        "Structured access (no bisection, δ=0.5)": "#fcc8d3",
        "Random": "#888888",
    }
    for scheme_name, group in summary.groupby("scheme"):
        group = group.sort_values("tau_p")
        plt.plot(
            group["tau_p"], group["p5_mbps"], marker="o",
            label=scheme_name, color=scheme_colors.get(scheme_name, "black"),
            linewidth=1.6,
        )
    plt.xlabel("Pilot number τ_p")
    plt.ylabel("95%-likely per-UE throughput [Mbit/s]")
    plt.title(
        f"Benchmark sensitivity (fractional power, "
        f"M={base_config.num_ues}, K={base_config.num_aps}, {args.realizations} MC)"
    )
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=7, loc="lower right")
    plt.tight_layout()
    plot_path = out_dir / f"benchmark_sensitivity{args.out_suffix}.png"
    plt.savefig(plot_path, dpi=200)
    print(f"Plot written to {plot_path}")


if __name__ == "__main__":
    main()
