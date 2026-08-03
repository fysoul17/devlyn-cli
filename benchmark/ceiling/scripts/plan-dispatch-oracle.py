#!/usr/bin/env python3
"""Post-hoc PLAN dispatch, delivery, ledger, and startup oracle."""
from __future__ import annotations

import argparse
import base64
import copy
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import zlib


PLAN_STEM = "PHASE 1 — PLAN (canonical body)"
PLAN_HEADING_RE = re.compile(rf"(?m)^#+[ \t]+{re.escape(PLAN_STEM)}")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PLAN_MAX_DISPATCHES = 2
SPAWN_FIELDS = (
    "round", "started_at", "triggered_by", "engine", "model_requested", "prompt_sha256",
)
COMPLETION_FIELDS = ("completed_at", "duration_ms", "verdict", "model_effective")
RECEIPT_FIELDS = SPAWN_FIELDS + COMPLETION_FIELDS
LEGACY_HISTORY_FIELDS = {"started_at", "verdict", "completed_at", "duration_ms"}
LEGACY_CURRENT_FIELDS = LEGACY_HISTORY_FIELDS | {
    "artifacts", "model_effective", "model_requested", "round", "sub_verdicts",
    "triggered_by",
}


def parse_time(value: object) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp missing or malformed")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def milliseconds(start: object, end: object) -> int:
    start_time = parse_time(start)
    end_time = parse_time(end)
    if end_time < start_time:
        raise ValueError("negative timestamp span")
    return round((end_time - start_time).total_seconds() * 1000)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: pathlib.Path, issues: list[str], label: str) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        issues.append(f"{label}-unavailable:{exc}")
        return None
    if not isinstance(value, dict):
        issues.append(f"{label}-malformed:not-object")
        return None
    return value


def resolve_result_dir(path: pathlib.Path) -> pathlib.Path:
    if (path / "timing.json").is_file() or (path / "devlyn-snapshot").is_dir():
        return path
    if (path / "result").is_dir():
        return path / "result"
    return path


def resolve_state(result_dir: pathlib.Path, issues: list[str]) -> tuple[dict | None, str | None]:
    snapshot = result_dir / "devlyn-snapshot"
    candidates = sorted(snapshot.glob("runs/*/pipeline.state.json"))
    root = snapshot / "pipeline.state.json"
    if root.is_file():
        candidates.append(root)
    if len(candidates) != 1:
        issues.append(f"pipeline-state-count:{len(candidates)}")
        if not candidates:
            return None, None
    path = candidates[-1]
    return read_json(path, issues, "pipeline-state"), str(path.relative_to(result_dir))


def parent_session_paths(result_dir: pathlib.Path) -> list[pathlib.Path]:
    session_root = result_dir.parent / "sessions"
    if not session_root.is_dir():
        return []
    return sorted(
        path for path in session_root.rglob("*.jsonl")
        if "subagents" not in path.parts
    )


def collect_agent_calls(
    session_paths: list[pathlib.Path], issues: list[str], result_dir: pathlib.Path,
) -> tuple[list[dict], int, list[dict]]:
    candidates: list[dict] = []
    sidechain_agent_count = 0
    writer_evidence: list[dict] = []
    for path in session_paths:
        try:
            lines = path.read_bytes().splitlines()
        except OSError as exc:
            issues.append(f"parent-session-unreadable:{path.name}:{exc}")
            continue
        for line_number, raw in enumerate(lines, 1):
            try:
                record = json.loads(raw)
            except ValueError:
                issues.append(f"parent-session-json-malformed:{path.name}:{line_number}")
                continue
            message = record.get("message") if isinstance(record, dict) else None
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool_name = block.get("name")
                tool_input = block.get("input")
                if not isinstance(tool_input, dict):
                    continue
                if tool_name in {"Write", "Edit"}:
                    target = tool_input.get("file_path", tool_input.get("path"))
                    if isinstance(target, str) and (
                        target == ".devlyn/plan.md" or target.endswith("/.devlyn/plan.md")
                    ):
                        writer_evidence.append(
                            {"source": path.name, "line": line_number, "tool": tool_name}
                        )
                if tool_name != "Agent":
                    continue
                if record.get("parent_tool_use_id") is not None:
                    sidechain_agent_count += 1
                    continue
                prompt = tool_input.get("prompt")
                tool_id = block.get("id")
                heading = None
                delivered_digest = None
                if isinstance(prompt, str):
                    delivered_digest = sha256_text(prompt)
                    heading = next(
                        (line for line in prompt.splitlines() if PLAN_HEADING_RE.match(line)),
                        None,
                    )
                candidates.append({
                    "tool_use_id": tool_id,
                    "timestamp": record.get("timestamp"),
                    "source": str(path.relative_to(result_dir.parent)),
                    "source_line": line_number,
                    "subagent_type": tool_input.get("subagent_type"),
                    "delivered_prompt_sha256": delivered_digest,
                    "diagnostics": {
                        "canonical_heading_match": heading is not None,
                        "heading": heading,
                    },
                })

    def order_key(dispatch: dict) -> tuple:
        try:
            timestamp = parse_time(dispatch["timestamp"])
        except (TypeError, ValueError):
            issues.append(f"dispatch-timestamp-malformed:{dispatch['tool_use_id']}")
            timestamp = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
        return timestamp, dispatch["source"], dispatch["source_line"]

    return sorted(candidates, key=order_key), sidechain_agent_count, writer_evidence


def bind_dispatches(
    receipts: list[dict], candidates: list[dict],
) -> tuple[list[dict], dict[int, dict], list[dict], list[dict], list[str]]:
    windows: list[dict] = []
    for receipt in receipts:
        if receipt["_schema"] == "invalid":
            continue
        windows.append({
            "ledger_index": receipt["_ledger_index"],
            "started_at": receipt["started_at"],
            "completed_at": receipt["completed_at"],
            "_start": parse_time(receipt["started_at"]),
            "_end": parse_time(receipt["completed_at"]),
            "_candidates": [],
        })

    violations: list[str] = []
    ambiguous_indexes: set[int] = set()
    has_overlap = False
    overlap_indexes: dict[int, set[int]] = {
        window["ledger_index"]: set() for window in windows
    }
    for left_index, left in enumerate(windows):
        for right in windows[left_index + 1:]:
            if max(left["_start"], right["_start"]) <= min(left["_end"], right["_end"]):
                pair = [left["ledger_index"], right["ledger_index"]]
                has_overlap = True
                ambiguous_indexes.update(pair)
                overlap_indexes[pair[0]].add(pair[1])
                overlap_indexes[pair[1]].add(pair[0])
    if has_overlap:
        violations.append("plan-authorization-windows-overlap")

    outside_plan: list[dict] = []
    non_plan: list[dict] = []
    for candidate in candidates:
        try:
            timestamp = parse_time(candidate["timestamp"])
        except (TypeError, ValueError):
            candidate["authorization_window_indexes"] = []
            continue
        memberships = [
            window for window in windows
            if window["_start"] <= timestamp <= window["_end"]
        ]
        candidate["authorization_window_indexes"] = [
            window["ledger_index"] for window in memberships
        ]
        for window in memberships:
            window["_candidates"].append(candidate)
        if len(memberships) > 1:
            violations.append("plan-agent-matches-multiple-authorization-windows")
            ambiguous_indexes.update(candidate["authorization_window_indexes"])
        elif not memberships:
            if candidate["diagnostics"]["canonical_heading_match"]:
                outside_plan.append(candidate)
            else:
                non_plan.append(candidate)

    bindings: dict[int, dict] = {}
    public_windows: list[dict] = []
    for window in windows:
        ledger_index = window["ledger_index"]
        candidate_ids = [candidate["tool_use_id"] for candidate in window["_candidates"]]
        if len(window["_candidates"]) > 1:
            violations.append("multiple-plan-agents-in-authorization-window")
            ambiguous_indexes.add(ledger_index)
        if ledger_index in ambiguous_indexes:
            status = "AMBIGUOUS"
        elif not window["_candidates"]:
            status = "MISSING"
        else:
            status = "BOUND"
            bindings[ledger_index] = window["_candidates"][0]
        public_windows.append({
            "ledger_index": ledger_index,
            "started_at": window["started_at"],
            "completed_at": window["completed_at"],
            "candidate_tool_use_ids": candidate_ids,
            "overlapping_ledger_indexes": sorted(overlap_indexes[ledger_index]),
            "status": status,
        })
    if outside_plan:
        violations.append("plan-dispatch-outside-authorization-window")
    return public_windows, bindings, outside_plan, non_plan, sorted(set(violations))


