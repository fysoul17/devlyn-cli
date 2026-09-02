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
import json
import os
import pathlib
import shutil
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
APPARATUS_SCRIPTS = ("sh-driver-0112.py", "boundary-ledger-0112.py", "smoke-gate-0112.py", "derive-schedule-0112.py", "g0-power-0112.py", "score-0112.py", "launch-0112.py", "usage-capture-0112.py", "../fixtures-0112/usage-endpoint-20260902-0840KST.raw.json", "../fixtures-0112/usage-jitter-B-20260902-1055KST.raw.json")
CALIBRATION_ENGINES = ("claude-opus-5", "claude-opus-4-8", "claude-sonnet-5")
CALIBRATION_TASKS = ("smoke-1", "smoke-2")
REQUIRED_PIN_TARGETS = frozenset([f"benchmark/executor-quality/scripts/{name}" if "/" not in name else f"benchmark/executor-quality/{name[3:]}" for name in APPARATUS_SCRIPTS] + ["docs/specs/iter0112/schedule.json", "docs/specs/iter0112/registered-params.json", "benchmark/executor-quality/tasks-0110-smoke/smoke-1 (whole tree)", "benchmark/executor-quality/tasks-0110-smoke/smoke-2 (whole tree)"])
STATUS_FIELDS = frozenset(("engine", "replicate_id", "session_label", "driver_command", "collector_command", "driver_exit", "driver_stdout_sha256", "driver_stderr_sha256", "driver_evidence_sha256", "status", "collector_exit", "collector_stdout_sha256", "collector_stderr_sha256", "infra_affected", "a5_clean", "first_late_threshold_crossed", "rows_sha256", "boundary_ledger_sha256", "artifact_dir", "completed_at"))
ATTEMPT_FIELDS = frozenset(("attempt_id", "replacement_of", "transport_state", "unrun_suffix", "sessions", "charged_session_equivalents"))
USAGE_FIELDS = ("source", "meter_id", "observed_at", "value", "attested_by", "used_percent", "display_resolution_percent", "reset_at", "panel_sha256", "auxiliary")
USAGE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "role", "sweep_id", "consumed_at"))
RESUME_ORACLE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "attempt_ids", "consumed_at", "probe_calls"))
CAPTURE_ENTRY_FIELDS = frozenset(("sha256", "bytes_base64", "consumed_at"))
SETTLEMENT_FIELDS = frozenset(("reset_at", "captures"))
COMPONENT_FIELDS = frozenset(("input", "output", "cache_create", "cache_read", "total"))
COMPLETED_SWEEP_FIELDS = frozenset(("sweep_id", "pre_sha256", "post_sha256", "receipts", "components", "draw"))
CALIBRATION_PENDING_NAME = "calibration-pending-0112.json"


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
    if not isinstance(venue, dict) or not isinstance(venue.get("usage_evidence"), dict) or not isinstance(venue.get("budget_gate"), dict) or not isinstance(venue.get("calendar"), dict) or not isinstance(venue.get("charged_accounting"), dict) or not isinstance(venue.get("resume_oracle"), dict) or not isinstance(venue.get("calibration"), dict) or not isinstance(venue.get("settlement"), dict) or not isinstance(venue.get("closure_check"), dict):
        raise LaunchViolation("venue-tolerance-schema-invalid")
    if venue["usage_evidence"].get("schema") != "iter0112-usage-v2" or venue["usage_evidence"].get("exact_fields") != list(USAGE_FIELDS) or venue["usage_evidence"].get("meter_id") != "current_week_all_models" or type(venue["usage_evidence"].get("freshness_seconds")) is not int:
        raise LaunchViolation("usage-evidence-schema-invalid")
    if type(venue["charged_accounting"].get("maximum_block_attempts")) is not int or venue["charged_accounting"]["maximum_block_attempts"] < 20:
        raise LaunchViolation("charged-allowance-invalid")
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


