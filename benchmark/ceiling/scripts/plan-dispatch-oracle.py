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
    try:
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except OverflowError as exc:
        raise ValueError("timestamp missing or malformed") from exc


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
) -> tuple[list[dict], list[dict], int, list[dict]]:
    candidates: list[dict] = []
    tool_results: list[dict] = []
    sidechain_agent_count = 0
    writer_evidence: list[dict] = []
    pending_agent_references: list[tuple[str, str, int]] = []
    for path in session_paths:
        try:
            source = str(path.relative_to(result_dir.parent))
            source_valid = bool(source)
        except ValueError:
            source = str(path)
            source_valid = False
            issues.append(f"parent-session-shape:source-outside-result:{path.name}:0")

        def shape_issue(code: str, line_number: int) -> str:
            issue = f"parent-session-shape:{code}:{path.name}:{line_number}"
            issues.append(issue)
            return issue

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
            if not isinstance(record, dict):
                shape_issue("record-not-object", line_number)
                continue
            if "message" not in record:
                referenced_ids: set[str] = set()
                for container in (record, record.get("attachment")):
                    if not isinstance(container, dict):
                        continue
                    hook_name = container.get("hookName")
                    if (
                        isinstance(hook_name, str)
                        and hook_name in {"PreToolUse:Agent", "PostToolUse:Agent"}
                    ):
                        for id_key in ("toolUseID", "tool_use_id"):
                            referenced_id = container.get(id_key)
                            if isinstance(referenced_id, str):
                                referenced_ids.add(referenced_id)
                record_type = record.get("type")
                referenced_id = record.get("tool_use_id")
                if (
                    isinstance(record_type, str)
                    and (record_type == "system" or record_type.startswith("task_"))
                    and isinstance(referenced_id, str)
                    and ("subagent_type" in record or "prompt" in record)
                ):
                    referenced_ids.add(referenced_id)
                pending_agent_references.extend(
                    (referenced_id, source, line_number)
                    for referenced_id in referenced_ids
                )
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                shape_issue("message-not-object", line_number)
                continue
            content = message.get("content")
            if isinstance(content, str):
                continue
            if not isinstance(content, list):
                shape_issue("content-not-array-or-string", line_number)
                continue
            for block in content:
                if not isinstance(block, dict):
                    shape_issue("content-block-not-object", line_number)
                    continue
                block_type = block.get("type")
                if not isinstance(block_type, str) or not block_type:
                    shape_issue("content-block-type-malformed", line_number)
                    continue
                if block_type not in {"tool_result", "tool_use"}:
                    continue

                parent_marker = record.get("parent_tool_use_id")
                parent_marker_valid = (
                    parent_marker is None
                    or (isinstance(parent_marker, str) and bool(parent_marker))
                )
                if not parent_marker_valid:
                    shape_issue("parent-tool-use-id-malformed", line_number)
                    continue
                is_top_level = parent_marker is None

                if block_type == "tool_result":
                    if not is_top_level:
                        continue
                    role = message.get("role")
                    role_valid = isinstance(role, str) and bool(role)
                    if not role_valid:
                        shape_issue("message-role-malformed", line_number)
                    tool_use_id = block.get("tool_use_id")
                    tool_use_id_valid = (
                        isinstance(tool_use_id, str) and bool(tool_use_id)
                    )
                    if not tool_use_id_valid:
                        shape_issue("tool-result-id-malformed", line_number)
                    is_error_present = "is_error" in block
                    is_error = block.get("is_error")
                    tool_results.append({
                        "tool_use_id": tool_use_id,
                        "tool_use_id_present": "tool_use_id" in block,
                        "tool_use_id_valid": tool_use_id_valid,
                        "source": source,
                        "source_valid": source_valid,
                        "source_line": line_number,
                        "role": role,
                        "role_valid": role_valid,
                        "parent_tool_use_id_valid": parent_marker_valid,
                        "is_error_present": is_error_present,
                        "is_error": is_error,
                    })
                    continue
                tool_name = block.get("name")
                tool_name_valid = isinstance(tool_name, str) and bool(tool_name)
                if not tool_name_valid:
                    shape_issue("tool-use-name-malformed", line_number)
                    continue
                if tool_name == "Agent":
                    if not is_top_level:
                        sidechain_agent_count += 1
                        continue
                    role = message.get("role")
                    role_valid = isinstance(role, str) and bool(role)
                    if not role_valid:
                        shape_issue("message-role-malformed", line_number)
                    tool_input = block.get("input")
                    agent_input_valid = isinstance(tool_input, dict)
                    if not agent_input_valid:
                        shape_issue("agent-input-not-object", line_number)
                    agent_input = tool_input if agent_input_valid else {}
                    prompt = agent_input.get("prompt")
                    tool_id = block.get("id")
                    tool_id_valid = isinstance(tool_id, str) and bool(tool_id)
                    if not tool_id_valid:
                        shape_issue("agent-tool-use-id-malformed", line_number)
                    timestamp = record.get("timestamp")
                    subagent_type_present = "subagent_type" in agent_input
                    subagent_type = agent_input.get("subagent_type")
                    subagent_type_valid = (
                        not subagent_type_present
                        or (isinstance(subagent_type, str) and bool(subagent_type))
                    )
                    if subagent_type_present and not subagent_type_valid:
                        shape_issue("agent-subagent-type-malformed", line_number)
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
                        "tool_use_id_present": "id" in block,
                        "tool_use_id_valid": tool_id_valid,
                        "timestamp": timestamp,
                        "source": source,
                        "source_valid": source_valid,
                        "source_line": line_number,
                        "role": role,
                        "role_valid": role_valid,
                        "parent_tool_use_id_valid": parent_marker_valid,
                        "tool_name_valid": tool_name_valid,
                        "agent_input_valid": agent_input_valid,
                        "subagent_type": subagent_type,
                        "subagent_type_valid": subagent_type_valid,
                        "delivered_prompt_sha256": delivered_digest,
                        "mode_present": "mode" in agent_input,
                        "run_in_background_present": "run_in_background" in agent_input,
                        "run_in_background": agent_input.get("run_in_background"),
                        "diagnostics": {
                            "canonical_heading_match": heading is not None,
                            "heading": heading,
                        },
                    })
                    continue
                if tool_name in {"Write", "Edit"}:
                    tool_input = block.get("input")
                    if not isinstance(tool_input, dict):
                        shape_issue("writer-input-not-object", line_number)
                        continue
                    target_key = (
                        "file_path" if "file_path" in tool_input
                        else "path" if "path" in tool_input
                        else None
                    )
                    target = tool_input.get(target_key) if target_key else None
                    if not isinstance(target, str) or not target:
                        shape_issue("writer-target-malformed", line_number)
                        continue
                    if (
                        target == ".devlyn/plan.md" or target.endswith("/.devlyn/plan.md")
                    ):
                        writer_evidence.append(
                            {"source": path.name, "line": line_number, "tool": tool_name}
                        )

    known_agent_ids = {
        row["tool_use_id"]
        for row in candidates + tool_results
        if row["tool_use_id_valid"]
    }
    orphan_records: set[tuple[str, int]] = set()
    for referenced_id, source, line_number in pending_agent_references:
        record_key = (source, line_number)
        if referenced_id not in known_agent_ids and record_key not in orphan_records:
            issues.append(
                f"parent-session-shape:agent-evidence-orphan:"
                f"{source}:{line_number}"
            )
            orphan_records.add(record_key)

    def order_key(dispatch: dict) -> tuple:
        try:
            timestamp = parse_time(dispatch["timestamp"])
        except (TypeError, ValueError):
            issues.append(f"dispatch-timestamp-malformed:{dispatch['tool_use_id']}")
            timestamp = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
        return timestamp, dispatch["source"], dispatch["source_line"]

    candidates = sorted(candidates, key=order_key)
    uses_by_key: dict[tuple[str, object], list[dict]] = {}
    results_by_key: dict[tuple[str, object], list[dict]] = {}
    for candidate in candidates:
        if (
            candidate["source_valid"]
            and candidate["tool_use_id_valid"]
        ):
            uses_by_key.setdefault(
                (candidate["source"], candidate["tool_use_id"]), []
            ).append(candidate)
    for result in tool_results:
        if (
            result["source_valid"]
            and result["tool_use_id_valid"]
        ):
            results_by_key.setdefault(
                (result["source"], result["tool_use_id"]), []
            ).append(result)
    for candidate in candidates:
        key = (candidate["source"], candidate["tool_use_id"])
        key_valid = (
            candidate["source_valid"]
            and candidate["tool_use_id_valid"]
        )
        matching_results = results_by_key.get(key, []) if key_valid else []
        candidate["duplicate_tool_use_id"] = (
            key_valid and len(uses_by_key[key]) > 1
        )
        candidate["matching_tool_result_count"] = len(matching_results)
        candidate["matching_tool_result_lines"] = [
            result["source_line"] for result in matching_results
        ]
        if len(matching_results) != 1:
            candidate["acceptance_disposition"] = (
                "INCOMPLETE" if not matching_results else "CONTRACT-VIOLATION"
            )
            continue
        result = matching_results[0]
        is_error = result["is_error"]
        if not result["is_error_present"] or is_error is None or is_error is False:
            candidate["acceptance_disposition"] = "ACCEPTED"
        elif is_error is True:
            candidate["acceptance_disposition"] = "REJECTED"
        else:
            candidate["acceptance_disposition"] = "INCOMPLETE"
    return candidates, tool_results, sidechain_agent_count, writer_evidence


