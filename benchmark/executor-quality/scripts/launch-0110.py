#!/usr/bin/env python3
"""Stageable iter-0110 launcher with outcome-blind block replacement."""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import datetime
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import threading

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_SCHEDULE = REPO / "docs/specs/iter0110/schedule.json"
DEFAULT_PARAMS = REPO / "docs/specs/iter0110/registered-params.json"
DRIVER = HERE / "sh-driver-0110.py"
COLLECTOR = HERE / "boundary-ledger-0110.py"
MANIFEST_NAME = "launch-manifest-0110.json"
PIN_FILE = REPO / "docs/specs/iter0110/scripts.sha256"
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
ENGINES = (*MATRIX_ENGINES, "claude-sonnet-5")
APPARATUS_SCRIPTS = ("sh-driver-0110.py", "boundary-ledger-0110.py", "smoke-gate-0110.py", "derive-schedule-0110.py", "g0-power-0110.py", "score-0110.py", "launch-0110.py")
REQUIRED_PIN_TARGETS = frozenset([f"benchmark/executor-quality/scripts/{name}" for name in APPARATUS_SCRIPTS] + ["docs/specs/iter0110/schedule.json", "docs/specs/iter0110/registered-params.json", "benchmark/executor-quality/tasks-0110-smoke/smoke-1 (whole tree)", "benchmark/executor-quality/tasks-0110-smoke/smoke-2 (whole tree)"])
STATUS_FIELDS = frozenset(("engine", "replicate_id", "session_label", "driver_command", "collector_command", "driver_exit", "driver_stdout_sha256", "driver_stderr_sha256", "status", "collector_exit", "collector_stdout_sha256", "collector_stderr_sha256", "infra_affected", "a5_clean", "first_late_threshold_crossed", "rows_sha256", "boundary_ledger_sha256", "artifact_dir"))
ATTEMPT_FIELDS = frozenset(("attempt_id", "replacement_of", "transport_state", "unrun_suffix", "sessions"))
FRESH_API_WINDOW_FIELDS = ("source", "observed_at", "resets_at", "value", "attested_by")
FRESH_API_WINDOW_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "attempt_ids"))


class LaunchViolation(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: pathlib.Path) -> object:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"cannot-read-json:{path}:{exc}") from exc


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def load_inputs(schedule_path: pathlib.Path, params_path: pathlib.Path) -> tuple[dict[str, object], dict[str, object]]:
    schedule, params = read_json(schedule_path), read_json(params_path)
    if not isinstance(schedule, dict) or schedule.get("schema") != "iter0110-session-horizon-schedule-v1":
        raise LaunchViolation("schedule-schema-mismatch")
    if not isinstance(params, dict) or params.get("schema") != "iter0110-registered-params-v1":
        raise LaunchViolation("params-schema-mismatch")
    if schedule.get("k") != 8 or params.get("k") != 8 or schedule.get("engines") != list(ENGINES) or params.get("matrix_engines") != list(MATRIX_ENGINES):
        raise LaunchViolation("registered-input-mismatch")
    sessions, registered = schedule.get("sessions"), params.get("schedule")
    if not isinstance(sessions, list) or not isinstance(registered, dict) or len(sessions) != registered.get("sessions"):
        raise LaunchViolation("registered-session-count-mismatch")
    if any(not isinstance(s, dict) or not isinstance(s.get("tasks"), list) or len(s["tasks"]) != 8 for s in sessions):
        raise LaunchViolation("schedule-session-shape-invalid")
    amendment = params.get("amendment6")
    if not isinstance(amendment, dict) or type(amendment.get("cap_replacement_blocks_per_root")) is not int or amendment["cap_replacement_blocks_per_root"] < 0:
        raise LaunchViolation("amendment6-replacement-cap-invalid")
    if type(amendment.get("fresh_window_max_age_minutes")) is not int or amendment["fresh_window_max_age_minutes"] < 0:
        raise LaunchViolation("amendment6-fresh-window-age-invalid")
    if amendment.get("fresh_api_window_fields") != list(FRESH_API_WINDOW_FIELDS):
        raise LaunchViolation("amendment6-fresh-window-schema-invalid")
    return schedule, params


def whole_tree_sha256(root: pathlib.Path) -> str:
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: os.fsencode(f"./{path.relative_to(root)}"))
    return hashlib.sha256(b"".join(f"{sha256(path)}  ./{path.relative_to(root)}\n".encode() for path in files)).hexdigest()


def script_digests() -> dict[str, str]:
    return {name: sha256(HERE / name) for name in APPARATUS_SCRIPTS}


def verify_script_inventory(pin_file: pathlib.Path = PIN_FILE) -> str:
    try:
        lines = pin_file.read_text().splitlines()
    except OSError as exc:
        raise LaunchViolation(f"script-pin-unreadable:{exc}") from exc
    entries: list[tuple[str, str]] = []
    for number, line in enumerate(lines, 1):
        if not line or line.startswith("#"):
            continue
        digest, separator, target = line.partition("  ")
        if not separator or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest) or not target or any(t == target for _d, t in entries):
            raise LaunchViolation(f"script-pin-malformed:{number}")
        entries.append((digest, target))
    targets = {target for _digest, target in entries}
    unknown, missing = sorted(targets - REQUIRED_PIN_TARGETS), sorted(REQUIRED_PIN_TARGETS - targets)
    if unknown:
        raise LaunchViolation(f"script-pin-unknown-target:{unknown[0]}")
    if missing:
        raise LaunchViolation(f"script-pin-required-target-missing:{missing[0]}")
    for expected, target in entries:
        try:
            actual = whole_tree_sha256(REPO / target[:-13]) if target.endswith(" (whole tree)") else sha256(REPO / target)
        except OSError as exc:
            raise LaunchViolation(f"script-pin-target-unreadable:{target}") from exc
        if actual != expected:
            raise LaunchViolation(f"script-pin-mismatch:{target}")
    return sha256(pin_file)


