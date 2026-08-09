#!/usr/bin/env python3
"""Command-line interface for the account ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ledger import LedgerError, apply_operation


def read_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_accounts(path: str, accounts: dict[str, int]) -> None:
    Path(path).write_text(json.dumps(accounts, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def apply_one(accounts_path: str, operation_path: str) -> int:
    accounts = read_json(accounts_path)
    operation = read_json(operation_path)
    if not isinstance(accounts, dict):
        raise ValueError("accounts file must contain an object")
    try:
        apply_operation(accounts, operation)
    except LedgerError as exc:
        print(json.dumps({"applied": None, "rejected": {"reason": str(exc)}}))
        return 1
    write_accounts(accounts_path, accounts)
    print(json.dumps({"applied": 1, "rejected": None}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("accounts_path")
    apply_parser.add_argument("operation_path")
    args = parser.parse_args(argv)

    if args.command == "apply":
        return apply_one(args.accounts_path, args.operation_path)
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
