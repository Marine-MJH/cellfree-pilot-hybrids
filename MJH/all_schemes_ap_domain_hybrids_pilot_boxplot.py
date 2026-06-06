#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
코드 사용법

python .\all_schemes_reproduce.py --mode all --setups 200 --plot --outdir all_scheme_results
python .\all_schemes_reproduce.py --mode fig1 --setups 10 --plot --beam-detect-snr-db 20 --outdir test_threshold
여기서 --mode를
1. fig1
2. sweep-n
3. sweep-k
4. all
4개 중 하나를 고를 수 있다.

또한, 만약 pilot 수가 너무 많아 threshold를 높여서 report 되는 beam 수를 줄이려면
--beam-detect-snr-db 20 과 같이 추가하면 된다.
"""


"""
All-scheme simulator for:
  Beam-Domain-Based Pilot Assignment for Energy Efficient Cell-Free Massive MIMO

Implemented schemes:
  proposed : Weighted-threshold beam-domain active/moderate beam graph + DSATUR, adaptive tau_p.
  random   : Largest-large-scale-fading AP selection + random fixed pilots.
  greedy   : Largest-large-scale-fading AP selection + Ngo-style greedy fixed-pilot refinement.
  gc       : AP-overlap graph coloring baseline with fixed tau_p.
  wgf      : Weighted graph framework baseline, approximated as greedy Max-k-Cut with fixed tau_p.
  matching-fixed    : AP-beam-resource many-to-many matching + weighted-threshold overlap + fixed tau_p.
  matching-adaptive : AP-beam-resource many-to-many matching + weighted-threshold overlap + adaptive tau_p.

Additional AP-domain hybrids in this variant:
  topap-bisect       : Top-N strongest-AP overlap graph + N-bisection + fixed tau_p.
  h2-gao-greedy      : AP-domain Gao-style matching + beta-dot-beta greedy pilot choice.
  h3-topap-adaptive  : Top-8 AP overlap graph + quota-free coloring + adaptive actual tau_p.
  h4-topap-greedy    : TopAP conflict graph + fixed-budget beta-dot-beta greedy pilot choice.

Reproduction caveat:
  The beam-domain letter gives only high-level descriptions of GC/WGF AP-selection details and
  refers to [2], [3]. Since those reference papers are not embedded here, GC/WGF AP selection and
  WGF edge weights are implemented according to the descriptions in the letter: AP-overlap graph
  and weighted potential pilot-contamination graph. The exact results can differ from the authors'
  implementation if [2]/[3] use different AP-selection/weight definitions.

What is close to the beam-domain paper:
  - Proposed Algorithm 1: Eq. (2), weighted Eq. (15)-(18), DSATUR, adaptive tau_p.
  - Fixed tau_p=10 for Random/Greedy/WGF/GC.
  - MRC closed-form SINR structure of Eq. (9)-(14).
  - Max-min uplink data power control with max 200 mW.
  - RF-chain count: proposed uses active beam union; baselines use all N RF chains at active APs.

Dependencies:
  pip install numpy matplotlib scipy

Examples:
  python all_schemes_reproduce.py --mode fig1 --setups 20 --plot
  python all_schemes_reproduce.py --mode sweep-n --setups 20 --plot
  python all_schemes_reproduce.py --mode sweep-k --setups 20 --plot
  python all_schemes_reproduce.py --mode all --setups 200 --plot
