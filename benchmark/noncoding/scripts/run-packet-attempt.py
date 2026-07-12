#!/usr/bin/env python3
"""Run one blinded packet-to-executor-to-oracle attempt in an opaque workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
REPO_ROOT = ROOT.parent.parent
MANIFEST_PATH = ROOT / "manifest.json"
PACKET_MODULE = runpy.run_path(str(SCRIPT_DIR / "packet-schema.py"))
CONFORMANCE_MODULE = runpy.run_path(str(SCRIPT_DIR / "conformance-gate.py"))
CLAUDE_ISOLATION = REPO_ROOT / "benchmark/ceiling/scripts/claude-isolation.py"
SEATS = {"terra", "sonnet"}


class RunnerError(RuntimeError):
    """The attempt is invalid and must not enter calibration counts."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot read {path}: {exc}") from exc


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if not files:
        raise RunnerError(f"seed has no files: {root}")
    for path in files:
        if path.is_symlink():
            raise RunnerError(f"seed symlink forbidden: {path}")
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(format(path.stat().st_mode & 0o777, "04o").encode("ascii") + b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def fixture_record(fixture_id: str) -> tuple[dict[str, Any], Path]:
    manifest = read_json(MANIFEST_PATH)
    fixtures = manifest.get("fixtures") if isinstance(manifest, dict) else None
    if not isinstance(fixtures, dict) or fixture_id not in fixtures:
        valid = ", ".join(sorted(fixtures or {}))
        raise RunnerError(f"unknown fixture {fixture_id!r}; valid fixtures: {valid}")
    record = fixtures[fixture_id]
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise RunnerError(f"fixture manifest record malformed: {fixture_id}")
    fixture = (ROOT / record["path"]).resolve()
    try:
        fixture.relative_to((ROOT / "calibration").resolve())
    except ValueError as exc:
        raise RunnerError(f"fixture escapes calibration namespace: {fixture}") from exc
    return record, fixture


def resolve_packet(record: dict[str, Any], packet_arg: str) -> Path:
    packet = Path(packet_arg)
    if not packet.is_absolute():
        packet = (ROOT / packet).resolve()
    else:
        packet = packet.resolve()
    declared = record.get("packets")
    if not isinstance(declared, dict):
        raise RunnerError("fixture has no packet declarations")
    allowed = {(ROOT / value).resolve() for value in declared.values() if isinstance(value, str)}
    no_op = (ROOT / read_json(MANIFEST_PATH).get("no_op_packet", "")).resolve()
    allowed.add(no_op)
    if packet not in allowed:
        raise RunnerError(f"packet is not frozen for this fixture: {packet}")
    if not packet.is_file():
        raise RunnerError(f"packet missing: {packet}")
    return packet


def validate_inputs(args: argparse.Namespace) -> tuple[dict[str, Any], Path, Path, dict[str, Any]]:
    if args.seat not in SEATS:
        raise RunnerError(f"seat must be one of: {', '.join(sorted(SEATS))}")
    if args.attempt < 1:
        raise RunnerError("attempt must be a positive integer")
    if args.timeout_seconds < 1:
        raise RunnerError("timeout-seconds must be positive")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id) is None:
        raise RunnerError("run-id must match [A-Za-z0-9][A-Za-z0-9._-]*")
    record, fixture = fixture_record(args.fixture)
    task_path = fixture / "task.txt"
    seed = fixture / "seed"
    base_path = fixture / "base.json"
    oracle = fixture / "hidden/oracle.sh"
    for required in (task_path, base_path, oracle):
        if not required.is_file():
            raise RunnerError(f"fixture file missing: {required}")
    if not seed.is_dir():
        raise RunnerError(f"seed directory missing: {seed}")
    if not os.access(oracle, os.X_OK):
        raise RunnerError(f"oracle is not executable: {oracle}")
    base = read_json(base_path)
    if not isinstance(base, dict) or set(base) != {"repo", "tree_sha256"} or base["repo"] != "./seed":
        raise RunnerError(f"base.json malformed: {base_path}")
    observed_tree = tree_sha256(seed)
    if base["tree_sha256"] != observed_tree:
        raise RunnerError(f"seed tree hash mismatch: expected {base['tree_sha256']} observed {observed_tree}")
    try:
        CONFORMANCE_MODULE["validate_fixture"](fixture)
    except Exception as exc:
        raise RunnerError(f"conformance freeze failed: {exc}") from exc
    packet_path = resolve_packet(record, args.packet)
    try:
        packet = PACKET_MODULE["load_packet"](packet_path)
    except Exception as exc:
        raise RunnerError(str(exc)) from exc
    return record, fixture, packet_path, packet


