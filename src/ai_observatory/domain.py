from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TargetTier(StrEnum):
    CORE = "core"
    WATCH = "watch"
    PERSONAL = "personal"


class TargetKind(StrEnum):
    COMPANY = "company"
    PERSON = "person"
    PROJECT = "project"
    THEME = "theme"


class SourceMethod(StrEnum):
    GITHUB_RELEASES = "github_releases"
    RSS = "rss"
    HTML = "html"
    X_MCP = "x_mcp"


class EvidenceTier(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DISCOVERY_ONLY = "discovery_only"


@dataclass(frozen=True)
class SourceSpec:
    id: str
    method: SourceMethod
    url: str
    evidence_tier: EvidenceTier = EvidenceTier.PRIMARY
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TargetSpec:
    id: str
    name: str
    kind: TargetKind
    tier: TargetTier
    themes: tuple[str, ...]
    sources: tuple[SourceSpec, ...]


@dataclass(frozen=True)
class ThemeSpec:
    id: str
    name: str
    weight: int
