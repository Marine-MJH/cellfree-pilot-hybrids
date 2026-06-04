"""Hybrid #1 — Top-N strong-AP overlap conflict graph + greedy coloring.

Diagnostic-informed variant of Liu 2020 graph coloring. The conflict-graph
edge is determined by *shared top-N strongest-AP* membership (D1 axis from
Diagnosis.md §4.1) rather than the cumulative-β serving set (Liu's
definition).

Two operating modes:

- ``bisect=False`` (default): uses fixed ``top_n``. Diagnosis.md §6.4 found
  N ≈ τ_p / 2 optimal so passing ``top_n=tau_p//2`` per call also works.
- ``bisect=True`` (Hybrid #1 + N-bisection): runs an integer bisection on
  N so that the greedy coloring uses exactly τ_p colors, matching the
  τ_p-budget. Analogue of Liu's θ-bisection.

Motivation (from Diagnosis.md §4-6):

- D1 (top-N strong-AP collision rate) was identified as the dominant
  determinant of P5 (worst-case) throughput.
- TopAP (fixed N=5 at τ_p=10, N=10 at τ_p∈{15,20,25}) already beat
  Gao/Liu/Chen at small τ_p (Diagnosis.md §6.2-6.3).
- N-bisection automates the N choice across the τ_p sweep.

Algorithm (fixed N):

1. For each UE k, identify its top-N APs by β_{km}.
2. Build a binary conflict graph G: edge (i, j) iff users i and j share
   at least one top-N AP.
3. Greedy coloring (Liu-style, max-degree-first with per-color quota
   ⌈K / τ_p⌉). Falls back to modulo wrapping if chromatic > τ_p.

Algorithm (bisection on N):

Repeat the fixed-N procedure with N adjusted by integer bisection in
``[top_n_min, top_n_max]``. If chromatic > τ_p the conflict graph is too
dense → reduce N. If chromatic < τ_p → increase N (tighter conflict
definition). Stop when chromatic == τ_p, when the integer interval
collapses, or after ``max_bisection_iters``.
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class TopAPGraphColoringPilotAssignment(PilotAssignmentScheme):
    """Hybrid #1: conflict graph based on shared top-N strongest APs.

    Optionally performs integer bisection on ``N`` so chromatic == τ_p.
    """

    name = "Top-AP graph coloring"

    def __init__(
        self,
        seed: int | None = None,
        *,
        top_n: int = 10,
        bisect: bool = False,
        top_n_min: int = 2,
        top_n_max: int = 40,
        max_bisection_iters: int = 20,
        adaptive_tau_p: bool = False,
    ) -> None:
        super().__init__(seed)
        self.top_n = int(top_n)
        self.bisect = bool(bisect)
        self.top_n_min = int(top_n_min)
        self.top_n_max = int(top_n_max)
        self.max_bisection_iters = int(max_bisection_iters)
        # Hybrid #3 (Mussbah_reproduce_plan.md §13.5): when True, use raw
        # quota-free chromatic as actual τ_p — same mechanism as Mussbah's
        # adaptive τ_p, but on top of the TopAP conflict graph. Disables the
        # per-color quota that normally forces colors = τ_p_design.
        self.adaptive_tau_p = bool(adaptive_tau_p)
        # Diagnostics populated by the last assign call:
        self.n_colors_used_: int | None = None
        self.n_used_: int | None = None

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        if self.adaptive_tau_p:
            # Build conflict + quota-free coloring → raw chromatic as τ_p_actual.
            n_used = self.top_n
            if self.bisect:
                # Find largest N such that real_chromatic ≤ τ_p (same as bisect mode).
                n_used = self._bisect_choose_n(network, tau_p)
            conflict = self._build_conflict(network.beta, n_used)
            colors = self._quota_free_color(conflict)
            self.n_used_ = int(n_used)
            self.n_colors_used_ = int(colors.max() + 1) if colors.size else 0
            return colors.astype(int)
        if not self.bisect:
            pilots, n_colors = self._build_and_color(network, self.top_n, tau_p)
            self.n_colors_used_ = int(n_colors)
            self.n_used_ = int(min(self.top_n, network.beta.shape[1]))
            return self._clip_to_tau_p(pilots, tau_p)
        return self._assign_with_bisection(network, tau_p)

    @staticmethod
    def _quota_free_color(conflict: np.ndarray) -> np.ndarray:
        """Max-degree-first greedy coloring without per-color quota.

        Returns colors of length K with values in ``[0, chromatic_estimate)``.
        Used by ``adaptive_tau_p`` mode so the output reflects the actual
        chromatic number of the conflict graph, not the design τ_p.
        """
        K = conflict.shape[0]
        if K == 0:
            return np.empty(0, dtype=int)
        colors = np.full(K, -1, dtype=int)
        degree = conflict.sum(axis=1)
        order = np.argsort(-degree)
        for v in order:
            used: set[int] = set()
            for u in np.flatnonzero(conflict[v]):
                if colors[u] >= 0:
                    used.add(int(colors[u]))
            c = 0
            while c in used:
                c += 1
            colors[v] = c
        return colors

    def _bisect_choose_n(self, network: Network, tau_p: int) -> int:
        """Return the largest ``N`` such that quota-free chromatic ≤ τ_p.

        Same selection logic as ``_assign_with_bisection`` but returns the
        chosen N for use by ``adaptive_tau_p`` mode.
        """
        M = network.beta.shape[1]
        n_lo = max(1, self.top_n_min)
        n_hi = min(self.top_n_max, M - 1) if M > 1 else 1
        if n_hi < n_lo:
            n_hi = n_lo
        beta = network.beta
        best_n = n_lo
        for _ in range(self.max_bisection_iters):
            if n_lo > n_hi:
                break
            n_mid = (n_lo + n_hi) // 2
            conflict = self._build_conflict(beta, n_mid)
            chi = self._real_chromatic(conflict)
            if chi <= tau_p:
                best_n = n_mid
                n_lo = n_mid + 1
            else:
                n_hi = n_mid - 1
        return best_n

    # ------------------------------------------------------------------
    # Bisection wrapper
    # ------------------------------------------------------------------
    def _assign_with_bisection(self, network: Network, tau_p: int) -> np.ndarray:
        """Find the largest ``N`` such that the *quota-free* greedy chromatic
        number of the top-N conflict graph is ≤ τ_p.

        Rationale: the per-color quota ``⌈K/τ_p⌉`` forces the *quota-bounded*
        coloring (used for actual pilot assignment) to almost always emit
        exactly τ_p colors, regardless of N. So a chromatic-equals-τ_p
        termination is trivially satisfied and pushes N too small, weakening
        the conflict definition. Instead, we measure the *quota-free* greedy
        chromatic (upper-bound estimate of true χ) and bisect on N so that
        the conflict graph still fits within τ_p colors without quota
        intervention. Larger N → stricter conflict → larger chromatic, so
        the relationship is monotone enough for integer bisection.
        """
        M = network.beta.shape[1]
        n_lo = max(1, self.top_n_min)
        n_hi = min(self.top_n_max, M - 1) if M > 1 else 1
        if n_hi < n_lo:
            n_hi = n_lo

        beta = network.beta
        best_n = n_lo
        best_chromatic = M + 1

        for _ in range(self.max_bisection_iters):
            if n_lo > n_hi:
                break
            n_mid = (n_lo + n_hi) // 2
            conflict = self._build_conflict(beta, n_mid)
            chi = self._real_chromatic(conflict)
            if chi <= tau_p:
                # OK — try larger N to tighten conflict.
                best_n = n_mid
                best_chromatic = chi
                n_lo = n_mid + 1
            else:
                # Too dense — shrink N.
                n_hi = n_mid - 1

        # Final assignment with the chosen N (this re-applies the per-color
        # quota; we keep the same coloring routine used in fixed-N mode).
        pilots, n_colors = self._build_and_color(network, best_n, tau_p)
        self.n_colors_used_ = int(n_colors)
        self.n_used_ = int(best_n)
        return self._clip_to_tau_p(pilots, tau_p)

    @staticmethod
    def _build_conflict(beta: np.ndarray, top_n: int) -> np.ndarray:
        K, M = beta.shape
        n_eff = int(np.clip(top_n, 1, M))
        top_aps = np.argpartition(-beta, n_eff - 1, axis=1)[:, :n_eff]
        is_top = np.zeros((K, M), dtype=bool)
        rows = np.arange(K)[:, None]
        is_top[rows, top_aps] = True
        conflict = (is_top.astype(np.int32) @ is_top.astype(np.int32).T) > 0
        np.fill_diagonal(conflict, False)
        return conflict

    @staticmethod
    def _real_chromatic(conflict: np.ndarray) -> int:
        """Quota-free max-degree-first greedy coloring → chromatic upper bound."""
        K = conflict.shape[0]
        if K == 0:
            return 0
        colors = np.full(K, -1, dtype=int)
        degree = conflict.sum(axis=1)
        order = np.argsort(-degree)
        for v in order:
            used: set[int] = set()
            for u in np.flatnonzero(conflict[v]):
                if colors[u] >= 0:
                    used.add(int(colors[u]))
            c = 0
            while c in used:
                c += 1
            colors[v] = c
        return int(colors.max() + 1)

    # ------------------------------------------------------------------
    # Core build + color
    # ------------------------------------------------------------------
    def _build_and_color(
        self, network: Network, top_n: int, tau_p: int
    ) -> tuple[np.ndarray, int]:
        beta = network.beta  # (K, M) where K=num_ues, M=num_aps
        K, M = beta.shape
        n_eff = int(np.clip(top_n, 1, M))
        top_aps = np.argpartition(-beta, n_eff - 1, axis=1)[:, :n_eff]
        is_top = np.zeros((K, M), dtype=bool)
        rows = np.arange(K)[:, None]
        is_top[rows, top_aps] = True
        conflict = (is_top.astype(np.int32) @ is_top.astype(np.int32).T) > 0
        np.fill_diagonal(conflict, False)
        return self._greedy_coloring(conflict, tau_p)

    def _greedy_coloring(
        self, conflict: np.ndarray, tau_p: int
    ) -> tuple[np.ndarray, int]:
        """Liu-style max-degree-first greedy with per-color quota ⌈K/τ_p⌉."""
        K = conflict.shape[0]
        per_color_quota = max(1, int(np.ceil(K / max(tau_p, 1))))
        colors = np.full(K, -1, dtype=int)
        current_color = 0

        while np.any(colors < 0):
            uncolored = np.flatnonzero(colors < 0)
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

    @staticmethod
    def _clip_to_tau_p(pilots: np.ndarray, tau_p: int) -> np.ndarray:
        if pilots.max(initial=-1) < tau_p:
            return pilots.astype(int)
        return (pilots % tau_p).astype(int)
