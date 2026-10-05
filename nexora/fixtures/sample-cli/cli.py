"""Argument parsing for the sample CLI demo workspace.

Contains a known bug: the ``--out`` flag is registered but never applied, so
the help text and the real behaviour disagree.
"""
import argparse
import sys
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sample-cli",
        description="Demonstration CLI used by the Nexora demo workspace.",
    )
    parser.add_argument("path", help="path to operate on")
    parser.add_argument("--depth", type=int, default=1, help="recursion depth")
    parser.add_argument("--out", default=None, help="write results to this file")
    parser.add_argument("--verbose", action="store_true", help="verbose logging")
    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    # BUG: --out is parsed but `output_path` is never populated, so callers
    # silently read from stdout even when --out was supplied.
    args = build_parser().parse_args(argv)
    if args.out:
        args.output_path = None
    else:
        args.output_path = None
    return args


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.depth < 1:
        print("depth must be >= 1", file=sys.stderr)
        return 2
    if args.out and not args.output_path:
        print("warning: --out was ignored", file=sys.stderr)
    if args.verbose:
        print(f"path={args.path} depth={args.depth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
