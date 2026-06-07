"""Build presentation-ready figures with reduced references and stable labels.

This script does not rerun simulations. It reads common-ground presentation
artifacts and replots the main deck figures with slide-ready method names.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = PROJECT_ROOT / "figures"

MAIN_SETUP = FIG_DIR / "presentation_main_setup_main_beam20_wt10.csv"
K_SWEEP = FIG_DIR / "presentation_k_sweep_common_50x10_summary.csv"


METHODS = [
    {
        "scheme": "Random",
        "label": "Random",
        "role": "Reference",
        "color": "#707070",
        "linestyle": "-",
    },
    {
        "scheme": "Gao matching",
        "label": "Gao Matching",
        "role": "Reference",
        "color": "#1f78b4",
        "linestyle": "-",
    },
    {
        "scheme": "Mussbah",
        "label": "Mussbah Beam Graph",
        "role": "Reference",
        "color": "#ff7f00",
        "linestyle": "-",
    },
    {
        "scheme": "Hybrid#3 (TopAP N=8 adaptive)",
        "label": "AP-Top-N (N=8)",
        "role": "Proposed",
        "color": "#e7298a",
        "linestyle": "--",
    },
    {
        "scheme": "MJH weighted-count strict",
        "label": "Beam-Weighted Threshold",
        "role": "Proposed",
        "color": "#d95f02",
        "linestyle": "--",
    },
    {
        "scheme": "MJH beam-resource matching",
        "label": "Beam-Resource Matching",
        "role": "Proposed",
        "color": "#5e3c99",
        "linestyle": "--",
    },
]

K_SWEEP_METHODS = [
    {
        "scheme": "Random",
        "label": "Random",
        "role": "Reference",
        "color": "#707070",
        "linestyle": "-",
    },
    {
        "scheme": "Gao matching",
        "label": "Gao Matching",
        "role": "Reference",
        "color": "#1f78b4",
        "linestyle": "-",
    },
    {
        "scheme": "Mussbah",
        "label": "Mussbah Beam Graph",
        "role": "Reference",
        "color": "#ff7f00",
        "linestyle": "-",
    },
    {
        "scheme": "Hybrid#3 (TopAP N=8 adaptive)",
        "label": "AP-Top-N (N=8)",
        "role": "Proposed",
        "color": "#e7298a",
        "linestyle": "--",
    },
    {
        "scheme": "MJH weighted-count strict",
        "label": "Beam-Weighted Threshold",
        "role": "Proposed",
        "color": "#d95f02",
        "linestyle": "--",
    },
    {
        "scheme": "MJH beam-resource matching",
        "label": "Beam-Resource Matching",
        "role": "Proposed",
        "color": "#5e3c99",
        "linestyle": "--",
    },
]


def method_labels() -> dict[str, str]:
    return {m["scheme"]: m["label"] for m in METHODS}


def method_colors() -> dict[str, str]:
    return {m["scheme"]: m["color"] for m in METHODS}


def add_group_divider(ax, x: float = 2.5) -> None:
    ax.axvline(x, color="#bbbbbb", linewidth=0.9, linestyle=":")


def plot_pilot_box(setup: pd.DataFrame) -> None:
    labels = method_labels()
    colors = method_colors()
    data = []
    names = []
    for method in METHODS:
        vals = setup[setup["scheme"] == method["scheme"]]["tau_p_actual"].to_numpy(dtype=float)
        data.append(vals)
        names.append(method["scheme"])

    fig, ax = plt.subplots(figsize=(8.6, 4.9))
    bp = ax.boxplot(
        data,
        tick_labels=[labels[n] for n in names],
        showmeans=True,
        patch_artist=True,
        meanprops=dict(marker="D", markerfacecolor="white", markeredgecolor="black", markersize=5),
    )
    for patch, name in zip(bp["boxes"], names):
        patch.set_facecolor(colors[name])
        patch.set_alpha(0.62)
    for i, vals in enumerate(data, start=1):
        mean = float(np.mean(vals)) if len(vals) else 0.0
        ax.text(i + 0.08, mean, f"{mean:.1f}", va="center", ha="left", fontsize=8)
    ax.axhline(15, color="#444444", linestyle="--", linewidth=0.9, label=r"design $\tau_p=15$")
    ax.set_ylabel(r"Actual pilot count $\tau_p^{actual}$")
    ax.set_title("Actual pilot count by method")
    ax.tick_params(axis="x", labelrotation=18)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    add_group_divider(ax)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "presentation_clean_pilot_box.png", dpi=220)
    plt.close(fig)

def plot_k_sweep(k_sweep: pd.DataFrame, metric: str, ylabel: str, title: str, out_name: str) -> None:
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method in K_SWEEP_METHODS:
        scheme = method["scheme"]
        sub = k_sweep[k_sweep["scheme"] == scheme].sort_values("K")
        if sub.empty:
            continue
        ax.plot(
            sub["K"],
            sub[metric],
            marker="o",
            markersize=5.5,
            linewidth=2.4 if method["role"] == "Proposed" else 2.0,
            color=method["color"],
            linestyle=method["linestyle"],
            label=method["label"],
        )
    ax.set_xlabel("Number of users K")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, pad=6)
    ax.set_xticks(sorted(k_sweep["K"].unique()))
    ax.axvspan(39.5, max(k_sweep["K"]) + 0.5, color="#f2f2f2", zorder=0)
    ylim = ax.get_ylim()
    ax.text(
        40.0,
        ylim[0] + 0.08 * (ylim[1] - ylim[0]),
        "higher-load region",
        fontsize=8,
        color="#555555",
        ha="left",
        va="bottom",
    )
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.5, loc="best")
    fig.tight_layout(pad=0.7)
    fig.savefig(FIG_DIR / out_name, dpi=220)
    plt.close(fig)


def main() -> None:
    for path in [MAIN_SETUP, K_SWEEP]:
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run experiments/run_presentation_k_sweep_common_50x10.sh first."
            )

    setup = pd.read_csv(MAIN_SETUP)
    k_sweep = pd.read_csv(K_SWEEP)

    plot_pilot_box(setup)
    plot_k_sweep(
        k_sweep,
        metric="mean_se",
        ylabel="Average SE [bit/s/Hz/user]",
        title="Common-ground SE under increasing user load",
        out_name="presentation_clean_k_sweep_se.png",
    )
    plot_k_sweep(
        k_sweep,
        metric="mean_ee",
        ylabel="Average EE [bit/s/Hz/W]",
        title="Common-ground EE under increasing user load",
        out_name="presentation_clean_k_sweep_ee.png",
    )

    for name in [
        "presentation_clean_pilot_box.png",
        "presentation_clean_k_sweep_se.png",
        "presentation_clean_k_sweep_ee.png",
    ]:
        print(FIG_DIR / name)


if __name__ == "__main__":
    main()
