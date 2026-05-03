#!/usr/bin/env python3
"""iter-0033c gate table — NEW L2 vs NEW L1 on /devlyn:resolve.

Reads:
  - manifest (immutable; built by build-pair-eligible-manifest.py)
  - per-fixture judge.json files under <results-dir>/<fixture>/<arm>/judge.json
  - per-fixture timing/result.json files for wall + disqualifier signals
  - per-fixture pipeline.state.json (under <work-dir>/.devlyn/runs/) for
    pair_judge sub-verdict — required for Gate 6 + Gate 8.

Emits:
  - gates.json — machine-readable {gate_id, status, evidence}
  - gates.md   — human-readable summary table

Gates per iter-0033c §"Acceptance gate":
  1a smoke (mode wiring) — recorded externally; pre-suite gate
  1b smoke (codex avail)  — recorded externally; pre-suite gate
  1c smoke (impl confound) — recorded externally; pre-suite gate
  2  no-regression vs L1 (gated arm): every fixture (l2_gated − solo) ≥ −3
  3  lift on pair-eligible (gated arm, SHIP-BLOCKER): on frozen pair-eligible set,
     count fixtures with (l2_gated − solo) ≥ +5; require count ≥ gate3_threshold_count.
  4  hard-floor: zero l2_gated disqualifier on previously-clean l1 fixtures;
     zero l2_gated CRITICAL/HIGH design.* / security.* on previously-clean l1;
     zero l2_gated watchdog timeouts (where l1 didn't time out).
  5  efficiency: per-fixture l2_gated_wall / l1_wall ≤ 2.0× (≤ 3.0× allowed only
     when l2 catches a categorical rescue l1 missed).
  6  trigger discipline (fixture-level): for each pair-eligible fixture, if
     l2_forced lifts ≥ +5 OR catches categorical rescue, AND forced is not
     impl-confounded, AND forced.pair_judge present → l2_gated MUST also have
     pair_judge present on that fixture.
  7  attribution (4-class, data-only): per-fixture classify into
     {no_material_lift, implementation_confounded, tool_or_trigger_lift,
      deliberation_lift}. Reporting only; not pass/fail.
  8  artifact contract: pair_judge non-null for every fixture where pair fired;
     pair findings distinguishable from solo judge findings.

Ship-blockers: 1a, 1b, 1c, 2, 3, 4, 6.
Quality gates: 5, 8 (failure → root-cause iter; Phase 4 holds).
Data-only: 7.
"""
import argparse
import json
import sys
from pathlib import Path


def load_judge(results_dir: Path, fixture: str) -> dict | None:
    p = results_dir / fixture / "judge.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def load_result(results_dir: Path, fixture: str, arm: str) -> dict | None:
    p = results_dir / fixture / arm / "result.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def load_state(work_dir_root: Path, run_id: str, fixture: str, arm: str) -> dict | None:
    """state.json lives in /tmp/bench-{run_id}-{fixture}-{arm}/.devlyn/runs/<rs-id>/."""
    work = work_dir_root / f"bench-{run_id}-{fixture}-{arm}"
    runs = work / ".devlyn" / "runs"
    if not runs.is_dir():
        return None
    candidates = sorted(runs.glob("*/pipeline.state.json"))
    if not candidates:
        return None
    return json.loads(candidates[-1].read_text())


def archive_run_dir(work_dir_root: Path, run_id: str, fixture: str, arm: str) -> Path | None:
    """The .devlyn/runs/<rs-id>/ where pipeline archived per-run artifacts."""
    work = work_dir_root / f"bench-{run_id}-{fixture}-{arm}"
    runs = work / ".devlyn" / "runs"
    if not runs.is_dir():
        return None
    cands = sorted(runs.glob("*/pipeline.state.json"))
    if not cands:
        return None
    return cands[-1].parent


def changed_files(results_dir: Path, fixture: str, arm: str) -> set[str]:
    """Read changed-files.txt for an arm; returns set of file paths."""
    p = results_dir / fixture / arm / "changed-files.txt"
    if not p.is_file():
        return set()
    return {ln.strip() for ln in p.read_text().splitlines() if ln.strip()}


