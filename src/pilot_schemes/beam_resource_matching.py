"""MJH teammate's AP-beam-resource many-to-many matching pilot assignment.

Extension of Gao 2024 UE-AP matching to beam-domain.

Reference: ``MJH/beam_matching.py`` (matching_beam_assignment, many_to_many_resource_matching,
assign_pilots_by_matching_groups). The original implementation lives in the
teammate directory; this is a faithful port wired into our framework so that
the algorithm can run on our common-ground multi-antenna environment.

Algorithm sketch
----------------
1. Beam reports: use ``Network.beam_info`` to obtain reported / active /
   moderate beam masks for each UE.
2. UE quota: number of active beams (Mussbah Algorithm 1 reference rule).
3. Many-to-many matching between UEs and resources ``r=(l, n)``:
   - UE preference list: candidate beams sorted by beam power.
   - Resource preference rank: candidate UEs sorted by beam power.
   - Resource quota: ``baseline_tau_p``.
4. Resource groups -> beam-overlap ratio matrix M.
5. Groups processed in descending overlap-sum order; orthogonal pilots
   assigned within each group, falling back to min-conflict if exhausted.

Two variants:

- ``adaptive_tau_p=True``  (default): tau_p = max resource-group size.
- ``adaptive_tau_p=False``: tau_p = baseline_tau_p (fixed).

(``adaptive=True`` is the strongest variant in the teammate's own results.)
"""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class BeamResourceMatchingPilotAssignment(PilotAssignmentScheme):
    """MJH AP-beam-resource many-to-many matching pilot assignment."""

    name = "BeamResourceMatching"

    def __init__(
        self,
        seed: int | None = None,
        *,
        delta: float = 0.95,
        baseline_tau_p: int = 10,
        adaptive_tau_p: bool = True,
    ) -> None:
        super().__init__(seed)
        self.delta = float(delta)
        self.baseline_tau_p = max(int(baseline_tau_p), 1)
        self.adaptive_tau_p = bool(adaptive_tau_p)
        self.n_colors_used_: int | None = None
        self.mu_mask_: np.ndarray | None = None  # (K, L*N) bool — final matching
        self.max_group_size_: int | None = None

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------
    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        if getattr(network, "beam_powers", None) is None:
            raise NotImplementedError(
                "BeamResourceMatching requires multi-antenna Network (num_antennas_per_ap > 1)."
            )
        K = int(network.num_ues)
        L = int(network.num_aps)
        N = int(network.num_antennas_per_ap)
        R = L * N

        b_active_LN_K, b_inactive_LN_K = network.beam_info(delta=self.delta)
        # Transpose to (K, L*N) for easier per-UE indexing
        b_active = b_active_LN_K.T.astype(bool)
        b_inactive = b_inactive_LN_K.T.astype(bool)
        reported = b_active | b_inactive  # (K, L*N)

        beam_power_K_R = network.beam_powers.reshape(K, R).astype(float)

        candidates = reported.copy()
        for k in range(K):
            if not np.any(candidates[k]):
                candidates[k, int(np.argmax(beam_power_K_R[k]))] = True

        ue_quota = b_active.sum(axis=1).astype(int)
        ue_quota[ue_quota <= 0] = 1

        mu = self._many_to_many_matching(
            K, R, candidates, beam_power_K_R, ue_quota, self.baseline_tau_p
        )
        self.mu_mask_ = mu

        active = mu.reshape(K, L, N)
        moderate = candidates.reshape(K, L, N) & (~active)

        resource_groups: List[List[int]] = []
        group_sizes: List[int] = []
        for r in range(R):
            users = np.flatnonzero(mu[:, r]).astype(int).tolist()
            resource_groups.append(users)
            group_sizes.append(len(users))
        max_group_size = max(group_sizes) if group_sizes else 1
        self.max_group_size_ = int(max_group_size)

        if self.adaptive_tau_p:
            tau_for_assignment = max(1, int(max_group_size))
        else:
            tau_for_assignment = int(self.baseline_tau_p)

        M_ratio = self._beam_overlap_ratio(active.reshape(K, R), moderate.reshape(K, R))

        pilots = self._assign_pilots_by_groups(
            resource_groups, M_ratio, tau_for_assignment, self.rng
        )
        self.n_colors_used_ = int(pilots.max(initial=-1) + 1)
        return pilots.astype(int)

    # ------------------------------------------------------------------
    # Helpers (ports of MJH/beam_matching.py)
    # ------------------------------------------------------------------
    @staticmethod
    def _many_to_many_matching(
        K: int,
        R: int,
        candidates: np.ndarray,
        power_K_R: np.ndarray,
        ue_quota: np.ndarray,
        resource_quota: int,
    ) -> np.ndarray:
        """Port of ``MJH/beam_matching.py:many_to_many_resource_matching``."""
        ue_pref: List[List[int]] = []
        for k in range(K):
            idx = np.flatnonzero(candidates[k])
            order = idx[np.argsort(power_K_R[k, idx])[::-1]]
            ue_pref.append(order.astype(int).tolist())

        resource_rank = np.full((R, K), np.iinfo(np.int32).max, dtype=np.int32)
        for r in range(R):
            users = np.flatnonzero(candidates[:, r])
            if users.size == 0:
                continue
            order = users[np.argsort(power_K_R[users, r])[::-1]]
            resource_rank[r, order] = np.arange(order.size, dtype=np.int32)

        mu = np.zeros((K, R), dtype=bool)
        next_ptr = np.zeros(K, dtype=int)
        free = np.ones(K, dtype=bool)
        quota_u = np.maximum(ue_quota, 1)
        q_r = max(int(resource_quota), 1)

        while np.any(free):
            proposers_by_r: Dict[int, List[int]] = {}
            for k in np.flatnonzero(free):
                if int(mu[k].sum()) >= quota_u[k] or next_ptr[k] >= len(ue_pref[k]):
                    free[k] = False
                    continue
                r = ue_pref[k][next_ptr[k]]
                next_ptr[k] += 1
                proposers_by_r.setdefault(r, []).append(k)
            if not proposers_by_r:
                break
            for r, proposers in proposers_by_r.items():
                current = np.flatnonzero(mu[:, r]).astype(int).tolist()
                pool = sorted(
                    set(current + proposers),
                    key=lambda u: (resource_rank[r, u], u),
                )
                accepted = set(pool[:q_r])
                mu[:, r] = False
                if accepted:
                    mu[list(accepted), r] = True
            for k in range(K):
                if int(mu[k].sum()) >= quota_u[k] or next_ptr[k] >= len(ue_pref[k]):
                    free[k] = False
                else:
                    free[k] = True

        for k in range(K):
            if not np.any(mu[k]):
                r = int(np.argmax(power_K_R[k]))
                users = np.flatnonzero(mu[:, r]).astype(int).tolist() + [k]
                users = sorted(set(users), key=lambda u: (resource_rank[r, u], u))[:q_r]
                mu[:, r] = False
                mu[users, r] = True
        return mu

    @staticmethod
    def _beam_overlap_ratio(active_K_R: np.ndarray, moderate_K_R: np.ndarray) -> np.ndarray:
        K = active_K_R.shape[0]
        A = active_K_R.astype(np.int8)
        I = moderate_K_R.astype(np.int8)
        overlap = A @ A.T + A @ I.T + I @ A.T
        denom = np.maximum(A.sum(axis=1).astype(float), 1.0)
        M_ratio = overlap.astype(float) / denom[:, None]
        np.fill_diagonal(M_ratio, 0.0)
        return M_ratio

    @staticmethod
    def _assign_pilots_by_groups(
        resource_groups: List[List[int]],
        M_ratio: np.ndarray,
        tau_p: int,
        rng: np.random.Generator,
    ) -> np.ndarray:
        K = M_ratio.shape[0]
        tau = max(int(tau_p), 1)
        pilot = -np.ones(K, dtype=int)

        group_scores = []
        for r, g in enumerate(resource_groups):
            users = np.asarray(g, dtype=int)
            if users.size <= 1:
                S = 0.0
            else:
                S = float(np.sum(M_ratio[np.ix_(users, users)]))
            group_scores.append((S, r))
        group_scores.sort(key=lambda x: (-x[0], x[1]))

        total_pilots = np.arange(tau, dtype=int)
        user_priority = M_ratio.sum(axis=1)

        for _, r in group_scores:
            g = list(resource_groups[r])
            if not g:
                continue
            g.sort(key=lambda u: (-user_priority[u], u))
            occupied = set(int(pilot[u]) for u in g if pilot[u] >= 0)
            for u in g:
                if pilot[u] >= 0:
                    continue
                available = np.array(
                    [p for p in total_pilots if int(p) not in occupied], dtype=int
                )
                if available.size > 0:
                    chosen = int(rng.choice(available))
                else:
                    costs = np.zeros(tau, dtype=float)
                    for p in range(tau):
                        same = np.flatnonzero(pilot == p)
                        costs[p] = (
                            float(np.sum(M_ratio[u, same] + M_ratio[same, u]))
                            if same.size
                            else 0.0
                        )
                    chosen = int(np.argmin(costs))
                pilot[u] = chosen
                occupied.add(chosen)

        for u in range(K):
            if pilot[u] >= 0:
                continue
            costs = np.zeros(tau, dtype=float)
            for p in range(tau):
                same = np.flatnonzero(pilot == p)
                costs[p] = (
                    float(np.sum(M_ratio[u, same] + M_ratio[same, u]))
                    if same.size
                    else 0.0
                )
            pilot[u] = int(np.argmin(costs))
        return pilot
