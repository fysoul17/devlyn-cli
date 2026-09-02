#!/usr/bin/env python3
"""Frozen derived scorer for the iter-0112 session-horizon cell."""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict


HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_SCHEDULE = REPO / "docs/specs/iter0112/schedule.json"
DEFAULT_PARAMS = REPO / "docs/specs/iter0112/registered-params.json"
G0_PATH = HERE / "g0-power-0112.py"
LAUNCH_PATH = HERE / "launch-0112.py"
PIN_FILE = REPO / "docs/specs/iter0112/scripts.sha256"
G0_SHA256 = "5ba1a47be5ae328a782555e587c5fc17e051cccfb8f0c8f8a2163075ca8a95a3"
SCHEDULE_SHA256 = "3b319cf6324e4a19d6b42c74d14b915f4e11d500c35456ce5008ce7802044554"
PARAMS_SHA256 = "354667c7c32cd9174789198e72c4aa5ee97ad7b13ad66a272d18055bb83595e2"
LAUNCHER_SHA256 = "7065b818ee70b9f09a51004ca487c2dda3fd4c5b6d0025f88baa965b244262ab"
LAUNCH_MANIFEST_NAME = "launch-manifest-0112.json"
MATRIX_ENGINES = ("claude-opus-5", "claude-opus-4-8")
ENGINES = (*MATRIX_ENGINES, "claude-sonnet-5")
G3_MIN_NON_TIED_PAIRS = 47
HEADROOM_CAVEAT = "relative interaction only; a positive ΔH must never be narrated as opus-5 degrades absolutely"
RUN_BOUNDED = REPO / "config/skills/_shared/run-bounded.py"
BOUND_SEC = 1800
DRIVER_TOOLS = "Read,Grep,Glob,Edit,Write,Bash"
ROW_FIELDS = {
    "run_id",
    "task",
    "replicate",
    "engine_requested",
    "engine_attested",
    "manifestations_total",
    "manifestations_failed",
    "catastrophic",
    "incomplete",
    "infra_invalid",
    "wall_ms",
    "prompt_sha256",
    "session_label",
    "k",
    "position_index",
    "position_class",
    "launched_resume_id",
    "reported_session_id",
    "custody_ok",
    "custody_broken",
    "cli_returncode",
    "cli_stdout_bytes",
    "cli_stdout_sha256",
    "cli_stderr_bytes",
    "cli_stderr_sha256",
    "cli_argv",
    "host_origin_attestation",
}
COMPLETED_SWEEP_FIELDS = {"sweep_id", "pre_sha256", "post_sha256", "receipts", "components", "draw"}


