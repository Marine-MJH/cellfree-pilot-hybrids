"""Tests for Mussbah 2024 beam-domain pilot assignment (Algorithm 1).

Covers:

- Eq. (17) / (18) interference matrix and adjacency derivation.
- Dsatur graph coloring correctness on simple structured graphs.
- τ_p adaptation (modulo on excess colors, spare on shortage).
- ``assign()`` raises until a multi-antenna Network is available.
"""

from __future__ import annotations

import numpy as np

from src.config import SimulationConfig
from src.network import Network
from src.pilot_schemes.beam_domain_mussbah import BeamDomainPilotAssignment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_beam_inputs(active_lists, total_beams):
    """Build (B_active, B_inactive) from per-user beam lists.

    Parameters
    ----------
    active_lists : list[list[int]]
        ``active_lists[k]`` = indices of beams in user ``k``'s active set.
    total_beams : int
        Total beam dimension ``L·N`` (rows of the boolean matrices).

    Returns
    -------
    (b_active, b_inactive)
        Both shape ``(total_beams, len(active_lists))``. Here we set
        ``b_inactive = 0`` everywhere so the conflict graph is determined
        purely by active-active overlap (the dominant term in Eq. 17).
    """
    K = len(active_lists)
    b_act = np.zeros((total_beams, K), dtype=np.int32)
    b_in = np.zeros_like(b_act)
    for k, beams in enumerate(active_lists):
        b_act[beams, k] = 1
    return b_act, b_in


# ---------------------------------------------------------------------------
# Algorithm 1 — Eq. (17) and (18)
# ---------------------------------------------------------------------------
def test_interference_and_adjacency_disjoint_beam_sets() -> None:
    """Users with completely disjoint active beam sets should have no edges
    in the conflict graph and therefore all be free to share a pilot."""

    b_act, b_in = _make_beam_inputs(
        active_lists=[[0, 1], [2, 3], [4, 5]],
        total_beams=6,
    )
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=4)

    # With no conflicts every user gets color 0 from Dsatur.
    assert np.all(pilots == 0)
    assert scheme.n_colors_used_ == 1
    # And the adjacency matrix should be all-zero (off-diagonal).
    assert scheme.adjacency_ is not None
    assert not scheme.adjacency_.any()


def test_interference_and_adjacency_overlapping_beam_sets() -> None:
    """Users with shared active beams must end up on different pilots."""

    b_act, b_in = _make_beam_inputs(
        active_lists=[[0, 1], [1, 2], [3, 4]],
        total_beams=5,
    )
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=4)

    # Users 0 and 1 share beam 1 → must have different pilots.
    assert pilots[0] != pilots[1]
    # User 2 is disjoint from both → can reuse either pilot.
    assert scheme.n_colors_used_ == 2


def test_inactive_beam_term_creates_edge() -> None:
    """An inactive-but-reported beam of one user that coincides with an
    active beam of another still triggers a conflict (Eq. 17 captures
    this via the ``B^(a)ᵀB^(i)`` and ``B^(i)ᵀB^(a)`` cross-terms)."""

    b_act = np.zeros((4, 2), dtype=np.int32)
    b_in = np.zeros((4, 2), dtype=np.int32)
    # User 0: active beam 0
    b_act[0, 0] = 1
    # User 1: active beam 2, but inactive beam 0 reported
    b_act[2, 1] = 1
    b_in[0, 1] = 1
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=2)

    # Edge should exist between users 0 and 1 → distinct pilots.
    assert pilots[0] != pilots[1]


# ---------------------------------------------------------------------------
# Dsatur coloring — structured graph cases
# ---------------------------------------------------------------------------
def test_dsatur_on_complete_graph_uses_k_colors() -> None:
    """K_5 (complete graph on 5 vertices) requires exactly 5 colors."""

    b_act = np.eye(5, dtype=np.int32)
    # Make every user share the same single extra beam → all pairs conflict.
    extra = np.ones((1, 5), dtype=np.int32)
    b_act = np.vstack([b_act, extra])
    b_in = np.zeros_like(b_act)
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=10)

    assert scheme.n_colors_used_ == 5
    assert len(set(pilots.tolist())) == 5  # all distinct


