# AI Research Observatory Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first independently useful vertical slice: load the approved target registry, collect core GitHub and official-site signals, preserve immutable Evidence, isolate source failures, and render a Chinese daily evidence report with explicit coverage.

**Architecture:** A Python CLI loads YAML target definitions, dispatches isolated source adapters, writes content-addressed Evidence to date-scoped JSONL, and records a run manifest for every planned source. This phase deliberately stops before Claim, Direction, scoring, SQLite, personal queues, and external-action drafts; those remain separate follow-on plans after the evidence foundation is proven.

**Tech Stack:** Python 3.11+, standard-library `argparse`, dataclasses and XML parsing; PyYAML 6+, Requests 2.31+, BeautifulSoup4 4.12+, pytest 8+.

## Global Constraints

- Default user-facing CLI text and generated reports are Chinese; preserve original English titles, repository names, URLs, and evidence text.
- Evidence is immutable and content-addressed. A repeated run with the same source content must not append a duplicate record.
- A source is always reported as `healthy`, `degraded`, `unavailable`, or `stale`; unavailable coverage must never be interpreted as “no updates”.
- `primary` Evidence may support later Claims; `secondary` is contextual; `discovery_only` creates verification candidates only.
- This phase is single-process and local-first. Runtime Evidence, reports, manifests, databases, credentials, and private drafts are gitignored.
- Tokens, cookies, passwords, authorization headers, and private keys must never be serialized to configuration, Evidence, logs, reports, or fixtures.
- No code in this phase may comment on GitHub, create an Issue, submit a PR, or publish to X.
- Tests run offline by default. Live network smoke tests are opt-in and never part of the default pytest command.
- Work directly on the currently checked-out branch; do not create or switch branches unless the user explicitly requests it.

## Scope Decomposition

This plan implements Phase 1 only and ends with a working evidence radar for core targets.

1. **Phase 1 — Evidence Foundation (this plan):** registry, GitHub / RSS / HTML adapters, immutable Evidence, run manifests, source health, Chinese daily report.
2. **Phase 2 — Research Intelligence (separate plan):** SQLite research graph, Signal normalization, Claim and Direction rules, four independent scores, weekly synthesis.
3. **Phase 3 — Personal Workbench (separate plan):** Research Gate, External Action Gate, WIP-limited learning / contribution / communication queues, review UI.
4. **Phase 4 — Community Integrations and Hardening (separate plan):** X host bridge, AI Radar Evidence import, external-action drafts, failure injection matrix, full golden-week acceptance.

## File Structure

```text
pyproject.toml                         # package metadata, dependencies, CLI entry point
.gitignore                             # excludes all private/runtime artifacts
README.md                              # Phase 1 setup, commands, safety boundary
config/targets.yaml                    # approved company/project registry and core sources
config/themes.yaml                     # personalized research themes
src/ai_observatory/__init__.py         # package version
src/ai_observatory/cli.py              # health, validate-config, scan, render-daily commands
src/ai_observatory/paths.py            # project-relative runtime paths
src/ai_observatory/domain.py           # target, source, tier and evidence enums/models
src/ai_observatory/registry.py         # YAML loading and validation
src/ai_observatory/evidence.py         # Evidence construction, hashing and JSON conversion
src/ai_observatory/ledger.py           # immutable date-scoped JSONL ledger
src/ai_observatory/sources/base.py      # adapter protocol, context, result and registry
src/ai_observatory/sources/github.py    # GitHub Releases collector
src/ai_observatory/sources/feed.py      # RSS / Atom collector
src/ai_observatory/sources/html.py      # configured official-page collector
src/ai_observatory/runner.py            # isolated orchestration and run manifest
src/ai_observatory/reports.py           # Chinese coverage and daily Evidence reports
tests/fixtures/                         # offline GitHub, RSS, Atom and HTML snapshots
tests/test_cli.py
tests/test_registry.py
tests/test_ledger.py
tests/test_adapter_contract.py
tests/test_github_adapter.py
tests/test_feed_html_adapters.py
tests/test_runner.py
tests/test_reports.py
tests/test_golden_phase1.py
```

---

### Task 1: Bootstrap the Python package and safe runtime paths

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `src/ai_observatory/__init__.py`
- Create: `src/ai_observatory/paths.py`
- Create: `src/ai_observatory/cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: no earlier task.
- Produces: `ProjectPaths.from_root(root: Path) -> ProjectPaths`, `ProjectPaths.ensure_runtime_dirs() -> None`, `main(argv: Sequence[str] | None = None) -> int`, and the `ai-observatory` console entry point.

- [ ] **Step 1: Write the failing CLI test**

```python
# tests/test_cli.py
from ai_observatory.cli import main


def test_health_command_prints_chinese_status(capsys):
    assert main(["health"]) == 0
    assert capsys.readouterr().out.strip() == "AI Research Observatory：运行正常"
```

- [ ] **Step 2: Run the test and verify the package does not exist**

Run:

```powershell
python -m pytest tests/test_cli.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'ai_observatory'`.

- [ ] **Step 3: Add package metadata, runtime exclusions, paths, and the minimal CLI**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-research-observatory"
version = "0.1.0"
description = "A local-first, evidence-driven AI research observatory."
requires-python = ">=3.11"
dependencies = [
  "PyYAML>=6.0.1",
  "requests>=2.31.0",
  "beautifulsoup4>=4.12.3",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[project.scripts]
ai-observatory = "ai_observatory.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

```gitignore
# .gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
*.egg-info/
evidence/
runs/
data/
reports/
cards/
review/
.env
.browser-profile/
.superpowers/
```

```python
# src/ai_observatory/__init__.py
__version__ = "0.1.0"
```

```python
# src/ai_observatory/paths.py
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
```

```python
# src/ai_observatory/cli.py
from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-observatory")
    parser.add_subparsers(dest="command", required=True).add_parser("health")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "health":
        print("AI Research Observatory：运行正常")
        return 0
    raise AssertionError(f"unsupported command: {args.command}")
```

- [ ] **Step 4: Install the editable package and verify the test passes**

Run:

```powershell
python -m pip install -e ".[dev]"
python -m pytest tests/test_cli.py -v
```

Expected: `1 passed`.

- [ ] **Step 5: Commit the bootstrap**

```powershell
git add pyproject.toml .gitignore src/ai_observatory tests/test_cli.py
git commit -m "build: bootstrap observatory package"
```

---

### Task 2: Model and validate the approved target registry

**Files:**
- Create: `src/ai_observatory/domain.py`
- Create: `src/ai_observatory/registry.py`
- Create: `config/targets.yaml`
- Create: `config/themes.yaml`
- Create: `tests/test_registry.py`
- Modify: `src/ai_observatory/cli.py`

**Interfaces:**
- Consumes: `ProjectPaths.config` from Task 1.
- Produces: `TargetTier`, `TargetKind`, `SourceMethod`, `EvidenceTier`, `SourceSpec`, `TargetSpec`, `ThemeSpec`, `Registry`, and `load_registry(targets_path: Path, themes_path: Path) -> Registry`.

- [ ] **Step 1: Write registry tests for approved counts and invalid references**

```python
# tests/test_registry.py
from pathlib import Path

import pytest

from ai_observatory.registry import RegistryError, load_registry


ROOT = Path(__file__).parents[1]


def test_registry_contains_approved_target_pool():
    registry = load_registry(ROOT / "config/targets.yaml", ROOT / "config/themes.yaml")
    assert len(registry.by_kind("company")) == 17
    assert len(registry.by_kind("project")) == 28
    assert len(registry.by_kind_and_tier("company", "core")) == 6
    assert len(registry.by_kind_and_tier("project", "core")) == 8