class ScoreViolation(ValueError):
    """A frozen-input or result-custody violation."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_launcher_digest() -> str:
    target = "benchmark/executor-quality/scripts/launch-0112.py"
    try:
        entries = [line.partition("  ") for line in PIN_FILE.read_text().splitlines() if line and not line.startswith("#")]
    except OSError as exc:
        raise ScoreViolation(f"frozen-dependency-unreadable:{PIN_FILE}") from exc
    matches = [digest for digest, separator, path in entries if separator and path == target and is_digest(digest)]
    if len(matches) != 1 or matches[0] != LAUNCHER_SHA256:
        raise ScoreViolation(f"frozen-dependency-digest-mismatch:{PIN_FILE}")
    return LAUNCHER_SHA256


def verify_frozen_dependencies(schedule_path: pathlib.Path, params_path: pathlib.Path) -> str:
    for path, expected in (
        (G0_PATH, G0_SHA256),
        (schedule_path, SCHEDULE_SHA256),
        (params_path, PARAMS_SHA256),
    ):
        try:
            actual = sha256(path)
        except OSError as exc:
            raise ScoreViolation(f"frozen-dependency-unreadable:{path}") from exc
        if actual != expected:
            raise ScoreViolation(f"frozen-dependency-digest-mismatch:{path}")
    launcher_digest = pinned_launcher_digest()
    try:
        actual_launcher_digest = sha256(LAUNCH_PATH)
    except OSError as exc:
        raise ScoreViolation(f"frozen-dependency-unreadable:{LAUNCH_PATH}") from exc
    if actual_launcher_digest != LAUNCHER_SHA256 or launcher_digest != LAUNCHER_SHA256:
        raise ScoreViolation(f"frozen-dependency-digest-mismatch:{LAUNCH_PATH}")
    return LAUNCHER_SHA256


def load_g0():
    spec = importlib.util.spec_from_file_location("iter0112_g0_shared", G0_PATH)
    if spec is None or spec.loader is None:
        raise ScoreViolation("g0-shared-path-unloadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G0 = None
LAUNCHER = None


def initialize_frozen_dependencies(schedule_path: pathlib.Path, params_path: pathlib.Path) -> None:
    global G0, LAUNCHER
    verify_frozen_dependencies(schedule_path, params_path)
    G0 = load_g0()
    spec = importlib.util.spec_from_file_location("iter0112_launch_calendar", LAUNCH_PATH)
    if spec is None or spec.loader is None:
        raise ScoreViolation("launch-calendar-unloadable")
    LAUNCHER = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(LAUNCHER)


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path: pathlib.Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoreViolation(f"cannot-read-json:{path}:{exc}") from exc


def preflight_launch_manifest(results_root: pathlib.Path, schedule_path: pathlib.Path, params_path: pathlib.Path) -> dict[str, object]:
    """Reject mutable launcher/pin substitutions before their bytes are importable."""
    manifest = read_json(results_root / LAUNCH_MANIFEST_NAME)
    if not isinstance(manifest, dict) or manifest.get("schema") != "iter0112-launch-manifest-v5":
        raise ScoreViolation("launch-manifest-schema-mismatch")
    if manifest.get("schedule_sha256") != sha256(schedule_path):
        raise ScoreViolation("launch-manifest-schedule-mismatch")
    if manifest.get("params_sha256") != sha256(params_path):
        raise ScoreViolation("launch-manifest-params-mismatch")
    launcher_digest = pinned_launcher_digest()
    try:
        actual_launcher_digest, pin_digest = sha256(LAUNCH_PATH), sha256(PIN_FILE)
    except OSError as exc:
        raise ScoreViolation("frozen-dependency-unreadable:launcher-or-pin") from exc
    scripts = manifest.get("script_sha256")
    if not isinstance(scripts, dict) or scripts.get("launch-0112.py") != LAUNCHER_SHA256 or launcher_digest != LAUNCHER_SHA256 or actual_launcher_digest != LAUNCHER_SHA256:
        raise ScoreViolation("launch-manifest-launcher-digest-mismatch")
    if manifest.get("scripts_sha256_pin_file") != pin_digest:
        raise ScoreViolation("launch-manifest-script-pin-mismatch")
    return manifest


def read_jsonl(path: pathlib.Path) -> list[object]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScoreViolation(f"cannot-read-jsonl:{path}:{exc}") from exc
    rows = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise ScoreViolation(f"blank-jsonl-line:{path}:{number}")
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ScoreViolation(f"invalid-jsonl:{path}:{number}:{exc.msg}") from exc
    return rows


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def failure_fraction(row: dict[str, object]) -> float:
    if row["catastrophic"] or row["incomplete"]:
        return 1.0
    total = row["manifestations_total"]
    failed = row["manifestations_failed"]
    if type(total) is not int or type(failed) is not int or total <= 0 or not 0 <= failed <= total:
        raise ScoreViolation(f"manifestation-count-invalid:{row.get('run_id')}")
    return failed / total


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ScoreViolation(reason)


def parse_iso8601(value: object, field: str) -> datetime.datetime:
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScoreViolation(f"timestamp-{field}-invalid") from exc
    require(parsed.tzinfo is not None, f"timestamp-{field}-invalid")
    return parsed.astimezone(datetime.timezone.utc)


def ceil_div(numerator: int, denominator: int) -> int:
    require(type(numerator) is int and type(denominator) is int and numerator >= 0 and denominator > 0, "tpp-invalid")
    return (numerator + denominator - 1) // denominator


def used_percent_upper(evidence: dict[str, object]) -> int:
    used, resolution = evidence.get("used_percent"), evidence.get("display_resolution_percent")
    require(type(used) is int and 0 <= used <= 100 and type(resolution) is int and resolution == 1, "usage-evidence-numeric-invalid")
    return min(100, used + resolution)


def usage_gate(evidence: dict[str, object], sweep: int, params: dict[str, object], tpp_gate: int) -> bool:
    budget = params["venue_tolerance"]["budget_gate"]
    burn = budget["first_sweep_burn_bound_transport_tokens"] if sweep == 1 else budget["subsequent_sweep_burn_bound_transport_tokens"]
    return used_percent_upper(evidence) + ceil_div(int(burn), tpp_gate) + ceil_div(int(budget["reserve_transport_tokens"]), tpp_gate) < 100


def expected_probe_argv(params: dict[str, object], engine: str) -> list[str]:
    command = params["venue_tolerance"]["resume_oracle"].get("probe_command")
    require(isinstance(command, list) and command.count("<engine>") == 1 and all(isinstance(value, str) for value in command), "resume-oracle-probe-command-invalid")
    return [engine if value == "<engine>" else value for value in command]


def registered_driver_argv(row: dict[str, object], params: dict[str, object]) -> bool:
    argv = row.get("cli_argv")
    if argv is None:
        return row.get("cli_returncode") is None
    if not isinstance(argv, list) or not all(isinstance(value, str) for value in argv):
        return False
    registered = params["venue_tolerance"]["driver_evidence"]
    engine = row.get("engine_requested")
    if not isinstance(engine, str):
        return False
    prefix = [sys.executable, str(RUN_BOUNDED), str(BOUND_SEC), "--", registered["cli_path"], "-p"]
    if argv[:6] != prefix or len(argv) < 18 or not argv[6]:
        return False
    suffix = ["--model", engine, "--effort", "high", "--output-format", "json", "--dangerously-skip-permissions", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--allowedTools", DRIVER_TOOLS]
    remainder = argv[7:]
    if remainder[:len(suffix)] != suffix:
        return False
    trailing = remainder[len(suffix):]
    return trailing == [] or trailing == ["--resume", row.get("launched_resume_id")]


def is_aup_refusal(payload: object, engine: object) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(engine, str)
        and payload.get("is_error") is True
        and payload.get("subtype") == "success"
        and payload.get("terminal_reason") == "api_error"
        and payload.get("stop_reason") == "refusal"
        and "api_error_status" in payload
        and payload["api_error_status"] is None
        and isinstance(payload.get("modelUsage"), dict)
        and set(payload["modelUsage"]) == {engine}
    )


def load_registration(schedule_path: pathlib.Path, params_path: pathlib.Path) -> tuple[dict[str, object], dict[str, object]]:
    if G0 is None:
        initialize_frozen_dependencies(schedule_path, params_path)
    try:
        schedule, _sessions_by_replicate, _task_ids = G0.parse_schedule(schedule_path)
    except (G0.ProofViolation, OSError, ValueError) as exc:
        raise ScoreViolation(f"schedule-invalid:{exc}") from exc
    params = read_json(params_path)
    require(isinstance(params, dict), "params-not-object")
    require(params.get("schema") == "iter0112-registered-params-v1", "params-schema-mismatch")
    require(params.get("k") == G0.K, "params-k-mismatch")
    require(params.get("engines") == list(ENGINES), "params-engines-mismatch")
    require(params.get("matrix_engines") == list(MATRIX_ENGINES), "params-matrix-engines-mismatch")
    require(params.get("delta_h") == G0.DELTA_H, "params-delta-h-mismatch")
    require(params.get("complete_replicates") == len(schedule["blocks"]), "params-replicate-count-mismatch")
    registration = params.get("g0")
    require(isinstance(registration, dict), "params-g0-missing")
    bootstrap = registration.get("bootstrap")
    require(isinstance(bootstrap, dict), "params-bootstrap-missing")
    require(bootstrap.get("unit") == "complete_block_crossover_replicate", "params-bootstrap-unit-mismatch")
    require(bootstrap.get("method") == "percentile", "params-bootstrap-method-mismatch")
    require(bootstrap.get("seed") == G0.BOOTSTRAP_SEED, "params-bootstrap-seed-mismatch")
    require(bootstrap.get("resamples") == G0.BOOTSTRAP_RESAMPLES, "params-bootstrap-resamples-mismatch")
    require(
        registration.get("saturation_definition")
        == "all matrix-engine LATE task fractions equal 1 in every deciding replicate; SATURATED precedes CI terminals",
        "params-saturation-definition-mismatch",
    )
    anchors = registration.get("published_marginal_anchors")
    require(anchors == G0.ANCHORS, "params-anchor-mismatch")
    expected_digest = hashlib.sha256(schedule_path.read_bytes()).hexdigest()
    schedule_spec = params.get("schedule")
    require(isinstance(schedule_spec, dict), "params-schedule-missing")
    require(schedule_spec.get("sessions") == len(schedule["sessions"]), "params-session-count-mismatch")
    require(expected_digest == SCHEDULE_SHA256, "schedule-digest-mismatch")
    venue = params.get("venue_tolerance")
    require(isinstance(venue, dict) and isinstance(venue.get("charged_accounting"), dict) and isinstance(venue.get("usage_evidence"), dict) and isinstance(venue.get("resume_oracle"), dict) and isinstance(venue.get("calibration"), dict) and isinstance(venue.get("settlement"), dict) and isinstance(venue.get("closure_check"), dict), "params-venue-tolerance-invalid")
    require(venue["usage_evidence"].get("schema") == "iter0112-usage-v2" and venue["usage_evidence"].get("meter_id") == "current_week_all_models", "params-usage-schema-mismatch")
    closure = venue["closure_check"]
    derivation = closure.get("probe_prefix_bound_derivation")
    require(closure.get("probe_prefix_bound_transport_tokens") == 43042 and isinstance(derivation, dict) and derivation.get("maximum_observed_transport_tokens") == 34433 and derivation.get("safety_factor_numerator") == 5 and derivation.get("safety_factor_denominator") == 4, "params-closure-probe-bound-invalid")
    return schedule, params


def session_directory(root: pathlib.Path, session: dict[str, object], attempt_id: str) -> pathlib.Path:
    return root / "attempts" / attempt_id / f"{session['engine']}.{session['session_label']}.r{session['replicate_index']}"


def verify_session_artifacts(status: dict[str, object], directory: pathlib.Path, label: str) -> None:
    require(status.get("status") == "completed", f"launch-session-not-complete:{label}")
    for filename, field in (
        ("rows.jsonl", "rows_sha256"),
        ("boundary-ledger.json", "boundary_ledger_sha256"),
        ("cli-attestation.json", "driver_evidence_sha256"),
    ):
        expected = status.get(field)
        require(isinstance(expected, str) and len(expected) == 64, f"launch-artifact-digest-missing:{label}:{filename}")
        try:
            actual = sha256(directory / filename)
        except OSError as exc:
            raise ScoreViolation(f"launch-artifact-unreadable:{label}:{filename}") from exc
        require(actual == expected, f"launch-artifact-digest-mismatch:{label}:{filename}")


def verify_driver_evidence(directory: pathlib.Path, rows: list[object], params: dict[str, object], label: str) -> None:
    evidence = read_json(directory / "cli-attestation.json")
    registered = params["venue_tolerance"]["driver_evidence"]
    require(isinstance(evidence, dict) and set(evidence) == {"schema", "cli_version", "cli_path", "cli_sha256", "strict_whole_envelope_json", "strict_mcp_config", "invocations"}, f"cli-evidence-schema-invalid:{label}")
    require(evidence.get("schema") == "iter0112-cli-attestation-v1" and evidence.get("cli_version") == registered["cli_version"] and evidence.get("cli_path") == registered["cli_path"] and evidence.get("cli_sha256") == registered["cli_sha256"] and evidence.get("strict_whole_envelope_json") is True and evidence.get("strict_mcp_config") is True, f"cli-evidence-pin-invalid:{label}")
    invocations = evidence.get("invocations")
    require(isinstance(invocations, list) and len(invocations) == 8, f"cli-evidence-invocations-invalid:{label}")
    by_position = {row.get("position_index"): row for row in rows if isinstance(row, dict)}
    for item in invocations:
        require(isinstance(item, dict) and set(item) == {"position_index", "task", "argv", "returncode", "stdout", "stderr"}, f"cli-evidence-invocation-invalid:{label}")
        position = item.get("position_index")
        row = by_position.get(position)
        require(isinstance(row, dict) and item.get("task") == row.get("task") and item.get("argv") == row.get("cli_argv") and item.get("returncode") == row.get("cli_returncode"), f"cli-evidence-row-mismatch:{label}:p{position}")
        require(registered_driver_argv(row, params), f"cli-evidence-command-invalid:{label}:p{position}")
        for stream in ("stdout", "stderr"):
            raw = item.get(stream)
            path = directory / f"t{position}.{row['task']}" / f"cli.{stream}"
            require(isinstance(raw, dict) and set(raw) == {"bytes", "sha256"} and raw.get("bytes") == row.get(f"cli_{stream}_bytes") and raw.get("sha256") == row.get(f"cli_{stream}_sha256"), f"cli-evidence-stream-schema-invalid:{label}:p{position}:{stream}")
            require(type(raw["bytes"]) is int and raw["bytes"] >= 0 and isinstance(raw["sha256"], str) and len(raw["sha256"]) == 64, f"cli-evidence-stream-value-invalid:{label}:p{position}:{stream}")
            try:
                payload = path.read_bytes()
            except OSError as exc:
                raise ScoreViolation(f"cli-evidence-stream-unreadable:{label}:p{position}:{stream}") from exc
            require(len(payload) == raw["bytes"] and hashlib.sha256(payload).hexdigest() == raw["sha256"] and not (path.stat().st_mode & 0o222), f"cli-evidence-stream-digest-invalid:{label}:p{position}:{stream}")
        host = row.get("host_origin_attestation")
        if host is not None:
            host_path = directory / f"t{position}.{row['task']}" / "host-origin.json"
            require(host_path.exists() and not (host_path.stat().st_mode & 0o222) and read_json(host_path) == host, f"host-origin-evidence-invalid:{label}:p{position}")


def sessions_by_block(schedule: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    blocks: dict[str, list[dict[str, object]]] = {}
    for session in schedule["sessions"]:
        blocks.setdefault(str(session["replicate_id"]), []).append(session)
    return blocks


def attempt_census(rows: list[object]) -> dict[str, int]:
    typed = [row for row in rows if isinstance(row, dict)]
    return {
        "rows": len(typed),
        "infra_invalid_rows": sum(row.get("infra_invalid") is True for row in typed),
        "aup_catastrophic_rows": sum(row.get("infra_invalid") is False and row.get("catastrophic") is True for row in typed),
        "aup_custody_broken_rows": sum(row.get("infra_invalid") is False and row.get("custody_broken") is True for row in typed),
    }


def add_census(total: Counter[str], value: dict[str, int]) -> None:
    for key, count in value.items():
        total[key] += count


def aup_census_by_cell(rows: list[object], directory: pathlib.Path) -> Counter[str]:
    result: Counter[str] = Counter()
    for row in rows:
        if not isinstance(row, dict):
            continue
        position = row.get("position_index")
        task = row.get("task")
        if type(position) is not int or not isinstance(task, str):
            continue
        try:
            payload = json.loads((directory / f"t{position}.{task}" / "cli.stdout").read_bytes())
        except (OSError, json.JSONDecodeError):
            continue
        if is_aup_refusal(payload, row.get("engine_requested")):
            result[f"{row['engine_requested']}:{task}:p{position}"] += 1
    return result


def is_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def decode_usage(raw: bytes, params: dict[str, object]) -> dict[str, object]:
    try:
        evidence = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScoreViolation("usage-evidence-bytes-invalid") from exc
    fields = params["venue_tolerance"]["usage_evidence"]["exact_fields"]
    require(isinstance(evidence, dict) and set(evidence) == set(fields) and evidence.get("source") == "usage" and evidence.get("meter_id") == "current_week_all_models", "usage-evidence-digest-invalid")
    require(isinstance(evidence.get("value"), str) and evidence["value"] and isinstance(evidence.get("attested_by"), str) and evidence["attested_by"] and is_digest(evidence.get("panel_sha256")), "usage-evidence-text-invalid")
    used_percent_upper(evidence)
    auxiliary = evidence.get("auxiliary")
    require(isinstance(auxiliary, dict) and set(auxiliary) == {"current_week_fable_percent", "current_session_percent"} and all(value is None or (type(value) is int and 0 <= value <= 100) for value in auxiliary.values()), "usage-evidence-auxiliary-invalid")
    parse_iso8601(evidence.get("observed_at"), "usage-observed-at")
    parse_iso8601(evidence.get("reset_at"), "usage-reset-at")
    return evidence


def validate_usage_consumption(evidence: dict[str, object], consumed_at: datetime.datetime, params: dict[str, object]) -> None:
    observed = parse_iso8601(evidence.get("observed_at"), "usage-observed-at")
    usage = params["venue_tolerance"]["usage_evidence"]
    skew = datetime.timedelta(seconds=usage["clock_skew_seconds"])
    freshness = datetime.timedelta(seconds=usage["freshness_seconds"])
    require(observed <= consumed_at + skew and consumed_at - observed <= freshness, "usage-evidence-stale")


def decode_capture(entry: object, params: dict[str, object]) -> tuple[dict[str, object], datetime.datetime]:
    require(isinstance(entry, dict) and set(entry) == {"sha256", "bytes_base64", "consumed_at"} and is_digest(entry.get("sha256")), "calibration-capture-invalid")
    try:
        raw = base64.b64decode(entry["bytes_base64"], validate=True)
    except (ValueError, TypeError) as exc:
        raise ScoreViolation("calibration-capture-invalid") from exc
    require(hashlib.sha256(raw).hexdigest() == entry["sha256"], "calibration-capture-invalid")
    consumed_at = parse_iso8601(entry.get("consumed_at"), "calibration-capture-consumed-at")
    evidence = decode_usage(raw, params)
    validate_usage_consumption(evidence, consumed_at, params)
    return evidence, consumed_at


def calibration_receipt_layout(sessions: object) -> list[tuple[str, str]]:
    if not isinstance(sessions, list) or not sessions or len(sessions) % len(ENGINES):
        raise ScoreViolation("calibration-program-invalid")
    expected: list[tuple[str, str]] = []
    labels: list[str] = []
    for index, engine in enumerate(ENGINES * (len(sessions) // len(ENGINES))):
        unit = index // len(ENGINES) + 1
        label = f"calibration-{unit}-{engine}"
        labels.append(label)
        for position, task in enumerate(("smoke-1", "smoke-2"), 1):
            expected.append((f"calibration/{engine}.{label}.r1/t{position}.{task}/cli.stdout", engine))
    require(sessions == labels, "calibration-program-invalid")
    return expected


def completed_sweep_receipt_layout(root: pathlib.Path, manifest: dict[str, object], schedule: dict[str, object], sweep: int) -> list[tuple[str, str]]:
    expected: list[tuple[str, str]] = []
    blocks = manifest.get("blocks")
    require(isinstance(blocks, dict), "launch-manifest-blocks-invalid")
    for block in schedule["blocks"]:
        if block["sweep_id"] != sweep:
            continue
        replicate_id = str(block["replicate_id"])
        stored = blocks.get(replicate_id)
        require(isinstance(stored, dict) and isinstance(stored.get("designated_attempt"), str), "sweep-not-complete")
        attempt = next((item for item in stored.get("attempts", []) if isinstance(item, dict) and item.get("attempt_id") == stored["designated_attempt"]), None)
        require(isinstance(attempt, dict) and isinstance(attempt.get("sessions"), dict), "sweep-not-complete")
        for session in sessions_by_block(schedule)[replicate_id]:
            status = attempt["sessions"].get(str(session["session_label"]))
            expected_dir = session_directory(root, session, str(attempt["attempt_id"]))
            require(isinstance(status, dict) and status.get("status") == "completed" and status.get("artifact_dir") == str(expected_dir.relative_to(root)), "sweep-not-complete")
            for position, task in enumerate(session["tasks"], 1):
                expected.append((str((expected_dir / f"t{position}.{task['task_id']}" / "cli.stdout").relative_to(root)), str(session["engine"])))
    require(bool(expected), "sweep-not-complete")
    return expected


def receipt_components(root: pathlib.Path, receipts: object, expected_layout: list[tuple[str, str]] | None = None) -> dict[str, int]:
    require(isinstance(receipts, list) and receipts, "calibration-receipts-invalid")
    result = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "total": 0}
    seen: set[str] = set()
    mapping = {"inputTokens": "input", "outputTokens": "output", "cacheCreationInputTokens": "cache_create", "cacheReadInputTokens": "cache_read"}
    actual_layout: list[tuple[str, str]] = []
    for receipt in receipts:
        require(isinstance(receipt, dict) and set(receipt) == {"path", "sha256", "engine", "completed_at"} and isinstance(receipt.get("path"), str) and receipt.get("engine") in ENGINES and is_digest(receipt.get("sha256")), "calibration-receipt-invalid")
        path = pathlib.PurePath(receipt["path"])
        require(not path.is_absolute() and ".." not in path.parts and receipt["path"] not in seen, "calibration-receipt-path-invalid")
        seen.add(receipt["path"])
        actual_layout.append((receipt["path"], str(receipt["engine"])))
        try:
            raw = (root / path).read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ScoreViolation("calibration-receipt-unreadable") from exc
        require(hashlib.sha256(raw).hexdigest() == receipt["sha256"], "calibration-receipt-digest-invalid")
        require(isinstance(payload, dict) and isinstance(payload.get("modelUsage"), dict) and set(payload["modelUsage"]) == {receipt["engine"]} and isinstance(payload["modelUsage"][receipt["engine"]], dict), "calibration-receipt-schema-invalid")
        usage = payload["modelUsage"][receipt["engine"]]
        require(all(type(usage.get(source)) is int and usage[source] >= 0 for source in mapping), "calibration-receipt-components-invalid")
        for source, target in mapping.items():
            result[target] += usage[source]
    result["total"] = sum(result[key] for key in ("input", "output", "cache_create", "cache_read"))
    require(expected_layout is None or actual_layout == expected_layout, "calibration-receipt-program-invalid")
    return result


def calibration_for_epoch(manifest: dict[str, object], reset_at: str) -> dict[str, object] | None:
    values = manifest.get("calibrations")
    require(isinstance(values, list), "launch-manifest-calibrations-invalid")
    return next((value for value in reversed(values) if isinstance(value, dict) and value.get("reset_at") == reset_at), None)


def verify_calibrations(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], root: pathlib.Path) -> None:
    calibrations = manifest.get("calibrations")
    accounting = params["venue_tolerance"]["calibration"]["accounting"]
    require(isinstance(calibrations, list) and type(manifest.get("calibration_session_equivalents")) is int, "launch-manifest-calibrations-invalid")
    if LAUNCHER is None:
        initialize_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    try:
        charged_sessions = LAUNCHER.validate_manifest_calibration_ledger(manifest, root, params)
    except LAUNCHER.LaunchViolation as exc:
        raise ScoreViolation(str(exc)) from exc
    total_sessions = 0
    resets: set[str] = set()
    for calibration in calibrations:
        try:
            LAUNCHER.calibration_entry_valid(calibration, root, params, manifest, schedule)
        except LAUNCHER.LaunchViolation as exc:
            raise ScoreViolation(str(exc)) from exc
        require(isinstance(calibration, dict) and isinstance(calibration.get("reset_at"), str) and type(calibration.get("session_equivalents")) is int, "launch-manifest-calibration-invalid")
        require(calibration["reset_at"] not in resets, "calibration-cross-epoch-invalid"); resets.add(calibration["reset_at"])
        total_sessions += calibration["session_equivalents"]
    require(total_sessions <= charged_sessions == manifest["calibration_session_equivalents"] and charged_sessions <= accounting["root_session_cap"], "calibration-session-accounting-invalid")


def launcher_projection() -> object:
    if LAUNCHER is None:
        initialize_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    return LAUNCHER


def account_consumption_times(manifest: dict[str, object]) -> list[datetime.datetime]:
    try:
        return launcher_projection().account_consumption_times(manifest)
    except LAUNCHER.LaunchViolation as exc:
        raise ScoreViolation(str(exc)) from exc


def manifest_as_of(manifest: dict[str, object], at: datetime.datetime) -> dict[str, object]:
    try:
        return launcher_projection().manifest_as_of(manifest, at)
    except LAUNCHER.LaunchViolation as exc:
        raise ScoreViolation(str(exc)) from exc


def verify_settlements(manifest: dict[str, object], params: dict[str, object]) -> None:
    settlements = manifest.get("settlements")
    require(isinstance(settlements, list), "settlement-entry-invalid")
    for entry in settlements:
        require(isinstance(entry, dict) and set(entry) == {"reset_at", "captures"} and isinstance(entry.get("reset_at"), str) and isinstance(entry.get("captures"), list) and len(entry["captures"]) == 2, "settlement-entry-invalid")
        parse_iso8601(entry["reset_at"], "settlement-reset-at")
        first, first_consumed = decode_capture(entry["captures"][0], params)
        second, second_consumed = decode_capture(entry["captures"][1], params)
        require(first["reset_at"] == second["reset_at"] == entry["reset_at"], "settlement-cross-epoch-invalid")
        first_time = parse_iso8601(first.get("observed_at"), "settlement-observed-at")
        second_time = parse_iso8601(second.get("observed_at"), "settlement-observed-at")
        require(first["used_percent"] == second["used_percent"] and second_time - first_time >= datetime.timedelta(seconds=120), "settlement-invalid")
        prior_calls = account_consumption_times(manifest_as_of(manifest, first_time))
        require(not prior_calls or first_time >= max(prior_calls) + datetime.timedelta(seconds=180), "settlement-too-early")
        require(not account_consumed_after(manifest_as_of(manifest, second_time), first_time, second_time, (first_consumed, second_consumed)), "settlement-too-early")


def latest_settlement(manifest: dict[str, object], reset_at: str, params: dict[str, object], at: datetime.datetime | None = None) -> tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str, tuple[datetime.datetime, datetime.datetime]] | None:
    candidates: list[tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str, tuple[datetime.datetime, datetime.datetime]]] = []
    for calibration in manifest.get("calibrations", []):
        if not isinstance(calibration, dict) or calibration.get("reset_at") != reset_at:
            continue
        captures = calibration.get("settlement_captures")
        require(isinstance(captures, list) and len(captures) == 2, "calibration-settlement-invalid")
        first, first_consumed = decode_capture(captures[0], params)
        second, second_consumed = decode_capture(captures[1], params)
        first_time, second_time = parse_iso8601(first.get("observed_at"), "settlement-observed-at"), parse_iso8601(second.get("observed_at"), "settlement-observed-at")
        if at is None or second_time <= at:
            candidates.append((first, second, first_time, second_time, captures[1]["sha256"], (first_consumed, second_consumed)))
    for entry in manifest.get("settlements", []):
        if not isinstance(entry, dict) or entry.get("reset_at") != reset_at:
            continue
        captures = entry.get("captures")
        require(isinstance(captures, list) and len(captures) == 2, "settlement-entry-invalid")
        first, first_consumed = decode_capture(captures[0], params)
        second, second_consumed = decode_capture(captures[1], params)
        first_time, second_time = parse_iso8601(first.get("observed_at"), "settlement-observed-at"), parse_iso8601(second.get("observed_at"), "settlement-observed-at")
        if at is None or second_time <= at:
            candidates.append((first, second, first_time, second_time, captures[1]["sha256"], (first_consumed, second_consumed)))
    return max(candidates, key=lambda candidate: candidate[3]) if candidates else None


def evidence_by_digest(manifest: dict[str, object], params: dict[str, object]) -> dict[str, tuple[dict[str, object], datetime.datetime]]:
    result: dict[str, tuple[dict[str, object], datetime.datetime]] = {}
    for calibration in manifest.get("calibrations", []):
        require(isinstance(calibration, dict), "launch-manifest-calibrations-invalid")
        captures = [calibration.get("pre_capture"), *(calibration.get("settlement_captures", []) if isinstance(calibration.get("settlement_captures"), list) else [])]
        for capture in captures:
            evidence, consumed_at = decode_capture(capture, params)
            digest = capture["sha256"]
            require(digest not in result, "usage-evidence-reused")
            result[digest] = (evidence, consumed_at)
    for settlement in manifest.get("settlements", []):
        require(isinstance(settlement, dict) and isinstance(settlement.get("captures"), list), "settlement-entry-invalid")
        for capture in settlement["captures"]:
            evidence, consumed_at = decode_capture(capture, params)
            digest = capture["sha256"]
            require(digest not in result, "usage-evidence-reused")
            result[digest] = (evidence, consumed_at)
    for entry in manifest.get("usage_evidence", []):
        require(isinstance(entry, dict) and isinstance(entry.get("bytes_base64"), str) and is_digest(entry.get("sha256")), "usage-evidence-entry-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ScoreViolation("usage-evidence-bytes-invalid") from exc
        require(hashlib.sha256(raw).hexdigest() == entry["sha256"], "usage-evidence-digest-invalid")
        consumed_at = parse_iso8601(entry.get("consumed_at"), "usage-consumed-at")
        evidence = decode_usage(raw, params)
        validate_usage_consumption(evidence, consumed_at, params)
        prior = result.get(entry["sha256"])
        require(prior is None or prior[0] == evidence, "usage-evidence-digest-invalid")
        result.setdefault(entry["sha256"], (evidence, consumed_at))
    return result


def tpp_gate_for_epoch(manifest: dict[str, object], reset_at: str, params: dict[str, object], consumed_at: datetime.datetime) -> int:
    calibration = calibration_for_epoch(manifest, reset_at)
    require(calibration is not None and isinstance(calibration.get("tpp_chain"), list), "calibration-missing-for-epoch")
    evidence = evidence_by_digest(manifest, params)
    observations = []
    for observation in calibration["tpp_chain"]:
        require(isinstance(observation, dict) and is_digest(observation.get("post_sha256")) and observation["post_sha256"] in evidence, "tpp-chain-invalid")
        if evidence[observation["post_sha256"]][1] <= consumed_at:
            observations.append(observation.get("tpp_obs"))
    require(bool(observations) and all(type(value) is int and value > 0 for value in observations), "tpp-chain-invalid")
    return min(observations)


def consumed_probe_calls(manifest: dict[str, object]) -> int:
    entries = manifest.get("resume_oracles")
    require(isinstance(entries, list) and all(isinstance(entry, dict) and type(entry.get("probe_calls")) is int and entry["probe_calls"] >= 0 for entry in entries), "resume-oracle-manifest-invalid")
    return sum(entry["probe_calls"] for entry in entries)


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


def recalibration_bound(root: pathlib.Path, manifest: dict[str, object], params: dict[str, object]) -> int:
    calibrations = manifest.get("calibrations")
    require(isinstance(calibrations, list) and calibrations and isinstance(calibrations[0], dict), "calibration-missing-for-epoch")
    first = calibrations[0]
    sessions, receipts = first.get("sessions"), first.get("receipts")
    require(isinstance(sessions, list) and isinstance(receipts, list), "calibration-session-accounting-invalid")
    base_sessions = sessions[:len(ENGINES)]
    base_receipts = receipts[:len(ENGINES) * 2]
    base = receipt_components(root, base_receipts, calibration_receipt_layout(base_sessions))
    maximum = params["venue_tolerance"]["calibration"]["accounting"]["epoch_session_cap"]
    require(type(maximum) is int and maximum % len(ENGINES) == 0, "calibration-session-accounting-invalid")
    return base["total"] * maximum // len(ENGINES)


def consumed_replay_events(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> int:
    blocks = manifest.get("blocks")
    require(isinstance(blocks, dict), "launch-manifest-blocks-invalid")
    voids = {
        str(attempt["attempt_id"])
        for block in blocks.values()
        if isinstance(block, dict) and isinstance(block.get("attempts"), list)
        for attempt in block["attempts"]
        if isinstance(attempt, dict) and attempt.get("transport_state") == "VOID" and isinstance(attempt.get("attempt_id"), str) and isinstance(attempt.get("sessions"), dict) and any(isinstance(status, dict) and status.get("infra_affected") is True for status in attempt["sessions"].values())
    }
    groups = initial_attempt_batches(schedule, int(params["schedule"]["lanes"]))
    oracles = manifest.get("resume_oracles")
    require(isinstance(oracles, list), "resume-oracle-manifest-invalid")
    seen: set[str] = set().union(*groups) if groups else set()
    for entry in oracles:
        require(isinstance(entry, dict) and isinstance(entry.get("attempt_ids"), list) and all(isinstance(attempt_id, str) for attempt_id in entry["attempt_ids"]), "resume-oracle-manifest-invalid")
        group = set(entry["attempt_ids"])
        require(len(group) == len(entry["attempt_ids"]) and not group & seen, "resume-oracle-attempt-ids-invalid")
        groups.append(group)
        seen.update(group)
    require(voids <= seen, "closure-replay-event-unmapped")
    return sum(bool(group & voids) for group in groups)


def closure_payload(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], root: pathlib.Path, bound_evidence_sha256: str, sweep: int, consumed_at: datetime.datetime) -> dict[str, object]:
    """The scorer executes the launcher's canonical calendar, never a fork."""
    if LAUNCHER is None:
        initialize_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    try:
        return LAUNCHER.closure_payload(manifest, schedule, params, root, bound_evidence_sha256, sweep, consumed_at)
    except LAUNCHER.LaunchViolation as exc:
        raise ScoreViolation(str(exc)) from exc


