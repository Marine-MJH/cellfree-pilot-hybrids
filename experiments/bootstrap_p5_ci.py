"""Bootstrap 95% CI for the P5 throughput metric.

Reads the raw per-UE throughput CSV emitted by ``benchmark_sensitivity.py``
(``benchmark_sensitivity_raw{suffix}.csv``) and computes a percentile
bootstrap confidence interval for the 95%-likely (P5) throughput of each
(tau_p, scheme) pair.

Why this matters
----------------
The P5 metric is a sample percentile and therefore noisier than the mean.
A point estimate from 100 MC realizations is informative but not
definitive — a 95% CI quantifies how much of the observed Gao-vs-benchmark
gap could be MC variability vs. a real effect.

Usage::

    python experiments/bootstrap_p5_ci.py --suffix _100mc --bootstrap 1000

Output: ``figures/bootstrap_p5_ci{suffix}.csv`` with columns
``tau_p, scheme, p5_mbps, p5_ci_low, p5_ci_high, p5_se``.
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


def bootstrap_p5(values: np.ndarray, n_boot: int, rng: np.random.Generator) -> tuple[float, float, float, float]:
    """Return (p5_estimate, ci_low, ci_high, std_err) for percentile bootstrap."""
    n = values.size
    boot_p5 = np.empty(n_boot)
    for b in range(n_boot):
        sample = rng.choice(values, size=n, replace=True)
        boot_p5[b] = np.percentile(sample, 5)
    p5_estimate = float(np.percentile(values, 5))
    ci_low, ci_high = np.percentile(boot_p5, [2.5, 97.5])
    return p5_estimate, float(ci_low), float(ci_high), float(boot_p5.std(ddof=1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap CI for P5 throughput")
    parser.add_argument("--suffix", type=str, default="_100mc",
                        help="Suffix appended to the default raw CSV filename")
    parser.add_argument("--raw-path", type=str, default=None,
                        help="Explicit path to a raw CSV with columns "
                             "(tau_p, scheme, throughput_mbps). Overrides --suffix.")
    parser.add_argument("--out-name", type=str, default=None,
                        help="Override the output bootstrap CSV name (without .csv).")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    figs_dir = PROJECT_ROOT / "figures"
    if args.raw_path is not None:
        raw_path = Path(args.raw_path)
        if not raw_path.is_absolute():
            raw_path = figs_dir / raw_path.name
    else:
        raw_path = figs_dir / f"benchmark_sensitivity_raw{args.suffix}.csv"
    if not raw_path.exists():
        raise SystemExit(
            f"Raw CSV not found: {raw_path}.\n"
            f"Run benchmark_sensitivity.py first with --out-suffix {args.suffix}, "
            f"or pass --raw-path to point at a different file."
        )

    frame = pd.read_csv(raw_path)
    rng = np.random.default_rng(args.seed)
    rows: list[dict[str, float | int | str]] = []
    for (tau_p, scheme), group in frame.groupby(["tau_p", "scheme"]):
        values = group["throughput_mbps"].to_numpy()
        p5_est, ci_low, ci_high, se = bootstrap_p5(values, args.bootstrap, rng)
        rows.append(
            {
                "tau_p": int(tau_p),
                "scheme": scheme,
                "n_samples": int(values.size),
                "p5_mbps": p5_est,
                "p5_ci_low": ci_low,
                "p5_ci_high": ci_high,
                "p5_ci_half_width": (ci_high - ci_low) / 2.0,
                "p5_se": se,
            }
        )

    out = pd.DataFrame(rows).sort_values(["tau_p", "scheme"]).reset_index(drop=True)
    out_name = args.out_name or f"bootstrap_p5_ci{args.suffix}"
    out_path = figs_dir / f"{out_name}.csv"
    out.to_csv(out_path, index=False)
    print(f"Bootstrap P5 CI written to {out_path}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