def build_prompt(task_text: str, packet: dict[str, Any]) -> str:
    rendered = json.dumps(packet, indent=2, sort_keys=False)
    return (
        "You are the downstream executor. The task states the desired outcome; the JSON packet "
        "defines the authorized work. Execute its tasks, dependencies, context, and scope exactly "
        "as written. `depends_on` defines the legal execution order; array position is not a schedule. "
        "Do not infer, repair, reorder, or enrich missing packet content. If tasks is empty, make no "
        "repository changes.\n\n"
        f"{task_text.rstrip()}\n\nExecution packet (JSON):\n{rendered}\n"
    )


def opaque_id(prefix: str, value: str, length: int = 12) -> str:
    return prefix + sha256_bytes(value.encode("utf-8"))[:length]


def runner_commit_sha() -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    sha = completed.stdout.strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", sha) is None:
        raise RunnerError("runner commit SHA unavailable")
    return sha


def initialize_workspace(seed: Path, workspace: Path) -> str:
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(seed, workspace)
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(workspace.parent),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "LANG": "C",
        "LC_ALL": "C",
    }
    commands = (
        ["git", "init", "-q"],
        ["git", "add", "--all"],
        ["git", "-c", "user.name=Harbor Maintainer", "-c", "user.email=maintainer@localhost", "commit", "-q", "-m", "Initial source"],
    )
    for command in commands:
        completed = subprocess.run(command, cwd=workspace, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            raise RunnerError(f"workspace initialization failed: {completed.stderr.decode(errors='replace').strip()}")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace, env=env, text=True, stdout=subprocess.PIPE, check=True
    ).stdout.strip()


def run_process(command: list[str], *, cwd: Path, env: dict[str, str] | None, timeout: int) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
        raise RunnerError(f"executor timed out after {timeout}s") from exc
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def prepare_codex_home(external: Path, real_home: Path) -> Path:
    codex_home = external
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text(
        'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "xhigh"\n', encoding="utf-8"
    )
    source = Path(os.environ.get("NONCODING_TEST_AUTH_JSON", str(real_home / ".codex/auth.json")))
    if not source.is_file():
        raise RunnerError(f"Codex auth file missing: {source}")
    destination = codex_home / "auth.json"
    shutil.copyfile(source, destination)
    destination.chmod(0o600)
    return codex_home


def direct_binary(name: str) -> Path:
    module = runpy.run_path(str(CLAUDE_ISOLATION))
    explicit = os.environ.get(f"NONCODING_TEST_{name.upper()}_BIN")
    try:
        return Path(module["resolve_direct_binary"](name, explicit))
    except Exception as exc:
        raise RunnerError(str(exc)) from exc


