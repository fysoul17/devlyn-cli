#!/usr/bin/env python3
"""Build the iter-0033c pair-eligible manifest (Codex R0/R0.5 + R0-infra/R0.5-infra).

Manifest captures the immutable Gate-3 input to iter-0033c-compare.py:
  - which fixtures are pair-eligible (high-value ∪ L1≤L0 ∪ F9-if-iter-0033a-passed)
  - what the Gate-3 threshold count is
  - sha256 over the canonical document so any post-write tampering is detectable

Hashing pattern is the pre-stamp form lifted from
benchmark/auto-resolve/scripts/pair-plan-lint.py:81-91 — deep-copy the manifest,
zero out `manifest_sha256`, serialize with `sort_keys=True, separators=(",",":"),
ensure_ascii=False, allow_nan=False`, then sha256 the bytes.

Inputs (all required):
  --c1-summary <path>        iter-0033 (C1) summary.json (selection grounds; never a comparison baseline)
  --f9-judge <path>          iter-0033a F9 judge.json (F9 inclusion proof)
  --l1-rerun-summary <path>  L1 rerun summary at iter-0033c HEAD (fresh baseline)
  --output <path>            destination .devlyn/manifests/iter-0033c-pair-eligible.json

Selection rule (frozen pre-registration, iter-0033c §"Pair-eligible fixture set"):
  high_value = {F2, F3, F4, F6, F7}
  promoted_by_l1_le_l0 = {f ∈ C1 summary | solo_claude.score ≤ bare.score}
  conditional_excluded = {F1, F5}    # promoted only if L1≤L0
  reporting_only = {F8}              # excluded from Gate 3
  pair_eligible = high_value ∪ promoted_by_l1_le_l0 ∪ {F9 if iter-0033a passed}
                  − reporting_only
                  − conditional_excluded that did not get promoted
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HIGH_VALUE = ["F2", "F3", "F4", "F6", "F7"]
CONDITIONAL = ["F1", "F5"]
REPORTING_ONLY = ["F8"]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_manifest_sha256(manifest: dict) -> str:
    """Pre-stamp hash per pair-plan-lint.py:81-91 — zero out the stamp, then sha256."""
    pre = copy.deepcopy(manifest)
    pre["manifest_sha256"] = ""
    s = json.dumps(
        pre,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fixture_short_id(full: str) -> str:
    """'F3-backend-contract-risk' -> 'F3'. Pure prefix; matches existing convention."""
    return full.split("-", 1)[0] if "-" in full else full


def compute_promoted_l1_le_l0(c1_rows: list) -> list:
    """Return short fixture IDs (e.g. 'F3') where solo_claude.score ≤ bare.score in C1."""
    promoted = []
    for row in c1_rows:
        arms = row.get("arms", {})
        solo = arms.get("solo_claude", {}).get("score")
        bare = arms.get("bare", {}).get("score")
        if solo is None or bare is None:
            continue
        if solo <= bare:
            promoted.append(fixture_short_id(row["fixture"]))
    return promoted


def f9_passed(f9_judge: dict) -> bool:
    """iter-0033a passed iff A score > B score AND A is not disqualified."""
    a = f9_judge.get("a_score")
    b = f9_judge.get("b_score")
    dqs = f9_judge.get("disqualifiers") or {}
    if a is None or b is None:
        return False
    return a > b and not bool(dqs.get("A", False))


def head_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c1-summary", required=True)
    ap.add_argument("--f9-judge", required=True)
    ap.add_argument("--l1-rerun-summary", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    c1_path = Path(args.c1_summary)
    f9_path = Path(args.f9_judge)
    l1_path = Path(args.l1_rerun_summary)
    out_path = Path(args.output)

    for p, label in [(c1_path, "c1-summary"), (f9_path, "f9-judge"), (l1_path, "l1-rerun-summary")]:
        if not p.is_file():
            print(f"error: {label} not found: {p}", file=sys.stderr)
            return 2

    c1 = json.loads(c1_path.read_text())
    f9 = json.loads(f9_path.read_text())

    promoted = compute_promoted_l1_le_l0(c1.get("rows", []))
    f9_in = f9_passed(f9)

    pair_eligible = list(HIGH_VALUE)  # frozen high-value list, ordered
    for fx in promoted:
        if fx not in pair_eligible and fx not in REPORTING_ONLY:
            pair_eligible.append(fx)
    if f9_in and "F9" not in pair_eligible:
        pair_eligible.append("F9")
    pair_eligible = [fx for fx in pair_eligible if fx not in REPORTING_ONLY]

    conditional_promoted = [fx for fx in CONDITIONAL if fx in promoted]
    conditional_excluded = [fx for fx in CONDITIONAL if fx not in promoted]
    pair_eligible_sorted = sorted(pair_eligible, key=lambda s: (s[0], int(s[1:])))

    gate3_total = len(pair_eligible_sorted)
    gate3_threshold = (gate3_total + 1) // 2  # ≥50% — ceil(gate3_total / 2)

    manifest = {
        "schema_version": "1.0",
        "iter": "0033c",
        "head": head_sha(),
        "sources": {
            "c1_summary": {"path": str(c1_path), "sha256": file_sha256(c1_path)},
            "f9_judge": {"path": str(f9_path), "sha256": file_sha256(f9_path)},
            "l1_rerun_summary": {"path": str(l1_path), "sha256": file_sha256(l1_path)},
        },
        "selection_rule": {
            "high_value": HIGH_VALUE,
            "promoted_by_l1_le_l0": sorted(set(promoted)),
            "f9_included": f9_in,
            "f9_passed_iter_0033a": f9_in,
            "reporting_only": REPORTING_ONLY,
            "conditional_excluded": conditional_excluded,
            "conditional_promoted": conditional_promoted,
        },
        "fixtures_pair_eligible": pair_eligible_sorted,
        "gate3_threshold_count": gate3_threshold,
        "gate3_total": gate3_total,
        "manifest_sha256": "",
    }
    manifest["manifest_sha256"] = canonical_manifest_sha256(manifest)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"[manifest] wrote {out_path}")
    print(f"[manifest] pair-eligible: {pair_eligible_sorted} "
          f"(gate3 ≥ {gate3_threshold} / {gate3_total})")
    print(f"[manifest] sha256: {manifest['manifest_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
