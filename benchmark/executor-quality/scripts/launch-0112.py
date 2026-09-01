#!/usr/bin/env python3
"""Stageable iter-0112 launcher with budget-gated, outcome-blind block replay."""
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
DEFAULT_SCHEDULE = REPO / "docs/specs/iter0112/schedule.json"
DEFAULT_PARAMS = REPO / "docs/specs/iter0112/registered-params.json"
DRIVER = HERE / "sh-driver-0112.py"
COLLECTOR = HERE / "boundary-ledger-0112.py"
MANIFEST_NAME = "launch-manifest-0112.json"
PIN_FILE = REPO / "docs/specs/iter0112/scripts.sha256"
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
ENGINES = (*MATRIX_ENGINES, "claude-sonnet-5")
APPARATUS_SCRIPTS = ("sh-driver-0112.py", "boundary-ledger-0112.py", "smoke-gate-0112.py", "derive-schedule-0112.py", "g0-power-0112.py", "score-0112.py", "launch-0112.py")
REQUIRED_PIN_TARGETS = frozenset([f"benchmark/executor-quality/scripts/{name}" for name in APPARATUS_SCRIPTS] + ["docs/specs/iter0112/schedule.json", "docs/specs/iter0112/registered-params.json"])
STATUS_FIELDS = frozenset(("engine", "replicate_id", "session_label", "driver_command", "collector_command", "driver_exit", "driver_stdout_sha256", "driver_stderr_sha256", "driver_evidence_sha256", "status", "collector_exit", "collector_stdout_sha256", "collector_stderr_sha256", "infra_affected", "a5_clean", "first_late_threshold_crossed", "rows_sha256", "boundary_ledger_sha256", "artifact_dir"))
ATTEMPT_FIELDS = frozenset(("attempt_id", "replacement_of", "transport_state", "unrun_suffix", "sessions", "charged_session_equivalents"))
USAGE_FIELDS = ("source", "observed_at", "value", "attested_by", "used_transport_tokens", "limit_transport_tokens", "reset_at")
USAGE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "role", "sweep_id", "consumed_at"))
RESUME_ORACLE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "attempt_ids", "consumed_at", "probe_calls"))


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
    if not isinstance(params, dict) or params.get("schema") != "iter0112-registered-params-v1":
        raise LaunchViolation("params-schema-mismatch")
    if schedule.get("k") != 8 or params.get("k") != 8 or schedule.get("engines") != list(ENGINES) or params.get("matrix_engines") != list(MATRIX_ENGINES):
        raise LaunchViolation("registered-input-mismatch")
    sessions, registered = schedule.get("sessions"), params.get("schedule")
    if not isinstance(sessions, list) or not isinstance(registered, dict) or len(sessions) != registered.get("sessions"):
        raise LaunchViolation("registered-session-count-mismatch")
    if registered.get("lanes") != 3:
        raise LaunchViolation("registered-lanes-invalid")
    if any(not isinstance(s, dict) or not isinstance(s.get("tasks"), list) or len(s["tasks"]) != 8 for s in sessions):
        raise LaunchViolation("schedule-session-shape-invalid")
    venue = params.get("venue_tolerance")
    if not isinstance(venue, dict) or not isinstance(venue.get("usage_evidence"), dict) or not isinstance(venue.get("budget_gate"), dict) or not isinstance(venue.get("calendar"), dict) or not isinstance(venue.get("charged_accounting"), dict) or not isinstance(venue.get("resume_oracle"), dict):
        raise LaunchViolation("venue-tolerance-schema-invalid")
    if venue["usage_evidence"].get("exact_fields") != list(USAGE_FIELDS) or type(venue["usage_evidence"].get("freshness_seconds")) is not int:
        raise LaunchViolation("usage-evidence-schema-invalid")
    if type(venue["charged_accounting"].get("maximum_block_attempts")) is not int or venue["charged_accounting"]["maximum_block_attempts"] < 20:
        raise LaunchViolation("charged-allowance-invalid")
    if type(venue["usage_evidence"].get("clock_skew_seconds")) is not int or venue["usage_evidence"]["clock_skew_seconds"] < 0:
        raise LaunchViolation("usage-evidence-clock-skew-invalid")
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
        raise LaunchViolation(f"timestamp-{field}-invalid") from exc
    if parsed.tzinfo is None:
        raise LaunchViolation(f"timestamp-{field}-invalid")
    return parsed.astimezone(datetime.timezone.utc)


def load_usage_evidence(path: pathlib.Path, params: dict[str, object]) -> tuple[bytes, dict[str, object], str]:
    try:
        raw = path.read_bytes()
        evidence = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"usage-evidence-unreadable:{exc}") from exc
    if not isinstance(evidence, dict) or set(evidence) != set(USAGE_FIELDS) or evidence.get("source") != "usage":
        raise LaunchViolation("usage-evidence-schema-invalid")
    if any(not isinstance(evidence.get(field), str) or not evidence[field] for field in ("observed_at", "value", "attested_by", "reset_at")):
        raise LaunchViolation("usage-evidence-text-invalid")
    if any(type(evidence.get(field)) is not int or evidence[field] < 0 for field in ("used_transport_tokens", "limit_transport_tokens")) or evidence["limit_transport_tokens"] <= 0 or evidence["used_transport_tokens"] > evidence["limit_transport_tokens"]:
        raise LaunchViolation("usage-evidence-numeric-invalid")
    observed = parse_iso8601(evidence["observed_at"], "observed_at")
    parse_iso8601(evidence["reset_at"], "reset_at")
    now = datetime.datetime.now(datetime.timezone.utc)
    skew = datetime.timedelta(seconds=params["venue_tolerance"]["usage_evidence"]["clock_skew_seconds"])
    if observed > now + skew:
        raise LaunchViolation("usage-evidence-future")
    if now - observed > datetime.timedelta(seconds=params["venue_tolerance"]["usage_evidence"]["freshness_seconds"]):
        raise LaunchViolation("usage-evidence-stale")
    return raw, evidence, hashlib.sha256(raw).hexdigest()


