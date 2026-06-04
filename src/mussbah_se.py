"""Mussbah 2024 paper-faithful uplink SE computation (Monte Carlo).

Implements paper Eq. (3-9): pilot signal model, beam-domain MMSE channel
estimation, MRC combining, and empirical per-UE SINR / SE. Active beam
selection (Eq. 2) is provided externally via ``beam_info(delta)``.

Why Monte Carlo (over closed-form Eq. 10-14):

- Eq. (10-14) involve nested trace terms with cross-AP projections; an
  exact closed-form implementation is fragile to mis-index.
- An MC implementation directly samples channel realisations, builds the
  same pilot/data signals, runs the same MMSE/MRC pipeline, and averages
  empirical SINR. For ~50 channel realisations per setup the noise on
  the average SINR is small relative to large-scale variation across
  setups (which the outer 200 setups handle).
- MC also makes verification easier — each step matches a paper equation.

Function ``mussbah_uplink_se(network, pilots, n_channel_samples, delta, rng)``
returns per-UE SE values (one number per UE).
"""

from __future__ import annotations

import numpy as np

from .mussbah_channel import (
    beam_domain_channel,
    one_ring_covariance,
    sample_channel,
)
from .network import Network


def _geometric_angles(network: Network) -> np.ndarray:
    """Return geometric AoA (K, M) from UE to AP, wraparound-aware."""
    diff = network.ue_positions_m[:, None, :] - network.ap_positions_m[None, :, :]
    diff = (
        (diff + network.config.area_size_m / 2.0) % network.config.area_size_m
    ) - network.config.area_size_m / 2.0
    theta = np.arctan2(diff[..., 1], diff[..., 0])
    if network.ap_rotations_rad is not None:
        theta = theta - network.ap_rotations_rad[None, :]
    return theta