def receipt_schema(receipt: dict) -> str:
    def valid_completion() -> bool:
        valid = (
            isinstance(receipt.get("started_at"), str)
            and isinstance(receipt.get("completed_at"), str)
            and isinstance(receipt.get("duration_ms"), (int, float))
            and not isinstance(receipt.get("duration_ms"), bool)
            and receipt["duration_ms"] >= 0
            and isinstance(receipt.get("verdict"), str)
            and bool(receipt["verdict"])
        )
        if not valid:
            return False
        try:
            return parse_time(receipt["started_at"]) <= parse_time(receipt["completed_at"])
        except ValueError:
            return False

    if set(receipt) == LEGACY_HISTORY_FIELDS:
        return "legacy-pre-d1-four-key" if valid_completion() else "invalid"
    if set(receipt) - {"engine"} == LEGACY_CURRENT_FIELDS:
        # Two pre-D1 current-entry variants exist in the retained 0088
        # receipts: C3 (no engine key, inherit-null model_requested) and the
        # F7/C1 class (engine + model_requested strings). Both lack the D1
        # digest and are unattestable, not invalid.
        legacy_current = (
            valid_completion()
            and isinstance(receipt.get("round"), int)
            and not isinstance(receipt.get("round"), bool)
            and receipt["round"] >= 0
            and receipt.get("triggered_by") is None
            and (receipt.get("model_requested") is None
                 or isinstance(receipt.get("model_requested"), str))
            and (receipt.get("engine") is None
                 or isinstance(receipt.get("engine"), str))
            and receipt.get("model_effective") is None
            and receipt.get("sub_verdicts") is None
            and receipt.get("artifacts") == {
                "findings_file": None, "log_file": None,
            }
        )
        return "legacy-pre-d1-current" if legacy_current else "invalid"
    if not all(field in receipt for field in RECEIPT_FIELDS):
        return "invalid"
    valid = (
        valid_completion()
        and isinstance(receipt["round"], int)
        and not isinstance(receipt["round"], bool)
        and receipt["round"] >= 0
        and (receipt["triggered_by"] is None or isinstance(receipt["triggered_by"], str))
        and isinstance(receipt["engine"], str) and bool(receipt["engine"])
        and isinstance(receipt["model_requested"], str) and bool(receipt["model_requested"])
        and isinstance(receipt["prompt_sha256"], str)
        and SHA256_RE.fullmatch(receipt["prompt_sha256"]) is not None
        and (receipt["model_effective"] is None or isinstance(receipt["model_effective"], str))
    )
    return "d1-complete" if valid else "invalid"


def collect_receipts(
    state: dict | None, issues: list[str],
) -> tuple[list[dict], dict | None]:
    phases = state.get("phases") if isinstance(state, dict) else None
    plan = phases.get("plan") if isinstance(phases, dict) else None
    if not isinstance(plan, dict):
        return [], None
    if not plan:
        return [], plan
    history_present = "history" in plan
    raw_history = plan.get("history", [])
    history: list[dict] = []
    if not isinstance(raw_history, list):
        issues.append("plan-ledger-structure:history-not-array")
    else:
        for index, row in enumerate(raw_history):
            if not isinstance(row, dict):
                issues.append(
                    f"plan-ledger-structure:history-row-not-object:{index}"
                )
                continue
            history.append(row)
    records = [copy.deepcopy(row) for row in history]
    if plan.get("started_at") is None:
        issues.append("plan-ledger-structure:current-started-at-missing")
    round_value = plan.get("round")
    if (
        isinstance(round_value, int)
        and not isinstance(round_value, bool)
        and round_value > 0
        and not history_present
    ):
        issues.append(
            "plan-ledger-structure:history-key-missing-for-nonzero-round"
        )
    if plan.get("started_at") is not None:
        records.append({field: copy.deepcopy(value) for field, value in plan.items() if field != "history"})
    for ledger_index, record in enumerate(records):
        record["_ledger_index"] = ledger_index
        record["_schema"] = receipt_schema(
            {key: value for key, value in record.items() if not key.startswith("_")}
        )
    return records, plan


def build_startup(
    receipts: list[dict], plan: dict | None, timing: dict | None, attribution: dict | None,
) -> tuple[dict, dict | None]:
    result = {
        "method": "first-ledger-span",
        "startup_recomputed_ms": None,
        "attribution_startup_ms": attribution.get("startup_ms") if attribution else None,
        "delta_ms": None,
        "tolerance_ms": 1000,
        "status": "INCOMPLETE",
    }
    diagnostic = None
    invoke_start = timing.get("invoke_started_at") if timing else None
    if receipts and invoke_start is not None:
        try:
            recomputed = milliseconds(invoke_start, receipts[0].get("started_at"))
            attributed = result["attribution_startup_ms"]
            result["startup_recomputed_ms"] = recomputed
            if isinstance(attributed, (int, float)) and not isinstance(attributed, bool):
                delta = recomputed - attributed
                result["delta_ms"] = delta
                result["status"] = "PASS" if abs(delta) <= 1000 else "FAIL"
        except (TypeError, ValueError):
            pass
    history = plan.get("history") if isinstance(plan, dict) else None
    if isinstance(history, list) and history and invoke_start is not None:
        try:
            legacy = milliseconds(invoke_start, plan.get("started_at"))
            authoritative = result["startup_recomputed_ms"]
            diagnostic = {
                "name": "legacy-current-round-only-startup-truncation",
                "wrong_procedure": "current-plan-started-at-minus-invoke-start",
                "current_round_only_ms": legacy,
                "delta_from_authoritative_ms": (
                    legacy - authoritative if isinstance(authoritative, int) else None
                ),
                "scored": False,
            }
        except (TypeError, ValueError):
            diagnostic = {
                "name": "legacy-current-round-only-startup-truncation",
                "wrong_procedure": "current-plan-started-at-minus-invoke-start",
                "current_round_only_ms": None,
                "delta_from_authoritative_ms": None,
                "scored": False,
            }
    return result, diagnostic