def codex_environment(home: Path, codex_home: Path, codex_binary: Path) -> dict[str, str]:
    node = shutil.which("node")
    path_parts = [str(codex_binary.parent)]
    if node:
        path_parts.append(str(Path(node).resolve().parent))
    path_parts.extend(["/usr/bin", "/bin", "/usr/sbin", "/sbin"])
    frozen_path = os.pathsep.join(dict.fromkeys(path_parts))
    if ".superset" in frozen_path:
        raise RunnerError("Superset path reached frozen Codex PATH")
    (home / "t").mkdir(parents=True, exist_ok=True)
    (home / "n").mkdir(parents=True, exist_ok=True)
    (home / ".npmrc").touch()
    return {
        "PATH": frozen_path,
        "HOME": str(home),
        "CODEX_HOME": str(codex_home),
        "TERM": "dumb",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "TZ": "UTC",
        "TMPDIR": str(home / "t"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "NPM_CONFIG_USERCONFIG": str(home / ".npmrc"),
        "NPM_CONFIG_CACHE": str(home / "n"),
    }


def codex_runtime_model(transcript: str) -> str | None:
    match = re.search(r"^model:\s*(\S+)\s*$", transcript, re.MULTILINE | re.IGNORECASE)
    return match.group(1) if match else None


def claude_runtime_model(stdout: str) -> str | None:
    try:
        wrapper = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    usage = wrapper.get("modelUsage") or wrapper.get("usage")
    if not isinstance(usage, dict) or not usage:
        return None
    models = sorted(str(model) for model in usage)
    return models[0] if len(models) == 1 else ",".join(models)


def scan_contamination(
    transcript: str,
    *,
    fixture_id: str,
    run_id: str,
    packet_name: str,
    workspace: Path,
    external_root: Path,
    host_home: Path,
) -> list[str]:
    sanitized = transcript
    path_boundary = r"(?=$|[/\s'\"`)\]}>:,;])"
    for sanctioned_root in sorted({str(workspace), str(external_root)}, key=len, reverse=True):
        sanitized = re.sub(re.escape(sanctioned_root) + path_boundary, "", sanitized)
    markers = {
        "repository-identity": ["devlyn-cli", "benchmark/noncoding", "autoresearch/iterations"],
        "host-context": [
            "/.agents/skills/",
            "/.codex/skills/",
            str(host_home),
            "~/.claude/",
            "/.superset/",
        ],
        "blinded-label": [fixture_id, run_id, packet_name],
    }
    lowered = sanitized.casefold()
    hits: list[str] = []
    for family, values in markers.items():
        if any(value and value.casefold() in lowered for value in values):
            hits.append(family)
    return hits


def execute(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    _record, fixture, packet_path, packet = validate_inputs(args)
    task_text = (fixture / "task.txt").read_text(encoding="utf-8")
    prompt = build_prompt(task_text, packet)
    if args.preview_prompt:
        sys.stdout.write(prompt)
        raise SystemExit(0)
    if args.validate_only:
        print("packet-attempt validation: PASS")
        raise SystemExit(0)

    real_home = Path.home()
    external_root = Path(os.environ.get("NONCODING_EXTERNAL_ROOT", str(real_home / ".local/share/nx02"))).resolve()
    run_opaque = opaque_id("r", args.run_id)
    task_opaque = opaque_id("t", args.fixture)
    packet_bytes = packet_path.read_bytes()
    packet_id = opaque_id("p", sha256_bytes(packet_bytes), 16)
    seat_opaque = "s1" if args.seat == "terra" else "s2"
    attempt_opaque = f"a{args.attempt}"
    attempt_root = external_root / run_opaque / task_opaque / packet_id / seat_opaque / attempt_opaque
    workspace = attempt_root / "w"
    home = attempt_root / "h"
    codex_home = attempt_root / "d"
    artifact_dir = Path(args.result_dir).resolve() if args.result_dir else attempt_root / "o"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    baseline_sha = initialize_workspace(fixture / "seed", workspace)
    prepared_codex_home = prepare_codex_home(codex_home, real_home)
    prompt_path = artifact_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    transcript_path = artifact_dir / "transcript.txt"
    metadata_path = artifact_dir / "claude-isolation.json"
    started = time.monotonic()
    if args.seat == "terra":
        binary = direct_binary("codex")
        version_result = subprocess.run([str(binary), "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        version_lines = (version_result.stdout or version_result.stderr).strip().splitlines()
        if version_result.returncode != 0 or not version_lines:
            raise RunnerError("direct Codex CLI version probe failed")
        cli_version = version_lines[0]
        command = [
            str(binary), "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
            "--skip-git-repo-check", "--disable", "hooks", "-C", str(workspace),
            "-s", "workspace-write", "-m", "gpt-5.6-terra", "-c", "model_reasoning_effort=xhigh", prompt,
        ]
        completed = run_process(command, cwd=workspace, env=codex_environment(home, prepared_codex_home, binary), timeout=args.timeout_seconds)
        runtime_model = codex_runtime_model(completed.stdout + "\n" + completed.stderr)
        requested_alias = "gpt-5.6-terra"
        isolation_metadata = None
    else:
        prompt_path.write_text(prompt, encoding="utf-8")
        command = [
            sys.executable, str(CLAUDE_ISOLATION), "launch", "--mode", "arm",
            "--home", str(home), "--codex-home", str(prepared_codex_home),
            "--workdir", str(workspace), "--prompt-file", str(prompt_path),
            "--debug-file", str(artifact_dir / "claude-debug.log"),
            "--metadata-out", str(metadata_path),
            "--user-memory-file", str(real_home / ".claude/CLAUDE.md"),
            "--timeout-seconds", str(args.timeout_seconds),
        ]
        completed = run_process(command, cwd=workspace, env=None, timeout=args.timeout_seconds + 45)
        runtime_model = claude_runtime_model(completed.stdout)
        requested_alias = "sonnet"
        isolation_metadata = read_json(metadata_path) if metadata_path.is_file() else None
        cli_version = (
            isolation_metadata.get("direct_claude", {}).get("version")
            if isinstance(isolation_metadata, dict)
            else None
        )
    elapsed = time.monotonic() - started
    transcript = completed.stdout + ("\n" if completed.stdout and completed.stderr else "") + completed.stderr
    transcript_path.write_text(transcript, encoding="utf-8")
    invalid_reasons: list[str] = []
    if completed.returncode != 0:
        invalid_reasons.append(f"executor-exit:{completed.returncode}")
    if args.seat == "terra" and runtime_model != "gpt-5.6-terra":
        invalid_reasons.append(f"runtime-model:{runtime_model or 'missing'}")
    if args.seat == "sonnet" and (runtime_model is None or "sonnet" not in runtime_model.casefold()):
        invalid_reasons.append(f"runtime-model:{runtime_model or 'missing'}")
    invalid_reasons.extend(
        f"contamination:{value}"
        for value in scan_contamination(
            transcript,
            fixture_id=args.fixture,
            run_id=args.run_id,
            packet_name=packet_path.name,
            workspace=workspace,
            external_root=external_root,
            host_home=real_home,
        )
    )
    try:
        relative_workspace = workspace.resolve().relative_to(external_root)
        if re.search(r"devlyn|bench|fixture|calibration|good|bad", str(relative_workspace), re.IGNORECASE):
            invalid_reasons.append("opaque-path-failed")
    except ValueError:
        invalid_reasons.append("workspace-outside-external-root")

    oracle = fixture / "hidden/oracle.sh"
    oracle_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "FIXTURE_HIDDEN_DIR": str(fixture / "hidden"),
    }
    try:
        oracle_result = run_process([str(oracle)], cwd=workspace, env=oracle_env, timeout=min(args.timeout_seconds, 300))
        oracle_raw = {
            "exit": oracle_result.returncode,
            "stdout": oracle_result.stdout,
            "stderr": oracle_result.stderr,
        }
    except RunnerError as exc:
        invalid_reasons.append(f"oracle-runtime:{exc}")
        oracle_raw = {"exit": None, "stdout": "", "stderr": str(exc)}
    outcome = "INVALID" if invalid_reasons else ("resolve" if oracle_raw["exit"] == 0 else "fail")
    result = {
        "fixture": args.fixture,
        "packet_id": packet_id,
        "seat": args.seat,
        "attempt": args.attempt,
        "outcome": outcome,
        "wall_seconds": round(elapsed, 3),
        "oracle": oracle_raw,
        "provenance": {
            "run_id": args.run_id,
            "runner_commit_sha": runner_commit_sha(),
            "cli_version": cli_version,
            "requested_alias": requested_alias,
            "runtime_resolved_model": runtime_model,
            "base_tree_sha256": tree_sha256(fixture / "seed"),
            "baseline_commit_sha": baseline_sha,
            "packet_sha256": sha256_bytes(packet_bytes),
            "task_sha256": sha256_bytes(task_text.encode("utf-8")),
            "external_root": str(external_root),
            "workspace": str(workspace),
            "opaque_run_id": run_opaque,
            "opaque_task_id": task_opaque,
            "executor_exit": completed.returncode,
            "transcript_sha256": sha256_bytes(transcript.encode("utf-8")),
            "claude_isolation": isolation_metadata,
            "invalid_reasons": invalid_reasons,
        },
    }
    result_path = artifact_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result, result_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--packet", required=True)
    parser.add_argument("--seat", required=True)
    parser.add_argument("--attempt", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--validate-only", action="store_true")
    modes.add_argument("--preview-prompt", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result, result_path = execute(args)
    except SystemExit:
        raise
    except (RunnerError, OSError, subprocess.SubprocessError) as exc:
        print(f"PACKET_ATTEMPT_INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"result": str(result_path), "outcome": result["outcome"]}, sort_keys=True))
    return 3 if result["outcome"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
