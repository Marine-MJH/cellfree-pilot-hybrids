from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import SimulationConfig, db_to_linear


@dataclass
class Network:
    """Topology and large-scale fading for a cell-free massive MIMO snapshot.

    When ``config.num_antennas_per_ap > 1`` a beam-domain power profile is
    also built (``beam_powers`` shape ``(K, M, N)``). Schemes that need
    beam-domain info call :meth:`beam_info` to obtain Mussbah-style
    ``(B_active, B_inactive)`` binary matrices.

    When ``config.pathloss_model == "umi3gpp"`` an additional ``is_los``
    boolean mask of shape ``(K, M)`` records per-link LoS / NLoS draw
    used to set Rician K-factor in the multi-antenna channel model.
    """

    config: SimulationConfig
    ap_positions_m: np.ndarray
    ue_positions_m: np.ndarray
    distances_m: np.ndarray
    beta: np.ndarray
    beta_db: np.ndarray
    beam_powers: np.ndarray | None = None  # (K, M, N) or None for single-antenna
    is_los: np.ndarray | None = None  # (K, M) bool, only set when pathloss_model="umi3gpp"
    ap_rotations_rad: np.ndarray | None = None  # (M,), ULA local-frame rotation per AP

    @classmethod
    def random(
        cls,
        config: SimulationConfig,
        rng: np.random.Generator | None = None,
        *,
        num_aps: int | None = None,
        num_ues: int | None = None,
    ) -> "Network":
        rng = np.random.default_rng(config.random_seed) if rng is None else rng
        k = config.num_aps if num_aps is None else num_aps
        m = config.num_ues if num_ues is None else num_ues

        ap_positions = rng.uniform(0.0, config.area_size_m, size=(k, 2))
        ue_positions = rng.uniform(0.0, config.area_size_m, size=(m, 2))
        distances = wraparound_distances(
            ue_positions,
            ap_positions,
            config.area_size_m,
            height_delta_m=config.ap_height_m - config.ue_height_m,
        )
        distances_2d = wraparound_distances(
            ue_positions,
            ap_positions,
            config.area_size_m,
            height_delta_m=0.0,
        )
        is_los: np.ndarray | None = None
        if config.pathloss_model == "umi3gpp":
            from .pathloss_umi import umi_channel_gain_db

            beta_db, is_los = umi_channel_gain_db(
                distances_2d,
                h_bs_m=config.ap_height_m,
                h_ut_m=config.ue_height_m,
                fc_ghz=config.carrier_frequency_mhz / 1000.0,
                rng=rng,
            )
        else:
            beta_db = ngo_2017_pathloss_db(distances, config)
            if config.shadow_std_db > 0:
                beta_db = beta_db + rng.normal(
                    0.0, config.shadow_std_db, size=beta_db.shape
                )
        beta = db_to_linear(beta_db)

        beam_powers = None
        ap_rotations: np.ndarray | None = None
        if config.num_antennas_per_ap > 1:
            if config.ap_orientation == "random":
                ap_rotations = rng.uniform(0.0, 2 * np.pi, size=k)
            else:
                ap_rotations = np.zeros(k)
            beam_powers = compute_beam_powers(
                beta,
                ue_positions,
                ap_positions,
                config.area_size_m,
                num_antennas=config.num_antennas_per_ap,
                angular_spread_rad=config.angular_spread_rad,
                one_ring_radius_m=config.one_ring_radius_m,
                distances_m=distances,
                ap_rotations_rad=ap_rotations,
                rng=rng,
            )
        return cls(
            config,
            ap_positions,
            ue_positions,
            distances,
            beta,
            beta_db,
            beam_powers,
            is_los,
            ap_rotations,
        )

    @property
    def num_ues(self) -> int:
        return self.beta.shape[0]

    @property
    def num_aps(self) -> int:
        return self.beta.shape[1]

    @property
    def num_antennas_per_ap(self) -> int:
        if self.beam_powers is None:
            return 1
        return int(self.beam_powers.shape[2])

    def all_serving_mask(self) -> np.ndarray:
        return np.ones_like(self.beta, dtype=bool)

    def strongest_ap_mask(self, quota_per_ue: int = 1) -> np.ndarray:
        quota = int(np.clip(quota_per_ue, 1, self.num_aps))
        order = np.argsort(-self.beta, axis=1)[:, :quota]
        mask = np.zeros_like(self.beta, dtype=bool)
        rows = np.arange(self.num_ues)[:, None]
        mask[rows, order] = True
        return mask

    # ------------------------------------------------------------------
    # Beam-domain support (Mussbah 2024)
    # ------------------------------------------------------------------
    def beam_flattened(self) -> "Network":
        """Return a virtual single-antenna Network where each beam is one AP.

        Mussbah_reproduce_plan.md §6.1: simplified reproduce path. Each
        ``(AP m, beam n)`` pair is treated as one virtual AP with
        ``β_{k, m·N+n} = beam_powers[k, m, n]``. AP positions are duplicated
        per beam (same physical location, separate virtual identity).

        Useful for evaluating any single-antenna pilot scheme on the
        beam-domain power profile without implementing the full multi-
        antenna SE closed-form (Mussbah Eq.9-14). Comparison between
        algorithms is fair under this surrogate; absolute throughput is
        not directly comparable to Mussbah paper figures because of
        channel-model and SE-formula differences.
        """
        if self.beam_powers is None:
            return self
        K, M, N = self.beam_powers.shape
        new_beta = self.beam_powers.reshape(K, M * N)
        new_ap_pos = np.repeat(self.ap_positions_m, N, axis=0)
        new_distances = np.repeat(self.distances_m, N, axis=1)
        new_beta_db = 10.0 * np.log10(np.maximum(new_beta, 1e-300))
        new_config = self.config.with_updates(
            num_aps=M * N, num_antennas_per_ap=1
        )
        return Network(
            config=new_config,
            ap_positions_m=new_ap_pos,
            ue_positions_m=self.ue_positions_m,
            distances_m=new_distances,
            beta=new_beta,
            beta_db=new_beta_db,
            beam_powers=None,
        )

    def beam_info(
        self,
        delta: float = 0.95,
        *,
        snr_threshold_db: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        if snr_threshold_db is None:
            snr_threshold_db = self.config.beam_detection_snr_db
        """Mussbah Algorithm 1 inputs: (B_active, B_inactive).

        Paper §V: "we assume that any beam with a signal-to-noise ratio
        greater than zero can be detected and is reported to the CPU".
        The reported set ``B_k`` is therefore the *detected* set — beams
        whose per-beam SNR ≥ ``snr_threshold_db`` (default 0 dB). Among
        the reported beams, the smallest prefix whose cumulative power
        reaches ``delta · total_reported_power`` is the *active* set;
        the remaining reported beams are *inactive* (Eq. 2 + Eq. 16).

        Returns boolean matrices of shape ``(L=M*N, K)`` matching
        Eq.(15)/(16).
        """
        if self.beam_powers is None:
            raise RuntimeError(
                "Network.beam_info requires num_antennas_per_ap > 1. "
                "Configure SimulationConfig(num_antennas_per_ap=N>1)."
            )
        bp = self.beam_powers  # (K, M, N)
        K, M, N = bp.shape
        flat = bp.reshape(K, M * N)
        L = M * N

        # Detection threshold (per-beam SNR ≥ snr_threshold_db).
        # Per-beam received signal power = pilot_power · β_beam.
        # Detected iff (pilot_power · β_beam) / noise_power ≥ 10^(threshold_db/10).
        pilot_power = self.config.pilot_power_w
        noise_power = self.config.noise_power_w
        threshold_lin = 10.0 ** (snr_threshold_db / 10.0)
        beam_min_power = threshold_lin * noise_power / max(pilot_power, 1e-30)
        reported_kl = flat >= beam_min_power  # (K, L)

        # Mask out non-detected beams from the cumulative sort so they cannot
        # be picked into the active set.
        flat_masked = np.where(reported_kl, flat, 0.0)
        order = np.argsort(-flat_masked, axis=1)
        sorted_powers = np.take_along_axis(flat_masked, order, axis=1)
        totals = sorted_powers.sum(axis=1, keepdims=True)
        cumulative = np.cumsum(sorted_powers, axis=1)
        target = float(delta) * totals
        # Number of beams to keep per UE (at least 1 even if all undetected)
        keep = (cumulative < target).sum(axis=1) + 1
        keep = np.minimum(keep, L)

        rank = np.empty_like(order)
        rank[np.arange(K)[:, None], order] = np.arange(L)[None, :]
        is_active_kl = (rank < keep[:, None]) & reported_kl
        # Edge case: UE with zero reported beams — pick strongest beam by all measures
        zero_reported = ~reported_kl.any(axis=1)
        if zero_reported.any():
            strongest = np.argmax(flat[zero_reported], axis=1)
            for idx, k_idx in enumerate(np.flatnonzero(zero_reported)):
                is_active_kl[k_idx] = False
                is_active_kl[k_idx, strongest[idx]] = True
                reported_kl[k_idx, strongest[idx]] = True
        is_inactive_kl = reported_kl & ~is_active_kl

        b_active = is_active_kl.T.astype(np.int32)
        b_inactive = is_inactive_kl.T.astype(np.int32)
        return b_active, b_inactive


def compute_beam_powers(
    beta: np.ndarray,
    ue_positions_m: np.ndarray,
    ap_positions_m: np.ndarray,
    area_size_m: float,
    *,
    num_antennas: int,
    angular_spread_rad: float = 0.0,
    one_ring_radius_m: float = 0.0,
    distances_m: np.ndarray | None = None,
    ap_rotations_rad: np.ndarray | None = None,
    rng: np.random.Generator | None = None,
    num_paths: int = 8,
) -> np.ndarray:
    """Beam-domain large-scale power profile per (UE, AP, beam).

    Channel models supported (mutually exclusive, in priority order):

    - **One-ring** (when ``one_ring_radius_m > 0``): Mussbah 2024 paper-faithful
      Shiu 2000 model. Scatterers uniformly distributed on a ring of radius
      ``one_ring_radius_m`` around the UE. Half angular spread per (k, m)
      ``Δ_{km} = arctan(r_ring / d_{km})``, with ``d_{km}`` the UE-AP distance.
      Multipath offsets uniform in ``[-Δ, +Δ]`` — narrow when d ≫ r, wide when
      d ~ r.
    - **Gaussian** (when ``angular_spread_rad > 0`` and ``one_ring_radius_m == 0``):
      ``num_paths`` MC offsets with std ``angular_spread_rad``.
    - **Single-path** (both 0): deterministic geometric AoA only.

    ULA half-wavelength assumed; AP orientation = 0 (pointing +x). Per-AP
    N-point DFT.

    Returns ``beam_powers`` of shape ``(K, M, N)`` with
    ``beam_powers[k, m, n] = β_{km} · E_p [|F_n^H · a(θ_p)|^2 / N]``.
    Energy-preserving: summing over n equals ``β_{km}`` in expectation.
    """
    K, M = beta.shape
    N = int(num_antennas)
    diff = ue_positions_m[:, None, :] - ap_positions_m[None, :, :]  # (K, M, 2)
    diff = ((diff + area_size_m / 2.0) % area_size_m) - area_size_m / 2.0
    theta_geom = np.arctan2(diff[..., 1], diff[..., 0])  # (K, M)
    # Subtract per-AP orientation so the steering vector argument is in the
    # AP's local frame (ULA broadside aligned with the AP's rotation angle).
    if ap_rotations_rad is not None:
        theta_geom = theta_geom - ap_rotations_rad[None, :]

    if one_ring_radius_m > 0.0:
        if distances_m is None:
            raise ValueError("distances_m required for one-ring model.")
        if rng is None:
            rng = np.random.default_rng()
        # Half angular spread per (k, m) from one-ring geometry. Clipped at π/2
        # so that very close UE-AP pairs (d < r) get a full 180° spread.
        delta_half = np.arctan(one_ring_radius_m / np.maximum(distances_m, 1e-6))
        delta_half = np.minimum(delta_half, np.pi / 2)
        u = rng.uniform(-1.0, 1.0, size=(K, M, num_paths))
        offsets = delta_half[..., None] * u  # uniform in [-Δ, +Δ]
        thetas = theta_geom[..., None] + offsets
        P = num_paths
    elif angular_spread_rad > 0.0:
        if rng is None:
            rng = np.random.default_rng()
        offsets = rng.normal(0.0, angular_spread_rad, size=(K, M, num_paths))
        thetas = theta_geom[..., None] + offsets
        P = num_paths
    else:
        thetas = theta_geom[..., None]  # (K, M, 1)
        P = 1

    n_idx = np.arange(N)
    sin_theta = np.sin(thetas)  # (K, M, P)
    phases = np.pi * sin_theta[..., None] * n_idx[None, None, None, :]  # (K, M, P, N)
    a = np.exp(1j * phases)  # (K, M, P, N)

    l_idx = np.arange(N)
    F = np.exp(-2j * np.pi * np.outer(n_idx, l_idx) / N) / np.sqrt(N)  # (N, N)
    beam_amp = np.einsum("nl,kmpn->kmpl", F.conj(), a)
    beam_power_per_path = (np.abs(beam_amp) ** 2) / N
    beam_power = beam_power_per_path.mean(axis=2)  # (K, M, N)
    return beta[..., None] * beam_power


def wraparound_distances(
    ue_positions_m: np.ndarray,
    ap_positions_m: np.ndarray,
    area_size_m: float,
    *,
    height_delta_m: float = 0.0,
) -> np.ndarray:
    """Compute torus/wrap-around UE-AP distances in meters."""

    delta = np.abs(ue_positions_m[:, None, :] - ap_positions_m[None, :, :])
    delta = np.minimum(delta, area_size_m - delta)
    horizontal = np.linalg.norm(delta, axis=2)
    return np.sqrt(horizontal**2 + height_delta_m**2)


def ngo_2017_pathloss_db(distance_m: np.ndarray, config: SimulationConfig) -> np.ndarray:
    """Three-slope path loss from Ngo et al.; output is channel gain in dB.

    The model uses distances in km inside the logarithms. The config exposes
    d0/d1 in meters because that is easier to read alongside the paper.
    """

    distance_km = np.maximum(np.asarray(distance_m, dtype=float) / 1000.0, 1e-9)
    d0 = config.pathloss_d0_m / 1000.0
    d1 = config.pathloss_d1_m / 1000.0
    f = config.carrier_frequency_mhz
    h_ap = config.ap_height_m
    h_ue = config.ue_height_m

    l_const = (
        46.3
        + 33.9 * np.log10(f)
        - 13.82 * np.log10(h_ap)
        - (1.1 * np.log10(f) - 0.7) * h_ue
        + (1.56 * np.log10(f) - 0.8)
    )

    beta_db = np.empty_like(distance_km)
    far = distance_km > d1
    middle = (distance_km > d0) & ~far
    near = ~far & ~middle

    beta_db[far] = -l_const - 35.0 * np.log10(distance_km[far])
    beta_db[middle] = -l_const - 15.0 * np.log10(d1) - 20.0 * np.log10(distance_km[middle])
    beta_db[near] = -l_const - 15.0 * np.log10(d1) - 20.0 * np.log10(d0)
    return beta_db
