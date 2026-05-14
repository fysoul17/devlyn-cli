#!/usr/bin/env python3
"""F9 skill-driven arm artifact + transcript fingerprint check.

Out-of-band per Codex R0.5 §B (iter-0033a): expected.json.verification_commands
apply to ALL arms (run-fixture.sh:472), so a `docs/specs/**` check there would
punish bare. This script runs AFTER run-fixture.sh and asserts skill-driven
arms produced the artifacts the 2-skill ideate→resolve chain should emit.

Bare arm is exempt by construction.

Usage:
  check-f9-artifacts.py --result-dir <results/<run_id>/F9-e2e-ideate-to-resolve/<arm>>

Exits:
  0 — all checks pass (or bare arm — exempt).
  1 — skill-driven arm but artifact contract violated.
  2 — invalid invocation (missing args, missing dir).

Emits a small JSON report at <result-dir>/check-f9-artifacts.json.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

from pair_evidence_contract import loads_strict_json_object


SKILL_DRIVEN_ARMS = {"variant", "solo_claude", "l2_gated", "l2_risk_probes", "l2_forced"}
EXEMPT_ARMS = {"bare"}

SPEC_DIR_GLOB = "docs/specs/*/spec.md"
SPEC_EXPECTED_GLOB = "docs/specs/*/spec.expected.json"

# Transcript fingerprint regexes (negative checks only — `claude -p`
# transcript captures only the agent's final reply, not intermediate
# tool calls; positive resolve invocation evidence lives in state).
RE_AUTO_RESOLVE = re.compile(r"/devlyn:auto-resolve\b")
RE_PREFLIGHT = re.compile(r"/devlyn:preflight\b")


def _load_json_object(path: Path) -> tuple[dict | None, str | None]:
    try:
        data = loads_strict_json_object(path.read_text())
    except json.JSONDecodeError as exc:
        return None, f"{exc.__class__.__name__}: {exc}"
    except ValueError as exc:
        if str(exc) == "top-level JSON value must be an object":
            return None, "expected JSON object"
        return None, f"{exc.__class__.__name__}: {exc}"
    return data, None


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

    if arm not in SKILL_DRIVEN_ARMS:
        print(f"error: unknown arm '{arm}' (expected one of {SKILL_DRIVEN_ARMS | EXEMPT_ARMS})",
              file=sys.stderr)
        return 2

    # The fixture's work-dir is referenced from result_dir/timing.json. The
    # arm produced files inside that work-dir; we glob from there.
    timing_path = result_dir / "timing.json"
    work_dir: Path
    if timing_path.is_file():
        timing, _timing_error = _load_json_object(timing_path)
        if timing is not None:
            work_dir = Path(timing.get("work_dir", ""))
        else:
            work_dir = Path("__invalid_timing_work_dir__")
    else:
        work_dir = Path("__missing_timing_work_dir__")

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

    # Resolve invocation evidence — primary source is pipeline.state.json,
    # NOT transcript.txt. `claude -p` only emits the agent's final reply to
    # stdout; intermediate Skill / Agent / Bash tool calls do not appear in
    # transcript.txt. Therefore "regex /devlyn:resolve --spec in transcript"
    # is the wrong source. The authoritative evidence resolve actually ran
    # in --spec mode is `state.mode == "spec"` plus `state.source.type ==
    # "spec"` plus a populated `state.source.spec_path` pointing under
    # `docs/specs/`. Per state-schema.md this is single-source-of-truth.
    # Look for the archive first (preferred), then fall back to the live
    # in-flight location. NEW resolve currently lands artifacts directly in
    # `.devlyn/` and may skip the move-to-runs/ archive step (TODO: separate
    # iter to fix archive); both locations carry the same authoritative
    # state shape.
    archived_paths = list(work_dir.glob(".devlyn/runs/*/pipeline.state.json"))
    live_path = work_dir / ".devlyn" / "pipeline.state.json"
    state_paths = archived_paths if archived_paths else (
        [live_path] if live_path.is_file() else []
    )
    if not state_paths:
        report["checks"].append({
            "name": "pipeline.state.json-present",
            "pass": False,
            "reason": "neither .devlyn/runs/*/pipeline.state.json nor .devlyn/pipeline.state.json found in work_dir",
        })
        report["pass"] = False
    else:
        # Read the most recent run.
        state_path = sorted(state_paths)[-1]
        state, state_error = _load_json_object(state_path)
        if state is None:
            report["checks"].append({
                "name": "pipeline.state.json-parses",
                "pass": False,
                "reason": state_error,
            })
            report["pass"] = False

        if state is not None:
            archived = "/runs/" in str(state_path)
            report["checks"].append({
                "name": "pipeline.state.json-present",
                "pass": True,
                "path": str(state_path.relative_to(work_dir)),
                "archived_to_runs_dir": archived,
            })
            if not archived:
                # Not a fail — note for harness developer that NEW resolve
                # is skipping the archive step in this run.
                report["checks"].append({
                    "name": "archive-step-completed",
                    "pass": True,
                    "warning": "NEW resolve left artifacts in .devlyn/ instead of .devlyn/runs/<id>/ — archive step skipped (separate iter for harness fix)",
                })
            mode = state.get("mode")
            src_type = (state.get("source") or {}).get("type")
            spec_path = (state.get("source") or {}).get("spec_path") or ""
            spec_under_specs = spec_path.startswith("docs/specs/") and spec_path.endswith("spec.md")
            mode_ok = mode == "spec"
            src_ok = src_type == "spec"
            report["checks"].append({
                "name": "state.mode-and-source-spec",
                "pass": mode_ok and src_ok and spec_under_specs,
                "mode": mode,
                "source.type": src_type,
                "source.spec_path": spec_path,
            })
            if not (mode_ok and src_ok and spec_under_specs):
                report["pass"] = False

    # Transcript fingerprint — negative checks only. transcript.txt records
    # the agent's final reply; if the agent (or any subagent) had invoked
    # /devlyn:auto-resolve or /devlyn:preflight, the prompt-following gate
    # should still surface the name in the summary. Positive resolve
    # evidence lives in state above; here we just rule out the deprecated
    # 3-skill chain names.
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
