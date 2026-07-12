#!/usr/bin/env python3
"""Run or replay one blinded terminal-behavior attempt in an opaque workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


CELL_ROOT = Path(__file__).resolve().parent
NONCODING_ROOT = CELL_ROOT.parent.parent
REPO_ROOT = NONCODING_ROOT.parent.parent
MANIFEST_PATH = NONCODING_ROOT / "manifest.json"
METHOD_CARD = REPO_ROOT / "benchmark/ceiling/corpus/copycat-doc.md"
CLAUDE_ISOLATION = REPO_ROOT / "benchmark/ceiling/scripts/claude-isolation.py"
PACKET_RUNNER = runpy.run_path(str(NONCODING_ROOT / "scripts/run-packet-attempt.py"))
CONFORMANCE = runpy.run_path(str(NONCODING_ROOT / "scripts/conformance-gate.py"))
HARNESS_EXCLUDES = (".devlyn/**", ".claude/**", "AGENTS.md", "CLAUDE.md")


class RunnerError(RuntimeError):
    """The attempt is invalid and cannot enter a scored cohort."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot read {path}: {exc}") from exc


def manifest_cell() -> dict[str, Any]:
    manifest = read_json(MANIFEST_PATH)
    try:
        cell = manifest["cells"]["intent"]
    except (KeyError, TypeError) as exc:
        raise RunnerError("manifest cells.intent block is missing") from exc
    if not isinstance(cell, dict) or not isinstance(cell.get("fixtures"), dict):
        raise RunnerError("manifest cells.intent block is malformed")
    return cell


def fixture_record(fixture_id: str) -> tuple[dict[str, Any], Path]:
    fixtures = manifest_cell()["fixtures"]
    if fixture_id not in fixtures:
        raise RunnerError(f"unknown fixture {fixture_id!r}; valid fixtures: {', '.join(sorted(fixtures))}")
    record = fixtures[fixture_id]
    if not isinstance(record, dict) or not isinstance(record.get("path"), str):
        raise RunnerError(f"fixture record is malformed: {fixture_id}")
    fixture = (NONCODING_ROOT / record["path"]).resolve()
    try:
        fixture.relative_to(CELL_ROOT)
    except ValueError as exc:
        raise RunnerError(f"fixture escapes cell root: {fixture}") from exc
    return record, fixture


def validate_fixture(fixture_id: str) -> tuple[dict[str, Any], Path]:
    record, fixture = fixture_record(fixture_id)
    for required in (fixture / "task.txt", fixture / "hidden/oracle.sh"):
        if not required.is_file():
            raise RunnerError(f"fixture file missing: {required}")
    if not (fixture / "seed").is_dir():
        raise RunnerError(f"seed directory missing: {fixture / 'seed'}")
    if not os.access(fixture / "hidden/oracle.sh", os.X_OK):
        raise RunnerError(f"oracle is not executable: {fixture / 'hidden/oracle.sh'}")
    identity_pattern = re.compile(r"devlyn|benchmark|fixture|intent|holdout", re.IGNORECASE)
    visible_files = [fixture / "task.txt"] + sorted(path for path in (fixture / "seed").rglob("*") if path.is_file())
    for path in visible_files:
        if identity_pattern.search(path.read_text(encoding="utf-8", errors="replace")):
            raise RunnerError(f"arm-visible identity marker in {path}")
    task_sha = sha256_bytes((fixture / "task.txt").read_bytes())
    seed_sha = PACKET_RUNNER["tree_sha256"](fixture / "seed")
    if task_sha != record.get("task_sha256"):
        raise RunnerError(f"task hash mismatch for {fixture_id}")
    if seed_sha != record.get("seed_tree_sha256"):
        raise RunnerError(f"seed hash mismatch for {fixture_id}")
    try:
        CONFORMANCE["validate_fixture"](fixture)
    except Exception as exc:
        raise RunnerError(f"conformance freeze failed: {exc}") from exc
    return record, fixture


