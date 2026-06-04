from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .channel import ChannelEstimator
from .network import Network


@dataclass
class SinrComponents:
    desired_gain: np.ndarray
    noise: np.ndarray
    noncoherent_interference: np.ndarray
    coherent_pilot_interference: np.ndarray

    @property
    def interference_matrix(self) -> np.ndarray:
        return self.noncoherent_interference + self.coherent_pilot_interference


def sinr_components(
    network: Network,
    pilot_assignment: np.ndarray,
    *,
    serving_mask: np.ndarray | None = None,
    estimator: ChannelEstimator | None = None,
) -> SinrComponents:
    estimator = ChannelEstimator() if estimator is None else estimator
    assignment = np.asarray(pilot_assignment)
    gamma = estimator.gamma(network, assignment)
    serving = network.all_serving_mask() if serving_mask is None else np.asarray(serving_mask, dtype=bool)
    effective_gamma = gamma * serving

    desired_gain = effective_gamma.sum(axis=1) ** 2
    noise = network.config.noise_power_w * effective_gamma.sum(axis=1)
    noncoherent = effective_gamma @ network.beta.T

    ratio_basis = effective_gamma / np.maximum(network.beta, 1e-300)
    coherent_raw = ratio_basis @ network.beta.T
    same_pilot = assignment[:, None] == assignment[None, :]
    coherent = coherent_raw**2 * same_pilot
    np.fill_diagonal(coherent, 0.0)
    return SinrComponents(desired_gain, noise, noncoherent, coherent)


def compute_sinr(
    network: Network,
    pilot_assignment: np.ndarray,
    powers_w: np.ndarray,
    *,
    serving_mask: np.ndarray | None = None,
) -> np.ndarray:
    powers = np.asarray(powers_w, dtype=float)
    components = sinr_components(network, pilot_assignment, serving_mask=serving_mask)
    denominator = components.noise + components.interference_matrix @ powers
    numerator = powers * components.desired_gain
    return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0)


def throughput_bps(network: Network, sinr: np.ndarray, tau_p: int) -> np.ndarray:
    prelog = max(0.0, 1.0 - tau_p / network.config.tau_c) / 2.0
    return network.config.bandwidth_hz * prelog * np.log2(1.0 + np.maximum(sinr, 0.0))


def per_ue_throughput_bps(
    network: Network,
    pilot_assignment: np.ndarray,
    powers_w: np.ndarray,
    tau_p: int,
    *,
    serving_mask: np.ndarray | None = None,
) -> np.ndarray:
    return throughput_bps(
        network,
        compute_sinr(network, pilot_assignment, powers_w, serving_mask=serving_mask),
        tau_p,
    )


def likely_95(values: np.ndarray) -> float:
    """95%-likely throughput: the 5th percentile of per-UE throughput."""

    return float(np.percentile(np.asarray(values), 5.0))


def cdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.sort(np.asarray(values))
    y = np.arange(1, x.size + 1, dtype=float) / x.size
    return x, y