def test_registry_rejects_unknown_theme(tmp_path):
    targets = tmp_path / "targets.yaml"
    themes = tmp_path / "themes.yaml"
    targets.write_text(
        "targets:\n  - id: bad\n    name: Bad\n    kind: project\n    tier: core\n"
        "    themes: [missing]\n    sources: []\n",
        encoding="utf-8",
    )
    themes.write_text("themes: []\n", encoding="utf-8")
    with pytest.raises(RegistryError, match="unknown theme: missing"):
        load_registry(targets, themes)
```

- [ ] **Step 2: Run the registry tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_registry.py -v
```

Expected: import fails because `ai_observatory.registry` does not exist.

- [ ] **Step 3: Add the domain types and strict YAML loader**

```python
# src/ai_observatory/domain.py
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
```

```python
# src/ai_observatory/registry.py
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
            target
            for target in self.targets
            if target.kind.value == kind and target.tier.value == tier
        )


def _read_yaml(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise RegistryError(f"mapping required: {path}")
    return payload


def load_registry(targets_path: Path, themes_path: Path) -> Registry:
    theme_rows = _read_yaml(themes_path).get("themes", [])
    themes = tuple(
        ThemeSpec(id=row["id"], name=row["name"], weight=int(row["weight"]))
        for row in theme_rows
    )
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
            sources.append(
                SourceSpec(
                    id=source_id,
                    method=SourceMethod(source_row["method"]),
                    url=source_row["url"],
                    evidence_tier=EvidenceTier(source_row.get("evidence_tier", "primary")),
                    enabled=bool(source_row.get("enabled", True)),
                    config={key: value for key, value in source_row.items() if key not in known},
                )
            )
        targets.append(
            TargetSpec(
                id=target_id,
                name=row["name"],
                kind=TargetKind(row["kind"]),
                tier=TargetTier(row["tier"]),
                themes=tuple(row.get("themes", [])),
                sources=tuple(sources),
            )
        )
    return Registry(targets=tuple(targets), themes=themes)
```

Create `config/themes.yaml` with these exact rows:

```yaml
themes:
  - {id: agent_runtime, name: Agent Knowledge Runtime, weight: 20}
  - {id: agent_infra, name: Agent Infra / Harness, weight: 20}
  - {id: rag, name: RAG / Knowledge Engineering, weight: 15}
  - {id: inference, name: Inference / Serving, weight: 15}
  - {id: enterprise_transfer, name: Enterprise / Java Transferability, weight: 15}
```

Create the complete approved `config/targets.yaml`. Disabled sources intentionally preserve coverage without guessing selectors or implementing the X host bridge in Phase 1:

```yaml
targets:
  - id: openai
    name: OpenAI
    kind: company
    tier: core
    themes: [agent_runtime, agent_infra]
    sources:
      - {id: openai_news_rss, method: rss, url: "https://openai.com/news/rss.xml", evidence_tier: primary, enabled: true, max_items: 20}
  - id: anthropic
    name: Anthropic
    kind: company
    tier: core
    themes: [agent_runtime, agent_infra]
    sources:
      - {id: anthropic_news_html, method: html, url: "https://www.anthropic.com/news", evidence_tier: primary, enabled: false, reason: selector_not_verified}
  - id: google_deepmind
    name: Google DeepMind
    kind: company
    tier: core
    themes: [agent_runtime, inference]
    sources:
      - {id: deepmind_blog_rss, method: rss, url: "https://deepmind.google/blog/rss.xml", evidence_tier: primary, enabled: true, max_items: 20}
  - id: meta_ai
    name: Meta AI / FAIR
    kind: company
    tier: core
    themes: [agent_runtime, inference]
    sources:
      - {id: meta_ai_blog_html, method: html, url: "https://ai.meta.com/blog/", evidence_tier: primary, enabled: false, reason: selector_not_verified}
  - id: deepseek
    name: DeepSeek
    kind: company
    tier: core
    themes: [inference, agent_runtime]
    sources:
      - {id: deepseek_x, method: x_mcp, url: "https://x.com/deepseek_ai", evidence_tier: primary, enabled: false, reason: phase4_host_bridge}
  - id: alibaba_qwen
    name: Alibaba Qwen
    kind: company
    tier: core
    themes: [agent_runtime, inference]
    sources:
      - {id: qwen_x, method: x_mcp, url: "https://x.com/Alibaba_Qwen", evidence_tier: primary, enabled: false, reason: phase4_host_bridge}

  - {id: microsoft_research, name: Microsoft Research, kind: company, tier: watch, themes: [agent_infra, enterprise_transfer], sources: []}
  - {id: nvidia_research, name: NVIDIA Research, kind: company, tier: watch, themes: [inference], sources: []}
  - {id: hugging_face, name: Hugging Face, kind: company, tier: watch, themes: [agent_infra, inference], sources: []}
  - {id: mistral_ai, name: Mistral AI, kind: company, tier: watch, themes: [inference], sources: []}
  - {id: moonshot_ai, name: Moonshot AI, kind: company, tier: watch, themes: [agent_runtime], sources: []}
  - {id: bytedance_seed, name: ByteDance Seed, kind: company, tier: watch, themes: [agent_runtime, inference], sources: []}
  - {id: zhipu_ai, name: Zhipu AI, kind: company, tier: watch, themes: [agent_runtime], sources: []}
  - {id: minimax, name: MiniMax, kind: company, tier: watch, themes: [agent_runtime], sources: []}
  - {id: cohere, name: Cohere, kind: company, tier: watch, themes: [rag, enterprise_transfer], sources: []}
  - {id: xai, name: xAI, kind: company, tier: watch, themes: [inference], sources: []}
  - {id: megvii, name: Megvii, kind: company, tier: personal, themes: [enterprise_transfer], sources: []}

  - id: langgenius_dify
    name: Dify
    kind: project
    tier: core
    themes: [agent_runtime, rag, enterprise_transfer]
    sources:
      - {id: dify_releases, method: github_releases, url: "https://github.com/langgenius/dify", evidence_tier: primary, enabled: true, repo: "langgenius/dify", max_items: 5}
  - id: run_llama_llama_index
    name: LlamaIndex
    kind: project
    tier: core
    themes: [agent_runtime, rag]
    sources:
      - {id: llama_index_releases, method: github_releases, url: "https://github.com/run-llama/llama_index", evidence_tier: primary, enabled: true, repo: "run-llama/llama_index", max_items: 5}
  - id: langchain_ai_langgraph
    name: LangGraph
    kind: project
    tier: core
    themes: [agent_runtime, agent_infra]
    sources:
      - {id: langgraph_releases, method: github_releases, url: "https://github.com/langchain-ai/langgraph", evidence_tier: primary, enabled: true, repo: "langchain-ai/langgraph", max_items: 5}
  - id: modelcontextprotocol_modelcontextprotocol
    name: Model Context Protocol
    kind: project
    tier: core
    themes: [agent_runtime, agent_infra]
    sources:
      - {id: mcp_releases, method: github_releases, url: "https://github.com/modelcontextprotocol/modelcontextprotocol", evidence_tier: primary, enabled: true, repo: "modelcontextprotocol/modelcontextprotocol", max_items: 5}
  - id: vllm_project_vllm
    name: vLLM
    kind: project
    tier: core
    themes: [inference]
    sources:
      - {id: vllm_releases, method: github_releases, url: "https://github.com/vllm-project/vllm", evidence_tier: primary, enabled: true, repo: "vllm-project/vllm", max_items: 5}
  - id: sgl_project_sglang
    name: SGLang
    kind: project
    tier: core
    themes: [inference]
    sources:
      - {id: sglang_releases, method: github_releases, url: "https://github.com/sgl-project/sglang", evidence_tier: primary, enabled: true, repo: "sgl-project/sglang", max_items: 5}
  - id: langfuse_langfuse
    name: Langfuse
    kind: project
    tier: core
    themes: [agent_infra]
    sources:
      - {id: langfuse_releases, method: github_releases, url: "https://github.com/langfuse/langfuse", evidence_tier: primary, enabled: true, repo: "langfuse/langfuse", max_items: 5}
  - id: letta_ai_letta
    name: Letta
    kind: project
    tier: core
    themes: [agent_runtime]
    sources:
      - {id: letta_releases, method: github_releases, url: "https://github.com/letta-ai/letta", evidence_tier: primary, enabled: true, repo: "letta-ai/letta", max_items: 5}

  - {id: infiniflow_ragflow, name: RAGFlow, kind: project, tier: watch, themes: [rag], sources: []}
  - {id: deepset_ai_haystack, name: Haystack, kind: project, tier: watch, themes: [rag], sources: []}
  - {id: labring_fastgpt, name: FastGPT, kind: project, tier: watch, themes: [rag, enterprise_transfer], sources: []}
  - {id: hkuds_lightrag, name: LightRAG, kind: project, tier: watch, themes: [rag], sources: []}
  - {id: openai_openai_agents_python, name: OpenAI Agents SDK, kind: project, tier: watch, themes: [agent_runtime], sources: []}
  - {id: microsoft_autogen, name: AutoGen, kind: project, tier: watch, themes: [agent_runtime], sources: []}
  - {id: crewaiinc_crewai, name: CrewAI, kind: project, tier: watch, themes: [agent_runtime], sources: []}
  - {id: openhands_openhands, name: OpenHands, kind: project, tier: watch, themes: [agent_runtime, agent_infra], sources: []}
  - {id: browser_use_browser_use, name: browser-use, kind: project, tier: watch, themes: [agent_runtime], sources: []}
  - {id: google_adk_python, name: Google ADK, kind: project, tier: watch, themes: [agent_runtime], sources: []}
  - {id: ggml_org_llama_cpp, name: llama.cpp, kind: project, tier: watch, themes: [inference], sources: []}
  - {id: nvidia_tensorrt_llm, name: TensorRT-LLM, kind: project, tier: watch, themes: [inference], sources: []}
  - {id: deepspeedai_deepspeed, name: DeepSpeed, kind: project, tier: watch, themes: [inference], sources: []}
  - {id: ray_project_ray, name: Ray, kind: project, tier: watch, themes: [agent_infra, inference], sources: []}
  - {id: ollama_ollama, name: Ollama, kind: project, tier: watch, themes: [inference], sources: []}
  - {id: arize_ai_phoenix, name: Phoenix, kind: project, tier: watch, themes: [agent_infra], sources: []}
  - {id: vibrantlabsai_ragas, name: Ragas, kind: project, tier: watch, themes: [rag, agent_infra], sources: []}
  - {id: confident_ai_deepeval, name: DeepEval, kind: project, tier: watch, themes: [agent_infra], sources: []}
  - {id: promptfoo_promptfoo, name: promptfoo, kind: project, tier: watch, themes: [agent_infra], sources: []}
  - {id: mem0ai_mem0, name: Mem0, kind: project, tier: watch, themes: [agent_runtime], sources: []}
```

