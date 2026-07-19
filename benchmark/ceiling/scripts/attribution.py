#!/usr/bin/env python3
"""Generate deterministic phase-attribution data from a retained A-arm attempt."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


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


def state_path(snapshot: Path) -> Path:
    archived = sorted(snapshot.glob("runs/*/pipeline.state.json"))
    if archived:
        return archived[-1]
    root = snapshot / "pipeline.state.json"
    if root.is_file():
        return root
    raise AttributionError(f"pipeline.state.json not found under {snapshot}")


def clipped_union_ms(
    spans: list[tuple[dt.datetime, dt.datetime]],
    run_start: dt.datetime,
    run_end: dt.datetime,
) -> int | float:
    clipped = [
        (max(start, run_start), min(end, run_end))
        for start, end in spans
        if end > run_start and start < run_end
    ]
    clipped = [(start, end) for start, end in clipped if end > start]
    clipped.sort(key=lambda span: span[0])
    merged: list[tuple[dt.datetime, dt.datetime]] = []
    for start, end in clipped:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return normalized(sum((end - start).total_seconds() * 1000 for start, end in merged))


def collect_span(
    record: dict,
    label: str,
    spans: list[tuple[dt.datetime, dt.datetime]],
    incomplete: list[dict],
    phase: str,
    source: str,
) -> None:
    started_at = record.get("started_at")
    completed_at = record.get("completed_at")
    if started_at is None and completed_at is None:
        return
    start = parse_time(started_at, f"{label}.started_at")
    if completed_at is None:
        incomplete.append({"phase": phase, "record": source, "started_at": started_at})
        return
    end = parse_time(completed_at, f"{label}.completed_at")
    if end < start:
        raise AttributionError(f"{label}.completed_at precedes started_at")
    spans.append((start, end))


def build_attribution(timing: dict, state: dict) -> dict:
    elapsed_seconds = number(timing.get("elapsed_seconds"), "timing.elapsed_seconds")
    assert elapsed_seconds is not None
    elapsed_ms = normalized(elapsed_seconds * 1000)
    run_start = parse_time(state.get("started_at"), "state.started_at")
    run_end = run_start + dt.timedelta(milliseconds=elapsed_ms)

    phases = state.get("phases")
    if not isinstance(phases, dict):
        raise AttributionError("state.phases must be an object")

    phase_report: dict[str, dict] = {}
    spans: list[tuple[dt.datetime, dt.datetime]] = []
    incomplete: list[dict] = []
    phase_sum: int | float = 0
    for phase_name in sorted(phases):
        entry = phases[phase_name]
        if not isinstance(entry, dict):
            raise AttributionError(f"phases.{phase_name} must be an object")
        current_duration = number(
            entry.get("duration_ms"),
            f"phases.{phase_name}.duration_ms",
            nullable=True,
        )
        history = entry.get("history", [])
        if not isinstance(history, list):
            raise AttributionError(f"phases.{phase_name}.history must be an array")
        history_sum: int | float = 0
        for index, prior in enumerate(history):
            if not isinstance(prior, dict):
                raise AttributionError(f"phases.{phase_name}.history[{index}] must be an object")
            prior_duration = number(
                prior.get("duration_ms"),
                f"phases.{phase_name}.history[{index}].duration_ms",
                nullable=True,
            )
            history_sum += prior_duration or 0
            collect_span(
                prior,
                f"phases.{phase_name}.history[{index}]",
                spans,
                incomplete,
                phase_name,
                f"history[{index}]",
            )
        collect_span(
            entry,
            f"phases.{phase_name}",
            spans,
            incomplete,
            phase_name,
            "current",
        )
        history_sum = normalized(history_sum)
        phase_sum += (current_duration or 0) + history_sum
        phase_report[phase_name] = {
            "current_triggered_by": entry.get("triggered_by"),
            "duration_ms": current_duration,
            "history_sum_ms": history_sum,
        }

    union_ms = clipped_union_ms(spans, run_start, run_end)
    verify = phases.get("verify")
    verify = verify if isinstance(verify, dict) else {}
    implement = phase_report.get("implement", {"duration_ms": None, "history_sum_ms": 0})
    return {
        "elapsed_ms": elapsed_ms,
        "implement_total_ms": normalized(
            (implement["duration_ms"] or 0) + implement["history_sum_ms"]
        ),
        "incomplete_spans": incomplete,
        "judge_durations_ms": verify.get("judge_durations_ms"),
        "non_phase_residual_ms": normalized(elapsed_ms - union_ms),
        "phase_sum_ms": normalized(phase_sum),
        "phases": phase_report,
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
    state = load_json(state_path(snapshot))
    if not isinstance(state, dict):
        raise AttributionError("pipeline.state.json must contain an object")
    payload = build_attribution(timing, state)
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


def write_case(root: Path, name: str, state: dict, elapsed_seconds: int) -> Path:
    attempt = root / name
    archive = attempt / "devlyn-snapshot" / "runs" / name
    archive.mkdir(parents=True)
    (attempt / "timing.json").write_text(
        json.dumps({"elapsed_seconds": elapsed_seconds}) + "\n",
        encoding="utf-8",
    )
    (archive / "pipeline.state.json").write_text(
        json.dumps(state) + "\n",
        encoding="utf-8",
    )
    return attempt


def self_test() -> int:
    checks = Checks()
    with tempfile.TemporaryDirectory(prefix="attribution-self-test-") as temporary:
        root = Path(temporary)
        complete = {
            "started_at": "2026-07-19T00:00:00Z",
            "phases": {
                "plan": {
                    "started_at": "2026-07-19T00:00:01Z",
                    "completed_at": "2026-07-19T00:00:03Z",
                    "duration_ms": 2000,
                    "verdict": "PASS",
                },
                "implement": {
                    "started_at": "2026-07-19T00:00:04Z",
                    "completed_at": "2026-07-19T00:00:07Z",
                    "duration_ms": 3000,
                    "verdict": "PASS",
                },
                "verify": {
                    "started_at": "2026-07-19T00:00:08Z",
                    "completed_at": "2026-07-19T00:00:09Z",
                    "duration_ms": 1000,
                    "verdict": "PASS",
                    "judge_durations_ms": {"judge": 600, "pair_judge": 300},
                },
            },
        }
        complete_dir = write_case(root, "complete", complete, 10)
        complete_payload = write_attribution(complete_dir)
        first_bytes = (complete_dir / "attribution.json").read_bytes()
        write_attribution(complete_dir)
        checks.equal((complete_dir / "attribution.json").read_bytes(), first_bytes)
        checks.equal(complete_payload["phase_sum_ms"], 6000)
        checks.equal(complete_payload["non_phase_residual_ms"], 4000)
        checks.equal(complete_payload["phase_sum_ms"] + complete_payload["non_phase_residual_ms"], 10000)
        checks.equal(complete_payload["implement_total_ms"], 3000)
        checks.equal(complete_payload["verify_complete"], True)
        checks.equal(complete_payload["judge_durations_ms"], {"judge": 600, "pair_judge": 300})

        reentry = {
            "started_at": "2026-07-19T00:00:00Z",
            "phases": {
                "implement": {
                    "started_at": "2026-07-19T00:00:03Z",
                    "completed_at": "2026-07-19T00:00:05Z",
                    "duration_ms": 2000,
                    "triggered_by": "verify",
                    "verdict": "PASS",
                    "history": [
                        {
                            "started_at": "2026-07-19T00:00:01Z",
                            "completed_at": "2026-07-19T00:00:02Z",
                            "duration_ms": 1000,
                            "verdict": "NEEDS_WORK",
                        }
                    ],
                }
            },
        }
        reentry_payload = write_attribution(write_case(root, "reentry", reentry, 10))
        checks.equal(reentry_payload["implement_total_ms"], 3000)
        checks.equal(reentry_payload["phase_sum_ms"], 3000)
        checks.equal(reentry_payload["non_phase_residual_ms"], 7000)
        checks.equal(reentry_payload["phases"]["implement"]["history_sum_ms"], 1000)
        checks.equal(reentry_payload["phases"]["implement"]["current_triggered_by"], "verify")

        incomplete = {
            "started_at": "2026-07-19T00:00:00Z",
            "phases": {
                "implement": {
                    "started_at": "2026-07-19T00:00:01Z",
                    "completed_at": "2026-07-19T00:00:03Z",
                    "duration_ms": 2000,
                    "verdict": "PASS",
                },
                "verify": {
                    "started_at": "2026-07-19T00:00:08Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "verdict": None,
                },
            },
        }
        incomplete_payload = write_attribution(write_case(root, "incomplete", incomplete, 10))
        checks.equal(incomplete_payload["verify_complete"], False)
        checks.equal(incomplete_payload["non_phase_residual_ms"], 8000)
        checks.equal(incomplete_payload["phase_sum_ms"] + incomplete_payload["non_phase_residual_ms"], 10000)
        checks.equal(
            incomplete_payload["incomplete_spans"],
            [{"phase": "verify", "record": "current", "started_at": "2026-07-19T00:00:08Z"}],
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
