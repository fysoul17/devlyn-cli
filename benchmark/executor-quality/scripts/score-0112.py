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
G0_SHA256 = "5ba1a47be5ae328a782555e587c5fc17e051cccfb8f0c8f8a2163075ca8a95a3"
SCHEDULE_SHA256 = "3b319cf6324e4a19d6b42c74d14b915f4e11d500c35456ce5008ce7802044554"
PARAMS_SHA256 = "36ea870fc5f0ce4eb16838ddf1c3c8eda1202f8886c133f027c62f54e1ede863"
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


class ScoreViolation(ValueError):
    """A frozen-input or result-custody violation."""


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen_dependencies(schedule_path: pathlib.Path, params_path: pathlib.Path) -> None:
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


def load_g0():
    spec = importlib.util.spec_from_file_location("iter0112_g0_shared", G0_PATH)
    if spec is None or spec.loader is None:
        raise ScoreViolation("g0-shared-path-unloadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G0 = None


def initialize_frozen_dependencies(schedule_path: pathlib.Path, params_path: pathlib.Path) -> None:
    global G0
    verify_frozen_dependencies(schedule_path, params_path)
    G0 = load_g0()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path: pathlib.Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ScoreViolation(f"cannot-read-json:{path}:{exc}") from exc


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


def usage_gate(evidence: dict[str, object], sweep: int, params: dict[str, object]) -> bool:
    budget = params["venue_tolerance"]["budget_gate"]
    burn = budget["first_sweep_burn_bound_transport_tokens"] if sweep == 1 else budget["subsequent_sweep_burn_bound_transport_tokens"]
    return evidence["used_transport_tokens"] + burn + budget["reserve_transport_tokens"] < evidence["limit_transport_tokens"]


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
    require(isinstance(venue, dict) and isinstance(venue.get("charged_accounting"), dict) and isinstance(venue.get("usage_evidence"), dict) and isinstance(venue.get("resume_oracle"), dict), "params-venue-tolerance-invalid")
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


def verify_evidence_chain(manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object]) -> None:
    entries = manifest.get("usage_evidence")
    require(isinstance(entries, list), "usage-evidence-missing")
    seen: set[str] = set()
    decoded: list[tuple[dict[str, object], dict[str, object], datetime.datetime, datetime.datetime]] = []
    fields = params["venue_tolerance"]["usage_evidence"]["exact_fields"]
    usage_params = params["venue_tolerance"]["usage_evidence"]
    calendar = params["venue_tolerance"]["calendar"]
    created = parse_iso8601(manifest.get("created_at"), "created_at")
    expiry = created + datetime.timedelta(hours=calendar["root_age_hours"])
    freshness = datetime.timedelta(seconds=usage_params["freshness_seconds"])
    skew = datetime.timedelta(seconds=usage_params["clock_skew_seconds"])
    latest_reset: datetime.datetime | None = None
    reset_transitions = 0
    prior_limit: int | None = None
    prior_used: int | None = None
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == {"sha256", "bytes_base64", "role", "sweep_id", "consumed_at"} and isinstance(entry.get("sha256"), str) and len(entry["sha256"]) == 64 and entry.get("role") in {"pre-sweep", "post-sweep", "resume"} and type(entry.get("sweep_id")) is int, "usage-evidence-entry-invalid")
        try:
            raw = base64.b64decode(entry["bytes_base64"], validate=True)
            evidence = json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            raise ScoreViolation("usage-evidence-bytes-invalid") from exc
        require(hashlib.sha256(raw).hexdigest() == entry["sha256"] and entry["sha256"] not in seen and isinstance(evidence, dict) and list(evidence) != [] and set(evidence) == set(fields) and evidence.get("source") == "usage", "usage-evidence-digest-invalid")
        require(all(type(evidence.get(key)) is int and evidence[key] >= 0 for key in ("used_transport_tokens", "limit_transport_tokens")) and evidence["limit_transport_tokens"] > 0 and evidence["used_transport_tokens"] <= evidence["limit_transport_tokens"], "usage-evidence-numeric-invalid")
        observed = parse_iso8601(evidence.get("observed_at"), "usage-observed-at")
        consumed_at = parse_iso8601(entry.get("consumed_at"), "usage-consumed-at")
        reset_at = parse_iso8601(evidence.get("reset_at"), "usage-reset-at")
        require(created <= consumed_at < expiry, "usage-evidence-expired")
        require(observed <= consumed_at + skew and consumed_at - observed <= freshness, "usage-evidence-stale")
        require(entry["role"] == "post-sweep" or usage_gate(evidence, entry["sweep_id"], params), "usage-evidence-headroom-refused")
        if latest_reset is None:
            prior_limit, prior_used = evidence["limit_transport_tokens"], evidence["used_transport_tokens"]
        elif reset_at == latest_reset:
            require(evidence["limit_transport_tokens"] == prior_limit and evidence["used_transport_tokens"] >= prior_used, "usage-evidence-nonmonotone")
            prior_used = evidence["used_transport_tokens"]
        else:
            require(reset_at > latest_reset, "usage-evidence-reset-not-advancing")
            reset_transitions += 1
            require(reset_transitions <= calendar["max_reset_epochs"], "usage-evidence-reset-epochs-exceeded")
            prior_limit, prior_used = evidence["limit_transport_tokens"], evidence["used_transport_tokens"]
        latest_reset = reset_at
        seen.add(entry["sha256"])
        decoded.append((entry, evidence, observed, consumed_at))
    for sweep in range(1, int(schedule["sweeps"]) + 1):
        require(any(entry["role"] == "pre-sweep" and entry["sweep_id"] == sweep for entry, _evidence, _observed, _consumed in decoded), f"usage-pre-evidence-missing:sweep-{sweep}")
        require(any(entry["role"] == "post-sweep" and entry["sweep_id"] == sweep for entry, _evidence, _observed, _consumed in decoded), f"usage-post-evidence-missing:sweep-{sweep}")
    oracles = manifest.get("resume_oracles")
    require(isinstance(oracles, list), "resume-oracle-missing")
    oracle_ids: set[str] = set()
    oracle_seen: set[str] = set()
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
        for attempt_id in entry["attempt_ids"]:
            require(isinstance(attempt_id, str) and attempt_id not in oracle_ids, "resume-oracle-attempt-ids-invalid")
            oracle_ids.add(attempt_id)
    require(consumed_probe_calls <= params["venue_tolerance"]["resume_oracle"]["probe_budget_session_equivalents"], "resume-oracle-probe-budget-exceeded")
    replacements = {f"{replicate_id}.a{index}" for replicate_id, block in manifest["blocks"].items() for index, _attempt in enumerate(block["attempts"], 1) if index > 1}
    require(replacements == oracle_ids, "resume-oracle-replacement-unattested")


