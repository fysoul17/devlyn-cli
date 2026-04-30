#!/usr/bin/env python3
"""F9 variant/solo arm artifact + transcript fingerprint check.

Out-of-band per Codex R0.5 §B (iter-0033a): expected.json.verification_commands
apply to ALL arms (run-fixture.sh:472), so a `docs/specs/**` check there would
punish bare. This script runs AFTER run-fixture.sh and asserts variant/solo
arms produced the artifacts the 2-skill ideate→resolve chain should emit.

Bare arm is exempt by construction.

Usage:
  check-f9-artifacts.py --result-dir <results/<run_id>/F9-e2e-ideate-to-resolve/<arm>>

Exits:
  0 — all checks pass (or bare arm — exempt).
  1 — variant/solo arm but artifact contract violated.
  2 — invalid invocation (missing args, missing dir).

Emits a small JSON report at <result-dir>/check-f9-artifacts.json.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path


VARIANT_ARMS = {"variant", "solo_claude", "l2_gated", "l2_forced"}
EXEMPT_ARMS = {"bare"}

SPEC_DIR_GLOB = "docs/specs/*/spec.md"
SPEC_EXPECTED_GLOB = "docs/specs/*/spec.expected.json"

# Transcript fingerprint regexes.
RE_RESOLVE_INVOCATION = re.compile(r"/devlyn:resolve\s+--spec\s+\S+", re.MULTILINE)
RE_AUTO_RESOLVE = re.compile(r"/devlyn:auto-resolve\b")
RE_PREFLIGHT = re.compile(r"/devlyn:preflight\b")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--result-dir", required=True,
                   help="Path to results/<run_id>/<fixture>/<arm>/")
    args = p.parse_args()

    result_dir = Path(args.result_dir)
    if not result_dir.is_dir():
        print(f"error: result dir not found: {result_dir}", file=sys.stderr)
        return 2

    arm = result_dir.name
    fixture = result_dir.parent.name

    if fixture != "F9-e2e-ideate-to-resolve":
        print(f"error: this script is F9-only (got fixture={fixture})", file=sys.stderr)
        return 2

    report = {
        "fixture": fixture,
        "arm": arm,
        "checks": [],
        "exempt": False,
        "pass": True,
    }

    if arm in EXEMPT_ARMS:
        report["exempt"] = True
        report["checks"].append({"name": "arm-is-bare-exempt", "pass": True})
        _write_report(result_dir, report)
        return 0

    if arm not in VARIANT_ARMS:
        print(f"error: unknown arm '{arm}' (expected one of {VARIANT_ARMS | EXEMPT_ARMS})",
              file=sys.stderr)
        return 2

    # The fixture's work-dir is referenced from result_dir/timing.json. The
    # arm produced files inside that work-dir; we glob from there.
    timing_path = result_dir / "timing.json"
    work_dir: Path
    if timing_path.is_file():
        try:
            timing = json.loads(timing_path.read_text())
            work_dir = Path(timing.get("work_dir", ""))
        except Exception:
            work_dir = Path("")
    else:
        work_dir = Path("")

    if not work_dir.is_dir():
        report["checks"].append({
            "name": "work-dir-resolvable",
            "pass": False,
            "reason": f"work_dir from timing.json not usable: {work_dir!r}",
        })
        report["pass"] = False
        _write_report(result_dir, report)
        return 1

    # Check 1: docs/specs/<id>-<slug>/spec.md exists.
    specs_root = work_dir / "docs" / "specs"
    spec_md_files = list(specs_root.glob("*/spec.md")) if specs_root.is_dir() else []
    spec_md_present = bool(spec_md_files)
    report["checks"].append({
        "name": "spec.md-exists-under-docs/specs",
        "pass": spec_md_present,
        "matched": [str(p.relative_to(work_dir)) for p in spec_md_files],
    })
    if not spec_md_present:
        report["pass"] = False

    # Check 2: spec.expected.json exists at the same dir.
    spec_exp_files = list(specs_root.glob("*/spec.expected.json")) if specs_root.is_dir() else []
    spec_exp_present = bool(spec_exp_files)
    report["checks"].append({
        "name": "spec.expected.json-exists-under-docs/specs",
        "pass": spec_exp_present,
        "matched": [str(p.relative_to(work_dir)) for p in spec_exp_files],
    })
    if not spec_exp_present:
        report["pass"] = False

    # Path-shape regression: the parent dir name should be `<id>-<slug>` shape.
    # Both id and slug are kebab-case, so the dir must contain at least one
    # hyphen. Bare `<id>/spec.md` (no hyphen) is the legacy shape we reject.
    if spec_md_files:
        bad_shapes = [p for p in spec_md_files if "-" not in p.parent.name]
        report["checks"].append({
            "name": "path-shape-id-slug",
            "pass": not bad_shapes,
            "non_conforming": [str(p.relative_to(work_dir)) for p in bad_shapes],
        })
        if bad_shapes:
            report["pass"] = False

    # Transcript fingerprint checks.
    transcript_path = result_dir / "transcript.txt"
    if not transcript_path.is_file():
        report["checks"].append({
            "name": "transcript-readable",
            "pass": False,
            "reason": f"transcript.txt missing at {transcript_path}",
        })
        report["pass"] = False
        _write_report(result_dir, report)
        return 1

    transcript = transcript_path.read_text(errors="replace")

    resolve_hits = RE_RESOLVE_INVOCATION.findall(transcript)
    report["checks"].append({
        "name": "transcript-contains-resolve-spec-invocation",
        "pass": len(resolve_hits) >= 1,
        "count": len(resolve_hits),
    })
    if len(resolve_hits) < 1:
        report["pass"] = False

    auto_resolve_hits = RE_AUTO_RESOLVE.findall(transcript)
    report["checks"].append({
        "name": "transcript-no-auto-resolve",
        "pass": len(auto_resolve_hits) == 0,
        "count": len(auto_resolve_hits),
    })
    if auto_resolve_hits:
        report["pass"] = False

    preflight_hits = RE_PREFLIGHT.findall(transcript)
    report["checks"].append({
        "name": "transcript-no-preflight",
        "pass": len(preflight_hits) == 0,
        "count": len(preflight_hits),
    })
    if preflight_hits:
        report["pass"] = False

    _write_report(result_dir, report)
    return 0 if report["pass"] else 1


def _write_report(result_dir: Path, report: dict) -> None:
    out_path = result_dir / "check-f9-artifacts.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    sys.exit(main())