def pair_findings_distinguishable(work_dir_root: Path, run_id: str, fixture: str, arm: str) -> bool:
    """True iff archive has at least one per-engine pair-judge artifact for >=2 engines.

    Gate 8: pair findings must be distinguishable from solo judge findings. The
    orchestrator (Claude reading SKILL.md) was observed across smokes 1a + 1c
    (fixed-diff) writing per-judge artifacts under several naming conventions:

      * `verify-judge-<engine>.md`            (smoke 1a, full pair mode)
      * `verify.judge.<engine>.findings.jsonl` (smoke 1c, verify-only pair mode)
      * `verify.judge.<engine>.summary.json`   (verify-only mode auxiliary)

    Detection treats "two distinct engine identifiers across any of those patterns"
    as distinguishable. archive_run.py moves both `verify-judge-*.md` (added in
    iter-0033c) and any `*.findings.jsonl` (existing pre-iter-0033c) so both
    conventions land in the run dir. Either missing distinct engines = broken.
    """
    archive = archive_run_dir(work_dir_root, run_id, fixture, arm)
    if archive is None:
        return False
    import re
    # Collect engine identifiers across all observed pair-judge naming patterns.
    patterns = [
        re.compile(r"^verify-judge-(?P<engine>[a-z0-9_]+)\.md$"),
        re.compile(r"^verify\.judge\.(?P<engine>[a-z0-9_]+)\.findings\.jsonl$"),
        re.compile(r"^verify\.judge\.(?P<engine>[a-z0-9_]+)\.summary\.json$"),
    ]
    engines = set()
    for f in archive.iterdir():
        if not f.is_file():
            continue
        for pat in patterns:
            m = pat.match(f.name)
            if m:
                engines.add(m.group("engine"))
                break
    return len(engines) >= 2


def impl_confounded_for_fixture(results_dir: Path, fixture: str) -> bool:
    """True iff symmetric difference of changed-files between solo_claude and
    l2_forced is non-empty. Drives Gate 7 attribution + Gate 3 carve-out
    decision per Codex R-final-smoke Q5 (option (b): fixed-diff for confounded
    fixtures only, NOT a wholesale pivot).

    Smoke 1c (2026-05-02) confirmed F2 confounds (solo touched 1 file, l2_forced
    touched 2 — l2_forced added a test file solo skipped) while F3 does not
    (both arms touched the same 2 files).
    """
    solo = changed_files(results_dir, fixture, "solo_claude")
    forced = changed_files(results_dir, fixture, "l2_forced")
    if not solo or not forced:
        return False  # arm absent → can't claim confound
    return solo.symmetric_difference(forced) != set()


def fixture_short(name: str) -> str:
    return name.split("-", 1)[0] if "-" in name else name


def find_results_dir_fixtures(results_dir: Path) -> list[str]:
    return sorted(d.name for d in results_dir.iterdir() if d.is_dir())


def get_score(judge: dict, arm: str) -> int | None:
    """Score for a given arm. Prefer judge.json's `scores_by_arm` (already
    arm-keyed); fall back to blind A/B/C lookup with case-correct `<letter>_score`
    field (judge.sh writes a_score/b_score lowercase, not A_score)."""
    if not judge:
        return None
    sba = judge.get("scores_by_arm") or {}
    if arm in sba:
        return sba[arm]
    mapping = judge.get("_blind_mapping") or {}
    letter = next((k for k, v in mapping.items() if v == arm), None)
    if not letter:
        return None
    return judge.get(f"{letter.lower()}_score")


def get_disqualifier(judge: dict, arm: str) -> bool:
    """DQ flag for a given arm. Prefer `disqualifiers_by_arm` written by judge.sh
    line 314-323; fall back to blind A/B/C with case-correct letter."""
    if not judge:
        return False
    dba = judge.get("disqualifiers_by_arm") or {}
    if arm in dba:
        return bool(dba[arm].get("disqualifier", False))
    dqs = judge.get("disqualifiers") or {}
    mapping = judge.get("_blind_mapping") or {}
    letter = next((k for k, v in mapping.items() if v == arm), None)
    if not letter:
        return False
    return bool(dqs.get(letter, False))


def gate_2_no_regression(rows: list[dict]) -> dict:
    failures = []
    for row in rows:
        if row["solo_score"] is None or row["l2_gated_score"] is None:
            continue
        delta = row["l2_gated_score"] - row["solo_score"]
        if delta < -3:
            failures.append({"fixture": row["fixture"], "delta": delta})
    return {
        "gate": "2-no-regression",
        "status": "PASS" if not failures else "FAIL",
        "rule": "every fixture: (l2_gated − solo) ≥ −3",
        "failures": failures,
    }