def calibration_receipt_layout(sessions: object) -> list[tuple[str, str]]:
    if not isinstance(sessions, list) or not sessions or len(sessions) % len(CALIBRATION_ENGINES):
        raise LaunchViolation("calibration-program-invalid")
    expected: list[tuple[str, str]] = []
    labels: list[str] = []
    for index, engine in enumerate(CALIBRATION_ENGINES * (len(sessions) // len(CALIBRATION_ENGINES))):
        unit = index // len(CALIBRATION_ENGINES) + 1
        label = f"calibration-{unit}-{engine}"
        labels.append(label)
        for position, task in enumerate(CALIBRATION_TASKS, 1):
            expected.append((f"calibration/{engine}.{label}.r1/t{position}.{task}/cli.stdout", engine))
    if sessions != labels:
        raise LaunchViolation("calibration-program-invalid")
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


def calibration_entry_valid(entry: object, out: pathlib.Path, params: dict[str, object], manifest: dict[str, object], schedule: dict[str, object]) -> None:
    required = {"reset_at", "pre_capture", "settlement_captures", "sessions", "receipts", "components", "tpp_chain", "session_equivalents"}
    if not isinstance(entry, dict) or set(entry) != required or not isinstance(entry.get("reset_at"), str) or not isinstance(entry.get("sessions"), list) or not isinstance(entry.get("receipts"), list) or not isinstance(entry.get("components"), dict) or not isinstance(entry.get("tpp_chain"), list) or type(entry.get("session_equivalents")) is not int:
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
    if first["used_percent"] != second["used_percent"] or second_time - first_time < datetime.timedelta(seconds=120):
        raise LaunchViolation("calibration-settlement-invalid")
    components = sum_receipts(out, entry["receipts"], calibration_receipt_layout(entry["sessions"]))
    if entry["components"] != components or not calibration_mix_ok(components):
        raise LaunchViolation("calibration-mix-invalid")
    latest_receipt = max(parse_iso8601(str(receipt["completed_at"]), "calibration-receipt-completed-at") for receipt in entry["receipts"])
    if second_time < latest_receipt + datetime.timedelta(seconds=180):
        raise LaunchViolation("calibration-settlement-too-early")
    delta = second["used_percent"] - pre["used_percent"]
    if delta < 3:
        raise LaunchViolation("calibration-delta-unidentifiable")
    if entry["session_equivalents"] != len(entry["sessions"]) or not 1 <= entry["session_equivalents"] <= params["venue_tolerance"]["calibration"]["accounting"]["max_per_epoch"]:
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
    calibrations = manifest.get("calibrations", [])
    if not isinstance(calibrations, list):
        raise LaunchViolation("launch-manifest-calibrations-invalid")
    for calibration in calibrations:
        if not isinstance(calibration, dict) or not isinstance(calibration.get("receipts"), list):
            raise LaunchViolation("launch-manifest-calibrations-invalid")
        times.extend(parse_iso8601(str(receipt.get("completed_at")), "calibration-receipt-completed-at") for receipt in calibration["receipts"] if isinstance(receipt, dict))
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
        if not isinstance(calibration, dict) or not isinstance(calibration.get("receipts"), list):
            raise LaunchViolation("manifest-as-of-invalid")
        completed_at = [latest_capture_at(calibration, "settlement_captures")]
        completed_at.extend(parse_iso8601(str(receipt.get("completed_at")), "manifest-as-of-calibration-completed-at") for receipt in calibration["receipts"] if isinstance(receipt, dict))
        if any(not isinstance(receipt, dict) for receipt in calibration["receipts"]):
            raise LaunchViolation("manifest-as-of-invalid")
        if max(completed_at) > at:
            continue
        projected_calibration = dict(calibration)
        chain = calibration.get("tpp_chain")
        if isinstance(chain, list):
            projected_calibration["tpp_chain"] = [observation for observation in chain if not isinstance(observation, dict) or evidence_at.get(observation.get("post_sha256"), at + datetime.timedelta(microseconds=1)) <= at]
        projected_calibrations.append(projected_calibration)
    projected["calibrations"] = projected_calibrations
    projected["calibration_session_equivalents"] = sum(calibration.get("session_equivalents", 0) for calibration in projected_calibrations if type(calibration.get("session_equivalents")) is int)

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
    recorded_calls = account_consumption_times(manifest_as_of(manifest, second_time))
    if any(first_time < call <= second_time for call in recorded_calls):
        raise LaunchViolation("settlement-too-early")


def latest_settlement(manifest: dict[str, object], reset_at: str, params: dict[str, object]) -> tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str] | None:
    candidates: list[tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str]] = []
    for calibration in manifest.get("calibrations", []):
        if not isinstance(calibration, dict) or calibration.get("reset_at") != reset_at:
            continue
        captures = calibration.get("settlement_captures")
        if not isinstance(captures, list) or len(captures) != 2:
            raise LaunchViolation("calibration-settlement-invalid")
        _first_raw, first = decode_capture(captures[0], params)
        _second_raw, second = decode_capture(captures[1], params)
        candidates.append((first, second, parse_iso8601(str(first["observed_at"]), "settlement-observed-at"), parse_iso8601(str(second["observed_at"]), "settlement-observed-at"), str(captures[1]["sha256"])))
    for entry in manifest.get("settlements", []):
        if not isinstance(entry, dict) or entry.get("reset_at") != reset_at:
            continue
        settlement_entry_valid(entry, manifest, params)
        first_capture, second_capture = entry["captures"]
        _first_raw, first = decode_capture(first_capture, params)
        _second_raw, second = decode_capture(second_capture, params)
        candidates.append((first, second, parse_iso8601(str(first["observed_at"]), "settlement-observed-at"), parse_iso8601(str(second["observed_at"]), "settlement-observed-at"), str(second_capture["sha256"])))
    return max(candidates, key=lambda candidate: candidate[3]) if candidates else None