def resolve_replay(record: dict[str, Any], replay_arg: Path) -> tuple[str, Path]:
    replays = record.get("replays")
    if not isinstance(replays, dict):
        raise RunnerError("fixture replay declarations are missing")
    candidate = replay_arg if replay_arg.is_absolute() else REPO_ROOT / replay_arg
    candidate = candidate.resolve()
    declared: dict[str, Path] = {}
    for role, asset in replays.items():
        if not isinstance(role, str) or not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
            raise RunnerError("fixture replay declaration is malformed")
        declared[role] = (NONCODING_ROOT / asset["path"]).resolve()
    matches = [role for role, path in declared.items() if path == candidate]
    if len(matches) != 1:
        raise RunnerError(f"replay directory is not frozen for this fixture: {candidate}")
    if not candidate.is_dir():
        raise RunnerError(f"replay directory missing: {candidate}")
    for required in (candidate / "patch.diff", candidate / "message.txt"):
        if not required.is_file():
            raise RunnerError(f"replay asset missing: {required}")
    asset = replays[matches[0]]
    if sha256_bytes((candidate / "patch.diff").read_bytes()) != asset.get("patch_sha256"):
        raise RunnerError(f"replay patch hash mismatch: {candidate}")
    if sha256_bytes((candidate / "message.txt").read_bytes()) != asset.get("message_sha256"):
        raise RunnerError(f"replay message hash mismatch: {candidate}")
    return matches[0], candidate


def opaque_id(prefix: str, value: str, length: int = 12) -> str:
    return prefix + sha256_bytes(value.encode("utf-8"))[:length]


def prompt_for(arm: str, task_text: str) -> str:
    task = task_text.rstrip()
    if arm == "A":
        return "/devlyn:resolve " + json.dumps(task) + " --pair-verify"
    lead = "Fix or implement the following in this repository. Verify your work before finishing."
    if arm == "B":
        return f"{lead}\n\n{task}\n"
    method = METHOD_CARD.read_text(encoding="utf-8").rstrip()
    return (
        f"{method}\n\nFollow the methodology above end-to-end yourself (plan, implement, build gate, "
        f"cleanup, then a fresh-eyes verification pass) while completing this task:\n\n{task}\n"
    )