def gate_3_lift(rows: list[dict], manifest: dict) -> dict:
    eligible = set(manifest["fixtures_pair_eligible"])
    threshold = manifest["gate3_threshold_count"]
    total = manifest["gate3_total"]
    counted = []
    for row in rows:
        fx = fixture_short(row["fixture"])
        if fx not in eligible:
            continue
        if row["solo_score"] is None or row["l2_gated_score"] is None:
            continue
        delta = row["l2_gated_score"] - row["solo_score"]
        counted.append({"fixture": row["fixture"], "delta": delta, "lift_ge5": delta >= 5})
    n_lift = sum(1 for c in counted if c["lift_ge5"])
    return {
        "gate": "3-lift-on-pair-eligible",
        "ship_blocker": True,
        "status": "PASS" if n_lift >= threshold else "FAIL",
        "rule": f"lift ≥ +5 on ≥ {threshold} of {total} pair-eligible fixtures",
        "lift_count": n_lift,
        "threshold": threshold,
        "total": total,
        "details": counted,
    }


def classify_l2_disqualifier(row: dict, mechanical_findings: list[dict]) -> str:
    """Bucket why L2 disqualified a previously-clean L1 fixture (Codex R-final-fdfd Q2).

    Buckets:
      - `mechanical_failed`: deterministic spec-verify gate ALSO flagged a
        disqualifier-class finding → real product defect → Gate 4 FAIL.
      - `target_env_reproduced`: pair-JUDGE finding manually reproduced in the
        target env (post-suite human adjudication). Gate 4 FAIL.
      - `pair_sandbox_only`: pair-JUDGE surfaced a CRITICAL/HIGH finding that
        mechanical did NOT trigger. Could be valid-but-environment-conditional
        (e.g. EPERM handling on systems where ~/.claude is unreadable); Codex's
        smoke 1c-fixed on F2 was textbook of this. Logged as Gate 7 evidence,
        NOT Gate 4 FAIL.

    Default classification = `pair_sandbox_only` when mechanical didn't fail.
    `target_env_reproduced` requires post-hoc manual override (no auto-reproducer).
    """
    has_mechanical_dq = any(
        (f.get("severity") in ("CRITICAL", "HIGH")
         and f.get("source") in ("mechanical", "spec-verify"))
        or f.get("disqualifier") is True
        for f in mechanical_findings
    )
    if has_mechanical_dq:
        return "mechanical_failed"
    return "pair_sandbox_only"


def load_mechanical_findings(work_dir_root: Path, run_id: str, fixture: str, arm: str) -> list[dict]:
    archive = archive_run_dir(work_dir_root, run_id, fixture, arm)
    if archive is None:
        return []
    p = archive / "verify-mechanical.findings.jsonl"
    if not p.is_file():
        return []
    out = []
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def gate_4_hard_floor(rows: list[dict], work_dir_root: Path, run_id: str) -> dict:
    failures = []
    sandbox_only = []
    for row in rows:
        if row["solo_dq"]:
            continue
        if row["l2_gated_dq"]:
            mech = load_mechanical_findings(work_dir_root, run_id, row["fixture"], "l2_gated")
            classification = classify_l2_disqualifier(row, mech)
            entry = {"fixture": row["fixture"], "kind": "l2_gated_dq_on_clean_l1",
                     "classification": classification}
            if classification in ("mechanical_failed", "target_env_reproduced"):
                failures.append(entry)
            else:
                sandbox_only.append(entry)
        if row["l2_gated_timeout"] and not row["solo_timeout"]:
            failures.append({"fixture": row["fixture"], "kind": "l2_gated_timeout_only",
                             "classification": "timeout"})
    return {
        "gate": "4-hard-floor",
        "ship_blocker": True,
        "status": "PASS" if not failures else "FAIL",
        "rule": ("zero l2_gated dq / timeout on previously-clean l1 fixtures, "
                 "where dq is classified as mechanical_failed OR target_env_reproduced "
                 "(pair_sandbox_only logged as Gate 7 evidence per Codex R-final-fdfd Q2)"),
        "failures": failures,
        "pair_sandbox_only_logged": sandbox_only,
    }


def gate_5_efficiency(rows: list[dict]) -> dict:
    failures = []
    details = []
    for row in rows:
        if row["solo_wall"] is None or row["l2_gated_wall"] is None:
            continue
        if row["solo_wall"] == 0:
            continue
        ratio = row["l2_gated_wall"] / row["solo_wall"]
        details.append({"fixture": row["fixture"], "ratio": round(ratio, 2)})
        if ratio > 2.0:
            failures.append({"fixture": row["fixture"], "ratio": round(ratio, 2)})
    return {
        "gate": "5-efficiency",
        "status": "PASS" if not failures else "FAIL",
        "rule": "per-fixture l2_gated_wall / l1_wall ≤ 2.0×",
        "failures": failures,
        "details": details,
    }


