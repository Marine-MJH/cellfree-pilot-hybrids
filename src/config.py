from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SimulationConfig:
    """Shared parameters for Gao et al. (2024) reproduction experiments."""

    num_aps: int = 500
    num_ues: int = 200
    tau_p: int = 20
    tau_c: int = 200
    bandwidth_hz: float = 20e6
    carrier_frequency_mhz: float = 1900.0
    area_size_m: float = 1000.0
    ap_height_m: float = 10.0
    ue_height_m: float = 1.65
    ue_max_power_w: float = 0.1
    pilot_power_w: float = 0.1
    noise_psd_dbm_per_hz: float = -174.0
    shadow_std_db: float = 8.0
    pathloss_d0_m: float = 10.0
    pathloss_d1_m: float = 50.0
    random_seed: int = 7
    # Multi-antenna extension (Mussbah 2024). default 1 = single-antenna
    # Gao mode. Mussbah default = 8 antennas per AP in a ULA.
    num_antennas_per_ap: int = 1
    angular_spread_rad: float = 0.0  # 0 = single-path deterministic AoA (Gaussian spread)
    one_ring_radius_m: float = 0.0  # > 0 = one-ring scatterer model (Mussbah default 30 m)
    # Path-loss / LoS model selection
    pathloss_model: str = "ngo2017"  # "ngo2017" (Gao default) or "umi3gpp" (Mussbah default)
    rician_k_los_db: float = 10.0  # LoS Rician K-factor (Mussbah default)
    rician_k_nlos_db: float = -np.inf  # NLoS = pure Rayleigh (K → 0). Used when umi3gpp.
    # AP/ULA orientation. Paper micro-detail not specified — try "random"
    # (each AP has independent ULA rotation) vs "fixed" (all APs ULA broadside
    # at +x). Random is more realistic in real deployments; fixed creates
    # spatial correlation between UEs that see similar AoA structures.
    ap_orientation: str = "fixed"  # "fixed" or "random"
    # Beam detection SNR threshold (paper §V "SNR > 0" — ambiguous interpretation).
    # Default 0 dB; empirically +6 dB matches paper's implied chromatic level.
    beam_detection_snr_db: float = 0.0

    @property
    def noise_power_w(self) -> float:
        noise_dbm = self.noise_psd_dbm_per_hz + 10.0 * np.log10(self.bandwidth_hz)
        return 10.0 ** ((noise_dbm - 30.0) / 10.0)

    def with_updates(self, **kwargs: object) -> "SimulationConfig":
        data = self.__dict__.copy()
        data.update(kwargs)
        return SimulationConfig(**data)


def db_to_linear(value_db: np.ndarray | float) -> np.ndarray | float:
    return 10.0 ** (np.asarray(value_db) / 10.0)


def linear_to_db(value: np.ndarray | float) -> np.ndarray | float:
    return 10.0 * np.log10(np.asarray(value))
