from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence


class SourceStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    STALE = "stale"


@dataclass(frozen=True)
class CollectContext:
    run_id: str
    run_date: date
    collected_at: datetime
    timeout_seconds: int


@dataclass(frozen=True)
class CollectResult:
    status: SourceStatus
    evidence: tuple[Evidence, ...]
    diagnostics: dict = field(default_factory=dict)


class SourceAdapter(Protocol):
    method: SourceMethod

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult: ...


class AdapterRegistry:
    def __init__(self, adapters: list[SourceAdapter]):
        self._adapters = {adapter.method: adapter for adapter in adapters}

    def get(self, method: SourceMethod) -> SourceAdapter:
        try:
            return self._adapters[method]
        except KeyError as exc:
            raise LookupError(f"no adapter for {method.value}") from exc
