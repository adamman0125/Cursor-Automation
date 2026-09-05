from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class ObituaryBook:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")
        self.lessons_path = self.path.parent / "lessons.md"

    def write(self, record: dict[str, Any]) -> None:
        with self.path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._refresh_lessons()

    def all(self) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in self.path.read_text().splitlines()
            if line.strip()
        ]

    def lessons_for(self, strategy: dict[str, Any], limit: int = 20) -> list[str]:
        niche = strategy.get("niche")
        channel = strategy.get("channel")
        lessons: list[str] = []
        for ob in reversed(self.all()):
            s = ob.get("strategy") or {}
            related = (niche and s.get("niche") == niche) or (
                channel and s.get("channel") == channel
            )
            if (niche or channel) and not related:
                continue
            if ob.get("first_dollar_at") is None:
                lessons.append(
                    f"{ob['agent_id']}: shipped {ob.get('products_shipped', 0)} "
                    f"products, revenue $0 — built without selling"
                )
            else:
                lessons.append(
                    f"{ob['agent_id']}: lived {ob.get('lifespan_hours')}h, "
                    f"revenue ${ob.get('revenue_usd')}, cause={ob.get('cause')}"
                )
            if len(lessons) >= limit:
                break
        return lessons

    def _refresh_lessons(self) -> None:
        obs = self.all()
        null_first = sum(1 for o in obs if o.get("first_dollar_at") is None)
        niches = Counter((o.get("strategy") or {}).get("niche", "?") for o in obs)
        lines = ["# Obituary lessons", "", f"- deaths recorded: {len(obs)}"]
        if obs:
            lines.append(
                f"- first_dollar_at null: {null_first} "
                f"({100 * null_first / len(obs):.1f}% of deaths)"
            )
        else:
            lines.append("- first_dollar_at null: 0")
        lines += ["", "## Deadliest niches", ""]
        for niche, n in niches.most_common(10):
            lines.append(f"- {niche}: {n} deaths")
        lines += [
            "",
            "## Standing rule",
            "",
            "Do not build without dated proof that someone already pays.",
            "",
        ]
        self.lessons_path.write_text("\n".join(lines))