def load_window_attestation(path: pathlib.Path, params: dict[str, object]) -> tuple[bytes, dict[str, object]]:
    try:
        raw, attestation = path.read_bytes(), json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"window-attestation-unreadable:{exc}") from exc
    denominators = params.get("effective_context", {}).get("context_window_denominator_tokens") if isinstance(params.get("effective_context"), dict) else None
    if not isinstance(attestation, dict) or not isinstance(denominators, dict):
        raise LaunchViolation("window-attestation-invalid")
    if set(attestation) != {"attested_by", "source", *ENGINES}:
        raise LaunchViolation("window-attestation-schema-mismatch")
    if any(type(attestation.get(engine)) is not int or attestation[engine] != denominators.get(engine) for engine in ENGINES):
        raise LaunchViolation("window-attestation-denominator-mismatch")
    if any(not isinstance(attestation.get(name), str) or not attestation[name] for name in ("attested_by", "source")):
        raise LaunchViolation("window-attestation-author-invalid")
    return raw, attestation


def parse_iso8601(value: str, field: str) -> datetime.datetime:
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LaunchViolation(f"replacement-fresh-api-window-{field}-invalid") from exc
    if parsed.tzinfo is None:
        raise LaunchViolation(f"replacement-fresh-api-window-{field}-invalid")
    return parsed.astimezone(datetime.timezone.utc)


def load_fresh_api_window(path: pathlib.Path, params: dict[str, object]) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
        evidence = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"replacement-fresh-api-window-unreadable:{exc}") from exc
    if not isinstance(evidence, dict) or set(evidence) != set(FRESH_API_WINDOW_FIELDS):
        raise LaunchViolation("replacement-fresh-api-window-schema-invalid")
    if evidence.get("source") not in {"usage", "429-reset"} or any(not isinstance(evidence.get(field), str) or not evidence[field] for field in FRESH_API_WINDOW_FIELDS if field != "source"):
        raise LaunchViolation("replacement-fresh-api-window-invalid")
    observed_at = parse_iso8601(evidence["observed_at"], "observed_at")
    resets_at = parse_iso8601(evidence["resets_at"], "resets_at")
    now = datetime.datetime.now(datetime.timezone.utc)
    if now < resets_at:
        raise LaunchViolation("replacement-fresh-api-window-not-reset")
    age = now - max(observed_at, resets_at)
    limit = datetime.timedelta(minutes=params["amendment6"]["fresh_window_max_age_minutes"])
    if age > limit:
        raise LaunchViolation("replacement-fresh-api-window-stale")
    return raw, hashlib.sha256(raw).hexdigest()


def session_key(session: dict[str, object]) -> str:
    return str(session["session_label"])


def attempt_root(out: pathlib.Path, attempt_id: str) -> pathlib.Path:
    return out / "attempts" / attempt_id


def session_directory(root: pathlib.Path, session: dict[str, object]) -> pathlib.Path:
    return root / f"{session['engine']}.{session['session_label']}.r{session['replicate_index']}"


def command_for(session: dict[str, object], root: pathlib.Path, run_id: str) -> list[str]:
    return [sys.executable, str(DRIVER), "--engine", str(session["engine"]), "--session-label", session_key(session), "--tasks", ",".join(str(item["task_id"]) for item in session["tasks"]), "--replicate", str(session["replicate_index"]), "--out", str(root), "--run-id", run_id]


def collector_command_for(directory: pathlib.Path) -> list[str]:
    return [sys.executable, str(COLLECTOR), "--session-dir", str(directory)]


def parse_session_dir(stdout: bytes, expected: pathlib.Path) -> None:
    for line in reversed(stdout.decode(errors="replace").splitlines()):
        try:
            result = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict) and result.get("session_dir") == str(expected):
            return
    raise LaunchViolation("driver-session-dir-missing")


def rows(directory: pathlib.Path) -> list[dict[str, object]]:
    try:
        result = [json.loads(line) for line in (directory / "rows.jsonl").read_text().splitlines()]
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"session-rows-unreadable:{directory}") from exc
    if not all(isinstance(row, dict) for row in result):
        raise LaunchViolation(f"session-rows-invalid:{directory}")
    return result


def a5_fields(directory: pathlib.Path, engine: str, params: dict[str, object]) -> tuple[bool, bool]:
    try:
        session_rows = rows(directory)
        ledger = read_json(directory / "boundary-ledger.json")
    except LaunchViolation:
        return False, False
    indexed = {row.get("position_index"): row for row in session_rows}
    if set(indexed) != set(range(1, 9)) or any(row.get("infra_invalid") or row.get("catastrophic") or row.get("custody_ok") is not True or row.get("custody_broken") is not False for row in indexed.values()):
        return False, False
    boundaries = {item.get("position_index"): item for item in ledger.get("boundaries", []) if isinstance(item, dict)} if isinstance(ledger, dict) else {}
    effective = params.get("effective_context")
    if not isinstance(effective, dict) or not isinstance(effective.get("context_window_denominator_tokens"), dict):
        return False, False
    required = max(int(effective["absolute_threshold_tokens"]), float(effective["context_window_fraction_threshold"]) * int(effective["context_window_denominator_tokens"][engine]))
    crossed = any(item.get("records_invalid") is False and type(item.get("peak_effective_context")) is int and item["peak_effective_context"] >= required for position, item in boundaries.items() if type(position) is int and position < 5)
    return True, crossed


