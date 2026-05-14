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
  --l1-rerun-summary <path>  L1 rerun summary archived for provenance, not selection
  --output <path>            destination .devlyn/manifests/iter-0033c-pair-eligible.json

Selection rule (frozen pre-registration, iter-0033c §"Pair-eligible fixture set"):
  high_value = {F2, F3, F4, F6, F7}
  promoted_by_l1_le_l0 = {f ∈ C1 summary | solo_claude.score ≤ bare.score}
  conditional_excluded = {F1, F5}    # promoted only if L1≤L0
  reporting_only = {F8}              # excluded from Gate 3
  pair_eligible = high_value ∪ promoted_by_l1_le_l0 ∪ {F9 if iter-0033a passed}
                  − reporting_only
                  − conditional_excluded that did not get promoted
                  − current rejected/ceiling registry
"""
import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pair_evidence_contract import is_score, reject_json_constant

HIGH_VALUE = ["F2", "F3", "F4", "F6", "F7"]
CONDITIONAL = ["F1", "F5"]
REPORTING_ONLY = ["F8"]
REJECTED_REGISTRY = Path(__file__).with_name("pair-rejected-fixtures.sh")


def exact_bool(value: object) -> bool | None:
    return value if isinstance(value, bool) else None


def disqualifier_flag(value: object, *, default: bool = False) -> bool:
    if value is None:
        return default
    parsed = exact_bool(value)
    return parsed if parsed is not None else True


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


def load_rejected_fixture_reasons(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise ValueError(f"rejected fixture registry not found: {path}")
    rejected: dict[str, str] = {}
    current: str | None = None
    for line in path.read_text().splitlines():
        match = re.match(r"\s*([FS]\d+)-\*\|([FS]\d+)\)", line)
        if match and match.group(1) == match.group(2):
            current = match.group(1)
            continue
        reason = re.match(r'\s*echo "([^"]+)"', line)
        if current and reason:
            rejected[current] = reason.group(1)
            current = None
    return dict(sorted(rejected.items(), key=lambda item: (item[0][0], int(item[0][1:]))))


def load_rejected_short_ids(path: Path) -> list[str]:
    return list(load_rejected_fixture_reasons(path))


def load_json_object(path: Path, label: str) -> dict:
    try:
        data = json.loads(path.read_text(), parse_constant=reject_json_constant)
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} malformed: invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} malformed: expected object")
    return data


def compute_promoted_l1_le_l0(c1_rows: list) -> list:
    """Return short fixture IDs (e.g. 'F3') where solo_claude.score ≤ bare.score in C1."""
    promoted = []
    for row in c1_rows:
        if not isinstance(row, dict):
            continue
        raw_arms = row.get("arms")
        arms = raw_arms if isinstance(raw_arms, dict) else {}
        raw_solo = arms.get("solo_claude")
        raw_bare = arms.get("bare")
        solo_arm = raw_solo if isinstance(raw_solo, dict) else {}
        bare_arm = raw_bare if isinstance(raw_bare, dict) else {}
        if (
            disqualifier_flag(solo_arm.get("disqualifier"))
            or disqualifier_flag(bare_arm.get("disqualifier"))
        ):
            continue
        solo = solo_arm.get("score")
        bare = bare_arm.get("score")
        if not is_score(solo) or not is_score(bare):
            continue
        if solo <= bare:
            fixture = row.get("fixture")
            if isinstance(fixture, str):
                promoted.append(fixture_short_id(fixture))
    return promoted


def mapped_score(judge: dict, arm: str) -> int | None:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return None
    letter = next((slot for slot, mapped in mapping.items() if mapped == arm), None)
    if letter is None:
        return None
    raw_scores = judge.get("scores_by_arm")
    scores = raw_scores if isinstance(raw_scores, dict) else {}
    score = scores.get(arm)
    if is_score(score):
        return score
    legacy = judge.get(f"{letter.lower()}_score")
    return legacy if is_score(legacy) else None


def mapped_disqualifier(judge: dict, arm: str) -> bool:
    mapping = judge.get("_blind_mapping")
    if not isinstance(mapping, dict):
        return True
    letter = next((slot for slot, mapped in mapping.items() if mapped == arm), None)
    if letter is None:
        return True
    raw_by_arm = judge.get("disqualifiers_by_arm")
    if raw_by_arm is not None and not isinstance(raw_by_arm, dict):
        return True
    by_arm = raw_by_arm if isinstance(raw_by_arm, dict) else {}
    if arm in by_arm:
        entry = by_arm.get(arm)
        return disqualifier_flag(
            entry.get("disqualifier") if isinstance(entry, dict) else entry
        )
    raw_legacy = judge.get("disqualifiers")
    if raw_legacy is not None and not isinstance(raw_legacy, dict):
        return True
    legacy = raw_legacy if isinstance(raw_legacy, dict) else {}
    return disqualifier_flag(legacy.get(letter))


def f9_passed(f9_judge: dict) -> bool:
    """iter-0033a passed iff solo_claude beats bare and solo is not disqualified."""
    solo = mapped_score(f9_judge, "solo_claude")
    bare = mapped_score(f9_judge, "bare")
    if solo is None or bare is None:
        return False
    return solo > bare and not mapped_disqualifier(f9_judge, "solo_claude")


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

    try:
        c1 = load_json_object(c1_path, "c1-summary")
        f9 = load_json_object(f9_path, "f9-judge")
        rejected_reasons = load_rejected_fixture_reasons(REJECTED_REGISTRY)
        rejected_short_ids = list(rejected_reasons)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    c1_rows = c1.get("rows")
    if not isinstance(c1_rows, list):
        print("error: c1-summary malformed: rows must be an array", file=sys.stderr)
        return 2

    promoted = compute_promoted_l1_le_l0(c1_rows)
    f9_in = f9_passed(f9)

    pair_eligible = list(HIGH_VALUE)  # frozen high-value list, ordered
    for fx in promoted:
        if fx not in pair_eligible and fx not in REPORTING_ONLY:
            pair_eligible.append(fx)
    if f9_in and "F9" not in pair_eligible:
        pair_eligible.append("F9")
    pair_eligible = [fx for fx in pair_eligible if fx not in REPORTING_ONLY]
    rejected_excluded = sorted(
        {fx for fx in pair_eligible if fx in rejected_short_ids},
        key=lambda s: (s[0], int(s[1:])),
    )
    pair_eligible = [fx for fx in pair_eligible if fx not in rejected_short_ids]

    conditional_promoted = [fx for fx in CONDITIONAL if fx in promoted]
    conditional_excluded = [fx for fx in CONDITIONAL if fx not in promoted]
    pair_eligible_sorted = sorted(pair_eligible, key=lambda s: (s[0], int(s[1:])))
    if not pair_eligible_sorted:
        rejected_text = ", ".join(rejected_excluded) if rejected_excluded else "none"
        print(
            "error: no pair-eligible fixtures remain after rejected-registry filtering "
            f"(rejected_excluded={rejected_text})",
            file=sys.stderr,
        )
        return 1

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
            "rejected_registry": str(REJECTED_REGISTRY),
            "rejected_excluded": rejected_excluded,
            "rejected_excluded_reasons": {
                fixture: rejected_reasons[fixture] for fixture in rejected_excluded
            },
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
