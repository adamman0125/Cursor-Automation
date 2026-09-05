from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SimulatedChain:
    """Append-only public ledger. Not a real chain."""

    def __init__(self, path: Path, treasury_address: str = "treasury-public"):
        self.path = path
        self.treasury_address = treasury_address
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")
        self._lock = threading.Lock()
        self._balances: dict[str, float] = {}
        self._revoked: set[str] = set()
        self._load()

    def _load(self) -> None:
        self._balances = {self.treasury_address: 0.0}
        self._revoked = set()
        for line in self.path.read_text().splitlines():
            if line.strip():
                self._apply(json.loads(line), persist=False)

    def _apply(self, ev: dict[str, Any], persist: bool) -> None:
        typ = ev["type"]
        if typ == "credit":
            addr = ev["to"]
            self._balances[addr] = self._balances.get(addr, 0.0) + float(ev["amount"])
        elif typ == "debit":
            addr = ev["from"]
            self._balances[addr] = self._balances.get(addr, 0.0) - float(ev["amount"])
        elif typ == "transfer":
            frm, to, amt = ev["from"], ev["to"], float(ev["amount"])
            self._balances[frm] = self._balances.get(frm, 0.0) - amt
            self._balances[to] = self._balances.get(to, 0.0) + amt
        elif typ == "revoke":
            self._revoked.add(ev["address"])
        if persist:
            with self.path.open("a") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def _emit(self, ev: dict[str, Any]) -> None:
        with self._lock:
            self._apply({**ev, "at": _utc_now()}, persist=True)

    def balance_usd(self, address: str) -> float:
        with self._lock:
            return round(self._balances.get(address, 0.0), 6)

    def credit(self, address: str, amount: float, memo: str, category: str) -> None:
        self._emit(
            {
                "type": "credit",
                "to": address,
                "amount": round(amount, 6),
                "memo": memo,
                "category": category,
            }
        )

    def debit(
        self, address: str, amount: float, memo: str, category: str, payee: str
    ) -> None:
        if category not in {"inference", "hosting", "domains", "other"}:
            raise ValueError(f"unknown debit category: {category}")
        if address in self._revoked:
            raise PermissionError(f"wallet {address} revoked")
        self._emit(
            {
                "type": "debit",
                "from": address,
                "amount": round(amount, 6),
                "memo": memo,
                "category": category,
                "payee": payee,
            }
        )

    def transfer(self, frm: str, to: str, amount: float, memo: str) -> None:
        if frm in self._revoked:
            raise PermissionError(f"wallet {frm} revoked")
        self._emit(
            {
                "type": "transfer",
                "from": frm,
                "to": to,
                "amount": round(amount, 6),
                "memo": memo,
            }
        )

    def revoke_all_grants(self, address: str) -> None:
        self._emit({"type": "revoke", "address": address, "memo": "grants revoked"})

    def sweep_to(self, frm: str, to: str) -> float:
        bal = self.balance_usd(frm)
        if bal > 0:
            # Allow residual sweep after revoke by emitting transfer directly.
            self._emit(
                {
                    "type": "transfer",
                    "from": frm,
                    "to": to,
                    "amount": round(bal, 6),
                    "memo": "reaper sweep residual",
                }
            )
        return bal
