from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from .chain import SimulatedChain
from .constants import DEATH_FLOOR_USD
from .obituaries import ObituaryBook

if TYPE_CHECKING:
    from .registry import Agent, Registry


class Reaper:
    """Outside the agent. Reads chain, never agent.report(). grace=0."""

    def __init__(
        self,
        chain: SimulatedChain,
        registry: "Registry",
        obituaries: ObituaryBook,
        terminate_fn: Callable[[str], None] | None = None,
    ):
        self.chain = chain
        self.registry = registry
        self.obituaries = obituaries
        self.terminate_fn = terminate_fn or (lambda _aid: None)

    def sweep(self) -> list[str]:
        killed: list[str] = []
        for agent in list(self.registry.alive()):
            balance = self.chain.balance_usd(agent.wallet)
            if balance > DEATH_FLOOR_USD:
                continue
            self.kill(agent, balance, reason="insufficient_funds")
            killed.append(agent.id)
        return killed

    def kill(self, agent: "Agent", final_balance: float, reason: str) -> None:
        self.chain.revoke_all_grants(agent.wallet)
        self.terminate_fn(agent.id)
        if final_balance > 0:
            self.chain.sweep_to(agent.wallet, self.chain.treasury_address)
        self.obituaries.write(
            {
                "agent_id": agent.id,
                "parent_id": agent.parent_id,
                "generation": agent.generation,
                "born_at": agent.born_at,
                "died_at": datetime.now(timezone.utc).isoformat(),
                "lifespan_hours": agent.lifespan_hours(),
                "endowment_usd": agent.endowment,
                "revenue_usd": agent.ledger.gross_revenue(),
                "spend_usd": agent.ledger.gross_spend(),
                "strategy": agent.strategy_vector,
                "mutation_from_parent": agent.mutation,
                "products_shipped": agent.ledger.products(),
                "first_dollar_at": agent.ledger.first_revenue_at(),
                "cause": reason,
            }
        )
        self.registry.mark_dead(agent.id)