def gate_6_trigger_discipline(rows: list[dict], manifest: dict) -> dict:
    eligible = set(manifest["fixtures_pair_eligible"])
    failures = []
    for row in rows:
        fx = fixture_short(row["fixture"])
        if fx not in eligible:
            continue
        if row["l2_forced_score"] is None:
            continue
        forced_lift = (
            row["l2_forced_score"] is not None and row["solo_score"] is not None
            and (row["l2_forced_score"] - row["solo_score"] >= 5)
        )
        forced_rescue = bool(row["solo_dq"] and not row["l2_forced_dq"])
        forced_pair_present = bool(row["l2_forced_pair_judge_present"])
        gated_pair_present = bool(row["l2_gated_pair_judge_present"])
        if (forced_lift or forced_rescue) and forced_pair_present and not gated_pair_present:
            failures.append({
                "fixture": row["fixture"],
                "forced_lift": forced_lift,
                "forced_rescue": forced_rescue,
                "gated_pair_judge_present": gated_pair_present,
            })
    return {
        "gate": "6-trigger-discipline",
        "ship_blocker": True,
        "status": "PASS" if not failures else "FAIL",
        "rule": "if forced lifts ≥ +5 (or rescues) → gated must also fire pair on that fixture",
        "failures": failures,
    }


def gate_7_attribution(rows: list[dict], manifest: dict) -> dict:
    """4-class classification per fixture; data-gathering only.

    no_material_lift           — solo and l2 verdicts equivalent within ±2
    implementation_confounded  — IMPLEMENT diffs differ materially (smoke 1c flagged)
    tool_or_trigger_lift       — mechanical/coverage finding caused axis change
    deliberation_lift          — pair_judge surfaces verdict-binding finding absent from solo
    """
    classes = []
    for row in rows:
        fx = fixture_short(row["fixture"])
        cls = "no_material_lift"  # default
        if row["impl_confounded"]:
            cls = "implementation_confounded"
        elif row["solo_score"] is not None and row["l2_gated_score"] is not None:
            delta = row["l2_gated_score"] - row["solo_score"]
            if abs(delta) <= 2:
                cls = "no_material_lift"
            elif row["pair_judge_unique_finding"]:
                cls = "deliberation_lift"
            elif row["mechanical_finding_drove_change"]:
                cls = "tool_or_trigger_lift"
            else:
                cls = "deliberation_lift" if delta >= 5 else "no_material_lift"
        classes.append({"fixture": row["fixture"], "class": cls,
                        "pair_eligible": fx in set(manifest["fixtures_pair_eligible"])})
    return {
        "gate": "7-attribution",
        "data_only": True,
        "status": "DATA",
        "classes": classes,
    }


def gate_8_artifact_contract(rows: list[dict]) -> dict:
    failures = []
    for row in rows:
        # If pair fired (forced arm has pair_judge present) but artifact missing
        if row["pair_fired"] and not row["pair_findings_distinguishable"]:
            failures.append({"fixture": row["fixture"],
                             "missing": "pair_judge_findings_distinguishable"})
    return {
        "gate": "8-artifact-contract",
        "status": "PASS" if not failures else "FAIL",
        "rule": "pair_judge non-null when fired; pair findings distinguishable from solo",
        "failures": failures,
    }


def build_rows(results_dir: Path, work_dir_root: Path, run_id: str) -> list[dict]:
    fixtures = find_results_dir_fixtures(results_dir)
    rows = []
    for fx in fixtures:
        judge = load_judge(results_dir, fx)
        solo_r = load_result(results_dir, fx, "solo_claude")
        gated_r = load_result(results_dir, fx, "l2_gated")
        forced_r = load_result(results_dir, fx, "l2_forced")
        gated_state = load_state(work_dir_root, run_id, fx, "l2_gated")
        forced_state = load_state(work_dir_root, run_id, fx, "l2_forced")

        def pair_judge_present(state: dict | None) -> bool:
            if not state:
                return False
            phases = state.get("phases") or {}
            verify = phases.get("verify") or {}
            sub = verify.get("sub_verdicts") or {}
            return sub.get("pair_judge") is not None

        # Pair findings distinguishability — checked from archive of whichever
        # arm fired pair-mode. l2_forced always fires (when present); l2_gated
        # only on natural triggers. Use l2_forced as the audit anchor when
        # available; fall back to l2_gated.
        pair_anchor_arm = "l2_forced" if forced_state else (
            "l2_gated" if gated_state else None
        )
        pair_findings_ok = (
            pair_findings_distinguishable(work_dir_root, run_id, fx, pair_anchor_arm)
            if pair_anchor_arm else False
        )
        rows.append({
            "fixture": fx,
            "solo_score": get_score(judge, "solo_claude"),
            "l2_gated_score": get_score(judge, "l2_gated"),
            "l2_forced_score": get_score(judge, "l2_forced"),
            "solo_dq": get_disqualifier(judge, "solo_claude"),
            "l2_gated_dq": get_disqualifier(judge, "l2_gated"),
            "l2_forced_dq": get_disqualifier(judge, "l2_forced"),
            "solo_wall": (solo_r or {}).get("elapsed_seconds"),
            "l2_gated_wall": (gated_r or {}).get("elapsed_seconds"),
            "solo_timeout": bool((solo_r or {}).get("timed_out")),
            "l2_gated_timeout": bool((gated_r or {}).get("timed_out")),
            "l2_gated_pair_judge_present": pair_judge_present(gated_state),
            "l2_forced_pair_judge_present": pair_judge_present(forced_state),
            "pair_fired": pair_judge_present(gated_state) or pair_judge_present(forced_state),
            "pair_findings_distinguishable": pair_findings_ok,
            "impl_confounded": impl_confounded_for_fixture(results_dir, fx),
            # Below remain conservative defaults — populating them needs cross-
            # finding diffs (verify.findings.jsonl from each pair-judge file)
            # that are out of scope for this iter's compare script. Recorded
            # as TODO for follow-up; iter-0033c attribution downgrades fixtures
            # with these defaults to no_material_lift unless the score delta
            # itself is ≥+5 (then deliberation_lift), so the conservative
            # default never inflates the count.
            "pair_judge_unique_finding": False,
            "mechanical_finding_drove_change": False,
        })
    return rows