def verify_closure_receipts(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], root: pathlib.Path, admissions: list[dict[str, object]], evidence_entries: list[dict[str, object]]) -> set[str]:
    entries = manifest.get("closure_receipts")
    require(isinstance(entries, list) and entries, "closure-receipt-missing")
    seen: set[str] = set(); passed_admissions: set[tuple[int, str]] = set(); failed_receipts: list[tuple[int, datetime.datetime, dict[str, object], dict[str, object]]] = []
    receipts: list[tuple[int, datetime.datetime, dict[str, object], dict[str, object]]] = []
    for index, entry in enumerate(entries):
        require(isinstance(entry, dict) and set(entry) == {"sha256", "bytes_base64", "sweep_id", "consumed_at"} and is_digest(entry.get("sha256")) and type(entry.get("sweep_id")) is int, "closure-receipt-invalid")
        consumed_at = parse_iso8601(entry.get("consumed_at"), "closure-consumed-at")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True); payload = json.loads(raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ScoreViolation("closure-receipt-invalid") from exc
        require(hashlib.sha256(raw).hexdigest() == entry["sha256"] and entry["sha256"] not in seen and isinstance(payload, dict) and is_digest(payload.get("bound_evidence_sha256")), "closure-receipt-invalid")
        require(payload == closure_payload(manifest_as_of(manifest, consumed_at), schedule, params, root, payload["bound_evidence_sha256"], entry["sweep_id"], consumed_at), "closure-receipt-invalid")
        seen.add(entry["sha256"])
        receipts.append((index, consumed_at, entry, payload))
        if payload["passed"] is True:
            passed_admissions.add((payload["sweep_id"], payload["bound_evidence_sha256"]))
        else:
            failed_receipts.append((index, consumed_at, entry, payload))
    terminal_admissions: set[str] = set()
    if manifest.get("terminal") == "CALIBRATION_DRIFT_OVER_BUDGET":
        require(bool(receipts), "closure-terminal-receipt-missing")
        terminal_receipt = max(receipts, key=lambda receipt: (receipt[1], receipt[0]))
        _index, _consumed_at, _entry, payload = terminal_receipt
        require(payload["passed"] is False and failed_receipts == [terminal_receipt], "closure-terminal-receipt-invalid")
        contexts = {
            (entry["sweep_id"], entry["sha256"])
            for entry in evidence_entries
            if entry.get("role") in {"pre-sweep", "resume"}
        }
        contexts.update(
            (entry["sweep_id"] + 1, entry["sha256"])
            for entry in evidence_entries
            if entry.get("role") == "post-sweep"
        )
        projected = manifest_as_of(manifest, _consumed_at)
        calibrations = projected.get("calibrations")
        require(isinstance(calibrations, list) and calibrations, "closure-terminal-receipt-invalid")
        final_calibration = calibrations[-1]
        require(isinstance(final_calibration, dict) and isinstance(final_calibration.get("settlement_captures"), list) and len(final_calibration["settlement_captures"]) == 2 and isinstance(final_calibration["settlement_captures"][1], dict) and is_digest(final_calibration["settlement_captures"][1].get("sha256")), "closure-terminal-receipt-invalid")
        terminal_calibration_s2_origins = {
            (launcher_projection().next_unadmitted_sweep(projected, schedule), final_calibration["settlement_captures"][1]["sha256"])
        }
        terminal_context = (payload["sweep_id"], payload["bound_evidence_sha256"])
        require(terminal_context in contexts | terminal_calibration_s2_origins, "closure-terminal-receipt-invalid")
        if terminal_context in {(entry["sweep_id"], entry["sha256"]) for entry in admissions}:
            terminal_admissions.add(payload["bound_evidence_sha256"])
    else:
        require(not failed_receipts, "closure-receipt-invalid")
    for admission in admissions:
        if admission["sha256"] not in terminal_admissions:
            require((admission["sweep_id"], admission["sha256"]) in passed_admissions, f"closure-receipt-missing:sweep-{admission['sweep_id']}")
    return terminal_admissions


def verify_completed_sweeps(manifest: dict[str, object], schedule: dict[str, object], root: pathlib.Path, usage: dict[str, tuple[dict[str, object], dict[str, object]]]) -> list[dict[str, object]]:
    entries = manifest.get("completed_sweeps", [])
    require(isinstance(entries, list), "completed-sweep-entry-invalid")
    prior_sweep = 0
    failures: list[dict[str, object]] = []
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == COMPLETED_SWEEP_FIELDS and type(entry.get("sweep_id")) is int and 1 <= entry["sweep_id"] <= schedule["sweeps"] and entry["sweep_id"] > prior_sweep and is_digest(entry.get("pre_sha256")) and is_digest(entry.get("post_sha256")), "completed-sweep-entry-invalid")
        pre_pair, post_pair = usage.get(entry["pre_sha256"]), usage.get(entry["post_sha256"])
        require(pre_pair is not None and post_pair is not None, "completed-sweep-provenance-invalid")
        pre_entry, pre = pre_pair
        post_entry, post = post_pair
        require(pre_entry["role"] == "pre-sweep" and post_entry["role"] == "post-sweep" and pre_entry["sweep_id"] == post_entry["sweep_id"] == entry["sweep_id"] and pre["reset_at"] == post["reset_at"], "completed-sweep-provenance-invalid")
        components = receipt_components(root, entry.get("receipts"), completed_sweep_receipt_layout(root, manifest, schedule, entry["sweep_id"]))
        require(entry.get("components") == components and entry.get("draw") == components["total"], "completed-sweep-entry-invalid")
        if not (components["total"] > 0 and 1000 * components["cache_read"] >= 973 * components["total"]):
            failures.append(entry)
        prior_sweep = entry["sweep_id"]
    if manifest.get("terminal") == "CALIBRATION_UNIDENTIFIABLE":
        require(bool(failures) and failures[-1] == entries[-1], "completed-sweep-mix-terminal-invalid")
    else:
        require(not failures, "completed-sweep-mix-invalid")
    return entries


def account_consumed_after(manifest: dict[str, object], observed_at: datetime.datetime, until: datetime.datetime, excluded: tuple[datetime.datetime, datetime.datetime] = ()) -> bool:
    selected = {time: excluded.count(time) for time in excluded}
    for time in account_consumption_times(manifest):
        if not observed_at < time <= until:
            continue
        if selected.get(time, 0):
            selected[time] -= 1
            continue
        return True
    return False


def verify_reset_timeline(timeline: list[tuple[datetime.datetime, datetime.datetime, dict[str, object]]], max_reset_epochs: int) -> None:
    try:
        launcher_projection().verify_reset_timeline(timeline, max_reset_epochs)
    except LAUNCHER.LaunchViolation as exc:
        raise ScoreViolation(str(exc)) from exc


def require_settlement_admission(evidence: dict[str, object], settlement: tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime, str, tuple[datetime.datetime, datetime.datetime]]) -> datetime.datetime:
    _first, second, first_observed, second_observed, _settlement_digest, _settlement_calls = settlement
    require(str(evidence["reset_at"]) == str(second["reset_at"]) and evidence["used_percent"] == second["used_percent"] and parse_iso8601(evidence.get("observed_at"), "usage-evidence-observed-at") > second_observed, "settlement-stale")
    return first_observed


