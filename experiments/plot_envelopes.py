"""Defense-quality envelope figures.

Generates two figures from existing summary CSVs:

1. **τ_p envelope at K=30** — shows that Mussbah/Hybrid#3 advantage scales
   with τ_p_design while non-adaptive schemes plateau. Defends paper claim's
   enabling condition (τ_p_design > chromatic).

2. **K envelope at τ_p=10** — paper Fig.3 style. Shows Mussbah K-sensitivity
   (catastrophic at K=45) vs our hybrid robustness.

Both figures include all 9 schemes (Random, Gao, GC, Structured, Mussbah,
TopAP, H2, Hybrid#3, Hybrid#4).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIGS = PROJECT_ROOT / "figures"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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

HIGHLIGHT = {"Mussbah", "Hybrid#3 (TopAP N=8 adaptive)", "TopAP (bisect)", "H2 Gao+greedy"}


def line_style(name: str) -> dict:
    if name in HIGHLIGHT:
        return {"linewidth": 2.2, "marker": "o", "markersize": 5}
    return {"linewidth": 1.4, "marker": "s", "markersize": 3.5, "alpha": 0.7}


def plot_tau_envelope() -> None:
    """Plot SE vs τ_p_design at K=30."""
    suffixes = {
        10: "100x10_v3",
        15: "tau15_v2",
        20: "tau20_v2",
        30: "tau30_v2",
    }
    rows: list[dict] = []
    for tau_p, suffix in suffixes.items():
        path = FIGS / f"mussbah_fig3_k_sweep_summary_{suffix}.csv"
        if not path.exists():
            print(f"skip {tau_p}: {path} not found")
            continue
        df = pd.read_csv(path)
        sub = df[df["K"] == 30]
        for _, r in sub.iterrows():
            rows.append({
                "tau_p_design": tau_p,
                "scheme": r["scheme"],
                "p5_se": r["p5_se"],
                "mean_se": r["mean_se"],
            })
    df = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=False)
    for ax, metric, ylabel in [
        (axes[0], "mean_se", "Mean SE [bit/s/Hz/user]"),
        (axes[1], "p5_se", "P5 SE [bit/s/Hz/user]"),
    ]:
        for name in SCHEME_ORDER:
            sub = df[df["scheme"] == name].sort_values("tau_p_design")
            if sub.empty:
                continue
            style = line_style(name)
            ax.plot(sub["tau_p_design"], sub[metric], label=name,
                    color=SCHEME_COLORS.get(name, "black"), **style)
        ax.set_xlabel("τ_p_design")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    fig.suptitle("τ_p_design envelope at K=30 (paper-faithful UMi + adaptive τ_p Mussbah/Hybrid#3)",
                 fontsize=11)
    fig.tight_layout()
    out = FIGS / "envelope_tau_p_K30.png"
    fig.savefig(out, dpi=200)
    print(f"τ_p envelope → {out}")


def plot_k_envelope() -> None:
    """Plot SE vs K at τ_p_design=10 (paper Fig.3 style)."""
    path = FIGS / "mussbah_fig3_k_sweep_summary_100x10_v3.csv"
    if not path.exists():
        print(f"skip K envelope: {path} not found")
        return
    df = pd.read_csv(path)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=False)
    for ax, metric, ylabel in [
        (axes[0], "mean_se", "Mean SE [bit/s/Hz/user]"),
        (axes[1], "p5_se", "P5 SE [bit/s/Hz/user]"),
    ]:
        for name in SCHEME_ORDER:
            sub = df[df["scheme"] == name].sort_values("K")
            if sub.empty:
                continue
            style = line_style(name)
            ax.plot(sub["K"], sub[metric], label=name,
                    color=SCHEME_COLORS.get(name, "black"), **style)
        ax.set_xlabel("Number of UEs K")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    fig.suptitle("K envelope at τ_p_design=10 (paper-faithful UMi, paper Fig.3 style)",
                 fontsize=11)
    fig.tight_layout()
    out = FIGS / "envelope_K_tau10.png"
    fig.savefig(out, dpi=200)
    print(f"K envelope → {out}")


def plot_advantage_vs_random() -> None:
    """Plot advantage (%) vs Random for each scheme at each (K, tau_p) point."""
    path = FIGS / "mussbah_fig3_k_sweep_summary_100x10_v3.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    random_vals = df[df["scheme"] == "Random"].set_index("K")["mean_se"]
    df["mean_vs_random_pct"] = df.apply(
        lambda r: 100.0 * (r["mean_se"] - random_vals[r["K"]]) / random_vals[r["K"]], axis=1
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    for name in SCHEME_ORDER:
        if name == "Random":
            continue
        sub = df[df["scheme"] == name].sort_values("K")
        if sub.empty:
            continue
        style = line_style(name)
        ax.plot(sub["K"], sub["mean_vs_random_pct"], label=name,
                color=SCHEME_COLORS.get(name, "black"), **style)
    ax.axhline(0, color="black", linestyle="-", linewidth=0.5)
    ax.set_xlabel("Number of UEs K")
    ax.set_ylabel("Mean SE advantage vs Random [%]")
    ax.set_title("Algorithm advantage vs Random across K (τ_p_design=10)", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    out = FIGS / "envelope_advantage_vs_random.png"
    fig.savefig(out, dpi=200)
    print(f"Advantage vs Random → {out}")


if __name__ == "__main__":
    plot_tau_envelope()
    plot_k_envelope()
    plot_advantage_vs_random()
