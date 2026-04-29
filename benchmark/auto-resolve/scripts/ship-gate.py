#!/usr/bin/env python3
"""
ship-gate.py — apply RUBRIC.md ship thresholds to a suite run's summary.json.

Usage:
    ship-gate.py --run-id <ID>                   # check gates, return 0/1 via exit code
    ship-gate.py --run-id <ID> --bless           # if PASS, promote summary to baselines/shipped.json

Exits 0 on PASS, 1 on FAIL.
"""
from __future__ import annotations
import argparse, json, pathlib, sys, shutil, datetime


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--bless", action="store_true")
    p.add_argument("--accept-missing", action="store_true",
                   help="skip hard-floor gates that require fixtures not yet implemented "
                        "(F9 and the 7-of-9 count) — only for suites in bootstrap")
    args = p.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    summary_p = root / "results" / args.run_id / "summary.json"
    if not summary_p.exists():
        print(f"no summary at {summary_p}", file=sys.stderr); return 1
    summary = json.loads(summary_p.read_text())

    baseline_p = root / "history" / "baselines" / "shipped.json"
    baseline = None
    if baseline_p.exists():
        try:
            baseline = json.loads(baseline_p.read_text())
        except Exception:
            baseline = None

    failures: list[str] = []
    warnings: list[str] = []

    # Hard floor 1: no disqualifier in variant
    if summary["hard_floor_violations"] > 0:
        failures.append(f"{summary['hard_floor_violations']} variant disqualifier(s) — see report")

    # Hard floor 2: F9 must pass (skipped during bootstrap via --accept-missing)
    # Variant arm legacy gate kept for L2 baseline comparability.
    f9_row = next((r for r in summary["rows"] if r.get("fixture") == "F9-e2e-ideate-to-preflight"), None)
    if f9_row is None:
        if not args.accept_missing:
            failures.append("F9 (E2E novice flow) missing — add fixture or run with --accept-missing")
    else:
        if (f9_row.get("margin") or -999) < 5:
            failures.append("F9 (E2E novice flow) must have variant margin ≥ +5")

    # Hard floor 3: ≥ 7 of 9 gated fixtures with margin ≥ +5
    # (skipped during bootstrap via --accept-missing)
    if summary["gated_fixtures"] > 0 and summary["margin_ge_5_count"] < 7:
        if not args.accept_missing:
            failures.append(
                f"only {summary['margin_ge_5_count']} of {summary['gated_fixtures']} "
                f"gated fixtures have variant margin ≥ +5 (need ≥ 7)"
            )

    # iter-0023 — L1 (solo_claude) gates per NORTH-STAR.md ops test #1.
    # Codex R1 (this iter) caught that ship-gate enforced only legacy L2
    # `variant` margin and never read `solo_over_bare`. Now NORTH-STAR's
    # documented L1 floor (≥ +5, ≥ 7/9 fixtures, F9 ≥ +5, no L1
    # disqualifier) is mechanically enforced.
    arms_present = summary.get("arms_present", {})
    margins_avg = summary.get("margins_avg", {})
    if arms_present.get("solo_claude"):
        l1_avg = margins_avg.get("solo_over_bare")
        if l1_avg is not None and l1_avg < 5:
            warnings.append(
                f"L1 (solo_over_bare) suite avg {l1_avg:+.1f} below NORTH-STAR floor +5 "
                "(reporting only — per-fixture L1 gates below are decisive)"
            )
        # F9 L1 floor
        if f9_row is not None:
            f9_l1 = (f9_row.get("margins") or {}).get("solo_over_bare")
            if f9_l1 is None:
                if not args.accept_missing:
                    failures.append("F9 L1 (solo_over_bare) margin missing — measurement invalid")
            elif f9_l1 < 5:
                failures.append(f"F9 L1 (solo_over_bare) margin {f9_l1:+d} < +5 floor")
        # 7-of-9 L1 floor
        l1_ge_5 = 0
        l1_gated = 0
        for r in summary.get("rows", []):
            if (r.get("category") or "").lower() == "known-limit":
                continue
            m = (r.get("margins") or {}).get("solo_over_bare")
            if m is None:
                continue
            l1_gated += 1
            if m >= 5:
                l1_ge_5 += 1
        if l1_gated > 0 and l1_ge_5 < 7 and not args.accept_missing:
            failures.append(
                f"L1: only {l1_ge_5} of {l1_gated} gated fixtures have solo_over_bare ≥ +5 (need ≥ 7)"
            )
        # L1 disqualifier floor
        l1_dq = sum(
            1 for r in summary.get("rows", [])
            if ((r.get("arms") or {}).get("solo_claude") or {}).get("disqualifier")
        )
        if l1_dq > 0:
            failures.append(f"L1 disqualifier(s): {l1_dq} solo_claude arm(s) hit a disqualifier")
        # L1 axis-validity gate (judge.sh records out-of-range axis cells under
        # `_axis_validation` per fixture). If any L1 row has invalid axis data,
        # the L1 score for that row is not trustworthy.
        l1_axis_invalid = 0
        for r in summary.get("rows", []):
            av = (r.get("arms") or {}).get("solo_claude") or {}
            inv = av.get("_axis_validation_out_of_range_count")
            if inv is not None and inv > 0:
                l1_axis_invalid += 1
        if l1_axis_invalid > 0:
            failures.append(
                f"L1 axis-invalid: {l1_axis_invalid} fixture(s) have out-of-range axis cells — "
                "re-judge before trusting L1 margins"
            )

    # Hard floor 4: no per-fixture regression worse than −5 vs shipped baseline
    if baseline:
        prev_rows = {r["fixture"]: r for r in baseline.get("rows", [])}
        for r in summary["rows"]:
            fid = r.get("fixture")
            prev = prev_rows.get(fid)
            if prev and r.get("variant_score") is not None and prev.get("variant_score") is not None:
                delta = r["variant_score"] - prev["variant_score"]
                if delta < -5:
                    failures.append(f"{fid} regressed {delta:+d} vs shipped (floor: −5)")

    # Soft gate: suite average margin drop > 3
    if baseline:
        margin_delta = summary["margin_avg"] - baseline.get("margin_avg", 0)
        if margin_delta < -3:
            warnings.append(f"suite margin dropped {margin_delta:+.1f} vs shipped (soft gate: > −3)")

    # Soft gate: any fixture that was > +5 before is now ≤ 0
    if baseline:
        prev_rows = {r["fixture"]: r for r in baseline.get("rows", [])}
        for r in summary["rows"]:
            fid = r.get("fixture")
            prev = prev_rows.get(fid)
            if prev and (prev.get("margin") or 0) > 5 and (r.get("margin") or 0) <= 0:
                warnings.append(
                    f"{fid} lost its margin: was {prev['margin']:+d}, now {r['margin']:+d}"
                )

    verdict = "PASS" if not failures else "FAIL"
    print(f"\n═══ SHIP-GATE VERDICT: {verdict} ═══\n")
    if failures:
        print("Hard-floor failures:")
        for f in failures:
            print(f"  ✗ {f}")
        print()
    if warnings:
        print("Soft-gate warnings:")
        for w in warnings:
            print(f"  ⚠ {w}")
        print()
    if not failures and not warnings:
        print("No gate violations. Suite is ship-ready.")

    # Bless if PASS + --bless — opt-in promotion to shipped baseline.
    # Per BENCHMARK-DESIGN.md Karpathy Check, automatic history mutation is
    # deferred until after the suite format stabilizes; `--bless` stays as
    # the explicit promotion path, and `summary.json` inside the run dir
    # is the durable record for ad-hoc inspection.
    if verdict == "PASS" and args.bless:
        baseline_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(summary_p, baseline_p)
        print(f"\nBlessed: {baseline_p}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
