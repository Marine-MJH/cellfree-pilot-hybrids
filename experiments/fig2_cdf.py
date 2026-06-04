from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import pandas as pd

from _common import add_common_args, config_from_args, curve_style, default_schemes, ensure_figures_dir, ordered_scheme_names, selected_power_controls

from src.metrics import cdf
from src.simulator import Simulator


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce Gao Fig. 2 CDF.")
    add_common_args(parser)
    args = parser.parse_args()

    config = config_from_args(args, tau_p=20, num_ues=200)
    schemes = default_schemes(args.seed, args.gao_serving)
    simulator = Simulator(config, seed=args.seed)

    plt.figure(figsize=(7.0, 4.6))
    labeled_schemes = set()
    rows = []
    for power_control in selected_power_controls(args):
        values = simulator.collect_throughputs(
            schemes,
            power_control,
            n_realizations=args.realizations,
            show_progress=not args.no_progress,
        )
        for name in ordered_scheme_names(values.keys()):
            mbps = values[name] / 1e6
            x, y = cdf(mbps)
            rows.append(
                {
                    "scheme": name,
                    "power_control": power_control.name,
                    "p5_mbps": float(pd.Series(mbps).quantile(0.05)),
                    "p50_mbps": float(pd.Series(mbps).quantile(0.50)),
                    "p95_mbps": float(pd.Series(mbps).quantile(0.95)),
                    "mean_mbps": float(pd.Series(mbps).mean()),
                }
            )
            style = curve_style(name, power_control.name)
            legend_label = style.pop("legend_label")
            style["label"] = legend_label if name not in labeled_schemes else "_nolegend_"
            labeled_schemes.add(name)
            plt.plot(x, y, **style)
    plt.xlabel("Per-UE uplink throughput [Mbit/s]")
    plt.ylabel("CDF")
    if not args.auto_axes and not args.quick:
        plt.xlim(2, 20)
        plt.ylim(0, 1)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    suffix = ("_quick" if args.quick else "") + args.out_suffix
    out_path = ensure_figures_dir() / f"gao_fig2_cdf{suffix}.png"
    plt.savefig(out_path, dpi=200)
    pd.DataFrame(rows).to_csv(ensure_figures_dir() / f"gao_fig2_cdf_summary{suffix}.csv", index=False)
    print(out_path)


if __name__ == "__main__":
    main()
