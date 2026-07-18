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
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


sys.dont_write_bytecode = True


REPO = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = REPO / "benchmark/ceiling/results/r6-replay-20260718"
TMP_ROOT = Path("/tmp/codex-0072-v6-build/r6-replay-work")
PROMPTS = {
    "F1": {
        "path": Path("/tmp/codex-0072-r6/f1-prompt.txt"),
        "sha256": "00cddba55a0aaabff3e4dbea1264c412e806a293408bf25378babd8c7dbd23b1",
    },
    "FL1": {
        "path": Path("/tmp/codex-0072-r6/fl1-prompt.txt"),
        "sha256": "b422dd6e6783945f43059ffa2ad0cae76aac270289720416e5b0ea838bee5e83",
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
GOAL_SHA = "f3467374f6554ece0b14e48250222d11fc6675aae4cb0ded70fc3503a78c9674"
PATCH_SHA = "cfac5a9fafc59a1ddf019f1fb49412e5ddfd8ff393c28619b8de641997e56c9b"
AUTHORIZED_SURFACE = ("bin/cli.js", "tests/cli.test.js")
MODEL_BY_ENGINE = {"terra": "gpt-5.6-terra", "sonnet": "sonnet"}
CELLS = (
    ("F1-terra", "F1", "terra"),
    ("F1-sonnet", "F1", "sonnet"),
    ("FL1-terra", "FL1", "terra"),
    ("FL1-sonnet", "FL1", "sonnet"),
)
GLOBAL_CAP = 12
TIMEOUT_SECONDS = 600
REGISTRATION = "iter-0072 Registration v6 / DECISIONS 0072.14"
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
    "valid",
    "invalid_reasons",
}


class ProbeError(RuntimeError):
    """The frozen replay contract could not be established."""


@dataclass(frozen=True)
class PreparedWorkspace:
    path: Path
    overlay_input_source: str
    pre_status: str
    pre_untracked: dict[str, str]


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
    """Import and invoke the exact nested check-7/check-8 gate predicates."""
    gate = load_module(SCRIPT_DIR / "f7-carrier-gate.py", "r6_f7_carrier_gate")
    functions: dict[str, Callable[[str], tuple[bool, str]]] = {}
    for constant in gate.main.__code__.co_consts:
        if not isinstance(constant, types.CodeType) or constant.co_name not in {"check7", "check8"}:
            continue
        if constant.co_freevars:
            raise ProbeError(f"f7 carrier predicate {constant.co_name} unexpectedly gained a closure")
        functions[constant.co_name] = types.FunctionType(constant, vars(gate))
    if set(functions) != {"check7", "check8"}:
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
            snapshot[relative] = sha256_file(candidate)
        elif candidate.is_symlink():
            snapshot[relative] = "symlink:" + os.readlink(candidate)
    return snapshot


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
        if disposition == "FIRED" and judgment is not None:
            errors.append(f"{obligation}-FIRED-has-judgment")
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
    workspace: Path, prompt: Path, artifact_dir: Path, home: Path
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
        "final_message": final,
    }


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


def execute_replica(
    *,
    cell: str,
    prompt_variant: str,
    engine: str,
    replica: int,
    results_dir: Path,
    tmp_root: Path,
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
    prompt = PROMPTS[prompt_variant]["path"]
    pre_tree = {
        "head": git_output(workspace, "rev-parse", "HEAD").strip(),
        "tracked_dirty": bool(
            git_output(workspace, "status", "--porcelain", "--untracked-files=no")
        ),
        "status_sha256": sha256_bytes(prepared.pre_status.encode()),
        "overlay_input_source": prepared.overlay_input_source,
    }
    worker = (
        run_codex(workspace, prompt, artifact_dir, home)
        if engine == "terra"
        else run_sonnet(workspace, prompt, artifact_dir, home)
    )
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
    readout = static_readout(workspace)
    readout["credited_uvr_fired"] = bool(readout["uvr_fired"] and boundary["passed"])
    readout["credited_path_test_fired"] = bool(
        readout["path_test_fired"] and boundary["passed"]
    )
    requested_model = MODEL_BY_ENGINE[engine]
    invalid_reasons: list[str] = []
    if worker["exit_code"] != 0:
        invalid_reasons.append("worker-exit-nonzero")
    if worker["timed_out"]:
        invalid_reasons.append("worker-timeout")
    if not final:
        invalid_reasons.append("worker-final-message-missing")
    if not worker["cli_version"]:
        invalid_reasons.append("cli-version-missing")
    effective = worker["effective_model"]
    if effective is None:
        invalid_reasons.append("effective-model-missing")
    if worker["effective_model_source"] is None:
        invalid_reasons.append("effective-model-source-missing")
    elif engine == "terra" and effective != requested_model:
        invalid_reasons.append("effective-model-mismatch")
    elif engine == "sonnet" and "sonnet" not in effective.casefold():
        invalid_reasons.append("effective-model-mismatch")
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


def validate_prompts() -> None:
    for variant, contract in PROMPTS.items():
        path = contract["path"]
        if not path.is_file():
            raise ProbeError(f"{variant} prompt missing: {path}")
        if sha256_file(path) != contract["sha256"]:
            raise ProbeError(f"{variant} prompt hash mismatch")


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
        receipt["valid"] = bool(receipt.get("valid")) and not missing_receipt_fields(receipt)
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


def build_manifest(results_dir: Path, summary: dict[str, Any]) -> dict[str, Any]:
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
            for variant, contract in PROMPTS.items()
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
                "timeout_seconds": TIMEOUT_SECONDS,
                "fresh_home_per_replica": True,
            },
        },
        "adaptive_rule_trace": adaptive_trace(summary),
        "global_worker_runs": summary["global_worker_runs"],
        "updated_at": utc_now(),
    }


def update_outputs(results_dir: Path) -> dict[str, Any]:
    summary = summarize(results_dir)
    atomic_json(results_dir / "summary.json", summary)
    atomic_json(results_dir / "manifest.json", build_manifest(results_dir, summary))
    return summary


def run_probe(results_dir: Path, tmp_root: Path) -> int:
    validate_prompts()
    results_dir.mkdir(parents=True, exist_ok=True)
    tmp_root.mkdir(parents=True, exist_ok=True)
    lock_path = results_dir / ".runner.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProbeError(f"another r6 replay runner holds {lock_path}") from exc
        update_outputs(results_dir)
        for cell, prompt_variant, engine in CELLS:
            while True:
                receipts = load_receipts(results_dir, cell)
                valid = [receipt for receipt in receipts if receipt.get("valid")]
                target = desired_valid_replicas(receipts)
                if len(valid) >= target:
                    break
                if not can_start_worker(results_dir):
                    update_outputs(results_dir)
                    return 2
                replica = next_replica_number(results_dir, cell)
                execute_replica(
                    cell=cell,
                    prompt_variant=prompt_variant,
                    engine=engine,
                    replica=replica,
                    results_dir=results_dir,
                    tmp_root=tmp_root,
                )
                update_outputs(results_dir)
        update_outputs(results_dir)
    return 0


def expect(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS {label}")


def self_test() -> int:
    validate_prompts()
    expect(True, "F1/FL1 full SHA-256 validation")
    with tempfile.TemporaryDirectory(prefix="r6-replay-selftest-") as temporary:
        root = Path(temporary)
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

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    run_parser.add_argument("--tmp-root", type=Path, default=TMP_ROOT)
    subparsers.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "self-test":
            return self_test()
        return run_probe(args.results_dir.resolve(), args.tmp_root.resolve())
    except (ProbeError, AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"R6_REPLAY_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
