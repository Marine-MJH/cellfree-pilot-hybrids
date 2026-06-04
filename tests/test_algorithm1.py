from __future__ import annotations

import numpy as np

from src.config import SimulationConfig
from src.network import Network
from src.pilot_schemes.matching_gao import MatchingBasedPilotAssignment


def toy_network() -> Network:
    config = SimulationConfig(num_aps=3, num_ues=3, tau_p=2, shadow_std_db=0.0)
    beta = np.array(
        [
            [10.0, 8.0, 1.0],
            [9.0, 7.0, 8.0],
            [1.0, 1.0, 10.0],
        ]
    )
    positions = np.zeros((3, 2))
    return Network(config, positions, positions, np.ones((3, 3)), beta, 10 * np.log10(beta))


def test_matching_respects_ap_quota_and_serves_users() -> None:
    network = toy_network()
    scheme = MatchingBasedPilotAssignment(seed=1)
    result = scheme.match_users_to_aps(network, tau_p=2)

    assert np.all(result.groups.sum(axis=0) <= 2)
    assert np.all(result.groups.sum(axis=1) >= 1)


def test_pilot_assignment_is_orthogonal_inside_toy_groups() -> None:
    network = toy_network()
    scheme = MatchingBasedPilotAssignment(seed=1)
    pilots = scheme.assign(network, tau_p=2)
    groups = scheme.groups_
    assert groups is not None

    for ap in range(network.num_aps):
        group = np.flatnonzero(groups[:, ap])
        assert len(np.unique(pilots[group])) == len(group)


def test_serving_mask_defaults_to_all_aps_for_sinr() -> None:
    """Current experiment convention: matching output is used for pilot
    grouping, while the simulator evaluates throughput with all-AP serving.
    PROGRESS.md records the remaining serving-set interpretation risk."""

    network = toy_network()
    scheme = MatchingBasedPilotAssignment(seed=1)
    scheme.assign(network, tau_p=2)
    serving = scheme.serving_matrix(network)
    assert serving.shape == (network.num_ues, network.num_aps)
    assert bool(serving.all())


def test_matched_serving_policy_uses_matching_groups() -> None:
    network = toy_network()
    scheme = MatchingBasedPilotAssignment(seed=1, serving_policy="matched")
    scheme.assign(network, tau_p=2)
    serving = scheme.serving_matrix(network)

    assert scheme.groups_ is not None
    assert np.array_equal(serving, scheme.groups_)
