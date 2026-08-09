#!/usr/bin/env python3
"""Command-line interface for the release artifact vault."""

from __future__ import annotations

import argparse
import json

from vault import list_artifacts, load_mapping


def emit(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True))


def list_command(catalog_path: str) -> int:
    catalog = load_mapping(catalog_path)
    emit({"artifacts": list_artifacts(catalog)})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("catalog_path")
    args = parser.parse_args(argv)

    if args.command == "list":
        return list_command(args.catalog_path)
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
