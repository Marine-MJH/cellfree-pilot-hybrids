"""Replot high-K six-method results without Mussbah Beam Graph.

Mussbah can dominate the axis at high K because its adaptive pilot count exceeds
the coherence block. This script reads the existing high-K CSV outputs and
generates presentation-readable plots for the remaining five methods only.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "figures" / "presentation_high_k_6method"
OUT_DIR = PROJECT_ROOT / "figures" / "presentation_high_k_6method_no_mussbah"
SUMMARY = SRC_DIR / "high_k_6method_summary.csv"
ECDF_RAW = SRC_DIR / "high_k_6method_ecdf_raw.csv"

METHODS = [
    {
        "method_id": "random",
        "label": "Random",
        "color": "#6f6f6f",
        "linestyle": "-",
        "linewidth": 2.3,
    },
    {
        "method_id": "gao",
        "label": "Gao Matching",
        "color": "#1f78b4",
        "linestyle": ":",
        "linewidth": 2.0,
    },
    {
        "method_id": "topn",
        "label": "AP-Top-N (N=8)",
        "color": "#e7298a",
        "linestyle": "--",
        "linewidth": 2.4,
    },
    {
        "method_id": "beam_weighted",
        "label": "Beam-Weighted Threshold",
        "color": "#d95f02",
        "linestyle": "--",
        "linewidth": 2.4,
    },
    {
        "method_id": "beam_resource",
        "label": "Beam-Resource Matching",
        "color": "#7b3294",
        "linestyle": "--",
        "linewidth": 2.4,
    },
]


def plot_line(df: pd.DataFrame, metric: str, ylabel: str, title: str, out_file: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method in METHODS:
        sub = df[df["method_id"] == method["method_id"]].sort_values("K")
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
    ax.legend(fontsize=7.4, loc="best", framealpha=0.92, ncols=2)
    fig.tight_layout(pad=0.7)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def plot_ecdf(raw: pd.DataFrame, out_file: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    for method in METHODS:
        vals = np.sort(raw.loc[raw["method_id"] == method["method_id"], "throughput_mbps"].to_numpy(dtype=float))
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
    k_values = sorted(raw["K"].unique())
    k_text = str(k_values[0]) if len(k_values) == 1 else ",".join(str(k) for k in k_values)
    ax.set_xlabel("Per-UE throughput [Mbit/s]")
    ax.set_ylabel("eCDF")
    ax.set_title(f"eCDF of per-UE throughput, high-K K={k_text}")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.4, loc="best", framealpha=0.92)
    fig.tight_layout(pad=0.8)
    fig.savefig(out_file, dpi=240)
    plt.close(fig)


def write_readme(df: pd.DataFrame) -> None:
    source_readme = SRC_DIR / "README.md"
    inherited = source_readme.read_text() if source_readme.exists() else ""
    text = "\n".join(
        [
            "# High-K 5-Method Figures Without Mussbah",
            "",
            "Purpose: replot the existing high-K results after removing Mussbah Beam Graph, whose pilot count exceeds the coherence block at high K and compresses the y-axis.",
            "",
            "No simulation was rerun for this directory. These plots are generated from:",
            "",
            f"- {SUMMARY.relative_to(PROJECT_ROOT)}",
            f"- {ECDF_RAW.relative_to(PROJECT_ROOT)}",
            "",
            "Included methods:",
            "",
            "- Random",
            "- Gao Matching",
            "- AP-Top-N (N=8)",
            "- Beam-Weighted Threshold",
            "- Beam-Resource Matching",
            "",
            f"K-list = {' '.join(str(k) for k in sorted(df['K'].unique()))}",
            "",
            "Inherited source setting:",
            "",
            inherited.strip(),
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(text)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(SUMMARY)
    summary = summary[summary["method_id"] != "mussbah"].copy()
    raw = pd.read_csv(ECDF_RAW)
    raw = raw[raw["method_id"] != "mussbah"].copy()

    summary_path = OUT_DIR / "high_k_5method_summary.csv"
    raw_path = OUT_DIR / "high_k_5method_ecdf_raw.csv"
    summary.to_csv(summary_path, index=False)
    raw.to_csv(raw_path, index=False)

    plot_line(
        summary,
        "avgSE",
        "Average SE [bit/s/Hz/user]",
        "High-K average SE without Mussbah",
        OUT_DIR / "high_k_5method_avg_se_vs_k.png",
    )
    plot_line(
        summary,
        "avgEE",
        "Average EE [bit/s/Hz/W]",
        "High-K EE without Mussbah",
        OUT_DIR / "high_k_5method_avg_ee_vs_k.png",
    )
    plot_line(
        summary,
        "avgTauP",
        r"Average actual pilot count $\tau_p$",
        "High-K pilot count without Mussbah",
        OUT_DIR / "high_k_5method_pilot_count_vs_k.png",
    )
    plot_line(
        summary,
        "p5ThroughputMbps",
        "95%-likely per-UE throughput [Mbit/s]",
        "High-K 95%-likely throughput without Mussbah",
        OUT_DIR / "high_k_5method_p5_throughput_vs_k.png",
    )
    if not raw.empty:
        plot_ecdf(raw, OUT_DIR / "high_k_5method_ecdf_throughput.png")
    write_readme(summary)

    for path in [
        OUT_DIR / "README.md",
        summary_path,
        raw_path,
        OUT_DIR / "high_k_5method_avg_se_vs_k.png",
        OUT_DIR / "high_k_5method_avg_ee_vs_k.png",
        OUT_DIR / "high_k_5method_pilot_count_vs_k.png",
        OUT_DIR / "high_k_5method_p5_throughput_vs_k.png",
        OUT_DIR / "high_k_5method_ecdf_throughput.png",
    ]:
        print(path)


if __name__ == "__main__":
    main()
