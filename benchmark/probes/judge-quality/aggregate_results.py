#!/usr/bin/env python3
"""
aggregate_results.py — turns results/summary.json (written by
run_judge_quality.py) into the recall/precision matrix, per-case table, and
miss-set overlap (P3) for autoresearch/iterations/0055-judge-quality.md.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUMMARY_PATH = HERE / "results" / "summary.json"


def load_cases_meta():
    meta = {}
    for path in sorted((HERE / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        meta[case["id"]] = case["ground_truth"]
    return meta


def main():
    data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    meta = load_cases_meta()

    for judge, records in data.items():
        defect_recs = [r for r in records if meta[r["case"]]["type"] != "clean"]
        clean_recs = [r for r in records if meta[r["case"]]["type"] == "clean"]

        hits = sum(1 for r in defect_recs if r.get("hit") is True)
        fps = sum(1 for r in clean_recs if r.get("false_positive") is True)
        parse_errs = sum(1 for r in records if r.get("parse_error"))

        axis_valid = axis_total = 0
        for r in records:
            parsed = r.get("parsed") or {}
            for f in parsed.get("findings", []) if isinstance(parsed, dict) else []:
                axis_total += 1
                if f.get("axis") in ("no_workaround", "scope_discipline"):
                    axis_valid += 1

        print(f"\n=== {judge} ===")
        print(f"recall (rep-level):    {hits}/{len(defect_recs)} = {hits/len(defect_recs):.2f}")
        print(f"false-positive rate:    {fps}/{len(clean_recs)} = {fps/len(clean_recs):.2f}")
        print(f"parse errors:           {parse_errs}/{len(records)}")
        if axis_total:
            print(f"axis-field compliance:  {axis_valid}/{axis_total} findings had a valid axis enum")

        print("per-case (any-rep hit / total reps hit):")
        by_case = {}
        for r in records:
            by_case.setdefault(r["case"], []).append(r)
        for case_id, recs in by_case.items():
            gt = meta[case_id]
            if gt["type"] == "clean":
                n_fp = sum(1 for r in recs if r.get("false_positive") is True)
                print(f"  {case_id:12s} clean     fp={n_fp}/{len(recs)}")
            else:
                n_hit = sum(1 for r in recs if r.get("hit") is True)
                any_hit = n_hit > 0
                print(f"  {case_id:12s} {gt['class']:16s} hit={n_hit}/{len(recs)} any_hit={any_hit}")

    if set(data.keys()) >= {"ollama", "sonnet"}:
        print("\n=== miss-set overlap (P3) — defect cases only, any-rep-hit ===")
        judges = list(data.keys())
        any_hit = {j: {} for j in judges}
        for judge, records in data.items():
            by_case = {}
            for r in records:
                by_case.setdefault(r["case"], []).append(r)
            for case_id, recs in by_case.items():
                if meta[case_id]["type"] == "clean":
                    continue
                any_hit[judge][case_id] = any(r.get("hit") is True for r in recs)
        defect_case_ids = [c for c, gt in meta.items() if gt["type"] != "clean"]
        for case_id in defect_case_ids:
            statuses = {j: any_hit[j].get(case_id) for j in judges}
            print(f"  {case_id:12s} {statuses}")


if __name__ == "__main__":
    main()
