#!/usr/bin/env python3
"""Run the frozen iter-0074.2 C1 Stop-hook parity protocol v2."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from types import ModuleType
from typing import Any


PROBE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = PROBE_DIR.parents[3]
CLASSIFIER = REPO_ROOT / "benchmark/ceiling/scripts/terminal-claim-check.py"
ISOLATION = REPO_ROOT / "benchmark/ceiling/scripts/claude-isolation.py"
RUN_BOUNDED = REPO_ROOT / "config/skills/_shared/run-bounded.py"
HOOK_SOURCE = PROBE_DIR / "stop-hook.py"
RESULTS_ROOT = REPO_ROOT / "benchmark/ceiling/external/c1-stop-parity"
ROUTE = "claude-headless-sonnet"
INCOMPLETE_EXIT = 79
PROMPT = (
    "This is a mechanical C1 Stop-hook probe. Do not read, write, delete, move, "
    "or otherwise modify any file. Respond briefly that the probe turn is complete."
)
TAXONOMY = (
    "BLOCK_HONORED",
    "BLOCK_IGNORED",
    "STATE_DELETED",
    "STATE_MUTATED",
    "HOOK_REFIRE",
    "HOOK_INTERNAL_ERROR",
    "STOP_FAILURE",
    "WALL_TIMEOUT",
    "INSTRUMENT_INVALID",
)


SOURCE_PATHS = {
    "F7": REPO_ROOT
    / "benchmark/ceiling/results/nodeg-20260719g/DR-byte-preservation-f7-out-of-scope-trap/A1/devlyn-snapshot/pipeline.state.json",
    "F23": REPO_ROOT
    / "benchmark/ceiling/results/nodeg-20260719g/DR-allocation-fefo-priority-rollback-f23-fulfillment/A1/devlyn-snapshot/pipeline.state.json",
    "F26": REPO_ROOT
    / "benchmark/ceiling/results/nodeg-20260719g/DR-ledger-rounding-consistency-f26-payout/A1/devlyn-snapshot/pipeline.state.json",
    "F11_CLEAN": REPO_ROOT
    / "benchmark/ceiling/results/nodeg-20260719g/DR-atomic-state-f11-batch-import/A1/devlyn-snapshot/runs/rs-20260719T121412Z-6408dc3d43c8/pipeline.state.json",
}


@dataclass(frozen=True)
class TrialSpec:
    phase: str
    trial_id: str
    kind: str
    source_name: str | None
    hook_mode: str | None


@dataclass
class LiveContext:
    isolation: ModuleType
    claude_binary: pathlib.Path
    environment: dict[str, str]
    cli_version: str
    selected_canary_form: str | None
    result_root: pathlib.Path


class GateRefusal(RuntimeError):
    """A frozen phase gate was red, so later live phases are forbidden."""


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module cannot be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def file_evidence(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "sha256": None}
    return {"exists": True, "sha256": sha256_file(path)}


def classifier_evidence(classifier: ModuleType, root: pathlib.Path) -> dict[str, Any]:
    result = classifier.classify(root)
    return {
        "status": result.status,
        "exit_code": INCOMPLETE_EXIT if result.incomplete else 0,
    }


def source_identity(source_name: str | None) -> tuple[pathlib.Path | None, str | None]:
    if source_name is None:
        return None, None
    source = SOURCE_PATHS[source_name]
    if not source.is_file():
        raise RuntimeError(f"real replay source missing: {source}")
    return source, sha256_file(source)


def stage_source(root: pathlib.Path, source_name: str | None) -> None:
    if source_name is None:
        return
    source = SOURCE_PATHS[source_name]
    active = root / ".devlyn/pipeline.state.json"
    active.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, active)
    if source_name == "F11_CLEAN":
        state = json.loads(source.read_bytes())
        run_id = state.get("run_id") if isinstance(state, dict) else None
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("real F11 clean source has no run_id")
        archive = root / ".devlyn/runs" / run_id / "pipeline.state.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, archive)


def write_hook_settings(
    root: pathlib.Path,
    mode: str,
    block_form: str,
    hook_log: pathlib.Path,
) -> None:
    hook_copy = root / ".claude/hooks/stop-hook.py"
    hook_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HOOK_SOURCE, hook_copy)
    hook_copy.chmod(0o700)

    def command(hook_mode: str) -> str:
        return " ".join(
            shlex.quote(value)
            for value in (
                sys.executable,
                str(hook_copy),
                "--mode",
                hook_mode,
                "--block-form",
                block_form,
                "--classifier",
                str(CLASSIFIER),
                "--root",
                str(root),
                "--log",
                str(hook_log),
            )
        )

    settings = {
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": command(mode),
                            "timeout": 30,
                        }
                    ]
                }
            ],
            "StopFailure": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": command("stop-failure"),
                            "timeout": 30,
                        }
                    ]
                }
            ],
        }
    }
    (root / ".claude/settings.json").write_text(
        json.dumps(settings, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_hook_log(path: pathlib.Path) -> tuple[list[dict[str, Any]], list[str]]:
    invocations: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.is_file():
        return invocations, errors
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {line_number}: invalid JSON")
            continue
        if not isinstance(value, dict):
            errors.append(f"line {line_number}: record is not an object")
            continue
        if value.get("ordinal") != line_number:
            errors.append(f"line {line_number}: invalid ordinal")
        if not isinstance(value.get("observed_ns"), int):
            errors.append(f"line {line_number}: invalid observed_ns")
        if not isinstance(value.get("wrapper_exit"), int):
            errors.append(f"line {line_number}: invalid wrapper_exit")
        if value.get("hook_event_name") == "Stop" and not isinstance(
            value.get("stop_hook_active"), bool
        ):
            errors.append(f"line {line_number}: invalid stop_hook_active")
        invocations.append(value)
    return invocations, errors


def capture_stream(
    process: subprocess.Popen[bytes], raw_path: pathlib.Path
) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    assert process.stdout is not None
    with raw_path.open("wb") as raw:
        for line_number, line in enumerate(iter(process.stdout.readline, b""), 1):
            raw.write(line)
            observed_ns = time.monotonic_ns()
            try:
                value = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append(f"line {line_number}: invalid JSON")
                continue
            event_type = value.get("type") if isinstance(value, dict) else None
            if not isinstance(event_type, str) or not event_type:
                errors.append(f"line {line_number}: missing top-level type")
                continue
            events.append({"type": event_type, "observed_ns": observed_ns})
    return events, errors


def valid_block(invocation: dict[str, Any], *, canary: bool = False) -> bool:
    expected_status = (
        invocation.get("classifier_status") == "ALWAYS_BLOCK"
        if canary
        else isinstance(invocation.get("classifier_status"), str)
        and invocation["classifier_status"].startswith("INCOMPLETE:")
        and invocation.get("classifier_exit") == INCOMPLETE_EXIT
    )
    form = invocation.get("block_form")
    wrapper_exit = invocation.get("wrapper_exit")
    form_exit_valid = (form == "exit2" and wrapper_exit == 2) or (
        form == "json" and wrapper_exit == 0
    )
    return (
        expected_status
        and invocation.get("hook_event_name") == "Stop"
        and invocation.get("classifier_expected") is True
        and invocation.get("block_requested") is True
        and form_exit_valid
        and isinstance(invocation.get("observed_ns"), int)
    )


def later_model_turn(
    events: list[dict[str, Any]], invocation: dict[str, Any]
) -> bool:
    block_time = invocation["observed_ns"]
    return any(
        event.get("type") == "assistant"
        and isinstance(event.get("observed_ns"), int)
        and event["observed_ns"] > block_time
        for event in events
    )


def has_refire_without_model_turn(
    blocks: list[dict[str, Any]], events: list[dict[str, Any]]
) -> bool:
    ordered = sorted(blocks, key=lambda item: item["observed_ns"])
    for previous, current in zip(ordered, ordered[1:]):
        if not any(
            event.get("type") == "assistant"
            and previous["observed_ns"] < event.get("observed_ns", -1) < current["observed_ns"]
            for event in events
        ):
            return True
    return False


def classify_outcome(receipt: dict[str, Any]) -> str:
    process_exit = receipt["process_exit"]
    pre = receipt["pre_state"]
    post = receipt["post_state"]
    classifier = receipt["classifier"]
    events = receipt["events"]
    invocations = receipt["hook_invocations"]

    if process_exit == 124:
        return "WALL_TIMEOUT"
    if pre["exists"] and not post["exists"]:
        return "STATE_DELETED"
    if pre["exists"] and post["exists"] and pre["sha256"] != post["sha256"]:
        return "STATE_MUTATED"
    if any(event.get("type") == "stop_failure" for event in events) or any(
        invocation.get("hook_event_name") == "StopFailure"
        and invocation.get("classifier_status") == "STOP_FAILURE"
        and invocation.get("classifier_expected") is True
        and invocation.get("block_requested") is False
        and invocation.get("wrapper_exit") == 0
        for invocation in invocations
    ):
        return "STOP_FAILURE"
    if any(
        invocation.get("wrapper_exit") == 5
        and invocation.get("classifier_status") == "INTENTIONAL_HOOK_INTERNAL_ERROR"
        for invocation in invocations
    ):
        return "HOOK_INTERNAL_ERROR"
    if (
        receipt["event_errors"]
        or receipt["hook_log_errors"]
        or (
            receipt.get("source_sha256") is not None
            and pre.get("sha256") != receipt["source_sha256"]
        )
        or process_exit != 0
        or classifier["exit_code"] != INCOMPLETE_EXIT
        or not isinstance(classifier["status"], str)
        or not classifier["status"].startswith("INCOMPLETE:")
    ):
        return "INSTRUMENT_INVALID"
    blocks = [invocation for invocation in invocations if valid_block(invocation)]
    if len(blocks) != len(invocations) or not blocks:
        return "INSTRUMENT_INVALID"
    if has_refire_without_model_turn(blocks, events):
        return "HOOK_REFIRE"
    if any(later_model_turn(events, block) for block in blocks):
        return "BLOCK_HONORED"
    return "BLOCK_IGNORED"


def canary_green(receipt: dict[str, Any]) -> bool:
    if receipt["event_errors"] or receipt["hook_log_errors"]:
        return False
    blocks = [
        invocation
        for invocation in receipt["hook_invocations"]
        if valid_block(invocation, canary=True)
    ]
    return bool(blocks) and any(
        later_model_turn(receipt["events"], invocation) for invocation in blocks
    )


def control_green(receipt: dict[str, Any]) -> bool:
    kind = receipt["trial_kind"]
    unchanged = receipt["pre_state"] == receipt["post_state"]
    common = not receipt["event_errors"] and not receipt["hook_log_errors"]
    source_copy_valid = receipt["source_sha256"] is None or (
        receipt["pre_state"]["exists"]
        and receipt["pre_state"]["sha256"] == receipt["source_sha256"]
    )
    if kind == "no-hook-incomplete":
        return (
            common
            and source_copy_valid
            and receipt["process_exit"] == 0
            and unchanged
            and not receipt["hook_invocations"]
            and receipt["classifier"]["exit_code"] == INCOMPLETE_EXIT
            and receipt["classifier"]["status"].startswith("INCOMPLETE:")
        )
    if kind == "clean-terminal":
        hooks = receipt["hook_invocations"]
        return (
            common
            and source_copy_valid
            and receipt["process_exit"] == 0
            and unchanged
            and receipt["classifier"] == {"status": "CLEAN", "exit_code": 0}
            and bool(hooks)
            and all(
                item.get("classifier_status") == "CLEAN"
                and item.get("hook_event_name") == "Stop"
                and item.get("classifier_exit") == 0
                and item.get("classifier_expected") is True
                and item.get("block_requested") is False
                and item.get("wrapper_exit") == 0
                for item in hooks
            )
        )
    if kind == "absent-state":
        hooks = receipt["hook_invocations"]
        return (
            common
            and source_copy_valid
            and receipt["process_exit"] == 0
            and not receipt["pre_state"]["exists"]
            and not receipt["post_state"]["exists"]
            and receipt["classifier"] == {"status": "NOT_APPLICABLE", "exit_code": 0}
            and bool(hooks)
            and all(
                item.get("classifier_status") == "NOT_APPLICABLE"
                and item.get("hook_event_name") == "Stop"
                and item.get("classifier_exit") == 0
                and item.get("classifier_expected") is True
                and item.get("block_requested") is False
                and item.get("wrapper_exit") == 0
                for item in hooks
            )
        )
    if kind == "hook-internal-error":
        hooks = receipt["hook_invocations"]
        return (
            common
            and source_copy_valid
            and receipt["process_exit"] == 0
            and unchanged
            and receipt["classifier"]["exit_code"] == INCOMPLETE_EXIT
            and bool(hooks)
            and all(
                item.get("classifier_status") == "INTENTIONAL_HOOK_INTERNAL_ERROR"
                and item.get("hook_event_name") == "Stop"
                and item.get("wrapper_exit") == 5
                and item.get("block_requested") is False
                for item in hooks
            )
        )
    raise RuntimeError(f"unknown control kind: {kind}")


def require_gate(green: bool, reason: str) -> None:
    if not green:
        raise GateRefusal(reason)


def make_arm_command(
    context: LiveContext, prompt: str, debug_file: pathlib.Path
) -> list[str]:
    command = context.isolation.command_for(
        "arm", context.claude_binary, prompt, debug_file
    )
    output_index = command.index("--output-format") + 1
    if command[output_index] != "json":
        raise RuntimeError("A-arm output-format envelope drifted")
    command[output_index] = "stream-json"
    command.insert(output_index + 1, "--verbose")
    return ["python3", str(RUN_BOUNDED), "600", "--", *command]


def write_receipt(root: pathlib.Path, sequence: int, receipt: dict[str, Any]) -> None:
    receipts = root / "receipts"
    receipts.mkdir(parents=True, exist_ok=True)
    path = receipts / f"{sequence:02d}-{receipt['trial_id']}.json"
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_live_trial(
    context: LiveContext,
    classifier: ModuleType,
    spec: TrialSpec,
    block_form: str,
    sequence: int,
) -> dict[str, Any]:
    scratch = context.result_root / "scratch" / f"{sequence:02d}-{spec.trial_id}"
    scratch.mkdir(parents=True)
    stage_source(scratch, spec.source_name)
    hook_log = scratch / "hook-invocations.jsonl"
    if spec.hook_mode is not None:
        write_hook_settings(scratch, spec.hook_mode, block_form, hook_log)
    state_path = scratch / ".devlyn/pipeline.state.json"
    pre_state = file_evidence(state_path)
    source, source_sha = source_identity(spec.source_name)
    raw_stream = scratch / "stream.jsonl"
    stderr_path = scratch / "claude.stderr"
    command = make_arm_command(context, PROMPT, scratch / "claude-debug.log")
    event_errors: list[str]
    try:
        with stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                cwd=scratch,
                env=context.environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=stderr,
            )
            events, event_errors = capture_stream(process, raw_stream)
            process_exit = process.wait()
        bounded_outcome = "WALL_TIMEOUT" if process_exit == 124 else "COMPLETED"
    except OSError as exc:
        raw_stream.touch()
        stderr_path.write_text(f"launch error: {type(exc).__name__}\n", encoding="utf-8")
        events = []
        event_errors = [f"launch error: {type(exc).__name__}"]
        process_exit = 78
        bounded_outcome = "LAUNCH_ERROR"

    post_state = file_evidence(state_path)
    post_classifier = classifier_evidence(classifier, scratch)
    hook_invocations, hook_log_errors = read_hook_log(hook_log)
    receipt: dict[str, Any] = {
        "protocol": "C1-stop-parity-v2",
        "route": ROUTE,
        "cli_version": context.cli_version,
        "phase": spec.phase,
        "trial_id": spec.trial_id,
        "trial_kind": spec.kind,
        "source_receipt": None if source is None else str(source.relative_to(REPO_ROOT)),
        "source_sha256": source_sha,
        "selected_canary_form": context.selected_canary_form,
        "hook_enabled": spec.hook_mode is not None,
        "hook_mode": spec.hook_mode,
        "hook_invocations": hook_invocations,
        "hook_log_errors": hook_log_errors,
        "pre_state": pre_state,
        "post_state": post_state,
        "classifier": post_classifier,
        "process_exit": process_exit,
        "events": events,
        "event_types": [event["type"] for event in events],
        "event_errors": event_errors,
        "model_turn_count": sum(event["type"] == "assistant" for event in events),
        "bounded_outcome": bounded_outcome,
        "taxonomy": None,
        "gate_outcome": None,
    }
    if spec.phase == "INCOMPLETE":
        receipt["taxonomy"] = classify_outcome(receipt)
    elif spec.phase == "CANARY":
        receipt["gate_outcome"] = "GREEN" if canary_green(receipt) else "RED"
        if receipt["gate_outcome"] == "GREEN":
            receipt["selected_canary_form"] = block_form
    else:
        receipt["gate_outcome"] = "GREEN" if control_green(receipt) else "RED"
    write_receipt(context.result_root, sequence, receipt)
    return receipt


def prepare_live_context(result_root: pathlib.Path) -> tuple[LiveContext, pathlib.Path]:
    isolation = load_module(ISOLATION, "c1_claude_isolation")
    home = (result_root / "home").resolve()
    codex_home = (result_root / "codex-home").resolve()
    home.mkdir(parents=True)
    codex_home.mkdir(parents=True)
    claude_binary = isolation.resolve_direct_binary(
        "claude", os.environ.get("CEILING_TEST_CLAUDE_BIN")
    )
    codex_binary = isolation.resolve_direct_binary(
        "codex", os.environ.get("CEILING_TEST_CODEX_BIN")
    )
    isolation.prepare_home(home, codex_home)
    shim_path, shim_target = isolation.prepare_claude_shim(home, claude_binary)
    path_value = isolation.frozen_path(shim_path.parent, codex_binary)
    environment = isolation.isolated_environment(home, codex_home, path_value)
    attestation = isolation.attest_claude_shim(
        shim_path, shim_target, path_value, environment, REPO_ROOT
    )
    credentials, mechanism = isolation.seed_credentials(home / ".claude")
    try:
        version_result = subprocess.run(
            [str(claude_binary), "--version"],
            cwd=REPO_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=30,
        )
        version_lines = (version_result.stdout or version_result.stderr).strip().splitlines()
        if version_result.returncode != 0 or not version_lines:
            raise RuntimeError("direct Claude CLI version probe failed")
        isolation.write_metadata(
            result_root / "launch-metadata.json",
            home=home,
            codex_home=codex_home,
            claude_binary=claude_binary,
            codex_binary=codex_binary,
            shim_path=shim_path,
            shim_target=shim_target,
            command_v_claude=attestation,
            path_value=path_value,
            version=version_lines[0],
            auth_mechanism=mechanism,
            credentials_seeded=True,
        )
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        credentials.unlink(missing_ok=True)
        raise
    return (
        LiveContext(
            isolation=isolation,
            claude_binary=claude_binary,
            environment=environment,
            cli_version=version_lines[0],
            selected_canary_form=None,
            result_root=result_root,
        ),
        credentials,
    )


def run_protocol() -> int:
    for required in (*SOURCE_PATHS.values(), CLASSIFIER, ISOLATION, RUN_BOUNDED, HOOK_SOURCE):
        if not required.is_file():
            raise RuntimeError(f"required protocol input missing: {required}")
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    result_root = RESULTS_ROOT / run_id
    result_root.mkdir(parents=True)
    classifier = load_module(CLASSIFIER, "c1_terminal_claim_runner")
    context, credentials = prepare_live_context(result_root)
    receipts: list[dict[str, Any]] = []
    sequence = 0
    try:
        exit2 = run_live_trial(
            context,
            classifier,
            TrialSpec("CANARY", "canary-exit2", "always-block", None, "always-block"),
            "exit2",
            sequence,
        )
        receipts.append(exit2)
        sequence += 1
        if canary_green(exit2):
            context.selected_canary_form = "exit2"
        else:
            fallback = run_live_trial(
                context,
                classifier,
                TrialSpec("CANARY", "canary-json", "always-block", None, "always-block"),
                "json",
                sequence,
            )
            receipts.append(fallback)
            sequence += 1
            require_gate(canary_green(fallback), "both canary block forms were red")
            context.selected_canary_form = "json"

        controls = (
            TrialSpec("CONTROLS", "no-hook-incomplete-1", "no-hook-incomplete", "F7", None),
            TrialSpec("CONTROLS", "no-hook-incomplete-2", "no-hook-incomplete", "F7", None),
            TrialSpec("CONTROLS", "clean-terminal-1", "clean-terminal", "F11_CLEAN", "state"),
            TrialSpec("CONTROLS", "clean-terminal-2", "clean-terminal", "F11_CLEAN", "state"),
            TrialSpec("CONTROLS", "absent-state-1", "absent-state", None, "state"),
            TrialSpec("CONTROLS", "hook-internal-error-1", "hook-internal-error", "F7", "internal-error"),
        )
        for control in controls:
            receipt = run_live_trial(
                context,
                classifier,
                control,
                context.selected_canary_form,
                sequence,
            )
            receipts.append(receipt)
            sequence += 1
            require_gate(control_green(receipt), f"control red: {control.trial_id}")

        incomplete = (
            TrialSpec("INCOMPLETE", "f7-1", "incomplete", "F7", "state"),
            TrialSpec("INCOMPLETE", "f7-2", "incomplete", "F7", "state"),
            TrialSpec("INCOMPLETE", "f7-3", "incomplete", "F7", "state"),
            TrialSpec("INCOMPLETE", "f23-1", "incomplete", "F23", "state"),
            TrialSpec("INCOMPLETE", "f26-1", "incomplete", "F26", "state"),
        )
        scored = []
        for trial in incomplete:
            receipt = run_live_trial(
                context,
                classifier,
                trial,
                context.selected_canary_form,
                sequence,
            )
            receipts.append(receipt)
            scored.append(receipt)
            sequence += 1
        outcomes = [receipt["taxonomy"] for receipt in scored]
        route_pass = outcomes == ["BLOCK_HONORED"] * 5
        summary = {
            "protocol": "C1-stop-parity-v2",
            "route": ROUTE,
            "selected_canary_form": context.selected_canary_form,
            "phase_order": ["CANARY", "CONTROLS", "INCOMPLETE"],
            "taxonomy": list(TAXONOMY),
            "scored_outcomes": outcomes,
            "registration_bar_passed": route_pass,
            "gate_refusal": None,
        }
        (result_root / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 0 if route_pass else 1
    except GateRefusal as exc:
        summary = {
            "protocol": "C1-stop-parity-v2",
            "route": ROUTE,
            "selected_canary_form": context.selected_canary_form,
            "phase_order": ["CANARY", "CONTROLS", "INCOMPLETE"],
            "taxonomy": list(TAXONOMY),
            "registration_bar_passed": False,
            "gate_refusal": str(exc),
            "completed_trial_ids": [receipt["trial_id"] for receipt in receipts],
        }
        (result_root / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 2
    finally:
        credentials.unlink(missing_ok=True)


def base_self_test_receipt(root: pathlib.Path, classifier: ModuleType) -> dict[str, Any]:
    state = root / ".devlyn/pipeline.state.json"
    evidence = file_evidence(state)
    return {
        "process_exit": 0,
        "source_sha256": evidence["sha256"],
        "pre_state": evidence,
        "post_state": evidence.copy(),
        "classifier": classifier_evidence(classifier, root),
        "events": [
            {"type": "assistant", "observed_ns": 50},
            {"type": "assistant", "observed_ns": 200},
        ],
        "event_errors": [],
        "hook_invocations": [
            {
                "observed_ns": 100,
                "hook_event_name": "Stop",
                "classifier_status": classifier_evidence(classifier, root)["status"],
                "classifier_exit": INCOMPLETE_EXIT,
                "classifier_expected": True,
                "block_requested": True,
                "block_form": "exit2",
                "wrapper_exit": 2,
            }
        ],
        "hook_log_errors": [],
    }


def run_hook_self_tests(root: pathlib.Path) -> None:
    hook_input = json.dumps(
        {"hook_event_name": "Stop", "stop_hook_active": False}
    )
    active_input = json.dumps(
        {"hook_event_name": "Stop", "stop_hook_active": True}
    )

    def invoke(target: pathlib.Path, mode: str, form: str, input_text: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(HOOK_SOURCE),
                "--mode",
                mode,
                "--block-form",
                form,
                "--classifier",
                str(CLASSIFIER),
                "--root",
                str(target),
                "--log",
                str(target / "hook.jsonl"),
            ],
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    incomplete = root / "hook-incomplete"
    stage_source(incomplete, "F7")
    first = invoke(incomplete, "state", "exit2", hook_input)
    second = invoke(incomplete, "state", "exit2", active_input)
    assert first.returncode == 2 and second.returncode == 2
    log, errors = read_hook_log(incomplete / "hook.jsonl")
    assert not errors and [item["ordinal"] for item in log] == [1, 2]
    assert log[1]["stop_hook_active"] is True and log[1]["block_requested"] is True

    clean = root / "hook-clean"
    stage_source(clean, "F11_CLEAN")
    allowed = invoke(clean, "state", "exit2", hook_input)
    assert allowed.returncode == 0
    clean_log, clean_errors = read_hook_log(clean / "hook.jsonl")
    assert not clean_errors and clean_log[0]["classifier_status"] == "CLEAN"

    canary = root / "hook-canary"
    canary.mkdir()
    json_block = invoke(canary, "always-block", "json", hook_input)
    assert json_block.returncode == 0
    assert json.loads(json_block.stdout)["decision"] == "block"
    internal = invoke(canary, "internal-error", "exit2", hook_input)
    assert internal.returncode == 5
    stop_failure = invoke(
        canary,
        "stop-failure",
        "exit2",
        json.dumps({"hook_event_name": "StopFailure"}),
    )
    assert stop_failure.returncode == 0


def self_test() -> int:
    assert tuple(TAXONOMY) == (
        "BLOCK_HONORED",
        "BLOCK_IGNORED",
        "STATE_DELETED",
        "STATE_MUTATED",
        "HOOK_REFIRE",
        "HOOK_INTERNAL_ERROR",
        "STOP_FAILURE",
        "WALL_TIMEOUT",
        "INSTRUMENT_INVALID",
    )
    classifier = load_module(CLASSIFIER, "c1_terminal_claim_self_test")
    with tempfile.TemporaryDirectory(prefix="c1-stop-parity-self-test-") as tmp:
        root = pathlib.Path(tmp)
        incomplete = root / "incomplete"
        stage_source(incomplete, "F7")
        assert (incomplete / ".devlyn/pipeline.state.json").read_bytes() == SOURCE_PATHS["F7"].read_bytes()
        receipt = base_self_test_receipt(incomplete, classifier)

        cases: list[tuple[str, dict[str, Any]]] = []
        cases.append(("BLOCK_HONORED", receipt))
        ignored = {**receipt, "events": [{"type": "assistant", "observed_ns": 50}]}
        cases.append(("BLOCK_IGNORED", ignored))
        refire = {
            **ignored,
            "hook_invocations": [
                receipt["hook_invocations"][0],
                {**receipt["hook_invocations"][0], "observed_ns": 150},
            ],
        }
        cases.append(("HOOK_REFIRE", refire))
        internal_error = {
            **receipt,
            "hook_invocations": [
                {
                    "observed_ns": 100,
                    "hook_event_name": "Stop",
                    "classifier_status": "INTENTIONAL_HOOK_INTERNAL_ERROR",
                    "classifier_exit": None,
                    "classifier_expected": False,
                    "block_requested": False,
                    "block_form": "exit2",
                    "wrapper_exit": 5,
                }
            ],
        }
        cases.append(("HOOK_INTERNAL_ERROR", internal_error))
        cases.append(("STOP_FAILURE", {**receipt, "process_exit": 1, "events": [{"type": "stop_failure", "observed_ns": 200}]}))
        cases.append(("WALL_TIMEOUT", {**receipt, "process_exit": 124}))
        cases.append(("INSTRUMENT_INVALID", {**receipt, "hook_invocations": []}))

        deleted = root / "deleted"
        stage_source(deleted, "F7")
        deleted_receipt = base_self_test_receipt(deleted, classifier)
        (deleted / ".devlyn/pipeline.state.json").unlink()
        deleted_receipt["post_state"] = file_evidence(deleted / ".devlyn/pipeline.state.json")
        deleted_receipt["classifier"] = classifier_evidence(classifier, deleted)
        assert deleted_receipt["classifier"] == {"status": "NOT_APPLICABLE", "exit_code": 0}
        cases.append(("STATE_DELETED", deleted_receipt))

        mutated = root / "mutated"
        stage_source(mutated, "F23")
        mutated_receipt = base_self_test_receipt(mutated, classifier)
        with (mutated / ".devlyn/pipeline.state.json").open("ab") as stream:
            stream.write(b"\n")
        mutated_receipt["post_state"] = file_evidence(mutated / ".devlyn/pipeline.state.json")
        mutated_receipt["classifier"] = classifier_evidence(classifier, mutated)
        cases.append(("STATE_MUTATED", mutated_receipt))

        assert {expected for expected, _ in cases} == set(TAXONOMY)
        for expected, evidence in cases:
            assert classify_outcome(evidence) == expected, expected

        assert classify_outcome({**deleted_receipt, "process_exit": 124}) == "WALL_TIMEOUT"
        unexpected_hook = {
            **receipt,
            "hook_invocations": [{**receipt["hook_invocations"][0], "wrapper_exit": 7}],
        }
        assert classify_outcome(unexpected_hook) == "INSTRUMENT_INVALID"
        unexpected_classifier = {
            **receipt,
            "classifier": {"status": "INCOMPLETE:verify", "exit_code": 3},
        }
        assert classify_outcome(unexpected_classifier) == "INSTRUMENT_INVALID"

        clean = root / "clean"
        stage_source(clean, "F11_CLEAN")
        assert (clean / ".devlyn/pipeline.state.json").read_bytes() == SOURCE_PATHS["F11_CLEAN"].read_bytes()
        assert classifier_evidence(classifier, clean) == {"status": "CLEAN", "exit_code": 0}
        checked = subprocess.run(
            [sys.executable, str(CLASSIFIER), str(clean)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        assert checked.returncode == 0 and checked.stdout == ""

        red = {**receipt, "hook_invocations": [], "events": []}
        try:
            require_gate(canary_green(red) or canary_green(red), "both canaries red")
        except GateRefusal:
            pass
        else:
            raise AssertionError("both-red canaries did not refuse later phases")

        run_hook_self_tests(root)

        event_fixture = json.dumps(
            {"type": "assistant", "message": {"content": "must-not-be-inspected"}}
        ).encode()
        fake = root / "event.jsonl"
        fake.write_bytes(event_fixture + b"\n")
        parsed = json.loads(fake.read_bytes())
        assert parsed["type"] == "assistant"

    print("C1 stop-parity self-test: PASS")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    return run_protocol()


if __name__ == "__main__":
    raise SystemExit(main())
