#!/usr/bin/env python3
"""Stageable iter-0112 launcher with percent-calibrated, outcome-blind block replay.

Launch-day order: offline pins/window checks and a quiet account; pre-percent
capture; frozen calibration batch (and retained prefix attestation); two settled
post captures; calibration and closure checks; a fresh final same-epoch capture
equal to the settlement second; dry-run; then launch.  Any later account call
requires a fresh capture.
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import datetime
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import shlex
import subprocess
import sys
import tempfile
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_SCHEDULE = REPO / "docs/specs/iter0112/schedule.json"
DEFAULT_PARAMS = REPO / "docs/specs/iter0112/registered-params.json"
DRIVER = HERE / "sh-driver-0112.py"
COLLECTOR = HERE / "boundary-ledger-0112.py"
USAGE_CAPTURE = HERE / "usage-capture-0112.py"
PENDING_FIXTURE = REPO / "benchmark/executor-quality/fixtures-0112/calibration-pending-20260902.json"
PENDING_RECEIPT_FIXTURE = REPO / "benchmark/executor-quality/fixtures-0112/calibration-pending-20260902-receipts"
MANIFEST_NAME = "launch-manifest-0112.json"
PIN_FILE = REPO / "docs/specs/iter0112/scripts.sha256"
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
ENGINES = (*MATRIX_ENGINES, "claude-sonnet-5")
APPARATUS_SCRIPTS = ("sh-driver-0112.py", "boundary-ledger-0112.py", "smoke-gate-0112.py", "derive-schedule-0112.py", "g0-power-0112.py", "score-0112.py", "launch-0112.py", "usage-capture-0112.py", "../fixtures-0112/usage-endpoint-20260902-0840KST.raw.json", "../fixtures-0112/usage-jitter-B-20260902-1055KST.raw.json", "../fixtures-0112/calibration-pending-20260902.json")
CALIBRATION_ENGINES = ("claude-opus-5", "claude-opus-4-8", "claude-sonnet-5")
CALIBRATION_TASKS = ("smoke-1", "smoke-2")
REQUIRED_PIN_TARGETS = frozenset([f"benchmark/executor-quality/scripts/{name}" if "/" not in name else f"benchmark/executor-quality/{name[3:]}" for name in APPARATUS_SCRIPTS] + ["docs/specs/iter0112/schedule.json", "docs/specs/iter0112/registered-params.json", "benchmark/executor-quality/fixtures-0112/calibration-pending-20260902-receipts (whole tree)", "benchmark/executor-quality/tasks-0110-smoke/smoke-1 (whole tree)", "benchmark/executor-quality/tasks-0110-smoke/smoke-2 (whole tree)"])
STATUS_FIELDS = frozenset(("engine", "replicate_id", "session_label", "driver_command", "collector_command", "driver_exit", "driver_stdout_sha256", "driver_stderr_sha256", "driver_evidence_sha256", "status", "collector_exit", "collector_stdout_sha256", "collector_stderr_sha256", "infra_affected", "a5_clean", "first_late_threshold_crossed", "rows_sha256", "boundary_ledger_sha256", "artifact_dir", "completed_at"))
ATTEMPT_FIELDS = frozenset(("attempt_id", "replacement_of", "transport_state", "unrun_suffix", "sessions", "charged_session_equivalents"))
USAGE_FIELDS = ("source", "meter_id", "observed_at", "value", "attested_by", "used_percent", "display_resolution_percent", "reset_at", "panel_sha256", "auxiliary")
USAGE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "role", "sweep_id", "consumed_at"))
RESUME_ORACLE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "attempt_ids", "consumed_at", "probe_calls"))
CAPTURE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "consumed_at"))
CALIBRATION_ATTEMPT_FIELDS = frozenset(("attempt_id", "status", "started_at", "epoch", "captures", "units", "settlement_pairs", "sessions", "receipts", "session_equivalents", "settlement_commit"))
SETTLEMENT_FIELDS = frozenset(("reset_at", "captures"))
COMPONENT_FIELDS = frozenset(("input", "output", "cache_create", "cache_read", "total"))
COMPLETED_SWEEP_FIELDS = frozenset(("sweep_id", "pre_sha256", "post_sha256", "receipts", "components", "draw"))
CALIBRATION_PENDING_NAME = "calibration-pending-0112.json"
CALIBRATION_LEDGER_NAME = "calibration-ledger-0112.json"


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
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_bytes(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


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
    if not isinstance(venue, dict) or not isinstance(venue.get("usage_evidence"), dict) or not isinstance(venue.get("budget_gate"), dict) or not isinstance(venue.get("calendar"), dict) or not isinstance(venue.get("charged_accounting"), dict) or not isinstance(venue.get("resume_oracle"), dict) or not isinstance(venue.get("calibration"), dict) or not isinstance(venue.get("settlement"), dict) or not isinstance(venue.get("closure_check"), dict):
        raise LaunchViolation("venue-tolerance-schema-invalid")
    if venue["usage_evidence"].get("schema") != "iter0112-usage-v2" or venue["usage_evidence"].get("exact_fields") != list(USAGE_FIELDS) or venue["usage_evidence"].get("meter_id") != "current_week_all_models" or type(venue["usage_evidence"].get("freshness_seconds")) is not int:
        raise LaunchViolation("usage-evidence-schema-invalid")
    if type(venue["charged_accounting"].get("maximum_block_attempts")) is not int or venue["charged_accounting"]["maximum_block_attempts"] < 20:
        raise LaunchViolation("charged-allowance-invalid")
    calibration = venue["calibration"]
    accounting = calibration.get("accounting")
    session_bound, bracket_bound = calibration.get("full_session_bound_transport_tokens"), calibration.get("full_bracket_wall_ms")
    if not isinstance(accounting, dict) or set(accounting) != {"per_session_equivalents", "attempt_session_cap", "epoch_session_cap", "root_session_cap", "derivation"} or accounting.get("per_session_equivalents") != 1 or accounting.get("attempt_session_cap") != 36 or accounting.get("epoch_session_cap") != 36 or accounting.get("root_session_cap") != 252 or not isinstance(accounting.get("derivation"), str) or not isinstance(session_bound, dict) or not isinstance(bracket_bound, dict) or type(session_bound.get("value")) is not int or session_bound["value"] <= 0 or type(bracket_bound.get("value")) is not int or bracket_bound["value"] <= 0:
        raise LaunchViolation("calibration-session-accounting-invalid")
    if type(venue["usage_evidence"].get("clock_skew_seconds")) is not int or venue["usage_evidence"]["clock_skew_seconds"] < 0:
        raise LaunchViolation("usage-evidence-clock-skew-invalid")
    closure = venue["closure_check"]
    derivation = closure.get("probe_prefix_bound_derivation")
    if type(closure.get("probe_prefix_bound_transport_tokens")) is not int or closure["probe_prefix_bound_transport_tokens"] <= 0 or not isinstance(derivation, dict) or derivation.get("maximum_observed_transport_tokens") != 34433 or derivation.get("safety_factor_numerator") != 5 or derivation.get("safety_factor_denominator") != 4 or closure["probe_prefix_bound_transport_tokens"] != ceil_div(34433 * 5, 4):
        raise LaunchViolation("closure-probe-bound-invalid")
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


def decode_usage_evidence(raw: bytes, params: dict[str, object]) -> dict[str, object]:
    try:
        evidence = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LaunchViolation("usage-evidence-schema-invalid") from exc
    if not isinstance(evidence, dict) or set(evidence) != set(USAGE_FIELDS) or evidence.get("source") != "usage" or evidence.get("meter_id") != params["venue_tolerance"]["usage_evidence"]["meter_id"]:
        raise LaunchViolation("usage-evidence-schema-invalid")
    if any(not isinstance(evidence.get(field), str) or not evidence[field] for field in ("observed_at", "value", "attested_by", "reset_at")):
        raise LaunchViolation("usage-evidence-text-invalid")
    if type(evidence.get("used_percent")) is not int or not 0 <= evidence["used_percent"] <= 100 or type(evidence.get("display_resolution_percent")) is not int or evidence["display_resolution_percent"] != 1 or not is_digest(evidence.get("panel_sha256")):
        raise LaunchViolation("usage-evidence-numeric-invalid")
    auxiliary = evidence.get("auxiliary")
    if not isinstance(auxiliary, dict) or set(auxiliary) != {"current_week_fable_percent", "current_session_percent"} or any(value is not None and (type(value) is not int or not 0 <= value <= 100) for value in auxiliary.values()):
        raise LaunchViolation("usage-evidence-auxiliary-invalid")
    parse_iso8601(evidence["observed_at"], "observed_at")
    parse_iso8601(evidence["reset_at"], "reset_at")
    return evidence


def validate_usage_consumption(evidence: dict[str, object], consumed_at: datetime.datetime, params: dict[str, object]) -> None:
    observed = parse_iso8601(str(evidence["observed_at"]), "observed_at")
    skew = datetime.timedelta(seconds=params["venue_tolerance"]["usage_evidence"]["clock_skew_seconds"])
    freshness = datetime.timedelta(seconds=params["venue_tolerance"]["usage_evidence"]["freshness_seconds"])
    if observed > consumed_at + skew:
        raise LaunchViolation("usage-evidence-future")
    if consumed_at - observed > freshness:
        raise LaunchViolation("usage-evidence-stale")


def load_usage_evidence(path: pathlib.Path, params: dict[str, object]) -> tuple[bytes, dict[str, object], str]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LaunchViolation(f"usage-evidence-unreadable:{exc}") from exc
    evidence = decode_usage_evidence(raw, params)
    validate_usage_consumption(evidence, datetime.datetime.now(datetime.timezone.utc), params)
    return raw, evidence, hashlib.sha256(raw).hexdigest()


def ceil_div(numerator: int, denominator: int) -> int:
    if type(numerator) is not int or type(denominator) is not int or numerator < 0 or denominator <= 0:
        raise LaunchViolation("tpp-invalid")
    return (numerator + denominator - 1) // denominator


def used_percent_upper(evidence: dict[str, object]) -> int:
    used, resolution = evidence.get("used_percent"), evidence.get("display_resolution_percent")
    if type(used) is not int or type(resolution) is not int:
        raise LaunchViolation("usage-evidence-numeric-invalid")
    return min(100, used + resolution)


def usage_gate(evidence: dict[str, object], sweep: int, params: dict[str, object], tpp_gate: int) -> bool:
    budget = params["venue_tolerance"]["budget_gate"]
    burn = budget["first_sweep_burn_bound_transport_tokens"] if sweep == 1 else budget["subsequent_sweep_burn_bound_transport_tokens"]
    return used_percent_upper(evidence) + ceil_div(burn, tpp_gate) + ceil_div(budget["reserve_transport_tokens"], tpp_gate) < 100


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


def capture_entry(raw: bytes, digest: str, consumed_at: datetime.datetime | None = None) -> dict[str, object]:
    return {"sha256": digest, "bytes_base64": base64.b64encode(raw).decode(), "consumed_at": (consumed_at or datetime.datetime.now(datetime.timezone.utc)).isoformat()}


def decode_capture(entry: object, params: dict[str, object]) -> tuple[bytes, dict[str, object]]:
    if not isinstance(entry, dict) or set(entry) != CAPTURE_ENTRY_FIELDS or not is_digest(entry.get("sha256")) or not isinstance(entry.get("bytes_base64"), str):
        raise LaunchViolation("calibration-capture-invalid")
    consumed_at = parse_iso8601(str(entry.get("consumed_at")), "calibration-capture-consumed-at")
    try:
        raw = base64.b64decode(entry["bytes_base64"], validate=True)
        evidence = json.loads(raw)
    except (ValueError, json.JSONDecodeError) as exc:
        raise LaunchViolation("calibration-capture-invalid") from exc
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise LaunchViolation("calibration-capture-invalid")
    checked = decode_usage_evidence(raw, params)
    validate_usage_consumption(checked, consumed_at, params)
    return raw, checked


def empty_components() -> dict[str, int]:
    return {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "total": 0}


def token_components(payload: object, engine: str) -> dict[str, int]:
    if not isinstance(payload, dict) or not isinstance(payload.get("modelUsage"), dict) or set(payload["modelUsage"]) != {engine}:
        raise LaunchViolation("calibration-receipt-schema-invalid")
    usage = payload["modelUsage"][engine]
    names = {"inputTokens": "input", "outputTokens": "output", "cacheCreationInputTokens": "cache_create", "cacheReadInputTokens": "cache_read"}
    if not isinstance(usage, dict) or any(type(usage.get(source)) is not int or usage[source] < 0 for source in names):
        raise LaunchViolation("calibration-receipt-components-invalid")
    result = {target: usage[source] for source, target in names.items()}
    result["total"] = sum(result.values())
    return result


def calibration_session_labels(sessions: object, attempt_id: int | None = None) -> list[str]:
    """Validate the ordered prefix which has been charged to one bracket attempt."""
    if not isinstance(sessions, list):
        raise LaunchViolation("calibration-program-invalid")
    labels: list[str] = []
    for index in range(len(sessions)):
        engine = CALIBRATION_ENGINES[index % len(CALIBRATION_ENGINES)]
        unit = index // len(CALIBRATION_ENGINES) + 1
        label = f"calibration-{unit}-{engine}" if attempt_id is None else f"calibration-a{attempt_id}-u{unit}-{engine}"
        labels.append(label)
    if sessions != labels:
        raise LaunchViolation("calibration-program-invalid")
    return labels


def calibration_receipt_layout(sessions: object, attempt_id: int | None = None) -> list[tuple[str, str]]:
    labels = calibration_session_labels(sessions, attempt_id)
    if not labels:
        return []
    expected: list[tuple[str, str]] = []
    for label in labels:
        engine = next(candidate for candidate in CALIBRATION_ENGINES if label.endswith(f"-{candidate}"))
        for position, task in enumerate(CALIBRATION_TASKS, 1):
            expected.append((f"calibration/{engine}.{label}.r1/t{position}.{task}/cli.stdout", engine))
    return expected


def completed_sweep_receipt_layout(out: pathlib.Path, manifest: dict[str, object], schedule: dict[str, object], sweep: int) -> list[tuple[str, str]]:
    expected: list[tuple[str, str]] = []
    for block in schedule["blocks"]:
        if block["sweep_id"] != sweep:
            continue
        attempt = designated(manifest, str(block["replicate_id"]))
        if attempt is None:
            raise LaunchViolation("sweep-not-complete")
        for session in block_sessions(schedule)[str(block["replicate_id"])]:
            status = attempt["sessions"].get(session_key(session))
            if not isinstance(status, dict) or status.get("status") != "completed" or status.get("artifact_dir") != str(session_directory(attempt_root(out, str(attempt["attempt_id"])), session).relative_to(out)):
                raise LaunchViolation("sweep-not-complete")
            for position, task in enumerate(session["tasks"], 1):
                expected.append((str((out / str(status["artifact_dir"]) / f"t{position}.{task['task_id']}" / "cli.stdout").relative_to(out)), str(session["engine"])))
    if not expected:
        raise LaunchViolation("sweep-not-complete")
    return expected


def sum_receipts(out: pathlib.Path, receipts: object, expected_layout: list[tuple[str, str]] | None = None) -> dict[str, int]:
    if not isinstance(receipts, list) or not receipts:
        raise LaunchViolation("calibration-receipts-invalid")
    result = empty_components()
    seen: set[str] = set()
    actual_layout: list[tuple[str, str]] = []
    for receipt in receipts:
        if not isinstance(receipt, dict) or set(receipt) != {"path", "sha256", "engine", "completed_at"} or not isinstance(receipt.get("path"), str) or not is_digest(receipt.get("sha256")) or receipt.get("engine") not in CALIBRATION_ENGINES:
            raise LaunchViolation("calibration-receipt-invalid")
        parse_iso8601(str(receipt["completed_at"]), "calibration-receipt-completed-at")
        relative = pathlib.PurePath(receipt["path"])
        if relative.is_absolute() or ".." in relative.parts or receipt["path"] in seen:
            raise LaunchViolation("calibration-receipt-path-invalid")
        seen.add(receipt["path"])
        actual_layout.append((receipt["path"], str(receipt["engine"])))
        path = out / relative
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise LaunchViolation("calibration-receipt-unreadable") from exc
        if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
            raise LaunchViolation("calibration-receipt-digest-invalid")
        for name, value in token_components(payload, str(receipt["engine"])).items():
            result[name] += value
    if expected_layout is not None and actual_layout != expected_layout:
        raise LaunchViolation("calibration-receipt-program-invalid")
    return result


def calibration_for_epoch(manifest: dict[str, object], reset_at: str) -> dict[str, object] | None:
    calibrations = manifest.get("calibrations")
    if not isinstance(calibrations, list):
        raise LaunchViolation("launch-manifest-calibrations-invalid")
    return next((entry for entry in reversed(calibrations) if isinstance(entry, dict) and entry.get("reset_at") == reset_at), None)


def evidence_by_digest(manifest: dict[str, object], params: dict[str, object]) -> dict[str, tuple[dict[str, object], datetime.datetime]]:
    result: dict[str, tuple[dict[str, object], datetime.datetime]] = {}
    for calibration in manifest.get("calibrations", []):
        if not isinstance(calibration, dict):
            raise LaunchViolation("launch-manifest-calibrations-invalid")
        captures = [calibration.get("pre_capture"), *(calibration.get("settlement_captures", []) if isinstance(calibration.get("settlement_captures"), list) else [])]
        for capture in captures:
            raw, evidence = decode_capture(capture, params)
            digest = hashlib.sha256(raw).hexdigest()
            if digest in result:
                raise LaunchViolation("usage-evidence-reused")
            result[digest] = (evidence, parse_iso8601(str(capture["consumed_at"]), "calibration-capture-consumed-at"))
    for settlement in manifest.get("settlements", []):
        if not isinstance(settlement, dict) or not isinstance(settlement.get("captures"), list):
            raise LaunchViolation("settlement-entry-invalid")
        for capture in settlement["captures"]:
            raw, evidence = decode_capture(capture, params)
            digest = hashlib.sha256(raw).hexdigest()
            if digest in result:
                raise LaunchViolation("usage-evidence-reused")
            result[digest] = (evidence, parse_iso8601(str(capture["consumed_at"]), "settlement-capture-consumed-at"))
    for entry in manifest.get("usage_evidence", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("bytes_base64"), str) or not is_digest(entry.get("sha256")):
            raise LaunchViolation("launch-manifest-usage-evidence-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid") from exc
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise LaunchViolation("usage-evidence-reused")
        evidence = decode_usage_evidence(raw, params)
        consumed = parse_iso8601(str(entry.get("consumed_at")), "usage-consumed-at")
        validate_usage_consumption(evidence, consumed, params)
        prior = result.get(entry["sha256"])
        if prior is not None and prior[0] != evidence:
            raise LaunchViolation("usage-evidence-reused")
        result.setdefault(entry["sha256"], (evidence, consumed))
    return result


def tpp_gate_for_epoch(manifest: dict[str, object], reset_at: str, params: dict[str, object], consumed_at: datetime.datetime | None = None) -> int:
    calibration = calibration_for_epoch(manifest, reset_at)
    if calibration is None or not isinstance(calibration.get("tpp_chain"), list):
        raise LaunchViolation("calibration-missing-for-epoch")
    evidence = evidence_by_digest(manifest, params)
    observations: list[object] = []
    for entry in calibration["tpp_chain"]:
        if not isinstance(entry, dict) or not is_digest(entry.get("post_sha256")) or entry["post_sha256"] not in evidence:
            raise LaunchViolation("tpp-chain-invalid")
        if consumed_at is None or evidence[entry["post_sha256"]][1] <= consumed_at:
            observations.append(entry.get("tpp_obs"))
    if not observations or any(type(value) is not int or value <= 0 for value in observations):
        raise LaunchViolation("tpp-chain-invalid")
    return min(observations)


def calibration_mix_ok(components: dict[str, int], completed_sweep: bool = False) -> bool:
    total, cache_read = components.get("total"), components.get("cache_read")
    if type(total) is not int or type(cache_read) is not int or total <= 0:
        return False
    return 1000 * cache_read >= 973 * total if completed_sweep else 1000 * cache_read <= 973 * total


def usage_entries_by_digest(manifest: dict[str, object], params: dict[str, object]) -> dict[str, tuple[dict[str, object], dict[str, object]]]:
    entries = manifest.get("usage_evidence")
    if not isinstance(entries, list):
        raise LaunchViolation("launch-manifest-usage-evidence-invalid")
    result: dict[str, tuple[dict[str, object], dict[str, object]]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != USAGE_ENTRY_FIELDS or not is_digest(entry.get("sha256")) or not isinstance(entry.get("bytes_base64"), str):
            raise LaunchViolation("launch-manifest-usage-evidence-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid") from exc
        if hashlib.sha256(raw).hexdigest() != entry["sha256"] or entry["sha256"] in result:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid")
        result[entry["sha256"]] = (entry, decode_usage_evidence(raw, params))
    return result


def validate_completed_sweeps(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], out: pathlib.Path) -> list[dict[str, object]]:
    entries = manifest.get("completed_sweeps", [])
    if not isinstance(entries, list):
        raise LaunchViolation("completed-sweep-entry-invalid")
    usage = usage_entries_by_digest(manifest, params)
    previous_sweep = 0
    failures: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != COMPLETED_SWEEP_FIELDS or type(entry.get("sweep_id")) is not int or not 1 <= entry["sweep_id"] <= schedule["sweeps"] or entry["sweep_id"] <= previous_sweep or not is_digest(entry.get("pre_sha256")) or not is_digest(entry.get("post_sha256")):
            raise LaunchViolation("completed-sweep-entry-invalid")
        pre_pair, post_pair = usage.get(entry["pre_sha256"]), usage.get(entry["post_sha256"])
        if pre_pair is None or post_pair is None:
            raise LaunchViolation("completed-sweep-provenance-invalid")
        pre_entry, pre = pre_pair
        post_entry, post = post_pair
        if pre_entry["role"] != "pre-sweep" or post_entry["role"] != "post-sweep" or pre_entry["sweep_id"] != entry["sweep_id"] or post_entry["sweep_id"] != entry["sweep_id"] or pre["reset_at"] != post["reset_at"]:
            raise LaunchViolation("completed-sweep-provenance-invalid")
        components = sum_receipts(out, entry.get("receipts"), completed_sweep_receipt_layout(out, manifest, schedule, entry["sweep_id"]))
        if entry.get("components") != components or entry.get("draw") != components["total"]:
            raise LaunchViolation("completed-sweep-entry-invalid")
        if not calibration_mix_ok(components, completed_sweep=True):
            failures.append(entry)
        previous_sweep = entry["sweep_id"]
    if manifest.get("terminal") == "CALIBRATION_UNIDENTIFIABLE":
        if not failures or failures[-1] != entries[-1]:
            raise LaunchViolation("completed-sweep-mix-terminal-invalid")
    elif failures:
        raise LaunchViolation("completed-sweep-mix-invalid")
    return entries


def validate_sweep_tpp_provenance(manifest: dict[str, object], params: dict[str, object]) -> None:
    usage = usage_entries_by_digest(manifest, params)
    for calibration in manifest.get("calibrations", []):
        if not isinstance(calibration, dict) or not isinstance(calibration.get("tpp_chain"), list):
            raise LaunchViolation("tpp-chain-invalid")
        for observation in calibration["tpp_chain"][1:]:
            if not isinstance(observation, dict):
                raise LaunchViolation("tpp-chain-invalid")
            pre_pair, post_pair = usage.get(observation.get("pre_sha256")), usage.get(observation.get("post_sha256"))
            if pre_pair is None or post_pair is None:
                raise LaunchViolation("tpp-chain-provenance-invalid")
            pre_entry, pre = pre_pair
            post_entry, post = post_pair
            if pre_entry["role"] != "pre-sweep" or post_entry["role"] != "post-sweep" or pre_entry["sweep_id"] != observation.get("sweep_id") or post_entry["sweep_id"] != observation.get("sweep_id") or pre["reset_at"] != post["reset_at"] or pre["reset_at"] != calibration.get("reset_at") or observation.get("delta_percent") != post["used_percent"] - pre["used_percent"]:
                raise LaunchViolation("tpp-chain-provenance-invalid")


def attempt_charge_valid(attempt: object) -> bool:
    if not calibration_attempt_shape_valid(attempt):
        return False
    try:
        parse_iso8601(str(attempt["started_at"]), "calibration-attempt-started-at")
    except LaunchViolation:
        return False
    units = attempt["units"]
    if any(not isinstance(unit, dict) or set(unit) != {"unit", "sessions", "receipts", "started_at"} or unit.get("unit") != number or not isinstance(unit.get("sessions"), list) or not isinstance(unit.get("receipts"), list) for number, unit in enumerate(units, 1)):
        return False
    try:
        return all(parse_iso8601(str(unit["started_at"]), "calibration-unit-started-at") >= parse_iso8601(str(attempt["started_at"]), "calibration-attempt-started-at") for unit in units) and attempt["session_equivalents"] == len(units) * len(CALIBRATION_ENGINES)
    except LaunchViolation:
        return False


def calibration_status(attempt: object, reset_at: str | None, params: dict[str, object]) -> str | None:
    """Return the first failed persisted-evidence predicate, in registered order."""
    if not isinstance(attempt, dict) or not isinstance(attempt.get("captures"), dict) or "P2" not in attempt["captures"]:
        return None
    if not pre_pair_valid(attempt, reset_at, params):
        return "abandoned:pre-pair-invalid"
    if not fable_witness(attempt, params):
        return "abandoned:fable-meter-moved"
    pairs = attempt.get("settlement_pairs")
    if not isinstance(pairs, list) or not pairs or not isinstance(pairs[-1], dict) or "S2" not in pairs[-1]:
        return None
    if not settlement_valid(attempt, reset_at, params):
        return "abandoned:settlement-invalid"
    return None


def calibration_attempt_valid(attempt: object, reset_at: str | None, out: pathlib.Path, params: dict[str, object]) -> None:
    if not attempt_charge_valid(attempt):
        raise LaunchViolation("calibration-attempt-invalid")
    captures = attempt["captures"]
    epoch = attempt["epoch"]
    if epoch is None:
        if captures.get("P1") is not None or captures.get("reset_at") is not None:
            raise LaunchViolation("calibration-attempt-epoch-invalid")
    elif reset_at != epoch or captures.get("reset_at") != epoch:
        raise LaunchViolation("calibration-attempt-epoch-invalid")
    if attempt["status"] == "abandoned:interrupted":
        # An interrupted prefix is an audit artifact, but its P1 epoch remains custody evidence.
        return
    if reset_at is None:
        if captures.get("reset_at") is not None or captures.get("P1") is not None:
            raise LaunchViolation("calibration-attempt-invalid")
    elif captures.get("reset_at") != reset_at:
        raise LaunchViolation("calibration-cross-epoch-invalid")
    if any(name not in {"P1", "P2", "reset_at"} for name in captures) or ("P2" in captures and "P1" not in captures):
        raise LaunchViolation("calibration-bracket-captures-invalid")
    for name in ("P1", "P2"):
        if name in captures:
            decode_capture(captures[name], params)
    units = attempt["units"]
    expected_units = (len(attempt["sessions"]) + len(CALIBRATION_ENGINES) - 1) // len(CALIBRATION_ENGINES)
    abandoned = str(attempt["status"]).startswith("abandoned:")
    empty_capture_unit = abandoned and len(units) == expected_units + 1 and isinstance(units[-1], dict) and units[-1].get("sessions") == [] and units[-1].get("receipts") == []
    if (len(units) != expected_units and not empty_capture_unit) or any(not isinstance(unit, dict) or set(unit) != {"unit", "sessions", "receipts", "started_at"} or unit.get("unit") != number or not isinstance(unit.get("sessions"), list) or not isinstance(unit.get("receipts"), list) for number, unit in enumerate(units, 1)):
        raise LaunchViolation("calibration-unit-invalid")
    if attempt["sessions"] != [label for unit in units for label in unit["sessions"]] or attempt["receipts"] != [receipt for unit in units for receipt in unit["receipts"]]:
        raise LaunchViolation("calibration-unit-invalid")
    for number, unit in enumerate(units, 1):
        start = (number - 1) * len(CALIBRATION_ENGINES)
        if unit["sessions"] != attempt["sessions"][start:start + len(CALIBRATION_ENGINES)]:
            raise LaunchViolation("calibration-unit-invalid")
    legacy = str(attempt["status"]).startswith("abandoned:venue-over-budget-20260902")
    expected_receipts = calibration_receipt_layout(attempt["sessions"], None if legacy else attempt["attempt_id"])
    receipt_layout = [(str(receipt.get("path")), str(receipt.get("engine"))) for receipt in attempt["receipts"] if isinstance(receipt, dict)]
    if len(receipt_layout) != len(attempt["receipts"]) or receipt_layout != expected_receipts[:len(receipt_layout)]:
        raise LaunchViolation("calibration-receipt-program-invalid")
    if attempt["receipts"]:
        sum_receipts(out, attempt["receipts"])
    commit = attempt["settlement_commit"]
    if commit is not None and (not isinstance(commit, dict) or set(commit) != {"calibration", "closure", "sweep", "closure_at"} or not isinstance(commit.get("calibration"), dict) or not isinstance(commit.get("closure"), dict) or type(commit.get("sweep")) is not int):
        raise LaunchViolation("calibration-settlement-commit-invalid")
    pairs = attempt["settlement_pairs"]
    if any(not isinstance(pair, dict) or set(pair) not in ({"unit", "S1", "S2"}, {"unit", "S1"}) or (set(pair) == {"unit", "S1"} and (not abandoned or pair is not pairs[-1])) or type(pair.get("unit")) is not int or not 1 <= pair["unit"] <= len(units) for pair in pairs) or [pair["unit"] for pair in pairs] != list(range(1, len(pairs) + 1)):
        raise LaunchViolation("calibration-bracket-captures-invalid")
    for pair in pairs:
        decode_capture(pair["S1"], params)
        if "S2" in pair:
            decode_capture(pair["S2"], params)
    classified = calibration_status(attempt, reset_at, params)
    status = attempt["status"]
    if status in {"open", "settled", "abandoned:venue-over-budget", "abandoned:venue-over-budget-20260902"}:
        if classified is not None:
            raise LaunchViolation("calibration-attempt-status-evidence-invalid")
    elif status != classified:
        raise LaunchViolation("calibration-attempt-status-evidence-invalid")


def calibration_entry_valid(entry: object, out: pathlib.Path, params: dict[str, object], manifest: dict[str, object], schedule: dict[str, object]) -> None:
    required = {"reset_at", "pre_capture", "settlement_captures", "sessions", "receipts", "components", "tpp_chain", "session_equivalents", "attempts"}
    if not isinstance(entry, dict) or set(entry) != required or not isinstance(entry.get("reset_at"), str) or not isinstance(entry.get("sessions"), list) or not isinstance(entry.get("receipts"), list) or not isinstance(entry.get("components"), dict) or not isinstance(entry.get("tpp_chain"), list) or type(entry.get("session_equivalents")) is not int or not isinstance(entry.get("attempts"), list):
        raise LaunchViolation("launch-manifest-calibration-invalid")
    parse_iso8601(entry["reset_at"], "calibration-reset-at")
    _pre_raw, pre = decode_capture(entry["pre_capture"], params)
    settlements = entry["settlement_captures"]
    if not isinstance(settlements, list) or len(settlements) != 2:
        raise LaunchViolation("calibration-settlement-invalid")
    _first_raw, first = decode_capture(settlements[0], params)
    _second_raw, second = decode_capture(settlements[1], params)
    if any(capture["reset_at"] != entry["reset_at"] for capture in (pre, first, second)):
        raise LaunchViolation("calibration-cross-epoch-invalid")
    first_time, second_time = parse_iso8601(first["observed_at"], "settlement-observed-at"), parse_iso8601(second["observed_at"], "settlement-observed-at")
    if first["used_percent"] != second["used_percent"] or second_time - first_time < datetime.timedelta(seconds=125):
        raise LaunchViolation("calibration-settlement-invalid")
    attempts = entry["attempts"]
    settled_attempt: dict[str, object] | None = None
    charged = 0
    seen_attempt_ids: set[int] = set()
    for attempt in attempts:
        if not isinstance(attempt, dict) or attempt.get("attempt_id") in seen_attempt_ids:
            raise LaunchViolation("calibration-attempt-invalid")
        seen_attempt_ids.add(int(attempt["attempt_id"]))
        calibration_attempt_valid(attempt, entry["reset_at"], out, params)
        charged += attempt["session_equivalents"]
        if attempt["status"] == "settled":
            if settled_attempt is not None:
                raise LaunchViolation("calibration-attempt-invalid")
            settled_attempt = attempt
    if settled_attempt is None or entry["sessions"] != settled_attempt["sessions"] or entry["receipts"] != settled_attempt["receipts"] or entry["session_equivalents"] != charged:
        raise LaunchViolation("calibration-session-accounting-invalid")
    captures = settled_attempt["captures"]
    pairs = settled_attempt["settlement_pairs"]
    if not all(name in captures for name in ("P1", "P2")) or not pairs or len(pairs) != len(settled_attempt["units"]):
        raise LaunchViolation("calibration-bracket-captures-invalid")
    _p1_raw, p1 = decode_capture(captures["P1"], params)
    _p2_raw, p2 = decode_capture(captures["P2"], params)
    p1_time = parse_iso8601(p1["observed_at"], "calibration-pre-pair-observed-at")
    p2_time = parse_iso8601(p2["observed_at"], "calibration-pre-pair-observed-at")
    if p1["reset_at"] != entry["reset_at"] or p2["reset_at"] != entry["reset_at"] or p1["used_percent"] != p2["used_percent"] or p2_time - p1_time < datetime.timedelta(seconds=600):
        raise LaunchViolation("calibration-pre-pair-invalid")
    final_pair = pairs[-1]
    _s1_raw, s1 = decode_capture(final_pair["S1"], params)
    _s2_raw, s2 = decode_capture(final_pair["S2"], params)
    if entry["settlement_captures"] != [final_pair["S1"], final_pair["S2"]] or s1["used_percent"] != s2["used_percent"]:
        raise LaunchViolation("calibration-settlement-invalid")
    components = sum_receipts(out, entry["receipts"], calibration_receipt_layout(entry["sessions"], settled_attempt["attempt_id"]))
    if entry["components"] != components or not calibration_mix_ok(components):
        raise LaunchViolation("calibration-mix-invalid")
    latest_receipt = max(parse_iso8601(str(receipt["completed_at"]), "calibration-receipt-completed-at") for receipt in entry["receipts"])
    if first_time < latest_receipt + datetime.timedelta(seconds=180):
        raise LaunchViolation("calibration-settlement-too-early")
    delta = second["used_percent"] - pre["used_percent"]
    if delta < 1:
        raise LaunchViolation("calibration-delta-unidentifiable")
    accounting = params["venue_tolerance"]["calibration"]["accounting"]
    if not 1 <= entry["session_equivalents"] <= accounting["epoch_session_cap"] or any(attempt["session_equivalents"] > accounting["attempt_session_cap"] for attempt in attempts):
        raise LaunchViolation("calibration-session-accounting-invalid")
    chain = entry["tpp_chain"]
    if not chain or not isinstance(chain[0], dict) or chain[0] != {"kind": "calibration", "pre_sha256": entry["pre_capture"]["sha256"], "post_sha256": settlements[-1]["sha256"], "receipt_digests": [receipt["sha256"] for receipt in entry["receipts"]], "components": components, "draw": components["total"], "delta_percent": delta, "tpp_obs": components["total"] // (delta + 1)}:
        raise LaunchViolation("tpp-chain-invalid")
    for observation in chain[1:]:
        if not isinstance(observation, dict) or set(observation) != {"kind", "sweep_id", "pre_sha256", "post_sha256", "receipts", "components", "draw", "delta_percent", "tpp_obs"} or observation.get("kind") != "sweep" or type(observation.get("sweep_id")) is not int or not is_digest(observation.get("pre_sha256")) or not is_digest(observation.get("post_sha256")) or type(observation.get("delta_percent")) is not int or observation["delta_percent"] < 1 or type(observation.get("tpp_obs")) is not int:
            raise LaunchViolation("tpp-chain-invalid")
        sweep_components = sum_receipts(out, observation["receipts"], completed_sweep_receipt_layout(out, manifest, schedule, observation["sweep_id"]))
        if observation.get("components") != sweep_components or observation.get("draw") != sweep_components["total"] or not calibration_mix_ok(sweep_components, completed_sweep=True) or observation["tpp_obs"] != sweep_components["total"] // (observation["delta_percent"] + 1):
            raise LaunchViolation("tpp-chain-invalid")
def account_consumption_times(manifest: dict[str, object]) -> list[datetime.datetime]:
    """Return every persisted account-consuming call, including partial attempts."""
    times: list[datetime.datetime] = []
    for _reset_at, attempt in manifest_calibration_attempts(manifest):
        captures = attempt.get("captures")
        pairs = attempt.get("settlement_pairs")
        units = attempt.get("units")
        if not isinstance(captures, dict) or not isinstance(pairs, list) or not isinstance(units, list):
            raise LaunchViolation("launch-manifest-calibrations-invalid")
        for unit in units:
            if not isinstance(unit, dict) or not isinstance(unit.get("started_at"), str):
                raise LaunchViolation("calibration-unit-started-at")
            times.extend([parse_iso8601(unit["started_at"], "calibration-unit-started-at")] * len(CALIBRATION_ENGINES))
        if attempt.get("status") == "abandoned:interrupted":
            continue
        for capture in captures.values():
            if isinstance(capture, dict):
                times.append(parse_iso8601(str(capture.get("consumed_at")), "calibration-capture-consumed-at"))
        for pair in pairs:
            if not isinstance(pair, dict):
                raise LaunchViolation("launch-manifest-calibrations-invalid")
            for capture in pair.values():
                if isinstance(capture, dict):
                    times.append(parse_iso8601(str(capture.get("consumed_at")), "calibration-capture-consumed-at"))
    settlements = manifest.get("settlements")
    if not isinstance(settlements, list):
        raise LaunchViolation("settlement-entry-invalid")
    for settlement in settlements:
        if not isinstance(settlement, dict) or not isinstance(settlement.get("captures"), list):
            raise LaunchViolation("settlement-entry-invalid")
        for capture in settlement["captures"]:
            if not isinstance(capture, dict):
                raise LaunchViolation("settlement-entry-invalid")
            times.append(parse_iso8601(str(capture.get("consumed_at")), "settlement-capture-consumed-at"))
    blocks = manifest.get("blocks")
    if not isinstance(blocks, dict):
        raise LaunchViolation("launch-manifest-blocks-invalid")
    for block in blocks.values():
        if not isinstance(block, dict) or not isinstance(block.get("attempts"), list):
            raise LaunchViolation("launch-manifest-blocks-invalid")
        for attempt in block["attempts"]:
            if not isinstance(attempt, dict) or not isinstance(attempt.get("sessions"), dict):
                raise LaunchViolation("launch-manifest-attempt-invalid")
            for status in attempt["sessions"].values():
                if not isinstance(status, dict):
                    raise LaunchViolation("launch-manifest-status-invalid")
                times.append(parse_iso8601(str(status.get("completed_at")), "launch-session-completed-at"))
    oracles = manifest.get("resume_oracles", [])
    if not isinstance(oracles, list):
        raise LaunchViolation("resume-oracle-manifest-invalid")
    for entry in oracles:
        if not isinstance(entry, dict) or not isinstance(entry.get("bytes_base64"), str):
            raise LaunchViolation("resume-oracle-manifest-invalid")
        try:
            oracle = json.loads(base64.b64decode(entry["bytes_base64"], validate=True))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise LaunchViolation("resume-oracle-manifest-invalid") from exc
        if not isinstance(oracle, dict) or not isinstance(oracle.get("probes"), list):
            raise LaunchViolation("resume-oracle-manifest-invalid")
        times.extend(parse_iso8601(str(probe.get("observed_at")), "resume-oracle-probe-observed-at") for probe in oracle["probes"] if isinstance(probe, dict))
    return times


def manifest_as_of(manifest: dict[str, object], at: datetime.datetime) -> dict[str, object]:
    """Return the append-only manifest state recorded no later than ``at``."""
    if not isinstance(manifest, dict) or not isinstance(at, datetime.datetime):
        raise LaunchViolation("manifest-as-of-invalid")
    at = at.astimezone(datetime.timezone.utc)

    def capture_observed_at(capture: object) -> datetime.datetime:
        if not isinstance(capture, dict) or not isinstance(capture.get("bytes_base64"), str):
            raise LaunchViolation("manifest-as-of-invalid")
        try:
            payload = json.loads(base64.b64decode(capture["bytes_base64"], validate=True))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise LaunchViolation("manifest-as-of-invalid") from exc
        if not isinstance(payload, dict):
            raise LaunchViolation("manifest-as-of-invalid")
        return parse_iso8601(str(payload.get("observed_at")), "manifest-as-of-observed-at")

    def latest_capture_at(entry: object, field: str) -> datetime.datetime:
        if not isinstance(entry, dict) or not isinstance(entry.get(field), list):
            raise LaunchViolation("manifest-as-of-invalid")
        captures = entry[field]
        if not captures:
            raise LaunchViolation("manifest-as-of-invalid")
        return max(capture_observed_at(capture) for capture in captures)

    evidence_at: dict[str, datetime.datetime] = {}
    for entry in manifest.get("usage_evidence", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("sha256"), str):
            raise LaunchViolation("manifest-as-of-invalid")
        evidence_at.setdefault(entry["sha256"], parse_iso8601(str(entry.get("consumed_at")), "manifest-as-of-usage-consumed-at"))
    for field, captures_field in (("calibrations", "settlement_captures"), ("settlements", "captures")):
        entries = manifest.get(field, [])
        if not isinstance(entries, list):
            raise LaunchViolation("manifest-as-of-invalid")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get(captures_field), list):
                raise LaunchViolation("manifest-as-of-invalid")
            for capture in entry[captures_field]:
                if not isinstance(capture, dict) or not isinstance(capture.get("sha256"), str):
                    raise LaunchViolation("manifest-as-of-invalid")
                evidence_at.setdefault(capture["sha256"], capture_observed_at(capture))
    for calibration in manifest.get("calibrations", []):
        if not isinstance(calibration, dict) or not isinstance(calibration.get("attempts"), list):
            raise LaunchViolation("manifest-as-of-invalid")
        for attempt in calibration["attempts"]:
            if not isinstance(attempt, dict) or not isinstance(attempt.get("captures"), dict):
                raise LaunchViolation("manifest-as-of-invalid")
            for capture in attempt["captures"].values():
                if isinstance(capture, dict) and isinstance(capture.get("sha256"), str):
                    evidence_at.setdefault(capture["sha256"], capture_observed_at(capture))
            pairs = attempt.get("settlement_pairs")
            if not isinstance(pairs, list):
                raise LaunchViolation("manifest-as-of-invalid")
            for pair in pairs:
                if not isinstance(pair, dict):
                    raise LaunchViolation("manifest-as-of-invalid")
                for name in ("S1", "S2"):
                    capture = pair.get(name)
                    if isinstance(capture, dict) and isinstance(capture.get("sha256"), str):
                        evidence_at.setdefault(capture["sha256"], capture_observed_at(capture))

    projected = dict(manifest)
    usage_entries = manifest.get("usage_evidence", [])
    if not isinstance(usage_entries, list):
        raise LaunchViolation("manifest-as-of-invalid")
    projected["usage_evidence"] = [entry for entry in usage_entries if isinstance(entry, dict) and evidence_at.get(entry.get("sha256"), at + datetime.timedelta(microseconds=1)) <= at]

    calibrations = manifest.get("calibrations", [])
    if not isinstance(calibrations, list):
        raise LaunchViolation("manifest-as-of-invalid")
    projected_calibrations: list[dict[str, object]] = []
    for calibration in calibrations:
        if not isinstance(calibration, dict) or not isinstance(calibration.get("attempts"), list):
            raise LaunchViolation("manifest-as-of-invalid")
        completed_at = [latest_capture_at(calibration, "settlement_captures")]
        for attempt in calibration["attempts"]:
            if not isinstance(attempt, dict) or not isinstance(attempt.get("receipts"), list) or any(not isinstance(receipt, dict) for receipt in attempt["receipts"]):
                raise LaunchViolation("manifest-as-of-invalid")
            completed_at.extend(parse_iso8601(str(receipt.get("completed_at")), "manifest-as-of-calibration-completed-at") for receipt in attempt["receipts"])
        if max(completed_at) > at:
            continue
        projected_calibration = dict(calibration)
        chain = calibration.get("tpp_chain")
        if isinstance(chain, list):
            projected_calibration["tpp_chain"] = [observation for observation in chain if not isinstance(observation, dict) or evidence_at.get(observation.get("post_sha256"), at + datetime.timedelta(microseconds=1)) <= at]
        projected_calibrations.append(projected_calibration)
    projected["calibrations"] = projected_calibrations
    ledger = manifest.get("calibration_ledger")
    if not isinstance(ledger, dict) or set(ledger) != {"epochs", "unassigned_attempts"} or not isinstance(ledger.get("epochs"), list) or not isinstance(ledger.get("unassigned_attempts"), list):
        raise LaunchViolation("manifest-as-of-invalid")

    def captured_before(capture: object) -> bool:
        return isinstance(capture, dict) and parse_iso8601(str(capture.get("consumed_at")), "manifest-as-of-capture-consumed-at") <= at

    def project_attempt(attempt: object) -> dict[str, object] | None:
        if not attempt_charge_valid(attempt):
            raise LaunchViolation("manifest-as-of-invalid")
        assert isinstance(attempt, dict)
        if parse_iso8601(str(attempt["started_at"]), "manifest-as-of-attempt-started-at") > at:
            return None
        projected_attempt = json.loads(json.dumps(attempt))
        units = [unit for unit in attempt["units"] if parse_iso8601(str(unit["started_at"]), "manifest-as-of-unit-started-at") <= at]
        receipts = [receipt for unit in units for receipt in unit["receipts"] if isinstance(receipt, dict) and parse_iso8601(str(receipt.get("completed_at")), "manifest-as-of-calibration-completed-at") <= at]
        captures = {name: capture for name, capture in attempt["captures"].items() if name != "reset_at" and captured_before(capture)}
        if "P1" in captures and "reset_at" in attempt["captures"]:
            captures["reset_at"] = attempt["captures"]["reset_at"]
        pairs: list[dict[str, object]] = []
        for pair in attempt["settlement_pairs"]:
            if not isinstance(pair, dict) or type(pair.get("unit")) is not int:
                raise LaunchViolation("manifest-as-of-invalid")
            projected_pair = {"unit": pair["unit"]}
            for name in ("S1", "S2"):
                if name in pair and captured_before(pair[name]):
                    projected_pair[name] = pair[name]
            if len(projected_pair) > 1:
                pairs.append(projected_pair)
        if not units and not captures and not pairs:
            return None
        projected_attempt["receipts"] = receipts
        projected_attempt["units"] = units
        projected_attempt["sessions"] = [label for unit in units for label in unit["sessions"]]
        projected_attempt["session_equivalents"] = len(units) * len(CALIBRATION_ENGINES)
        if projected_attempt["status"] == "abandoned:interrupted":
            projected_attempt.update({"captures": {}, "settlement_pairs": [], "receipts": []})
        else:
            projected_attempt["captures"] = captures
            projected_attempt["settlement_pairs"] = pairs
        return projected_attempt

    projected_epochs: list[dict[str, object]] = []
    for epoch in ledger["epochs"]:
        if not isinstance(epoch, dict) or not isinstance(epoch.get("reset_at"), str) or not isinstance(epoch.get("attempts"), list):
            raise LaunchViolation("manifest-as-of-invalid")
        attempts = [projected_attempt for attempt in epoch["attempts"] if (projected_attempt := project_attempt(attempt)) is not None]
        if attempts:
            projected_epochs.append({"reset_at": epoch["reset_at"], "attempts": attempts})
    projected_unassigned = [projected_attempt for attempt in ledger["unassigned_attempts"] if (projected_attempt := project_attempt(attempt)) is not None]
    projected["calibration_ledger"] = {"epochs": projected_epochs, "unassigned_attempts": projected_unassigned}
    projected["calibration_session_equivalents"] = sum(
        attempt["session_equivalents"]
        for _reset_at, attempt in manifest_calibration_attempts(projected)
        if type(attempt.get("session_equivalents")) is int
    )

    settlements = manifest.get("settlements", [])
    if not isinstance(settlements, list):
        raise LaunchViolation("manifest-as-of-invalid")
    projected["settlements"] = [entry for entry in settlements if isinstance(entry, dict) and latest_capture_at(entry, "captures") <= at]

    oracles = manifest.get("resume_oracles", [])
    if not isinstance(oracles, list):
        raise LaunchViolation("manifest-as-of-invalid")
    projected["resume_oracles"] = [entry for entry in oracles if isinstance(entry, dict) and parse_iso8601(str(entry.get("consumed_at")), "manifest-as-of-oracle-consumed-at") <= at]

    blocks = manifest.get("blocks")
    if not isinstance(blocks, dict):
        raise LaunchViolation("manifest-as-of-invalid")
    projected_blocks: dict[str, object] = {}
    for replicate_id, block in blocks.items():
        if not isinstance(block, dict) or not isinstance(block.get("attempts"), list):
            raise LaunchViolation("manifest-as-of-invalid")
        projected_block = dict(block)
        attempts: list[dict[str, object]] = []
        for attempt in block["attempts"]:
            if not isinstance(attempt, dict) or not isinstance(attempt.get("sessions"), dict):
                raise LaunchViolation("manifest-as-of-invalid")
            if any(not isinstance(status, dict) for status in attempt["sessions"].values()):
                raise LaunchViolation("manifest-as-of-invalid")
            projected_attempt = dict(attempt)
            projected_attempt["sessions"] = {
                label: status for label, status in attempt["sessions"].items()
                if parse_iso8601(str(status.get("completed_at")), "manifest-as-of-attempt-completed-at") <= at
            }
            attempts.append(projected_attempt)
        projected_block["attempts"] = attempts
        if projected_block.get("designated_attempt") not in {attempt.get("attempt_id") for attempt in attempts}:
            projected_block["designated_attempt"] = None
        projected_blocks[str(replicate_id)] = projected_block
    projected["blocks"] = projected_blocks

    receipts = manifest.get("closure_receipts", [])
    if not isinstance(receipts, list):
        raise LaunchViolation("manifest-as-of-invalid")
    projected["closure_receipts"] = [entry for entry in receipts if isinstance(entry, dict) and parse_iso8601(str(entry.get("consumed_at")), "manifest-as-of-closure-consumed-at") <= at]
    return projected


def settlement_entry_valid(entry: object, manifest: dict[str, object], params: dict[str, object]) -> None:
    if not isinstance(entry, dict) or set(entry) != SETTLEMENT_FIELDS or not isinstance(entry.get("reset_at"), str) or not isinstance(entry.get("captures"), list) or len(entry["captures"]) != 2:
        raise LaunchViolation("settlement-entry-invalid")
    parse_iso8601(entry["reset_at"], "settlement-reset-at")
    _first_raw, first = decode_capture(entry["captures"][0], params)
    _second_raw, second = decode_capture(entry["captures"][1], params)
    if first["reset_at"] != entry["reset_at"] or second["reset_at"] != entry["reset_at"]:
        raise LaunchViolation("settlement-cross-epoch-invalid")
    first_time = parse_iso8601(str(first["observed_at"]), "settlement-observed-at")
    second_time = parse_iso8601(str(second["observed_at"]), "settlement-observed-at")
    if first["used_percent"] != second["used_percent"] or second_time - first_time < datetime.timedelta(seconds=120):
        raise LaunchViolation("settlement-invalid")
    prior_calls = account_consumption_times(manifest_as_of(manifest, first_time))
    if prior_calls and first_time < max(prior_calls) + datetime.timedelta(seconds=180):
        raise LaunchViolation("settlement-too-early")
    selected = (parse_iso8601(str(entry["captures"][0]["consumed_at"]), "settlement-capture-consumed-at"), parse_iso8601(str(entry["captures"][1]["consumed_at"]), "settlement-capture-consumed-at"))
    if account_consumed_after(manifest_as_of(manifest, second_time), first_time, selected):
        raise LaunchViolation("settlement-too-early")


def latest_settlement(manifest: dict[str, object], reset_at: str, params: dict[str, object]) -> tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str, tuple[datetime.datetime, datetime.datetime]] | None:
    candidates: list[tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str, tuple[datetime.datetime, datetime.datetime]]] = []
    for calibration in manifest.get("calibrations", []):
        if not isinstance(calibration, dict) or calibration.get("reset_at") != reset_at:
            continue
        captures = calibration.get("settlement_captures")
        if not isinstance(captures, list) or len(captures) != 2:
            raise LaunchViolation("calibration-settlement-invalid")
        _first_raw, first = decode_capture(captures[0], params)
        _second_raw, second = decode_capture(captures[1], params)
        candidates.append((first, second, parse_iso8601(str(first["observed_at"]), "settlement-observed-at"), parse_iso8601(str(second["observed_at"]), "settlement-observed-at"), str(captures[1]["sha256"]), (parse_iso8601(str(captures[0]["consumed_at"]), "settlement-capture-consumed-at"), parse_iso8601(str(captures[1]["consumed_at"]), "settlement-capture-consumed-at"))))
    for entry in manifest.get("settlements", []):
        if not isinstance(entry, dict) or entry.get("reset_at") != reset_at:
            continue
        settlement_entry_valid(entry, manifest, params)
        first_capture, second_capture = entry["captures"]
        _first_raw, first = decode_capture(first_capture, params)
        _second_raw, second = decode_capture(second_capture, params)
        candidates.append((first, second, parse_iso8601(str(first["observed_at"]), "settlement-observed-at"), parse_iso8601(str(second["observed_at"]), "settlement-observed-at"), str(second_capture["sha256"]), (parse_iso8601(str(first_capture["consumed_at"]), "settlement-capture-consumed-at"), parse_iso8601(str(second_capture["consumed_at"]), "settlement-capture-consumed-at"))))
    return max(candidates, key=lambda candidate: candidate[3]) if candidates else None


def base_manifest(schedule_path: pathlib.Path, params_path: pathlib.Path, run_id: str, pin_sha: str, attestation: bytes) -> dict[str, object]:
    schedule, _params = load_inputs(schedule_path, params_path)
    return {"schema": "iter0112-launch-manifest-v5", "run_id": run_id, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "schedule_sha256": sha256(schedule_path), "params_sha256": sha256(params_path), "script_sha256": script_digests(), "scripts_sha256_pin_file": pin_sha, "window_attestation_sha256": hashlib.sha256(attestation).hexdigest(), "window_attestation_bytes_base64": base64.b64encode(attestation).decode(), "usage_evidence": [], "calibrations": [], "calibration_ledger": {"epochs": [], "unassigned_attempts": []}, "calibration_ledger_generation": 0, "settlements": [], "closure_receipts": [], "calendar": None, "calibration_session_equivalents": 0, "resume_oracles": [], "completed_sweeps": [], "blocks": {str(block["replicate_id"]): {"replicate_id": str(block["replicate_id"]), "attempts": [], "designated_attempt": None} for block in schedule["blocks"]}, "a5": {engine: {"a5_evaluated_attempt": None, "a5_evaluated_session": None, "a5_crossed": None} for engine in MATRIX_ENGINES}, "terminal": "RUNNING"}


def manifest_calibration_attempts(manifest: dict[str, object]) -> list[tuple[str | None, dict[str, object]]]:
    ledger = manifest.get("calibration_ledger")
    if not isinstance(ledger, dict) or set(ledger) != {"epochs", "unassigned_attempts"} or not isinstance(ledger.get("epochs"), list) or not isinstance(ledger.get("unassigned_attempts"), list):
        raise LaunchViolation("launch-manifest-calibration-ledger-invalid")
    result: list[tuple[str | None, dict[str, object]]] = []
    expected_count = 0
    for epoch in ledger["epochs"]:
        if not isinstance(epoch, dict) or set(epoch) != {"reset_at", "attempts"} or not isinstance(epoch.get("reset_at"), str) or not isinstance(epoch.get("attempts"), list):
            raise LaunchViolation("launch-manifest-calibration-ledger-invalid")
        expected_count += len(epoch["attempts"])
        for attempt in epoch["attempts"]:
            if not isinstance(attempt, dict):
                raise LaunchViolation("launch-manifest-calibration-ledger-invalid")
            result.append((epoch["reset_at"], attempt))
    expected_count += len(ledger["unassigned_attempts"])
    for attempt in ledger["unassigned_attempts"]:
        if not isinstance(attempt, dict):
            raise LaunchViolation("launch-manifest-calibration-ledger-invalid")
        result.append((None, attempt))
    if len(result) != expected_count:
        raise LaunchViolation("launch-manifest-calibration-ledger-invalid")
    return result


def validate_manifest_calibration_ledger(manifest: dict[str, object], out: pathlib.Path, params: dict[str, object]) -> int:
    attempts = manifest_calibration_attempts(manifest)
    accounting = params["venue_tolerance"]["calibration"]["accounting"]
    seen_ids: set[int] = set()
    reset_attempts: dict[str, list[dict[str, object]]] = {}
    for reset_at, attempt in attempts:
        calibration_attempt_valid(attempt, reset_at, out, params)
        if attempt["attempt_id"] in seen_ids:
            raise LaunchViolation("calibration-attempt-invalid")
        seen_ids.add(attempt["attempt_id"])
        if reset_at is None and not str(attempt["status"]).startswith("abandoned:"):
            raise LaunchViolation("calibration-attempt-invalid")
        if reset_at is not None:
            reset_attempts.setdefault(reset_at, []).append(attempt)
        if attempt["session_equivalents"] > accounting["attempt_session_cap"]:
            raise LaunchViolation("calibration-session-accounting-invalid")
    if any(sum(attempt["session_equivalents"] for attempt in epoch_attempts) > accounting["epoch_session_cap"] for epoch_attempts in reset_attempts.values()):
        raise LaunchViolation("calibration-session-accounting-invalid")
    calibrations = manifest.get("calibrations")
    if not isinstance(calibrations, list):
        raise LaunchViolation("launch-manifest-calibrations-invalid")
    for calibration in calibrations:
        analytical_attempts = [attempt for attempt in reset_attempts.get(str(calibration.get("reset_at")), []) if attempt.get("status") != "abandoned:interrupted"] if isinstance(calibration, dict) else []
        if not isinstance(calibration, dict) or not isinstance(calibration.get("reset_at"), str) or calibration.get("attempts") != analytical_attempts:
            raise LaunchViolation("calibration-ledger-manifest-mismatch")
    if any(any(attempt.get("status") == "settled" for attempt in epoch_attempts) and not any(isinstance(calibration, dict) and calibration.get("reset_at") == reset_at for calibration in calibrations) for reset_at, epoch_attempts in reset_attempts.items()):
        raise LaunchViolation("calibration-ledger-manifest-mismatch")
    return sum(attempt["session_equivalents"] for _reset, attempt in attempts)


def calibration_ledger_projection(ledger: dict[str, object]) -> dict[str, object]:
    epochs, abandoned = ledger.get("epochs"), ledger.get("abandoned_intents")
    if not isinstance(epochs, list) or not isinstance(abandoned, list):
        raise LaunchViolation("calibration-ledger-invalid")
    return {"epochs": json.loads(json.dumps(epochs)), "unassigned_attempts": json.loads(json.dumps(abandoned))}


def calibration_ledger_extends(previous: object, candidate: object) -> bool:
    if not isinstance(previous, dict) or not isinstance(candidate, dict) or set(previous) != {"epochs", "unassigned_attempts"} or set(candidate) != set(previous) or not isinstance(previous.get("epochs"), list) or not isinstance(candidate.get("epochs"), list) or not isinstance(previous.get("unassigned_attempts"), list) or not isinstance(candidate.get("unassigned_attempts"), list):
        return False
    if len(candidate["epochs"]) < len(previous["epochs"]) or len(candidate["unassigned_attempts"]) < len(previous["unassigned_attempts"]):
        return False
    if candidate["unassigned_attempts"][:len(previous["unassigned_attempts"])] != previous["unassigned_attempts"]:
        return False
    for index, prior_epoch in enumerate(previous["epochs"]):
        current_epoch = candidate["epochs"][index]
        if not isinstance(prior_epoch, dict) or not isinstance(current_epoch, dict) or prior_epoch.get("reset_at") != current_epoch.get("reset_at") or not isinstance(prior_epoch.get("attempts"), list) or not isinstance(current_epoch.get("attempts"), list) or len(current_epoch["attempts"]) < len(prior_epoch["attempts"]) or current_epoch["attempts"][:len(prior_epoch["attempts"])] != prior_epoch["attempts"]:
            return False
    return True


def sync_manifest_calibration_ledger(manifest: dict[str, object], ledger: dict[str, object]) -> None:
    if not isinstance(ledger.get("epochs"), list) or not isinstance(ledger.get("abandoned_intents"), list) or ledger.get("pending_attempt") is not None:
        raise LaunchViolation("calibration-ledger-invalid")
    manifest["calibration_ledger"] = calibration_ledger_projection(ledger)
    by_reset = {str(epoch["reset_at"]): epoch["attempts"] for epoch in ledger["epochs"] if isinstance(epoch, dict) and isinstance(epoch.get("reset_at"), str) and isinstance(epoch.get("attempts"), list)}
    calibrations = manifest.get("calibrations")
    if not isinstance(calibrations, list):
        raise LaunchViolation("launch-manifest-calibrations-invalid")
    for calibration in calibrations:
        if not isinstance(calibration, dict) or not isinstance(calibration.get("reset_at"), str) or calibration["reset_at"] not in by_reset:
            raise LaunchViolation("calibration-ledger-manifest-mismatch")
        calibration["attempts"] = json.loads(json.dumps([attempt for attempt in by_reset[calibration["reset_at"]] if attempt.get("status") != "abandoned:interrupted"]))
        calibration["session_equivalents"] = sum(attempt["session_equivalents"] for attempt in calibration["attempts"] if isinstance(attempt, dict) and type(attempt.get("session_equivalents")) is int)
    manifest["calibration_session_equivalents"] = sum(attempt["session_equivalents"] for _reset, attempt in manifest_calibration_attempts(manifest))


def persist_calibration_state(out: pathlib.Path, manifest: dict[str, object], ledger: dict[str, object]) -> None:
    """Advance the ledger generation before atomically publishing its manifest pointer."""
    sync_manifest_calibration_ledger(manifest, ledger)
    write_calibration_ledger(out, ledger)
    manifest["calibration_ledger_generation"] = ledger["generation"]
    write_json(out / MANIFEST_NAME, manifest)


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
    parse_iso8601(str(status.get("completed_at")), f"launch-manifest-status-completed-at:{label}")
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


def validate_manifest(manifest: dict[str, object], schedule: dict[str, object], out: pathlib.Path, run_id: str, params: dict[str, object]) -> None:
    evidence_entries = manifest.get("usage_evidence")
    calibrations = manifest.get("calibrations")
    settlements = manifest.get("settlements")
    if not isinstance(evidence_entries, list) or not isinstance(calibrations, list) or not isinstance(settlements, list) or type(manifest.get("calibration_ledger_generation")) is not int or manifest["calibration_ledger_generation"] < 0 or not isinstance(manifest.get("closure_receipts"), list) or not isinstance(manifest.get("resume_oracles"), list):
        raise LaunchViolation("launch-manifest-evidence-invalid")
    for calibration in calibrations:
        calibration_entry_valid(calibration, out, params, manifest, schedule)
    for settlement in settlements:
        settlement_entry_valid(settlement, manifest, params)
    charged_calibrations = validate_manifest_calibration_ledger(manifest, out, params)
    if type(manifest.get("calibration_session_equivalents")) is not int or manifest["calibration_session_equivalents"] != charged_calibrations or manifest["calibration_session_equivalents"] > params["venue_tolerance"]["calibration"]["accounting"]["root_session_cap"]:
        raise LaunchViolation("calibration-session-accounting-invalid")
    reset_epochs = [calibration["reset_at"] for calibration in calibrations]
    if len(set(reset_epochs)) != len(reset_epochs):
        raise LaunchViolation("calibration-cross-epoch-invalid")
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
        decoded_evidence = decode_usage_evidence(evidence, params)
        validate_usage_consumption(decoded_evidence, parse_iso8601(str(entry["consumed_at"]), "usage-consumed-at"), params)
        consumed.add(entry["sha256"])
    validate_sweep_tpp_provenance(manifest, params)
    validate_completed_sweeps(manifest, schedule, params, out)
    validate_closure_receipts(manifest, schedule, params, out)
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
    if not isinstance(manifest, dict) or manifest.get("schema") != "iter0112-launch-manifest-v5":
        raise LaunchViolation("launch-manifest-schema-mismatch")
    expected = base_manifest(schedule_path, params_path, run_id, pin_sha, attestation)
    for field in ("run_id", "schedule_sha256", "params_sha256", "script_sha256", "scripts_sha256_pin_file", "window_attestation_sha256", "window_attestation_bytes_base64"):
        if manifest.get(field) != expected[field]:
            raise LaunchViolation(f"launch-manifest-{field}-mismatch")
    schedule, _params = load_inputs(schedule_path, params_path)
    ledger = load_calibration_ledger(out, run_id, schedule_path, params_path, pin_sha)
    manifest_generation = manifest.get("calibration_ledger_generation")
    if type(manifest_generation) is not int or manifest_generation < 0 or ledger["generation"] < manifest_generation:
        raise LaunchViolation("calibration-ledger-manifest-mismatch")
    if ledger["generation"] == manifest_generation and manifest.get("calibration_ledger") != calibration_ledger_projection(ledger):
        raise LaunchViolation("calibration-ledger-manifest-mismatch")
    recover_open_calibration_attempts(out, ledger, _params)
    if not publish_settlement_commits(out, manifest, ledger, schedule, _params):
        sync_manifest_calibration_ledger(manifest, ledger)
        manifest["calibration_ledger_generation"] = ledger["generation"]
        write_json(out / MANIFEST_NAME, manifest)
    refresh_designations(manifest, schedule)
    validate_manifest(manifest, schedule, out, run_id, _params)
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
    status: dict[str, object] = {"engine": session["engine"], "replicate_id": session["replicate_id"], "session_label": session_key(session), "driver_command": command, "collector_command": collector_command, "driver_exit": driver.returncode, "driver_stdout_sha256": hashlib.sha256(driver.stdout).hexdigest(), "driver_stderr_sha256": hashlib.sha256(driver.stderr).hexdigest(), "driver_evidence_sha256": None, "status": "driver_failed", "collector_exit": None, "collector_stdout_sha256": None, "collector_stderr_sha256": None, "infra_affected": False, "a5_clean": False, "first_late_threshold_crossed": None, "rows_sha256": None, "boundary_ledger_sha256": None, "artifact_dir": str(directory.relative_to(out)), "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
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
    calendar = manifest.get("calendar")
    if calendar is None:
        return False
    if not isinstance(calendar, dict) or type(calendar.get("root_age_hours")) is not int:
        raise LaunchViolation("calendar-pinned-invalid")
    return datetime.datetime.now(datetime.timezone.utc) >= created + datetime.timedelta(hours=calendar["root_age_hours"])


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
    consumed_at = datetime.datetime.now(datetime.timezone.utc)
    pending = {"sha256": digest, "bytes_base64": base64.b64encode(raw).decode(), "role": role, "sweep_id": sweep, "consumed_at": consumed_at.isoformat()}
    manifest["usage_evidence"].append(pending)
    calendar = manifest.get("calendar")
    maximum_transitions = params["venue_tolerance"]["calendar"].get("W_max") if calendar is None else calendar.get("max_reset_epochs") if isinstance(calendar, dict) else None
    if type(maximum_transitions) is not int:
        raise LaunchViolation("calendar-pinned-invalid")
    try:
        verify_reset_timeline(full_timeline(manifest, params), maximum_transitions)
    except BaseException:
        manifest["usage_evidence"].pop()
        raise


def expected_probe_argv(params: dict[str, object], engine: str) -> list[str]:
    command = params["venue_tolerance"]["resume_oracle"].get("probe_command")
    if not isinstance(command, list) or command.count("<engine>") != 1 or not all(isinstance(value, str) for value in command):
        raise LaunchViolation("resume-oracle-probe-command-invalid")
    return [engine if value == "<engine>" else value for value in command]


def load_resume_oracle(path: pathlib.Path, usage_digest: str, params: dict[str, object]) -> tuple[bytes, str, int, list[datetime.datetime]]:
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
    observed_times: list[datetime.datetime] = []
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
        observed_times.append(finished)
    return raw, hashlib.sha256(raw).hexdigest(), len(ordered), observed_times


def consumed_probe_calls(manifest: dict[str, object]) -> int:
    entries = manifest.get("resume_oracles")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) or set(entry) != RESUME_ORACLE_ENTRY_FIELDS or type(entry.get("probe_calls")) is not int or entry["probe_calls"] < 0 for entry in entries):
        raise LaunchViolation("resume-oracle-manifest-invalid")
    return sum(entry["probe_calls"] for entry in entries)


def account_consumed_after(manifest: dict[str, object], observed_at: datetime.datetime, settlement_call_times: tuple[datetime.datetime, datetime.datetime]) -> bool:
    """Subtract exactly one selected event per settlement capture, never all equal timestamps."""
    selected = {time: settlement_call_times.count(time) for time in settlement_call_times}
    for time in account_consumption_times(manifest):
        if time <= observed_at:
            continue
        if selected.get(time, 0):
            selected[time] -= 1
            continue
        return True
    return False


def validate_settlement_admission(manifest: dict[str, object], usage: dict[str, object], params: dict[str, object], probe_times: list[datetime.datetime]) -> None:
    settlement = latest_settlement(manifest, str(usage["reset_at"]), params)
    if settlement is None:
        raise LaunchViolation("fresh-settlement-required")
    _first, second, first_observed, second_observed, _settlement_digest, settlement_call_times = settlement
    observed_at = parse_iso8601(str(usage["observed_at"]), "usage-evidence-observed-at")
    if str(usage["reset_at"]) != str(second["reset_at"]) or usage["used_percent"] != second["used_percent"] or observed_at <= second_observed:
        raise LaunchViolation("settlement-stale")
    if any(probe_time >= first_observed for probe_time in probe_times):
        raise LaunchViolation("resume-probe-after-settlement")
    if account_consumed_after(manifest, first_observed, settlement_call_times):
        raise LaunchViolation("fresh-settlement-required")


def calibration_command(engine: str, label: str, root: pathlib.Path, run_id: str) -> list[str]:
    return [sys.executable, str(DRIVER), "--engine", engine, "--session-label", label, "--tasks", ",".join(CALIBRATION_TASKS), "--replicate", "1", "--out", str(root), "--run-id", run_id, "--smoke"]


def run_calibration_batch(out: pathlib.Path, run_id: str, unit: int, attempt_id: int | None = None, ledger: dict[str, object] | None = None, attempt: dict[str, object] | None = None) -> tuple[list[str], list[dict[str, object]]]:
    root = out / "calibration"
    sessions: list[str] = []
    receipts: list[dict[str, object]] = []
    unit_record: dict[str, object] | None = None
    if attempt is not None:
        if ledger is None or not isinstance(attempt.get("units"), list):
            raise LaunchViolation("calibration-ledger-invalid")
        unit_record = {"unit": unit, "sessions": [], "receipts": [], "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        attempt["units"].append(unit_record)
        attempt["session_equivalents"] = len(attempt["units"]) * len(CALIBRATION_ENGINES)
        write_calibration_ledger(out, ledger)
    for engine in CALIBRATION_ENGINES:
        label = f"calibration-{unit}-{engine}" if attempt_id is None else f"calibration-a{attempt_id}-u{unit}-{engine}"
        command = calibration_command(engine, label, root, run_id)
        if attempt is not None:
            attempt["sessions"].append(label)
            assert unit_record is not None
            unit_record["sessions"].append(label)
        completed = subprocess.run(command, cwd=REPO, capture_output=True)
        if completed.returncode:
            raise LaunchViolation("calibration-session-failed")
        directory = root / f"{engine}.{label}.r1"
        parse_session_dir(completed.stdout, directory)
        for position, task in enumerate(CALIBRATION_TASKS, 1):
            path = directory / f"t{position}.{task}" / "cli.stdout"
            try:
                raw = path.read_bytes()
                token_components(json.loads(raw), engine)
            except (OSError, json.JSONDecodeError, LaunchViolation) as exc:
                raise LaunchViolation("calibration-receipt-invalid") from exc
            receipts.append({"path": str(path.relative_to(out)), "sha256": hashlib.sha256(raw).hexdigest(), "engine": engine, "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
        sessions.append(label)
        if attempt is not None:
            session_receipts = receipts[-len(CALIBRATION_TASKS):]
            attempt["receipts"].extend(session_receipts)
            assert unit_record is not None
            unit_record["receipts"].extend(session_receipts)
    return sessions, receipts


def pending_path(out: pathlib.Path) -> pathlib.Path:
    return out / CALIBRATION_PENDING_NAME


def calibration_ledger_path(out: pathlib.Path) -> pathlib.Path:
    return out / CALIBRATION_LEDGER_NAME


def empty_calibration_ledger(run_id: str, schedule_path: pathlib.Path, params_path: pathlib.Path, pin: str) -> dict[str, object]:
    return {
        "schema": "iter0112-calibration-ledger-v3",
        "run_id": run_id,
        "schedule_sha256": sha256(schedule_path),
        "params_sha256": sha256(params_path),
        "pin_sha256": pin,
        "generation": 0,
        "pending_attempt": None,
        "abandoned_intents": [],
        "epochs": [],
    }


def load_calibration_ledger(out: pathlib.Path, run_id: str, schedule_path: pathlib.Path, params_path: pathlib.Path, pin: str) -> dict[str, object]:
    path = calibration_ledger_path(out)
    expected = empty_calibration_ledger(run_id, schedule_path, params_path, pin)
    if not path.exists():
        return expected
    ledger = read_json(path)
    if not isinstance(ledger, dict) or set(ledger) != set(expected) or any(ledger.get(key) != expected[key] for key in ("schema", "run_id", "schedule_sha256", "params_sha256", "pin_sha256")) or type(ledger.get("generation")) is not int or ledger["generation"] < 0 or ledger.get("pending_attempt") is not None and not isinstance(ledger.get("pending_attempt"), dict) or not isinstance(ledger.get("abandoned_intents"), list) or not isinstance(ledger.get("epochs"), list):
        raise LaunchViolation("calibration-ledger-invalid")
    seen_resets: set[str] = set()
    seen_attempts: set[int] = set()
    for epoch in ledger["epochs"]:
        if not isinstance(epoch, dict) or set(epoch) != {"reset_at", "attempts"} or not isinstance(epoch.get("reset_at"), str) or epoch["reset_at"] in seen_resets or not isinstance(epoch.get("attempts"), list):
            raise LaunchViolation("calibration-ledger-invalid")
        parse_iso8601(epoch["reset_at"], "calibration-ledger-reset-at")
        seen_resets.add(epoch["reset_at"])
        for attempt in epoch["attempts"]:
            if not calibration_attempt_shape_valid(attempt) or attempt["attempt_id"] in seen_attempts or attempt["epoch"] != epoch["reset_at"] or attempt["captures"].get("reset_at") != epoch["reset_at"]:
                raise LaunchViolation("calibration-ledger-invalid")
            seen_attempts.add(attempt["attempt_id"])
    for attempt in ledger["abandoned_intents"]:
        if not calibration_attempt_shape_valid(attempt) or attempt["attempt_id"] in seen_attempts or attempt["epoch"] is not None or attempt["captures"].get("reset_at") is not None or not str(attempt.get("status")).startswith("abandoned:"):
            raise LaunchViolation("calibration-ledger-invalid")
        seen_attempts.add(attempt["attempt_id"])
    pending = ledger.get("pending_attempt")
    if pending is not None and (not calibration_attempt_shape_valid(pending) or pending["attempt_id"] in seen_attempts):
        raise LaunchViolation("calibration-ledger-invalid")
    return ledger


def write_calibration_ledger(out: pathlib.Path, ledger: dict[str, object]) -> None:
    if type(ledger.get("generation")) is not int or ledger["generation"] < 0:
        raise LaunchViolation("calibration-ledger-invalid")
    ledger["generation"] += 1
    write_json(calibration_ledger_path(out), ledger)


def calibration_attempt_shape_valid(attempt: object) -> bool:
    return isinstance(attempt, dict) and set(attempt) == CALIBRATION_ATTEMPT_FIELDS and type(attempt.get("attempt_id")) is int and attempt["attempt_id"] > 0 and isinstance(attempt.get("status"), str) and isinstance(attempt.get("started_at"), str) and (attempt.get("epoch") is None or isinstance(attempt.get("epoch"), str)) and isinstance(attempt.get("captures"), dict) and isinstance(attempt.get("units"), list) and isinstance(attempt.get("settlement_pairs"), list) and isinstance(attempt.get("sessions"), list) and isinstance(attempt.get("receipts"), list) and type(attempt.get("session_equivalents")) is int and (attempt.get("settlement_commit") is None or isinstance(attempt.get("settlement_commit"), dict))


def ledger_attempts(ledger: dict[str, object]) -> list[dict[str, object]]:
    epochs = ledger.get("epochs")
    if not isinstance(epochs, list):
        raise LaunchViolation("calibration-ledger-invalid")
    unassigned = ledger.get("abandoned_intents")
    if not isinstance(unassigned, list):
        raise LaunchViolation("calibration-ledger-invalid")
    return [attempt for epoch in epochs if isinstance(epoch, dict) and isinstance(epoch.get("attempts"), list) for attempt in epoch["attempts"] if isinstance(attempt, dict)] + [attempt for attempt in unassigned if isinstance(attempt, dict)]


def ledger_epoch(ledger: dict[str, object], reset_at: str, create: bool = False) -> dict[str, object] | None:
    epochs = ledger.get("epochs")
    if not isinstance(epochs, list):
        raise LaunchViolation("calibration-ledger-invalid")
    found = next((epoch for epoch in epochs if isinstance(epoch, dict) and epoch.get("reset_at") == reset_at), None)
    if found is None and create:
        found = {"reset_at": reset_at, "attempts": []}
        epochs.append(found)
    return found


def next_calibration_attempt_id(ledger: dict[str, object]) -> int:
    pending = ledger.get("pending_attempt")
    attempts = ledger_attempts(ledger)
    if isinstance(pending, dict):
        attempts.append(pending)
    return max((int(attempt["attempt_id"]) for attempt in attempts), default=0) + 1


def import_pending_attempt(out: pathlib.Path, ledger: dict[str, object], params: dict[str, object]) -> None:
    """Preserve the A4 partial draw as charged, never as a fabricated bracket."""
    path = pending_path(out)
    if not path.exists():
        return
    pending = load_pending_calibration(out)
    _raw, pre = decode_capture(pending["pre_capture"], params)
    sessions, receipts = pending["sessions"], pending["receipts"]
    if not isinstance(sessions, list) or not isinstance(receipts, list) or len(sessions) != 6 or int(pending["unit"]) != 2:
        raise LaunchViolation("calibration-pending-import-invalid")
    sum_receipts(out, receipts, calibration_receipt_layout(sessions))
    reset_at = str(pre["reset_at"])
    try:
        imported_started_at = parse_iso8601(str(pending["pre_capture"]["consumed_at"]), "calibration-pending-started-at").isoformat()
    except (KeyError, TypeError, LaunchViolation) as exc:
        raise LaunchViolation("calibration-pending-import-invalid") from exc
    imported = {
        "attempt_id": 1,
        "status": "abandoned:venue-over-budget-20260902",
        "started_at": imported_started_at,
        "epoch": reset_at,
        "captures": {"P1": pending["pre_capture"], "reset_at": reset_at},
        "units": [
            {"unit": unit, "sessions": sessions[(unit - 1) * len(CALIBRATION_ENGINES):unit * len(CALIBRATION_ENGINES)], "receipts": receipts[(unit - 1) * len(CALIBRATION_ENGINES) * len(CALIBRATION_TASKS):unit * len(CALIBRATION_ENGINES) * len(CALIBRATION_TASKS)], "started_at": imported_started_at}
            for unit in range(1, 3)
        ],
        "settlement_pairs": [],
        "sessions": sessions,
        "receipts": receipts,
        "session_equivalents": len(sessions),
        "settlement_commit": None,
    }
    matching = [attempt for attempt in ledger_attempts(ledger) if isinstance(attempt, dict) and all(attempt.get(field) == imported[field] for field in CALIBRATION_ATTEMPT_FIELDS - {"attempt_id"})]
    if matching:
        if len(matching) != 1:
            raise LaunchViolation("calibration-pending-ledger-conflict")
        path.unlink()
        return
    if ledger_attempts(ledger) or ledger.get("pending_attempt") is not None:
        raise LaunchViolation("calibration-pending-ledger-conflict")
    epoch = ledger_epoch(ledger, reset_at, create=True)
    assert epoch is not None
    imported["attempt_id"] = next_calibration_attempt_id(ledger)
    attempt = imported
    epoch["attempts"].append(attempt)
    write_calibration_ledger(out, ledger)
    path.unlink()


def capture_from_launcher(out: pathlib.Path, sequence: int, label: str, params: dict[str, object]) -> tuple[bytes, dict[str, object], str, dict[str, object]]:
    verify_script_inventory()
    prefix = out / "captures" / f"{sequence:04d}-{label}"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run([sys.executable, str(USAGE_CAPTURE), "--out", str(prefix)], cwd=REPO, capture_output=True)
    if completed.returncode:
        raise LaunchViolation("calibration-capture-failed")
    evidence_path = pathlib.Path(f"{prefix}.json")
    raw, evidence, digest = load_usage_evidence(evidence_path, params)
    return raw, evidence, digest, capture_entry(raw, digest)


def fable_witness(attempt: object, params: dict[str, object]) -> bool:
    values: list[int | None] = []
    if not isinstance(attempt, dict) or not isinstance(attempt.get("captures"), dict) or not isinstance(attempt.get("settlement_pairs"), list):
        return False
    entries = [entry for name, entry in attempt["captures"].items() if name != "reset_at"]
    for pair in attempt["settlement_pairs"]:
        if not isinstance(pair, dict):
            return False
        entries.extend(entry for name, entry in pair.items() if name != "unit")
    for entry in entries:
        try:
            _raw, evidence = decode_capture(entry, params)
        except LaunchViolation:
            return False
        value = evidence["auxiliary"]["current_week_fable_percent"]
        if value is not None and type(value) is not int:
            return False
        values.append(value)
    return not values or all(value == values[0] for value in values)


def pre_pair_valid(attempt: object, reset_at: str | None, params: dict[str, object]) -> bool:
    if reset_at is None or not isinstance(attempt, dict) or not isinstance(attempt.get("captures"), dict):
        return False
    captures = attempt["captures"]
    if "P1" not in captures or "P2" not in captures:
        return False
    try:
        _p1_raw, p1 = decode_capture(captures["P1"], params)
        _p2_raw, p2 = decode_capture(captures["P2"], params)
    except LaunchViolation:
        return False
    return p1["reset_at"] == reset_at and p2["reset_at"] == reset_at and p1["reset_at"] == p2["reset_at"] and p1["used_percent"] == p2["used_percent"]


def settlement_valid(attempt: object, reset_at: str | None, params: dict[str, object]) -> bool:
    if reset_at is None or not isinstance(attempt, dict) or not isinstance(attempt.get("settlement_pairs"), list):
        return False
    pairs = attempt["settlement_pairs"]
    if not pairs:
        return False
    for pair in pairs:
        if not isinstance(pair, dict) or "S1" not in pair:
            return False
        try:
            _s1_raw, s1 = decode_capture(pair["S1"], params)
        except LaunchViolation:
            return False
        if "S2" not in pair:
            return False
        try:
            _s2_raw, s2 = decode_capture(pair["S2"], params)
        except LaunchViolation:
            return False
        if s1["reset_at"] != reset_at or s2["reset_at"] != reset_at or s1["reset_at"] != s2["reset_at"] or s1["used_percent"] != s2["used_percent"]:
            return False
    return True


def full_timeline(manifest: dict[str, object], params: dict[str, object]) -> list[tuple[datetime.datetime, datetime.datetime, dict[str, object]]]:
    """The one custody timeline: every recorded attempt epoch, manifest usage, settlements."""
    timeline: list[tuple[datetime.datetime, datetime.datetime, dict[str, object]]] = []
    for ledger_epoch_at, attempt in manifest_calibration_attempts(manifest):
        if not isinstance(attempt.get("captures"), dict):
            raise LaunchViolation("launch-manifest-calibrations-invalid")
        epoch = attempt.get("epoch")
        captures = attempt["captures"]
        if epoch is None:
            if captures.get("P1") is not None or captures.get("reset_at") is not None:
                raise LaunchViolation("calibration-attempt-epoch-invalid")
            continue
        p1 = captures.get("P1")
        if not isinstance(p1, dict):
            raise LaunchViolation("calibration-attempt-epoch-invalid")
        _p1_raw, p1_evidence = decode_capture(p1, params)
        if ledger_epoch_at != epoch or p1_evidence["reset_at"] != epoch or captures.get("reset_at") != epoch:
            raise LaunchViolation("calibration-attempt-epoch-invalid")
        for capture in attempt["captures"].values():
            if isinstance(capture, dict):
                _raw, evidence = decode_capture(capture, params)
                timeline.append((parse_iso8601(str(capture["consumed_at"]), "calibration-capture-consumed-at"), parse_iso8601(str(evidence["observed_at"]), "usage-observed-at"), evidence))
        pairs = attempt.get("settlement_pairs")
        if not isinstance(pairs, list):
            raise LaunchViolation("launch-manifest-calibrations-invalid")
        for pair in pairs:
            if not isinstance(pair, dict):
                raise LaunchViolation("launch-manifest-calibrations-invalid")
            for name in ("S1", "S2"):
                capture = pair.get(name)
                if capture is None and str(attempt.get("status", "")).startswith("abandoned:"):
                    continue
                if not isinstance(capture, dict):
                    raise LaunchViolation("launch-manifest-calibrations-invalid")
                _raw, evidence = decode_capture(capture, params)
                timeline.append((parse_iso8601(str(capture["consumed_at"]), "calibration-capture-consumed-at"), parse_iso8601(str(evidence["observed_at"]), "usage-observed-at"), evidence))
    for entry in manifest.get("usage_evidence", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("bytes_base64"), str):
            raise LaunchViolation("launch-manifest-usage-evidence-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid") from exc
        evidence = decode_usage_evidence(raw, params)
        timeline.append((parse_iso8601(str(entry.get("consumed_at")), "usage-consumed-at"), parse_iso8601(str(evidence["observed_at"]), "usage-observed-at"), evidence))
    for settlement in manifest.get("settlements", []):
        if not isinstance(settlement, dict) or not isinstance(settlement.get("captures"), list):
            raise LaunchViolation("settlement-entry-invalid")
        for capture in settlement["captures"]:
            _raw, evidence = decode_capture(capture, params)
            timeline.append((parse_iso8601(str(capture["consumed_at"]), "settlement-capture-consumed-at"), parse_iso8601(str(evidence["observed_at"]), "usage-observed-at"), evidence))
    return timeline


def verify_reset_timeline(timeline: list[tuple[datetime.datetime, datetime.datetime, dict[str, object]]], max_reset_epochs: int) -> None:
    prior_reset: str | None = None
    prior_used: int | None = None
    seen_resets: set[str] = set()
    reset_transitions = 0
    for _consumed, _observed, evidence in sorted(timeline, key=lambda value: value[:2]):
        reset_at = str(evidence["reset_at"])
        if prior_reset is None:
            prior_reset, prior_used = reset_at, int(evidence["used_percent"])
            seen_resets.add(reset_at)
        elif reset_at == prior_reset:
            if int(evidence["used_percent"]) < prior_used:
                raise LaunchViolation("usage-evidence-nonmonotone")
            prior_used = int(evidence["used_percent"])
        else:
            if reset_at in seen_resets:
                raise LaunchViolation("usage-evidence-reset-reused-old")
            if int(evidence["used_percent"]) > prior_used:
                raise LaunchViolation("usage-evidence-reset-with-rise")
            reset_transitions += 1
            if reset_transitions > max_reset_epochs:
                raise LaunchViolation("usage-evidence-reset-epochs-exceeded")
            prior_reset, prior_used = reset_at, int(evidence["used_percent"])
            seen_resets.add(reset_at)


def calibration_attempt_by_id(ledger: dict[str, object], attempt_id: int) -> dict[str, object] | None:
    pending = ledger.get("pending_attempt")
    if isinstance(pending, dict) and pending.get("attempt_id") == attempt_id:
        return pending
    return next((attempt for attempt in ledger_attempts(ledger) if attempt.get("attempt_id") == attempt_id), None)


def capture_bracket_slot(out: pathlib.Path, ledger: dict[str, object], attempt: dict[str, object], slot: str, label: str, params: dict[str, object], pair: dict[str, object] | None = None) -> tuple[dict[str, object], dict[str, object]]:
    sequence = 1 + sum(1 for _path in (out / "captures").glob("*.json")) if (out / "captures").exists() else 1
    _raw, evidence, _digest, entry = capture_from_launcher(out, sequence, label, params)
    if pair is None:
        attempt["captures"][slot] = entry
        if slot == "P1":
            attempt["captures"]["reset_at"] = evidence["reset_at"]
            attempt["epoch"] = evidence["reset_at"]
    else:
        pair[slot] = entry
    write_calibration_ledger(out, ledger)
    return evidence, entry


def recover_open_calibration_attempts(out: pathlib.Path, ledger: dict[str, object], params: dict[str, object]) -> None:
    pending = ledger.get("pending_attempt")
    if isinstance(pending, dict):
        pending["status"] = "abandoned:interrupted"
        epoch = pending.get("epoch")
        if epoch is None:
            ledger["abandoned_intents"].append(pending)
        else:
            target = ledger_epoch(ledger, epoch, create=True)
            assert target is not None
            target["attempts"].append(pending)
        ledger["pending_attempt"] = None
        write_calibration_ledger(out, ledger)
    for epoch in ledger.get("epochs", []):
        if not isinstance(epoch, dict) or not isinstance(epoch.get("attempts"), list):
            raise LaunchViolation("calibration-ledger-invalid")
        for attempt in epoch["attempts"]:
            if not isinstance(attempt, dict) or attempt.get("status") == "settled" or str(attempt.get("status", "")).startswith("abandoned:"):
                continue
            if isinstance(attempt.get("settlement_commit"), dict):
                continue
            attempt["status"] = "abandoned:interrupted"
            write_calibration_ledger(out, ledger)


def load_pending_calibration(out: pathlib.Path) -> dict[str, object]:
    pending = read_json(pending_path(out))
    required = {"schema", "run_id", "schedule_sha256", "params_sha256", "pin_sha256", "window_attestation_sha256", "pre_capture", "sessions", "receipts", "unit"}
    if not isinstance(pending, dict) or set(pending) != required or pending.get("schema") != "iter0112-calibration-pending-v1" or not isinstance(pending.get("sessions"), list) or not isinstance(pending.get("receipts"), list) or type(pending.get("unit")) is not int:
        raise LaunchViolation("calibration-pending-invalid")
    return pending


def recalibration_bound(out: pathlib.Path, manifest: dict[str, object], params: dict[str, object]) -> int:
    calibrations = manifest.get("calibrations")
    if not isinstance(calibrations, list) or not calibrations or not isinstance(calibrations[0], dict):
        raise LaunchViolation("calibration-missing-for-epoch")
    first = calibrations[0]
    sessions = first.get("sessions")
    receipts = first.get("receipts")
    if not isinstance(sessions, list) or not isinstance(receipts, list):
        raise LaunchViolation("calibration-session-accounting-invalid")
    base_sessions = sessions[:len(CALIBRATION_ENGINES)]
    base_receipts = receipts[:len(CALIBRATION_ENGINES) * len(CALIBRATION_TASKS)]
    base = sum_receipts(out, base_receipts, calibration_receipt_layout(base_sessions))
    maximum = params["venue_tolerance"]["calibration"]["accounting"]["epoch_session_cap"]
    if type(maximum) is not int or maximum % len(CALIBRATION_ENGINES):
        raise LaunchViolation("calibration-session-accounting-invalid")
    return base["total"] * maximum // len(CALIBRATION_ENGINES)


def initial_attempt_batches(schedule: dict[str, object], lanes: int) -> list[set[str]]:
    gate_id = str(schedule["blocks"][0]["replicate_id"])
    batches: list[set[str]] = []
    for sweep in range(1, int(schedule["sweeps"]) + 1):
        pending = [str(block["replicate_id"]) for block in schedule["blocks"] if block["sweep_id"] == sweep]
        while pending:
            width = 1 if pending[0] == gate_id else lanes
            batch, pending = pending[:width], pending[width:]
            batches.append({f"{replicate_id}.a1" for replicate_id in batch})
    return batches


def next_unadmitted_sweep(manifest: dict[str, object], schedule: dict[str, object]) -> int:
    entries = manifest.get("usage_evidence")
    if not isinstance(entries, list):
        raise LaunchViolation("launch-manifest-usage-evidence-invalid")
    admitted = {entry.get("sweep_id") for entry in entries if isinstance(entry, dict) and entry.get("role") in {"pre-sweep", "resume"}}
    return next((sweep for sweep in range(1, int(schedule["sweeps"]) + 1) if sweep not in admitted), int(schedule["sweeps"]) + 1)


def consumed_replay_events(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> int:
    blocks = manifest.get("blocks")
    if not isinstance(blocks, dict):
        raise LaunchViolation("launch-manifest-blocks-invalid")
    voids = {
        str(attempt["attempt_id"])
        for block in blocks.values()
        if isinstance(block, dict) and isinstance(block.get("attempts"), list)
        for attempt in block["attempts"]
        if isinstance(attempt, dict) and attempt.get("transport_state") == "VOID" and isinstance(attempt.get("attempt_id"), str) and isinstance(attempt.get("sessions"), dict) and any(isinstance(status, dict) and status.get("infra_affected") is True for status in attempt["sessions"].values())
    }
    groups = initial_attempt_batches(schedule, int(params["schedule"]["lanes"]))
    oracles = manifest.get("resume_oracles")
    if not isinstance(oracles, list):
        raise LaunchViolation("resume-oracle-manifest-invalid")
    seen: set[str] = set().union(*groups) if groups else set()
    for entry in oracles:
        if not isinstance(entry, dict) or not isinstance(entry.get("attempt_ids"), list) or not all(isinstance(attempt_id, str) for attempt_id in entry["attempt_ids"]):
            raise LaunchViolation("resume-oracle-manifest-invalid")
        group = set(entry["attempt_ids"])
        if len(group) != len(entry["attempt_ids"]) or group & seen:
            raise LaunchViolation("resume-oracle-attempt-ids-invalid")
        groups.append(group)
        seen.update(group)
    if not voids <= seen:
        raise LaunchViolation("closure-replay-event-unmapped")
    return sum(bool(group & voids) for group in groups)


def closure_actions(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], sweep: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Materialize the remaining-work input so a pinned calendar can replay it byte-for-byte."""
    budget, closure = params["venue_tolerance"]["budget_gate"], params["venue_tolerance"]["closure_check"]
    nominal_waves, replay_waves = int(closure["nominal_waves"]), int(closure["worst_case_replay_waves"])
    wall_ms = int(closure["max_block_wall_ms"])
    future_burns = [int(budget["first_sweep_burn_bound_transport_tokens"] if future_sweep == 1 else budget["subsequent_sweep_burn_bound_transport_tokens"]) for future_sweep in range(sweep, int(schedule["sweeps"]) + 1)]
    if nominal_waves != 2 * int(schedule["sweeps"]):
        raise LaunchViolation("closure-nominal-waves-invalid")
    remaining_replays = max(0, replay_waves - consumed_replay_events(manifest, schedule, params))
    remaining_calls = int(closure["probe_calls"]) - consumed_probe_calls(manifest)
    if remaining_calls < 0:
        raise LaunchViolation("resume-oracle-probe-budget-exhausted")
    reserve = int(budget["reserve_transport_tokens"])
    actions: list[dict[str, object]] = []
    for future_sweep, burn in zip(range(sweep, int(schedule["sweeps"]) + 1), future_burns):
        actions.append({"name": f"nominal-sweep-{future_sweep}-burn-reserve", "tokens": [burn, reserve], "active_ms": 2 * wall_ms})
    replay_burn = max(future_burns, default=int(budget["subsequent_sweep_burn_bound_transport_tokens"]))
    for event in range(1, remaining_replays + 1):
        actions.append({"name": f"replay-event-{event}-burn-reserve", "tokens": [replay_burn, reserve], "active_ms": wall_ms})
    actions.extend({"name": f"probe-{index}", "tokens": int(closure["probe_prefix_bound_transport_tokens"]), "active_ms": 0} for index in range(1, remaining_calls + 1))
    return actions, {"sweep": sweep, "actions": actions, "remaining_nominal_sweeps": len(future_burns), "remaining_nominal_waves": 2 * len(future_burns), "remaining_replay_waves": remaining_replays, "remaining_probe_calls": remaining_calls}


