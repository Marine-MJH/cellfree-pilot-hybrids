"""Mussbah et al. (2024) beam-domain pilot assignment (Algorithm 1).

Reference:
    M. Mussbah, S. Schwarz, M. Rupp,
    "Beam-Domain-Based Pilot Assignment for Energy Efficient Cell-Free
    Massive MIMO," IEEE Commun. Lett., vol. 28, no. 9, pp. 2176-2180,
    Sep. 2024.

The paper assumes multi-antenna APs and beam-domain processing. This
module implements the algorithm proper (interference graph + Dsatur
coloring) in a system-model-agnostic way: the caller supplies the active
and inactive beam-user association matrices, and this class returns
pilot indices. A multi-antenna Network that synthesises those matrices
is a separate, larger work and remains a stub (see :func:`assign`).

Equations referenced below are from the published paper.

Algorithm 1 outline:

1. For each user k, determine the active beam set ``B_k^(a)`` via Eq. (2)
   (a δ-threshold cumulative-power rule — caller's responsibility here).
2. Construct ``B^(a) ∈ {0,1}^{L·N × K}`` (Eq. 15) and ``B^(i) ∈ {0,1}^{L·N × K}``
   (Eq. 16): active-beams and inactive-but-reported beams per user.
3. Compute ``B = B^(a)ᵀ B^(a) + B^(a)ᵀ B^(i) + B^(i)ᵀ B^(a)`` (Eq. 17).
   Element ``B[i,j]`` counts beam-overlap-relations between users i and j.
4. Adjacency ``A[i,j] = 1`` iff ``B[i,j] > 0`` and ``i ≠ j`` (Eq. 18).
5. Apply Dsatur (saturation-degree) graph coloring to ``A``. Each color
   becomes a pilot. The pilot count ``τ_p`` adapts to the chromatic number.

If the caller fixes ``τ_p`` (typical for cross-scheme comparison), this
implementation folds excess colors via modulo and tolerates spare pilots
when fewer colors are used.
"""