- [ ] **Step 4: Replace the CLI with exact `health` and `validate-config` commands, then run the tests**

```python
# src/ai_observatory/cli.py
from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .paths import ProjectPaths
from .registry import load_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-observatory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    validate = subparsers.add_parser("validate-config")
    validate.add_argument("--root", type=Path, default=Path.cwd())
    return parser


def _validate_config(root: Path) -> int:
    paths = ProjectPaths.from_root(root)
    registry = load_registry(paths.config / "targets.yaml", paths.config / "themes.yaml")
    print(f"配置有效：{len(registry.targets)} 个观察对象，{len(registry.themes)} 个研究主题")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "health":
        print("AI Research Observatory：运行正常")
        return 0
    if args.command == "validate-config":
        return _validate_config(args.root)
    raise AssertionError(f"unsupported command: {args.command}")
```

Run:

```powershell
python -m pytest tests/test_registry.py -v
ai-observatory validate-config --root .
```

Expected: registry tests pass and CLI prints `配置有效：45 个观察对象，5 个研究主题`.

- [ ] **Step 5: Commit the registry**

```powershell
git add config src/ai_observatory/domain.py src/ai_observatory/registry.py src/ai_observatory/cli.py tests/test_registry.py
git commit -m "feat: add approved observation registry"
```

---

### Task 3: Implement immutable content-addressed Evidence

**Files:**
- Create: `src/ai_observatory/evidence.py`
- Create: `src/ai_observatory/ledger.py`
- Create: `tests/test_ledger.py`

**Interfaces:**
- Consumes: `EvidenceTier` and `SourceMethod` from Task 2.
- Produces: `Evidence.create(...) -> Evidence`, `Evidence.to_dict() -> dict`, `EvidenceLedger.append(run_date: date, evidence: Evidence) -> bool`, and `EvidenceLedger.read_date(run_date: date) -> tuple[Evidence, ...]`.

- [ ] **Step 1: Write failing tests for deterministic IDs and append idempotency**

```python
# tests/test_ledger.py
from datetime import UTC, date, datetime

from ai_observatory.domain import EvidenceTier, SourceMethod
from ai_observatory.evidence import Evidence
from ai_observatory.ledger import EvidenceLedger


def sample_evidence() -> Evidence:
    return Evidence.create(
        target_id="vllm_project_vllm",
        source_id="vllm_releases",
        source_method=SourceMethod.GITHUB_RELEASES,
        evidence_tier=EvidenceTier.PRIMARY,
        title="v0.9.0",
        url="https://github.com/vllm-project/vllm/releases/tag/v0.9.0",
        content="release notes",
        published_at=datetime(2026, 8, 19, tzinfo=UTC),
        collected_at=datetime(2026, 8, 19, 1, tzinfo=UTC),
        run_id="run-1",
    )


def test_evidence_id_is_deterministic():
    assert sample_evidence().evidence_id == sample_evidence().evidence_id


def test_ledger_does_not_append_duplicate(tmp_path):
    ledger = EvidenceLedger(tmp_path)
    evidence = sample_evidence()
    assert ledger.append(date(2026, 8, 19), evidence) is True
    assert ledger.append(date(2026, 8, 19), evidence) is False
    assert ledger.read_date(date(2026, 8, 19)) == (evidence,)
```

- [ ] **Step 2: Run the ledger tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_ledger.py -v
```

Expected: import fails because `ai_observatory.evidence` does not exist.

- [ ] **Step 3: Implement canonical Evidence and the JSONL ledger**

```python
# src/ai_observatory/evidence.py
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime

from .domain import EvidenceTier, SourceMethod