def simulate_calendar(created: datetime.datetime, reset_at: datetime.datetime, start: datetime.datetime, used: int, tpp: int, actions: list[dict[str, object]], weeks: int, recalibration_tokens: int, recalibration_wall_ms: int) -> tuple[bool, dict[str, object]]:
    expiry = created + datetime.timedelta(hours=weeks * 168)
    now, next_reset = start, reset_at
    transitions: list[dict[str, object]] = []
    trajectory: list[dict[str, object]] = []
    for action in actions:
        if not isinstance(action, dict) or set(action) != {"name", "tokens", "active_ms"} or not isinstance(action["name"], str) or type(action["active_ms"]) is not int:
            raise LaunchViolation("calendar-actions-invalid")
        tokens = action["tokens"] if isinstance(action["tokens"], list) else [action["tokens"]]
        if not tokens or any(type(token) is not int or token < 0 for token in tokens):
            raise LaunchViolation("calendar-actions-invalid")
        charge = sum(ceil_div(token, tpp) for token in tokens)
        while now >= next_reset or now + datetime.timedelta(milliseconds=action["active_ms"]) > next_reset or used + charge >= 100:
            if next_reset >= expiry:
                return False, {"expiry": expiry, "calendar_end": now, "transition_timeline": transitions, "trajectory": trajectory}
            wait_ms = max(0, int((next_reset - now).total_seconds() * 1000))
            now = next_reset
            used = 1 + ceil_div(recalibration_tokens, tpp)
            now += datetime.timedelta(milliseconds=recalibration_wall_ms)
            transitions.append({"reset_at": next_reset.isoformat(), "wait_ms": wait_ms, "calibration_tokens": recalibration_tokens, "calibration_wall_ms": recalibration_wall_ms, "used_percent_upper_after_calibration": used})
            if used >= 100 or now >= expiry:
                return False, {"expiry": expiry, "calendar_end": now, "transition_timeline": transitions, "trajectory": trajectory}
            next_reset += datetime.timedelta(hours=168)
        used += charge
        now += datetime.timedelta(milliseconds=action["active_ms"])
        trajectory.append({"action": action["name"], "used_percent_upper": used, "at": now.isoformat()})
    return now < expiry, {"expiry": expiry, "calendar_end": now, "transition_timeline": transitions, "trajectory": trajectory}


