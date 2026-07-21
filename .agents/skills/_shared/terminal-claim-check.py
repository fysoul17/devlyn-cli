#!/usr/bin/env python3
"""Classify active or invocation-set devlyn terminal claims."""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import TextIO


INCOMPLETE_EXIT = 79
VALID_VERIFY_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "BLOCKED"}
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
ENGINE_UNAVAILABLE_RE = re.compile(r"^[A-Za-z0-9_.-]+-unavailable$")
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
WORK_PHASE_ORDER = PHASE_ORDER[:-1]
HALT_WITNESS_PHASES = {
    "plan-empty": "plan",
    "risk-halt": "plan",
    "implement-empty": "implement",
    "build-gate-exhausted": "build_gate",
    "verify-exhausted": "verify",
}


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


def valid_final_verdict(value: object) -> bool:
    return isinstance(value, str) and (
        value in VALID_VERIFY_VERDICTS
        or (value.startswith("BLOCKED:") and len(value) > 8)
    )


def terminal_halt_witness(phases: dict[str, object]) -> tuple[str, str] | None:
    final_report = phases.get("final_report")
    if not isinstance(final_report, dict):
        return None
    verdict = final_report.get("verdict")
    if not isinstance(verdict, str) or not verdict.startswith("BLOCKED:"):
        return None
    reason = verdict.removeprefix("BLOCKED:")
    target = HALT_WITNESS_PHASES.get(reason)
    if target is None and (
        reason == "fresh-context-unavailable" or ENGINE_UNAVAILABLE_RE.fullmatch(reason)
    ):
        reached = [name for name in WORK_PHASE_ORDER if phases.get(name) is not None]
        target = reached[-1] if reached else None
    if target is None:
        return None
    phase = phases.get(target)
    if not isinstance(phase, dict) or phase.get("completed_at") is None:
        return None
    target_index = WORK_PHASE_ORDER.index(target)
    if any(phases.get(name) is not None for name in WORK_PHASE_ORDER[target_index + 1:]):
        return None
    return target, reason


def classify_state_bytes(
    root: pathlib.Path,
    state_path: pathlib.Path,
    state_bytes: bytes,
    *,
    archived: bool,
) -> tuple[Classification, dict[str, object] | None]:
    try:
        state = json.loads(
            state_bytes.decode("utf-8"),
            parse_constant=reject_json_constant,
        )
    except (UnicodeError, ValueError):
        return malformed(f"run state unreadable or invalid: {state_path}"), None
    if not isinstance(state, dict):
        return malformed("run state must be a JSON object"), None

    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not SAFE_RUN_ID_RE.fullmatch(run_id):
        return malformed("run state has invalid run_id"), state
    phases = state.get("phases")
    if not isinstance(phases, dict):
        return malformed("run state phases must be a JSON object", run_id), state

    open_span: Classification | None = None
    for name in phase_names(phases):
        phase = phases[name]
        if phase is None:
            continue
        if not isinstance(phase, dict):
            return malformed(f"phase {name} must be a JSON object or null", run_id), state
        lifecycle = validate_lifecycle(name, phase, run_id)
        if lifecycle is not None:
            if lifecycle.status == "MALFORMED":
                return lifecycle, state
            open_span = open_span or lifecycle
        history = phase.get("history")
        if history is None:
            continue
        if not isinstance(history, list):
            return malformed(f"phase {name} history must be an array", run_id), state
        for index, prior in enumerate(history):
            if not isinstance(prior, dict):
                return malformed(f"phase {name} history[{index}] must be an object", run_id), state
            lifecycle = validate_lifecycle(name, prior, run_id)
            if lifecycle is not None:
                if lifecycle.status == "MALFORMED":
                    return lifecycle, state
                open_span = open_span or incomplete(
                    name, f"phase {name} history[{index}] started but not completed", run_id
                )

    final_report = phases.get("final_report")
    final_completed = (
        isinstance(final_report, dict) and final_report.get("completed_at") is not None
    )
    if final_completed and not valid_final_verdict(final_report.get("verdict")):
        return malformed("final_report completed with null or invalid verdict", run_id), state
    if open_span is not None:
        return open_span, state

    verify = phases.get("verify")
    if isinstance(verify, dict) and verify.get("completed_at") is not None:
        verdict = verify.get("verdict")
        if verdict is None:
            return incomplete("verify", "verify completed without verdict", run_id), state
        if verdict not in VALID_VERIFY_VERDICTS:
            return malformed("verify has invalid verdict", run_id), state
    else:
        verdict = None

    archive_state = root / ".devlyn" / "runs" / run_id / "pipeline.state.json"
    archive_valid = (
        archived and state_path.parent.name == run_id
    ) or archive_state.is_file()
    if verdict is not None:
        if not final_completed:
            return incomplete(
                "final_report", "verify completed but final report not completed", run_id,
            ), state
        if not archive_valid:
            return incomplete(
                "archive", "final report completed but run state not archived", run_id,
            ), state
        return Classification(
            "CLEAN", None, "verify and terminal archive complete", run_id, False
        ), state

    witness = terminal_halt_witness(phases)
    if witness is not None:
        phase, reason = witness
        if not archive_valid:
            return incomplete("archive", "terminal halt witness not archived", run_id), state
        return Classification(
            "CLEAN", None, f"terminal halt witnessed at {phase}: {reason}", run_id, False,
        ), state

    return incomplete("verify", "verify did not complete with a valid verdict", run_id), state