@dataclass(frozen=True)
class Evidence:
    schema_version: int
    evidence_id: str
    target_id: str
    source_id: str
    source_method: SourceMethod
    evidence_tier: EvidenceTier
    title: str
    url: str
    content: str
    published_at: datetime
    collected_at: datetime
    content_hash: str
    run_id: str

    @classmethod
    def create(
        cls,
        *,
        target_id: str,
        source_id: str,
        source_method: SourceMethod,
        evidence_tier: EvidenceTier,
        title: str,
        url: str,
        content: str,
        published_at: datetime,
        collected_at: datetime,
        run_id: str,
    ) -> "Evidence":
        normalized = " ".join(content.split())
        content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        identity = json.dumps(
            [target_id, source_id, url, published_at.isoformat(), content_hash],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        evidence_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        return cls(
            schema_version=1,
            evidence_id=evidence_id,
            target_id=target_id,
            source_id=source_id,
            source_method=source_method,
            evidence_tier=evidence_tier,
            title=title.strip(),
            url=url,
            content=normalized,
            published_at=published_at,
            collected_at=collected_at,
            content_hash=content_hash,
            run_id=run_id,
        )

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["source_method"] = self.source_method.value
        payload["evidence_tier"] = self.evidence_tier.value
        payload["published_at"] = self.published_at.isoformat()
        payload["collected_at"] = self.collected_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "Evidence":
        return cls(
            **{
                **payload,
                "source_method": SourceMethod(payload["source_method"]),
                "evidence_tier": EvidenceTier(payload["evidence_tier"]),
                "published_at": datetime.fromisoformat(payload["published_at"]),
                "collected_at": datetime.fromisoformat(payload["collected_at"]),
            }
        )
```

```python
# src/ai_observatory/ledger.py
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
```

- [ ] **Step 4: Run the tests twice to verify idempotency**

Run:

```powershell
python -m pytest tests/test_ledger.py -v
python -m pytest tests/test_ledger.py -v
```

Expected: both runs report `2 passed`.

- [ ] **Step 5: Commit the Evidence ledger**

```powershell
git add src/ai_observatory/evidence.py src/ai_observatory/ledger.py tests/test_ledger.py
git commit -m "feat: add immutable evidence ledger"
```

---

### Task 4: Define the source adapter contract and fixture adapter

**Files:**
- Create: `src/ai_observatory/sources/__init__.py`
- Create: `src/ai_observatory/sources/base.py`
- Create: `tests/test_adapter_contract.py`

**Interfaces:**
- Consumes: `SourceSpec`, `TargetSpec`, and `Evidence`.
- Produces: `SourceStatus`, `CollectContext`, `CollectResult`, `SourceAdapter.collect(...)`, and `AdapterRegistry.get(method: SourceMethod) -> SourceAdapter`.

- [ ] **Step 1: Write a failing test for successful zero-result coverage**

```python
# tests/test_adapter_contract.py
from datetime import UTC, date, datetime

from ai_observatory.domain import SourceMethod
from ai_observatory.sources.base import AdapterRegistry, CollectContext, CollectResult, SourceStatus


class EmptyAdapter:
    method = SourceMethod.RSS

    def collect(self, target, source, context):
        return CollectResult(status=SourceStatus.HEALTHY, evidence=(), diagnostics={"queried": True})


def test_successful_zero_result_is_healthy():
    registry = AdapterRegistry([EmptyAdapter()])
    result = registry.get(SourceMethod.RSS).collect(
        None,
        None,
        CollectContext(
            run_id="run-1",
            run_date=date(2026, 8, 19),
            collected_at=datetime(2026, 8, 19, tzinfo=UTC),
            timeout_seconds=10,
        ),
    )
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence == ()
    assert result.diagnostics["queried"] is True
```

- [ ] **Step 2: Run the contract test and verify it fails**

Run: `python -m pytest tests/test_adapter_contract.py -v`

Expected: import fails because `ai_observatory.sources.base` does not exist.

- [ ] **Step 3: Implement the adapter types and registry**

```python
# src/ai_observatory/sources/__init__.py
"""Source adapters."""
```

```python
# src/ai_observatory/sources/base.py
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

    def collect(
        self,
        target: TargetSpec,
        source: SourceSpec,
        context: CollectContext,
    ) -> CollectResult: ...


class AdapterRegistry:
    def __init__(self, adapters: list[SourceAdapter]):
        self._adapters = {adapter.method: adapter for adapter in adapters}

    def get(self, method: SourceMethod) -> SourceAdapter:
        try:
            return self._adapters[method]
        except KeyError as exc:
            raise LookupError(f"no adapter for {method.value}") from exc
```

- [ ] **Step 4: Run the adapter test**

Run: `python -m pytest tests/test_adapter_contract.py -v`

Expected: `1 passed`.

- [ ] **Step 5: Commit the adapter contract**

```powershell
git add src/ai_observatory/sources tests/test_adapter_contract.py
git commit -m "feat: define source adapter contract"
```

---

### Task 5: Collect GitHub Releases with rate-limit diagnostics

**Files:**
- Create: `src/ai_observatory/sources/github.py`
- Create: `tests/test_github_adapter.py`

**Interfaces:**
- Consumes: Task 4 adapter contract and Task 3 `Evidence.create`.
- Produces: `GitHubReleasesAdapter(session: requests.Session | None = None)` with `method = SourceMethod.GITHUB_RELEASES`.

- [ ] **Step 1: Write failing tests for a release and a rate-limit response**

```python
# tests/test_github_adapter.py
from datetime import UTC, date, datetime
import json
from types import SimpleNamespace

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier
from ai_observatory.sources.base import CollectContext, SourceStatus
from ai_observatory.sources.github import GitHubReleasesAdapter


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.last_kwargs = None

    def get(self, *args, **kwargs):
        self.last_kwargs = kwargs
        return self.response


def target_and_source():
    target = TargetSpec("vllm_project_vllm", "vLLM", TargetKind.PROJECT, TargetTier.CORE, ("inference",), ())
    source = SourceSpec(
        "vllm_releases",
        SourceMethod.GITHUB_RELEASES,
        "https://github.com/vllm-project/vllm",
        EvidenceTier.PRIMARY,
        True,
        {"repo": "vllm-project/vllm", "max_items": 5},
    )
    return target, source


def context():
    return CollectContext("run-1", date(2026, 8, 19), datetime(2026, 8, 19, tzinfo=UTC), 10)


def test_collects_release_as_primary_evidence():
    response = SimpleNamespace(
        status_code=200,
        headers={"X-RateLimit-Remaining": "4999"},
        json=lambda: [{
            "name": "v0.9.0", "tag_name": "v0.9.0", "body": "release notes",
            "html_url": "https://github.com/vllm-project/vllm/releases/tag/v0.9.0",
            "published_at": "2026-08-19T00:00:00Z", "draft": False, "prerelease": False,
        }],
    )
    result = GitHubReleasesAdapter(FakeSession(response)).collect(*target_and_source(), context())
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence[0].title == "v0.9.0"
    assert result.diagnostics["rate_limit_remaining"] == 4999


def test_rate_limit_is_unavailable_not_empty():
    response = SimpleNamespace(
        status_code=403,
        headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1787100000"},
        json=lambda: {"message": "rate limit"},
    )
    result = GitHubReleasesAdapter(FakeSession(response)).collect(*target_and_source(), context())
    assert result.status is SourceStatus.UNAVAILABLE
    assert result.evidence == ()
    assert result.diagnostics["reason"] == "rate_limited"


def test_optional_token_is_request_only(monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        headers={"X-RateLimit-Remaining": "4999"},
        json=lambda: [],
    )
    session = FakeSession(response)
    monkeypatch.setenv("GITHUB_TOKEN", "test-secret-token")
    result = GitHubReleasesAdapter(session).collect(*target_and_source(), context())
    assert session.last_kwargs["headers"]["Authorization"] == "Bearer test-secret-token"
    assert "test-secret-token" not in json.dumps(result.diagnostics)
```

- [ ] **Step 2: Run the GitHub tests and verify they fail**

Run: `python -m pytest tests/test_github_adapter.py -v`

Expected: import fails because `ai_observatory.sources.github` does not exist.

- [ ] **Step 3: Implement the read-only GitHub Releases adapter**

```python
# src/ai_observatory/sources/github.py
from __future__ import annotations

from datetime import datetime
import os

import requests

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


class GitHubReleasesAdapter:
    method = SourceMethod.GITHUB_RELEASES

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        repo = source.config["repo"]
        limit = int(source.config.get("max_items", 5))
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.session.get(
            f"https://api.github.com/repos/{repo}/releases",
            params={"per_page": limit},
            headers=headers,
            timeout=context.timeout_seconds,
        )
        remaining = int(response.headers.get("X-RateLimit-Remaining", "-1"))
        if response.status_code == 403 and remaining == 0:
            return CollectResult(
                SourceStatus.UNAVAILABLE,
                (),
                {
                    "reason": "rate_limited",
                    "rate_limit_remaining": remaining,
                    "rate_limit_reset": response.headers.get("X-RateLimit-Reset"),
                },
            )
        if response.status_code != 200:
            return CollectResult(
                SourceStatus.UNAVAILABLE,
                (),
                {"reason": "http_error", "status_code": response.status_code},
            )
        evidence = tuple(
            Evidence.create(
                target_id=target.id,
                source_id=source.id,
                source_method=source.method,
                evidence_tier=source.evidence_tier,
                title=row.get("name") or row["tag_name"],
                url=row["html_url"],
                content=row.get("body") or row["tag_name"],
                published_at=datetime.fromisoformat(row["published_at"].replace("Z", "+00:00")),
                collected_at=context.collected_at,
                run_id=context.run_id,
            )
            for row in response.json()
            if not row.get("draft") and not row.get("prerelease")
        )
        return CollectResult(
            SourceStatus.HEALTHY,
            evidence,
            {"queried": True, "rate_limit_remaining": remaining, "record_count": len(evidence)},
        )
```

- [ ] **Step 4: Run the GitHub adapter tests**

Run: `python -m pytest tests/test_github_adapter.py -v`

Expected: `3 passed`.

- [ ] **Step 5: Commit the GitHub collector**

```powershell
git add src/ai_observatory/sources/github.py tests/test_github_adapter.py
git commit -m "feat: collect github release evidence"
```

---

### Task 6: Collect official RSS, Atom, and configured HTML pages

**Files:**
- Create: `src/ai_observatory/sources/feed.py`
- Create: `src/ai_observatory/sources/html.py`
- Create: `tests/fixtures/feed/sample-rss.xml`
- Create: `tests/fixtures/feed/sample-atom.xml`
- Create: `tests/fixtures/html/sample-news.html`
- Create: `tests/test_feed_html_adapters.py`

**Interfaces:**
- Consumes: adapter contract and `Evidence.create`.
- Produces: `FeedAdapter(session=None)` for `SourceMethod.RSS` and `HtmlAdapter(session=None)` for `SourceMethod.HTML`.

- [ ] **Step 1: Write failing offline parsing tests**

```python
# tests/test_feed_html_adapters.py
from datetime import UTC, date, datetime
from pathlib import Path

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier
from ai_observatory.sources.base import CollectContext, SourceStatus
from ai_observatory.sources.feed import FeedAdapter
from ai_observatory.sources.html import HtmlAdapter


FIXTURES = Path(__file__).parent / "fixtures"


class TextResponse:
    status_code = 200
    headers = {}

    def __init__(self, text):
        self.text = text
        self.content = text.encode("utf-8")


class FakeSession:
    def __init__(self, text):
        self.text = text

    def get(self, *args, **kwargs):
        return TextResponse(self.text)


TARGET = TargetSpec("openai", "OpenAI", TargetKind.COMPANY, TargetTier.CORE, ("agent_runtime",), ())
CONTEXT = CollectContext("run-1", date(2026, 8, 19), datetime(2026, 8, 19, tzinfo=UTC), 10)


def test_rss_adapter_extracts_primary_evidence():
    xml = (FIXTURES / "feed/sample-rss.xml").read_text(encoding="utf-8")
    source = SourceSpec("openai_rss", SourceMethod.RSS, "https://example.test/rss", EvidenceTier.PRIMARY)
    result = FeedAdapter(FakeSession(xml)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence[0].title == "Agent Runtime Update"


def test_html_adapter_requires_configured_selector():
    html = (FIXTURES / "html/sample-news.html").read_text(encoding="utf-8")
    source = SourceSpec(
        "openai_html", SourceMethod.HTML, "https://example.test/news", EvidenceTier.PRIMARY,
        True, {"item_selector": "article", "title_selector": "h2", "link_selector": "a"},
    )
    result = HtmlAdapter(FakeSession(html)).collect(TARGET, source, CONTEXT)
    assert result.status is SourceStatus.HEALTHY
    assert result.evidence[0].url == "https://example.test/research/agent-runtime"
```

- [ ] **Step 2: Add exact fixtures and verify tests fail for missing adapters**

```xml
<!-- tests/fixtures/feed/sample-rss.xml -->
<rss version="2.0"><channel><title>Research</title><item>
<title>Agent Runtime Update</title>
<link>https://example.test/research/agent-runtime</link>
<description>Evidence-first runtime design.</description>
<pubDate>Wed, 19 Aug 2026 00:00:00 GMT</pubDate>
</item></channel></rss>
```

```xml
<!-- tests/fixtures/feed/sample-atom.xml -->
<feed xmlns="http://www.w3.org/2005/Atom"><title>Research</title><entry>
<title>Serving Update</title><link href="https://example.test/serving"/>
<summary>Lower latency serving.</summary><updated>2026-08-19T00:00:00Z</updated>
</entry></feed>
```

```html
<!-- tests/fixtures/html/sample-news.html -->
<main><article><h2>Agent Runtime Update</h2>
<a href="/research/agent-runtime">Read</a><p>Evidence-first runtime design.</p>
<time datetime="2026-08-19T00:00:00Z">2026-08-19</time></article></main>
```

Run: `python -m pytest tests/test_feed_html_adapters.py -v`

Expected: import fails for the missing adapter modules.

- [ ] **Step 3: Implement FeedAdapter and HtmlAdapter**

```python
# src/ai_observatory/sources/feed.py
from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin
from xml.etree import ElementTree

import requests

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


ATOM = "{http://www.w3.org/2005/Atom}"


def _parse_date(value: str | None, fallback: datetime) -> tuple[datetime, bool]:
    if not value:
        return fallback, True
    try:
        if "," in value:
            return parsedate_to_datetime(value), False
        return datetime.fromisoformat(value.replace("Z", "+00:00")), False
    except (TypeError, ValueError):
        return fallback, True


class FeedAdapter:
    method = SourceMethod.RSS

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        response = self.session.get(source.url, timeout=context.timeout_seconds)
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "http_error", "status_code": response.status_code})
        try:
            root = ElementTree.fromstring(response.content)
        except ElementTree.ParseError as exc:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "parse_error", "message": str(exc)})

        rows: list[tuple[str, str, str, str | None]] = []
        for item in root.findall(".//item"):
            rows.append((
                item.findtext("title") or "Untitled",
                item.findtext("link") or source.url,
                item.findtext("description") or "",
                item.findtext("pubDate"),
            ))
        for entry in root.findall(f".//{ATOM}entry"):
            link = entry.find(f"{ATOM}link")
            rows.append((
                entry.findtext(f"{ATOM}title") or "Untitled",
                (link.get("href") if link is not None else None) or source.url,
                entry.findtext(f"{ATOM}summary") or entry.findtext(f"{ATOM}content") or "",
                entry.findtext(f"{ATOM}published") or entry.findtext(f"{ATOM}updated"),
            ))

        evidence: list[Evidence] = []
        inferred_dates = 0
        for title, link, content, published in rows[: int(source.config.get("max_items", 20))]:
            published_at, inferred = _parse_date(published, context.collected_at)
            inferred_dates += int(inferred)
            evidence.append(Evidence.create(
                target_id=target.id,
                source_id=source.id,
                source_method=source.method,
                evidence_tier=source.evidence_tier,
                title=title,
                url=urljoin(source.url, link),
                content=content or title,
                published_at=published_at,
                collected_at=context.collected_at,
                run_id=context.run_id,
            ))
        return CollectResult(
            SourceStatus.HEALTHY,
            tuple(evidence),
            {"queried": True, "record_count": len(evidence), "published_at_inferred_count": inferred_dates},
        )