def analyze(result_path: pathlib.Path) -> dict:
    result_dir = resolve_result_dir(result_path)
    evidence_issues: list[str] = []
    product_violations: list[str] = []
    diagnostics: list[dict] = []
    state, state_source = resolve_state(result_dir, evidence_issues)
    timing = read_json(result_dir / "timing.json", evidence_issues, "timing")
    attribution = read_json(result_dir / "attribution.json", evidence_issues, "attribution")
    receipts, plan = collect_receipts(state, evidence_issues)
    candidates, sidechain_agent_count, writer_evidence = collect_agent_calls(
        parent_session_paths(result_dir), evidence_issues, result_dir,
    )
    authorization_windows, bindings, outside_plan, non_plan, binding_violations = (
        bind_dispatches(receipts, candidates)
    )
    product_violations.extend(binding_violations)
    plan_candidates = [
        candidate for candidate in candidates
        if candidate.get("authorization_window_indexes") or candidate in outside_plan
    ]
    bound_dispatches = [
        bindings[receipt["_ledger_index"]] | {
            "ledger_index": receipt["_ledger_index"],
        }
        for receipt in receipts
        if receipt["_ledger_index"] in bindings
    ]
    content_diagnostic = {
        "name": "dispatch-content-diagnostics",
        "canonical_heading_stem": PLAN_STEM,
        "outside_authorization_plan_tool_use_ids": [
            candidate["tool_use_id"] for candidate in outside_plan
        ],
        "out_of_window_non_plan_tool_use_ids": [
            candidate["tool_use_id"] for candidate in non_plan
        ],
    }

    legacy_receipts = [
        receipt for receipt in receipts
        if receipt["_schema"].startswith("legacy-pre-d1")
    ]
    invalid_receipts = [receipt for receipt in receipts if receipt["_schema"] == "invalid"]
    conclusive_dispatch_violation = (
        len(plan_candidates) > PLAN_MAX_DISPATCHES or bool(binding_violations)
    )
    if legacy_receipts:
        diagnostics.append({
            "name": "legacy-pre-d1-plan-receipt-schema",
            "ledger_indexes": [receipt["_ledger_index"] for receipt in legacy_receipts],
            "schemas": [receipt["_schema"] for receipt in legacy_receipts],
            "delivery_digest_attestation": "unavailable",
            "scored_as_startup": False,
        })
        if not conclusive_dispatch_violation:
            evidence_issues.append("plan-receipt-schema-incomplete")
    if invalid_receipts:
        evidence_issues.append("plan-receipt-schema-invalid")
    continuity: list[dict] = []
    seen: set[int] = set()
    for ledger_index, receipt in enumerate(receipts):
        round_value = (
            ledger_index
            if receipt["_schema"] == "legacy-pre-d1-four-key"
            else receipt.get("round")
        )
        if not isinstance(round_value, int) or isinstance(round_value, bool):
            continuity.append({
                "name": "round-continuity-unscorable-receipt",
                "ledger_index": ledger_index,
            })
            continue
        missing = [prior for prior in range(round_value) if prior not in seen]
        if missing:
            continuity.append({
                "name": "round-continuity-missing-prior-receipts",
                "ledger_index": ledger_index,
                "round": round_value,
                "missing_prior_rounds": missing,
            })
        if round_value != ledger_index:
            continuity.append({
                "name": "round-continuity-nonmonotonic",
                "ledger_index": ledger_index,
                "round": round_value,
                "expected_round": ledger_index,
            })
        seen.add(round_value)
    if continuity:
        product_violations.append("round-continuity")

    delivery: list[dict] = []
    per_round: list[dict] = []
    windows_by_index = {
        window["ledger_index"]: window
        for window in authorization_windows
        if "ledger_index" in window
    }
    for receipt in receipts:
        index = receipt["_ledger_index"]
        dispatch = bindings.get(index)
        window = windows_by_index.get(index)
        window_status = window["status"] if window else "INVALID"
        expected_digest = receipt.get("prompt_sha256")
        delivered_digest = dispatch.get("delivered_prompt_sha256") if dispatch else None
        if receipt["_schema"] == "invalid":
            matched = None
            delivery_status = "INVALID:receipt-schema"
        elif window_status == "AMBIGUOUS":
            matched = None
            delivery_status = "AMBIGUOUS:authorization-window"
        elif dispatch and receipt["_schema"].startswith("legacy-pre-d1"):
            matched = None
            delivery_status = "UNATTESTABLE:legacy-pre-d1-receipt"
        elif dispatch:
            matched = (
                isinstance(expected_digest, str)
                and isinstance(delivered_digest, str)
                and expected_digest == delivered_digest
            )
            delivery_status = "PASS" if matched else "FAIL"
        elif outside_plan:
            matched = None
            delivery_status = "OUTSIDE:authorization-window"
        else:
            matched = False
            delivery_status = "MISSING:agent-tool-use"
        delivery.append({
            "ledger_index": index,
            "round": receipt.get("round"),
            "tool_use_id": dispatch.get("tool_use_id") if dispatch else None,
            "candidate_tool_use_ids": window["candidate_tool_use_ids"] if window else [],
            "recorded_prompt_sha256": expected_digest,
            "delivered_prompt_sha256": delivered_digest,
            "match": matched,
            "status": delivery_status,
        })
        composition_gap = None
        ledger_span = None
        try:
            ledger_span = milliseconds(receipt.get("started_at"), receipt.get("completed_at"))
        except (TypeError, ValueError):
            pass
        if dispatch:
            try:
                composition_gap = milliseconds(receipt.get("started_at"), dispatch.get("timestamp"))
            except (TypeError, ValueError):
                product_violations.append(f"composition-gap-invalid:{index}")
        per_round.append({
            "ledger_index": index,
            "round": receipt.get("round") if receipt else None,
            "ledger_span_ms": ledger_span,
            "spw_to_agent_composition_gap_ms": composition_gap,
            "agent_tool_use_id": dispatch.get("tool_use_id") if dispatch else None,
        })
    missing_windows = [
        window for window in authorization_windows
        if window.get("status") == "MISSING"
    ]
    if missing_windows and not outside_plan:
        evidence_issues.append("missing-delivery-evidence")
    if any(row["status"] == "FAIL" for row in delivery):
        product_violations.append("delivered-prompt-digest-mismatch")
    if not receipts and not plan_candidates:
        evidence_issues.append("missing-plan-ledger")
    if missing_windows and not outside_plan and not plan_candidates:
        evidence_issues.append("missing-plan-agent-tool-use")
    if len(plan_candidates) > PLAN_MAX_DISPATCHES or len(receipts) > PLAN_MAX_DISPATCHES:
        product_violations.append("plan-dispatch-cap-exceeded")

    inter_round: list[dict] = []
    for index in range(1, len(receipts)):
        try:
            gap = milliseconds(receipts[index - 1].get("completed_at"), receipts[index].get("started_at"))
        except (TypeError, ValueError):
            gap = None
        inter_round.append({"after_ledger_index": index - 1, "gap_ms": gap})

    legal_receipts = receipts[:PLAN_MAX_DISPATCHES]
    region = {"started_at": None, "completed_at": None, "duration_ms": None}
    first_legal_dispatch = (
        bindings.get(legal_receipts[0]["_ledger_index"])
        if legal_receipts else None
    )
    if legal_receipts and first_legal_dispatch:
        region["started_at"] = first_legal_dispatch.get("timestamp")
        region["completed_at"] = legal_receipts[-1].get("completed_at")
        try:
            region["duration_ms"] = milliseconds(region["started_at"], region["completed_at"])
        except (TypeError, ValueError):
            pass

    startup, legacy_diagnostic = build_startup(receipts, plan, timing, attribution)
    if startup["status"] == "INCOMPLETE" and not outside_plan:
        evidence_issues.append("startup-conjunct-unavailable")
    elif startup["status"] == "FAIL":
        product_violations.append("startup-conjunct-mismatch")

    evidence_issues = sorted(set(evidence_issues))
    product_violations = sorted(set(product_violations))
    evidence_complete = not evidence_issues
    product_eligible = not product_violations
    classification = (
        "INCOMPLETE" if not evidence_complete
        else "COMPLETE" if product_eligible
        else "CONTRACT-VIOLATION"
    )
    public_receipts = [
        {key: value for key, value in receipt.items() if not key.startswith("_")}
        | {"schema": receipt["_schema"], "ledger_index": receipt["_ledger_index"]}
        for receipt in receipts
    ]
    return {
        "schema_version": 2,
        "classification": classification,
        "evidence": {"complete": evidence_complete, "issues": evidence_issues},
        "product": {"eligible": product_eligible, "violations": product_violations},
        "result_dir": str(result_dir),
        "state_source": state_source,
        "dispatch_identity": {
            "authority": "ledger-window+top-level-parent-Agent",
            "plan_dispatch_count": len(plan_candidates),
            "agent_tool_use_count": len(candidates),
            "sidechain_agent_tool_use_count": sidechain_agent_count,
            "non_plan_agent_tool_use_count": len(non_plan),
            "dispatches": bound_dispatches,
            "agent_candidates": candidates,
            "authorization_windows": authorization_windows,
            "outside_authorization_plan_dispatches": outside_plan,
            "plan_md_writer_corroboration": writer_evidence,
        },
        "ledger": {"receipt_count": len(receipts), "receipts": public_receipts},
        "round_continuity": continuity,
        "delivery_attestation": delivery,
        "decomposition": {
            "plan_region_first_dispatch_to_final_legal_completion": region,
            "per_round": per_round,
            "parent_inter_round_gaps": inter_round,
        },
        "startup": startup,
        "diagnostics": (
            diagnostics
            + ([] if legacy_diagnostic is None else [legacy_diagnostic])
            + [content_diagnostic]
        ),
    }


