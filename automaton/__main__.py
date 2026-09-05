from __future__ import annotations

import argparse
import json
from pathlib import Path

from automaton.phase1 import run_phase1


def main() -> None:
    p = argparse.ArgumentParser(description="Automaton mortality-engine")
    p.add_argument("command", choices=["phase1", "phase2", "demo"])
    p.add_argument("--workspace", type=Path, default=None)
    p.add_argument("--endowment", type=float, default=2.0)
    p.add_argument("--hosting-per-hour", type=float, default=0.05)
    p.add_argument("--sale", type=float, default=25.0)
    args = p.parse_args()

    if args.command == "phase1":
        report = run_phase1(
            args.workspace,
            endowment=args.endowment,
            hosting_per_hour=args.hosting_per_hour,
        )
        print(
            json.dumps(
                {
                    "passed": report["passed"],
                    "agent_id": report["agent_id"],
                    "expected_death_ticks": report["expected_death_ticks"],
                    "actual_death_ticks": report["actual_death_ticks"],
                    "final_balance_usd": report["final_balance_usd"],
                    "obituaries": report["obituaries"],
                    "checks": report["checks"],
                },
                indent=2,
            )
        )
        raise SystemExit(0 if report["passed"] else 1)

    # Phase 2 kept available but Phase 1 is the active track.
    from automaton.sim import AutomatonSim
    import shutil

    ws = args.workspace or (Path(__file__).resolve().parent / "workspace" / args.command)
    if ws.exists():
        shutil.rmtree(ws)
    sim = AutomatonSim(ws)
    print(json.dumps({"note": "Use `phase1` for the current track. Phase 2 next.", "workspace": str(ws)}, indent=2))


if __name__ == "__main__":
    main()
