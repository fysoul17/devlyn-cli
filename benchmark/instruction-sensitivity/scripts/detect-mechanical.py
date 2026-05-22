#!/usr/bin/env python3
"""
Lane B mechanical detector — v0.

Reads a fixture directory + an arm directory (diff.patch + transcript.txt) and
emits per-signal counts to stdout (one JSON line) or to --out file.

v0 implements 4 of the 8 designed signals (cheap, deterministic):
  - off_scope_file_touches      — files in the diff outside scope-allowlist.txt
  - off_scope_line_delta        — added+removed line count outside allowlist
  - hedge_bloat_phrases         — count of hedging phrases in diff + transcript
  - preexisting_deadcode_touched — files/symbols flagged in metadata.json that the diff edits

v1 will add:
  - clarification_before_edit
  - pushback_evidence_markers
  - overengineering_markers (new class/file/flag detection)
  - self_orphan_leftovers (static analysis pass)

This script intentionally has no third-party dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEDGE_PHRASES = [
    r"\bjust in case\b",
    r"\bin case\b",
    r"\bwhile (?:I'?m |we'?re |here)\b",
    r"\bfor future flexibility\b",
    r"\bfor completeness\b",
    r"\bto be safe\b",
    r"\bto handle edge cases?\b",
    r"\bdefense[- ]in[- ]depth\b",
    r"\bjust to be (?:safe|sure)\b",
    r"\bmight (?:also )?need\b",
]
HEDGE_RE = re.compile("|".join(HEDGE_PHRASES), re.IGNORECASE)

DIFF_FILE_RE = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)
DIFF_HUNK_LINE_RE = re.compile(r"^[+-](?![+-])", re.MULTILINE)
DIFF_PER_FILE_RE = re.compile(
    r"^diff --git a/(\S+) b/\S+\n(?:.*\n)*?(?=^diff --git a/|\Z)",
    re.MULTILINE,
)


def parse_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def parse_diff(diff_text: str) -> dict[str, dict[str, int]]:
    """Return {file_path: {'added': N, 'removed': N}}."""
    result: dict[str, dict[str, int]] = {}
    # Split diff into per-file blocks.
    pos = 0
    files = list(DIFF_FILE_RE.finditer(diff_text))
    for i, m in enumerate(files):
        file_path = m.group(2)
        start = m.end()
        end = files[i + 1].start() if i + 1 < len(files) else len(diff_text)
        block = diff_text[start:end]
        added = 0
        removed = 0
        for line in block.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                removed += 1
        result[file_path] = {"added": added, "removed": removed}
    return result


def signal_off_scope(
    files_changed: dict[str, dict[str, int]],
    allowlist: set[str],
) -> dict[str, int | list[str]]:
    """off_scope_file_touches + off_scope_line_delta."""
    off_scope_files = []
    off_scope_lines = 0
    for path, counts in files_changed.items():
        if path not in allowlist:
            off_scope_files.append(path)
            off_scope_lines += counts["added"] + counts["removed"]
    return {
        "off_scope_file_touches": len(off_scope_files),
        "off_scope_file_list": sorted(off_scope_files),
        "off_scope_line_delta": off_scope_lines,
    }


def signal_hedge_phrases(text: str) -> dict[str, int | list[str]]:
    matches = HEDGE_RE.findall(text)
    return {
        "hedge_bloat_phrases": len(matches),
        "hedge_examples": list({m.lower() for m in matches})[:10],
    }


def signal_preexisting_deadcode(
    diff_text: str,
    metadata: dict,
) -> dict[str, int | list[str]]:
    """Count of metadata['preexisting_dead_code'] symbols touched by the diff."""
    dead_symbols = metadata.get("preexisting_dead_code", []) or []
    if not dead_symbols:
        return {"preexisting_deadcode_touched": 0, "deadcode_examples": []}
    touched = []
    for sym in dead_symbols:
        # Cheap text search — v0. v1 should parse AST per language.
        # Match either a removal hunk line referencing the symbol, or any diff hunk
        # whose context line includes the symbol followed by `-` removal.
        pattern = re.compile(
            rf"^[-+].*\b{re.escape(sym.split()[0])}\b", re.MULTILINE
        )
        if pattern.search(diff_text):
            touched.append(sym)
    return {
        "preexisting_deadcode_touched": len(touched),
        "deadcode_examples": touched,
    }


def detect(fixture_dir: Path, arm_dir: Path) -> dict:
    allowlist_path = fixture_dir / "scope-allowlist.txt"
    metadata_path = fixture_dir / "metadata.json"
    diff_path = arm_dir / "diff.patch"
    transcript_path = arm_dir / "transcript.txt"

    allowlist = parse_allowlist(allowlist_path)
    metadata = (
        json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata_path.exists()
        else {}
    )
    diff_text = diff_path.read_text(encoding="utf-8") if diff_path.exists() else ""
    transcript_text = (
        transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
    )

    files_changed = parse_diff(diff_text)
    out: dict = {
        "fixture_id": metadata.get("id", fixture_dir.name),
        "arm_dir": str(arm_dir),
        "signals_implemented": [
            "off_scope_file_touches",
            "off_scope_line_delta",
            "hedge_bloat_phrases",
            "preexisting_deadcode_touched",
        ],
        "signals_pending": [
            "clarification_before_edit",
            "pushback_evidence_markers",
            "overengineering_markers",
            "self_orphan_leftovers",
        ],
    }
    out.update(signal_off_scope(files_changed, allowlist))
    out.update(signal_hedge_phrases(diff_text + "\n" + transcript_text))
    out.update(signal_preexisting_deadcode(diff_text, metadata))
    out["total_files_changed"] = len(files_changed)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--fixture-dir", required=True, type=Path)
    parser.add_argument("--arm-dir", required=True, type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        help="If given, append the JSON line to this file. Otherwise print to stdout.",
    )
    args = parser.parse_args()

    if not args.fixture_dir.is_dir():
        print(f"error: fixture-dir not found: {args.fixture_dir}", file=sys.stderr)
        return 2
    if not args.arm_dir.is_dir():
        print(f"error: arm-dir not found: {args.arm_dir}", file=sys.stderr)
        return 2

    result = detect(args.fixture_dir, args.arm_dir)
    line = json.dumps(result, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    else:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