def verify_evidence_chain(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], root: pathlib.Path) -> None:
    verify_calibrations(manifest, schedule, params, root)
    verify_settlements(manifest, params)
    entries = manifest.get("usage_evidence")
    require(isinstance(entries, list), "usage-evidence-missing")
    seen: set[str] = set()
    decoded: list[tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime]] = []
    usage_params = params["venue_tolerance"]["usage_evidence"]
    calendar = manifest.get("calendar")
    require(isinstance(calendar, dict) and set(calendar) == {"formula_version", "derivation_inputs", "W", "root_age_hours", "max_reset_epochs", "expiry", "transition_timeline", "trajectory"} and type(calendar.get("W")) is int and calendar.get("root_age_hours") == calendar["W"] * 168 and calendar.get("max_reset_epochs") == calendar["W"], "calendar-pinned-invalid")
    created = parse_iso8601(manifest.get("created_at"), "created_at")
    expiry = created + datetime.timedelta(hours=calendar["root_age_hours"])
    require(calendar.get("expiry") == expiry.isoformat(), "calendar-pinned-invalid")
    freshness = datetime.timedelta(seconds=usage_params["freshness_seconds"])
    skew = datetime.timedelta(seconds=usage_params["clock_skew_seconds"])
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == {"sha256", "bytes_base64", "role", "sweep_id", "consumed_at"} and isinstance(entry.get("sha256"), str) and len(entry["sha256"]) == 64 and entry.get("role") in {"pre-sweep", "post-sweep", "resume"} and type(entry.get("sweep_id")) is int, "usage-evidence-entry-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise ScoreViolation("usage-evidence-bytes-invalid") from exc
        evidence = decode_usage(raw, params)
        require(hashlib.sha256(raw).hexdigest() == entry["sha256"] and entry["sha256"] not in seen, "usage-evidence-digest-invalid")
        observed = parse_iso8601(evidence.get("observed_at"), "usage-observed-at")
        consumed_at = parse_iso8601(entry.get("consumed_at"), "usage-consumed-at")
        require(created <= consumed_at < expiry, "usage-evidence-expired")
        require(observed <= consumed_at + skew and consumed_at - observed <= freshness, "usage-evidence-stale")
        require(calibration_for_epoch(manifest, str(evidence["reset_at"])) is not None, "calibration-missing-for-epoch")
        seen.add(entry["sha256"])
        decoded.append((entry, evidence, observed, consumed_at))
    launcher = launcher_projection()
    try:
        verify_reset_timeline(launcher.full_timeline(manifest, params), calendar["max_reset_epochs"])
    except LAUNCHER.LaunchViolation as exc:
        raise ScoreViolation(str(exc)) from exc
    by_digest = {entry["sha256"]: (entry, evidence) for entry, evidence, _observed, _consumed in decoded}
    completed_sweeps = verify_completed_sweeps(manifest, schedule, root, by_digest)
    terminal = manifest.get("terminal")
    admitted_through = int(schedule["sweeps"])
    if terminal in {"CALIBRATION_UNIDENTIFIABLE", "CALIBRATION_DRIFT_OVER_BUDGET"}:
        admitted_through = max((entry["sweep_id"] for entry, _evidence, _observed, _consumed in decoded if entry["role"] == "post-sweep"), default=0)
    for sweep in range(1, admitted_through + 1):
        require(any(entry["role"] == "pre-sweep" and entry["sweep_id"] == sweep for entry, _evidence, _observed, _consumed in decoded), f"usage-pre-evidence-missing:sweep-{sweep}")
        require(any(entry["role"] == "post-sweep" and entry["sweep_id"] == sweep for entry, _evidence, _observed, _consumed in decoded), f"usage-post-evidence-missing:sweep-{sweep}")
    for calibration in manifest["calibrations"]:
        for observation in calibration["tpp_chain"][1:]:
            pre_pair, post_pair = by_digest.get(observation["pre_sha256"]), by_digest.get(observation["post_sha256"])
            require(pre_pair is not None and post_pair is not None, "tpp-chain-provenance-invalid")
            pre_entry, pre_evidence = pre_pair; post_entry, post_evidence = post_pair
            require(pre_entry["role"] == "pre-sweep" and post_entry["role"] == "post-sweep" and pre_entry["sweep_id"] == post_entry["sweep_id"] == observation["sweep_id"] and pre_evidence["reset_at"] == post_evidence["reset_at"] == calibration["reset_at"] and observation["delta_percent"] == post_evidence["used_percent"] - pre_evidence["used_percent"], "tpp-chain-provenance-invalid")
    oracles = manifest.get("resume_oracles")
    require(isinstance(oracles, list), "resume-oracle-missing")
    oracle_ids: set[str] = set()
    oracle_seen: set[str] = set()
    oracle_probes_by_usage: dict[str, list[dict[str, object]]] = {}
    consumed_probe_calls = 0
    order = params["venue_tolerance"]["resume_oracle"]["probe_order"]
    probe_freshness = datetime.timedelta(seconds=params["venue_tolerance"]["resume_oracle"]["probe_freshness_seconds"])
    driver = params["venue_tolerance"]["driver_evidence"]
    for entry in oracles:
        require(isinstance(entry, dict) and set(entry) == {"sha256", "bytes_base64", "attempt_ids", "consumed_at", "probe_calls"} and isinstance(entry.get("sha256"), str) and len(entry["sha256"]) == 64 and isinstance(entry.get("attempt_ids"), list) and type(entry.get("probe_calls")) is int and entry["probe_calls"] >= 0, "resume-oracle-entry-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
            oracle = json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ScoreViolation("resume-oracle-bytes-invalid") from exc
        consumed_at = parse_iso8601(entry.get("consumed_at"), "resume-consumed-at")
        require(created <= consumed_at < expiry, "resume-oracle-expired")
        require(hashlib.sha256(raw).hexdigest() == entry["sha256"] and entry["sha256"] not in oracle_seen and isinstance(oracle, dict) and set(oracle) == {"schema", "observed_at", "usage_sha256", "probes"} and oracle.get("schema") == "iter0112-resume-oracle-v1" and oracle.get("usage_sha256") in seen, "resume-oracle-digest-invalid")
        wrapper_observed = parse_iso8601(oracle.get("observed_at"), "resume-observed-at")
        require(wrapper_observed <= consumed_at + skew and consumed_at - wrapper_observed <= probe_freshness, "resume-oracle-stale")
        probes = oracle.get("probes")
        require(isinstance(probes, list) and [probe.get("model") if isinstance(probe, dict) else None for probe in probes] == order, "resume-oracle-probe-order-invalid")
        require(entry["probe_calls"] == len(probes), "resume-oracle-probe-call-count-invalid")
        prior_finished: datetime.datetime | None = None
        for expected, probe in zip(order, probes):
            require(isinstance(probe, dict) and set(probe) == {"model", "argv", "executable_path", "executable_sha256", "started_at", "observed_at", "returncode", "stdout_bytes_base64", "stdout_sha256"}, "resume-oracle-probe-invalid")
            started = parse_iso8601(probe.get("started_at"), "probe-started-at")
            finished = parse_iso8601(probe.get("observed_at"), "probe-observed-at")
            require(finished >= started and (prior_finished is None or started > prior_finished), "resume-oracle-probe-order-invalid")
            require(finished <= consumed_at + skew and consumed_at - finished <= probe_freshness, "resume-oracle-probe-stale")
            require(probe.get("argv") == expected_probe_argv(params, expected) and probe.get("executable_path") == driver["cli_path"] and probe.get("executable_sha256") == driver["cli_sha256"] and probe.get("returncode") == 0, "resume-oracle-probe-command-invalid")
            try:
                stdout = base64.b64decode(probe["stdout_bytes_base64"], validate=True)
                payload = json.loads(stdout)
            except (ValueError, json.JSONDecodeError) as exc:
                raise ScoreViolation("resume-oracle-probe-json-invalid") from exc
            require(hashlib.sha256(stdout).hexdigest() == probe.get("stdout_sha256") and isinstance(payload, dict) and payload.get("is_error") is not True and isinstance(payload.get("modelUsage"), dict) and set(payload["modelUsage"]) == {expected}, "resume-oracle-probe-failed")
            prior_finished = finished
        consumed_probe_calls += entry["probe_calls"]
        oracle_seen.add(entry["sha256"])
        require(oracle["usage_sha256"] not in oracle_probes_by_usage, "resume-oracle-digest-invalid")
        oracle_probes_by_usage[oracle["usage_sha256"]] = probes
        for attempt_id in entry["attempt_ids"]:
            require(isinstance(attempt_id, str) and attempt_id not in oracle_ids, "resume-oracle-attempt-ids-invalid")
            oracle_ids.add(attempt_id)
    require(consumed_probe_calls <= params["venue_tolerance"]["resume_oracle"]["probe_budget_session_equivalents"], "resume-oracle-probe-budget-exceeded")
    replacements = {f"{replicate_id}.a{index}" for replicate_id, block in manifest["blocks"].items() for index, _attempt in enumerate(block["attempts"], 1) if index > 1}
    require(replacements == oracle_ids, "resume-oracle-replacement-unattested")
    admissions = [entry for entry, _evidence, _observed, _consumed in decoded if entry["role"] in {"pre-sweep", "resume"}]
    terminal_evidence = verify_closure_receipts(manifest, schedule, params, root, admissions, [entry for entry, _evidence, _observed, _consumed in decoded])
    for entry, evidence, _observed, consumed_at in decoded:
        if entry["role"] == "post-sweep" or entry["sha256"] in terminal_evidence:
            continue
        tpp_gate = tpp_gate_for_epoch(manifest, str(evidence["reset_at"]), params, consumed_at)
        require(usage_gate(evidence, entry["sweep_id"], params, tpp_gate), "usage-evidence-headroom-refused")
        settlement = latest_settlement(manifest, str(evidence["reset_at"]), params, consumed_at)
        require(settlement is not None, "fresh-settlement-required")
        first_observed = require_settlement_admission(evidence, settlement)
        require(not account_consumed_after(manifest, first_observed, consumed_at, settlement[5]), "fresh-settlement-required")
        if entry["role"] == "resume":
            probes = oracle_probes_by_usage.get(entry["sha256"])
            require(probes is not None and all(parse_iso8601(probe.get("observed_at"), "resume-oracle-probe-observed-at") < first_observed for probe in probes), "resume-probe-after-settlement")


def designated_sessions(
    manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], root: pathlib.Path
) -> tuple[dict[str, tuple[dict[str, object], pathlib.Path]], dict[str, object]]:
    """Verify v3 provenance and return only mechanically designated sessions."""
    require(manifest.get("schema") == "iter0112-launch-manifest-v5", "launch-manifest-schema-mismatch")
    require(manifest.get("schedule_sha256") == sha256(DEFAULT_SCHEDULE), "launch-manifest-schedule-mismatch")
    require(manifest.get("params_sha256") == sha256(DEFAULT_PARAMS), "launch-manifest-params-mismatch")
    verify_evidence_chain(manifest, schedule, params, root)
    blocks = manifest.get("blocks")
    by_block = sessions_by_block(schedule)
    require(isinstance(blocks, dict) and set(blocks) == set(by_block), "launch-manifest-blocks-invalid")
    all_census: Counter[str] = Counter()
    designated_census: Counter[str] = Counter()
    all_aup_cells: Counter[str] = Counter()
    designated_aup_cells: Counter[str] = Counter()
    selected: dict[str, tuple[dict[str, object], pathlib.Path]] = {}
    void_count = 0
    charged_attempts = 0
    for replicate_id, sessions in by_block.items():
        block = blocks[replicate_id]
        require(isinstance(block, dict) and block.get("replicate_id") == replicate_id, f"launch-manifest-block-invalid:{replicate_id}")
        attempts = block.get("attempts")
        require(isinstance(attempts, list), f"launch-manifest-attempts-invalid:{replicate_id}")
        clean_ids: list[str] = []
        clean_attempt: dict[str, object] | None = None
        for index, attempt in enumerate(attempts, 1):
            attempt_id = f"{replicate_id}.a{index}"
            require(isinstance(attempt, dict) and set(attempt) == {"attempt_id", "replacement_of", "transport_state", "unrun_suffix", "sessions", "charged_session_equivalents"}, f"launch-manifest-attempt-invalid:{attempt_id}")
            require(attempt.get("attempt_id") == attempt_id and attempt.get("replacement_of") == (None if index == 1 else f"{replicate_id}.a{index - 1}"), f"launch-manifest-provenance-invalid:{attempt_id}")
            require(attempt.get("charged_session_equivalents") == params["venue_tolerance"]["charged_accounting"]["charge_per_started_block_session_equivalents"], f"launch-manifest-charged-attempt-invalid:{attempt_id}")
            charged_attempts += 1
            statuses = attempt.get("sessions")
            require(isinstance(statuses, dict), f"launch-manifest-attempt-sessions-invalid:{attempt_id}")
            labels = {str(session["session_label"]) for session in sessions}
            require(set(statuses) <= labels, f"launch-manifest-attempt-session-invalid:{attempt_id}")
            actual_infra = False
            for session in sessions:
                label = str(session["session_label"])
                status = statuses.get(label)
                if status is None:
                    continue
                require(isinstance(status, dict), f"launch-manifest-session-invalid:{attempt_id}:{label}")
                require(status.get("engine") == session["engine"] and status.get("replicate_id") == session["replicate_id"] and status.get("session_label") == label, f"launch-manifest-session-provenance-invalid:{attempt_id}:{label}")
                relative = status.get("artifact_dir")
                require(isinstance(relative, str) and relative == str(session_directory(root, session, attempt_id).relative_to(root)) and not pathlib.PurePath(relative).is_absolute() and ".." not in pathlib.PurePath(relative).parts, f"launch-manifest-artifact-path-invalid:{attempt_id}:{label}")
                directory = root / relative
                verify_session_artifacts(status, directory, label)
                stored_rows = read_jsonl(directory / "rows.jsonl")
                verify_driver_evidence(directory, stored_rows, params, label)
                add_census(all_census, attempt_census(stored_rows))
                all_aup_cells.update(aup_census_by_cell(stored_rows, directory))
                actual_infra = actual_infra or any(isinstance(row, dict) and row.get("infra_invalid") is True for row in stored_rows)
                require((status.get("infra_affected") is True) == any(isinstance(row, dict) and row.get("infra_invalid") is True for row in stored_rows), f"launch-manifest-infra-provenance-invalid:{attempt_id}:{label}")
            state = attempt.get("transport_state")
            require(state in {"VOID", "CLEAN", "RUNNING", "STRUCTURAL_FAILURE"}, f"launch-manifest-attempt-state-invalid:{attempt_id}")
            if state == "VOID":
                require(actual_infra, f"launch-manifest-void-without-infra:{attempt_id}")
                first_infra = next(index for index, session in enumerate(sessions) if isinstance(statuses.get(str(session["session_label"])), dict) and statuses[str(session["session_label"])].get("infra_affected") is True)
                require(attempt.get("unrun_suffix") == [str(session["session_label"]) for session in sessions[first_infra + 1:]] and not any(label in statuses for label in attempt["unrun_suffix"]), f"launch-manifest-void-suffix-invalid:{attempt_id}")
                void_count += 1
            if state == "CLEAN":
                require(set(statuses) == labels and not actual_infra and all(statuses[str(session["session_label"])].get("status") == "completed" for session in sessions), f"launch-manifest-clean-invalid:{attempt_id}")
                require(index == len(attempts), f"launch-manifest-clean-attempt-followed:{attempt_id}")
                clean_ids.append(attempt_id)
                if clean_attempt is None:
                    clean_attempt = attempt
            if index > 1:
                require(attempts[index - 2].get("transport_state") == "VOID", f"launch-manifest-replacement-without-void:{attempt_id}")
        require(block.get("designated_attempt") == (clean_ids[0] if clean_ids else None), f"launch-manifest-designation-invalid:{replicate_id}")
        if clean_attempt is not None:
            for session in sessions:
                label = str(session["session_label"])
                status = clean_attempt["sessions"][label]
                require(status.get("infra_affected") is False, f"designated-infra-invalid:{replicate_id}:{label}")
                directory = root / status["artifact_dir"]
                selected[label] = (status, directory)
                designated_rows = read_jsonl(directory / "rows.jsonl")
                add_census(designated_census, attempt_census(designated_rows))
                designated_aup_cells.update(aup_census_by_cell(designated_rows, directory))
    require(charged_attempts <= params["venue_tolerance"]["charged_accounting"]["maximum_block_attempts"], "charged-allowance-exceeded")
    require(charged_attempts * params["venue_tolerance"]["charged_accounting"]["charge_per_started_block_session_equivalents"] <= params["venue_tolerance"]["charged_accounting"]["session_equivalent_allowance"], "charged-session-equivalents-exceeded")
    if manifest.get("terminal") == "CHARGED_ALLOWANCE_EXHAUSTED":
        raise ScoreViolation("charged-allowance-exhausted")
    if manifest.get("terminal") == "WALL_CLOCK_EXPIRED":
        raise ScoreViolation("wall-clock-expired")
    if manifest.get("terminal") in {"CALIBRATION_UNIDENTIFIABLE", "CALIBRATION_DRIFT_OVER_BUDGET"}:
        raise ScoreViolation(str(manifest["terminal"]).lower())
    if manifest.get("terminal") == "REPLACEMENT_PENDING":
        raise ScoreViolation("undesignated-void-block")
    require(manifest.get("terminal") == "LAUNCH_COMPLETE", "launch-not-complete")
    require(len(selected) == len(schedule["sessions"]), "undesignated-void-block")
    return selected, {"all_attempts": dict(all_census), "designated_attempts": dict(designated_census), "all_attempts_aup_by_engine_task_position": dict(sorted(all_aup_cells.items())), "designated_attempts_aup_by_engine_task_position": dict(sorted(designated_aup_cells.items()))}


def load_launch_manifest(results_root: pathlib.Path, schedule_path: pathlib.Path, params_path: pathlib.Path) -> dict[str, object]:
    return preflight_launch_manifest(results_root, schedule_path, params_path)


def expected_positions(session: dict[str, object]) -> dict[int, dict[str, object]]:
    tasks = session["tasks"]
    require(isinstance(tasks, list), "schedule-session-tasks-invalid")
    positions = {item["position_index"]: item for item in tasks if isinstance(item, dict)}
    require(len(positions) == G0.K and set(positions) == set(range(1, G0.K + 1)), "schedule-positions-invalid")
    return positions


def validate_row(row: object, session: dict[str, object], expected: dict[int, dict[str, object]]) -> dict[str, object]:
    require(isinstance(row, dict), "row-not-object")
    require(set(row) == ROW_FIELDS, f"row-schema-mismatch:{row.get('run_id')}")
    position = row["position_index"]
    require(type(position) is int and position in expected, f"row-position-invalid:{row.get('run_id')}")
    task = expected[position]
    require(row["engine_requested"] == session["engine"], f"row-engine-mismatch:{row.get('run_id')}")
    attested = row["engine_attested"]
    require(
        attested == session["engine"] or (row["catastrophic"] is True and attested is None),
        f"row-attestation-mismatch:{row.get('run_id')}",
    )
    require(row["session_label"] == session["session_label"], f"row-label-mismatch:{row.get('run_id')}")
    require(row["replicate"] == session["replicate_index"], f"row-replicate-mismatch:{row.get('run_id')}")
    require(row["k"] == G0.K, f"row-k-mismatch:{row.get('run_id')}")
    require(row["task"] == task["task_id"], f"row-task-mismatch:{row.get('run_id')}")
    require(row["position_class"] == task["position_class"], f"row-position-class-mismatch:{row.get('run_id')}")
    for name in ("catastrophic", "incomplete", "infra_invalid", "custody_ok", "custody_broken"):
        require(type(row[name]) is bool, f"row-{name}-invalid:{row.get('run_id')}")
    require(row["cli_returncode"] is None or type(row["cli_returncode"]) is int, f"row-cli-returncode-invalid:{row.get('run_id')}")
    for stream in ("stdout", "stderr"):
        require(type(row[f"cli_{stream}_bytes"]) is int and row[f"cli_{stream}_bytes"] >= 0, f"row-cli-{stream}-bytes-invalid:{row.get('run_id')}")
        require(isinstance(row[f"cli_{stream}_sha256"], str) and len(row[f"cli_{stream}_sha256"]) == 64, f"row-cli-{stream}-digest-invalid:{row.get('run_id')}")
    require(row["cli_argv"] is None or (isinstance(row["cli_argv"], list) and all(isinstance(arg, str) for arg in row["cli_argv"])), f"row-cli-argv-invalid:{row.get('run_id')}")
    require(row["host_origin_attestation"] is None or isinstance(row["host_origin_attestation"], dict), f"row-host-origin-invalid:{row.get('run_id')}")
    require(isinstance(row["run_id"], str) and row["run_id"], "row-run-id-invalid")
    require(type(row["wall_ms"]) is int and row["wall_ms"] >= 0, f"row-wall-invalid:{row.get('run_id')}")
    require(isinstance(row["prompt_sha256"], str) and len(row["prompt_sha256"]) == 64, f"row-prompt-digest-invalid:{row.get('run_id')}")
    total = row["manifestations_total"]
    failed = row["manifestations_failed"]
    require(type(total) is int and total >= 0, f"row-total-invalid:{row.get('run_id')}")
    require(type(failed) is int and 0 <= failed <= total, f"row-failed-invalid:{row.get('run_id')}")
    return row


