#!/usr/bin/env python3
"""Deterministic, sweep-stageable launcher for the iter-0110 session matrix."""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile


HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_SCHEDULE = REPO / "docs/specs/iter0110/schedule.json"
DEFAULT_PARAMS = REPO / "docs/specs/iter0110/registered-params.json"
DRIVER = HERE / "sh-driver-0110.py"
COLLECTOR = HERE / "boundary-ledger-0110.py"
MANIFEST_NAME = "launch-manifest-0110.json"
PIN_FILE = REPO / "docs/specs/iter0110/scripts.sha256"
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
APPARATUS_SCRIPTS = (
    "sh-driver-0110.py",
    "boundary-ledger-0110.py",
    "smoke-gate-0110.py",
    "derive-schedule-0110.py",
    "g0-power-0110.py",
    "score-0110.py",
    "launch-0110.py",
)
REQUIRED_PIN_TARGETS = frozenset(
    [f"benchmark/executor-quality/scripts/{name}" for name in APPARATUS_SCRIPTS]
    + [
        "docs/specs/iter0110/schedule.json",
        "docs/specs/iter0110/registered-params.json",
        "benchmark/executor-quality/tasks-0110-smoke/smoke-1 (whole tree)",
        "benchmark/executor-quality/tasks-0110-smoke/smoke-2 (whole tree)",
    ]
)
SESSION_STATUSES = frozenset(("driver_failed", "driver_receipt_invalid", "collector_failed", "collector_receipt_invalid", "completed"))
SESSION_STATUS_FIELDS = frozenset(
    (
        "engine",
        "replicate_id",
        "session_label",
        "driver_command",
        "collector_command",
        "driver_exit",
        "driver_stdout_sha256",
        "driver_stderr_sha256",
        "status",
        "collector_exit",
        "collector_stdout_sha256",
        "collector_stderr_sha256",
        "infra_affected",
        "a5_clean",
        "first_late_threshold_crossed",
        "rows_sha256",
        "boundary_ledger_sha256",
    )
)


class LaunchViolation(ValueError):
    """A frozen launch input or partial-root violation."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: pathlib.Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"cannot-read-json:{path}:{exc}") from exc


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def load_inputs(schedule_path: pathlib.Path, params_path: pathlib.Path) -> tuple[dict[str, object], dict[str, object]]:
    schedule = read_json(schedule_path)
    params = read_json(params_path)
    if not isinstance(schedule, dict) or schedule.get("schema") != "iter0110-session-horizon-schedule-v1":
        raise LaunchViolation("schedule-schema-mismatch")
    if not isinstance(params, dict) or params.get("schema") != "iter0110-registered-params-v1":
        raise LaunchViolation("params-schema-mismatch")
    if schedule.get("k") != 8 or params.get("k") != 8:
        raise LaunchViolation("registered-k-mismatch")
    if schedule.get("engines") != [*MATRIX_ENGINES, "claude-sonnet-5"] or params.get("matrix_engines") != list(MATRIX_ENGINES):
        raise LaunchViolation("registered-engine-mismatch")
    sessions = schedule.get("sessions")
    registered_schedule = params.get("schedule")
    if not isinstance(registered_schedule, dict):
        raise LaunchViolation("params-schedule-invalid")
    if not isinstance(sessions, list) or len(sessions) != registered_schedule.get("sessions"):
        raise LaunchViolation("registered-session-count-mismatch")
    for session in sessions:
        if not isinstance(session, dict) or not isinstance(session.get("tasks"), list) or len(session["tasks"]) != 8:
            raise LaunchViolation("schedule-session-shape-invalid")
    return schedule, params


def script_digests() -> dict[str, str]:
    return {name: sha256(HERE / name) for name in APPARATUS_SCRIPTS}


def whole_tree_sha256(root: pathlib.Path) -> str:
    """Implement the inventory's documented find/sort/shasum recipe."""
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: os.fsencode(f"./{path.relative_to(root)}"),
    )
    listing = b"".join(
        f"{sha256(path)}  ./{path.relative_to(root)}\n".encode("utf-8")
        for path in files
    )
    return hashlib.sha256(listing).hexdigest()


def verify_script_inventory(pin_file: pathlib.Path = PIN_FILE) -> str:
    try:
        lines = pin_file.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise LaunchViolation(f"script-pin-unreadable:{exc}") from exc
    entries = []
    for number, line in enumerate(lines, start=1):
        if not line or line.startswith("#"):
            continue
        expected, separator, target = line.partition("  ")
        if not separator or len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            raise LaunchViolation(f"script-pin-malformed:{number}")
        if not target or any(known_target == target for _known_digest, known_target in entries):
            raise LaunchViolation(f"script-pin-target-invalid:{number}")
        entries.append((expected, target))
    if not entries:
        raise LaunchViolation("script-pin-empty")
    targets = {target for _expected, target in entries}
    unknown = sorted(targets - REQUIRED_PIN_TARGETS)
    if unknown:
        raise LaunchViolation(f"script-pin-unknown-target:{unknown[0]}")
    missing = sorted(REQUIRED_PIN_TARGETS - targets)
    if missing:
        raise LaunchViolation(f"script-pin-required-target-missing:{missing[0]}")
    for expected, target in entries:
        whole_tree_suffix = " (whole tree)"
        if target.endswith(whole_tree_suffix):
            root = REPO / target[: -len(whole_tree_suffix)]
            if not root.is_dir():
                raise LaunchViolation(f"script-pin-tree-missing:{target}")
            actual = whole_tree_sha256(root)
        else:
            path = REPO / target
            try:
                actual = sha256(path)
            except OSError as exc:
                raise LaunchViolation(f"script-pin-target-unreadable:{target}") from exc
        if actual != expected:
            raise LaunchViolation(f"script-pin-mismatch:{target}")
    return sha256(pin_file)


