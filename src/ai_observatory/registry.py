from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier, ThemeSpec


class RegistryError(ValueError):
    pass


@dataclass(frozen=True)
class Registry:
    targets: tuple[TargetSpec, ...]
    themes: tuple[ThemeSpec, ...]

    def by_kind(self, kind: str) -> tuple[TargetSpec, ...]:
        return tuple(target for target in self.targets if target.kind.value == kind)

    def by_kind_and_tier(self, kind: str, tier: str) -> tuple[TargetSpec, ...]:
        return tuple(
            target for target in self.targets
            if target.kind.value == kind and target.tier.value == tier
        )


def _read_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise RegistryError(f"mapping required: {path}")
    return payload


def load_registry(targets_path: Path, themes_path: Path) -> Registry:
    theme_rows = _read_yaml(themes_path).get("themes", [])
    themes = tuple(ThemeSpec(row["id"], row["name"], int(row["weight"])) for row in theme_rows)
    theme_ids = {theme.id for theme in themes}
    targets: list[TargetSpec] = []
    seen_targets: set[str] = set()
    seen_sources: set[str] = set()
    for row in _read_yaml(targets_path).get("targets", []):
        target_id = row["id"]
        if target_id in seen_targets:
            raise RegistryError(f"duplicate target: {target_id}")
        seen_targets.add(target_id)
        for theme_id in row.get("themes", []):
            if theme_id not in theme_ids:
                raise RegistryError(f"unknown theme: {theme_id}")
        sources: list[SourceSpec] = []
        for source_row in row.get("sources", []):
            source_id = source_row["id"]
            if source_id in seen_sources:
                raise RegistryError(f"duplicate source: {source_id}")
            seen_sources.add(source_id)
            known = {"id", "method", "url", "evidence_tier", "enabled"}
            sources.append(SourceSpec(
                id=source_id,
                method=SourceMethod(source_row["method"]),
                url=source_row["url"],
                evidence_tier=EvidenceTier(source_row.get("evidence_tier", "primary")),
                enabled=bool(source_row.get("enabled", True)),
                config={key: value for key, value in source_row.items() if key not in known},
            ))
        targets.append(TargetSpec(
            id=target_id,
            name=row["name"],
            kind=TargetKind(row["kind"]),
            tier=TargetTier(row["tier"]),
            themes=tuple(row.get("themes", [])),
            sources=tuple(sources),
        ))
    return Registry(tuple(targets), themes)
