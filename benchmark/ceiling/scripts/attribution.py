#!/usr/bin/env python3
"""Generate deterministic phase-attribution data from a retained A-arm attempt."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


CONSERVATION_TOLERANCE_MS = 1000


class AttributionError(ValueError):
    pass


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def load_json(path: Path) -> object:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=reject_json_constant,
        )
    except (OSError, ValueError) as exc:
        raise AttributionError(f"cannot read {path}: {exc}") from exc


def parse_time(value: object, label: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise AttributionError(f"{label} is missing or malformed")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise AttributionError(f"{label} is missing or malformed") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def number(value: object, label: str, *, nullable: bool = False) -> int | float | None:
    if value is None and nullable:
        return None
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        raise AttributionError(f"{label} must be a non-negative finite number")
    return value


def normalized(value: int | float) -> int | float:
    rounded = round(value, 3)
    return int(rounded) if rounded == int(rounded) else rounded


def milliseconds(start: dt.datetime, end: dt.datetime, label: str) -> int | float:
    if end < start:
        raise AttributionError(f"negative span: {label}")
    return normalized((end - start).total_seconds() * 1000)


def state_paths(snapshot: Path) -> list[Path]:
    paths = sorted(snapshot.glob("runs/*/pipeline.state.json"))
    root = snapshot / "pipeline.state.json"
    if root.is_file():
        paths.append(root)
    if not paths:
        raise AttributionError(f"pipeline.state.json not found under {snapshot}")
    return paths


def merged_intervals(
    spans: list[tuple[dt.datetime, dt.datetime]],
    lower: dt.datetime | None = None,
    upper: dt.datetime | None = None,
) -> list[tuple[dt.datetime, dt.datetime]]:
    clipped: list[tuple[dt.datetime, dt.datetime]] = []
    for start, end in spans:
        if end < start:
            raise AttributionError("negative span in interval union")
        if lower is not None and end <= lower:
            continue
        if upper is not None and start >= upper:
            continue
        start = max(start, lower) if lower is not None else start
        end = min(end, upper) if upper is not None else end
        if end > start:
            clipped.append((start, end))
    clipped.sort(key=lambda span: (span[0], span[1]))
    merged: list[tuple[dt.datetime, dt.datetime]] = []
    for start, end in clipped:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def union_ms(spans: list[tuple[dt.datetime, dt.datetime]]) -> int | float:
    return normalized(sum((end - start).total_seconds() * 1000 for start, end in spans))


def timing_window(timing: dict) -> tuple[dt.datetime | None, dt.datetime | None, int | float, bool]:
    elapsed_seconds = number(timing.get("elapsed_seconds"), "timing.elapsed_seconds")
    assert elapsed_seconds is not None
    legacy_elapsed_ms = normalized(elapsed_seconds * 1000)
    schema_version = timing.get("schema_version")
    if schema_version == 2:
        invoke_start = parse_time(timing.get("invoke_started_at"), "timing.invoke_started_at")
        invoke_end = parse_time(timing.get("invoke_completed_at"), "timing.invoke_completed_at")
        elapsed_ms = milliseconds(invoke_start, invoke_end, "timing invocation")
        return invoke_start, invoke_end, elapsed_ms, True
    if schema_version not in (None, 1):
        raise AttributionError(f"unsupported timing.schema_version: {schema_version!r}")
    return None, None, legacy_elapsed_ms, False


def build_attribution(timing: dict, states: list[tuple[str, dict]]) -> dict:
    invoke_start, invoke_end, elapsed_ms, timing_v2 = timing_window(timing)
    completed_spans: list[tuple[dt.datetime, dt.datetime]] = []
    open_spans: list[tuple[dt.datetime, str]] = []
    run_starts: list[dt.datetime] = []
    incomplete: list[dict] = []
    phase_report: dict[str, dict] = {}
    phase_sum: int | float = 0
    latest_phases: dict = {}

    ordered_states: list[tuple[dt.datetime, str, dict]] = []
    for source, state in states:
        run_start = parse_time(state.get("started_at"), f"{source}.started_at")
        phases = state.get("phases")
        if not isinstance(phases, dict):
            raise AttributionError(f"{source}.phases must be an object")
        ordered_states.append((run_start, source, state))
    ordered_states.sort(key=lambda row: (row[0], row[1]))

    def collect_record(record: dict, label: str, phase: str, source: str) -> None:
        started_at = record.get("started_at")
        completed_at = record.get("completed_at")
        if started_at is None:
            return
        start = parse_time(started_at, f"{label}.started_at")
        if completed_at is None:
            incomplete.append(
                {"phase": phase, "record": source, "started_at": started_at}
            )
            open_spans.append((start, label))
            return
        end = parse_time(completed_at, f"{label}.completed_at")
        if end < start:
            raise AttributionError(f"negative span: {label}.completed_at precedes started_at")
        completed_spans.append((start, end))

    for run_start, source, state in ordered_states:
        run_starts.append(run_start)
        phases = state["phases"]
        latest_phases = phases
        for phase_name in sorted(phases):
            entry = phases[phase_name]
            if entry is None:
                continue
            if not isinstance(entry, dict):
                raise AttributionError(f"{source}.phases.{phase_name} must be an object")
            current_duration = number(
                entry.get("duration_ms"),
                f"{source}.phases.{phase_name}.duration_ms",
                nullable=True,
            )
            history = entry.get("history", [])
            if not isinstance(history, list):
                raise AttributionError(f"{source}.phases.{phase_name}.history must be an array")
            history_sum: int | float = 0
            for index, prior in enumerate(history):
                if not isinstance(prior, dict):
                    raise AttributionError(
                        f"{source}.phases.{phase_name}.history[{index}] must be an object"
                    )
                prior_duration = number(
                    prior.get("duration_ms"),
                    f"{source}.phases.{phase_name}.history[{index}].duration_ms",
                    nullable=True,
                )
                history_sum += prior_duration or 0
                collect_record(
                    prior,
                    f"{source}.phases.{phase_name}.history[{index}]",
                    phase_name,
                    f"history[{index}]",
                )
            collect_record(
                entry,
                f"{source}.phases.{phase_name}",
                phase_name,
                "current",
            )
            history_sum = normalized(history_sum)
            phase_sum += (current_duration or 0) + history_sum
            report = phase_report.setdefault(
                phase_name,
                {"current_triggered_by": None, "duration_ms": None, "history_sum_ms": 0},
            )
            report["current_triggered_by"] = entry.get("triggered_by")
            if current_duration is not None:
                report["duration_ms"] = normalized(
                    (report["duration_ms"] or 0) + current_duration
                )
            report["history_sum_ms"] = normalized(report["history_sum_ms"] + history_sum)

    lower = invoke_start if timing_v2 else None
    upper = invoke_end if timing_v2 else None
    phase_union = merged_intervals(completed_spans, lower, upper)
    phase_union_ms = union_ms(phase_union)
    residual_ms = normalized(elapsed_ms - phase_union_ms)
    if residual_ms < -CONSERVATION_TOLERANCE_MS:
        raise AttributionError(
            f"phase union exceeds invocation elapsed by {-residual_ms} ms"
        )
    residual_ms = max(0, residual_ms)

    activity_starts = sorted({start for start, _ in completed_spans} | {start for start, _ in open_spans})
    censored_raw: list[tuple[dt.datetime, dt.datetime]] = []
    for start, label in open_spans:
        candidates = [candidate for candidate in activity_starts if candidate > start]
        candidates.extend(run_start for run_start in run_starts if run_start > start)
        if candidates:
            censor_end = min(candidates)
        elif timing_v2:
            assert invoke_end is not None
            censor_end = invoke_end
        else:
            continue
        if censor_end < start:
            raise AttributionError(f"negative censored span: {label}")
        censored_raw.append((start, censor_end))

    activity_union = merged_intervals(completed_spans + censored_raw, lower, upper)
    censored_open_span_ms = normalized(union_ms(activity_union) - phase_union_ms)
    if censored_open_span_ms < -CONSERVATION_TOLERANCE_MS:
        raise AttributionError("negative censored-open union")
    censored_open_span_ms = max(0, censored_open_span_ms)

    interphase_gap_ms: int | float = 0
    outer_loop_gap_ms: int | float = 0
    for (_, previous_end), (next_start, _) in zip(activity_union, activity_union[1:]):
        gap_ms = milliseconds(previous_end, next_start, "activity frontier gap")
        if any(previous_end < run_start <= next_start for run_start in run_starts[1:]):
            outer_loop_gap_ms += gap_ms
        else:
            interphase_gap_ms += gap_ms
    interphase_gap_ms = normalized(interphase_gap_ms)
    outer_loop_gap_ms = normalized(outer_loop_gap_ms)

    startup_ms: int | float | None = None
    tail_ms: int | float | None = None
    legacy_edge_residual_ms: int | float | None = None
    decomposition_status = "complete" if timing_v2 else "legacy-partial"
    if not activity_union:
        decomposition_status = "failed"
        conservation_residue_ms = residual_ms
    elif timing_v2:
        assert invoke_start is not None and invoke_end is not None
        startup_ms = milliseconds(invoke_start, activity_union[0][0], "startup")
        tail_ms = milliseconds(activity_union[-1][1], invoke_end, "tail")
        allocated = normalized(
            startup_ms
            + interphase_gap_ms
            + outer_loop_gap_ms
            + censored_open_span_ms
            + tail_ms
        )
        conservation_residue_ms = normalized(residual_ms - allocated)
        if abs(conservation_residue_ms) > CONSERVATION_TOLERANCE_MS:
            decomposition_status = "failed"
    else:
        identifiable_interior = normalized(
            interphase_gap_ms + outer_loop_gap_ms + censored_open_span_ms
        )
        observed_activity_start = min(
            [start for start, _ in completed_spans]
            + [start for start, _ in open_spans]
        )
        observed_activity_end = max(
            [end for _, end in completed_spans]
            + [start for start, _ in open_spans]
        )
        observed_activity_envelope_ms = milliseconds(
            observed_activity_start,
            observed_activity_end,
            "legacy observed activity envelope",
        )
        legacy_edge_residual_ms = normalized(
            elapsed_ms - observed_activity_envelope_ms
        )
        conservation_residue_ms = normalized(
            residual_ms - legacy_edge_residual_ms - identifiable_interior
        )
        if legacy_edge_residual_ms < 0 or abs(
            conservation_residue_ms
        ) > CONSERVATION_TOLERANCE_MS:
            decomposition_status = "failed"

    verify = latest_phases.get("verify")
    verify = verify if isinstance(verify, dict) else {}
    implement = phase_report.get("implement", {"duration_ms": 0, "history_sum_ms": 0})
    return {
        "censored_open_span_ms": censored_open_span_ms,
        "conservation_residue_ms": conservation_residue_ms,
        "decomposition_status": decomposition_status,
        "elapsed_ms": elapsed_ms,
        "implement_total_ms": normalized(
            (implement["duration_ms"] or 0) + implement["history_sum_ms"]
        ),
        "incomplete_spans": incomplete,
        "interphase_gap_ms": interphase_gap_ms,
        "judge_durations_ms": verify.get("judge_durations_ms"),
        "legacy_edge_residual_ms": legacy_edge_residual_ms,
        "non_phase_residual_ms": residual_ms,
        "outer_loop_gap_ms": outer_loop_gap_ms,
        "phase_sum_ms": normalized(phase_sum),
        "phase_union_ms": phase_union_ms,
        "phases": phase_report,
        "startup_ms": startup_ms,
        "tail_ms": tail_ms,
        "verify_complete": (
            verify.get("completed_at") is not None and verify.get("verdict") is not None
        ),
    }


def write_attribution(attempt_dir: Path) -> dict:
    timing = load_json(attempt_dir / "timing.json")
    if not isinstance(timing, dict):
        raise AttributionError("timing.json must contain an object")
    snapshot = attempt_dir / "devlyn-snapshot"
    if not snapshot.is_dir():
        raise AttributionError(f"devlyn-snapshot directory not found: {snapshot}")
    states: list[tuple[str, dict]] = []
    for path in state_paths(snapshot):
        state = load_json(path)
        if not isinstance(state, dict):
            raise AttributionError(f"{path} must contain an object")
        states.append((str(path.relative_to(snapshot)), state))
    payload = build_attribution(timing, states)
    (attempt_dir / "attribution.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


class Checks:
    def __init__(self) -> None:
        self.count = 0

    def equal(self, actual: object, expected: object) -> None:
        self.count += 1
        if actual != expected:
            raise AssertionError(f"expected {expected!r}, got {actual!r}")

    def true(self, actual: object, label: str) -> None:
        self.count += 1
        if actual is not True:
            raise AssertionError(f"expected true for {label}, got {actual!r}")


def copy_real_receipt(source: Path, target: Path) -> None:
    target.mkdir(parents=True)
    shutil.copyfile(source / "timing.json", target / "timing.json")
    source_snapshot = source / "devlyn-snapshot"
    target_snapshot = target / "devlyn-snapshot"
    for source_state in state_paths(source_snapshot):
        relative = source_state.relative_to(source_snapshot)
        target_state = target_snapshot / relative
        target_state.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_state, target_state)


def self_test() -> int:
    checks = Checks()
    results = Path(__file__).resolve().parent.parent / "results"
    fixtures = {
        "f11": results / "nodeg-20260719g/DR-atomic-state-f11-batch-import/A1",
        "two_run": results / "nodeg-20260720a/FS1-schedule-max-runs/A1",
        "f7": results / "nodeg-20260719g/DR-byte-preservation-f7-out-of-scope-trap/A1",
        "f12": results / "nodeg-20260719g/DR-auth-signature-f12-webhook/A1",
    }
    for name, source in fixtures.items():
        if not source.is_dir():
            raise AssertionError(f"real receipt fixture missing: {name}: {source}")

    with tempfile.TemporaryDirectory(prefix="attribution-self-test-") as temporary:
        root = Path(temporary)
        copied: dict[str, Path] = {}
        for name, source in fixtures.items():
            copied[name] = root / name
            copy_real_receipt(source, copied[name])

        f11 = write_attribution(copied["f11"])
        first_bytes = (copied["f11"] / "attribution.json").read_bytes()
        write_attribution(copied["f11"])
        checks.equal((copied["f11"] / "attribution.json").read_bytes(), first_bytes)
        checks.equal(f11["decomposition_status"], "legacy-partial")
        checks.equal(f11["phase_union_ms"], 1068563)
        checks.equal(f11["verify_complete"], True)
        checks.equal(f11["judge_durations_ms"], {"judge": 159000, "pair_judge": 173000})
        checks.equal(f11["conservation_residue_ms"], 0)

        two_run = write_attribution(copied["two_run"])
        checks.equal(two_run["decomposition_status"], "legacy-partial")
        checks.equal(two_run["implement_total_ms"], 588922)
        checks.true(two_run["outer_loop_gap_ms"] > 0, "two-run outer-loop gap")
        checks.true(two_run["phase_union_ms"] > 557452, "all archived runs included")
        checks.equal(two_run["conservation_residue_ms"], 0)

        f7 = write_attribution(copied["f7"])
        checks.equal(f7["verify_complete"], False)
        checks.true(bool(f7["incomplete_spans"]), "F7 incomplete verify retained")
        checks.equal(f7["censored_open_span_ms"], 0)
        checks.equal(f7["tail_ms"], None)

        f12 = write_attribution(copied["f12"])
        checks.equal(f12["verify_complete"], True)
        checks.true(bool(f12["incomplete_spans"]), "F12 timeout open implement retained")
        checks.equal(f12["censored_open_span_ms"], 0)

        timing = load_json(copied["f11"] / "timing.json")
        assert isinstance(timing, dict)
        timing.update(
            {
                "schema_version": 2,
                "invoke_started_at": "2026-07-19T12:14:00.000Z",
                "invoke_completed_at": "2026-07-19T12:40:07.000Z",
            }
        )
        (copied["f11"] / "timing.json").write_text(
            json.dumps(timing, indent=2) + "\n", encoding="utf-8"
        )
        canary = write_attribution(copied["f11"])
        checks.equal(canary["decomposition_status"], "complete")
        checks.equal(canary["legacy_edge_residual_ms"], None)
        checks.true(canary["startup_ms"] is not None, "timing-v2 startup")
        checks.true(canary["tail_ms"] is not None, "timing-v2 tail")
        checks.true(
            abs(canary["conservation_residue_ms"]) <= CONSERVATION_TOLERANCE_MS,
            "timing-v2 conservation",
        )

        interphase = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("interphase-turns.py")), "--self-test"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        checks.equal(interphase.returncode, 0)
    print(f"SELFTEST PASS: {checks.count} assertions")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("attempt_dir", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.attempt_dir is not None:
            parser.error("attempt_dir is not allowed with --self-test")
        return self_test()
    if args.attempt_dir is None:
        parser.error("attempt_dir is required unless --self-test")
    try:
        write_attribution(args.attempt_dir)
    except AttributionError as exc:
        print(f"ATTRIBUTION_ERROR: {exc}", file=sys.stderr)
        return 2
    print(args.attempt_dir / "attribution.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
