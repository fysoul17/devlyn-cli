#!/usr/bin/env python3
"""Validate a shadow fixture solo ceiling avoidance note."""
from __future__ import annotations

import argparse
import pathlib
import re
import sys


SECTION_RE = re.compile(r"(?ms)^##[ \t]+Solo ceiling avoidance\b[^\n]*\n(.*?)(?=^##[ \t]+|\Z)")
CONTROL_RE = re.compile(r"\bS[2-6]\b|S2-S6|solo-saturated|rejected controls?", re.IGNORECASE)
REASON_RE = re.compile(r"\bdiffer(?:s|ent|ence)?\b|\bunlike\b|\bbecause\b|\bpreserve\b|\bheadroom\b", re.IGNORECASE)


def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        print(f"{path}: expected UTF-8 text ({exc})", file=sys.stderr)
        raise SystemExit(2) from None
    except OSError as exc:
        print(f"{path}: unable to read ({exc})", file=sys.stderr)
        raise SystemExit(2) from None


def solo_ceiling_avoidance_error(text: str) -> str | None:
    match = SECTION_RE.search(text)
    if not match:
        return "missing ## Solo ceiling avoidance section"
    section = match.group(1)
    if "solo_claude" not in section:
        return "solo ceiling avoidance must mention solo_claude"
    if not CONTROL_RE.search(section):
        return "solo ceiling avoidance must compare against rejected or solo-saturated controls such as S2-S6"
    if not REASON_RE.search(section):
        return "solo ceiling avoidance must state difference/headroom reasoning"
    return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=pathlib.Path)
    args = parser.parse_args(argv)
    err = solo_ceiling_avoidance_error(read_text(args.path))
    if err:
        print(f"{args.path}: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