def write_oracle(result_path: pathlib.Path) -> tuple[pathlib.Path, dict]:
    result_dir = resolve_result_dir(result_path)
    payload = analyze(result_dir)
    output = result_dir / "plan-dispatch-oracle.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output, payload


# Minimal records synthesized from the real iter-0088 retained JSONL bytes.
# The source prompt/line digests make provenance auditable without making the
# self-test depend on a machine-local receipt directory at runtime.
REAL_DISPATCH_FIXTURES = {
    "C2": [
        (127, "2026-08-02T02:58:58.818Z", "toolu_01SJskjekY33fEbFLQfC49A7", "claude", "\n## PHASE 1 — PLAN (canonical body)\n\n<role>\n", "11038d67f3e542c7b2c263ab487e6a33c4fc76e6af520e129ce82d39b9df616e", "cfe1e3b621d24d0c6e6bb21dd40d3df67eaa3a16e23bd9e127f420265661946f"),
        (302, "2026-08-02T03:17:21.841Z", "toolu_014j2jkZbMnUtubUuLAgpWp9", "claude", "\n# PHASE 3 — BUILD_GATE (canonical body)\n\nBUILD_GATE is mechanical / deterministic — same commands CI / Docker / production run.\n", "24e1dee7fc13672ede7971846226c0826913e6de94c59b98e4684b51cbf0c7cd", "ebc7c1731629a70b016d12964e55c889883c40e13ee98c7912807b91990dd9d6"),
        (402, "2026-08-02T03:33:42.119Z", "toolu_014kw3WkEhLjTvpLEP7wAGSx", "claude", "\n# PHASE 5 — VERIFY — pair-JUDGE sub-phase (bounded adversarial complement, fresh context)\n", "1081d30213e77850d5bb48230195eec67f9a0318df3efeab66eb85681cee9f05", "18108ccde664072ee87a992316d1ec1fa61597ca1e037e1f8959fcc707c9c0bb"),
        (513, "2026-08-02T03:44:25.728Z", "toolu_014XmftThw8c9VhB8enpgQ4r", "claude", "\n# PHASE 5 — VERIFY — pair-JUDGE sub-phase (bounded adversarial complement, fresh context, round 1)\n", "5b1b292e180e0d53ef70d04f273385c6afc2b33bc9c4cdd0cd333cb92a6f9d6d", "06931ab39bd62957a655bec6acb3c55e02aa0cbb4e1b7c077a408427c5f1404e"),
    ],
    "C3": [
        (129, "2026-08-02T04:11:49.215Z", "toolu_018uNqsJQ5z8XT2Fh2Neqk9K", "general-purpose", "\n# PHASE 1 — PLAN (canonical body)\n\n<role>\n", "d61e8c5bb92af5b1fdd3a599af0e3909fd0fef2e3753e69fb124a08ab73bda00", "6abe5a10a6871f1a945ed9a1b3475835bace210fb10175326c249824384d7b2e"),
        (153, "2026-08-02T04:16:06.690Z", "toolu_01V6ZMhiFhtsz2d5pJLApuHu", "general-purpose", "# PHASE 1 — PLAN (canonical body) — ROUND 1, CORRECTING ROUND 0\n", "4ce2da0b0dcd7efead6b42fde0af40a3ab5d59094f1b5230c0ff7627be4c268f", "070b667e16f6564b6f8e7cef75eb98d2da7b41324668a09efb076fcc2ba7dcad"),
        (188, "2026-08-02T04:19:49.092Z", "toolu_01XsaLyzy6mTYub6HEwomSMg", "general-purpose", "# PHASE 1 — PLAN (canonical body) — ROUND 2, narrow sync fix\n", "ea8a9367ef6cab0c9eca5b5555c21a344c2cbd25196844f105faeb27d84bcaba", "0819172824557e0098ad9b79a721f9ef7d5df76d6c2bd745fc10e8c50e049ba8"),
    ],
    "F7C1": [
        (131, "2026-08-02T01:02:11.105Z", "toolu_01QikfnCL9TLDNe9xVBZjjYi", "claude", "\n# PHASE 1 — PLAN (canonical body)\n\n<role>\n", "f7e405e91268925d8887514c3347b180d0e3635d7b3ed0a91b3017918d5d8e79", "ee821b9a39d0307acba2ad38ac9669019fbdae0306467e756fbf7f432d6b57fa"),
    ],
}

# zlib-compressed JSON of the three exact retained C3 Agent prompt strings.
REAL_C3_PROMPTS_B64 = (
    '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'
)

REAL_STARTUP_FIXTURES = {
    "F7C1": ("2026-08-02T00:58:04.045Z", 213270, [], ("2026-08-02T01:01:37.315Z", "2026-08-02T01:03:20.535Z", 103220, "PASS", 1)),
    "F7C2": ("2026-08-02T01:37:06.096Z", 154197, [], ("2026-08-02T01:39:40.293Z", "2026-08-02T01:41:23.229Z", 102936, "PASS", 0)),
    "F12C1": ("2026-08-02T02:01:03.770Z", 156297, [], ("2026-08-02T02:03:40.067Z", "2026-08-02T02:07:07.744Z", 207677, "PASS", 0)),
    "C2": ("2026-08-02T02:55:30.944Z", 181103, [], ("2026-08-02T02:58:32.047Z", "2026-08-02T03:04:45.248Z", 373201, "PASS", 0)),
    "C3": (
        "2026-08-02T04:08:05.046Z", 181191,
        [
            ("2026-08-02T04:11:06.237Z", "2026-08-02T04:15:51.283Z", 285046, "NEEDS_WORK"),
            ("2026-08-02T04:15:51.336Z", "2026-08-02T04:19:42.566Z", 231230, "NEEDS_WORK"),
        ],
        ("2026-08-02T04:19:42.615Z", "2026-08-02T04:20:20.117Z", 37502, "PASS", 2),
    ),
}


def fixture_dispatches(name: str) -> list[dict]:
    records = []
    retained_prompts = None
    if name == "C3":
        retained_prompts = json.loads(zlib.decompress(base64.b64decode(
            "".join(REAL_C3_PROMPTS_B64)
        )).decode("utf-8"))
    for index, fixture in enumerate(REAL_DISPATCH_FIXTURES[name]):
        line, timestamp, tool_id, subagent_type, prompt, source_prompt, source_line = fixture
        if retained_prompts is not None:
            prompt = retained_prompts[index]
            assert sha256_text(prompt) == source_prompt
        records.append({
            "timestamp": timestamp,
            "fixture_source": {
                "retained_line": line,
                "source_prompt_sha256": source_prompt,
                "source_jsonl_line_sha256": source_line,
            },
            "message": {"content": [{
                "type": "tool_use", "name": "Agent", "id": tool_id,
                "input": {"subagent_type": subagent_type, "prompt": prompt},
            }]},
        })
    return records


