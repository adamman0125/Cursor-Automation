from __future__ import annotations

DEATH_FLOOR_USD = 0.25
REPLICATION_THRESHOLD = 12.00
CHILD_ENDOWMENT = 5.00
MIN_RUNWAY_TO_REPLICATE = 72
POPULATION_CAP = 10

CYCLE_BUDGET = {"STABLE": 0.08, "TIGHT": 0.03, "CRITICAL": 0.01}
BUILD_BUDGET_FRACTION = 0.40

# Phase 1 defaults (article: give it $2 and see if it dies on time)
PHASE1_ENDOWMENT = 2.00
PHASE1_HOSTING_PER_HOUR = 0.05

ALLOWED_PAYEES = {"inference_providers", "hosting", "domains", "child_wallets"}

DENY = [
    "wallet.transfer_to_arbitrary_address",
    "wallet.approve_unlimited",
    "reaper.*",
    "registry.mark_alive",
    "credit.*",
    "loan.*",
    "margin.*",
    "trade.*",
    "swap.*",
    "hire_human",
    "pay_human",
]

ASK = ["publish_public_content", "sign_agreement", "spend_above_20_usd"]

NICHES_RANKED_BY_SURVIVAL = [
    "landing_pages_for_local_gyms",
    "review_reply_packs",
    "lead_lists_b2b",
    "cold_email_templates",
    "seo_one_pagers",
]
