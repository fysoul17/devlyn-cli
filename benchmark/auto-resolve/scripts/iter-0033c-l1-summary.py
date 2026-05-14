#!/usr/bin/env python3
"""Build iter-0033c L1 rerun summary from per-fixture judge/result artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import is_score, is_strict_number, loads_strict_json_object


SCORE_ARMS = ("solo_claude", "l2_gated", "l2_forced", "bare")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = loads_strict_json_object(path.read_text(encoding="utf8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    return data


def score_for(judge: dict[str, Any], arm: str, mapping: dict[str, Any]) -> int | None:
    letter = next(
        (slot for slot, mapped in mapping.items() if slot in {"A", "B", "C"} and mapped == arm),
        None,
    )
    if letter is None:
        return None
    raw_scores = judge.get("scores_by_arm")
    scores = raw_scores if isinstance(raw_scores, dict) else {}
    score = scores.get(arm)
    if is_score(score):
        return score
    legacy = judge.get(f"{letter.lower()}_score")
    return legacy if is_score(legacy) else None


def strict_number(value: object) -> object:
    return value if is_strict_number(value) else None


def build_summary(results_dir: Path, run_id: str, git_sha: str) -> dict[str, Any]:
    rows = []
    for fx_dir in sorted(p for p in results_dir.iterdir() if p.is_dir()):
        judge_path = fx_dir / "judge.json"
        if not judge_path.is_file():
            continue
        judge = load_json(judge_path)
        raw_mapping = judge.get("_blind_mapping")
        mapping = raw_mapping if isinstance(raw_mapping, dict) else {}
        arms = {}
        for arm_name in SCORE_ARMS:
            score = score_for(judge, arm_name, mapping)
            if score is None and arm_name not in set(mapping.values()):
                continue
            arm_dir = fx_dir / arm_name
            result = load_json(arm_dir / "result.json") if (arm_dir / "result.json").is_file() else {}
            arms[arm_name] = {
                "score": score,
                "wall_s": strict_number(result.get("elapsed_seconds")),
                "verify_score": strict_number(result.get("verify_score")),
                "files_changed": result.get("files_changed"),
                "timed_out": result.get("timed_out"),
                "disqualifier": result.get("disqualifier"),
            }
        rows.append({"fixture": fx_dir.name, "arms": arms})
    return {
        "run_id": run_id,
        "git_sha": git_sha,
        "fixtures_total": len(rows),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--git-sha", required=True)
    args = parser.parse_args()

    summary = build_summary(args.results_dir, args.run_id, args.git_sha)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf8")
    print(f"[l1-rerun-summary] wrote {args.out} (fixtures={summary['fixtures_total']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