def load_window_attestation(path: pathlib.Path, params: dict[str, object]) -> tuple[bytes, dict[str, object]]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"window-attestation-unreadable:{exc}") from exc
    if not isinstance(payload, dict):
        raise LaunchViolation("window-attestation-not-object")
    effective = params.get("effective_context")
    denominators = effective.get("context_window_denominator_tokens") if isinstance(effective, dict) else None
    if not isinstance(denominators, dict):
        raise LaunchViolation("registered-window-denominators-invalid")
    for engine in (*MATRIX_ENGINES, "claude-sonnet-5"):
        if type(denominators.get(engine)) is not int or type(payload.get(engine)) is not int:
            raise LaunchViolation(f"window-attestation-engine-invalid:{engine}")
        if payload[engine] != denominators[engine]:
            raise LaunchViolation(f"window-attestation-denominator-mismatch:{engine}")
    for name in ("attested_by", "source"):
        if not isinstance(payload.get(name), str) or not payload[name]:
            raise LaunchViolation(f"window-attestation-{name}-invalid")
    return raw, payload


def command_for(session: dict[str, object], out: pathlib.Path, run_id: str) -> list[str]:
    tasks = ",".join(str(item["task_id"]) for item in session["tasks"])
    return [
        sys.executable,
        str(DRIVER),
        "--engine",
        str(session["engine"]),
        "--session-label",
        str(session["session_label"]),
        "--tasks",
        tasks,
        "--replicate",
        str(session["replicate_index"]),
        "--out",
        str(out),
        "--run-id",
        run_id,
    ]


def collector_command_for(session: dict[str, object], out: pathlib.Path) -> list[str]:
    return [sys.executable, str(COLLECTOR), "--session-dir", str(session_directory(out, session))]


def session_key(session: dict[str, object]) -> str:
    return str(session["session_label"])


def session_directory(out: pathlib.Path, session: dict[str, object]) -> pathlib.Path:
    return out / f"{session['engine']}.{session['session_label']}.r{session['replicate_index']}"


