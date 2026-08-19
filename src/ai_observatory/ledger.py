from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .evidence import Evidence


class EvidenceLedger:
    def __init__(self, root: Path):
        self.root = root

    def _path(self, run_date: date) -> Path:
        return self.root / run_date.isoformat() / "evidence.jsonl"

    def read_date(self, run_date: date) -> tuple[Evidence, ...]:
        path = self._path(run_date)
        if not path.exists():
            return ()
        return tuple(
            Evidence.from_dict(json.loads(line))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )

    def append(self, run_date: date, evidence: Evidence) -> bool:
        existing = {item.evidence_id for item in self.read_date(run_date)}
        if evidence.evidence_id in existing:
            return False
        path = self._path(run_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(evidence.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        return True
