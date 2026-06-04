"""Bootstrap 95% CI for per-UE SE results (defense-quality statistics).

Reads any raw SE CSV with columns (scheme, se_bps_per_hz) optionally with
(K, tau_p) grouping. Computes percentile bootstrap CI (B=1000) on P5, median,
mean SE per scheme group. Used to defend statistical significance of
algorithm advantages in cross-paper figures.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def bootstrap_stat(values: np.ndarray, n_boot: int, rng: np.random.Generator,
                   stat_fn) -> tuple[float, float, float]:
    """Return (estimate, ci_low, ci_high) for percentile bootstrap of stat_fn."""
    n = values.size
    boot = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(values, size=n, replace=True)
        boot[b] = stat_fn(sample)
    est = float(stat_fn(values))
    ci_low, ci_high = np.percentile(boot, [2.5, 97.5])
    return est, float(ci_low), float(ci_high)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True,
                        help="Raw CSV path (must have 'scheme' + 'se_bps_per_hz' columns)")
    parser.add_argument("--group-by", type=str, default=None,
                        help="Optional extra grouping column (e.g. 'K', 'tau_p')")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    raw_path = Path(args.input)
    if not raw_path.is_absolute():
        raw_path = PROJECT_ROOT / "figures" / raw_path.name
    if not raw_path.exists():
        raise SystemExit(f"Not found: {raw_path}")

    df = pd.read_csv(raw_path)
    # Determine value column: 'se_bps_per_hz' for SE, 'throughput_mbps' for throughput
    if "se_bps_per_hz" in df.columns:
        value_col = "se_bps_per_hz"
        metric_label = "se"
    elif "throughput_mbps" in df.columns:
        value_col = "throughput_mbps"
        metric_label = "tp_mbps"
    else:
        raise SystemExit(f"No 'se_bps_per_hz' or 'throughput_mbps' column in {raw_path}")

    rng = np.random.default_rng(args.seed)
    group_cols = ["scheme"]
    if args.group_by:
        group_cols = [args.group_by, "scheme"]

    rows: list[dict] = []
    for keys, sub in df.groupby(group_cols):
        if isinstance(keys, tuple):
            row = dict(zip(group_cols, keys))
        else:
            row = {group_cols[0]: keys}
        vals = sub[value_col].to_numpy()
        p5, p5_lo, p5_hi = bootstrap_stat(vals, args.bootstrap, rng, lambda x: np.percentile(x, 5))
        med, med_lo, med_hi = bootstrap_stat(vals, args.bootstrap, rng, np.median)
        mean, mean_lo, mean_hi = bootstrap_stat(vals, args.bootstrap, rng, np.mean)
        row.update({
            f"p5_{metric_label}": p5,
            f"p5_{metric_label}_ci_low": p5_lo,
            f"p5_{metric_label}_ci_high": p5_hi,
            f"median_{metric_label}": med,
            f"median_{metric_label}_ci_low": med_lo,
            f"median_{metric_label}_ci_high": med_hi,
            f"mean_{metric_label}": mean,
            f"mean_{metric_label}_ci_low": mean_lo,
            f"mean_{metric_label}_ci_high": mean_hi,
            "n_samples": int(vals.size),
        })
        rows.append(row)

    out_df = pd.DataFrame(rows).sort_values(group_cols).reset_index(drop=True)
    out_name = args.out
    if out_name is None:
        out_name = f"bootstrap_ci_{raw_path.stem}.csv"
    out_path = PROJECT_ROOT / "figures" / Path(out_name).name
    out_df.to_csv(out_path, index=False)
    print(f"Bootstrap CI written to {out_path}")
    print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