def custody_break(rows: list[dict[str, object]], custody: object, label: str) -> int:
    require(isinstance(custody, dict), f"custody-not-object:{label}")
    ordered = sorted(rows, key=lambda row: int(row["position_index"]))
    broken = [int(row["position_index"]) for row in ordered if row["custody_broken"] or not row["custody_ok"]]
    first = min(broken) if broken else G0.K + 1
    for row in ordered:
        position = int(row["position_index"])
        expected_ok = position < first
        require(
            row["custody_ok"] is expected_ok and row["custody_broken"] is (not expected_ok),
            f"custody-row-marking-mismatch:{label}:p{position}",
        )
    links = custody.get("links")
    require(isinstance(links, list), f"custody-links-invalid:{label}")
    require(len(links) == min(first, G0.K), f"custody-link-count-mismatch:{label}")
    expected_resume = None
    for position, link in enumerate(links, 1):
        require(isinstance(link, dict), f"custody-link-invalid:{label}:p{position}")
        row = ordered[position - 1]
        require(link.get("position_index") == position, f"custody-link-position-mismatch:{label}:p{position}")
        require(link.get("launched_resume_id") == expected_resume == row["launched_resume_id"], f"custody-resume-mismatch:{label}:p{position}")
        require(link.get("reported_session_id") == row["reported_session_id"], f"custody-reported-mismatch:{label}:p{position}")
        if position < first:
            require(isinstance(row["reported_session_id"], str) and row["reported_session_id"], f"custody-reported-id-missing:{label}:p{position}")
            expected_resume = row["reported_session_id"]
    return first


def boundary_map(path: pathlib.Path, label: str) -> dict[int, dict[str, object]]:
    ledger = read_json(path)
    require(isinstance(ledger, dict) and isinstance(ledger.get("boundaries"), list), f"boundary-ledger-invalid:{label}")
    boundaries = ledger["boundaries"]
    mapped = {
        boundary.get("position_index"): boundary
        for boundary in boundaries
        if isinstance(boundary, dict) and type(boundary.get("position_index")) is int
    }
    require(len(mapped) == G0.K and set(mapped) == set(range(1, G0.K + 1)), f"boundary-ledger-positions-invalid:{label}")
    for position, boundary in mapped.items():
        require(type(boundary.get("records_invalid")) is bool, f"boundary-records-invalid-field:{label}:p{position}")
        require(type(boundary.get("inferred_compaction")) is bool, f"boundary-compaction-field:{label}:p{position}")
        peak = boundary.get("peak_effective_context")
        require(peak is None or (type(peak) is int and peak >= 0), f"boundary-peak-invalid:{label}:p{position}")
    return mapped


def reoracle_damage(path: pathlib.Path, rows: list[dict[str, object]], label: str) -> tuple[int, list[str]]:
    payload = read_json(path)
    require(isinstance(payload, list), f"reoracle-not-list:{label}")
    seen = set()
    damage = []
    by_position = {int(row["position_index"]): row for row in rows}
    for item in payload:
        require(isinstance(item, dict), f"reoracle-item-invalid:{label}")
        position = item.get("position_index")
        require(type(position) is int and position in by_position and position not in seen, f"reoracle-position-invalid:{label}")
        seen.add(position)
        row = by_position[position]
        require(item.get("task") == row["task"], f"reoracle-task-mismatch:{label}:p{position}")
        require(type(item.get("manifestations_total")) is int and type(item.get("manifestations_failed")) is int, f"reoracle-count-invalid:{label}:p{position}")
        if row["manifestations_failed"] == 0 and item["manifestations_failed"] > 0:
            damage.append(f"{label}:p{position}:{row['task']}")
    return len(damage), damage


def new_report(schedule_path: pathlib.Path, params_path: pathlib.Path, root: pathlib.Path) -> dict[str, object]:
    return {
        "schema": "iter0112-derived-verdict-v1",
        "results_root": str(root),
        "schedule_sha256": sha256(schedule_path),
        "params_sha256": sha256(params_path),
        "g0_shared_path_sha256": sha256(G0_PATH),
        "g3_minimum_non_tied_pairs": G3_MIN_NON_TIED_PAIRS,
        "headroom_caveat": HEADROOM_CAVEAT,
    }


def score(results_root: pathlib.Path, schedule_path: pathlib.Path, params_path: pathlib.Path) -> tuple[dict[str, object], int]:
    launch_manifest = preflight_launch_manifest(results_root, schedule_path, params_path)
    schedule, params = load_registration(schedule_path, params_path)
    report = new_report(schedule_path, params_path, results_root)
    designated, attempt_censuses = designated_sessions(launch_manifest, schedule, params, results_root)
    expected_root_rows: list[dict[str, object]] = []
    values: dict[tuple[str, str, str, str], float] = {}
    raw_late: list[tuple[str, str, str, int, float, bool, list[str]]] = []
    taxonomy: Counter[str] = Counter()
    compaction: Counter[str] = Counter()
    reoracle_count = 0
    reoracle_examples: list[str] = []
    session_records: list[dict[str, object]] = []
    denominators = params["effective_context"]["context_window_denominator_tokens"]
    absolute = params["effective_context"]["absolute_threshold_tokens"]
    fraction = params["effective_context"]["context_window_fraction_threshold"]
    require(isinstance(denominators, dict) and type(absolute) is int and isinstance(fraction, (int, float)), "params-thresholds-invalid")

    for session in schedule["sessions"]:
        require(isinstance(session, dict), "schedule-session-invalid")
        label = str(session["session_label"])
        status, directory = designated[label]
        verify_session_artifacts(status, directory, label)
        rows = [validate_row(row, session, expected_positions(session)) for row in read_jsonl(directory / "rows.jsonl")]
        require(len(rows) == G0.K, f"session-row-count-mismatch:{label}")
        by_position = {int(row["position_index"]): row for row in rows}
        require(len(by_position) == G0.K, f"session-row-duplicate-position:{label}")
        broken_at = custody_break(rows, read_json(directory / "custody.json"), label)
        boundaries = boundary_map(directory / "boundary-ledger.json", label)
        damage_count, damage = reoracle_damage(directory / "end_of_session_reoracle.json", rows, label)
        reoracle_count += damage_count
        reoracle_examples.extend(damage)
        expected_root_rows.extend(rows)
        engine = str(session["engine"])
        replicate_id = str(session["replicate_id"])
        for position, row in sorted(by_position.items()):
            if row["catastrophic"]:
                taxonomy["catastrophic"] += 1
            if row["incomplete"]:
                taxonomy["incomplete"] += 1
            if row["infra_invalid"]:
                taxonomy["infra_invalid"] += 1
            if position >= broken_at:
                taxonomy["custody_broken"] += 1
            boundary = boundaries[position]
            if boundary["records_invalid"]:
                taxonomy["records_invalid"] += 1
            if boundary["inferred_compaction"]:
                compaction[engine] += 1
            row_valid = position < broken_at and not row["infra_invalid"] and not boundary["records_invalid"]
            outcome = failure_fraction(row)
            task_id = str(row["task"])
            position_class = str(row["position_class"])
            key = (engine, replicate_id, task_id, position_class)
            require(key not in values, f"duplicate-observation:{label}:p{position}")
            if position_class == "EARLY":
                if row_valid:
                    values[key] = outcome
            else:
                reasons = []
                if not row_valid:
                    reasons.append("row-invalid")
                required_peak = max(int(absolute), float(fraction) * int(denominators[engine]))
                crossed = any(
                    not boundaries[candidate]["records_invalid"]
                    and boundaries[candidate]["peak_effective_context"] is not None
                    and boundaries[candidate]["peak_effective_context"] >= required_peak
                    for candidate in range(1, position)
                )
                if not crossed:
                    reasons.append("threshold-unreached")
                qualified = row_valid and crossed
                raw_late.append((engine, replicate_id, task_id, position, outcome, qualified, reasons))
                if qualified:
                    values[key] = outcome
        session_records.append({"session_label": label, "broken_at": broken_at})

    root_rows = read_jsonl(results_root / "ledger.jsonl")
    expected_multiset = Counter(canonical_bytes(row) for row in expected_root_rows)
    actual_multiset = Counter(canonical_bytes(row) for row in root_rows if isinstance(row, dict))
    require(len(root_rows) == len(expected_root_rows) and actual_multiset == expected_multiset, "root-ledger-session-join-mismatch")
    report["row_taxonomy"] = {name: taxonomy[name] for name in ("catastrophic", "infra_invalid", "incomplete", "custody_broken", "records_invalid")}
    report["sessions"] = session_records
    report["diagnostics"] = {
        "compaction_marker_counts": {engine: compaction[engine] for engine in ENGINES},
        "end_of_session_reoracle_damage": {"count": reoracle_count, "instances": sorted(reoracle_examples)},
        "attempt_censuses": attempt_censuses,
    }

    if taxonomy["infra_invalid"]:
        report.update({"terminal": "UNSCORED", "reason": "designated-infra-invalid", "exit_mapping": "3=unscored/structural-or-infrastructure"})
        return report, 3

    anchors = params["g0"]["published_marginal_anchors"]
    tolerance = params["g1_early_mean_tolerance"]
    g1 = {}
    g1_passed = True
    for engine in ENGINES:
        per_task: dict[str, list[float]] = defaultdict(list)
        for (value_engine, _replicate, task, position_class), value in values.items():
            if value_engine == engine and position_class == "EARLY":
                per_task[task].append(value)
        balanced = mean([mean(per_task[task]) for task in sorted(per_task) if mean(per_task[task]) is not None])
        deviation = None if balanced is None else balanced - anchors[engine]
        passed = (
            balanced is not None
            and len(per_task) == 32
            and abs(deviation) <= tolerance[engine]
        )
        g1[engine] = {"anchor": anchors[engine], "early_mean": balanced, "deviation": deviation, "tolerance": tolerance[engine], "task_count": len(per_task), "passed": passed}
        g1_passed = g1_passed and passed
    report["g1_early_transport"] = g1

    exclusions: Counter[str] = Counter()
    eligible_late: Counter[str] = Counter()
    for engine, _replicate, _task, _position, _value, qualified, reasons in raw_late:
        if qualified:
            eligible_late[engine] += 1
        else:
            exclusions[engine] += 1
            for reason in reasons:
                exclusions[f"{engine}:{reason}"] += 1
    report["g2_horizon_attestation"] = {
        "absolute_threshold_tokens": absolute,
        "context_window_fraction_threshold": fraction,
        "eligible_late_cells": {engine: eligible_late[engine] for engine in ENGINES},
        "excluded_late_cells": {engine: exclusions[engine] for engine in ENGINES},
        "excluded_late_reasons": {key: exclusions[key] for key in sorted(exclusions) if ":" in key},
    }

    late_by_engine: dict[str, list[float]] = defaultdict(list)
    early_by_engine: dict[str, list[float]] = defaultdict(list)
    late_position_by_engine: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (engine, _replicate, _task, position_class), value in values.items():
        if position_class == "EARLY":
            early_by_engine[engine].append(value)
        else:
            late_by_engine[engine].append(value)
    for engine, _replicate, _task, position, value, qualified, _reasons in raw_late:
        if qualified:
            late_position_by_engine[engine][position].append(value)
    report["diagnostics"].update(
        {
            "absolute_degradations": {
                engine: None if mean(late_by_engine[engine]) is None or mean(early_by_engine[engine]) is None else mean(late_by_engine[engine]) - mean(early_by_engine[engine])
                for engine in MATRIX_ENGINES
            },
            "late_position_absolute_contrast": {
                engine: {
                    str(position): None if mean(values_at_position) is None or mean(early_by_engine[engine]) is None else mean(values_at_position) - mean(early_by_engine[engine])
                    for position, values_at_position in sorted(late_position_by_engine[engine].items())
                }
                for engine in ENGINES
            },
            "sonnet_late": {"early_mean": mean(early_by_engine["claude-sonnet-5"]), "late_mean": mean(late_by_engine["claude-sonnet-5"]), "late_cells": len(late_by_engine["claude-sonnet-5"])},
        }
    )

    if not g1_passed:
        report.update({"terminal": "TRANSPORT_FAIL_NO_MATRIX_SCORING", "exit_mapping": "2=transport-refusal"})
        return report, 2

    block_tasks = {block["replicate_id"]: block["task_ids"] for block in schedule["blocks"]}
    per_engine_pairs: dict[str, dict[tuple[str, str], tuple[float, float]]] = {engine: {} for engine in MATRIX_ENGINES}
    complete_replicate_means: list[float] = []
    complete_replicates: list[str] = []
    for replicate_id, tasks in sorted(block_tasks.items()):
        observations: dict[str, dict[str, tuple[float, float]]] = {engine: {} for engine in MATRIX_ENGINES}
        complete = True
        for engine in MATRIX_ENGINES:
            for task in tasks:
                early = values.get((engine, replicate_id, task, "EARLY"))
                late = values.get((engine, replicate_id, task, "LATE"))
                if early is not None and late is not None:
                    observations[engine][task] = (early, late)
                    per_engine_pairs[engine][(replicate_id, task)] = (early, late)
                else:
                    complete = False
        if complete:
            complete_replicates.append(replicate_id)
            complete_replicate_means.append(G0.complete_replicate_interaction(observations))
    g3 = {
        "minimum_non_tied_pairs": G3_MIN_NON_TIED_PAIRS,
        "required_complete_replicates": params["complete_replicates"],
        "complete_replicates": len(complete_replicates),
        "per_engine": {
            engine: {
                "paired_cells": len(per_engine_pairs[engine]),
                "non_tied_pairs": sum(early != late for early, late in per_engine_pairs[engine].values()),
            }
            for engine in MATRIX_ENGINES
        },
    }
    g3["passed"] = len(complete_replicates) == params["complete_replicates"] and all(
        details["non_tied_pairs"] >= G3_MIN_NON_TIED_PAIRS for details in g3["per_engine"].values()
    )
    report["g3_estimand_support"] = g3
    if not g3["passed"]:
        report.update({"terminal": "INCONCLUSIVE_AT_PILOT_N", "reason": "estimand-support", "exit_mapping": "0=registered-terminal"})
        return report, 0

    saturated = all(
        late == 1.0
        for engine in MATRIX_ENGINES
        for _early, late in per_engine_pairs[engine].values()
    )
    delta, ci, terminal = G0.decision_path(complete_replicate_means, saturated, params["g0"]["bootstrap"]["resamples"])
    report["decision"] = {
        "estimand": "mean_t,r((late-early)_opus5-(late-early)_opus48)",
        "replicate_means": complete_replicate_means,
        "delta_h": delta,
        "materiality_threshold": params["delta_h"],
        "percentile_bootstrap_ci": list(ci),
        "saturated": saturated,
        "shared_path": "g0-power-0112.py:complete_replicate_interaction+decision_path",
    }
    report.update({"terminal": terminal, "exit_mapping": "0=registered-terminal"})
    return report, 0


def finish(report: dict[str, object], exit_code: int, root: pathlib.Path) -> int:
    encoded = canonical_bytes(report)
    root.mkdir(parents=True, exist_ok=True)
    (root / "verdict-0112.json").write_bytes(encoded)
    sys.stdout.buffer.write(encoded)
    print(f"TERMINAL: {report['terminal']}")
    return exit_code


