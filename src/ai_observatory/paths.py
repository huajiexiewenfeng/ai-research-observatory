from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    config: Path
    evidence: Path
    runs: Path
    reports: Path

    @classmethod
    def from_root(cls, root: Path) -> "ProjectPaths":
        resolved = root.resolve()
        return cls(
            root=resolved,
            config=resolved / "config",
            evidence=resolved / "evidence",
            runs=resolved / "runs",
            reports=resolved / "reports",
        )

    def ensure_runtime_dirs(self) -> None:
        for path in (self.evidence, self.runs, self.reports):
            path.mkdir(parents=True, exist_ok=True)
