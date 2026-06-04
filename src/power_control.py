from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .metrics import sinr_components
from .network import Network


class PowerControl(ABC):
    name: str = "base"

    @abstractmethod
    def compute(
        self,
        network: Network,
        pilot_assignment: np.ndarray,
        *,
        serving_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        """Return per-UE uplink data powers in Watt."""


class FullPowerControl(PowerControl):
    name = "Full power"

    def compute(
        self,
        network: Network,
        pilot_assignment: np.ndarray,
        *,
        serving_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        return np.full(network.num_ues, network.config.ue_max_power_w, dtype=float)


class FractionalPowerControl(PowerControl):
    """Simple fractional power control baseline.

    alpha=0 gives full power. alpha=1 allocates relatively more power to UEs
    with weaker aggregate large-scale fading.
    """

    name = "Fractional power"

    def __init__(self, alpha: float = 0.5) -> None:
        self.alpha = alpha

    def compute(
        self,
        network: Network,
        pilot_assignment: np.ndarray,
        *,
        serving_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        serving = network.all_serving_mask() if serving_mask is None else serving_mask
        large_scale = np.sum(network.beta * serving, axis=1)
        weights = np.maximum(large_scale, 1e-300) ** (-self.alpha)
        weights = weights / np.max(weights)
        return network.config.ue_max_power_w * weights


class MaxMinPowerControl(PowerControl):
    """Bisection max-min SINR power control for the fixed closed-form SINR."""

    name = "Max-min power"

    def __init__(self, tolerance: float = 1e-4, max_iterations: int = 60) -> None:
        self.tolerance = tolerance
        self.max_iterations = max_iterations

    def compute(
        self,
        network: Network,
        pilot_assignment: np.ndarray,
        *,
        serving_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        components = sinr_components(network, pilot_assignment, serving_mask=serving_mask)
        gain = np.maximum(components.desired_gain, 1e-300)
        interference = components.interference_matrix
        noise = components.noise
        p_max = network.config.ue_max_power_w

        low = 0.0
        high = self._initial_upper_bound(gain, interference, noise, p_max)
        best = np.full(network.num_ues, p_max, dtype=float)
        for _ in range(self.max_iterations):
            target = 0.5 * (low + high)
            feasible, powers = self._feasible(target, gain, interference, noise, p_max)
            if feasible:
                low = target
                best = powers
            else:
                high = target
            if high - low <= self.tolerance * max(1.0, high):
                break
        return np.clip(best, 0.0, p_max)

    def _initial_upper_bound(
        self,
        gain: np.ndarray,
        interference: np.ndarray,
        noise: np.ndarray,
        p_max: float,
    ) -> float:
        full = np.full(gain.shape, p_max, dtype=float)
        denom = noise + interference @ full
        sinr = np.divide(full * gain, denom, out=np.zeros_like(gain), where=denom > 0)
        return max(1e-6, float(np.max(sinr) * 2.0 + 1e-6))

    def _feasible(
        self,
        target: float,
        gain: np.ndarray,
        interference: np.ndarray,
        noise: np.ndarray,
        p_max: float,
    ) -> tuple[bool, np.ndarray]:
        f_matrix = target * interference / gain[:, None]
        u_vector = target * noise / gain
        try:
            powers = np.linalg.solve(np.eye(gain.size) - f_matrix, u_vector)
        except np.linalg.LinAlgError:
            return False, np.full(gain.shape, np.inf)
        feasible = np.all(np.isfinite(powers)) and np.all(powers >= -1e-12) and np.all(powers <= p_max + 1e-12)
        return bool(feasible), powers