def bind_dispatches(
    receipts: list[dict], candidates: list[dict],
) -> tuple[
    list[dict], dict[int, dict], list[dict], list[dict], list[str], list[str],
]:
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
            matching_receipt = next(
                receipt
                for receipt in receipts
                if receipt["_ledger_index"] == window["ledger_index"]
            )
            expected_digest = matching_receipt.get("prompt_sha256")
            shape_violations = []
            if (
                matching_receipt["_schema"] == "d1-complete"
                and candidate["delivered_prompt_sha256"] != expected_digest
            ):
                shape_violations.append("prompt-digest-mismatch")
            if candidate["mode_present"]:
                shape_violations.append("mode-present")
            if (
                not candidate["run_in_background_present"]
                or candidate["run_in_background"] is not False
            ):
                shape_violations.append("run-in-background-not-boolean-false")
            candidate.setdefault("authorization_evaluations", []).append({
                "ledger_index": window["ledger_index"],
                "shape_valid": not shape_violations,
                "shape_violations": shape_violations,
            })
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
    evidence_issues: list[str] = []
    for window in windows:
        ledger_index = window["ledger_index"]
        candidate_ids = [candidate["tool_use_id"] for candidate in window["_candidates"]]
        attempt_contract_violation = False
        attempt_incomplete = False
        for candidate in window["_candidates"]:
            evaluation = next(
                row for row in candidate["authorization_evaluations"]
                if row["ledger_index"] == ledger_index
            )
            if candidate["duplicate_tool_use_id"]:
                violations.append("duplicate-agent-tool-use-id")
                attempt_contract_violation = True
            if candidate["matching_tool_result_count"] > 1:
                violations.append("multiple-agent-tool-results")
                attempt_contract_violation = True
            if candidate["acceptance_disposition"] == "REJECTED":
                violations.append("rejected-plan-agent-attempt")
                attempt_contract_violation = True
            elif candidate["acceptance_disposition"] == "INCOMPLETE":
                issue = (
                    "missing-agent-tool-result"
                    if candidate["matching_tool_result_count"] == 0
                    else "malformed-agent-tool-result-is-error"
                )
                evidence_issues.append(issue)
                attempt_incomplete = True
            if not evaluation["shape_valid"]:
                violations.append("plan-agent-call-shape-invalid")
                if "prompt-digest-mismatch" in evaluation["shape_violations"]:
                    violations.append("delivered-prompt-digest-mismatch")
                attempt_contract_violation = True
        if (
            len(window["_candidates"]) > 1
            and not attempt_contract_violation
            and not attempt_incomplete
        ):
            violations.append("multiple-plan-agents-in-authorization-window")
            attempt_contract_violation = True
        if len(window["_candidates"]) > 1:
            ambiguous_indexes.add(ledger_index)
        if ledger_index in ambiguous_indexes:
            status = "AMBIGUOUS"
        elif not window["_candidates"]:
            status = "MISSING"
        else:
            status = "BOUND"
            bindings[ledger_index] = window["_candidates"][0]
        structural_ambiguity = bool(overlap_indexes[ledger_index]) or any(
            len(candidate["authorization_window_indexes"]) > 1
            for candidate in window["_candidates"]
        )
        if structural_ambiguity or attempt_contract_violation:
            window_classification = "CONTRACT-VIOLATION"
        elif attempt_incomplete or not window["_candidates"]:
            window_classification = "INCOMPLETE"
        else:
            window_classification = "COMPLETE"
        public_windows.append({
            "ledger_index": ledger_index,
            "started_at": window["started_at"],
            "completed_at": window["completed_at"],
            "candidate_tool_use_ids": candidate_ids,
            "overlapping_ledger_indexes": sorted(overlap_indexes[ledger_index]),
            "status": status,
            "classification": window_classification,
        })
    if outside_plan:
        violations.append("plan-dispatch-outside-authorization-window")
    return (
        public_windows, bindings, outside_plan, non_plan,
        sorted(set(violations)), sorted(set(evidence_issues)),
    )


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
    candidates, tool_results, sidechain_agent_count, writer_evidence = collect_agent_calls(
        parent_session_paths(result_dir), evidence_issues, result_dir,
    )
    (
        authorization_windows, bindings, outside_plan, non_plan,
        binding_violations, binding_evidence_issues,
    ) = (
        bind_dispatches(receipts, candidates)
    )
    product_violations.extend(binding_violations)
    evidence_issues.extend(binding_evidence_issues)
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
        "CONTRACT-VIOLATION" if binding_violations
        else "INCOMPLETE" if not evidence_complete
        else "COMPLETE" if product_eligible
        else "CONTRACT-VIOLATION"
    )
    public_receipts = [
        {key: value for key, value in receipt.items() if not key.startswith("_")}
        | {"schema": receipt["_schema"], "ledger_index": receipt["_ledger_index"]}
        for receipt in receipts
    ]
    return {
        "schema_version": 3,
        "classification": classification,
        "evidence": {"complete": evidence_complete, "issues": evidence_issues},
        "product": {"eligible": product_eligible, "violations": product_violations},
        "result_dir": str(result_dir),
        "state_source": state_source,
        "dispatch_identity": {
            "authority": "ledger-window+top-level-parent-Agent",
            "plan_dispatch_count": len(plan_candidates),
            "agent_tool_use_count": len(candidates),
            "tool_result_count": len(tool_results),
            "sidechain_agent_tool_use_count": sidechain_agent_count,
            "non_plan_agent_tool_use_count": len(non_plan),
            "dispatches": bound_dispatches,
            "agent_candidates": candidates,
            "agent_tool_results": tool_results,
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

# zlib-compressed JSON containing the exact iter-0091 Stage B Canary 1 and
# Canary 2 PLAN prompts. The retained source lines and result shapes below
# keep the replay hermetic.
REAL_0091_STAGE_B_PROMPTS_B64 = (
    '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'
    'qJXaathxJm04/NmuWqeT2FRk9w7FrRTbj7nZ95BUOss9gZ+ayYfI/ob1tc2LyasqbWnqOPnWN9+1i4kWh0ma+1kp2KCR8z+YN3lQ'
    'xDII6ETmtCeoZyhhL0vpxyMWnUVamEgcSn6efPnlP36ZcHLSQeM2EQbmyXuxIJJ/LV8grH5JNC9tSdYEyFLW1eX9vuZqtD/G5oV8'
    'G5BEvVtZ52K71JEw8rvRe8kOCmF92hgf0OcpkRZaXS5RM2sDm2K+BsdIBLdPP9mKoAJAqfaQS/rNADRwgs9Vy/xXepmd7GkGMfq/'
    'oJvhazEZlmRfPfl5ucUyWPFBsnTa8QQL/Gy5zrSTtte6OCg7kuSFfpvZe8gJXQk+K1Et70/42DNOKZjxMoWPnhBmHtp0dvLLz7/I'
    'QrMSeeN4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4z+F4'
    'z+F4z+F4z+F4z+F4z+F4z+H/2T2HXUU92us0faNF8//Ruw/f/rq/85lXIM57+RjxexIxm8H5+Q6c5/NvE2jmwkoP1mfJTuL25Mk8'
    'yeGz+VDsC8z2GEmFsG4YAEtHATvvWEZWJagySWPWlU38+ISFH1zG2B1j7wj67ZbRjWjTDq/YmDNGn3FVgyCg37N2HLGrlvpWHiAS'
    'dnXZMwa3jtRXmiaYyqMX6sRt6RoShWK6lwNLUsu93mWjhzp6bcNtxkKwV5ZmxFNWa9/pIxQiTJ/IOfwCKh+IIEz39XLFPKUIBOSn'
    'ZoVFTJQ1dFxir3Vrh7YHdacNsT/xCz1Pt0seql2yNmsWwbtlp2mtyukf0Gq+jUPl9cn7L8IRlab0gvd1yUQ+5ZdDKe7L3+rC3FBs'
    'pWaTkus3LfnbrtiUxnzqmg3fG/M388nbNuYXDvt5Vu4u3fz8X0PUzto='
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
            "message": {"role": "assistant", "content": [
                {
                    "type": "tool_use", "name": "Agent", "id": tool_id,
                    "input": {
                        "subagent_type": subagent_type,
                        "prompt": prompt,
                        "run_in_background": False,
                    },
                },
                {"type": "tool_result", "tool_use_id": tool_id},
            ]},
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


def write_stage_b_fixture(root: pathlib.Path, name: str) -> pathlib.Path:
    prompts = json.loads(zlib.decompress(base64.b64decode(
        "".join(REAL_0091_STAGE_B_PROMPTS_B64)
    )).decode("utf-8"))
    fixtures = {
        "canary1": {
            "invoke": "2026-08-03T18:23:19.117640Z",
            "startup_ms": 96219,
            "started_at": "2026-08-03T18:24:55.337Z",
            "completed_at": "2026-08-03T18:26:57.070Z",
            "duration_ms": 121733,
            "digest": "709c87e76696f7c231ec8550e7d066102a8cf9c134b0966279d96daf97d29c15",
            "rows": {
                94: {
                    "timestamp": "2026-08-03T18:25:24.507Z",
                    "message": {"role": "assistant", "content": [{
                        "type": "tool_use", "name": "Agent",
                        "id": "toolu_011v8BKUh3wK1jN5SY1HhR46",
                        "input": {
                            "subagent_type": "claude", "prompt": prompts[0],
                            "run_in_background": False,
                        },
                    }]},
                },
                108: {
                    "timestamp": "2026-08-03T18:26:57.063Z",
                    "message": {"role": "assistant", "content": [{
                        "type": "tool_result",
                        "tool_use_id": "toolu_011v8BKUh3wK1jN5SY1HhR46",
                    }]},
                },
            },
        },
        "canary2": {
            "invoke": "2026-08-03T18:30:31.408337Z",
            "startup_ms": 131485,
            "started_at": "2026-08-03T18:32:42.893Z",
            "completed_at": "2026-08-03T18:35:11.526Z",
            "duration_ms": 148633,
            "digest": "0078aefb16635a4d817d0f1027c8e27647cb28240f0c63cb8e1f8ab65d4d5ad2",
            "rows": {
                129: {
                    "timestamp": "2026-08-03T18:33:13.729Z",
                    "message": {"role": "assistant", "content": [{
                        "type": "tool_use", "name": "Agent",
                        "id": "toolu_01VHyvLgF7naatc6TGUxjP6q",
                        "input": {
                            "subagent_type": "claude", "prompt": prompts[1],
                            "mode": "bypassAll",
                        },
                    }]},
                },
                130: {
                    "timestamp": "2026-08-03T18:33:13.731Z",
                    "message": {"role": "assistant", "content": [{
                        "type": "tool_result",
                        "tool_use_id": "toolu_01VHyvLgF7naatc6TGUxjP6q",
                        "is_error": True,
                    }]},
                },
                131: {
                    "timestamp": "2026-08-03T18:33:42.402Z",
                    "message": {"role": "assistant", "content": [{
                        "type": "tool_use", "name": "Agent",
                        "id": "toolu_01KTY3tPwJ8XPs5xT89unHE6",
                        "input": {
                            "subagent_type": "claude", "prompt": prompts[1],
                            "mode": "bypassPermissions",
                        },
                    }]},
                },
                134: {
                    "timestamp": "2026-08-03T18:33:42.499Z",
                    "message": {"role": "assistant", "content": [{
                        "type": "tool_result",
                        "tool_use_id": "toolu_01KTY3tPwJ8XPs5xT89unHE6",
                    }]},
                },
            },
        },
    }
    fixture = fixtures[name]
    result = root / f"0091-stage-b-{name}" / "result"
    state_path = result / "devlyn-snapshot" / "runs" / "run" / "pipeline.state.json"
    state_path.parent.mkdir(parents=True)
    state = {"phases": {"plan": {
        "started_at": fixture["started_at"],
        "completed_at": fixture["completed_at"],
        "duration_ms": fixture["duration_ms"],
        "verdict": "PASS", "round": 0, "triggered_by": None,
        "engine": "claude", "model_requested": "claude-sonnet-5",
        "prompt_sha256": fixture["digest"], "model_effective": None,
    }}}
    state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
    (result / "timing.json").write_text(json.dumps({
        "schema_version": 2, "invoke_started_at": fixture["invoke"],
    }) + "\n", encoding="utf-8")
    (result / "attribution.json").write_text(json.dumps({
        "startup_ms": fixture["startup_ms"],
    }) + "\n", encoding="utf-8")
    session = result.parent / "sessions" / "parent.jsonl"
    session.parent.mkdir()
    numbered_rows = fixture["rows"]
    session.write_text("".join(
        json.dumps(numbered_rows.get(line, {
            "message": {"role": "assistant", "content": []},
        }), ensure_ascii=False) + "\n"
        for line in range(1, max(numbered_rows) + 1)
    ), encoding="utf-8")
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
        equal(c2["schema_version"], 3)
        equal(
            c2["dispatch_identity"]["dispatches"][0]["diagnostics"]["heading"],
            "## " + PLAN_STEM,
        )

        absent = object()
        same_id = object()
        retained_prompt = c2_records[0]["message"]["content"][0]["input"]["prompt"]

        def attempt_records(
            tool_id: object,
            *,
            timestamp: str = "2026-08-02T02:58:58.818Z",
            prompt: str = retained_prompt,
            mode: object = absent,
            background: object = False,
            result_count: int = 1,
            result_id: object = same_id,
            is_error: object = absent,
        ) -> list[dict]:
            tool_input = {"subagent_type": "claude", "prompt": prompt}
            if mode is not absent:
                tool_input["mode"] = mode
            if background is not absent:
                tool_input["run_in_background"] = background
            tool_use = {
                "type": "tool_use", "name": "Agent",
                "input": tool_input,
            }
            if tool_id is not absent:
                tool_use["id"] = tool_id
            rows = [{
                "timestamp": timestamp,
                "message": {"role": "assistant", "content": [tool_use]},
            }]
            for result_index in range(result_count):
                result = {"type": "tool_result"}
                resolved_result_id = tool_id if result_id is same_id else result_id
                if resolved_result_id is not absent:
                    result["tool_use_id"] = resolved_result_id
                if is_error is not absent:
                    result["is_error"] = is_error
                rows.append({
                    "timestamp": "2026-08-02T03:00:00.000Z",
                    "message": {"role": "assistant", "content": [result]},
                    "fixture_result_index": result_index,
                })
            return rows

        def analyze_attempts(name: str, rows: list[dict]) -> dict:
            result = write_fixture(
                root, name, [copy.deepcopy(c2_records[0])], source_name="C2"
            )
            session = result.parent / "sessions" / "parent.jsonl"
            session.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
            return analyze(result)

        def has_shape_issue(payload: dict, code: str) -> bool:
            return any(
                issue.startswith(f"parent-session-shape:{code}:")
                for issue in payload["evidence"]["issues"]
            )

        benign_record_rows = attempt_records("benign-no-message")
        benign_record_rows.append({"type": "summary", "summary": "complete"})
        benign_record = analyze_attempts("benign-no-message", benign_record_rows)
        equal(benign_record["classification"], "COMPLETE")
        equal(has_shape_issue(benign_record, "message-not-object"), False)
        equal(has_shape_issue(benign_record, "agent-evidence-orphan"), False)
        equal(benign_record["evidence"]["complete"], True)

        correlated_hook_rows = attempt_records("correlated-hook")
        correlated_hook_rows.append({
            "hookName": "PostToolUse:Agent",
            "toolUseID": "correlated-hook",
        })
        correlated_hook = analyze_attempts("correlated-hook", correlated_hook_rows)
        equal(correlated_hook["classification"], "COMPLETE")
        equal(has_shape_issue(correlated_hook, "agent-evidence-orphan"), False)

        orphan_hook_rows = attempt_records("orphan-hook")
        orphan_hook_rows.append({
            "attachment": {
                "hookName": "PreToolUse:Agent",
                "tool_use_id": "missing-agent",
            },
        })
        orphan_hook = analyze_attempts("orphan-hook", orphan_hook_rows)
        equal(orphan_hook["classification"], "INCOMPLETE")
        equal(has_shape_issue(orphan_hook, "agent-evidence-orphan"), True)

        same_basename_result = write_fixture(
            root, "same-basename", [copy.deepcopy(c2_records[0])], source_name="C2"
        )
        same_basename_sessions = same_basename_result.parent / "sessions"
        (same_basename_sessions / "parent.jsonl").write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in attempt_records("same-basename")
            ),
            encoding="utf-8",
        )
        for source_dir in ("a", "b"):
            orphan_session = same_basename_sessions / source_dir / "parent.jsonl"
            orphan_session.parent.mkdir()
            orphan_session.write_text(
                json.dumps(orphan_hook_rows[-1]) + "\n", encoding="utf-8"
            )
        same_basename = analyze(same_basename_result)
        same_basename_orphans = [
            issue for issue in same_basename["evidence"]["issues"]
            if issue.startswith("parent-session-shape:agent-evidence-orphan:")
        ]
        equal(len(same_basename_orphans), 2)

        unrelated_id_rows = attempt_records("unrelated-id")
        unrelated_id_rows.append({
            "hookName": "PostToolUse:Read",
            "tool_use_id": "unrelated-id",
        })
        unrelated_id = analyze_attempts("unrelated-id", unrelated_id_rows)
        equal(unrelated_id["classification"], "COMPLETE")
        equal(has_shape_issue(unrelated_id, "agent-evidence-orphan"), False)

        absent_subagent_rows = attempt_records("absent-subagent-type")
        del absent_subagent_rows[0]["message"]["content"][0]["input"][
            "subagent_type"
        ]
        absent_subagent = analyze_attempts("absent-subagent-type", absent_subagent_rows)
        absent_subagent_candidate = absent_subagent["dispatch_identity"][
            "agent_candidates"
        ][0]
        equal(absent_subagent["classification"], "COMPLETE")
        equal(has_shape_issue(absent_subagent, "agent-subagent-type-malformed"), False)
        equal(absent_subagent_candidate["subagent_type_valid"], True)
        equal(absent_subagent_candidate["acceptance_disposition"], "ACCEPTED")

        missing_identifiers = analyze_attempts(
            "missing-agent-and-result-identifiers",
            attempt_records(absent, result_id=absent),
        )
        equal(missing_identifiers["classification"], "INCOMPLETE")
        equal(
            missing_identifiers["dispatch_identity"]["agent_candidates"][0][
                "matching_tool_result_count"
            ],
            0,
        )
        equal(has_shape_issue(missing_identifiers, "agent-tool-use-id-malformed"), True)
        equal(has_shape_issue(missing_identifiers, "tool-result-id-malformed"), True)

        for label, malformed_id in (
            ("missing", absent),
            ("null", None),
            ("integer", 7),
            ("empty-string", ""),
        ):
            malformed_agent_id = analyze_attempts(
                f"malformed-agent-id-{label}",
                attempt_records(malformed_id),
            )
            malformed_agent = malformed_agent_id["dispatch_identity"][
                "agent_candidates"
            ][0]
            equal(malformed_agent_id["classification"], "INCOMPLETE")
            equal(malformed_agent["tool_use_id_valid"], False)
            equal(malformed_agent["matching_tool_result_count"], 0)
            equal(
                has_shape_issue(malformed_agent_id, "agent-tool-use-id-malformed"),
                True,
            )

            malformed_result_id = analyze_attempts(
                f"malformed-result-id-{label}",
                attempt_records("valid-agent-id", result_id=malformed_id),
            )
            malformed_result = malformed_result_id["dispatch_identity"][
                "agent_tool_results"
            ][0]
            equal(malformed_result_id["classification"], "INCOMPLETE")
            equal(malformed_result["tool_use_id_valid"], False)
            equal(
                malformed_result_id["dispatch_identity"]["agent_candidates"][0][
                    "matching_tool_result_count"
                ],
                0,
            )
            equal(
                has_shape_issue(malformed_result_id, "tool-result-id-malformed"),
                True,
            )

        invalid_id_bad_shape = analyze_attempts(
            "malformed-id-with-invalid-call-shape",
            attempt_records(absent, result_id=absent, mode="bypassPermissions"),
        )
        equal(invalid_id_bad_shape["classification"], "CONTRACT-VIOLATION")
        equal(
            invalid_id_bad_shape["dispatch_identity"]["agent_candidates"][0][
                "matching_tool_result_count"
            ],
            0,
        )
        equal(
            "plan-agent-call-shape-invalid"
            in invalid_id_bad_shape["product"]["violations"],
            True,
        )

        collection_shape_cases = (
            ("record", "record-not-object", "INCOMPLETE"),
            ("message", "message-not-object", "INCOMPLETE"),
            ("content", "content-not-array-or-string", "INCOMPLETE"),
            ("block", "content-block-not-object", "INCOMPLETE"),
            ("block-type", "content-block-type-malformed", "INCOMPLETE"),
            ("role", "message-role-malformed", "INCOMPLETE"),
            ("parent-marker", "parent-tool-use-id-malformed", "INCOMPLETE"),
            ("tool-name", "tool-use-name-malformed", "INCOMPLETE"),
            ("agent-input", "agent-input-not-object", "CONTRACT-VIOLATION"),
            ("subagent-type", "agent-subagent-type-malformed", "INCOMPLETE"),
            ("result-role", "message-role-malformed", "INCOMPLETE"),
            ("result-parent-marker", "parent-tool-use-id-malformed", "INCOMPLETE"),
        )
        for label, expected_issue, expected_classification in collection_shape_cases:
            rows = attempt_records(f"shape-{label}")
            use_row = rows[0]
            result_row = rows[1]
            if label == "record":
                rows[0] = []
            elif label == "message":
                use_row["message"] = None
            elif label == "content":
                use_row["message"]["content"] = 7
            elif label == "block":
                use_row["message"]["content"][0] = []
            elif label == "block-type":
                use_row["message"]["content"][0]["type"] = 7
            elif label == "role":
                use_row["message"]["role"] = 7
            elif label == "parent-marker":
                use_row["parent_tool_use_id"] = 7
            elif label == "tool-name":
                use_row["message"]["content"][0]["name"] = 7
            elif label == "agent-input":
                use_row["message"]["content"][0]["input"] = []
            elif label == "subagent-type":
                use_row["message"]["content"][0]["input"]["subagent_type"] = 7
            elif label == "result-role":
                result_row["message"]["role"] = 7
            else:
                result_row["parent_tool_use_id"] = 7
            malformed_shape = analyze_attempts(f"malformed-{label}", rows)
            equal(malformed_shape["classification"], expected_classification)
            equal(has_shape_issue(malformed_shape, expected_issue), True)

        malformed_writer_rows = attempt_records("malformed-writer")
        malformed_writer_rows.append({
            "timestamp": "2026-08-02T02:59:01.000Z",
            "message": {"role": "assistant", "content": [{
                "type": "tool_use", "name": "Write", "id": "writer",
                "input": {"file_path": 7},
            }]},
        })
        malformed_writer = analyze_attempts(
            "malformed-writer-target", malformed_writer_rows
        )
        equal(malformed_writer["classification"], "INCOMPLETE")
        equal(has_shape_issue(malformed_writer, "writer-target-malformed"), True)

        malformed_writer_input_rows = attempt_records("malformed-writer-input")
        malformed_writer_input_rows.append({
            "timestamp": "2026-08-02T02:59:01.000Z",
            "message": {"role": "assistant", "content": [{
                "type": "tool_use", "name": "Edit", "id": "writer",
                "input": None,
            }]},
        })
        malformed_writer_input = analyze_attempts(
            "malformed-writer-input", malformed_writer_input_rows
        )
        equal(malformed_writer_input["classification"], "INCOMPLETE")
        equal(
            has_shape_issue(malformed_writer_input, "writer-input-not-object"), True
        )

        source_scope_result = root / "source-scope" / "result"
        outside_source = root / "outside-source.jsonl"
        outside_source.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in attempt_records("outside-source")
            ),
            encoding="utf-8",
        )
        source_issues: list[str] = []
        source_candidates, source_results, _, _ = collect_agent_calls(
            [outside_source], source_issues, source_scope_result
        )
        equal(source_candidates[0]["source_valid"], False)
        equal(source_results[0]["source_valid"], False)
        equal(source_candidates[0]["matching_tool_result_count"], 0)
        equal(
            any(
                issue.startswith("parent-session-shape:source-outside-result:")
                for issue in source_issues
            ),
            True,
        )

        for label, is_error in (
            ("absent", absent), ("false", False), ("null", None),
        ):
            delayed = analyze_attempts(
                f"delayed-result-{label}",
                attempt_records(f"delayed-{label}", is_error=is_error),
            )
            equal(delayed["classification"], "COMPLETE")
            equal(
                delayed["dispatch_identity"]["agent_candidates"][0][
                    "acceptance_disposition"
                ],
                "ACCEPTED",
            )

        missing_tool_result = analyze_attempts(
            "missing-tool-result", attempt_records("missing-result", result_count=0)
        )
        equal(missing_tool_result["classification"], "INCOMPLETE")
        equal(
            missing_tool_result["dispatch_identity"]["authorization_windows"][0][
                "classification"
            ],
            "INCOMPLETE",
        )

        duplicate_id = analyze_attempts(
            "duplicate-tool-use-id",
            attempt_records("duplicate", result_count=0)
            + attempt_records(
                "duplicate", timestamp="2026-08-02T02:59:00.000Z", result_count=0
            ),
        )
        equal(duplicate_id["classification"], "CONTRACT-VIOLATION")
        equal("duplicate-agent-tool-use-id" in duplicate_id["product"]["violations"], True)

        malformed_role_duplicate_rows = (
            attempt_records("malformed-role-duplicate")
            + attempt_records(
                "malformed-role-duplicate",
                timestamp="2026-08-02T02:59:00.000Z",
                result_count=0,
            )
        )
        malformed_role_duplicate_rows[2]["message"]["role"] = 7
        malformed_role_duplicate = analyze_attempts(
            "malformed-role-duplicate-tool-use-id", malformed_role_duplicate_rows
        )
        equal(malformed_role_duplicate["classification"], "CONTRACT-VIOLATION")
        equal(
            [
                candidate["duplicate_tool_use_id"]
                for candidate in malformed_role_duplicate["dispatch_identity"][
                    "agent_candidates"
                ]
            ],
            [True, True],
        )
        equal(
            [
                candidate["matching_tool_result_count"]
                for candidate in malformed_role_duplicate["dispatch_identity"][
                    "agent_candidates"
                ]
            ],
            [1, 1],
        )
        equal(
            "duplicate-agent-tool-use-id"
            in malformed_role_duplicate["product"]["violations"],
            True,
        )

        multiple_results = analyze_attempts(
            "multiple-matching-results",
            attempt_records("multiple-results", result_count=2),
        )
        equal(multiple_results["classification"], "CONTRACT-VIOLATION")
        equal("multiple-agent-tool-results" in multiple_results["product"]["violations"], True)

        malformed_role_result_rows = attempt_records(
            "malformed-role-multiple-results", result_count=2
        )
        malformed_role_result_rows[2]["message"]["role"] = 7
        malformed_role_results = analyze_attempts(
            "malformed-role-multiple-results", malformed_role_result_rows
        )
        equal(malformed_role_results["classification"], "CONTRACT-VIOLATION")
        equal(
            malformed_role_results["dispatch_identity"]["agent_candidates"][0][
                "matching_tool_result_count"
            ],
            2,
        )
        equal(
            "multiple-agent-tool-results"
            in malformed_role_results["product"]["violations"],
            True,
        )

        malformed_result = analyze_attempts(
            "malformed-is-error",
            attempt_records("malformed-result", is_error="false"),
        )
        equal(malformed_result["classification"], "INCOMPLETE")

        accepted_plus_missing = analyze_attempts(
            "accepted-plus-missing",
            attempt_records("accepted")
            + attempt_records(
                "missing", timestamp="2026-08-02T02:59:00.000Z", result_count=0
            ),
        )
        equal(accepted_plus_missing["classification"], "INCOMPLETE")
        equal(accepted_plus_missing["product"]["violations"], [])

        many_accepted = analyze_attempts(
            "many-accepted",
            attempt_records("accepted-one")
            + attempt_records(
                "accepted-two", timestamp="2026-08-02T02:59:00.000Z"
            ),
        )
        equal(many_accepted["classification"], "CONTRACT-VIOLATION")
        equal(
            many_accepted["product"]["violations"],
            ["multiple-plan-agents-in-authorization-window"],
        )

        rejected = analyze_attempts(
            "rejected-only", attempt_records("rejected", is_error=True)
        )
        equal(rejected["classification"], "CONTRACT-VIOLATION")
        equal("rejected-plan-agent-attempt" in rejected["product"]["violations"], True)

        prompt_mismatch = analyze_attempts(
            "prompt-mismatch", attempt_records("prompt-mismatch", prompt="wrong bytes")
        )
        equal(prompt_mismatch["classification"], "CONTRACT-VIOLATION")

        for label, mode in (("string", "bypassPermissions"), ("null", None)):
            mode_present = analyze_attempts(
                f"mode-present-{label}",
                attempt_records(f"mode-{label}", mode=mode),
            )
            equal(mode_present["classification"], "CONTRACT-VIOLATION")

        for label, background, expected in (
            ("absent", absent, "CONTRACT-VIOLATION"),
            ("null", None, "CONTRACT-VIOLATION"),
            ("numeric-zero", 0, "CONTRACT-VIOLATION"),
            ("string-false", "false", "CONTRACT-VIOLATION"),
            ("boolean-false", False, "COMPLETE"),
        ):
            background_shape = analyze_attempts(
                f"background-{label}",
                attempt_records(f"background-{label}", background=background),
            )
            equal(background_shape["classification"], expected)

        for label, is_error in (("accepted", absent), ("rejected", True)):
            outside_heading = analyze_attempts(
                f"outside-heading-{label}",
                attempt_records(
                    f"outside-{label}",
                    timestamp="2026-08-02T03:05:00.000Z",
                    is_error=is_error,
                ),
            )
            equal(outside_heading["classification"], "CONTRACT-VIOLATION")
            equal(
                outside_heading["product"]["violations"],
                ["plan-dispatch-outside-authorization-window"],
            )

        outside_ordinary = analyze_attempts(
            "outside-ordinary",
            attempt_records(
                "outside-ordinary",
                timestamp="2026-08-02T03:05:00.000Z",
                prompt="ordinary non-PLAN call",
            ),
        )
        equal(outside_ordinary["classification"], "INCOMPLETE")
        equal(outside_ordinary["dispatch_identity"]["non_plan_agent_tool_use_count"], 1)

        null_input_rows = attempt_records("null-input")
        null_input_rows[0]["message"]["content"][0]["input"] = None
        null_input = analyze_attempts("null-input-in-window", null_input_rows)
        null_input_attempt = null_input["dispatch_identity"]["agent_candidates"][0]
        equal(null_input["classification"], "CONTRACT-VIOLATION")
        equal(
            null_input["product"]["violations"],
            ["delivered-prompt-digest-mismatch", "plan-agent-call-shape-invalid"],
        )
        equal(null_input_attempt["delivered_prompt_sha256"], None)
        equal(null_input_attempt["mode_present"], False)
        equal(null_input_attempt["run_in_background_present"], False)
        equal(null_input_attempt["run_in_background"], None)

        null_plus_valid_rows = attempt_records("null-plus-valid")
        null_plus_valid_rows[0]["message"]["content"][0]["input"] = None
        null_plus_valid = analyze_attempts(
            "null-input-plus-valid",
            null_plus_valid_rows
            + attempt_records(
                "valid-after-null", timestamp="2026-08-02T02:59:00.000Z"
            ),
        )
        equal(null_plus_valid["classification"], "CONTRACT-VIOLATION")
        equal(
            [
                row["acceptance_disposition"]
                for row in null_plus_valid["dispatch_identity"]["agent_candidates"]
            ],
            ["ACCEPTED", "ACCEPTED"],
        )
        equal(
            null_plus_valid["dispatch_identity"]["authorization_windows"][0][
                "classification"
            ],
            "CONTRACT-VIOLATION",
        )

        null_outside_rows = attempt_records(
            "null-outside", timestamp="2026-08-02T03:05:00.000Z"
        )
        null_outside_rows[0]["message"]["content"][0]["input"] = None
        null_outside = analyze_attempts("null-input-outside-window", null_outside_rows)
        equal(null_outside["classification"], "INCOMPLETE")
        equal(null_outside["product"]["violations"], [])
        equal(null_outside["dispatch_identity"]["plan_dispatch_count"], 0)
        equal(null_outside["dispatch_identity"]["non_plan_agent_tool_use_count"], 1)
        equal(
            null_outside["dispatch_identity"]["agent_candidates"][0]["diagnostics"][
                "canonical_heading_match"
            ],
            False,
        )

        retained_canary1 = analyze(write_stage_b_fixture(root, "canary1"))
        canary1_attempt = retained_canary1["dispatch_identity"]["agent_candidates"][0]
        equal(retained_canary1["classification"], "COMPLETE")
        equal(canary1_attempt["source_line"], 94)
        equal(canary1_attempt["matching_tool_result_lines"], [108])
        equal(canary1_attempt["acceptance_disposition"], "ACCEPTED")
        equal(canary1_attempt["mode_present"], False)
        equal(canary1_attempt["run_in_background"] is False, True)
        equal(
            canary1_attempt["delivered_prompt_sha256"],
            "709c87e76696f7c231ec8550e7d066102a8cf9c134b0966279d96daf97d29c15",
        )

        retained_canary2 = analyze(write_stage_b_fixture(root, "canary2"))
        canary2_attempts = retained_canary2["dispatch_identity"]["agent_candidates"]
        equal(retained_canary2["classification"], "CONTRACT-VIOLATION")
        equal([row["source_line"] for row in canary2_attempts], [129, 131])
        equal(
            [row["matching_tool_result_lines"] for row in canary2_attempts],
            [[130], [134]],
        )
        equal(
            [row["acceptance_disposition"] for row in canary2_attempts],
            ["REJECTED", "ACCEPTED"],
        )
        equal([row["mode_present"] for row in canary2_attempts], [True, True])
        equal(
            [row["run_in_background_present"] for row in canary2_attempts],
            [False, False],
        )
        equal(
            "multiple-plan-agents-in-authorization-window"
            in retained_canary2["product"]["violations"],
            False,
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
        found, _, _, _ = collect_agent_calls(
            parent_session_paths(quote_dir), issues, quote_dir
        )
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
            ["delivered-prompt-digest-mismatch", "plan-agent-call-shape-invalid"],
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
        duplicate["message"]["content"][1]["tool_use_id"] = "second-in-window"
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
            ["duplicate-agent-tool-use-id", "multiple-agent-tool-results"],
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
        legacy_duplicate["message"]["content"][1]["tool_use_id"] = (
            "legacy-second-in-window"
        )
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
        # evidence remains visible as corroboration, and excluded Agent fields
        # do not contaminate otherwise complete top-level evidence.
        sidechain_result = write_fixture(
            root, "sidechain-agent-writer", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        sidechain_session = sidechain_result.parent / "sessions" / "parent.jsonl"
        sidechain_rows = [json.loads(sidechain_session.read_text())]
        sidechain_rows.append({
            "timestamp": 7,
            "parent_tool_use_id": "parent-agent",
            "message": {"role": 7, "content": [
                {
                    "type": "tool_use", "name": "Agent", "id": 7,
                    "input": [],
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
        for code in (
            "message-role-malformed",
            "agent-input-not-object",
            "agent-tool-use-id-malformed",
            "agent-subagent-type-malformed",
        ):
            equal(has_shape_issue(sidechain, code), False)

        sidechain_result = write_fixture(
            root, "sidechain-malformed-tool-result", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        sidechain_result_session = (
            sidechain_result.parent / "sessions" / "parent.jsonl"
        )
        sidechain_result_rows = [
            json.loads(sidechain_result_session.read_text())
        ]
        sidechain_result_rows.append({
            "timestamp": "2026-08-02T02:59:01.000Z",
            "parent_tool_use_id": "parent-agent",
            "message": {"role": 7, "content": [{
                "type": "tool_result", "tool_use_id": 7, "is_error": "false",
            }]},
        })
        sidechain_result_session.write_text(
            "".join(json.dumps(row) + "\n" for row in sidechain_result_rows)
        )
        malformed_sidechain_result = analyze(sidechain_result)
        equal(malformed_sidechain_result["classification"], "COMPLETE")
        equal(
            malformed_sidechain_result["dispatch_identity"]["tool_result_count"],
            1,
        )
        for code in (
            "message-role-malformed",
            "tool-result-id-malformed",
        ):
            equal(has_shape_issue(malformed_sidechain_result, code), False)

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
        equal(malformed_receipt["classification"], "CONTRACT-VIOLATION")
        equal(malformed_receipt["dispatch_identity"]["authorization_windows"], [])
        equal(
            "plan-receipt-schema-invalid" in malformed_receipt["evidence"]["issues"],
            True,
        )

        overflow_receipt_result = write_fixture(
            root, "overflow-receipt-time", [copy.deepcopy(c2_records[0])],
            source_name="C2",
        )
        overflow_receipt_state_path = next(
            (overflow_receipt_result / "devlyn-snapshot").glob(
                "runs/*/pipeline.state.json"
            )
        )
        overflow_receipt_state = json.loads(overflow_receipt_state_path.read_text())
        overflow_receipt_state["phases"]["plan"]["started_at"] = (
            "0001-01-01T00:00:00+14:00"
        )
        overflow_receipt_state_path.write_text(json.dumps(overflow_receipt_state) + "\n")
        overflow_receipt = analyze(overflow_receipt_result)
        equal(overflow_receipt["classification"], "CONTRACT-VIOLATION")
        equal(overflow_receipt["ledger"]["receipts"][0]["schema"], "invalid")
        equal(overflow_receipt["dispatch_identity"]["authorization_windows"], [])

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
        equal(reversed_receipt["classification"], "CONTRACT-VIOLATION")
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
            equal(malformed["classification"], "CONTRACT-VIOLATION")
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
        equal(malformed_legacy["classification"], "CONTRACT-VIOLATION")
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
                "--phase", "plan", "transition", "--verdict", "PASS",
                "--next-phase", "implement", "--next-round", "0",
                "--next-engine", "claude",
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
            "message": {"role": "assistant", "content": [
                {
                    "type": "tool_use", "name": "Agent", "id": "p0089-6",
                    "input": {
                        "subagent_type": "general-purpose",
                        "prompt": rendered.read_text(),
                        "run_in_background": False,
                    },
                },
                {"type": "tool_result", "tool_use_id": "p0089-6"},
            ]},
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
