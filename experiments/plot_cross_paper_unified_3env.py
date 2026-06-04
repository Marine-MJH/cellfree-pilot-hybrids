"""Plot E2/E3/E4 multi-antenna comparison after E4 unified run.

The three panels have different interpretation levels:
- E2: Mussbah paper environment, N=8
- E3: Gao-sized environment forced to N=8, stress test
- E4: common-ground unified environment, neither paper-original
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

PANELS = [
    (
        "E2 Mussbah original\nK=30, L=100, N=8",
        FIGS / "mussbah_fig1_full_summary_9schemes.csv",
    ),
    (
        "E3 Gao-sized N=8 stress\nK=200, L=500, N=8",
        FIGS / "cross_paper_full_gao_summary_final.csv",
    ),
    (
        "E4 common ground\nK=50, L=200, N=8",
        FIGS / "cross_paper_unified_E4_summary_E4.csv",
    ),
]


def load_summary(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Missing summary file: {path}")
    df = pd.read_csv(path).set_index("scheme").loc[SCHEME_ORDER].reset_index()
    random_p5 = float(df.loc[df["scheme"] == "Random", "p5_se"].iloc[0])
    random_mean = float(df.loc[df["scheme"] == "Random", "mean_se"].iloc[0])
    df["p5_vs_random_pct"] = 100.0 * (df["p5_se"] - random_p5) / random_p5
    df["mean_vs_random_pct"] = 100.0 * (df["mean_se"] - random_mean) / random_mean
    return df


def main() -> None:
    fig, axes = plt.subplots(2, 3, figsize=(17, 8.4), sharex=True)

    for col, (title, path) in enumerate(PANELS):
        df = load_summary(path)
        colors = [SCHEME_COLORS.get(s, "black") for s in df["scheme"]]
        x = np.arange(len(df))

        ax_top = axes[0, col]
        ax_top.bar(x, df["p5_se"], color=colors, edgecolor="black", linewidth=0.5)
        ax_top.set_title(title, fontsize=10)
        ax_top.set_ylabel("P5 SE")
        ax_top.grid(True, axis="y", alpha=0.3)
        ax_top.axhline(
            float(df.loc[df["scheme"] == "Random", "p5_se"].iloc[0]),
            color="gray",
            linestyle="--",
            linewidth=0.8,
        )

        ax_bottom = axes[1, col]
        vals = df["mean_vs_random_pct"].to_numpy()
        ax_bottom.bar(x, vals, color=colors, edgecolor="black", linewidth=0.5)
        ax_bottom.axhline(0.0, color="black", linewidth=0.7)
        ax_bottom.set_ylabel("Mean vs Random [%]")
        ax_bottom.grid(True, axis="y", alpha=0.3)
        ax_bottom.set_xticks(x)
        ax_bottom.set_xticklabels(df["scheme"], rotation=35, ha="right", fontsize=8)

        for idx, val in enumerate(vals):
            offset = 0.6 if val >= 0 else -1.2
            ax_bottom.text(idx, val + offset, f"{val:+.1f}", ha="center", fontsize=7)

    fig.suptitle(
        "Multi-antenna algorithm comparison: E2 paper env, E3 stress env, E4 unified common ground",
        fontsize=12,
    )
    fig.tight_layout()
    out = FIGS / "cross_paper_unified_3env.png"
    fig.savefig(out, dpi=200)
    print(f"3-env plot -> {out}")


if __name__ == "__main__":
    main()