```

```python
# src/ai_observatory/sources/html.py
from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..domain import SourceMethod, SourceSpec, TargetSpec
from ..evidence import Evidence
from .base import CollectContext, CollectResult, SourceStatus


def _html_date(item, fallback: datetime) -> tuple[datetime, bool]:
    time = item.select_one("time[datetime]")
    if time is None:
        return fallback, True
    try:
        return datetime.fromisoformat(time["datetime"].replace("Z", "+00:00")), False
    except ValueError:
        return fallback, True


class HtmlAdapter:
    method = SourceMethod.HTML

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def collect(self, target: TargetSpec, source: SourceSpec, context: CollectContext) -> CollectResult:
        required = ("item_selector", "title_selector", "link_selector")
        if any(not source.config.get(key) for key in required):
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "invalid_config"})
        response = self.session.get(source.url, timeout=context.timeout_seconds)
        if response.status_code != 200:
            return CollectResult(SourceStatus.UNAVAILABLE, (), {"reason": "http_error", "status_code": response.status_code})
        soup = BeautifulSoup(response.text, "html.parser")
        evidence: list[Evidence] = []
        inferred_dates = 0
        limit = int(source.config.get("max_items", 20))
        for item in soup.select(source.config["item_selector"])[:limit]:
            title_node = item.select_one(source.config["title_selector"])
            link_node = item.select_one(source.config["link_selector"])
            if title_node is None or link_node is None or not link_node.get("href"):
                continue
            published_at, inferred = _html_date(item, context.collected_at)
            inferred_dates += int(inferred)
            title = title_node.get_text(" ", strip=True)
            evidence.append(Evidence.create(
                target_id=target.id,
                source_id=source.id,
                source_method=source.method,
                evidence_tier=source.evidence_tier,
                title=title,
                url=urljoin(source.url, link_node["href"]),
                content=item.get_text(" ", strip=True) or title,
                published_at=published_at,
                collected_at=context.collected_at,
                run_id=context.run_id,
            ))
        return CollectResult(
            SourceStatus.HEALTHY,
            tuple(evidence),
            {"queried": True, "record_count": len(evidence), "published_at_inferred_count": inferred_dates},
        )
