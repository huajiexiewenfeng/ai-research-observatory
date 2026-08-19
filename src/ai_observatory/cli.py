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
