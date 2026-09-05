from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Metabolism:
    hosting_per_hour: float
    inference_per_cycle: float
    committed_monthly: float
    cycles_last_hour: int

    def burn_per_hour(self) -> float:
        return (
            self.hosting_per_hour
            + self.inference_per_cycle * self.cycles_last_hour
            + self.committed_monthly / 730
        )