def write_synthetic_manifest(root: pathlib.Path, schedule: dict[str, object]) -> None:
    blocks = {}
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now = now_dt.isoformat()
    reset_at = (now_dt + datetime.timedelta(days=1)).isoformat()
    params = read_json(DEFAULT_PARAMS)
    assert isinstance(params, dict)

    def usage(used_percent: int, observed: datetime.datetime, label: str = "synthetic panel") -> bytes:
        return canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": observed.isoformat(), "value": label, "attested_by": "self-test", "used_percent": used_percent, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})

    calibration_receipts = []
    components = {"input": 30000000, "output": 30000000, "cache_create": 30000000, "cache_read": 10000000}
    calibration_sessions = [f"calibration-a1-u1-{engine}" for engine in ENGINES]
    for engine, label in zip(ENGINES, calibration_sessions):
        directory = root / "calibration" / f"{engine}.{label}.r1"
        for position, task in enumerate(("smoke-1", "smoke-2"), 1):
            path = directory / f"t{position}.{task}" / "cli.stdout"
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = canonical_bytes({"modelUsage": {engine: {"inputTokens": components["input"], "outputTokens": components["output"], "cacheCreationInputTokens": components["cache_create"], "cacheReadInputTokens": components["cache_read"]}}})
            path.write_bytes(raw)
            calibration_receipts.append({"path": str(path.relative_to(root)), "sha256": hashlib.sha256(raw).hexdigest(), "engine": engine, "completed_at": (now_dt - datetime.timedelta(seconds=2_500)).isoformat()})
    summed = {"input": 180000000, "output": 180000000, "cache_create": 180000000, "cache_read": 60000000, "total": 600000000}
    p1_raw, p2_raw = usage(5, now_dt - datetime.timedelta(seconds=3_000), "calibration p1"), usage(5, now_dt - datetime.timedelta(seconds=2_200), "calibration p2")
    p1 = {"sha256": hashlib.sha256(p1_raw).hexdigest(), "bytes_base64": base64.b64encode(p1_raw).decode(), "consumed_at": (now_dt - datetime.timedelta(seconds=3_000)).isoformat()}
    pre = {"sha256": hashlib.sha256(p2_raw).hexdigest(), "bytes_base64": base64.b64encode(p2_raw).decode(), "consumed_at": (now_dt - datetime.timedelta(seconds=2_200)).isoformat()}
    first_raw = usage(10, now_dt - datetime.timedelta(seconds=1_925), "calibration settle 1")
    first = {"sha256": hashlib.sha256(first_raw).hexdigest(), "bytes_base64": base64.b64encode(first_raw).decode(), "consumed_at": (now_dt - datetime.timedelta(seconds=1_925)).isoformat()}
    post_raw = usage(10, now_dt - datetime.timedelta(seconds=1_800), "calibration settle 2")
    second = {"sha256": hashlib.sha256(post_raw).hexdigest(), "bytes_base64": base64.b64encode(post_raw).decode(), "consumed_at": (now_dt - datetime.timedelta(seconds=1_800)).isoformat()}
    calibration_pair = {"unit": 1, "S1": first, "S2": second}
    calibration_attempt = {"attempt_id": 1, "status": "settled", "started_at": (now_dt - datetime.timedelta(seconds=2_600)).isoformat(), "epoch": reset_at, "captures": {"P1": p1, "P2": pre, "reset_at": reset_at}, "units": [{"unit": 1, "sessions": calibration_sessions, "receipts": calibration_receipts, "started_at": (now_dt - datetime.timedelta(seconds=2_600)).isoformat()}], "settlement_pairs": [calibration_pair], "sessions": calibration_sessions, "receipts": calibration_receipts, "session_equivalents": 3, "settlement_commit": None}
    calibration = {"reset_at": reset_at, "pre_capture": pre, "settlement_captures": [first, second], "sessions": calibration_sessions, "receipts": calibration_receipts, "components": summed, "tpp_chain": [{"kind": "calibration", "pre_sha256": pre["sha256"], "post_sha256": second["sha256"], "receipt_digests": [receipt["sha256"] for receipt in calibration_receipts], "components": summed, "draw": summed["total"], "delta_percent": 5, "tpp_obs": 100000000}], "session_equivalents": 3, "attempts": [calibration_attempt]}
    evidence_entries = []
    settlements = []
    for sweep in range(1, int(schedule["sweeps"]) + 1):
        first_time = now_dt - datetime.timedelta(seconds=1_600 - 305 * (sweep - 1))
        second_time = first_time + datetime.timedelta(seconds=120)
        first_raw = usage(10, first_time, f"settlement first {sweep}")
        second_raw = usage(10, second_time, f"settlement second {sweep}")
        first_capture = {"sha256": hashlib.sha256(first_raw).hexdigest(), "bytes_base64": base64.b64encode(first_raw).decode(), "consumed_at": first_time.isoformat()}
        second_capture = {"sha256": hashlib.sha256(second_raw).hexdigest(), "bytes_base64": base64.b64encode(second_raw).decode(), "consumed_at": second_time.isoformat()}
        settlements.append({"reset_at": reset_at, "captures": [first_capture, second_capture]})
        admission_time = second_time + datetime.timedelta(seconds=1)
        admission_raw = usage(10, admission_time, f"synthetic pre-sweep {sweep}")
        evidence_entries.append({"sha256": hashlib.sha256(admission_raw).hexdigest(), "bytes_base64": base64.b64encode(admission_raw).decode(), "role": "pre-sweep", "sweep_id": sweep, "consumed_at": (admission_time + datetime.timedelta(seconds=1)).isoformat()})
        post_time = admission_time + datetime.timedelta(seconds=1)
        post_raw = usage(10, post_time, f"synthetic post-sweep {sweep}")
        evidence_entries.append({"sha256": hashlib.sha256(post_raw).hexdigest(), "bytes_base64": base64.b64encode(post_raw).decode(), "role": "post-sweep", "sweep_id": sweep, "consumed_at": (post_time + datetime.timedelta(seconds=1)).isoformat()})
    for replicate_id, sessions in sessions_by_block(schedule).items():
        attempt_id = f"{replicate_id}.a1"
        statuses = {}
        for session in sessions:
            directory = session_directory(root, session, attempt_id)
            statuses[str(session["session_label"])] = {
                "engine": session["engine"], "replicate_id": replicate_id, "session_label": session["session_label"],
                "status": "completed", "infra_affected": False,
                "rows_sha256": sha256(directory / "rows.jsonl"),
                "boundary_ledger_sha256": sha256(directory / "boundary-ledger.json"),
                "driver_evidence_sha256": sha256(directory / "cli-attestation.json"),
                "artifact_dir": str(directory.relative_to(root)), "completed_at": (now_dt - datetime.timedelta(seconds=200)).isoformat(),
            }
        blocks[replicate_id] = {
            "replicate_id": replicate_id,
            "attempts": [{"attempt_id": attempt_id, "replacement_of": None, "transport_state": "CLEAN", "unrun_suffix": [], "sessions": statuses, "charged_session_equivalents": 6}],
            "designated_attempt": attempt_id,
        }
    manifest = {
        "schema": "iter0112-launch-manifest-v5", "created_at": (now_dt - datetime.timedelta(seconds=3_200)).isoformat(),
        "schedule_sha256": sha256(DEFAULT_SCHEDULE), "params_sha256": sha256(DEFAULT_PARAMS), "script_sha256": LAUNCHER.script_digests(), "scripts_sha256_pin_file": sha256(PIN_FILE),
        "usage_evidence": evidence_entries, "calibrations": [calibration], "calibration_ledger": {"epochs": [{"reset_at": reset_at, "attempts": [json.loads(json.dumps(calibration_attempt))]}], "unassigned_attempts": []}, "calibration_ledger_generation": 0, "settlements": settlements,
        "calibration_session_equivalents": 3, "closure_receipts": [], "calendar": None, "resume_oracles": [],
        "blocks": blocks, "terminal": "LAUNCH_COMPLETE",
    }
    for sweep in range(1, int(schedule["sweeps"]) + 1):
        bound_digest = next(entry["sha256"] for entry in evidence_entries if entry["role"] == "pre-sweep" and entry["sweep_id"] == sweep)
        consumed_at = next(parse_iso8601(entry["consumed_at"], "synthetic-consumed-at") for entry in evidence_entries if entry["sha256"] == bound_digest and entry["role"] == "pre-sweep")
        closure = closure_payload(manifest, schedule, params, root, bound_digest, sweep, consumed_at)
        if manifest["calendar"] is None:
            manifest["calendar"] = closure["calendar"]
        closure_raw = canonical_bytes(closure)
        manifest["closure_receipts"].append({"sha256": hashlib.sha256(closure_raw).hexdigest(), "bytes_base64": base64.b64encode(closure_raw).decode(), "sweep_id": sweep, "consumed_at": consumed_at.isoformat()})
    (root / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))


def synthetic_root(root: pathlib.Path, variant: str) -> None:
    schedule, params = load_registration(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    all_rows = []
    anchors = G0.ANCHORS
    task_signs = {
        (block["replicate_id"], task): 0.01 if index % 2 == 0 else -0.01
        for block in schedule["blocks"]
        for index, task in enumerate(sorted(block["task_ids"]))
    }
    for session in schedule["sessions"]:
        directory = session_directory(root, session, f"{session['replicate_id']}.a1")
        directory.mkdir(parents=True)
        rows = []
        links = []
        boundaries = []
        invocations = []
        resume = None
        for item in session["tasks"]:
            position = item["position_index"]
            engine = session["engine"]
            value = anchors[engine]
            if item["position_class"] == "LATE":
                if variant in {"confirmed", "refuted"} and engine in MATRIX_ENGINES:
                    value += task_signs[(session["replicate_id"], item["task_id"])]
                if variant == "confirmed" and engine == "claude-opus-5":
                    value += 0.3
                if variant == "refuted" and engine == "claude-opus-4-8":
                    value += 0.3
                if variant == "saturated" and engine in MATRIX_ENGINES:
                    value = 1.0
            if variant == "g1-fail" and item["position_class"] == "EARLY" and engine == "claude-sonnet-5":
                value = 0.8
            reported = f"{session['session_label']}-p{position}"
            argv = [sys.executable, str(RUN_BOUNDED), str(BOUND_SEC), "--", params["venue_tolerance"]["driver_evidence"]["cli_path"], "-p", "synthetic prompt", "--model", engine, "--effort", "high", "--output-format", "json", "--dangerously-skip-permissions", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--allowedTools", DRIVER_TOOLS]
            if resume is not None:
                argv.extend(("--resume", resume))
            row = {
                "run_id": f"synthetic:{engine}:{session['session_label']}:p{position}",
                "task": item["task_id"],
                "replicate": session["replicate_index"],
                "engine_requested": engine,
                "engine_attested": engine,
                "manifestations_total": 10000,
                "manifestations_failed": int(value * 10000),
                "catastrophic": False,
                "incomplete": False,
                "infra_invalid": False,
                "wall_ms": 1,
                "prompt_sha256": "0" * 64,
                "session_label": session["session_label"],
                "k": 8,
                "position_index": position,
                "position_class": item["position_class"],
                "launched_resume_id": resume,
                "reported_session_id": reported,
                "custody_ok": True,
                "custody_broken": False,
                "cli_returncode": 0,
                "cli_stdout_bytes": 0,
                "cli_stdout_sha256": hashlib.sha256(b"").hexdigest(),
                "cli_stderr_bytes": 0,
                "cli_stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "cli_argv": argv,
                "host_origin_attestation": None,
            }
            rows.append(row)
            links.append({"position_index": position, "launched_resume_id": resume, "reported_session_id": reported})
            resume = reported
            peak = 100000 if position >= 4 and variant != "g2-exclusion" else 1000
            boundaries.append({"position_index": position, "records_invalid": False, "peak_effective_context": peak, "inferred_compaction": False})
            task_dir = directory / f"t{position}.{item['task_id']}"
            task_dir.mkdir()
            for stream in ("stdout", "stderr"):
                raw_path = task_dir / f"cli.{stream}"
                raw_path.write_bytes(b"")
                raw_path.chmod(0o444)
            invocations.append({"position_index": position, "task": item["task_id"], "argv": argv, "returncode": 0, "stdout": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}, "stderr": {"bytes": 0, "sha256": hashlib.sha256(b"").hexdigest()}})
        (directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows))
        (directory / "custody.json").write_bytes(canonical_bytes({"links": links}))
        (directory / "boundary-ledger.json").write_bytes(canonical_bytes({"session_dir": str(directory), "boundaries": boundaries}))
        (directory / "end_of_session_reoracle.json").write_bytes(canonical_bytes([
            {"position_index": row["position_index"], "task": row["task"], "manifestations_total": row["manifestations_total"], "manifestations_failed": 0, "oracle_ok": True}
            for row in rows
        ]))
        (directory / "cli-attestation.json").write_bytes(canonical_bytes({"schema": "iter0112-cli-attestation-v1", "cli_version": "2.1.226", "cli_path": "/Users/aipalm/.local/share/nx01/pins/claude-2.1.226-iter0100/claude", "cli_sha256": "013a1cf17df5ff1dcc189d5d6fd3fdd5f097ddc3cd41aa9992e99805574febbe", "strict_whole_envelope_json": True, "strict_mcp_config": True, "invocations": invocations}))
        all_rows.extend(rows)
    (root / "ledger.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in all_rows))
    write_synthetic_manifest(root, schedule)


def add_void_replacement(root: pathlib.Path, schedule: dict[str, object]) -> None:
    """Make a real on-disk void attempt whose clean successor is designated."""
    manifest = read_json(root / LAUNCH_MANIFEST_NAME)
    assert isinstance(manifest, dict)
    replicate_id = str(schedule["blocks"][0]["replicate_id"])
    sessions = sessions_by_block(schedule)[replicate_id]
    block = manifest["blocks"][replicate_id]
    original = block["attempts"][0]
    assert isinstance(original, dict)
    replacement_id = f"{replicate_id}.a2"
    for session in sessions:
        source = session_directory(root, session, f"{replicate_id}.a1")
        target = session_directory(root, session, replacement_id)
        shutil.copytree(source, target)
    replacement_statuses = {}
    for session in sessions:
        directory = session_directory(root, session, replacement_id)
        replacement_statuses[str(session["session_label"])] = {
            "engine": session["engine"], "replicate_id": replicate_id, "session_label": session["session_label"],
            "status": "completed", "infra_affected": False,
            "rows_sha256": sha256(directory / "rows.jsonl"), "boundary_ledger_sha256": sha256(directory / "boundary-ledger.json"), "driver_evidence_sha256": sha256(directory / "cli-attestation.json"),
            "artifact_dir": str(directory.relative_to(root)), "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    first = sessions[0]
    original_directory = session_directory(root, first, f"{replicate_id}.a1")
    first_rows = read_jsonl(original_directory / "rows.jsonl")
    assert isinstance(first_rows[0], dict)
    first_rows[0]["infra_invalid"] = True
    (original_directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in first_rows))
    void_status = dict(original["sessions"][str(first["session_label"])])
    void_status["infra_affected"] = True
    void_status["rows_sha256"] = sha256(original_directory / "rows.jsonl")
    original.update({"transport_state": "VOID", "unrun_suffix": [str(session["session_label"]) for session in sessions[1:]], "sessions": {str(first["session_label"]): void_status}})
    block["attempts"].append({"attempt_id": replacement_id, "replacement_of": f"{replicate_id}.a1", "transport_state": "CLEAN", "unrun_suffix": [], "sessions": replacement_statuses, "charged_session_equivalents": 6})
    block["designated_attempt"] = replacement_id
    usage_digest = manifest["usage_evidence"][0]["sha256"]
    probe_now = datetime.datetime.now(datetime.timezone.utc)
    probe_time = probe_now.isoformat()
    params = read_json(DEFAULT_PARAMS)
    assert isinstance(params, dict)
    driver = params["venue_tolerance"]["driver_evidence"]
    probes = []
    for index, engine in enumerate(ENGINES):
        stdout = canonical_bytes({"is_error": False, "modelUsage": {engine: {}}})
        started = probe_now - datetime.timedelta(seconds=3 - index)
        finished = started + datetime.timedelta(milliseconds=500)
        probes.append({"model": engine, "argv": expected_probe_argv(params, engine), "executable_path": driver["cli_path"], "executable_sha256": driver["cli_sha256"], "started_at": started.isoformat(), "observed_at": finished.isoformat(), "returncode": 0, "stdout_bytes_base64": base64.b64encode(stdout).decode(), "stdout_sha256": hashlib.sha256(stdout).hexdigest()})
    oracle = {"schema": "iter0112-resume-oracle-v1", "observed_at": probe_time, "usage_sha256": usage_digest, "probes": probes}
    oracle_bytes = canonical_bytes(oracle)
    manifest["resume_oracles"].append({"sha256": hashlib.sha256(oracle_bytes).hexdigest(), "bytes_base64": base64.b64encode(oracle_bytes).decode(), "attempt_ids": [replacement_id], "consumed_at": probe_time, "probe_calls": len(probes)})
    selected_rows = b""
    for rid, block_sessions_for_id in sorted(sessions_by_block(schedule).items()):
        selected_id = manifest["blocks"][rid]["designated_attempt"]
        selected_attempt = next(attempt for attempt in manifest["blocks"][rid]["attempts"] if attempt["attempt_id"] == selected_id)
        for session in block_sessions_for_id:
            selected_rows += (root / selected_attempt["sessions"][str(session["session_label"])]["artifact_dir"] / "rows.jsonl").read_bytes()
    (root / "ledger.jsonl").write_bytes(selected_rows)
    (root / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))


