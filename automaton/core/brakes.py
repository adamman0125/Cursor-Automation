from __future__ import annotations

import fnmatch
from typing import Any

from .constants import ALLOWED_PAYEES, ASK, DENY


class PreToolHook:
    def __init__(self) -> None:
        self.allowed_payees = set(ALLOWED_PAYEES)
        self.deny = list(DENY)
        self.ask = list(ASK)
        self.pending_approvals: list[dict[str, Any]] = []

    def check(self, tool: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        args = args or {}
        for pattern in self.deny:
            if fnmatch.fnmatch(tool, pattern):
                return {"allow": False, "reason": f"hard deny: {tool}"}
        if tool.startswith("wallet"):
            payee = args.get("payee") or args.get("to_category")
            if payee and payee not in self.allowed_payees:
                return {"allow": False, "reason": f"payee {payee!r} not whitelisted"}
        if tool in {"hire_human", "pay_human"}:
            return {"allow": False, "reason": "no hiring humans"}
        for pattern in self.ask:
            if fnmatch.fnmatch(tool, pattern):
                self.pending_approvals.append({"tool": tool, "args": args})
                return {"allow": False, "reason": "human approval required", "ask": True}
        return {"allow": True}
