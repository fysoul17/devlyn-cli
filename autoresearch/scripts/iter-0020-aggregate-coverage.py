#!/usr/bin/env python3
"""iter-0020 suite-level coverage aggregator (Codex R2 Q6).

Per-fixture `.devlyn/coverage.json` files (emitted by
`coverage_report.py` at PHASE 5) report whether iter-0020+ changed
routes were applicable to each fixture and whether they fired. Hard
acceptance #4 demands "coverage.json proving every changed route was
exercised" — at the SUITE level, this means every changed `route_id`
must appear in `applicable_fired` of at least one fixture's per-run
coverage.json.

This script walks a benchmark suite results dir, reads every fixture's
archived coverage.json, aggregates by route_id, and emits a verdict:
PASS if every changed route fired at least once, FAIL otherwise. Fails
loud when a fixture has `applicable_missed` non-empty (router bug).

Usage:
    python3 autoresearch/scripts/iter-0020-aggregate-coverage.py \\
        benchmark/auto-resolve/results/<RUN_ID>/

Exit codes:
    0: every changed route exercised ≥1 time AND no router bugs
    1: at least one changed route never fired OR a router bug detected
    2: invocation error (missing dir, no coverage.json files, etc.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: iter-0020-aggregate-coverage.py <results_dir>", file=sys.stderr)
        return 2
    results_dir = Path(sys.argv[1])
    if not results_dir.is_dir():
        print(f"[aggregate] {results_dir} is not a directory", file=sys.stderr)
        return 2

    # Per-fixture coverage.json lives at <results>/<fixture>/<arm>/coverage.json
    # AFTER archive (which moves it from .devlyn/) — but the bench harness
    # archives PER ARM. Conservative: scan every coverage.json under results.
    coverage_files = sorted(results_dir.rglob("coverage.json"))
    if not coverage_files:
        print(f"[aggregate] no coverage.json files under {results_dir}", file=sys.stderr)
        return 2

    # route_id → {arm/fixture path that fired, or empty}
    fired_by_route: dict[str, list[str]] = {}
    missed_by_route: dict[str, list[str]] = {}
    routes_seen: set[str] = set()

    for cf in coverage_files:
        try:
            cov = json.loads(cf.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"[aggregate] cannot parse {cf}: {e}", file=sys.stderr)
            return 2
        rel = str(cf.relative_to(results_dir))
        for entry in cov.get("applicable_fired", []):
            rid = entry.get("route_id")
            if rid:
                routes_seen.add(rid)
                fired_by_route.setdefault(rid, []).append(rel)
        for entry in cov.get("applicable_missed", []):
            rid = entry.get("route_id")
            if rid:
                routes_seen.add(rid)
                missed_by_route.setdefault(rid, []).append(rel)
        for entry in cov.get("not_applicable", []):
            rid = entry.get("route_id")
            if rid:
                routes_seen.add(rid)

    # Reconcile: a route is "covered" if fired ≥1 time AND no missed.
    print(f"\n{'=' * 70}")
    print(f"iter-0020 suite-level coverage aggregation")
    print(f"Results dir: {results_dir}")
    print(f"Coverage files scanned: {len(coverage_files)}")
    print(f"{'=' * 70}\n")

    failed = False
    if not routes_seen:
        print("  ⚠ No changed routes evaluated by any fixture. Either no")
        print("    iter-0020+ routes are registered in coverage_report.py")
        print("    CHANGED_ROUTES, or none of the fixtures invoked PHASE 5.")
        return 1

    for rid in sorted(routes_seen):
        fired = fired_by_route.get(rid, [])
        missed = missed_by_route.get(rid, [])
        if fired and not missed:
            marker = "✓ EXERCISED"
        elif missed:
            marker = "✗ ROUTER BUG (applicable_missed)"
            failed = True
        else:
            marker = "✗ NEVER FIRED"
            failed = True
        print(f"  {marker}  {rid}")
        for f in fired:
            print(f"           └─ fired: {f}")
        for m in missed:
            print(f"           └─ MISSED (router did not fire override): {m}")

    print(f"\n{'=' * 70}")
    if failed:
        print("VERDICT: FAIL — at least one changed route is not provably exercised.")
        print("Hard acceptance #4 NOT satisfied. Fix before iter-0020 ships.")
    else:
        print("VERDICT: PASS — every changed route was exercised ≥1 time with no")
        print("router bugs detected. Hard acceptance #4 satisfied.")
    print(f"{'=' * 70}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
