#!/usr/bin/env python3
"""Serial, window-aware operator drain for the iter-0113 quick panel."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import importlib.util
import io
import json
import math
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable
from zoneinfo import ZoneInfo


sys.dont_write_bytecode = True
REPO = pathlib.Path("/Users/aipalm/Documents/GitHub/devlyn-cli")
RUNNER = REPO / "benchmark/layer-lift/run-lift-panel.py"
SCORER = REPO / "benchmark/layer-lift/score-lift.py"
PARAMS = REPO / "benchmark/layer-lift/registered-params.json"
USAGE_CAPTURE = REPO / "benchmark/executor-quality/scripts/usage-capture-0112.py"
ACTIVE_CLI = re.compile(r"(?:^|[\s/])(?:claude\s+-p|codex\s+exec|grok\s+-p)(?:\s|$)")


class DrainError(RuntimeError):
    pass


class DrainInterrupted(RuntimeError):
    pass


@dataclass(frozen=True)
class ChildResult:
    returncode: int
    output: str


class ChildState:
    def __init__(self) -> None:
        self.child: subprocess.Popen[bytes] | None = None
        self.interrupted = False

    def handle_signal(self, signum: int, _frame: Any) -> None:
        self.interrupted = True
        if self.child is not None and self.child.poll() is None:
            try:
                os.killpg(self.child.pid, signum)
            except ProcessLookupError:
                pass


def utc_stamp(now: dt.datetime | None = None) -> str:
    instant = now or dt.datetime.now(dt.timezone.utc)
    return instant.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def append_log(path: pathlib.Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {message}\n")


def append_output(path: pathlib.Path, output: bytes) -> str:
    text = output.decode("utf-8", errors="replace")
    with path.open("ab") as handle:
        handle.write(output)
        if output and not output.endswith(b"\n"):
            handle.write(b"\n")
    return text


def pid_is_live(path: pathlib.Path) -> bool:
    if not path.is_file():
        return False
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def load_params() -> dict[str, Any]:
    try:
        value = json.loads(PARAMS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DrainError(f"registered params unavailable: {exc}") from exc
    if not isinstance(value, dict):
        raise DrainError("registered params must be an object")
    return value


def usage_utilization(payload: object) -> float:
    if not isinstance(payload, dict) or not isinstance(payload.get("five_hour"), dict):
        raise DrainError("usage raw JSON lacks five_hour")
    value = payload["five_hour"].get("utilization")
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise DrainError("usage raw JSON has invalid five_hour.utilization")
    return float(value)


def in_quiet_window(now: dt.datetime, params: dict[str, Any]) -> bool:
    try:
        window = params["quiet_window_kst"]
        start = dt.time.fromisoformat(window["start"])
        end = dt.time.fromisoformat(window["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DrainError("registered quiet_window_kst is invalid") from exc
    local = now.astimezone(ZoneInfo("Asia/Seoul")).timetz().replace(tzinfo=None)
    if start < end:
        return start <= local < end
    return local >= start or local < end


def gate_reasons(
    ps_output: str,
    usage_payload: object,
    now: dt.datetime,
    params: dict[str, Any],
    max_session_percent: float,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if ACTIVE_CLI.search(ps_output):
        reasons.append("supported CLI session is active")
    utilization = usage_utilization(usage_payload)
    if utilization > max_session_percent:
        reasons.append(f"five_hour.utilization={utilization:g}% exceeds {max_session_percent:g}%")
    if in_quiet_window(now, params):
        reasons.append("quiet_window_kst is active")
    return tuple(reasons)


def machine_ps() -> str:
    try:
        result = subprocess.run(
            ["ps", "-eo", "command"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DrainError(f"process probe unavailable: {exc}") from exc
    if result.returncode != 0:
        raise DrainError(f"process probe failed: {result.stderr.strip()}")
    return result.stdout


def capture_usage(out: pathlib.Path) -> dict[str, Any]:
    prefix = out / "usage" / utc_stamp()
    prefix.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(USAGE_CAPTURE), "--out", str(prefix)],
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise DrainError(f"usage capture failed rc={result.returncode}")
    raw_path = pathlib.Path(f"{prefix}.raw.json")
    try:
        payload = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DrainError(f"usage raw JSON unavailable: {exc}") from exc
    if not isinstance(payload, dict):
        raise DrainError("usage raw JSON must be an object")
    return payload


def gate(
    out: pathlib.Path,
    log: pathlib.Path,
    params: dict[str, Any],
    max_session_percent: float,
    state: ChildState,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    previous: tuple[str, ...] | None = None
    while True:
        if state.interrupted:
            raise DrainInterrupted()
        try:
            reasons = gate_reasons(
                machine_ps(), capture_usage(out), dt.datetime.now(dt.timezone.utc), params, max_session_percent,
            )
        except DrainError as exc:
            reasons = (str(exc),)
        if reasons != previous:
            append_log(log, "gate blocked: " + "; ".join(reasons) if reasons else "gate ready")
            previous = reasons
        if not reasons:
            return
        sleep(120)


def quick_tasks() -> list[str]:
    spec = importlib.util.spec_from_file_location("layer_lift_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise DrainError("cannot import run-lift-panel.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    params = module.read_object(module.PARAMS_PATH)
    return module.selected_tasks(params, "quick")


def latest_infra_invalid(
    path: pathlib.Path, *, previous_attempt: int | None = None,
) -> tuple[tuple[object, object, object], ...]:
    if not path.is_file():
        return ()
    latest: dict[tuple[object, object, object], dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DrainError(f"rows ledger unreadable: {exc}") from exc
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DrainError(f"rows ledger invalid at line {number}") from exc
        if not isinstance(row, dict) or type(row.get("attempt")) is not int:
            raise DrainError(f"rows ledger invalid at line {number}")
        key = (row.get("arm"), row.get("task"), row.get("rep"))
        existing = latest.get(key)
        if existing is None or row["attempt"] > existing["attempt"]:
            latest[key] = row
    return tuple(
        key for key, row in latest.items()
        if row.get("infra_invalid") is True
        and (previous_attempt is None or row["attempt"] == previous_attempt)
    )


def preflight_busy(output: str) -> bool:
    return "live writer/state found" in output or "quiet-window exclusion is active" in output


def saturation_refusal(output: str) -> bool:
    return "REFUSED: PANEL_SATURATED: further scheduling refused" in output.splitlines()


def pending_cells(cells: tuple[tuple[object, object, object], ...]) -> str:
    return ", ".join(str(cell) for cell in cells)


def runner_argv(
    model: str,
    out: pathlib.Path,
    run_id: str,
    attempt: int,
    task: str | None = None,
    *,
    resume: bool = False,
) -> list[str]:
    argv = [
        sys.executable, str(RUNNER), "run", "--model", model, "--panel", "quick",
        "--out", str(out), "--run-id", run_id, "--attempt", str(attempt),
    ]
    if resume:
        argv.append("--resume")
    if task is not None:
        argv.extend(("--task", task))
    return argv


def invoke_child(argv: list[str], log: pathlib.Path, state: ChildState) -> ChildResult:
    append_log(log, "RUN " + " ".join(argv))
    if state.interrupted:
        raise DrainInterrupted()
    process = subprocess.Popen(
        argv,
        cwd=REPO,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    state.child = process
    if state.interrupted:
        state.handle_signal(signal.SIGTERM, None)
    output, _ = process.communicate()
    state.child = None
    text = append_output(log, output)
    if state.interrupted:
        raise DrainInterrupted()
    return ChildResult(process.returncode, text)


def terminal_line(output: str) -> str | None:
    for line in output.splitlines():
        if line == "PANEL_SATURATED" or line.startswith(("LIFT-0113:", "NEEDS_TOPUP ")):
            return line
    return None


def run_sequence(
    model: str,
    out: pathlib.Path,
    run_id: str,
    log: pathlib.Path,
    *,
    wait_for_gate: Callable[[], None],
    run_child: Callable[[list[str], pathlib.Path], ChildResult],
    task_list: Callable[[], list[str]],
) -> int:
    smoke_log = out / "smoke" / "smoke.log"
    if not smoke_log.is_file() or "SMOKE-0113: PASS" not in smoke_log.read_text(encoding="utf-8"):
        wait_for_gate()
        result = run_child(
            runner_argv(model, out / "smoke", f"{run_id}-smoke", 1, "EQ3-AF2") + ["--smoke"],
            smoke_log,
        )
        append_log(log, f"smoke rc={result.returncode}")
        if result.returncode != 0 or "SMOKE-0113: PASS" not in result.output:
            append_log(log, "STOP smoke did not pass")
            return 2
    else:
        append_log(log, "smoke already passed")

    panel = out / "panel"
    pending_tasks = task_list()
    score_after_saturation_refusal = False
    for pass_number in range(1, 4):
        retry_tasks: list[str] = []
        for task in pending_tasks:
            wait_for_gate()
            result = run_child(runner_argv(model, panel, run_id, 1, task, resume=True), log)
            append_log(log, f"attempt 1 pass={pass_number} task={task} rc={result.returncode}")
            if saturation_refusal(result.output):
                append_log(log, "saturation refusal: scoring")
                score_after_saturation_refusal = True
                break
            busy_refusal = "REFUSED:" in result.output and preflight_busy(result.output)
            if "REFUSED:" in result.output and not busy_refusal:
                append_log(log, f"STOP task={task} refused outside a preflight-busy condition")
                return 2
            if busy_refusal or result.returncode != 0:
                retry_tasks.append(task)
        if score_after_saturation_refusal:
            break
        if not retry_tasks:
            break
        if pass_number == 3:
            append_log(log, f"STOP attempt 1 incomplete after 3 passes: {', '.join(retry_tasks)}")
            return 2
        pending_tasks = retry_tasks

    rows = panel / "rows.jsonl"
    attempts = () if score_after_saturation_refusal else (2, 3)
    for attempt in attempts:
        if not latest_infra_invalid(rows, previous_attempt=attempt - 1):
            continue
        for pass_number in range(1, 4):
            wait_for_gate()
            result = run_child(runner_argv(model, panel, run_id, attempt), log)
            append_log(log, f"attempt {attempt} pass={pass_number} rc={result.returncode}")
            if saturation_refusal(result.output):
                append_log(log, "saturation refusal: scoring")
                score_after_saturation_refusal = True
                break
            busy_refusal = "REFUSED:" in result.output and preflight_busy(result.output)
            if not busy_refusal and (result.returncode != 0 or "REFUSED:" in result.output):
                append_log(
                    log,
                    f"STOP attempt {attempt} retry-unsafe outcome rc={result.returncode}; "
                    f"pending infrastructure-invalid cells: {pending_cells(latest_infra_invalid(rows))}",
                )
                return 2
            if not busy_refusal:
                break
            if pass_number == 3:
                append_log(
                    log,
                    f"STOP attempt {attempt} incomplete after 3 passes; "
                    f"pending infrastructure-invalid cells: {pending_cells(latest_infra_invalid(rows))}",
                )
                return 2
        if score_after_saturation_refusal:
            break

    result = run_child(
        [sys.executable, str(SCORER), "score", "--rows", str(rows), "--params", str(PARAMS), "--out", str(out / "verdict.json")],
        out / "score.log",
    )
    line = terminal_line(result.output)
    if result.returncode != 0 or line is None:
        append_log(log, f"STOP scorer rc={result.returncode}")
        return 2
    append_log(log, line)
    (out / "drain.done").write_text(line + "\n", encoding="utf-8")
    return 0


def run_foreground(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out).resolve()
    log = out / "drain.log"
    params = load_params()
    state = ChildState()
    old_int = signal.signal(signal.SIGINT, state.handle_signal)
    old_term = signal.signal(signal.SIGTERM, state.handle_signal)
    try:
        return run_sequence(
            args.model, out, args.run_id, log,
            wait_for_gate=lambda: gate(out, log, params, args.max_session_percent, state),
            run_child=lambda argv, child_log: invoke_child(argv, child_log, state),
            task_list=quick_tasks,
        )
    except DrainInterrupted:
        append_log(log, "STOP interrupted")
        return 143
    except DrainError as exc:
        append_log(log, f"STOP {exc}")
        return 2
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)


def detach(args: argparse.Namespace) -> int:
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    pid_path = out / "drain.pid"
    if pid_is_live(pid_path):
        raise DrainError(f"drain.pid names a live process: {pid_path.read_text(encoding='utf-8').strip()}")
    try:
        first = os.fork()
    except OSError as exc:
        raise DrainError(f"first detach fork failed: {exc}") from exc
    if first:
        return 0
    os.setsid()
    try:
        second = os.fork()
    except OSError:
        os._exit(2)
    if second:
        os._exit(0)
    log = (out / "drain.log").open("ab")
    os.dup2(log.fileno(), sys.stdout.fileno())
    os.dup2(log.fileno(), sys.stderr.fileno())
    with pid_path.open("w", encoding="utf-8") as handle:
        handle.write(f"{os.getpid()}\n")
    return run_foreground(args)


def start(args: argparse.Namespace, *, detach_run: Callable[[argparse.Namespace], int] = detach) -> int:
    done = pathlib.Path(args.out).resolve() / "drain.done"
    if done.is_file():
        try:
            print(done.read_text(encoding="utf-8"), end="")
        except OSError as exc:
            raise DrainError(f"drain.done unreadable: {exc}") from exc
        return 0
    return detach_run(args)


def self_test() -> int:
    names: list[str] = []
    params = {"quiet_window_kst": {"start": "23:00", "end": "01:00"}}
    blocked = gate_reasons(
        "COMMAND\nclaude -p active\n", {"five_hour": {"utilization": 11}},
        dt.datetime(2026, 9, 3, 23, 30, tzinfo=ZoneInfo("Asia/Seoul")), params, 10,
    )
    assert blocked == (
        "supported CLI session is active",
        "five_hour.utilization=11% exceeds 10%",
        "quiet_window_kst is active",
    )
    assert gate_reasons(
        "/opt/vendor/codex exec --read-only\n", {"five_hour": {"utilization": 0}},
        dt.datetime(2026, 9, 3, 2, tzinfo=ZoneInfo("Asia/Seoul")), params, 10,
    ) == ("supported CLI session is active",)
    assert gate_reasons(
        "COMMAND\n", {"five_hour": {"utilization": 10}},
        dt.datetime(2026, 9, 3, 2, tzinfo=ZoneInfo("Asia/Seoul")), params, 10,
    ) == ()
    names.append("injected-gate-predicates")
    assert "--resume" not in runner_argv("claude-fixture", pathlib.Path("/smoke"), "smoke", 1, "EQ3-AF2")
    assert "--resume" in runner_argv("claude-fixture", pathlib.Path("/panel"), "panel", 1, "EQ3-AF2", resume=True)
    names.append("smoke-and-task-resume-argv")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")
        panel = root / "panel"
        panel.mkdir()
        (panel / "rows.jsonl").write_text(
            json.dumps({"arm": "L0", "task": "EQ3-AF2", "rep": 1, "attempt": 1, "infra_invalid": True}) + "\n",
            encoding="utf-8",
        )
        calls: list[list[str]] = []
        gates: list[None] = []
        attempt_runs: dict[int, int] = {}

        def fake_gate() -> None:
            gates.append(None)

        def fake_child(argv: list[str], child_log: pathlib.Path) -> ChildResult:
            calls.append(argv)
            if argv[1] == str(SCORER):
                output = "pair_timeouts=0\nLIFT-0113: Q1=LIFT E1=EFFICIENT Q2=LIFT E2=EFFICIENT M=fixture panel=quick receipt=fixture\n"
                append_output(child_log, output.encode())
                return ChildResult(0, output)
            attempt = int(argv[argv.index("--attempt") + 1])
            attempt_runs[attempt] = attempt_runs.get(attempt, 0) + 1
            if attempt in (2, 3) and attempt_runs[attempt] == 1:
                return ChildResult(3, "REFUSED: live writer/state found\n")
            if attempt == 2:
                (panel / "rows.jsonl").write_text(
                    json.dumps({"arm": "L0", "task": "EQ3-AF2", "rep": 1, "attempt": 2, "infra_invalid": True}) + "\n",
                    encoding="utf-8",
                )
            return ChildResult(0, "NO-JOBS: fake runner\n")

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=fake_gate, run_child=fake_child, task_list=lambda: ["EQ3-AF2"],
        )
        attempts = [int(call[call.index("--attempt") + 1]) for call in calls if call[1] == str(RUNNER)]
        assert rc == 0 and attempts == [1, 2, 2, 3, 3]
        assert all("--resume" not in call for call in calls if call[1] == str(RUNNER) and int(call[call.index("--attempt") + 1]) > 1)
        assert all("--smoke" not in call for call in calls)
        assert (root / "drain.done").is_file() and len(gates) == 5
        assert "pair_timeouts=0" in (root / "score.log").read_text(encoding="utf-8")
        drain_log = (root / "drain.log").read_text(encoding="utf-8")
        assert "pair_timeouts=0" not in drain_log and drain_log.count("LIFT-0113:") == 1
    names.append("attempt-two-busy-retries-without-resume")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")
        panel = root / "panel"
        panel.mkdir()
        pending = ("L0", "EQ3-AF2", 1)
        (panel / "rows.jsonl").write_text(
            json.dumps({"arm": pending[0], "task": pending[1], "rep": pending[2], "attempt": 1, "infra_invalid": True}) + "\n",
            encoding="utf-8",
        )
        calls: list[list[str]] = []

        def interrupted_attempt_two(argv: list[str], _log: pathlib.Path) -> ChildResult:
            calls.append(argv)
            return ChildResult(143, "interrupted\n")

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=lambda: None, run_child=interrupted_attempt_two, task_list=lambda: [],
        )
        assert rc == 2 and calls == [runner_argv("claude-fixture", panel, "fixture", 2)]
        assert (
            "STOP attempt 2 retry-unsafe outcome rc=143; "
            "pending infrastructure-invalid cells: ('L0', 'EQ3-AF2', 1)"
        ) in (root / "drain.log").read_text(encoding="utf-8")
    names.append("attempt-two-nonzero-stops-with-pending-cell")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")
        panel = root / "panel"
        panel.mkdir()
        committed = ("L0", "EQ3-AF1", 1)
        pending = ("L0", "EQ3-AF2", 1)
        (panel / "rows.jsonl").write_text(
            "\n".join((
                json.dumps({"arm": committed[0], "task": committed[1], "rep": committed[2], "attempt": 2, "infra_invalid": True}),
                json.dumps({"arm": pending[0], "task": pending[1], "rep": pending[2], "attempt": 1, "infra_invalid": True}),
            )) + "\n",
            encoding="utf-8",
        )
        calls: list[list[str]] = []

        def partial_attempt_two(argv: list[str], _log: pathlib.Path) -> ChildResult:
            calls.append(argv)
            return ChildResult(143, "interrupted\n")

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=lambda: None, run_child=partial_attempt_two, task_list=lambda: [],
        )
        assert rc == 2 and calls == [runner_argv("claude-fixture", panel, "fixture", 2)]
        assert (
            "STOP attempt 2 retry-unsafe outcome rc=143; "
            "pending infrastructure-invalid cells: ('L0', 'EQ3-AF1', 1), ('L0', 'EQ3-AF2', 1)"
        ) in (root / "drain.log").read_text(encoding="utf-8")
    names.append("partial-attempt-stop-names-all-latest-infra-invalid-cells")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")
        calls: list[list[str]] = []

        def busy_then_idle(argv: list[str], child_log: pathlib.Path) -> ChildResult:
            calls.append(argv)
            if argv[1] == str(SCORER):
                output = "PANEL_SATURATED\n"
                append_output(child_log, output.encode())
                return ChildResult(0, output)
            if len(calls) == 1:
                return ChildResult(3, "REFUSED: live writer/state found\n")
            return ChildResult(0, "NO-JOBS: fake runner\n")

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=lambda: None, run_child=busy_then_idle, task_list=lambda: ["EQ3-AF2"],
        )
        attempts = [int(call[call.index("--attempt") + 1]) for call in calls if call[1] == str(RUNNER)]
        assert rc == 0 and attempts == [1, 1]
    names.append("busy-task-retries-then-no-jobs")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")
        calls: list[list[str]] = []

        def always_busy(argv: list[str], _log: pathlib.Path) -> ChildResult:
            calls.append(argv)
            return ChildResult(3, "REFUSED: quiet-window exclusion is active\n")

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=lambda: None, run_child=always_busy, task_list=lambda: ["EQ3-AF2", "EQ3-BD1"],
        )
        tasks = [call[call.index("--task") + 1] for call in calls]
        assert rc == 2 and tasks == ["EQ3-AF2", "EQ3-BD1"] * 3
        assert "STOP attempt 1 incomplete after 3 passes: EQ3-AF2, EQ3-BD1" in (root / "drain.log").read_text(encoding="utf-8")
    names.append("busy-task-three-pass-cap")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")
        calls: list[list[str]] = []

        def saturated_attempt_one(argv: list[str], child_log: pathlib.Path) -> ChildResult:
            calls.append(argv)
            if argv[1] == str(RUNNER):
                return ChildResult(3, "REFUSED: PANEL_SATURATED: further scheduling refused\n")
            output = "PANEL_SATURATED\n"
            append_output(child_log, output.encode())
            return ChildResult(0, output)

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=lambda: None, run_child=saturated_attempt_one, task_list=lambda: ["EQ3-AF2", "EQ3-BD1"],
        )
        assert rc == 0 and [call[1] for call in calls] == [str(RUNNER), str(SCORER)]
        assert (root / "drain.done").read_text(encoding="utf-8") == "PANEL_SATURATED\n"
        assert "saturation refusal: scoring" in (root / "drain.log").read_text(encoding="utf-8")
    names.append("attempt-one-saturation-refusal-scores")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        smoke = root / "smoke"
        smoke.mkdir()
        (smoke / "smoke.log").write_text("SMOKE-0113: PASS\n", encoding="utf-8")

        def saturated_score(argv: list[str], child_log: pathlib.Path) -> ChildResult:
            assert argv[1] == str(SCORER)
            output = "pair_timeouts=0\nPANEL_SATURATED\n"
            append_output(child_log, output.encode())
            return ChildResult(0, output)

        rc = run_sequence(
            "claude-fixture", root, "fixture", root / "drain.log",
            wait_for_gate=lambda: None, run_child=saturated_score, task_list=lambda: [],
        )
        assert rc == 0 and (root / "drain.done").read_text(encoding="utf-8") == "PANEL_SATURATED\n"
        assert terminal_line("PANEL_SATURATED\n") == "PANEL_SATURATED"
        assert "pair_timeouts=0" in (root / "score.log").read_text(encoding="utf-8")
        drain_log = (root / "drain.log").read_text(encoding="utf-8")
        assert "pair_timeouts=0" not in drain_log and drain_log.count("PANEL_SATURATED") == 1
    names.append("saturation-terminal-and-score-log-isolation")

    with tempfile.TemporaryDirectory(prefix="drain-quick-self-test-") as raw:
        root = pathlib.Path(raw)
        (root / "drain.done").write_text("PANEL_SATURATED\n", encoding="utf-8")
        detaches: list[None] = []
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            rc = start(argparse.Namespace(out=str(root)), detach_run=lambda _args: detaches.append(None) or 1)
        assert rc == 0 and detaches == [] and captured.getvalue() == "PANEL_SATURATED\n"
    names.append("completed-drain-skips-detach-and-child-launches")
    print(f"PASS drain-quick self-test {len(names)}/{len(names)}: {', '.join(names)}")
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model")
    ap.add_argument("--out")
    ap.add_argument("--run-id")
    ap.add_argument("--max-session-percent", type=float, default=10)
    ap.add_argument("--self-test", action="store_true")
    return ap


def main() -> int:
    ap = parser()
    args = ap.parse_args()
    if args.self_test:
        if any(value is not None for value in (args.model, args.out, args.run_id)):
            ap.error("--self-test does not accept --model, --out, or --run-id")
        return self_test()
    if any(value is None for value in (args.model, args.out, args.run_id)):
        ap.error("--model, --out, and --run-id are required")
    if not math.isfinite(args.max_session_percent) or not 0 <= args.max_session_percent <= 100:
        ap.error("--max-session-percent must be between 0 and 100")
    try:
        return start(args)
    except DrainError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