def raw_fixture_state(name: str) -> tuple[dict, dict, dict]:
    invoke, startup, history_rows, current = REAL_STARTUP_FIXTURES[name]
    history = [
        {"started_at": row[0], "completed_at": row[1], "duration_ms": row[2], "verdict": row[3]}
        for row in history_rows
    ]
    plan = {
        "started_at": current[0], "completed_at": current[1],
        "duration_ms": current[2], "verdict": current[3], "round": current[4],
        "triggered_by": None, "model_effective": None,
        "artifacts": {"findings_file": None, "log_file": None},
        "sub_verdicts": None,
    }
    if name == "C3":
        plan["model_requested"] = None
    else:
        # The other four retained arms carry the engine-bearing variant.
        plan.update({"engine": "claude", "model_requested": "claude-sonnet-5"})
    if history:
        plan["history"] = history
    return (
        {"started_at": invoke, "phases": {"plan": plan}},
        {"schema_version": 2, "invoke_started_at": invoke},
        {"startup_ms": startup},
    )


def enrich_fixture_plan(state: dict, dispatch_records: list[dict], rounds: list[int] | None = None) -> None:
    plan = state["phases"]["plan"]
    records = [*plan.get("history", []), plan]
    plan_dispatches = [
        dispatch for dispatch in dispatch_records
        if PLAN_HEADING_RE.search(dispatch["message"]["content"][0]["input"]["prompt"])
    ]
    assert len(records) == len(plan_dispatches)
    for index, (receipt, dispatch) in enumerate(zip(records, plan_dispatches)):
        prompt = dispatch["message"]["content"][0]["input"]["prompt"]
        receipt.update({
            "round": rounds[index] if rounds is not None else index,
            "triggered_by": None if index == 0 else "plan",
            "engine": "claude",
            "model_requested": "claude-sonnet-5",
            "prompt_sha256": sha256_text(prompt),
            "model_effective": None,
        })


def write_fixture(
    root: pathlib.Path,
    name: str,
    dispatch_records: list[dict],
    *,
    rounds: list[int] | None = None,
    source_name: str | None = None,
    enrich_receipts: bool = True,
) -> pathlib.Path:
    result = root / name / "result"
    state, timing, attribution = raw_fixture_state(source_name or name)
    if dispatch_records and enrich_receipts:
        enrich_fixture_plan(state, dispatch_records, rounds)
    state_path = result / "devlyn-snapshot" / "runs" / "run" / "pipeline.state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False) + "\n", encoding="utf-8")
    (result / "timing.json").write_text(json.dumps(timing) + "\n", encoding="utf-8")
    (result / "attribution.json").write_text(json.dumps(attribution) + "\n", encoding="utf-8")
    if dispatch_records:
        session = result.parent / "sessions" / "parent.jsonl"
        session.parent.mkdir()
        session.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in dispatch_records),
            encoding="utf-8",
        )
    return result


