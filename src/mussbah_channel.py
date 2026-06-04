"""Mussbah 2024 paper-faithful multi-antenna channel model.

Implements:

- One-ring NLoS spatial covariance C_{k,l} ∈ C^{N×N} (Shiu 2000, radius 30 m).
- Rician LoS mean μ_{k,l} ∈ C^N from geometric angle.
- Channel realisation: ``h_{k,l} ~ CN(μ_{k,l}, C_{k,l})``.

Channel parameterisation (Mussbah Eq. 1 and one-ring assumption from §V):

- LoS component (per UE-AP link, K-factor 10 dB by default):
    ``h^LoS_{k,l} = sqrt(β_{k,l} · K_R / (K_R+1)) · a(θ_geom)``
  where ``a(θ)`` is the ULA steering vector ``a_n(θ) = exp(jπ n sin θ)``.
- NLoS covariance (one-ring, radius r):
    ``C_{k,l} = (β_{k,l} / (K_R+1)) · (1/(2Δ)) ∫_{-Δ}^{+Δ} a(θ+δ) a(θ+δ)^H dδ``
  with half-spread ``Δ = arctan(r / d_{k,l})``.

Beam-domain transform (Eq. 1): ``U^H h_{k,l}`` with ``U`` = N-point DFT.
"""

from __future__ import annotations

import numpy as np


def steering_vector(theta: np.ndarray, num_antennas: int) -> np.ndarray:
    """ULA half-wavelength steering vector.

    Parameters
    ----------
    theta : array of arbitrary shape (...,)
        AoA in radians.
    num_antennas : int

    Returns
    -------
    a : complex array of shape (..., N)
    """
    theta = np.asarray(theta)
    n = np.arange(num_antennas)
    phases = np.pi * np.sin(theta[..., None]) * n
    return np.exp(1j * phases)


def one_ring_covariance(
    beta: np.ndarray,
    theta_geom: np.ndarray,
    distances_m: np.ndarray,
    *,
    num_antennas: int,
    one_ring_radius_m: float,
    rician_k_db: float = 10.0,
    num_quadrature: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute one-ring NLoS covariance and LoS mean (both in element domain).

    Returns
    -------
    mu : complex array (K, M, N) — LoS mean. ``||μ||² = β · K/(K+1)``.
    cov : complex array (K, M, N, N) — NLoS covariance. ``tr(cov) = β / (K+1)``.
    """
    K_arr, M = beta.shape
    N = int(num_antennas)
    K_R = 10.0 ** (rician_k_db / 10.0)
    los_frac = K_R / (K_R + 1.0)
    nlos_frac = 1.0 / (K_R + 1.0)

    delta_half = np.arctan(one_ring_radius_m / np.maximum(distances_m, 1e-6))
    delta_half = np.minimum(delta_half, np.pi / 2)

    a_geom = steering_vector(theta_geom, N)  # (K, M, N)
    mu = np.sqrt(beta * los_frac)[..., None] * a_geom  # (K, M, N)

    # Quadrature points uniformly in [-1, 1], midpoint rule
    q = np.linspace(-1.0, 1.0, num_quadrature, endpoint=False)
    q = q + (q[1] - q[0]) / 2.0
    angles = theta_geom[..., None] + delta_half[..., None] * q[None, None, :]
    a_q = steering_vector(angles, N)  # (K, M, Q, N)
    # cov = β·(1/(K+1))·(1/Q) Σ_q a a^H
    cov = np.einsum("kmqn,kmqp->kmnp", a_q, a_q.conj()) / num_quadrature
    cov = (beta * nlos_frac)[..., None, None] * cov

    return mu.astype(np.complex128), cov.astype(np.complex128)


def sample_channel(
    mu: np.ndarray,
    cov: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw one channel realisation per (UE, AP): ``h_{k,m} ~ CN(μ_{k,m}, C_{k,m})``.

    Uses eigenvalue decomposition for the principal square root.
    """
    K_arr, M, N = mu.shape
    eigvals, eigvecs = np.linalg.eigh(cov)
    eigvals = np.clip(eigvals, 0.0, None)
    sqrt_diag = np.sqrt(eigvals)
    w_re = rng.standard_normal(size=(K_arr, M, N))
    w_im = rng.standard_normal(size=(K_arr, M, N))
    w = (w_re + 1j * w_im) / np.sqrt(2.0)
    w_scaled = sqrt_diag * w
    h_nlos = np.einsum("kmnp,kmp->kmn", eigvecs, w_scaled)
    return mu + h_nlos


def beam_domain_channel(
    h_element: np.ndarray,
    num_antennas: int,
) -> np.ndarray:
    """Apply N-point DFT to each (UE, AP)'s element-domain channel.

    Eq.(1): ``h^(B)_{k,l} = U^H h_{k,l}``.
    """
    n = np.arange(num_antennas)
    F = np.exp(-2j * np.pi * np.outer(n, n) / num_antennas) / np.sqrt(num_antennas)
    return np.einsum("nl,kml->kmn", F.conj(), h_element)