def render_markdown(gates: list[dict], rows: list[dict]) -> str:
    lines = ["# iter-0033c gate table\n"]
    lines.append("| fixture | solo | l2_gated | Δ | l2_forced | l2g pair? | l2f pair? | wall_ratio |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rows:
        delta = (
            r["l2_gated_score"] - r["solo_score"]
            if r["l2_gated_score"] is not None and r["solo_score"] is not None
            else None
        )
        ratio = (
            round(r["l2_gated_wall"] / r["solo_wall"], 2)
            if r["l2_gated_wall"] is not None and r["solo_wall"]
            else None
        )
        lines.append(
            f"| {r['fixture']} | {r['solo_score']} | {r['l2_gated_score']} | "
            f"{('+' if delta and delta > 0 else '') + str(delta) if delta is not None else '-'} | "
            f"{r['l2_forced_score']} | "
            f"{'✓' if r['l2_gated_pair_judge_present'] else '✗'} | "
            f"{'✓' if r['l2_forced_pair_judge_present'] else '✗'} | "
            f"{ratio if ratio is not None else '-'} |"
        )
    lines.append("\n## Gates\n")
    for g in gates:
        ship = " (SHIP-BLOCKER)" if g.get("ship_blocker") else ""
        lines.append(f"- **{g['gate']}{ship}**: {g['status']} — {g.get('rule', '')}")
        if g.get("failures"):
            for f in g["failures"]:
                lines.append(f"  - FAIL: {f}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--work-dir-root", default="/tmp",
                    help="parent dir of bench-* WORK_DIRs (default: /tmp)")
    ap.add_argument("--run-id", required=True,
                    help="benchmark run id used by run-fixture.sh (matches WORK_DIR prefix)")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    rows = build_rows(Path(args.results_dir), Path(args.work_dir_root), args.run_id)

    gates = [
        gate_2_no_regression(rows),
        gate_3_lift(rows, manifest),
        gate_4_hard_floor(rows, Path(args.work_dir_root), args.run_id),
        gate_5_efficiency(rows),
        gate_6_trigger_discipline(rows, manifest),
        gate_7_attribution(rows, manifest),
        gate_8_artifact_contract(rows),
    ]

    out = {
        "iter": "0033c",
        "manifest_sha256": manifest["manifest_sha256"],
        "manifest_head": manifest.get("head"),
        "rows": rows,
        "gates": gates,
        "ship_blockers_failed": [g["gate"] for g in gates
                                  if g.get("ship_blocker") and g["status"] == "FAIL"],
        "quality_gates_failed": [g["gate"] for g in gates
                                  if not g.get("ship_blocker") and g["status"] == "FAIL"],
    }
    Path(args.out_json).write_text(json.dumps(out, indent=2) + "\n")
    Path(args.out_md).write_text(render_markdown(gates, rows))

    print(f"[compare] gates -> {args.out_json}")
    print(f"[compare] markdown -> {args.out_md}")
    failed = out["ship_blockers_failed"]
    if failed:
        print(f"[compare] SHIP-BLOCKER FAIL: {failed}")
        return 1
    print("[compare] all ship-blockers PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
