"""Build presentation-ready figures with reduced references and stable labels.

This script does not rerun simulations. It reads same-environment presentation
artifacts and replots the main deck figures with slide-ready method names.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = PROJECT_ROOT / "figures"
OUT_DIR = FIG_DIR / "presentation_6method"

MAIN_SETUP = FIG_DIR / "presentation_main_setup_main_beam20_wt10.csv"
K_SWEEP = FIG_DIR / "presentation_k_sweep_common_50x10_summary.csv"
LOAD_CROSSOVER = FIG_DIR / "presentation_load_crossover_6method_50x10_summary.csv"
MJH_WITH_GAO = (
    PROJECT_ROOT
    / "MJH"
    / "result_200_boxplot_ap_domain_env_fixed_with_gao_parallel8"
    / "sweep_K_all_schemes.csv"
)
MJH_MUSSBAH_EDGE0 = (
    PROJECT_ROOT
    / "MJH"
    / "result_200_boxplot_ap_domain_env_fixed_mussbah_edge0_parallel8"
    / "sweep_K_all_schemes.csv"
)
PRESENTATION_SIX_CSV = OUT_DIR / "presentation_mjh_6method_k_sweep.csv"


METHODS = [
    {
        "scheme": "Random",
        "label": "Random",
        "role": "Reference",
        "color": "#8a8a8a",
        "linestyle": "-",
    },
    {
        "scheme": "Gao matching",
        "label": "Gao Matching",
        "role": "Reference",
        "color": "#1f78b4",
        "linestyle": ":",
    },
    {
        "scheme": "Mussbah",
        "label": "Mussbah Beam Graph",
        "role": "Reference",
        "color": "#009e73",
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
        "color": "#7b3294",
        "linestyle": "--",
    },
]

K_SWEEP_METHODS = [
    {
        "scheme": "Random",
        "label": "Random",
        "role": "Reference",
        "color": "#8a8a8a",
        "linestyle": "-",
    },
    {
        "scheme": "Gao matching",
        "label": "Gao Matching",
        "role": "Reference",
        "color": "#1f78b4",
        "linestyle": ":",
    },
    {
        "scheme": "Mussbah",
        "label": "Mussbah Beam Graph",
        "role": "Reference",
        "color": "#009e73",
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
        "color": "#7b3294",
        "linestyle": "--",
    },
]

PRESENTATION_SIX_METHODS = [
    {
        "source": "base",
        "scheme": "Random",
        "method_id": "random",
        "label": "Random",
        "color": "#6f6f6f",
        "linestyle": "-",
        "linewidth": 2.4,
    },
    {
        "source": "base",
        "scheme": "GaoMatching",
        "method_id": "gao",
        "label": "Gao Matching",
        "color": "#1f78b4",
        "linestyle": ":",
        "linewidth": 2.0,
    },
    {
        "source": "mussbah",
        "scheme": "Proposed",
        "method_id": "mussbah",
        "label": "Mussbah Beam Graph",
        "color": "#009e73",
        "linestyle": "-.",
        "linewidth": 2.2,
    },
    {
        "source": "base",
        "scheme": "H3TopAPAdaptive",
        "method_id": "topn",
        "label": "AP-Top-N (N=8)",
        "color": "#e7298a",
        "linestyle": "--",
        "linewidth": 2.4,
    },
    {
        "source": "base",
        "scheme": "Proposed",
        "method_id": "beam_weighted",
        "label": "Beam-Weighted Threshold",
        "color": "#d95f02",
        "linestyle": "--",
        "linewidth": 2.4,
    },
    {
        "source": "base",
        "scheme": "MatchingBeamAdaptive",
        "method_id": "beam_resource",
        "label": "Beam-Resource Matching",
        "color": "#7b3294",
        "linestyle": "--",
        "linewidth": 2.4,
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
    fig.savefig(OUT_DIR / "presentation_clean_pilot_box.png", dpi=220)
    plt.close(fig)

def plot_k_sweep(k_sweep: pd.DataFrame, metric: str, ylabel: str, title: str, out_name: str) -> None:
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method in K_SWEEP_METHODS:
        scheme = method["scheme"]
        sub = k_sweep[k_sweep["scheme"] == scheme].sort_values("K")
        if sub.empty:
            continue
        linewidth = 3.2 if scheme == "Random" else 1.8 if scheme == "Gao matching" else 2.5
        markersize = 5.8 if scheme not in {"Random", "Gao matching"} else 5.0
        alpha = 0.92 if scheme != "Gao matching" else 0.85
        ax.plot(
            sub["K"],
            sub[metric],
            marker="o",
            markersize=markersize,
            linewidth=linewidth,
            color=method["color"],
            linestyle=method["linestyle"],
            alpha=alpha,
            label=method["label"],
        )
    ax.set_xlabel("Number of users K")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, pad=6)
    ax.set_xticks(sorted(k_sweep["K"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.5, loc="best", framealpha=0.92)
    fig.tight_layout(pad=0.7)
    fig.savefig(OUT_DIR / out_name, dpi=220)
    plt.close(fig)


def build_presentation_six_method_sweep() -> pd.DataFrame:
    base = pd.read_csv(MJH_WITH_GAO)
    mussbah = pd.read_csv(MJH_MUSSBAH_EDGE0)
    frames = []

    for method in PRESENTATION_SIX_METHODS:
        source = base if method["source"] == "base" else mussbah
        sub = source[source["scheme"] == method["scheme"]].copy()
        if sub.empty:
            raise ValueError(f"Missing scheme {method['scheme']} in {method['source']} source")
        sub.insert(1, "method_id", method["method_id"])
        sub.insert(2, "label", method["label"])
        frames.append(sub)

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(PRESENTATION_SIX_CSV, index=False)
    return combined


def plot_presentation_six_sweep(
    sweep: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    out_name: str,
) -> None:
    fig, ax = plt.subplots(figsize=(9.8, 4.0))
    for method in PRESENTATION_SIX_METHODS:
        sub = sweep[sweep["method_id"] == method["method_id"]].sort_values("K")
        if sub.empty:
            continue
        ax.plot(
            sub["K"],
            sub[metric],
            marker="o",
            markersize=5.3,
            linewidth=method["linewidth"],
            color=method["color"],
            linestyle=method["linestyle"],
            alpha=0.94,
            label=method["label"],
        )
    ax.set_xlabel("Number of users K")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, pad=6)
    ax.set_xticks(sorted(sweep["K"].unique()))
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.2, loc="best", framealpha=0.92, ncols=2)
    fig.tight_layout(pad=0.7)
    fig.savefig(OUT_DIR / out_name, dpi=240)
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for path in [K_SWEEP, LOAD_CROSSOVER, MJH_WITH_GAO, MJH_MUSSBAH_EDGE0]:
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run the corresponding presentation experiment script first."
            )

    k_sweep = pd.read_csv(K_SWEEP)
    load_crossover = pd.read_csv(LOAD_CROSSOVER)

    plot_k_sweep(
        k_sweep,
        metric="mean_se",
        ylabel="Average SE [bit/s/Hz/user]",
        title="Same-environment SE under increasing user load",
        out_name="presentation_clean_k_sweep_se.png",
    )
    plot_k_sweep(
        k_sweep,
        metric="mean_ee",
        ylabel="Average EE [bit/s/Hz/W]",
        title="Same-environment EE under increasing user load",
        out_name="presentation_clean_k_sweep_ee.png",
    )
    plot_k_sweep(
        load_crossover,
        metric="mean_se",
        ylabel="Average SE [bit/s/Hz/user]",
        title="Average SE under increasing user load",
        out_name="presentation_clean_load_crossover_se.png",
    )

    presentation_six = build_presentation_six_method_sweep()
    plot_presentation_six_sweep(
        presentation_six,
        metric="avgSE",
        ylabel="Average SE [bit/s/Hz/user]",
        title="Average SE under increasing user load",
        out_name="presentation_clean_load_crossover_se.png",
    )
    plot_presentation_six_sweep(
        presentation_six,
        metric="avgEE",
        ylabel="Average EE [bit/s/Hz/W]",
        title="Energy efficiency under increasing user load",
        out_name="presentation_clean_load_crossover_ee.png",
    )
    plot_presentation_six_sweep(
        presentation_six,
        metric="avgTauP",
        ylabel=r"Average actual pilot count $\tau_p$",
        title="Average pilot count under increasing user load",
        out_name="presentation_clean_pilot_count_vs_k.png",
    )

    for name in [
        "presentation_clean_pilot_count_vs_k.png",
        "presentation_clean_k_sweep_se.png",
        "presentation_clean_k_sweep_ee.png",
        "presentation_clean_load_crossover_se.png",
        "presentation_clean_load_crossover_ee.png",
        "presentation_mjh_6method_k_sweep.csv",
    ]:
        print(OUT_DIR / name)


if __name__ == "__main__":
    main()