def classify_active_state(
    root: pathlib.Path, state_bytes: bytes,
) -> tuple[Classification, dict[str, object] | None]:
    """Classify only the supplied active-state snapshot and return its parsed object."""
    state_path = root / ".devlyn" / "pipeline.state.json"
    return classify_state_bytes(root, state_path, state_bytes, archived=False)


def classify_state(
    root: pathlib.Path, state_path: pathlib.Path, *, archived: bool,
) -> Classification:
    try:
        state_path.lstat()
    except FileNotFoundError:
        return malformed(f"run state absent: {state_path}")
    except OSError:
        return malformed(f"run state unreadable or invalid: {state_path}")
    if not state_path.is_file():
        return malformed(f"run state is not a file: {state_path}")

    try:
        state_bytes = state_path.read_bytes()
    except OSError:
        return malformed(f"run state unreadable or invalid: {state_path}")
    result, _ = classify_state_bytes(
        root, state_path, state_bytes, archived=archived,
    )
    return result


def invocation_members(
    root: pathlib.Path, before_run_ids: set[str],
) -> list[tuple[pathlib.Path, bool]]:
    members: list[tuple[pathlib.Path, bool]] = []
    runs = root / ".devlyn" / "runs"
    try:
        children = list(runs.iterdir())
    except FileNotFoundError:
        children = []
    except OSError:
        return [(runs, True)]
    for child in children:
        if child.name in before_run_ids:
            continue
        state_path = child / "pipeline.state.json"
        try:
            state_path.lstat()
        except FileNotFoundError:
            continue
        except OSError:
            pass
        members.append((state_path, True))
    active = root / ".devlyn" / "pipeline.state.json"
    try:
        active.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        members.append((active, False))
    else:
        members.append((active, False))
    return members


def classify(root: pathlib.Path, before_run_ids: set[str] | None = None) -> Classification:
    members = invocation_members(root, before_run_ids or set())
    if not members:
        return Classification(
            "NOT_APPLICABLE", None, "no new archived or active run state", None, False
        )
    results = [
        classify_state(root, state_path, archived=archived)
        for state_path, archived in members
    ]
    failures = [result for result in results if result.incomplete]
    if not failures:
        return Classification(
            "CLEAN", None, f"all {len(results)} invocation run states complete", None, False
        )
    if len(results) == 1:
        return failures[0]
    status = (
        "MALFORMED"
        if any(result.status == "MALFORMED" for result in failures)
        else "INCOMPLETE:set"
    )
    phase = None if status == "MALFORMED" else "set"
    reason = "invocation run-set incomplete: " + json.dumps([
        {"run_id": result.run_id, "status": result.status, "reason": result.reason}
        for result in failures
    ], separators=(",", ":"))
    return Classification(status, phase, reason, None, True)