def stage_harness(workspace: Path) -> str:
    (workspace / ".claude").mkdir()
    shutil.copytree(REPO_ROOT / "config/skills", workspace / ".claude/skills")
    shutil.copyfile(REPO_ROOT / "CLAUDE.md", workspace / "CLAUDE.md")
    shutil.copyfile(REPO_ROOT / "AGENTS.md", workspace / "AGENTS.md")
    (workspace / ".devlyn").mkdir()
    (workspace / ".devlyn/engines.json").write_text('{"executor":"codex"}\n', encoding="utf-8")
    environment = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(workspace.parent),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "LANG": "C",
        "LC_ALL": "C",
    }
    completed = subprocess.run(
        [
            "git", "-c", "user.name=Harbor Maintainer", "-c", "user.email=maintainer@localhost",
            "add", ".claude", ".devlyn", "CLAUDE.md", "AGENTS.md",
        ],
        cwd=workspace,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        completed = subprocess.run(
            [
                "git", "-c", "user.name=Harbor Maintainer", "-c", "user.email=maintainer@localhost",
                "commit", "-q", "--amend", "--no-edit",
            ],
            cwd=workspace,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode != 0:
        raise RunnerError(f"harness staging failed: {completed.stderr.decode(errors='replace').strip()}")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=workspace, env=environment, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    ).stdout.strip()


def extract_claude_message(stdout: str) -> str:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RunnerError(f"Claude output is not JSON: {exc}") from exc
    result = payload.get("result")
    if not isinstance(result, str):
        raise RunnerError("Claude output has no string result")
    return result


def capture_patch(workspace: Path, baseline_sha: str, output: Path) -> None:
    pathspec = ["."] + [f":(exclude){path}" for path in HARNESS_EXCLUDES]
    subprocess.run(
        ["git", "add", "-N", "--", *pathspec], cwd=workspace,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    completed = subprocess.run(
        ["git", "diff", "--binary", baseline_sha, "--", *pathspec], cwd=workspace,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode != 0:
        raise RunnerError(f"diff capture failed: {completed.stderr.decode(errors='replace').strip()}")
    output.write_bytes(completed.stdout)


def contamination_hits(
    transcript: str,
    *,
    arm: str | None,
    fixture_id: str,
    run_id: str,
    workspace: Path,
    external_root: Path,
    host_home: Path,
) -> list[str]:
    sanitized = transcript
    boundary = r"(?=$|[/\s'\"`)\]}>:,;])"
    for root in sorted({str(workspace), str(external_root)}, key=len, reverse=True):
        sanitized = re.sub(re.escape(root) + boundary, "", sanitized)
    markers = {
        "axis-identity": [
            fixture_id,
            run_id,
            "benchmark/noncoding/cells/intent",
            "counterfactual intent holdout",
        ],
        "host-context": [str(host_home), "~/.claude/", "/.agents/skills/", "/.codex/skills/", "/.superset/"],
    }
    if arm in {"B", "C"}:
        markers["repository-identity"] = ["devlyn-cli", "autoresearch/iterations"]
    lowered = sanitized.casefold()
    return [family for family, values in markers.items() if any(value.casefold() in lowered for value in values)]


def run_oracle(fixture: Path, workspace: Path, baseline_sha: str, final_message: Path, home: Path) -> dict[str, Any]:
    (home / "t").mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(home),
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "TMPDIR": str(home / "t"),
        "FINAL_MESSAGE_PATH": str(final_message),
        "BASELINE_COMMIT_SHA": baseline_sha,
        "FIXTURE_HIDDEN_DIR": str(fixture / "hidden"),
    }
    completed = PACKET_RUNNER["run_process"](
        [str(fixture / "hidden/oracle.sh")], cwd=workspace, env=environment, timeout=300
    )
    return {"exit": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def execute(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    record, fixture = validate_fixture(args.fixture)
    replay_role: str | None = None
    replay_dir: Path | None = None
    if args.replay is not None:
        if args.arm is not None:
            raise RunnerError("--replay and --arm are mutually exclusive")
        replay_role, replay_dir = resolve_replay(record, args.replay)
    elif args.arm is None:
        raise RunnerError("--arm is required outside replay mode")
    if args.attempt < 1 or args.timeout_seconds < 1:
        raise RunnerError("attempt and timeout-seconds must be positive")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run_id) is None:
        raise RunnerError("run-id has invalid characters")

    task_text = (fixture / "task.txt").read_text(encoding="utf-8")
    if args.preview_prompt:
        if replay_dir is not None:
            raise RunnerError("--preview-prompt is unavailable in replay mode")
        sys.stdout.write(prompt_for(args.arm, task_text))
        raise SystemExit(0)
    if args.validate_only:
        print("intent-attempt validation: PASS")
        raise SystemExit(0)

    real_home = Path.home()
    external_root = Path(os.environ.get("NONCODING_EXTERNAL_ROOT", str(real_home / ".local/share/nx03"))).resolve()
    path_identity = re.compile(r"intent|holdout|devlyn|bench|fixture", re.IGNORECASE)
    if path_identity.search(external_root.as_posix()) or REPO_ROOT == external_root or REPO_ROOT in external_root.parents:
        raise RunnerError(f"external root is not opaque and external: {external_root}")
    run_opaque = opaque_id("r", args.run_id)
    task_opaque = opaque_id("f", args.fixture)
    route_opaque = "r0" if replay_dir is not None else {"A": "r1", "B": "r2", "C": "r3"}[args.arm]
    attempt_root = external_root / run_opaque / task_opaque / route_opaque / f"a{args.attempt}"
    workspace = attempt_root / "w"
    home = attempt_root / "h"
    codex_home = attempt_root / "d"
    private_dir = attempt_root / "i"
    artifact_dir = args.result_dir.resolve() if args.result_dir else attempt_root / "o"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    baseline_sha = PACKET_RUNNER["initialize_workspace"](fixture / "seed", workspace)
    if args.arm == "A":
        baseline_sha = stage_harness(workspace)

    prompt = "" if replay_dir is not None else prompt_for(args.arm, task_text)
    prompt_path = artifact_dir / "prompt.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    private_prompt_path = private_dir / "p"
    private_prompt_path.write_text(prompt, encoding="utf-8")
    transcript_path = artifact_dir / "transcript.txt"
    final_message_path = artifact_dir / "final-message.txt"
    private_final_message_path = private_dir / "m"
    patch_path = artifact_dir / "patch.diff"
    started = time.monotonic()
    invalid_reasons: list[str] = []
    cli_version: str | None = None
    runtime_model: str | None = None
    requested_alias = "replay"
    executor_exit: int | None = None
    claude_metadata: dict[str, Any] | None = None

    if replay_dir is not None:
        patch = replay_dir / "patch.diff"
        if patch.stat().st_size:
            applied = subprocess.run(
                ["git", "apply", str(patch)], cwd=workspace,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            if applied.returncode != 0:
                raise RunnerError(f"replay patch failed: {applied.stderr.decode(errors='replace').strip()}")
        shutil.copyfile(replay_dir / "message.txt", final_message_path)
        transcript = ""
        executor_exit = 0
    else:
        prepared_codex_home = PACKET_RUNNER["prepare_codex_home"](codex_home, real_home)
        if args.arm in {"B", "C"}:
            binary = PACKET_RUNNER["direct_binary"]("codex")
            version = subprocess.run(
                [str(binary), "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
            )
            lines = (version.stdout or version.stderr).strip().splitlines()
            if version.returncode != 0 or not lines:
                raise RunnerError("direct Codex version probe failed")
            cli_version = lines[0]
            command = [
                str(binary), "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
                "--skip-git-repo-check", "--disable", "hooks", "-C", str(workspace),
                "-s", "workspace-write", "-m", "gpt-5.6-terra", "-c", "model_reasoning_effort=xhigh",
                "--output-last-message", str(private_final_message_path), prompt,
            ]
            completed = PACKET_RUNNER["run_process"](
                command,
                cwd=workspace,
                env=PACKET_RUNNER["codex_environment"](home, prepared_codex_home, binary),
                timeout=args.timeout_seconds,
            )
            transcript = completed.stdout + ("\n" if completed.stdout and completed.stderr else "") + completed.stderr
            runtime_model = PACKET_RUNNER["codex_runtime_model"](transcript)
            requested_alias = "gpt-5.6-terra"
        else:
            metadata_path = private_dir / "isolation.json"
            debug_path = private_dir / "debug.log"
            command = [
                sys.executable, str(CLAUDE_ISOLATION), "launch", "--mode", "arm",
                "--home", str(home), "--codex-home", str(prepared_codex_home),
                "--workdir", str(workspace), "--prompt-file", str(private_prompt_path),
                "--debug-file", str(debug_path),
                "--metadata-out", str(metadata_path),
                "--user-memory-file", str(real_home / ".claude/CLAUDE.md"),
                "--timeout-seconds", str(args.timeout_seconds),
            ]
            completed = PACKET_RUNNER["run_process"](
                command, cwd=workspace, env=None, timeout=args.timeout_seconds + 45
            )
            transcript = completed.stdout + ("\n" if completed.stdout and completed.stderr else "") + completed.stderr
            runtime_model = PACKET_RUNNER["claude_runtime_model"](completed.stdout)
            requested_alias = "sonnet+terra-executor"
            claude_metadata = read_json(metadata_path) if metadata_path.is_file() else None
            if metadata_path.is_file():
                shutil.copyfile(metadata_path, artifact_dir / "claude-isolation.json")
            if debug_path.is_file():
                shutil.copyfile(debug_path, artifact_dir / "claude-debug.log")
            cli_version = (
                claude_metadata.get("direct_claude", {}).get("version")
                if isinstance(claude_metadata, dict)
                else None
            )
            if completed.returncode == 0:
                final_message_path.write_text(extract_claude_message(completed.stdout), encoding="utf-8")
        if args.arm in {"B", "C"} and private_final_message_path.is_file():
            shutil.copyfile(private_final_message_path, final_message_path)
        executor_exit = completed.returncode
        if completed.returncode != 0:
            invalid_reasons.append(f"executor-exit:{completed.returncode}")
        if args.arm in {"B", "C"} and runtime_model != "gpt-5.6-terra":
            invalid_reasons.append(f"runtime-model:{runtime_model or 'missing'}")
        if args.arm == "A" and (runtime_model is None or "sonnet" not in runtime_model.casefold()):
            invalid_reasons.append(f"runtime-model:{runtime_model or 'missing'}")
        if not final_message_path.is_file():
            invalid_reasons.append("final-message-missing")

    elapsed = time.monotonic() - started
    transcript_path.write_text(transcript, encoding="utf-8")
    hits = contamination_hits(
        transcript,
        arm=args.arm,
        fixture_id=args.fixture,
        run_id=args.run_id,
        workspace=workspace,
        external_root=external_root,
        host_home=real_home,
    )
    invalid_reasons.extend(f"contamination:{hit}" for hit in hits)
    try:
        relative_workspace = workspace.resolve().relative_to(external_root)
    except ValueError:
        invalid_reasons.append("workspace-outside-external-root")
    else:
        if re.search(r"intent|holdout|devlyn|bench|fixture", relative_workspace.as_posix(), re.IGNORECASE):
            invalid_reasons.append("opaque-path-failed")

    capture_patch(workspace, baseline_sha, patch_path)
    if final_message_path.is_file():
        try:
            oracle = run_oracle(fixture, workspace, baseline_sha, final_message_path, home)
        except Exception as exc:
            invalid_reasons.append(f"oracle-runtime:{exc}")
            oracle = {"exit": None, "stdout": "", "stderr": str(exc)}
    else:
        oracle = {"exit": None, "stdout": "", "stderr": "final message missing"}
    outcome = "INVALID" if invalid_reasons else ("PASS" if oracle["exit"] == 0 else "FAIL")

    isolation = {
        "external_root": str(external_root),
        "workspace": str(workspace),
        "opaque_paths": not any(reason == "opaque-path-failed" for reason in invalid_reasons),
        "outside_project": REPO_ROOT not in workspace.parents,
        "claude": claude_metadata,
    }
    contamination = {"markers": hits, "passed": not hits}
    (artifact_dir / "isolation.json").write_text(json.dumps(isolation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (artifact_dir / "contamination.json").write_text(
        json.dumps(contamination, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (artifact_dir / "opaque-map.json").write_text(
        json.dumps(
            {"run": {"opaque": run_opaque, "source": args.run_id}, "task": {"opaque": task_opaque, "source": args.fixture}},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    result = {
        "fixture": args.fixture,
        "arm": args.arm,
        "replay": replay_role,
        "attempt": args.attempt,
        "outcome": outcome,
        "wall_seconds": round(elapsed, 3),
        "oracle": oracle,
        "artifacts": {
            "final_message": str(final_message_path),
            "patch": str(patch_path),
            "transcript": str(transcript_path),
        },
        "provenance": {
            "run_id": args.run_id,
            "runner_commit_sha": PACKET_RUNNER["runner_commit_sha"](),
            "cli_version": cli_version,
            "requested_alias": requested_alias,
            "runtime_resolved_model": runtime_model,
            "base_tree_sha256": PACKET_RUNNER["tree_sha256"](fixture / "seed"),
            "baseline_commit_sha": baseline_sha,
            "task_sha256": sha256_bytes(task_text.encode("utf-8")),
            "executor_exit": executor_exit,
            "transcript_sha256": sha256_bytes(transcript.encode("utf-8")),
            "invalid_reasons": invalid_reasons,
        },
    }
    result_path = artifact_dir / "result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result, result_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--arm", choices=("A", "B", "C"))
    parser.add_argument("--replay", type=Path)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--run-id", default="replay")
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--validate-only", action="store_true")
    modes.add_argument("--preview-prompt", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        result, result_path = execute(parse_args())
    except SystemExit:
        raise
    except (RunnerError, OSError, subprocess.SubprocessError) as exc:
        print(f"INTENT_ATTEMPT_INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"result": str(result_path), "outcome": result["outcome"]}, sort_keys=True))
    return 3 if result["outcome"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
