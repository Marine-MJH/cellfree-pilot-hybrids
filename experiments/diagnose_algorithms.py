"""Diagnostic metrics for pilot assignment algorithms.

Computes D1-D5 metrics defined in Diagnosis.md §3:

- D1: Top-N strong-AP collision rate (per UE)
- D2: Per-UE coherent pilot interference (power-independent part)
- D3: Pilot reuse spatial distance (median / p5)
- D4: Conflict graph chromatic number (Dsatur upper bound)
- D5: Decision disagreement (pair-level pilot assignment overlap)

Inputs and conventions:

- ``network.beta`` shape is ``(num_ues, num_aps)`` in the codebase
  (paper writes ``β_{mk}`` with m=AP; rows here are UEs).
- ``pilots`` is shape ``(num_ues,)`` with values in ``[0, tau_p)``.

Usage::

    python experiments/diagnose_algorithms.py --realizations 50 --tau-values 10 20 30
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

from src.config import SimulationConfig
from src.metrics import sinr_components
from src.network import Network
from src.pilot_schemes import (
    GraphColoringPilotAssignment,
    MatchingBasedPilotAssignment,
    StructuredPilotAccessAssignment,
    TopAPGraphColoringPilotAssignment,
)


# ---------------------------------------------------------------------------
# D1: top-N strong-AP collision rate (per UE)
# ---------------------------------------------------------------------------
def d1_strong_ap_collisions(network: Network, pilots: np.ndarray, top_n: int = 10) -> np.ndarray:
    """For each UE k, count same-pilot UEs that share ≥1 of k's top-N strongest APs."""
    beta = network.beta  # (K, M) where K=num_ues, M=num_aps
    K, M = beta.shape
    top_n = min(top_n, M)
    top_aps = np.argpartition(-beta, top_n - 1, axis=1)[:, :top_n]  # (K, top_n)
    is_top = np.zeros((K, M), dtype=bool)
    rows = np.arange(K)[:, None]
    is_top[rows, top_aps] = True
    shared_top = (is_top.astype(np.int32) @ is_top.T.astype(np.int32)) > 0  # (K, K)
    same_pilot = pilots[:, None] == pilots[None, :]
    np.fill_diagonal(shared_top, False)
    np.fill_diagonal(same_pilot, False)
    return (shared_top & same_pilot).sum(axis=1)


# ---------------------------------------------------------------------------
# D2: per-UE coherent pilot interference (power-independent part)
# ---------------------------------------------------------------------------
def d2_coherent_interference(network: Network, pilots: np.ndarray) -> np.ndarray:
    """Sum of coherent pilot interference entries per UE (Eq. 8 same-pilot term)."""
    comp = sinr_components(network, pilots)
    return comp.coherent_pilot_interference.sum(axis=1)  # (K,)


# ---------------------------------------------------------------------------
# D3: pilot reuse spatial distance
# ---------------------------------------------------------------------------
def d3_pilot_reuse_distance(network: Network, pilots: np.ndarray) -> dict[str, float]:
    """Pairwise UE distance distribution among same-pilot pairs.

    Returns median / 5th-percentile / mean in meters.
    """
    pos = network.ue_positions_m  # (K, 2)
    dists: list[float] = []
    for p in np.unique(pilots):
        users = np.flatnonzero(pilots == p)
        if users.size < 2:
            continue
        sub = pos[users]
        diff = sub[:, None, :] - sub[None, :, :]
        d = np.linalg.norm(diff, axis=2)
        iu = np.triu_indices_from(d, k=1)
        dists.extend(d[iu].tolist())
    if not dists:
        return {"median_m": float("nan"), "p5_m": float("nan"), "mean_m": float("nan")}
    arr = np.asarray(dists)
    return {
        "median_m": float(np.median(arr)),
        "p5_m": float(np.percentile(arr, 5)),
        "mean_m": float(np.mean(arr)),
    }


# ---------------------------------------------------------------------------
# D4: chromatic number of Liu-style conflict graph (Dsatur upper bound)
# ---------------------------------------------------------------------------
def _dsatur_color_count(adjacency: np.ndarray) -> int:
    K = adjacency.shape[0]
    if K == 0:
        return 0
    adj = adjacency.astype(bool)
    colors = np.full(K, -1, dtype=int)
    degree = adj.sum(axis=1)
    saturation = np.zeros(K, dtype=int)
    ncs: list[set[int]] = [set() for _ in range(K)]
    for _ in range(K):
        uncolored = np.flatnonzero(colors < 0)
        if uncolored.size == 0:
            break
        sat = saturation[uncolored]
        max_sat = sat.max()
        cands = uncolored[sat == max_sat]
        if cands.size > 1:
            deg = degree[cands]
            v = int(cands[int(np.argmax(deg))])
        else:
            v = int(cands[0])
        c = 0
        while c in ncs[v]:
            c += 1
        colors[v] = c
        for u in np.flatnonzero(adj[v]):
            if colors[u] >= 0:
                continue
            if c not in ncs[u]:
                ncs[u].add(c)
                saturation[u] = len(ncs[u])
    return int(colors.max() + 1)