"""

import argparse
import csv
import os
import hashlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

try:
    from scipy.optimize import minimize
except Exception:  # pragma: no cover
    minimize = None


# =============================================================================
# Basic utilities
# =============================================================================


def db2lin(x_db: float | np.ndarray) -> float | np.ndarray:
    return 10.0 ** (np.asarray(x_db) / 10.0)


def lin2db(x: float | np.ndarray) -> float | np.ndarray:
    return 10.0 * np.log10(np.maximum(np.asarray(x), 1e-300))


def complex_normal(rng: np.random.Generator, shape: Tuple[int, ...], variance: float = 1.0) -> np.ndarray:
    return np.sqrt(variance / 2.0) * (rng.standard_normal(shape) + 1j * rng.standard_normal(shape))


def stable_seed(*items: object) -> int:
    """Deterministic 32-bit seed helper independent of RNG consumption order."""
    raw = "|".join(str(x) for x in items).encode("utf-8")
    return int(hashlib.blake2b(raw, digest_size=4).hexdigest(), 16)


def dft_matrix(n: int) -> np.ndarray:
    row = np.arange(n)[:, None]
    col = np.arange(n)[None, :]
    return np.exp(1j * 2.0 * np.pi * row * col / n) / np.sqrt(n)


def ula_steering_vector(n_ant: int, angle_rad: float, d_over_lambda: float = 0.5) -> np.ndarray:
    m = np.arange(n_ant)
    return np.exp(1j * 2.0 * np.pi * d_over_lambda * m * np.sin(angle_rad))


def wraparound_delta(from_xy: np.ndarray, to_xy: np.ndarray, side_m: float) -> np.ndarray:
    delta = to_xy - from_xy
    delta -= side_m * np.round(delta / side_m)
    return delta


def umi_los_probability(d2d_m: float) -> float:
    d = max(float(d2d_m), 1e-6)
    if d <= 18.0:
        return 1.0
    return min(18.0 / d, 1.0) * (1.0 - np.exp(-d / 36.0)) + np.exp(-d / 36.0)


def pathloss_umi_approx_db(
    d2d_m: float,
    d3d_m: float,
    fc_ghz: float,
    los: bool,
    ap_height_m: float,
    ue_height_m: float,
    rng: np.random.Generator,
    shadowing: bool = True,
) -> float:
    """UMi-like pathloss approximation; not a full TR 38.901 implementation."""
    d1 = max(float(d3d_m), 1.0)
    d2 = max(float(d2d_m), 10.0)
    carrier_hz = fc_ghz * 1e9
    c0 = 299792458.0
    h_bs_eff = max(ap_height_m - 1.0, 0.1)
    h_ut_eff = max(ue_height_m - 1.0, 0.1)
    breakpoint_distance = 4.0 * h_bs_eff * h_ut_eff * carrier_hz / c0

    pl_los_1 = 32.4 + 21.0 * np.log10(d1) + 20.0 * np.log10(fc_ghz)
    pl_los_2 = (
        32.4
        + 40.0 * np.log10(d1)
        + 20.0 * np.log10(fc_ghz)
        - 9.5 * np.log10(breakpoint_distance**2 + (ap_height_m - ue_height_m) ** 2)
    )
    pl_los = pl_los_1 if d2 <= breakpoint_distance else pl_los_2
    pl_nlos = 35.3 * np.log10(d1) + 22.4 + 21.3 * np.log10(fc_ghz) - 0.3 * (ue_height_m - 1.5)

    if los:
        pl = pl_los
        sigma_sf = 4.0
    else:
        pl = max(pl_los, pl_nlos)
        sigma_sf = 7.82
    if shadowing:
        pl += rng.normal(0.0, sigma_sf)
    return float(pl)


def one_ring_covariance_approx(n_ant: int, mean_angle: float, angular_spread: float, n_samples: int = 31) -> np.ndarray:
    if n_ant == 1:
        return np.ones((1, 1), dtype=np.complex128)
    angles = np.linspace(mean_angle - angular_spread, mean_angle + angular_spread, n_samples)
    r = np.zeros((n_ant, n_ant), dtype=np.complex128)
    for th in angles:
        a = ula_steering_vector(n_ant, th)
        r += np.outer(a, a.conj())
    r /= n_samples
    tr = np.real(np.trace(r))
    if tr > 0:
        r *= n_ant / tr
    return 0.5 * (r + r.conj().T)


# =============================================================================
# Dataclasses
# =============================================================================


@dataclass
class SimConfig:
    L: int = 100
    K: int = 30
    N: int = 8
    area_side_m: float = 1000.0
    ap_height_m: float = 10.0
    ue_height_m: float = 1.5
    fc_ghz: float = 5.0
    bandwidth_hz: float = 20e6
    tau_c: int = 100
    coherence_time_s: float = 1e-3
    rho_p_watt: float = 200e-3
    rho_data_max_watt: float = 200e-3
    rician_k_los_db: float = 10.0
    one_ring_radius_m: float = 30.0
    delta_active_percent: float = 95.0
    beam_detect_snr_db: float = 0.0
    n_scatter_angles: int = 31
    seed: int = 7

    # Baseline settings from the beam-domain paper.
    baseline_tau_p: int = 10
    greedy_iters: int = 8
    greedy_seed_offset: int = 13
    wgf_refine_iters: int = 8

    # Weighted-threshold beam-overlap graph settings.
    # Original beam-domain proposed is recovered with w_aa=w_ai=w_ia=1 and edge_threshold=0.
    w_aa: float = 1.0  # active-active beam overlap weight
    w_ai: float = 1.0  # active-moderate beam overlap weight
    w_ia: float = 1.0  # moderate-active beam overlap weight
    edge_threshold: float = 0.0  # create edge if weighted overlap > edge_threshold

    # Beam-domain many-to-many matching settings.
    matching_resource_quota: int = 0  # 0 means use baseline_tau_p

    # AP-domain hybrid settings. Existing schemes ignore these fields.
    topap_top_n: int = 10
    h3_topap_n: int = 8
    topap_bisect_min: int = 2
    topap_bisect_max: int = 40
    topap_bisect_iters: int = 20

    # Power control and power model.
    power_control: str = "maxmin"  # maxmin or full
    maxmin_maxiter: int = 250
    maxmin_restarts: int = 2
    power_model: str = "ref12-rf"  # ref12-rf, ref12-strict, simple
    fronthaul_mode: str = "active_users"  # all_users, active_users, active_rf
    pa_efficiency_zeta: float = 0.3
    p_fix_watt: float = 0.825
    p_user_watt: float = 0.1
    p_backhaul_traffic_watt: float = 1.0
    c_backhaul_bps: float = 100e6
    quant_bits_alpha: int = 2
    p_rf_chain_watt: float = 0.04

    @property
    def noise_power_watt(self) -> float:
        k_b = 1.380649e-23
        t0 = 290.0
        return k_b * t0 * self.bandwidth_hz


@dataclass
class ChannelStats:
    ap_pos: np.ndarray
    ue_pos: np.ndarray
    mu_h: np.ndarray
    cov_h: np.ndarray
    mu_b: np.ndarray
    cov_b: np.ndarray
    beam_power: np.ndarray
    beta_large_scale: np.ndarray
    los: np.ndarray


@dataclass
class Assignment:
    name: str
    active_mask: np.ndarray          # [K,L,N]
    moderate_mask: np.ndarray        # [K,L,N]
    reported_mask: np.ndarray        # [K,L,N]
    pilot_index: np.ndarray          # [K]
    tau_p: int
    n_active_rf_per_ap: np.ndarray   # [L]
    adjacency: np.ndarray            # [K,K]
    weights: Optional[np.ndarray] = None
    selected_ap_mask: Optional[np.ndarray] = None  # [K,L]


@dataclass
class ClosedFormCache:
    desired_mean: np.ndarray
    noise_expect: np.ndarray
    zeta_base: np.ndarray
    psi_sum: np.ndarray
    theta_sum: np.ndarray
    same_pilot: np.ndarray


@dataclass
class SetupSchemeResult:
    se: np.ndarray
    sinr: np.ndarray
    rho_data: np.ndarray
    ee: float
    assignment: Assignment


@dataclass
class SchemeMetrics:
    name: str
    avg_se_per_user: float
    sum_se: float
    likely95_se: float
    avg_ee: float
    avg_tau_p: float
    avg_active_rf: float
    avg_edges: float
    all_se_values: np.ndarray
    # Per-setup actual pilot counts. This is used only for plotting/diagnostics
    # and does not affect any assignment/SINR/SE/EE calculation.
    tau_p_values: Optional[np.ndarray] = None


# =============================================================================
# Channel generation
# =============================================================================


def generate_topology_and_channel_stats(cfg: SimConfig, rng: np.random.Generator) -> ChannelStats:
    L, K, N = cfg.L, cfg.K, cfg.N
    side = cfg.area_side_m
    U = dft_matrix(N)

    ap_pos = rng.uniform(0.0, side, size=(L, 2))
    ue_pos = rng.uniform(0.0, side, size=(K, 2))

    mu_h = np.zeros((K, L, N), dtype=np.complex128)
    cov_h = np.zeros((K, L, N, N), dtype=np.complex128)
    mu_b = np.zeros((K, L, N), dtype=np.complex128)
    cov_b = np.zeros((K, L, N, N), dtype=np.complex128)
    beam_power = np.zeros((K, L, N), dtype=np.float64)
    beta_large_scale = np.zeros((K, L), dtype=np.float64)
    los = np.zeros((K, L), dtype=bool)

    k_rician_los = float(db2lin(cfg.rician_k_los_db))

    for k in range(K):
        for l in range(L):
            dxy = wraparound_delta(ap_pos[l], ue_pos[k], side)
            d2d = float(np.linalg.norm(dxy))
            d3d = float(np.sqrt(d2d**2 + (cfg.ap_height_m - cfg.ue_height_m) ** 2))
            angle = float(np.arctan2(dxy[1], dxy[0]))

            is_los = bool(rng.random() < umi_los_probability(d2d))
            los[k, l] = is_los
            pl_db = pathloss_umi_approx_db(
                d2d,
                d3d,
                cfg.fc_ghz,
                is_los,
                cfg.ap_height_m,
                cfg.ue_height_m,
                rng,
                shadowing=True,
            )
            beta = float(db2lin(-pl_db))
            beta_large_scale[k, l] = beta

            angular_spread = float(np.arctan2(cfg.one_ring_radius_m, max(d2d, 1.0)))
            angular_spread = min(angular_spread, np.deg2rad(60.0))
            R = one_ring_covariance_approx(N, angle, angular_spread, cfg.n_scatter_angles)

            if is_los:
                a_los = ula_steering_vector(N, angle)
                mu = np.sqrt(beta * k_rician_los / (k_rician_los + 1.0)) * a_los
                C = beta / (k_rician_los + 1.0) * R
            else:
                mu = np.zeros(N, dtype=np.complex128)
                C = beta * R
            C = 0.5 * (C + C.conj().T)

            mu_h[k, l] = mu
            cov_h[k, l] = C

            mb = U.conj().T @ mu
            Cb = U.conj().T @ C @ U
            Cb = 0.5 * (Cb + Cb.conj().T)
            mu_b[k, l] = mb
            cov_b[k, l] = Cb
            beam_power[k, l] = np.maximum(np.real(np.diag(Cb)) + np.abs(mb) ** 2, 0.0)

    return ChannelStats(ap_pos, ue_pos, mu_h, cov_h, mu_b, cov_b, beam_power, beta_large_scale, los)


# =============================================================================
# Beam/AP selection helpers
# =============================================================================


def select_reported_active_moderate_beams(cfg: SimConfig, stats: ChannelStats) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    K, L, N = cfg.K, cfg.L, cfg.N
    power = stats.beam_power
    snr_lin = cfg.rho_p_watt * power / cfg.noise_power_watt
    reported = snr_lin > db2lin(cfg.beam_detect_snr_db)
    active = np.zeros((K, L, N), dtype=bool)
    moderate = np.zeros((K, L, N), dtype=bool)
    target = cfg.delta_active_percent / 100.0

    for k in range(K):
        flat_power = power[k].reshape(L * N)
        flat_reported = reported[k].reshape(L * N)
        idx = np.flatnonzero(flat_reported)
        if idx.size == 0:
            idx = np.array([int(np.argmax(flat_power))])
            flat_reported[idx[0]] = True
            reported[k] = flat_reported.reshape(L, N)
        ordered = idx[np.argsort(flat_power[idx])[::-1]]
        total = float(np.sum(flat_power[ordered]))
        if total <= 0.0:
            chosen = ordered[:1]
        else:
            cum = np.cumsum(flat_power[ordered]) / total
            n_active = int(np.searchsorted(cum, target, side="left") + 1)
            chosen = ordered[:n_active]
        active[k].reshape(L * N)[chosen] = True
        moderate[k] = reported[k] & (~active[k])
    return reported, active, moderate


def select_aps_largest_large_scale(cfg: SimConfig, stats: ChannelStats) -> np.ndarray:
    """Largest-large-scale-fading AP selection with delta=95%; used by random/greedy and as GC/WGF assumption."""
    K, L = cfg.K, cfg.L
    selected = np.zeros((K, L), dtype=bool)
    target = cfg.delta_active_percent / 100.0
    for k in range(K):
        beta = np.maximum(stats.beta_large_scale[k], 0.0)
        order = np.argsort(beta)[::-1]
        total = float(np.sum(beta[order]))
        if total <= 0.0:
            selected[k, order[0]] = True
            continue
        cum = np.cumsum(beta[order]) / total
        n_ap = int(np.searchsorted(cum, target, side="left") + 1)
        selected[k, order[:n_ap]] = True
    return selected


def active_mask_from_ap_selection(cfg: SimConfig, ap_mask: np.ndarray) -> np.ndarray:
    K, L, N = cfg.K, cfg.L, cfg.N
    active = np.zeros((K, L, N), dtype=bool)
    active[ap_mask, :] = True
    return active


def rf_chains_for_assignment(cfg: SimConfig, active_mask: np.ndarray, proposed: bool) -> np.ndarray:
    if proposed:
        return active_mask.any(axis=0).sum(axis=1).astype(int)
    # Baselines are not using beam-wise RF-chain switching: if AP is active, use all N chains.
    active_ap = active_mask.any(axis=(0, 2))
    return (active_ap.astype(int) * cfg.N).astype(int)


# =============================================================================
# Graph/coloring helpers
# =============================================================================


def dsatur_unbounded(adjacency: np.ndarray) -> np.ndarray:
    A = adjacency.astype(bool)
    K = A.shape[0]
    colors = -np.ones(K, dtype=int)
    degrees = A.sum(axis=1)
    for _ in range(K):
        uncolored = np.where(colors < 0)[0]
        if uncolored.size == 0:
            break
        sats = []
        for v in uncolored:
            sats.append(len(set(colors[A[v] & (colors >= 0)].tolist())))
        sats = np.array(sats)
        candidates = uncolored[sats == sats.max()]
        deg = degrees[candidates]
        candidates = candidates[deg == deg.max()]
        v = int(candidates.min())
        used = set(colors[A[v] & (colors >= 0)].tolist())
        c = 0
        while c in used:
            c += 1
        colors[v] = c
    return colors


def dsatur_constrained(adjacency: np.ndarray, tau_p: int, weights: Optional[np.ndarray] = None) -> np.ndarray:
    """DSATUR-like coloring with exactly tau_p available colors; conflicts are minimized if unavoidable."""
    A = adjacency.astype(bool)
    K = A.shape[0]
    colors = -np.ones(K, dtype=int)
    degrees = A.sum(axis=1)
    if weights is None:
        weights = A.astype(float)

    for _ in range(K):
        uncolored = np.where(colors < 0)[0]
        if uncolored.size == 0:
            break
        sats = []
        for v in uncolored:
            sats.append(len(set(colors[A[v] & (colors >= 0)].tolist())))
        sats = np.array(sats)
        candidates = uncolored[sats == sats.max()]
        deg = degrees[candidates]
        candidates = candidates[deg == deg.max()]
        v = int(candidates.min())

        costs = np.zeros(tau_p, dtype=float)
        for c in range(tau_p):
            same = colors == c
            costs[c] = np.sum(weights[v, same])
        colors[v] = int(np.argmin(costs))
    return colors


def weighted_max_k_cut_assignment(weights: np.ndarray, tau_p: int, rng: np.random.Generator, refine_iters: int = 8) -> np.ndarray:
    """Greedy + local refinement to minimize total same-pilot weight, equivalent to Max-k-Cut."""
    K = weights.shape[0]
    order = np.argsort(weights.sum(axis=1))[::-1]
    colors = -np.ones(K, dtype=int)

    for v in order:
        costs = np.zeros(tau_p, dtype=float)
        for c in range(tau_p):
            same = colors == c
            costs[c] = np.sum(weights[v, same])
        # random tie break for stability across exact ties
        min_cost = np.min(costs)
        best = np.flatnonzero(np.isclose(costs, min_cost))
        colors[v] = int(rng.choice(best))

    for _ in range(refine_iters):
        changed = False
        for v in order:
            current = colors[v]
            costs = np.zeros(tau_p, dtype=float)
            for c in range(tau_p):
                same = (colors == c)
                same[v] = False
                costs[c] = np.sum(weights[v, same])
            best = int(np.argmin(costs))
            if costs[best] + 1e-18 < costs[current]:
                colors[v] = best
                changed = True
        if not changed:
            break
    return colors


# =============================================================================
# Assignment builders
# =============================================================================


def weighted_beam_interference_matrix(
    cfg: SimConfig,
    active: np.ndarray,
    moderate: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Weighted-threshold version of the beam-domain proposed graph.

    Original paper:
        B = Ba^T Ba + Ba^T Bi + Bi^T Ba, A_ij = 1[B_ij > 0].

    This implementation:
        W = w_aa Ba^T Ba + w_ai Ba^T Bi + w_ia Bi^T Ba,
        A_ij = 1[W_ij > edge_threshold].

    Here Ba/Bi are beam-user association matrices for active/moderate beams.
    """
    K, L, N = active.shape
    A = active.reshape(K, L * N).astype(float)
    Q = moderate.reshape(K, L * N).astype(float)
    W = cfg.w_aa * (A @ A.T) + cfg.w_ai * (A @ Q.T) + cfg.w_ia * (Q @ A.T)
    np.fill_diagonal(W, 0.0)
    adjacency = W > cfg.edge_threshold
    np.fill_diagonal(adjacency, False)
    return W, adjacency


