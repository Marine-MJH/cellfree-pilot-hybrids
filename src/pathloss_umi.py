"""3GPP TR 38.901 Urban Microcell (UMi-Street Canyon) path loss + LoS probability.

References:
- 3GPP TR 38.901, "Study on channel model for frequencies from 0.5 to 100 GHz",
  Table 7.4.1-1, Table 7.4.2-1.
- Mussbah et al. 2024 §V uses this model with f_c = 5 GHz.

Conventions:
- All distances in meters; carrier frequency in GHz (NOT MHz).
- 2D distance is the horizontal projection; 3D distance includes height delta.
- Returns *channel gain* in dB (= -path_loss_db). Larger (less negative) means
  stronger received power.

For UMi-Street Canyon with h_BS = 10 m, h_UT ∈ [1.5, 22.5] m, 2 GHz ≤ f_c ≤ 100 GHz.
"""

from __future__ import annotations

import numpy as np

C_LIGHT_M_PER_S = 2.998e8


def los_probability_umi(distance_2d_m: np.ndarray) -> np.ndarray:
    """UMi LoS probability (Table 7.4.2-1, 38.901). Independent of UT height
    for h_UT < 23 m."""
    d2d = np.asarray(distance_2d_m, dtype=float)
    return np.where(
        d2d <= 18.0,
        1.0,
        18.0 / np.maximum(d2d, 1e-6)
        + np.exp(-d2d / 36.0) * (1.0 - 18.0 / np.maximum(d2d, 1e-6)),
    )


def _breakpoint_umi_m(h_bs_m: float, h_ut_m: float, fc_ghz: float) -> float:
    """Effective breakpoint distance d'_BP (3GPP TR 38.901 Note 1).

    d'_BP = 4 · h'_BS · h'_UT · f_c / c
    with h'_BS = h_BS - h_E, h'_UT = h_UT - h_E, h_E = 1 m (UMi).
    """
    h_e = 1.0
    return (
        4.0
        * (h_bs_m - h_e)
        * (h_ut_m - h_e)
        * (fc_ghz * 1e9)
        / C_LIGHT_M_PER_S
    )


def pathloss_umi_los_db(
    distance_2d_m: np.ndarray,
    h_bs_m: float,
    h_ut_m: float,
    fc_ghz: float,
) -> np.ndarray:
    """UMi-Street Canyon LoS path loss [dB]. Table 7.4.1-1."""
    d2d = np.asarray(distance_2d_m, dtype=float)
    d3d = np.sqrt(d2d ** 2 + (h_bs_m - h_ut_m) ** 2)
    d2d_safe = np.maximum(d2d, 10.0)
    d3d_safe = np.maximum(d3d, 10.0)
    d_bp = _breakpoint_umi_m(h_bs_m, h_ut_m, fc_ghz)

    pl1 = 32.4 + 21.0 * np.log10(d3d_safe) + 20.0 * np.log10(fc_ghz)
    pl2 = (
        32.4
        + 40.0 * np.log10(d3d_safe)
        + 20.0 * np.log10(fc_ghz)
        - 9.5 * np.log10(d_bp ** 2 + (h_bs_m - h_ut_m) ** 2)
    )
    return np.where(d2d_safe <= d_bp, pl1, pl2)


def pathloss_umi_nlos_db(
    distance_2d_m: np.ndarray,
    h_bs_m: float,
    h_ut_m: float,
    fc_ghz: float,
) -> np.ndarray:
    """UMi-Street Canyon NLoS path loss [dB] = max(PL_LoS, PL_NLoS-prime).

    Table 7.4.1-1, the NLoS formula is bounded below by the LoS PL.
    """
    d2d = np.asarray(distance_2d_m, dtype=float)
    d3d = np.sqrt(d2d ** 2 + (h_bs_m - h_ut_m) ** 2)
    d3d_safe = np.maximum(d3d, 10.0)
    pl_los = pathloss_umi_los_db(d2d, h_bs_m, h_ut_m, fc_ghz)
    pl_nlos_prime = (
        22.4
        + 35.3 * np.log10(d3d_safe)
        + 21.3 * np.log10(fc_ghz)
        - 0.3 * (h_ut_m - 1.5)
    )
    return np.maximum(pl_los, pl_nlos_prime)


def umi_channel_gain_db(
    distance_2d_m: np.ndarray,
    h_bs_m: float,
    h_ut_m: float,
    fc_ghz: float,
    rng: np.random.Generator,
    shadow_std_los_db: float = 4.0,
    shadow_std_nlos_db: float = 7.82,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample UMi channel gains [dB] with per-link LoS/NLoS draw + shadowing.

    Per (UE, AP) link:
    1. Draw LoS indicator with P_LoS(d_2D).
    2. Compute path loss (LoS or NLoS).
    3. Add log-normal shadowing (σ = 4 dB LoS, 7.82 dB NLoS, Table 7.5-6).

    Returns
    -------
    gain_db : array same shape as distance_2d_m, channel gain = -PL + shadowing.
    is_los : bool array same shape, True iff this link drew LoS.
    """
    d2d = np.asarray(distance_2d_m, dtype=float)
    p_los = los_probability_umi(d2d)
    u = rng.uniform(size=d2d.shape)
    is_los = u < p_los

    pl_los = pathloss_umi_los_db(d2d, h_bs_m, h_ut_m, fc_ghz)
    pl_nlos = pathloss_umi_nlos_db(d2d, h_bs_m, h_ut_m, fc_ghz)
    pl_db = np.where(is_los, pl_los, pl_nlos)

    shadow_std = np.where(is_los, shadow_std_los_db, shadow_std_nlos_db)
    shadow = rng.normal(0.0, shadow_std, size=d2d.shape)

    gain_db = -(pl_db) + shadow
    return gain_db, is_los
