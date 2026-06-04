from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class UpperBoundPilotAssignment(PilotAssignmentScheme):
    """Orthogonal-pilot upper bound: no pilot contamination is counted."""

    name = "Upper bound"

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        return np.arange(network.num_ues, dtype=int)
