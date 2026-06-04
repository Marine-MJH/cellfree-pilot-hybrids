from __future__ import annotations

import numpy as np

from ..network import Network
from .base import PilotAssignmentScheme


class RandomPilotAssignment(PilotAssignmentScheme):
    name = "Random"

    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        self.reset()
        return self.rng.integers(0, tau_p, size=network.num_ues, endpoint=False)