def beam_overlap_ratio_matrix(cfg: SimConfig, active: np.ndarray, moderate: np.ndarray) -> np.ndarray:
    """
    Directed weighted beam-overlap ratio used by MatchingBeam schemes.

    M^B_ij = (w_aa |A_i ∩ A_j| + w_ai |A_i ∩ I_j| + w_ia |I_i ∩ A_j|) / |A_i|.
    """
    K, L, N = active.shape
    A = active.reshape(K, L * N).astype(float)
    Q = moderate.reshape(K, L * N).astype(float)
    O = cfg.w_aa * (A @ A.T) + cfg.w_ai * (A @ Q.T) + cfg.w_ia * (Q @ A.T)
    denom = np.maximum(A.sum(axis=1, keepdims=True), 1.0)
    M = O / denom
    np.fill_diagonal(M, 0.0)
    return M


def proposed_assignment(cfg: SimConfig, stats: ChannelStats) -> Assignment:
    reported, active, moderate = select_reported_active_moderate_beams(cfg, stats)
    K = cfg.K
    W_interf, adjacency = weighted_beam_interference_matrix(cfg, active, moderate)
    colors = dsatur_unbounded(adjacency)
    tau_p = int(colors.max() + 1) if K > 0 else 0
    n_rf = rf_chains_for_assignment(cfg, active, proposed=True)
    return Assignment("Proposed", active, moderate, reported, colors, tau_p, n_rf, adjacency, W_interf.astype(float))


def many_to_many_resource_matching(
    cfg: SimConfig,
    stats: ChannelStats,
    reported: np.ndarray,
    ue_quota: np.ndarray,
    resource_quota: int,
) -> np.ndarray:
    """Many-to-many matching between UE k and AP-beam resource r=(l,n)."""
    K, L, N = cfg.K, cfg.L, cfg.N
    R = L * N
    power = stats.beam_power.reshape(K, R)
    candidates = reported.reshape(K, R).copy()

    prefs: List[np.ndarray] = []
    for k in range(K):
        idx = np.flatnonzero(candidates[k])
        if idx.size == 0:
            idx = np.array([int(np.argmax(power[k]))], dtype=int)
            candidates[k, idx[0]] = True
        order = idx[np.argsort(power[k, idx])[::-1]]
        prefs.append(order.astype(int))

    ue_quota = np.maximum(ue_quota.astype(int), 1)
    mu = np.zeros((K, R), dtype=bool)
    ptr = np.zeros(K, dtype=int)

    while True:
        active_users = [k for k in range(K) if mu[k].sum() < ue_quota[k] and ptr[k] < len(prefs[k])]
        if not active_users:
            break
        proposals: Dict[int, List[int]] = {}
        for k in active_users:
            r = int(prefs[k][ptr[k]])
            ptr[k] += 1
            proposals.setdefault(r, []).append(k)

        changed = False
        for r, prop_users in proposals.items():
            current = np.flatnonzero(mu[:, r]).tolist()
            cand = sorted(set(current + prop_users), key=lambda u: power[u, r], reverse=True)
            chosen = cand[:resource_quota]
            old = mu[:, r].copy()
            mu[:, r] = False
            mu[chosen, r] = True
            if not np.array_equal(old, mu[:, r]):
                changed = True
        # Even if no change, pointers have advanced; continue until preferences are exhausted.

    # Safeguard: make sure every UE has at least one active resource.
    for k in range(K):
        if mu[k].sum() == 0:
            idx = np.flatnonzero(candidates[k])
            if idx.size == 0:
                idx = np.array([int(np.argmax(power[k]))], dtype=int)
            # Prefer a resource with remaining quota; otherwise use the strongest one.
            free = [r for r in idx if mu[:, r].sum() < resource_quota]
            r_best = int(max(free, key=lambda r: power[k, r])) if free else int(idx[np.argmax(power[k, idx])])
            mu[k, r_best] = True
    return mu


def assign_pilots_by_matching_groups(
    cfg: SimConfig,
    mu: np.ndarray,
    M_ratio: np.ndarray,
    rng: np.random.Generator,
    adaptive: bool,
) -> Tuple[np.ndarray, int]:
    """Matching-paper Algorithm 2 extended to AP-beam resource groups."""
    K, R = mu.shape
    group_sizes = mu.sum(axis=0)
    max_group = int(np.max(group_sizes)) if R > 0 else 1
    if adaptive:
        tau_p = max(1, max_group)
    else:
        tau_p = cfg.baseline_tau_p
    pilot_list = np.arange(tau_p, dtype=int)
    colors = -np.ones(K, dtype=int)

    risks = np.zeros(R, dtype=float)
    for r in range(R):
        users = np.flatnonzero(mu[:, r])
        if users.size > 1:
            sub = M_ratio[np.ix_(users, users)].copy()
            np.fill_diagonal(sub, 0.0)
            risks[r] = float(np.sum(sub))
    group_order = np.argsort(risks)[::-1]

    for r in group_order:
        users = np.flatnonzero(mu[:, r])
        if users.size == 0:
            continue
        occupied = set(colors[u] for u in users if colors[u] >= 0)
        # Assign unassigned high-overlap users first.
        user_order = sorted(users.tolist(), key=lambda u: np.sum(M_ratio[u, users]) + np.sum(M_ratio[users, u]), reverse=True)
        for u in user_order:
            if colors[u] >= 0:
                continue
            available = [p for p in pilot_list if p not in occupied]
            if available:
                chosen = int(rng.choice(available))
            else:
                # Collision is unavoidable: choose pilot with minimum weighted beam-overlap cost.
                costs = np.zeros(tau_p, dtype=float)
                for p in pilot_list:
                    same = np.flatnonzero(colors == p)
                    if same.size:
                        costs[p] = float(np.sum(M_ratio[u, same] + M_ratio[same, u]))
                chosen = int(np.argmin(costs))
            colors[u] = chosen
            occupied.add(chosen)

    # Assign users that did not belong to any processed group.
    for u in range(K):
        if colors[u] < 0:
            costs = np.zeros(tau_p, dtype=float)
            for p in pilot_list:
                same = np.flatnonzero(colors == p)
                if same.size:
                    costs[p] = float(np.sum(M_ratio[u, same] + M_ratio[same, u]))
            colors[u] = int(np.argmin(costs))
    return colors, tau_p


def matching_beam_assignment(cfg: SimConfig, stats: ChannelStats, rng: np.random.Generator, adaptive: bool) -> Assignment:
    """AP-beam-resource many-to-many matching + weighted-threshold beam overlap pilot assignment."""
    reported, active_ref, _ = select_reported_active_moderate_beams(cfg, stats)
    K, L, N = cfg.K, cfg.L, cfg.N
    ue_quota = active_ref.reshape(K, L * N).sum(axis=1).astype(int)
    resource_quota = int(cfg.matching_resource_quota) if cfg.matching_resource_quota > 0 else int(cfg.baseline_tau_p)
    resource_quota = max(resource_quota, 1)

    mu = many_to_many_resource_matching(cfg, stats, reported, ue_quota, resource_quota)
    active = mu.reshape(K, L, N)
    moderate = reported & (~active)

    W_interf, adjacency = weighted_beam_interference_matrix(cfg, active, moderate)
    M_ratio = beam_overlap_ratio_matrix(cfg, active, moderate)
    colors, tau_p = assign_pilots_by_matching_groups(cfg, mu, M_ratio, rng, adaptive=adaptive)
    n_rf = rf_chains_for_assignment(cfg, active, proposed=True)
    name = "MatchingBeamAdaptive" if adaptive else "MatchingBeamFixed"
    return Assignment(name, active, moderate, reported, colors, tau_p, n_rf, adjacency, W_interf.astype(float))


def ap_overlap_adjacency(ap_mask: np.ndarray) -> np.ndarray:
    common = ap_mask.astype(int) @ ap_mask.astype(int).T
    adjacency = common > 0
    np.fill_diagonal(adjacency, False)
    return adjacency


def ap_weight_matrix(stats: ChannelStats, ap_mask: np.ndarray) -> np.ndarray:
    """Potential contamination weight used for WGF/greedy baselines."""
    beta = stats.beta_large_scale
    K, L = beta.shape
    W = np.zeros((K, K), dtype=float)
    for i in range(K):
        for j in range(i + 1, K):
            common = ap_mask[i] & ap_mask[j]
            if np.any(common):
                # Severity: common AP large-scale product. Normalized for numerical stability.
                wij = float(np.sum(beta[i, common] * beta[j, common]))
                W[i, j] = W[j, i] = wij
    if np.max(W) > 0:
        W = W / np.max(W)
    return W


