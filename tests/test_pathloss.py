from __future__ import annotations

import numpy as np

from src.config import SimulationConfig
from src.network import ngo_2017_pathloss_db, wraparound_distances


def test_pathloss_is_constant_below_d0_and_decreases_after() -> None:
    config = SimulationConfig(shadow_std_db=0.0)
    distances = np.array([1.0, 10.0, 50.0, 100.0])
    beta_db = ngo_2017_pathloss_db(distances, config)

    assert np.isclose(beta_db[0], beta_db[1])
    assert beta_db[1] > beta_db[2]
    assert beta_db[2] > beta_db[3]


def test_wraparound_uses_shortest_torus_distance() -> None:
    ue = np.array([[990.0, 500.0]])
    ap = np.array([[10.0, 500.0]])
    distance = wraparound_distances(ue, ap, area_size_m=1000.0)
    assert np.isclose(distance[0, 0], 20.0)
