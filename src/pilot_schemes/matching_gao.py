from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


@dataclass
class MatchingResult:
    groups: np.ndarray
    group_scores: np.ndarray


class MatchingBasedPilotAssignment(PilotAssignmentScheme):
    """Gao et al. Algorithms 1 and 2.

    Current experiment convention: the matching output is retained as pilot
    groups for Algorithm 2, while throughput evaluation uses the base-class
    all-AP serving mask. Gao's text also describes Algorithm 1 as AP
    selection, so this convention should be reported as a modeling choice
    and checked with a matched-serving sensitivity run before final claims.
    """

    name = "Gao matching"

    def __init__(
        self,
        seed: int | None = None,
        *,
        ue_quota: int | None = None,
        ap_quota: int | None = None,
        serving_policy: str = "all_ap",
    ) -> None:
        super().__init__(seed)
        self.ue_quota = ue_quota
        self.ap_quota = ap_quota
        if serving_policy not in {"all_ap", "matched"}:
            raise ValueError("serving_policy must be 'all_ap' or 'matched'.")
        self.serving_policy = serving_policy
        if serving_policy == "matched":
            self.name = "Gao matching (matched serving)"
        self.groups_: np.ndarray | None = None
        self.group_scores_: np.ndarray | None = None

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        result = self.match_users_to_aps(network, tau_p)
        self.groups_ = result.groups
        self.group_scores_ = result.group_scores
        if self.serving_policy == "matched":
            self.serving_matrix_ = result.groups
        return self.assign_pilots_from_groups(result.groups, result.group_scores, tau_p)

    def match_users_to_aps(self, network: Network, tau_p: int) -> MatchingResult:
        beta = network.beta
        m_count, k_count = beta.shape
        q_ap = tau_p if self.ap_quota is None else self.ap_quota
        q_ue = k_count if self.ue_quota is None else self.ue_quota
        q_ap = int(np.clip(q_ap, 1, m_count))
        q_ue = int(np.clip(q_ue, 1, k_count))

        ue_preferences = [list(row) for row in np.argsort(-beta, axis=1)]
        ap_rank = np.empty((k_count, m_count), dtype=int)
        for ap in range(k_count):
            ranked_users = np.argsort(-beta[:, ap])
            ap_rank[ap, ranked_users] = np.arange(m_count)

        matching = np.zeros((m_count, k_count), dtype=bool)
        free_users = set(range(m_count))
        while free_users:
            proposals: list[list[int]] = [[] for _ in range(k_count)]
            for ue in list(free_users):
                if matching[ue].sum() >= q_ue or not ue_preferences[ue]:
                    continue
                ap = ue_preferences[ue].pop(0)
                proposals[ap].append(ue)

            if not any(proposals):
                break

            for ap, proposed_users in enumerate(proposals):
                if not proposed_users:
                    continue
                current_users = np.flatnonzero(matching[:, ap]).tolist()
                candidates = np.array(sorted(set(current_users + proposed_users)), dtype=int)
                if candidates.size <= q_ap:
                    accepted = candidates
                else:
                    order = np.argsort(ap_rank[ap, candidates])
                    accepted = candidates[order[:q_ap]]
                matching[:, ap] = False
                matching[accepted, ap] = True

            for ue in list(free_users):
                if matching[ue].sum() >= q_ue or not ue_preferences[ue]:
                    free_users.remove(ue)

        group_scores = common_serving_ap_scores(matching)
        return MatchingResult(matching, group_scores)

    def assign_pilots_from_groups(
        self,
        groups: np.ndarray,
        group_scores: np.ndarray,
        tau_p: int,
    ) -> np.ndarray:
        pilots = np.full(groups.shape[0], -1, dtype=int)
        group_order = np.argsort(-group_scores)
        total_pilots = np.arange(tau_p, dtype=int)

        for ap in group_order:
            group = np.flatnonzero(groups[:, ap])
            if group.size == 0:
                continue
            occupied = set(pilots[group][pilots[group] >= 0].tolist())
            available = [pilot for pilot in total_pilots.tolist() if pilot not in occupied]
            unassigned = [ue for ue in group.tolist() if pilots[ue] < 0]
            if not unassigned:
                continue
            if len(available) < len(unassigned):
                raise RuntimeError("AP quota exceeded available pilots inside a Gao group.")
            chosen = self.rng.choice(available, size=len(unassigned), replace=False)
            pilots[np.array(unassigned, dtype=int)] = chosen

        missing = pilots < 0
        if np.any(missing):
            pilots[missing] = self.rng.integers(0, tau_p, size=int(np.sum(missing)), endpoint=False)
        return pilots


def common_serving_ap_scores(groups: np.ndarray) -> np.ndarray:
    """Compute Gao Eq. (9)-(10) group scores for each AP group."""

    matched = np.asarray(groups, dtype=bool)
    m_count, k_count = matched.shape
    match_counts = matched.sum(axis=1)
    common_counts = matched.astype(int) @ matched.astype(int).T
    denominator = np.maximum(match_counts, 1)[:, None]
    pair_ratio = common_counts / denominator
    np.fill_diagonal(pair_ratio, 0.0)

    scores = np.zeros(k_count, dtype=float)
    for ap in range(k_count):
        group = np.flatnonzero(matched[:, ap])
        if group.size > 1:
            scores[ap] = pair_ratio[np.ix_(group, group)].sum()
    return scores
