"""Chen et al. (2021) structured-access pilot assignment.

Faithful Python port of the algorithm from:
    S. Chen, J. Zhang, E. Björnson, J. Zhang, B. Ai,
    "Structured massive access for scalable cell-free massive MIMO systems",
    IEEE J. Sel. Areas Commun., vol. 39, no. 4, pp. 1086-1100, Apr. 2021.

Reference MATLAB: https://github.com/ShuaifeiChen273/structured_access_CFmMIMO
Specifically functionAPselection.m and functionUEgroup.m.

Two stages:

A) AP selection (`_initial_access`):
   Each UE iteratively picks its strongest unblacklisted AP. If that AP
   already serves > τ_p UEs, evict the one with the weakest β to the AP;
   evicted UE returns to the candidate list. A UE that ends up blacklisted
   on every AP becomes a "weak UE" and is granted service from all APs
   (mirrors Chen's lstOfWeakUEs handling).

B) UE grouping (`_form_groups`):
   Bisect on threshold δ ∈ [0.1, 0.6]. For each δ:
     - Compute the set of (AP, UE) pairs with β · MatA among the top δ
       fraction (in sorted-descending order).
     - Build a UE-UE conflict matrix B from the resulting MatA_ug.
     - Form groups: every UE with no conflicts is a singleton; remaining
       UEs are clustered greedily into compatible groups.
     - Each group gets one pilot.
   Adjust δ until the number of groups equals τ_p (or the bisection
   stagnates, in which case we fall back to the closest result).
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class StructuredPilotAccessAssignment(PilotAssignmentScheme):
    """Chen 2021 structured-access benchmark (Benchmark I)."""

    name = "Structured access"

    def __init__(
        self,
        seed: int | None = None,
        *,
        delta_init: float = 0.3,
        delta_min: float = 0.1,
        delta_max: float = 0.6,
        bisection_tol: float = 1e-4,
        max_bisection_iters: int = 25,
        max_access_iters: int | None = None,
    ) -> None:
        super().__init__(seed)
        self.delta_init = float(delta_init)
        self.delta_min = float(delta_min)
        self.delta_max = float(delta_max)
        self.bisection_tol = float(bisection_tol)
        self.max_bisection_iters = int(max_bisection_iters)
        self.max_access_iters = max_access_iters

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        beta = network.beta  # shape (M, K) — UE × AP
        mat_a, weak_ues = self._initial_access(beta, tau_p)
        pilots = self._bisect_groups(beta, mat_a, weak_ues, tau_p)
        return pilots

    # ------------------------------------------------------------------
    # Stage A: initial access with per-AP quota τ_p and weak-UE fallback
    # ------------------------------------------------------------------
    def _initial_access(self, beta: np.ndarray, tau_p: int) -> tuple[np.ndarray, set[int]]:
        m_count, k_count = beta.shape
        mat_a = np.zeros_like(beta, dtype=bool)  # serving relation
        blacklist = np.zeros_like(beta, dtype=bool)
        weak_ues: set[int] = set()
        pending = list(range(m_count))
        iter_cap = self.max_access_iters or (m_count * k_count * 4)

        seen = 0
        while pending:
            seen += 1
            if seen > iter_cap:
                break
            ue = pending.pop(0)
            while True:
                allowed = np.flatnonzero(~blacklist[ue] & ~mat_a[ue])
                if allowed.size == 0:
                    break
                if ue in weak_ues:
                    mat_a[ue, allowed] = True
                    break
                best_ap = int(allowed[int(np.argmax(beta[ue, allowed]))])
                mat_a[ue, best_ap] = True

                served = np.flatnonzero(mat_a[:, best_ap])
                if served.size <= tau_p:
                    continue
                # AP overloaded: evict weakest non-weak UE on this AP.
                non_weak = [u for u in served.tolist() if u not in weak_ues]
                if not non_weak:
                    non_weak = served.tolist()
                weakest = int(non_weak[int(np.argmin(beta[non_weak, best_ap]))])
                if weakest == ue:
                    # Just inserted — bounce it instead of the existing UEs.
                    weakest = ue
                blacklist[weakest, best_ap] = True
                mat_a[weakest, best_ap] = False
                # If the evicted UE is now blacklisted on all-but-one APs it
                # becomes a "weak UE" and gets a wholesale assignment later.
                if blacklist[weakest].sum() >= k_count - 1:
                    weak_ues.add(weakest)
                if weakest != ue and weakest not in pending:
                    pending.append(weakest)
                if weakest == ue:
                    # The just-placed UE was the one we evicted; resume its
                    # selection loop on the next iteration.
                    break

        # Last sweep so any weak UE without service ends up served everywhere.
        for ue in weak_ues:
            if mat_a[ue].sum() == 0:
                mat_a[ue, ~blacklist[ue]] = True
                if mat_a[ue].sum() == 0:
                    mat_a[ue, :] = True

        # Any UE that exited the loop with zero serving APs — assign its
        # strongest available AP as a safety net.
        for ue in range(m_count):
            if mat_a[ue].sum() == 0:
                best_ap = int(np.argmax(beta[ue]))
                mat_a[ue, best_ap] = True

        return mat_a, weak_ues

    # ------------------------------------------------------------------
    # Stage B: δ-bisection group formation
    # ------------------------------------------------------------------
    def _bisect_groups(
        self,
        beta: np.ndarray,
        mat_a: np.ndarray,
        weak_ues: set[int],
        tau_p: int,
    ) -> np.ndarray:
        delta = self.delta_init
        delta_lo, delta_hi = self.delta_min, self.delta_max
        best_pilots: np.ndarray | None = None
        best_gap = beta.shape[0] + 1

        for _ in range(self.max_bisection_iters):
            pilots, n_groups = self._form_groups_at_delta(beta, mat_a, weak_ues, delta)
            gap = abs(n_groups - tau_p)
            if gap < best_gap:
                best_gap = gap
                best_pilots = pilots.copy()
            if n_groups == tau_p:
                break
            if n_groups < tau_p:
                delta_lo = delta
            else:
                delta_hi = delta
            new_delta = 0.5 * (delta_lo + delta_hi)
            if abs(new_delta - delta) < self.bisection_tol:
                delta = new_delta
                break
            delta = new_delta

        assert best_pilots is not None
        return self._clip_to_tau_p(best_pilots, tau_p)

    def _form_groups_at_delta(
        self,
        beta: np.ndarray,
        mat_a: np.ndarray,
        weak_ues: set[int],
        delta: float,
    ) -> tuple[np.ndarray, int]:
        m_count, _ = beta.shape
        beta_x = beta * mat_a
        flat = beta_x.flatten()
        positives = flat[flat > 0]
        if positives.size == 0:
            return np.zeros(m_count, dtype=int), 1
        sorted_desc = np.sort(positives)[::-1]
        cutoff_idx = max(1, int(np.ceil(delta * sorted_desc.size))) - 1
        threshold = sorted_desc[min(cutoff_idx, sorted_desc.size - 1)]

        mat_a_ug = (beta_x >= threshold) & mat_a
        # Weak UEs keep their full mat_a entries (Chen MATLAB lines 70-72).
        for ue in weak_ues:
            mat_a_ug[ue] = mat_a[ue]

        # Conflict iff UEs share at least one AP in mat_a_ug.
        ints = mat_a_ug.astype(np.int32)
        conflict = (ints @ ints.T) > 0
        np.fill_diagonal(conflict, False)

        pilots = self._greedy_independent_set_grouping(conflict)
        n_groups = int(pilots.max() + 1) if pilots.size else 0
        return pilots, n_groups

    @staticmethod
    def _greedy_independent_set_grouping(conflict: np.ndarray) -> np.ndarray:
        """Form pilot groups: each group is an independent set in the conflict
        graph. Mirrors the Chen MATLAB grouping loop (singletons first, then
        absorb compatible UEs greedily)."""

        m_count = conflict.shape[0]
        pilots = np.full(m_count, -1, dtype=int)

        # Step 1: UEs with no conflicts each form their own group.
        next_group = 0
        no_conflict = ~conflict.any(axis=1)
        for ue in np.flatnonzero(no_conflict):
            pilots[ue] = next_group
            next_group += 1

        # Step 2: greedy absorption of remaining UEs.
        remaining = np.flatnonzero(pilots < 0).tolist()
        while remaining:
            head = remaining.pop(0)
            pilots[head] = next_group
            members = [head]
            survivors = []
            for ue in remaining:
                if not any(conflict[ue, m] for m in members):
                    pilots[ue] = next_group
                    members.append(ue)
                else:
                    survivors.append(ue)
            remaining = survivors
            next_group += 1

        return pilots

    def _clip_to_tau_p(self, pilots: np.ndarray, tau_p: int) -> np.ndarray:
        if pilots.max(initial=-1) < tau_p:
            return pilots.astype(int)
        return (pilots % tau_p).astype(int)
