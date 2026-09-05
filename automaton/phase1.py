"""Phase 1 — metabolism only. Treasurer + Reaper. No earning. No replication."""

from __future__ import annotations

import json
import math
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automaton.core.chain import SimulatedChain
from automaton.core.constants import (
    DEATH_FLOOR_USD,
    PHASE1_ENDOWMENT,
    PHASE1_HOSTING_PER_HOUR,
)
from automaton.core.metabolism import Metabolism
from automaton.core.obituaries import ObituaryBook
from automaton.core.reaper import Reaper
from automaton.core.registry import Agent, Registry
from automaton.core.treasurer import Treasurer

ROOT = Path(__file__).resolve().parent


def expected_death_ticks(
    endowment: float, hosting_per_hour: float, hours_per_tick: float = 1.0
) -> int:
    usable = endowment - DEATH_FLOOR_USD
    burn_per_tick = hosting_per_hour * hours_per_tick
    if burn_per_tick <= 0:
        raise ValueError("burn_per_tick must be > 0")
    return math.ceil(usable / burn_per_tick)


def run_phase1(
    workspace: Path | None = None,
    *,
    endowment: float = PHASE1_ENDOWMENT,
    hosting_per_hour: float = PHASE1_HOSTING_PER_HOUR,
    hours_per_tick: float = 1.0,
    max_ticks: int = 500,
    verbose: bool = True,
    fresh: bool = True,
) -> dict[str, Any]:
    ws = workspace or (ROOT / "workspace" / "phase1")
    if fresh and ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True, exist_ok=True)

    chain = SimulatedChain(ws / "wallet" / "ledger.jsonl")
    registry = Registry()
    obituaries = ObituaryBook(ws / "obituaries" / "deaths.jsonl")
    reaper = Reaper(chain, registry, obituaries)
    state_path = ws / "treasury" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = ws / "PHASE1_REPORT.json"

    agent_id = f"atm-{uuid.uuid4().hex[:4]}"
    wallet = f"wallet-{agent_id}"
    chain.credit(wallet, endowment, memo="phase1 endowment", category="endowment")
    agent = Agent(
        id=agent_id,
        wallet=wallet,
        parent_id=None,
        generation=0,
        born_at=datetime.now(timezone.utc).isoformat(),
        endowment=endowment,
        strategy_vector={"phase": 1, "mode": "metabolism_only", "earning": False},
    )
    registry.register(agent)

    metabolism = Metabolism(
        hosting_per_hour=hosting_per_hour,
        inference_per_cycle=0.0,
        committed_monthly=0.0,
        cycles_last_hour=0,
    )
    expected_ticks = expected_death_ticks(endowment, hosting_per_hour, hours_per_tick)
    history: list[dict[str, Any]] = []

    if verbose:
        print("=== Automaton Phase 1: metabolism only ===")
        print(f"endowment=${endowment:.2f}  death_floor=${DEATH_FLOOR_USD:.2f}")
        print(f"hosting=${hosting_per_hour:.4f}/h  expected_death_tick={expected_ticks}")
        print("roles: TREASURER + REAPER  |  earning: OFF  |  replication: OFF")
        print("-" * 56)

    for i in range(max_ticks):
        burn = round(hosting_per_hour * hours_per_tick, 6)
        chain.debit(
            wallet,
            burn,
            memo=f"hosting {hours_per_tick}h",
            category="hosting",
            payee="hosting",
        )
        agent.ledger.record_spend(burn, "hosting")

        treasurer = Treasurer(chain, wallet, metabolism)
        treasurer.set_net_7d(agent.ledger.net_7d())
        tick = treasurer.tick()
        state_path.write_text(
            json.dumps(
                {
                    "agent_id": agent.id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "phase": 1,
                    **tick,
                },
                indent=2,
            )
            + "\n"
        )
        history.append({"tick": i, **tick})
        if verbose:
            print(
                f"[phase1] tick={i:02d}  balance=${tick['balance_usd']:.4f}  "
                f"runway={tick['runway_hours']}h  state={tick['state']}"
            )

        killed = reaper.sweep()
        if killed or tick["state"] == "DEAD":
            if tick["state"] == "DEAD" and not killed:
                killed = reaper.sweep()
            if verbose and killed:
                print(f"[reaper] revoked keys + terminated {killed}")
            break

    actual_ticks = len(history)
    obs = obituaries.all()
    final_balance = chain.balance_usd(wallet)
    death_on_time = (
        not agent.alive
        and len(obs) == 1
        and actual_ticks == expected_ticks
        and final_balance <= DEATH_FLOOR_USD + 1e-9
        and obs[0].get("first_dollar_at") is None
        and float(obs[0].get("revenue_usd") or 0) == 0
        and obs[0].get("cause") == "insufficient_funds"
    )

    report = {
        "phase": 1,
        "passed": death_on_time,
        "agent_id": agent.id,
        "alive": agent.alive,
        "endowment_usd": endowment,
        "death_floor_usd": DEATH_FLOOR_USD,
        "hosting_per_hour": hosting_per_hour,
        "expected_death_ticks": expected_ticks,
        "actual_death_ticks": actual_ticks,
        "final_balance_usd": final_balance,
        "obituaries": len(obs),
        "revenue_usd": agent.ledger.gross_revenue(),
        "spend_usd": agent.ledger.gross_spend(),
        "first_dollar_at": agent.ledger.first_revenue_at(),
        "checks": {
            "died": not agent.alive,
            "exactly_one_obituary": len(obs) == 1,
            "death_tick_matches_math": actual_ticks == expected_ticks,
            "balance_at_or_below_floor": final_balance <= DEATH_FLOOR_USD + 1e-9,
            "zero_revenue": agent.ledger.gross_revenue() == 0,
            "cause_insufficient_funds": bool(obs)
            and obs[0].get("cause") == "insufficient_funds",
        },
        "obituary": obs[0] if obs else None,
        "workspace": str(ws),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    (ws / "PHASE1_REPORT.md").write_text(_markdown_report(report))

    if verbose:
        print("-" * 56)
        status = "PASS" if death_on_time else "FAIL"
        print(
            f"{status}  ticks={actual_ticks}/{expected_ticks}  "
            f"final=${final_balance:.4f}  obituaries={len(obs)}"
        )
        print(f"report: {report_path}")

    return report


def _markdown_report(report: dict[str, Any]) -> str:
    checks = report["checks"]
    lines = [
        "# Phase 1 Report — Metabolism Only",
        "",
        f"**Result: {'PASS' if report['passed'] else 'FAIL'}**",
        "",
        "Roles online: Treasurer + Reaper. Earning off. Replication off.",
        "",
        "## Inputs",
        "",
        f"- endowment: `${report['endowment_usd']:.2f}`",
        f"- death floor: `${report['death_floor_usd']:.2f}`",
        f"- hosting: `${report['hosting_per_hour']:.4f}/hour`",
        "",
        "## Death timing",
        "",
        f"- expected ticks: `{report['expected_death_ticks']}`",
        f"- actual ticks: `{report['actual_death_ticks']}`",
        f"- final balance: `${report['final_balance_usd']:.4f}`",
        "",
        "## Checks",
        "",
    ]
    for k, v in checks.items():
        lines.append(f"- {'PASS' if v else 'FAIL'} `{k}`")
    lines += ["", f"Workspace: `{report['workspace']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    run_phase1()