def test_dsatur_on_bipartite_uses_two_colors() -> None:
    """A complete bipartite graph K_{3,3} needs only 2 colors."""

    # Construct adjacency by sharing beams between groups {0,1,2} and {3,4,5}.
    # Each user in left has a unique "group beam" shared with each right user.
    K = 6
    L = 9  # one shared beam per left-right pair
    b_act = np.zeros((L, K), dtype=np.int32)
    b_idx = 0
    for left in range(3):
        for right in range(3, 6):
            b_act[b_idx, left] = 1
            b_act[b_idx, right] = 1
            b_idx += 1
    b_in = np.zeros_like(b_act)
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=5)

    assert scheme.n_colors_used_ == 2
    # Left users share one color, right users the other.
    left_colors = set(pilots[:3].tolist())
    right_colors = set(pilots[3:].tolist())
    assert left_colors.isdisjoint(right_colors)


# ---------------------------------------------------------------------------
# τ_p adaptation
# ---------------------------------------------------------------------------
def test_tau_p_adapts_via_modulo_when_chromatic_exceeds_target() -> None:
    """If Dsatur needs more colors than τ_p, the output collapses via modulo
    (matches the Liu-style clipping used elsewhere)."""

    # K_4 — needs 4 colors.
    b_act = np.eye(4, dtype=np.int32)
    extra = np.ones((1, 4), dtype=np.int32)
    b_act = np.vstack([b_act, extra])
    b_in = np.zeros_like(b_act)
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=2)

    assert scheme.n_colors_used_ == 4
    # Folded into [0, 2). At least one conflict pair must reuse a pilot.
    assert pilots.max() < 2


def test_tau_p_allows_spare_when_chromatic_below_target() -> None:
    """If only a couple of colors are needed but τ_p is large, the output
    stays in the low color range with spare pilots unused."""

    b_act, b_in = _make_beam_inputs([[0], [1]], total_beams=2)
    scheme = BeamDomainPilotAssignment(seed=0)
    pilots = scheme.assign_from_beam_info(b_act, b_in, tau_p=20)

    assert scheme.n_colors_used_ == 1
    assert pilots.max() < 20


# ---------------------------------------------------------------------------
# Standard interface — single-antenna config should raise, multi-antenna works
# ---------------------------------------------------------------------------
def test_assign_raises_when_single_antenna_config() -> None:
    config = SimulationConfig(num_aps=4, num_ues=3, tau_p=2, shadow_std_db=0.0)
    rng = np.random.default_rng(0)
    network = Network.random(config, rng=rng)
    scheme = BeamDomainPilotAssignment(seed=0)
    try:
        scheme.assign(network, tau_p=2)
    except (RuntimeError, NotImplementedError) as exc:
        msg = str(exc).lower()
        assert "beam_info" in msg or "num_antennas" in msg
    else:
        raise AssertionError("Expected RuntimeError or NotImplementedError")


def test_assign_works_with_multi_antenna_network() -> None:
    """Sanity check that Mussbah Algorithm 1 runs end-to-end on a multi-
    antenna network produced by Network.random."""
    config = SimulationConfig(
        num_aps=8, num_ues=6, tau_p=3, shadow_std_db=0.0, num_antennas_per_ap=4
    )
    rng = np.random.default_rng(0)
    network = Network.random(config, rng=rng)
    scheme = BeamDomainPilotAssignment(seed=0, delta=0.95)
    pilots = scheme.assign(network, tau_p=3)
    assert pilots.shape == (config.num_ues,)
    assert pilots.min() >= 0
    assert pilots.max() < 3
    assert scheme.n_colors_used_ is not None
    assert scheme.adjacency_ is not None


def test_network_beam_info_shapes() -> None:
    """beam_info returns (L=M·N, K) shaped binary matrices that are disjoint."""
    config = SimulationConfig(
        num_aps=5, num_ues=4, tau_p=2, shadow_std_db=0.0, num_antennas_per_ap=4
    )
    rng = np.random.default_rng(1)
    network = Network.random(config, rng=rng)
    b_active, b_inactive = network.beam_info(delta=0.9)
    L = config.num_aps * config.num_antennas_per_ap
    assert b_active.shape == (L, config.num_ues)
    assert b_inactive.shape == (L, config.num_ues)
    # Active and inactive are disjoint:
    overlap = b_active & b_inactive
    assert overlap.sum() == 0
    # Every UE has at least one active beam (else cumulative threshold fails):
    assert (b_active.sum(axis=0) >= 1).all()
