from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automaton.core.brakes import PreToolHook
from automaton.core.chain import SimulatedChain
from automaton.core.constants import CHILD_ENDOWMENT
from automaton.core.metabolism import Metabolism
from automaton.core.obituaries import ObituaryBook
from automaton.core.reaper import Reaper
from automaton.core.registry import Agent, Registry
from automaton.core.replicator import Replicator
from automaton.core.treasurer import Treasurer
from automaton.roles.workers import Builder, Prospector, Seller

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT / "workspace"


class AutomatonSim:
    """Local mortality-engine simulator (Phase 1–3)."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or WORKSPACE
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.chain = SimulatedChain(self.workspace / "wallet" / "ledger.jsonl")
        self.registry = Registry()
        self.obituaries = ObituaryBook(self.workspace / "obituaries" / "deaths.jsonl")
        self.hook = PreToolHook()
        self.reaper = Reaper(self.chain, self.registry, self.obituaries)
        self.prospector = Prospector(self.workspace)
        self.builder = Builder(self.workspace, self.chain, self.hook)
        self.seller = Seller(self.workspace, self.chain)
        self.state_path = self.workspace / "treasury" / "state.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def birth(self, *, endowment: float = CHILD_ENDOWMENT, strategy: dict[str, Any] | None = None, agent_id: str | None = None) -> Agent:
        aid = agent_id or f"atm-{uuid.uuid4().hex[:4]}"
        wallet = f"wallet-{aid}"
        self.chain.credit(wallet, endowment, memo="endowment", category="endowment")
        agent = Agent(
            id=aid,
            wallet=wallet,
            parent_id=None,
            generation=0,
            born_at=datetime.now(timezone.utc).isoformat(),
            endowment=endowment,
            strategy_vector=strategy or {
                "niche": "landing_pages_for_local_gyms",
                "price_point": 40,
                "channel": "cold_dm",
                "delivery_speed": "48h",
                "scope": "single_task",
                "first_touch_free": False,
            },
        )
        self.registry.register(agent)
        return agent

    def _treasurer(self, agent: Agent, metabolism: Metabolism) -> Treasurer:
        t = Treasurer(self.chain, agent.wallet, metabolism)
        t.set_net_7d(agent.ledger.net_7d())
        return t

    def write_state(self, agent: Agent, tick: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps({"agent_id": agent.id, "updated_at": datetime.now(timezone.utc).isoformat(), **tick}, indent=2) + "\n")

    def burn_hosting(self, agent: Agent, hours: float, rate: float) -> None:
        amount = round(hours * rate, 6)
        if amount <= 0:
            return
        self.chain.debit(agent.wallet, amount, memo=f"hosting {hours}h", category="hosting", payee="hosting")
        agent.ledger.record_spend(amount, "hosting")

    def burn_inference(self, agent: Agent, amount: float) -> None:
        if amount <= 0:
            return
        self.chain.debit(agent.wallet, amount, memo="inference cycle", category="inference", payee="inference_providers")
        agent.ledger.record_spend(amount, "inference")

    def phase1_run(self, *, endowment: float = 2.0, hosting_per_hour: float = 0.05, hours_per_tick: float = 1.0, max_ticks: int = 200, verbose: bool = True) -> dict[str, Any]:
        agent = self.birth(endowment=endowment)
        metabolism = Metabolism(hosting_per_hour=hosting_per_hour, inference_per_cycle=0.0, committed_monthly=0.0, cycles_last_hour=0)
        history: list[dict[str, Any]] = []
        for i in range(max_ticks):
            self.burn_hosting(agent, hours_per_tick, hosting_per_hour)
            tick = self._treasurer(agent, metabolism).tick()
            self.write_state(agent, tick)
            history.append({"tick": i, **tick})
            if verbose:
                print(f"[phase1] tick={i} balance=${tick['balance_usd']:.4f} runway={tick['runway_hours']}h state={tick['state']}")
            killed = self.reaper.sweep()
            if killed:
                if verbose:
                    print(f"[reaper] killed {killed}")
                break
            if tick["state"] == "DEAD":
                self.reaper.sweep()
                break
        return {"agent_id": agent.id, "alive": agent.alive, "final_balance": self.chain.balance_usd(agent.wallet), "ticks": len(history), "obituaries": len(self.obituaries.all()), "history": history}

    def phase2_cycle(self, agent: Agent, seeds: list[dict[str, Any]], *, simulate_sale: bool = False, sale_amount: float = 0.0, hosting_per_hour: float = 0.02, verbose: bool = True) -> dict[str, Any]:
        metabolism = Metabolism(hosting_per_hour=hosting_per_hour, inference_per_cycle=0.02, committed_monthly=0.0, cycles_last_hour=1)
        self.burn_hosting(agent, 1.0, hosting_per_hour)
        tick = self._treasurer(agent, metabolism).tick()
        self.write_state(agent, tick)
        if tick["state"] == "DEAD" or not agent.alive:
            self.reaper.sweep()
            return {"status": "dead", "tick": tick}

        hyps = self.prospector.run(seeds)
        if verbose:
            print(f"[prospector] accepted {len(hyps)} hypotheses")
        product = self.builder.run(agent, tick["cycle_budget"])
        sale = None
        if product and "error" not in product:
            if verbose:
                print(f"[builder] shipped {product['product_id']} spend=${product['spend_usd']}")
            sale = self.seller.run(agent, product, simulate_sale=simulate_sale, sale_amount=sale_amount)
            if verbose:
                print(f"[seller] invoice=${sale['invoice']['amount_usd']} paid={sale['paid']}")
        else:
            self.burn_inference(agent, min(tick["cycle_budget"], 0.01))
            if verbose:
                print("[builder] no valid hypothesis — skipped")

        killed = self.reaper.sweep()
        tick2 = self._treasurer(agent, metabolism).tick()
        self.write_state(agent, tick2)
        return {"status": "dead" if killed or not agent.alive else "alive", "tick": tick2, "hypotheses": hyps, "product": product, "sale": sale, "killed": killed}

    def try_replicate(self, parent: Agent) -> str | None:
        metabolism = Metabolism(0.02, 0.02, 0.0, 1)
        treasurer = self._treasurer(parent, metabolism)
        try:
            return Replicator(treasurer, self.registry, self.obituaries).spawn(parent)
        except PermissionError as e:
            print(f"[replicator] blocked: {e}")
            return None