from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class BeamDomainPilotAssignment(PilotAssignmentScheme):
    """Mussbah 2024 beam-domain pilot assignment (Algorithm 1).

    Two entry points:

    - :meth:`assign` — the standard ``PilotAssignmentScheme`` interface. Requires
      a multi-antenna :class:`Network` exposing beam-domain information via
      ``network.beam_info(delta)`` returning ``(B_active, B_inactive)``. The
      base :class:`Network` does not yet provide this, so this method raises
      ``NotImplementedError`` until the multi-antenna extension lands.
    - :meth:`assign_from_beam_info` — algorithm-only entry point. Pass the
      ``B_active`` / ``B_inactive`` matrices directly; useful for unit tests
      and for any caller that builds beam info externally.
    """

    name = "Mussbah beam-domain"

    def __init__(
        self,
        seed: int | None = None,
        *,
        delta: float = 0.95,
        adaptive_tau_p: bool = False,
    ) -> None:
        super().__init__(seed)
        self.delta = float(delta)
        # Paper §V.A: "the proposed scheme requires fewer pilots and therefore
        # reduces the training overhead". With ``adaptive_tau_p=True`` we
        # return raw Dsatur colors (no modulo wrap to τ_p), letting the
        # downstream SE formula see the actual number of distinct pilots used.
        self.adaptive_tau_p = bool(adaptive_tau_p)
        # Diagnostics populated by the last assignment call:
        self.n_colors_used_: int | None = None
        self.adjacency_: np.ndarray | None = None

    # ------------------------------------------------------------------
    # Standard interface — requires a multi-antenna Network (not yet built)
    # ------------------------------------------------------------------
    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        beam_info = getattr(network, "beam_info", None)
        if beam_info is None:
            raise NotImplementedError(
                "BeamDomainPilotAssignment.assign requires a Network with "
                "multi-antenna beam-domain support (Network.beam_info). "
                "Use assign_from_beam_info() for algorithm-only testing."
            )
        b_active, b_inactive = beam_info(delta=self.delta)
        self.reset()
        return self.assign_from_beam_info(b_active, b_inactive, tau_p)

    # ------------------------------------------------------------------
    # Algorithm-only entry point
    # ------------------------------------------------------------------
    def assign_from_beam_info(
        self,
        b_active: np.ndarray,
        b_inactive: np.ndarray,
        tau_p: int,
    ) -> np.ndarray:
        """Run Mussbah Algorithm 1 from explicit beam-user matrices.

        Parameters
        ----------
        b_active, b_inactive
            Boolean / 0-1 matrices of shape ``(L·N, K)``. ``b_active[b,k] = 1``
            iff beam index ``b`` is in user ``k``'s active beam set ``B_k^(a)``.
            Likewise ``b_inactive[b,k] = 1`` iff beam ``b`` is in the reported
            set ``B_k`` but not in ``B_k^(a)``.
        tau_p
            Target number of pilots. Colors used by Dsatur are clipped to
            ``[0, tau_p)`` via modulo if the chromatic number exceeds ``tau_p``.

        Returns
        -------
        pilots
            Pilot index per user, shape ``(K,)``.
        """
        b_act = np.asarray(b_active, dtype=np.int32)
        b_in = np.asarray(b_inactive, dtype=np.int32)
        if b_act.shape != b_in.shape:
            raise ValueError(
                f"b_active and b_inactive must share shape, got "
                f"{b_act.shape} vs {b_in.shape}"
            )

        # Eq. (17): B = B^(a)ᵀ B^(a) + B^(a)ᵀ B^(i) + B^(i)ᵀ B^(a)
        interference = b_act.T @ b_act + b_act.T @ b_in + b_in.T @ b_act
        # Eq. (18): adjacency
        adjacency = interference > 0
        np.fill_diagonal(adjacency, False)
        self.adjacency_ = adjacency

        colors = self._dsatur_coloring(adjacency)
        self.n_colors_used_ = int(colors.max(initial=-1) + 1)
        return self._adapt_to_tau_p(colors, tau_p)

    # ------------------------------------------------------------------
    # Dsatur graph coloring
    # ------------------------------------------------------------------
    def _dsatur_coloring(self, adjacency: np.ndarray) -> np.ndarray:
        """Dsatur algorithm (Brélaz 1979). At each step pick the uncolored
        vertex with maximum saturation degree (number of distinct colors
        among already-colored neighbors), breaking ties by highest plain
        degree, then assign the smallest color not used by its neighbors.
        """

        adj = np.asarray(adjacency, dtype=bool)
        K = adj.shape[0]
        if K == 0:
            return np.empty(0, dtype=int)

        colors = np.full(K, -1, dtype=int)
        degree = adj.sum(axis=1).astype(int)
        # saturation[v] = number of distinct colors among colored neighbors
        saturation = np.zeros(K, dtype=int)
        # Pre-allocated bitset for neighbor color tracking per vertex
        neighbor_color_sets: list[set[int]] = [set() for _ in range(K)]

        for _ in range(K):
            uncolored = np.flatnonzero(colors < 0)
            if uncolored.size == 0:
                break
            sat_un = saturation[uncolored]
            max_sat = sat_un.max()
            mask = sat_un == max_sat
            candidates = uncolored[mask]
            if candidates.size > 1:
                deg = degree[candidates]
                v = int(candidates[int(np.argmax(deg))])
            else:
                v = int(candidates[0])

            # Smallest color not in v's neighbor color set
            blocked = neighbor_color_sets[v]
            c = 0
            while c in blocked:
                c += 1
            colors[v] = c

            # Propagate saturation update to v's uncolored neighbors
            for u in np.flatnonzero(adj[v]):
                if colors[u] >= 0:
                    continue
                ncs = neighbor_color_sets[u]
                if c not in ncs:
                    ncs.add(c)
                    saturation[u] = len(ncs)

        return colors

    # ------------------------------------------------------------------
    # τ_p adaptation
    # ------------------------------------------------------------------
    def _adapt_to_tau_p(self, colors: np.ndarray, tau_p: int) -> np.ndarray:
        if self.adaptive_tau_p:
            return colors.astype(int)
        max_color = int(colors.max(initial=-1)) + 1
        if max_color <= tau_p:
            return colors.astype(int)
        return (colors % tau_p).astype(int)
