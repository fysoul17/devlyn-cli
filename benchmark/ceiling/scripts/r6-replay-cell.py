#!/usr/bin/env python3
"""Frozen-input iter-0072 Registration-v6 replay-selection probe."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


sys.dont_write_bytecode = True


REPO = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
ARCHIVED_RESULTS_DIR = REPO / "benchmark/ceiling/results/r6-replay-20260718"
RESULTS_DIR = REPO / "benchmark/ceiling/results/r6-replay-am5-20260718"
TMP_ROOT = Path("/tmp/codex-0072-am5-build/r6-replay-work")
CANONICAL_BODY = REPO / "config/skills/devlyn:resolve/references/phases/surface-close.md"
RESTRICTED_CELL = "FL1-sonnet"
RESTRICTED_TOOLS_CSV = "Read,Grep,Glob,Edit,Write"
PROMPTS = {
    "F1": {
        "source_path": ARCHIVED_RESULTS_DIR / "f1-prompt.txt",
        "filename": "f1-prompt.txt",
        "sha256": "00cddba55a0aaabff3e4dbea1264c412e806a293408bf25378babd8c7dbd23b1",
    },
    "FL1": {
        "source_path": ARCHIVED_RESULTS_DIR / "fl1-prompt.txt",
        "filename": "fl1-prompt.txt",
        # Amendment 5 frozen-input revision: the archived template remains
        # pinned separately; this pin is the prompt with the NEW canonical body.
        "template_sha256": "b422dd6e6783945f43059ffa2ad0cae76aac270289720416e5b0ea838bee5e83",
        "sha256": "72eead4dc71b3b02ec50f38d888576edea021c80d6e47699519982f5c388d71d",
    },
}
BUNDLE = (
    REPO
    / "benchmark/ceiling/results/nodeg-20260718c/gate-fail-artifacts/f7-row-repo.bundle"
)
OVERLAY = (
    REPO
    / "benchmark/ceiling/results/nodeg-20260718c/gate-fail-artifacts/"
    "f7-row-workspace-untracked.tgz"
)
PRE_SHA = "947dbf71494fc55bccf1c7f0dfe41959b1a65bd7"
CONTROL_BASE_SHA = "e5a20d983f63e62ad264174c025fad97769e9fc5"
GOAL_SHA = "f3467374f6554ece0b14e48250222d11fc6675aae4cb0ded70fc3503a78c9674"
PATCH_SHA = "cfac5a9fafc59a1ddf019f1fb49412e5ddfd8ff393c28619b8de641997e56c9b"
AUTHORIZED_SURFACE = ("bin/cli.js", "tests/cli.test.js")
OBLIGATIONS = ("UVR-STALE", "PATH-TEST")
MODEL_BY_ENGINE = {"terra": "gpt-5.6-terra", "sonnet": "sonnet"}
CELLS = (
    ("F1-terra", "F1", "terra"),
    ("F1-sonnet", "F1", "sonnet"),
    ("FL1-terra", "FL1", "terra"),
    ("FL1-sonnet", "FL1", "sonnet"),
)
GLOBAL_CAP = 12
CONTROL_WORKER_CAP = 4
CONTROL_NAMES = ("control-a-no-stale", "control-b-goal-frozen")
TIMEOUT_SECONDS = 600
REGISTRATION = "iter-0072 Registration v6 Amendment 5 / DECISIONS 0072.21"
VALIDATION_COMMAND_PATTERN = re.compile(
    r"npm\s+test|node\s+--test|node\s+-e|node\s+bin/|node\s+tests/|git\s+stash"
)
RECEIPT_FIELDS = {
    "schema_version",
    "cell",
    "replica",
    "prompt_variant",
    "engine",
    "requested_model",
    "effective_model",
    "effective_model_source",
    "cli_version",
    "prompt_sha256",
    "pre_tree",
    "post_tree",
    "delta_sha256",
    "output_sha256",
    "elapsed_seconds",
    "fresh_home",
    "exit_code",
    "timed_out",
    "readout",
    "phase_boundary",
    "execution_audit",
    "restriction_receipts",
    "valid",
    "invalid_reasons",
}
CONTROL_RECEIPT_FIELDS = RECEIPT_FIELDS | {
    "control",
    "control_inputs",
    "expected_disposition",
    "expected_delta",
    "control_scoring",
}


class ProbeError(RuntimeError):
    """The frozen replay contract could not be established."""


@dataclass(frozen=True)
class PreparedWorkspace:
    path: Path
    overlay_input_source: str
    pre_status: str
    pre_untracked: dict[str, str]


@dataclass(frozen=True)
class ControlContract:
    name: str
    goal: bytes
    input_patch: bytes
    expected_disposition: dict[str, str]
    expected_delta: str


@dataclass(frozen=True)
class PreparedControlWorkspace:
    prepared: PreparedWorkspace
    pre_tracked: dict[str, str]
    goal_sha256: str
    patch_sha256: str
    usage_sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    stdout: Any = subprocess.PIPE,
    stderr: Any = subprocess.PIPE,
    text: bool = True,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=stdout,
        stderr=stderr,
        text=text,
        timeout=timeout,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[Any], label: str) -> None:
    if result.returncode == 0:
        return
    stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else result.stderr
    raise ProbeError(f"{label} failed ({result.returncode}): {(stderr or '').strip()[:500]}")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def carrier_predicates() -> tuple[Callable[[str], tuple[bool, str]], Callable[[str], tuple[bool, str]]]:
    """Import and invoke the exact shared check-7/check-8 gate predicates."""
    gate = load_module(SCRIPT_DIR / "f7-carrier-gate.py", "r6_f7_carrier_gate")
    functions = {name: getattr(gate, name, None) for name in ("check7", "check8")}
    if not all(callable(function) for function in functions.values()):
        raise ProbeError("f7-carrier-gate.py check7/check8 predicates not found")
    return functions["check7"], functions["check8"]


def static_readout(workspace: Path) -> dict[str, Any]:
    check7, check8 = carrier_predicates()
    uvr, uvr_note = check7((workspace / "bin/cli.js").read_text(encoding="utf-8"))
    path_test, path_note = check8((workspace / "tests/cli.test.js").read_text(encoding="utf-8"))
    return {
        "uvr_fired": uvr,
        "uvr_evidence": uvr_note,
        "path_test_fired": path_test,
        "path_test_evidence": path_note,
        "predicate_source": "benchmark/ceiling/scripts/f7-carrier-gate.py:check7/check8",
    }


def git_output(workspace: Path, *arguments: str) -> str:
    result = run_command(["git", *arguments], cwd=workspace)
    require_success(result, "git " + " ".join(arguments))
    return result.stdout


def untracked_snapshot(workspace: Path) -> dict[str, str]:
    result = run_command(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=workspace, text=False
    )
    require_success(result, "git ls-files --others")
    snapshot: dict[str, str] = {}
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="strict")
        candidate = workspace / relative
        if candidate.is_file() and not candidate.is_symlink():
            mode = stat.S_IMODE(candidate.stat().st_mode)
            snapshot[relative] = f"{mode:o}:{sha256_file(candidate)}"
        elif candidate.is_symlink():
            snapshot[relative] = "symlink:" + os.readlink(candidate)
    return snapshot


def tracked_snapshot(workspace: Path) -> dict[str, str]:
    result = run_command(["git", "ls-files", "-z"], cwd=workspace, text=False)
    require_success(result, "git ls-files")
    snapshot: dict[str, str] = {}
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8", errors="strict")
        candidate = workspace / relative
        if candidate.is_file() and not candidate.is_symlink():
            snapshot[relative] = sha256_file(candidate)
        elif candidate.is_symlink():
            snapshot[relative] = "symlink:" + os.readlink(candidate)
        else:
            snapshot[relative] = "missing"
    return snapshot


def changed_snapshot_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(
        path
        for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )


def usage_block_sha256(path: Path) -> str:
    if not path.is_file():
        return "missing"
    matches = re.findall(rb"const USAGE = `.*?`;", path.read_bytes(), flags=re.DOTALL)
    if len(matches) != 1:
        return "malformed"
    return sha256_bytes(matches[0])


def restore_archived_prompt_inputs(workspace: Path) -> str:
    goal = workspace / ".devlyn/goal.raw.txt"
    patch = workspace / ".devlyn/surface-close.input.patch"
    if goal.is_file() and patch.is_file():
        return "overlay-root"
    candidates = sorted((workspace / ".devlyn/runs").glob("*/goal.raw.txt"))
    matched: list[Path] = []
    for archived_goal in candidates:
        archived_patch = archived_goal.parent / "surface-close.input.patch"
        if not archived_patch.is_file():
            continue
        if sha256_file(archived_goal) == GOAL_SHA and sha256_file(archived_patch) == PATCH_SHA:
            matched.append(archived_goal.parent)
    if len(matched) != 1:
        raise ProbeError(
            "overlay root prompt inputs missing and exact archived source is not unique: "
            f"matches={len(matched)}"
        )
    goal.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(matched[0] / "goal.raw.txt", goal)
    shutil.copyfile(matched[0] / "surface-close.input.patch", patch)
    return str(matched[0].relative_to(workspace))


def assert_frozen_workspace(workspace: Path) -> None:
    head = git_output(workspace, "rev-parse", "HEAD").strip()
    if head != PRE_SHA:
        raise ProbeError(f"pre-tree HEAD mismatch: {head}")
    tracked = git_output(workspace, "status", "--porcelain", "--untracked-files=no")
    if tracked:
        raise ProbeError(f"pre-tree tracked state is dirty: {tracked[:500]!r}")
    goal = workspace / ".devlyn/goal.raw.txt"
    patch = workspace / ".devlyn/surface-close.input.patch"
    if not goal.is_file() or sha256_file(goal) != GOAL_SHA:
        raise ProbeError(".devlyn/goal.raw.txt frozen hash mismatch")
    if not patch.is_file() or sha256_file(patch) != PATCH_SHA:
        raise ProbeError(".devlyn/surface-close.input.patch frozen hash mismatch")
    readout = static_readout(workspace)
    if readout["uvr_fired"] or readout["path_test_fired"]:
        raise ProbeError(f"pre-tree carriers are not both open: {readout}")


def prepare_workspace(target: Path) -> PreparedWorkspace:
    if target.exists():
        raise ProbeError(f"fresh workspace already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    clone = run_command(["git", "clone", "--quiet", str(BUNDLE), str(target)])
    require_success(clone, "bundle clone")
    checkout = run_command(["git", "checkout", "--quiet", "--detach", PRE_SHA], cwd=target)
    require_success(checkout, "pre_sha checkout")
    overlay = run_command(["tar", "-xzf", str(OVERLAY), "-C", str(target)])
    require_success(overlay, "workspace overlay extraction")
    input_source = restore_archived_prompt_inputs(target)
    assert_frozen_workspace(target)
    status = git_output(target, "status", "--short", "--untracked-files=normal")
    return PreparedWorkspace(target, input_source, status, untracked_snapshot(target))


VERDICT_PATTERN = re.compile(
    r"^(UVR-STALE|PATH-TEST): (FIRED|N/A) ([^:\n]+):([1-9][0-9]*)"
    r"(?: — ([^\n]+))?$"
)


def parse_verdict_rows(message: str, workspace: Path) -> dict[str, Any]:
    rows: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    row_positions: list[int] = []
    terminal_positions: list[int] = []
    terminal: str | None = None
    lines = message.splitlines()
    for index, line in enumerate(lines):
        if line == "PASS" or line.startswith("BLOCKED:surface-close-"):
            terminal_positions.append(index)
            terminal = line
        match = VERDICT_PATTERN.fullmatch(line)
        if not match:
            if line.startswith("UVR-STALE:"):
                errors.append("malformed-UVR-STALE")
            elif line.startswith("PATH-TEST:"):
                errors.append("malformed-PATH-TEST")
            continue
        obligation, disposition, relative, line_number_text, judgment = match.groups()
        if obligation in rows:
            errors.append(f"duplicate-{obligation}")
            continue
        line_number = int(line_number_text)
        citation_errors: list[str] = []
        if relative not in AUTHORIZED_SURFACE:
            citation_errors.append("out-of-surface")
        candidate = workspace / relative
        if not candidate.is_file():
            citation_errors.append("file-missing")
            line_count = 0
        else:
            line_count = len(candidate.read_text(encoding="utf-8").splitlines())
            if line_number > line_count:
                citation_errors.append("line-missing")
        if disposition == "N/A" and (judgment is None or not judgment.strip()):
            errors.append(f"{obligation}-N/A-missing-judgment")
        rows[obligation] = {
            "disposition": disposition,
            "file": relative,
            "line": line_number,
            "judgment": judgment,
            "citation_valid": not citation_errors,
            "citation_errors": citation_errors,
        }
        row_positions.append(index)
    for obligation in ("UVR-STALE", "PATH-TEST"):
        if obligation not in rows:
            errors.append(f"missing-{obligation}")
        elif not rows[obligation]["citation_valid"]:
            errors.append(f"invalid-citation-{obligation}")
    if len(terminal_positions) != 1:
        errors.append("terminal-count")
    elif row_positions and terminal_positions[0] <= max(row_positions):
        errors.append("terminal-not-after-rows")
    return {"valid": not errors, "rows": rows, "terminal": terminal, "errors": errors}


def terminal_passed(message: str) -> bool:
    terminals = [
        line
        for line in message.splitlines()
        if line == "PASS" or line.startswith("BLOCKED:surface-close-")
    ]
    return terminals == ["PASS"]


def imported_claude_isolation() -> Any:
    return load_module(SCRIPT_DIR / "claude-isolation.py", "r6_claude_isolation")


def direct_binary(name: str) -> Path:
    return imported_claude_isolation().resolve_direct_binary(
        name, os.environ.get(f"CEILING_TEST_{name.upper()}_BIN")
    )


def fresh_codex_environment(home: Path, codex_binary: Path) -> tuple[dict[str, str], Path]:
    codex_home = home / ".codex"
    codex_home.mkdir(parents=True)
    (home / "tmp").mkdir()
    (home / "npm-cache").mkdir()
    (home / ".npmrc").touch()
    (codex_home / "config.toml").write_text(
        'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "xhigh"\n', encoding="utf-8"
    )
    auth_source = Path(
        os.environ.get("CEILING_TEST_AUTH_JSON", str(Path.home() / ".codex/auth.json"))
    )
    if not auth_source.is_file():
        raise ProbeError(f"Codex auth file missing: {auth_source}")
    shutil.copyfile(auth_source, codex_home / "auth.json")
    (codex_home / "auth.json").chmod(stat.S_IRUSR | stat.S_IWUSR)
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "CODEX_HOME": str(codex_home),
            "CODEX_BIN": str(codex_binary),
            "CODEX_MONITORED_TIMEOUT_SEC": str(TIMEOUT_SECONDS),
            "TMPDIR": str(home / "tmp"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "NPM_CONFIG_USERCONFIG": str(home / ".npmrc"),
            "NPM_CONFIG_CACHE": str(home / "npm-cache"),
        }
    )
    return environment, codex_home


def parse_codex_effective_model(codex_home: Path) -> tuple[str | None, str | None]:
    values: list[tuple[str, str]] = []
    for session in sorted(codex_home.glob("sessions/**/*.jsonl")):
        for line in session.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "turn_context":
                continue
            model = (event.get("payload") or {}).get("model")
            if isinstance(model, str) and model:
                values.append((model, str(session.relative_to(codex_home))))
    unique = sorted({value for value, _ in values})
    if len(unique) != 1:
        return None, None
    source = next(path for value, path in values if value == unique[0])
    return unique[0], f"CODEX_HOME/{source}:turn_context.payload.model"


def run_codex(
    workspace: Path, prompt: Path, artifact_dir: Path, home: Path
) -> dict[str, Any]:
    codex_binary = direct_binary("codex")
    version = run_command([str(codex_binary), "--version"])
    require_success(version, "Codex version probe")
    environment, codex_home = fresh_codex_environment(home, codex_binary)
    stdout_path = artifact_dir / "engine.stdout"
    stderr_path = artifact_dir / "engine.stderr"
    engine_final_path = home / "final-message.txt"
    archived_final_path = artifact_dir / "final-message.txt"
    command = [
        "bash",
        str(REPO / "config/skills/_shared/codex-monitored.sh"),
        "-C",
        str(workspace),
        "-s",
        "workspace-write",
        "--json",
        "--color",
        "never",
        "--output-last-message",
        str(engine_final_path),
        prompt.read_text(encoding="utf-8"),
    ]
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        result = run_command(command, env=environment, stdout=stdout, stderr=stderr, text=False)
    elapsed = time.monotonic() - started
    effective, source = parse_codex_effective_model(codex_home)
    final = engine_final_path.read_bytes() if engine_final_path.is_file() else b""
    write_bytes(archived_final_path, final)
    return {
        "exit_code": result.returncode,
        "timed_out": result.returncode == 124,
        "elapsed_seconds": round(elapsed, 3),
        "cli_version": (version.stdout or version.stderr).strip().splitlines()[0],
        "effective_model": effective,
        "effective_model_source": source,
        "final_message": final,
    }


def run_sonnet(
    workspace: Path,
    prompt: Path,
    artifact_dir: Path,
    home: Path,
    tools_csv: str | None = None,
) -> dict[str, Any]:
    codex_home = home / ".codex"
    stdout_path = artifact_dir / "engine.stdout"
    stderr_path = artifact_dir / "engine.stderr"
    metadata_path = artifact_dir / "claude-isolation.json"
    debug_path = artifact_dir / "claude-debug.log"
    command = [
        "python3",
        str(SCRIPT_DIR / "claude-isolation.py"),
        "launch",
        "--mode",
        "arm",
        "--home",
        str(home),
        "--codex-home",
        str(codex_home),
        "--workdir",
        str(workspace),
        "--prompt-file",
        str(prompt),
        "--debug-file",
        str(debug_path),
        "--metadata-out",
        str(metadata_path),
        "--timeout-seconds",
        str(TIMEOUT_SECONDS),
    ]
    if tools_csv is not None:
        command.extend(["--tools-csv", tools_csv])
    user_memory = Path.home() / ".claude/CLAUDE.md"
    if user_memory.is_file():
        command.extend(["--user-memory-file", str(user_memory)])
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        result = run_command(command, stdout=stdout, stderr=stderr, text=False)
    elapsed = time.monotonic() - started
    wrapper: dict[str, Any] = {}
    if stdout_path.is_file():
        try:
            wrapper = json.loads(stdout_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            wrapper = {}
    model_usage = wrapper.get("modelUsage") if isinstance(wrapper, dict) else None
    models = sorted(model_usage) if isinstance(model_usage, dict) else []
    effective = models[0] if len(models) == 1 else None
    final_text = wrapper.get("result") if isinstance(wrapper, dict) else None
    final = final_text.encode("utf-8") if isinstance(final_text, str) else b""
    write_bytes(artifact_dir / "final-message.txt", final)
    metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() else {}
    cli_version = ((metadata.get("direct_claude") or {}).get("version"))
    return {
        "exit_code": result.returncode,
        "timed_out": result.returncode in {78, 124} and b"timed out" in stderr_path.read_bytes().lower(),
        "elapsed_seconds": round(elapsed, 3),
        "cli_version": cli_version,
        "effective_model": effective,
        "effective_model_source": "Claude JSON wrapper:modelUsage" if effective else None,
        "model_usage_present": isinstance(model_usage, dict) and bool(model_usage),
        "final_message": final,
    }


def codex_command_strings(value: Any) -> list[str]:
    commands: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key == "cmd" and isinstance(nested, str):
                commands.append(nested)
            else:
                commands.extend(codex_command_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            commands.extend(codex_command_strings(nested))
    elif isinstance(value, str):
        for match in re.finditer(r'"cmd"\s*:\s*', value):
            try:
                command, _ = json.JSONDecoder().raw_decode(value, match.end())
            except json.JSONDecodeError:
                continue
            if isinstance(command, str):
                commands.append(command)
    return commands


def transcript_commands(transcript: Path, engine: str) -> tuple[list[str], list[str]]:
    commands: list[str] = []
    errors: list[str] = []
    for line_number, line in enumerate(
        transcript.read_text(encoding="utf-8", errors="strict").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"worker-transcript-malformed:{line_number}")
            continue
        if engine == "sonnet":
            content = ((event.get("message") or {}).get("content"))
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                if item.get("name") != "Bash":
                    continue
                command = (item.get("input") or {}).get("command")
                if isinstance(command, str):
                    commands.append(command)
        elif engine == "terra":
            payload = event.get("payload")
            if isinstance(payload, dict) and payload.get("type") == "custom_tool_call":
                commands.extend(codex_command_strings(payload))
        else:
            raise ProbeError(f"unsupported transcript engine: {engine}")
    return commands, errors


def sonnet_bash_tool_use_count(transcript: Path) -> int:
    count = 0
    for line in transcript.read_text(encoding="utf-8", errors="strict").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = ((event.get("message") or {}).get("content"))
        if isinstance(content, list):
            count += sum(
                isinstance(item, dict)
                and item.get("type") == "tool_use"
                and item.get("name") == "Bash"
                for item in content
            )
    return count


def execution_audit_for_transcript(
    transcript: Path, engine: str, *, transcript_path: str = "worker-transcript.jsonl"
) -> tuple[dict[str, Any], list[str]]:
    try:
        commands, errors = transcript_commands(transcript, engine)
    except UnicodeDecodeError:
        commands = []
        errors = ["worker-transcript-not-utf8"]
    hits = [command for command in commands if VALIDATION_COMMAND_PATTERN.search(command)]
    return (
        {
            "n_commands": len(commands),
            "bash_tool_use_count": (
                sonnet_bash_tool_use_count(transcript) if engine == "sonnet" else None
            ),
            "validation_execution": bool(hits),
            "validation_hits": hits,
            "transcript_path": transcript_path,
        },
        errors,
    )


def locate_worker_transcripts(home: Path, engine: str) -> list[Path]:
    if engine == "sonnet":
        pattern = ".claude/projects/**/*.jsonl"
    elif engine == "terra":
        pattern = ".codex/sessions/**/rollout-*.jsonl"
    else:
        raise ProbeError(f"unsupported transcript engine: {engine}")
    return sorted(path for path in home.glob(pattern) if path.is_file())


def archive_and_audit_transcript(
    home: Path, engine: str, artifact_dir: Path
) -> tuple[dict[str, Any], list[str]]:
    sources = locate_worker_transcripts(home, engine)
    archived = artifact_dir / "worker-transcript.jsonl"
    if not sources:
        return (
            {
                "n_commands": 0,
                "bash_tool_use_count": 0 if engine == "sonnet" else None,
                "validation_execution": False,
                "validation_hits": [],
                "transcript_path": None,
            },
            ["worker-transcript-missing"],
        )
    transcript = b""
    for source in sources:
        value = source.read_bytes()
        transcript += value
        if value and not value.endswith(b"\n"):
            transcript += b"\n"
    write_bytes(archived, transcript)
    return execution_audit_for_transcript(archived, engine)


def restriction_receipts(
    tools_csv: str | None, worker: dict[str, Any], execution_audit: dict[str, Any]
) -> dict[str, Any]:
    applied = tools_csv is not None
    zero_bash = applied and execution_audit["bash_tool_use_count"] == 0
    model_usage = applied and bool(worker.get("model_usage_present"))
    jsonl_retained = applied and execution_audit["transcript_path"] is not None
    return {
        "applied": applied,
        "tools_csv": tools_csv,
        "bash_tool_use_count": execution_audit["bash_tool_use_count"] if applied else None,
        "zero_bash_tool_use": zero_bash if applied else None,
        "modelUsage_present": model_usage if applied else None,
        "jsonl_retained": jsonl_retained if applied else None,
        "passed": (zero_bash and model_usage and jsonl_retained) if applied else None,
    }


def worker_invalid_reasons(
    worker: dict[str, Any],
    engine: str,
    execution_audit: dict[str, Any],
    audit_errors: list[str],
    restriction: dict[str, Any],
) -> list[str]:
    invalid_reasons = list(audit_errors)
    if execution_audit["validation_execution"]:
        invalid_reasons.append("validation-execution")
    if worker["exit_code"] != 0:
        invalid_reasons.append("worker-exit-nonzero")
    if worker["timed_out"]:
        invalid_reasons.append("worker-timeout")
    if not worker["final_message"]:
        invalid_reasons.append("worker-final-message-missing")
    if not worker["cli_version"]:
        invalid_reasons.append("cli-version-missing")
    effective = worker["effective_model"]
    requested_model = MODEL_BY_ENGINE[engine]
    if effective is None:
        invalid_reasons.append("effective-model-missing")
    if worker["effective_model_source"] is None:
        invalid_reasons.append("effective-model-source-missing")
    elif engine == "terra" and effective != requested_model:
        invalid_reasons.append("effective-model-mismatch")
    elif engine == "sonnet" and "sonnet" not in effective.casefold():
        invalid_reasons.append("effective-model-mismatch")
    if restriction["applied"]:
        if not restriction["zero_bash_tool_use"]:
            invalid_reasons.append("restriction-bash-tool-use")
        if not restriction["modelUsage_present"]:
            invalid_reasons.append("restriction-modelUsage-missing")
        if not restriction["jsonl_retained"]:
            invalid_reasons.append("restriction-jsonl-missing")
    return invalid_reasons


def changed_paths(workspace: Path) -> list[str]:
    output = git_output(workspace, "diff", "--name-only", PRE_SHA, "--")
    return [line for line in output.splitlines() if line]


def phase_boundary(
    *,
    prompt_variant: str,
    final_message: str,
    workspace: Path,
    prepared: PreparedWorkspace,
) -> dict[str, Any]:
    errors: list[str] = []
    touched = changed_paths(workspace)
    outside = sorted(set(touched) - set(AUTHORIZED_SURFACE))
    if outside:
        errors.append("out-of-surface-delta")
    post_untracked = untracked_snapshot(workspace)
    changed_untracked = sorted(
        path
        for path in set(prepared.pre_untracked) | set(post_untracked)
        if prepared.pre_untracked.get(path) != post_untracked.get(path)
    )
    if changed_untracked:
        errors.append("untracked-overlay-mutated")
    head = git_output(workspace, "rev-parse", "HEAD").strip()
    if head != PRE_SHA:
        errors.append("worker-created-commit")
    if sha256_file(workspace / ".devlyn/goal.raw.txt") != GOAL_SHA:
        errors.append("goal-input-mutated")
    if sha256_file(workspace / ".devlyn/surface-close.input.patch") != PATCH_SHA:
        errors.append("patch-input-mutated")
    verdict_rows = None
    if prompt_variant == "FL1":
        verdict_rows = parse_verdict_rows(final_message, workspace)
        if not verdict_rows["valid"]:
            errors.append("adjudication-output-invalid")
        elif verdict_rows["terminal"] != "PASS":
            errors.append("worker-terminal-blocked")
    elif not terminal_passed(final_message):
        errors.append("worker-terminal-not-pass")
    return {
        "passed": not errors,
        "errors": errors,
        "touched_files": touched,
        "outside_surface": outside,
        "changed_untracked_files": changed_untracked,
        "verdict_rows": verdict_rows,
    }


def missing_receipt_fields(receipt: dict[str, Any]) -> list[str]:
    return sorted(RECEIPT_FIELDS - set(receipt))


def missing_control_receipt_fields(receipt: dict[str, Any]) -> list[str]:
    return sorted(CONTROL_RECEIPT_FIELDS - set(receipt))


def execute_replica(
    *,
    cell: str,
    prompt_variant: str,
    engine: str,
    replica: int,
    results_dir: Path,
    tmp_root: Path,
    prompts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    artifact_dir = results_dir / cell / f"replica-{replica:02d}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    run_root = tmp_root / cell / f"replica-{replica:02d}"
    workspace = run_root / "workspace"
    home = run_root / "home"
    home.mkdir(parents=True)
    atomic_json(
        artifact_dir / "attempt.json",
        {"started_at": utc_now(), "cell": cell, "replica": replica, "runner_pid": os.getpid()},
    )
    prepared = prepare_workspace(workspace)
    prompt = prompts[prompt_variant]["path"]
    pre_tree = {
        "head": git_output(workspace, "rev-parse", "HEAD").strip(),
        "tracked_dirty": bool(
            git_output(workspace, "status", "--porcelain", "--untracked-files=no")
        ),
        "status_sha256": sha256_bytes(prepared.pre_status.encode()),
        "overlay_input_source": prepared.overlay_input_source,
    }
    tools_csv = RESTRICTED_TOOLS_CSV if cell == RESTRICTED_CELL and engine == "sonnet" else None
    worker = (
        run_codex(workspace, prompt, artifact_dir, home)
        if engine == "terra"
        else run_sonnet(workspace, prompt, artifact_dir, home, tools_csv)
    )
    execution_audit, audit_errors = archive_and_audit_transcript(
        home, engine, artifact_dir
    )
    restriction = restriction_receipts(tools_csv, worker, execution_audit)
    delta = run_command(
        ["git", "diff", "--binary", "--no-ext-diff", PRE_SHA, "--"],
        cwd=workspace,
        text=False,
    )
    require_success(delta, "post-run git diff")
    write_bytes(artifact_dir / "delta.diff", delta.stdout)
    final = worker["final_message"]
    final_text = final.decode("utf-8", errors="replace")
    boundary = phase_boundary(
        prompt_variant=prompt_variant,
        final_message=final_text,
        workspace=workspace,
        prepared=prepared,
    )
    invalid_reasons = worker_invalid_reasons(
        worker, engine, execution_audit, audit_errors, restriction
    )
    readout = static_readout(workspace)
    readout["credited_uvr_fired"] = bool(
        readout["uvr_fired"] and boundary["passed"] and not invalid_reasons
    )
    readout["credited_path_test_fired"] = bool(
        readout["path_test_fired"] and boundary["passed"] and not invalid_reasons
    )
    requested_model = MODEL_BY_ENGINE[engine]
    effective = worker["effective_model"]
    receipt = {
        "schema_version": "r6-replay.v1",
        "cell": cell,
        "replica": replica,
        "prompt_variant": prompt_variant,
        "engine": engine,
        "requested_model": requested_model,
        "effective_model": effective,
        "effective_model_source": worker["effective_model_source"],
        "cli_version": worker["cli_version"],
        "prompt_sha256": sha256_file(prompt),
        "pre_tree": pre_tree,
        "post_tree": {
            "head": git_output(workspace, "rev-parse", "HEAD").strip(),
            "tracked_dirty": bool(
                git_output(workspace, "status", "--porcelain", "--untracked-files=no")
            ),
        },
        "delta_sha256": sha256_bytes(delta.stdout),
        "output_sha256": sha256_bytes(final),
        "elapsed_seconds": worker["elapsed_seconds"],
        "fresh_home": str(home),
        "exit_code": worker["exit_code"],
        "timed_out": worker["timed_out"],
        "readout": readout,
        "phase_boundary": boundary,
        "execution_audit": execution_audit,
        "restriction_receipts": restriction,
        "valid": not invalid_reasons,
        "invalid_reasons": invalid_reasons,
        "completed_at": utc_now(),
    }
    missing = missing_receipt_fields(receipt)
    if missing:
        receipt["valid"] = False
        receipt["invalid_reasons"].append("missing-receipts:" + ",".join(missing))
    atomic_json(artifact_dir / "receipts.json", receipt)
    return receipt


def prompt_bytes(variant: str, contract: dict[str, Any]) -> bytes:
    path = contract.get("path", contract.get("source_path"))
    if not isinstance(path, Path) or not path.is_file():
        raise ProbeError(f"{variant} prompt missing: {path}")
    source = path.read_bytes()
    if variant != "FL1" or "path" in contract:
        value = source
    else:
        if sha256_bytes(source) != contract["template_sha256"]:
            raise ProbeError("FL1 archived template hash mismatch")
        body = CANONICAL_BODY.read_bytes()
        start_marker = b"# PHASE 2.5 \xe2\x80\x94 SURFACE_CLOSE (canonical body)\n"
        end_marker = b"\n---\n\n## Supplied inputs"
        if not body.startswith(start_marker) or not body.endswith(b"\n"):
            raise ProbeError("SURFACE_CLOSE canonical body boundary malformed")
        if source.count(start_marker) != 1 or source.count(end_marker) != 1:
            raise ProbeError("FL1 archived template canonical-body boundary malformed")
        start = source.index(start_marker)
        end = source.index(end_marker, start)
        value = source[:start] + body + source[end:]
    if sha256_bytes(value) != contract["sha256"]:
        raise ProbeError(f"{variant} prompt hash mismatch")
    return value


def validate_prompts(prompts: dict[str, dict[str, Any]] = PROMPTS) -> None:
    for variant, contract in prompts.items():
        prompt_bytes(variant, contract)


def durable_prompts(results_dir: Path) -> dict[str, dict[str, Any]]:
    validate_prompts()
    results_dir.mkdir(parents=True, exist_ok=True)
    durable: dict[str, dict[str, Any]] = {}
    for variant, contract in PROMPTS.items():
        target = results_dir / contract["filename"]
        value = prompt_bytes(variant, contract)
        if target.exists():
            if not target.is_file() or target.read_bytes() != value:
                raise ProbeError(f"{variant} durable prompt conflicts: {target}")
        else:
            write_bytes(target, value)
        durable[variant] = {**contract, "path": target}
    validate_prompts(durable)
    return durable


def attempt_directories(results_dir: Path, cell: str | None = None) -> list[Path]:
    roots = [results_dir / cell] if cell else [results_dir / name for name, _, _ in CELLS]
    return sorted(
        path
        for root in roots
        if root.is_dir()
        for path in root.glob("replica-*")
        if (path / "attempt.json").is_file()
    )


def load_receipts(results_dir: Path, cell: str) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in attempt_directories(results_dir, cell):
        receipt_path = path / "receipts.json"
        if not receipt_path.is_file():
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        audit_errors: list[str] = []
        if "execution_audit" not in receipt:
            transcript = path / "worker-transcript.jsonl"
            if transcript.is_file():
                receipt["execution_audit"], audit_errors = execution_audit_for_transcript(
                    transcript, receipt.get("engine")
                )
            else:
                receipt["execution_audit"] = {
                    "n_commands": 0,
                    "validation_execution": False,
                    "validation_hits": [],
                    "transcript_path": None,
                }
                audit_errors = ["worker-transcript-missing"]
        audit = receipt["execution_audit"]
        audit_invalid = (
            bool(audit_errors)
            or not isinstance(audit, dict)
            or bool(audit.get("validation_execution"))
        )
        receipt["valid"] = (
            bool(receipt.get("valid"))
            and not audit_invalid
            and not missing_receipt_fields(receipt)
        )
        receipts.append(receipt)
    return receipts


def can_start_worker(results_dir: Path) -> bool:
    return len(attempt_directories(results_dir)) < GLOBAL_CAP


def next_replica_number(results_dir: Path, cell: str) -> int:
    numbers = []
    for path in attempt_directories(results_dir, cell):
        match = re.fullmatch(r"replica-([0-9]+)", path.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def desired_valid_replicas(receipts: list[dict[str, Any]]) -> int:
    valid = [receipt for receipt in receipts if receipt.get("valid")]
    if len(valid) < 2:
        return 2
    any_fire = any(
        (receipt.get("readout") or {}).get("uvr_fired") for receipt in valid[:2]
    )
    return 3 if any_fire else 2


def summarize(results_dir: Path) -> dict[str, Any]:
    cells: dict[str, Any] = {}
    for cell, prompt_variant, engine in CELLS:
        attempts = attempt_directories(results_dir, cell)
        receipts = load_receipts(results_dir, cell)
        valid = [receipt for receipt in receipts if receipt.get("valid")]
        target = desired_valid_replicas(receipts)
        fire_count = sum(
            bool((receipt.get("readout") or {}).get("uvr_fired")) for receipt in valid
        )
        path_count = sum(
            bool((receipt.get("readout") or {}).get("path_test_fired"))
            for receipt in valid
        )
        cells[cell] = {
            "prompt_variant": prompt_variant,
            "engine": engine,
            "worker_runs": len(attempts),
            "completed_receipts": len(receipts),
            "valid_replicas": len(valid),
            "invalid_worker_runs": len(attempts) - len(valid),
            "adaptive_target_valid_replicas": target,
            "uvr_fire_count": fire_count,
            "path_test_fire_count": path_count,
            "frozen_threshold": {"required_uvr_fires": 2, "required_replicas": 3},
            "threshold_count_met": len(valid) >= 3 and fire_count >= 2,
        }
    return {
        "schema_version": "r6-replay-summary.v1",
        "registration": REGISTRATION,
        "global_worker_runs": len(attempt_directories(results_dir)),
        "global_cap": GLOBAL_CAP,
        "cells": cells,
        "updated_at": utc_now(),
    }


def adaptive_trace(summary: dict[str, Any]) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for cell, state in summary["cells"].items():
        valid = state["valid_replicas"]
        if valid < 2:
            decision = "collect-two-valid"
        elif state["adaptive_target_valid_replicas"] == 2:
            decision = "stop-zero-of-two"
        elif valid < 3:
            decision = "collect-exactly-one-adaptive-replica"
        else:
            decision = "stop-after-third-valid"
        trace.append({"cell": cell, "decision": decision, **state})
    return trace


def build_manifest(
    results_dir: Path, summary: dict[str, Any], prompts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return {
        "schema_version": "r6-replay-manifest.v1",
        "registration": REGISTRATION,
        "rules": {
            "cells": [name for name, _, _ in CELLS],
            "initial_valid_replicas_per_cell": 2,
            "zero_of_two_uvr_stop": True,
            "any_uvr_fire_additional_valid_replicas": 1,
            "max_valid_replicas_per_cell": 3,
            "global_worker_run_cap": GLOBAL_CAP,
            "invalid_does_not_count_toward_cell": True,
            "invalid_counts_toward_global_cap": True,
            "worker_timeout_seconds": TIMEOUT_SECONDS,
        },
        "frozen_inputs": {
            "pre_sha": PRE_SHA,
            "bundle": {"path": str(BUNDLE.relative_to(REPO)), "sha256": sha256_file(BUNDLE)},
            "overlay": {"path": str(OVERLAY.relative_to(REPO)), "sha256": sha256_file(OVERLAY)},
            "goal_sha256": GOAL_SHA,
            "surface_close_input_patch_sha256": PATCH_SHA,
            "fl1_amendment5_canonical_body": {
                "path": str(CANONICAL_BODY.relative_to(REPO)),
                "sha256": sha256_file(CANONICAL_BODY),
                "assembled_prompt_sha256": PROMPTS["FL1"]["sha256"],
            },
            "overlay_prompt_input_restoration": (
                "The committed post-hoc overlay stores the exact prompt inputs under its single "
                ".devlyn/runs/<run-id>/ archive. Preparation copies those hash-matched bytes back "
                "to the prompt-required .devlyn root paths; no content is regenerated."
            ),
        },
        "prompts": {
            variant: {
                "path": str(contract["path"]),
                "sha256": sha256_file(contract["path"]),
                "bytes": contract["path"].stat().st_size,
            }
            for variant, contract in prompts.items()
        },
        "seats": {
            "terra": {
                "requested_model": "gpt-5.6-terra",
                "reasoning_effort": "xhigh",
                "route": "config/skills/_shared/codex-monitored.sh",
                "sandbox": "workspace-write",
                "network_grant": False,
                "fresh_home_and_codex_home_per_replica": True,
            },
            "sonnet": {
                "requested_model": "sonnet",
                "route": "benchmark/ceiling/scripts/claude-isolation.py launch --mode arm",
                "restricted_cell": RESTRICTED_CELL,
                "restricted_tools_csv": RESTRICTED_TOOLS_CSV,
                "timeout_seconds": TIMEOUT_SECONDS,
                "fresh_home_per_replica": True,
            },
        },
        "adaptive_rule_trace": adaptive_trace(summary),
        "global_worker_runs": summary["global_worker_runs"],
        "updated_at": utc_now(),
    }


def update_outputs(
    results_dir: Path, prompts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    summary = summarize(results_dir)
    atomic_json(results_dir / "summary.json", summary)
    atomic_json(results_dir / "manifest.json", build_manifest(results_dir, summary, prompts))
    return summary


def selected_cells(cell: str | None) -> tuple[tuple[str, str, str], ...]:
    if cell is None:
        return CELLS
    selected = tuple(candidate for candidate in CELLS if candidate[0] == cell)
    if not selected:
        raise ProbeError(f"unknown replay cell: {cell}")
    return selected


def run_probe(results_dir: Path, tmp_root: Path, cell: str | None = None) -> int:
    cells = selected_cells(cell)
    prompts = durable_prompts(results_dir)
    tmp_root.mkdir(parents=True, exist_ok=True)
    lock_path = results_dir / ".runner.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProbeError(f"another r6 replay runner holds {lock_path}") from exc
        update_outputs(results_dir, prompts)
        for cell, prompt_variant, engine in cells:
            while True:
                receipts = load_receipts(results_dir, cell)
                valid = [receipt for receipt in receipts if receipt.get("valid")]
                target = desired_valid_replicas(receipts)
                if len(valid) >= target:
                    break
                if not can_start_worker(results_dir):
                    update_outputs(results_dir, prompts)
                    return 2
                replica = next_replica_number(results_dir, cell)
                execute_replica(
                    cell=cell,
                    prompt_variant=prompt_variant,
                    engine=engine,
                    replica=replica,
                    results_dir=results_dir,
                    tmp_root=tmp_root,
                    prompts=prompts,
                )
                update_outputs(results_dir, prompts)
        update_outputs(results_dir, prompts)
    return 0


GOAL_PROMPT_HEADER = re.compile(
    rb"^### Goal \(raw, at `\.devlyn/goal\.raw\.txt`, sha256 ([0-9a-f]{64})\)\n",
    re.MULTILINE,
)
PATCH_PROMPT_HEADER = re.compile(
    rb"^### Patch \(`\.devlyn/surface-close\.input\.patch`, sha256 ([0-9a-f]{64})\)\n",
    re.MULTILINE,
)


def control_prompt_regions(prompt: bytes) -> dict[str, tuple[int, int]]:
    goal_matches = list(GOAL_PROMPT_HEADER.finditer(prompt))
    patch_matches = list(PATCH_PROMPT_HEADER.finditer(prompt))
    if len(goal_matches) != 1 or len(patch_matches) != 1:
        raise ProbeError("FL1 prompt Goal/Patch headers are not unique")
    goal_header = goal_matches[0]
    patch_header = patch_matches[0]
    if goal_header.end() >= patch_header.start() or prompt[goal_header.end():goal_header.end() + 1] != b"\n":
        raise ProbeError("FL1 Goal block delimiter malformed")
    if prompt[patch_header.start() - 2:patch_header.start()] != b"\n\n":
        raise ProbeError("FL1 Goal/Patch separator malformed")
    patch_prefix = b"\n```diff\n"
    if prompt[patch_header.end():patch_header.end() + len(patch_prefix)] != patch_prefix:
        raise ProbeError("FL1 Patch fence opener malformed")
    patch_body_start = patch_header.end() + len(patch_prefix)
    patch_close = prompt.find(b"```\n\n### authorized_surface", patch_body_start)
    if patch_close < 0:
        raise ProbeError("FL1 Patch fence closer malformed")
    return {
        "goal_sha": goal_header.span(1),
        "goal_body": (goal_header.end() + 1, patch_header.start() - 2),
        "patch_sha": patch_header.span(1),
        "patch_body": (patch_body_start, patch_close),
    }


def immutable_control_prompt_segments(prompt: bytes) -> tuple[bytes, ...]:
    regions = sorted(control_prompt_regions(prompt).values())
    segments: list[bytes] = []
    cursor = 0
    for start, end in regions:
        segments.append(prompt[cursor:start])
        cursor = end
    segments.append(prompt[cursor:])
    return tuple(segments)


def assemble_control_prompt(template: bytes, goal: bytes, input_patch: bytes) -> bytes:
    if sha256_bytes(template) != PROMPTS["FL1"]["sha256"]:
        raise ProbeError("FL1 control template hash mismatch")
    goal.decode("utf-8", errors="strict")
    input_patch.decode("utf-8", errors="strict")
    regions = control_prompt_regions(template)
    if template[slice(*regions["goal_sha"])].decode() != GOAL_SHA:
        raise ProbeError("FL1 control template Goal header hash mismatch")
    if template[slice(*regions["patch_sha"])].decode() != PATCH_SHA:
        raise ProbeError("FL1 control template Patch header hash mismatch")
    replacements = {
        "goal_sha": sha256_bytes(goal).encode(),
        "goal_body": goal,
        "patch_sha": sha256_bytes(input_patch).encode(),
        "patch_body": input_patch,
    }
    assembled = template
    for name, (start, end) in sorted(
        regions.items(), key=lambda item: item[1][0], reverse=True
    ):
        assembled = assembled[:start] + replacements[name] + assembled[end:]
    assembled_regions = control_prompt_regions(assembled)
    if assembled[slice(*assembled_regions["goal_body"])] != goal:
        raise ProbeError("assembled control Goal bytes mismatch")
    if assembled[slice(*assembled_regions["patch_body"])] != input_patch:
        raise ProbeError("assembled control Patch bytes mismatch")
    if immutable_control_prompt_segments(assembled) != immutable_control_prompt_segments(template):
        raise ProbeError("assembled control prompt changed immutable bytes")
    return assembled


def load_control_contract(control_dir: Path) -> ControlContract:
    required = {
        "goal.raw.txt",
        "input.patch",
        "expected-disposition.json",
    }
    missing = sorted(name for name in required if not (control_dir / name).is_file())
    if missing:
        raise ProbeError(f"{control_dir.name} missing control inputs: {','.join(missing)}")
    goal = (control_dir / "goal.raw.txt").read_bytes()
    input_patch = (control_dir / "input.patch").read_bytes()
    goal.decode("utf-8", errors="strict")
    input_patch.decode("utf-8", errors="strict")
    if not goal or not input_patch:
        raise ProbeError(f"{control_dir.name} has an empty Goal or Patch")
    try:
        expected = json.loads(
            (control_dir / "expected-disposition.json").read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ProbeError(f"{control_dir.name} expected-disposition malformed") from exc
    if not isinstance(expected, dict) or set(expected) != {*OBLIGATIONS, "expected_delta"}:
        raise ProbeError(f"{control_dir.name} expected-disposition shape mismatch")
    dispositions = {obligation: expected[obligation] for obligation in OBLIGATIONS}
    if any(value not in {"FIRED", "N/A"} for value in dispositions.values()):
        raise ProbeError(f"{control_dir.name} expected obligation disposition invalid")
    if expected["expected_delta"] not in {"empty", "test-only"}:
        raise ProbeError(f"{control_dir.name} expected_delta invalid")
    return ControlContract(
        control_dir.name,
        goal,
        input_patch,
        dispositions,
        expected["expected_delta"],
    )


def prepare_control_workspace(
    target: Path, control_dir: Path, contract: ControlContract
) -> PreparedControlWorkspace:
    if target.exists():
        raise ProbeError(f"fresh workspace already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    clone = run_command(["git", "clone", "--quiet", str(BUNDLE), str(target)])
    require_success(clone, "control bundle clone")
    checkout = run_command(
        ["git", "checkout", "--quiet", "--detach", CONTROL_BASE_SHA], cwd=target
    )
    require_success(checkout, "control base checkout")
    apply_result = run_command(
        ["git", "apply", "--whitespace=nowarn", str(control_dir / "input.patch")],
        cwd=target,
    )
    require_success(apply_result, "control input patch apply")
    input_paths = changed_paths_from(target, CONTROL_BASE_SHA)
    outside = sorted(set(input_paths) - set(AUTHORIZED_SURFACE))
    if outside:
        raise ProbeError(f"control input patch exceeds authorized surface: {outside}")
    overlay = run_command(["tar", "-xzf", str(OVERLAY), "-C", str(target)])
    require_success(overlay, "control workspace overlay extraction")
    goal_path = target / ".devlyn/goal.raw.txt"
    patch_path = target / ".devlyn/surface-close.input.patch"
    write_bytes(goal_path, contract.goal)
    write_bytes(patch_path, contract.input_patch)
    head = git_output(target, "rev-parse", "HEAD").strip()
    if head != CONTROL_BASE_SHA:
        raise ProbeError(f"control base HEAD mismatch: {head}")
    status = git_output(target, "status", "--short", "--untracked-files=normal")
    prepared = PreparedWorkspace(
        target,
        f"control:{control_dir.name}",
        status,
        untracked_snapshot(target),
    )
    return PreparedControlWorkspace(
        prepared,
        tracked_snapshot(target),
        sha256_file(goal_path),
        sha256_file(patch_path),
        usage_block_sha256(target / "bin/cli.js"),
    )


def changed_paths_from(workspace: Path, base_sha: str) -> list[str]:
    output = git_output(workspace, "diff", "--name-only", base_sha, "--")
    return [line for line in output.splitlines() if line]


def control_phase_boundary(
    *,
    final_message: str,
    workspace: Path,
    prepared: PreparedControlWorkspace,
) -> dict[str, Any]:
    errors: list[str] = []
    post_tracked = tracked_snapshot(workspace)
    touched = changed_snapshot_paths(prepared.pre_tracked, post_tracked)
    outside = sorted(set(touched) - set(AUTHORIZED_SURFACE))
    if outside:
        errors.append("out-of-surface-delta")
    pre_untracked = prepared.prepared.pre_untracked
    post_untracked = untracked_snapshot(workspace)
    changed_untracked = changed_snapshot_paths(pre_untracked, post_untracked)
    if changed_untracked:
        errors.append("untracked-overlay-mutated")
    head = git_output(workspace, "rev-parse", "HEAD").strip()
    if head != CONTROL_BASE_SHA:
        errors.append("worker-created-commit")
    goal_path = workspace / ".devlyn/goal.raw.txt"
    patch_path = workspace / ".devlyn/surface-close.input.patch"
    if not goal_path.is_file() or sha256_file(goal_path) != prepared.goal_sha256:
        errors.append("goal-input-mutated")
    if not patch_path.is_file() or sha256_file(patch_path) != prepared.patch_sha256:
        errors.append("patch-input-mutated")
    if any(not (workspace / relative).is_file() for relative in AUTHORIZED_SURFACE):
        errors.append("authorized-file-missing")
    usage_hunk_changed = usage_block_sha256(workspace / "bin/cli.js") != prepared.usage_sha256
    verdict_rows = parse_verdict_rows(final_message, workspace)
    if not verdict_rows["valid"]:
        errors.append("adjudication-output-invalid")
    elif verdict_rows["terminal"] != "PASS":
        errors.append("worker-terminal-blocked")
    return {
        "passed": not errors,
        "errors": errors,
        "touched_files": touched,
        "outside_surface": outside,
        "changed_untracked_files": changed_untracked,
        "usage_hunk_changed": usage_hunk_changed,
        "verdict_rows": verdict_rows,
    }


def score_control(
    expected_disposition: dict[str, str],
    expected_delta: str,
    verdict_rows: dict[str, Any],
    worker_changed_files: list[str],
    usage_hunk_changed: bool = False,
) -> dict[str, Any]:
    actual = {
        obligation: ((verdict_rows.get("rows") or {}).get(obligation) or {}).get(
            "disposition"
        )
        for obligation in OBLIGATIONS
    }
    disposition_matches = {
        obligation: actual[obligation] == expected_disposition[obligation]
        for obligation in OBLIGATIONS
    }
    if expected_delta == "empty":
        delta_matches = not worker_changed_files
    elif expected_delta == "test-only":
        delta_matches = worker_changed_files == ["tests/cli.test.js"]
    else:
        raise ProbeError(f"unsupported expected_delta: {expected_delta}")
    false_fired_obligations = [
        obligation
        for obligation in OBLIGATIONS
        if expected_disposition[obligation] == "N/A" and actual[obligation] == "FIRED"
    ]
    return {
        "actual_disposition": actual,
        "disposition_matches": disposition_matches,
        "correct_disposition": all(disposition_matches.values()),
        "actual_delta_files": worker_changed_files,
        "delta_matches": delta_matches,
        "false_fired_obligations": false_fired_obligations,
        "forbidden_edit": usage_hunk_changed,
        "false_fired": bool(false_fired_obligations or usage_hunk_changed),
    }


def execute_control_replica(
    *,
    contract: ControlContract,
    control_dir: Path,
    cell: str,
    engine: str,
    replica: int,
    results_dir: Path,
    tmp_root: Path,
    prompts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    artifact_dir = results_dir / "controls" / contract.name / f"replica-{replica:02d}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    run_root = tmp_root / "controls" / contract.name / f"replica-{replica:02d}"
    workspace = run_root / "workspace"
    home = run_root / "home"
    home.mkdir(parents=True)
    atomic_json(
        artifact_dir / "attempt.json",
        {
            "started_at": utc_now(),
            "cell": cell,
            "control": contract.name,
            "replica": replica,
            "runner_pid": os.getpid(),
        },
    )
    prepared = prepare_control_workspace(workspace, control_dir, contract)
    prompt = artifact_dir / "assembled-prompt.txt"
    assembled = assemble_control_prompt(
        prompts["FL1"]["path"].read_bytes(), contract.goal, contract.input_patch
    )
    write_bytes(prompt, assembled)
    pre_tree = {
        "head": git_output(workspace, "rev-parse", "HEAD").strip(),
        "tracked_dirty": bool(
            git_output(workspace, "status", "--porcelain", "--untracked-files=no")
        ),
        "status_sha256": sha256_bytes(prepared.prepared.pre_status.encode()),
        "overlay_input_source": prepared.prepared.overlay_input_source,
    }
    tools_csv = RESTRICTED_TOOLS_CSV
    worker = (
        run_codex(workspace, prompt, artifact_dir, home)
        if engine == "terra"
        else run_sonnet(workspace, prompt, artifact_dir, home, tools_csv)
    )
    execution_audit, audit_errors = archive_and_audit_transcript(
        home, engine, artifact_dir
    )
    restriction = restriction_receipts(tools_csv, worker, execution_audit)
    final = worker["final_message"]
    boundary = control_phase_boundary(
        final_message=final.decode("utf-8", errors="replace"),
        workspace=workspace,
        prepared=prepared,
    )
    scoring = score_control(
        contract.expected_disposition,
        contract.expected_delta,
        boundary["verdict_rows"],
        boundary["touched_files"],
        boundary["usage_hunk_changed"],
    )
    post_tracked = tracked_snapshot(workspace)
    worker_delta = [
        {
            "path": path,
            "before_snapshot": prepared.pre_tracked.get(path),
            "after_snapshot": post_tracked.get(path),
        }
        for path in boundary["touched_files"]
    ]
    atomic_json(artifact_dir / "worker-delta.json", worker_delta)
    delta_bytes = json.dumps(
        worker_delta, sort_keys=True, separators=(",", ":")
    ).encode()
    invalid_reasons = worker_invalid_reasons(
        worker, engine, execution_audit, audit_errors, restriction
    )
    invalid_reasons.extend(f"phase-boundary:{error}" for error in boundary["errors"])
    readout = (
        static_readout(workspace)
        if "authorized-file-missing" not in boundary["errors"]
        else {"error": "authorized-file-missing"}
    )
    receipt = {
        "schema_version": "r6-replay-control.v1",
        "cell": cell,
        "control": contract.name,
        "replica": replica,
        "prompt_variant": "FL1-control",
        "engine": engine,
        "requested_model": MODEL_BY_ENGINE[engine],
        "effective_model": worker["effective_model"],
        "effective_model_source": worker["effective_model_source"],
        "cli_version": worker["cli_version"],
        "prompt_sha256": sha256_bytes(assembled),
        "control_inputs": {
            "goal_sha256": prepared.goal_sha256,
            "input_patch_sha256": prepared.patch_sha256,
        },
        "expected_disposition": contract.expected_disposition,
        "expected_delta": contract.expected_delta,
        "pre_tree": pre_tree,
        "post_tree": {
            "head": git_output(workspace, "rev-parse", "HEAD").strip(),
            "tracked_dirty": bool(
                git_output(workspace, "status", "--porcelain", "--untracked-files=no")
            ),
        },
        "delta_sha256": sha256_bytes(delta_bytes),
        "output_sha256": sha256_bytes(final),
        "elapsed_seconds": worker["elapsed_seconds"],
        "fresh_home": str(home),
        "exit_code": worker["exit_code"],
        "timed_out": worker["timed_out"],
        "readout": readout,
        "phase_boundary": boundary,
        "execution_audit": execution_audit,
        "restriction_receipts": restriction,
        "control_scoring": scoring,
        "valid": not invalid_reasons,
        "invalid_reasons": invalid_reasons,
        "completed_at": utc_now(),
    }
    missing = missing_control_receipt_fields(receipt)
    if missing:
        receipt["valid"] = False
        receipt["invalid_reasons"].append("missing-receipts:" + ",".join(missing))
    atomic_json(artifact_dir / "receipts.json", receipt)
    return receipt


def control_attempt_directories(results_dir: Path, control: str) -> list[Path]:
    root = results_dir / "controls" / control
    return sorted(
        path
        for path in root.glob("replica-*")
        if path.is_dir() and (path / "attempt.json").is_file()
    )


def load_control_receipts(results_dir: Path, control: str) -> list[dict[str, Any]]:
    receipts: list[dict[str, Any]] = []
    for path in control_attempt_directories(results_dir, control):
        receipt_path = path / "receipts.json"
        if not receipt_path.is_file():
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        receipt["valid"] = bool(receipt.get("valid")) and not missing_control_receipt_fields(
            receipt
        )
        receipts.append(receipt)
    return receipts


def control_worker_needed(worker_runs: int, credited_replicas: int, requested: int) -> bool:
    return credited_replicas < requested and worker_runs < CONTROL_WORKER_CAP


def control_summary(results_dir: Path, control: str, replicas: int) -> dict[str, Any]:
    attempts = control_attempt_directories(results_dir, control)
    receipts = load_control_receipts(results_dir, control)
    valid = [receipt for receipt in receipts if receipt.get("valid")]
    correct = [
        receipt
        for receipt in valid
        if (receipt.get("control_scoring") or {}).get("correct_disposition")
        and (receipt.get("control_scoring") or {}).get("delta_matches")
        and not (receipt.get("control_scoring") or {}).get("false_fired")
    ]
    return {
        "schema_version": "r6-replay-control-summary.v1",
        "requested_replicas": replicas,
        "worker_runs": len(attempts),
        "completed_receipts": len(receipts),
        "credited_replicas": len(valid),
        "invalid_worker_runs": len(attempts) - len(valid),
        "correct_disposition_replicas": sum(
            bool((receipt.get("control_scoring") or {}).get("correct_disposition"))
            for receipt in valid
        ),
        "correct_delta_replicas": sum(
            bool((receipt.get("control_scoring") or {}).get("delta_matches"))
            for receipt in valid
        ),
        "false_fired_replicas": sum(
            bool((receipt.get("control_scoring") or {}).get("false_fired"))
            for receipt in valid
        ),
        "fully_correct_replicas": len(correct),
    }


def update_control_summary(results_dir: Path, control: str, replicas: int) -> dict[str, Any]:
    summary = control_summary(results_dir, control, replicas)
    atomic_json(results_dir / "controls" / control / "summary.json", summary)
    return summary


def control_bar_met(summary: dict[str, Any]) -> bool:
    requested = summary["requested_replicas"]
    return (
        summary["credited_replicas"] == requested
        and summary["fully_correct_replicas"] == requested
        and summary["false_fired_replicas"] == 0
    )


def run_controls(controls_dir: Path, cell: str, replicas: int) -> int:
    if cell != "FL1-sonnet" or replicas != 2:
        raise ProbeError("frozen control mode requires --cell FL1-sonnet --replicas 2")
    contracts = {
        name: load_control_contract(controls_dir / name) for name in CONTROL_NAMES
    }
    prompts = durable_prompts(RESULTS_DIR)
    controls_root = RESULTS_DIR / "controls"
    controls_root.mkdir(parents=True, exist_ok=True)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    lock_path = controls_root / ".runner.lock"
    summaries: list[dict[str, Any]] = []
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProbeError(f"another r6 control runner holds {lock_path}") from exc
        for name in CONTROL_NAMES:
            update_control_summary(RESULTS_DIR, name, replicas)
            while True:
                attempts = control_attempt_directories(RESULTS_DIR, name)
                receipts = load_control_receipts(RESULTS_DIR, name)
                credited = sum(bool(receipt.get("valid")) for receipt in receipts)
                if not control_worker_needed(len(attempts), credited, replicas):
                    break
                replica = max(
                    (
                        int(path.name.removeprefix("replica-"))
                        for path in attempts
                        if path.name.removeprefix("replica-").isdigit()
                    ),
                    default=0,
                ) + 1
                execute_control_replica(
                    contract=contracts[name],
                    control_dir=controls_dir / name,
                    cell=cell,
                    engine="sonnet",
                    replica=replica,
                    results_dir=RESULTS_DIR,
                    tmp_root=TMP_ROOT,
                    prompts=prompts,
                )
                update_control_summary(RESULTS_DIR, name, replicas)
            summaries.append(update_control_summary(RESULTS_DIR, name, replicas))
    return 0 if all(control_bar_met(summary) for summary in summaries) else 2


def expect(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS {label}")


def self_test() -> int:
    validate_prompts()
    expect(True, "F1/FL1 full SHA-256 validation")
    unknown_cell_failed_closed = False
    try:
        selected_cells("unknown")
    except ProbeError:
        unknown_cell_failed_closed = True
    expect(unknown_cell_failed_closed, "unknown --cell fails closed")
    restricted_command = imported_claude_isolation().command_for(
        "arm", Path("/direct/claude"), "prompt", None, RESTRICTED_TOOLS_CSV
    )
    expect(
        restricted_command[-2:] == ["--tools", RESTRICTED_TOOLS_CSV],
        "Claude arm route appends the Amendment-5 tools restriction",
    )
    with tempfile.TemporaryDirectory(prefix="r6-replay-selftest-") as temporary:
        root = Path(temporary)
        durable = durable_prompts(root / "durable-prompts")
        expect(
            all(contract["path"].parent == root / "durable-prompts" for contract in durable.values()),
            "prompt bytes copied durably into the results directory",
        )
        durable_fl1 = durable["FL1"]["path"].read_bytes()
        expect(
            sha256_bytes(durable_fl1) == PROMPTS["FL1"]["sha256"]
            and durable_fl1.count(CANONICAL_BODY.read_bytes()) == 1,
            "FL1 recorded revision assembles the NEW canonical body bytes",
        )
        prepared = prepare_workspace(root / "frozen-workspace")
        expect(
            prepared.overlay_input_source.startswith(".devlyn/runs/"),
            "bundle clone + overlay + archived-input restoration + frozen asserts",
        )

        synthetic = root / "synthetic"
        (synthetic / "bin").mkdir(parents=True)
        (synthetic / "tests").mkdir()
        (synthetic / "bin/cli.js").write_text(
            "const USAGE = `Commands:\n  version  Print version\n`;\n", encoding="utf-8"
        )
        (synthetic / "tests/cli.test.js").write_text("test('version', () => {});\n")
        open_readout = static_readout(synthetic)
        expect(
            not open_readout["uvr_fired"] and not open_readout["path_test_fired"],
            "check-7/check-8 imported predicates detect carriers open",
        )
        (synthetic / "bin/cli.js").write_text(
            "const USAGE = `Commands:\n  version [--format json]  Print version\n`;\n",
            encoding="utf-8",
        )
        (synthetic / "tests/cli.test.js").write_text(
            "test('reject yaml', () => { const status = 1; assert.equal(status, 1); "
            "run(['version', '--format', 'yaml']); });\n",
            encoding="utf-8",
        )
        closed_readout = static_readout(synthetic)
        expect(
            closed_readout["uvr_fired"] and closed_readout["path_test_fired"],
            "check-7/check-8 imported predicates detect carriers closed",
        )

        valid_fired = parse_verdict_rows(
            "UVR-STALE: FIRED bin/cli.js:2\n"
            "PATH-TEST: N/A tests/cli.test.js:1 — failure path already covered\nPASS",
            synthetic,
        )
        expect(valid_fired["valid"], "verdict parser accepts FIRED with valid citation")
        valid_fired_evidence = parse_verdict_rows(
            "UVR-STALE: FIRED bin/cli.js:2 — stale interface updated\n"
            "PATH-TEST: N/A tests/cli.test.js:1 — failure path already covered\nPASS",
            synthetic,
        )
        expect(
            valid_fired_evidence["valid"],
            "verdict parser accepts optional FIRED evidence from the NEW body",
        )
        valid_na = parse_verdict_rows(
            "UVR-STALE: N/A bin/cli.js:1 — no stale relationship\n"
            "PATH-TEST: N/A tests/cli.test.js:1 — path already covered\nPASS",
            synthetic,
        )
        expect(valid_na["valid"], "verdict parser accepts two evidenced N/A rows")
        missing = parse_verdict_rows(
            "UVR-STALE: FIRED bin/cli.js:1\nPASS", synthetic
        )
        expect(not missing["valid"], "verdict parser rejects a missing obligation line")
        malformed_extra = parse_verdict_rows(
            "UVR-STALE: FIRED bin/cli.js:1\n"
            "UVR-STALE: maybe bin/cli.js:1\n"
            "PATH-TEST: N/A tests/cli.test.js:1 — path already covered\nPASS",
            synthetic,
        )
        expect(
            not malformed_extra["valid"],
            "verdict parser rejects an extra malformed obligation line",
        )
        out_of_surface = parse_verdict_rows(
            "UVR-STALE: FIRED README.md:1\n"
            "PATH-TEST: N/A tests/cli.test.js:1 — path already covered\nPASS",
            synthetic,
        )
        expect(not out_of_surface["valid"], "verdict parser rejects out-of-surface citation")
        nonexistent = parse_verdict_rows(
            "UVR-STALE: FIRED bin/cli.js:99\n"
            "PATH-TEST: N/A tests/cli.test.js:1 — path already covered\nPASS",
            synthetic,
        )
        expect(not nonexistent["valid"], "verdict parser rejects nonexistent line")
        expect(
            not terminal_passed("BLOCKED:surface-close-impossible\nPASS"),
            "F1 terminal parser rejects mixed BLOCKED/PASS output",
        )

        complete_receipt = {field: None for field in RECEIPT_FIELDS}
        expect(not missing_receipt_fields(complete_receipt), "complete receipt shape accepted")
        complete_receipt.pop("effective_model")
        expect(
            missing_receipt_fields(complete_receipt) == ["effective_model"],
            "missing receipt makes run INVALID",
        )

        invalid_results = root / "invalid-results"
        invalid_dir = invalid_results / "F1-terra/replica-01"
        invalid_dir.mkdir(parents=True)
        (invalid_dir / "attempt.json").write_text("{}\n", encoding="utf-8")
        atomic_json(invalid_dir / "receipts.json", {**complete_receipt, "valid": True})
        invalid_summary = summarize(invalid_results)["cells"]["F1-terra"]
        expect(
            invalid_summary["valid_replicas"] == 0
            and invalid_summary["invalid_worker_runs"] == 1,
            "INVALID receipt counts globally but not toward the cell",
        )

        no_fire = [
            {"valid": True, "readout": {"uvr_fired": False}},
            {"valid": True, "readout": {"uvr_fired": False}},
        ]
        expect(desired_valid_replicas(no_fire) == 2, "zero-of-two stops the cell")
        no_fire[1]["readout"]["uvr_fired"] = True
        expect(
            desired_valid_replicas(no_fire) == 3,
            "any fire schedules exactly one additional valid replica",
        )

        cap_results = root / "cap-results"
        for index in range(GLOBAL_CAP):
            attempt = cap_results / CELLS[index % len(CELLS)][0] / f"replica-{index + 1:02d}"
            attempt.mkdir(parents=True)
            (attempt / "attempt.json").write_text("{}\n", encoding="utf-8")
        expect(not can_start_worker(cap_results), "12-worker global cap enforced")
        (next(iter(attempt_directories(cap_results))) / "attempt.json").unlink()
        expect(can_start_worker(cap_results), "worker allowed below global cap")

        sonnet_validation = root / "sonnet-validation.jsonl"
        sonnet_validation.write_text(
            json.dumps(
                {
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Bash",
                                "input": {"command": "sed -n '1,80p' bin/cli.js"},
                            },
                            {
                                "type": "tool_use",
                                "name": "Bash",
                                "input": {"command": "npm test"},
                            },
                        ]
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        sonnet_audit, sonnet_errors = execution_audit_for_transcript(
            sonnet_validation, "sonnet"
        )
        codex_validation = root / "codex-validation.jsonl"
        codex_validation.write_text(
            json.dumps(
                {
                    "payload": {
                        "type": "custom_tool_call",
                        "input": 'const r = await tools.exec_command({"cmd":"node --test tests/cli.test.js"});',
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        codex_audit, codex_errors = execution_audit_for_transcript(
            codex_validation, "terra"
        )
        expect(
            not sonnet_errors
            and sonnet_audit["n_commands"] == 2
            and sonnet_audit["bash_tool_use_count"] == 2
            and sonnet_audit["validation_hits"] == ["npm test"]
            and sonnet_audit["validation_execution"]
            and not codex_errors
            and codex_audit["n_commands"] == 1
            and codex_audit["validation_execution"],
            "execution audit detects sonnet/codex validation commands",
        )

        sonnet_read_only = root / "sonnet-read-only.jsonl"
        sonnet_read_only.write_text(
            json.dumps(
                {
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Bash",
                                "input": {"command": "git diff -- bin/cli.js"},
                            }
                        ]
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        codex_read_only = root / "codex-read-only.jsonl"
        codex_read_only.write_text(
            json.dumps(
                {
                    "payload": {
                        "type": "custom_tool_call",
                        "cmd": "shasum -a 256 .devlyn/goal.raw.txt",
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        sonnet_clean, _ = execution_audit_for_transcript(sonnet_read_only, "sonnet")
        codex_clean, _ = execution_audit_for_transcript(codex_read_only, "terra")
        expect(
            sonnet_clean["n_commands"] == 1
            and sonnet_clean["bash_tool_use_count"] == 1
            and not sonnet_clean["validation_execution"]
            and codex_clean["n_commands"] == 1
            and not codex_clean["validation_execution"],
            "execution audit allows sonnet/codex read-only commands",
        )
        clean_restriction = restriction_receipts(
            RESTRICTED_TOOLS_CSV,
            {"model_usage_present": True},
            {
                "n_commands": 0,
                "bash_tool_use_count": 0,
                "transcript_path": "worker-transcript.jsonl",
            },
        )
        dirty_restriction = restriction_receipts(
            RESTRICTED_TOOLS_CSV,
            {"model_usage_present": True},
            {
                "n_commands": 0,
                "bash_tool_use_count": 1,
                "transcript_path": "worker-transcript.jsonl",
            },
        )
        expect(
            clean_restriction["passed"]
            and clean_restriction["zero_bash_tool_use"]
            and clean_restriction["modelUsage_present"]
            and clean_restriction["jsonl_retained"]
            and not dirty_restriction["passed"],
            "restricted-route receipts require zero Bash tool_use plus modelUsage and JSONL",
        )

        control_goal = b"Control Goal bytes without a trailing newline"
        control_patch = (
            b"diff --git a/tests/cli.test.js b/tests/cli.test.js\n"
            b"--- a/tests/cli.test.js\n+++ b/tests/cli.test.js\n"
        )
        template = durable["FL1"]["path"].read_bytes()
        assembled = assemble_control_prompt(template, control_goal, control_patch)
        assembled_regions = control_prompt_regions(assembled)
        expect(
            assembled[slice(*assembled_regions["goal_body"])] == control_goal
            and assembled[slice(*assembled_regions["patch_body"])] == control_patch
            and assembled[slice(*assembled_regions["goal_sha"])].decode()
            == sha256_bytes(control_goal)
            and assembled[slice(*assembled_regions["patch_sha"])].decode()
            == sha256_bytes(control_patch)
            and immutable_control_prompt_segments(assembled)
            == immutable_control_prompt_segments(template)
            and bool(sha256_bytes(assembled)),
            "control prompt substitutes only Goal/Patch regions and records hashes",
        )

        def verdicts(uvr: str, path_test: str) -> dict[str, Any]:
            return {
                "rows": {
                    "UVR-STALE": {"disposition": uvr},
                    "PATH-TEST": {"disposition": path_test},
                }
            }

        expected_control = {"UVR-STALE": "N/A", "PATH-TEST": "FIRED"}
        correct = score_control(
            expected_control, "test-only", verdicts("N/A", "FIRED"), ["tests/cli.test.js"]
        )
        expect(
            correct["correct_disposition"]
            and correct["delta_matches"]
            and not correct["false_fired"],
            "control scoring accepts correct disposition",
        )
        wrong_obligation = score_control(
            {"UVR-STALE": "FIRED", "PATH-TEST": "FIRED"},
            "test-only",
            verdicts("N/A", "FIRED"),
            ["tests/cli.test.js"],
        )
        expect(
            not wrong_obligation["correct_disposition"]
            and not wrong_obligation["false_fired"],
            "control scoring rejects wrong obligation",
        )
        false_fired = score_control(
            expected_control,
            "test-only",
            verdicts("FIRED", "FIRED"),
            ["tests/cli.test.js"],
        )
        expect(
            false_fired["false_fired"]
            and false_fired["false_fired_obligations"] == ["UVR-STALE"],
            "control scoring detects false-fired obligation",
        )
        forbidden_edit = score_control(
            {"UVR-STALE": "FIRED", "PATH-TEST": "FIRED"},
            "test-only",
            verdicts("FIRED", "FIRED"),
            ["bin/cli.js", "tests/cli.test.js"],
            True,
        )
        expect(
            forbidden_edit["forbidden_edit"]
            and forbidden_edit["false_fired"]
            and not forbidden_edit["delta_matches"],
            "control scoring detects forbidden edit",
        )
        empty_delta = score_control(
            {"UVR-STALE": "N/A", "PATH-TEST": "N/A"},
            "empty",
            verdicts("N/A", "N/A"),
            [],
        )
        wrong_empty = score_control(
            {"UVR-STALE": "N/A", "PATH-TEST": "N/A"},
            "empty",
            verdicts("N/A", "N/A"),
            ["tests/cli.test.js"],
        )
        expect(
            empty_delta["delta_matches"]
            and not wrong_empty["delta_matches"]
            and correct["delta_matches"],
            "control scoring distinguishes empty and test-only deltas",
        )

        expect(
            control_worker_needed(0, 0, 2)
            and control_worker_needed(2, 0, 2)
            and not control_worker_needed(2, 2, 2)
            and not control_worker_needed(4, 0, 2),
            "control replacement scheduling stops at two credits or four workers",
        )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    run_parser.add_argument("--tmp-root", type=Path, default=TMP_ROOT)
    run_parser.add_argument("--cell")
    control_parser = subparsers.add_parser("run-control")
    control_parser.add_argument("--controls-dir", type=Path, required=True)
    control_parser.add_argument("--cell", required=True)
    control_parser.add_argument("--replicas", type=int, required=True)
    subparsers.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "self-test":
            return self_test()
        if args.command == "run-control":
            return run_controls(args.controls_dir.resolve(), args.cell, args.replicas)
        return run_probe(args.results_dir.resolve(), args.tmp_root.resolve(), args.cell)
    except (ProbeError, AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"R6_REPLAY_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
