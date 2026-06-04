"""Plot actual pilot count distribution for E4 unified benchmark.

The E4 result hinges on adaptive pilot counts:
- Mussbah uses many more pilots than the design budget in E4.
- Hybrid#3 uses fewer pilots via a sparser TopAP conflict graph.

This script turns ``cross_paper_unified_E4_raw_E4.csv`` into:
- figures/cross_paper_unified_E4_tau_p_actual_summary.csv
- figures/cross_paper_unified_E4_tau_p_actual.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIGS = PROJECT_ROOT / "figures"

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


def main() -> None:
    raw_path = FIGS / "cross_paper_unified_E4_raw_E4.csv"
    if not raw_path.exists():
        raise SystemExit(f"Missing E4 raw CSV: {raw_path}")

    raw = pd.read_csv(raw_path)
    per_setup = (
        raw[["setup", "scheme", "tau_p_design", "tau_p_actual"]]
        .drop_duplicates()
        .set_index("scheme")
        .loc[SCHEME_ORDER]
        .reset_index()
    )

    summary = (
        per_setup.groupby("scheme")
        .agg(
            tau_p_design=("tau_p_design", "first"),
            mean_tau_p_actual=("tau_p_actual", "mean"),
            median_tau_p_actual=("tau_p_actual", "median"),
            p5_tau_p_actual=("tau_p_actual", lambda x: float(np.percentile(x, 5))),
            p95_tau_p_actual=("tau_p_actual", lambda x: float(np.percentile(x, 95))),
            min_tau_p_actual=("tau_p_actual", "min"),
            max_tau_p_actual=("tau_p_actual", "max"),
            n_setups=("setup", "nunique"),
        )
        .reset_index()
        .set_index("scheme")
        .loc[SCHEME_ORDER]
        .reset_index()
    )

    out_csv = FIGS / "cross_paper_unified_E4_tau_p_actual_summary.csv"
    summary.to_csv(out_csv, index=False)

    fig, ax = plt.subplots(figsize=(11.5, 5.7))
    data = [
        per_setup[per_setup["scheme"] == scheme]["tau_p_actual"].to_numpy()
        for scheme in SCHEME_ORDER
    ]
    positions = np.arange(1, len(SCHEME_ORDER) + 1)
    box = ax.boxplot(
        data,
        positions=positions,
        patch_artist=True,
        widths=0.62,
        showfliers=False,
        medianprops={"color": "black", "linewidth": 1.2},
    )
    for patch, scheme in zip(box["boxes"], SCHEME_ORDER):
        patch.set_facecolor(SCHEME_COLORS.get(scheme, "white"))
        patch.set_alpha(0.85)
        patch.set_edgecolor("black")
        patch.set_linewidth(0.7)

    means = [float(np.mean(vals)) for vals in data]
    ax.scatter(positions, means, color="white", edgecolor="black", zorder=3, s=36, label="Mean")
    for x, mean_val in zip(positions, means):
        ax.text(x, mean_val + 0.7, f"{mean_val:.1f}", ha="center", va="bottom", fontsize=8)

    design_tau = int(per_setup["tau_p_design"].mode().iloc[0])
    ax.axhline(design_tau, color="#444444", linestyle="--", linewidth=1.0, label=f"tau_p_design={design_tau}")
    ax.set_xticks(positions)
    ax.set_xticklabels(SCHEME_ORDER, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("Actual pilot count")
    ax.set_title("E4 unified benchmark: actual pilot count by scheme")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()

    out_png = FIGS / "cross_paper_unified_E4_tau_p_actual.png"
    fig.savefig(out_png, dpi=200)

    print(f"tau_p actual summary -> {out_csv}")
    print(f"tau_p actual plot -> {out_png}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
