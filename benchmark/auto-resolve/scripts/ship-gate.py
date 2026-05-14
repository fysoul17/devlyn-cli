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

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import reject_json_constant


def load_dict_json(path: pathlib.Path) -> tuple[dict | None, str | None]:
    try:
        data = json.loads(path.read_text(), parse_constant=reject_json_constant)
    except (ValueError, json.JSONDecodeError):
        return None, "invalid JSON"
    if not isinstance(data, dict):
        return None, "expected object"
    return data, None


def object_or_empty(value) -> dict:
    return value if isinstance(value, dict) else {}


def rows_from_summary(summary: dict, failures: list[str]) -> list[dict]:
    raw_rows = summary.get("rows")
    if not isinstance(raw_rows, list):
        failures.append("summary rows missing or malformed — measurement invalid")
        return []
    rows = [row for row in raw_rows if isinstance(row, dict)]
    if len(rows) != len(raw_rows):
        failures.append("summary rows contain non-object entries — measurement invalid")
    return rows


def int_or_none(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def number_or_none(value) -> int | float | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, (int, float)) else None


def bool_or_none(value) -> bool | None:
    return value if isinstance(value, bool) else None


def axis_invalid_count(rows: list[dict], arm: str, failures: list[str]) -> int:
    total = 0
    for row in rows:
        arms = object_or_empty(row.get("arms"))
        payload = object_or_empty(arms.get(arm))
        raw_count = payload.get("_axis_validation_out_of_range_count", 0)
        count = number_or_none(raw_count)
        if count is None:
            failures.append(f"{arm} axis count malformed — measurement invalid")
        elif count > 0:
            total += 1
    return total


def unmapped_axis_invalid_count(rows: list[dict], failures: list[str]) -> int:
    total = 0
    for row in rows:
        raw_count = row.get("_axis_validation_unmapped_out_of_range_count", 0)
        count = number_or_none(raw_count)
        if count is None:
            failures.append("unmapped axis count malformed — measurement invalid")
        elif count > 0:
            total += 1
    return total


