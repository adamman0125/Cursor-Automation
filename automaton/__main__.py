from __future__ import annotations

import argparse
import json
from pathlib import Path

from automaton.sim import AutomatonSim


def main() -> None:
    p = argparse.ArgumentParser(description="Automaton mortality-engine simulator")
    p.add_argument("command", choices=["phase1", "phase2", "demo"])
    p.add_argument("--workspace", type=Path, default=None)
    p.add_argument("--endowment", type=float, default=2.0)
    p.add_argument("--sale", type=float, default=25.0)
    args = p.parse_args()

    # fresh workspace per run for demos
    ws = args.workspace
    if ws is None:
        ws = Path(__file__).resolve().parent / "workspace" / args.command
        if ws.exists():
            import shutil
            shutil.rmtree(ws)
    sim = AutomatonSim(ws)

    if args.command == "phase1":
        result = sim.phase1_run(endowment=args.endowment)
        print(json.dumps({k: result[k] for k in ("agent_id", "alive", "final_balance", "ticks", "obituaries")}, indent=2))
        return

    if args.command in {"phase2", "demo"}:
        agent = sim.birth(endowment=args.endowment)
        seeds = [
            {
                "id": "hyp-gym-landing",
                "what": "One-page landing site for a local gym lead magnet",
                "proof_url": "https://www.fiverr.com/categories/online-marketing/local-seo-services",
                "proof_dated_within_days": 2,
                "price_low": 25,
                "price_high": 75,
                "price_mid": 40,
                "hours_of_work": 2,
                "channel": "marketplace",
            },
            {
                "id": "hyp-no-proof",
                "what": "AI productivity coach nobody asked for",
                "proof_url": "",
                "proof_dated_within_days": 1,
                "price_low": 10,
                "hours_of_work": 5,
                "channel": "cold_dm",
            },
        ]
        result = sim.phase2_cycle(agent, seeds, simulate_sale=True, sale_amount=args.sale)
        print(json.dumps({
            "status": result["status"],
            "balance_usd": result["tick"]["balance_usd"],
            "state": result["tick"]["state"],
            "hypotheses": len(result.get("hypotheses") or []),
            "product": (result.get("product") or {}).get("product_id"),
            "paid": (result.get("sale") or {}).get("paid"),
            "obituaries": len(sim.obituaries.all()),
        }, indent=2))
        child = sim.try_replicate(agent)
        print(json.dumps({"replicate_attempt": child}, indent=2))


if __name__ == "__main__":
    main()
