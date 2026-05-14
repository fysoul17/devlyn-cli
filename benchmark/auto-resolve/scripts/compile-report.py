#!/usr/bin/env python3
"""
compile-report.py — aggregate one run's fixture artifacts into a summary.

Usage:
    compile-report.py --run-id <ID> [--label <VERSION>]

Reads: benchmark/auto-resolve/results/<run-id>/<fixture>/{judge.json, variant/result.json, bare/result.json}
Writes:
    results/<run-id>/summary.json  (machine)
    results/<run-id>/report.md     (human)

The report is the output of `npx devlyn-cli benchmark`. Ship-gate.py consumes summary.json.
"""
from __future__ import annotations
import argparse, json, pathlib, sys, subprocess, datetime

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import is_score, is_strict_number, loads_strict_json_object

KNOWN_ARMS = {"variant", "solo_claude", "bare"}
PASS_VERDICTS = {"PASS", "PASS_WITH_ISSUES"}


def verify_score_clean(value) -> bool:
    return is_strict_number(value) and value >= 1.0


def exact_bool(value):
    if value is True or value is False:
        return value
    if value is None:
        return False
    return None


def skill_verdict_clean(result: dict, arm: str) -> bool:
    if arm == "bare":
        return True
    return (
        result.get("terminal_verdict") in PASS_VERDICTS
        and result.get("verify_verdict") in PASS_VERDICTS
    )


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_dict_json(path: pathlib.Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = loads_strict_json_object(path.read_text())
    except (ValueError, json.JSONDecodeError):
        return {}
    return data


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def git_branch() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def axis_validation_breakdown(judge: dict):
    raw_validation = judge.get("_axis_validation")
    validation = raw_validation if isinstance(raw_validation, dict) else {}
    cells = validation.get("out_of_range_cells") or []
    declared_count = validation.get("out_of_range_count")
    total_invalid = max(
        declared_count if isinstance(declared_count, int) else 0,
        len(cells) if isinstance(cells, list) else 0,
    )
    raw_blind_mapping = judge.get("_blind_mapping")
    blind_mapping = raw_blind_mapping if isinstance(raw_blind_mapping, dict) else {}
    breakdown_to_letter = {
        "a_breakdown": "A",
        "b_breakdown": "B",
        "c_breakdown": "C",
    }
    by_arm = {}
    mapped_count = 0
    unmapped_cells = []
    if not isinstance(cells, list):
        return by_arm, total_invalid, [{"reason": "out_of_range_cells is not a list"}]
    for cell in cells:
        if not isinstance(cell, dict):
            unmapped_cells.append(cell)
            continue
        letter = breakdown_to_letter.get(cell.get("breakdown"))
        arm = blind_mapping.get(letter) if letter else None
        if arm in KNOWN_ARMS:
            by_arm.setdefault(arm, []).append(cell)
            mapped_count += 1
        else:
            unmapped_cells.append(cell)
    unmapped_count = max(0, total_invalid - mapped_count)
    if unmapped_count > len(unmapped_cells):
        unmapped_cells.extend(
            {"reason": "out_of_range_count exceeds mapped cells"}
            for _ in range(unmapped_count - len(unmapped_cells))
        )
    return by_arm, unmapped_count, unmapped_cells


def blind_mapped_arms(judge: dict) -> set[str]:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return set()
    return {arm for key, arm in mapping.items() if key in {"A", "B", "C"}}


def strict_number(value):
    return value if is_strict_number(value) else None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True)
    p.add_argument("--label", default=None, help="version label, e.g. v3.6")
    args = p.parse_args()

    bench_root = pathlib.Path(__file__).resolve().parent.parent
    res_root = bench_root / "results" / args.run_id
    if not res_root.is_dir():
        print(f"no results dir: {res_root}", file=sys.stderr); return 1

    fixtures = sorted([d.name for d in res_root.iterdir() if d.is_dir()])
    rows = []
    for fid in fixtures:
        fdir = res_root / fid
        judge_path = fdir / "judge.json"
        if not judge_path.exists():
            rows.append({"fixture": fid, "status": "NO_JUDGE", "reason": "judge.json missing"})
            continue
        judge = load_dict_json(judge_path)
        # iter-0019: 3-arm aware. judge.json now carries scores_by_arm /
        # findings_by_arm / disqualifiers_by_arm / margins. Older judge.json
        # can populate legacy fields, but any score still requires a matching
        # _blind_mapping arm before downstream consumers may trust it.
        raw_scores_by_arm = judge.get("scores_by_arm")
        scores_by_arm = raw_scores_by_arm if isinstance(raw_scores_by_arm, dict) else {}
        if not scores_by_arm:
            if is_score(judge.get("variant_score")):
                scores_by_arm["variant"] = judge["variant_score"]
            if is_score(judge.get("bare_score")):
                scores_by_arm["bare"] = judge["bare_score"]

        raw_findings_by_arm = judge.get("findings_by_arm")
        findings_by_arm = raw_findings_by_arm if isinstance(raw_findings_by_arm, dict) else {}
        raw_dq_by_arm = judge.get("disqualifiers_by_arm")
        dq_by_arm = raw_dq_by_arm if isinstance(raw_dq_by_arm, dict) else {}
        axis_invalid_by_arm, axis_unmapped_count, axis_unmapped_cells = axis_validation_breakdown(judge)
        mapped_arms = blind_mapped_arms(judge)
        trusted_scores_by_arm = {
            arm: score for arm, score in scores_by_arm.items()
            if arm in mapped_arms and is_score(score)
        }

        arm_results = {}
        for arm in ("variant", "solo_claude", "bare"):
            res_p = fdir / arm / "result.json"
            arm_results[arm] = load_dict_json(res_p)
        var_res = arm_results["variant"]
        solo_res = arm_results["solo_claude"]
        bare_res = arm_results["bare"]

        meta_p = bench_root / "fixtures" / fid / "metadata.json"
        category = "unknown"
        if meta_p.exists():
            try:
                category = load_dict_json(meta_p).get("category", "unknown")
            except Exception:
                pass

        def wall_ratio(numer, denom):
            if is_strict_number(numer) and is_strict_number(denom):
                return round(numer / denom, 2)
            return None

        # Disqualifier flags per arm = OR of deterministic result.json flag and
        # judge's subjective flag (from new dq_by_arm map; fall back to legacy
        # A/B-letter shape if present).
        def arm_dq_judge(arm: str):
            if arm in dq_by_arm:
                entry = dq_by_arm[arm]
                value = entry.get("disqualifier") if isinstance(entry, dict) else entry
                parsed = exact_bool(value)
                return (parsed is True or parsed is None, parsed is None)
            raw_mapping = judge.get("_blind_mapping")
            mapping = raw_mapping if isinstance(raw_mapping, dict) else {}
            for letter in ("A", "B", "C"):
                if mapping.get(letter) == arm:
                    raw_dqs = judge.get("disqualifiers")
                    dqs = raw_dqs if isinstance(raw_dqs, dict) else {}
                    parsed = exact_bool(dqs.get(letter))
                    return (parsed is True or parsed is None, parsed is None)
            return False, False

        def critical_findings_for(arm: str):
            entry = findings_by_arm.get(arm)
            if isinstance(entry, list):
                return entry
            if entry:
                return [entry]
            return []

        # Per-arm payload — arm absent = scores_by_arm key absent, downstream
        # consumers null-check.
        arms_block = {}
        for arm in ("variant", "solo_claude", "bare"):
            r = arm_results.get(arm) or {}
            raw_score = scores_by_arm.get(arm)
            score = trusted_scores_by_arm.get(arm)
            blind_mapping_arm_missing = raw_score is not None and arm not in mapped_arms
            judge_dq, judge_dq_malformed = arm_dq_judge(arm)
            result_bool_values = {
                field: exact_bool(r.get(field))
                for field in ("disqualifier", "timed_out", "invoke_failure", "environment_contamination")
            }
            malformed_boolean_fields = [
                field for field, value in result_bool_values.items() if value is None
            ]
            det_dq = bool(
                result_bool_values["disqualifier"] is True
                or result_bool_values["timed_out"] is True
                or result_bool_values["invoke_failure"] is True
                or result_bool_values["environment_contamination"] is True
                or bool(malformed_boolean_fields)
                or not verify_score_clean(r.get("verify_score"))
                or not skill_verdict_clean(r, arm)
                or blind_mapping_arm_missing
            )
            arms_block[arm] = {
                "score": score,
                "wall_s": strict_number(r.get("elapsed_seconds")),
                "verify_score": strict_number(r.get("verify_score")),
                "files_changed": r.get("files_changed"),
                "timed_out": result_bool_values["timed_out"] is True,
                "invoke_failure": result_bool_values["invoke_failure"] is True,
                "invoke_failure_reason": r.get("invoke_failure_reason"),
                "environment_contamination": result_bool_values["environment_contamination"] is True,
                "disqualifier": judge_dq or det_dq,
                "dq_judge": judge_dq,
                "dq_judge_malformed": judge_dq_malformed,
                "dq_deterministic": det_dq,
                "malformed_boolean_fields": malformed_boolean_fields,
                "blind_mapping_arm_missing": blind_mapping_arm_missing,
                "critical_findings": critical_findings_for(arm),
                "_axis_validation_out_of_range_count": len(axis_invalid_by_arm.get(arm, [])),
                "_axis_validation_out_of_range_cells": axis_invalid_by_arm.get(arm, []),
            }

        # Pairwise margins are derived from trusted mapped scores only. Cached
        # judge-side margins are redundant and can be stale if a partial artifact
        # is reused.
        def m(left, right, key):
            if left not in mapped_arms or right not in mapped_arms:
                return None
            l = trusted_scores_by_arm.get(left); r2 = trusted_scores_by_arm.get(right)
            if l is None or r2 is None:
                return None
            return l - r2

        def trusted_winner():
            winner = judge.get("winner_arm")
            if winner == "tie":
                return winner
            if winner in trusted_scores_by_arm:
                return winner
            return None

        row = {
            "fixture": fid,
            "category": category,
            "arms": arms_block,
            # Pairwise margins (positive = first arm beat second).
            "margins": {
                "variant_over_bare": m("variant", "bare", "variant_over_bare"),
                "solo_over_bare":    m("solo_claude", "bare", "solo_over_bare"),
                "variant_over_solo": m("variant", "solo_claude", "variant_over_solo"),
            },
            # Wall ratios per pairwise comparison (NORTH-STAR.md tests #2/#7
            # generalized): each layer must beat previous-layer-best-of-N.
            "wall_ratios": {
                "variant_over_bare": wall_ratio(arms_block["variant"]["wall_s"], arms_block["bare"]["wall_s"]),
                "solo_over_bare":    wall_ratio(arms_block["solo_claude"]["wall_s"], arms_block["bare"]["wall_s"]),
                "variant_over_solo": wall_ratio(arms_block["variant"]["wall_s"], arms_block["solo_claude"]["wall_s"]),
            },
            "winner": trusted_winner(),
            "_axis_validation_unmapped_out_of_range_count": axis_unmapped_count,
            "_axis_validation_unmapped_out_of_range_cells": axis_unmapped_cells,
            # Legacy fields preserved so older summary readers still parse.
            "variant_score": arms_block["variant"]["score"],
            "bare_score": arms_block["bare"]["score"],
            "margin": m("variant", "bare", "variant_over_bare"),
            "variant_disqualifier": arms_block["variant"]["disqualifier"],
            "variant_dq_judge": arms_block["variant"]["dq_judge"],
            "variant_dq_deterministic": arms_block["variant"]["dq_deterministic"],
            "variant_wall_s": arms_block["variant"]["wall_s"],
            "bare_wall_s": arms_block["bare"]["wall_s"],
            "wall_ratio_variant_over_bare": wall_ratio(
                arms_block["variant"]["wall_s"], arms_block["bare"]["wall_s"]),
            "variant_verify_score": arms_block["variant"]["verify_score"],
            "bare_verify_score": arms_block["bare"]["verify_score"],
            "variant_files_changed": arms_block["variant"]["files_changed"],
            "bare_files_changed": arms_block["bare"]["files_changed"],
            "critical_findings_variant": arms_block["variant"]["critical_findings"],
            "critical_findings_bare": arms_block["bare"]["critical_findings"],
        }
        rows.append(row)

    # Aggregate
    scored = [r for r in rows if r.get("variant_score") is not None]
    excluded_known_limit = [r for r in scored if r.get("category") == "edge"]  # F8 and similar
    gated_rows = [r for r in scored if r.get("category") != "edge"]

    def avg(values):
        vals = [v for v in values if v is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    # iter-0019: per-arm averages (whichever arms ran).
    arm_avg = {}
    for arm in ("variant", "solo_claude", "bare"):
        arm_avg[arm] = avg([(r.get("arms", {}).get(arm) or {}).get("score") for r in scored])

    # Pairwise margin averages (positive = first arm wins on average).
    def margin_avg(key):
        return avg([(r.get("margins") or {}).get(key) for r in scored])

    margins_avg = {
        "variant_over_bare":   margin_avg("variant_over_bare"),
        "solo_over_bare":      margin_avg("solo_over_bare"),
        "variant_over_solo":   margin_avg("variant_over_solo"),
    }
    # Pairwise wall-ratio averages.
    def wall_avg(key):
        return avg([(r.get("wall_ratios") or {}).get(key) for r in scored])

    wall_ratio_avg_by_pair = {
        "variant_over_bare":   wall_avg("variant_over_bare"),
        "solo_over_bare":      wall_avg("solo_over_bare"),
        "variant_over_solo":   wall_avg("variant_over_solo"),
    }

    # margin_ge_5_count over the iter-0018-era variant-vs-bare metric,
    # because the legacy ship-gate.py reads that. Pair-aware gates get
    # added in iter-0021 / 0022 once the data shape stabilizes.
    margin_ge_5 = sum(1 for r in gated_rows if (r.get("margin") or 0) >= 5)
    disqualifier_count = sum(1 for r in rows if r.get("variant_disqualifier"))

    # arm-presence flags so consumers know whether the iter is 2-arm legacy
    # or 3-arm post-iter-0019.
    has_solo = any(
        (arm := (r.get("arms", {}).get("solo_claude") or {})).get("score") is not None
        or arm.get("wall_s") is not None
        or bool(arm.get("disqualifier"))
        for r in rows
    )

    summary = {
        "run_id": args.run_id,
        "label": args.label,
        "git_sha": git_sha(),
        "branch": git_branch(),
        "completed_at": utc_now_iso(),
        "fixtures_total": len(rows),
        "fixtures_scored": len(scored),
        # Legacy 2-arm fields kept for ship-gate.py + history readers.
        "variant_avg": arm_avg.get("variant"),
        "bare_avg": arm_avg.get("bare"),
        "margin_avg": margins_avg.get("variant_over_bare"),
        "hard_floor_violations": disqualifier_count,
        "margin_ge_5_count": margin_ge_5,
        "gated_fixtures": len(gated_rows),
        "known_limit_fixtures": len(excluded_known_limit),
        "wall_ratio_variant_over_bare_avg": wall_ratio_avg_by_pair.get("variant_over_bare"),
        # iter-0019 — 3-arm aware aggregates.
        "arms_present": {"variant": True, "solo_claude": has_solo, "bare": True},
        "scores_avg_by_arm": arm_avg,
        "margins_avg": margins_avg,
        "wall_ratio_avg_by_pair": wall_ratio_avg_by_pair,
        "rows": rows,
    }
    (res_root / "summary.json").write_text(json.dumps(summary, indent=2))

    # Render human-readable report
    lines = [
        f"# Benchmark Suite Run — {summary['completed_at']}",
        "",
        f"Run-id: `{args.run_id}`",
        f"Label: `{args.label or '(unlabeled)'}`",
        f"Branch: `{summary['branch']}`",
        f"Git SHA: `{summary['git_sha'][:12]}`",
        "",
        "| Fixture | Category | variant (L2) | solo_claude (L1) | bare (L0) | variant-bare | solo_claude-bare | variant-solo_claude | Winner | Wall variant/solo_claude/bare | Wall variant/solo_claude | Wall variant/bare |",
        "|---------|----------|--------------|------------------|-----------|--------------|-------------------|----------------------|--------|--------------------------------|--------------------------|-------------------|",
    ]
    for r in rows:
        if r.get("variant_score") is None:
            lines.append(f"| {r['fixture']} | — | — | — | — | — | — | — | NO_JUDGE | — | — | — |")
            continue
        arms = r.get("arms", {}) or {}
        v = arms.get("variant", {}) or {}
        s = arms.get("solo_claude", {}) or {}
        b = arms.get("bare", {}) or {}
        margins = r.get("margins", {}) or {}
        wallr = r.get("wall_ratios", {}) or {}
        def fmt_score(arm):
            if arm.get("score") is None:
                return "—"
            tag = " ⚠DQ" if arm.get("disqualifier") else (" ⏱TO" if arm.get("timed_out") else "")
            return f"{arm['score']}{tag}"
        def fmt_margin(v): return f"{v:+d}" if isinstance(v, int) else "—"
        def fmt_wall(arm):
            return f"{arm['wall_s']}s" if arm.get("wall_s") else "?"
        l2_l0_wall = f"{wallr.get('variant_over_bare'):.1f}x" if wallr.get("variant_over_bare") else "—"
        l2_l1_wall = f"{wallr.get('variant_over_solo'):.1f}x" if wallr.get("variant_over_solo") else "—"
        wall_triplet = f"{fmt_wall(v)}/{fmt_wall(s)}/{fmt_wall(b)}"
        lines.append(
            f"| {r['fixture']} | {r['category']} | {fmt_score(v)} | {fmt_score(s)} | {fmt_score(b)} | "
            f"{fmt_margin(margins.get('variant_over_bare'))} | {fmt_margin(margins.get('solo_over_bare'))} | "
            f"{fmt_margin(margins.get('variant_over_solo'))} | {r.get('winner') or '—'} | "
            f"{wall_triplet} | {l2_l1_wall} | {l2_l0_wall} |"
        )
    def fmt_avg(v): return f"{v:.1f}" if isinstance(v, (int, float)) else "n/a"
    def fmt_signed(v): return f"{v:+.1f}" if isinstance(v, (int, float)) else "n/a"
    def fmt_ratio(v): return f"{v:.1f}x" if isinstance(v, (int, float)) else "n/a"
    margin_avg_val = summary.get("margin_avg")
    margin_avg_str = fmt_signed(margin_avg_val)
    wall_ratio_str = fmt_ratio(summary.get("wall_ratio_variant_over_bare_avg"))

    lines += [
        "",
        f"**Suite average variant (L2) score:**     {fmt_avg(summary['variant_avg'])}",
    ]
    if summary.get("arms_present", {}).get("solo_claude"):
        lines.append(f"**Suite average solo_claude (L1) score:** {fmt_avg(summary['scores_avg_by_arm'].get('solo_claude'))}")
    lines += [
        f"**Suite average bare (L0) score:**         {fmt_avg(summary['bare_avg'])}",
        "",
        f"**variant (L2) vs bare (L0) margin avg:** {margin_avg_str}   (ship floor: +5, NORTH-STAR preferred: +8)",
    ]
    if summary.get("arms_present", {}).get("solo_claude"):
        ms = summary.get("margins_avg", {}) or {}
        ws = summary.get("wall_ratio_avg_by_pair", {}) or {}
        lines += [
            f"**solo_claude (L1) vs bare (L0) margin avg:** {fmt_signed(ms.get('solo_over_bare'))}   (NORTH-STAR L1 contract: ≥+5)",
            f"**variant (L2) vs solo_claude (L1) margin avg:** {fmt_signed(ms.get('variant_over_solo'))}   (NORTH-STAR L2 contract: ≥+5 on pair-eligible)",
            f"**Wall ratio variant (L2) / bare (L0):** {fmt_ratio(ws.get('variant_over_bare'))}",
            f"**Wall ratio solo_claude (L1) / bare (L0):** {fmt_ratio(ws.get('solo_over_bare'))}",
            f"**Wall ratio variant (L2) / solo_claude (L1):** {fmt_ratio(ws.get('variant_over_solo'))}",
        ]
    else:
        lines.append(f"**Wall ratio variant (L2) / bare (L0) mean:** {wall_ratio_str}   (no solo_claude arm in this run)")
    lines += [
        f"**Hard-floor violations:**       {summary['hard_floor_violations']}",
        f"**Fixtures with margin ≥ +5:**   {summary['margin_ge_5_count']} / {summary['gated_fixtures']} (gate: ≥ 7)",
    ]
    # Critical findings digest — per-arm sections.
    def has_findings(arm):
        return bool((arm or {}).get("critical_findings"))
    cf_rows = [r for r in rows if any(has_findings((r.get("arms") or {}).get(a)) for a in ("variant", "solo_claude", "bare"))]
    if cf_rows:
        lines += ["", "## Critical Findings", ""]
        for r in cf_rows:
            lines.append(f"### {r['fixture']}")
            for arm_label, arm_key in [("variant (L2)", "variant"), ("solo_claude (L1)", "solo_claude"), ("bare (L0)", "bare")]:
                arm = (r.get("arms") or {}).get(arm_key) or {}
                if has_findings(arm):
                    lines.append(f"**{arm_label}:**")
                    for f in arm["critical_findings"]:
                        lines.append(f"- {f}")
            lines.append("")
    (res_root / "report.md").write_text("\n".join(lines))
    print((res_root / "report.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