```

- [ ] **Step 4: Run adapter and regression tests**

Run:

```powershell
python -m pytest tests/test_feed_html_adapters.py tests/test_github_adapter.py -v
```

Expected: all tests pass; no live network calls occur.

- [ ] **Step 5: Commit the official-site adapters**

```powershell
git add src/ai_observatory/sources/feed.py src/ai_observatory/sources/html.py tests/fixtures/feed tests/fixtures/html tests/test_feed_html_adapters.py
git commit -m "feat: collect official site evidence"
```

---

### Task 7: Orchestrate isolated collection and persist run manifests

**Files:**
- Create: `src/ai_observatory/runner.py`
- Create: `tests/test_runner.py`
- Modify: `src/ai_observatory/cli.py`

**Interfaces:**
- Consumes: `Registry`, `AdapterRegistry`, `EvidenceLedger`, and adapter results.
- Produces: `SourceRun`, `RunResult`, `run_collection(...) -> RunResult`, and CLI `scan --date YYYY-MM-DD --profile core --root PATH`.

- [ ] **Step 1: Write failing tests for source isolation and idempotent reruns**

```python
# tests/test_runner.py
from datetime import UTC, date, datetime

from ai_observatory.domain import EvidenceTier, SourceMethod, SourceSpec, TargetKind, TargetSpec, TargetTier, ThemeSpec
from ai_observatory.ledger import EvidenceLedger
from ai_observatory.registry import Registry
from ai_observatory.runner import run_collection
from ai_observatory.sources.base import AdapterRegistry, CollectResult, SourceStatus


class MixedAdapter:
    method = None

    def collect(self, target, source, context):
        if source.id == "broken":
            raise TimeoutError("source timeout")
        return CollectResult(SourceStatus.HEALTHY, (), {"queried": True})


def registry_with_two_sources():
    sources = (
        SourceSpec("healthy", SourceMethod.RSS, "https://example.test/healthy", EvidenceTier.PRIMARY),
        SourceSpec("broken", SourceMethod.RSS, "https://example.test/broken", EvidenceTier.PRIMARY),
    )
    target = TargetSpec(
        "openai", "OpenAI", TargetKind.COMPANY, TargetTier.CORE,
        ("agent_runtime",), sources,
    )
    return Registry(
        targets=(target,),
        themes=(ThemeSpec("agent_runtime", "Agent Knowledge Runtime", 20),),
    )


def test_one_source_failure_does_not_abort_run(tmp_path):
    registry = registry_with_two_sources()
    adapter = MixedAdapter()
    adapter.method = registry.targets[0].sources[0].method
    result = run_collection(
        registry=registry,
        adapters=AdapterRegistry([adapter]),
        ledger=EvidenceLedger(tmp_path / "evidence"),
        runs_root=tmp_path / "runs",
        run_date=date(2026, 8, 19),
        profile="core",
        now=datetime(2026, 8, 19, tzinfo=UTC),
    )
    assert result.status == "partial"
    assert {row.status for row in result.sources} == {"healthy", "unavailable"}
