#!/usr/bin/env python3
"""Classify whether a devlyn run made a complete terminal claim."""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import TextIO


INCOMPLETE_EXIT = 79
PASS_VERDICTS = {"PASS", "PASS_WITH_ISSUES"}
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
PHASE_ORDER = (
    "plan",
    "probe_derive",
    "implement",
    "surface_close",
    "build_gate",
    "cleanup",
    "verify",
    "final_report",
)


@dataclass(frozen=True)
class Classification:
    status: str
    phase: str | None
    reason: str
    run_id: str | None
    incomplete: bool

    def receipt(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "phase": self.phase,
            "reason": self.reason,
            "run_id": self.run_id,
        }


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def malformed(reason: str, run_id: str | None = None) -> Classification:
    return Classification("MALFORMED", None, reason, run_id, True)


def incomplete(phase: str, reason: str, run_id: str) -> Classification:
    return Classification(f"INCOMPLETE:{phase}", phase, reason, run_id, True)


def phase_names(phases: dict[str, object]) -> list[str]:
    known = [name for name in PHASE_ORDER if name in phases]
    return known + sorted(name for name in phases if name not in PHASE_ORDER)


def validate_lifecycle(
    name: str, phase: dict[str, object], run_id: str
) -> Classification | None:
    started = phase.get("started_at")
    completed = phase.get("completed_at")
    if started is not None and (not isinstance(started, str) or not started):
        return malformed(f"phase {name} has invalid started_at", run_id)
    if completed is not None and (not isinstance(completed, str) or not completed):
        return malformed(f"phase {name} has invalid completed_at", run_id)
    if completed is not None and started is None:
        return malformed(f"phase {name} completed without started_at", run_id)
    if started is not None and completed is None:
        return incomplete(name, "phase started but not completed", run_id)
    return None


def classify(root: pathlib.Path) -> Classification:
    state_path = root / ".devlyn" / "pipeline.state.json"
    try:
        state_path.lstat()
    except FileNotFoundError:
        return Classification(
            "NOT_APPLICABLE", None, "active pipeline state absent", None, False
        )
    except OSError:
        return malformed("active pipeline state unreadable or invalid")
    if not state_path.is_file():
        return malformed("active pipeline state is not a file")

    try:
        state = json.loads(
            state_path.read_text(encoding="utf-8"),
            parse_constant=reject_json_constant,
        )
    except (OSError, UnicodeError, ValueError):
        return malformed("active pipeline state unreadable or invalid")
    if not isinstance(state, dict):
        return malformed("active pipeline state must be a JSON object")

    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not SAFE_RUN_ID_RE.fullmatch(run_id):
        return malformed("active pipeline state has invalid run_id")
    phases = state.get("phases")
    if not isinstance(phases, dict):
        return malformed("active pipeline state phases must be a JSON object", run_id)

    for name in phase_names(phases):
        phase = phases[name]
        if phase is None:
            continue
        if not isinstance(phase, dict):
            return malformed(f"phase {name} must be a JSON object or null", run_id)
        lifecycle = validate_lifecycle(name, phase, run_id)
        if lifecycle is not None:
            return lifecycle

    verify = phases.get("verify")
    if isinstance(verify, dict) and verify.get("completed_at") is not None:
        verdict = verify.get("verdict")
        if verdict is None:
            return incomplete("verify", "verify completed without verdict", run_id)
        if not isinstance(verdict, str) or not verdict:
            return malformed("verify has invalid verdict", run_id)
    else:
        verdict = None

    final_report = phases.get("final_report")
    if verdict in PASS_VERDICTS and (
        not isinstance(final_report, dict)
        or final_report.get("completed_at") is None
    ):
        return incomplete(
            "final_report",
            "verify passed but final report not completed",
            run_id,
        )

    if isinstance(final_report, dict) and final_report.get("completed_at") is not None:
        archive_state = root / ".devlyn" / "runs" / run_id / "pipeline.state.json"
        if not archive_state.is_file():
            return incomplete(
                "archive",
                "final report completed but run state not archived",
                run_id,
            )

    return Classification("CLEAN", None, "terminal claim complete", run_id, False)


def run_check(root: pathlib.Path, output: TextIO) -> int:
    result = classify(root)
    if not result.incomplete:
        return 0
    output.write(json.dumps(result.receipt(), separators=(",", ":")) + "\n")
    return INCOMPLETE_EXIT


def bound_exit(arm_exit: int, classifier_exit: int) -> int:
    if arm_exit == 0 and classifier_exit == INCOMPLETE_EXIT:
        return INCOMPLETE_EXIT
    return arm_exit


def write_state(root: pathlib.Path, state: object) -> None:
    devlyn = root / ".devlyn"
    devlyn.mkdir(parents=True, exist_ok=True)
    (devlyn / "pipeline.state.json").write_text(
        json.dumps(state) + "\n", encoding="utf-8"
    )


def self_test() -> int:
    tests = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)

        state_19f = {
            "run_id": "rs-20260719T013328Z-9cfbafb5bc04",
            "phases": {
                "plan": {
                    "started_at": "2026-07-19T01:34:48.862Z",
                    "completed_at": "2026-07-19T01:36:29.118Z",
                    "verdict": "PASS",
                },
                "verify": {
                    "started_at": "2026-07-19T01:48:44.782Z",
                    "completed_at": None,
                    "verdict": None,
                },
                "final_report": None,
            },
        }
        write_state(root, state_19f)
        output = io.StringIO()
        assert run_check(root, output) == INCOMPLETE_EXIT
        assert json.loads(output.getvalue())["status"] == "INCOMPLETE:verify"
        tests += 1

        clean_state = {
            "run_id": "clean-run",
            "phases": {
                "verify": {
                    "started_at": "2026-07-19T02:00:00Z",
                    "completed_at": "2026-07-19T02:01:00Z",
                    "verdict": "PASS",
                },
                "final_report": {
                    "started_at": "2026-07-19T02:01:00Z",
                    "completed_at": "2026-07-19T02:02:00Z",
                    "verdict": "PASS",
                },
            },
        }
        write_state(root, clean_state)
        archive = root / ".devlyn" / "runs" / "clean-run"
        archive.mkdir(parents=True)
        (archive / "pipeline.state.json").write_text(
            json.dumps(clean_state) + "\n", encoding="utf-8"
        )
        output = io.StringIO()
        assert run_check(root, output) == 0
        assert output.getvalue() == ""
        (root / ".devlyn" / "pipeline.state.json").unlink()
        output = io.StringIO()
        assert run_check(root, output) == 0
        assert output.getvalue() == ""
        tests += 1

        write_state(root, {"run_id": "malformed-run", "phases": {}})
        (root / ".devlyn" / "pipeline.state.json").write_text("{\n", encoding="utf-8")
        output = io.StringIO()
        assert run_check(root, output) == INCOMPLETE_EXIT
        assert json.loads(output.getvalue())["status"] == "MALFORMED"
        tests += 1

        assert bound_exit(0, INCOMPLETE_EXIT) == INCOMPLETE_EXIT
        for protected in (86, 78, 124):
            assert bound_exit(protected, INCOMPLETE_EXIT) == protected
        tests += 1

    print(f"terminal-claim-check self-test: PASS ({tests} tests)")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify a devlyn terminal claim from project-root state."
    )
    parser.add_argument("root", nargs="?", default=".", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    return run_check(args.root, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
