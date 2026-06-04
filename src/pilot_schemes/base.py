from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..network import Network


class PilotAssignmentScheme(ABC):
    """Common interface for pilot-assignment schemes."""

    name: str = "base"

    def __init__(self, seed: int | None = None) -> None:
        self.rng = np.random.default_rng(seed)
        self.serving_matrix_: np.ndarray | None = None

    @abstractmethod
    def assign(self, network: Network, tau_p: int) -> np.ndarray:
        """Return pilot indices for all UEs, shape (M,)."""

    def serving_matrix(self, network: Network) -> np.ndarray:
        if self.serving_matrix_ is None:
            return network.all_serving_mask()
        return self.serving_matrix_

    def reset(self) -> None:
        self.serving_matrix_ = None
