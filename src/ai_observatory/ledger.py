from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .evidence import Evidence


class LedgerCorruptionError(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceRecord:
    schema_version: int
    run_date: date
    evidence: Evidence

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "run_date": self.run_date.isoformat(),
            "evidence": self.evidence.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "EvidenceRecord":
        return cls(
            schema_version=int(payload["schema_version"]),
            run_date=date.fromisoformat(payload["run_date"]),
            evidence=Evidence.from_dict(payload["evidence"]),
        )


class EvidenceLedger:
    def __init__(self, root: Path):
        self.root = root

    def _path(self) -> Path:
        return self.root / "ledger.jsonl"

    def _read_records(self) -> tuple[EvidenceRecord, ...]:
        path = self._path()
        if not path.exists():
            return ()
        records: list[EvidenceRecord] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(EvidenceRecord.from_dict(json.loads(line)))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise LedgerCorruptionError(f"invalid evidence ledger line {line_number}") from exc
        return tuple(records)

    def read_all(self) -> tuple[Evidence, ...]:
        return tuple(record.evidence for record in self._read_records())

    def read_date(self, run_date: date) -> tuple[Evidence, ...]:
        return tuple(
            record.evidence for record in self._read_records()
            if record.run_date == run_date
        )

    def append(self, run_date: date, evidence: Evidence) -> bool:
        records = self._read_records()
        if evidence.evidence_id in {record.evidence.evidence_id for record in records}:
            return False
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        record = EvidenceRecord(schema_version=1, run_date=run_date, evidence=evidence)
        serialized = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized + "\n")
        return True