def parse_session_dir(stdout: bytes, expected: pathlib.Path) -> pathlib.Path:
    for line in reversed(stdout.decode("utf-8", errors="replace").splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("session_dir") == str(expected):
            return expected
    raise LaunchViolation("driver-session-dir-missing")


def session_infra_affected(directory: pathlib.Path) -> bool:
    try:
        rows = [json.loads(line) for line in (directory / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError):
        return False
    return any(isinstance(row, dict) and row.get("infra_invalid") is True for row in rows)


def session_a5_clean(directory: pathlib.Path) -> bool:
    try:
        rows = [json.loads(line) for line in (directory / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
    except (OSError, json.JSONDecodeError):
        return False
    rows_by_position = {row.get("position_index"): row for row in rows if isinstance(row, dict)}
    return set(rows_by_position) == set(range(1, 9)) and all(
        row.get("infra_invalid") is False
        and row.get("catastrophic") is False
        and row.get("custody_ok") is True
        and row.get("custody_broken") is False
        for row in rows_by_position.values()
    )


def crossed_first_late_threshold(directory: pathlib.Path, engine: str, params: dict[str, object]) -> bool:
    try:
        rows = [json.loads(line) for line in (directory / "rows.jsonl").read_text(encoding="utf-8").splitlines()]
        boundary_ledger = read_json(directory / "boundary-ledger.json")
    except (OSError, json.JSONDecodeError, LaunchViolation):
        return False
    if not isinstance(boundary_ledger, dict) or not isinstance(boundary_ledger.get("boundaries"), list):
        return False
    rows_by_position = {row.get("position_index"): row for row in rows if isinstance(row, dict)}
    boundaries = {
        boundary.get("position_index"): boundary
        for boundary in boundary_ledger["boundaries"]
        if isinstance(boundary, dict)
    }
    if set(rows_by_position) != set(range(1, 9)) or not set(range(1, 5)) <= set(boundaries):
        return False
    if any(row.get("custody_ok") is not True or row.get("custody_broken") is not False for row in (rows_by_position[position] for position in range(1, 6))):
        return False
    effective = params.get("effective_context")
    if not isinstance(effective, dict):
        return False
    denominators = effective.get("context_window_denominator_tokens")
    absolute = effective.get("absolute_threshold_tokens")
    fraction = effective.get("context_window_fraction_threshold")
    if not isinstance(denominators, dict) or type(absolute) is not int or not isinstance(fraction, (int, float)) or type(denominators.get(engine)) is not int:
        return False
    threshold = max(absolute, fraction * denominators[engine])
    return any(
        boundary.get("records_invalid") is False
        and type(boundary.get("peak_effective_context")) is int
        and boundary["peak_effective_context"] >= threshold
        for boundary in (boundaries[position] for position in range(1, 5))
    )


def base_manifest(
    schedule_path: pathlib.Path,
    params_path: pathlib.Path,
    run_id: str,
    pin_file_sha256: str,
    window_attestation_bytes: bytes,
) -> dict[str, object]:
    return {
        "schema": "iter0110-launch-manifest-v1",
        "run_id": run_id,
        "schedule_sha256": sha256(schedule_path),
        "params_sha256": sha256(params_path),
        "script_sha256": script_digests(),
        "scripts_sha256_pin_file": pin_file_sha256,
        "window_attestation_sha256": hashlib.sha256(window_attestation_bytes).hexdigest(),
        "window_attestation_bytes_base64": base64.b64encode(window_attestation_bytes).decode("ascii"),
        "sessions": {},
        "a5": {
            engine: {"a5_evaluated_session": None, "a5_crossed": None}
            for engine in MATRIX_ENGINES
        },
        "terminal": "RUNNING",
    }


def load_manifest(
    out: pathlib.Path,
    schedule_path: pathlib.Path,
    params_path: pathlib.Path,
    run_id: str,
    pin_file_sha256: str,
    window_attestation_bytes: bytes,
) -> dict[str, object]:
    path = out / MANIFEST_NAME
    if not path.exists():
        return base_manifest(schedule_path, params_path, run_id, pin_file_sha256, window_attestation_bytes)
    manifest = read_json(path)
    if not isinstance(manifest, dict) or manifest.get("schema") != "iter0110-launch-manifest-v1":
        raise LaunchViolation("launch-manifest-schema-mismatch")
    expected = base_manifest(schedule_path, params_path, run_id, pin_file_sha256, window_attestation_bytes)
    for key in (
        "run_id",
        "schedule_sha256",
        "params_sha256",
        "script_sha256",
        "scripts_sha256_pin_file",
        "window_attestation_sha256",
        "window_attestation_bytes_base64",
    ):
        if manifest.get(key) != expected[key]:
            raise LaunchViolation(f"launch-manifest-{key}-mismatch")
    statuses = validate_session_statuses(manifest.get("sessions"))
    schedule, _params = load_inputs(schedule_path, params_path)
    validate_recorded_sessions(statuses, schedule["sessions"], out, run_id)
    validate_a5_state(manifest, schedule["sessions"], statuses)
    return manifest


def write_manifest(out: pathlib.Path, manifest: dict[str, object]) -> None:
    write_json(out / MANIFEST_NAME, manifest)


def run_session(session: dict[str, object], out: pathlib.Path, run_id: str, params: dict[str, object]) -> dict[str, object]:
    command = command_for(session, out, run_id)
    collector_command = collector_command_for(session, out)
    driver = subprocess.run(command, cwd=REPO, capture_output=True)
    status = {
        "engine": session["engine"],
        "replicate_id": session["replicate_id"],
        "session_label": session["session_label"],
        "driver_command": command,
        "collector_command": collector_command,
        "driver_exit": driver.returncode,
        "driver_stdout_sha256": hashlib.sha256(driver.stdout).hexdigest(),
        "driver_stderr_sha256": hashlib.sha256(driver.stderr).hexdigest(),
        "status": "driver_failed",
        "collector_exit": None,
        "collector_stdout_sha256": None,
        "collector_stderr_sha256": None,
        "infra_affected": False,
        "a5_clean": False,
        "first_late_threshold_crossed": None,
        "rows_sha256": None,
        "boundary_ledger_sha256": None,
    }
    if driver.returncode != 0:
        return status
    try:
        directory = parse_session_dir(driver.stdout, session_directory(out, session))
    except LaunchViolation:
        status["status"] = "driver_receipt_invalid"
        return status
    collector = subprocess.run(collector_command, cwd=REPO, capture_output=True)
    status.update(
        {
            "collector_exit": collector.returncode,
            "collector_stdout_sha256": hashlib.sha256(collector.stdout).hexdigest(),
            "collector_stderr_sha256": hashlib.sha256(collector.stderr).hexdigest(),
        }
    )
    if collector.returncode != 0:
        status["status"] = "collector_failed"
        return status
    try:
        status["rows_sha256"] = sha256(directory / "rows.jsonl")
        status["boundary_ledger_sha256"] = sha256(directory / "boundary-ledger.json")
    except OSError:
        status["status"] = "collector_receipt_invalid"
        return status
    status["infra_affected"] = session_infra_affected(directory)
    status["a5_clean"] = session_a5_clean(directory)
    if session["engine"] in MATRIX_ENGINES:
        status["first_late_threshold_crossed"] = crossed_first_late_threshold(directory, str(session["engine"]), params)
    status["status"] = "completed"
    return status


def completed_clean(status: object) -> bool:
    return (
        isinstance(status, dict)
        and status.get("status") == "completed"
        and status.get("infra_affected") is False
    )


def completed_a5_clean(status: object) -> bool:
    return completed_clean(status) and isinstance(status, dict) and status.get("a5_clean") is True


def status_violation(label: object, reason: str) -> None:
    raise LaunchViolation(f"launch-manifest-status-invalid:{label}:{reason}")


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def validate_session_status(label: object, status: object) -> None:
    if not isinstance(status, dict):
        status_violation(label, "not-object")
    if set(status) != SESSION_STATUS_FIELDS:
        status_violation(label, "fields")
    if status.get("session_label") != label or not isinstance(label, str) or not label:
        status_violation(label, "session-label")
    if status.get("status") not in SESSION_STATUSES:
        status_violation(label, "status")
    if status.get("engine") not in (*MATRIX_ENGINES, "claude-sonnet-5"):
        status_violation(label, "engine")
    if not isinstance(status.get("replicate_id"), str) or not status["replicate_id"]:
        status_violation(label, "replicate-id")
    if not isinstance(status.get("driver_command"), list) or not status["driver_command"] or not all(isinstance(part, str) for part in status["driver_command"]):
        status_violation(label, "driver-command")
    if not isinstance(status.get("collector_command"), list) or not status["collector_command"] or not all(isinstance(part, str) for part in status["collector_command"]):
        status_violation(label, "collector-command")
    if type(status.get("driver_exit")) is not int or not is_sha256(status.get("driver_stdout_sha256")) or not is_sha256(status.get("driver_stderr_sha256")):
        status_violation(label, "driver-receipt")
    collector_exit = status.get("collector_exit")
    if collector_exit is not None and type(collector_exit) is not int:
        status_violation(label, "collector-exit")
    collector_fields = ("collector_stdout_sha256", "collector_stderr_sha256")
    if collector_exit is None:
        if any(status[field] is not None for field in (*collector_fields, "rows_sha256", "boundary_ledger_sha256")):
            status_violation(label, "collector-receipt")
    elif not all(is_sha256(status[field]) for field in collector_fields):
        status_violation(label, "collector-receipt")
    if type(status.get("infra_affected")) is not bool or type(status.get("a5_clean")) is not bool:
        status_violation(label, "infra_affected")
    first_late = status.get("first_late_threshold_crossed")
    if first_late is not None and type(first_late) is not bool:
        status_violation(label, "first-late-threshold-crossed")
    name = status["status"]
    if name == "driver_failed":
        if status["driver_exit"] == 0 or collector_exit is not None or first_late is not None or status["a5_clean"]:
            status_violation(label, "driver-failed")
    elif name == "driver_receipt_invalid":
        if status["driver_exit"] != 0 or collector_exit is not None or first_late is not None or status["a5_clean"]:
            status_violation(label, "driver-receipt-invalid")
    elif name == "collector_failed":
        if status["driver_exit"] != 0 or collector_exit in (None, 0) or first_late is not None or status["a5_clean"]:
            status_violation(label, "collector-failed")
    elif name == "collector_receipt_invalid":
        if status["driver_exit"] != 0 or collector_exit != 0 or first_late is not None or status["a5_clean"]:
            status_violation(label, "collector-receipt-invalid")
    else:
        if status["driver_exit"] != 0 or collector_exit != 0 or not is_sha256(status.get("rows_sha256")) or not is_sha256(status.get("boundary_ledger_sha256")):
            status_violation(label, "completed-receipt")
        if status["engine"] in MATRIX_ENGINES and type(first_late) is not bool:
            status_violation(label, "first-late-threshold-crossed")
        if status["engine"] not in MATRIX_ENGINES and first_late is not None:
            status_violation(label, "first-late-threshold-crossed")


def validate_session_statuses(statuses: object) -> dict[str, object]:
    if not isinstance(statuses, dict):
        raise LaunchViolation("launch-manifest-sessions-invalid")
    for label, status in statuses.items():
        validate_session_status(label, status)
    return statuses


def validate_recorded_sessions(
    statuses: dict[str, object], sessions: list[dict[str, object]], out: pathlib.Path, run_id: str
) -> None:
    scheduled = {session_key(session): session for session in sessions}
    for label, status in statuses.items():
        session = scheduled.get(label)
        if session is None:
            status_violation(label, "unknown-schedule-session")
        if status["engine"] != session["engine"] or status["replicate_id"] != session["replicate_id"]:
            status_violation(label, "schedule-identity")
        if status["driver_command"] != command_for(session, out, run_id):
            status_violation(label, "driver-command-mismatch")
        if status["collector_command"] != collector_command_for(session, out):
            status_violation(label, "collector-command-mismatch")


def validate_a5_state(
    manifest: dict[str, object], sessions: list[dict[str, object]], statuses: dict[str, object]
) -> None:
    state = manifest.get("a5")
    if not isinstance(state, dict) or set(state) != set(MATRIX_ENGINES):
        raise LaunchViolation("launch-manifest-a5-invalid:engines")
    for engine in MATRIX_ENGINES:
        record = state[engine]
        if not isinstance(record, dict) or set(record) != {"a5_evaluated_session", "a5_crossed"}:
            raise LaunchViolation(f"launch-manifest-a5-invalid:{engine}:fields")
        evaluated = record["a5_evaluated_session"]
        crossed = record["a5_crossed"]
        first_clean = next(
            (
                session
                for session in sessions
                if session["engine"] == engine and completed_a5_clean(statuses.get(session_key(session)))
            ),
            None,
        )
        if first_clean is None:
            if evaluated is not None or crossed is not None:
                raise LaunchViolation(f"launch-manifest-a5-invalid:{engine}:unrecorded")
            continue
        status = statuses[session_key(first_clean)]
        if evaluated != session_key(first_clean) or crossed is not status["first_late_threshold_crossed"]:
            raise LaunchViolation(f"launch-manifest-a5-invalid:{engine}:record")


def record_a5_if_first_clean(manifest: dict[str, object], session: dict[str, object], status: dict[str, object]) -> None:
    engine = str(session["engine"])
    if engine not in MATRIX_ENGINES or not completed_a5_clean(status):
        return
    record = manifest["a5"][engine]
    if record["a5_evaluated_session"] is not None:
        return
    record["a5_evaluated_session"] = session_key(session)
    record["a5_crossed"] = status["first_late_threshold_crossed"]


def status_counts(statuses: dict[str, object]) -> dict[str, int]:
    validate_session_statuses(statuses)
    counts: dict[str, int] = {}
    for status in statuses.values():
        if completed_clean(status):
            name = "completed"
        elif status["status"] == "completed" and status["infra_affected"] is True:
            name = "infra_affected"
        else:
            name = status["status"]
        counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def terminalize(manifest: dict[str, object]) -> str:
    counts = status_counts(validate_session_statuses(manifest.get("sessions")))
    manifest["terminal_status_counts"] = counts
    terminal = (
        "LAUNCH_COMPLETE"
        if manifest.get("terminal") != "LAUNCH_PARTIAL"
        and counts == {"completed": len(manifest["sessions"])}
        else "LAUNCH_PARTIAL"
    )
    manifest["terminal"] = terminal
    return terminal


def receipt(out: pathlib.Path, terminal: str, manifest: dict[str, object], details: dict[str, object]) -> None:
    write_json(out / "launch-abort-0110.json", {"terminal": terminal, "details": details, "partial_session_status": manifest["sessions"]})


def infra_abort_streak(selected: list[dict[str, object]], statuses: dict[str, object]) -> int:
    streak = 0
    for session in selected:
        status = statuses.get(session_key(session))
        if isinstance(status, dict) and status.get("infra_affected") is True:
            streak += 1
        else:
            streak = 0
        if streak >= 3:
            return streak
    return 0


def derive_terminal(manifest: dict[str, object], selected: list[dict[str, object]]) -> tuple[str, dict[str, object]] | None:
    terminal = manifest.get("terminal")
    if terminal in {"A5_SUBJECT_UNAVAILABLE", "FAIL_FAST_THRESHOLD_UNREACHED", "INFRA_ABORT"}:
        return str(terminal), {}
    statuses = manifest["sessions"]
    streak = infra_abort_streak(selected, statuses)
    if streak >= 3:
        return "INFRA_ABORT", {"consecutive_infra_affected_sessions": streak}
    phase_a = [session for session in selected if session["replicate_id"] == selected[0]["replicate_id"]]
    if all(session_key(session) in statuses for session in phase_a):
        missing_a5 = next((engine for engine in MATRIX_ENGINES if manifest["a5"][engine]["a5_evaluated_session"] is None), None)
        if missing_a5 is not None:
            return "A5_SUBJECT_UNAVAILABLE", {"engine": missing_a5, "reason": "no-first-completed-clean-session"}
    for engine in MATRIX_ENGINES:
        if manifest["a5"][engine]["a5_crossed"] is False:
            return "FAIL_FAST_THRESHOLD_UNREACHED", {"engine": engine, "reason": "first-late-threshold-not-crossed"}
    return None


def persist_and_derive_terminal(out: pathlib.Path, manifest: dict[str, object], selected: list[dict[str, object]]) -> str | None:
    write_manifest(out, manifest)
    derived = derive_terminal(manifest, selected)
    if derived is None:
        return None
    terminal, details = derived
    manifest["terminal"] = terminal
    manifest["terminal_status_counts"] = status_counts(manifest["sessions"])
    receipt(out, terminal, manifest, details)
    write_manifest(out, manifest)
    return terminal


def run(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    if args.sweep < 1 or args.sweep > schedule.get("sweeps"):
        raise LaunchViolation("sweep-out-of-range")
    if args.lanes < 1:
        raise LaunchViolation("lanes-must-be-positive")
    selected = [session for session in schedule["sessions"] if session["sweep_id"] == args.sweep]
    if len(selected) != 24:
        raise LaunchViolation("sweep-session-count-mismatch")
    pin_file_sha256 = verify_script_inventory()
    window_attestation_bytes, _window_attestation = load_window_attestation(args.window_attestation, params)
    if args.dry_run:
        print(f"DRY_RUN: sweep={args.sweep} sessions={len(selected)} attempts={len(selected) * 8} lanes={args.lanes}")
        for session in selected:
            print(shlex.join(command_for(session, args.out, args.run_id)))
            print(shlex.join(collector_command_for(session, args.out)))
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(
        args.out,
        args.schedule,
        args.params,
        args.run_id,
        pin_file_sha256,
        window_attestation_bytes,
    )
    statuses = manifest["sessions"]
    replicate_ids = tuple(dict.fromkeys(str(session["replicate_id"]) for session in selected))
    for replicate_id in replicate_ids:
        block = [session for session in selected if str(session["replicate_id"]) == replicate_id]
        present = [session_key(session) in statuses for session in block]
        if any(present[index] and not present[index - 1] for index in range(1, len(present))):
            raise LaunchViolation(f"launch-manifest-block-order-gap:{replicate_id}")
    if persist_and_derive_terminal(args.out, manifest, selected) is not None:
        return 2

    missing_a5 = next(
        (engine for engine in MATRIX_ENGINES if manifest["a5"][engine]["a5_evaluated_session"] is None),
        None,
    )
    if missing_a5 is not None:
        if args.sweep != 1:
            raise LaunchViolation("a5-gate-requires-sweep-one")
        gate = [session for session in selected if str(session["replicate_id"]) == replicate_ids[0]]
        for session in gate:
            if session_key(session) in statuses:
                continue
            status = run_session(session, args.out, args.run_id, params)
            statuses[session_key(session)] = status
            record_a5_if_first_clean(manifest, session, status)
            if persist_and_derive_terminal(args.out, manifest, selected) is not None:
                return 2
            if all(manifest["a5"][engine]["a5_evaluated_session"] is not None for engine in MATRIX_ENGINES):
                break

    blocks = [
        [session for session in selected if str(session["replicate_id"]) == replicate_id and session_key(session) not in statuses]
        for replicate_id in replicate_ids
    ]
    blocks = [block for block in blocks if block]

    def run_block(block: list[dict[str, object]]) -> list[tuple[dict[str, object], dict[str, object]]]:
        return [(session, run_session(session, args.out, args.run_id, params)) for session in block]

    for start in range(0, len(blocks), args.lanes):
        batch = blocks[start : start + args.lanes]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.lanes) as executor:
            futures = [executor.submit(run_block, block) for block in batch]
            outcomes = [future.result() for future in futures]
        for block_outcomes in outcomes:
            for session, status in block_outcomes:
                statuses[session_key(session)] = status
        if persist_and_derive_terminal(args.out, manifest, selected) is not None:
            return 2
    terminal = terminalize(manifest)
    write_manifest(args.out, manifest)
    print(f"TERMINAL: {terminal}")
    return 0 if terminal == "LAUNCH_COMPLETE" else 2


def self_test() -> None:
    schedule, params = load_inputs(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    selected = [session for session in schedule["sessions"] if session["sweep_id"] == 1]
    if len(selected) != 24 or sum(len(session["tasks"]) for session in selected) != 192:
        raise AssertionError("sweep count mismatch")
    command = command_for(selected[0], pathlib.Path("/tmp/iter0110-launch-test"), "test-run")
    if command[command.index("--tasks") + 1] != "EQ3-MI6,EQ3-UA6,EQ3-BD2,EQ3-MI3,EQ3-UA4,EQ3-MI4,EQ3-MI7,EQ3-MI1":
        raise AssertionError("driver task order mismatch")
    with tempfile.TemporaryDirectory(prefix="iter0110-launch-") as temporary:
        directory = pathlib.Path(temporary)
        pin_file = directory / "scripts.sha256"
        pin_file.write_bytes(PIN_FILE.read_bytes())
        if verify_script_inventory(pin_file) != sha256(PIN_FILE):
            raise AssertionError("valid pin inventory did not verify")
        tampered_pin = pin_file.read_text(encoding="utf-8").replace("0b79", "0b78", 1)
        pin_file.write_text(tampered_pin, encoding="utf-8")
        try:
            verify_script_inventory(pin_file)
        except LaunchViolation as exc:
            if "script-pin-mismatch" not in str(exc):
                raise AssertionError("tampered inventory had the wrong failure") from exc
        else:
            raise AssertionError("tampered inventory was accepted")
        missing_pin = "\n".join(
            line
            for line in PIN_FILE.read_text(encoding="utf-8").splitlines()
            if not line.endswith("  benchmark/executor-quality/scripts/sh-driver-0110.py")
        ) + "\n"
        pin_file.write_text(missing_pin, encoding="utf-8")
        try:
            verify_script_inventory(pin_file)
        except LaunchViolation as exc:
            if "script-pin-required-target-missing" not in str(exc):
                raise AssertionError("incomplete inventory had the wrong failure") from exc
        else:
            raise AssertionError("incomplete inventory was accepted")
        attestation = directory / "window-attestation.json"
        attestation.write_text(
            json.dumps(
                {
                    "attested_by": "self-test",
                    "source": "self-test",
                    "claude-opus-5": 200000,
                    "claude-opus-4-8": 200000,
                    "claude-sonnet-5": 200000,
                }
            ),
            encoding="utf-8",
        )
        raw_attestation, _payload = load_window_attestation(attestation, params)
        invalid_attestation = json.loads(attestation.read_text(encoding="utf-8"))
        invalid_attestation["claude-sonnet-5"] = 199999
        attestation.write_text(json.dumps(invalid_attestation), encoding="utf-8")
        try:
            load_window_attestation(attestation, params)
        except LaunchViolation as exc:
            if "window-attestation-denominator-mismatch" not in str(exc):
                raise AssertionError("tampered attestation had the wrong failure") from exc
        else:
            raise AssertionError("tampered attestation was accepted")

        def completed_status(label: str, engine: str = "claude-opus-5", infra_affected: bool = False, a5_clean: bool = True, threshold_crossed: bool = True) -> dict[str, object]:
            digest = "0" * 64
            return {
                "engine": engine,
                "replicate_id": "self-test-replicate",
                "session_label": label,
                "driver_command": ["self-test-driver"],
                "collector_command": ["self-test-collector"],
                "driver_exit": 0,
                "driver_stdout_sha256": digest,
                "driver_stderr_sha256": digest,
                "status": "completed",
                "collector_exit": 0,
                "collector_stdout_sha256": digest,
                "collector_stderr_sha256": digest,
                "infra_affected": infra_affected,
                "a5_clean": a5_clean,
                "first_late_threshold_crossed": threshold_crossed if engine in MATRIX_ENGINES else None,
                "rows_sha256": digest,
                "boundary_ledger_sha256": digest,
            }

        def driver_failed_status(label: str) -> dict[str, object]:
            status = completed_status(label)
            status.update(
                {
                    "driver_exit": 1,
                    "status": "driver_failed",
                    "collector_exit": None,
                    "collector_stdout_sha256": None,
                    "collector_stderr_sha256": None,
                    "infra_affected": False,
                    "a5_clean": False,
                    "first_late_threshold_crossed": None,
                    "rows_sha256": None,
                    "boundary_ledger_sha256": None,
                }
            )
            return status

        manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
        manifest["terminal"] = "INFRA_ABORT"
        if derive_terminal(manifest, selected) != ("INFRA_ABORT", {}):
            raise AssertionError("sticky terminal was not derived")
        partial_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
        partial_manifest["sessions"] = {
            "prior-failed": driver_failed_status("prior-failed"),
            "later-clean": completed_status("later-clean"),
        }
        if terminalize(partial_manifest) != "LAUNCH_PARTIAL":
            raise AssertionError("manifest-wide driver failure was accepted")
        partial_manifest["sessions"]["later-clean-2"] = completed_status("later-clean-2")
        if terminalize(partial_manifest) != "LAUNCH_PARTIAL":
            raise AssertionError("partial terminal became complete after a later clean sweep")
        infra_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
        infra_manifest["sessions"] = {
            "clean-before": completed_status("clean-before"),
            "infra": completed_status("infra", infra_affected=True, a5_clean=False),
            "clean-after": completed_status("clean-after"),
        }
        if terminalize(infra_manifest) != "LAUNCH_PARTIAL" or infra_manifest["terminal_status_counts"] != {"completed": 2, "infra_affected": 1}:
            raise AssertionError("nonconsecutive infra-affected session was accepted")
        for name, value in (("missing", None), ("null", None), ("string", "false")):
            malformed = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
            malformed_status = completed_status(f"malformed-{name}")
            if name == "missing":
                del malformed_status["infra_affected"]
            else:
                malformed_status["infra_affected"] = value
            malformed["sessions"] = {f"malformed-{name}": malformed_status}
            try:
                terminalize(malformed)
            except LaunchViolation as exc:
                if f"launch-manifest-status-invalid:malformed-{name}:" not in str(exc):
                    raise AssertionError("malformed status had the wrong terminal failure") from exc
            else:
                raise AssertionError("malformed status terminalized")
            write_manifest(directory, malformed)
            try:
                load_manifest(directory, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
            except LaunchViolation as exc:
                if f"launch-manifest-status-invalid:malformed-{name}:" not in str(exc):
                    raise AssertionError("malformed status had the wrong load failure") from exc
            else:
                raise AssertionError("malformed status loaded")

        exact_out = directory / "exact-command"
        exact_out.mkdir()
        exact_session = selected[0]
        exact_status = completed_status(str(exact_session["session_label"]), str(exact_session["engine"]))
        exact_status.update(
            {
                "replicate_id": exact_session["replicate_id"],
                "driver_command": command_for(exact_session, exact_out, "self-test"),
                "collector_command": collector_command_for(exact_session, exact_out),
            }
        )
        exact_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
        exact_manifest["sessions"] = {str(exact_session["session_label"]): exact_status}
        exact_manifest["a5"][str(exact_session["engine"])] = {
            "a5_evaluated_session": exact_session["session_label"],
            "a5_crossed": True,
        }
        write_manifest(exact_out, exact_manifest)
        load_manifest(exact_out, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
        for field, command_name in (
            ("driver_command", "driver"),
            ("collector_command", "collector"),
        ):
            exact_manifest["sessions"][str(exact_session["session_label"])][field] = ["python", "unregistered-driver.py", "--wrong"]
            write_manifest(exact_out, exact_manifest)
            try:
                load_manifest(exact_out, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", sha256(PIN_FILE), raw_attestation)
            except LaunchViolation as exc:
                expected_error = f"launch-manifest-status-invalid:{exact_session['session_label']}:{command_name}-command-mismatch"
                if str(exc) != expected_error:
                    raise AssertionError(f"wrong {command_name} command had the wrong load failure") from exc
            else:
                raise AssertionError(f"wrong {command_name} command was accepted")
            exact_manifest["sessions"][str(exact_session["session_label"])][field] = (
                command_for(exact_session, exact_out, "self-test")
                if command_name == "driver"
                else collector_command_for(exact_session, exact_out)
            )
        synthetic_engines = ("claude-opus-5", "claude-opus-4-8", "claude-sonnet-5", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5")
        synthetic_sessions = [
            {
                "sweep_id": 1,
                "engine": synthetic_engines[index % 6],
                "session_label": f"a5-{index}",
                "replicate_id": f"a5-block-{index // 6}",
                "replicate_index": index // 6,
                "tasks": [{"task_id": str(position)} for position in range(8)],
            }
            for index in range(24)
        ]
        def run_a5_fixture(infra: set[str], failed: set[str], existing: dict[str, object] | None = None) -> tuple[int, dict[str, object], list[str], list[dict[str, object]], list[int]]:
            manifest = existing or {
                "terminal": "RUNNING",
                "sessions": {},
                "a5": {engine: {"a5_evaluated_session": None, "a5_crossed": None} for engine in MATRIX_ENGINES},
            }
            calls: list[str] = []
            persisted: list[dict[str, object]] = []
            workers: list[int] = []
            originals = {name: globals()[name] for name in ("load_inputs", "verify_script_inventory", "load_window_attestation", "load_manifest", "write_manifest", "receipt", "run_session")}
            original_executor = concurrent.futures.ThreadPoolExecutor
            try:
                globals().update(
                    {
                        "load_inputs": lambda _schedule, _params: ({"sweeps": 1, "sessions": synthetic_sessions}, params),
                        "verify_script_inventory": lambda: "self-test-pin",
                        "load_window_attestation": lambda _path, _params: (b"{}", {}),
                        "load_manifest": lambda *_args: manifest,
                        "write_manifest": lambda _out, current: persisted.append(json.loads(canonical_bytes(current))),
                        "receipt": lambda *_args: None,
                        "run_session": lambda session, *_args: calls.append(session_key(session)) or completed_status(session_key(session), str(session["engine"]), session_key(session) in infra, session_key(session) not in infra, session_key(session) not in failed),
                    }
                )
                concurrent.futures.ThreadPoolExecutor = lambda *args, **kwargs: workers.append(kwargs["max_workers"]) or original_executor(*args, **kwargs)
                result = run(argparse.Namespace(schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, sweep=1, lanes=3, window_attestation=attestation, dry_run=False, out=directory, run_id="a5-self-test"))
            finally:
                concurrent.futures.ThreadPoolExecutor = original_executor
                globals().update(originals)
            return result, manifest, calls, persisted, workers
        failed_result, failed_manifest, failed_calls, failed_persisted, _failed_workers = run_a5_fixture(set(), {"a5-0"})
        if failed_result != 2 or failed_calls != ["a5-0"] or failed_manifest["terminal"] != "FAIL_FAST_THRESHOLD_UNREACHED" or failed_persisted[-2]["a5"]["claude-opus-5"] != {"a5_evaluated_session": "a5-0", "a5_crossed": False}:
            raise AssertionError("first failing A5 session was not persisted before fail-fast")
        infra_result, infra_manifest, infra_calls, infra_persisted, _infra_workers = run_a5_fixture({"a5-0"}, {"a5-4"})
        if infra_result != 2 or infra_calls != [f"a5-{index}" for index in range(5)] or infra_manifest["a5"] != {"claude-opus-5": {"a5_evaluated_session": "a5-4", "a5_crossed": False}, "claude-opus-4-8": {"a5_evaluated_session": "a5-1", "a5_crossed": True}} or infra_persisted[-2]["a5"] != infra_manifest["a5"]:
            raise AssertionError("infra-affected first A5 session did not serially persist both engine records")
        unavailable_result, unavailable_manifest, unavailable_calls, unavailable_persisted, _unavailable_workers = run_a5_fixture({"a5-0", "a5-4"}, set())
        if unavailable_result != 2 or unavailable_calls != [f"a5-{index}" for index in range(6)] or unavailable_manifest["terminal"] != "A5_SUBJECT_UNAVAILABLE" or unavailable_manifest["a5"]["claude-opus-5"] != {"a5_evaluated_session": None, "a5_crossed": None} or unavailable_persisted[-1]["terminal"] != "A5_SUBJECT_UNAVAILABLE":
            raise AssertionError("completed A5 gate without an opus-5 subject did not abort")
        subject_resume = {**json.loads(canonical_bytes(unavailable_manifest)), "terminal": "RUNNING"}
        subject_result, subject_manifest, subject_calls, subject_persisted, _subject_workers = run_a5_fixture(set(), set(), subject_resume)
        if subject_result != 2 or subject_calls or subject_manifest["terminal"] != "A5_SUBJECT_UNAVAILABLE" or subject_persisted[-1]["terminal"] != "A5_SUBJECT_UNAVAILABLE":
            raise AssertionError("A5 subject abort resumed a session")
        infra_resume = {"terminal": "RUNNING", "sessions": {f"a5-{index}": completed_status(f"a5-{index}", str(synthetic_sessions[index]["engine"]), True, False) for index in range(3)}, "a5": {engine: {"a5_evaluated_session": None, "a5_crossed": None} for engine in MATRIX_ENGINES}}
        resume_result, resume_manifest, resume_calls, resume_persisted, _resume_workers = run_a5_fixture(set(), set(), infra_resume)
        if resume_result != 2 or resume_calls or resume_manifest["terminal"] != "INFRA_ABORT" or resume_persisted[-1]["terminal"] != "INFRA_ABORT":
            raise AssertionError("infra abort resumed a session")
        pass_result, pass_manifest, pass_calls, _pass_persisted, pass_workers = run_a5_fixture(set(), set())
        if pass_result != 0 or len(pass_calls) != 24 or pass_calls[:2] != ["a5-0", "a5-1"] or pass_manifest["terminal"] != "LAUNCH_COMPLETE" or pass_workers != [3, 3]:
            raise AssertionError("passing A5 gate did not open phase B on the configured lanes")
        second_selected = [session for session in schedule["sessions"] if session["sweep_id"] == 2]
        prior_sessions = [session for session in schedule["sessions"] if session["sweep_id"] == 1]
        second_manifest: dict[str, object] = {
            "terminal": "LAUNCH_COMPLETE",
            "sessions": {
                str(session["session_label"]): completed_status(str(session["session_label"]), str(session["engine"]))
                for session in prior_sessions
            },
            "a5": {
                engine: {
                    "a5_evaluated_session": next(
                        str(session["session_label"])
                        for session in prior_sessions
                        if session["engine"] == engine
                    ),
                    "a5_crossed": True,
                }
                for engine in MATRIX_ENGINES
            },
        }
        second_a5_before = canonical_bytes(second_manifest["a5"])
        second_calls: list[str] = []
        originals = {name: globals()[name] for name in ("load_inputs", "verify_script_inventory", "load_window_attestation", "load_manifest", "write_manifest", "receipt", "run_session")}
        try:
            globals().update(
                {
                    "load_inputs": lambda _schedule, _params: (schedule, params),
                    "verify_script_inventory": lambda: "self-test-pin",
                    "load_window_attestation": lambda _path, _params: (b"{}", {}),
                    "load_manifest": lambda *_args: second_manifest,
                    "write_manifest": lambda *_args: None,
                    "receipt": lambda *_args: None,
                    "run_session": lambda session, *_args: (
                        second_calls.append(str(session["session_label"]))
                        or completed_status(str(session["session_label"]), str(session["engine"]))
                    ),
                }
            )
            second_result = run(
                argparse.Namespace(
                    schedule=DEFAULT_SCHEDULE,
                    params=DEFAULT_PARAMS,
                    sweep=2,
                    lanes=1,
                    window_attestation=attestation,
                    dry_run=False,
                    out=directory,
                    run_id="a5-sweep-two-self-test",
                )
            )
        finally:
            globals().update(originals)
        if (
            second_result != 0
            or second_calls[:6] != [str(session["session_label"]) for session in second_selected[:6]]
            or canonical_bytes(second_manifest["a5"]) != second_a5_before
        ):
            raise AssertionError("A5 was re-evaluated after a prior clean sweep")
        rows = [
            {
                "position_index": position,
                "infra_invalid": False,
                "catastrophic": False,
                "custody_ok": True,
                "custody_broken": False,
            }
            for position in range(1, 9)
        ]
        (directory / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        if not session_a5_clean(directory):
            raise AssertionError("clean A5 session was not recognized")
        rows[0]["catastrophic"] = True
        (directory / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        if session_a5_clean(directory):
            raise AssertionError("catastrophic A5 session was accepted")
        rows[0]["catastrophic"] = False
        (directory / "rows.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        write_json(
            directory / "boundary-ledger.json",
            {
                "boundaries": [
                    {
                        "position_index": position,
                        "records_invalid": False,
                    "peak_effective_context": 100000 if position == 4 else 1000,
                    }
                    for position in range(1, 9)
                ]
            },
        )
        if not crossed_first_late_threshold(directory, "claude-opus-5", params):
            raise AssertionError("A5 threshold crossing was not recognized")
        write_json(
            directory / "boundary-ledger.json",
            {"boundaries": [{"position_index": position, "records_invalid": False, "peak_effective_context": 1000} for position in range(1, 9)]},
        )
        if crossed_first_late_threshold(directory, "claude-opus-5", params):
            raise AssertionError("A5 threshold failure was not recognized")
        write_json(
            directory / "boundary-ledger.json",
            {"boundaries": [{"position_index": position, "records_invalid": False, "peak_effective_context": 100000 if position == 5 else 1000} for position in range(1, 9)]},
        )
        if crossed_first_late_threshold(directory, "claude-opus-5", params):
            raise AssertionError("A5 accepted a threshold at the deciding late position")
    print("SELF_TEST_OK: sweep shape, complete pin inventory, terminal monotonicity, status-schema/command refusal, persisted abort derivation, serial A5 gate, one-time A5 state, attestation tamper, A5 prior-boundary pass/fail")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", type=int)
    parser.add_argument("--lanes", type=int, default=3)
    parser.add_argument("--out", type=pathlib.Path)
    parser.add_argument("--run-id")
    parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE)
    parser.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS)
    parser.add_argument("--window-attestation", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test()
        except (AssertionError, OSError, LaunchViolation, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.sweep is None or args.out is None or args.run_id is None or args.window_attestation is None:
        parser.error("--sweep, --out, --run-id, and --window-attestation are required unless --self-test is used")
    try:
        return run(args)
    except LaunchViolation as exc:
        print(f"FAIL launch-0110: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
