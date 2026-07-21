#!/usr/bin/env python3
"""Reconstruct dispatch-bound phase anatomy against a raw attribution baseline."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

import attribution


CONSERVATION_TOLERANCE_MS = 1000
POSTHOC_MAX_MS = 1000
MIN_DISPATCH_MS = 30_000
MAX_DISPATCH_LAG_MS = 300_000
DEFAULT_TIMEOUT_SECONDS = 3600
EXPECTED_COHORT_ROWS = 7
PARTITION_BUCKETS = (
    "phase_union_ms",
    "startup_ms",
    "interphase_gap_ms",
    "gap_to_censored_ms",
    "outer_loop_gap_ms",
    "censored_open_span_ms",
    "tail_ms",
)
DEBUG_EVENT_RE = re.compile(
    r"^(?P<timestamp>\S+) \[(?:INFO|WARN)\] \[Stall\] "
    r"tool_dispatch_(?P<event>start|end) tool=(?P<tool>Agent|Bash) "
    r"toolUseId=(?P<tool_id>\S+)"
)


class AnatomyError(ValueError):
    pass


def normalized(value: int | float) -> int | float:
    return attribution.normalized(value)


def difference_ms(left: object, right: object, label: str) -> int | float:
    if left is None or right is None:
        raise AnatomyError(f"{label} cannot compare null buckets")
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        raise AnatomyError(f"{label} buckets must be numeric")
    return normalized(left - right)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_object(path: Path) -> dict:
    value = attribution.load_json(path)
    if not isinstance(value, dict):
        raise AnatomyError(f"{path} must contain a JSON object")
    return value


def iso(value: object, label: str) -> dt.datetime:
    return attribution.parse_time(value, label)


def state_documents(attempt_dir: Path) -> list[tuple[str, dict]]:
    snapshot = attempt_dir / "devlyn-snapshot"
    if not snapshot.is_dir():
        raise AnatomyError(f"devlyn-snapshot directory not found: {snapshot}")
    documents: list[tuple[str, dict]] = []
    for path in attribution.state_paths(snapshot):
        documents.append((str(path.relative_to(snapshot)), load_object(path)))
    return documents


def dispatch_intervals(debug_path: Path) -> list[dict]:
    starts: dict[str, tuple[dt.datetime, str]] = {}
    intervals: list[dict] = []
    try:
        lines = debug_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise AnatomyError(f"cannot read {debug_path}: {exc}") from exc
    for line_number, line in enumerate(lines, 1):
        match = DEBUG_EVENT_RE.match(line)
        if match is None:
            continue
        timestamp = iso(match.group("timestamp"), f"{debug_path}:{line_number}")
        tool_id = match.group("tool_id")
        tool = match.group("tool")
        if match.group("event") == "start":
            if tool_id in starts:
                raise AnatomyError(f"duplicate dispatch start in {debug_path}: {tool_id}")
            starts[tool_id] = (timestamp, tool)
            continue
        started = starts.pop(tool_id, None)
        if started is None:
            continue
        start, started_tool = started
        if started_tool != tool or timestamp < start:
            raise AnatomyError(f"malformed dispatch interval in {debug_path}: {tool_id}")
        intervals.append(
            {
                "tool": tool,
                "tool_use_id": tool_id,
                "started_at": start,
                "completed_at": timestamp,
                "duration_ms": attribution.milliseconds(start, timestamp, "dispatch"),
            }
        )
    intervals.sort(key=lambda row: (row["started_at"], row["completed_at"], row["tool_use_id"]))
    return intervals


def phase_records(states: list[tuple[str, dict]]) -> list[dict]:
    records: list[dict] = []
    for source, state in states:
        phases = state.get("phases")
        if not isinstance(phases, dict):
            raise AnatomyError(f"{source}.phases must be an object")
        for phase_name in sorted(phases):
            entry = phases[phase_name]
            if entry is None:
                continue
            if not isinstance(entry, dict):
                raise AnatomyError(f"{source}.phases.{phase_name} must be an object")
            history = entry.get("history", [])
            if not isinstance(history, list):
                raise AnatomyError(f"{source}.phases.{phase_name}.history must be an array")
            for index, prior in enumerate(history):
                if not isinstance(prior, dict):
                    raise AnatomyError(
                        f"{source}.phases.{phase_name}.history[{index}] must be an object"
                    )
                records.append(
                    {
                        "source": source,
                        "phase": phase_name,
                        "record": f"history[{index}]",
                        "engine": entry.get("engine"),
                        "value": prior,
                    }
                )
            records.append(
                {
                    "source": source,
                    "phase": phase_name,
                    "record": "current",
                    "engine": entry.get("engine"),
                    "value": entry,
                }
            )
    return records


def expected_dispatch_tool(record: dict) -> str | None:
    phase = record["phase"]
    engine = record["engine"]
    if phase in {"plan", "build_gate"}:
        return "Agent"
    if phase == "surface_close":
        return "Bash"
    if engine == "claude":
        return "Agent"
    if engine == "codex":
        return "Bash"
    return None


def record_times(record: dict) -> tuple[dt.datetime | None, dt.datetime | None]:
    value = record["value"]
    started_at = value.get("started_at")
    completed_at = value.get("completed_at")
    start = None if started_at is None else iso(started_at, f"{record['phase']}.started_at")
    end = None if completed_at is None else iso(completed_at, f"{record['phase']}.completed_at")
    return start, end


def preceding_frontier(records: list[dict], target_start: dt.datetime) -> dt.datetime | None:
    ends: list[dt.datetime] = []
    for record in records:
        _, end = record_times(record)
        if end is not None and end <= target_start:
            ends.append(end)
    return max(ends) if ends else None


def apply_dispatch_corrections(states: list[tuple[str, dict]], dispatches: list[dict]) -> tuple[list[dict], list[str]]:
    records = phase_records(states)
    corrections: list[dict] = []
    ambiguities: list[str] = []
    for record in records:
        value = record["value"]
        start, end = record_times(record)
        duration = value.get("duration_ms")
        if start is None or end is None or not isinstance(duration, (int, float)):
            continue
        if duration > POSTHOC_MAX_MS:
            continue
        tool = expected_dispatch_tool(record)
        if tool is None:
            continue
        frontier = preceding_frontier([row for row in records if row is not record], start)
        candidates = []
        for dispatch in dispatches:
            if dispatch["tool"] != tool or dispatch["duration_ms"] < MIN_DISPATCH_MS:
                continue
            if dispatch["completed_at"] > start:
                continue
            lag_ms = attribution.milliseconds(dispatch["completed_at"], start, "dispatch lag")
            if lag_ms > MAX_DISPATCH_LAG_MS:
                continue
            if frontier is not None and dispatch["started_at"] < frontier:
                continue
            candidates.append(dispatch)
        label = f"{record['source']}.phases.{record['phase']}.{record['record']}"
        if len(candidates) > 1:
            ambiguities.append(f"ambiguous_dispatch:{label}:{len(candidates)}")
            continue
        if not candidates:
            continue
        dispatch = candidates[0]
        original_started_at = value["started_at"]
        value["started_at"] = dispatch["started_at"].isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )
        value["duration_ms"] = attribution.milliseconds(
            dispatch["started_at"], end, f"adjusted {record['phase']}"
        )
        corrections.append(
            {
                "phase": record["phase"],
                "record": record["record"],
                "source": record["source"],
                "recorded_started_at": original_started_at,
                "recorded_completed_at": value["completed_at"],
                "recorded_duration_ms": duration,
                "adjusted_started_at": value["started_at"],
                "adjusted_duration_ms": value["duration_ms"],
                "dispatch": {
                    "tool": dispatch["tool"],
                    "tool_use_id": dispatch["tool_use_id"],
                    "started_at": dispatch["started_at"].isoformat(timespec="milliseconds").replace(
                        "+00:00", "Z"
                    ),
                    "completed_at": dispatch["completed_at"].isoformat(timespec="milliseconds").replace(
                        "+00:00", "Z"
                    ),
                    "duration_ms": dispatch["duration_ms"],
                },
            }
        )
    return corrections, ambiguities


def verify_raw_baseline(raw: dict, computed: dict, task: str) -> None:
    for bucket in PARTITION_BUCKETS:
        delta = difference_ms(computed.get(bucket), raw.get(bucket), f"{task}.{bucket}")
        if abs(delta) > CONSERVATION_TOLERANCE_MS:
            raise AnatomyError(
                f"{task} raw attribution mismatch for {bucket}: computed={computed.get(bucket)} "
                f"baseline={raw.get(bucket)} delta={delta}"
            )


def partition_total(payload: dict, task: str) -> int | float:
    values = []
    for bucket in PARTITION_BUCKETS:
        value = payload.get(bucket)
        if not isinstance(value, (int, float)):
            raise AnatomyError(f"{task}.{bucket} must be numeric for timing-v2 anatomy")
        values.append(value)
    return normalized(sum(values))


def row_anatomy(attempt_dir: Path, timeout_seconds: int) -> dict:
    task = attempt_dir.parent.name
    timing = load_object(attempt_dir / "timing.json")
    raw_path = attempt_dir / "attribution.json"
    raw = load_object(raw_path)
    original_states = state_documents(attempt_dir)
    computed_raw = attribution.build_attribution(timing, copy.deepcopy(original_states))
    verify_raw_baseline(raw, computed_raw, task)

    adjusted_states = copy.deepcopy(original_states)
    records = phase_records(adjusted_states)
    dispatches = dispatch_intervals(attempt_dir / "claude-debug.log")
    corrections, ambiguities = apply_dispatch_corrections(adjusted_states, dispatches)
    adjusted = attribution.build_attribution(timing, adjusted_states)

    reasons = list(ambiguities)
    open_history = []
    for record in records:
        start, end = record_times(record)
        value = record["value"]
        if record["record"].startswith("history[") and start is not None and end is None:
            receipt = {
                "phase": record["phase"],
                "record": record["record"],
                "started_at": value.get("started_at"),
                "verdict": value.get("verdict"),
                "completed_at": None,
            }
            open_history.append(receipt)
            if value.get("verdict") is not None:
                reasons.append(
                    f"open_history_with_verdict:{record['phase']}:{record['record']}"
                )

    post_cap_records = []
    if timing.get("timed_out") is True:
        invoke_start = iso(timing.get("invoke_started_at"), f"{task}.timing.invoke_started_at")
        deadline = invoke_start + dt.timedelta(seconds=timeout_seconds)
        for record in records:
            start, _ = record_times(record)
            if start is not None and start > deadline:
                post_cap_records.append(
                    {
                        "phase": record["phase"],
                        "record": record["record"],
                        "started_at": record["value"].get("started_at"),
                    }
                )
        if post_cap_records:
            reasons.append("phase_activity_after_timeout_cap")

    raw_total = partition_total(raw, task)
    adjusted_total = partition_total(adjusted, task)
    elapsed_ms = raw.get("elapsed_ms")
    if not isinstance(elapsed_ms, (int, float)):
        raise AnatomyError(f"{task}.elapsed_ms must be numeric")
    raw_residue = normalized(raw_total - elapsed_ms)
    adjusted_residue = normalized(adjusted_total - elapsed_ms)

    ledger = {}
    relocation_sum: int | float = 0
    for bucket in PARTITION_BUCKETS:
        relocation = difference_ms(adjusted[bucket], raw[bucket], f"{task}.{bucket}")
        relocation_sum += relocation
        ledger[bucket] = {
            "raw_bucket_ms": raw[bucket],
            "declared_relocation_ms": relocation,
            "adjusted_bucket_ms": adjusted[bucket],
            "equation": "adjusted_bucket = raw_bucket + declared_relocation",
            "equation_passed": normalized(raw[bucket] + relocation) == adjusted[bucket],
        }
    relocation_sum = normalized(relocation_sum)
    conservation_passed = (
        abs(raw_residue) <= CONSERVATION_TOLERANCE_MS
        and abs(adjusted_residue) <= CONSERVATION_TOLERANCE_MS
        and abs(relocation_sum) <= CONSERVATION_TOLERANCE_MS
        and all(entry["equation_passed"] for entry in ledger.values())
    )

    return {
        "attempt": f"{task}/A1",
        "eligible": not reasons,
        "ineligibility_reasons": reasons,
        "receipt_flags": {
            "open_history": open_history,
            "post_cap_records": post_cap_records,
        },
        "phase_span_corrections": corrections,
        "raw_attribution": {
            "path": f"{task}/A1/attribution.json",
            "sha256": sha256_file(raw_path),
            **{key: raw.get(key) for key in ("elapsed_ms", *PARTITION_BUCKETS)},
        },
        "adjusted_attribution": {
            **{key: adjusted.get(key) for key in ("elapsed_ms", *PARTITION_BUCKETS)},
            "non_phase_residual_ms": adjusted.get("non_phase_residual_ms"),
        },
        "relocation_ledger": ledger,
        "conservation": {
            "tolerance_ms": CONSERVATION_TOLERANCE_MS,
            "raw_partition_total_ms": raw_total,
            "raw_residue_ms": raw_residue,
            "adjusted_partition_total_ms": adjusted_total,
            "adjusted_residue_ms": adjusted_residue,
            "relocation_sum_ms": relocation_sum,
            "passed": conservation_passed,
        },
    }


def selected_tasks(result_dir: Path) -> list[str]:
    cohort_path = result_dir / "nodeg-cohort.json"
    if cohort_path.is_file():
        cohort = load_object(cohort_path)
        tasks = cohort.get("selected_tasks")
        if not isinstance(tasks, list) or not tasks or not all(isinstance(row, str) for row in tasks):
            raise AnatomyError(f"{cohort_path}.selected_tasks must be a non-empty string array")
        return tasks
    return sorted(path.name for path in result_dir.iterdir() if (path / "A1").is_dir())


def median(values: list[int | float]) -> int | float:
    return normalized(statistics.median(values))


def build_cohort(result_dir: Path, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    tasks = selected_tasks(result_dir)
    rows = {task: row_anatomy(result_dir / task / "A1", timeout_seconds) for task in tasks}
    eligible = [task for task in tasks if rows[task]["eligible"]]
    conservation_passed = all(rows[task]["conservation"]["passed"] for task in tasks)
    ledger_published = all(bool(rows[task]["relocation_ledger"]) for task in tasks)
    startup_median = median(
        [rows[task]["adjusted_attribution"]["startup_ms"] for task in eligible]
    )
    interphase_median = median(
        [rows[task]["adjusted_attribution"]["interphase_gap_ms"] for task in eligible]
    )
    gate_passed = (
        len(tasks) == EXPECTED_COHORT_ROWS
        and len(eligible) >= 5
        and conservation_passed
        and ledger_published
    )
    return {
        "schema_version": 1,
        "instrument": "corrected-anatomy",
        "source_result_dir": result_dir.name,
        "source_run_id": result_dir.name,
        "timeout_cap_seconds": timeout_seconds,
        "gate": {
            "id": "P-0077-H",
            "verdict": "PASS" if gate_passed else "FAIL",
            "passed": gate_passed,
            "eligible_rows": eligible,
            "eligible_count": len(eligible),
            "total_rows": len(tasks),
            "expected_total_rows": EXPECTED_COHORT_ROWS,
            "minimum_eligible_rows": 5,
            "conservation_tolerance_ms": CONSERVATION_TOLERANCE_MS,
            "conservation_passed": conservation_passed,
            "relocation_ledger_published": ledger_published,
        },
        "denominators": {
            "population": eligible,
            "p_0077_b_adjusted_startup_median_ms": startup_median,
            "p_0077_b_multiplier": 0.60,
            "p_0077_b_absolute_target_ms": normalized(startup_median * 0.60),
            "p_0077_t_adjusted_interphase_median_ms": interphase_median,
            "p_0077_t_multiplier": 0.75,
            "p_0077_t_absolute_target_ms": normalized(interphase_median * 0.75),
        },
        "rows": rows,
    }


def correction(payload: dict, task: str, phase: str) -> dict | None:
    for row in payload["rows"][task]["phase_span_corrections"]:
        if row["phase"] == phase:
            return row
    return None


def self_test() -> int:
    result_dir = Path(__file__).resolve().parent.parent / "results" / "nodeg-20260721e"
    first = build_cohort(result_dir)
    second = build_cohort(result_dir)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    f11 = first["rows"]["DR-atomic-state-f11-batch-import"]
    assert f11["eligible"] is False
    assert f11["receipt_flags"]["open_history"] == [{
        "phase": "verify",
        "record": "history[0]",
        "started_at": "2026-07-21T07:08:11.684Z",
        "verdict": "BLOCKED",
        "completed_at": None,
    }]
    assert f11["raw_attribution"]["censored_open_span_ms"] == 686757
    f11_plan = correction(first, "DR-atomic-state-f11-batch-import", "plan")
    assert f11_plan is not None and f11_plan["recorded_duration_ms"] == 90
    assert f11_plan["dispatch"]["duration_ms"] == 48352

    f12 = first["rows"]["DR-auth-signature-f12-webhook"]
    f12_probe = correction(first, "DR-auth-signature-f12-webhook", "probe_derive")
    assert f12_probe is not None and f12_probe["recorded_duration_ms"] == 106
    assert f12_probe["dispatch"]["duration_ms"] == 151920

    f7_build_gate = correction(first, "DR-byte-preservation-f7-out-of-scope-trap", "build_gate")
    assert f7_build_gate is not None and f7_build_gate["record"] == "history[0]"
    assert f7_build_gate["recorded_duration_ms"] == 93

    f26 = first["rows"]["DR-ledger-rounding-consistency-f26-payout"]
    f26_records = phase_records(state_documents(
        result_dir / "DR-ledger-rounding-consistency-f26-payout" / "A1"
    ))
    f26_probe = next(row for row in f26_records if row["phase"] == "probe_derive")
    assert f26_probe["value"]["duration_ms"] == 409045
    assert correction(first, "DR-ledger-rounding-consistency-f26-payout", "probe_derive") is None
    assert f26["raw_attribution"]["phase_union_ms"] == f26["adjusted_attribution"]["phase_union_ms"]

    f23 = first["rows"]["DR-allocation-fefo-priority-rollback-f23-fulfillment"]
    f23_plan = correction(first, "DR-allocation-fefo-priority-rollback-f23-fulfillment", "plan")
    assert f23_plan is not None and f23_plan["recorded_duration_ms"] == 75
    assert f23_plan["dispatch"]["duration_ms"] == 52293
    assert f23["eligible"] is False and f23["receipt_flags"]["post_cap_records"]

    assert first["gate"]["passed"] is True
    assert first["gate"]["eligible_count"] == 5
    assert first["denominators"]["p_0077_b_adjusted_startup_median_ms"] == 225768
    assert first["denominators"]["p_0077_t_adjusted_interphase_median_ms"] == 397906
    print("PASS corrected-anatomy self-test")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_dir", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.result_dir is None:
        parser.error("result_dir is required unless --self-test is used")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    result_dir = args.result_dir.resolve()
    output = args.output.resolve() if args.output else result_dir / "corrected-baseline.json"
    try:
        payload = build_cohort(result_dir, args.timeout_seconds)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    except (AnatomyError, attribution.AttributionError, OSError, ValueError) as exc:
        print(f"corrected-anatomy failed: {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0 if payload["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