def self_test_adversarial() -> None:
    schedule, _params = load_registration(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    m6_aup = {"is_error": True, "subtype": "success", "terminal_reason": "api_error", "stop_reason": "refusal", "api_error_status": None, "modelUsage": {"claude-opus-5": {}}}
    assert is_aup_refusal(m6_aup, "claude-opus-5")
    assert not is_aup_refusal({key: value for key, value in m6_aup.items() if key != "api_error_status"}, "claude-opus-5")
    assert not is_aup_refusal({**m6_aup, "modelUsage": ["claude-opus-5"]}, "claude-opus-5")
    with tempfile.TemporaryDirectory(prefix="iter0112-score-v4-") as temporary:
        root = pathlib.Path(temporary) / "root"; root.mkdir()
        mutated_launcher = pathlib.Path(temporary) / "mutated-launch-0112.py"
        shutil.copy2(LAUNCH_PATH, mutated_launcher)
        mutated_launcher.write_bytes(mutated_launcher.read_bytes() + b"\n# mutation\n")
        original_launch_path = LAUNCH_PATH
        try:
            globals()["LAUNCH_PATH"] = mutated_launcher
            try:
                verify_frozen_dependencies(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            except ScoreViolation as exc:
                assert str(exc) == f"frozen-dependency-digest-mismatch:{mutated_launcher}"
            else:
                raise AssertionError("mutated launcher accepted")
        finally:
            globals()["LAUNCH_PATH"] = original_launch_path
        synthetic_root(root, "confirmed")
        e2e_root = pathlib.Path(temporary) / "first-calibration-admission"; e2e_root.mkdir()
        synthetic_root(e2e_root, "confirmed")
        synthetic_manifest = read_json(e2e_root / LAUNCH_MANIFEST_NAME)
        assert isinstance(synthetic_manifest, dict)
        attestation = canonical_bytes({"attested_by": "self-test", "source": "self-test", **_params["effective_context"]["context_window_denominator_tokens"]})
        pin = LAUNCHER.verify_script_inventory()
        e2e_manifest = LAUNCHER.base_manifest(DEFAULT_SCHEDULE, DEFAULT_PARAMS, "first-calibration-admission", pin, attestation)
        e2e_manifest["created_at"] = synthetic_manifest["created_at"]
        e2e_manifest["calibrations"] = json.loads(json.dumps(synthetic_manifest["calibrations"]))
        e2e_manifest["calibration_ledger"] = json.loads(json.dumps(synthetic_manifest["calibration_ledger"]))
        e2e_manifest["calibration_session_equivalents"] = synthetic_manifest["calibration_session_equivalents"]
        ledger = LAUNCHER.empty_calibration_ledger("first-calibration-admission", DEFAULT_SCHEDULE, DEFAULT_PARAMS, pin)
        ledger["epochs"] = json.loads(json.dumps(e2e_manifest["calibration_ledger"]["epochs"]))
        LAUNCHER.write_calibration_ledger(e2e_root, ledger)
        e2e_manifest["calibration_ledger"] = LAUNCHER.calibration_ledger_projection(ledger)
        e2e_manifest["calibration_ledger_generation"] = ledger["generation"]
        (e2e_root / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(e2e_manifest))
        calibration = e2e_manifest["calibrations"][0]
        assert isinstance(calibration, dict) and e2e_manifest["settlements"] == []
        reset_at = str(calibration["reset_at"])

        def e2e_usage(label: str, observed_at: datetime.datetime) -> bytes:
            return canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": observed_at.isoformat(), "value": label, "attested_by": "self-test", "used_percent": 10, "display_resolution_percent": 1, "reset_at": reset_at, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})

        admission_at = datetime.datetime.now(datetime.timezone.utc)
        admission_raw = e2e_usage("first calibration admission", admission_at)
        admission_path = e2e_root / "first-calibration-admission.json"; admission_path.write_bytes(admission_raw)
        attestation_path = e2e_root / "window-attestation.json"; attestation_path.write_bytes(attestation)
        original_subprocess_run = LAUNCHER.subprocess.run

        def stubbed_driver(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if len(command) > 1 and command[1] == str(LAUNCHER.DRIVER):
                engine = command[command.index("--engine") + 1]
                label = command[command.index("--session-label") + 1]
                replicate = command[command.index("--replicate") + 1]
                directory = pathlib.Path(command[command.index("--out") + 1]) / f"{engine}.{label}.r{replicate}"
                rows = read_jsonl(directory / "rows.jsonl")
                transcripts = directory / "transcripts"; transcripts.mkdir(exist_ok=True)
                transcript = transcripts / "requests.jsonl"
                offset = 0; boundaries = []; payload = b""
                for row in rows:
                    line = (json.dumps({"sessionId": row["reported_session_id"], "requestId": f"{label}-{row['position_index']}", "message": {"usage": {"input_tokens": 100000}}}) + "\n").encode()
                    before, offset = offset, offset + len(line); payload += line
                    boundaries.append({"position_index": row["position_index"], "launched_resume_id": row["launched_resume_id"], "transcript_dir": str(transcripts), "before": {"requests.jsonl": before} if before else {}, "after": {"requests.jsonl": offset}})
                transcript.write_bytes(payload)
                (directory / "boundaries.json").write_bytes(canonical_bytes(boundaries))
                return subprocess.CompletedProcess(command, 0, (json.dumps({"session_dir": str(directory)}) + "\n").encode(), b"")
            return original_subprocess_run(command, **kwargs)

        try:
            LAUNCHER.subprocess.run = stubbed_driver
            result = LAUNCHER.run(argparse.Namespace(sweep=1, lanes=3, out=e2e_root, run_id="first-calibration-admission", schedule=DEFAULT_SCHEDULE, params=DEFAULT_PARAMS, window_attestation=attestation_path, usage_evidence=admission_path, resume_oracle=None, record_usage_after=False, dry_run=False))
        finally:
            LAUNCHER.subprocess.run = original_subprocess_run
        assert result == 2
        e2e_manifest = read_json(e2e_root / LAUNCH_MANIFEST_NAME)
        assert isinstance(e2e_manifest, dict) and e2e_manifest["settlements"] == []
        pre_entry = next(entry for entry in e2e_manifest["usage_evidence"] if entry["role"] == "pre-sweep" and entry["sweep_id"] == 1)
        pre_consumed = parse_iso8601(pre_entry["consumed_at"], "first-calibration-admission-consumed-at")

        def usage_entry(label: str, role: str, sweep: int, observed_at: datetime.datetime) -> dict[str, object]:
            raw = e2e_usage(label, observed_at)
            return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes_base64": base64.b64encode(raw).decode(), "role": role, "sweep_id": sweep, "consumed_at": observed_at.isoformat()}

        e2e_manifest["usage_evidence"].append(usage_entry("first calibration post", "post-sweep", 1, pre_consumed + datetime.timedelta(seconds=10)))
        cursor = pre_consumed + datetime.timedelta(seconds=190)
        for sweep in range(2, int(schedule["sweeps"]) + 1):
            first_at, second_at = cursor, cursor + datetime.timedelta(seconds=120)
            first_raw, second_raw = e2e_usage(f"settlement first {sweep}", first_at), e2e_usage(f"settlement second {sweep}", second_at)
            e2e_manifest["settlements"].append({"reset_at": reset_at, "captures": [{"sha256": hashlib.sha256(first_raw).hexdigest(), "bytes_base64": base64.b64encode(first_raw).decode(), "consumed_at": first_at.isoformat()}, {"sha256": hashlib.sha256(second_raw).hexdigest(), "bytes_base64": base64.b64encode(second_raw).decode(), "consumed_at": second_at.isoformat()}]})
            pre_at, post_at = second_at + datetime.timedelta(seconds=1), second_at + datetime.timedelta(seconds=2)
            pre = usage_entry(f"synthetic pre-sweep {sweep}", "pre-sweep", sweep, pre_at)
            e2e_manifest["usage_evidence"].extend((pre, usage_entry(f"synthetic post-sweep {sweep}", "post-sweep", sweep, post_at)))
            closure = LAUNCHER.closure_payload(e2e_manifest, schedule, _params, e2e_root, pre["sha256"], sweep, pre_at)
            assert closure["passed"] is True
            LAUNCHER.append_closure_receipt(e2e_manifest, closure, sweep, pre_at)
            cursor = post_at + datetime.timedelta(seconds=180)
        complete_at = cursor + datetime.timedelta(seconds=1)
        for block in schedule["blocks"]:
            if block["sweep_id"] == 1:
                continue
            replicate_id, attempt_id = str(block["replicate_id"]), f"{block['replicate_id']}.a1"
            statuses = {}
            for session in sessions_by_block(schedule)[replicate_id]:
                directory = session_directory(e2e_root, session, attempt_id)
                a5_clean, crossed = LAUNCHER.a5_fields(directory, str(session["engine"]), _params)
                statuses[str(session["session_label"])] = {"engine": session["engine"], "replicate_id": replicate_id, "session_label": session["session_label"], "driver_command": LAUNCHER.command_for(session, e2e_root / "attempts" / attempt_id, "first-calibration-admission"), "collector_command": LAUNCHER.collector_command_for(directory), "driver_exit": 0, "driver_stdout_sha256": hashlib.sha256(b"").hexdigest(), "driver_stderr_sha256": hashlib.sha256(b"").hexdigest(), "driver_evidence_sha256": sha256(directory / "cli-attestation.json"), "status": "completed", "collector_exit": 0, "collector_stdout_sha256": hashlib.sha256(b"").hexdigest(), "collector_stderr_sha256": hashlib.sha256(b"").hexdigest(), "infra_affected": False, "a5_clean": a5_clean, "first_late_threshold_crossed": crossed if session["engine"] in MATRIX_ENGINES else None, "rows_sha256": sha256(directory / "rows.jsonl"), "boundary_ledger_sha256": sha256(directory / "boundary-ledger.json"), "artifact_dir": str(directory.relative_to(e2e_root)), "completed_at": complete_at.isoformat()}
            e2e_manifest["blocks"][replicate_id] = {"replicate_id": replicate_id, "attempts": [{"attempt_id": attempt_id, "replacement_of": None, "transport_state": "CLEAN", "unrun_suffix": [], "sessions": statuses, "charged_session_equivalents": 6}], "designated_attempt": attempt_id}
        assert LAUNCHER.persist(e2e_root, e2e_manifest, schedule, _params) == "LAUNCH_COMPLETE"
        report, exit_code = score(e2e_root, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        assert report["terminal"] == "CONFIRMED" and exit_code == 0
        sentinel = pathlib.Path(temporary) / "launcher-imported"
        original_manifest_bytes = (root / LAUNCH_MANIFEST_NAME).read_bytes()
        coupled_launcher = pathlib.Path(temporary) / "coupled-launch-0112.py"
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        coupled_launcher.write_text(source.replace("from __future__ import annotations\n", f"from __future__ import annotations\nopen({str(sentinel)!r}, 'w').write('executed')\n", 1), encoding="utf-8")
        coupled_pin = pathlib.Path(temporary) / "coupled-scripts.sha256"
        coupled_digest = sha256(coupled_launcher)
        coupled_pin.write_text("\n".join(coupled_digest + "  " + target if target == "benchmark/executor-quality/scripts/launch-0112.py" else digest + separator + target for digest, separator, target in (line.partition("  ") for line in PIN_FILE.read_text().splitlines())) + "\n", encoding="utf-8")
        coupled_manifest = read_json(root / LAUNCH_MANIFEST_NAME)
        assert isinstance(coupled_manifest, dict) and isinstance(coupled_manifest.get("script_sha256"), dict)
        coupled_manifest["script_sha256"]["launch-0112.py"] = coupled_digest
        coupled_manifest["scripts_sha256_pin_file"] = sha256(coupled_pin)
        (root / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(coupled_manifest))
        original_pin_file, original_launch_path = PIN_FILE, LAUNCH_PATH
        try:
            globals()["PIN_FILE"], globals()["LAUNCH_PATH"] = coupled_pin, coupled_launcher
            try:
                preflight_launch_manifest(root, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            except ScoreViolation as exc:
                assert str(exc) == f"frozen-dependency-digest-mismatch:{coupled_pin}"
            else:
                raise AssertionError("coupled launcher/pin mutation accepted")
            assert not sentinel.exists(), "unverified launcher was imported"
        finally:
            globals()["PIN_FILE"], globals()["LAUNCH_PATH"] = original_pin_file, original_launch_path
            (root / LAUNCH_MANIFEST_NAME).write_bytes(original_manifest_bytes)
        report, exit_code = score(root, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        assert report["terminal"] == "CONFIRMED" and exit_code == 0
        abandoned_only = read_json(root / LAUNCH_MANIFEST_NAME)
        assert isinstance(abandoned_only, dict)
        receipt_boundary = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=3_100)
        prior_attempt = json.loads(json.dumps(abandoned_only["calibration_ledger"]["epochs"][0]["attempts"][0]))
        prior_attempt.update({"attempt_id": 2, "status": "abandoned:interrupted", "started_at": receipt_boundary.isoformat(), "epoch": None, "captures": {}, "settlement_pairs": [], "settlement_commit": None})
        prior_attempt["receipts"] = prior_attempt["receipts"][:2]
        prior_attempt["units"] = [{"unit": 1, "sessions": prior_attempt["sessions"][:1], "receipts": prior_attempt["receipts"], "started_at": receipt_boundary.isoformat()}]
        prior_attempt["sessions"] = prior_attempt["sessions"][:1]
        prior_attempt["session_equivalents"] = 3
        for receipt in prior_attempt["receipts"]:
            receipt["completed_at"] = receipt_boundary.isoformat()
        abandoned_only["calibration_ledger"]["unassigned_attempts"].append(prior_attempt)
        for project in (LAUNCHER.manifest_as_of, manifest_as_of):
            before = project(abandoned_only, receipt_boundary - datetime.timedelta(microseconds=1))
            after = project(abandoned_only, receipt_boundary)
            assert before["calibration_session_equivalents"] == 0 and not account_consumption_times(before)
        assert after["calibration_session_equivalents"] == 3 and account_consumption_times(after) == [receipt_boundary, receipt_boundary, receipt_boundary]
        reset_now = datetime.datetime.now(datetime.timezone.utc)
        def reset_timeline(*pairs: tuple[str, int]) -> list[tuple[datetime.datetime, datetime.datetime, dict[str, object]]]:
            return [(reset_now + datetime.timedelta(seconds=index), reset_now + datetime.timedelta(seconds=index), {"reset_at": reset_at, "used_percent": used}) for index, (reset_at, used) in enumerate(pairs)]
        reset_late, reset_middle, reset_early = ((reset_now + datetime.timedelta(days=3)).isoformat(), (reset_now + datetime.timedelta(days=2)).isoformat(), (reset_now + datetime.timedelta(days=1)).isoformat())
        verify_reset_timeline(reset_timeline((reset_late, 10), (reset_middle, 5)), 1)
        for name, timeline, reason in (("retreat-rise", reset_timeline((reset_late, 10), (reset_middle, 11)), "usage-evidence-reset-with-rise"), ("advance-rise", reset_timeline((reset_middle, 10), (reset_late, 11)), "usage-evidence-reset-with-rise"), ("second-transition", reset_timeline((reset_late, 10), (reset_middle, 5), (reset_early, 4)), "usage-evidence-reset-epochs-exceeded"), ("reused", reset_timeline((reset_late, 10), (reset_middle, 5), (reset_late, 4)), "usage-evidence-reset-reused-old"), ("same-epoch-drop", reset_timeline((reset_late, 10), (reset_late, 9)), "usage-evidence-nonmonotone")):
            try: verify_reset_timeline(timeline, 1)
            except ScoreViolation as exc: assert str(exc) == reason
            else: raise AssertionError(f"{name} accepted")
        settlement = ({"reset_at": reset_middle, "used_percent": 10}, {"reset_at": reset_middle, "used_percent": 10}, reset_now - datetime.timedelta(seconds=120), reset_now, "a" * 64, (reset_now - datetime.timedelta(seconds=120), reset_now))
        for name, observed_at, used, accepted in (("older-equal", reset_now - datetime.timedelta(seconds=1), 10, False), ("same-time", reset_now, 10, False), ("later-equal", reset_now + datetime.timedelta(seconds=1), 10, True), ("later-unequal", reset_now + datetime.timedelta(seconds=1), 11, False)):
            evidence = {"reset_at": reset_middle, "used_percent": used, "observed_at": observed_at.isoformat()}
            try: assert require_settlement_admission(evidence, settlement) == settlement[2]
            except ScoreViolation as exc: assert not accepted and str(exc) == "settlement-stale"
            else: assert accepted, f"{name} admission refused"

        def reject(name, mutate, reason):
            fixture = pathlib.Path(temporary) / f"{name}-fixture"; shutil.copytree(root, fixture); manifest = read_json(fixture / LAUNCH_MANIFEST_NAME); assert isinstance(manifest, dict)
            mutate(manifest)
            (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))
            try: score(fixture, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            except ScoreViolation as exc: assert reason in str(exc), str(exc)
            else: raise AssertionError(f"{name} accepted")

        reject("v3", lambda manifest: manifest.__setitem__("schema", "iter0112-launch-manifest-v3"), "schema")
        reject("bad-calibration", lambda manifest: manifest["calibrations"][0]["components"].__setitem__("cache_read", 999999999), "mix")
        def fable_moved(manifest):
            capture = manifest["calibrations"][0]["attempts"][0]["settlement_pairs"][0]["S2"]
            payload = json.loads(base64.b64decode(capture["bytes_base64"])); payload["auxiliary"]["current_week_fable_percent"] = 8
            raw = canonical_bytes(payload); capture["bytes_base64"] = base64.b64encode(raw).decode(); capture["sha256"] = hashlib.sha256(raw).hexdigest()
            manifest["calibrations"][0]["settlement_captures"][1] = json.loads(json.dumps(capture))
            manifest["calibrations"][0]["tpp_chain"][0]["post_sha256"] = capture["sha256"]
            manifest["calibration_ledger"]["epochs"][0]["attempts"][0]["settlement_pairs"][0]["S2"] = json.loads(json.dumps(capture))
        reject("fable-moved", fable_moved, "calibration-attempt-status-evidence-invalid")
        def fable_returned(manifest):
            settled = manifest["calibrations"][0]["attempts"][0]
            early_s1 = json.loads(json.dumps(settled["settlement_pairs"][0]["S1"]))
            payload = json.loads(base64.b64decode(early_s1["bytes_base64"])); payload["auxiliary"]["current_week_fable_percent"] = 8
            raw = canonical_bytes(payload); early_s1["bytes_base64"] = base64.b64encode(raw).decode(); early_s1["sha256"] = hashlib.sha256(raw).hexdigest()
            abandoned = {"attempt_id": 2, "status": "abandoned:fable-meter-moved", "started_at": settled["started_at"], "epoch": settled["epoch"], "captures": json.loads(json.dumps(settled["captures"])), "units": [{"unit": 1, "sessions": [], "receipts": [], "started_at": settled["started_at"]}], "settlement_pairs": [{"unit": 1, "S1": early_s1, "S2": json.loads(json.dumps(settled["settlement_pairs"][0]["S2"]))}], "sessions": [], "receipts": [], "session_equivalents": 3, "settlement_commit": None}
            manifest["calibrations"][0]["attempts"].insert(0, abandoned)
            manifest["calibrations"][0]["session_equivalents"] += 3
            manifest["calibration_ledger"]["epochs"][0]["attempts"].insert(0, json.loads(json.dumps(abandoned)))
            manifest["calibration_session_equivalents"] += 3
        returned = pathlib.Path(temporary) / "fable-returned"; shutil.copytree(root, returned); returned_manifest = read_json(returned / LAUNCH_MANIFEST_NAME); assert isinstance(returned_manifest, dict); fable_returned(returned_manifest); (returned / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(returned_manifest)); assert score(returned, DEFAULT_SCHEDULE, DEFAULT_PARAMS)[1] == 0
        reject("mutated-closure", lambda manifest: manifest["closure_receipts"][0].__setitem__("sha256", "f" * 64), "closure")
        def mutate_closure_field(field, value):
            def mutate(manifest):
                receipt = manifest["closure_receipts"][0]
                payload = json.loads(base64.b64decode(receipt["bytes_base64"]))
                payload[field] = value
                raw = canonical_bytes(payload)
                receipt["bytes_base64"] = base64.b64encode(raw).decode()
                receipt["sha256"] = hashlib.sha256(raw).hexdigest()
            return mutate
        reject("closure-upper", mutate_closure_field("used_percent_upper", 999999), "closure")
        reject("closure-trajectory", mutate_closure_field("trajectory", [-999]), "closure")
        reject("closure-sessions", mutate_closure_field("calibration_sessions_per_epoch", -999), "closure")
        reject("closure-consumed", lambda manifest: manifest["closure_receipts"][0].__setitem__("consumed_at", "not-a-timestamp"), "timestamp")
        identity = pathlib.Path(temporary) / "closure-identity"; shutil.copytree(root, identity)
        manifest = read_json(identity / LAUNCH_MANIFEST_NAME); assert isinstance(manifest, dict)
        receipt = next(receipt for receipt in manifest["closure_receipts"] if receipt["sweep_id"] == 1)
        payload = json.loads(base64.b64decode(receipt["bytes_base64"]))
        payload = closure_payload(manifest, schedule, _params, identity, payload["bound_evidence_sha256"], 5, parse_iso8601(receipt["consumed_at"], "identity-receipt-consumed-at"))
        raw = canonical_bytes(payload); receipt["sha256"] = hashlib.sha256(raw).hexdigest(); receipt["bytes_base64"] = base64.b64encode(raw).decode(); receipt["sweep_id"] = 5
        (identity / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))
        try: score(identity, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        except ScoreViolation as exc: assert str(exc) == "closure-receipt-missing:sweep-1"
        else: raise AssertionError("sweep-5 receipt satisfied a sweep-1 admission")
        sibling_prefix = read_json(root / LAUNCH_MANIFEST_NAME); assert isinstance(sibling_prefix, dict)
        sibling_settlement = sibling_prefix["settlements"][0]
        sibling_first, _sibling_first_consumed = decode_capture(sibling_settlement["captures"][0], _params)
        sibling_second, _sibling_second_consumed = decode_capture(sibling_settlement["captures"][1], _params)
        sibling_first_at = parse_iso8601(sibling_first["observed_at"], "session-prefix-first-at")
        sibling_second_at = parse_iso8601(sibling_second["observed_at"], "session-prefix-second-at")
        sibling_block = sibling_prefix["blocks"][str(schedule["blocks"][0]["replicate_id"])]
        sibling_block["attempts"][0]["sessions"] = {"before-first": {"completed_at": (sibling_first_at - datetime.timedelta(seconds=30)).isoformat()}, "same-timestamp-sibling": {"completed_at": _sibling_first_consumed.isoformat()}, "after-second": {"completed_at": (sibling_second_at + datetime.timedelta(seconds=1)).isoformat()}}
        sibling_projected = manifest_as_of(sibling_prefix, sibling_first_at)
        expected_sibling_sessions = {"before-first"}
        if _sibling_first_consumed <= sibling_first_at:
            expected_sibling_sessions.add("same-timestamp-sibling")
        assert set(sibling_projected["blocks"][str(schedule["blocks"][0]["replicate_id"])]["attempts"][0]["sessions"]) == expected_sibling_sessions
        assert account_consumed_after(sibling_prefix, _sibling_first_consumed - datetime.timedelta(microseconds=1), _sibling_first_consumed + datetime.timedelta(microseconds=1), (_sibling_first_consumed, _sibling_second_consumed))
        try: verify_settlements(sibling_prefix, _params)
        except ScoreViolation as exc: assert str(exc) == "settlement-too-early"
        else: raise AssertionError("session-prefix scorer accepted a prior call")
        historical_void = pathlib.Path(temporary) / "historical-void"; shutil.copytree(root, historical_void)
        add_void_replacement(historical_void, schedule)
        manifest = read_json(historical_void / LAUNCH_MANIFEST_NAME); assert isinstance(manifest, dict)
        void_attempt = next(block for block in manifest["blocks"].values() if isinstance(block, dict) and isinstance(block.get("attempts"), list) and len(block["attempts"]) > 1)["attempts"][0]
        next(iter(void_attempt["sessions"].values()))["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (historical_void / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))
        assert score(historical_void, DEFAULT_SCHEDULE, DEFAULT_PARAMS)[1] == 0
        claimed_future = pathlib.Path(temporary) / "claimed-future"; shutil.copytree(historical_void, claimed_future)
        manifest = read_json(claimed_future / LAUNCH_MANIFEST_NAME); assert isinstance(manifest, dict)
        receipt = next(receipt for receipt in manifest["closure_receipts"] if receipt["sweep_id"] == 1)
        payload = json.loads(base64.b64decode(receipt["bytes_base64"]))
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=1)
        payload = closure_payload(manifest, schedule, _params, claimed_future, payload["bound_evidence_sha256"], 1, future)
        raw = canonical_bytes(payload); receipt["sha256"] = hashlib.sha256(raw).hexdigest(); receipt["bytes_base64"] = base64.b64encode(raw).decode()
        (claimed_future / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))
        try: score(claimed_future, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        except ScoreViolation as exc: assert str(exc) == "closure-receipt-invalid"
        else: raise AssertionError("closure receipt claimed future VOID state")
        pinned_calendar = json.loads(json.dumps(manifest))
        calendar = pinned_calendar["calendar"]
        calendar["W"] = 2 if calendar["W"] == 1 else 1
        calendar["root_age_hours"] = calendar["W"] * 168
        calendar["max_reset_epochs"] = calendar["W"]
        calendar["expiry"] = (parse_iso8601(pinned_calendar["created_at"], "calendar-self-test-created") + datetime.timedelta(hours=calendar["root_age_hours"])).isoformat()
        first_admission = next(entry for entry in pinned_calendar["usage_evidence"] if entry["role"] == "pre-sweep" and entry["sweep_id"] == 1)
        try: closure_payload(pinned_calendar, schedule, _params, historical_void, first_admission["sha256"], 1, parse_iso8601(first_admission["consumed_at"], "calendar-self-test-admission"))
        except ScoreViolation as exc: assert str(exc) == "calendar-pinned-w-mismatch"
        else: raise AssertionError("scorer accepted a calendar with a non-derived W")
        clean_manifest = read_json(root / LAUNCH_MANIFEST_NAME); assert isinstance(clean_manifest, dict)
        clean_admission = next(entry for entry in clean_manifest["usage_evidence"] if entry["role"] == "pre-sweep" and entry["sweep_id"] == 1)
        for tpp, passed, weeks in ((2_230_279, False, 6), (4_602_438, False, 6), (5_000_000, True, 5), (10_000_000, True, 3)):
            candidate = json.loads(json.dumps(clean_manifest))
            candidate["calendar"] = None
            candidate["created_at"] = (parse_iso8601(clean_admission["consumed_at"], "calendar-self-test-start") - datetime.timedelta(hours=169)).isoformat()
            candidate["calibrations"][0]["tpp_chain"][0]["tpp_obs"] = tpp
            result = closure_payload(candidate, schedule, _params, root, clean_admission["sha256"], 1, parse_iso8601(clean_admission["consumed_at"], "calendar-self-test-example"))
            assert result["passed"] is passed and result["calendar"]["W"] == weeks and result["calendar_headroom_ms"] == int((parse_iso8601(result["expiry"], "calendar-self-test-expiry") - parse_iso8601(result["calendar_end"], "calendar-self-test-end")).total_seconds() * 1000)
        lowered = json.loads(json.dumps(manifest))
        observation = lowered["calibrations"][0]["tpp_chain"][0]
        prior_tpp = observation["tpp_obs"]; observation["tpp_obs"] = 1
        try:
            try:
                closure_payload(lowered, schedule, _params, historical_void, first_admission["sha256"], 1, parse_iso8601(first_admission["consumed_at"], "calendar-self-test-low-tpp"))
            except ScoreViolation as exc:
                assert str(exc) == "calendar-pinned-input-mismatch"
            else:
                raise AssertionError("scorer accepted a coupled tpp/calendar mutation")
        finally:
            observation["tpp_obs"] = prior_tpp
        recalibration_tokens = _params["venue_tolerance"]["calibration"]["accounting"]["epoch_session_cap"] * _params["venue_tolerance"]["calibration"]["full_session_bound_transport_tokens"]["value"]
        recalibration_wall_ms = _params["venue_tolerance"]["calibration"]["full_bracket_wall_ms"]["value"]
        assert recalibration_wall_ms == 7_237_524
        equality_tpp = (recalibration_tokens + 98) // 99
        token_failed, token_detail = LAUNCHER.simulate_calendar(reset_now - datetime.timedelta(hours=1), reset_now, reset_now, 0, equality_tpp, [{"name": "admission", "tokens": 0, "active_ms": 0}], 1, recalibration_tokens, recalibration_wall_ms)
        wall_failed, _wall_detail = LAUNCHER.simulate_calendar(reset_now - datetime.timedelta(hours=168) + datetime.timedelta(milliseconds=recalibration_wall_ms), reset_now, reset_now, 0, 10**18, [{"name": "admission", "tokens": 0, "active_ms": 0}], 1, recalibration_tokens, recalibration_wall_ms)
        assert not token_failed and token_detail["transition_timeline"][0]["used_percent_upper_after_calibration"] == 100 and not wall_failed
        print("SELF_TEST_OK: v5 scorer schema, first settlement admission, calibration-S2 drift origin, ledger-attempt receipt custody, per-bracket Fable witness, immutable shared calendar replay, token/wall recalibration bounds, strict expiry boundaries, and non-derived W refusal")
        return

def self_test() -> None:
    schedule, _params = load_registration(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    self_test_adversarial()
    with tempfile.TemporaryDirectory(prefix="iter0112-score-a5fix9-") as temporary:
        root = pathlib.Path(temporary)
        synthetic_root(root, "confirmed")
        manifest = read_json(root / LAUNCH_MANIFEST_NAME)
        assert isinstance(manifest, dict)
        interrupted = json.loads(json.dumps(manifest["calibrations"][0]["attempts"][0]))
        interrupted.update({"attempt_id": 2, "status": "abandoned:interrupted", "epoch": None, "captures": {}, "settlement_pairs": [], "receipts": [], "units": [{"unit": 1, "sessions": [], "receipts": [], "started_at": interrupted["started_at"]}], "sessions": [], "session_equivalents": 3})
        manifest["calibration_ledger"]["unassigned_attempts"].append(interrupted)
        manifest["calibration_session_equivalents"] = 6
        (root / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))
        verify_evidence_chain(manifest, schedule, _params, root)
        _report, exit_code = score(root, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        assert exit_code == 0
        now = datetime.datetime.now(datetime.timezone.utc)

        def interrupted_epoch(attempt_id: int, epoch: str, consumed_at: datetime.datetime) -> dict[str, object]:
            raw = canonical_bytes({"source": "usage", "meter_id": "current_week_all_models", "observed_at": consumed_at.isoformat(), "value": f"epoch-{attempt_id}", "attested_by": "self-test", "used_percent": 5, "display_resolution_percent": 1, "reset_at": epoch, "panel_sha256": "a" * 64, "auxiliary": {"current_week_fable_percent": 7, "current_session_percent": None}})
            p1 = LAUNCHER.capture_entry(raw, hashlib.sha256(raw).hexdigest(), consumed_at)
            started = consumed_at.isoformat()
            sessions = [f"calibration-a{attempt_id}-u1-{engine}" for engine in ENGINES]
            return {"attempt_id": attempt_id, "status": "abandoned:interrupted", "started_at": started, "epoch": epoch, "captures": {"P1": p1, "reset_at": epoch}, "units": [{"unit": 1, "sessions": sessions, "receipts": [], "started_at": started}], "settlement_pairs": [], "sessions": sessions, "receipts": [], "session_equivalents": 3, "settlement_commit": None}

        epochs = [(now + datetime.timedelta(days=index + 1)).isoformat() for index in range(8)]
        attempts = [interrupted_epoch(index + 1, epoch, now + datetime.timedelta(seconds=index)) for index, epoch in enumerate(epochs)]
        epoch_manifest = {"calibration_ledger": {"epochs": [{"reset_at": epoch, "attempts": [attempt]} for epoch, attempt in zip(epochs, attempts)], "unassigned_attempts": []}, "usage_evidence": [], "settlements": [], "blocks": {}, "resume_oracles": []}
        launcher_timeline = LAUNCHER.full_timeline(epoch_manifest, _params)
        assert launcher_timeline == launcher_projection().full_timeline(epoch_manifest, _params) and len(launcher_timeline) == 8
        try:
            verify_reset_timeline(launcher_timeline, 6)
        except ScoreViolation as exc:
            assert str(exc) == "usage-evidence-reset-epochs-exceeded"
        else:
            raise AssertionError("scorer accepted seven interrupted epoch transitions under W=6")
        verify_reset_timeline(launcher_timeline, 7)
    print("SELF_TEST_OK: shared timeline counts interrupted epochs and preserves launcher/scorer parity")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=pathlib.Path)
    parser.add_argument("--schedule", type=pathlib.Path, default=DEFAULT_SCHEDULE)
    parser.add_argument("--params", type=pathlib.Path, default=DEFAULT_PARAMS)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        try:
            initialize_frozen_dependencies(args.schedule, args.params)
            self_test()
        except ScoreViolation as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 3
        except (AssertionError, OSError, ValueError) as exc:
            print(f"SELF_TEST: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.results_root is None:
        parser.error("--results-root is required unless --self-test is used")
    dependencies_verified = False
    try:
        preflight_launch_manifest(args.results_root, args.schedule, args.params)
        dependencies_verified = True
        report, exit_code = score(args.results_root, args.schedule, args.params)
    except ScoreViolation as exc:
        report = (
            new_report(args.schedule, args.params, args.results_root)
            if dependencies_verified
            else {
                "schema": "iter0112-derived-verdict-v1",
                "results_root": str(args.results_root),
                "g3_minimum_non_tied_pairs": G3_MIN_NON_TIED_PAIRS,
                "headroom_caveat": HEADROOM_CAVEAT,
            }
        )
        report.update({"terminal": "UNSCORED", "reason": str(exc), "exit_mapping": "3=unscored/structural-or-infrastructure"})
        exit_code = 3
    return finish(report, exit_code, args.results_root)


if __name__ == "__main__":
    raise SystemExit(main())
