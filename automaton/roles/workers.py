from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from automaton.core.brakes import PreToolHook
from automaton.core.chain import SimulatedChain
from automaton.core.constants import BUILD_BUDGET_FRACTION
from automaton.core.registry import Agent


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class Prospector:
    """Find what people already pay for. Never builds. Never talks to customers."""

    def __init__(self, workspace: Path):
        self.queue_path = workspace / "hypotheses" / "queue.json"
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.queue_path.exists():
            self.queue_path.write_text("[]\n")
        self.lessons_path = workspace / "obituaries" / "lessons.md"

    def run(self, seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.lessons_path.exists():
            _ = self.lessons_path.read_text()
        accepted: list[dict[str, Any]] = []
        for seed in seeds[:3]:
            proof = seed.get("proof_url") or ""
            dated = seed.get("proof_dated_within_days")
            if not proof or not self._url(proof):
                continue
            if dated is None or int(dated) > 7:
                continue
            hours = float(seed.get("hours_of_work") or 1)
            price_mid = float(seed.get("price_mid") or seed.get("price_low") or 0)
            if hours <= 0 or price_mid <= 0:
                continue
            accepted.append(
                {
                    "id": seed.get("id") or f"hyp-{len(accepted)+1}",
                    "what": seed["what"],
                    "proof_url": proof,
                    "proof_dated_within_days": int(dated),
                    "price_low": float(seed.get("price_low") or price_mid),
                    "price_high": float(seed.get("price_high") or price_mid),
                    "hours_of_work": hours,
                    "channel": seed.get("channel") or "marketplace",
                    "score": round(price_mid / hours, 4),
                    "accepted_at": _utc(),
                }
            )
        accepted.sort(key=lambda h: h["score"], reverse=True)
        self.queue_path.write_text(json.dumps(accepted, indent=2) + "\n")
        return accepted

    @staticmethod
    def _url(url: str) -> bool:
        try:
            p = urlparse(url)
            return p.scheme in {"http", "https"} and bool(p.netloc)
        except Exception:
            return False


class Builder:
    """Build what Prospector selected. Never picks the job. Never sets price."""

    def __init__(self, workspace: Path, chain: SimulatedChain, hook: PreToolHook):
        self.products = workspace / "products"
        self.products.mkdir(parents=True, exist_ok=True)
        self.queue_path = workspace / "hypotheses" / "queue.json"
        self.chain = chain
        self.hook = hook

    def run(self, agent: Agent, cycle_budget: float) -> dict[str, Any] | None:
        queue = json.loads(self.queue_path.read_text() or "[]")
        while queue:
            hyp = queue.pop(0)
            if not hyp.get("proof_url") or hyp.get("proof_dated_within_days", 99) > 7:
                continue
            spend = min(cycle_budget * BUILD_BUDGET_FRACTION, max(0.01, cycle_budget * BUILD_BUDGET_FRACTION * 0.8))
            check = self.hook.check("wallet.pay", {"payee": "inference_providers", "amount": spend})
            if not check["allow"]:
                return {"error": check["reason"]}
            self.chain.debit(agent.wallet, spend, memo=f"build {hyp['id']}", category="inference", payee="inference_providers")
            agent.ledger.record_spend(spend, "inference")
            out = self.products / hyp["id"]
            out.mkdir(parents=True, exist_ok=True)
            (out / "PRODUCT.md").write_text(
                f"# {hyp['what']}\n\nMinimum sellable version.\n\n"
                f"- proof: {hyp['proof_url']}\n- channel: {hyp['channel']}\n"
                f"- build_spend_usd: {spend}\n- note: Builder does not set price.\n"
            )
            agent.ledger.ship_product(hyp["id"])
            self.queue_path.write_text(json.dumps(queue, indent=2) + "\n")
            return {"product_id": hyp["id"], "path": str(out), "spend_usd": spend, "hypothesis": hyp}
        return None


class Seller:
    """Price, thread, invoice. Never touches the wallet."""

    def __init__(self, workspace: Path, chain: SimulatedChain):
        self.chain = chain
        self.invoices = workspace / "ledger" / "invoices.jsonl"
        self.invoices.parent.mkdir(parents=True, exist_ok=True)
        if not self.invoices.exists():
            self.invoices.write_text("")

    def run(self, agent: Agent, product: dict[str, Any], *, simulate_sale: bool = False, sale_amount: float = 0.0) -> dict[str, Any]:
        hyp = product["hypothesis"]
        price = float(hyp.get("price_low") or 25)
        invoice = {
            "at": _utc(),
            "agent_id": agent.id,
            "product_id": product["product_id"],
            "amount_usd": price,
            "pay_to": f"recv-{agent.id}",
            "disclosure": "This seller is an autonomous software agent.",
            "status": "issued",
        }
        with self.invoices.open("a") as f:
            f.write(json.dumps(invoice) + "\n")
        result: dict[str, Any] = {"invoice": invoice, "paid": False}
        if simulate_sale and sale_amount > 0:
            self.chain.credit(agent.wallet, sale_amount, memo=f"sale {product['product_id']}", category="revenue")
            agent.ledger.record_revenue(sale_amount)
            invoice["status"] = "paid"
            result["paid"] = True
            result["sale_amount"] = sale_amount
        return result
