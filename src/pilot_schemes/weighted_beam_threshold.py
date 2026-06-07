"""MJH teammate's weighted-threshold beam-domain pilot assignment.

Generalisation of Mussbah Algorithm 1. The Mussbah binary conflict matrix
``B = B^(a)^T B^(a) + B^(a)^T B^(i) + B^(i)^T B^(a)`` becomes a weighted
matrix with separate weights for the active-active and active-moderate
overlap terms, plus a threshold to drop weak edges:

    W[i,j] = w_aa * (B^(a)^T B^(a))[i,j]
           + w_am * ((B^(a)^T B^(i)) + (B^(i)^T B^(a)))[i,j]
    A[i,j] = W[i,j] > threshold (i != j)

DSATUR coloring on the resulting adjacency. Two variants are supported:

- ``weighted-count``: integer counts of overlapping beams.
- ``weighted-power``: power-weighted, using ``sqrt(power)`` per beam to
  reduce the effect of very weak moderate beams.

(``w_aa=w_am=1, threshold=0, variant=count``) recovers the original
Mussbah Algorithm 1 binary conflict graph.

Reference implementation: ``MJH/beam_w_threshold.py:559-637`` (proposed_assignment)
and ``MJH/beam_w_threshold.py:487-547`` (build_weighted_beam_interference_*).
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme
from .beam_domain_mussbah import BeamDomainPilotAssignment


class WeightedBeamThresholdPilotAssignment(PilotAssignmentScheme):
    """MJH weighted-threshold beam-domain pilot assignment."""

    name = "Weighted-Threshold"

    def __init__(
        self,
        seed: int | None = None,
        *,
        delta: float = 0.95,
        w_aa: float = 2.0,
        w_am: float = 1.0,
        threshold: float = 0.0,
        variant: str = "weighted-count",
        adaptive_tau_p: bool = True,
        normalize_power_weights: bool = True,
    ) -> None:
        super().__init__(seed)
        self.delta = float(delta)
        self.w_aa = float(w_aa)
        self.w_am = float(w_am)
        self.threshold = float(threshold)
        if variant not in ("weighted-count", "weighted-power"):
            raise ValueError(
                f"variant must be 'weighted-count' or 'weighted-power', got {variant}"
            )
        self.variant = variant
        self.adaptive_tau_p = bool(adaptive_tau_p)
        self.normalize_power_weights = bool(normalize_power_weights)
        # Diagnostics:
        self.n_colors_used_: int | None = None
        self.adjacency_: np.ndarray | None = None
        # Reuse Mussbah's DSATUR coloring implementation
        self._dsatur_helper = BeamDomainPilotAssignment(seed=seed, delta=delta)

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        beam_info = getattr(network, "beam_info", None)
        if beam_info is None:
            raise NotImplementedError(
                "WeightedBeamThresholdPilotAssignment.assign requires a Network with "
                "multi-antenna beam-domain support (Network.beam_info)."
            )
        b_active, b_inactive = beam_info(delta=self.delta)
        self.reset()
        return self._assign_from_beam_info(network, b_active, b_inactive, tau_p)

    def _assign_from_beam_info(
        self,
        network: Network,
        b_active: np.ndarray,
        b_inactive: np.ndarray,
        tau_p: int,
    ) -> np.ndarray:
        """Build weighted interference + threshold + DSATUR coloring."""
        b_act = np.asarray(b_active, dtype=np.int32)  # (L=M*N, K)
        b_in = np.asarray(b_inactive, dtype=np.int32)

        if self.variant == "weighted-count":
            W = self._weighted_count_matrix(b_act, b_in)
        else:  # weighted-power
            W = self._weighted_power_matrix(network, b_act, b_in)

        np.fill_diagonal(W, 0.0)
        adjacency = W > self.threshold
        np.fill_diagonal(adjacency, False)
        self.adjacency_ = adjacency

        colors = self._dsatur_helper._dsatur_coloring(adjacency)
        self.n_colors_used_ = int(colors.max(initial=-1) + 1)
        return self._adapt_to_tau_p(colors, tau_p)

    def _weighted_count_matrix(
        self, b_act: np.ndarray, b_in: np.ndarray
    ) -> np.ndarray:
        """Count-based weighted interference (MJH Eq. ~weighted-count)."""
        Baa = (b_act.T @ b_act).astype(float)
        Bai = (b_act.T @ b_in).astype(float)
        Bia = (b_in.T @ b_act).astype(float)
        return self.w_aa * Baa + self.w_am * (Bai + Bia)

    def _weighted_power_matrix(
        self,
        network: Network,
        b_act: np.ndarray,
        b_in: np.ndarray,
    ) -> np.ndarray:
        """Power-weighted interference using sqrt(power) per beam."""
        if network.beam_powers is None:
            raise RuntimeError(
                "weighted-power variant needs network.beam_powers (multi-antenna)."
            )
        K, M, N = network.beam_powers.shape
        # (K, M, N) -> (L=M*N, K)
        P = network.beam_powers.reshape(K, M * N).T.astype(float)
        A = b_act.astype(float)  # (L, K)
        I = b_in.astype(float)
        if self.normalize_power_weights:
            denom = np.sum(P * (A + I), axis=0, keepdims=True) + 1e-300
            P = P / denom
        Pa = P * A
        Pi = P * I
        sqrt_Pa = np.sqrt(Pa)
        sqrt_Pi = np.sqrt(Pi)
        W = (
            self.w_aa * (sqrt_Pa.T @ sqrt_Pa)
            + self.w_am * (sqrt_Pa.T @ sqrt_Pi)
            + self.w_am * (sqrt_Pi.T @ sqrt_Pa)
        )
        return W

    def _adapt_to_tau_p(self, colors: np.ndarray, tau_p: int) -> np.ndarray:
        """Same logic as BeamDomainPilotAssignment: adaptive or modulo wrap."""
        if self.adaptive_tau_p:
            return colors.astype(int)
        max_color = int(colors.max(initial=-1)) + 1
        if max_color <= tau_p:
            return colors.astype(int)
        return (colors % tau_p).astype(int)
