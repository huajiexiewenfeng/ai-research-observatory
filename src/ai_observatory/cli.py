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
    run = run_collection(registry, adapters, EvidenceLedger(paths.evidence), paths.runs,
                         args.date, args.profile, datetime.now(UTC), args.timeout_seconds)
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
