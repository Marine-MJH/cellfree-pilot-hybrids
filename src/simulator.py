from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

from .config import SimulationConfig
from .metrics import likely_95, per_ue_throughput_bps
from .network import Network
from .pilot_schemes.base import PilotAssignmentScheme
from .power_control import PowerControl


@dataclass
class SimulationRun:
    throughputs_bps: np.ndarray
    pilot_assignment: np.ndarray
    powers_w: np.ndarray
    serving_mask: np.ndarray


class Simulator:
    def __init__(self, config: SimulationConfig, seed: int | None = None) -> None:
        self.config = config
        self.rng = np.random.default_rng(config.random_seed if seed is None else seed)

    def run_once(
        self,
        scheme: PilotAssignmentScheme,
        power_control: PowerControl,
        *,
        num_ues: int | None = None,
        num_aps: int | None = None,
        tau_p: int | None = None,
    ) -> SimulationRun:
        tau = self.config.tau_p if tau_p is None else tau_p
        network = Network.random(self.config, self.rng, num_ues=num_ues, num_aps=num_aps)
        pilot_assignment = scheme.assign(network, tau)
        serving_mask = scheme.serving_matrix(network)
        powers = power_control.compute(network, pilot_assignment, serving_mask=serving_mask)
        throughputs = per_ue_throughput_bps(
            network,
            pilot_assignment,
            powers,
            tau,
            serving_mask=serving_mask,
        )
        return SimulationRun(throughputs, pilot_assignment, powers, serving_mask)

    def collect_throughputs(
        self,
        schemes: list[PilotAssignmentScheme],
        power_control: PowerControl,
        *,
        n_realizations: int,
        num_ues: int | None = None,
        num_aps: int | None = None,
        tau_p: int | None = None,
        show_progress: bool = True,
    ) -> dict[str, np.ndarray]:
        values = {scheme.name: [] for scheme in schemes}
        iterator = range(n_realizations)
        if show_progress:
            iterator = tqdm(iterator, desc=f"MC ({power_control.name})")
        for _ in iterator:
            network = Network.random(self.config, self.rng, num_ues=num_ues, num_aps=num_aps)
            tau = self.config.tau_p if tau_p is None else tau_p
            for scheme in schemes:
                pilot_assignment = scheme.assign(network, tau)
                serving_mask = scheme.serving_matrix(network)
                powers = power_control.compute(network, pilot_assignment, serving_mask=serving_mask)
                throughputs = per_ue_throughput_bps(
                    network,
                    pilot_assignment,
                    powers,
                    tau,
                    serving_mask=serving_mask,
                )
                values[scheme.name].append(throughputs)
        return {name: np.concatenate(chunks) for name, chunks in values.items()}

    def sweep_95_likely(
        self,
        schemes: list[PilotAssignmentScheme],
        power_control: PowerControl,
        *,
        n_realizations: int,
        tau_values: list[int] | None = None,
        ue_values: list[int] | None = None,
        num_aps: int | None = None,
        show_progress: bool = True,
    ) -> pd.DataFrame:
        if (tau_values is None) == (ue_values is None):
            raise ValueError("Provide exactly one of tau_values or ue_values.")

        rows: list[dict[str, float | int | str]] = []
        sweep_values = tau_values if tau_values is not None else ue_values
        label = "tau_p" if tau_values is not None else "num_ues"
        assert sweep_values is not None
        for value in sweep_values:
            tau = value if tau_values is not None else self.config.tau_p
            num_ues = value if ue_values is not None else self.config.num_ues
            throughputs = self.collect_throughputs(
                schemes,
                power_control,
                n_realizations=n_realizations,
                num_ues=num_ues,
                num_aps=num_aps,
                tau_p=tau,
                show_progress=show_progress,
            )
            for scheme_name, values in throughputs.items():
                rows.append(
                    {
                        label: int(value),
                        "scheme": scheme_name,
                        "power_control": power_control.name,
                        "throughput_95_likely_bps": likely_95(values),
                    }
                )
        return pd.DataFrame(rows)
