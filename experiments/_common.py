from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import SimulationConfig
from src.pilot_schemes import (  # noqa: E402
    GraphColoringPilotAssignment,
    MatchingBasedPilotAssignment,
    RandomPilotAssignment,
    StructuredPilotAccessAssignment,
    UpperBoundPilotAssignment,
)
from src.power_control import (  # noqa: E402
    FractionalPowerControl,
    FullPowerControl,
    MaxMinPowerControl,
)


SCHEME_ORDER = [
    "Upper bound",
    "Gao matching",
    "Gao matching (matched serving)",
    "Structured access",
    "Graph coloring",
    "Random",
]

SCHEME_STYLES = {
    "Upper bound": {"color": "#6a5acd", "label": "Upper bound limit"},
    "Gao matching": {"color": "#0072bd", "label": "Proposed scheme"},
    "Gao matching (matched serving)": {"color": "#0072bd", "label": "Proposed scheme (matched serving)"},
    "Structured access": {"color": "#d6275f", "label": "Benchmark scheme I [15]"},
    "Graph coloring": {"color": "#2ca02c", "label": "Benchmark scheme II [14]"},
    "Random": {"color": "#c43c60", "label": "Random scheme"},
}

POWER_LINESTYLES = {
    "Fractional power": "-",
    "Full power": "-",
    "Max-min power": ":",
}


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--realizations", type=int, default=20)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--quick", action="store_true", help="Use a small topology for smoke tests.")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument(
        "--power-controls",
        nargs="+",
        choices=["fractional", "full", "max-min"],
        default=["fractional", "max-min"],
        help=(
            "Power-control curves to plot. Paper figures use solid fractional and dotted "
            "max-min. 'full' = uniform p_max (논문 IV.B 본문의 'full uplink transmission "
            "power' 결과)."
        ),
    )
    parser.add_argument("--fractional-alpha", type=float, default=0.5)
    parser.add_argument("--max-min-iterations", type=int, default=35)
    parser.add_argument(
        "--gao-serving",
        choices=["all-ap", "matched"],
        default="all-ap",
        help=(
            "Serving mask for Gao matching throughput evaluation. 'all-ap' is the "
            "current main convention; 'matched' uses Algorithm 1 matching groups as xi_m."
        ),
    )
    parser.add_argument("--auto-axes", action="store_true", help="Do not force paper axis limits.")
    parser.add_argument(
        "--out-suffix",
        type=str,
        default="",
        help="Append to output filenames (e.g. '_full', '_maxmin') to keep multiple runs separate.",
    )


def config_from_args(args: argparse.Namespace, *, tau_p: int = 20, num_ues: int = 200) -> SimulationConfig:
    if args.quick:
        return SimulationConfig(num_aps=60, num_ues=min(num_ues, 40), tau_p=min(tau_p, 8), random_seed=args.seed)
    return SimulationConfig(num_aps=500, num_ues=num_ues, tau_p=tau_p, random_seed=args.seed)


def default_schemes(seed: int, gao_serving: str = "all-ap"):
    serving_policy = "all_ap" if gao_serving == "all-ap" else "matched"
    return [
        UpperBoundPilotAssignment(seed=seed + 1),
        MatchingBasedPilotAssignment(seed=seed + 2, serving_policy=serving_policy),
        StructuredPilotAccessAssignment(seed=seed + 3),
        GraphColoringPilotAssignment(seed=seed + 4),
        RandomPilotAssignment(seed=seed + 5),
    ]


def selected_power_controls(args: argparse.Namespace):
    controls = []
    for name in args.power_controls:
        if name == "fractional":
            controls.append(FractionalPowerControl(alpha=args.fractional_alpha))
        elif name == "full":
            controls.append(FullPowerControl())
        elif name == "max-min":
            controls.append(MaxMinPowerControl(max_iterations=args.max_min_iterations))
        else:
            raise ValueError(f"Unknown power control: {name}")
    return controls


def ordered_scheme_names(names):
    return [name for name in SCHEME_ORDER if name in names]


def curve_style(scheme_name: str, power_name: str) -> dict[str, object]:
    style = SCHEME_STYLES.get(scheme_name, {"label": scheme_name}).copy()
    style["legend_label"] = style.pop("label", scheme_name)
    style["linestyle"] = POWER_LINESTYLES.get(power_name, "-")
    style["linewidth"] = 1.8
    return style


def ensure_figures_dir() -> Path:
    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)
    return out_dir
