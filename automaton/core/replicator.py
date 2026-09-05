from __future__ import annotations

import copy
import random
import uuid
from datetime import datetime, timezone

from .constants import CHILD_ENDOWMENT, NICHES_RANKED_BY_SURVIVAL, POPULATION_CAP
from .obituaries import ObituaryBook
from .registry import Agent, Registry
from .treasurer import Treasurer

MUTABLE = {
    "price_point": lambda v: max(5, round(float(v) * random.uniform(0.6, 1.7))),
    "niche": lambda _v: random.choice(NICHES_RANKED_BY_SURVIVAL),
    "channel": lambda _v: random.choice(["cold_dm", "marketplace", "seo_landing", "community"]),
    "delivery_speed": lambda _v: random.choice(["same_hour", "same_day", "48h"]),
    "scope": lambda _v: random.choice(["single_task", "subscription"]),
    "first_touch_free": lambda v: not bool(v),
}


class Replicator:
    def __init__(self, treasurer: Treasurer, registry: Registry, obituaries: ObituaryBook):
        self.treasurer = treasurer
        self.registry = registry
        self.obituaries = obituaries

    def spawn(self, parent: Agent) -> str:
        gate = self.treasurer.tick()
        if not gate["may_replicate"]:
            raise PermissionError("no surplus or runway too short")
        if self.registry.population() >= POPULATION_CAP:
            raise PermissionError("population cap reached")

        strategy = copy.deepcopy(parent.strategy_vector)
        defaults = {
            "price_point": 40,
            "niche": NICHES_RANKED_BY_SURVIVAL[0],
            "channel": "cold_dm",
            "delivery_speed": "48h",
            "scope": "single_task",
            "first_touch_free": False,
        }
        for k, v in defaults.items():
            strategy.setdefault(k, v)

        key = random.choice(list(MUTABLE))
        old = strategy[key]
        strategy[key] = MUTABLE[key](strategy[key])
        mutation = {"field": key, "from": old, "to": strategy[key]}

        child_id = f"atm-{uuid.uuid4().hex[:4]}"
        child_wallet = f"wallet-{child_id}"
        self.treasurer.fund_child(child_wallet, CHILD_ENDOWMENT)

        child = Agent(
            id=child_id,
            wallet=child_wallet,
            parent_id=parent.id,
            generation=parent.generation + 1,
            born_at=datetime.now(timezone.utc).isoformat(),
            endowment=CHILD_ENDOWMENT,
            strategy_vector=strategy,
            mutation=mutation,
            briefing=self.obituaries.lessons_for(strategy, limit=20),
        )
        self.registry.register(child)
        return child.id
