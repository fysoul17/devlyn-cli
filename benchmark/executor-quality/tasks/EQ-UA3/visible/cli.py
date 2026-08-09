#!/usr/bin/env python3
"""Command-line interface for publication drafts."""

from __future__ import annotations

import argparse
import json

from publication import DraftError, load_json, validate_draft


def emit(payload: object) -> None:
    print(json.dumps(payload, sort_keys=True))


def check_draft_command(draft_path: str) -> int:
    try:
        draft = validate_draft(load_json(draft_path))
    except DraftError:
        emit({"valid": False})
        return 1
    emit({"slug": draft["slug"], "valid": True})
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    check_parser = subparsers.add_parser("check-draft")
    check_parser.add_argument("draft_path")
    args = parser.parse_args(argv)

    if args.command == "check-draft":
        return check_draft_command(args.draft_path)
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
