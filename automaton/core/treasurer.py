from __future__ import annotations
from typing import Any
from .chain import SimulatedChain
from .constants import (
    CHILD_ENDOWMENT, CYCLE_BUDGET, DEATH_FLOOR_USD,
    MIN_RUNWAY_TO_REPLICATE, REPLICATION_THRESHOLD,
)
from .metabolism import Metabolism

class Treasurer:
    def __init__(self, chain: SimulatedChain, wallet: str, metabolism: Metabolism):
        self.chain = chain
        self.wallet = wallet
        self.metabolism = metabolism
        self._net_7d = 0.0

    def set_net_7d(self, value: float) -> None:
        self._net_7d = value

    def runway_hours(self) -> float:
        balance = self.chain.balance_usd(self.wallet)
        burn = self.metabolism.burn_per_hour()
        if burn <= 0:
            return float("inf")
        return max(0.0, (balance - DEATH_FLOOR_USD) / burn)

    def tick(self) -> dict[str, Any]:
        balance = self.chain.balance_usd(self.wallet)
        runway = self.runway_hours()
        if balance <= DEATH_FLOOR_USD:
            return {"state": "DEAD", "runway_hours": 0.0, "surplus_7d": round(self._net_7d, 2),
                    "cycle_budget": 0.0, "may_replicate": False, "balance_usd": balance}
        state = "CRITICAL" if runway < 6 else "TIGHT" if runway < 24 else "STABLE"
        may_replicate = (
            self._net_7d >= REPLICATION_THRESHOLD
            and runway >= MIN_RUNWAY_TO_REPLICATE
            and balance - CHILD_ENDOWMENT > DEATH_FLOOR_USD * 40
        )
        return {"state": state, "runway_hours": round(runway, 1),
                "surplus_7d": round(self._net_7d, 2), "cycle_budget": CYCLE_BUDGET[state],
                "may_replicate": may_replicate, "balance_usd": balance}

    def fund_child(self, child_wallet: str, amount: float = CHILD_ENDOWMENT) -> None:
        self.chain.transfer(self.wallet, child_wallet, amount, memo="child endowment via treasurer")
