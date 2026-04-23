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
        var_res_p = fdir / "variant" / "result.json"
        bare_res_p = fdir / "bare" / "result.json"
        var_res = json.loads(var_res_p.read_text()) if var_res_p.exists() else {}
        bare_res = json.loads(bare_res_p.read_text()) if bare_res_p.exists() else {}

        # Determine category-specific gate (from fixture metadata)
        meta_p = bench_root / "fixtures" / fid / "metadata.json"
        category = "unknown"
        if meta_p.exists():
            try:
                category = json.loads(meta_p.read_text()).get("category", "unknown")
            except Exception:
                pass

        # Disqualifier = OR of deterministic result.json flag (computed by
        # run-fixture.sh from verify.json) and the judge's subjective flag.
        # The deterministic check is source of truth; the judge's is a second
        # opinion that can catch misses the regex couldn't express.
        variant_dq_judge = judge.get("disqualifiers", {}).get(
            "A" if judge.get("_blind_mapping", {}).get("A") == "variant" else "B", False
        )
        variant_dq_deterministic = bool(var_res.get("disqualifier", False))
        row = {
            "fixture": fid,
            "category": category,
            "variant_score": judge.get("variant_score"),
            "bare_score": judge.get("bare_score"),
            "margin": judge.get("margin"),
            "winner": judge.get("winner_arm"),
            "variant_disqualifier": variant_dq_judge or variant_dq_deterministic,
            "variant_dq_judge": variant_dq_judge,
            "variant_dq_deterministic": variant_dq_deterministic,
            "variant_wall_s": var_res.get("elapsed_seconds"),
            "bare_wall_s": bare_res.get("elapsed_seconds"),
            "variant_verify_score": var_res.get("verify_score"),
            "bare_verify_score": bare_res.get("verify_score"),
            "variant_files_changed": var_res.get("files_changed"),
            "bare_files_changed": bare_res.get("files_changed"),
            "critical_findings_variant": judge.get("critical_findings", {}).get(
                "A" if judge.get("_blind_mapping", {}).get("A") == "variant" else "B", []),
            "critical_findings_bare": judge.get("critical_findings", {}).get(
                "A" if judge.get("_blind_mapping", {}).get("A") == "bare" else "B", []),
        }
        rows.append(row)

    # Aggregate
    scored = [r for r in rows if r.get("variant_score") is not None]
    excluded_known_limit = [r for r in scored if r.get("category") == "edge"]  # F8 and similar
    gated_rows = [r for r in scored if r.get("category") != "edge"]
    variant_avg = sum(r["variant_score"] for r in scored) / max(len(scored), 1) if scored else 0
    bare_avg = sum(r["bare_score"] for r in scored) / max(len(scored), 1) if scored else 0
    margin_avg = variant_avg - bare_avg
    disqualifier_count = sum(1 for r in scored if r.get("variant_disqualifier"))
    margin_ge_5 = sum(1 for r in gated_rows if (r.get("margin") or 0) >= 5)

    summary = {
        "run_id": args.run_id,
        "label": args.label,
        "git_sha": git_sha(),
        "branch": git_branch(),
        "completed_at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "fixtures_total": len(rows),
        "fixtures_scored": len(scored),
        "variant_avg": round(variant_avg, 1),
        "bare_avg": round(bare_avg, 1),
        "margin_avg": round(margin_avg, 1),
        "hard_floor_violations": disqualifier_count,
        "margin_ge_5_count": margin_ge_5,
        "gated_fixtures": len(gated_rows),
        "known_limit_fixtures": len(excluded_known_limit),
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
        "| Fixture | Category | Variant | Bare | Margin | Winner | Verify (V/B) | Wall (V/B) |",
        "|---------|----------|---------|------|--------|--------|--------------|------------|",
    ]
    for r in rows:
        if r.get("variant_score") is None:
            lines.append(f"| {r['fixture']} | — | — | — | — | NO_JUDGE | — | — |")
            continue
        vverif = f"{int((r['variant_verify_score'] or 0)*100)}%"
        bverif = f"{int((r['bare_verify_score'] or 0)*100)}%"
        vwall = f"{r['variant_wall_s']}s" if r['variant_wall_s'] else "?"
        bwall = f"{r['bare_wall_s']}s" if r['bare_wall_s'] else "?"
        dq = " ⚠DQ" if r.get("variant_disqualifier") else ""
        lines.append(
            f"| {r['fixture']} | {r['category']} | {r['variant_score']}{dq} | {r['bare_score']} | "
            f"{r['margin']:+d} | {r['winner']} | {vverif}/{bverif} | {vwall}/{bwall} |"
        )
    lines += [
        "",
        f"**Suite average variant score:** {summary['variant_avg']}",
        f"**Suite average bare score:**    {summary['bare_avg']}",
        f"**Suite average margin:**        {summary['margin_avg']:+.1f}   (ship floor: +5)",
        f"**Hard-floor violations:**       {summary['hard_floor_violations']}",
        f"**Fixtures with margin ≥ +5:**   {summary['margin_ge_5_count']} / {summary['gated_fixtures']} (gate: ≥ 7 of 9)",
    ]
    # Critical findings digest
    cf_rows = [r for r in rows if r.get("critical_findings_variant") or r.get("critical_findings_bare")]
    if cf_rows:
        lines += ["", "## Critical Findings", ""]
        for r in cf_rows:
            lines.append(f"### {r['fixture']}")
            if r["critical_findings_variant"]:
                lines.append("**Variant:**")
                for f in r["critical_findings_variant"]:
                    lines.append(f"- {f}")
            if r["critical_findings_bare"]:
                lines.append("**Bare:**")
                for f in r["critical_findings_bare"]:
                    lines.append(f"- {f}")
            lines.append("")
    (res_root / "report.md").write_text("\n".join(lines))
    print((res_root / "report.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
