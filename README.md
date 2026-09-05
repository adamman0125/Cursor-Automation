# Automaton

Local implementation of the **mortality-engine** agent architecture from [this X article](https://x.com/i/article/2095073506077839360) (via [proAlishke](https://x.com/proalishke/status/2095154142775755173)).

Six roles. One rule: earn more than you burn, or the Reaper deletes you.

> This repo is a **local simulator**. Real crypto wallets, live Grok Bot cloud machines, and real customer outreach are **not** enabled by default.

## Roles

| Role | Owns | Stopline |
|------|------|----------|
| TREASURER | wallet, runway, budgets | never earns / never buys product |
| PROSPECTOR | demand discovery | never builds / never talks to customers |
| BUILDER | product, deploy | never picks job / never sets price |
| SELLER | price, thread, invoice | never touches wallet |
| REPLICATOR | spawn + one mutation | never decides surplus |
| REAPER | death + obituary | lives *outside* the agent |

## Constants

- Child endowment: **$5.00**
- Death floor: **$0.25**
- Cycle budget: **$0.08 / $0.03 / $0.01** (STABLE / TIGHT / CRITICAL)
- Build cap: **40%** of cycle budget
- Replication: **$12** 7-day surplus + **72h** runway

## Run

```bash
cd /agent
PYTHONPATH=. python -m automaton phase1 --endowment 2.0
PYTHONPATH=. python -m automaton phase2 --endowment 5.0 --sale 25
PYTHONPATH=. python -m pytest automaton/tests -q
```

### Phase order (from the article)

1. **Metabolism only** — TREASURER + REAPER. Give it $2, confirm death fires on time. ✅ **PASS** (`35/35` ticks, 1 obituary, $0 revenue)
2. **Earning, no replication** — add PROSPECTOR / BUILDER / SELLER. Reach first dollar.
3. **Replication under a cap** — turn on REPLICATOR, population cap 10.
4. **Raise the cap** — only after you know idle population cost.

Phase 1 artifacts land in `automaton/workspace/phase1/` (`PHASE1_REPORT.md`, ledger, obituary).

## Grok Bot prompts

Copy `automaton/prompts/*.md` into separate Grok Bots. **Do not create REAPER inside the same account.**

## Safety brakes (code, not prompts)

Transfers only to whitelisted payees. No REAPER access. No credit/leverage. No trading. Must disclose agent identity. No breeding under 72h runway. Population cap. No hiring humans.