def run_check(
    root: pathlib.Path, output: TextIO, before_run_ids: set[str] | None = None,
) -> int:
    result = classify(root, before_run_ids)
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


def write_archived_state(root: pathlib.Path, state: dict[str, object]) -> None:
    archive = root / ".devlyn" / "runs" / str(state["run_id"])
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "pipeline.state.json").write_text(
        json.dumps(state) + "\n", encoding="utf-8"
    )


def self_test() -> int:
    tests = 0
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)

        f23_state = {
            "version": "3.0",
            "run_id": "rs-20260720T133550Z-df45c8e5de59",
            "phases": {
                "plan": {"started_at": "2026-07-20T13:37:22Z", "completed_at": "2026-07-20T13:42:08Z", "verdict": "PASS"},
                "probe_derive": None,
                "implement": {"started_at": "2026-07-20T13:42:46Z", "completed_at": "2026-07-20T13:54:01Z", "verdict": "PASS"},
                "surface_close": {"started_at": "2026-07-20T14:01:49Z", "completed_at": "2026-07-20T14:04:11Z", "verdict": "BLOCKED"},
                "build_gate": None,
                "cleanup": None,
                "verify": None,
                "final_report": {"started_at": "2026-07-20T14:04:40Z", "completed_at": "2026-07-20T14:05:05Z", "verdict": "BLOCKED:surface-close-adjudication-malformed"},
            },
        }
        fs1_state = {
            "version": "3.0",
            "run_id": "rs-20260720T140815Z-068baf0da60c",
            "phases": {
                "plan": {"started_at": "2026-07-20T14:11:37Z", "completed_at": "2026-07-20T14:15:58Z", "verdict": "PASS"},
                "probe_derive": None,
                "implement": {"started_at": "2026-07-20T14:16:12Z", "completed_at": "2026-07-20T14:21:53Z", "verdict": "PASS"},
                "surface_close": {"started_at": "2026-07-20T14:40:32Z", "completed_at": "2026-07-20T14:43:53Z", "verdict": "BLOCKED"},
                "build_gate": {"started_at": "2026-07-20T14:25:44Z", "completed_at": "2026-07-20T14:25:44Z", "verdict": "PASS"},
                "cleanup": {"started_at": "2026-07-20T14:25:57Z", "completed_at": "2026-07-20T14:27:10Z", "verdict": "PASS"},
                "verify": {"started_at": "2026-07-20T14:27:42Z", "completed_at": "2026-07-20T14:44:56Z", "verdict": "BLOCKED"},
                "final_report": {"started_at": "2026-07-20T14:45:10Z", "completed_at": "2026-07-20T14:45:24Z", "verdict": "BLOCKED:surface-close-adjudication-malformed"},
            },
        }

        root = base / "set-quantification"
        write_archived_state(root, f23_state)
        write_archived_state(root, fs1_state)
        output = io.StringIO()
        assert run_check(root, output) == INCOMPLETE_EXIT
        receipt = json.loads(output.getvalue())
        assert receipt["status"] == "INCOMPLETE:set"
        assert f23_state["run_id"] in receipt["reason"]
        tests += 1

        root = base / "f25-open-history"
        f25_state = {
            "version": "3.0",
            "run_id": "rs-20260720T102955Z-6246a50033bb",
            "phases": {
                "build_gate": {
                    "started_at": "2026-07-20T10:57:53Z",
                    "completed_at": "2026-07-20T11:00:13Z",
                    "verdict": "PASS",
                    "history": [{"started_at": "2026-07-20T10:51:37Z", "completed_at": None, "verdict": None}],
                },
                "verify": {
                    "started_at": "2026-07-20T11:02:49Z",
                    "completed_at": None,
                    "verdict": None,
                },
                "final_report": None,
            },
        }
        write_state(root, f25_state)
        output = io.StringIO()
        assert run_check(root, output) == INCOMPLETE_EXIT
        receipt = json.loads(output.getvalue())
        assert receipt["status"] == "INCOMPLETE:build_gate"
        assert "history[0]" in receipt["reason"]
        tests += 1

        root = base / "fs1-clean"
        write_archived_state(root, fs1_state)
        output = io.StringIO()
        assert run_check(root, output) == 0
        assert output.getvalue() == ""
        tests += 1

        root = base / "clean-full-run"
        clean_state = {
            "run_id": "clean-run",
            "phases": {
                "verify": {"started_at": "2026-07-19T02:00:00Z", "completed_at": "2026-07-19T02:01:00Z", "verdict": "PASS"},
                "final_report": {"started_at": "2026-07-19T02:01:00Z", "completed_at": "2026-07-19T02:02:00Z", "verdict": "PASS"},
            },
        }
        write_archived_state(root, clean_state)
        output = io.StringIO()
        assert run_check(root, output) == 0
        assert output.getvalue() == ""
        tests += 1

        witness_rows = (
            ("plan-empty", "plan", "PASS"),
            ("risk-halt", "plan", "PASS"),
            ("implement-empty", "implement", "PASS"),
            ("build-gate-exhausted", "build_gate", "FAIL"),
            ("verify-exhausted", "verify", "NEEDS_WORK"),
            ("fresh-context-unavailable", "implement", "BLOCKED"),
            ("codex-unavailable", "plan", "BLOCKED"),
        )
        for reason, halt_phase, phase_verdict in witness_rows:
            root = base / f"witness-{reason}"
            phases: dict[str, object] = {name: None for name in PHASE_ORDER}
            phases[halt_phase] = {
                "started_at": "2026-07-20T00:00:00Z",
                "completed_at": "2026-07-20T00:01:00Z",
                "verdict": phase_verdict,
            }
            phases["final_report"] = {
                "started_at": "2026-07-20T00:01:00Z",
                "completed_at": "2026-07-20T00:02:00Z",
                "verdict": f"BLOCKED:{reason}",
            }
            state = {"run_id": f"witness-{reason}", "phases": phases}
            assert terminal_halt_witness(phases) == (halt_phase, reason)
            write_archived_state(root, state)
            assert classify(root).status == "CLEAN"
            tests += 1

        root = base / "rolled-back-not-witness"
        rolled_back = {
            "run_id": "rolled-back",
            "phases": {
                "surface_close": {
                    "started_at": "2026-07-20T00:00:00Z",
                    "completed_at": "2026-07-20T00:01:00Z",
                    "verdict": None,
                    "skipped_reason": "surface_close_rolled_back_adjudication_malformed",
                    "continued_after_block": True,
                },
                "verify": None,
                "final_report": {"started_at": "2026-07-20T00:01:00Z", "completed_at": "2026-07-20T00:02:00Z", "verdict": "BLOCKED:surface-close-adjudication-malformed"},
            },
        }
        write_archived_state(root, rolled_back)
        assert classify(root).status == "INCOMPLETE:verify"
        tests += 1

        root = base / "malformed-final"
        malformed_final = {
            "run_id": "malformed-final",
            "phases": {
                "final_report": {"started_at": "2026-07-20T00:00:00Z", "completed_at": "2026-07-20T00:01:00Z", "verdict": None},
            },
        }
        write_archived_state(root, malformed_final)
        output = io.StringIO()
        assert run_check(root, output) == INCOMPLETE_EXIT
        assert json.loads(output.getvalue())["status"] == "MALFORMED"
        tests += 1

        root = base / "not-applicable"
        write_archived_state(root, clean_state)
        assert classify(root, {"clean-run"}).status == "NOT_APPLICABLE"
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
    before_run_ids = {
        run_id for run_id in os.environ.get("DEVLYN_RUN_IDS_BEFORE", "").splitlines()
        if run_id
    }
    return run_check(args.root, sys.stdout, before_run_ids)


if __name__ == "__main__":
    raise SystemExit(main())
