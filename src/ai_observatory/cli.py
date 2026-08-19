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