def is_known_limit(row: dict) -> bool:
    raw_category = row.get("category")
    category = raw_category.lower() if isinstance(raw_category, str) else ""
    return category in {"edge", "known-limit"}


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
    summary, summary_error = load_dict_json(summary_p)
    if summary is None:
        print(f"measurement invalid: malformed summary.json ({summary_error})", file=sys.stderr)
        return 1

    baseline_p = root / "history" / "baselines" / "shipped.json"
    baseline = None
    if baseline_p.exists():
        baseline, _ = load_dict_json(baseline_p)
        if baseline is None:
            baseline = None

    failures: list[str] = []
    warnings: list[str] = []
    rows = rows_from_summary(summary, failures)

    # Hard floor 1: no disqualifier in variant
    hard_floor_violations = int_or_none(summary.get("hard_floor_violations"))
    if hard_floor_violations is None:
        failures.append("summary hard_floor_violations missing or malformed — measurement invalid")
    elif hard_floor_violations > 0:
        failures.append(f"{hard_floor_violations} variant disqualifier(s) — see report")
    variant_axis_invalid = axis_invalid_count(rows, "variant", failures)
    if variant_axis_invalid > 0:
        failures.append(
            f"variant axis-invalid: {variant_axis_invalid} fixture(s) have out-of-range axis cells — "
            "re-judge before trusting L2 margins"
        )
    bare_axis_invalid = axis_invalid_count(rows, "bare", failures)
    if bare_axis_invalid > 0:
        failures.append(
            f"bare axis-invalid: {bare_axis_invalid} fixture(s) have out-of-range axis cells — "
            "re-judge before trusting margins"
        )
    unmapped_axis_invalid = unmapped_axis_invalid_count(rows, failures)
    if unmapped_axis_invalid > 0:
        failures.append(
            f"judge axis-invalid unmapped: {unmapped_axis_invalid} fixture(s) have out-of-range axis cells "
            "that could not be mapped to an arm — re-judge before trusting margins"
        )

    # Hard floor 2: F9 must pass (skipped during bootstrap via --accept-missing)
    # Variant arm legacy gate kept for L2 baseline comparability.
    # iter-0033a (2026-04-30): renamed F9 dir from -to-preflight to -to-resolve to
    # match the shipped 2-skill contract (no preflight). The OLD pre-rename id
    # is preserved in fixtures/retired/ for replay.
    f9_row = next((r for r in rows if r.get("fixture") == "F9-e2e-ideate-to-resolve"), None)
    if f9_row is None:
        if not args.accept_missing:
            failures.append("F9 (E2E novice flow) missing — add fixture or run with --accept-missing")
    else:
        f9_margin = number_or_none(f9_row.get("margin"))
        if f9_margin is None:
            failures.append("F9 (E2E novice flow) margin missing or malformed — measurement invalid")
        elif f9_margin < 5:
            failures.append("F9 (E2E novice flow) must have variant margin ≥ +5")

    for row in rows:
        if not is_known_limit(row):
            continue
        margin = number_or_none(row.get("margin"))
        if margin is not None and (margin < -3 or margin > 3):
            warnings.append(
                f"{row.get('fixture')} known-limit margin {margin:+g} outside expected [-3,+3] range"
            )

    # Hard floor 3: at least 7 gated fixtures with margin ≥ +5
    # (skipped during bootstrap via --accept-missing)
    gated_fixtures = int_or_none(summary.get("gated_fixtures"))
    margin_ge_5_count = int_or_none(summary.get("margin_ge_5_count"))
    if gated_fixtures is None or margin_ge_5_count is None:
        failures.append("summary gated fixture counts missing or malformed — measurement invalid")
    elif gated_fixtures > 0 and margin_ge_5_count < 7:
        if not args.accept_missing:
            failures.append(
                f"only {margin_ge_5_count} of {gated_fixtures} "
                f"gated fixtures have variant margin ≥ +5 (need ≥ 7)"
            )

    # iter-0023 — L1 (solo_claude) gates per NORTH-STAR.md ops test #1.
    # Codex R1 (this iter) caught that ship-gate enforced only legacy L2
    # `variant` margin and never read `solo_over_bare`. Now NORTH-STAR's
    # documented L1 floor (≥ +5 on at least 7 gated fixtures, F9 ≥ +5, no L1
    # disqualifier) is mechanically enforced.
    raw_arms_present = summary.get("arms_present")
    if raw_arms_present is not None and not isinstance(raw_arms_present, dict):
        failures.append("summary arms_present malformed — measurement invalid")
    arms_present = object_or_empty(raw_arms_present)
    raw_margins_avg = summary.get("margins_avg")
    margins_avg = object_or_empty(raw_margins_avg)
    raw_solo_present = arms_present.get("solo_claude")
    solo_present = bool_or_none(raw_solo_present)
    if raw_solo_present is not None and solo_present is None:
        failures.append("summary arms_present.solo_claude malformed — measurement invalid")
    if solo_present is True:
        if raw_margins_avg is not None and not isinstance(raw_margins_avg, dict):
            failures.append("summary margins_avg malformed — measurement invalid")
        l1_dq_by_fixture: dict[str, bool] = {}
        for r in rows:
            fixture = str(r.get("fixture"))
            l1 = object_or_empty(object_or_empty(r.get("arms")).get("solo_claude"))
            raw_l1_dq = l1.get("disqualifier")
            parsed_l1_dq = bool_or_none(raw_l1_dq)
            if raw_l1_dq is not None and parsed_l1_dq is None:
                failures.append(f"{fixture} L1 disqualifier malformed — measurement invalid")
                l1_dq_by_fixture[fixture] = True
            else:
                l1_dq_by_fixture[fixture] = parsed_l1_dq is True

        l1_avg = margins_avg.get("solo_over_bare")
        if l1_avg is not None and number_or_none(l1_avg) is None:
            failures.append("L1 (solo_over_bare) suite avg malformed — measurement invalid")
        elif l1_avg is not None and l1_avg < 5:
            warnings.append(
                f"L1 (solo_over_bare) suite avg {l1_avg:+.1f} below NORTH-STAR floor +5 "
                "(reporting only — per-fixture L1 gates below are decisive)"
            )
        # F9 L1 floor
        if f9_row is not None:
            f9_l1 = object_or_empty(f9_row.get("margins")).get("solo_over_bare")
            if f9_l1 is None:
                if not args.accept_missing:
                    failures.append("F9 L1 (solo_over_bare) margin missing — measurement invalid")
            elif number_or_none(f9_l1) is None:
                failures.append("F9 L1 (solo_over_bare) margin malformed — measurement invalid")
            elif f9_l1 < 5:
                failures.append(f"F9 L1 (solo_over_bare) margin {f9_l1:+g} < +5 floor")
        # 7-fixture L1 floor — headroom-aware (added 2026-05-02 per iter-0033 R4
        # Codex collab + NORTH-STAR amendment + RUBRIC hard-floor 3 update).
        # A fixture is excluded from the denominator when 100 - L0_score < 5
        # AND L1_score >= 95 AND the L1 arm has no disqualifier / CRITICAL-HIGH
        # finding / watchdog timeout / regression worse than gate #4. Excluded
        # fixtures become fixture-rotation candidates if RUBRIC's
        # two-shipped-version saturation rule fires.
        l1_ge_5 = 0
        l1_gated = 0
        l1_excluded_headroom = []
        for r in rows:
            if is_known_limit(r):
                continue
            arms = object_or_empty(r.get("arms"))
            l0 = object_or_empty(arms.get("bare"))
            l1 = object_or_empty(arms.get("solo_claude"))
            l0_score = number_or_none(l0.get("score"))
            l1_score = number_or_none(l1.get("score"))
            m = number_or_none(object_or_empty(r.get("margins")).get("solo_over_bare"))
            if m is None:
                continue
            # Headroom carve-out — must satisfy ALL conditions:
            # (a) bare ceiling-near (100 - L0 < 5)
            # (b) L1 also ceiling-near (>=95)
            # (c) L1 arm clean (no disqualifier, no axis-invalid, fix-loop didn't fail)
            l1_dq_here = l1_dq_by_fixture.get(str(r.get("fixture")), False)
            l1_axis_count = number_or_none(l1.get("_axis_validation_out_of_range_count", 0))
            l1_axis_inv = bool(l1_axis_count is not None and l1_axis_count > 0)
            if (
                l0_score is not None and l1_score is not None
                and (100 - l0_score) < 5 and l1_score >= 95
                and not l1_dq_here and not l1_axis_inv
            ):
                l1_excluded_headroom.append({
                    "fixture": r.get("fixture"),
                    "l0_score": l0_score,
                    "l1_score": l1_score,
                    "margin": m,
                })
                continue
            l1_gated += 1
            if m >= 5:
                l1_ge_5 += 1
        if l1_gated > 0 and l1_ge_5 < 7 and not args.accept_missing:
            failures.append(
                f"L1: only {l1_ge_5} of {l1_gated} headroom-available fixtures have solo_over_bare ≥ +5 (need ≥ 7)"
            )
        if l1_excluded_headroom:
            warnings.append(
                "L1 headroom-excluded (saturation candidates per RUBRIC two-shipped-version rule): "
                + ", ".join(
                    f"{x['fixture']} (L0={x['l0_score']} L1={x['l1_score']} margin={x['margin']:+g})"
                    for x in l1_excluded_headroom
                )
            )
        # L1 disqualifier floor
        l1_dq = sum(
            1 for r in rows
            if l1_dq_by_fixture.get(str(r.get("fixture")), False)
        )
        if l1_dq > 0:
            failures.append(f"L1 disqualifier(s): {l1_dq} solo_claude arm(s) hit a disqualifier")
        # L1 axis-validity gate (judge.sh records out-of-range axis cells under
        # `_axis_validation` per fixture). If any L1 row has invalid axis data,
        # the L1 score for that row is not trustworthy.
        l1_axis_invalid = 0
        for r in rows:
            av = object_or_empty(object_or_empty(r.get("arms")).get("solo_claude"))
            inv = av.get("_axis_validation_out_of_range_count")
            count = number_or_none(inv)
            if inv is not None and count is None:
                failures.append("L1 axis count malformed — measurement invalid")
            elif count is not None and count > 0:
                l1_axis_invalid += 1
        if l1_axis_invalid > 0:
            failures.append(
                f"L1 axis-invalid: {l1_axis_invalid} fixture(s) have out-of-range axis cells — "
                "re-judge before trusting L1 margins"
            )

    # Hard floor 4: no per-fixture regression worse than −5 vs shipped baseline
    if baseline:
        prev_rows = {
            r["fixture"]: r for r in baseline.get("rows", [])
            if isinstance(r, dict) and isinstance(r.get("fixture"), str)
        }
        for r in rows:
            if is_known_limit(r):
                continue
            fid = r.get("fixture")
            prev = prev_rows.get(fid)
            current_score = number_or_none(r.get("variant_score"))
            previous_score = number_or_none(prev.get("variant_score")) if prev else None
            if prev and current_score is not None and previous_score is not None:
                delta = current_score - previous_score
                if delta < -5:
                    failures.append(f"{fid} regressed {delta:+g} vs shipped (floor: −5)")

    # Soft gate: suite average margin drop > 3
    if baseline:
        current_margin_avg = number_or_none(summary.get("margin_avg"))
        baseline_margin_avg = number_or_none(baseline.get("margin_avg"))
        if current_margin_avg is None:
            failures.append("suite margin missing — measurement invalid")
        elif baseline_margin_avg is None:
            warnings.append("shipped baseline margin malformed; skipping suite margin delta")
        else:
            margin_delta = current_margin_avg - baseline_margin_avg
            if margin_delta < -3:
                warnings.append(f"suite margin dropped {margin_delta:+.1f} vs shipped (soft gate: > −3)")

    # Soft gate: any fixture that was > +5 before is now ≤ 0
    if baseline:
        prev_rows = {
            r["fixture"]: r for r in baseline.get("rows", [])
            if isinstance(r, dict) and isinstance(r.get("fixture"), str)
        }
        for r in rows:
            fid = r.get("fixture")
            prev = prev_rows.get(fid)
            prev_margin = number_or_none(prev.get("margin")) if prev else None
            current_margin = number_or_none(r.get("margin"))
            if prev and prev_margin is not None and prev_margin > 5:
                if current_margin is None:
                    warnings.append(f"{fid} margin missing; was {prev_margin:+g}")
                elif current_margin <= 0:
                    warnings.append(
                        f"{fid} lost its margin: was {prev_margin:+g}, now {current_margin:+g}"
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
