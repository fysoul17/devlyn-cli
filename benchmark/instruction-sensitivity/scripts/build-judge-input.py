#!/usr/bin/env python3
"""
Build the instruction-blind judge input JSON for one fixture.

Inputs:
  --run-dir   path to results/<run-id>
  --fixture   fixture id (B1-...)

Reads:
  results/<run-id>/manifest.json               # slot_map per fixture
  fixtures/<fixture>/task.txt
  fixtures/<fixture>/spec.md
  fixtures/<fixture>/scope-allowlist.txt
  fixtures/<fixture>/behavior-contract.json
  results/<run-id>/arms/<arm-for-A>/<fixture>/{diff.patch,transcript.txt}
  results/<run-id>/arms/<arm-for-B>/<fixture>/{diff.patch,transcript.txt}

Writes to stdout the JSON object the judge prompt consumes. No arm identity in
output (only "A" / "B"). Diff and transcript are size-capped per RUBRIC.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MAX_DIFF_CHARS = 8192
MAX_TRANSCRIPT_CHARS = 4096


def read_text_capped(path: Path, limit: int) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= limit:
        return text
    keep = limit // 2 - 32
    return text[:keep] + "\n... [truncated] ...\n" + text[-keep:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--fixture", required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    fixture_dir = repo_root / "benchmark" / "instruction-sensitivity" / "fixtures" / args.fixture

    manifest = json.loads((args.run_dir / "manifest.json").read_text(encoding="utf-8"))
    slot = manifest["slot_map"][args.fixture]
    arm_for_A = slot["A"]
    arm_for_B = slot["B"]

    arm_A_dir = args.run_dir / "arms" / arm_for_A / args.fixture
    arm_B_dir = args.run_dir / "arms" / arm_for_B / args.fixture

    task = (fixture_dir / "task.txt").read_text(encoding="utf-8").strip()
    spec_text = (fixture_dir / "spec.md").read_text(encoding="utf-8")
    allowlist = [
        line.strip()
        for line in (fixture_dir / "scope-allowlist.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    contract = json.loads((fixture_dir / "behavior-contract.json").read_text(encoding="utf-8"))
    fixture_axes = list(contract.get("axes_scored", {}).keys())

    # Strip hidden sections from spec.md so the judge cannot read the trap rationale or
    # the mechanical verifier's assertions. Public sections seen by the judge: Task,
    # Expected good behavior, Expected bad behavior, Scoring axes.
    hidden_section_prefixes = (
        "## Why",                         # "Why this is ... (hidden from the agent)"
        "## Verification",                # "Verification (mechanical, hidden from agent and judge)"
    )
    spec_public_parts: list[str] = []
    skip = False
    for line in spec_text.splitlines():
        if any(line.lstrip().startswith(p) for p in hidden_section_prefixes):
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if not skip:
            spec_public_parts.append(line)
    spec_public = "\n".join(spec_public_parts).strip()

    payload = {
        "fixture_id": args.fixture,
        "task": task,
        "spec": spec_public,
        "scope_allowlist": allowlist,
        "fixture_axes": fixture_axes,
        "arm_A": {
            "diff": read_text_capped(arm_A_dir / "diff.patch", MAX_DIFF_CHARS),
            "transcript_excerpt": read_text_capped(arm_A_dir / "transcript.txt", MAX_TRANSCRIPT_CHARS),
        },
        "arm_B": {
            "diff": read_text_capped(arm_B_dir / "diff.patch", MAX_DIFF_CHARS),
            "transcript_excerpt": read_text_capped(arm_B_dir / "transcript.txt", MAX_TRANSCRIPT_CHARS),
        },
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
