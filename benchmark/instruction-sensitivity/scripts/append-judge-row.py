#!/usr/bin/env python3
"""
Append one judge verdict row to judge-findings.jsonl, with the A/B slot map
resolved back to arm identity (solo_old / solo_new). This is the ONLY place
where arm identity is reintroduced after the judge's blind call.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def coerce_json(text: str) -> dict:
    """Extract a strict-JSON object from the judge last-message file.

    codex --output-schema usually returns clean JSON, but sometimes wraps it in
    code fences or a leading note. Be liberal here, fail loudly if nothing.
    """
    text = text.strip()
    if not text:
        raise ValueError("empty judge response")
    try:
        return json.loads(text)
    except Exception:
        pass

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError(f"could not parse JSON from judge response: {text[:200]!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--judge-json", required=True, type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    slot = manifest["slot_map"][args.fixture]
    arm_for_A = slot["A"]
    arm_for_B = slot["B"]

    raw = args.judge_json.read_text(encoding="utf-8") if args.judge_json.exists() else ""
    try:
        verdict = coerce_json(raw)
    except Exception as exc:
        verdict = {"parse_error": str(exc), "raw_preview": raw[:400]}

    # Resolve per-axis winners A/B -> solo_old/solo_new.
    resolved = {}
    for axis, score in (verdict.get("scores") or {}).items():
        winner_slot = score.get("winner")
        winner_arm = (
            arm_for_A if winner_slot == "A"
            else arm_for_B if winner_slot == "B"
            else "tie"
        )
        resolved[axis] = {
            "A_label": (score.get("A") or {}).get("label"),
            "A_evidence": (score.get("A") or {}).get("evidence"),
            "B_label": (score.get("B") or {}).get("label"),
            "B_evidence": (score.get("B") or {}).get("evidence"),
            "winner_slot": winner_slot,
            "winner_arm": winner_arm,
        }

    overall_slot = verdict.get("overall_winner")
    overall_arm = (
        arm_for_A if overall_slot == "A"
        else arm_for_B if overall_slot == "B"
        else "tie"
    )

    row = {
        "fixture_id": args.fixture,
        "slot_map": {"A": arm_for_A, "B": arm_for_B},
        "axis_scores": resolved,
        "overall_winner_slot": overall_slot,
        "overall_winner_arm": overall_arm,
        "overall_reason": verdict.get("overall_reason"),
        "parse_error": verdict.get("parse_error"),
    }
    sys.stdout.write(json.dumps(row, ensure_ascii=False))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