def designated_sessions(
    manifest: dict[str, object], schedule: dict[str, object], params: dict[str, object], root: pathlib.Path
) -> tuple[dict[str, tuple[dict[str, object], pathlib.Path]], dict[str, object]]:
    """Verify v3 provenance and return only mechanically designated sessions."""
    require(manifest.get("schema") == "iter0112-launch-manifest-v3", "launch-manifest-schema-mismatch")
    require(manifest.get("schedule_sha256") == sha256(DEFAULT_SCHEDULE), "launch-manifest-schedule-mismatch")
    require(manifest.get("params_sha256") == sha256(DEFAULT_PARAMS), "launch-manifest-params-mismatch")
    verify_evidence_chain(manifest, schedule, params)
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
    if manifest.get("terminal") == "REPLACEMENT_PENDING":
        raise ScoreViolation("undesignated-void-block")
    require(manifest.get("terminal") == "LAUNCH_COMPLETE", "launch-not-complete")
    require(len(selected) == len(schedule["sessions"]), "undesignated-void-block")
    return selected, {"all_attempts": dict(all_census), "designated_attempts": dict(designated_census), "all_attempts_aup_by_engine_task_position": dict(sorted(all_aup_cells.items())), "designated_attempts_aup_by_engine_task_position": dict(sorted(designated_aup_cells.items()))}