def closure_payload(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], out: pathlib.Path, bound_evidence_sha256: str, sweep: int, consumed_at: datetime.datetime) -> dict[str, object]:
    """Place remaining work at a retained W, replaying the immutable derivation before use."""
    evidence = evidence_by_digest(manifest, params).get(bound_evidence_sha256)
    if evidence is None or evidence[1] > consumed_at:
        raise LaunchViolation("closure-bound-evidence-invalid")
    bound, bound_consumed = evidence
    tpp = tpp_gate_for_epoch(manifest, str(bound["reset_at"]), params, consumed_at)
    calendar_spec = params["venue_tolerance"]["calendar"]
    maximum = calendar_spec.get("W_max")
    calibration = params["venue_tolerance"]["calibration"]
    accounting = calibration.get("accounting") if isinstance(calibration, dict) else None
    session_bound = calibration.get("full_session_bound_transport_tokens") if isinstance(calibration, dict) else None
    bracket_bound = calibration.get("full_bracket_wall_ms") if isinstance(calibration, dict) else None
    if type(maximum) is not int or not 1 <= maximum <= 6 or not isinstance(accounting, dict) or not isinstance(session_bound, dict) or not isinstance(bracket_bound, dict) or type(accounting.get("epoch_session_cap")) is not int or type(session_bound.get("value")) is not int or type(bracket_bound.get("value")) is not int:
        raise LaunchViolation("calibration-session-accounting-invalid")
    recalibration_tokens = accounting["epoch_session_cap"] * session_bound["value"]
    recalibration_wall_ms = bracket_bound["value"]
    created, reset_at = parse_iso8601(str(manifest["created_at"]), "created_at"), parse_iso8601(str(bound["reset_at"]), "reset_at")
    actions, remaining_work = closure_actions(manifest, schedule, params, sweep)

    def simulate(weeks: int) -> tuple[bool, dict[str, object]]:
        return simulate_calendar(created, reset_at, consumed_at, used_percent_upper(bound), tpp, actions, weeks, recalibration_tokens, recalibration_wall_ms)

    pinned = manifest.get("calendar")
    if pinned is None:
        candidates = [(weeks, *simulate(weeks)) for weeks in range(1, maximum + 1)]
        selected = next(((weeks, detail) for weeks, passed, detail in candidates if passed), None)
        if selected is None:
            weeks, passed, detail = candidates[-1]
        else:
            weeks, detail, passed = selected[0], selected[1], True
        derivation_inputs = {"formula_version": calendar_spec["formula"], "tpp_input": tpp, "capture": {"sha256": bound_evidence_sha256, "reset_at": bound["reset_at"], "used_percent_upper": used_percent_upper(bound), "consumed_at": bound_consumed.isoformat()}, "calendar_start": consumed_at.isoformat(), "remaining_work": remaining_work}
        calendar = {"formula_version": calendar_spec["formula"], "derivation_inputs": derivation_inputs, "W": weeks, "root_age_hours": weeks * 168, "max_reset_epochs": weeks, "expiry": detail["expiry"].isoformat(), "transition_timeline": detail["transition_timeline"], "trajectory": detail["trajectory"]}
    else:
        required = {"formula_version", "derivation_inputs", "W", "root_age_hours", "max_reset_epochs", "expiry", "transition_timeline", "trajectory"}
        if not isinstance(pinned, dict) or set(pinned) != required or pinned.get("formula_version") != calendar_spec["formula"] or type(pinned.get("W")) is not int or not 1 <= pinned["W"] <= maximum or pinned.get("root_age_hours") != pinned["W"] * 168 or pinned.get("max_reset_epochs") != pinned["W"] or not isinstance(pinned.get("derivation_inputs"), dict):
            raise LaunchViolation("calendar-pinned-invalid")
        inputs = pinned["derivation_inputs"]
        if set(inputs) != {"formula_version", "tpp_input", "capture", "calendar_start", "remaining_work"} or inputs.get("formula_version") != calendar_spec["formula"] or type(inputs.get("tpp_input")) is not int or not isinstance(inputs.get("capture"), dict) or not isinstance(inputs.get("remaining_work"), dict):
            raise LaunchViolation("calendar-pinned-invalid")
        capture = inputs["capture"]
        if set(capture) != {"sha256", "reset_at", "used_percent_upper", "consumed_at"} or not is_digest(capture.get("sha256")) or not isinstance(capture.get("reset_at"), str) or type(capture.get("used_percent_upper")) is not int:
            raise LaunchViolation("calendar-pinned-invalid")
        initial_start = parse_iso8601(str(inputs["calendar_start"]), "calendar-pinned-start")
        initial_capture_at = parse_iso8601(str(capture["consumed_at"]), "calendar-pinned-capture")
        initial_manifest = manifest_as_of(manifest, initial_start)
        initial_evidence = evidence_by_digest(initial_manifest, params).get(capture["sha256"])
        if initial_evidence is None or initial_evidence[1] != initial_capture_at or initial_evidence[0].get("reset_at") != capture["reset_at"] or used_percent_upper(initial_evidence[0]) != capture["used_percent_upper"]:
            raise LaunchViolation("calendar-pinned-input-mismatch")
        initial_tpp = tpp_gate_for_epoch(initial_manifest, str(capture["reset_at"]), params, initial_start)
        initial_actions, initial_remaining = closure_actions(initial_manifest, schedule, params, int(initialsweep := inputs["remaining_work"].get("sweep", 0)))
        if initial_tpp != inputs["tpp_input"] or initial_remaining != inputs["remaining_work"]:
            raise LaunchViolation("calendar-pinned-input-mismatch")
        initial_detail = simulate_calendar(created, parse_iso8601(str(capture["reset_at"]), "calendar-pinned-reset"), initial_start, int(capture["used_percent_upper"]), initial_tpp, initial_actions, pinned["W"], recalibration_tokens, recalibration_wall_ms)
        initial_derived = next((candidate for candidate in range(1, maximum + 1) if simulate_calendar(created, parse_iso8601(str(capture["reset_at"]), "calendar-pinned-reset"), initial_start, int(capture["used_percent_upper"]), initial_tpp, initial_actions, candidate, recalibration_tokens, recalibration_wall_ms)[0]), None)
        expected_calendar = {"formula_version": calendar_spec["formula"], "derivation_inputs": inputs, "W": pinned["W"], "root_age_hours": pinned["W"] * 168, "max_reset_epochs": pinned["W"], "expiry": initial_detail[1]["expiry"].isoformat(), "transition_timeline": initial_detail[1]["transition_timeline"], "trajectory": initial_detail[1]["trajectory"]}
        if initial_derived != pinned["W"] or not initial_detail[0] or pinned != expected_calendar:
            raise LaunchViolation("calendar-pinned-w-mismatch")
        weeks, (passed, detail), calendar = pinned["W"], simulate(pinned["W"]), pinned
    calendar_end = detail["calendar_end"]
    closure = params["venue_tolerance"]["closure_check"]
    return {"schema": "iter0112-closure-v2", "passed": passed, "sweep_id": sweep, "bound_evidence_sha256": bound_evidence_sha256, "tpp_gate": tpp, "used_percent_upper": used_percent_upper(bound), "trajectory": detail["trajectory"], "nominal_waves": closure["nominal_waves"], "worst_case_replay_waves": closure["worst_case_replay_waves"], "worst_case_replay_placement": closure["worst_case_replay_placement"], "max_block_wall_ms": closure["max_block_wall_ms"], "probe_calls": closure["probe_calls"], "reset_at": bound["reset_at"], "calendar_start": consumed_at.isoformat(), "calendar_end": calendar_end.isoformat(), "expiry": detail["expiry"].isoformat(), "calendar_headroom_ms": int((detail["expiry"] - calendar_end).total_seconds() * 1000), "calendar": calendar, **remaining_work, "recalibration_tokens_per_epoch": recalibration_tokens, "recalibration_wall_ms_per_epoch": recalibration_wall_ms}


