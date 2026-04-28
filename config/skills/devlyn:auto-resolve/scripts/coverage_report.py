#!/usr/bin/env python3
"""Emit `.devlyn/coverage.json` proving every iter-0020 changed route
that APPLIES to this fixture was actually exercised.

Per-fixture semantics (iter-0020 + Codex R1 refinement): a per-fixture
coverage.json reports route evaluation in three buckets — applicable
fired, applicable missed (= failure), not applicable. Only
`applicable_missed` is a router bug. Suite-level aggregation across all
fixtures' coverage.json files proves "every changed route was exercised
by at least one fixture."

Schema:
{
  "version": 1,
  "run_id": "<state.run_id>",
  "fixture_class": "<state.source.fixture_class>",
  "all_applicable_routes_exercised": bool,
  "applicable_fired": [<route entry>...],
  "applicable_missed": [<route entry>...],
  "not_applicable":   [<route entry>...]
}

Each <route entry>:
{
  "route_id": "auto-resolve.BUILD.fixture_class:e2e",
  "fixture_class": {"category": "e2e"},
  "previous_route": {"build_engine": "codex"},
  "selected_route": {"build_engine": "claude"},
  "decision_evidence": {
    "fixture": "<fixture id if BENCH else null>",
    "input_path": ".devlyn/pipeline.state.json",
    "state_path": ".devlyn/pipeline.state.json",
    "observed_phase_engine": "<state.phases.build.engine>"
  },
  "short_circuit": {
    "rule_id": "route.fixture_class_e2e.build_claude",
    "result": "fired_observed" | "selected_but_observed_engine_diverged"
            | "applicable_but_override_did_not_fire"
            | "not_applicable_class_no_match"
  },
  "wall_budget_abort": {"budget_s": int|null, "triggered": bool}
}

Why: hard acceptance #4 requires "coverage.json proving every changed
route was exercised." This is the proof artifact iter-0020 ships.

Usage:
    python3 coverage_report.py [--devlyn-dir .devlyn]

Exit 0: coverage.json written.
Exit 2: invocation error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# iter-0020 changed routes registry. When iter-NNNN adds a routing change,
# append an entry here. coverage_report.py walks this list and reports
# whether the run exercised each.
CHANGED_ROUTES = [
    {
        "route_id": "auto-resolve.BUILD.fixture_class:e2e",
        "rule_id": "route.fixture_class_e2e.build_claude",
        "phase": "build",
        "fixture_class_match": {"category": "e2e"},
        "previous_engine": "codex",
        "selected_engine": "claude",
        "iter": "iter-0020",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    args = ap.parse_args()

    work = Path(os.environ.get("BENCH_WORKDIR") or os.getcwd())
    devlyn = work / args.devlyn_dir if not Path(args.devlyn_dir).is_absolute() \
        else Path(args.devlyn_dir)
    state_path = devlyn / "pipeline.state.json"
    if not state_path.is_file():
        print(f"[coverage] {state_path} not found", file=sys.stderr)
        return 2
    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[coverage] cannot parse {state_path}: {e}", file=sys.stderr)
        return 2

    run_id = state.get("run_id") or "unknown"
    fixture_class = (state.get("source") or {}).get("fixture_class")
    fixture_id = (state.get("source") or {}).get("fixture_id") \
        or os.environ.get("BENCH_FIXTURE") \
        or None
    overrides = ((state.get("route") or {}).get("engine_overrides") or {})

    # Per-fixture semantics (iter-0020): partition each changed route into
    # applicable_fired / applicable_missed / not_applicable. Only
    # `applicable_missed` is a failure — it means the fixture's class
    # matched but the override didn't fire (router bug). `not_applicable`
    # is fine — the route is for a different class. Suite-level aggregation
    # of multiple per-fixture coverage.json files proves "every changed
    # route was exercised by at least one fixture."
    applicable_fired: list[dict] = []
    applicable_missed: list[dict] = []
    not_applicable: list[dict] = []
    for r in CHANGED_ROUTES:
        phase = r["phase"]
        match = r["fixture_class_match"]
        class_match = match.get("category") == fixture_class
        phase_state = (state.get("phases") or {}).get(phase) or {}
        observed_engine = phase_state.get("engine")
        override_entry = overrides.get(phase)
        triggered = bool(override_entry and override_entry.get("to") == r["selected_engine"])

        if not class_match:
            result = "not_applicable_class_no_match"
        elif triggered and observed_engine == r["selected_engine"]:
            result = "fired_observed"
        elif triggered:
            result = "selected_but_observed_engine_diverged"
        else:
            result = "applicable_but_override_did_not_fire"

        entry = {
            "route_id": r["route_id"],
            "fixture_class": {"category": match.get("category")},
            "previous_route": {f"{phase}_engine": r["previous_engine"]},
            "selected_route": {f"{phase}_engine": r["selected_engine"]},
            "decision_evidence": {
                "fixture": fixture_id,
                "input_path": str(state_path.relative_to(work)) if state_path.is_relative_to(work) else str(state_path),
                "state_path": str(state_path.relative_to(work)) if state_path.is_relative_to(work) else str(state_path),
                "observed_phase_engine": observed_engine,
            },
            "short_circuit": {
                "rule_id": r["rule_id"],
                "result": result,
            },
            "wall_budget_abort": {
                "budget_s": None,
                "triggered": False,
            },
            "iter": r["iter"],
        }
        if not class_match:
            not_applicable.append(entry)
        elif result == "fired_observed":
            applicable_fired.append(entry)
        else:
            applicable_missed.append(entry)

    coverage = {
        "version": 1,
        "run_id": run_id,
        "fixture_class": fixture_class,
        # Per-fixture invariant: every applicable changed route must have
        # fired. Non-applicable routes do not affect this — they apply to
        # other fixture classes.
        "all_applicable_routes_exercised": len(applicable_missed) == 0,
        "applicable_fired": applicable_fired,
        "applicable_missed": applicable_missed,
        "not_applicable": not_applicable,
    }
    out = devlyn / "coverage.json"
    out.write_text(json.dumps(coverage, indent=2) + "\n")
    print(
        f"[coverage] wrote {out} "
        f"(applicable_fired={len(applicable_fired)}, "
        f"applicable_missed={len(applicable_missed)}, "
        f"not_applicable={len(not_applicable)})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
