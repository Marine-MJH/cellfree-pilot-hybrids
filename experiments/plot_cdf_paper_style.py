"""Plot CDF in paper Fig.1 style (zoomed low-SE region with annotated P5).

Used to verify whether our paper-faithful Mussbah reproduce produces the
right-shifted Mussbah CDF that paper Fig.1 shows. Default reads
``mussbah_fig1_full_raw_{suffix}.csv``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
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

SCHEME_STYLES = {
    "Random": {"linestyle": "-", "linewidth": 1.8, "alpha": 0.6},
    "Mussbah": {"linestyle": "-", "linewidth": 2.4, "alpha": 1.0},
    "Hybrid#3 (TopAP N=8 adaptive)": {"linestyle": "-", "linewidth": 2.4, "alpha": 1.0},
    "TopAP (bisect)": {"linestyle": "--", "linewidth": 1.8, "alpha": 0.8},
    "H2 Gao+greedy": {"linestyle": "--", "linewidth": 1.8, "alpha": 0.8},
    "Hybrid#4 (TopAP+greedy)": {"linestyle": ":", "linewidth": 1.6, "alpha": 0.7},
}
DEFAULT_STYLE = {"linestyle": "-", "linewidth": 1.4, "alpha": 0.5}


def style_for(name: str) -> dict:
    return SCHEME_STYLES.get(name, DEFAULT_STYLE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix", type=str, required=True,
                        help="raw CSV suffix (e.g. _tau20)")
    parser.add_argument("--xlim", type=float, nargs=2, default=[0.0, 8.0])
    parser.add_argument("--title", type=str, default=None)
    parser.add_argument("--out-suffix", type=str, default="_paperstyle")
    args = parser.parse_args()

    figs = PROJECT_ROOT / "figures"
    raw_path = figs / f"mussbah_fig1_full_raw{args.suffix}.csv"
    if not raw_path.exists():
        raise SystemExit(f"Raw CSV not found: {raw_path}")

    df = pd.read_csv(raw_path)
    schemes_in_data = [s for s in SCHEME_ORDER if s in df["scheme"].unique()]

    fig, (ax_main, ax_zoom) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    for name in schemes_in_data:
        sub = df[df["scheme"] == name]["se_bps_per_hz"].sort_values().to_numpy()
        cdf = np.arange(1, len(sub) + 1) / len(sub)
        style = style_for(name)
        ax_main.plot(sub, cdf, label=name, color=SCHEME_COLORS.get(name, "black"), **style)
        ax_zoom.plot(sub, cdf, label=name, color=SCHEME_COLORS.get(name, "black"), **style)

    # Main: full range
    ax_main.set_xlabel("Per-UE SE [bit/s/Hz/user]")
    ax_main.set_ylabel("eCDF")
    ax_main.grid(True, alpha=0.3)
    ax_main.legend(fontsize=7, loc="lower right")
    ax_main.set_title("Full range", fontsize=10)

    # Zoom: bottom-30% region (around P5 area, paper-style)
    ax_zoom.set_xlim(*args.xlim)
    ax_zoom.set_ylim(0.0, 0.30)
    ax_zoom.set_xlabel("Per-UE SE [bit/s/Hz/user]")
    ax_zoom.set_ylabel("eCDF")
    ax_zoom.grid(True, alpha=0.3)
    ax_zoom.legend(fontsize=7, loc="lower right")
    ax_zoom.set_title("Bottom 30% (P5 / P10 region — paper Fig.1 style)", fontsize=10)
    # Annotate P5 horizontal line
    ax_zoom.axhline(0.05, color="gray", linestyle=":", linewidth=0.8)
    ax_zoom.text(args.xlim[1] * 0.95, 0.055, "5%", fontsize=8, color="gray", ha="right")

    if args.title:
        fig.suptitle(args.title, fontsize=11)
    fig.tight_layout()
    out_path = figs / f"mussbah_cdf{args.out_suffix}.png"
    fig.savefig(out_path, dpi=200)
    print(f"Plot → {out_path}")


if __name__ == "__main__":
    main()