def usage_gate(evidence: dict[str, object], sweep: int, params: dict[str, object]) -> bool:
    budget = params["venue_tolerance"]["budget_gate"]
    burn = budget["first_sweep_burn_bound_transport_tokens"] if sweep == 1 else budget["subsequent_sweep_burn_bound_transport_tokens"]
    return evidence["used_transport_tokens"] + burn + budget["reserve_transport_tokens"] < evidence["limit_transport_tokens"]


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
    return {"schema": "iter0112-launch-manifest-v3", "run_id": run_id, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "schedule_sha256": sha256(schedule_path), "params_sha256": sha256(params_path), "script_sha256": script_digests(), "scripts_sha256_pin_file": pin_sha, "window_attestation_sha256": hashlib.sha256(attestation).hexdigest(), "window_attestation_bytes_base64": base64.b64encode(attestation).decode(), "usage_evidence": [], "resume_oracles": [], "blocks": {str(block["replicate_id"]): {"replicate_id": str(block["replicate_id"]), "attempts": [], "designated_attempt": None} for block in schedule["blocks"]}, "a5": {engine: {"a5_evaluated_attempt": None, "a5_evaluated_session": None, "a5_crossed": None} for engine in MATRIX_ENGINES}, "terminal": "RUNNING"}


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
        if status.get("collector_exit") != 0 or not all(is_digest(status.get(field)) for field in ("collector_stdout_sha256", "collector_stderr_sha256", "rows_sha256", "boundary_ledger_sha256", "driver_evidence_sha256")):
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
    evidence_entries = manifest.get("usage_evidence")
    if not isinstance(evidence_entries, list) or not isinstance(manifest.get("resume_oracles"), list):
        raise LaunchViolation("launch-manifest-evidence-invalid")
    consumed: set[str] = set()
    for entry in evidence_entries:
        if not isinstance(entry, dict) or set(entry) != USAGE_ENTRY_FIELDS or not is_digest(entry.get("sha256")) or not isinstance(entry.get("bytes_base64"), str) or entry.get("role") not in {"pre-sweep", "post-sweep", "resume"} or type(entry.get("sweep_id")) is not int:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid")
        parse_iso8601(str(entry.get("consumed_at")), "usage-consumed-at")
        try:
            evidence = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid") from exc
        if hashlib.sha256(evidence).hexdigest() != entry["sha256"] or entry["sha256"] in consumed:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid")
        consumed.add(entry["sha256"])
    oracle_seen: set[str] = set()
    for entry in manifest["resume_oracles"]:
        if not isinstance(entry, dict) or set(entry) != RESUME_ORACLE_ENTRY_FIELDS or not is_digest(entry.get("sha256")) or not isinstance(entry.get("bytes_base64"), str) or not isinstance(entry.get("attempt_ids"), list) or type(entry.get("probe_calls")) is not int or entry["probe_calls"] < 0:
            raise LaunchViolation("launch-manifest-resume-oracle-invalid")
        parse_iso8601(str(entry.get("consumed_at")), "resume-consumed-at")
        try:
            oracle_raw = base64.b64decode(entry["bytes_base64"], validate=True)
            oracle = json.loads(oracle_raw)
        except (ValueError, json.JSONDecodeError) as exc:
            raise LaunchViolation("launch-manifest-resume-oracle-invalid") from exc
        if hashlib.sha256(oracle_raw).hexdigest() != entry["sha256"] or entry["sha256"] in oracle_seen or not isinstance(oracle, dict) or not isinstance(oracle.get("probes"), list) or entry["probe_calls"] != len(oracle["probes"]):
            raise LaunchViolation("launch-manifest-resume-oracle-invalid")
        oracle_seen.add(entry["sha256"])
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
            if not isinstance(attempt, dict) or set(attempt) != ATTEMPT_FIELDS or attempt.get("attempt_id") != aid or attempt.get("replacement_of") != prior or attempt.get("transport_state") not in {"RUNNING", "VOID", "CLEAN", "STRUCTURAL_FAILURE"} or not isinstance(attempt.get("sessions"), dict) or not isinstance(attempt.get("unrun_suffix"), list) or attempt.get("charged_session_equivalents") != 6:
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
                for filename, field in (("rows.jsonl", "rows_sha256"), ("boundary-ledger.json", "boundary_ledger_sha256"), ("cli-attestation.json", "driver_evidence_sha256")):
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
    if not isinstance(manifest, dict) or manifest.get("schema") != "iter0112-launch-manifest-v3":
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
    attempt = {"attempt_id": f"{block['replicate_id']}.a{number}", "replacement_of": None if number == 1 else block["attempts"][-1]["attempt_id"], "transport_state": "RUNNING", "unrun_suffix": [], "sessions": {}, "charged_session_equivalents": 6}
    block["attempts"].append(attempt)
    return attempt


def run_session(session: dict[str, object], out: pathlib.Path, attempt_id: str, run_id: str, params: dict[str, object]) -> dict[str, object]:
    root, directory = attempt_root(out, attempt_id), session_directory(attempt_root(out, attempt_id), session)
    command, collector_command = command_for(session, root, run_id), collector_command_for(directory)
    driver = subprocess.run(command, cwd=REPO, capture_output=True)
    status: dict[str, object] = {"engine": session["engine"], "replicate_id": session["replicate_id"], "session_label": session_key(session), "driver_command": command, "collector_command": collector_command, "driver_exit": driver.returncode, "driver_stdout_sha256": hashlib.sha256(driver.stdout).hexdigest(), "driver_stderr_sha256": hashlib.sha256(driver.stderr).hexdigest(), "driver_evidence_sha256": None, "status": "driver_failed", "collector_exit": None, "collector_stdout_sha256": None, "collector_stderr_sha256": None, "infra_affected": False, "a5_clean": False, "first_late_threshold_crossed": None, "rows_sha256": None, "boundary_ledger_sha256": None, "artifact_dir": str(directory.relative_to(out))}
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
        status["rows_sha256"], status["boundary_ledger_sha256"], status["driver_evidence_sha256"] = sha256(directory / "rows.jsonl"), sha256(directory / "boundary-ledger.json"), sha256(directory / "cli-attestation.json")
        session_rows = rows(directory)
    except LaunchViolation:
        status["status"] = "collector_receipt_invalid"
        return status
    status["infra_affected"] = any(row.get("infra_invalid") is True for row in session_rows)
    for row in session_rows:
        if row.get("cli_argv") is None:
            try:
                stderr = (directory / f"t{row['position_index']}.{row['task']}" / "cli.stderr").read_text(encoding="utf-8")
            except (KeyError, OSError):
                status["status"] = "driver_receipt_invalid"
                return status
            if stderr.startswith("attempt setup failure:"):
                status["status"] = "driver_receipt_invalid"
                return status
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