def base_manifest(schedule_path: pathlib.Path, params_path: pathlib.Path, run_id: str, pin_sha: str, attestation: bytes) -> dict[str, object]:
    schedule, _params = load_inputs(schedule_path, params_path)
    return {"schema": "iter0112-launch-manifest-v4", "run_id": run_id, "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "schedule_sha256": sha256(schedule_path), "params_sha256": sha256(params_path), "script_sha256": script_digests(), "scripts_sha256_pin_file": pin_sha, "window_attestation_sha256": hashlib.sha256(attestation).hexdigest(), "window_attestation_bytes_base64": base64.b64encode(attestation).decode(), "usage_evidence": [], "calibrations": [], "settlements": [], "closure_receipts": [], "calibration_session_equivalents": 0, "resume_oracles": [], "completed_sweeps": [], "blocks": {str(block["replicate_id"]): {"replicate_id": str(block["replicate_id"]), "attempts": [], "designated_attempt": None} for block in schedule["blocks"]}, "a5": {engine: {"a5_evaluated_attempt": None, "a5_evaluated_session": None, "a5_crossed": None} for engine in MATRIX_ENGINES}, "terminal": "RUNNING"}


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
    if not isinstance(evidence_entries, list) or not isinstance(calibrations, list) or not isinstance(settlements, list) or not isinstance(manifest.get("closure_receipts"), list) or not isinstance(manifest.get("resume_oracles"), list):
        raise LaunchViolation("launch-manifest-evidence-invalid")
    for calibration in calibrations:
        calibration_entry_valid(calibration, out, params, manifest, schedule)
    for settlement in settlements:
        settlement_entry_valid(settlement, manifest, params)
    if type(manifest.get("calibration_session_equivalents")) is not int or manifest["calibration_session_equivalents"] != sum(calibration["session_equivalents"] for calibration in calibrations) or manifest["calibration_session_equivalents"] > params["venue_tolerance"]["calibration"]["accounting"]["max_per_root"]:
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
    if not isinstance(manifest, dict) or manifest.get("schema") != "iter0112-launch-manifest-v4":
        raise LaunchViolation("launch-manifest-schema-mismatch")
    expected = base_manifest(schedule_path, params_path, run_id, pin_sha, attestation)
    for field in ("run_id", "schedule_sha256", "params_sha256", "script_sha256", "scripts_sha256_pin_file", "window_attestation_sha256", "window_attestation_bytes_base64"):
        if manifest.get(field) != expected[field]:
            raise LaunchViolation(f"launch-manifest-{field}-mismatch")
    schedule, _params = load_inputs(schedule_path, params_path)
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
    timeline: list[tuple[datetime.datetime, datetime.datetime, dict[str, object]]] = []
    for calibration in manifest.get("calibrations", []):
        if isinstance(calibration, dict):
            for capture in [calibration.get("pre_capture"), *(calibration.get("settlement_captures", []) if isinstance(calibration.get("settlement_captures"), list) else [])]:
                if isinstance(capture, dict):
                    _raw, decoded = decode_capture(capture, params)
                    timeline.append((parse_iso8601(str(capture["consumed_at"]), "calibration-capture-consumed-at"), parse_iso8601(str(decoded["observed_at"]), "usage-observed-at"), decoded))
    for settlement in manifest.get("settlements", []):
        if not isinstance(settlement, dict) or not isinstance(settlement.get("captures"), list):
            raise LaunchViolation("settlement-entry-invalid")
        for capture in settlement["captures"]:
            _raw, decoded = decode_capture(capture, params)
            timeline.append((parse_iso8601(str(capture["consumed_at"]), "settlement-capture-consumed-at"), parse_iso8601(str(decoded["observed_at"]), "usage-observed-at"), decoded))
    for entry in manifest["usage_evidence"]:
        try:
            decoded = decode_usage_evidence(base64.b64decode(entry["bytes_base64"], validate=True), params)
        except (ValueError, TypeError) as exc:
            raise LaunchViolation("launch-manifest-usage-evidence-invalid") from exc
        timeline.append((parse_iso8601(str(entry["consumed_at"]), "usage-consumed-at"), parse_iso8601(str(decoded["observed_at"]), "usage-observed-at"), decoded))
    consumed_at = datetime.datetime.now(datetime.timezone.utc)
    timeline.append((consumed_at, parse_iso8601(str(evidence["observed_at"]), "usage-observed-at"), evidence))
    prior_reset: str | None = None
    prior_used: int | None = None
    seen_resets: set[str] = set()
    transitions = 0
    for _consumed, _observed, item in sorted(timeline, key=lambda value: value[:2]):
        reset_at = str(item["reset_at"])
        if prior_reset is None:
            prior_reset, prior_used = reset_at, int(item["used_percent"])
            seen_resets.add(reset_at)
        elif reset_at == prior_reset:
            if int(item["used_percent"]) < prior_used:
                raise LaunchViolation("usage-evidence-nonmonotone")
            prior_used = int(item["used_percent"])
        else:
            if reset_at in seen_resets:
                raise LaunchViolation("usage-evidence-reset-reused-old")
            if int(item["used_percent"]) > prior_used:
                raise LaunchViolation("usage-evidence-reset-with-rise")
            transitions += 1
            if transitions > params["venue_tolerance"]["calendar"]["max_reset_epochs"]:
                raise LaunchViolation("usage-evidence-reset-epochs-exceeded")
            prior_reset, prior_used = reset_at, int(item["used_percent"])
            seen_resets.add(reset_at)
    manifest["usage_evidence"].append({"sha256": digest, "bytes_base64": base64.b64encode(raw).decode(), "role": role, "sweep_id": sweep, "consumed_at": consumed_at.isoformat()})


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


def account_consumed_after(manifest: dict[str, object], observed_at: datetime.datetime) -> bool:
    return any(time > observed_at for time in account_consumption_times(manifest))


def validate_settlement_admission(manifest: dict[str, object], usage: dict[str, object], params: dict[str, object], probe_times: list[datetime.datetime]) -> None:
    settlement = latest_settlement(manifest, str(usage["reset_at"]), params)
    if settlement is None:
        raise LaunchViolation("fresh-settlement-required")
    _first, second, first_observed, second_observed, _settlement_digest = settlement
    observed_at = parse_iso8601(str(usage["observed_at"]), "usage-evidence-observed-at")
    if str(usage["reset_at"]) != str(second["reset_at"]) or usage["used_percent"] != second["used_percent"] or observed_at <= second_observed:
        raise LaunchViolation("settlement-stale")
    if any(probe_time >= first_observed for probe_time in probe_times):
        raise LaunchViolation("resume-probe-after-settlement")
    if account_consumed_after(manifest, first_observed):
        raise LaunchViolation("fresh-settlement-required")


def calibration_command(engine: str, label: str, root: pathlib.Path, run_id: str) -> list[str]:
    return [sys.executable, str(DRIVER), "--engine", engine, "--session-label", label, "--tasks", ",".join(CALIBRATION_TASKS), "--replicate", "1", "--out", str(root), "--run-id", run_id, "--smoke"]


def run_calibration_batch(out: pathlib.Path, run_id: str, unit: int) -> tuple[list[str], list[dict[str, object]]]:
    root = out / "calibration"
    sessions: list[str] = []
    receipts: list[dict[str, object]] = []
    for engine in CALIBRATION_ENGINES:
        label = f"calibration-{unit}-{engine}"
        command = calibration_command(engine, label, root, run_id)
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
    return sessions, receipts


def pending_path(out: pathlib.Path) -> pathlib.Path:
    return out / CALIBRATION_PENDING_NAME


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
    maximum = params["venue_tolerance"]["calibration"]["accounting"]["max_per_epoch"]
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


def closure_payload(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], out: pathlib.Path, bound_evidence_sha256: str, sweep: int, consumed_at: datetime.datetime) -> dict[str, object]:
    """A deterministic, integer-only worst-case admission simulation."""
    evidence = evidence_by_digest(manifest, params).get(bound_evidence_sha256)
    if evidence is None or evidence[1] > consumed_at:
        raise LaunchViolation("closure-bound-evidence-invalid")
    bound, _bound_consumed = evidence
    tpp = tpp_gate_for_epoch(manifest, str(bound["reset_at"]), params, consumed_at)
    budget, closure = params["venue_tolerance"]["budget_gate"], params["venue_tolerance"]["closure_check"]
    created = parse_iso8601(str(manifest["created_at"]), "created_at")
    expiry = created + datetime.timedelta(hours=params["venue_tolerance"]["calendar"]["root_age_hours"])
    reset_at = parse_iso8601(str(bound["reset_at"]), "reset_at")
    nominal_waves, replay_waves = int(closure["nominal_waves"]), int(closure["worst_case_replay_waves"])
    wall_ms = int(closure["max_block_wall_ms"])
    future_burns = [int(budget["first_sweep_burn_bound_transport_tokens"] if future_sweep == 1 else budget["subsequent_sweep_burn_bound_transport_tokens"]) for future_sweep in range(sweep, int(schedule["sweeps"]) + 1)]
    future_sweeps = len(future_burns)
    if nominal_waves != 2 * int(schedule["sweeps"]):
        raise LaunchViolation("closure-nominal-waves-invalid")
    remaining_nominal_waves = 2 * future_sweeps
    replay_events = consumed_replay_events(manifest, schedule, params)
    remaining_replays = max(0, replay_waves - replay_events)
    calibrations = manifest.get("calibrations")
    if not isinstance(calibrations, list):
        raise LaunchViolation("launch-manifest-calibrations-invalid")
    total_epochs = int(params["venue_tolerance"]["calendar"]["max_reset_epochs"]) + 1
    remaining_calibration_epochs = total_epochs - len(calibrations)
    if remaining_calibration_epochs < 0:
        raise LaunchViolation("calibration-session-accounting-invalid")
    transitioned = remaining_calibration_epochs == 0
    remaining_wait_ms = 0 if transitioned else int(closure["evidenced_reset_wait_ms"])
    remaining_active_ms = (remaining_nominal_waves + remaining_replays) * wall_ms
    calendar_start = consumed_at
    calendar_span_ms = remaining_active_ms + remaining_wait_ms
    calendar_end = calendar_start + datetime.timedelta(milliseconds=calendar_span_ms)
    used = used_percent_upper(bound)
    trajectory: list[int] = []
    actions: list[tuple[int, int]] = []
    reserve = int(budget["reserve_transport_tokens"])
    for index, burn in enumerate(future_burns, 1):
        wave = 2 * index - 1
        actions.append((wave, burn))
        actions.append((wave, reserve))
    replay_burn = max(future_burns, default=int(budget["subsequent_sweep_burn_bound_transport_tokens"]))
    remaining_calls = int(closure["probe_calls"]) - consumed_probe_calls(manifest)
    if remaining_calls < 0:
        raise LaunchViolation("resume-oracle-probe-budget-exhausted")
    for wave in range(remaining_nominal_waves + 1, remaining_nominal_waves + remaining_replays + 1):
        actions.extend(((wave, replay_burn), (wave, reserve)))
        calls_here, remainder = divmod(remaining_calls, remaining_replays)
        actions.extend((wave, int(closure["probe_prefix_bound_transport_tokens"])) for _ in range(calls_here + (1 if wave - remaining_nominal_waves <= remainder else 0)))
    final_wave = remaining_nominal_waves + remaining_replays
    if remaining_replays == 0 and remaining_calls:
        if final_wave == 0:
            raise LaunchViolation("closure-actions-missing")
        actions.extend((final_wave, int(closure["probe_prefix_bound_transport_tokens"])) for _ in range(remaining_calls))
    if remaining_calibration_epochs:
        if final_wave == 0:
            raise LaunchViolation("closure-actions-missing")
        actions.append((final_wave, recalibration_bound(out, manifest, params)))
    for wave, tokens in actions:
        admission_time = calendar_start + datetime.timedelta(milliseconds=calendar_span_ms * wave // final_wave)
        if not transitioned and admission_time >= reset_at:
            used, transitioned = 0, True
        used += ceil_div(tokens, tpp)
        trajectory.append(used)
    passed = max(trajectory, default=used) < 100 and calendar_end <= expiry and (transitioned or remaining_wait_ms == 0)
    calibration = calibration_for_epoch(manifest, str(bound["reset_at"]))
    if calibration is None or type(calibration.get("session_equivalents")) is not int:
        raise LaunchViolation("calibration-session-accounting-invalid")
    return {"schema": "iter0112-closure-v1", "passed": passed, "sweep_id": sweep, "bound_evidence_sha256": bound_evidence_sha256, "tpp_gate": tpp, "used_percent_upper": used_percent_upper(bound), "trajectory": trajectory, "nominal_waves": closure["nominal_waves"], "worst_case_replay_waves": closure["worst_case_replay_waves"], "worst_case_replay_placement": closure["worst_case_replay_placement"], "max_block_wall_ms": wall_ms, "probe_calls": closure["probe_calls"], "reset_at": bound["reset_at"], "reset_transitions": closure["reset_transitions"], "calendar_start": calendar_start.isoformat(), "calendar_end": calendar_end.isoformat(), "evidenced_reset_wait_ms": closure["evidenced_reset_wait_ms"], "expiry": expiry.isoformat(), "calibration_sessions_per_epoch": calibration["session_equivalents"], "remaining_nominal_sweeps": future_sweeps, "remaining_nominal_waves": remaining_nominal_waves, "remaining_replay_waves": remaining_replays, "remaining_probe_calls": remaining_calls, "remaining_calibration_epochs": remaining_calibration_epochs, "remaining_reset_wait_ms": remaining_wait_ms}


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
            if manifest["calibration_session_equivalents"] + len(pending["sessions"]) + len(CALIBRATION_ENGINES) > params["venue_tolerance"]["calibration"]["accounting"]["max_per_root"]:
                raise LaunchViolation("calibration-session-accounting-invalid")
        unit = int(pending["unit"]) + 1
        sessions, receipts = run_calibration_batch(args.out, args.run_id, unit)
        pending["sessions"].extend(sessions); pending["receipts"].extend(receipts); pending["unit"] = unit
    else:
        if args.calibration_top_up:
            raise LaunchViolation("calibration-top-up-without-base")
        if (args.out / MANIFEST_NAME).exists():
            manifest = load_manifest(args.out, args.schedule, args.params, args.run_id, pin, attestation_raw)
            if calibration_for_epoch(manifest, str(pre["reset_at"])) is not None or manifest["calibration_session_equivalents"] + len(CALIBRATION_ENGINES) > params["venue_tolerance"]["calibration"]["accounting"]["max_per_root"]:
                raise LaunchViolation("calibration-session-accounting-invalid")
        sessions, receipts = run_calibration_batch(args.out, args.run_id, 1)
        pending = {"schema": "iter0112-calibration-pending-v1", "run_id": args.run_id, "schedule_sha256": sha256(args.schedule), "params_sha256": sha256(args.params), "pin_sha256": pin, "window_attestation_sha256": hashlib.sha256(attestation_raw).hexdigest(), "pre_capture": capture_entry(raw, digest), "sessions": sessions, "receipts": receipts, "unit": 1}
    if len(pending["sessions"]) > params["venue_tolerance"]["calibration"]["accounting"]["max_per_epoch"]:
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
    if calibration_for_epoch(manifest, calibration["reset_at"]) is not None or manifest["calibration_session_equivalents"] + calibration["session_equivalents"] > params["venue_tolerance"]["calibration"]["accounting"]["max_per_root"]:
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
    append_closure_receipt(manifest, closure, sweep, closure_at)
    write_json(args.out / MANIFEST_NAME, manifest)
    pending_path(args.out).unlink()
    print(f"CALIBRATION_SETTLED: tpp_gate={chain['tpp_obs']}")
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


def self_test() -> None:
    """Exercise the v4 input boundary before the legacy transport fixtures below."""
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
            return canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": observed_at.isoformat(), "value": value, "attested_by": "self-test", "used_percent": used, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": None, "current_session_percent": None}})
        old_reset, new_reset = (now + datetime.timedelta(days=1)).isoformat(), (now + datetime.timedelta(days=2)).isoformat()
        def capture(raw: bytes, consumed_at: datetime.datetime) -> dict[str, object]:
            return capture_entry(raw, hashlib.sha256(raw).hexdigest(), consumed_at)
        old_pre = evidence_raw("old-pre", old_reset, 5, now - datetime.timedelta(seconds=250))
        old_settle = evidence_raw("old-settle", old_reset, 8, now - datetime.timedelta(seconds=230))
        old_usage = evidence_raw("old-usage", old_reset, 10, now - datetime.timedelta(seconds=200))
        new_pre = evidence_raw("new-pre", new_reset, 2, now - datetime.timedelta(seconds=150))
        new_settle = evidence_raw("new-settle", new_reset, 5, now - datetime.timedelta(seconds=130))
        fresh_epoch = evidence_raw("fresh-epoch", new_reset, 6, now - datetime.timedelta(seconds=1))
        transition = {"calibrations": [{"pre_capture": capture(old_pre, now - datetime.timedelta(seconds=250)), "settlement_captures": [capture(old_settle, now - datetime.timedelta(seconds=229)), capture(old_settle, now - datetime.timedelta(seconds=229))]}, {"pre_capture": capture(new_pre, now - datetime.timedelta(seconds=150)), "settlement_captures": [capture(new_settle, now - datetime.timedelta(seconds=129)), capture(new_settle, now - datetime.timedelta(seconds=129))]}], "settlements": [], "usage_evidence": [{"sha256": hashlib.sha256(old_usage).hexdigest(), "bytes_base64": base64.b64encode(old_usage).decode(), "role": "post-sweep", "sweep_id": 1, "consumed_at": (now - datetime.timedelta(seconds=200)).isoformat()}]}
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
            return {"calibrations": [], "settlements": [], "usage_evidence": [{"sha256": hashlib.sha256(initial).hexdigest(), "bytes_base64": base64.b64encode(initial).decode(), "role": "pre-sweep", "sweep_id": 1, "consumed_at": (now - datetime.timedelta(seconds=2)).isoformat()}]}
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
        two_transitions = reset_manifest((now + datetime.timedelta(days=3)).isoformat(), 10)
        append_reset(two_transitions, "first-transition", (now + datetime.timedelta(days=2)).isoformat(), 5)
        try: append_reset(two_transitions, "second-transition", (now + datetime.timedelta(days=1)).isoformat(), 4)
        except LaunchViolation as exc: assert str(exc) == "usage-evidence-reset-epochs-exceeded"
        else: raise AssertionError("second reset transition accepted")
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

        sessions = [f"calibration-1-{engine}" for engine in CALIBRATION_ENGINES]
        receipts = []
        for engine, label in zip(CALIBRATION_ENGINES, sessions):
            for position, task in enumerate(CALIBRATION_TASKS, 1):
                path = root / "calibration" / f"{engine}.{label}.r1" / f"t{position}.{task}" / "cli.stdout"; path.parent.mkdir(parents=True, exist_ok=True)
                receipt = canonical_bytes({"modelUsage": {engine: {"inputTokens": 40_000_000, "outputTokens": 40_000_000, "cacheCreationInputTokens": 40_000_000, "cacheReadInputTokens": 10_000_000}}})
                path.write_bytes(receipt); receipts.append({"path": str(path.relative_to(root)), "sha256": hashlib.sha256(receipt).hexdigest(), "engine": engine, "completed_at": (now - datetime.timedelta(seconds=300)).isoformat()})
        components = sum_receipts(root, receipts, calibration_receipt_layout(sessions))
        pre_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "pre", "used_percent": 5, "observed_at": (now - datetime.timedelta(seconds=250)).isoformat()})
        settle_a_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "settle-a", "observed_at": (now - datetime.timedelta(seconds=125)).isoformat()})
        settle_b_raw = canonical_bytes({**json.loads(valid.read_bytes()), "value": "settle-b"})
        entry = lambda value: capture_entry(value, hashlib.sha256(value).hexdigest(), parse_iso8601(str(json.loads(value)["observed_at"]), "self-test-capture-observed-at"))
        calibration = {"reset_at": reset, "pre_capture": entry(pre_raw), "settlement_captures": [entry(settle_a_raw), entry(settle_b_raw)], "sessions": sessions, "receipts": receipts, "components": components, "tpp_chain": [{"kind": "calibration", "pre_sha256": hashlib.sha256(pre_raw).hexdigest(), "post_sha256": hashlib.sha256(settle_b_raw).hexdigest(), "receipt_digests": [receipt["sha256"] for receipt in receipts], "components": components, "draw": components["total"], "delta_percent": 5, "tpp_obs": components["total"] // 6}], "session_equivalents": 3}
        manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "self-test", "0" * 64, canonical_bytes({"attested_by": "self-test", "source": "self-test", **{engine: 1000000 for engine in ENGINES}}))
        manifest["calibrations"] = [calibration]; manifest["calibration_session_equivalents"] = 3
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
        record_first = usage("record-settlement-first.json", 10, now - datetime.timedelta(seconds=200))
        record_second = usage("record-settlement-second.json", 10, now - datetime.timedelta(seconds=75))
        record_fresh = usage("record-settlement-fresh.json", 10, now - datetime.timedelta(seconds=25))
        record_out = root / "record-settlement"; record_out.mkdir()
        shutil.copytree(root / "calibration", record_out / "calibration")
        record_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "record-settlement", pin, attestation_raw)
        record_calibration = json.loads(json.dumps(calibration))
        for receipt in record_calibration["receipts"]:
            receipt["completed_at"] = (now - datetime.timedelta(seconds=700)).isoformat()
        record_pre = evidence_raw("record-calibration-pre", reset, 5, now - datetime.timedelta(seconds=600))
        record_settle_first = evidence_raw("record-calibration-settle-first", reset, 10, now - datetime.timedelta(seconds=500))
        record_settle_second = evidence_raw("record-calibration-settle-second", reset, 10, now - datetime.timedelta(seconds=300))
        record_calibration["pre_capture"] = entry(record_pre)
        record_calibration["settlement_captures"] = [entry(record_settle_first), entry(record_settle_second)]
        record_calibration["tpp_chain"] = [{"kind": "calibration", "pre_sha256": hashlib.sha256(record_pre).hexdigest(), "post_sha256": hashlib.sha256(record_settle_second).hexdigest(), "receipt_digests": [receipt["sha256"] for receipt in record_calibration["receipts"]], "components": components, "draw": components["total"], "delta_percent": 5, "tpp_obs": components["total"] // 6}]
        record_manifest["calibrations"] = [record_calibration]; record_manifest["calibration_session_equivalents"] = 3
        write_json(record_out / MANIFEST_NAME, record_manifest)
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
        post_one = evidence_raw("record-settlement-post-one", reset, 10, now - datetime.timedelta(seconds=25))
        append_usage(reloaded_manifest, post_one, decode_usage_evidence(post_one, params), hashlib.sha256(post_one).hexdigest(), "post-sweep", 1, params)
        write_json(record_out / MANIFEST_NAME, reloaded_manifest)
        try:
            globals()["derive_terminal"] = lambda *_args: ("LAUNCH_PARTIAL", {})
            next_usage = usage("record-settlement-next.json", 10, now - datetime.timedelta(seconds=5))
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
        write_json(sweep_three_out / MANIFEST_NAME, sweep_three_manifest)
        sweep_three_first = usage("sweep-three-settlement-first.json", 10, now - datetime.timedelta(seconds=175))
        sweep_three_second = usage("sweep-three-settlement-second.json", 10, now - datetime.timedelta(seconds=50))
        sweep_three_fresh = usage("sweep-three-fresh.json", 10, now - datetime.timedelta(seconds=25))
        try:
            sys.argv = [str(HERE / "launch-0112.py"), "--out", str(sweep_three_out), "--run-id", "sweep-three", "--window-attestation", str(attestation), "--record-settlement", "--settlement-usage-evidence", str(sweep_three_first), "--settlement-usage-evidence", str(sweep_three_second)]
            assert main() == 0
        finally:
            sys.argv = saved_argv
        sweep_three_manifest = load_manifest(sweep_three_out, DEFAULT_SCHEDULE, DEFAULT_PARAMS, "sweep-three", pin, attestation_raw)
        post_two = evidence_raw("sweep-two-post", reset, 10, now - datetime.timedelta(seconds=25))
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
            quiet_manifest["calibrations"] = [calibration]; quiet_manifest["calibration_session_equivalents"] = 3
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
            post_manifest["calibrations"] = [calibration]; post_manifest["calibration_session_equivalents"] = 3
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
            mix_manifest["calibrations"] = [json.loads(json.dumps(calibration))]; mix_manifest["calibration_session_equivalents"] = 3
            mix_manifest["calibrations"][0]["tpp_chain"] = mix_manifest["calibrations"][0]["tpp_chain"][:1]
            append_usage(mix_manifest, raw, evidence, digest, "pre-sweep", 1, params)
            globals()["load_manifest"] = lambda *_args: mix_manifest
            globals()["sum_receipts"] = lambda *_args, **_kwargs: {"input": 1, "output": 1, "cache_create": 1, "cache_read": 972, "total": 1000}
            assert run(post_args) == 2 and mix_manifest["terminal"] == "CALIBRATION_UNIDENTIFIABLE"
            assert mix_manifest["completed_sweeps"] == [{"sweep_id": 1, "pre_sha256": digest, "post_sha256": hashlib.sha256(post_usage.read_bytes()).hexdigest(), "receipts": [{"path": "synthetic", "sha256": "a" * 64, "engine": "claude-opus-5", "completed_at": now.isoformat()}], "components": {"input": 1, "output": 1, "cache_create": 1, "cache_read": 972, "total": 1000}, "draw": 1000}]
            partial_manifest = base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "partial-self-test", pin, attestation_raw)
            partial_manifest["calibrations"] = [json.loads(json.dumps(calibration))]; partial_manifest["calibrations"][0]["tpp_chain"] = partial_manifest["calibrations"][0]["tpp_chain"][:1]; partial_manifest["calibration_session_equivalents"] = 3
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
        manifest["calibrations"][0]["tpp_chain"] = manifest["calibrations"][0]["tpp_chain"][:1]
        manifest["created_at"] = (now - datetime.timedelta(hours=169)).isoformat()
        assert not closure_payload(manifest, schedule, params, root, hashlib.sha256(settle_b_raw).hexdigest(), 1, now)["passed"]
    print("SELF_TEST_OK: v4 percent schema, reset transitions, temporal-prefix closure and settlement replay, quiet admission equality, closure admission identities/waves/events, registered settlement plus run() lifecycle paths, drift/quiet/mix run paths, partial-prefix exemption, tpp minimum, and closure pass/refusal")
    return

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", type=int); parser.add_argument("--lanes", type=int, default=3); parser.add_argument("--out", type=pathlib.Path); parser.add_argument("--run-id"); parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE); parser.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS); parser.add_argument("--window-attestation", type=pathlib.Path); parser.add_argument("--usage-evidence", type=pathlib.Path); parser.add_argument("--resume-oracle", type=pathlib.Path); parser.add_argument("--record-usage-after", action="store_true"); parser.add_argument("--record-settlement", action="store_true"); parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--calibrate", action="store_true"); parser.add_argument("--calibration-top-up", action="store_true"); parser.add_argument("--settle-calibration", action="store_true"); parser.add_argument("--settlement-usage-evidence", type=pathlib.Path, action="append"); parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try: self_test()
        except (AssertionError, OSError, LaunchViolation, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr); return 1
        return 0
    if args.out is None or args.run_id is None or args.window_attestation is None:
        parser.error("--out, --run-id, and --window-attestation are required unless --self-test is used")
    try:
        if args.calibrate:
            if args.settle_calibration or args.usage_evidence is None:
                parser.error("--calibrate requires --usage-evidence and cannot be combined with --settle-calibration")
            return run_calibration(args)
        if args.settle_calibration:
            return run_settle_calibration(args)
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