def self_test() -> int:
    assertions = 0

    def equal(actual: object, expected: object) -> None:
        nonlocal assertions
        assertions += 1
        if actual != expected:
            raise AssertionError(f"expected {expected!r}, got {actual!r}")

    with tempfile.TemporaryDirectory(prefix="plan-dispatch-oracle-") as raw:
        root = pathlib.Path(raw)
        c2_records = fixture_dispatches("C2")
        c2_result = write_fixture(root, "C2", c2_records)
        c2 = analyze(c2_result)
        equal(c2["dispatch_identity"]["plan_dispatch_count"], 1)
        equal(c2["dispatch_identity"]["agent_tool_use_count"], 4)
        equal(c2["dispatch_identity"]["non_plan_agent_tool_use_count"], 3)
        equal(c2["classification"], "COMPLETE")
        equal(c2["schema_version"], 2)
        equal(
            c2["dispatch_identity"]["dispatches"][0]["diagnostics"]["heading"],
            "## " + PLAN_STEM,
        )

        quoted = copy.deepcopy(c2_records)
        quoted[0]["message"]["content"][0]["input"]["prompt"] = (
            "The retained title was quoted mid-line: ## " + PLAN_STEM + "\n"
        )
        quote_dir = root / "quoted" / "result"
        (quote_dir.parent / "sessions").mkdir(parents=True)
        (quote_dir.parent / "sessions" / "parent.jsonl").write_text(
            json.dumps(quoted[0], ensure_ascii=False) + "\n", encoding="utf-8"
        )
        issues: list[str] = []
        found, _, _ = collect_agent_calls(parent_session_paths(quote_dir), issues, quote_dir)
        equal(len(found), 1)
        equal(found[0]["diagnostics"]["canonical_heading_match"], False)
        equal(issues, [])

        prewrite_state = json.loads(next((c2_result / "devlyn-snapshot").glob("runs/*/pipeline.state.json")).read_text())
        prewrite_state["phases"]["plan"] = {}
        prewrite_result = root / "prewrite" / "result"
        prewrite_state_path = prewrite_result / "devlyn-snapshot" / "runs" / "run" / "pipeline.state.json"
        prewrite_state_path.parent.mkdir(parents=True)
        prewrite_state_path.write_text(json.dumps(prewrite_state) + "\n")
        for source in ("timing.json", "attribution.json"):
            (prewrite_result / source).write_bytes((c2_result / source).read_bytes())
        prewrite_session = prewrite_result.parent / "sessions"
        prewrite_session.mkdir()
        (prewrite_session / "parent.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in c2_records)
        )
        prewrite = analyze(prewrite_result)
        equal(prewrite["dispatch_identity"]["plan_dispatch_count"], 1)
        equal(prewrite["evidence"]["complete"], True)
        equal(prewrite["product"]["eligible"], False)
        equal(
            prewrite["product"]["violations"],
            ["plan-dispatch-outside-authorization-window"],
        )
        equal(prewrite["classification"], "CONTRACT-VIOLATION")

        no_dispatch_result = root / "no-dispatch" / "result"
        no_dispatch_state = copy.deepcopy(prewrite_state)
        no_dispatch_state_path = (
            no_dispatch_result / "devlyn-snapshot" / "runs" / "run" / "pipeline.state.json"
        )
        no_dispatch_state_path.parent.mkdir(parents=True)
        no_dispatch_state_path.write_text(json.dumps(no_dispatch_state) + "\n")
        for source in ("timing.json", "attribution.json"):
            (no_dispatch_result / source).write_bytes((c2_result / source).read_bytes())
        no_dispatch = analyze(no_dispatch_result)
        equal(no_dispatch["evidence"]["complete"], False)
        equal(no_dispatch["classification"], "INCOMPLETE")

        # P-0091-A1: a heading-less but fully captured in-window Agent remains
        # the PLAN dispatch. Its adverse bytes cannot erase their own identity.
        adverse_result = write_fixture(
            root, "0090-C1-heading-less-mismatch", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        adverse_session = adverse_result.parent / "sessions" / "parent.jsonl"
        adverse_row = json.loads(adverse_session.read_text())
        adverse_row["message"]["content"][0]["input"]["prompt"] = (
            "$(cat /Users/aipalm/Documents/GitHub/devlyn-cli/.devlyn/plan.prompt)"
        )
        adverse_session.write_text(json.dumps(adverse_row) + "\n")
        adverse = analyze(adverse_result)
        equal(adverse["classification"], "CONTRACT-VIOLATION")
        equal(adverse["evidence"]["complete"], True)
        equal(adverse["dispatch_identity"]["plan_dispatch_count"], 1)
        equal(adverse["dispatch_identity"]["authorization_windows"][0]["status"], "BOUND")
        equal(
            adverse["dispatch_identity"]["dispatches"][0]["diagnostics"][
                "canonical_heading_match"
            ],
            False,
        )
        equal(adverse["delivery_attestation"][0]["match"], False)
        equal(
            adverse["product"]["violations"],
            ["delivered-prompt-digest-mismatch"],
        )

        # More than one captured top-level Agent in one authorization window
        # is complete product evidence, never a silently selected dispatch.
        multiple_result = write_fixture(
            root, "two-in-one-window", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        multiple_session = multiple_result.parent / "sessions" / "parent.jsonl"
        multiple_rows = [json.loads(multiple_session.read_text())]
        duplicate = copy.deepcopy(multiple_rows[0])
        duplicate["message"]["content"][0]["id"] = "second-in-window"
        duplicate["timestamp"] = "2026-08-02T02:59:00.000Z"
        multiple_rows.append(duplicate)
        multiple_session.write_text(
            "".join(json.dumps(row) + "\n" for row in multiple_rows)
        )
        multiple = analyze(multiple_result)
        equal(multiple["classification"], "CONTRACT-VIOLATION")
        equal(multiple["evidence"]["complete"], True)
        equal(multiple["dispatch_identity"]["plan_dispatch_count"], 2)
        equal(multiple["dispatch_identity"]["dispatches"], [])
        equal(
            multiple["dispatch_identity"]["authorization_windows"][0]["status"],
            "AMBIGUOUS",
        )
        equal(
            multiple["product"]["violations"],
            ["multiple-plan-agents-in-authorization-window"],
        )

        same_id_result = write_fixture(
            root, "same-id-two-in-one-window", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        same_id_session = same_id_result.parent / "sessions" / "parent.jsonl"
        same_id_rows = [json.loads(same_id_session.read_text())]
        same_id_duplicate = copy.deepcopy(same_id_rows[0])
        same_id_duplicate["timestamp"] = "2026-08-02T02:59:00.000Z"
        same_id_duplicate["message"]["content"][0]["input"]["prompt"] = "second"
        same_id_rows.append(same_id_duplicate)
        same_id_session.write_text(
            "".join(json.dumps(row) + "\n" for row in same_id_rows)
        )
        same_id = analyze(same_id_result)
        equal(same_id["classification"], "CONTRACT-VIOLATION")
        equal(same_id["evidence"]["complete"], True)
        equal(same_id["dispatch_identity"]["plan_dispatch_count"], 2)
        equal(
            same_id["dispatch_identity"]["authorization_windows"][0]["status"],
            "AMBIGUOUS",
        )
        equal(
            same_id["product"]["violations"],
            ["multiple-plan-agents-in-authorization-window"],
        )

        legacy_multiple_result = write_fixture(
            root, "legacy-two-in-one-window", [copy.deepcopy(c2_records[0])],
            source_name="C2", enrich_receipts=False,
        )
        legacy_multiple_session = (
            legacy_multiple_result.parent / "sessions" / "parent.jsonl"
        )
        legacy_multiple_rows = [json.loads(legacy_multiple_session.read_text())]
        legacy_duplicate = copy.deepcopy(legacy_multiple_rows[0])
        legacy_duplicate["message"]["content"][0]["id"] = "legacy-second-in-window"
        legacy_duplicate["timestamp"] = "2026-08-02T02:59:00.000Z"
        legacy_multiple_rows.append(legacy_duplicate)
        legacy_multiple_session.write_text(
            "".join(json.dumps(row) + "\n" for row in legacy_multiple_rows)
        )
        legacy_multiple = analyze(legacy_multiple_result)
        equal(legacy_multiple["classification"], "CONTRACT-VIOLATION")
        equal(legacy_multiple["evidence"]["complete"], True)
        equal(
            legacy_multiple["product"]["violations"],
            ["multiple-plan-agents-in-authorization-window"],
        )

        # Sidechain filtering applies only to Agent candidates. Nested writer
        # evidence remains visible as corroboration.
        sidechain_result = write_fixture(
            root, "sidechain-agent-writer", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        sidechain_session = sidechain_result.parent / "sessions" / "parent.jsonl"
        sidechain_rows = [json.loads(sidechain_session.read_text())]
        sidechain_rows.append({
            "timestamp": "2026-08-02T02:59:01.000Z",
            "parent_tool_use_id": "parent-agent",
            "message": {"content": [
                {
                    "type": "tool_use", "name": "Agent", "id": "nested-agent",
                    "input": {"subagent_type": "claude", "prompt": "nested"},
                },
                {
                    "type": "tool_use", "name": "Write", "id": "nested-writer",
                    "input": {"file_path": ".devlyn/plan.md", "content": "plan"},
                },
            ]},
        })
        sidechain_session.write_text(
            "".join(json.dumps(row) + "\n" for row in sidechain_rows)
        )
        sidechain = analyze(sidechain_result)
        equal(sidechain["classification"], "COMPLETE")
        equal(sidechain["dispatch_identity"]["agent_tool_use_count"], 1)
        equal(sidechain["dispatch_identity"]["sidechain_agent_tool_use_count"], 1)
        equal(len(sidechain["dispatch_identity"]["plan_md_writer_corroboration"]), 1)

        # A canonical PLAN heading may escalate captured off-ledger evidence;
        # it may not restore content as the in-window identity authority.
        outside_result = write_fixture(
            root, "heading-outside-window", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        outside_session = outside_result.parent / "sessions" / "parent.jsonl"
        outside_row = json.loads(outside_session.read_text())
        outside_row["timestamp"] = "2026-08-02T03:05:00.000Z"
        outside_session.write_text(json.dumps(outside_row) + "\n")
        outside = analyze(outside_result)
        equal(outside["classification"], "CONTRACT-VIOLATION")
        equal(outside["evidence"]["complete"], True)
        equal(outside["dispatch_identity"]["authorization_windows"][0]["status"], "MISSING")
        equal(len(outside["dispatch_identity"]["outside_authorization_plan_dispatches"]), 1)
        equal(
            outside["product"]["violations"],
            ["plan-dispatch-outside-authorization-window"],
        )

        malformed_time_result = write_fixture(
            root, "malformed-agent-time", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        malformed_time_session = malformed_time_result.parent / "sessions" / "parent.jsonl"
        malformed_time_row = json.loads(malformed_time_session.read_text())
        malformed_time_row["timestamp"] = "not-a-timestamp"
        malformed_time_session.write_text(json.dumps(malformed_time_row) + "\n")
        malformed_time = analyze(malformed_time_result)
        equal(malformed_time["classification"], "INCOMPLETE")
        equal(
            any(
                issue.startswith("dispatch-timestamp-malformed:")
                for issue in malformed_time["evidence"]["issues"]
            ),
            True,
        )

        malformed_receipt_result = write_fixture(
            root, "malformed-receipt-time", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        malformed_receipt_state_path = next(
            (malformed_receipt_result / "devlyn-snapshot").glob(
                "runs/*/pipeline.state.json"
            )
        )
        malformed_receipt_state = json.loads(malformed_receipt_state_path.read_text())
        malformed_receipt_state["phases"]["plan"]["started_at"] = "not-a-timestamp"
        malformed_receipt_state_path.write_text(json.dumps(malformed_receipt_state) + "\n")
        malformed_receipt = analyze(malformed_receipt_result)
        equal(malformed_receipt["classification"], "INCOMPLETE")
        equal(malformed_receipt["dispatch_identity"]["authorization_windows"], [])
        equal(
            "plan-receipt-schema-invalid" in malformed_receipt["evidence"]["issues"],
            True,
        )

        reversed_receipt_result = write_fixture(
            root, "reversed-receipt-window", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        reversed_receipt_state_path = next(
            (reversed_receipt_result / "devlyn-snapshot").glob(
                "runs/*/pipeline.state.json"
            )
        )
        reversed_receipt_state = json.loads(reversed_receipt_state_path.read_text())
        reversed_receipt_state["phases"]["plan"]["started_at"] = (
            "2026-08-02T03:05:00.000Z"
        )
        reversed_receipt_state_path.write_text(json.dumps(reversed_receipt_state) + "\n")
        reversed_receipt = analyze(reversed_receipt_result)
        equal(reversed_receipt["classification"], "INCOMPLETE")
        equal(reversed_receipt["ledger"]["receipts"][0]["schema"], "invalid")
        equal(reversed_receipt["dispatch_identity"]["authorization_windows"], [])

        c3_records = fixture_dispatches("C3")
        c3_prompts = [
            row["message"]["content"][0]["input"]["prompt"] for row in c3_records
        ]
        equal([len(prompt.encode("utf-8")) for prompt in c3_prompts], [6822, 3607, 1112])
        equal(
            [sha256_text(prompt) for prompt in c3_prompts],
            [row[5] for row in REAL_DISPATCH_FIXTURES["C3"]],
        )
        c3_result = write_fixture(root, "C3", c3_records)
        c3 = analyze(c3_result)
        equal(c3["dispatch_identity"]["plan_dispatch_count"], 3)
        equal(c3["classification"], "CONTRACT-VIOLATION")
        equal(c3["evidence"]["complete"], True)
        equal(c3["startup"]["startup_recomputed_ms"], 181191)
        equal(c3["startup"]["delta_ms"], 0)
        equal(c3["diagnostics"][0]["name"], "legacy-current-round-only-startup-truncation")
        equal(c3["diagnostics"][0]["current_round_only_ms"], 697569)
        equal(c3["diagnostics"][0]["delta_from_authoritative_ms"], 516378)
        equal(c3["decomposition"]["per_round"][0]["spw_to_agent_composition_gap_ms"], 42978)
        c3_region = c3["decomposition"][
            "plan_region_first_dispatch_to_final_legal_completion"
        ]
        equal(c3_region["started_at"], "2026-08-02T04:11:49.215Z")
        equal(c3_region["completed_at"], "2026-08-02T04:19:42.566Z")
        equal(c3_region["duration_ms"], 473351)

        overlap_result = write_fixture(
            root, "C3-overlapping-windows", copy.deepcopy(c3_records),
            source_name="C3",
        )
        overlap_state_path = next(
            (overlap_result / "devlyn-snapshot").glob("runs/*/pipeline.state.json")
        )
        overlap_state = json.loads(overlap_state_path.read_text())
        overlap_state["phases"]["plan"]["history"][0]["completed_at"] = (
            "2026-08-02T04:16:10.000Z"
        )
        overlap_state_path.write_text(json.dumps(overlap_state) + "\n")
        overlap = analyze(overlap_result)
        equal(overlap["classification"], "CONTRACT-VIOLATION")
        equal(overlap["evidence"]["complete"], True)
        equal(overlap["dispatch_identity"]["authorization_windows"][0]["status"], "AMBIGUOUS")
        equal(overlap["dispatch_identity"]["authorization_windows"][1]["status"], "AMBIGUOUS")
        equal(
            overlap["dispatch_identity"]["agent_candidates"][1][
                "authorization_window_indexes"
            ],
            [0, 1],
        )
        equal(
            "plan-authorization-windows-overlap" in overlap["product"]["violations"],
            True,
        )
        equal(
            "plan-agent-matches-multiple-authorization-windows"
            in overlap["product"]["violations"],
            True,
        )

        # P-0089-4 raw retained-shape replay: two exact four-key history
        # rows plus the pre-D1 current receipt remain schema-distinct. Their
        # missing D1 digests are diagnostic, while three retained Agent
        # deliveries conclusively prove the no-ship cap violation.
        c3_raw_result = write_fixture(
            root, "C3-raw-retained", c3_records,
            source_name="C3", enrich_receipts=False,
        )
        c3_raw = analyze(c3_raw_result)
        equal(c3_raw["dispatch_identity"]["plan_dispatch_count"], 3)
        equal(c3_raw["classification"], "CONTRACT-VIOLATION")
        equal(c3_raw["evidence"]["complete"], True)
        equal(c3_raw["product"]["eligible"], False)
        equal(c3_raw["product"]["violations"], ["plan-dispatch-cap-exceeded"])
        equal(
            [receipt["schema"] for receipt in c3_raw["ledger"]["receipts"]],
            [
                "legacy-pre-d1-four-key",
                "legacy-pre-d1-four-key",
                "legacy-pre-d1-current",
            ],
        )
        equal(
            [row["status"] for row in c3_raw["delivery_attestation"]],
            ["UNATTESTABLE:legacy-pre-d1-receipt"] * 3,
        )
        equal(c3_raw["diagnostics"][0]["name"], "legacy-pre-d1-plan-receipt-schema")
        equal(c3_raw["startup"]["startup_recomputed_ms"], 181191)
        equal(c3_raw["startup"]["delta_ms"], 0)
        equal(
            c3_raw["decomposition"]["per_round"][0]["spw_to_agent_composition_gap_ms"],
            42978,
        )
        c3_raw_region = c3_raw["decomposition"][
            "plan_region_first_dispatch_to_final_legal_completion"
        ]
        equal(c3_raw_region["started_at"], "2026-08-02T04:11:49.215Z")
        equal(c3_raw_region["completed_at"], "2026-08-02T04:19:42.566Z")
        equal(c3_raw_region["duration_ms"], 473351)

        structural_variants = {
            "history-not-array": "plan-ledger-structure:history-not-array",
            "history-row-not-object": (
                "plan-ledger-structure:history-row-not-object:0"
            ),
            "current-started-at-missing": (
                "plan-ledger-structure:current-started-at-missing"
            ),
            "nonzero-round-history-key-missing": (
                "plan-ledger-structure:history-key-missing-for-nonzero-round"
            ),
        }
        for variant, expected_issue in structural_variants.items():
            malformed_result = write_fixture(
                root, f"C3-{variant}", c3_records,
                source_name="C3", enrich_receipts=False,
            )
            state_path = next(
                (malformed_result / "devlyn-snapshot").glob(
                    "runs/*/pipeline.state.json"
                )
            )
            state = json.loads(state_path.read_text())
            plan = state["phases"]["plan"]
            if variant == "history-not-array":
                plan["history"] = {}
            elif variant == "history-row-not-object":
                plan["history"][0] = "not-an-object"
            elif variant == "current-started-at-missing":
                plan["started_at"] = None
            else:
                del plan["history"]
            state_path.write_text(json.dumps(state) + "\n")
            malformed = analyze(malformed_result)
            equal(malformed["classification"], "INCOMPLETE")
            equal(expected_issue in malformed["evidence"]["issues"], True)

        malformed_legacy_result = write_fixture(
            root, "C3-malformed-legacy-shape", c3_records,
            source_name="C3", enrich_receipts=False,
        )
        malformed_state_path = next(
            (malformed_legacy_result / "devlyn-snapshot").glob(
                "runs/*/pipeline.state.json"
            )
        )
        malformed_state = json.loads(malformed_state_path.read_text())
        malformed_state["phases"]["plan"]["triggered_by"] = 7
        malformed_state_path.write_text(json.dumps(malformed_state) + "\n")
        malformed_legacy = analyze(malformed_legacy_result)
        equal(malformed_legacy["classification"], "INCOMPLETE")
        equal(
            malformed_legacy["ledger"]["receipts"][-1]["schema"], "invalid"
        )
        equal(
            "plan-receipt-schema-invalid" in malformed_legacy["evidence"]["issues"],
            True,
        )

        f7_records = fixture_dispatches("F7C1")
        f7_result = write_fixture(root, "F7C1", f7_records, rounds=[1])
        f7 = analyze(f7_result)
        equal(f7["round_continuity"][0]["name"], "round-continuity-missing-prior-receipts")
        equal(f7["round_continuity"][0]["missing_prior_rounds"], [0])

        # Raw retained-shape replay of the engine-bearing pre-D1 variant
        # (real F7/C1 current-entry keys): legacy, unattestable — never
        # schema-invalid, never a digest MISMATCH.
        f7_raw_result = write_fixture(
            root, "F7C1-raw-retained", f7_records,
            source_name="F7C1", enrich_receipts=False,
        )
        f7_raw = analyze(f7_raw_result)
        equal(
            [receipt["schema"] for receipt in f7_raw["ledger"]["receipts"]],
            ["legacy-pre-d1-current"],
        )
        equal(
            f7_raw["delivery_attestation"][0]["status"],
            "UNATTESTABLE:legacy-pre-d1-receipt",
        )
        equal("plan-receipt-schema-invalid" in f7_raw["evidence"]["issues"], False)
        equal(f7_raw["diagnostics"][0]["name"], "legacy-pre-d1-plan-receipt-schema")
        equal(f7_raw["classification"], "INCOMPLETE")
        equal(f7_raw["round_continuity"][0]["name"], "round-continuity-missing-prior-receipts")
        equal(f7_raw["startup"]["delta_ms"], 0)

        expected_startups = {"F7C1": 213270, "F7C2": 154197, "F12C1": 156297, "C3": 181191}
        for name, expected in expected_startups.items():
            if name == "F7C1":
                payload = f7
            elif name == "C3":
                payload = c3
            else:
                fixture = write_fixture(root, name, [])
                payload = analyze(fixture)
            equal(payload["startup"]["startup_recomputed_ms"], expected)
            equal(payload["startup"]["delta_ms"], 0)
            equal(payload["startup"]["status"], "PASS")

        flipped_result = write_fixture(
            root, "C2-flipped-source", c2_records, source_name="C2"
        )
        flipped_session = flipped_result.parent / "sessions" / "parent.jsonl"
        flipped_rows = [json.loads(line) for line in flipped_session.read_text().splitlines()]
        prompt_input = flipped_rows[0]["message"]["content"][0]["input"]
        before_prompt = prompt_input["prompt"].encode("utf-8")
        prompt_input["prompt"] = prompt_input["prompt"].replace("<role>", "<rolf>", 1)
        equal(len(prompt_input["prompt"].encode("utf-8")), len(before_prompt))
        flipped_session.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in flipped_rows)
        )
        flipped = analyze(flipped_result)
        equal(flipped["classification"], "CONTRACT-VIOLATION")
        equal(flipped["delivery_attestation"][0]["match"], False)

        missing_result = write_fixture(
            root, "C2-missing-source", c2_records, source_name="C2"
        )
        (missing_result.parent / "sessions" / "parent.jsonl").unlink()
        missing = analyze(missing_result)
        equal(missing["classification"], "INCOMPLETE")
        equal("missing-delivery-evidence" in missing["evidence"]["issues"], True)

        # P-0089-6 end-to-end: renderer output bytes -> stdout digest -> SPW
        # receipt -> retained Agent prompt -> oracle delivery comparison.
        repo = pathlib.Path(__file__).resolve().parents[3]
        renderer = repo / "config/skills/_shared/phase-prompt-render.py"
        spw = repo / "config/skills/_shared/state-phase-write.py"
        e2e_root = root / "p0089-6-e2e"
        inputs = e2e_root / "inputs"
        inputs.mkdir(parents=True)
        adapter = inputs / "adapter.md"
        canonical = inputs / "plan.md"
        context = inputs / "context"
        rendered = e2e_root / ".devlyn" / "plan.prompt"
        rendered.parent.mkdir()
        adapter.write_bytes(b"adapter\n")
        canonical.write_text("# " + PLAN_STEM + "\n", encoding="utf-8")
        context.write_bytes(b"task-context\n")
        render_run = subprocess.run(
            [
                sys.executable, str(renderer), "--adapter", str(adapter),
                "--canonical-body", str(canonical), "--task-context", str(context),
                "--output", str(rendered),
            ],
            capture_output=True, text=True, check=False,
        )
        equal(render_run.returncode, 0)
        rendered_digest = render_run.stdout.strip()
        e2e_result = e2e_root / "result"
        e2e_state_path = (
            e2e_result / "devlyn-snapshot" / "runs" / "run" / "pipeline.state.json"
        )
        e2e_state_path.parent.mkdir(parents=True)
        e2e_state_path.write_text('{"phases": {}}\n', encoding="utf-8")
        spawn_run = subprocess.run(
            [
                sys.executable, str(spw), "--devlyn-dir", str(e2e_state_path.parent),
                "--phase", "plan", "spawn", "--round", "0", "--engine", "claude",
                "--model", "plan-test-model", "--prompt-sha256", rendered_digest,
            ],
            capture_output=True, text=True, check=False, cwd=repo,
        )
        equal(spawn_run.returncode, 0)
        complete_run = subprocess.run(
            [
                sys.executable, str(spw), "--devlyn-dir", str(e2e_state_path.parent),
                "--phase", "plan", "complete", "--verdict", "PASS",
            ],
            capture_output=True, text=True, check=False, cwd=repo,
        )
        equal(complete_run.returncode, 0)
        e2e_state = json.loads(e2e_state_path.read_text())
        e2e_plan = e2e_state["phases"]["plan"]
        equal(e2e_plan["prompt_sha256"], rendered_digest)
        started = parse_time(e2e_plan["started_at"])
        invoke = started - dt.timedelta(milliseconds=100)
        invoke_text = invoke.strftime("%Y-%m-%dT%H:%M:%S.") + f"{invoke.microsecond // 1000:03d}Z"
        (e2e_result / "timing.json").write_text(
            json.dumps({"schema_version": 2, "invoke_started_at": invoke_text}) + "\n"
        )
        (e2e_result / "attribution.json").write_text('{"startup_ms": 100}\n')
        e2e_session = e2e_result.parent / "sessions" / "parent.jsonl"
        e2e_session.parent.mkdir()
        e2e_record = {
            "timestamp": e2e_plan["started_at"],
            "message": {"content": [{
                "type": "tool_use", "name": "Agent", "id": "p0089-6",
                "input": {"subagent_type": "general-purpose", "prompt": rendered.read_text()},
            }]},
        }
        e2e_session.write_text(json.dumps(e2e_record) + "\n")
        e2e = analyze(e2e_result)
        equal(e2e["classification"], "COMPLETE")
        equal(e2e["delivery_attestation"][0]["match"], True)

        output, written = write_oracle(c2_result)
        first = output.read_bytes()
        output, repeated = write_oracle(c2_result)
        equal(written, repeated)
        equal(output.read_bytes(), first)

    print(f"SELFTEST PASS: {assertions} assertions")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", nargs="?", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.result_dir is not None:
            parser.error("result_dir is not allowed with --self-test")
        return self_test()
    if args.result_dir is None:
        parser.error("result_dir is required unless --self-test")
    result_dir = resolve_result_dir(args.result_dir)
    if not result_dir.is_dir():
        parser.error(f"result_dir is not a directory: {result_dir}")
    output, payload = write_oracle(result_dir)
    print(output)
    return {"COMPLETE": 0, "CONTRACT-VIOLATION": 1, "INCOMPLETE": 2}[payload["classification"]]


if __name__ == "__main__":
    raise SystemExit(main())