def load_launch_manifest(results_root: pathlib.Path, schedule_path: pathlib.Path, params_path: pathlib.Path) -> dict[str, object]:
    manifest = read_json(results_root / LAUNCH_MANIFEST_NAME)
    require(isinstance(manifest, dict), "launch-manifest-not-object")
    require(manifest.get("schema") == "iter0112-launch-manifest-v3", "launch-manifest-schema-mismatch")
    require(manifest.get("schedule_sha256") == sha256(schedule_path), "launch-manifest-schedule-mismatch")
    require(manifest.get("params_sha256") == sha256(params_path), "launch-manifest-params-mismatch")
    return manifest


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
    schedule, params = load_registration(schedule_path, params_path)
    launch_manifest = load_launch_manifest(results_root, schedule_path, params_path)
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
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    evidence_entries = []
    for sweep in range(1, int(schedule["sweeps"]) + 1):
        for role in ("pre-sweep", "post-sweep"):
            payload = canonical_bytes({"source": "usage", "observed_at": now, "value": f"synthetic {role} {sweep}", "attested_by": "self-test", "used_transport_tokens": len(evidence_entries), "limit_transport_tokens": 2000000000, "reset_at": now})
            evidence_entries.append({"sha256": hashlib.sha256(payload).hexdigest(), "bytes_base64": base64.b64encode(payload).decode(), "role": role, "sweep_id": sweep, "consumed_at": now})
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
                "artifact_dir": str(directory.relative_to(root)),
            }
        blocks[replicate_id] = {
            "replicate_id": replicate_id,
            "attempts": [{"attempt_id": attempt_id, "replacement_of": None, "transport_state": "CLEAN", "unrun_suffix": [], "sessions": statuses, "charged_session_equivalents": 6}],
            "designated_attempt": attempt_id,
        }
    (root / LAUNCH_MANIFEST_NAME).write_bytes(
        canonical_bytes(
            {
                "schema": "iter0112-launch-manifest-v3",
                "created_at": now,
                "schedule_sha256": sha256(DEFAULT_SCHEDULE),
                "params_sha256": sha256(DEFAULT_PARAMS),
                "usage_evidence": evidence_entries,
                "resume_oracles": [],
                "blocks": blocks,
                "terminal": "LAUNCH_COMPLETE",
            }
        )
    )


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
            "artifact_dir": str(directory.relative_to(root)),
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