def block_sessions(schedule: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    result: dict[str, list[dict[str, object]]] = {}
    for session in schedule["sessions"]:
        result.setdefault(str(session["replicate_id"]), []).append(session)
    return result


def base_manifest(schedule_path: pathlib.Path, params_path: pathlib.Path, run_id: str, pin_sha: str, attestation: bytes) -> dict[str, object]:
    schedule, _params = load_inputs(schedule_path, params_path)
    return {"schema": "iter0110-launch-manifest-v2", "run_id": run_id, "schedule_sha256": sha256(schedule_path), "params_sha256": sha256(params_path), "script_sha256": script_digests(), "scripts_sha256_pin_file": pin_sha, "window_attestation_sha256": hashlib.sha256(attestation).hexdigest(), "window_attestation_bytes_base64": base64.b64encode(attestation).decode(), "fresh_api_windows": [], "blocks": {str(block["replicate_id"]): {"replicate_id": str(block["replicate_id"]), "attempts": [], "designated_attempt": None} for block in schedule["blocks"]}, "a5": {engine: {"a5_evaluated_attempt": None, "a5_evaluated_session": None, "a5_crossed": None} for engine in MATRIX_ENGINES}, "terminal": "RUNNING"}


def is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_status(session: dict[str, object], status: object, out: pathlib.Path, attempt_id: str, run_id: str) -> None:
    label = session_key(session)
    if not isinstance(status, dict) or set(status) != STATUS_FIELDS:
        raise LaunchViolation(f"launch-manifest-status-invalid:{label}:fields")
    root, directory = attempt_root(out, attempt_id), session_directory(attempt_root(out, attempt_id), session)
    if status.get("engine") != session["engine"] or status.get("replicate_id") != session["replicate_id"] or status.get("session_label") != label or status.get("artifact_dir") != str(directory.relative_to(out)):
        raise LaunchViolation(f"launch-manifest-status-invalid:{label}:identity")
    if status.get("driver_command") != command_for(session, root, run_id) or status.get("collector_command") != collector_command_for(directory):
        raise LaunchViolation(f"launch-manifest-status-invalid:{label}:command")
    if status.get("status") not in {"driver_failed", "driver_receipt_invalid", "collector_failed", "collector_receipt_invalid", "completed"} or type(status.get("driver_exit")) is not int or not is_digest(status.get("driver_stdout_sha256")) or not is_digest(status.get("driver_stderr_sha256")) or type(status.get("infra_affected")) is not bool or type(status.get("a5_clean")) is not bool:
        raise LaunchViolation(f"launch-manifest-status-invalid:{label}:receipt")
    if status["status"] == "completed":
        if status.get("collector_exit") != 0 or not all(is_digest(status.get(field)) for field in ("collector_stdout_sha256", "collector_stderr_sha256", "rows_sha256", "boundary_ledger_sha256")):
            raise LaunchViolation(f"launch-manifest-status-invalid:{label}:completed")
        expected = session["engine"] in MATRIX_ENGINES
        if (expected and type(status.get("first_late_threshold_crossed")) is not bool) or (not expected and status.get("first_late_threshold_crossed") is not None):
            raise LaunchViolation(f"launch-manifest-status-invalid:{label}:a5")


def clean_attempt(attempt: dict[str, object], sessions: list[dict[str, object]]) -> bool:
    return attempt["transport_state"] == "CLEAN" and set(attempt["sessions"]) == {session_key(session) for session in sessions} and all(attempt["sessions"][session_key(session)].get("status") == "completed" and attempt["sessions"][session_key(session)].get("infra_affected") is False for session in sessions)


def normalize(attempt: dict[str, object], sessions: list[dict[str, object]]) -> None:
    statuses = attempt["sessions"]
    infra = next((index for index, session in enumerate(sessions) if statuses.get(session_key(session), {}).get("infra_affected") is True), None)
    if infra is not None:
        attempt["transport_state"] = "VOID"
        attempt["unrun_suffix"] = [session_key(session) for session in sessions[infra + 1:]]
    elif any(statuses.get(session_key(session), {}).get("status") != "completed" for session in sessions if session_key(session) in statuses):
        attempt["transport_state"] = "STRUCTURAL_FAILURE"
    elif set(statuses) == {session_key(session) for session in sessions}:
        attempt["transport_state"] = "CLEAN"


def validate_manifest(manifest: dict[str, object], schedule: dict[str, object], out: pathlib.Path, run_id: str) -> None:
    windows = manifest.get("fresh_api_windows")
    if not isinstance(windows, list):
        raise LaunchViolation("launch-manifest-fresh-api-windows-invalid")
    consumed: set[str] = set()
    for entry in windows:
        if not isinstance(entry, dict) or set(entry) != FRESH_API_WINDOW_ENTRY_FIELDS or not is_digest(entry.get("sha256")) or not isinstance(entry.get("bytes_base64"), str) or not isinstance(entry.get("attempt_ids"), list) or not entry["attempt_ids"] or not all(isinstance(attempt_id, str) and attempt_id for attempt_id in entry["attempt_ids"]):
            raise LaunchViolation("launch-manifest-fresh-api-window-invalid")
        try:
            evidence = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise LaunchViolation("launch-manifest-fresh-api-window-invalid") from exc
        if hashlib.sha256(evidence).hexdigest() != entry["sha256"] or entry["sha256"] in consumed:
            raise LaunchViolation("launch-manifest-fresh-api-window-invalid")
        consumed.add(entry["sha256"])
    by_block = block_sessions(schedule)
    if not isinstance(manifest.get("blocks"), dict) or set(manifest["blocks"]) != set(by_block):
        raise LaunchViolation("launch-manifest-blocks-invalid")
    for replicate_id, sessions in by_block.items():
        block = manifest["blocks"][replicate_id]
        if not isinstance(block, dict) or set(block) != {"replicate_id", "attempts", "designated_attempt"} or block.get("replicate_id") != replicate_id or not isinstance(block.get("attempts"), list):
            raise LaunchViolation(f"launch-manifest-block-invalid:{replicate_id}")
        clean: list[str] = []
        for index, attempt in enumerate(block["attempts"], 1):
            aid, prior = f"{replicate_id}.a{index}", None if index == 1 else f"{replicate_id}.a{index - 1}"
            if not isinstance(attempt, dict) or set(attempt) != ATTEMPT_FIELDS or attempt.get("attempt_id") != aid or attempt.get("replacement_of") != prior or attempt.get("transport_state") not in {"RUNNING", "VOID", "CLEAN", "STRUCTURAL_FAILURE"} or not isinstance(attempt.get("sessions"), dict) or not isinstance(attempt.get("unrun_suffix"), list):
                raise LaunchViolation(f"launch-manifest-attempt-invalid:{aid}")
            if not set(attempt["sessions"]) <= {session_key(session) for session in sessions}:
                raise LaunchViolation(f"launch-manifest-attempt-session-invalid:{aid}")
            for session in sessions:
                if session_key(session) in attempt["sessions"]:
                    validate_status(session, attempt["sessions"][session_key(session)], out, aid, run_id)
            normalize(attempt, sessions)
            if index > 1 and block["attempts"][index - 2]["transport_state"] != "VOID":
                raise LaunchViolation(f"launch-manifest-replacement-without-void:{aid}")
            if attempt["transport_state"] == "CLEAN" and index != len(block["attempts"]):
                raise LaunchViolation(f"launch-manifest-clean-attempt-followed:{aid}")
            if attempt["transport_state"] == "VOID":
                first = next(i for i, session in enumerate(sessions) if attempt["sessions"].get(session_key(session), {}).get("infra_affected") is True)
                if attempt["unrun_suffix"] != [session_key(session) for session in sessions[first + 1:]] or any(label in attempt["sessions"] for label in attempt["unrun_suffix"]):
                    raise LaunchViolation(f"launch-manifest-void-suffix-invalid:{aid}")
            if clean_attempt(attempt, sessions):
                clean.append(aid)
        if block["designated_attempt"] != (clean[0] if clean else None):
            raise LaunchViolation(f"launch-manifest-designation-invalid:{replicate_id}")
    if not isinstance(manifest.get("a5"), dict) or set(manifest["a5"]) != set(MATRIX_ENGINES):
        raise LaunchViolation("launch-manifest-a5-invalid")


def verify_recorded_attempt_artifacts(manifest: dict[str, object], schedule: dict[str, object], out: pathlib.Path) -> None:
    for replicate_id, sessions in block_sessions(schedule).items():
        block = manifest["blocks"][replicate_id]
        for attempt in block["attempts"]:
            for session in sessions:
                label = session_key(session)
                status = attempt["sessions"].get(label)
                if not isinstance(status, dict) or status.get("status") != "completed":
                    continue
                directory = out / status["artifact_dir"]
                for filename, field in (("rows.jsonl", "rows_sha256"), ("boundary-ledger.json", "boundary_ledger_sha256")):
                    try:
                        actual = sha256(directory / filename)
                    except OSError as exc:
                        raise LaunchViolation(f"launch-artifact-unreadable:{attempt['attempt_id']}:{label}:{filename}") from exc
                    if actual != status[field]:
                        raise LaunchViolation(f"launch-artifact-digest-mismatch:{attempt['attempt_id']}:{label}:{filename}")


def load_manifest(out: pathlib.Path, schedule_path: pathlib.Path, params_path: pathlib.Path, run_id: str, pin_sha: str, attestation: bytes) -> dict[str, object]:
    if not (out / MANIFEST_NAME).exists():
        return base_manifest(schedule_path, params_path, run_id, pin_sha, attestation)
    manifest = read_json(out / MANIFEST_NAME)
    if not isinstance(manifest, dict) or manifest.get("schema") != "iter0110-launch-manifest-v2":
        raise LaunchViolation("launch-manifest-schema-mismatch")
    expected = base_manifest(schedule_path, params_path, run_id, pin_sha, attestation)
    for field in ("run_id", "schedule_sha256", "params_sha256", "script_sha256", "scripts_sha256_pin_file", "window_attestation_sha256", "window_attestation_bytes_base64"):
        if manifest.get(field) != expected[field]:
            raise LaunchViolation(f"launch-manifest-{field}-mismatch")
    schedule, _params = load_inputs(schedule_path, params_path)
    refresh_designations(manifest, schedule)
    validate_manifest(manifest, schedule, out, run_id)
    verify_recorded_attempt_artifacts(manifest, schedule, out)
    return manifest


def new_attempt(block: dict[str, object]) -> dict[str, object]:
    number = len(block["attempts"]) + 1
    attempt = {"attempt_id": f"{block['replicate_id']}.a{number}", "replacement_of": None if number == 1 else block["attempts"][-1]["attempt_id"], "transport_state": "RUNNING", "unrun_suffix": [], "sessions": {}}
    block["attempts"].append(attempt)
    return attempt


def run_session(session: dict[str, object], out: pathlib.Path, attempt_id: str, run_id: str, params: dict[str, object]) -> dict[str, object]:
    root, directory = attempt_root(out, attempt_id), session_directory(attempt_root(out, attempt_id), session)
    command, collector_command = command_for(session, root, run_id), collector_command_for(directory)
    driver = subprocess.run(command, cwd=REPO, capture_output=True)
    status: dict[str, object] = {"engine": session["engine"], "replicate_id": session["replicate_id"], "session_label": session_key(session), "driver_command": command, "collector_command": collector_command, "driver_exit": driver.returncode, "driver_stdout_sha256": hashlib.sha256(driver.stdout).hexdigest(), "driver_stderr_sha256": hashlib.sha256(driver.stderr).hexdigest(), "status": "driver_failed", "collector_exit": None, "collector_stdout_sha256": None, "collector_stderr_sha256": None, "infra_affected": False, "a5_clean": False, "first_late_threshold_crossed": None, "rows_sha256": None, "boundary_ledger_sha256": None, "artifact_dir": str(directory.relative_to(out))}
    if driver.returncode:
        return status
    try:
        parse_session_dir(driver.stdout, directory)
    except LaunchViolation:
        status["status"] = "driver_receipt_invalid"
        return status
    collector = subprocess.run(collector_command, cwd=REPO, capture_output=True)
    status.update({"collector_exit": collector.returncode, "collector_stdout_sha256": hashlib.sha256(collector.stdout).hexdigest(), "collector_stderr_sha256": hashlib.sha256(collector.stderr).hexdigest()})
    if collector.returncode:
        status["status"] = "collector_failed"
        return status
    try:
        status["rows_sha256"], status["boundary_ledger_sha256"] = sha256(directory / "rows.jsonl"), sha256(directory / "boundary-ledger.json")
        session_rows = rows(directory)
    except LaunchViolation:
        status["status"] = "collector_receipt_invalid"
        return status
    status["infra_affected"] = any(row.get("infra_invalid") is True for row in session_rows)
    if session["engine"] in MATRIX_ENGINES:
        status["a5_clean"], status["first_late_threshold_crossed"] = a5_fields(directory, str(session["engine"]), params)
    status["status"] = "completed"
    return status


def refresh_designations(manifest: dict[str, object], schedule: dict[str, object]) -> None:
    for rid, sessions in block_sessions(schedule).items():
        block = manifest["blocks"][rid]
        for attempt in block["attempts"]:
            normalize(attempt, sessions)
        clean = [attempt["attempt_id"] for attempt in block["attempts"] if clean_attempt(attempt, sessions)]
        block["designated_attempt"] = clean[0] if clean else None


def designated(manifest: dict[str, object], rid: str) -> dict[str, object] | None:
    block, identity = manifest["blocks"][rid], manifest["blocks"][rid]["designated_attempt"]
    return next((attempt for attempt in block["attempts"] if attempt["attempt_id"] == identity), None)


def derive_a5(manifest: dict[str, object], schedule: dict[str, object]) -> None:
    gate_id = str(schedule["blocks"][0]["replicate_id"])
    attempt = designated(manifest, gate_id)
    sessions = block_sessions(schedule)[gate_id]
    for engine in MATRIX_ENGINES:
        record = manifest["a5"][engine]
        record.update({"a5_evaluated_attempt": None, "a5_evaluated_session": None, "a5_crossed": None})
        session = next((item for item in sessions if item["engine"] == engine), None)
        status = attempt["sessions"].get(session_key(session)) if attempt is not None and session is not None else None
        if isinstance(status, dict) and status.get("status") == "completed" and status.get("infra_affected") is False and status.get("a5_clean") is True:
            record.update({"a5_evaluated_attempt": attempt["attempt_id"], "a5_evaluated_session": session_key(session), "a5_crossed": status["first_late_threshold_crossed"]})


def replacement_count(manifest: dict[str, object]) -> int:
    return sum(attempt["transport_state"] == "VOID" for block in manifest["blocks"].values() for attempt in block["attempts"])


def replacement_cap(params: dict[str, object]) -> int:
    return params["amendment6"]["cap_replacement_blocks_per_root"]


def derive_terminal(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> tuple[str, dict[str, object]]:
    refresh_designations(manifest, schedule)
    derive_a5(manifest, schedule)
    count = replacement_count(manifest)
    cap = replacement_cap(params)
    if count > cap:
        return "REPLACEMENT_CAP_EXCEEDED", {"replacement_attempts": count, "cap": cap}
    if any(attempt["transport_state"] == "STRUCTURAL_FAILURE" for block in manifest["blocks"].values() for attempt in block["attempts"]):
        return "UNREGISTERED_STRUCTURAL_FAILURE", {}
    gate_id = str(schedule["blocks"][0]["replicate_id"])
    if manifest["blocks"][gate_id]["designated_attempt"] is not None:
        missing = next((engine for engine in MATRIX_ENGINES if manifest["a5"][engine]["a5_evaluated_session"] is None), None)
        failed = next((engine for engine in MATRIX_ENGINES if manifest["a5"][engine]["a5_crossed"] is False), None)
        if missing is not None:
            return "A5_SUBJECT_UNAVAILABLE", {"engine": missing}
        if failed is not None:
            return "FAIL_FAST_THRESHOLD_UNREACHED", {"engine": failed}
    if any(attempt["transport_state"] == "VOID" and block["designated_attempt"] is None for block in manifest["blocks"].values() for attempt in block["attempts"]):
        return "REPLACEMENT_PENDING", {"replacement_attempts": count, "cap": cap}
    if all(block["designated_attempt"] is not None for block in manifest["blocks"].values()):
        return "LAUNCH_COMPLETE", {}
    return "LAUNCH_PARTIAL", {}


def refresh_ledger(out: pathlib.Path, manifest: dict[str, object], schedule: dict[str, object]) -> None:
    payload = b""
    for rid, sessions in sorted(block_sessions(schedule).items()):
        attempt = designated(manifest, rid)
        if attempt is None:
            continue
        for session in sessions:
            try:
                payload += (out / attempt["sessions"][session_key(session)]["artifact_dir"] / "rows.jsonl").read_bytes()
            except OSError as exc:
                raise LaunchViolation(f"designated-ledger-unreadable:{rid}:{session_key(session)}") from exc
    (out / "ledger.jsonl").write_bytes(payload)


def persist(out: pathlib.Path, manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> str:
    terminal, details = derive_terminal(manifest, schedule, params)
    manifest["terminal"], manifest["replacement_attempts"] = terminal, replacement_count(manifest)
    write_json(out / MANIFEST_NAME, manifest)
    if terminal in {"REPLACEMENT_PENDING", "REPLACEMENT_CAP_EXCEEDED", "A5_SUBJECT_UNAVAILABLE", "FAIL_FAST_THRESHOLD_UNREACHED", "UNREGISTERED_STRUCTURAL_FAILURE"}:
        write_json(out / "launch-abort-0110.json", {"terminal": terminal, "details": details, "blocks": manifest["blocks"]})
    if any(block["designated_attempt"] is not None for block in manifest["blocks"].values()):
        refresh_ledger(out, manifest, schedule)
    return terminal


def execute_attempt(out: pathlib.Path, manifest: dict[str, object], attempt: dict[str, object], sessions: list[dict[str, object]], run_id: str, params: dict[str, object], write_lock: threading.Lock | None = None) -> str:
    for session in sessions:
        if session_key(session) in attempt["sessions"]:
            continue
        status = run_session(session, out, str(attempt["attempt_id"]), run_id, params)
        if write_lock is None:
            attempt["sessions"][session_key(session)] = status
            normalize(attempt, sessions)
            write_json(out / MANIFEST_NAME, manifest)
        else:
            with write_lock:
                attempt["sessions"][session_key(session)] = status
                normalize(attempt, sessions)
                write_json(out / MANIFEST_NAME, manifest)
        if attempt["transport_state"] in {"VOID", "STRUCTURAL_FAILURE"}:
            return str(attempt["transport_state"])
    if write_lock is None:
        normalize(attempt, sessions)
    else:
        with write_lock:
            normalize(attempt, sessions)
    return str(attempt["transport_state"])


def run(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    if args.sweep < 1 or args.sweep > schedule["sweeps"] or args.lanes < 1:
        raise LaunchViolation("launch-arguments-invalid")
    selected = [s for s in schedule["sessions"] if s["sweep_id"] == args.sweep]
    pin, (raw, attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    if args.dry_run:
        print(f"DRY_RUN: sweep={args.sweep} sessions={len(selected)} attempts={len(selected) * 8} lanes={args.lanes}")
        for session in selected:
            print(shlex.join(command_for(session, args.out, args.run_id)))
        return 0
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, raw)
    sticky = {"REPLACEMENT_CAP_EXCEEDED", "A5_SUBJECT_UNAVAILABLE", "FAIL_FAST_THRESHOLD_UNREACHED", "UNREGISTERED_STRUCTURAL_FAILURE", "LAUNCH_COMPLETE"}
    by_block = block_sessions(schedule)
    terminal, _details = derive_terminal(manifest, schedule, params)
    pending = terminal == "REPLACEMENT_PENDING"
    if args.fresh_api_window is not None and not pending:
        raise LaunchViolation("replacement-fresh-api-window-unexpected")
    fresh_api_window: tuple[bytes, str] | None = None
    if pending:
        if args.fresh_api_window is None:
            raise LaunchViolation("replacement-fresh-api-window-missing")
        fresh_api_window = load_fresh_api_window(args.fresh_api_window, params)
        if any(entry["sha256"] == fresh_api_window[1] for entry in manifest["fresh_api_windows"]):
            raise LaunchViolation("replacement-fresh-api-window-reused")
    terminal = persist(args.out, manifest, schedule, params)
    if terminal in sticky:
        print(f"TERMINAL: {terminal}")
        return 0 if terminal == "LAUNCH_COMPLETE" else 2
    gate_id = str(schedule["blocks"][0]["replicate_id"])
    if not manifest["blocks"][gate_id]["attempts"] and args.sweep != 1:
        raise LaunchViolation("a5-gate-requires-sweep-one")
    running = [(rid, sessions) for rid, sessions in by_block.items() if manifest["blocks"][rid]["designated_attempt"] is None and manifest["blocks"][rid]["attempts"] and manifest["blocks"][rid]["attempts"][-1]["transport_state"] == "RUNNING"]
    pending = [(rid, sessions) for rid, sessions in by_block.items() if manifest["blocks"][rid]["designated_attempt"] is None and manifest["blocks"][rid]["attempts"] and manifest["blocks"][rid]["attempts"][-1]["transport_state"] == "VOID"]
    if running:
        candidates, reuse_running = running, True
    elif pending:
        candidates, reuse_running = pending, False
    else:
        ids = tuple(dict.fromkeys(str(session["replicate_id"]) for session in selected))
        candidates, reuse_running = [(rid, by_block[rid]) for rid in ids if not manifest["blocks"][rid]["attempts"]], False
    while candidates:
        gate_pending = manifest["blocks"][gate_id]["designated_attempt"] is None and candidates[0][0] == gate_id
        batch_size = 1 if pending or gate_pending else args.lanes
        batch, candidates = candidates[:batch_size], candidates[batch_size:]
        attempts = [(rid, sessions, manifest["blocks"][rid]["attempts"][-1] if reuse_running else new_attempt(manifest["blocks"][rid])) for rid, sessions in batch]
        if fresh_api_window is not None:
            evidence, digest = fresh_api_window
            manifest["fresh_api_windows"].append({"sha256": digest, "bytes_base64": base64.b64encode(evidence).decode(), "attempt_ids": [str(attempt["attempt_id"]) for _rid, _sessions, attempt in attempts]})
            fresh_api_window = None
        write_json(args.out / MANIFEST_NAME, manifest)
        lock = threading.Lock()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(attempts)) as executor:
            futures = [executor.submit(execute_attempt, args.out, manifest, attempt, sessions, args.run_id, params, lock) for _rid, sessions, attempt in attempts]
            states = [future.result() for future in futures]
        terminal = persist(args.out, manifest, schedule, params)
        if any(state in {"VOID", "STRUCTURAL_FAILURE"} for state in states) or terminal != "LAUNCH_PARTIAL":
            print(f"TERMINAL: {terminal}")
            return 0 if terminal == "LAUNCH_COMPLETE" else 2
    terminal = persist(args.out, manifest, schedule, params)
    print(f"TERMINAL: {terminal}")
    return 0 if terminal == "LAUNCH_COMPLETE" else 2


def self_test() -> None:
    schedule, params = load_inputs(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    by_block = block_sessions(schedule)
    gate = by_block[str(schedule["blocks"][0]["replicate_id"])]
    configured_rows: dict[tuple[str, str], dict[str, object]] = {}

    def fake_session(session: dict[str, object], out: pathlib.Path, attempt_id: str, run_id: str, _params: dict[str, object]) -> dict[str, object]:
        root = attempt_root(out, attempt_id)
        directory = session_directory(root, session)
        directory.mkdir(parents=True, exist_ok=False)
        requested = configured_rows.get((attempt_id, session_key(session)), {})
        infra_position = requested.get("infra_position")
        session_rows = [
            {
                "position_index": task["position_index"],
                "infra_invalid": task["position_index"] == infra_position,
                "catastrophic": requested.get("catastrophic", False),
                "custody_broken": requested.get("custody_broken", False),
                "manifestations_failed": requested.get("manifestations_failed", 0),
            }
            for task in session["tasks"]
        ]
        (directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in session_rows))
        (directory / "boundary-ledger.json").write_bytes(canonical_bytes({"boundaries": [{"position_index": position, "records_invalid": False, "peak_effective_context": 100000} for position in range(1, 9)]}))
        root_digest = "0" * 64
        infra = infra_position is not None
        adverse = requested.get("catastrophic", False) or requested.get("custody_broken", False)
        return {
            "engine": session["engine"], "replicate_id": session["replicate_id"], "session_label": session_key(session),
            "driver_command": command_for(session, root, run_id), "collector_command": collector_command_for(directory),
            "driver_exit": 0, "driver_stdout_sha256": root_digest, "driver_stderr_sha256": root_digest,
            "status": "completed", "collector_exit": 0, "collector_stdout_sha256": root_digest, "collector_stderr_sha256": root_digest,
            "infra_affected": infra, "a5_clean": not infra and not adverse,
            "first_late_threshold_crossed": True if session["engine"] in MATRIX_ENGINES else None,
            "rows_sha256": sha256(directory / "rows.jsonl"), "boundary_ledger_sha256": sha256(directory / "boundary-ledger.json"),
            "artifact_dir": str(directory.relative_to(out)),
        }

    def fingerprint(root: pathlib.Path) -> str:
        payload = b"".join(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file())
        return hashlib.sha256(payload).hexdigest()

    def fresh_window(path: pathlib.Path, seconds_ago: int, value: str) -> None:
        observed = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=seconds_ago)
        path.write_bytes(canonical_bytes({"source": "usage", "observed_at": observed.isoformat(), "resets_at": observed.isoformat(), "value": value, "attested_by": "self-test"}))

    with tempfile.TemporaryDirectory(prefix="iter0110-launch-") as temporary:
        out = pathlib.Path(temporary)
        attestation = out / "attestation.json"
        attestation.write_bytes(canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
        valid = out / "fresh-valid.json"
        stale = out / "fresh-stale.json"
        fresh_window(valid, 1, "usage t1")
        fresh_window(stale, params["amendment6"]["fresh_window_max_age_minutes"] * 60 + 1, "stale usage")
        original_run_session, original_verify_inventory = run_session, verify_script_inventory
        globals()["run_session"] = fake_session
        globals()["verify_script_inventory"] = lambda: sha256(PIN_FILE)
        try:
            def invocation(sweep: int, fresh: pathlib.Path | None = None) -> argparse.Namespace:
                return argparse.Namespace(sweep=sweep, lanes=3, out=out, run_id="t1", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, fresh_api_window=fresh, dry_run=False)

            gate_id = str(gate[0]["replicate_id"])
            configured_rows[(f"{gate_id}.a1", session_key(gate[1]))] = {"infra_position": 3}
            if run(invocation(1)) != 2:
                raise AssertionError("T1 void launch exit")
            manifest_path = out / MANIFEST_NAME
            manifest = read_json(manifest_path)
            if not isinstance(manifest, dict) or manifest.get("terminal") != "REPLACEMENT_PENDING" or manifest["blocks"][gate_id]["attempts"][0]["transport_state"] != "VOID":
                raise AssertionError("T1 pending")
            original_root = attempt_root(out, f"{gate_id}.a1")
            original_digest = fingerprint(original_root)
            if manifest["blocks"][gate_id]["attempts"][0]["unrun_suffix"] != [session_key(session) for session in gate[2:]] or any(session_directory(original_root, session).exists() for session in gate[2:]):
                raise AssertionError("T3 execute-attempt unrun suffix")
            tampered = session_directory(original_root, gate[0]) / "rows.jsonl"
            original_rows = tampered.read_bytes()
            manifest_before = manifest_path.read_bytes()
            tampered.write_bytes(original_rows + b" ")
            try:
                run(invocation(1, valid))
            except LaunchViolation as exc:
                if not str(exc).startswith("launch-artifact-digest-mismatch:"):
                    raise AssertionError("T1 integrity refusal reason") from exc
            else:
                raise AssertionError("T1 tampered prior artifact launched")
            if manifest_path.read_bytes() != manifest_before:
                raise AssertionError("T1 integrity refusal wrote manifest")
            tampered.write_bytes(original_rows)
            for evidence, expected in ((None, "replacement-fresh-api-window-missing"), (stale, "replacement-fresh-api-window-stale")):
                try:
                    run(invocation(1, evidence))
                except LaunchViolation as exc:
                    if str(exc) != expected:
                        raise AssertionError(f"T1 fresh-window refusal: {exc}") from exc
                else:
                    raise AssertionError(f"T1 accepted {expected}")
            if run(invocation(1, valid)) != 2:
                raise AssertionError("T1 replacement launch exit")
            manifest = read_json(manifest_path)
            if not isinstance(manifest, dict) or manifest["blocks"][gate_id]["designated_attempt"] != f"{gate_id}.a2" or fingerprint(original_root) != original_digest or manifest["fresh_api_windows"][-1]["attempt_ids"] != [f"{gate_id}.a2"]:
                raise AssertionError("T1 replacement provenance")
            if manifest["a5"]["claude-opus-5"]["a5_evaluated_attempt"] != f"{gate_id}.a2":
                raise AssertionError("T5 gate re-derivation")
            run(invocation(1))
            sweep_two_id = next(str(session["replicate_id"]) for session in schedule["sessions"] if session["sweep_id"] == 2)
            configured_rows[(f"{sweep_two_id}.a1", session_key(by_block[sweep_two_id][0]))] = {"infra_position": 2}
            if run(invocation(2)) != 2:
                raise AssertionError("T1 later void launch exit")
            try:
                run(invocation(2, valid))
            except LaunchViolation as exc:
                if str(exc) != "replacement-fresh-api-window-reused":
                    raise AssertionError("T1 reused evidence refusal") from exc
            else:
                raise AssertionError("T1 reused evidence accepted")
            replacement_window = out / "fresh-replacement.json"
            fresh_window(replacement_window, 1, "usage t2")
            if run(invocation(2, replacement_window)) != 2:
                raise AssertionError("T1 second replacement launch exit")
            for sweep in range(2, schedule["sweeps"] + 1):
                run(invocation(sweep))
            manifest = read_json(manifest_path)
            if not isinstance(manifest, dict) or manifest.get("terminal") != "LAUNCH_COMPLETE":
                raise AssertionError("T1 whole-root completion")
            try:
                run(invocation(schedule["sweeps"], replacement_window))
            except LaunchViolation as exc:
                if str(exc) != "replacement-fresh-api-window-unexpected":
                    raise AssertionError("T1 unexpected evidence refusal") from exc
            else:
                raise AssertionError("T1 accepted evidence without pending block")

            configured_rows.clear()
            outcome = out / "outcome-blind"
            raw, _attestation = load_window_attestation(attestation, params)
            clean_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "t4-clean", sha256(PIN_FILE), raw)
            clean_attempt = new_attempt(clean_manifest["blocks"][gate_id])
            configured_rows[(str(clean_attempt["attempt_id"]), session_key(gate[0]))] = {"catastrophic": True, "custody_broken": True, "manifestations_failed": 8}
            if execute_attempt(outcome, clean_manifest, clean_attempt, gate, "t4-clean", params) != "CLEAN":
                raise AssertionError("T4 adverse outcome became void")
            refresh_designations(clean_manifest, schedule)
            if clean_manifest["blocks"][gate_id]["designated_attempt"] != clean_attempt["attempt_id"]:
                raise AssertionError("T4 adverse outcome was not designated")
            void_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "t4-void", sha256(PIN_FILE), raw)
            void_attempt = new_attempt(void_manifest["blocks"][gate_id])
            configured_rows[(str(void_attempt["attempt_id"]), session_key(gate[0]))] = {"infra_position": 4}
            if execute_attempt(outcome / "infra", void_manifest, void_attempt, gate, "t4-void", params) != "VOID":
                raise AssertionError("T4 infra row did not void an otherwise perfect attempt")

            capped = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "t2", sha256(PIN_FILE), raw)
            capped_out = out / "capped"
            for _ in range(3):
                attempt = new_attempt(capped["blocks"][gate_id])
                configured_rows[(str(attempt["attempt_id"]), session_key(gate[0]))] = {"infra_position": 1}
                if execute_attempt(capped_out, capped, attempt, gate, "t2", params) != "VOID":
                    raise AssertionError("T2 fixture did not void")
            if derive_terminal(capped, schedule, params)[0] != "REPLACEMENT_CAP_EXCEEDED":
                raise AssertionError("T2 replacement cap")
        finally:
            globals()["run_session"] = original_run_session
            globals()["verify_script_inventory"] = original_verify_inventory
    print("SELF_TEST_OK: T1 run/resume/integrity/fresh-window/whole-root, T2 cap, T3 execute-attempt suffix, T4 outcome blindness, T5 gate re-derivation")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", type=int); parser.add_argument("--lanes", type=int, default=3); parser.add_argument("--out", type=pathlib.Path); parser.add_argument("--run-id"); parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE); parser.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS); parser.add_argument("--window-attestation", type=pathlib.Path); parser.add_argument("--fresh-api-window", type=pathlib.Path); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try: self_test()
        except (AssertionError, OSError, LaunchViolation, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr); return 1
        return 0
    if args.sweep is None or args.out is None or args.run_id is None or args.window_attestation is None:
        parser.error("--sweep, --out, --run-id, and --window-attestation are required unless --self-test is used")
    try: return run(args)
    except LaunchViolation as exc:
        print(f"FAIL launch-0110: {exc}", file=sys.stderr); return 3


if __name__ == "__main__":
    raise SystemExit(main())
