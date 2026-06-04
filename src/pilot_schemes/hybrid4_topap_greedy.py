"""Hybrid #4 — TopAP conflict graph + greedy contamination-min pilot selection.

Combines the two best non-adaptive hybrids identified in Diagnosis.md:

- **Hybrid #1 (TopAP bisect)**: top-N AP overlap conflict graph + max-degree
  greedy coloring. D1 axis dominance.
- **Hybrid #2 (Gao + greedy contam-min)**: Gao matching grouping + greedy
  β·β contamination-minimising pilot selection per group. D2 axis dominance.

Hybrid #4 replaces Hybrid #1's *coloring* step (which only minimises D1 axis
collisions) with Hybrid #2's *greedy contamination-min selection* (which
considers D2 axis simultaneously). This way the conflict graph still drives
the *grouping* (via maximum-independent-set traversal), but the pilot
assignment within and across groups respects β·β contamination too.

Cross-paper motivation (Mussbah_reproduce_plan.md §15 + Diagnosis.md §9):
- TopAP bisect and H2 Gao+greedy are the two cross-paper robust algorithms.
- Their advantages are *complementary* (D1 vs D2 axis).
- Combining them as a single non-adaptive scheme should preserve robustness
  on both Gao (K=200) and Mussbah (K=30) environments — unlike Mussbah and
  Hybrid#3 which lose advantage at large K.

Algorithm:
1. Build TopAP conflict graph (shared top-N strongest APs, like Hybrid#1).
2. Order UEs by maximum graph degree (max-degree-first, Liu 2020 style).
3. For each UE in order, pick the pilot p ∈ [0, τ_p) that minimises
   β_k · sum_per_pilot[p] (greedy contamination-min, like Hybrid#2).
4. Update sum_per_pilot incrementally.

Both axes considered: the conflict graph forces *non-trivial* selection
order; the contamination-min step picks the *best* available pilot.
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class Hybrid4TopAPGreedyPilotAssignment(PilotAssignmentScheme):
    """Hybrid #4 — TopAP conflict graph + greedy contamination-min selection."""

    name = "Hybrid#4 TopAP+greedy"

    def __init__(
        self,
        seed: int | None = None,
        *,
        top_n: int = 10,
    ) -> None:
        super().__init__(seed)
        self.top_n = int(top_n)
        self.n_colors_used_: int | None = None

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        beta = network.beta  # (K, M)
        K, M = beta.shape
        n_eff = int(np.clip(self.top_n, 1, M))

        # 1. Top-N AP membership
        top_aps = np.argpartition(-beta, n_eff - 1, axis=1)[:, :n_eff]
        is_top = np.zeros((K, M), dtype=bool)
        rows = np.arange(K)[:, None]
        is_top[rows, top_aps] = True

        # 2. Conflict graph (binary)
        conflict = (is_top.astype(np.int32) @ is_top.astype(np.int32).T) > 0
        np.fill_diagonal(conflict, False)

        # 3. Max-degree-first traversal order
        degree = conflict.sum(axis=1)
        order = np.argsort(-degree)  # high-degree first

        # 4. Greedy contamination-min pilot selection
        pilots = np.full(K, -1, dtype=int)
        sum_per_pilot = np.zeros((tau_p, M), dtype=beta.dtype)
        for k in order:
            # Conflict-aware: prefer pilots not used by k's neighbours
            blocked = set()
            for u in np.flatnonzero(conflict[k]):
                if pilots[u] >= 0:
                    blocked.add(int(pilots[u]))
            available = [p for p in range(tau_p) if p not in blocked]
            if not available:
                # All pilots blocked by conflict — fall back to all pilots, let
                # contamination-min choose the least painful.
                available = list(range(tau_p))
            available_arr = np.array(available, dtype=int)
            contam = sum_per_pilot[available_arr] @ beta[k]
            pick = int(available_arr[int(np.argmin(contam))])
            pilots[k] = pick
            sum_per_pilot[pick] += beta[k]

        self.n_colors_used_ = int(len(np.unique(pilots)))
        return pilots