def d4_chromatic_number(network: Network, theta: float = 0.7) -> int:
    """Liu-style conflict graph (cumulative-β serving set) chromatic number.

    Uses Dsatur as an upper bound (NP-hard to compute exactly).
    """
    beta = network.beta  # (K, M)
    K, M = beta.shape
    sorted_beta = np.sort(beta, axis=1)[:, ::-1]
    cumsum = np.cumsum(sorted_beta, axis=1)
    totals = cumsum[:, -1]
    threshold = theta * totals
    counts = (cumsum < threshold[:, None]).sum(axis=1) + 1
    counts = np.minimum(counts, M)
    order = np.argsort(-beta, axis=1)
    serving = np.zeros_like(beta, dtype=bool)
    for k in range(K):
        serving[k, order[k, : counts[k]]] = True
    adjacency = (serving.astype(np.int32) @ serving.T.astype(np.int32)) > 0
    np.fill_diagonal(adjacency, False)
    return _dsatur_color_count(adjacency)


# ---------------------------------------------------------------------------
# D5: decision disagreement (pair-level)
# ---------------------------------------------------------------------------
def d5_decision_disagreement(pilots_a: np.ndarray, pilots_b: np.ndarray) -> dict[str, float]:
    """Fraction of UE pairs where A and B disagree on same/different pilot."""
    same_a = pilots_a[:, None] == pilots_a[None, :]
    same_b = pilots_b[:, None] == pilots_b[None, :]
    K = pilots_a.size
    iu = np.triu_indices(K, k=1)
    a_same = same_a[iu]
    b_same = same_b[iu]
    n_pairs = a_same.size
    agree = (a_same == b_same).sum()
    a_only = (a_same & ~b_same).sum()
    b_only = (~a_same & b_same).sum()
    return {
        "agree_rate": float(agree / n_pairs),
        "a_same_b_diff_rate": float(a_only / n_pairs),
        "a_diff_b_same_rate": float(b_only / n_pairs),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Algorithm diagnosis")
    parser.add_argument("--realizations", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tau-values", type=int, nargs="+", default=[10, 20, 30])
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--theta-chromatic", type=float, default=0.7)
    parser.add_argument("--out-suffix", type=str, default="_50mc")
    args = parser.parse_args()

    config = SimulationConfig(num_aps=500, num_ues=200, tau_p=20, random_seed=args.seed)
    rng_master = np.random.default_rng(args.seed)

    records: list[dict[str, float | int | str]] = []
    pair_records: list[dict[str, float | int | str]] = []

    for r in range(args.realizations):
        network = Network.random(config, rng_master)
        chromatic = d4_chromatic_number(network, theta=args.theta_chromatic)
        for tau_p in args.tau_values:
            schemes = {
                "Gao matching": MatchingBasedPilotAssignment(seed=args.seed + 10 + r),
                "Graph coloring": GraphColoringPilotAssignment(seed=args.seed + 20 + r),
                "Structured access": StructuredPilotAccessAssignment(seed=args.seed + 30 + r),
                "Top-AP graph coloring": TopAPGraphColoringPilotAssignment(
                    seed=args.seed + 40 + r, top_n=args.top_n
                ),
            }
            pilots_by_scheme = {name: scheme.assign(network, tau_p) for name, scheme in schemes.items()}
            for name, pilots in pilots_by_scheme.items():
                d1 = d1_strong_ap_collisions(network, pilots, top_n=args.top_n)
                d2 = d2_coherent_interference(network, pilots)
                d3 = d3_pilot_reuse_distance(network, pilots)
                records.append(
                    {
                        "realization": r,
                        "tau_p": tau_p,
                        "scheme": name,
                        "d1_mean": float(d1.mean()),
                        "d1_p95": float(np.percentile(d1, 95)),
                        "d2_mean": float(d2.mean()),
                        "d2_p95": float(np.percentile(d2, 95)),
                        "d3_median_m": d3["median_m"],
                        "d3_p5_m": d3["p5_m"],
                        "d4_chromatic": chromatic,
                    }
                )
            for name_a, name_b in [
                ("Gao matching", "Graph coloring"),
                ("Gao matching", "Structured access"),
                ("Graph coloring", "Structured access"),
            ]:
                d5 = d5_decision_disagreement(pilots_by_scheme[name_a], pilots_by_scheme[name_b])
                pair_records.append(
                    {
                        "realization": r,
                        "tau_p": tau_p,
                        "pair": f"{name_a} vs {name_b}",
                        **d5,
                    }
                )

    frame = pd.DataFrame(records)
    pair_frame = pd.DataFrame(pair_records)

    out_dir = PROJECT_ROOT / "figures"
    out_dir.mkdir(exist_ok=True)
    raw_path = out_dir / f"diagnose_algorithms_raw{args.out_suffix}.csv"
    pair_raw_path = out_dir / f"diagnose_algorithms_pairs_raw{args.out_suffix}.csv"
    frame.to_csv(raw_path, index=False)
    pair_frame.to_csv(pair_raw_path, index=False)

    summary_cols = ["d1_mean", "d1_p95", "d2_mean", "d2_p95",
                    "d3_median_m", "d3_p5_m", "d4_chromatic"]
    summary = frame.groupby(["tau_p", "scheme"])[summary_cols].mean().reset_index()
    pair_summary = (
        pair_frame.groupby(["tau_p", "pair"])
        [["agree_rate", "a_same_b_diff_rate", "a_diff_b_same_rate"]]
        .mean()
        .reset_index()
    )

    summary_path = out_dir / f"diagnose_algorithms_summary{args.out_suffix}.csv"
    pair_summary_path = out_dir / f"diagnose_algorithms_pairs_summary{args.out_suffix}.csv"
    summary.to_csv(summary_path, index=False)
    pair_summary.to_csv(pair_summary_path, index=False)

    print(f"Per-scheme summary → {summary_path}")
    print(summary.to_string(index=False))
    print(f"\nPair-level summary → {pair_summary_path}")
    print(pair_summary.to_string(index=False))


if __name__ == "__main__":
    main()
