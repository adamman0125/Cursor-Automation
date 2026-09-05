from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class Ledger:
    revenues: list[dict[str, Any]] = field(default_factory=list)
    spends: list[dict[str, Any]] = field(default_factory=list)
    product_ids: list[str] = field(default_factory=list)

    def record_revenue(self, amount: float) -> None:
        self.revenues.append({"amount": amount, "at": _utc_now()})

    def record_spend(self, amount: float, category: str) -> None:
        self.spends.append({"amount": amount, "category": category, "at": _utc_now()})

    def ship_product(self, product_id: str) -> None:
        self.product_ids.append(product_id)

    def gross_revenue(self) -> float:
        return round(sum(r["amount"] for r in self.revenues), 6)

    def gross_spend(self) -> float:
        return round(sum(s["amount"] for s in self.spends), 6)

    def products(self) -> int:
        return len(self.product_ids)

    def first_revenue_at(self) -> str | None:
        return self.revenues[0]["at"] if self.revenues else None

    def net_7d(self) -> float:
        return self.gross_revenue() - self.gross_spend()

@dataclass
class Agent:
    id: str
    wallet: str
    parent_id: str | None
    generation: int
    born_at: str
    endowment: float
    strategy_vector: dict[str, Any]
    mutation: dict[str, Any] | None = None
    briefing: list[str] = field(default_factory=list)
    alive: bool = True
    ledger: Ledger = field(default_factory=Ledger)

    def lifespan_hours(self) -> float:
        born = datetime.fromisoformat(self.born_at)
        now = datetime.now(timezone.utc)
        if born.tzinfo is None:
            born = born.replace(tzinfo=timezone.utc)
        return round((now - born).total_seconds() / 3600.0, 3)

class Registry:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def alive(self) -> list[Agent]:
        return [a for a in self._agents.values() if a.alive]

    def population(self) -> int:
        return len(self.alive())

    def mark_dead(self, agent_id: str) -> None:
        self._agents[agent_id].alive = False

    def all(self) -> list[Agent]:
        return list(self._agents.values())
