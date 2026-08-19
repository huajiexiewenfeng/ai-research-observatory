from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from .domain import TargetTier
from .ledger import EvidenceLedger
from .registry import Registry
from .sources.base import AdapterRegistry, CollectContext, SourceStatus


@dataclass(frozen=True)
class SourceRun:
    target_id: str
    source_id: str
    method: str
    status: str
    collected_count: int
    appended_count: int
    diagnostics: dict

    @classmethod
    def from_dict(cls, payload: dict) -> "SourceRun":
        return cls(**payload)


@dataclass(frozen=True)
class RunResult:
    run_id: str
    run_date: date
    profile: str
    status: str
    sources: tuple[SourceRun, ...]

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "run_date": self.run_date.isoformat(),
                "profile": self.profile, "status": self.status,
                "sources": [asdict(source) for source in self.sources]}

    @classmethod
    def from_dict(cls, payload: dict) -> "RunResult":
        return cls(payload["run_id"], date.fromisoformat(payload["run_date"]),
                   payload["profile"], payload["status"],
                   tuple(SourceRun.from_dict(row) for row in payload["sources"]))


def run_collection(
    registry: Registry, adapters: AdapterRegistry, ledger: EvidenceLedger,
    runs_root: Path, run_date: date, profile: str, now: datetime,
    timeout_seconds: int = 15,
) -> RunResult:
    run_id = f"{now:%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    allowed_tiers = {TargetTier.CORE} if profile == "core" else set(TargetTier)
    source_runs: list[SourceRun] = []
    for target in registry.targets:
        if target.tier not in allowed_tiers:
            continue
        for source in target.sources:
            if not source.enabled:
                source_runs.append(SourceRun(
                    target.id, source.id, source.method.value, SourceStatus.STALE.value,
                    0, 0, {"reason": source.config.get("reason", "disabled")},
                ))
                continue
            context = CollectContext(run_id, run_date, now, timeout_seconds)
            try:
                result = adapters.get(source.method).collect(target, source, context)
                appended = sum(ledger.append(run_date, item) for item in result.evidence)
                source_runs.append(SourceRun(
                    target.id, source.id, source.method.value, result.status.value,
                    len(result.evidence), appended, result.diagnostics,
                ))
            except Exception as exc:
                source_runs.append(SourceRun(
                    target.id, source.id, source.method.value, SourceStatus.UNAVAILABLE.value,
                    0, 0, {"reason": "adapter_exception", "exception_type": type(exc).__name__},
                ))
    if not source_runs:
        status = "empty"
    elif all(row.status == SourceStatus.HEALTHY.value for row in source_runs):
        status = "complete"
    else:
        status = "partial"
    run = RunResult(run_id, run_date, profile, status, tuple(source_runs))
    manifest = runs_root / run_date.isoformat() / f"{run_id}.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return run


def load_run_result(path: Path) -> RunResult:
    return RunResult.from_dict(json.loads(path.read_text(encoding="utf-8")))