def charged_attempt_count(manifest: dict[str, object]) -> int:
    return sum(len(block["attempts"]) for block in manifest["blocks"].values())


def root_expired(manifest: dict[str, object], params: dict[str, object]) -> bool:
    created = parse_iso8601(str(manifest["created_at"]), "created_at")
    return datetime.datetime.now(datetime.timezone.utc) >= created + datetime.timedelta(hours=params["venue_tolerance"]["calendar"]["root_age_hours"])


def derive_terminal(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> tuple[str, dict[str, object]]:
    refresh_designations(manifest, schedule)
    derive_a5(manifest, schedule)
    count = replacement_count(manifest)
    charged = charged_attempt_count(manifest)
    if root_expired(manifest, params):
        return "WALL_CLOCK_EXPIRED", {"charged_attempts": charged}
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
    incomplete = any(block["designated_attempt"] is None for block in manifest["blocks"].values())
    if incomplete and charged >= params["venue_tolerance"]["charged_accounting"]["maximum_block_attempts"]:
        return "CHARGED_ALLOWANCE_EXHAUSTED", {"charged_attempts": charged}
    if any(attempt["transport_state"] == "VOID" and block["designated_attempt"] is None for block in manifest["blocks"].values() for attempt in block["attempts"]):
        return "REPLACEMENT_PENDING", {"replacement_attempts": count, "charged_attempts": charged}
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
    if terminal in {"REPLACEMENT_PENDING", "A5_SUBJECT_UNAVAILABLE", "FAIL_FAST_THRESHOLD_UNREACHED", "UNREGISTERED_STRUCTURAL_FAILURE", "CHARGED_ALLOWANCE_EXHAUSTED", "WALL_CLOCK_EXPIRED"}:
        write_json(out / "launch-abort-0112.json", {"terminal": terminal, "details": details, "blocks": manifest["blocks"]})
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


def append_usage(manifest: dict[str, object], raw: bytes, evidence: dict[str, object], digest: str, role: str, sweep: int, params: dict[str, object]) -> None:
    if any(entry["sha256"] == digest for entry in manifest["usage_evidence"]):
        raise LaunchViolation("usage-evidence-reused")
    previous = []
    for entry in manifest["usage_evidence"]:
        decoded = json.loads(base64.b64decode(entry["bytes_base64"]))
        previous.append(decoded)
    epochs = [item["reset_at"] for item in previous]
    if epochs and evidence["reset_at"] in epochs and evidence["reset_at"] != epochs[-1]:
        raise LaunchViolation("usage-evidence-reset-reused-old")
    if epochs and evidence["reset_at"] != epochs[-1] and parse_iso8601(evidence["reset_at"], "reset_at") <= parse_iso8601(epochs[-1], "reset_at"):
        raise LaunchViolation("usage-evidence-reset-not-advancing")
    if epochs and evidence["reset_at"] != epochs[-1]:
        transitions = sum(previous_epoch != next_epoch for previous_epoch, next_epoch in zip(epochs, epochs[1:]))
        if transitions >= params["venue_tolerance"]["calendar"]["max_reset_epochs"]:
            raise LaunchViolation("usage-evidence-reset-epochs-exceeded")
    same_epoch = [item for item in previous if item["reset_at"] == evidence["reset_at"]]
    if same_epoch and (evidence["limit_transport_tokens"] != same_epoch[-1]["limit_transport_tokens"] or evidence["used_transport_tokens"] < same_epoch[-1]["used_transport_tokens"]):
        raise LaunchViolation("usage-evidence-nonmonotone")
    manifest["usage_evidence"].append({"sha256": digest, "bytes_base64": base64.b64encode(raw).decode(), "role": role, "sweep_id": sweep, "consumed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})


def expected_probe_argv(params: dict[str, object], engine: str) -> list[str]:
    command = params["venue_tolerance"]["resume_oracle"].get("probe_command")
    if not isinstance(command, list) or command.count("<engine>") != 1 or not all(isinstance(value, str) for value in command):
        raise LaunchViolation("resume-oracle-probe-command-invalid")
    return [engine if value == "<engine>" else value for value in command]


def load_resume_oracle(path: pathlib.Path, usage_digest: str, params: dict[str, object]) -> tuple[bytes, str, int]:
    try:
        raw = path.read_bytes()
        oracle = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise LaunchViolation(f"resume-oracle-unreadable:{exc}") from exc
    if not isinstance(oracle, dict) or set(oracle) != {"schema", "observed_at", "usage_sha256", "probes"} or oracle.get("schema") != "iter0112-resume-oracle-v1" or oracle.get("usage_sha256") != usage_digest or not isinstance(oracle.get("probes"), list):
        raise LaunchViolation("resume-oracle-schema-invalid")
    now = datetime.datetime.now(datetime.timezone.utc)
    observed = parse_iso8601(str(oracle["observed_at"]), "observed_at")
    freshness = datetime.timedelta(seconds=params["venue_tolerance"]["resume_oracle"]["probe_freshness_seconds"])
    skew = datetime.timedelta(seconds=params["venue_tolerance"]["usage_evidence"]["clock_skew_seconds"])
    if observed > now + skew or now - observed > freshness:
        raise LaunchViolation("resume-oracle-stale")
    ordered = params["venue_tolerance"]["resume_oracle"]["probe_order"]
    if len(oracle["probes"]) != len(ordered):
        raise LaunchViolation("resume-oracle-probe-count-invalid")
    prior = None
    for expected, probe in zip(ordered, oracle["probes"]):
        if not isinstance(probe, dict) or set(probe) != {"model", "argv", "executable_path", "executable_sha256", "started_at", "observed_at", "returncode", "stdout_bytes_base64", "stdout_sha256"} or probe.get("model") != expected or probe.get("returncode") != 0 or not is_digest(probe.get("stdout_sha256")):
            raise LaunchViolation("resume-oracle-probe-invalid")
        started, finished = parse_iso8601(str(probe["started_at"]), "probe-started-at"), parse_iso8601(str(probe["observed_at"]), "probe-observed-at")
        if finished < started or (prior is not None and started <= prior):
            raise LaunchViolation("resume-oracle-probe-order-invalid")
        if finished > now + skew or now - finished > freshness:
            raise LaunchViolation("resume-oracle-probe-stale")
        argv = probe.get("argv")
        registered = params["venue_tolerance"]["driver_evidence"]
        if argv != expected_probe_argv(params, expected) or probe.get("executable_path") != registered["cli_path"] or probe.get("executable_sha256") != registered["cli_sha256"]:
            raise LaunchViolation("resume-oracle-probe-command-invalid")
        try:
            executable_sha = sha256(pathlib.Path(str(probe["executable_path"])))
        except OSError as exc:
            raise LaunchViolation("resume-oracle-probe-executable-unreadable") from exc
        if executable_sha != registered["cli_sha256"]:
            raise LaunchViolation("resume-oracle-probe-executable-mismatch")
        prior = finished
        try:
            stdout = base64.b64decode(probe["stdout_bytes_base64"], validate=True)
            payload = json.loads(stdout)
        except (ValueError, json.JSONDecodeError) as exc:
            raise LaunchViolation("resume-oracle-probe-json-invalid") from exc
        if hashlib.sha256(stdout).hexdigest() != probe["stdout_sha256"] or not isinstance(payload, dict) or payload.get("is_error") is True or not isinstance(payload.get("modelUsage"), dict) or set(payload["modelUsage"]) != {expected}:
            raise LaunchViolation("resume-oracle-probe-failed")
    return raw, hashlib.sha256(raw).hexdigest(), len(ordered)


def consumed_probe_calls(manifest: dict[str, object]) -> int:
    entries = manifest.get("resume_oracles")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) or set(entry) != RESUME_ORACLE_ENTRY_FIELDS or type(entry.get("probe_calls")) is not int or entry["probe_calls"] < 0 for entry in entries):
        raise LaunchViolation("resume-oracle-manifest-invalid")
    return sum(entry["probe_calls"] for entry in entries)


def run(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    if args.sweep < 1 or args.sweep > schedule["sweeps"] or args.lanes != params["schedule"]["lanes"]:
        raise LaunchViolation("launch-arguments-invalid")
    pin, (attestation_raw, _attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    usage_raw, usage, usage_digest = load_usage_evidence(args.usage_evidence, params)
    if args.dry_run:
        if not usage_gate(usage, args.sweep, params):
            raise LaunchViolation("usage-budget-gate-refused")
        print(f"DRY_RUN: sweep={args.sweep} strict-budget-gate=PASS")
        return 0
    manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw)
    if args.record_usage_after:
        if any(entry["role"] == "post-sweep" and entry["sweep_id"] == args.sweep for entry in manifest["usage_evidence"]):
            raise LaunchViolation("usage-post-evidence-already-recorded")
        append_usage(manifest, usage_raw, usage, usage_digest, "post-sweep", args.sweep, params)
        write_json(args.out / MANIFEST_NAME, manifest)
        print(f"USAGE_RECORDED: post-sweep={args.sweep}")
        return 0
    terminal, _details = derive_terminal(manifest, schedule, params)
    if terminal in {"WALL_CLOCK_EXPIRED", "CHARGED_ALLOWANCE_EXHAUSTED", "A5_SUBJECT_UNAVAILABLE", "FAIL_FAST_THRESHOLD_UNREACHED", "UNREGISTERED_STRUCTURAL_FAILURE", "LAUNCH_COMPLETE"}:
        terminal = persist(args.out, manifest, schedule, params)
        print(f"TERMINAL: {terminal}")
        return 0 if terminal == "LAUNCH_COMPLETE" else 2
    if args.sweep > 1 and not any(entry["role"] == "post-sweep" and entry["sweep_id"] == args.sweep - 1 for entry in manifest["usage_evidence"]):
        raise LaunchViolation("usage-post-evidence-missing")
    if not usage_gate(usage, args.sweep, params):
        raise LaunchViolation("usage-budget-gate-refused")
    pending = terminal == "REPLACEMENT_PENDING"
    if pending:
        if args.resume_oracle is None:
            raise LaunchViolation("resume-oracle-missing")
        oracle_raw, oracle_digest, oracle_calls = load_resume_oracle(args.resume_oracle, usage_digest, params)
        if any(entry["sha256"] == oracle_digest for entry in manifest["resume_oracles"]):
            raise LaunchViolation("resume-oracle-reused")
        if consumed_probe_calls(manifest) + oracle_calls > params["venue_tolerance"]["resume_oracle"]["probe_budget_session_equivalents"]:
            raise LaunchViolation("resume-oracle-probe-budget-exhausted")
        manifest["resume_oracles"].append({"sha256": oracle_digest, "bytes_base64": base64.b64encode(oracle_raw).decode(), "attempt_ids": [], "consumed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "probe_calls": oracle_calls})
    elif args.resume_oracle is not None:
        raise LaunchViolation("resume-oracle-unexpected")
    append_usage(manifest, usage_raw, usage, usage_digest, "resume" if pending else "pre-sweep", args.sweep, params)
    gate_id, by_block = str(schedule["blocks"][0]["replicate_id"]), block_sessions(schedule)
    if not manifest["blocks"][gate_id]["attempts"] and args.sweep != 1:
        raise LaunchViolation("a5-gate-requires-sweep-one")
    running = [(rid, sessions) for rid, sessions in by_block.items() if manifest["blocks"][rid]["designated_attempt"] is None and manifest["blocks"][rid]["attempts"] and manifest["blocks"][rid]["attempts"][-1]["transport_state"] == "RUNNING"]
    voids = [(rid, sessions) for rid, sessions in by_block.items() if manifest["blocks"][rid]["designated_attempt"] is None and manifest["blocks"][rid]["attempts"] and manifest["blocks"][rid]["attempts"][-1]["transport_state"] == "VOID"]
    if running:
        candidates, reuse_running = running, True
    elif voids:
        candidates, reuse_running = voids, False
    else:
        ids = tuple(dict.fromkeys(str(session["replicate_id"]) for session in schedule["sessions"] if session["sweep_id"] == args.sweep))
        candidates, reuse_running = [(rid, by_block[rid]) for rid in ids if not manifest["blocks"][rid]["attempts"]], False
    while candidates:
        batch_size = 1 if candidates[0][0] == gate_id else args.lanes
        batch, candidates = candidates[:batch_size], candidates[batch_size:]
        if not reuse_running and charged_attempt_count(manifest) + len(batch) > params["venue_tolerance"]["charged_accounting"]["maximum_block_attempts"]:
            manifest["terminal"] = "CHARGED_ALLOWANCE_EXHAUSTED"
            write_json(args.out / MANIFEST_NAME, manifest)
            print("TERMINAL: CHARGED_ALLOWANCE_EXHAUSTED")
            return 2
        attempts = [(rid, sessions, manifest["blocks"][rid]["attempts"][-1] if reuse_running else new_attempt(manifest["blocks"][rid])) for rid, sessions in batch]
        if pending:
            manifest["resume_oracles"][-1]["attempt_ids"].extend(attempt["attempt_id"] for _rid, _sessions, attempt in attempts)
        args.out.mkdir(parents=True, exist_ok=True)
        write_json(args.out / MANIFEST_NAME, manifest)
        lock = threading.Lock()
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(attempts)) as executor:
            states = [future.result() for future in [executor.submit(execute_attempt, args.out, manifest, attempt, sessions, args.run_id, params, lock) for _rid, sessions, attempt in attempts]]
        terminal = persist(args.out, manifest, schedule, params)
        if any(state in {"VOID", "STRUCTURAL_FAILURE"} for state in states) or terminal != "LAUNCH_PARTIAL":
            print(f"TERMINAL: {terminal}")
            return 0 if terminal == "LAUNCH_COMPLETE" else 2
    terminal = persist(args.out, manifest, schedule, params)
    print(f"TERMINAL: {terminal}")
    return 0 if terminal == "LAUNCH_COMPLETE" else 2


def self_test() -> None:
    schedule, params = load_inputs(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    budget = params["venue_tolerance"]["budget_gate"]
    limit = budget["first_sweep_burn_bound_transport_tokens"] + budget["reserve_transport_tokens"]
    equal = {"used_transport_tokens": 0, "limit_transport_tokens": limit}
    greater = {"used_transport_tokens": 0, "limit_transport_tokens": limit + 1}
    assert not usage_gate(equal, 1, params) and usage_gate(greater, 1, params)
    with tempfile.TemporaryDirectory(prefix="iter0112-launch-") as temporary:
        root = pathlib.Path(temporary)
        evidence = root / "usage.json"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        payload = {"source": "usage", "observed_at": now, "value": "self-test", "attested_by": "self-test", "used_transport_tokens": 1, "limit_transport_tokens": 999999999, "reset_at": now}
        evidence.write_bytes(canonical_bytes(payload))
        raw, parsed, digest = load_usage_evidence(evidence, params)
        manifest = {"usage_evidence": []}
        append_usage(manifest, raw, parsed, digest, "pre-sweep", 1, params)
        try:
            append_usage(manifest, raw, parsed, digest, "resume", 1, params)
        except LaunchViolation as exc:
            assert str(exc) == "usage-evidence-reused"
        else:
            raise AssertionError("usage evidence reuse accepted")
        initial_reset = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
        advanced_reset = initial_reset + datetime.timedelta(days=1)
        second_advanced_reset = advanced_reset + datetime.timedelta(days=1)

        def epoch_evidence(value, reset_at):
            payload = {"source": "usage", "observed_at": now, "value": value, "attested_by": "self-test", "used_transport_tokens": 1, "limit_transport_tokens": 999999999, "reset_at": reset_at.isoformat()}
            raw = canonical_bytes(payload)
            return raw, payload, hashlib.sha256(raw).hexdigest()

        epoch_manifest = {"usage_evidence": []}
        first_epoch = epoch_evidence("initial epoch", initial_reset)
        advanced_epoch = epoch_evidence("advanced epoch", advanced_reset)
        append_usage(epoch_manifest, *first_epoch, "pre-sweep", 1, params)
        append_usage(epoch_manifest, *advanced_epoch, "post-sweep", 1, params)
        try:
            append_usage(epoch_manifest, *epoch_evidence("second transition", second_advanced_reset), "pre-sweep", 2, params)
        except LaunchViolation as exc:
            assert str(exc) == "usage-evidence-reset-epochs-exceeded"
        else:
            raise AssertionError("second reset transition accepted")
        try:
            append_usage(epoch_manifest, *epoch_evidence("backward reset", initial_reset - datetime.timedelta(days=1)), "pre-sweep", 2, params)
        except LaunchViolation as exc:
            assert str(exc) == "usage-evidence-reset-not-advancing"
        else:
            raise AssertionError("backward reset accepted")
        try:
            append_usage(epoch_manifest, *epoch_evidence("reused reset", initial_reset), "pre-sweep", 2, params)
        except LaunchViolation as exc:
            assert str(exc) == "usage-evidence-reset-reused-old"
        else:
            raise AssertionError("reused reset accepted")
        attestation = root / "window-attestation.json"
        attestation.write_bytes(canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
        out = root / "root"
        attempts_with_infra = set()

        epoch = datetime.datetime.now(datetime.timezone.utc).isoformat()

        def usage_file(name, used, limit_value, seconds_ago=0, reset_at=epoch):
            observed = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=seconds_ago)
            path = root / name
            path.write_bytes(canonical_bytes({"source": "usage", "observed_at": observed.isoformat(), "value": name, "attested_by": "self-test", "used_transport_tokens": used, "limit_transport_tokens": limit_value, "reset_at": reset_at}))
            return path

        def fake_session(session, fake_out, attempt_id, run_id, _params):
            directory = session_directory(attempt_root(fake_out, attempt_id), session)
            directory.mkdir(parents=True, exist_ok=False)
            infra = (attempt_id, session_key(session)) in attempts_with_infra
            session_rows = [{"position_index": task["position_index"], "infra_invalid": infra and task["position_index"] == 1, "catastrophic": False, "custody_ok": True, "custody_broken": False} for task in session["tasks"]]
            (directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in session_rows))
            (directory / "boundary-ledger.json").write_bytes(canonical_bytes({"boundaries": [{"position_index": position, "records_invalid": False, "peak_effective_context": 100000} for position in range(1, 9)]}))
            (directory / "cli-attestation.json").write_bytes(canonical_bytes({"synthetic": True}))
            digest = "0" * 64
            return {"engine": session["engine"], "replicate_id": session["replicate_id"], "session_label": session_key(session), "driver_command": command_for(session, attempt_root(fake_out, attempt_id), run_id), "collector_command": collector_command_for(directory), "driver_exit": 0, "driver_stdout_sha256": digest, "driver_stderr_sha256": digest, "driver_evidence_sha256": sha256(directory / "cli-attestation.json"), "status": "completed", "collector_exit": 0, "collector_stdout_sha256": digest, "collector_stderr_sha256": digest, "infra_affected": infra, "a5_clean": not infra, "first_late_threshold_crossed": True if session["engine"] in MATRIX_ENGINES else None, "rows_sha256": sha256(directory / "rows.jsonl"), "boundary_ledger_sha256": sha256(directory / "boundary-ledger.json"), "artifact_dir": str(directory.relative_to(fake_out))}

        original_run_session, original_inventory = run_session, verify_script_inventory
        globals()["run_session"] = fake_session
        globals()["verify_script_inventory"] = lambda: "0" * 64
        try:
            def invocation(usage_path, resume_oracle=None, record=False, sweep=1, lanes=3, target=out):
                return argparse.Namespace(sweep=sweep, lanes=lanes, out=target, run_id="self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=usage_path, resume_oracle=resume_oracle, record_usage_after=record, dry_run=False)

            missing = root / "missing.json"
            before = out.exists()
            try:
                run(invocation(missing))
            except LaunchViolation as exc:
                assert str(exc).startswith("usage-evidence-unreadable:")
            else:
                raise AssertionError("missing usage evidence accepted")
            assert out.exists() is before
            stale = usage_file("stale.json", 0, 999999999, 301)
            try:
                run(invocation(stale))
            except LaunchViolation as exc:
                assert str(exc) == "usage-evidence-stale"
            else:
                raise AssertionError("stale usage evidence accepted")
            future = usage_file("future.json", 0, 999999999, -6)
            try:
                run(invocation(future))
            except LaunchViolation as exc:
                assert str(exc) == "usage-evidence-future"
            else:
                raise AssertionError("future usage evidence accepted")
            equality = usage_file("equality.json", 0, limit, 0)
            try:
                run(invocation(equality))
            except LaunchViolation as exc:
                assert str(exc) == "usage-budget-gate-refused"
            else:
                raise AssertionError("strict equality boundary accepted")
            initial = usage_file("initial.json", 1, 999999999, 0)
            try:
                run(invocation(initial, lanes=2))
            except LaunchViolation as exc:
                assert str(exc) == "launch-arguments-invalid"
            else:
                raise AssertionError("mutable lane count accepted")
            gate_id = str(schedule["blocks"][0]["replicate_id"])
            attempts_with_infra.add((f"{gate_id}.a1", session_key(block_sessions(schedule)[gate_id][0])))
            assert run(invocation(initial)) == 2
            manifest_path = out / MANIFEST_NAME
            before_manifest = manifest_path.read_bytes()
            resumed = usage_file("resumed.json", 2, 999999999, 0)
            try:
                run(invocation(resumed))
            except LaunchViolation as exc:
                assert str(exc) == "resume-oracle-missing"
            else:
                raise AssertionError("resume without oracle accepted")
            assert manifest_path.read_bytes() == before_manifest
            raw_resume, _value, resume_digest = load_usage_evidence(resumed, params)
            probe_now = datetime.datetime.now(datetime.timezone.utc)
            probe_time = probe_now.isoformat()
            driver = params["venue_tolerance"]["driver_evidence"]
            probes = []
            for index, engine in enumerate(ENGINES):
                stdout = canonical_bytes({"is_error": False, "modelUsage": {engine: {}}})
                started = probe_now - datetime.timedelta(seconds=3 - index)
                finished = started + datetime.timedelta(milliseconds=500)
                probes.append({"model": engine, "argv": expected_probe_argv(params, engine), "executable_path": driver["cli_path"], "executable_sha256": driver["cli_sha256"], "started_at": started.isoformat(), "observed_at": finished.isoformat(), "returncode": 0, "stdout_bytes_base64": base64.b64encode(stdout).decode(), "stdout_sha256": hashlib.sha256(stdout).hexdigest()})
            oracle_path = root / "resume-oracle.json"
            oracle_path.write_bytes(canonical_bytes({"schema": "iter0112-resume-oracle-v1", "observed_at": probe_time, "usage_sha256": resume_digest, "probes": probes}))
            stale_oracle = root / "resume-oracle-stale-probe.json"
            stale_probes = [dict(probe) for probe in probes]
            stale_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=301)).isoformat()
            stale_probes[0]["started_at"] = stale_time
            stale_probes[0]["observed_at"] = stale_time
            stale_oracle.write_bytes(canonical_bytes({"schema": "iter0112-resume-oracle-v1", "observed_at": probe_time, "usage_sha256": resume_digest, "probes": stale_probes}))
            before_manifest = manifest_path.read_bytes()
            try:
                run(invocation(resumed, stale_oracle))
            except LaunchViolation as exc:
                assert str(exc) == "resume-oracle-probe-stale"
            else:
                raise AssertionError("stale per-probe oracle accepted")
            assert manifest_path.read_bytes() == before_manifest
            command_oracle = root / "resume-oracle-command.json"
            command_probes = [dict(probe) for probe in probes]
            command_probes[0]["argv"] = ["/unregistered/cli"]
            command_oracle.write_bytes(canonical_bytes({"schema": "iter0112-resume-oracle-v1", "observed_at": probe_time, "usage_sha256": resume_digest, "probes": command_probes}))
            try:
                run(invocation(resumed, command_oracle))
            except LaunchViolation as exc:
                assert str(exc) == "resume-oracle-probe-command-invalid"
            else:
                raise AssertionError("unregistered probe command accepted")
            assert manifest_path.read_bytes() == before_manifest
            list_usage_oracle = root / "resume-oracle-list-model-usage.json"
            list_usage_probes = [dict(probe) for probe in probes]
            list_usage_stdout = canonical_bytes({"is_error": False, "modelUsage": [ENGINES[0]]})
            list_usage_probes[0]["stdout_bytes_base64"] = base64.b64encode(list_usage_stdout).decode()
            list_usage_probes[0]["stdout_sha256"] = hashlib.sha256(list_usage_stdout).hexdigest()
            list_usage_oracle.write_bytes(canonical_bytes({"schema": "iter0112-resume-oracle-v1", "observed_at": probe_time, "usage_sha256": resume_digest, "probes": list_usage_probes}))
            try:
                run(invocation(resumed, list_usage_oracle))
            except LaunchViolation as exc:
                assert str(exc) == "resume-oracle-probe-failed"
            else:
                raise AssertionError("list-valued probe modelUsage accepted")
            assert manifest_path.read_bytes() == before_manifest
            assert run(invocation(resumed, oracle_path)) == 2
            post = usage_file("post.json", 3, 999999999, 0)
            assert run(invocation(post, record=True)) == 0

            attempts_with_infra.clear()
            weekly = root / "weekly-recovery"
            weekly_initial = usage_file("weekly-initial.json", 4, 999999999, reset_at=initial_reset.isoformat())
            assert run(invocation(weekly_initial, target=weekly)) == 2
            weekly_post = usage_file("weekly-post.json", 5, 999999999, reset_at=initial_reset.isoformat())
            assert run(invocation(weekly_post, record=True, target=weekly)) == 0
            weekly_recovery = usage_file("weekly-recovery.json", 6, 999999999, reset_at=advanced_reset.isoformat())
            assert run(invocation(weekly_recovery, sweep=2, target=weekly)) == 2
            weekly_manifest = read_json(weekly / MANIFEST_NAME)
            assert {json.loads(base64.b64decode(entry["bytes_base64"]))["reset_at"] for entry in weekly_manifest["usage_evidence"]} == {initial_reset.isoformat(), advanced_reset.isoformat()}

            paused = root / "post-sweep-pause"
            assert run(invocation(usage_file("pause-pre.json", 7, 999999999), target=paused)) == 2
            paused_limit = 999999999
            paused_used = paused_limit - params["venue_tolerance"]["budget_gate"]["subsequent_sweep_burn_bound_transport_tokens"] - params["venue_tolerance"]["budget_gate"]["reserve_transport_tokens"]
            assert run(invocation(usage_file("pause-post.json", paused_used, paused_limit), record=True, target=paused)) == 0
            try:
                run(invocation(usage_file("pause-next-pre.json", paused_used, paused_limit), sweep=2, target=paused))
            except LaunchViolation as exc:
                assert str(exc) == "usage-budget-gate-refused"
            else:
                raise AssertionError("low-headroom next sweep accepted")

            def oracle_for(name, usage_path):
                _raw, _payload, usage_digest = load_usage_evidence(usage_path, params)
                probe_now = datetime.datetime.now(datetime.timezone.utc)
                now = probe_now.isoformat()
                driver = params["venue_tolerance"]["driver_evidence"]
                probes = []
                for index, engine in enumerate(ENGINES):
                    stdout = canonical_bytes({"is_error": False, "modelUsage": {engine: {}}})
                    started = probe_now - datetime.timedelta(seconds=3 - index)
                    finished = started + datetime.timedelta(milliseconds=500)
                    probes.append({"model": engine, "argv": expected_probe_argv(params, engine), "executable_path": driver["cli_path"], "executable_sha256": driver["cli_sha256"], "started_at": started.isoformat(), "observed_at": finished.isoformat(), "returncode": 0, "stdout_bytes_base64": base64.b64encode(stdout).decode(), "stdout_sha256": hashlib.sha256(stdout).hexdigest()})
                path = root / name
                path.write_bytes(canonical_bytes({"schema": "iter0112-resume-oracle-v1", "observed_at": now, "usage_sha256": usage_digest, "probes": probes}))
                return path

            attempts_with_infra.clear()
            parallel = root / "parallel-voids"
            sweep_one = [str(block["replicate_id"]) for block in schedule["blocks"] if block["sweep_id"] == 1]
            for replicate_id in sweep_one[1:]:
                attempts_with_infra.add((f"{replicate_id}.a1", session_key(block_sessions(schedule)[replicate_id][0])))
            parallel_initial = usage_file("parallel-initial.json", 10, 999999999, 0)
            assert run(invocation(parallel_initial, target=parallel)) == 2
            parallel_resume = usage_file("parallel-resume.json", 11, 999999999, 0)
            assert run(invocation(parallel_resume, oracle_for("parallel-oracle-1.json", parallel_resume), target=parallel)) == 2
            parallel_manifest = read_json(parallel / MANIFEST_NAME)
            assert isinstance(parallel_manifest, dict)
            first_oracle = parallel_manifest["resume_oracles"][0]
            assert first_oracle["probe_calls"] == 3 and len(first_oracle["attempt_ids"]) == 3
            assert all(len(parallel_manifest["blocks"][replicate_id]["attempts"]) == 2 for replicate_id in sweep_one[1:])
            parallel_post = usage_file("parallel-post.json", 12, 999999999, 0)
            assert run(invocation(parallel_post, record=True, target=parallel)) == 0
            sweep_two = [str(block["replicate_id"]) for block in schedule["blocks"] if block["sweep_id"] == 2]
            for replicate_id in sweep_two[:3]:
                attempts_with_infra.add((f"{replicate_id}.a1", session_key(block_sessions(schedule)[replicate_id][0])))
            second_initial = usage_file("parallel-second-initial.json", 13, 999999999, 0)
            assert run(invocation(second_initial, sweep=2, target=parallel)) == 2
            second_resume = usage_file("parallel-second-resume.json", 14, 999999999, 0)
            assert run(invocation(second_resume, oracle_for("parallel-oracle-2.json", second_resume), sweep=2, target=parallel)) == 2
            parallel_manifest = read_json(parallel / MANIFEST_NAME)
            assert isinstance(parallel_manifest, dict)
            assert len(parallel_manifest["resume_oracles"]) == 2 and consumed_probe_calls(parallel_manifest) == 6

            expired = root / "expired"
            expired_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", "0" * 64, attestation.read_bytes())
            expired_manifest["created_at"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=169)).isoformat()
            expired.mkdir()
            (expired / MANIFEST_NAME).write_bytes(canonical_bytes(expired_manifest))
            expired_usage = usage_file("expired-usage.json", 15, 999999999, 0)
            assert run(invocation(expired_usage, target=expired)) == 2
            charged = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "charged", "0" * 64, attestation.read_bytes())
            charged_block = charged["blocks"][gate_id]
            for _ in range(params["venue_tolerance"]["charged_accounting"]["maximum_block_attempts"]):
                new_attempt(charged_block)
            assert derive_terminal(charged, schedule, params)[0] == "CHARGED_ALLOWANCE_EXHAUSTED"
        finally:
            globals()["run_session"] = original_run_session
            globals()["verify_script_inventory"] = original_inventory
        integration = root / "status-classification"

        class FakeProcess:
            def __init__(self, returncode, stdout=b"", stderr=b""):
                self.returncode, self.stdout, self.stderr = returncode, stdout, stderr

        def classify_session(label, first_argv, first_stderr, suffix_stderr):
            session = {"engine": "claude-sonnet-5", "replicate_id": label, "session_label": label, "replicate_index": 1, "tasks": [{"position_index": 1, "task_id": "A"}, {"position_index": 2, "task_id": "B"}]}
            attempt_id = f"{label}.a1"
            directory = session_directory(attempt_root(integration, attempt_id), session)
            directory.mkdir(parents=True)
            rows_payload = [{"position_index": 1, "task": "A", "cli_argv": first_argv, "infra_invalid": False}, {"position_index": 2, "task": "B", "cli_argv": None, "infra_invalid": False}]
            (directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows_payload))
            (directory / "boundary-ledger.json").write_bytes(canonical_bytes({"boundaries": []}))
            (directory / "cli-attestation.json").write_bytes(canonical_bytes({"synthetic": True}))
            for position, task, stderr in ((1, "A", first_stderr), (2, "B", suffix_stderr)):
                task_dir = directory / f"t{position}.{task}"
                task_dir.mkdir()
                (task_dir / "cli.stderr").write_text(stderr, encoding="utf-8")
            original_subprocess_run = subprocess.run
            def fake_subprocess(command, **_kwargs):
                if len(command) > 1 and command[1] == str(DRIVER):
                    return FakeProcess(0, (json.dumps({"session_dir": str(directory)}) + "\n").encode())
                return FakeProcess(0)
            globals()["subprocess"].run = fake_subprocess
            try:
                return run_session(session, integration, attempt_id, "self-test", params)
            finally:
                globals()["subprocess"].run = original_subprocess_run

        setup_status = classify_session("setup-structural", None, "attempt setup failure: malformed task\n", "custody broken by earlier invocation\n")
        runner_status = classify_session("runner-scoreable", ["registered", "driver"], "runner failure: self-test\n", "custody broken by earlier invocation\n")
        assert setup_status["status"] == "driver_receipt_invalid" and setup_status["infra_affected"] is False
        assert runner_status["status"] == "completed" and runner_status["infra_affected"] is False
    print("SELF_TEST_OK: run() refusal reachability (missing/stale/future/equality/resume), setup-structural versus runner-scoreable mapping, fixed lanes, three-block lane-parallel replay, multi-resume per-call accounting, 168h expiry, strict budget boundary, consumed evidence append-only, charged accounting, raw-attestation schema")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", type=int); parser.add_argument("--lanes", type=int, default=3); parser.add_argument("--out", type=pathlib.Path); parser.add_argument("--run-id"); parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE); parser.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS); parser.add_argument("--window-attestation", type=pathlib.Path); parser.add_argument("--usage-evidence", type=pathlib.Path); parser.add_argument("--resume-oracle", type=pathlib.Path); parser.add_argument("--record-usage-after", action="store_true"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try: self_test()
        except (AssertionError, OSError, LaunchViolation, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr); return 1
        return 0
    if args.sweep is None or args.out is None or args.run_id is None or args.window_attestation is None or args.usage_evidence is None:
        parser.error("--sweep, --out, --run-id, --window-attestation, and --usage-evidence are required unless --self-test is used")
    try: return run(args)
    except LaunchViolation as exc:
        print(f"FAIL launch-0112: {exc}", file=sys.stderr); return 3


if __name__ == "__main__":
    raise SystemExit(main())
