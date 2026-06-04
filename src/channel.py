from __future__ import annotations

import numpy as np

from .network import Network


class ChannelEstimator:
    """MMSE large-scale channel-estimation variance from Gao Eq. (4)."""

    def __init__(self, pilot_power_w: float | None = None) -> None:
        self.pilot_power_w = pilot_power_w

    def gamma(self, network: Network, pilot_assignment: np.ndarray) -> np.ndarray:
        beta = network.beta
        assignment = np.asarray(pilot_assignment)
        pilot_power = network.config.pilot_power_w if self.pilot_power_w is None else self.pilot_power_w
        eta = np.full(network.num_ues, pilot_power, dtype=float)

        denominator = np.zeros_like(beta)
        for pilot in np.unique(assignment):
            users = assignment == pilot
            denominator[users, :] = eta[users, None] * 0.0 + np.sum(
                eta[users, None] * beta[users, :],
                axis=0,
                keepdims=True,
            )
        denominator = denominator + network.config.noise_power_w
        return eta[:, None] * beta**2 / denominator
