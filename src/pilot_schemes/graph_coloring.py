"""Liu et al. (2020) graph-coloring pilot assignment.

Faithful Python port of the algorithm from:
    H. Liu, J. Zhang, S. Jin, B. Ai,
    "Graph coloring based pilot assignment for cell-free massive MIMO systems",
    IEEE Trans. Veh. Technol., vol. 69, no. 8, pp. 9180-9184, Aug. 2020.

Reference MATLAB code: https://github.com/BJTU-MIMO/CF-Graph-Coloring-Pilot-Assignment

Algorithm outline (matches reference simulation_main.m / functiongraph.m / funcnumofcolor.m):

1. Per-UE AP selection by cumulative-β threshold θ:
   for each UE k, sort APs by β_mk descending and accumulate until the running
   sum reaches θ_k · Σ_m β_mk. The serving set I(k) is the APs included.
2. Build binary conflict graph G on UEs: edge (j, j') iff I(j) ∩ I(j') ≠ ∅.
3. Greedy coloring with up to ⌈K/τ_p⌉ UEs per color:
   pick the uncolored UE with max degree, assign next color, then keep
   adding non-adjacent uncolored UEs to the same color until either the
   independent set is exhausted or the per-color quota is reached.
4. Bisection on θ so that the number of colors used equals τ_p.
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class GraphColoringPilotAssignment(PilotAssignmentScheme):
    """Liu 2020 graph-coloring benchmark (Benchmark II)."""

    name = "Graph coloring"

    def __init__(
        self,
        seed: int | None = None,
        *,
        theta_init: float = 0.94,
        theta_min: float = 0.20,
        theta_max: float = 0.999,
        bisection_tol: float = 1e-4,
        max_bisection_iters: int = 30,
    ) -> None:
        super().__init__(seed)
        self.theta_init = float(theta_init)
        self.theta_min = float(theta_min)
        self.theta_max = float(theta_max)
        self.bisection_tol = float(bisection_tol)
        self.max_bisection_iters = int(max_bisection_iters)

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        beta = network.beta
        m_count, k_count = beta.shape

        theta = self.theta_init
        theta_lo, theta_hi = self.theta_min, self.theta_max
        best_pilots: np.ndarray | None = None
        best_gap = m_count + 1

        for _ in range(self.max_bisection_iters):
            serving = self._serving_set_by_threshold(beta, theta)
            pilots, n_colors = self._greedy_coloring(serving, tau_p)
            gap = abs(n_colors - tau_p)
            if gap < best_gap:
                best_gap = gap
                best_pilots = pilots.copy()

            if n_colors == tau_p:
                break
            if n_colors > tau_p:
                # Too many colors needed — relax (smaller θ → fewer APs per UE
                # → sparser conflict graph → fewer colors).
                theta_hi = theta
            else:
                # Too few colors — tighten (larger θ → more APs per UE).
                theta_lo = theta
            new_theta = 0.5 * (theta_lo + theta_hi)
            if abs(new_theta - theta) < self.bisection_tol:
                theta = new_theta
                break
            theta = new_theta

        assert best_pilots is not None
        return self._clip_to_tau_p(best_pilots, tau_p)

    @staticmethod
    def _serving_set_by_threshold(beta: np.ndarray, theta: float) -> np.ndarray:
        """Boolean mask (M, K). serving[m, k]=True iff β_mk is among the
        strongest APs that together collect ≥ θ · Σ_k β_mk for UE m."""

        sorted_desc = np.sort(beta, axis=1)[:, ::-1]
        total = sorted_desc.sum(axis=1, keepdims=True)
        cumulative = np.cumsum(sorted_desc, axis=1)
        target = theta * total
        cutoff_idx = np.argmax(cumulative >= target, axis=1)
        cutoff_value = sorted_desc[np.arange(beta.shape[0]), cutoff_idx]
        return beta >= cutoff_value[:, None]

    def _greedy_coloring(self, serving: np.ndarray, tau_p: int) -> tuple[np.ndarray, int]:
        """Greedy coloring with at most ⌈M / tau_p⌉ UEs per color.

        Matches the loop structure of funcnumofcolor.m: at every new colour
        pick the highest-degree uncoloured node, then iteratively absorb
        non-adjacent nodes until the per-colour quota is hit.
        """

        m_count = serving.shape[0]
        # Boolean conflict matrix: True iff UEs i and j share at least one
        # selected AP. Diagonal kept False (a UE doesn't conflict with itself).
        conflict = (serving.astype(np.int32) @ serving.astype(np.int32).T) > 0
        np.fill_diagonal(conflict, False)

        per_color_quota = max(1, int(np.ceil(m_count / max(tau_p, 1))))
        colors = np.full(m_count, -1, dtype=int)
        current_color = 0

        while np.any(colors < 0):
            uncolored = np.flatnonzero(colors < 0)
            # Degree within still-uncolored nodes — matches Liu's "weight" loop.
            sub_conflict = conflict[np.ix_(uncolored, uncolored)]
            degree = sub_conflict.sum(axis=1)
            seed = int(uncolored[int(np.argmax(degree))])
            colors[seed] = current_color
            blocked = conflict[seed].copy()
            blocked[seed] = True
            placed = 1
            while placed < per_color_quota:
                candidates = np.flatnonzero((colors < 0) & ~blocked)
                if candidates.size == 0:
                    break
                pick = int(candidates[0])
                colors[pick] = current_color
                blocked |= conflict[pick]
                blocked[pick] = True
                placed += 1
            current_color += 1

        return colors, current_color

    def _clip_to_tau_p(self, pilots: np.ndarray, tau_p: int) -> np.ndarray:
        """Map color indices into the [0, tau_p) pilot range. If more colors
        were used than τ_p, fold extras by modulo (preserves grouping but
        reuses pilots across over-flowed colors)."""

        if pilots.max(initial=-1) < tau_p:
            return pilots.astype(int)
        return (pilots % tau_p).astype(int)