def baseline_assignment(cfg: SimConfig, stats: ChannelStats, scheme: str, rng: np.random.Generator) -> Assignment:
    scheme_l = scheme.lower()
    tau_p = cfg.baseline_tau_p
    ap_mask = select_aps_largest_large_scale(cfg, stats)
    active = active_mask_from_ap_selection(cfg, ap_mask)
    moderate = np.zeros_like(active, dtype=bool)
    reported = active.copy()
    adjacency = ap_overlap_adjacency(ap_mask)
    weights = ap_weight_matrix(stats, ap_mask)

    if scheme_l == "random":
        colors = rng.integers(0, tau_p, size=cfg.K)
        name = "Random"
    elif scheme_l == "gc":
        colors = dsatur_constrained(adjacency, tau_p, weights=None)
        name = "GC"
    elif scheme_l == "wgf":
        colors = weighted_max_k_cut_assignment(weights, tau_p, rng, refine_iters=cfg.wgf_refine_iters)
        name = "WGF"
    elif scheme_l == "greedy":
        colors = greedy_pilot_assignment_metric(cfg, stats, active, ap_mask, weights, rng)
        name = "Greedy"
    else:
        raise ValueError(f"Unknown baseline scheme: {scheme}")

    n_rf = rf_chains_for_assignment(cfg, active, proposed=False)
    return Assignment(name, active, moderate, reported, colors.astype(int), tau_p, n_rf, adjacency, weights, selected_ap_mask=ap_mask)


