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
        judge = json.loads(judge_path.read_text())
        # iter-0019: 3-arm aware. judge.json now carries scores_by_arm /
        # findings_by_arm / disqualifiers_by_arm / margins. Older judge.json
        # (pre-iter-0019, only variant_score + bare_score) is handled by
        # falling back to legacy fields.
        scores_by_arm = judge.get("scores_by_arm") or {}
        if not scores_by_arm:
            if "variant_score" in judge:
                scores_by_arm["variant"] = judge["variant_score"]
            if "bare_score" in judge:
                scores_by_arm["bare"] = judge["bare_score"]

        findings_by_arm = judge.get("findings_by_arm") or {}
        dq_by_arm = judge.get("disqualifiers_by_arm") or {}
        margins = judge.get("margins") or {}

        arm_results = {}
        for arm in ("variant", "solo_claude", "bare"):
            res_p = fdir / arm / "result.json"
            arm_results[arm] = json.loads(res_p.read_text()) if res_p.exists() else {}
        var_res = arm_results["variant"]
        solo_res = arm_results["solo_claude"]
        bare_res = arm_results["bare"]

        meta_p = bench_root / "fixtures" / fid / "metadata.json"
        category = "unknown"
        if meta_p.exists():
            try:
                category = json.loads(meta_p.read_text()).get("category", "unknown")
            except Exception:
                pass

        def wall_ratio(numer, denom):
            if numer and denom:
                return round(numer / denom, 2)
            return None

        # Disqualifier flags per arm = OR of deterministic result.json flag and
        # judge's subjective flag (from new dq_by_arm map; fall back to legacy
        # A/B-letter shape if present).
        def arm_dq_judge(arm: str):
            if arm in dq_by_arm:
                return bool(dq_by_arm[arm].get("disqualifier", False))
            mapping = judge.get("_blind_mapping", {}) or {}
            for letter in ("A", "B", "C"):
                if mapping.get(letter) == arm:
                    return bool((judge.get("disqualifiers", {}) or {}).get(letter, False))
            return False

        # Per-arm payload — arm absent = scores_by_arm key absent, downstream
        # consumers null-check.
        arms_block = {}
        for arm in ("variant", "solo_claude", "bare"):
            r = arm_results.get(arm) or {}
            score = scores_by_arm.get(arm)
            judge_dq = arm_dq_judge(arm)
            det_dq = bool(r.get("disqualifier", False))
            arms_block[arm] = {
                "score": score,
                "wall_s": r.get("elapsed_seconds"),
                "verify_score": r.get("verify_score"),
                "files_changed": r.get("files_changed"),
                "timed_out": bool(r.get("timed_out", False)),
                "disqualifier": judge_dq or det_dq,
                "dq_judge": judge_dq,
                "dq_deterministic": det_dq,
                "critical_findings": findings_by_arm.get(arm, []) if findings_by_arm else [],
            }

        # Pairwise margins. Prefer judge-side margins (single calibrated
        # scoring) over arithmetic differences, but fall through to compute
        # from scores_by_arm if the judge didn't emit margins.
        def m(left, right, key):
            if margins.get(key) is not None:
                return margins[key]
            l = scores_by_arm.get(left); r2 = scores_by_arm.get(right)
            if l is None or r2 is None:
                return None
            return l - r2

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
            "winner": judge.get("winner_arm"),
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
    disqualifier_count = sum(1 for r in scored if r.get("variant_disqualifier"))

    # arm-presence flags so consumers know whether the iter is 2-arm legacy
    # or 3-arm post-iter-0019.
    has_solo = any((r.get("arms", {}).get("solo_claude") or {}).get("score") is not None for r in scored)

    summary = {
        "run_id": args.run_id,
        "label": args.label,
        "git_sha": git_sha(),
        "branch": git_branch(),
        "completed_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
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
        "| Fixture | Category | L2 (variant) | L1 (solo_claude) | L0 (bare) | L2-L0 | L1-L0 | L2-L1 | Winner | Wall L2/L1/L0 | Wall L2/L0 |",
        "|---------|----------|--------------|------------------|-----------|-------|-------|-------|--------|---------------|-----------|",
    ]
    for r in rows:
        if r.get("variant_score") is None:
            lines.append(f"| {r['fixture']} | — | — | — | — | — | — | — | NO_JUDGE | — | — |")
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
        wall_triplet = f"{fmt_wall(v)}/{fmt_wall(s)}/{fmt_wall(b)}"
        lines.append(
            f"| {r['fixture']} | {r['category']} | {fmt_score(v)} | {fmt_score(s)} | {fmt_score(b)} | "
            f"{fmt_margin(margins.get('variant_over_bare'))} | {fmt_margin(margins.get('solo_over_bare'))} | "
            f"{fmt_margin(margins.get('variant_over_solo'))} | {r.get('winner') or '—'} | {wall_triplet} | {l2_l0_wall} |"
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
        f"**L2 vs L0 margin avg:** {margin_avg_str}   (ship floor: +5, NORTH-STAR preferred: +8)",
    ]
    if summary.get("arms_present", {}).get("solo_claude"):
        ms = summary.get("margins_avg", {}) or {}
        ws = summary.get("wall_ratio_avg_by_pair", {}) or {}
        lines += [
            f"**L1 vs L0 margin avg:** {fmt_signed(ms.get('solo_over_bare'))}   (NORTH-STAR L1 contract: ≥+5)",
            f"**L2 vs L1 margin avg:** {fmt_signed(ms.get('variant_over_solo'))}   (NORTH-STAR L2 contract: ≥+5 on pair-eligible)",
            f"**Wall ratio L2/L0:** {fmt_ratio(ws.get('variant_over_bare'))}",
            f"**Wall ratio L1/L0:** {fmt_ratio(ws.get('solo_over_bare'))}",
            f"**Wall ratio L2/L1:** {fmt_ratio(ws.get('variant_over_solo'))}",
        ]
    else:
        lines.append(f"**Wall ratio variant/bare (mean):** {wall_ratio_str}   (no solo_claude arm in this run)")
    lines += [
        f"**Hard-floor violations:**       {summary['hard_floor_violations']}",
        f"**Fixtures with margin ≥ +5:**   {summary['margin_ge_5_count']} / {summary['gated_fixtures']} (gate: ≥ 7 of 9)",
    ]
    # Critical findings digest — per-arm sections.
    def has_findings(arm):
        return bool((arm or {}).get("critical_findings"))
    cf_rows = [r for r in rows if any(has_findings((r.get("arms") or {}).get(a)) for a in ("variant", "solo_claude", "bare"))]
    if cf_rows:
        lines += ["", "## Critical Findings", ""]
        for r in cf_rows:
            lines.append(f"### {r['fixture']}")
            for arm_label, arm_key in [("Variant (L2)", "variant"), ("Solo Claude (L1)", "solo_claude"), ("Bare (L0)", "bare")]:
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
