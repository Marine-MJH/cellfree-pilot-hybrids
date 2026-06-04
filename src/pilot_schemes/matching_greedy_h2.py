"""Hybrid #2 — Gao matching + greedy contamination-min pilot assignment.

Motivation (from Diagnosis.md §4-5):

- Gao Algorithm 1 (many-to-many matching) groups each AP's top-τ_p UEs by
  β, which is what gives Gao its D1 (top-AP collision) optimality at
  small τ_p (§4.1, §4.6 H1).
- Gao Algorithm 2 then assigns pilots *randomly* within each group's
  available pilot pool, ordered by the common-serving-AP ratio S_k.
  This random step is where D2-axis information is lost.
- This hybrid keeps Gao Algorithm 1 exactly (preserving the D1 win) and
  replaces Algorithm 2's random pilot draw with a *greedy contamination-
  minimising* selection: for each unassigned UE in the current group,
  pick the available pilot whose already-assigned same-pilot UEs sum the
  least β·β co-location against the candidate UE.

Greedy choice metric for UE k considering pilot p:

    C(k, p) = Σ_{k' : pilot(k') == p} <β_k, β_{k'}>

where ``<·, ·>`` is the standard inner product over AP indices. This is
the per-pair contribution to the Σβ·β contamination metric used in
``experiments/benchmark_sensitivity.py``.

Algorithm:

1. Run Gao Algorithm 1 (matching → groups) — identical to ``MatchingBasedPilotAssignment``.
2. Iterate groups in descending S_k order.
3. For each group, iterate unassigned UEs (no particular order):
   - Find the pilot among the currently-available pool that minimises
     C(ue, p) given the *current* partial assignment.
   - Assign and remove it from the local pool.
4. Fall back to random for any UE that remains unassigned (rare).
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme
from .matching_gao import MatchingBasedPilotAssignment


class HybridGaoColoringPilotAssignment(PilotAssignmentScheme):
    """Hybrid #2 — Gao matching + greedy contamination-minimising pilots."""

    name = "Hybrid Gao+greedy"

    def __init__(self, seed: int | None = None) -> None:
        super().__init__(seed)
        self._matcher = MatchingBasedPilotAssignment(seed=seed)
        self.groups_: np.ndarray | None = None
        self.group_scores_: np.ndarray | None = None

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        result = self._matcher.match_users_to_aps(network, tau_p)
        self.groups_ = result.groups
        self.group_scores_ = result.group_scores
        return self._assign_pilots_greedy(
            result.groups, result.group_scores, tau_p, network.beta
        )

    def _assign_pilots_greedy(
        self,
        groups: np.ndarray,
        group_scores: np.ndarray,
        tau_p: int,
        beta: np.ndarray,
    ) -> np.ndarray:
        """Vectorised greedy contamination-min pilot selection.

        Incremental ``sum_per_pilot[p, m]`` keeps the per-AP β running sum
        for currently-assigned UEs on pilot ``p``. Contamination of UE k
        on pilot ``p`` is then ``β_k · sum_per_pilot[p]``, computed via a
        single matrix-vector product per UE — O(τ_p · M) per UE.
        """
        K, M = groups.shape[0], beta.shape[1]
        pilots = np.full(K, -1, dtype=int)
        sum_per_pilot = np.zeros((tau_p, M), dtype=beta.dtype)
        group_order = np.argsort(-group_scores)

        for ap in group_order:
            group = np.flatnonzero(groups[:, ap])
            if group.size == 0:
                continue
            occupied_pilots = pilots[group][pilots[group] >= 0]
            occupied = np.zeros(tau_p, dtype=bool)
            occupied[occupied_pilots] = True
            available_mask = ~occupied
            unassigned = group[pilots[group] < 0]
            if unassigned.size == 0:
                continue
            if available_mask.sum() < unassigned.size:
                raise RuntimeError("AP quota exceeded available pilots inside a Gao group.")
            order = self.rng.permutation(unassigned.size)
            for idx in order:
                ue = int(unassigned[idx])
                available_idx = np.flatnonzero(available_mask)
                if available_idx.size == 0:
                    break
                contam = sum_per_pilot[available_idx] @ beta[ue]  # (n_avail,)
                pick = int(available_idx[int(np.argmin(contam))])
                pilots[ue] = pick
                sum_per_pilot[pick] += beta[ue]
                available_mask[pick] = False

        missing = pilots < 0
        if np.any(missing):
            pilots[missing] = self.rng.integers(
                0, tau_p, size=int(np.sum(missing)), endpoint=False
            )
        return pilots