def mussbah_uplink_se(
    network: Network,
    pilots: np.ndarray,
    *,
    n_channel_samples: int = 20,
    tau_p_length: int | None = None,
    delta: float = 0.95,
    rician_k_db: float = 10.0,
    one_ring_radius_m: float | None = None,
    rng: np.random.Generator | None = None,
    uplink_powers_w: np.ndarray | None = None,
) -> np.ndarray:
    """Compute Mussbah paper-faithful uplink SE per UE (Eq. 8) via MC.

    Parameters
    ----------
    network : Network
        Must have ``num_antennas_per_ap > 1`` and ``beam_powers`` populated.
    pilots : (K,) int
        Pilot index assigned to each UE.
    n_channel_samples : int
        Number of small-scale channel realisations per setup.
    tau_p_length : int or None
        Pilot sequence length used for pilot noise variance and prelog. None
        uses ``max(pilots) + 1``. Set this to the design budget for fixed-budget
        sanity checks where an adaptive assignment leaves some pilots unused.
    delta : float
        Active beam threshold in Eq. 2.
    rician_k_db, one_ring_radius_m :
        Channel model parameters. ``one_ring_radius_m`` defaults to
        ``network.config.one_ring_radius_m``.
    rng : np.random.Generator
    uplink_powers_w : (K,) or None
        Per-UE uplink data power. None → uniform 0.1 W.

    Returns
    -------
    se_per_ue : (K,) float — SE in bit/s/Hz.
    """
    if network.beam_powers is None:
        raise RuntimeError("mussbah_uplink_se requires a multi-antenna Network.")

    cfg = network.config
    K_arr = network.num_ues
    M = network.num_aps
    N = network.num_antennas_per_ap
    rng = np.random.default_rng() if rng is None else rng
    r_ring = (
        cfg.one_ring_radius_m if one_ring_radius_m is None else float(one_ring_radius_m)
    )
    if r_ring <= 0.0:
        raise ValueError("Mussbah SE requires one_ring_radius_m > 0 (paper default 30 m).")

    pilots = np.asarray(pilots, dtype=int)
    # Pilot sequence length for pilot signal model and the (τ_c - τ_p)/τ_c
    # training-overhead factor. By default, use max index + 1 so adaptive
    # schemes expose their actual pilot count. For fixed-budget sanity checks,
    # pass tau_p_length explicitly so unused pilot sequences still count toward
    # training overhead and pilot observation length.
    #
    # NOTE: Mussbah paper §V.A claims 92% of Mussbah's advantage comes from
    # reduced training overhead when chromatic < τ_p. Capturing that requires
    # adaptive τ_p per scheme + scheme-specific overhead factors. In our
    # current environment (Ngo 2017 path loss instead of 3GPP UMa) the
    # chromatic number on Mussbah's beam-overlap graph exceeds 10 for the
    # K=30 setting, so Mussbah's adaptive τ_p advantage cannot materialise
    # in this reproduction without further channel-model upgrades.
    tau_p_observed = max(int(pilots.max()) + 1, 1)
    if tau_p_length is None:
        tau_p = tau_p_observed
    else:
        tau_p = int(tau_p_length)
        if tau_p < tau_p_observed:
            raise ValueError(
                f"tau_p_length={tau_p} is smaller than max(pilots)+1={tau_p_observed}."
            )
    tau_c = cfg.tau_c
    sigma2 = cfg.noise_power_w
    pilot_power = cfg.pilot_power_w
    if uplink_powers_w is None:
        uplink_powers = np.full(K_arr, cfg.ue_max_power_w, dtype=float)
    else:
        uplink_powers = np.asarray(uplink_powers_w, dtype=float)

    # ----- Channel covariance + LoS mean (deterministic per setup) -----
    theta_geom = _geometric_angles(network)
    mu, cov = one_ring_covariance(
        network.beta,
        theta_geom,
        network.distances_m,
        num_antennas=N,
        one_ring_radius_m=r_ring,
        rician_k_db=rician_k_db,
    )
    # Beam-domain LoS mean and covariance
    F = np.exp(-2j * np.pi * np.outer(np.arange(N), np.arange(N)) / N) / np.sqrt(N)
    # mu_beam (K, M, N) = U^H mu (apply F.conj().T along last)
    mu_beam = np.einsum("nl,kml->kmn", F.conj(), mu)
    # cov_beam (K, M, N, N) = U^H C U
    cov_beam = np.einsum("an,kmnp,pb->kmab", F.conj(), cov, F)

    # ----- Active beam set per (UE, AP) ------
    # network.beam_info returns L=M*N × K flattened. Reshape to (K, M, N) bool.
    b_active_flat, _ = network.beam_info(delta=delta)
    is_active = b_active_flat.T.astype(bool).reshape(K_arr, M, N)
    # A_k = APs with at least one active beam for UE k
    ap_in_A_k = is_active.any(axis=2)  # (K, M)

    # ----- Monte Carlo over channel realisations ----
    se_acc = np.zeros(K_arr, dtype=float)

    for sample in range(n_channel_samples):
        # Element-domain channel (K, M, N)
        h_element = sample_channel(mu, cov, rng)
        # Beam-domain channel
        h_beam = beam_domain_channel(h_element, N)  # (K, M, N)

        # ---- Pilot phase ----
        # In beam domain at AP m: y^B_{p,m} = Σ_k √(τ_p ρ^p) h_beam[k, m] · φ_{p_k}^H + noise
        # After multiplying y^B_{p,m} · φ_{p_k} / sqrt(τ_p ρ^p), we get:
        #   y_p,k,m = h_beam[k, m] + Σ_{i ≠ k, p_i = p_k} h_beam[i, m] + n', n' ~ CN(0, σ_n²/(τ_p ρ^p) · I)
        # Build for each (k, m): y_p,k,m (shape N).
        noise_var_pilot = sigma2 / (tau_p * pilot_power)

        # Group UEs by pilot
        y_p = np.zeros((K_arr, M, N), dtype=np.complex128)
        for p in range(tau_p):
            users_p = np.flatnonzero(pilots == p)
            if users_p.size == 0:
                continue
            # Sum of all same-pilot channels at each AP
            sum_h_beam_p = h_beam[users_p].sum(axis=0)  # (M, N)
            noise = (
                rng.standard_normal(size=(M, N))
                + 1j * rng.standard_normal(size=(M, N))
            ) * np.sqrt(noise_var_pilot / 2.0)
            # Each user k in users_p gets y_p,k,m = sum_h_beam_p + noise
            for k in users_p:
                y_p[k] = sum_h_beam_p + noise

        # ---- MMSE estimate per (k, m), per active beam ----
        # For active beam b in B^(a)_{k,m}:
        #   ĥ^B_{k,m,b} = μ_beam[k,m,b] + cov_beam_diag · (y_p[k,m,b] - mean_y_p) / var_y_p
        # mean_y_p = Σ_{i: p_i = p_k} μ_beam[i, m, b]
        # var_y_p = Σ_{i: p_i = p_k} cov_beam_diag[i, m, b] + noise_var_pilot
        # We use diagonal covariance (independent per-beam) as a simplification
        # for the MMSE estimate — the off-diagonals of cov_beam are small for
        # one-ring channels with moderate Δ.
        cov_beam_diag = np.diagonal(cov_beam, axis1=-2, axis2=-1).real  # (K, M, N)
        # For each pilot group, compute mean_mu_per_pilot (M, N), var_per_pilot (M, N)
        h_hat_beam = np.zeros((K_arr, M, N), dtype=np.complex128)
        for p in range(tau_p):
            users_p = np.flatnonzero(pilots == p)
            if users_p.size == 0:
                continue
            mu_sum_p = mu_beam[users_p].sum(axis=0)  # (M, N)
            cov_sum_p = cov_beam_diag[users_p].sum(axis=0)  # (M, N)
            denom = cov_sum_p + noise_var_pilot  # (M, N)
            for k in users_p:
                gain = cov_beam_diag[k] / np.maximum(denom, 1e-30)  # (M, N)
                h_hat_beam[k] = mu_beam[k] + gain * (y_p[k] - mu_sum_p)

        # Zero out inactive beams in the estimate (we don't use them for MRC)
        h_hat_beam = h_hat_beam * is_active  # (K, M, N) elementwise mask

        # ---- Empirical MRC SINR ----
        # MRC combining vector v_{k,l} = ĥ_{k,l} (beam-domain, on active beams only).
        # Received signal at AP l from a unit-power data symbol from user i:
        #   s_{l, i} = ĥ_{k,l}^H · h_beam[i, l] (active beams only)
        # SINR_k = |Σ_l √ρ_k · ĥ_{k,l}^H · h_beam[k, l]|²
        #        / (Σ_i ρ_i |Σ_l ĥ_{k,l}^H · h_beam[i, l]|²
        #           - ρ_k |Σ_l ĥ_{k,l}^H · h_beam[k, l]|²
        #           + σ_n² Σ_l ||ĥ_{k,l}||²)
        # Compute per-realisation SINR; final SE will be log2(1 + mean SINR).

        # Σ_l ĥ_{k,l}^H · h_beam[i, l] for each (k, i) — sum only over active l of k
        # Active beams masked already, so dot product just sums.
        # Shape (K, K): combined_signal[k, i] = Σ_{l, n in active(k,l)} conj(ĥ_{k,l,n}) · h_beam[i,l,n]
        combined = np.einsum("kln,iln->ki", h_hat_beam.conj(), h_beam)
        # Per-UE SINR
        sqrt_p = np.sqrt(uplink_powers)
        numer = uplink_powers * np.abs(np.diagonal(combined)) ** 2  # ρ_k |s_{k,k}|²
        # Σ_i ρ_i |s_{k,i}|²
        all_terms = uplink_powers[None, :] * np.abs(combined) ** 2  # (K, K)
        sum_terms = all_terms.sum(axis=1)  # (K,)
        # Noise term: σ² Σ_l ||ĥ_{k,l}||² (over active beams)
        noise_term = sigma2 * (np.abs(h_hat_beam) ** 2).sum(axis=(1, 2))  # (K,)
        denom = sum_terms - numer + noise_term
        sinr = numer / np.maximum(denom, 1e-30)
        se = (tau_c - tau_p) / tau_c * np.log2(1.0 + sinr)
        se_acc += se

    se_acc /= n_channel_samples
    return se_acc