def self_test() -> None:
    schedule, _params = load_registration(DEFAULT_SCHEDULE, DEFAULT_PARAMS)
    m6_aup = {"is_error": True, "subtype": "success", "terminal_reason": "api_error", "stop_reason": "refusal", "api_error_status": None, "modelUsage": {"claude-opus-5": {}}}
    assert is_aup_refusal(m6_aup, "claude-opus-5")
    assert not is_aup_refusal({key: value for key, value in m6_aup.items() if key != "api_error_status"}, "claude-opus-5")
    assert not is_aup_refusal({**m6_aup, "modelUsage": ["claude-opus-5"]}, "claude-opus-5")
    scenarios = {
        "g1-fail": "TRANSPORT_FAIL_NO_MATRIX_SCORING",
        "g2-exclusion": "INCONCLUSIVE_AT_PILOT_N",
        "g3-fail": "INCONCLUSIVE_AT_PILOT_N",
        "saturated": "SATURATED",
        "confirmed": "CONFIRMED",
        "refuted": "MATERIAL_GAP_REFUTED",
    }
    with tempfile.TemporaryDirectory(prefix="iter0112-score-") as temporary:
        root = pathlib.Path(temporary)
        tampered_params = root / "registered-params.json"
        tampered_bytes = bytearray(DEFAULT_PARAMS.read_bytes())
        tampered_bytes[0] ^= 1
        tampered_params.write_bytes(tampered_bytes)
        try:
            verify_frozen_dependencies(DEFAULT_SCHEDULE, tampered_params)
        except ScoreViolation as exc:
            if str(tampered_params) not in str(exc):
                raise AssertionError("tampered params error did not name the mismatched file") from exc
        else:
            raise AssertionError("tampered params were accepted")
        for variant, terminal in scenarios.items():
            fixture = root / variant
            synthetic_root(fixture, variant)
            if variant == "confirmed":
                first_session = schedule["sessions"][0]
                rows_path = session_directory(fixture, first_session, f"{first_session['replicate_id']}.a1") / "rows.jsonl"
                original = rows_path.read_bytes()
                rows_path.write_bytes(original + b" ")
                try:
                    score(fixture, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
                except ScoreViolation as exc:
                    if str(first_session["session_label"]) not in str(exc):
                        raise AssertionError("tampered rows error did not name the session") from exc
                else:
                    raise AssertionError("tampered rows were accepted")
                rows_path.write_bytes(original)
            report, exit_code = score(fixture, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            if report["terminal"] != terminal or exit_code != (2 if variant == "g1-fail" else 0):
                raise AssertionError(f"{variant}: {report['terminal']} exit {exit_code}")
            if variant == "g2-exclusion" and not any(report["g2_horizon_attestation"]["excluded_late_cells"].values()):
                raise AssertionError("g2 exclusion fixture did not exclude late cells")
            if variant == "g3-fail" and report["g3_estimand_support"]["passed"]:
                raise AssertionError("g3 fixture unexpectedly passed")
            if variant == "confirmed":
                decision = report["decision"]
                shared = G0.decision_path(decision["replicate_means"], decision["saturated"], G0.BOOTSTRAP_RESAMPLES)
                if shared != (decision["delta_h"], tuple(decision["percentile_bootstrap_ci"]), report["terminal"]):
                    raise AssertionError("scorer decision differs from shared G0 path")
                repeat, repeat_exit = score(fixture, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
                if repeat_exit != exit_code or canonical_bytes(repeat) != canonical_bytes(report):
                    raise AssertionError("scorer double-run was not byte-identical")

        def expect_evidence_rejection(name, mutate, expected_reason):
            fixture = root / name
            synthetic_root(fixture, "confirmed")
            mutate(fixture)
            try:
                score(fixture, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
            except ScoreViolation as exc:
                if expected_reason not in str(exc):
                    raise AssertionError(f"{name}: expected {expected_reason}, got {exc}") from exc
            else:
                raise AssertionError(f"{name}: malformed evidence accepted")

        def rewrite_usage_entry(manifest, index, mutate):
            entry = manifest["usage_evidence"][index]
            payload = json.loads(base64.b64decode(entry["bytes_base64"]))
            mutate(payload)
            raw = canonical_bytes(payload)
            entry["bytes_base64"] = base64.b64encode(raw).decode()
            entry["sha256"] = hashlib.sha256(raw).hexdigest()

        def rewrite_reset_epochs(fixture, reset_epochs):
            manifest = read_json(fixture / LAUNCH_MANIFEST_NAME)
            assert isinstance(manifest, dict) and len(manifest["usage_evidence"]) == len(reset_epochs)
            for index, reset_at in enumerate(reset_epochs):
                rewrite_usage_entry(manifest, index, lambda payload, reset_at=reset_at: payload.__setitem__("reset_at", reset_at))
            (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))

        initial_reset_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
        advanced_reset_at = initial_reset_at + datetime.timedelta(days=1)
        second_advanced_reset_at = advanced_reset_at + datetime.timedelta(days=1)
        initial_reset = initial_reset_at.isoformat()
        advanced_reset = advanced_reset_at.isoformat()
        second_advanced_reset = second_advanced_reset_at.isoformat()
        backward_reset = (initial_reset_at - datetime.timedelta(days=1)).isoformat()
        one_transition = [initial_reset, initial_reset, *([advanced_reset] * 8)]
        reset_transition = root / "reset-one-transition"
        synthetic_root(reset_transition, "confirmed")
        rewrite_reset_epochs(reset_transition, one_transition)
        report, exit_code = score(reset_transition, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        if report["terminal"] != "CONFIRMED" or exit_code != 0:
            raise AssertionError("one advancing reset transition was not accepted")

        expect_evidence_rejection(
            "reset-second-transition",
            lambda fixture: rewrite_reset_epochs(fixture, [initial_reset, initial_reset, advanced_reset, advanced_reset, *([second_advanced_reset] * 6)]),
            "usage-evidence-reset-epochs-exceeded",
        )
        expect_evidence_rejection(
            "reset-backward",
            lambda fixture: rewrite_reset_epochs(fixture, [initial_reset, initial_reset, *([backward_reset] * 8)]),
            "usage-evidence-reset-not-advancing",
        )
        expect_evidence_rejection(
            "reset-reused",
            lambda fixture: rewrite_reset_epochs(fixture, [initial_reset, initial_reset, advanced_reset, advanced_reset, *([initial_reset] * 6)]),
            "usage-evidence-reset-not-advancing",
        )

        expect_evidence_rejection(
            "evidence-tampered",
            lambda fixture: (lambda manifest: ((manifest["usage_evidence"][0].__setitem__("sha256", "f" * 64)), (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))))(read_json(fixture / LAUNCH_MANIFEST_NAME)),
            "usage-evidence-digest-invalid",
        )
        expect_evidence_rejection(
            "evidence-stale",
            lambda fixture: (lambda manifest: (rewrite_usage_entry(manifest, 0, lambda payload: payload.__setitem__("observed_at", (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=301)).isoformat())), (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))))(read_json(fixture / LAUNCH_MANIFEST_NAME)),
            "usage-evidence-stale",
        )
        expect_evidence_rejection(
            "evidence-reordered",
            lambda fixture: (lambda manifest: ((manifest.__setitem__("usage_evidence", [manifest["usage_evidence"][1], manifest["usage_evidence"][0], *manifest["usage_evidence"][2:]])), (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))))(read_json(fixture / LAUNCH_MANIFEST_NAME)),
            "usage-evidence-nonmonotone",
        )

        def refresh_session_digests(fixture, manifest, session):
            attempt_id = manifest["blocks"][str(session["replicate_id"])]["designated_attempt"]
            directory = session_directory(fixture, session, attempt_id)
            status = manifest["blocks"][str(session["replicate_id"])]["attempts"][0]["sessions"][str(session["session_label"])]
            status["rows_sha256"] = sha256(directory / "rows.jsonl")
            status["driver_evidence_sha256"] = sha256(directory / "cli-attestation.json")

        def refresh_synthetic_ledger(fixture, manifest):
            payload = b""
            for session in schedule["sessions"]:
                block = manifest["blocks"][str(session["replicate_id"])]
                attempt = next(item for item in block["attempts"] if item["attempt_id"] == block["designated_attempt"])
                payload += (fixture / attempt["sessions"][str(session["session_label"])]["artifact_dir"] / "rows.jsonl").read_bytes()
            (fixture / "ledger.jsonl").write_bytes(payload)

        def out_of_contract_driver_argv(fixture):
            manifest = read_json(fixture / LAUNCH_MANIFEST_NAME)
            assert isinstance(manifest, dict)
            session = schedule["sessions"][0]
            directory = session_directory(fixture, session, f"{session['replicate_id']}.a1")
            rows = read_jsonl(directory / "rows.jsonl")
            assert isinstance(rows[0], dict)
            rows[0]["cli_argv"][0] = "/unregistered/python"
            (directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(row) for row in rows))
            attestation = read_json(directory / "cli-attestation.json")
            assert isinstance(attestation, dict)
            attestation["invocations"][0]["argv"] = rows[0]["cli_argv"]
            (directory / "cli-attestation.json").write_bytes(canonical_bytes(attestation))
            refresh_session_digests(fixture, manifest, session)
            refresh_synthetic_ledger(fixture, manifest)
            (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))

        expect_evidence_rejection("evidence-driver-argv", out_of_contract_driver_argv, "cli-evidence-command-invalid")

        def malformed_probe_stdout(fixture):
            add_void_replacement(fixture, schedule)
            manifest = read_json(fixture / LAUNCH_MANIFEST_NAME)
            assert isinstance(manifest, dict)
            entry = manifest["resume_oracles"][0]
            oracle = json.loads(base64.b64decode(entry["bytes_base64"]))
            malformed = b"{"
            oracle["probes"][0]["stdout_bytes_base64"] = base64.b64encode(malformed).decode()
            oracle["probes"][0]["stdout_sha256"] = hashlib.sha256(malformed).hexdigest()
            raw = canonical_bytes(oracle)
            entry["bytes_base64"] = base64.b64encode(raw).decode()
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))

        expect_evidence_rejection("evidence-probe-stdout", malformed_probe_stdout, "resume-oracle-probe-json-invalid")

        def list_valued_probe_stdout(fixture):
            add_void_replacement(fixture, schedule)
            manifest = read_json(fixture / LAUNCH_MANIFEST_NAME)
            assert isinstance(manifest, dict)
            entry = manifest["resume_oracles"][0]
            oracle = json.loads(base64.b64decode(entry["bytes_base64"]))
            malformed = canonical_bytes({"is_error": False, "modelUsage": [ENGINES[0]]})
            oracle["probes"][0]["stdout_bytes_base64"] = base64.b64encode(malformed).decode()
            oracle["probes"][0]["stdout_sha256"] = hashlib.sha256(malformed).hexdigest()
            raw = canonical_bytes(oracle)
            entry["bytes_base64"] = base64.b64encode(raw).decode()
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))

        expect_evidence_rejection("evidence-probe-list-model-usage", list_valued_probe_stdout, "resume-oracle-probe-failed")

        def set_aup_receipt(fixture, refusal=True):
            manifest = read_json(fixture / LAUNCH_MANIFEST_NAME)
            assert isinstance(manifest, dict)
            session = schedule["sessions"][0]
            position = 8
            task = session["tasks"][position - 1]["task_id"]
            directory = session_directory(fixture, session, f"{session['replicate_id']}.a1")
            stdout_path = directory / f"t{position}.{task}" / "cli.stdout"
            receipt = {"is_error": True, "subtype": "success", "terminal_reason": "api_error", "stop_reason": "refusal" if refusal else "end_turn", "api_error_status": None, "modelUsage": {session["engine"]: {}}}
            stdout_path.chmod(0o644)
            stdout_path.write_bytes(canonical_bytes(receipt))
            stdout_path.chmod(0o444)
            rows = read_jsonl(directory / "rows.jsonl")
            assert isinstance(rows[position - 1], dict)
            row = rows[position - 1]
            row["cli_returncode"] = 1
            row["cli_stdout_bytes"] = stdout_path.stat().st_size
            row["cli_stdout_sha256"] = sha256(stdout_path)
            row["manifestations_failed"] = row["manifestations_total"]
            (directory / "rows.jsonl").write_bytes(b"".join(canonical_bytes(value) for value in rows))
            attestation = read_json(directory / "cli-attestation.json")
            assert isinstance(attestation, dict)
            invocation = attestation["invocations"][position - 1]
            invocation["returncode"] = 1
            invocation["stdout"] = {"bytes": row["cli_stdout_bytes"], "sha256": row["cli_stdout_sha256"]}
            (directory / "cli-attestation.json").write_bytes(canonical_bytes(attestation))
            refresh_session_digests(fixture, manifest, session)
            refresh_synthetic_ledger(fixture, manifest)
            (fixture / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(manifest))

        aup_positive = root / "aup-positive"
        synthetic_root(aup_positive, "confirmed")
        set_aup_receipt(aup_positive)
        report, _exit_code = score(aup_positive, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        if not report["diagnostics"]["attempt_censuses"]["designated_attempts_aup_by_engine_task_position"]:
            raise AssertionError("AUP refusal was not counted by its registered classifier")
        aup_negative = root / "aup-negative"
        synthetic_root(aup_negative, "confirmed")
        set_aup_receipt(aup_negative, refusal=False)
        report, _exit_code = score(aup_negative, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        if report["diagnostics"]["attempt_censuses"]["designated_attempts_aup_by_engine_task_position"]:
            raise AssertionError("non-refusal receipt entered AUP census")
        late_position = root / "late-position-crossing"
        synthetic_root(late_position, "confirmed")
        for session in schedule["sessions"]:
            ledger_path = session_directory(late_position, session, f"{session['replicate_id']}.a1") / "boundary-ledger.json"
            ledger = read_json(ledger_path)
            ledger["boundaries"][3]["peak_effective_context"] = 1000
            ledger["boundaries"][4]["peak_effective_context"] = 100000
            ledger_path.write_bytes(canonical_bytes(ledger))
        write_synthetic_manifest(late_position, schedule)
        report, exit_code = score(late_position, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        if report["terminal"] != "INCONCLUSIVE_AT_PILOT_N" or exit_code != 0:
            raise AssertionError("late-position threshold crossing was accepted")
        if not any("threshold-unreached" in key for key in report["g2_horizon_attestation"]["excluded_late_reasons"]):
            raise AssertionError("late-position threshold crossing was not excluded")
        designated_only = root / "designated-only"
        synthetic_root(designated_only, "confirmed")
        add_void_replacement(designated_only, schedule)
        report, exit_code = score(designated_only, DEFAULT_SCHEDULE, DEFAULT_PARAMS)
        censuses = report["diagnostics"]["attempt_censuses"]
        if exit_code != 0 or censuses["all_attempts"]["infra_invalid_rows"] != 1 or censuses["designated_attempts"].get("infra_invalid_rows", 0) != 0:
            raise AssertionError("T6 void rows entered the designated score join")
        allowance = root / "allowance-exhausted"
        synthetic_root(allowance, "confirmed")
        allowance_manifest = read_json(allowance / LAUNCH_MANIFEST_NAME)
        assert isinstance(allowance_manifest, dict)
        allowance_manifest["terminal"] = "CHARGED_ALLOWANCE_EXHAUSTED"
        (allowance / LAUNCH_MANIFEST_NAME).write_bytes(canonical_bytes(allowance_manifest))
        completed = subprocess.run([sys.executable, str(HERE / "score-0112.py"), "--results-root", str(allowance)], capture_output=True, text=True)
        if completed.returncode != 3 or "charged-allowance-exhausted" not in completed.stdout:
            raise AssertionError(f"charged allowance exit: {completed.returncode}")
    print("SELF_TEST_OK: frozen dependencies, launch digest tamper, G1/G2/G3, strict terminals, deterministic score, charged allowance, designated-only join, strict AUP classifier, reset-transition accounting, post-sweep pause evidence, tampered/stale/reordered usage, registered driver argv, malformed probe stdout, raw stream attestations")


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
        initialize_frozen_dependencies(args.schedule, args.params)
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
