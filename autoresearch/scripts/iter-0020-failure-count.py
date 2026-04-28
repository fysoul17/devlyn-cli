#!/usr/bin/env python3
"""iter-0020 Phase A verdict — compute pair_policy_failure_count.

Per Codex R0 (2026-04-28) Option D:
- Predefined failure predicate per pair-routed fixture class:
    L2-L1 < +5
    OR L2 < L1 (any margin)
    OR L2 introduces DQ/CRITICAL/HIGH regression absent in L1
  while paying material L2 wall-time premium (wall_ratio_variant_over_solo > 1.5).

Read summary.json from the iter-0020 Phase A run; emit per-fixture verdict
table + failure_count + decision recommendation.

Usage:
    python3 autoresearch/scripts/iter-0020-failure-count.py <results_dir>

Where <results_dir> is the suite output, e.g.
    benchmark/auto-resolve/results/<RUN_ID>-iter-0020-phaseA-preflight/

Exits:
    0 = failure_count == 0 → close iter-0020 as "data confirms"
    1 = failure_count >= 1 → Phase B fires (narrow/drop pair for failing classes)
    2 = invocation error
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

WALL_RATIO_THRESHOLD = 1.5  # "material L2 wall-time premium" floor


def classify_fixture(row: dict) -> tuple[str, list[str]]:
    """Return (verdict, reasons) for one fixture row.

    verdict in {"PAIR_OK", "PAIR_FAILS"}
    """
    arms = row.get("arms") or {}
    v = arms.get("variant") or {}
    s = arms.get("solo_claude") or {}
    if not v or not s:
        return ("PAIR_OK", ["L2 or L1 arm missing — cannot evaluate, treating as no-failure"])

    margins = row.get("margins") or {}
    wall_ratios = row.get("wall_ratios") or {}
    v_score = v.get("score")
    s_score = s.get("score")
    v_over_s_margin = margins.get("variant_over_solo")
    v_over_s_wall = wall_ratios.get("variant_over_solo")
    v_dq = bool(v.get("disqualifier", False))
    s_dq = bool(s.get("disqualifier", False))
    v_critical = v.get("critical_findings") or []
    s_critical = s.get("critical_findings") or []

    reasons: list[str] = []
    is_failure = False

    # Need wall premium to flag — pair without wall cost is not a "wasted pair"
    material_wall = (v_over_s_wall is not None) and (v_over_s_wall > WALL_RATIO_THRESHOLD)

    if v_over_s_margin is not None and v_over_s_margin < 5:
        if material_wall:
            is_failure = True
            reasons.append(
                f"L2-L1 margin = {v_over_s_margin:+d} < +5 floor "
                f"AND wall_ratio = {v_over_s_wall:.2f}× > {WALL_RATIO_THRESHOLD}× "
                f"(failure: pair cost not layer-cost-justified)"
            )
        else:
            reasons.append(
                f"L2-L1 margin = {v_over_s_margin:+d} < +5 BUT wall_ratio "
                f"= {v_over_s_wall}× ≤ {WALL_RATIO_THRESHOLD}× (no material premium → not flagged)"
            )

    if v_score is not None and s_score is not None and v_score < s_score:
        if material_wall:
            is_failure = True
            reasons.append(
                f"L2 score = {v_score} < L1 score = {s_score} AND material wall premium "
                f"(failure: L2 actively regressed)"
            )
        else:
            reasons.append(
                f"L2 < L1 BUT no material wall premium (not flagged — but suspect)"
            )

    # DQ/CRITICAL/HIGH regression absent in L1
    if v_dq and not s_dq:
        is_failure = True
        reasons.append("L2 disqualifier=true but L1 disqualifier=false (regression)")
    if len(v_critical) > len(s_critical):
        is_failure = True
        reasons.append(
            f"L2 has {len(v_critical)} CRITICAL findings vs L1 {len(s_critical)} "
            f"(regression)"
        )

    if not reasons:
        reasons.append(
            f"L2-L1 margin = {v_over_s_margin if v_over_s_margin is not None else 'n/a'}, "
            f"wall_ratio = {v_over_s_wall if v_over_s_wall is not None else 'n/a'}× "
            "(no failure)"
        )

    return ("PAIR_FAILS" if is_failure else "PAIR_OK", reasons)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: iter-0020-failure-count.py <results_dir>", file=sys.stderr)
        return 2
    results_dir = Path(sys.argv[1])
    summary_path = results_dir / "summary.json"
    if not summary_path.is_file():
        print(f"[iter-0020] {summary_path} not found", file=sys.stderr)
        return 2
    summary = json.loads(summary_path.read_text())
    rows = summary.get("rows") or []
    if not rows:
        print(f"[iter-0020] no fixture rows in summary.json", file=sys.stderr)
        return 2

    print(f"\n{'=' * 78}")
    print(f"iter-0020 Phase A verdict — failure-count computation")
    print(f"Results dir: {results_dir}")
    print(f"{'=' * 78}\n")

    failure_count = 0
    failures: list[str] = []
    for row in rows:
        fid = row.get("fixture", "?")
        category = row.get("category") or "n/a"
        verdict, reasons = classify_fixture(row)
        marker = "✗ FAIL" if verdict == "PAIR_FAILS" else "✓ OK  "
        print(f"  {marker}  {fid:42}  category={category:10}")
        for r in reasons:
            print(f"           └─ {r}")
        if verdict == "PAIR_FAILS":
            failure_count += 1
            failures.append(f"{fid} (category={category})")
        print()

    print(f"{'=' * 78}")
    print(f"pair_policy_failure_count = {failure_count}")
    print(f"{'=' * 78}\n")

    if failure_count == 0:
        print("DECISION: close iter-0020 as 'data confirms current routing post "
              "iter-0019.6+.8; no behavior change shipped'.")
        print("ROLLBACK CONDITION: reopen routing if 9-fixture suite OR real-project "
              "trial reveals any class crossing the same failure predicate.")
        return 0
    else:
        print(f"DECISION: Phase B fires. Failing fixture-class(es):")
        for f in failures:
            print(f"  - {f}")
        print()
        print("Phase B scope: smallest executable route change for failing class(es) "
              "ONLY. Add deterministic short-circuit + coverage.json ONLY for "
              "changed routes. 9-fixture run gates ship.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
