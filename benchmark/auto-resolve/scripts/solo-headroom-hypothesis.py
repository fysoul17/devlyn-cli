#!/usr/bin/env python3
"""Validate that a pair-candidate fixture states an actionable solo-headroom hypothesis."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys


from pair_evidence_contract import (
    actionable_observable_commands,
    has_actionable_solo_headroom_hypothesis_text,
)


def combined_text(paths: list[pathlib.Path]) -> str:
    chunks: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError as exc:
            print(f"{path}: expected UTF-8 text ({exc})", file=sys.stderr)
            raise SystemExit(2) from None
    return "\n".join(chunks)


def has_actionable_hypothesis(text: str) -> bool:
    return has_actionable_solo_headroom_hypothesis_text(text)


def expected_commands(path: pathlib.Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        print(f"{path}: expected UTF-8 JSON ({exc})", file=sys.stderr)
        raise SystemExit(2) from None
    except json.JSONDecodeError as exc:
        print(f"{path}: invalid JSON ({exc})", file=sys.stderr)
        raise SystemExit(2) from None

    commands = data.get("verification_commands")
    if not isinstance(commands, list):
        print(f"{path}: verification_commands must be a list", file=sys.stderr)
        raise SystemExit(2)

    result: set[str] = set()
    for index, command in enumerate(commands):
        if not isinstance(command, dict) or not isinstance(command.get("cmd"), str):
            print(f"{path}: verification_commands[{index}].cmd must be a string", file=sys.stderr)
            raise SystemExit(2)
        result.add(command["cmd"])
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--expected-json",
        type=pathlib.Path,
        help="Require the observable hypothesis command to match expected.json verification_commands[].cmd.",
    )
    parser.add_argument("paths", nargs="+", type=pathlib.Path)
    args = parser.parse_args(argv)
    text = combined_text(args.paths)
    if not has_actionable_hypothesis(text):
        return 1
    if args.expected_json is None:
        return 0
    expected = expected_commands(args.expected_json)
    return 0 if any(command in expected for command in actionable_observable_commands(text)) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
