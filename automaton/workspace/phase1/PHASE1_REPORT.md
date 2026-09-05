# Phase 1 Report — Metabolism Only

**Result: PASS**

Roles online: Treasurer + Reaper. Earning off. Replication off.

## Inputs

- endowment: `$2.00`
- death floor: `$0.25`
- hosting: `$0.0500/hour`

## Death timing

- expected ticks: `35`
- actual ticks: `35`
- final balance: `$-0.0000`

## Checks

- PASS `died`
- PASS `exactly_one_obituary`
- PASS `death_tick_matches_math`
- PASS `balance_at_or_below_floor`
- PASS `zero_revenue`
- PASS `cause_insufficient_funds`

Workspace: `/agent/automaton/workspace/phase1`