def append_closure_receipt(manifest: dict[str, object], payload: dict[str, object], sweep: int, consumed_at: datetime.datetime) -> None:
    raw = canonical_bytes(payload)
    digest = hashlib.sha256(raw).hexdigest()
    if any(entry.get("sha256") == digest for entry in manifest["closure_receipts"]):
        raise LaunchViolation("closure-receipt-reused")
    manifest["closure_receipts"].append({"sha256": digest, "bytes_base64": base64.b64encode(raw).decode(), "sweep_id": sweep, "consumed_at": consumed_at.isoformat()})


def validate_closure_receipts(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], out: pathlib.Path) -> None:
    receipts = manifest.get("closure_receipts")
    if not isinstance(receipts, list):
        raise LaunchViolation("closure-receipt-invalid")
    seen: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict) or set(receipt) != {"sha256", "bytes_base64", "sweep_id", "consumed_at"} or not is_digest(receipt.get("sha256")) or type(receipt.get("sweep_id")) is not int:
            raise LaunchViolation("closure-receipt-invalid")
        consumed_at = parse_iso8601(str(receipt.get("consumed_at")), "closure-consumed-at")
        try:
            raw = base64.b64decode(receipt["bytes_base64"], validate=True)
            payload = json.loads(raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise LaunchViolation("closure-receipt-invalid") from exc
        if hashlib.sha256(raw).hexdigest() != receipt["sha256"] or receipt["sha256"] in seen or not isinstance(payload, dict) or not is_digest(payload.get("bound_evidence_sha256")):
            raise LaunchViolation("closure-receipt-invalid")
        expected = closure_payload(manifest_as_of(manifest, consumed_at), schedule, params, out, payload["bound_evidence_sha256"], receipt["sweep_id"], consumed_at)
        if payload != expected:
            raise LaunchViolation("closure-receipt-invalid")
        seen.add(receipt["sha256"])


def run_calibration(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    pin, (attestation_raw, _attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    raw, pre, digest = load_usage_evidence(args.usage_evidence, params)
    args.out.mkdir(parents=True, exist_ok=True)
    pending_file = pending_path(args.out)
    if pending_file.exists():
        pending = load_pending_calibration(args.out)
        if not args.calibration_top_up or pending["unit"] != 1 or pending["run_id"] != args.run_id or pending["schedule_sha256"] != sha256(args.schedule) or pending["params_sha256"] != sha256(args.params) or pending["pin_sha256"] != pin or pending["window_attestation_sha256"] != hashlib.sha256(attestation_raw).hexdigest():
            raise LaunchViolation("calibration-pending-mismatch")
        _prior_raw, prior = decode_capture(pending["pre_capture"], params)
        if prior["reset_at"] != pre["reset_at"]:
            raise LaunchViolation("calibration-cross-epoch-invalid")
        if (args.out / MANIFEST_NAME).exists():
            manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw)
            if manifest["calibration_session_equivalents"] + len(pending["sessions"]) + len(CALIBRATION_ENGINES) > params["venue_tolerance"]["calibration"]["accounting"]["root_session_cap"]:
                raise LaunchViolation("calibration-session-accounting-invalid")
        unit = int(pending["unit"]) + 1
        sessions, receipts = run_calibration_batch(args.out, args.run_id, unit)
        pending["sessions"].extend(sessions); pending["receipts"].extend(receipts); pending["unit"] = unit
    else:
        if args.calibration_top_up:
            raise LaunchViolation("calibration-top-up-without-base")
        if (args.out / MANIFEST_NAME).exists():
            manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw)
            if calibration_for_epoch(manifest, str(pre["reset_at"])) is not None or manifest["calibration_session_equivalents"] + len(CALIBRATION_ENGINES) > params["venue_tolerance"]["calibration"]["accounting"]["root_session_cap"]:
                raise LaunchViolation("calibration-session-accounting-invalid")
        sessions, receipts = run_calibration_batch(args.out, args.run_id, 1)
        pending = {"schema": "iter0112-calibration-pending-v1", "run_id": args.run_id, "schedule_sha256": sha256(args.schedule), "params_sha256": sha256(args.params), "pin_sha256": pin, "window_attestation_sha256": hashlib.sha256(attestation_raw).hexdigest(), "pre_capture": capture_entry(raw, digest), "sessions": sessions, "receipts": receipts, "unit": 1}
    if len(pending["sessions"]) > params["venue_tolerance"]["calibration"]["accounting"]["attempt_session_cap"]:
        raise LaunchViolation("calibration-session-cap-exceeded")
    write_json(pending_file, pending)
    print(f"CALIBRATION_BATCH_RECORDED: sessions={len(pending['sessions'])}")
    return 0


def run_settle_calibration(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    pin, (attestation_raw, _attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    pending = load_pending_calibration(args.out)
    if pending["run_id"] != args.run_id or pending["schedule_sha256"] != sha256(args.schedule) or pending["params_sha256"] != sha256(args.params) or pending["pin_sha256"] != pin or pending["window_attestation_sha256"] != hashlib.sha256(attestation_raw).hexdigest():
        raise LaunchViolation("calibration-pending-mismatch")
    if not isinstance(args.settlement_usage_evidence, list) or len(args.settlement_usage_evidence) != 2:
        raise LaunchViolation("calibration-settlement-captures-required")
    captures = [load_usage_evidence(path, params) for path in args.settlement_usage_evidence]
    _pre_raw, pre = decode_capture(pending["pre_capture"], params)
    if any(capture[1]["reset_at"] != pre["reset_at"] for capture in captures):
        raise LaunchViolation("calibration-cross-epoch-invalid")
    first, second = captures[0][1], captures[1][1]
    first_time, second_time = parse_iso8601(first["observed_at"], "settlement-observed-at"), parse_iso8601(second["observed_at"], "settlement-observed-at")
    if first["used_percent"] != second["used_percent"] or second_time - first_time < datetime.timedelta(seconds=120):
        raise LaunchViolation("calibration-settlement-invalid")
    components = sum_receipts(args.out, pending["receipts"], calibration_receipt_layout(pending["sessions"]))
    latest = max(parse_iso8601(str(receipt["completed_at"]), "calibration-receipt-completed-at") for receipt in pending["receipts"])
    if second_time < latest + datetime.timedelta(seconds=180):
        raise LaunchViolation("calibration-settlement-too-early")
    if not calibration_mix_ok(components):
        raise LaunchViolation("CALIBRATION_UNIDENTIFIABLE")
    delta = second["used_percent"] - pre["used_percent"]
    if delta < 3:
        if int(pending["unit"]) == 1:
            print("CALIBRATION_TOP_UP_REQUIRED")
            return 2
        raise LaunchViolation("CALIBRATION_UNIDENTIFIABLE")
    chain = {"kind": "calibration", "pre_sha256": pending["pre_capture"]["sha256"], "post_sha256": captures[-1][2], "receipt_digests": [receipt["sha256"] for receipt in pending["receipts"]], "components": components, "draw": components["total"], "delta_percent": delta, "tpp_obs": components["total"] // (delta + 1)}
    calibration = {"reset_at": pre["reset_at"], "pre_capture": pending["pre_capture"], "settlement_captures": [capture_entry(raw, digest) for raw, _value, digest in captures], "sessions": pending["sessions"], "receipts": pending["receipts"], "components": components, "tpp_chain": [chain], "session_equivalents": len(pending["sessions"])}
    exists = (args.out / MANIFEST_NAME).exists()
    manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw) if exists else base_manifest(args.schedule, args.params, args.run_id, pin, attestation_raw)
    if calibration_for_epoch(manifest, calibration["reset_at"]) is not None or manifest["calibration_session_equivalents"] + calibration["session_equivalents"] > params["venue_tolerance"]["calibration"]["accounting"]["root_session_cap"]:
        raise LaunchViolation("calibration-session-accounting-invalid")
    manifest["calibrations"].append(calibration); manifest["calibration_session_equivalents"] += calibration["session_equivalents"]
    closure_at = datetime.datetime.now(datetime.timezone.utc)
    sweep = next_unadmitted_sweep(manifest, schedule)
    closure = closure_payload(manifest, schedule, params, args.out, captures[-1][2], sweep, closure_at)
    if not closure["passed"]:
        if exists:
            append_closure_receipt(manifest, closure, sweep, closure_at)
            manifest["terminal"] = "CALIBRATION_DRIFT_OVER_BUDGET"; write_json(args.out / MANIFEST_NAME, manifest)
            print("TERMINAL: CALIBRATION_DRIFT_OVER_BUDGET")
            return 2
        raise LaunchViolation("VENUE_OVER_BUDGET")
    if manifest["calendar"] is None and "calendar" in closure:
        manifest["calendar"] = closure["calendar"]
    append_closure_receipt(manifest, closure, sweep, closure_at)
    write_json(args.out / MANIFEST_NAME, manifest)
    pending_path(args.out).unlink()
    print(f"CALIBRATION_SETTLED: tpp_gate={chain['tpp_obs']}")
    return 0


def calibration_from_ledger(ledger: dict[str, object], reset_at: str, params: dict[str, object], out: pathlib.Path, settled_attempt: dict[str, object] | None = None) -> dict[str, object]:
    epoch = ledger_epoch(ledger, reset_at)
    if epoch is None or not isinstance(epoch.get("attempts"), list):
        raise LaunchViolation("calibration-ledger-invalid")
    attempts = epoch["attempts"]
    settled = settled_attempt if settled_attempt is not None else next((attempt for attempt in attempts if isinstance(attempt, dict) and attempt.get("status") == "settled"), None)
    if not isinstance(settled, dict) or not isinstance(settled.get("captures"), dict):
        raise LaunchViolation("calibration-ledger-unsettled")
    captures = settled["captures"]
    for name in ("P1", "P2"):
        if name not in captures:
            raise LaunchViolation("calibration-ledger-captures-invalid")
    pairs = settled.get("settlement_pairs")
    if not isinstance(pairs, list) or not pairs:
        raise LaunchViolation("calibration-ledger-captures-invalid")
    final_pair = pairs[-1]
    if not isinstance(final_pair, dict) or set(final_pair) != {"unit", "S1", "S2"}:
        raise LaunchViolation("calibration-ledger-captures-invalid")
    _p2_raw, p2 = decode_capture(captures["P2"], params)
    _s1_raw, s1 = decode_capture(final_pair["S1"], params)
    _s2_raw, s2 = decode_capture(final_pair["S2"], params)
    if any(evidence["reset_at"] != reset_at for evidence in (p2, s1, s2)):
        raise LaunchViolation("calibration-cross-epoch-invalid")
    receipts = settled.get("receipts")
    sessions = settled.get("sessions")
    if not isinstance(receipts, list) or not isinstance(sessions, list) or type(settled.get("attempt_id")) is not int:
        raise LaunchViolation("calibration-ledger-invalid")
    components = sum_receipts(out, receipts, calibration_receipt_layout(sessions, settled["attempt_id"]))
    delta = s2["used_percent"] - p2["used_percent"]
    chain = {"kind": "calibration", "pre_sha256": captures["P2"]["sha256"], "post_sha256": final_pair["S2"]["sha256"], "receipt_digests": [receipt["sha256"] for receipt in receipts], "components": components, "draw": components["total"], "delta_percent": delta, "tpp_obs": components["total"] // (delta + 1) if delta >= 0 else 0}
    analytical_attempts = [attempt for attempt in attempts if isinstance(attempt, dict) and attempt.get("status") != "abandoned:interrupted"]
    session_equivalents = sum(attempt.get("session_equivalents", 0) for attempt in analytical_attempts if type(attempt.get("session_equivalents")) is int)
    return {"reset_at": reset_at, "pre_capture": captures["P2"], "settlement_captures": [final_pair["S1"], final_pair["S2"]], "sessions": sessions, "receipts": receipts, "components": components, "tpp_chain": [chain], "session_equivalents": session_equivalents, "attempts": analytical_attempts}


def settlement_commit_calibration(calibration: dict[str, object]) -> dict[str, object]:
    """The commit captures calibration inputs without recursively embedding itself."""
    projected = json.loads(json.dumps(calibration))
    attempts = projected.get("attempts")
    if not isinstance(attempts, list):
        raise LaunchViolation("calibration-settlement-commit-invalid")
    for attempt in attempts:
        if not isinstance(attempt, dict):
            raise LaunchViolation("calibration-settlement-commit-invalid")
        attempt["settlement_commit"] = None
    return projected


def publish_settlement_commits(out: pathlib.Path, manifest: dict[str, object], ledger: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> bool:
    """Finish every ledger-written settlement commit exactly once after a restart."""
    if ledger.get("pending_attempt") is not None:
        raise LaunchViolation("calibration-ledger-invalid")
    needs_sync = manifest.get("calibration_ledger") != calibration_ledger_projection(ledger) or manifest.get("calibration_ledger_generation") != ledger.get("generation")
    sync_manifest_calibration_ledger(manifest, ledger)
    published = False
    for reset_at, projected_attempt in manifest_calibration_attempts({**manifest, "calibration_ledger": calibration_ledger_projection(ledger)}):
        attempt_id = projected_attempt.get("attempt_id")
        attempt = calibration_attempt_by_id(ledger, attempt_id) if type(attempt_id) is int else None
        if reset_at is None or not isinstance(attempt, dict) or attempt.get("status") not in {"open", "settled"}:
            continue
        commit = attempt.get("settlement_commit")
        if not isinstance(commit, dict):
            continue
        published = published or needs_sync
        committed_ledger = ledger if attempt["status"] == "settled" else json.loads(json.dumps(ledger))
        committed_attempt = calibration_attempt_by_id(committed_ledger, attempt_id)
        if committed_attempt is None:
            raise LaunchViolation("calibration-ledger-invalid")
        committed_attempt["status"] = "settled"
        calibration = calibration_from_ledger(committed_ledger, reset_at, params, out, committed_attempt)
        if commit.get("calibration") != settlement_commit_calibration(calibration) or type(commit.get("sweep")) is not int or not isinstance(commit.get("closure"), dict) or not isinstance(commit.get("closure_at"), str):
            raise LaunchViolation("calibration-settlement-commit-invalid")
        closure_at = parse_iso8601(commit["closure_at"], "calibration-settlement-commit-at")
        settlement_captures = calibration["settlement_captures"]
        if not isinstance(settlement_captures, list) or len(settlement_captures) != 2:
            raise LaunchViolation("calibration-settlement-commit-invalid")
        expected = closure_payload({**manifest, "calibration_ledger": calibration_ledger_projection(ledger), "calibrations": [*manifest["calibrations"], calibration] if not any(isinstance(item, dict) and item.get("reset_at") == reset_at for item in manifest["calibrations"]) else manifest["calibrations"]}, schedule, params, out, settlement_captures[1]["sha256"], commit["sweep"], closure_at)
        if commit["closure"] != expected:
            raise LaunchViolation("calibration-settlement-commit-invalid")
        existing = next((item for item in manifest["calibrations"] if isinstance(item, dict) and item.get("reset_at") == reset_at), None)
        if existing is None:
            manifest["calibrations"].append(calibration)
            published = True
        elif existing != calibration:
            raise LaunchViolation("calibration-ledger-manifest-mismatch")
        if manifest["calendar"] is None and expected["passed"] is True:
            manifest["calendar"] = expected["calendar"]
            published = True
        raw = canonical_bytes(expected)
        receipt = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes_base64": base64.b64encode(raw).decode(), "sweep_id": commit["sweep"], "consumed_at": closure_at.isoformat()}
        if receipt not in manifest["closure_receipts"]:
            manifest["closure_receipts"].append(receipt)
            published = True
        if expected["passed"] is False:
            published = published or manifest.get("terminal") != "CALIBRATION_DRIFT_OVER_BUDGET"
            manifest["terminal"] = "CALIBRATION_DRIFT_OVER_BUDGET"
        if attempt["status"] != "settled":
            attempt["status"] = "settled"
            published = True
    if published:
        persist_calibration_state(out, manifest, ledger)
    return published


def abandon_bracket(out: pathlib.Path, ledger: dict[str, object], attempt: dict[str, object], reason: str, params: dict[str, object], manifest: dict[str, object] | None = None) -> int:
    attempt["status"] = f"abandoned:{reason}"
    captures = attempt.get("captures")
    reset_at = captures.get("reset_at") if isinstance(captures, dict) and isinstance(captures.get("reset_at"), str) else None
    if calibration_status(attempt, reset_at, params) != attempt["status"]:
        raise LaunchViolation("calibration-attempt-status-evidence-invalid")
    if manifest is None:
        write_calibration_ledger(out, ledger)
    else:
        persist_calibration_state(out, manifest, ledger)
    print("CALIBRATION_BRACKET_CONTAMINATED" if reason == "fable-meter-moved" else f"CALIBRATION_BRACKET_ABANDONED: {reason}")
    return 2


def preflight_bracket_epoch(manifest: dict[str, object], reset_at: str, params: dict[str, object], out: pathlib.Path, ledger: dict[str, object]) -> None:
    if root_expired(manifest, params):
        manifest["terminal"] = "WALL_CLOCK_EXPIRED"
        persist_calibration_state(out, manifest, ledger)
        raise LaunchViolation("WALL_CLOCK_EXPIRED")
    calendar = manifest.get("calendar")
    rootless = calendar is None
    maximum = params["venue_tolerance"]["calendar"].get("W_max") if calendar is None else calendar.get("W") if isinstance(calendar, dict) else None
    if type(maximum) is not int:
        raise LaunchViolation("calendar-pinned-invalid")
    try:
        candidate = json.loads(json.dumps(manifest))
        candidate["calibration_ledger"] = calibration_ledger_projection(ledger)
        verify_reset_timeline(full_timeline(candidate, params), maximum)
    except LaunchViolation as exc:
        if str(exc) != "usage-evidence-reset-epochs-exceeded":
            raise
        if rootless:
            manifest["terminal"] = "VENUE_OVER_BUDGET"
        persist_calibration_state(out, manifest, ledger)
        raise LaunchViolation("VENUE_OVER_BUDGET") if rootless else exc


def run_calibrate_bracket(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    pin, (attestation_raw, _attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    args.out.mkdir(parents=True, exist_ok=True)
    ledger = load_calibration_ledger(args.out, args.run_id, args.schedule, args.params, pin)
    import_pending_attempt(args.out, ledger, params)
    existing_manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw) if (args.out / MANIFEST_NAME).exists() else None
    if existing_manifest is not None:
        ledger = load_calibration_ledger(args.out, args.run_id, args.schedule, args.params, pin)
    if existing_manifest is not None and root_expired(existing_manifest, params):
        existing_manifest["terminal"] = "WALL_CLOCK_EXPIRED"
        persist_calibration_state(args.out, existing_manifest, ledger)
        print("TERMINAL: WALL_CLOCK_EXPIRED")
        return 2
    recovered_manifest = existing_manifest if existing_manifest is not None else base_manifest(args.schedule, args.params, args.run_id, pin, attestation_raw)
    if any(attempt.get("status") == "open" and isinstance(attempt.get("settlement_commit"), dict) for attempt in ledger_attempts(ledger)) and publish_settlement_commits(args.out, recovered_manifest, ledger, schedule, params):
        print("CALIBRATION_BRACKET_SETTLED: recovered settlement commit")
        return 0
    recover_open_calibration_attempts(args.out, ledger, params)
    if publish_settlement_commits(args.out, recovered_manifest, ledger, schedule, params):
        print("CALIBRATION_BRACKET_SETTLED: recovered settlement commit")
        return 0
    attempt_id = next_calibration_attempt_id(ledger)
    attempt: dict[str, object] = {"attempt_id": attempt_id, "status": "open", "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "epoch": None, "captures": {}, "units": [], "settlement_pairs": [], "sessions": [], "receipts": [], "session_equivalents": 0, "settlement_commit": None}
    ledger["pending_attempt"] = attempt
    write_calibration_ledger(args.out, ledger)
    p1, _p1_entry = capture_bracket_slot(args.out, ledger, attempt, "P1", "p1", params)
    epoch = ledger_epoch(ledger, str(p1["reset_at"]), create=True)
    assert epoch is not None
    epoch["attempts"].append(attempt)
    ledger["pending_attempt"] = None
    write_calibration_ledger(args.out, ledger)
    time.sleep(600)
    p2, _p2_entry = capture_bracket_slot(args.out, ledger, attempt, "P2", "p2", params)
    classified = calibration_status(attempt, str(p1["reset_at"]), params)
    if classified is not None:
        return abandon_bracket(args.out, ledger, attempt, classified.partition(":")[2], params, existing_manifest)
    accounting = params["venue_tolerance"]["calibration"]["accounting"]
    attempt_maximum, epoch_maximum = accounting["attempt_session_cap"], accounting["epoch_session_cap"]
    manifest_for_preflight = existing_manifest if existing_manifest is not None else base_manifest(args.schedule, args.params, args.run_id, pin, attestation_raw)
    preflight_bracket_epoch(manifest_for_preflight, str(p2["reset_at"]), params, args.out, ledger)
    if existing_manifest is not None:
        if calibration_for_epoch(existing_manifest, str(p2["reset_at"])) is not None:
            raise LaunchViolation("calibration-session-accounting-invalid")
    while True:
        preflight_bracket_epoch(manifest_for_preflight, str(p2["reset_at"]), params, args.out, ledger)
        charged_epoch = sum(item.get("session_equivalents", 0) for item in epoch["attempts"] if isinstance(item, dict) and type(item.get("session_equivalents")) is int)
        if attempt["session_equivalents"] + len(CALIBRATION_ENGINES) > attempt_maximum or charged_epoch + len(CALIBRATION_ENGINES) > epoch_maximum:
            raise LaunchViolation("calibration-session-cap-exceeded")
        root_charged = sum(item["session_equivalents"] for item in ledger_attempts(ledger))
        if root_charged + len(CALIBRATION_ENGINES) > accounting["root_session_cap"]:
            raise LaunchViolation("calibration-session-accounting-invalid")
        unit = len(attempt["units"]) + 1
        run_calibration_batch(args.out, args.run_id, unit, attempt_id, ledger, attempt)
        time.sleep(180)
        pair: dict[str, object] = {"unit": unit}
        attempt["settlement_pairs"].append(pair)
        s1, _s1_entry = capture_bracket_slot(args.out, ledger, attempt, "S1", f"u{unit}-s1", params, pair)
        time.sleep(125)
        s2, s2_entry = capture_bracket_slot(args.out, ledger, attempt, "S2", f"u{unit}-s2", params, pair)
        classified = calibration_status(attempt, str(p2["reset_at"]), params)
        if classified is not None:
            return abandon_bracket(args.out, ledger, attempt, classified.partition(":")[2], params, existing_manifest)
        components = sum_receipts(args.out, attempt["receipts"], calibration_receipt_layout(attempt["sessions"], attempt_id))
        if not calibration_mix_ok(components):
            raise LaunchViolation("CALIBRATION_UNIDENTIFIABLE")
        delta = s2["used_percent"] - p2["used_percent"]
        no_complete_unit_fits = charged_epoch + 2 * len(CALIBRATION_ENGINES) > epoch_maximum
        if delta >= 4 or attempt["session_equivalents"] == attempt_maximum or no_complete_unit_fits:
            if delta == 0:
                raise LaunchViolation("CALIBRATION_UNIDENTIFIABLE")
            committed_ledger = json.loads(json.dumps(ledger))
            committed_attempt = calibration_attempt_by_id(committed_ledger, attempt_id)
            if committed_attempt is None:
                raise LaunchViolation("calibration-ledger-invalid")
            committed_attempt["status"] = "settled"
            calibration = calibration_from_ledger(committed_ledger, str(p2["reset_at"]), params, args.out, committed_attempt)
            manifest = existing_manifest if existing_manifest is not None else base_manifest(args.schedule, args.params, args.run_id, pin, attestation_raw)
            manifest["calibrations"].append(json.loads(json.dumps(calibration)))
            sync_manifest_calibration_ledger(manifest, ledger)
            if manifest["calibration_session_equivalents"] > accounting["root_session_cap"]:
                raise LaunchViolation("calibration-session-accounting-invalid")
            closure_at = datetime.datetime.now(datetime.timezone.utc)
            sweep = next_unadmitted_sweep(manifest, schedule)
            closure = closure_payload(manifest, schedule, params, args.out, s2_entry["sha256"], sweep, closure_at)
            if not closure["passed"]:
                if existing_manifest is not None:
                    attempt["settlement_commit"] = {"calibration": settlement_commit_calibration(calibration), "closure": closure, "sweep": sweep, "closure_at": closure_at.isoformat()}
                    write_calibration_ledger(args.out, ledger)
                    attempt["status"] = "settled"
                    write_calibration_ledger(args.out, ledger)
                    publish_settlement_commits(args.out, manifest, ledger, schedule, params)
                    print("CALIBRATION_DRIFT_OVER_BUDGET")
                    return 2
                attempt["status"] = "abandoned:venue-over-budget"
                if calibration_status(attempt, str(p2["reset_at"]), params) is not None:
                    raise LaunchViolation("calibration-attempt-status-evidence-invalid")
                write_calibration_ledger(args.out, ledger)
                print("VENUE_OVER_BUDGET")
                return 2
            attempt["settlement_commit"] = {"calibration": settlement_commit_calibration(calibration), "closure": closure, "sweep": sweep, "closure_at": closure_at.isoformat()}
            write_calibration_ledger(args.out, ledger)
            attempt["status"] = "settled"
            write_calibration_ledger(args.out, ledger)
            publish_settlement_commits(args.out, manifest, ledger, schedule, params)
            print(f"CALIBRATION_BRACKET_SETTLED: tpp_gate={closure['tpp_gate']} W={closure['calendar']['W']}")
            return 0


def run_record_settlement(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    pin, (attestation_raw, _attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    if not isinstance(args.settlement_usage_evidence, list) or len(args.settlement_usage_evidence) != 2:
        raise LaunchViolation("settlement-captures-required")
    if not (args.out / MANIFEST_NAME).exists():
        raise LaunchViolation("calibration-manifest-missing")
    manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw)
    captures = [load_usage_evidence(path, params) for path in args.settlement_usage_evidence]
    first, second = captures[0][1], captures[1][1]
    if first["reset_at"] != second["reset_at"]:
        raise LaunchViolation("settlement-cross-epoch-invalid")
    entry = {"reset_at": first["reset_at"], "captures": [capture_entry(raw, digest) for raw, _evidence, digest in captures]}
    settlement_entry_valid(entry, manifest, params)
    manifest["settlements"].append(entry)
    write_json(args.out / MANIFEST_NAME, manifest)
    print(f"SETTLEMENT_RECORDED: reset_at={entry['reset_at']}")
    return 0


def completed_sweep_receipts(out: pathlib.Path, manifest: dict[str, object], schedule: dict[str, object], sweep: int) -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    for relative, engine in completed_sweep_receipt_layout(out, manifest, schedule, sweep):
        path = out / relative
        raw = path.read_bytes()
        token_components(json.loads(raw), engine)
        receipts.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "engine": engine, "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    return receipts


def run(args: argparse.Namespace) -> int:
    schedule, params = load_inputs(args.schedule, args.params)
    if args.sweep < 1 or args.sweep > schedule["sweeps"] or args.lanes != params["schedule"]["lanes"]:
        raise LaunchViolation("launch-arguments-invalid")
    pin, (attestation_raw, _attestation) = verify_script_inventory(), load_window_attestation(args.window_attestation, params)
    usage_raw, usage, usage_digest = load_usage_evidence(args.usage_evidence, params)
    if not (args.out / MANIFEST_NAME).exists():
        raise LaunchViolation("calibration-manifest-missing")
    manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw)
    if root_expired(manifest, params):
        manifest["terminal"] = "WALL_CLOCK_EXPIRED"
        write_json(args.out / MANIFEST_NAME, manifest)
        print("TERMINAL: WALL_CLOCK_EXPIRED")
        return 2
    calibration = calibration_for_epoch(manifest, str(usage["reset_at"]))
    if calibration is None:
        raise LaunchViolation("calibration-missing-for-epoch")
    tpp_gate = tpp_gate_for_epoch(manifest, str(usage["reset_at"]), params)
    if args.record_usage_after:
        if any(entry["role"] == "post-sweep" and entry["sweep_id"] == args.sweep for entry in manifest["usage_evidence"]):
            raise LaunchViolation("usage-post-evidence-already-recorded")
        append_usage(manifest, usage_raw, usage, usage_digest, "post-sweep", args.sweep, params)
        pre_entry = next((entry for entry in reversed(manifest["usage_evidence"][:-1]) if entry["role"] == "pre-sweep" and entry["sweep_id"] == args.sweep), None)
        if pre_entry is None:
            raise LaunchViolation("usage-pre-evidence-missing")
        _pre_raw, pre = decode_capture({"sha256": pre_entry["sha256"], "bytes_base64": pre_entry["bytes_base64"], "consumed_at": pre_entry["consumed_at"]}, params)
        if pre["reset_at"] != usage["reset_at"]:
            raise LaunchViolation("calibration-cross-epoch-invalid")
        receipts = completed_sweep_receipts(args.out, manifest, schedule, args.sweep)
        components = sum_receipts(args.out, receipts, completed_sweep_receipt_layout(args.out, manifest, schedule, args.sweep))
        completed = {"sweep_id": args.sweep, "pre_sha256": pre_entry["sha256"], "post_sha256": usage_digest, "receipts": receipts, "components": components, "draw": components["total"]}
        completed_sweeps = manifest.setdefault("completed_sweeps", [])
        if not isinstance(completed_sweeps, list) or any(not isinstance(entry, dict) or entry.get("sweep_id") == args.sweep for entry in completed_sweeps):
            raise LaunchViolation("completed-sweep-entry-invalid")
        completed_sweeps.append(completed)
        if not calibration_mix_ok(components, completed_sweep=True):
            manifest["terminal"] = "CALIBRATION_UNIDENTIFIABLE"
            write_json(args.out / MANIFEST_NAME, manifest)
            print("TERMINAL: CALIBRATION_UNIDENTIFIABLE")
            return 2
        delta = usage["used_percent"] - pre["used_percent"]
        prior_tpp = tpp_gate_for_epoch(manifest, str(usage["reset_at"]), params)
        if delta >= 1:
            calibration["tpp_chain"].append({"kind": "sweep", "sweep_id": args.sweep, "pre_sha256": pre_entry["sha256"], "post_sha256": usage_digest, "receipts": receipts, "components": components, "draw": components["total"], "delta_percent": delta, "tpp_obs": components["total"] // (delta + 1)})
            current_tpp = tpp_gate_for_epoch(manifest, str(usage["reset_at"]), params)
            if current_tpp < prior_tpp:
                closure_at = datetime.datetime.now(datetime.timezone.utc)
                closure = closure_payload(manifest, schedule, params, args.out, usage_digest, args.sweep + 1, closure_at)
                if manifest["calendar"] is None and "calendar" in closure:
                    manifest["calendar"] = closure["calendar"]
                append_closure_receipt(manifest, closure, args.sweep + 1, closure_at)
                if not closure["passed"]:
                    manifest["terminal"] = "CALIBRATION_DRIFT_OVER_BUDGET"
                    write_json(args.out / MANIFEST_NAME, manifest)
                    print("TERMINAL: CALIBRATION_DRIFT_OVER_BUDGET")
                    return 2
        write_json(args.out / MANIFEST_NAME, manifest)
        print(f"USAGE_RECORDED: post-sweep={args.sweep}")
        return 0
    terminal, _details = derive_terminal(manifest, schedule, params)
    if manifest.get("terminal") in {"CALIBRATION_UNIDENTIFIABLE", "CALIBRATION_DRIFT_OVER_BUDGET"}:
        print(f"TERMINAL: {manifest['terminal']}")
        return 2
    if terminal in {"WALL_CLOCK_EXPIRED", "CHARGED_ALLOWANCE_EXHAUSTED", "A5_SUBJECT_UNAVAILABLE", "FAIL_FAST_THRESHOLD_UNREACHED", "UNREGISTERED_STRUCTURAL_FAILURE", "LAUNCH_COMPLETE"}:
        terminal = persist(args.out, manifest, schedule, params)
        print(f"TERMINAL: {terminal}")
        return 0 if terminal == "LAUNCH_COMPLETE" else 2
    if args.sweep > 1 and not any(entry["role"] == "post-sweep" and entry["sweep_id"] == args.sweep - 1 for entry in manifest["usage_evidence"]):
        raise LaunchViolation("usage-post-evidence-missing")
    pending = terminal == "REPLACEMENT_PENDING"
    oracle_raw: bytes | None = None
    oracle_digest: str | None = None
    oracle_calls = 0
    probe_times: list[datetime.datetime] = []
    if pending:
        if args.resume_oracle is None:
            raise LaunchViolation("resume-oracle-missing")
        oracle_raw, oracle_digest, oracle_calls, probe_times = load_resume_oracle(args.resume_oracle, usage_digest, params)
        if any(entry["sha256"] == oracle_digest for entry in manifest["resume_oracles"]):
            raise LaunchViolation("resume-oracle-reused")
        if consumed_probe_calls(manifest) + oracle_calls > params["venue_tolerance"]["resume_oracle"]["probe_budget_session_equivalents"]:
            raise LaunchViolation("resume-oracle-probe-budget-exhausted")
    elif args.resume_oracle is not None:
        raise LaunchViolation("resume-oracle-unexpected")
    validate_settlement_admission(manifest, usage, params, probe_times)
    if not usage_gate(usage, args.sweep, params, tpp_gate):
        raise LaunchViolation("usage-budget-gate-refused")
    if args.dry_run:
        print(f"DRY_RUN: sweep={args.sweep} strict-percent-budget-gate=PASS")
        return 0
    if pending:
        assert oracle_raw is not None and oracle_digest is not None
        manifest["resume_oracles"].append({"sha256": oracle_digest, "bytes_base64": base64.b64encode(oracle_raw).decode(), "attempt_ids": [], "consumed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "probe_calls": oracle_calls})
    append_usage(manifest, usage_raw, usage, usage_digest, "resume" if pending else "pre-sweep", args.sweep, params)
    closure_at = datetime.datetime.now(datetime.timezone.utc)
    closure = closure_payload(manifest, schedule, params, args.out, usage_digest, args.sweep, closure_at)
    if manifest["calendar"] is None and "calendar" in closure:
        manifest["calendar"] = closure["calendar"]
    append_closure_receipt(manifest, closure, args.sweep, closure_at)
    if not closure["passed"]:
        manifest["terminal"] = "CALIBRATION_DRIFT_OVER_BUDGET"
        write_json(args.out / MANIFEST_NAME, manifest)
        print("TERMINAL: CALIBRATION_DRIFT_OVER_BUDGET")
        return 2
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


def self_test_adversarial() -> None:
    """Exercise the full adversarial input, recovery, custody, and calendar matrix."""
    schedule, params = load_inputs(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    with tempfile.TemporaryDirectory(prefix="iter0112-launch-v4-") as temporary:
        root = pathlib.Path(temporary)
        now = datetime.datetime.now(datetime.timezone.utc)
        reset = (now + datetime.timedelta(days=1)).isoformat()

        def usage(name: str, used: int = 10, observed: datetime.datetime | None = None) -> pathlib.Path:
            path = root / name
            payload = {"source": "usage", "meter_id": "current_week_all_models", "observed_at": (observed or now).isoformat(), "value": name, "attested_by": "self-test", "used_percent": used, "display_resolution_percent": 1, "reset_at": reset, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": None, "current_session_percent": None}}
            path.write_bytes(canonical_bytes(payload)); return path

        def expect(path: pathlib.Path, reason: str) -> None:
            try:
                load_usage_evidence(path, params)
            except LaunchViolation as exc:
                assert reason in str(exc)
            else:
                raise AssertionError(f"{reason} accepted")

        valid = usage("valid.json")
        raw, evidence, digest = load_usage_evidence(valid, params)
        assert used_percent_upper({**evidence, "used_percent": 100}) == 100
        assert not usage_gate(evidence, 1, params, 1_000_000) and usage_gate(evidence, 1, params, 1_000_000_000)
        def evidence_raw(value: str, reset_at: str, used: int, observed_at: datetime.datetime) -> bytes:
            return canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": observed_at.isoformat(), "value": value, "attested_by": "self-test", "used_percent": used, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
        old_reset, new_reset = (now + datetime.timedelta(days=1)).isoformat(), (now + datetime.timedelta(days=2)).isoformat()
        def capture(raw: bytes, consumed_at: datetime.datetime) -> dict[str, object]:
            return capture_entry(raw, hashlib.sha256(raw).hexdigest(), consumed_at)
        old_pre = evidence_raw("old-pre", old_reset, 5, now - datetime.timedelta(seconds=250))
        old_settle = evidence_raw("old-settle", old_reset, 8, now - datetime.timedelta(seconds=230))
        old_usage = evidence_raw("old-usage", old_reset, 10, now - datetime.timedelta(seconds=200))
        new_pre = evidence_raw("new-pre", new_reset, 2, now - datetime.timedelta(seconds=150))
        new_settle = evidence_raw("new-settle", new_reset, 5, now - datetime.timedelta(seconds=130))
        fresh_epoch = evidence_raw("fresh-epoch", new_reset, 6, now - datetime.timedelta(seconds=1))
        transition = {"calibrations": [{"pre_capture": capture(old_pre, now - datetime.timedelta(seconds=250)), "settlement_captures": [capture(old_settle, now - datetime.timedelta(seconds=229)), capture(old_settle, now - datetime.timedelta(seconds=229))], "attempts": []}, {"pre_capture": capture(new_pre, now - datetime.timedelta(seconds=150)), "settlement_captures": [capture(new_settle, now - datetime.timedelta(seconds=129)), capture(new_settle, now - datetime.timedelta(seconds=129))], "attempts": []}], "calibration_ledger": {"epochs": [], "unassigned_attempts": []}, "settlements": [], "usage_evidence": [{"sha256": hashlib.sha256(old_usage).hexdigest(), "bytes_base64": base64.b64encode(old_usage).decode(), "role": "post-sweep", "sweep_id": 1, "consumed_at": (now - datetime.timedelta(seconds=200)).isoformat()}]}
        append_usage(transition, fresh_epoch, decode_usage_evidence(fresh_epoch, params), hashlib.sha256(fresh_epoch).hexdigest(), "pre-sweep", 1, params)
        assert transition["usage_evidence"][-1]["sha256"] == hashlib.sha256(fresh_epoch).hexdigest()
        for name, bad_reset, reason in (("reused", old_reset, "usage-evidence-reset-reused-old"), ("rise", (now + datetime.timedelta(days=1, hours=12)).isoformat(), "usage-evidence-reset-with-rise")):
            broken = json.loads(json.dumps(transition))
            bad = evidence_raw(name, bad_reset, 7, now)
            try: append_usage(broken, bad, decode_usage_evidence(bad, params), hashlib.sha256(bad).hexdigest(), "pre-sweep", 1, params)
            except LaunchViolation as exc: assert str(exc) == reason
            else: raise AssertionError(f"{name} reset sequence accepted")
        def reset_manifest(reset_at: str, used: int) -> dict[str, object]:
            initial = evidence_raw("reset-initial", reset_at, used, now - datetime.timedelta(seconds=2))
            return {"calibrations": [], "calibration_ledger": {"epochs": [], "unassigned_attempts": []}, "settlements": [], "usage_evidence": [{"sha256": hashlib.sha256(initial).hexdigest(), "bytes_base64": base64.b64encode(initial).decode(), "role": "pre-sweep", "sweep_id": 1, "consumed_at": (now - datetime.timedelta(seconds=2)).isoformat()}]}
        def append_reset(manifest: dict[str, object], label: str, reset_at: str, used: int) -> None:
            candidate = evidence_raw(label, reset_at, used, now - datetime.timedelta(seconds=1))
            append_usage(manifest, candidate, decode_usage_evidence(candidate, params), hashlib.sha256(candidate).hexdigest(), "pre-sweep", 1, params)
        retreat = reset_manifest((now + datetime.timedelta(days=2)).isoformat(), 10)
        append_reset(retreat, "retreat-drop", (now + datetime.timedelta(days=1)).isoformat(), 5)
        for label, first_reset, second_reset, second_used, reason in (("retreat-rise", (now + datetime.timedelta(days=2)).isoformat(), (now + datetime.timedelta(days=1)).isoformat(), 11, "usage-evidence-reset-with-rise"), ("advance-rise", (now + datetime.timedelta(days=1)).isoformat(), (now + datetime.timedelta(days=2)).isoformat(), 11, "usage-evidence-reset-with-rise"), ("same-epoch-drop", reset, reset, 9, "usage-evidence-nonmonotone")):
            broken = reset_manifest(first_reset, 10)
            try: append_reset(broken, label, second_reset, second_used)
            except LaunchViolation as exc: assert str(exc) == reason
            else: raise AssertionError(f"{label} accepted")
        transition_cap = reset_manifest((now + datetime.timedelta(days=8)).isoformat(), 10)
        for transition in range(1, 8):
            try:
                append_reset(transition_cap, f"transition-{transition}", (now + datetime.timedelta(days=8 - transition)).isoformat(), 10 - transition)
            except LaunchViolation as exc:
                assert transition == 7 and str(exc) == "usage-evidence-reset-epochs-exceeded"
            else:
                assert transition < 7, "seventh reset transition accepted"
        for field, value, reason in (("meter_id", "wrong", "schema"), ("display_resolution_percent", 2, "numeric"), ("panel_sha256", None, "numeric"), ("auxiliary", {}, "auxiliary")):
            bad = json.loads(valid.read_bytes()); bad[field] = value; path = root / f"bad-{field}.json"; write_json(path, bad); expect(path, f"usage-evidence-{reason}")
            attestation = root / "window-attestation.json"
            write_json(attestation, {"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}})
            run_args = argparse.Namespace(sweep=1, lanes=3, out=root / "run-boundary", run_id="self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=path, resume_oracle=None, record_usage_after=False, dry_run=False)
            try: run(run_args)
            except LaunchViolation as exc: assert f"usage-evidence-{reason}" in str(exc)
            else: raise AssertionError(f"run() accepted bad {field}")
        run_args.usage_evidence = valid
        run_args.out.mkdir(parents=True)
        write_json(run_args.out / MANIFEST_NAME, {"schema": "iter0112-launch-manifest-v3"})
        try: run(run_args)
        except LaunchViolation as exc: assert str(exc) == "launch-manifest-schema-mismatch"
        else: raise AssertionError("run() accepted manifest v3")

        sessions = [f"calibration-a1-u1-{engine}" for engine in CALIBRATION_ENGINES]
        receipts = []
        for engine, label in zip(CALIBRATION_ENGINES, sessions):
            for position, task in enumerate(CALIBRATION_TASKS, 1):
                path = root / "calibration" / f"{engine}.{label}.r1" / f"t{position}.{task}" / "cli.stdout"; path.parent.mkdir(parents=True, exist_ok=True)
                receipt = canonical_bytes({"modelUsage": {engine: {"inputTokens": 40_000_000, "outputTokens": 40_000_000, "cacheCreationInputTokens": 40_000_000, "cacheReadInputTokens": 10_000_000}}})
                path.write_bytes(receipt); receipts.append({"path": str(path.relative_to(root)), "sha256": hashlib.sha256(receipt).hexdigest(), "engine": engine, "completed_at": (now - datetime.timedelta(seconds=310)).isoformat()})
        components = sum_receipts(root, receipts, calibration_receipt_layout(sessions, 1))
        p1_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "p1", "used_percent": 5, "observed_at": (now - datetime.timedelta(seconds=1_000)).isoformat(), "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
        pre_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "pre", "used_percent": 5, "observed_at": (now - datetime.timedelta(seconds=400)).isoformat(), "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
        settle_a_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "settle-a", "observed_at": (now - datetime.timedelta(seconds=125)).isoformat(), "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
        settle_b_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "settle-b", "observed_at": now.isoformat(), "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
        entry = lambda value: capture_entry(value, hashlib.sha256(value).hexdigest(), parse_iso8601(str(json.loads(value)["observed_at"]), "self-test-capture-observed-at"))
        calibration_pair = {"unit": 1, "S1": entry(settle_a_raw), "S2": entry(settle_b_raw)}
        calibration_started_at = (now - datetime.timedelta(seconds=400)).isoformat()
        calibration_attempt = {"attempt_id": 1, "status": "settled", "started_at": calibration_started_at, "epoch": reset, "captures": {"P1": entry(p1_raw), "P2": entry(pre_raw), "reset_at": reset}, "units": [{"unit": 1, "sessions": sessions, "receipts": receipts, "started_at": calibration_started_at}], "settlement_pairs": [calibration_pair], "sessions": sessions, "receipts": receipts, "session_equivalents": 3, "settlement_commit": None}
        calibration = {"reset_at": reset, "pre_capture": entry(pre_raw), "settlement_captures": [entry(settle_a_raw), entry(settle_b_raw)], "sessions": sessions, "receipts": receipts, "components": components, "tpp_chain": [{"kind": "calibration", "pre_sha256": hashlib.sha256(pre_raw).hexdigest(), "post_sha256": hashlib.sha256(settle_b_raw).hexdigest(), "receipt_digests": [receipt["sha256"] for receipt in receipts], "components": components, "draw": components["total"], "delta_percent": 5, "tpp_obs": components["total"] // 6}], "session_equivalents": 3, "attempts": [calibration_attempt]}
        manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
        manifest["calibrations"] = [calibration]; manifest["calibration_ledger"] = {"epochs": [{"reset_at": reset, "attempts": [json.loads(json.dumps(calibration_attempt))]}], "unassigned_attempts": []}; manifest["calibration_session_equivalents"] = 3
        calibration_entry_valid(calibration, root, params, manifest, schedule)
        for name, observed_at, used, accepted in (("older-equal", now - datetime.timedelta(seconds=1), 10, False), ("same-time", now, 10, False), ("later-equal", now + datetime.timedelta(seconds=1), 10, True), ("later-unequal", now + datetime.timedelta(seconds=1), 11, False)):
            candidate = decode_usage_evidence(evidence_raw(name, reset, used, observed_at), params)
            try:
                validate_settlement_admission(manifest, candidate, params, [])
            except LaunchViolation as exc:
                assert not accepted and str(exc) == "settlement-stale"
            else:
                assert accepted
        partial_between = json.loads(json.dumps(manifest))
        partial_block = partial_between["blocks"][str(schedule["blocks"][0]["replicate_id"])]
        partial_block["attempts"] = [{"attempt_id": f"{partial_block['replicate_id']}.a1", "replacement_of": None, "transport_state": "VOID", "unrun_suffix": [], "sessions": {"partial": {"completed_at": (now - datetime.timedelta(seconds=30)).isoformat()}}, "charged_session_equivalents": 6}]
        try: settlement_entry_valid({"reset_at": reset, "captures": [entry(settle_a_raw), entry(settle_b_raw)]}, partial_between, params)
        except LaunchViolation as exc: assert str(exc) == "settlement-too-early"
        else: raise AssertionError("partial call between settlement captures accepted")
        sibling_prefix = json.loads(json.dumps(manifest))
        sibling_first = canonical_bytes({**json.loads(valid.read_bytes()), "value": "sibling-prefix-first", "observed_at": (now + datetime.timedelta(seconds=10)).isoformat()})
        sibling_second = canonical_bytes({**json.loads(valid.read_bytes()), "value": "sibling-prefix-second", "observed_at": (now + datetime.timedelta(seconds=130)).isoformat()})
        sibling_settlement = {"reset_at": reset, "captures": [entry(sibling_first), entry(sibling_second)]}
        sibling_prefix["settlements"] = [sibling_settlement]
        sibling_block = sibling_prefix["blocks"][str(schedule["blocks"][0]["replicate_id"])]
        sibling_block["attempts"] = [{"attempt_id": f"{sibling_block['replicate_id']}.a1", "replacement_of": None, "transport_state": "RUNNING", "unrun_suffix": [], "sessions": {"before-first": {"completed_at": (now - datetime.timedelta(seconds=20)).isoformat()}, "after-second": {"completed_at": (now + datetime.timedelta(seconds=131)).isoformat()}}, "charged_session_equivalents": 6}]
        sibling_projected = manifest_as_of(sibling_prefix, now + datetime.timedelta(seconds=10))
        assert set(sibling_projected["blocks"][str(schedule["blocks"][0]["replicate_id"])]["attempts"][0]["sessions"]) == {"before-first"}
        try: settlement_entry_valid(sibling_settlement, sibling_prefix, params)
        except LaunchViolation as exc: assert str(exc) == "settlement-too-early"
        else: raise AssertionError("session-prefix settlement accepted a prior call")
        for mutation, reason in ((lambda item: item["settlement_captures"].__setitem__(1, dict(item["settlement_captures"][0])), "settlement"), (lambda item: item.__setitem__("reset_at", (now + datetime.timedelta(days=2)).isoformat()), "cross-epoch")):
            broken = json.loads(json.dumps(calibration)); mutation(broken)
            try: calibration_entry_valid(broken, root, params, manifest, schedule)
            except LaunchViolation as exc: assert reason in str(exc)
            else: raise AssertionError(f"{reason} calibration accepted")
        assert calibration_mix_ok(components) and calibration_mix_ok({"total": 1000, "cache_read": 973}, True)
        assert not calibration_mix_ok({"total": 1000, "cache_read": 974}) and not calibration_mix_ok({"total": 1000, "cache_read": 972}, True)
        assert tpp_gate_for_epoch(manifest, reset, params, now) == components["total"] // 6
        historical_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "historical", "observed_at": (now - datetime.timedelta(hours=6)).isoformat()})
        historical_entry = capture_entry(historical_raw, hashlib.sha256(historical_raw).hexdigest(), now - datetime.timedelta(hours=6) + datetime.timedelta(seconds=10))
        assert decode_capture(historical_entry, params)[1]["value"] == "historical"
        historical_path = root / "historical.json"; historical_path.write_bytes(historical_raw)
        expect(historical_path, "usage-evidence-stale")
        replay = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "historical", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
        replay["created_at"] = (now - datetime.timedelta(hours=6)).isoformat()
        replay["usage_evidence"] = [{"sha256": historical_entry["sha256"], "bytes_base64": historical_entry["bytes_base64"], "role": "resume", "sweep_id": 1, "consumed_at": historical_entry["consumed_at"]}]
        replay_root = root / "historical-reload"; replay_root.mkdir()
        write_json(replay_root / MANIFEST_NAME, replay)
        assert load_manifest(replay_root, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "historical", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))["usage_evidence"] == replay["usage_evidence"]
        closure = closure_payload(manifest, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), 1, now)
        assert closure["passed"] and closure["remaining_nominal_waves"] == 10
        replay_event = json.loads(json.dumps(manifest))
        for block in [block for block in schedule["blocks"] if block["sweep_id"] == 1][1:]:
            replay_block = replay_event["blocks"][str(block["replicate_id"])]
            replay_block["attempts"] = [{"attempt_id": f"{replay_block['replicate_id']}.a1", "replacement_of": None, "transport_state": "VOID", "unrun_suffix": [], "sessions": {"partial": {"completed_at": (now - datetime.timedelta(seconds=1)).isoformat(), "infra_affected": True}}, "charged_session_equivalents": 6}]
        assert closure_payload(replay_event, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), 1, now)["remaining_replay_waves"] == 3
        append_closure_receipt(manifest, closure, 1, now)
        validate_manifest(manifest, schedule, root, "self-test", params)
        historical_void = json.loads(json.dumps(manifest))
        for block in [block for block in schedule["blocks"] if block["sweep_id"] == 1][1:]:
            replay_block = historical_void["blocks"][str(block["replicate_id"])]
            replay_block["attempts"] = [{"attempt_id": f"{replay_block['replicate_id']}.a1", "replacement_of": None, "transport_state": "VOID", "unrun_suffix": [], "sessions": {"partial": {"completed_at": (now + datetime.timedelta(seconds=1)).isoformat(), "infra_affected": True}}, "charged_session_equivalents": 6}]
        validate_closure_receipts(historical_void, schedule, params, root)
        claimed_future = json.loads(json.dumps(historical_void))
        future_payload = closure_payload(claimed_future, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), 1, now + datetime.timedelta(seconds=2))
        assert future_payload["remaining_replay_waves"] == 3
        append_closure_receipt(claimed_future, future_payload, 1, now)
        try: validate_closure_receipts(claimed_future, schedule, params, root)
        except LaunchViolation as exc: assert str(exc) == "closure-receipt-invalid"
        else: raise AssertionError("closure receipt claimed future VOID state")
        def reject_closure(field: str, value: object) -> None:
            broken = json.loads(json.dumps(manifest))
            receipt = broken["closure_receipts"][0]
            payload = json.loads(base64.b64decode(receipt["bytes_base64"])); payload[field] = value
            payload_raw = canonical_bytes(payload); receipt["bytes_base64"] = base64.b64encode(payload_raw).decode(); receipt["sha256"] = hashlib.sha256(payload_raw).hexdigest()
            try: validate_manifest(broken, schedule, root, "self-test", params)
            except LaunchViolation as exc: assert "closure" in str(exc)
            else: raise AssertionError(f"closure {field} accepted")
        for field, value in (("used_percent_upper", 999999), ("trajectory", [-999]), ("calibration_sessions_per_epoch", -999)):
            reject_closure(field, value)
        broken_consumed = json.loads(json.dumps(manifest)); broken_consumed["closure_receipts"][0]["consumed_at"] = "not-a-timestamp"
        try: validate_manifest(broken_consumed, schedule, root, "self-test", params)
        except LaunchViolation as exc: assert "timestamp" in str(exc)
        else: raise AssertionError("closure consumed_at accepted")
        attestation = root / "window-attestation-run.json"
        attestation_raw = canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}})
        attestation.write_bytes(attestation_raw)
        pin = verify_script_inventory()
        assert "usage-capture-0112.py" in script_digests() and "../fixtures-0112/usage-endpoint-20260902-0840KST.raw.json" in script_digests() and "../fixtures-0112/usage-jitter-B-20260902-1055KST.raw.json" in script_digests()
        record_first = usage("record-settlement-first.json", 10, now - datetime.timedelta(seconds=125))
        record_second = usage("record-settlement-second.json", 10, now)
        record_fresh = usage("record-settlement-fresh.json", 10, now + datetime.timedelta(seconds=1))
        record_out = root / "record-settlement"; record_out.mkdir()
        shutil.copytree(root / "calibration", record_out / "calibration")
        record_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "record-settlement", pin, attestation_raw)
        record_calibration = json.loads(json.dumps(calibration))
        for receipt in record_calibration["receipts"] + record_calibration["attempts"][0]["receipts"] + record_calibration["attempts"][0]["units"][0]["receipts"]:
            receipt["completed_at"] = (now - datetime.timedelta(seconds=650)).isoformat()
        record_p1 = evidence_raw("record-calibration-p1", reset, 5, now - datetime.timedelta(seconds=1_250))
        record_pre = evidence_raw("record-calibration-pre", reset, 5, now - datetime.timedelta(seconds=650))
        record_settle_first = evidence_raw("record-calibration-settle-first", reset, 10, now - datetime.timedelta(seconds=450))
        record_settle_second = evidence_raw("record-calibration-settle-second", reset, 10, now - datetime.timedelta(seconds=325))
        record_calibration["pre_capture"] = entry(record_pre)
        record_calibration["settlement_captures"] = [entry(record_settle_first), entry(record_settle_second)]
        record_pair = {"unit": 1, "S1": entry(record_settle_first), "S2": entry(record_settle_second)}
        record_calibration["attempts"][0]["captures"] = {"P1": entry(record_p1), "P2": entry(record_pre), "reset_at": reset}
        record_calibration["attempts"][0]["settlement_pairs"] = [record_pair]
        record_calibration["tpp_chain"] = [{"kind": "calibration", "pre_sha256": hashlib.sha256(record_pre).hexdigest(), "post_sha256": hashlib.sha256(record_settle_second).hexdigest(), "receipt_digests": [receipt["sha256"] for receipt in record_calibration["receipts"]], "components": components, "draw": components["total"], "delta_percent": 5, "tpp_obs": components["total"] // 6}]
        record_manifest["calibrations"] = [record_calibration]; record_manifest["calibration_session_equivalents"] = 3
        record_ledger = empty_calibration_ledger("record-settlement", DEFAULT_SCHEDULE, DEFAULT_PARAMS, pin)
        record_ledger["epochs"] = [{"reset_at": reset, "attempts": json.loads(json.dumps(record_calibration["attempts"]))}]
        persist_calibration_state(record_out, record_manifest, record_ledger)
        saved_argv = sys.argv
        try:
            sys.argv = [str(HERE / "launch-0112.py"), "--out", str(record_out), "--run-id", "record-settlement", "--window-attestation", str(attestation), "--record-settlement", "--settlement-usage-evidence", str(record_first), "--settlement-usage-evidence", str(record_second)]
            assert main() == 0
        finally:
            sys.argv = saved_argv
        record_execute, record_persist, record_derive = execute_attempt, persist, derive_terminal
        def record_later_attempt(out: pathlib.Path, mutable_manifest: dict[str, object], attempt: dict[str, object], sessions: list[dict[str, object]], run_id: str, _params: dict[str, object], _lock: threading.Lock | None = None) -> str:
            session = sessions[0]
            attempt_root_path = attempt_root(out, str(attempt["attempt_id"]))
            directory = session_directory(attempt_root_path, session)
            attempt["sessions"][session_key(session)] = {"engine": session["engine"], "replicate_id": session["replicate_id"], "session_label": session_key(session), "driver_command": command_for(session, attempt_root_path, run_id), "collector_command": collector_command_for(directory), "driver_exit": 1, "driver_stdout_sha256": hashlib.sha256(b"").hexdigest(), "driver_stderr_sha256": hashlib.sha256(b"").hexdigest(), "driver_evidence_sha256": None, "status": "driver_failed", "collector_exit": None, "collector_stdout_sha256": None, "collector_stderr_sha256": None, "infra_affected": False, "a5_clean": False, "first_late_threshold_crossed": None, "rows_sha256": None, "boundary_ledger_sha256": None, "artifact_dir": str(directory.relative_to(out)), "completed_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1)).isoformat()}
            normalize(attempt, sessions)
            write_json(out / MANIFEST_NAME, mutable_manifest)
            return "STRUCTURAL_FAILURE"
        try:
            globals()["execute_attempt"] = record_later_attempt
            globals()["persist"] = lambda *_args: "REPLACEMENT_PENDING"
            record_admission = argparse.Namespace(sweep=1, lanes=3, out=record_out, run_id="record-settlement", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=record_fresh, resume_oracle=None, record_usage_after=False, dry_run=False)
            assert run(record_admission) == 2
        finally:
            globals()["execute_attempt"] = record_execute
            globals()["persist"] = record_persist
        recorded_manifest = read_json(record_out / MANIFEST_NAME)
        assert len(recorded_manifest["settlements"]) == 1
        admission = next(entry for entry in recorded_manifest["usage_evidence"] if entry["role"] == "pre-sweep" and entry["sweep_id"] == 1)
        receipt = next(receipt for receipt in recorded_manifest["closure_receipts"] if receipt["sweep_id"] == 1)
        assert admission["sha256"] == hashlib.sha256(record_fresh.read_bytes()).hexdigest() and json.loads(base64.b64decode(receipt["bytes_base64"]))["calendar_start"] == receipt["consumed_at"]
        reloaded_manifest = load_manifest(record_out, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "record-settlement", pin, attestation_raw)
        post_one = evidence_raw("record-settlement-post-one", reset, 10, now + datetime.timedelta(seconds=2))
        append_usage(reloaded_manifest, post_one, decode_usage_evidence(post_one, params), hashlib.sha256(post_one).hexdigest(), "post-sweep", 1, params)
        write_json(record_out / MANIFEST_NAME, reloaded_manifest)
        try:
            globals()["derive_terminal"] = lambda *_args: ("LAUNCH_PARTIAL", {})
            next_usage = usage("record-settlement-next.json", 10, now + datetime.timedelta(seconds=3))
            next_admission = argparse.Namespace(sweep=2, lanes=3, out=record_out, run_id="record-settlement", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=next_usage, resume_oracle=None, record_usage_after=False, dry_run=False)
            try: run(next_admission)
            except LaunchViolation as exc: assert str(exc) == "fresh-settlement-required"
            else: raise AssertionError("next admission reused a settlement after a recorded session")
        finally:
            globals()["derive_terminal"] = record_derive
        sweep_three_out = root / "sweep-three"; sweep_three_out.mkdir()
        shutil.copytree(root / "calibration", sweep_three_out / "calibration")
        sweep_three_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "sweep-three", pin, attestation_raw)
        sweep_three_manifest["calibrations"] = [json.loads(json.dumps(record_calibration))]; sweep_three_manifest["calibration_session_equivalents"] = 3
        sweep_three_ledger = empty_calibration_ledger("sweep-three", DEFAULT_SCHEDULE, DEFAULT_PARAMS, pin)
        sweep_three_ledger["epochs"] = [{"reset_at": reset, "attempts": json.loads(json.dumps(record_calibration["attempts"]))}]
        persist_calibration_state(sweep_three_out, sweep_three_manifest, sweep_three_ledger)
        sweep_three_first = usage("sweep-three-settlement-first.json", 10, now - datetime.timedelta(seconds=125))
        sweep_three_second = usage("sweep-three-settlement-second.json", 10, now)
        sweep_three_fresh = usage("sweep-three-fresh.json", 10, now + datetime.timedelta(seconds=1))
        try:
            sys.argv = [str(HERE / "launch-0112.py"), "--out", str(sweep_three_out), "--run-id", "sweep-three", "--window-attestation", str(attestation), "--record-settlement", "--settlement-usage-evidence", str(sweep_three_first), "--settlement-usage-evidence", str(sweep_three_second)]
            assert main() == 0
        finally:
            sys.argv = saved_argv
        sweep_three_manifest = load_manifest(sweep_three_out, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "sweep-three", pin, attestation_raw)
        post_two = evidence_raw("sweep-two-post", reset, 10, now + datetime.timedelta(seconds=2))
        append_usage(sweep_three_manifest, post_two, decode_usage_evidence(post_two, params), hashlib.sha256(post_two).hexdigest(), "post-sweep", 2, params)
        new_attempt(sweep_three_manifest["blocks"][str(schedule["blocks"][0]["replicate_id"])])
        write_json(sweep_three_out / MANIFEST_NAME, sweep_three_manifest)
        try:
            globals()["execute_attempt"] = lambda *_args: "VOID"
            globals()["persist"] = lambda *_args: "REPLACEMENT_PENDING"
            sweep_three_admission = argparse.Namespace(sweep=3, lanes=3, out=sweep_three_out, run_id="sweep-three", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=sweep_three_fresh, resume_oracle=None, record_usage_after=False, dry_run=False)
            assert run(sweep_three_admission) == 2
        finally:
            globals()["execute_attempt"] = record_execute
            globals()["persist"] = record_persist
        recorded_manifest = read_json(sweep_three_out / MANIFEST_NAME)
        receipt = next(receipt for receipt in recorded_manifest["closure_receipts"] if receipt["sweep_id"] == 3)
        payload = json.loads(base64.b64decode(receipt["bytes_base64"]))
        assert payload["remaining_nominal_waves"] == 6 and payload["calendar_start"] == receipt["consumed_at"]
        pending_sessions = [f"calibration-{unit}-{engine}" for unit in (1, 2) for engine in CALIBRATION_ENGINES]
        pending_receipts = [{"path": f"pending-{index}", "sha256": "a" * 64, "engine": engine, "completed_at": (now - datetime.timedelta(seconds=300)).isoformat()} for index, engine in enumerate(CALIBRATION_ENGINES * 4)]
        pending_base = {"schema": "iter0112-calibration-pending-v1", "run_id": "settle-self-test", "schedule_sha256": sha256(DEFAULT_SCHEDULE), "params_sha256": sha256(DEFAULT_PARAMS), "pin_sha256": pin, "window_attestation_sha256": hashlib.sha256(attestation_raw).hexdigest(), "pre_capture": entry(pre_raw), "sessions": pending_sessions, "receipts": pending_receipts, "unit": 2}
        legacy_restart = root / "legacy-import-restart"; legacy_restart.mkdir()
        write_json(pending_path(legacy_restart), pending_base)
        legacy_ledger = empty_calibration_ledger("settle-self-test", DEFAULT_SCHEDULE, DEFAULT_PARAMS, pin)
        original_pending_sum, original_unlink = sum_receipts, pathlib.Path.unlink
        try:
            globals()["sum_receipts"] = lambda *_args, **_kwargs: {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "total": 0}
            def interrupt_after_ledger(path: pathlib.Path, *args: object, **kwargs: object) -> None:
                if path == pending_path(legacy_restart):
                    persisted = load_calibration_ledger(legacy_restart, "settle-self-test", DEFAULT_SCHEDULE, DEFAULT_PARAMS, pin)
                    assert len(ledger_attempts(persisted)) == 1
                    raise OSError("self-test crash after pending ledger append")
                original_unlink(path, *args, **kwargs)
            pathlib.Path.unlink = interrupt_after_ledger
            try:
                import_pending_attempt(legacy_restart, legacy_ledger, params)
            except OSError as exc:
                assert str(exc) == "self-test crash after pending ledger append"
            else:
                raise AssertionError("legacy import did not stop at the ledger/unlink boundary")
            pathlib.Path.unlink = original_unlink
            restarted_legacy_ledger = load_calibration_ledger(legacy_restart, "settle-self-test", DEFAULT_SCHEDULE, DEFAULT_PARAMS, pin)
            import_pending_attempt(legacy_restart, restarted_legacy_ledger, params)
            imported_attempts = ledger_attempts(restarted_legacy_ledger)
            assert not pending_path(legacy_restart).exists() and len(imported_attempts) == 1 and imported_attempts[0]["session_equivalents"] == 6 and {unit["started_at"] for unit in imported_attempts[0]["units"]} == {pending_base["pre_capture"]["consumed_at"]}
        finally:
            pathlib.Path.unlink = original_unlink
            globals()["sum_receipts"] = original_pending_sum
        settle_args = argparse.Namespace(out=root / "settle", run_id="settle-self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, settlement_usage_evidence=[], calibration_top_up=False)
        originals = {name: globals()[name] for name in ("load_pending_calibration", "sum_receipts", "completed_sweep_receipts", "completed_sweep_receipt_layout", "closure_payload")}
        try:
            globals()["load_pending_calibration"] = lambda _out: dict(pending_base)
            globals()["sum_receipts"] = lambda *_args, **_kwargs: {"input": 40_000_000, "output": 40_000_000, "cache_create": 40_000_000, "cache_read": 10_000_000, "total": 130_000_000}
            for first_offset, latest_offset, expected in ((60, 0, "calibration-settlement-invalid"), (125, 0, "calibration-settlement-too-early"), (125, 0, "CALIBRATION_UNIDENTIFIABLE")):
                settled_percent = 10 if expected != "CALIBRATION_UNIDENTIFIABLE" else 6
                first_path = usage(f"settle-first-{expected}.json", settled_percent, now - datetime.timedelta(seconds=first_offset))
                second_path = usage(f"settle-second-{expected}.json", settled_percent, now - datetime.timedelta(seconds=latest_offset))
                pending_base["pre_capture"] = entry(pre_raw if expected != "CALIBRATION_UNIDENTIFIABLE" else canonical_bytes({**json.loads(pre_raw), "used_percent": 5}))
                if expected == "calibration-settlement-too-early":
                    pending_base["receipts"] = [{**receipt, "completed_at": (now - datetime.timedelta(seconds=100)).isoformat()} for receipt in pending_receipts]
                else:
                    pending_base["receipts"] = pending_receipts
                settle_args.settlement_usage_evidence = [first_path, second_path]
                try: run_settle_calibration(settle_args)
                except LaunchViolation as exc: assert expected in str(exc), str(exc)
                else: raise AssertionError(f"run_settle_calibration accepted {expected}")
            quiet_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "quiet-self-test", pin, attestation_raw)
            quiet_manifest["calibrations"] = [calibration]; quiet_manifest["calibration_ledger"] = {"epochs": [{"reset_at": reset, "attempts": json.loads(json.dumps(calibration["attempts"]))}], "unassigned_attempts": []}; quiet_manifest["calibration_session_equivalents"] = 3
            quiet_usage = usage("quiet-inequality.json", 11)
            quiet_args = argparse.Namespace(sweep=1, lanes=3, out=root / "quiet", run_id="quiet-self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=quiet_usage, resume_oracle=None, record_usage_after=False, dry_run=False)
            quiet_args.out.mkdir(); write_json(quiet_args.out / MANIFEST_NAME, {"schema": "self-test"})
            globals()["load_pending_calibration"] = originals["load_pending_calibration"]
            original_load_manifest = globals()["load_manifest"]
            globals()["load_manifest"] = lambda *_args: json.loads(json.dumps(quiet_manifest))
            try: run(quiet_args)
            except LaunchViolation as exc: assert str(exc) == "settlement-stale"
            else: raise AssertionError("run() accepted non-settlement gate evidence")
            original_latest_settlement = globals()["latest_settlement"]
            globals()["latest_settlement"] = lambda *_args: None
            absent_args = argparse.Namespace(**{**vars(quiet_args), "dry_run": True})
            try: run(absent_args)
            except LaunchViolation as exc: assert str(exc) == "fresh-settlement-required"
            else: raise AssertionError("dry-run accepted absent settlement")
            globals()["latest_settlement"] = original_latest_settlement
            unequal_dry_args = argparse.Namespace(**{**vars(quiet_args), "dry_run": True})
            try: run(unequal_dry_args)
            except LaunchViolation as exc: assert str(exc) == "settlement-stale"
            else: raise AssertionError("dry-run accepted unequal settlement")
            valid_dry_usage = usage("quiet-later-equal.json", 10, now + datetime.timedelta(seconds=1))
            valid_dry_args = argparse.Namespace(**{**vars(quiet_args), "usage_evidence": valid_dry_usage, "dry_run": True})
            assert run(valid_dry_args) == 0
            recapture_manifest = json.loads(json.dumps(quiet_manifest))
            gate_usage = usage("quiet-settlement.json", 10, now + datetime.timedelta(seconds=1))
            recapture_args = argparse.Namespace(sweep=1, lanes=3, out=root / "quiet", run_id="quiet-self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=gate_usage, resume_oracle=root / "recapture-oracle.json", record_usage_after=False, dry_run=False)
            recapture_block = recapture_manifest["blocks"][str(schedule["blocks"][0]["replicate_id"])]
            recapture_block["attempts"] = [{"attempt_id": f"{recapture_block['replicate_id']}.a1", "replacement_of": None, "transport_state": "VOID", "unrun_suffix": [], "sessions": {"partial": {"completed_at": (now + datetime.timedelta(seconds=1)).isoformat()}}, "charged_session_equivalents": 6}]
            globals()["load_manifest"] = lambda *_args: recapture_manifest
            original_load_resume_oracle = globals()["load_resume_oracle"]
            globals()["load_resume_oracle"] = lambda *_args: (b"{}", "b" * 64, 0, [])
            try: run(recapture_args)
            except LaunchViolation as exc: assert str(exc) == "fresh-settlement-required"
            else: raise AssertionError("run() ignored a VOID attempt in the settlement census")
            globals()["load_resume_oracle"] = original_load_resume_oracle
            globals()["load_manifest"] = original_load_manifest
            post_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "post-self-test", pin, attestation_raw)
            post_manifest["calibrations"] = [calibration]; post_manifest["calibration_ledger"] = {"epochs": [{"reset_at": reset, "attempts": json.loads(json.dumps(calibration["attempts"]))}], "unassigned_attempts": []}; post_manifest["calibration_session_equivalents"] = 3
            append_usage(post_manifest, raw, evidence, digest, "pre-sweep", 1, params)
            post_usage = usage("post-usage.json", 20)
            post_args = argparse.Namespace(sweep=1, lanes=3, out=root / "post", run_id="post-self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=post_usage, resume_oracle=None, record_usage_after=True, dry_run=False)
            post_args.out.mkdir(); write_json(post_args.out / MANIFEST_NAME, {"schema": "self-test"})
            globals()["load_manifest"] = lambda *_args: post_manifest
            globals()["completed_sweep_receipt_layout"] = lambda *_args: [("synthetic", "claude-opus-5")]
            globals()["completed_sweep_receipts"] = lambda *_args: [{"path": "synthetic", "sha256": "a" * 64, "engine": "claude-opus-5", "completed_at": now.isoformat()}]
            globals()["sum_receipts"] = lambda *_args, **_kwargs: {"input": 1, "output": 1, "cache_create": 1, "cache_read": 10_000_000, "total": 10_000_003}
            globals()["closure_payload"] = lambda *_args: {"schema": "self-test", "passed": False}
            assert run(post_args) == 2 and post_manifest["terminal"] == "CALIBRATION_DRIFT_OVER_BUDGET"
            mix_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "post-self-test", pin, attestation_raw)
            mix_manifest["calibrations"] = [json.loads(json.dumps(calibration))]; mix_manifest["calibration_ledger"] = {"epochs": [{"reset_at": reset, "attempts": json.loads(json.dumps(calibration["attempts"]))}], "unassigned_attempts": []}; mix_manifest["calibration_session_equivalents"] = 3
            mix_manifest["calibrations"][0]["tpp_chain"] = mix_manifest["calibrations"][0]["tpp_chain"][:1]
            append_usage(mix_manifest, raw, evidence, digest, "pre-sweep", 1, params)
            globals()["load_manifest"] = lambda *_args: mix_manifest
            globals()["sum_receipts"] = lambda *_args, **_kwargs: {"input": 1, "output": 1, "cache_create": 1, "cache_read": 972, "total": 1000}
            assert run(post_args) == 2 and mix_manifest["terminal"] == "CALIBRATION_UNIDENTIFIABLE"
            assert mix_manifest["completed_sweeps"] == [{"sweep_id": 1, "pre_sha256": digest, "post_sha256": hashlib.sha256(post_usage.read_bytes()).hexdigest(), "receipts": [{"path": "synthetic", "sha256": "a" * 64, "engine": "claude-opus-5", "completed_at": now.isoformat()}], "components": {"input": 1, "output": 1, "cache_create": 1, "cache_read": 972, "total": 1000}, "draw": 1000}]
            partial_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "partial-self-test", pin, attestation_raw)
            partial_manifest["calibrations"] = [json.loads(json.dumps(calibration))]; partial_manifest["calibration_ledger"] = {"epochs": [{"reset_at": reset, "attempts": json.loads(json.dumps(calibration["attempts"]))}], "unassigned_attempts": []}; partial_manifest["calibrations"][0]["tpp_chain"] = partial_manifest["calibrations"][0]["tpp_chain"][:1]; partial_manifest["calibration_session_equivalents"] = 3
            partial_usage = usage("partial-later-equal.json", 10, now + datetime.timedelta(seconds=1))
            partial_args = argparse.Namespace(sweep=1, lanes=3, out=root / "partial", run_id="partial-self-test", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation, usage_evidence=partial_usage, resume_oracle=None, record_usage_after=False, dry_run=True)
            partial_args.out.mkdir(); write_json(partial_args.out / MANIFEST_NAME, {"schema": "self-test"})
            globals()["load_manifest"] = lambda *_args: partial_manifest
            globals()["completed_sweep_receipts"] = lambda *_args: (_ for _ in ()).throw(AssertionError("partial prefix evaluated as completed"))
            assert run(partial_args) == 0
        finally:
            for name, value in originals.items(): globals()[name] = value
            if "original_load_manifest" in locals(): globals()["load_manifest"] = original_load_manifest
            if "original_load_resume_oracle" in locals(): globals()["load_resume_oracle"] = original_load_resume_oracle
            if "original_latest_settlement" in locals(): globals()["latest_settlement"] = original_latest_settlement
        bracket_components = {"input": 240_000_000, "output": 240_000_000, "cache_create": 240_000_000, "cache_read": 60_000_000, "total": 780_000_000}
        bracket_originals = {name: globals()[name] for name in ("verify_script_inventory", "load_window_attestation", "capture_from_launcher", "run_calibration_batch", "sum_receipts", "closure_payload", "write_calibration_ledger")}
        bracket_sleep = time.sleep
        original_datetime = datetime.datetime
        try:
            class ControlledDateTime(datetime.datetime):
                @classmethod
                def now(cls, tz: datetime.tzinfo | None = None) -> datetime.datetime:
                    return now if tz is not None else now.replace(tzinfo=None)

            datetime.datetime = ControlledDateTime
            globals()["verify_script_inventory"] = lambda: "0" * 64
            globals()["load_window_attestation"] = lambda *_args: (canonical_bytes({"attested_by": "self-test", "source": "self-test"}), {})
            globals()["sum_receipts"] = lambda *_args, **_kwargs: dict(bracket_components)

            def run_bracket_case(name: str, deltas: list[int], closure_passes: bool, fable_moves: bool = False, fable_values: list[int | None] | None = None, imported_sessions: int = 0, reset_at: str | None = None, existing_manifest: dict[str, object] | None = None, batch_fn=None, pre_pair_invalid: bool = False, settlement_invalid: bool = False, baseline_used: int = 5, seed_ledger: dict[str, object] | None = None, seed_artifacts: pathlib.Path | None = None) -> tuple[int, dict[str, object], list[int], list[str], list[dict[str, object]]]:
                out = root / f"bracket-{name}"
                reset_at = reset_at or (now + datetime.timedelta(days=1)).isoformat()
                captured_at = now + datetime.timedelta(seconds=600)
                prior_timeline = full_timeline(existing_manifest, params) if existing_manifest is not None else []
                if seed_ledger is not None:
                    for prior_attempt in ledger_attempts(seed_ledger):
                        captures = [capture for capture in prior_attempt.get("captures", {}).values() if isinstance(capture, dict)]
                        captures.extend(capture for pair in prior_attempt.get("settlement_pairs", []) if isinstance(pair, dict) for capture in pair.values() if isinstance(capture, dict))
                        for capture in captures:
                            _raw, evidence = decode_capture(capture, params)
                            prior_timeline.append((parse_iso8601(str(capture["consumed_at"]), "self-test-prior-capture"), parse_iso8601(str(evidence["observed_at"]), "self-test-prior-observation"), evidence))
                if prior_timeline:
                    captured_at = max(captured_at, max(max(consumed_at, observed_at) for consumed_at, observed_at, _evidence in prior_timeline) + datetime.timedelta(seconds=1))
                if fable_values is None:
                    captures: list[tuple[int, int | None]] = [(baseline_used, 7), (baseline_used + 1 if pre_pair_invalid else baseline_used, 7)]
                    for unit, delta in enumerate(deltas, 1):
                        fable = 8 if fable_moves and unit == 1 else 7
                        captures.extend(((baseline_used + delta, fable), (baseline_used + delta + int(settlement_invalid and unit == 1), fable)))
                else:
                    if len(fable_values) != 2 + 2 * len(deltas):
                        raise AssertionError("fable value sequence did not cover P1/P2 and every settlement pair")
                    captures = [(baseline_used + 1 if pre_pair_invalid and index == 1 else baseline_used if index < 2 else baseline_used + deltas[(index - 2) // 2], value) for index, value in enumerate(fable_values)]
                sequence = iter(captures)
                sleeps: list[int] = []
                labels: list[str] = []
                snapshots: list[dict[str, object]] = []

                def fake_capture(_out: pathlib.Path, _sequence: int, _label: str, _params: dict[str, object]) -> tuple[bytes, dict[str, object], str, dict[str, object]]:
                    nonlocal captured_at
                    used, fable = next(sequence)
                    raw = canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": captured_at.isoformat(), "value": f"bracket-{name}", "attested_by": "self-test", "used_percent": used, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": fable, "current_session_percent": None}})
                    digest = hashlib.sha256(raw).hexdigest()
                    entry = capture_entry(raw, digest, captured_at)
                    captured_at += datetime.timedelta(seconds=600 if _label == "p1" else 125)
                    return raw, decode_usage_evidence(raw, params), digest, entry

                def fake_batch(_out: pathlib.Path, _run_id: str, unit: int, attempt_id: int, ledger: dict[str, object], attempt: dict[str, object]) -> tuple[list[str], list[dict[str, object]]]:
                    nonlocal captured_at
                    unit_labels = [f"calibration-a{attempt_id}-u{unit}-{engine}" for engine in CALIBRATION_ENGINES]
                    labels.extend(unit_labels)
                    unit_record = {"unit": unit, "sessions": [], "receipts": [], "started_at": now.isoformat()}
                    attempt["units"].append(unit_record)
                    attempt["session_equivalents"] = len(attempt["units"]) * len(CALIBRATION_ENGINES)
                    write_calibration_ledger(_out, ledger)
                    receipts: list[dict[str, object]] = []
                    for engine, label in zip(CALIBRATION_ENGINES, unit_labels):
                        attempt["sessions"].append(label)
                        unit_record["sessions"].append(label)
                        for position, task in enumerate(CALIBRATION_TASKS, 1):
                            path = _out / "calibration" / f"{engine}.{label}.r1" / f"t{position}.{task}" / "cli.stdout"
                            path.parent.mkdir(parents=True, exist_ok=True)
                            raw = canonical_bytes({"modelUsage": {engine: {"inputTokens": 40_000_000, "outputTokens": 40_000_000, "cacheCreationInputTokens": 40_000_000, "cacheReadInputTokens": 10_000_000}}})
                            path.write_bytes(raw)
                            receipt = {"path": str(path.relative_to(_out)), "sha256": hashlib.sha256(raw).hexdigest(), "engine": engine, "completed_at": (captured_at - datetime.timedelta(seconds=181)).isoformat()}
                            receipts.append(receipt)
                            attempt["receipts"].append(receipt)
                            unit_record["receipts"].append(receipt)
                            write_calibration_ledger(_out, ledger)
                    return unit_labels, receipts

                globals()["capture_from_launcher"] = fake_capture
                globals()["run_calibration_batch"] = fake_batch if batch_fn is None else batch_fn
                globals()["closure_payload"] = lambda *_args: {"schema": "self-test", "passed": closure_passes, "calendar": {"W": 1}, "tpp_gate": 1_000_000}
                time.sleep = lambda seconds: sleeps.append(seconds)
                original_write = globals()["write_calibration_ledger"]
                def capture_write(path: pathlib.Path, value: dict[str, object]) -> None:
                    snapshots.append(json.loads(json.dumps(value)))
                    original_write(path, value)
                globals()["write_calibration_ledger"] = capture_write
                if seed_artifacts is not None:
                    out.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(seed_artifacts / "calibration", out / "calibration", dirs_exist_ok=True)
                if seed_ledger is not None:
                    out.mkdir(parents=True, exist_ok=True)
                    seeded_ledger = json.loads(json.dumps(seed_ledger))
                    seeded_ledger["run_id"] = name
                    write_calibration_ledger(out, seeded_ledger)
                elif imported_sessions:
                    legacy_sessions = [f"calibration-{unit}-{engine}" for unit in (1, 2) for engine in CALIBRATION_ENGINES][:imported_sessions]
                    ledger = empty_calibration_ledger(name, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
                    legacy_raw = canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": (now - datetime.timedelta(seconds=700)).isoformat(), "value": f"bracket-{name}-legacy", "attested_by": "self-test", "used_percent": 5, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
                    legacy_entry = capture_entry(legacy_raw, hashlib.sha256(legacy_raw).hexdigest(), now - datetime.timedelta(seconds=700))
                    epoch = ledger_epoch(ledger, reset_at, create=True); assert epoch is not None
                    units = [{"unit": number, "sessions": legacy_sessions[(number - 1) * len(CALIBRATION_ENGINES):number * len(CALIBRATION_ENGINES)], "receipts": [], "started_at": now.isoformat()} for number in range(1, ceil_div(imported_sessions, len(CALIBRATION_ENGINES)) + 1)]
                    epoch["attempts"].append({"attempt_id": 1, "status": "abandoned:venue-over-budget-20260902", "started_at": now.isoformat(), "epoch": reset_at, "captures": {"P1": legacy_entry, "reset_at": reset_at}, "units": units, "settlement_pairs": [], "sessions": legacy_sessions, "receipts": [], "session_equivalents": len(units) * len(CALIBRATION_ENGINES), "settlement_commit": None})
                    out.mkdir(parents=True)
                    write_calibration_ledger(out, ledger)
                if existing_manifest is not None:
                    out.mkdir(parents=True, exist_ok=True)
                    write_json(out / MANIFEST_NAME, {"self_test": "existing-v5-manifest"})
                    carried = existing_manifest.get("calibration_ledger")
                    if seed_ledger is None and isinstance(carried, dict) and isinstance(carried.get("epochs"), list) and isinstance(carried.get("unassigned_attempts"), list):
                        ledger = empty_calibration_ledger(name, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
                        ledger["epochs"] = json.loads(json.dumps(carried["epochs"]))
                        ledger["abandoned_intents"] = json.loads(json.dumps(carried["unassigned_attempts"]))
                        write_calibration_ledger(out, ledger)
                original_load_manifest = globals()["load_manifest"]
                try:
                    if existing_manifest is not None:
                        globals()["load_manifest"] = lambda *_args: existing_manifest
                    args = argparse.Namespace(out=out, run_id=name, schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=root / "self-test-attestation.json")
                    result = run_calibrate_bracket(args)
                finally:
                    globals()["load_manifest"] = original_load_manifest
                ledger = read_json(calibration_ledger_path(out))
                assert isinstance(ledger, dict)
                globals()["write_calibration_ledger"] = original_write
                return result, ledger, sleeps, labels, snapshots

            live_pending_out = root / "live-pending-import"; live_pending_out.mkdir()
            live_pending_bytes = PENDING_FIXTURE.read_bytes()
            pending_path(live_pending_out).write_bytes(live_pending_bytes)
            shutil.copytree(PENDING_RECEIPT_FIXTURE, live_pending_out / "calibration")
            live_pending_ledger = empty_calibration_ledger("live-pending", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            import_pending_attempt(live_pending_out, live_pending_ledger, params)
            imported = ledger_attempts(live_pending_ledger)
            assert len(imported) == 1 and imported[0]["status"] == "abandoned:venue-over-budget-20260902" and imported[0]["session_equivalents"] == 6 and all(set(unit) == {"unit", "sessions", "receipts", "started_at"} for unit in imported[0]["units"])
            pending_path(live_pending_out).write_bytes(live_pending_bytes)
            import_pending_attempt(live_pending_out, live_pending_ledger, params)
            assert not pending_path(live_pending_out).exists() and len(ledger_attempts(live_pending_ledger)) == 1
            live_result, live_ledger, _sleeps, _labels, _snapshots = run_bracket_case("live-pending", [4], True, baseline_used=6, seed_ledger=live_pending_ledger, seed_artifacts=live_pending_out)
            assert live_result == 0 and [attempt["attempt_id"] for attempt in ledger_attempts(live_ledger)] == [1, 2]
            live_out = root / "bracket-live-pending"
            live_manifest = read_json(live_out / MANIFEST_NAME); assert isinstance(live_manifest, dict)
            settlement = latest_settlement(live_manifest, str(live_ledger["epochs"][-1]["reset_at"]), params); assert settlement is not None
            admission_at = parse_iso8601(str(settlement[1]["observed_at"]), "live-pending-admission") + datetime.timedelta(seconds=1)
            admission_raw = canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": admission_at.isoformat(), "value": "live-pending-first-admission", "attested_by": "self-test", "used_percent": settlement[1]["used_percent"], "display_resolution_percent": 1, "reset_at": settlement[1]["reset_at"], "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
            admission_path = live_out / "live-pending-first-admission.json"; admission_path.write_bytes(admission_raw)
            assert not account_consumed_after(live_manifest, settlement[2], settlement[5]), account_consumption_times(live_manifest)
            validate_settlement_admission(live_manifest, decode_usage_evidence(admission_path.read_bytes(), params), params, [])
            live_score_spec = importlib.util.spec_from_file_location("iter0112_live_pending_scorer", HERE / "score-0112.py")
            assert live_score_spec is not None and live_score_spec.loader is not None
            live_scorer = importlib.util.module_from_spec(live_score_spec); live_score_spec.loader.exec_module(live_scorer)
            live_scorer.initialize_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            live_scorer.verify_calibrations(live_manifest, schedule, params, live_out)
            contaminated, contaminated_ledger, _sleeps, _labels, _snapshots = run_bracket_case("contaminated", [4], True, fable_moves=True)
            contaminated_attempts = contaminated_ledger["epochs"][-1]["attempts"]
            assert contaminated == 2 and contaminated_attempts[-1]["status"] == "abandoned:fable-meter-moved" and contaminated_attempts[-1]["session_equivalents"] == 3
            contaminated_reloaded = load_calibration_ledger(root / "bracket-contaminated", "contaminated", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            calibration_attempt_valid(contaminated_reloaded["epochs"][-1]["attempts"][-1], reset, root / "bracket-contaminated", params)
            settlement_abandoned, settlement_ledger, _sleeps, _labels, _snapshots = run_bracket_case("settlement-invalid", [4], True, settlement_invalid=True)
            assert settlement_abandoned == 2 and settlement_ledger["epochs"][-1]["attempts"][-1]["status"] == "abandoned:settlement-invalid"
            settlement_reloaded = load_calibration_ledger(root / "bracket-settlement-invalid", "settlement-invalid", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            calibration_attempt_valid(settlement_reloaded["epochs"][-1]["attempts"][-1], reset, root / "bracket-settlement-invalid", params)
            null_settled, null_ledger, _sleeps, _labels, _snapshots = run_bracket_case("fable-null-stable", [4], True, fable_values=[None, None, None, None])
            null_moved, null_moved_ledger, _sleeps, _labels, _snapshots = run_bracket_case("fable-null-moved", [4], True, fable_values=[None, None, 7, 7])
            assert null_settled == 0 and null_ledger["epochs"][-1]["attempts"][-1]["status"] == "settled"
            assert null_moved == 2 and null_moved_ledger["epochs"][-1]["attempts"][-1]["status"] == "abandoned:fable-meter-moved"
            for name, ledger in (("fable-null-stable", null_ledger), ("fable-null-moved", null_moved_ledger)):
                reloaded = load_calibration_ledger(root / f"bracket-{name}", name, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
                calibration_attempt_valid(reloaded["epochs"][-1]["attempts"][-1], reset, root / f"bracket-{name}", params)
            existing_pre_pair = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "existing-pre-pair", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            existing_pre_pair["calibrations"] = [json.loads(json.dumps(calibration))]
            existing_pre_pair["calibrations"][0]["tpp_chain"] = existing_pre_pair["calibrations"][0]["tpp_chain"][:1]
            existing_pre_pair["calibration_ledger"] = {"epochs": [{"reset_at": reset, "attempts": json.loads(json.dumps(calibration["attempts"]))}], "unassigned_attempts": []}
            existing_pre_pair["calibration_session_equivalents"] = 3
            existing_pre_pair_result, _existing_pre_pair_ledger, _sleeps, _labels, _snapshots = run_bracket_case("existing-pre-pair", [4], True, existing_manifest=existing_pre_pair, pre_pair_invalid=True, baseline_used=10, seed_artifacts=root)
            assert existing_pre_pair_result == 2
            globals()["write_calibration_ledger"] = bracket_originals["write_calibration_ledger"]
            reloaded_pre_pair = load_manifest(root / "bracket-existing-pre-pair", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "existing-pre-pair", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            assert reloaded_pre_pair["calibration_ledger"] == existing_pre_pair["calibration_ledger"]
            persisted_pre_pair = reloaded_pre_pair["calibration_ledger"]["epochs"][-1]["attempts"][-1]
            calibration_attempt_valid(persisted_pre_pair, reset, root / "bracket-existing-pre-pair", params)
            topped_up, topup_ledger, topup_sleeps, topup_labels, snapshots = run_bracket_case("topup", [2, 4], True)
            topup_attempts = topup_ledger["epochs"][-1]["attempts"]
            assert topped_up == 0 and topup_attempts[-1]["status"] == "settled" and topup_sleeps == [600, 180, 125, 180, 125] and len(topup_labels) == len(set(topup_labels)) == 6
            assert any(snapshot.get("epochs") and snapshot["epochs"][-1]["attempts"][-1]["captures"].get("P1") for snapshot in snapshots)
            assert any(snapshot.get("epochs") and snapshot["epochs"][-1]["attempts"][-1]["session_equivalents"] == len(CALIBRATION_ENGINES) for snapshot in snapshots)
            assert any(snapshot.get("epochs") and snapshot["epochs"][-1]["attempts"][-1]["settlement_pairs"] and "S1" in snapshot["epochs"][-1]["attempts"][-1]["settlement_pairs"][-1] and "S2" not in snapshot["epochs"][-1]["attempts"][-1]["settlement_pairs"][-1] for snapshot in snapshots)
            reset_epoch_manifest = read_json(root / "bracket-topup" / MANIFEST_NAME)
            assert isinstance(reset_epoch_manifest, dict)
            reset_epoch_manifest["calendar"]["root_age_hours"] = 168
            reset_epoch_ledger = json.loads(json.dumps(topup_ledger)); reset_epoch_ledger["generation"] -= 1
            reset_epoch = (now + datetime.timedelta(days=8)).isoformat()
            reset_result, _reset_ledger, _sleeps, reset_labels, _snapshots = run_bracket_case("settlement-then-reset", [4], True, reset_at=reset_epoch, existing_manifest=reset_epoch_manifest, seed_ledger=reset_epoch_ledger, seed_artifacts=root / "bracket-topup")
            assert reset_result == 0 and len(reset_labels) == len(CALIBRATION_ENGINES) and [calibration["reset_at"] for calibration in reset_epoch_manifest["calibrations"]] == [reset, reset_epoch]
            def snapshot_attempt(snapshot: dict[str, object]) -> dict[str, object] | None:
                epochs = snapshot.get("epochs")
                if not isinstance(epochs, list) or not epochs or not isinstance(epochs[-1], dict) or not isinstance(epochs[-1].get("attempts"), list) or not epochs[-1]["attempts"]:
                    return None
                attempt = epochs[-1]["attempts"][-1]
                return attempt if isinstance(attempt, dict) else None

            recovery_fixtures = {
                "pre-p1": next(snapshot for snapshot in snapshots if snapshot.get("pending_attempt") is not None and not snapshot.get("epochs")),
                "p1": next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and "P1" in attempt["captures"] and "P2" not in attempt["captures"]),
                "p2": next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and "P2" in attempt["captures"] and not attempt["sessions"]),
                "unit-reserved": next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and attempt["units"] and not attempt["sessions"]),
                "s1": next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and attempt["settlement_pairs"] and "S1" in attempt["settlement_pairs"][-1] and "S2" not in attempt["settlement_pairs"][-1]),
                "s2": next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and attempt["settlement_pairs"] and "S2" in attempt["settlement_pairs"][-1] and attempt["status"] == "open"),
                "commit": next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and attempt["status"] == "open" and isinstance(attempt["settlement_commit"], dict)),
            }
            settled_ledger_snapshot = next(snapshot for snapshot in snapshots if (attempt := snapshot_attempt(snapshot)) is not None and attempt["status"] == "settled" and isinstance(attempt["settlement_commit"], dict))
            settled_ledger_root = root / "existing-root-settled-ledger"; settled_ledger_root.mkdir()
            shutil.copytree(root / "bracket-topup" / "calibration", settled_ledger_root / "calibration")
            settled_ledger_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "existing-root-settled-ledger", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            write_json(settled_ledger_root / MANIFEST_NAME, settled_ledger_manifest)
            settled_ledger = json.loads(json.dumps(settled_ledger_snapshot)); settled_ledger["run_id"] = "existing-root-settled-ledger"
            write_calibration_ledger(settled_ledger_root, settled_ledger)
            strict_validation_calls: list[object] = []
            original_validate_manifest = globals()["validate_manifest"]
            try:
                def validate_recovered_settlement(candidate: dict[str, object], *_args: object) -> None:
                    assert len(candidate["calibrations"]) == 1 and len(candidate["closure_receipts"]) == 1
                    strict_validation_calls.append(None)
                globals()["validate_manifest"] = validate_recovered_settlement
                recovered_settled = load_manifest(settled_ledger_root, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "existing-root-settled-ledger", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
                republished_settled = load_manifest(settled_ledger_root, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "existing-root-settled-ledger", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            finally:
                globals()["validate_manifest"] = original_validate_manifest
            assert len(strict_validation_calls) == 2 and republished_settled["calibrations"] == recovered_settled["calibrations"] and republished_settled["closure_receipts"] == recovered_settled["closure_receipts"]
            score_spec = importlib.util.spec_from_file_location("iter0112_recovery_scorer", HERE / "score-0112.py")
            assert score_spec is not None and score_spec.loader is not None
            recovery_scorer = importlib.util.module_from_spec(score_spec); score_spec.loader.exec_module(recovery_scorer)
            recovery_scorer.initialize_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            rootless_retry, _retry_ledger, _sleeps, retry_labels, _snapshots = run_bracket_case("contaminated-retry", [4], True, seed_ledger=contaminated_reloaded, seed_artifacts=root / "bracket-contaminated", baseline_used=9)
            retry_manifest = read_json(root / "bracket-contaminated-retry" / MANIFEST_NAME)
            assert rootless_retry == 0 and len(retry_labels) == len(CALIBRATION_ENGINES) and isinstance(retry_manifest, dict)
            recovery_scorer.verify_calibrations(retry_manifest, schedule, params, root / "bracket-contaminated-retry")
            retry_reset = (now + datetime.timedelta(days=8)).isoformat()
            existing_pre_pair["calendar"] = {"W": 2, "root_age_hours": 336}
            existing_retry, _retry_ledger, _sleeps, retry_labels, _snapshots = run_bracket_case("existing-pre-pair-retry", [4], True, reset_at=retry_reset, existing_manifest=existing_pre_pair, seed_artifacts=root)
            assert existing_retry == 0 and len(retry_labels) == len(CALIBRATION_ENGINES)
            recovery_scorer.verify_calibrations(existing_pre_pair, schedule, params, root / "bracket-existing-pre-pair-retry")
            for boundary, snapshot in recovery_fixtures.items():
                recovery_artifacts = root / "bracket-topup"
                result, _ledger, _sleeps, _labels, _snapshots = run_bracket_case(f"recovery-{boundary}", [4], True, seed_ledger=snapshot, seed_artifacts=recovery_artifacts, baseline_used=9)
                assert result == 0
                recovered_manifest = read_json(root / f"bracket-recovery-{boundary}" / MANIFEST_NAME)
                assert isinstance(recovered_manifest, dict)
                if boundary != "commit":
                    recovery_scorer.verify_calibrations(recovered_manifest, schedule, params, root / f"bracket-recovery-{boundary}")
                else:
                    assert len(recovered_manifest["calibrations"]) == 1 and recovered_manifest["closure_receipts"]
            commit_existing = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "recovery-commit-existing", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            commit_result, _commit_ledger, _sleeps, commit_labels, _snapshots = run_bracket_case("recovery-commit-existing", [4], True, existing_manifest=commit_existing, seed_ledger=recovery_fixtures["commit"], seed_artifacts=root / "bracket-topup", baseline_used=9)
            assert commit_result == 0 and not commit_labels and len(commit_existing["calibrations"]) == 1 and commit_existing["closure_receipts"]
            for boundary, snapshot in recovery_fixtures.items():
                restart_root = root / f"restart-{boundary}"; restart_root.mkdir()
                shutil.copytree(root / "bracket-topup" / "calibration", restart_root / "calibration")
                restart_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, f"restart-{boundary}", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
                write_json(restart_root / MANIFEST_NAME, restart_manifest)
                restart_ledger = json.loads(json.dumps(snapshot)); restart_ledger["run_id"] = f"restart-{boundary}"
                write_calibration_ledger(restart_root, restart_ledger)

                class DelayedRestartDateTime(ControlledDateTime):
                    @classmethod
                    def now(cls, tz: datetime.tzinfo | None = None) -> datetime.datetime:
                        delayed = now + datetime.timedelta(seconds=params["venue_tolerance"]["usage_evidence"]["freshness_seconds"] + 1)
                        return delayed if tz is not None else delayed.replace(tzinfo=None)

                prior_datetime = datetime.datetime
                try:
                    datetime.datetime = DelayedRestartDateTime
                    if boundary == "commit":
                        original_validate_manifest = globals()["validate_manifest"]
                        try:
                            globals()["validate_manifest"] = lambda candidate, *_args: (_ for _ in ()).throw(AssertionError("settled commit was not published before validation")) if not candidate["calibrations"] or not candidate["closure_receipts"] else None
                            reloaded = load_manifest(restart_root, DEFAULT_SCHEDULE, DEFAULT_PARAMS, f"restart-{boundary}", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
                        finally:
                            globals()["validate_manifest"] = original_validate_manifest
                    else:
                        reloaded = load_manifest(restart_root, DEFAULT_SCHEDULE, DEFAULT_PARAMS, f"restart-{boundary}", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
                finally:
                    datetime.datetime = prior_datetime
                repaired_ledger = load_calibration_ledger(restart_root, f"restart-{boundary}", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
                assert reloaded["calibration_ledger"] == calibration_ledger_projection(repaired_ledger) and reloaded["calibration_ledger_generation"] == repaired_ledger["generation"] and repaired_ledger["pending_attempt"] is None
            recovery_out = root / "bracket-recovery"; recovery_out.mkdir()
            recovery_ledger = empty_calibration_ledger("recovery", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            recovered_p1 = {"attempt_id": 2, "status": "open", "started_at": now.isoformat(), "epoch": None, "captures": {}, "units": [], "settlement_pairs": [], "sessions": [], "receipts": [], "session_equivalents": 0, "settlement_commit": None}
            recovery_ledger["pending_attempt"] = recovered_p1
            write_calibration_ledger(recovery_out, recovery_ledger)
            recovered = load_calibration_ledger(recovery_out, "recovery", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            recover_open_calibration_attempts(recovery_out, recovered, params)
            assert recovered["pending_attempt"] is None and recovered["abandoned_intents"] == [recovered_p1 | {"status": "abandoned:interrupted"}]
            session_label = "calibration-a3-u1-claude-opus-5"
            session_path = recovery_out / "calibration" / f"claude-opus-5.{session_label}.r1" / "t1.smoke-1" / "cli.stdout"
            session_path.parent.mkdir(parents=True)
            session_raw = canonical_bytes({"modelUsage": {"claude-opus-5": {"inputTokens": 1, "outputTokens": 1, "cacheCreationInputTokens": 1, "cacheReadInputTokens": 100}}})
            session_path.write_bytes(session_raw)
            interrupted = {"attempt_id": 3, "status": "open", "started_at": now.isoformat(), "epoch": reset, "captures": {"P1": entry(p1_raw), "reset_at": reset}, "units": [{"unit": 1, "sessions": [session_label], "receipts": [], "started_at": now.isoformat()}], "settlement_pairs": [], "sessions": [session_label], "receipts": [], "session_equivalents": 3, "settlement_commit": None}
            epoch = ledger_epoch(recovered, reset, create=True); assert epoch is not None; epoch["attempts"].append(interrupted)
            write_calibration_ledger(recovery_out, recovered)
            restarted = load_calibration_ledger(recovery_out, "recovery", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            recover_open_calibration_attempts(recovery_out, restarted, params)
            partial = restarted["epochs"][-1]["attempts"][-1]
            assert partial["status"] == "abandoned:interrupted" and partial["session_equivalents"] == len(CALIBRATION_ENGINES)
            s1_label = "calibration-a4-u1-claude-opus-5"
            s1_receipts: list[dict[str, object]] = []
            for position, task in enumerate(CALIBRATION_TASKS, 1):
                path = recovery_out / "calibration" / f"claude-opus-5.{s1_label}.r1" / f"t{position}.{task}" / "cli.stdout"; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(session_raw)
                s1_receipts.append({"path": str(path.relative_to(recovery_out)), "sha256": hashlib.sha256(session_raw).hexdigest(), "engine": "claude-opus-5", "completed_at": now.isoformat()})
            s1_only = {"attempt_id": 4, "status": "abandoned:interrupted", "started_at": now.isoformat(), "epoch": reset, "captures": {"P1": entry(p1_raw), "P2": entry(pre_raw), "reset_at": reset}, "units": [{"unit": 1, "sessions": [s1_label], "receipts": s1_receipts, "started_at": now.isoformat()}], "settlement_pairs": [{"unit": 1, "S1": entry(settle_a_raw)}], "sessions": [s1_label], "receipts": s1_receipts, "session_equivalents": 3, "settlement_commit": None}
            calibration_attempt_valid(s1_only, reset, recovery_out, params)
            settled_after_restart = json.loads(json.dumps(calibration))
            settled_after_restart["tpp_chain"] = settled_after_restart["tpp_chain"][:1]
            settled_after_restart["attempts"] = [partial, json.loads(json.dumps(calibration_attempt))]
            settled_after_restart["session_equivalents"] = 6
            restarted_epoch = ledger_epoch(restarted, reset); assert restarted_epoch is not None; restarted_epoch["attempts"].append(settled_after_restart["attempts"][1])
            shutil.copytree(root / "calibration", recovery_out / "calibration", dirs_exist_ok=True)
            recovery_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "recovery", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            recovery_manifest["calibrations"] = [settled_after_restart]
            sync_manifest_calibration_ledger(recovery_manifest, restarted)
            bracket_sum = globals()["sum_receipts"]
            try:
                globals()["sum_receipts"] = bracket_originals["sum_receipts"]
                calibration_entry_valid(settled_after_restart, recovery_out, params, recovery_manifest, schedule)
                score_spec = importlib.util.spec_from_file_location("iter0112_recovery_scorer", HERE / "score-0112.py")
                assert score_spec is not None and score_spec.loader is not None
                recovery_scorer = importlib.util.module_from_spec(score_spec); score_spec.loader.exec_module(recovery_scorer)
                recovery_scorer.initialize_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
                recovery_scorer.verify_calibrations(recovery_manifest, schedule, params, recovery_out)
            finally:
                globals()["sum_receipts"] = bracket_sum
            cap_failed, failed_ledger, _sleeps, _labels, _snapshots = run_bracket_case("cap-fail", [1] * 10, False, imported_sessions=6)
            failed_attempts = failed_ledger["epochs"][-1]["attempts"]
            assert cap_failed == 2 and failed_attempts[-1]["status"] == "abandoned:venue-over-budget" and sum(attempt["session_equivalents"] for attempt in failed_attempts) == 36
            cap_passed, passed_ledger, _sleeps, _labels, _snapshots = run_bracket_case("cap-pass", [1] * 10, True, imported_sessions=6)
            passed_attempts = passed_ledger["epochs"][-1]["attempts"]
            assert cap_passed == 0 and passed_attempts[-1]["status"] == "settled" and sum(attempt["session_equivalents"] for attempt in passed_attempts) == 36
            for prefix in (1, 2):
                prefix_result, prefix_ledger, _sleeps, _labels, _snapshots = run_bracket_case(f"prefix-{prefix}", [1] * 11, True, imported_sessions=prefix)
                prefix_attempts = prefix_ledger["epochs"][-1]["attempts"]
                assert prefix_result == 0 and prefix_attempts[-1]["status"] == "settled" and sum(attempt["session_equivalents"] for attempt in prefix_attempts) == 36
            old_reset = (now + datetime.timedelta(days=1)).isoformat()
            fresh_reset = (now + datetime.timedelta(days=8)).isoformat()
            multi_epoch_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "multi-epoch", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test"}))
            multi_epoch_manifest["calibrations"] = [json.loads(json.dumps(calibration))]
            multi_epoch_manifest["calibration_ledger"] = {"epochs": [{"reset_at": old_reset, "attempts": json.loads(json.dumps(calibration["attempts"]))}], "unassigned_attempts": []}
            multi_epoch_manifest["calibration_session_equivalents"] = 3
            multi_epoch_manifest["calendar"] = {"W": 2, "root_age_hours": 168}
            multi_epoch_manifest["terminal"] = "REPLACEMENT_PENDING"
            multi_result, _multi_ledger, _sleeps, _labels, _snapshots = run_bracket_case("multi-epoch", [4], True, reset_at=fresh_reset, existing_manifest=multi_epoch_manifest)
            assert multi_result == 0 and [calibration["reset_at"] for calibration in multi_epoch_manifest["calibrations"]] == [old_reset, fresh_reset] and multi_epoch_manifest["calendar"]["W"] == 2 and multi_epoch_manifest["terminal"] == "REPLACEMENT_PENDING" and multi_epoch_manifest["calibration_session_equivalents"] == 6
            multi_usage = root / "multi-epoch-resume.json"
            multi_usage.write_bytes(canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": now.isoformat(), "value": "multi-epoch-resume", "attested_by": "self-test", "used_percent": 5, "display_resolution_percent": 1, "reset_at": fresh_reset, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}}))
            multi_originals = {name: globals()[name] for name in ("load_manifest", "derive_terminal", "load_resume_oracle", "validate_settlement_admission", "usage_gate")}
            try:
                globals()["load_manifest"] = lambda *_args: multi_epoch_manifest
                globals()["derive_terminal"] = lambda *_args: ("REPLACEMENT_PENDING", {})
                globals()["load_resume_oracle"] = lambda *_args: (b"{}", "1" * 64, 0, [])
                globals()["validate_settlement_admission"] = lambda *_args: None
                globals()["usage_gate"] = lambda *_args: True
                multi_admission = argparse.Namespace(sweep=1, lanes=3, out=root / "bracket-multi-epoch", run_id="multi-epoch", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=root / "self-test-attestation.json", usage_evidence=multi_usage, resume_oracle=root / "multi-epoch-oracle.json", record_usage_after=False, dry_run=True)
                assert run(multi_admission) == 0
            finally:
                for name, value in multi_originals.items(): globals()[name] = value
            def refuse_before_batch(name: str, manifest: dict[str, object], reset_at: str) -> None:
                batch_calls: list[object] = []
                def no_batch(*_args: object, **_kwargs: object) -> tuple[list[str], list[dict[str, object]]]:
                    batch_calls.append((_args, _kwargs))
                    raise AssertionError("reset-exhausted root reached model batch")
                try:
                    run_bracket_case(name, [4], True, reset_at=reset_at, existing_manifest=manifest, batch_fn=no_batch)
                except LaunchViolation as exc:
                    assert str(exc) == "usage-evidence-reset-epochs-exceeded"
                else:
                    raise AssertionError("W+1 reset accepted")
                assert not batch_calls
            def persisted_preflight_attempt(attempt_id: int, reset_at: str, p1_used: int, p2_used: int, observed_at: datetime.datetime, status: str) -> dict[str, object]:
                p1 = evidence_raw(f"preflight-{attempt_id}-p1", reset_at, p1_used, observed_at)
                p2 = evidence_raw(f"preflight-{attempt_id}-p2", reset_at, p2_used, observed_at + datetime.timedelta(seconds=1))
                return {"attempt_id": attempt_id, "status": status, "started_at": observed_at.isoformat(), "epoch": reset_at, "captures": {"P1": entry(p1), "P2": entry(p2), "reset_at": reset_at}, "units": [], "settlement_pairs": [], "sessions": [], "receipts": [], "session_equivalents": 0, "settlement_commit": None}
            e0_reset, e1_reset, e2_reset = ((now + datetime.timedelta(days=3)).isoformat(), (now + datetime.timedelta(days=2)).isoformat(), (now + datetime.timedelta(days=1)).isoformat())
            e0 = persisted_preflight_attempt(1, e0_reset, 10, 10, now - datetime.timedelta(minutes=3), "settled")
            e1 = persisted_preflight_attempt(2, e1_reset, 4, 5, now - datetime.timedelta(minutes=2), "abandoned:pre-pair-invalid")
            e2 = persisted_preflight_attempt(3, e2_reset, 2, 2, now - datetime.timedelta(minutes=1), "open")
            preflight_ledger = empty_calibration_ledger("ledger-reset-parity", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            preflight_ledger["epochs"] = [{"reset_at": e0_reset, "attempts": [e0]}, {"reset_at": e1_reset, "attempts": [e1]}, {"reset_at": e2_reset, "attempts": [e2]}]
            preflight_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "ledger-reset-parity", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test"}))
            preflight_manifest["calendar"] = {"W": 1, "root_age_hours": 168}
            preflight_out = root / "ledger-reset-parity"; preflight_out.mkdir()
            try:
                preflight_bracket_epoch(preflight_manifest, e2_reset, params, preflight_out, preflight_ledger)
            except LaunchViolation as exc:
                assert str(exc) == "usage-evidence-reset-epochs-exceeded"
            else:
                raise AssertionError("E0-settled/E1-abandoned/E2 reached a calibration batch")
            try:
                recovery_scorer.verify_reset_timeline(full_timeline({"calibration_ledger": calibration_ledger_projection(preflight_ledger), "usage_evidence": [], "settlements": []}, params), 1)
            except recovery_scorer.ScoreViolation as exc:
                assert str(exc) == "usage-evidence-reset-epochs-exceeded"
            else:
                raise AssertionError("scorer accepted E0-settled/E1-abandoned/E2")
            expiry_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "expired-bracket", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test"}))
            expiry_manifest["created_at"] = (now - datetime.timedelta(hours=168)).isoformat()
            expiry_manifest["calendar"] = {"W": 1, "root_age_hours": 168}
            expiry_calls: list[object] = []
            def no_expiry_batch(*_args: object, **_kwargs: object) -> tuple[list[str], list[dict[str, object]]]:
                expiry_calls.append((_args, _kwargs))
                raise AssertionError("exact-expiry root reached model batch")
            expired_result, _expired_ledger, _sleeps, _labels, _snapshots = run_bracket_case("exact-expiry", [4], True, existing_manifest=expiry_manifest, batch_fn=no_expiry_batch)
            assert expired_result == 2 and expiry_manifest["terminal"] == "WALL_CLOCK_EXPIRED" and not expiry_calls
            reset_limited = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "reset-limited-bracket", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test"}))
            reset_limited["calendar"] = {"W": 1, "root_age_hours": 168}
            limited_resets = [(now + datetime.timedelta(days=2)).isoformat(), (now + datetime.timedelta(days=3)).isoformat()]
            reset_limited["calibrations"] = [{"reset_at": limited_reset, "attempts": []} for limited_reset in limited_resets]
            reset_limited["calibration_ledger"] = {"epochs": [{"reset_at": limited_reset, "attempts": [persisted_preflight_attempt(index + 1, limited_reset, 10 - 5 * index, 10 - 5 * index, now - datetime.timedelta(minutes=2 - index), "abandoned:interrupted")]} for index, limited_reset in enumerate(limited_resets)], "unassigned_attempts": []}
            refuse_before_batch("w-plus-one", reset_limited, (now + datetime.timedelta(days=4)).isoformat())
            seventh_resets = [(now + datetime.timedelta(days=index + 1)).isoformat() for index in range(7)]
            seventh_ledger = empty_calibration_ledger("seventh-epoch-root-cap", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
            for index, epoch_reset in enumerate(seventh_resets, 1):
                charged = 36 if index < 7 else 33
                labels = [f"abandoned-{index}-{session}" for session in range(charged)]
                units = [{"unit": number, "sessions": labels[(number - 1) * len(CALIBRATION_ENGINES):number * len(CALIBRATION_ENGINES)], "receipts": [], "started_at": now.isoformat()} for number in range(1, charged // len(CALIBRATION_ENGINES) + 1)]
                epoch_p1 = evidence_raw(f"seventh-epoch-{index}", epoch_reset, 5, now + datetime.timedelta(seconds=index))
                seventh_ledger["epochs"].append({"reset_at": epoch_reset, "attempts": [{"attempt_id": index, "status": "abandoned:interrupted", "started_at": now.isoformat(), "epoch": epoch_reset, "captures": {"P1": entry(epoch_p1), "reset_at": epoch_reset}, "units": units, "settlement_pairs": [], "sessions": labels, "receipts": [], "session_equivalents": charged, "settlement_commit": None}]})
            seventh_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "seventh-epoch-root-cap", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
            seventh_manifest["calendar"] = {"W": 6, "root_age_hours": 168 * 6}
            seventh_manifest["calibrations"] = [{"reset_at": epoch_reset, "attempts": []} for epoch_reset in seventh_resets[:6]]
            seventh_result, seventh_completed, _sleeps, seventh_labels, _snapshots = run_bracket_case("seventh-epoch-root-cap", [4], True, reset_at=seventh_resets[-1], existing_manifest=seventh_manifest, seed_ledger=seventh_ledger)
            assert seventh_result == 0 and len(seventh_labels) == len(CALIBRATION_ENGINES) and sum(attempt["session_equivalents"] for attempt in ledger_attempts(seventh_completed)) == 252
        finally:
            for name, value in bracket_originals.items(): globals()[name] = value
            time.sleep = bracket_sleep
            datetime.datetime = original_datetime
        manifest["calibrations"][0]["tpp_chain"] = manifest["calibrations"][0]["tpp_chain"][:1]
        manifest["created_at"] = (now - datetime.timedelta(hours=169)).isoformat()
        for tpp, passed, weeks in ((2_230_279, False, 6), (4_602_438, False, 6), (5_000_000, True, 5), (10_000_000, True, 3)):
            candidate = json.loads(json.dumps(manifest)); candidate["calendar"] = None; candidate["calibrations"][0]["tpp_chain"][0]["tpp_obs"] = tpp
            closure = closure_payload(candidate, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), 1, now)
            assert closure["passed"] is passed and closure["calendar"]["W"] == weeks and closure["calendar_headroom_ms"] == int((parse_iso8601(closure["expiry"], "self-test-expiry") - parse_iso8601(closure["calendar_end"], "self-test-calendar-end")).total_seconds() * 1000)
            if tpp == 5_000_000:
                candidate["calendar"] = closure["calendar"]
                assert all(closure_payload(candidate, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), admission, now)["passed"] and closure_payload(candidate, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), admission, now)["calendar"]["W"] == 5 for admission in range(1, 4))
                coupled = json.loads(json.dumps(candidate)); coupled["calendar"]["derivation_inputs"]["tpp_input"] += 1
                try:
                    closure_payload(coupled, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), 2, now)
                except LaunchViolation as exc:
                    assert str(exc) == "calendar-pinned-input-mismatch"
                else:
                    raise AssertionError("coupled calendar/tpp mutation accepted")
        recalibration_tokens = params["venue_tolerance"]["calibration"]["accounting"]["epoch_session_cap"] * params["venue_tolerance"]["calibration"]["full_session_bound_transport_tokens"]["value"]
        recalibration_wall_ms = params["venue_tolerance"]["calibration"]["full_bracket_wall_ms"]["value"]
        assert recalibration_wall_ms == 7_237_524
        equality_tpp = ceil_div(recalibration_tokens, 99)
        equal_reset, equal_detail = simulate_calendar(now - datetime.timedelta(hours=1), now, now, 0, equality_tpp, [{"name": "admission", "tokens": 0, "active_ms": 0}], 1, recalibration_tokens, recalibration_wall_ms)
        assert not equal_reset and equal_detail["transition_timeline"][0]["used_percent_upper_after_calibration"] == 100
        wall_only, _wall_detail = simulate_calendar(now - datetime.timedelta(hours=168) + datetime.timedelta(milliseconds=recalibration_wall_ms), now, now, 0, 10**18, [{"name": "admission", "tokens": 0, "active_ms": 0}], 1, recalibration_tokens, recalibration_wall_ms)
        exact_reset, _exact_detail = simulate_calendar(now - datetime.timedelta(hours=168), now, now, 0, 10**18, [{"name": "admission", "tokens": 0, "active_ms": 0}], 1, recalibration_tokens, recalibration_wall_ms)
        exact_completion, _completion_detail = simulate_calendar(now - datetime.timedelta(hours=168), now + datetime.timedelta(days=1), now - datetime.timedelta(milliseconds=1), 0, 10**18, [{"name": "completion", "tokens": 0, "active_ms": 1}], 1, recalibration_tokens, recalibration_wall_ms)
        assert not wall_only and not exact_reset and not exact_completion
        burn_only, _burn_detail = simulate_calendar(now, now + datetime.timedelta(hours=168), now, 98, 100, [{"name": "burn", "tokens": 100, "active_ms": 0}], 1, 0, 0)
        burn_reserve, _pair_detail = simulate_calendar(now, now + datetime.timedelta(hours=168), now, 98, 100, [{"name": "burn-reserve", "tokens": [100, 1], "active_ms": 0}], 1, 0, 0)
        assert burn_only and not burn_reserve
        temporal = json.loads(json.dumps(manifest))
        temporal_attempt = temporal["calibration_ledger"]["epochs"][0]["attempts"][0]
        temporal_label = temporal_attempt["sessions"][0]
        temporal_start = now + datetime.timedelta(seconds=10)
        temporal_receipt = now + datetime.timedelta(seconds=20)
        temporal_attempt["sessions"] = [temporal_label]
        temporal_attempt["receipts"] = temporal_attempt["receipts"][:2]
        temporal_attempt["units"] = [{"unit": 1, "sessions": [temporal_label], "receipts": temporal_attempt["receipts"], "started_at": temporal_start.isoformat()}]
        for receipt in temporal_attempt["receipts"]:
            receipt["completed_at"] = temporal_receipt.isoformat()
        for point, expected in ((temporal_start - datetime.timedelta(microseconds=1), 0), (temporal_start, 1), (temporal_receipt, 1)):
            projected = manifest_as_of(temporal, point)
            attempts = projected["calibration_ledger"]["epochs"]
            actual = len(attempts[0]["attempts"][0]["sessions"]) if attempts else 0
            assert actual == expected
        sibling = json.loads(json.dumps(manifest))
        sibling["settlements"] = []
        first_settlement = latest_settlement(sibling, reset, params)
        assert first_settlement is not None
        sibling["blocks"][str(schedule["blocks"][0]["replicate_id"])]["attempts"].append({"sessions": {"same-timestamp-sibling": {"completed_at": first_settlement[5][0].isoformat()}}})
        assert account_consumed_after(sibling, first_settlement[5][0] - datetime.timedelta(microseconds=1), first_settlement[5])
    print("SELF_TEST_OK: v5 bracket custody, write-ahead interruption recovery, contamination/top-up/cap pass-fail, reset transitions, temporal-prefix closure, settlement replay, quiet admission equality, pinned-calendar closure, separate-ceiling boundary, drift/quiet/mix run paths, and partial-prefix exemption")
    return


def self_test() -> None:
    """Prove the single evidence classifier and conservative interruption charge."""
    self_test_adversarial()
    _schedule, params = load_inputs(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    now = datetime.datetime.now(datetime.timezone.utc)
    reset = (now + datetime.timedelta(days=7)).isoformat()

    def capture(label: str, used: int, fable: int = 7) -> dict[str, object]:
        raw = canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": now.isoformat(), "value": label, "attested_by": "self-test", "used_percent": used, "display_resolution_percent": 1, "reset_at": reset, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": fable, "current_session_percent": None}})
        return capture_entry(raw, hashlib.sha256(raw).hexdigest(), now)

    def attempt(status: str, captures: dict[str, object], pairs: list[dict[str, object]] = [], charged: bool = False) -> dict[str, object]:
        started = now.isoformat()
        unit = {"unit": 1, "sessions": [f"calibration-a1-u1-{engine}" for engine in CALIBRATION_ENGINES], "receipts": [], "started_at": started}
        return {"attempt_id": 1, "status": status, "started_at": started, "epoch": reset if captures else None, "captures": {**captures, "reset_at": reset} if captures else {}, "units": [unit] if charged else [], "settlement_pairs": pairs, "sessions": unit["sessions"] if charged else [], "receipts": [], "session_equivalents": 3 if charged else 0, "settlement_commit": None}

    p1, p2 = capture("p1", 5), capture("p2", 5)
    statuses = (
        ("abandoned:pre-pair-invalid", attempt("abandoned:pre-pair-invalid", {"P1": p1, "P2": capture("p2-bad", 6)})),
        ("abandoned:fable-meter-moved", attempt("abandoned:fable-meter-moved", {"P1": p1, "P2": capture("p2-fable", 5, 8)})),
        ("abandoned:settlement-invalid", attempt("abandoned:settlement-invalid", {"P1": p1, "P2": p2}, [{"unit": 1, "S1": capture("s1", 8), "S2": capture("s2", 9)}], True)),
    )
    for expected, record in statuses:
        assert calibration_status(record, reset, params) == expected, (expected, calibration_status(record, reset, params))
        calibration_attempt_valid(record, reset, pathlib.Path("."), params)
    prefixes = [
        attempt("abandoned:interrupted", {"P1": p1}),
        attempt("abandoned:interrupted", {"P1": p1, "P2": p2}),
        attempt("abandoned:interrupted", {"P1": p1, "P2": p2}, charged=True),
        attempt("abandoned:interrupted", {"P1": p1, "P2": p2}, [{"unit": 1, "S1": capture("s1-only", 8)}], True),
        attempt("abandoned:interrupted", {"P1": p1, "P2": p2}, [{"unit": 1, "S1": capture("s1", 8), "S2": capture("s2", 8)}], True),
    ]
    for record in prefixes:
        calibration_attempt_valid(record, reset, pathlib.Path("."), params)
    charged = [prefixes[2]] * 12
    assert sum(record["session_equivalents"] for record in charged) == 36 and 7 * 36 == 252
    with tempfile.TemporaryDirectory(prefix="iter0112-interrupted-") as temporary:
        root = pathlib.Path(temporary)
        ledger = empty_calibration_ledger("self-test", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
        ledger["epochs"] = [{"reset_at": reset, "attempts": [attempt("open", {"P1": p1}, charged=True)]}]
        recover_open_calibration_attempts(root, ledger, params)
        assert ledger["epochs"][0]["attempts"][0]["status"] == "abandoned:interrupted"
        assert load_calibration_ledger(root, "self-test", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)["epochs"][0]["attempts"][0]["session_equivalents"] == 3
        before_p1 = attempt("open", {})
        ledger = empty_calibration_ledger("before-p1", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
        ledger["pending_attempt"] = before_p1
        recover_open_calibration_attempts(root, ledger, params)
        assert ledger["epochs"] == [] and ledger["abandoned_intents"] == [before_p1 | {"status": "abandoned:interrupted"}]
    manifest = {"calibration_ledger": {"epochs": [{"reset_at": reset, "attempts": [prefixes[-1]]}], "unassigned_attempts": []}, "usage_evidence": [], "settlements": [], "blocks": {}, "resume_oracles": []}
    assert len(full_timeline(manifest, params)) == 4
    assert account_consumption_times(manifest).count(now) == 3

    def interrupted_epoch(attempt_id: int, epoch: str, consumed_at: datetime.datetime) -> dict[str, object]:
        raw = canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": consumed_at.isoformat(), "value": f"epoch-{attempt_id}", "attested_by": "self-test", "used_percent": 5, "display_resolution_percent": 1, "reset_at": epoch, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
        p1 = capture_entry(raw, hashlib.sha256(raw).hexdigest(), consumed_at)
        started = consumed_at.isoformat()
        sessions = [f"calibration-a{attempt_id}-u1-{engine}" for engine in CALIBRATION_ENGINES]
        return {"attempt_id": attempt_id, "status": "abandoned:interrupted", "started_at": started, "epoch": epoch, "captures": {"P1": p1, "reset_at": epoch}, "units": [{"unit": 1, "sessions": sessions, "receipts": [], "started_at": started}], "settlement_pairs": [], "sessions": sessions, "receipts": [], "session_equivalents": 3, "settlement_commit": None}

    epochs = [(now + datetime.timedelta(days=index + 1)).isoformat() for index in range(8)]
    interrupted_attempts = [interrupted_epoch(index + 1, epoch, now + datetime.timedelta(seconds=index)) for index, epoch in enumerate(epochs)]
    eight_epoch_manifest = {"calibration_ledger": {"epochs": [{"reset_at": epoch, "attempts": [attempt]} for epoch, attempt in zip(epochs, interrupted_attempts)], "unassigned_attempts": []}, "usage_evidence": [], "settlements": [], "blocks": {}, "resume_oracles": []}
    epoch_timeline = full_timeline(eight_epoch_manifest, params)
    assert len(epoch_timeline) == 8
    try:
        verify_reset_timeline(epoch_timeline, 6)
    except LaunchViolation as exc:
        assert str(exc) == "usage-evidence-reset-epochs-exceeded"
    else:
        raise AssertionError("seven interrupted epoch transitions escaped W=6")
    verify_reset_timeline(epoch_timeline, 7)
    with tempfile.TemporaryDirectory(prefix="iter0112-epoch-preflight-") as temporary:
        root = pathlib.Path(temporary)
        ledger = empty_calibration_ledger("epoch-preflight", DEFAULT_SCHEDULE, DEFAULT_PARAMS, "0" * 64)
        ledger["epochs"] = json.loads(json.dumps(eight_epoch_manifest["calibration_ledger"]["epochs"]))
        exhausted = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "epoch-preflight", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test"}))
        exhausted["calendar"] = {"W": 6, "root_age_hours": 168 * 6}
        try:
            preflight_bracket_epoch(exhausted, epochs[-1], params, root, ledger)
        except LaunchViolation as exc:
            assert str(exc) == "usage-evidence-reset-epochs-exceeded"
        else:
            raise AssertionError("W=6 preflight reached a model batch")
        rootless = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "epoch-rootless", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test"}))
        try:
            preflight_bracket_epoch(rootless, epochs[-1], params, root, ledger)
        except LaunchViolation as exc:
            assert str(exc) == "VENUE_OVER_BUDGET" and rootless["terminal"] == "VENUE_OVER_BUDGET"
        else:
            raise AssertionError("rootless W_max=6 accepted eight epochs")
    print("SELF_TEST_OK: ordered classifier, interrupted prefixes, conservative 36/36/252 charge, durable epoch timeline custody, and 7-interruption W preflight")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", type=int); parser.add_argument("--lanes", type=int, default=3); parser.add_argument("--out", type=pathlib.Path); parser.add_argument("--run-id"); parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE); parser.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS); parser.add_argument("--window-attestation", type=pathlib.Path); parser.add_argument("--usage-evidence", type=pathlib.Path); parser.add_argument("--resume-oracle", type=pathlib.Path); parser.add_argument("--record-usage-after", action="store_true"); parser.add_argument("--record-settlement", action="store_true"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--calibrate-bracket", action="store_true"); parser.add_argument("--settlement-usage-evidence", type=pathlib.Path, action="append"); parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try: self_test()
        except (AssertionError, OSError, LaunchViolation, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr); return 1
        return 0
    if args.out is None or args.run_id is None or args.window_attestation is None:
        parser.error("--out, --run-id, and --window-attestation are required unless --self-test is used")
    try:
        if args.calibrate_bracket:
            if any(value is not None for value in (args.sweep, args.usage_evidence, args.resume_oracle)) or args.record_usage_after or args.record_settlement or args.dry_run or args.settlement_usage_evidence:
                parser.error("--calibrate-bracket accepts only shared out/run/pins arguments")
            return run_calibrate_bracket(args)
        if args.record_settlement:
            if args.usage_evidence is not None or args.resume_oracle is not None or args.record_usage_after or args.dry_run or args.sweep is not None:
                parser.error("--record-settlement requires exactly two --settlement-usage-evidence values and no launch flags")
            return run_record_settlement(args)
        if args.sweep is None or args.usage_evidence is None:
            parser.error("--sweep and --usage-evidence are required for launch, record, or dry-run")
        return run(args)
    except LaunchViolation as exc:
        print(f"FAIL launch-0112: {exc}", file=sys.stderr); return 3


if __name__ == "__main__":
    raise SystemExit(main())
