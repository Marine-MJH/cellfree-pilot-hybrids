from __future__ import annotations

import numpy as np

from src.config import SimulationConfig
from src.metrics import compute_sinr, sinr_components, throughput_bps
from src.network import Network
from src.power_control import MaxMinPowerControl


def small_network(beta: np.ndarray) -> Network:
    m, k = beta.shape
    config = SimulationConfig(num_aps=k, num_ues=m, tau_p=m, shadow_std_db=0.0)
    return Network(config, np.zeros((k, 2)), np.zeros((m, 2)), np.ones((m, k)), beta, 10 * np.log10(beta))


def test_single_ue_sinr_is_positive() -> None:
    network = small_network(np.array([[1e-9, 2e-9]]))
    sinr = compute_sinr(network, np.array([0]), np.array([network.config.ue_max_power_w]))
    assert sinr.shape == (1,)
    assert sinr[0] > 0


def test_orthogonal_pilots_remove_coherent_pilot_interference() -> None:
    network = small_network(np.array([[1e-9, 2e-9], [2e-9, 1e-9]]))
    components = sinr_components(network, np.array([0, 1]))
    assert np.allclose(components.coherent_pilot_interference, 0.0)


def test_throughput_goes_to_zero_when_tau_p_reaches_tau_c() -> None:
    network = small_network(np.array([[1e-9]]))
    throughput = throughput_bps(network, np.array([10.0]), tau_p=network.config.tau_c)
    assert np.allclose(throughput, 0.0)


def test_max_min_power_control_returns_feasible_bounds() -> None:
    network = small_network(np.array([[1e-9, 2e-9], [2e-9, 1e-9]]))
    powers = MaxMinPowerControl().compute(network, np.array([0, 1]))

    assert powers.shape == (2,)
    assert np.all(powers >= 0.0)
    assert np.all(powers <= network.config.ue_max_power_w)


def test_max_min_power_control_equalizes_sinr() -> None:
    network = small_network(np.array([[1e-9, 3e-9], [4e-9, 1e-9], [2e-9, 2e-9]]))
    assignment = np.array([0, 1, 0])
    powers = MaxMinPowerControl(tolerance=1e-5, max_iterations=80).compute(network, assignment)
    sinr = compute_sinr(network, assignment, powers)

    assert np.max(sinr) - np.min(sinr) < 1e-4