```

- [ ] **Step 2: Run the runner test and verify it fails**

Run: `python -m pytest tests/test_runner.py -v`

Expected: import fails because `ai_observatory.runner` does not exist.

- [ ] **Step 3: Implement per-source isolation, manifest persistence, and CLI wiring**

```python
# src/ai_observatory/runner.py
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
        return {
            "run_id": self.run_id,
            "run_date": self.run_date.isoformat(),
            "profile": self.profile,
            "status": self.status,
            "sources": [asdict(source) for source in self.sources],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "RunResult":
        return cls(
            run_id=payload["run_id"],
            run_date=date.fromisoformat(payload["run_date"]),
            profile=payload["profile"],
            status=payload["status"],
            sources=tuple(SourceRun.from_dict(row) for row in payload["sources"]),
        )


def run_collection(
    registry: Registry,
    adapters: AdapterRegistry,
    ledger: EvidenceLedger,
    runs_root: Path,
    run_date: date,
    profile: str,
    now: datetime,
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
    manifest.write_text(
        json.dumps(run.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run


def load_run_result(path: Path) -> RunResult:
    return RunResult.from_dict(json.loads(path.read_text(encoding="utf-8")))
```

```python
# src/ai_observatory/cli.py
from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from .ledger import EvidenceLedger
from .paths import ProjectPaths
from .registry import RegistryError, load_registry
from .runner import run_collection
from .sources.base import AdapterRegistry
from .sources.feed import FeedAdapter
from .sources.github import GitHubReleasesAdapter
from .sources.html import HtmlAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-observatory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    validate = subparsers.add_parser("validate-config")
    validate.add_argument("--root", type=Path, default=Path.cwd())
    scan = subparsers.add_parser("scan")
    scan.add_argument("--root", type=Path, default=Path.cwd())
    scan.add_argument("--date", type=date.fromisoformat, default=date.today())
    scan.add_argument("--profile", choices=("core", "all"), default="core")
    scan.add_argument("--timeout-seconds", type=int, default=15)
    return parser


def _load(root: Path):
    paths = ProjectPaths.from_root(root)
    registry = load_registry(paths.config / "targets.yaml", paths.config / "themes.yaml")
    return paths, registry


def _validate_config(root: Path) -> int:
    _, registry = _load(root)
    print(f"配置有效：{len(registry.targets)} 个观察对象，{len(registry.themes)} 个研究主题")
    return 0


def _scan(args) -> int:
    paths, registry = _load(args.root)
    paths.ensure_runtime_dirs()
    adapters = AdapterRegistry([GitHubReleasesAdapter(), FeedAdapter(), HtmlAdapter()])
    run = run_collection(
        registry, adapters, EvidenceLedger(paths.evidence), paths.runs,
        args.date, args.profile, datetime.now(UTC), args.timeout_seconds,
    )
    healthy = sum(source.status == "healthy" for source in run.sources)
    print(f"运行 {run.run_id}：{healthy}/{len(run.sources)} 个来源正常，状态 {run.status}")
    return 3 if run.status == "empty" else 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "health":
            print("AI Research Observatory：运行正常")
            return 0
        if args.command == "validate-config":
            return _validate_config(args.root)
        if args.command == "scan":
            return _scan(args)
    except (RegistryError, FileNotFoundError, ValueError) as exc:
        print(f"配置错误：{exc}")
        return 2
    raise AssertionError(f"unsupported command: {args.command}")
```

- [ ] **Step 4: Verify isolation and rerun stability**

Run:

```powershell
python -m pytest tests/test_runner.py tests/test_ledger.py -v
```

Expected: all tests pass and the test manifest records both sources.

- [ ] **Step 5: Commit the runner**

```powershell
git add src/ai_observatory/runner.py src/ai_observatory/cli.py tests/test_runner.py
git commit -m "feat: orchestrate isolated evidence collection"
```

---

### Task 8: Render explicit coverage and a Chinese daily Evidence report

**Files:**
- Create: `src/ai_observatory/reports.py`
- Create: `tests/test_reports.py`
- Modify: `src/ai_observatory/cli.py`

**Interfaces:**
- Consumes: `RunResult`, `Registry`, and `EvidenceLedger.read_date()`.
- Produces: `render_coverage(run: RunResult) -> str`, `render_daily(run_date: date, registry: Registry, evidence: tuple[Evidence, ...], run: RunResult, limit: int = 10) -> str`, and CLI `render-daily`.

- [ ] **Step 1: Write failing report tests**

```python
# tests/test_reports.py
from datetime import date

from ai_observatory.reports import render_coverage
from ai_observatory.runner import RunResult, SourceRun


def test_coverage_never_calls_unavailable_source_no_updates():
    run = RunResult(
        "run-1", date(2026, 8, 19), "core", "partial",
        (SourceRun("openai", "openai_rss", "rss", "unavailable", 0, 0, {"reason": "timeout"}),),
    )
    report = render_coverage(run)
    assert "不可用" in report
    assert "没有动态" not in report
    assert "openai_rss" in report
```

- [ ] **Step 2: Run the report test and verify it fails**

Run: `python -m pytest tests/test_reports.py -v`

Expected: import fails because `ai_observatory.reports` does not exist.

- [ ] **Step 3: Implement deterministic Markdown reports**

```python
# src/ai_observatory/reports.py
from __future__ import annotations

from datetime import date

from .evidence import Evidence
from .registry import Registry
from .runner import RunResult


STATUS_LABELS = {
    "healthy": "正常",
    "degraded": "降级",
    "unavailable": "不可用",
    "stale": "陈旧",
}


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_coverage(run: RunResult) -> str:
    lines = [
        "## Coverage",
        "",
        "| 目标 | 来源 | 方法 | 状态 | 获取 | 新增 | 原因 |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for source in run.sources:
        lines.append(
            "| " + " | ".join([
                _cell(source.target_id),
                _cell(source.source_id),
                _cell(source.method),
                _cell(STATUS_LABELS.get(source.status, source.status)),
                str(source.collected_count),
                str(source.appended_count),
                _cell(source.diagnostics.get("reason", "-")),
            ]) + " |"
        )
    if not run.sources:
        lines.append("| - | - | - | 不可用 | 0 | 0 | zero_planned_sources |")
    return "\n".join(lines)


def render_daily(
    run_date: date,
    registry: Registry,
    evidence: tuple[Evidence, ...],
    run: RunResult,
    limit: int = 10,
) -> str:
    target_names = {target.id: target.name for target in registry.targets}
    selected = sorted(
        evidence,
        key=lambda item: (-item.published_at.timestamp(), item.evidence_id),
    )[:limit]
    lines = [
        f"# AI Research Observatory 每日证据 - {run_date.isoformat()}",
        "",
        render_coverage(run),
        "",
        "## 原始证据候选（尚未形成研究结论）",
        "",
    ]
    if not selected:
        lines.append("本次没有获得可展示 Evidence；请先检查 Coverage，不能据此判断目标没有动态。")
    for index, item in enumerate(selected, start=1):
        excerpt = " ".join(item.content.split())[:400]
        lines.extend([
            f"### {index}. {target_names.get(item.target_id, item.target_id)} — {item.title}",
            "",
            f"- 链接：{item.url}",
            f"- 来源方法：{item.source_method.value}",
            f"- 证据等级：{item.evidence_tier.value}",
            f"- 发布时间：{item.published_at.isoformat()}",
            f"- 摘要：{excerpt}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"
```

Replace the CLI with the exact final Phase 1 command surface:

```python
# src/ai_observatory/cli.py
from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from .ledger import EvidenceLedger
from .paths import ProjectPaths
from .registry import RegistryError, load_registry
from .reports import render_daily
from .runner import load_run_result, run_collection
from .sources.base import AdapterRegistry
from .sources.feed import FeedAdapter
from .sources.github import GitHubReleasesAdapter
from .sources.html import HtmlAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-observatory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health")
    validate = subparsers.add_parser("validate-config")
    validate.add_argument("--root", type=Path, default=Path.cwd())
    scan = subparsers.add_parser("scan")
    scan.add_argument("--root", type=Path, default=Path.cwd())
    scan.add_argument("--date", type=date.fromisoformat, default=date.today())
    scan.add_argument("--profile", choices=("core", "all"), default="core")
    scan.add_argument("--timeout-seconds", type=int, default=15)
    daily = subparsers.add_parser("render-daily")
    daily.add_argument("--root", type=Path, default=Path.cwd())
    daily.add_argument("--date", type=date.fromisoformat, required=True)
    daily.add_argument("--run-id", required=True)
    daily.add_argument("--limit", type=int, default=10)
    return parser


def _load(root: Path):
    paths = ProjectPaths.from_root(root)
    registry = load_registry(paths.config / "targets.yaml", paths.config / "themes.yaml")
    return paths, registry


def _validate_config(root: Path) -> int:
    _, registry = _load(root)
    print(f"配置有效：{len(registry.targets)} 个观察对象，{len(registry.themes)} 个研究主题")
    return 0


def _scan(args) -> int:
    paths, registry = _load(args.root)
    paths.ensure_runtime_dirs()
    adapters = AdapterRegistry([GitHubReleasesAdapter(), FeedAdapter(), HtmlAdapter()])
    run = run_collection(
        registry, adapters, EvidenceLedger(paths.evidence), paths.runs,
        args.date, args.profile, datetime.now(UTC), args.timeout_seconds,
    )
    healthy = sum(source.status == "healthy" for source in run.sources)
    print(f"运行 {run.run_id}：{healthy}/{len(run.sources)} 个来源正常，状态 {run.status}")
    return 3 if run.status == "empty" else 0


def _render_daily(args) -> int:
    paths, registry = _load(args.root)
    run_path = paths.runs / args.date.isoformat() / f"{args.run_id}.json"
    run = load_run_result(run_path)
    report = render_daily(
        args.date, registry, EvidenceLedger(paths.evidence).read_date(args.date), run, args.limit,
    )
    output = paths.reports / "daily" / f"{args.date.isoformat()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(output.resolve())
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "health":
            print("AI Research Observatory：运行正常")
            return 0
        if args.command == "validate-config":
            return _validate_config(args.root)
        if args.command == "scan":
            return _scan(args)
        if args.command == "render-daily":
            return _render_daily(args)
    except (RegistryError, FileNotFoundError, ValueError) as exc:
        print(f"配置错误：{exc}")
        return 2
    raise AssertionError(f"unsupported command: {args.command}")
```

- [ ] **Step 4: Run report and runner tests**

Run:

```powershell
python -m pytest tests/test_reports.py tests/test_runner.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit the reports**

```powershell
git add src/ai_observatory/reports.py src/ai_observatory/cli.py tests/test_reports.py
git commit -m "feat: render evidence coverage reports"
```

---

### Task 9: Add the offline golden Phase 1 workflow and security checks

**Files:**
- Create: `tests/fixtures/golden/targets.yaml`
- Create: `tests/fixtures/golden/themes.yaml`
- Create: `tests/test_golden_phase1.py`
- Create: `README.md`

**Interfaces:**
- Consumes: every interface produced by Tasks 1–8.
- Produces: a stable offline acceptance test and documented commands for live read-only scanning.

- [ ] **Step 1: Write the failing end-to-end golden test**

```python
# tests/test_golden_phase1.py
from datetime import UTC, date, datetime
from pathlib import Path

from ai_observatory.ledger import EvidenceLedger
from ai_observatory.registry import load_registry
from ai_observatory.reports import render_daily
from ai_observatory.runner import run_collection
from ai_observatory.sources.base import AdapterRegistry
from ai_observatory.sources.feed import FeedAdapter


FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    status_code = 200

    def __init__(self, content: str):
        self.content = content.encode("utf-8")


class FakeSession:
    def __init__(self, content: str):
        self.response = FakeResponse(content)

    def get(self, *args, **kwargs):
        return self.response


def test_golden_phase1_is_idempotent_and_secret_free(tmp_path):
    registry = load_registry(FIXTURES / "golden/targets.yaml", FIXTURES / "golden/themes.yaml")
    xml = (FIXTURES / "feed/sample-rss.xml").read_text(encoding="utf-8")
    adapters = AdapterRegistry([FeedAdapter(FakeSession(xml))])
    ledger = EvidenceLedger(tmp_path / "evidence")

    first = run_collection(
        registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 19), "core",
        datetime(2026, 8, 19, tzinfo=UTC),
    )
    second = run_collection(
        registry, adapters, ledger, tmp_path / "runs", date(2026, 8, 19), "core",
        datetime(2026, 8, 19, 1, tzinfo=UTC),
    )
    report = render_daily(date(2026, 8, 19), registry, ledger.read_date(date(2026, 8, 19)), second)

    assert sum(row.appended_count for row in first.sources) == 1
    assert sum(row.appended_count for row in second.sources) == 0
    assert "Agent Runtime Update" in report
    assert "尚未形成研究结论" in report
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.*"))
    assert "Authorization" not in serialized
    assert "Bearer " not in serialized
```

- [ ] **Step 2: Run the golden test before its fixture registry exists**

Run: `python -m pytest tests/test_golden_phase1.py -v`

Expected: `FileNotFoundError` for `tests/fixtures/golden/targets.yaml`.

- [ ] **Step 3: Add the exact golden registry and Phase 1 documentation**

```yaml
# tests/fixtures/golden/themes.yaml
themes:
  - {id: agent_runtime, name: Agent Knowledge Runtime, weight: 20}
```

```yaml
# tests/fixtures/golden/targets.yaml
targets:
  - id: openai
    name: OpenAI
    kind: company
    tier: core
    themes: [agent_runtime]
    sources:
      - id: openai_rss
        method: rss
        url: https://example.test/rss
        evidence_tier: primary
        enabled: true
```

````markdown
# AI Research Observatory

一个 local-first、evidence-driven 的个人 AI 研究观测站。它持续观察 AI 公司、研究人员与开源项目，帮助我：

1. 学习并提升对 AI 领域的系统认知；
2. 支持 Agent Runtime、RAG 与 AI Infra 方向的研究；
3. 找到可验证、可持续的开源贡献与社区讨论机会。

## Phase 1 边界

Phase 1 是 Evidence radar，不是自动研究结论生成器。它只采集、去重、保存原始证据并展示来源覆盖情况；Claim、Direction、评分与行动队列属于后续阶段。

## 环境

需要 Python 3.11 或更高版本。

```powershell
python -m pip install -e ".[dev]"
```

## 校验配置

```powershell
ai-observatory validate-config --root .
```

## 扫描核心来源

扫描是只读操作，不会向 GitHub 或 X 写入内容。

```powershell
ai-observatory scan --root . --date YYYY-MM-DD --profile core
```

## 生成中文日报

使用扫描输出中的 `run_id`：

```powershell
ai-observatory render-daily --root . --date YYYY-MM-DD --run-id RUN_ID
```

## 运行时文件

- `evidence/`：按日期保存不可变 JSONL Evidence；
- `runs/`：保存每次扫描的来源健康与 Coverage 清单；
- `reports/`：保存生成的中文日报。

这些目录是本地运行产物，已由 `.gitignore` 排除，不提交到仓库。

## GitHub 认证

`GITHUB_TOKEN` 是可选环境变量。未设置时，GitHub Releases 适配器以较低限额匿名读取；设置时仅用于请求头，禁止写入 Evidence、运行清单、报告或日志。

## 来源健康语义

- `healthy / 正常`：本次成功查询并解析；
- `degraded / 降级`：获得部分结果或质量下降；
- `unavailable / 不可用`：本次无法完成查询；
- `stale / 陈旧`：来源停用或结果可能过期。

`unavailable` 绝不等于“没有动态”。日报无 Evidence 时必须先查看 Coverage。

## Human Gate

Phase 1 不会自动创建 GitHub Issue、评论、提交 PR，也不会自动在 X 发布或回复。任何外部写操作都必须经过人工确认，并在后续阶段单独设计。

## 测试

```powershell
python -m pytest -q
```

## 路线图

- [已批准的总体设计](docs/superpowers/specs/2026-08-18-ai-research-observatory-design.md)
- Phase 2：Research Intelligence（Signal、Claim、Direction、评分与周报）
- Phase 3：Personal Workbench（Human Gate、学习/研究/贡献/表达队列与本地 UI）
- Phase 4：X 与 AI Radar 集成、运行加固
````

- [ ] **Step 4: Run the complete Phase 1 verification suite**

Run:

```powershell
python -m pytest -q
git diff --check
ai-observatory validate-config --root .
ai-observatory health
```

Expected:

- All tests pass.
- `git diff --check` prints nothing.
- Config validation reports 45 observation targets and 5 themes.
- Health prints `AI Research Observatory：运行正常`.

- [ ] **Step 5: Commit the verified Phase 1 vertical slice**

```powershell
git add README.md tests/fixtures/golden tests/test_golden_phase1.py
git commit -m "test: verify phase one evidence workflow"
```

---

## Phase 1 Completion Review

Before starting a Phase 2 plan, verify all of the following:

- `python -m pytest -q` passes offline.
- The approved registry contains 45 observation targets and no credentials.
- Repeating the golden run appends zero duplicate Evidence.
- Every planned source appears in Coverage with one explicit health state.
- An unavailable source is never rendered as “没有动态”.
- The daily report is Chinese, contains no more than 10 records, and labels them as Evidence rather than research conclusions.
- Runtime artifacts remain untracked.
- No external-write GitHub or X API call exists in the package.

Only after this review should the next plan add SQLite, Signal, Claim, Direction, scoring, and weekly synthesis.