def greedy_pilot_assignment_metric(
    cfg: SimConfig,
    stats: ChannelStats,
    active: np.ndarray,
    ap_mask: np.ndarray,
    weights: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Ngo-style greedy baseline:
      - start from random fixed pilots;
      - iteratively select the user with the largest current same-pilot contamination metric;
      - assign that user to the pilot minimizing same-pilot contamination.

    The original [1] uses a large-scale-fading metric for reassignment. This implementation uses
    the AP-overlap large-scale product weight W_ij as the same-pilot contamination metric.
    """
    K, tau_p = cfg.K, cfg.baseline_tau_p
    colors = rng.integers(0, tau_p, size=K)
    W = weights

    for _ in range(cfg.greedy_iters):
        same_cost = np.zeros(K, dtype=float)
        for k in range(K):
            same = (colors == colors[k])
            same[k] = False
            same_cost[k] = np.sum(W[k, same])
        k_star = int(np.argmax(same_cost))
        costs = np.zeros(tau_p, dtype=float)
        for p in range(tau_p):
            same = (colors == p)
            same[k_star] = False
            costs[p] = np.sum(W[k_star, same])
        colors[k_star] = int(np.argmin(costs))
    return colors



# =============================================================================
# AP-domain hybrid assignment builders
# =============================================================================


def _normalized_pair_weight_from_features(features: np.ndarray) -> np.ndarray:
    W = features.astype(float) @ features.astype(float).T
    np.fill_diagonal(W, 0.0)
    mx = float(np.max(W)) if W.size else 0.0
    if mx > 0.0:
        W = W / mx
    return W


def ap_domain_hybrid_masks(cfg: SimConfig, stats: ChannelStats) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Use the same AP-selection/active-mask convention as Random/Greedy/WGF/GC."""
    ap_mask = select_aps_largest_large_scale(cfg, stats)
    active = active_mask_from_ap_selection(cfg, ap_mask)
    moderate = np.zeros_like(active, dtype=bool)
    reported = active.copy()
    n_rf = rf_chains_for_assignment(cfg, active, proposed=False)
    return ap_mask, active, moderate, reported, n_rf


def topn_overlap_conflict(features: np.ndarray, top_n: int) -> Tuple[np.ndarray, np.ndarray]:
    """Conflict graph from shared top-N features. Returns (adjacency, overlap_count)."""
    K, M = features.shape
    if K == 0:
        return np.zeros((0, 0), dtype=bool), np.zeros((0, 0), dtype=float)
    n_eff = int(np.clip(top_n, 1, M))
    top_idx = np.argpartition(-features, n_eff - 1, axis=1)[:, :n_eff]
    is_top = np.zeros((K, M), dtype=bool)
    rows = np.arange(K)[:, None]
    is_top[rows, top_idx] = True
    overlap = is_top.astype(np.int32) @ is_top.astype(np.int32).T
    adjacency = overlap > 0
    np.fill_diagonal(adjacency, False)
    np.fill_diagonal(overlap, 0)
    return adjacency, overlap.astype(float)


def quota_free_greedy_color(conflict: np.ndarray) -> np.ndarray:
    """Max-degree-first greedy coloring without a per-color quota."""
    K = conflict.shape[0]
    if K == 0:
        return np.empty(0, dtype=int)
    colors = np.full(K, -1, dtype=int)
    degree = conflict.sum(axis=1)
    order = np.argsort(-degree)
    for v in order:
        used = set()
        for u in np.flatnonzero(conflict[v]):
            if colors[u] >= 0:
                used.add(int(colors[u]))
        c = 0
        while c in used:
            c += 1
        colors[v] = c
    return colors


def quota_free_chromatic(conflict: np.ndarray) -> int:
    colors = quota_free_greedy_color(conflict)
    return int(colors.max() + 1) if colors.size else 0


def topap_quota_coloring(conflict: np.ndarray, tau_p: int) -> Tuple[np.ndarray, int]:
    """TopAP fixed-budget coloring used by TopAP-bisect: max-degree first + per-color quota."""
    K = conflict.shape[0]
    if K == 0:
        return np.empty(0, dtype=int), 0
    per_color_quota = max(1, int(np.ceil(K / max(tau_p, 1))))
    colors = np.full(K, -1, dtype=int)
    current_color = 0

    while np.any(colors < 0):
        uncolored = np.flatnonzero(colors < 0)
        sub_conflict = conflict[np.ix_(uncolored, uncolored)]
        degree = sub_conflict.sum(axis=1)
        seed = int(uncolored[int(np.argmax(degree))])
        colors[seed] = current_color
        blocked = conflict[seed].copy()
        blocked[seed] = True
        placed = 1
        while placed < per_color_quota:
            candidates = np.flatnonzero((colors < 0) & ~blocked)
            if candidates.size == 0:
                break
            pick = int(candidates[0])
            colors[pick] = current_color
            blocked |= conflict[pick]
            blocked[pick] = True
            placed += 1
        current_color += 1

    n_colors_raw = int(current_color)
    if colors.max(initial=-1) >= tau_p:
        colors = colors % max(tau_p, 1)
    return colors.astype(int), n_colors_raw


def choose_topn_by_bisection(features: np.ndarray, tau_p: int, n_min: int, n_max: int, max_iters: int) -> int:
    """Largest N such that quota-free greedy chromatic of the top-N graph is <= tau_p."""
    M = features.shape[1]
    lo = max(1, int(n_min))
    hi = min(int(n_max), M - 1) if M > 1 else 1
    if hi < lo:
        hi = lo
    best = lo
    for _ in range(max_iters):
        if lo > hi:
            break
        mid = (lo + hi) // 2
        conflict, _ = topn_overlap_conflict(features, mid)
        chi = quota_free_chromatic(conflict)
        if chi <= tau_p:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return int(best)


def topap_bisect_assignment(cfg: SimConfig, stats: ChannelStats, rng: np.random.Generator) -> Assignment:
    del rng
    ap_mask, active, moderate, reported, n_rf = ap_domain_hybrid_masks(cfg, stats)
    tau_p = cfg.baseline_tau_p
    beta = stats.beta_large_scale
    n_used = choose_topn_by_bisection(
        beta,
        tau_p,
        cfg.topap_bisect_min,
        cfg.topap_bisect_max,
        cfg.topap_bisect_iters,
    )
    adjacency, overlap = topn_overlap_conflict(beta, n_used)
    colors, _ = topap_quota_coloring(adjacency, tau_p)
    return Assignment(
        "TopAPBisect",
        active,
        moderate,
        reported,
        colors,
        tau_p,
        n_rf,
        adjacency,
        overlap,
        selected_ap_mask=ap_mask,
    )


def topap_adaptive_assignment(cfg: SimConfig, stats: ChannelStats, rng: np.random.Generator) -> Assignment:
    del rng
    ap_mask, active, moderate, reported, n_rf = ap_domain_hybrid_masks(cfg, stats)
    adjacency, overlap = topn_overlap_conflict(stats.beta_large_scale, cfg.h3_topap_n)
    colors = quota_free_greedy_color(adjacency)
    tau_p_actual = int(colors.max() + 1) if colors.size else 0
    return Assignment(
        "H3TopAPAdaptive",
        active,
        moderate,
        reported,
        colors.astype(int),
        tau_p_actual,
        n_rf,
        adjacency,
        overlap,
        selected_ap_mask=ap_mask,
    )


def hybrid4_topap_greedy_assignment(cfg: SimConfig, stats: ChannelStats, rng: np.random.Generator) -> Assignment:
    del rng
    ap_mask, active, moderate, reported, n_rf = ap_domain_hybrid_masks(cfg, stats)
    beta = stats.beta_large_scale
    tau_p = cfg.baseline_tau_p
    adjacency, overlap = topn_overlap_conflict(beta, cfg.topap_top_n)
    K, M = beta.shape
    degree = adjacency.sum(axis=1)
    order = np.argsort(-degree)
    pilots = np.full(K, -1, dtype=int)
    sum_per_pilot = np.zeros((tau_p, M), dtype=beta.dtype)

    for k in order:
        blocked = set()
        for u in np.flatnonzero(adjacency[k]):
            if pilots[u] >= 0:
                blocked.add(int(pilots[u]))
        available = [p for p in range(tau_p) if p not in blocked]
        if not available:
            available = list(range(tau_p))
        available_arr = np.asarray(available, dtype=int)
        contam = sum_per_pilot[available_arr] @ beta[k]
        pick = int(available_arr[int(np.argmin(contam))])
        pilots[k] = pick
        sum_per_pilot[pick] += beta[k]

    weights = _normalized_pair_weight_from_features(beta)
    # Keep overlap as the adjacency diagnostic and beta-dot-beta as weights for later analysis.
    weights = np.maximum(weights, overlap / max(float(np.max(overlap)), 1.0))
    return Assignment(
        "H4TopAPGreedy",
        active,
        moderate,
        reported,
        pilots.astype(int),
        tau_p,
        n_rf,
        adjacency,
        weights,
        selected_ap_mask=ap_mask,
    )


def many_to_many_ap_matching(
    cfg: SimConfig,
    stats: ChannelStats,
    ap_mask_ref: np.ndarray,
    ap_quota: int,
) -> np.ndarray:
    """Gao-style many-to-many matching between UEs and APs using AP-domain beta."""
    K, L = cfg.K, cfg.L
    beta = stats.beta_large_scale
    # Use the baseline serving-set size as UE quota so H2 is compatible with this simulator's AP selection.
    ue_quota = np.maximum(ap_mask_ref.sum(axis=1).astype(int), 1)
    prefs = [np.argsort(beta[k])[::-1].astype(int) for k in range(K)]
    ptr = np.zeros(K, dtype=int)
    mu = np.zeros((K, L), dtype=bool)
    ap_quota = max(int(ap_quota), 1)

    while True:
        active_users = [k for k in range(K) if mu[k].sum() < ue_quota[k] and ptr[k] < L]
        if not active_users:
            break
        proposals: Dict[int, List[int]] = {}
        for k in active_users:
            ap = int(prefs[k][ptr[k]])
            ptr[k] += 1
            proposals.setdefault(ap, []).append(k)
        for ap, prop_users in proposals.items():
            current = np.flatnonzero(mu[:, ap]).tolist()
            candidates = sorted(set(current + prop_users), key=lambda u: beta[u, ap], reverse=True)
            chosen = candidates[:ap_quota]
            mu[:, ap] = False
            mu[chosen, ap] = True

    for k in range(K):
        if mu[k].sum() == 0:
            ap = int(np.argmax(beta[k]))
            mu[k, ap] = True
    return mu


def common_serving_ap_ratio(mu: np.ndarray) -> np.ndarray:
    common = mu.astype(int) @ mu.astype(int).T
    denom = np.maximum(mu.sum(axis=1, keepdims=True), 1)
    ratio = common / denom
    np.fill_diagonal(ratio, 0.0)
    return ratio.astype(float)


def group_scores_from_ratio(mu: np.ndarray, ratio: np.ndarray) -> np.ndarray:
    _, L = mu.shape
    scores = np.zeros(L, dtype=float)
    for ap in range(L):
        users = np.flatnonzero(mu[:, ap])
        if users.size > 1:
            sub = ratio[np.ix_(users, users)].copy()
            np.fill_diagonal(sub, 0.0)
            scores[ap] = float(np.sum(sub))
    return scores


def h2_gao_greedy_assignment(cfg: SimConfig, stats: ChannelStats, rng: np.random.Generator) -> Assignment:
    ap_mask, active, moderate, reported, n_rf = ap_domain_hybrid_masks(cfg, stats)
    tau_p = cfg.baseline_tau_p
    beta = stats.beta_large_scale
    mu = many_to_many_ap_matching(cfg, stats, ap_mask, ap_quota=tau_p)
    ratio = common_serving_ap_ratio(mu)
    group_scores = group_scores_from_ratio(mu, ratio)
    group_order = np.argsort(-group_scores)

    K, M = beta.shape
    pilots = np.full(K, -1, dtype=int)
    sum_per_pilot = np.zeros((tau_p, M), dtype=beta.dtype)

    for ap in group_order:
        group = np.flatnonzero(mu[:, ap])
        if group.size == 0:
            continue
        occupied_pilots = pilots[group][pilots[group] >= 0]
        occupied = np.zeros(tau_p, dtype=bool)
        occupied[occupied_pilots] = True
        available_mask = ~occupied
        unassigned = group[pilots[group] < 0]
        if unassigned.size == 0:
            continue
        # Preserve H2's randomized within-group processing order, but make the pilot choice deterministic greedy.
        for idx in rng.permutation(unassigned.size):
            ue = int(unassigned[idx])
            available_idx = np.flatnonzero(available_mask)
            if available_idx.size == 0:
                available_idx = np.arange(tau_p, dtype=int)
            contam = sum_per_pilot[available_idx] @ beta[ue]
            pick = int(available_idx[int(np.argmin(contam))])
            pilots[ue] = pick
            sum_per_pilot[pick] += beta[ue]
            if pick < available_mask.size:
                available_mask[pick] = False

    missing = np.flatnonzero(pilots < 0)
    for ue in missing:
        contam = sum_per_pilot @ beta[ue]
        pick = int(np.argmin(contam))
        pilots[ue] = pick
        sum_per_pilot[pick] += beta[ue]

    adjacency = ap_overlap_adjacency(mu)
    weights = _normalized_pair_weight_from_features(beta)
    return Assignment(
        "H2GaoGreedy",
        active,
        moderate,
        reported,
        pilots.astype(int),
        tau_p,
        n_rf,
        adjacency,
        weights,
        selected_ap_mask=ap_mask,
    )

# =============================================================================
# Closed-form SINR and max-min power control
# =============================================================================


def _submatrix(M: np.ndarray, idx: np.ndarray) -> np.ndarray:
    return M[np.ix_(idx, idx)]


def build_closed_form_cache(cfg: SimConfig, stats: ChannelStats, assignment: Assignment) -> ClosedFormCache:
    K, L = cfg.K, cfg.L
    sigma2 = cfg.noise_power_watt
    tau_p = max(assignment.tau_p, 1)
    noise_var_after_pilot = sigma2 / max(cfg.rho_p_watt * tau_p, 1e-30)

    desired_mean = np.zeros(K, dtype=np.complex128)
    noise_expect = np.zeros(K, dtype=float)
    zeta_base = np.zeros((K, K), dtype=float)
    psi_sum = np.zeros((K, K), dtype=np.complex128)
    theta_sum = np.zeros((K, K), dtype=np.complex128)
    same_pilot = np.equal.outer(assignment.pilot_index, assignment.pilot_index)

    for k in range(K):
        active_aps = np.flatnonzero(assignment.active_mask[k].any(axis=1))
        psi_by_i: List[List[complex]] = [[] for _ in range(K)]
        same_by_i: List[List[float]] = [[] for _ in range(K)]
        theta_by_i: List[List[complex]] = [[] for _ in range(K)]

        for l in active_aps:
            idx = np.flatnonzero(assignment.active_mask[k, l])
            if idx.size == 0:
                continue
            d = idx.size
            I = np.eye(d, dtype=np.complex128)
            mu_k = stats.mu_b[k, l, idx]
            C_k = _submatrix(stats.cov_b[k, l], idx)

            Cy = C_k.copy()
            for j in range(K):
                if j != k and assignment.pilot_index[j] == assignment.pilot_index[k]:
                    Cy += _submatrix(stats.cov_b[j, l], idx)
            Cy += noise_var_after_pilot * I
            Cy = 0.5 * (Cy + Cy.conj().T)
            try:
                invCy_Ck = np.linalg.solve(Cy, C_k)
            except np.linalg.LinAlgError:
                invCy_Ck = np.linalg.pinv(Cy) @ C_k

            Psi_self = C_k.conj().T @ invCy_Ck
            Psi_self = 0.5 * (Psi_self + Psi_self.conj().T)
            desired_l = np.vdot(mu_k, mu_k) + np.trace(Psi_self)
            desired_mean[k] += desired_l
            noise_expect[k] += float(np.real(desired_l))

            A_mat = np.outer(mu_k, mu_k.conj()) + Psi_self
            for i in range(K):
                mu_i = stats.mu_b[i, l, idx]
                C_i = _submatrix(stats.cov_b[i, l], idx)
                psi = np.vdot(mu_k, mu_i)
                B_mat = np.outer(mu_i, mu_i.conj()) + C_i
                same_term = np.trace(A_mat @ B_mat)
                psi_by_i[i].append(psi)
                same_by_i[i].append(float(np.real(same_term)))
                if assignment.pilot_index[i] == assignment.pilot_index[k]:
                    theta = np.trace(C_i.conj().T @ invCy_Ck)
                else:
                    theta = 0.0 + 0.0j
                theta_by_i[i].append(theta)

        for i in range(K):
            psi_vec = np.asarray(psi_by_i[i], dtype=np.complex128)
            same_vec = np.asarray(same_by_i[i], dtype=float)
            theta_vec = np.asarray(theta_by_i[i], dtype=np.complex128)
            if psi_vec.size == 0:
                continue
            # Eq. (13): same-AP terms plus cross-AP mean terms.
            cross_mean = np.abs(np.sum(psi_vec)) ** 2 - np.sum(np.abs(psi_vec) ** 2)
            zeta_base[k, i] = float(np.sum(same_vec) + np.real(cross_mean))
            psi_sum[k, i] = np.sum(psi_vec)
            theta_sum[k, i] = np.sum(theta_vec)

    return ClosedFormCache(desired_mean, noise_expect, zeta_base, psi_sum, theta_sum, same_pilot)


def expected_second_moment(cache: ClosedFormCache, rho: np.ndarray, k: int, i: int) -> float:
    val = float(cache.zeta_base[k, i])
    if cache.same_pilot[k, i]:
        denom = max(float(rho[k]), 1e-30)
        ratio = max(float(rho[i]) / denom, 0.0)
        psi = cache.psi_sum[k, i]
        theta = cache.theta_sum[k, i]
        # Compact Eq. (14): |psi + sqrt(ratio)*theta|^2 - |psi|^2.
        chi = np.abs(psi + np.sqrt(ratio) * theta) ** 2 - np.abs(psi) ** 2
        val += float(np.real(chi))
    return max(val, 0.0)


def sinr_closed_form(cfg: SimConfig, cache: ClosedFormCache, rho: np.ndarray) -> np.ndarray:
    K = cfg.K
    sinr = np.zeros(K, dtype=float)
    signal_gain = np.abs(cache.desired_mean) ** 2
    for k in range(K):
        numerator = rho[k] * signal_gain[k]
        denom = 0.0
        for i in range(K):
            denom += rho[i] * expected_second_moment(cache, rho, k, i)
        denom -= rho[k] * signal_gain[k]
        denom += cfg.noise_power_watt * cache.noise_expect[k]
        sinr[k] = max(float(numerator), 0.0) / max(float(np.real(denom)), 1e-300)
    return sinr


def se_from_sinr(cfg: SimConfig, assignment: Assignment, sinr: np.ndarray) -> np.ndarray:
    prelog = max(cfg.tau_c - assignment.tau_p, 0) / cfg.tau_c
    return prelog * np.log2(1.0 + np.maximum(sinr, 0.0))


def max_min_power_control(cfg: SimConfig, cache: ClosedFormCache, rng: np.random.Generator) -> np.ndarray:
    K = cfg.K
    pmax = cfg.rho_data_max_watt
    if cfg.power_control == "full" or minimize is None:
        return np.full(K, pmax, dtype=float)

    # Variables are normalized powers x[0:K] in [0,1] and common SINR target t=x[K].
    def unpack(x):
        rho = np.clip(x[:K], 0.0, 1.0) * pmax
        t = float(x[K])
        return rho, t

    def obj(x):
        return -float(x[K])

    def cons_fun(x):
        rho, t = unpack(x)
        return sinr_closed_form(cfg, cache, rho) - t

    bounds = [(0.0, 1.0)] * K + [(0.0, None)]
    constraints = [{"type": "ineq", "fun": cons_fun}]

    # Initial guesses: full power and a few randomized vectors.
    starts = []
    full_rho = np.ones(K)
    full_sinr = sinr_closed_form(cfg, cache, full_rho * pmax)
    starts.append(np.r_[full_rho, max(0.0, 0.5 * np.min(full_sinr))])
    for _ in range(max(cfg.maxmin_restarts - 1, 0)):
        r = rng.uniform(0.4, 1.0, size=K)
        s = sinr_closed_form(cfg, cache, r * pmax)
        starts.append(np.r_[r, max(0.0, 0.5 * np.min(s))])

    best_x = starts[0]
    best_t = -np.inf
    for x0 in starts:
        res = minimize(
            obj,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": cfg.maxmin_maxiter, "ftol": 1e-7, "disp": False},
        )
        x = res.x if res.success else x0
        rho, _ = unpack(x)
        t_actual = float(np.min(sinr_closed_form(cfg, cache, rho)))
        if t_actual > best_t:
            best_t = t_actual
            best_x = x
    rho, _ = unpack(best_x)
    return np.clip(rho, 0.0, pmax)


# =============================================================================
# Power consumption and evaluation
# =============================================================================


def active_user_count_per_ap(assignment: Assignment) -> np.ndarray:
    return assignment.active_mask.any(axis=2).sum(axis=0).astype(float)


def power_consumption(cfg: SimConfig, assignment: Assignment, sum_se: float, rho: np.ndarray) -> float:
    if cfg.power_model == "simple":
        p_tx = float(np.sum(rho)) + cfg.K * 0.02
        p_ap = cfg.L * 0.2
        p_rf = float(np.sum(assignment.n_active_rf_per_ap) * cfg.p_rf_chain_watt)
        p_fh = 0.002 * sum_se
        return p_tx + p_ap + p_rf + p_fh

    active_ap = assignment.n_active_rf_per_ap > 0
    n_active_ap = int(np.sum(active_ap))
    n_active_rf = float(np.sum(assignment.n_active_rf_per_ap))
    p_tx = float(np.sum(rho) / cfg.pa_efficiency_zeta)
    p_user = cfg.K * cfg.p_user_watt

    if cfg.power_model == "ref12-strict":
        p_ap = n_active_ap * cfg.p_fix_watt
    elif cfg.power_model == "ref12-rf":
        p_ap_base = max(cfg.p_fix_watt - cfg.N * cfg.p_rf_chain_watt, 0.0)
        p_ap = n_active_ap * p_ap_base + n_active_rf * cfg.p_rf_chain_watt
    else:
        raise ValueError("Unknown power_model")

    tau_f = max(cfg.tau_c - assignment.tau_p, 0)
    if cfg.fronthaul_mode == "all_users":
        symbols_per_ap = np.full(cfg.L, cfg.K, dtype=float)
    elif cfg.fronthaul_mode == "active_users":
        symbols_per_ap = active_user_count_per_ap(assignment)
    elif cfg.fronthaul_mode == "active_rf":
        symbols_per_ap = assignment.n_active_rf_per_ap.astype(float)
    else:
        raise ValueError("Unknown fronthaul_mode")
    r_bh = 2.0 * symbols_per_ap * tau_f * cfg.quant_bits_alpha / max(cfg.coherence_time_s, 1e-30)
    p_bh = cfg.p_backhaul_traffic_watt * r_bh / cfg.c_backhaul_bps
    return p_tx + p_user + p_ap + float(np.sum(p_bh[active_ap]))


def evaluate_assignment(cfg: SimConfig, stats: ChannelStats, assignment: Assignment, rng: np.random.Generator) -> SetupSchemeResult:
    cache = build_closed_form_cache(cfg, stats, assignment)
    rho = max_min_power_control(cfg, cache, rng)
    sinr = sinr_closed_form(cfg, cache, rho)
    se = se_from_sinr(cfg, assignment, sinr)
    ee = float(np.sum(se) / max(power_consumption(cfg, assignment, float(np.sum(se)), rho), 1e-30))
    return SetupSchemeResult(se=se, sinr=sinr, rho_data=rho, ee=ee, assignment=assignment)


# =============================================================================
# Simulation loops
# =============================================================================


SCHEME_ORDER = [
    "Random", "Greedy", "WGF", "GC",
    "TopAPBisect", "H2GaoGreedy", "H3TopAPAdaptive", "H4TopAPGreedy",
    "Proposed", "MatchingBeamFixed", "MatchingBeamAdaptive",
]


def build_assignment_for_scheme(cfg: SimConfig, stats: ChannelStats, scheme: str, rng: np.random.Generator) -> Assignment:
    sl = scheme.lower()
    if sl == "proposed":
        return proposed_assignment(cfg, stats)
    if sl in {"matchingbeamfixed", "matching-fixed", "matching_fixed"}:
        return matching_beam_assignment(cfg, stats, rng, adaptive=False)
    if sl in {"matchingbeamadaptive", "matching-adaptive", "matching_adaptive"}:
        return matching_beam_assignment(cfg, stats, rng, adaptive=True)
    if sl in {"topapbisect", "topap-bisect", "topap_bisect"}:
        return topap_bisect_assignment(cfg, stats, rng)
    if sl in {"h2gaogreedy", "h2-gao-greedy", "h2_gao_greedy", "h2"}:
        return h2_gao_greedy_assignment(cfg, stats, rng)
    if sl in {"h3topapadaptive", "h3-topap-adaptive", "h3_topap_adaptive", "topap-adaptive", "h3"}:
        return topap_adaptive_assignment(cfg, stats, rng)
    if sl in {"h4topapgreedy", "h4-topap-greedy", "h4_topap_greedy", "topap-greedy", "h4"}:
        return hybrid4_topap_greedy_assignment(cfg, stats, rng)
    return baseline_assignment(cfg, stats, scheme, rng)


def run_all_schemes_for_setup(cfg: SimConfig, setup_idx: int, schemes: Sequence[str]) -> Dict[str, SetupSchemeResult]:
    # Separate topology RNG from scheme RNG so adding/removing schemes does not change old-scheme topologies.
    topo_seed = stable_seed(cfg.seed, "topology", cfg.K, cfg.N, setup_idx)
    topo_rng = np.random.default_rng(topo_seed)
    stats = generate_topology_and_channel_stats(cfg, topo_rng)
    results: Dict[str, SetupSchemeResult] = {}
    for scheme in schemes:
        scheme_seed = stable_seed(cfg.seed, "scheme", cfg.K, cfg.N, setup_idx, scheme)
        scheme_rng = np.random.default_rng(scheme_seed)
        assign = build_assignment_for_scheme(cfg, stats, scheme, scheme_rng)
        results[assign.name] = evaluate_assignment(cfg, stats, assign, scheme_rng)
    return results


def summarize_scheme_results(name: str, se_list: List[np.ndarray], ee_list: List[float], tau_list: List[int], rf_list: List[float], edge_list: List[int]) -> SchemeMetrics:
    all_se = np.concatenate(se_list) if se_list else np.array([])
    return SchemeMetrics(
        name=name,
        avg_se_per_user=float(np.mean(all_se)) if all_se.size else 0.0,
        sum_se=float(np.mean([np.sum(x) for x in se_list])) if se_list else 0.0,
        likely95_se=float(np.percentile(all_se, 5.0)) if all_se.size else 0.0,
        avg_ee=float(np.mean(ee_list)) if ee_list else 0.0,
        avg_tau_p=float(np.mean(tau_list)) if tau_list else 0.0,
        avg_active_rf=float(np.mean(rf_list)) if rf_list else 0.0,
        avg_edges=float(np.mean(edge_list)) if edge_list else 0.0,
        all_se_values=all_se,
        tau_p_values=np.asarray(tau_list, dtype=float),
    )


def run_simulation(cfg: SimConfig, n_setups: int, schemes: Sequence[str], verbose: bool = True) -> Dict[str, SchemeMetrics]:
    store_se = {s: [] for s in SCHEME_ORDER if s.lower() in [x.lower() for x in schemes]}
    store_ee = {s: [] for s in store_se}
    store_tau = {s: [] for s in store_se}
    store_rf = {s: [] for s in store_se}
    store_edges = {s: [] for s in store_se}

    # Normalize scheme names for lookup.
    requested = []
    for s in SCHEME_ORDER:
        if s.lower() in [x.lower() for x in schemes]:
            requested.append(s)

    for setup in range(n_setups):
        results = run_all_schemes_for_setup(cfg, setup, requested)
        if verbose:
            print(f"setup {setup+1:03d}/{n_setups}")
        for name in requested:
            r = results[name]
            store_se[name].append(r.se)
            store_ee[name].append(r.ee)
            store_tau[name].append(r.assignment.tau_p)
            store_rf[name].append(float(np.mean(r.assignment.n_active_rf_per_ap)))
            store_edges[name].append(int(np.sum(r.assignment.adjacency) // 2))
            if verbose:
                print(
                    f"  {name:8s}: tau_p={r.assignment.tau_p:2d}, "
                    f"edges={store_edges[name][-1]:4d}, RF/AP={store_rf[name][-1]:5.2f}, "
                    f"avgSE={np.mean(r.se):.4f}, EE={r.ee:.6f}"
                )
    return {name: summarize_scheme_results(name, store_se[name], store_ee[name], store_tau[name], store_rf[name], store_edges[name]) for name in requested}


# =============================================================================
# Plotting and CLI
# =============================================================================


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def plot_ecdf(metrics_by_scheme: Dict[str, SchemeMetrics], out_file: Optional[str] = None) -> None:
    if plt is None:
        print("matplotlib not available")
        return
    plt.figure(figsize=(7.2, 5.0))
    for name in SCHEME_ORDER:
        if name not in metrics_by_scheme:
            continue
        vals = np.sort(metrics_by_scheme[name].all_se_values)
        if vals.size == 0:
            continue
        y = np.arange(1, vals.size + 1) / vals.size
        plt.plot(vals, y, linewidth=2.0, label=name)
    plt.xlabel("SE [bit/s/Hz/user]")
    plt.ylabel("eCDF")
    plt.grid(True, alpha=0.3)
    plt.title("eCDF of per-user SE, K=30, N=8")
    plt.legend()
    if out_file:
        plt.savefig(out_file, dpi=200, bbox_inches="tight")
        print(f"Saved {out_file}")
        plt.close()
    else:
        plt.show()


def plot_sweep(xvals: Sequence[int], rows: List[Tuple], ylabel: str, idx: int, title: str, xlabel: str, out_file: Optional[str]) -> None:
    if plt is None:
        print("matplotlib not available")
        return
    plt.figure(figsize=(7.2, 5.0))
    for name in SCHEME_ORDER:
        y = [row[1][name][idx] for row in rows if name in row[1]]
        if len(y) == len(xvals):
            plt.plot(xvals, y, marker="o", linewidth=2.0, label=name)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.title(title)
    plt.legend()
    if out_file:
        plt.savefig(out_file, dpi=200, bbox_inches="tight")
        print(f"Saved {out_file}")
        plt.close()
    else:
        plt.show()




def _ordered_available_schemes(metrics_by_scheme: Dict[str, SchemeMetrics], selected_schemes: Optional[Sequence[str]] = None) -> List[str]:
    """Return selected schemes in SCHEME_ORDER order, keeping only schemes present in metrics."""
    if selected_schemes is None:
        selected = set(metrics_by_scheme.keys())
    else:
        selected = set(selected_schemes)
    return [name for name in SCHEME_ORDER if name in metrics_by_scheme and name in selected]


def plot_pilot_tau_boxplot(
    metrics_by_scheme: Dict[str, SchemeMetrics],
    selected_schemes: Optional[Sequence[str]] = None,
    out_file: Optional[str] = None,
    title: str = "Per-setup actual pilot count",
    show_points: bool = False,
) -> None:
    """Boxplot of assignment.tau_p values collected over Monte-Carlo setups.

    This function is diagnostic-only. It reads SchemeMetrics.tau_p_values, which
    is populated from assignment.tau_p after each setup has already been evaluated.
    It does not change pilot assignment, power control, SINR, SE, or EE logic.
    """
    if plt is None:
        print("matplotlib not available")
        return
    names = _ordered_available_schemes(metrics_by_scheme, selected_schemes)
    data = []
    labels = []
    for name in names:
        vals = metrics_by_scheme[name].tau_p_values
        if vals is None or len(vals) == 0:
            continue
        data.append(np.asarray(vals, dtype=float))
        labels.append(name)
    if not data:
        print("No pilot-count data available for pilot boxplot")
        return

    width = max(7.2, 0.55 * len(labels) + 2.0)
    plt.figure(figsize=(width, 5.0))
    positions = np.arange(1, len(labels) + 1)
    plt.boxplot(data, positions=positions, labels=labels, showmeans=True)
    if show_points:
        rng = np.random.default_rng(12345)
        for pos, vals in zip(positions, data):
            jitter = rng.uniform(-0.08, 0.08, size=len(vals))
            plt.scatter(np.full(len(vals), pos) + jitter, vals, s=12, alpha=0.45)
    plt.ylabel("Actual pilot count $\\tau_p$")
    plt.xlabel("Scheme")
    plt.title(title)
    plt.grid(True, axis="y", alpha=0.3)
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    if out_file:
        plt.savefig(out_file, dpi=200, bbox_inches="tight")
        print(f"Saved {out_file}")
        plt.close()
    else:
        plt.show()


def save_pilot_tau_values_csv(
    metrics_by_scheme: Dict[str, SchemeMetrics],
    selected_schemes: Optional[Sequence[str]],
    path: str,
    scenario: str,
) -> None:
    """Save per-setup tau_p values used by the pilot boxplot."""
    names = _ordered_available_schemes(metrics_by_scheme, selected_schemes)
    rows = []
    for name in names:
        vals = metrics_by_scheme[name].tau_p_values
        if vals is None:
            continue
        for setup_idx, tau_p in enumerate(np.asarray(vals, dtype=float)):
            rows.append((scenario, setup_idx, name, tau_p))
    save_csv(path, ["scenario", "setup", "scheme", "tau_p"], rows)


def _pilot_boxplot_schemes_from_args(args: argparse.Namespace, fallback_schemes: Sequence[str]) -> List[str]:
    if getattr(args, "pilot_boxplot_schemes", None):
        return canonical_schemes(args.pilot_boxplot_schemes)
    return list(fallback_schemes)


def maybe_plot_pilot_boxplot(
    args: argparse.Namespace,
    metrics: Dict[str, SchemeMetrics],
    schemes: Sequence[str],
    outdir: str,
    tag: str,
    title: str,
) -> None:
    if not getattr(args, "pilot_boxplot", False):
        return
    selected = _pilot_boxplot_schemes_from_args(args, schemes)
    plot_pilot_tau_boxplot(
        metrics,
        selected_schemes=selected,
        out_file=os.path.join(outdir, f"{tag}_pilot_tau_boxplot.png"),
        title=title,
        show_points=getattr(args, "pilot_boxplot_points", False),
    )
    if getattr(args, "pilot_boxplot_csv", False):
        save_pilot_tau_values_csv(
            metrics,
            selected,
            os.path.join(outdir, f"{tag}_pilot_tau_values.csv"),
            scenario=tag,
        )



def combine_tau_metrics(metric_objects: Sequence[Tuple[int, Dict[str, SchemeMetrics]]]) -> Dict[str, SchemeMetrics]:
    """Combine tau_p_values across sweep points for pilot-count boxplot only.

    Other metric fields are set to summary placeholders because this combined
    object is used exclusively by plot_pilot_tau_boxplot/save_pilot_tau_values_csv.
    """
    combined_values: Dict[str, List[float]] = {}
    for _, metrics in metric_objects:
        for name, m in metrics.items():
            vals = m.tau_p_values
            if vals is None:
                continue
            combined_values.setdefault(name, []).extend(np.asarray(vals, dtype=float).tolist())
    combined: Dict[str, SchemeMetrics] = {}
    for name, vals in combined_values.items():
        tau_vals = np.asarray(vals, dtype=float)
        combined[name] = SchemeMetrics(
            name=name,
            avg_se_per_user=0.0,
            sum_se=0.0,
            likely95_se=0.0,
            avg_ee=0.0,
            avg_tau_p=float(np.mean(tau_vals)) if tau_vals.size else 0.0,
            avg_active_rf=0.0,
            avg_edges=0.0,
            all_se_values=np.empty(0, dtype=float),
            tau_p_values=tau_vals,
        )
    return combined

def metrics_to_tuple(m: SchemeMetrics) -> Tuple[float, float, float, float, float, float]:
    return (m.avg_se_per_user, m.likely95_se, m.avg_ee, m.avg_tau_p, m.avg_active_rf, m.avg_edges)


def print_metrics_table(metrics: Dict[str, SchemeMetrics], cfg: SimConfig) -> None:
    print(f"\n=== Summary: K={cfg.K}, N={cfg.N}, power_control={cfg.power_control}, power_model={cfg.power_model} ===")
    print("scheme, avgSE, 95likelySE, avgEE, avgTauP, avgRF/AP, avgEdges")
    for name in SCHEME_ORDER:
        if name not in metrics:
            continue
        m = metrics[name]
        print(f"{name:8s}, {m.avg_se_per_user:.6g}, {m.likely95_se:.6g}, {m.avg_ee:.6g}, {m.avg_tau_p:.4g}, {m.avg_active_rf:.4g}, {m.avg_edges:.4g}")


def save_csv(path: str, header: List[str], rows: Iterable[Sequence]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"Saved {path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="All-scheme reproduction-oriented simulator")
    p.add_argument("--mode", choices=["fig1", "sweep-n", "sweep-k", "all", "single"], default="fig1")
    p.add_argument("--schemes", nargs="+", default=["random", "greedy", "wgf", "gc", "proposed", "matching-fixed", "matching-adaptive"], help="Schemes to simulate")
    p.add_argument("--L", type=int, default=100)
    p.add_argument("--K", type=int, default=30)
    p.add_argument("--N", type=int, default=8)
    p.add_argument("--K-list", type=int, nargs="+", default=[25, 30, 35, 40, 45])
    p.add_argument("--N-list", type=int, nargs="+", default=[1, 2, 4, 8])
    p.add_argument("--setups", type=int, default=20, help="Paper uses 200; default is smaller for testing")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--delta", type=float, default=95.0)
    p.add_argument("--baseline-tau-p", type=int, default=10)
    p.add_argument("--beam-detect-snr-db", type=float, default=0.0)
    p.add_argument("--w-aa", type=float, default=1.0, help="Weight for active-active beam overlap in proposed/matching graphs")
    p.add_argument("--w-ai", type=float, default=1.0, help="Weight for active-moderate beam overlap in proposed/matching graphs")
    p.add_argument("--w-ia", type=float, default=1.0, help="Weight for moderate-active beam overlap in proposed/matching graphs")
    p.add_argument("--edge-threshold", type=float, default=0.0, help="Create interference edge if weighted overlap is greater than this threshold")
    p.add_argument("--matching-resource-quota", type=int, default=0, help="Quota per AP-beam resource for MatchingBeam schemes; 0 means baseline_tau_p")
    p.add_argument("--topap-top-n", type=int, default=10, help="Top-N APs for AP-domain TopAP/H4 hybrids")
    p.add_argument("--h3-topap-n", type=int, default=8, help="Top-N APs for H3 TopAP adaptive")
    p.add_argument("--topap-bisect-min", type=int, default=2, help="Minimum N for TopAP-bisect")
    p.add_argument("--topap-bisect-max", type=int, default=40, help="Maximum N for TopAP-bisect")
    p.add_argument("--topap-bisect-iters", type=int, default=20, help="Maximum bisection iterations for TopAP-bisect")
    p.add_argument("--power-control", choices=["maxmin", "full"], default="maxmin")
    p.add_argument("--power-model", choices=["ref12-rf", "ref12-strict", "simple"], default="ref12-rf")
    p.add_argument("--fronthaul-mode", choices=["all_users", "active_users", "active_rf"], default="active_users")
    p.add_argument("--greedy-iters", type=int, default=8)
    p.add_argument("--wgf-refine-iters", type=int, default=8)
    p.add_argument("--maxmin-maxiter", type=int, default=250)
    p.add_argument("--maxmin-restarts", type=int, default=2)
    p.add_argument("--outdir", type=str, default="all_scheme_results")
    p.add_argument("--plot", action="store_true")
    p.add_argument("--pilot-boxplot", action="store_true", help="Save boxplots of per-setup actual pilot counts tau_p")
    p.add_argument("--pilot-boxplot-schemes", nargs="+", default=None, help="Subset of schemes to include in the pilot-count boxplot; defaults to --schemes")
    p.add_argument("--pilot-boxplot-points", action="store_true", help="Overlay setup-level points on the pilot-count boxplot")
    p.add_argument("--pilot-boxplot-csv", action="store_true", help="Also save per-setup tau_p values used by the pilot-count boxplot")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


def cfg_from_args(args: argparse.Namespace, K: Optional[int] = None, N: Optional[int] = None, seed_offset: int = 0) -> SimConfig:
    return SimConfig(
        L=args.L,
        K=args.K if K is None else int(K),
        N=args.N if N is None else int(N),
        delta_active_percent=args.delta,
        baseline_tau_p=args.baseline_tau_p,
        beam_detect_snr_db=args.beam_detect_snr_db,
        seed=args.seed + seed_offset,
        w_aa=args.w_aa,
        w_ai=args.w_ai,
        w_ia=args.w_ia,
        edge_threshold=args.edge_threshold,
        matching_resource_quota=args.matching_resource_quota,
        topap_top_n=args.topap_top_n,
        h3_topap_n=args.h3_topap_n,
        topap_bisect_min=args.topap_bisect_min,
        topap_bisect_max=args.topap_bisect_max,
        topap_bisect_iters=args.topap_bisect_iters,
        power_control=args.power_control,
        power_model=args.power_model,
        fronthaul_mode=args.fronthaul_mode,
        greedy_iters=args.greedy_iters,
        wgf_refine_iters=args.wgf_refine_iters,
        maxmin_maxiter=args.maxmin_maxiter,
        maxmin_restarts=args.maxmin_restarts,
    )


def canonical_schemes(schemes: Sequence[str]) -> List[str]:
    names = []
    for s in schemes:
        sl = s.lower()
        if sl == "random":
            names.append("Random")
        elif sl == "greedy":
            names.append("Greedy")
        elif sl == "wgf":
            names.append("WGF")
        elif sl == "gc":
            names.append("GC")
        elif sl == "proposed":
            names.append("Proposed")
        elif sl in {"matching-fixed", "matching_fixed", "matchingbeamfixed"}:
            names.append("MatchingBeamFixed")
        elif sl in {"matching-adaptive", "matching_adaptive", "matchingbeamadaptive"}:
            names.append("MatchingBeamAdaptive")
        elif sl in {"topap-bisect", "topap_bisect", "topapbisect"}:
            names.append("TopAPBisect")
        elif sl in {"h2", "h2-gao-greedy", "h2_gao_greedy", "h2gaogreedy"}:
            names.append("H2GaoGreedy")
        elif sl in {"h3", "h3-topap-adaptive", "h3_topap_adaptive", "h3topapadaptive", "topap-adaptive"}:
            names.append("H3TopAPAdaptive")
        elif sl in {"h4", "h4-topap-greedy", "h4_topap_greedy", "h4topapgreedy", "topap-greedy"}:
            names.append("H4TopAPGreedy")
        else:
            raise ValueError(f"Unknown scheme {s}")
    return names


def run_fig1(args: argparse.Namespace, schemes: List[str], outdir: str) -> Dict[str, SchemeMetrics]:
    cfg = cfg_from_args(args, K=30, N=8, seed_offset=0)
    metrics = run_simulation(cfg, args.setups, schemes, verbose=not args.quiet)
    print_metrics_table(metrics, cfg)
    if args.plot:
        plot_ecdf(metrics, os.path.join(outdir, "fig1_ecdf_vs_se_all_schemes.png"))
    maybe_plot_pilot_boxplot(
        args,
        metrics,
        schemes,
        outdir,
        tag="fig1",
        title="Pilot count distribution, Fig.1 setting (K=30, N=8)",
    )
    return metrics


def run_sweep_n(args: argparse.Namespace, schemes: List[str], outdir: str) -> List[Tuple[int, Dict[str, Tuple]]]:
    rows = []
    metric_objects_by_n: List[Tuple[int, Dict[str, SchemeMetrics]]] = []
    for idx, N in enumerate(args.N_list):
        print(f"\n######## Sweep N={N} ########")
        cfg = cfg_from_args(args, K=30, N=N, seed_offset=1000 * idx)
        metrics = run_simulation(cfg, args.setups, schemes, verbose=not args.quiet)
        print_metrics_table(metrics, cfg)
        rows.append((N, {name: metrics_to_tuple(metrics[name]) for name in metrics}))
        metric_objects_by_n.append((N, metrics))
        maybe_plot_pilot_boxplot(
            args,
            metrics,
            schemes,
            outdir,
            tag=f"sweep_N_{N}",
            title=f"Pilot count distribution, N={N} (K=30)",
        )
    if args.plot:
        xvals = list(args.N_list)
        plot_sweep(xvals, rows, "Average SE [bit/s/Hz/user]", 0, "Average SE vs Number of antennas", "Number of antennas N", os.path.join(outdir, "fig2a_avg_se_vs_antennas_all_schemes.png"))
        plot_sweep(xvals, rows, "Average EE [bit/Joule/Hz]", 2, "Average EE vs Number of antennas", "Number of antennas N", os.path.join(outdir, "fig2b_avg_ee_vs_antennas_all_schemes.png"))
    csv_rows = []
    for x, d in rows:
        for name, vals in d.items():
            csv_rows.append((x, name, *vals))
    save_csv(os.path.join(outdir, "sweep_N_all_schemes.csv"), ["N", "scheme", "avgSE", "likely95SE", "avgEE", "avgTauP", "avgRF", "avgEdges"], csv_rows)
    if getattr(args, "pilot_boxplot", False):
        combined = combine_tau_metrics(metric_objects_by_n)
        maybe_plot_pilot_boxplot(
            args,
            combined,
            schemes,
            outdir,
            tag="sweep_N_all_points",
            title="Pilot count distribution across all N sweep points",
        )
    return rows


def run_sweep_k(args: argparse.Namespace, schemes: List[str], outdir: str) -> List[Tuple[int, Dict[str, Tuple]]]:
    rows = []
    metric_objects_by_k: List[Tuple[int, Dict[str, SchemeMetrics]]] = []
    for idx, K in enumerate(args.K_list):
        print(f"\n######## Sweep K={K} ########")
        cfg = cfg_from_args(args, K=K, N=8, seed_offset=1000 * idx)
        metrics = run_simulation(cfg, args.setups, schemes, verbose=not args.quiet)
        print_metrics_table(metrics, cfg)
        rows.append((K, {name: metrics_to_tuple(metrics[name]) for name in metrics}))
        metric_objects_by_k.append((K, metrics))
        maybe_plot_pilot_boxplot(
            args,
            metrics,
            schemes,
            outdir,
            tag=f"sweep_K_{K}",
            title=f"Pilot count distribution, K={K} (N=8)",
        )
    if args.plot:
        xvals = list(args.K_list)
        plot_sweep(xvals, rows, "Average SE [bit/s/Hz/user]", 0, "Average SE vs Number of users", "Number of users K", os.path.join(outdir, "fig3a_avg_se_vs_users_all_schemes.png"))
        plot_sweep(xvals, rows, "Average EE [bit/Joule/Hz]", 2, "Average EE vs Number of users", "Number of users K", os.path.join(outdir, "fig3b_avg_ee_vs_users_all_schemes.png"))
    csv_rows = []
    for x, d in rows:
        for name, vals in d.items():
            csv_rows.append((x, name, *vals))
    save_csv(os.path.join(outdir, "sweep_K_all_schemes.csv"), ["K", "scheme", "avgSE", "likely95SE", "avgEE", "avgTauP", "avgRF", "avgEdges"], csv_rows)
    if getattr(args, "pilot_boxplot", False):
        combined = combine_tau_metrics(metric_objects_by_k)
        maybe_plot_pilot_boxplot(
            args,
            combined,
            schemes,
            outdir,
            tag="sweep_K_all_points",
            title="Pilot count distribution across all K sweep points",
        )
    return rows


def main() -> None:
    args = parse_args()
    outdir = ensure_dir(args.outdir)
    schemes = canonical_schemes(args.schemes)

    if args.mode == "fig1":
        run_fig1(args, schemes, outdir)
    elif args.mode == "sweep-n":
        run_sweep_n(args, schemes, outdir)
    elif args.mode == "sweep-k":
        run_sweep_k(args, schemes, outdir)
    elif args.mode == "single":
        cfg = cfg_from_args(args)
        metrics = run_simulation(cfg, args.setups, schemes, verbose=not args.quiet)
        print_metrics_table(metrics, cfg)
        if args.plot:
            plot_ecdf(metrics, os.path.join(outdir, "single_ecdf_all_schemes.png"))
        maybe_plot_pilot_boxplot(
            args,
            metrics,
            schemes,
            outdir,
            tag="single",
            title=f"Pilot count distribution, single setting (K={cfg.K}, N={cfg.N})",
        )
    elif args.mode == "all":
        run_fig1(args, schemes, outdir)
        run_sweep_n(args, schemes, outdir)
        run_sweep_k(args, schemes, outdir)


if __name__ == "__main__":
    main()
