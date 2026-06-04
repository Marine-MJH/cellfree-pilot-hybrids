from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import pandas as pd

from _common import add_common_args, config_from_args, curve_style, default_schemes, ensure_figures_dir, ordered_scheme_names, selected_power_controls

from src.simulator import Simulator


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce Gao Fig. 4 vs UE number.")
    add_common_args(parser)
    parser.add_argument("--ue-values", type=int, nargs="+", default=[100, 125, 150, 175, 200])
    parser.add_argument("--tau-p", type=int, default=20)
    args = parser.parse_args()

    config = config_from_args(args, tau_p=args.tau_p, num_ues=max(args.ue_values))
    ue_values = [20, 30, 40] if args.quick else args.ue_values

    schemes = default_schemes(args.seed, args.gao_serving)
    simulator = Simulator(config, seed=args.seed)
    frames = []
    for power_control in selected_power_controls(args):
        frames.append(
            simulator.sweep_95_likely(
                schemes,
                power_control,
                n_realizations=args.realizations,
                ue_values=ue_values,
                show_progress=not args.no_progress,
            )
        )
    frame = pd.concat(frames, ignore_index=True)

    plt.figure(figsize=(7.0, 4.6))
    labeled_schemes = set()
    for power_name, power_group in frame.groupby("power_control", sort=False):
        for scheme in ordered_scheme_names(power_group["scheme"].unique()):
            group = power_group[power_group["scheme"] == scheme].sort_values("num_ues")
            style = curve_style(scheme, power_name)
            legend_label = style.pop("legend_label")
            style["label"] = legend_label if scheme not in labeled_schemes else "_nolegend_"
            labeled_schemes.add(scheme)
            plt.plot(group["num_ues"], group["throughput_95_likely_bps"] / 1e6, marker="o", **style)
    plt.xlabel("UE number M")
    plt.ylabel("95%-likely per-UE throughput [Mbit/s]")
    if not args.auto_axes and not args.quick:
        plt.xlim(100, 200)
        plt.ylim(0, 11)
        plt.xticks([100, 120, 140, 160, 180, 200])
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    suffix = ("_quick" if args.quick else "") + args.out_suffix
    out_path = ensure_figures_dir() / f"gao_fig4_vs_ue_number{suffix}.png"
    plt.savefig(out_path, dpi=200)
    frame.to_csv(ensure_figures_dir() / f"gao_fig4_vs_ue_number{suffix}.csv", index=False)
    print(out_path)


if __name__ == "__main__":
    main()
