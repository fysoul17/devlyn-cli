#!/usr/bin/env python3
"""Build or reconstruct a ceiling-arm isolation receipt."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ARG_COUNT = 26


class RecoveryError(RuntimeError):
    pass


def recovery_error(field: str, detail: str) -> RecoveryError:
    return RecoveryError(f"{field}: {detail}")


def load_receipt(path: Path, field: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise recovery_error(field, f"regular file required: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise recovery_error(field, f"malformed JSON: {exc}")
    if not isinstance(value, dict):
        raise recovery_error(field, "object required")
    return value


def field(value: dict, name: str, expected_type: type):
    current = value
    lookup_name = name.split(".json.", 1)[1] if ".json." in name else name
    for component in lookup_name.split("."):
        if not isinstance(current, dict) or component not in current:
            raise recovery_error(name, "missing")
        current = current[component]
    if expected_type is int:
        valid = isinstance(current, int) and not isinstance(current, bool)
    else:
        valid = isinstance(current, expected_type)
    if not valid:
        raise recovery_error(name, f"{expected_type.__name__} required")
    return current


def require_regular_file(path: Path, name: str, *, mode: int | None = None) -> None:
    if path.is_symlink() or not path.is_file():
        raise recovery_error(name, f"regular file required: {path}")
    if mode is not None:
        actual = stat.S_IMODE(path.stat().st_mode)
        if actual != mode:
            raise recovery_error(name, f"mode {mode:04o} required, found {actual:04o}")


def require_directory(path: Path, name: str) -> None:
    if path.is_symlink() or not path.is_dir():
        raise recovery_error(name, f"directory required: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def lexical_path(path: Path) -> Path:
    return Path(os.path.normpath(str(path)))


def lexical_symlink_target(path: Path, name: str) -> Path:
    try:
        target = Path(os.readlink(path))
    except OSError as exc:
        raise recovery_error(name, f"symlink target unreadable: {exc}") from exc
    if not target.is_absolute():
        target = path.parent / target
    return lexical_path(target)


def recover_post_hoc(attempt_dir: Path) -> list[str]:
    require_directory(attempt_dir, "attempt_dir")
    attempt_dir = attempt_dir.resolve()
    timing_path = attempt_dir / "timing.json"
    neutral_path = attempt_dir / "neutralization.json"
    deps_path = attempt_dir / "deps-staging.json"
    metadata_path = attempt_dir / "claude-isolation.json"
    transcript_path = attempt_dir / "transcript.txt"
    canary_stdout = attempt_dir / "shell-canary.stdout"
    canary_stderr = attempt_dir / "shell-canary.stderr"

    timing = load_receipt(timing_path, "timing.json")
    neutral = load_receipt(neutral_path, "neutralization.json")
    deps = load_receipt(deps_path, "deps-staging.json")
    metadata = load_receipt(metadata_path, "claude-isolation.json")
    for path, name in (
        (transcript_path, "transcript.txt"),
        (canary_stdout, "shell-canary.stdout"),
        (canary_stderr, "shell-canary.stderr"),
    ):
        require_regular_file(path, name)

    task = field(timing, "timing.json.task", str)
    arm = field(timing, "timing.json.arm", str)
    attempt = field(timing, "timing.json.attempt", int)
    worktree_text = field(timing, "timing.json.worktree", str)
    if arm != "A":
        raise recovery_error("timing.json.arm", f"expected A, found {arm}")
    if attempt < 1:
        raise recovery_error("timing.json.attempt", f"positive integer required, found {attempt}")
    attempt_token = f"{arm}{attempt}"
    if attempt_dir.name != attempt_token:
        raise recovery_error(
            "attempt_dir.name", f"expected {attempt_token}, found {attempt_dir.name}"
        )
    if attempt_dir.parent.name != task:
        raise recovery_error(
            "attempt_dir.task", f"expected parent {task}, found {attempt_dir.parent.name}"
        )
    run_id = attempt_dir.parent.parent.name
    if not run_id:
        raise recovery_error("attempt_dir.run_id", "missing grandparent name")

    worktree = Path(worktree_text)
    if not worktree.is_absolute():
        raise recovery_error("timing.json.worktree", "absolute path required")
    require_directory(worktree, "timing.json.worktree")
    worktree = worktree.resolve()
    if worktree.name != "repo" or worktree.parent.name != attempt_token:
        raise recovery_error(
            "timing.json.worktree",
            f"expected .../w/<opaque-run>/<opaque-task>/{attempt_token}/repo",
        )
    opaque_task_id = worktree.parents[1].name
    opaque_run_id = worktree.parents[2].name
    if worktree.parents[3].name != "w":
        raise recovery_error("timing.json.worktree", "missing w topology component")
    external_root = worktree.parents[4]
    if (
        external_root.name != "nx01"
        or external_root.parent.name != "share"
        or external_root.parent.parent.name != ".local"
    ):
        raise recovery_error(
            "timing.json.worktree", "expected preserved ~/.local/share/nx01 topology"
        )
    if not re.fullmatch(r"[a-z][a-z0-9]*", opaque_run_id):
        raise recovery_error("topology.opaque_run_id", f"malformed: {opaque_run_id}")
    if not re.fullmatch(r"[a-z][a-z0-9]*", opaque_task_id):
        raise recovery_error("topology.opaque_task_id", f"malformed: {opaque_task_id}")
    expected_opaque_run = "r" + hashlib.sha256(run_id.encode()).hexdigest()[:12]
    expected_opaque_task = "f" + hashlib.sha256(task.encode()).hexdigest()[:12]
    if opaque_run_id != expected_opaque_run:
        raise recovery_error(
            "topology.opaque_run_id",
            f"expected {expected_opaque_run} from attempt_dir.run_id, found {opaque_run_id}",
        )
    if opaque_task_id != expected_opaque_task:
        raise recovery_error(
            "topology.opaque_task_id",
            f"expected {expected_opaque_task} from timing.json.task, found {opaque_task_id}",
        )

    claude_home = Path(field(metadata, "claude-isolation.json.home", str))
    expected_claude_home = (
        external_root / "claude-homes" / opaque_run_id / opaque_task_id / attempt_token
    )
    if claude_home != expected_claude_home:
        raise recovery_error(
            "claude-isolation.json.home",
            f"expected {expected_claude_home}, found {claude_home}",
        )
    require_directory(claude_home, "claude-isolation.json.home")

    codex_home = external_root / "d" / opaque_run_id / opaque_task_id / attempt_token
    bare_home = external_root / "h" / opaque_run_id / opaque_task_id / attempt_token
    artifact_dir = (
        external_root / "a" / opaque_run_id / opaque_task_id / attempt_token.lower()
    )
    require_directory(codex_home, "topology.codex_home")
    require_directory(bare_home, "topology.bare_home")
    require_regular_file(codex_home / "config.toml", "topology.codex_home.config.toml")
    require_regular_file(codex_home / "auth.json", "topology.codex_home.auth.json", mode=0o600)
    require_regular_file(bare_home / ".npmrc", "topology.bare_home.npmrc")
    require_directory(bare_home / "t", "topology.bare_home.tmpdir")
    require_directory(bare_home / "n", "topology.bare_home.npm_cache")

    if field(deps, "deps-staging.json.schema_version", int) != 1:
        raise recovery_error("deps-staging.json.schema_version", "expected 1")
    deps_status = field(deps, "deps-staging.json.status", str)
    if deps_status not in {"PASS", "SKIPPED_NO_LOCKFILE"}:
        raise recovery_error("deps-staging.json.status", f"non-recoverable: {deps_status}")
    node_bin = Path(field(deps, "deps-staging.json.node_bin", str))
    if not node_bin.is_absolute():
        raise recovery_error("deps-staging.json.node_bin", "absolute path required")
    require_regular_file(node_bin, "deps-staging.json.node_bin")
    if not os.access(node_bin, os.X_OK):
        raise recovery_error("deps-staging.json.node_bin", "executable required")

    if field(neutral, "neutralization.json.schema_version", int) != 1:
        raise recovery_error("neutralization.json.schema_version", "expected 1")
    neutral_sha = field(neutral, "neutralization.json.neutral_baseline_sha", str)
    if not re.fullmatch(r"[0-9a-f]{40}", neutral_sha):
        raise recovery_error("neutralization.json.neutral_baseline_sha", "40 lowercase hex required")
    git_check = subprocess.run(
        ["git", "-C", str(worktree), "cat-file", "-e", f"{neutral_sha}^{{commit}}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if git_check.returncode != 0:
        raise recovery_error(
            "neutralization.json.neutral_baseline_sha", "commit absent from retained worktree"
        )

    direct_claude = field(metadata, "claude-isolation.json.direct_claude", dict)
    claude_binary = Path(field(direct_claude, "path", str))
    claude_sha = field(direct_claude, "sha256", str)
    claude_version = field(direct_claude, "version", str)
    if not claude_binary.is_absolute():
        raise recovery_error("claude-isolation.json.direct_claude.path", "absolute path required")
    if not re.fullmatch(r"[0-9a-f]{64}", claude_sha):
        raise recovery_error(
            "claude-isolation.json.direct_claude.sha256", "64 lowercase hex required"
        )
    if not claude_version.strip():
        raise recovery_error("claude-isolation.json.direct_claude.version", "non-empty required")
    if field(direct_claude, "superset_wrapper", bool) is not False:
        raise recovery_error(
            "claude-isolation.json.direct_claude.superset_wrapper", "expected false"
        )

    direct_codex = field(metadata, "claude-isolation.json.direct_codex", dict)
    codex_binary = Path(field(direct_codex, "path", str))
    codex_sha = field(direct_codex, "sha256", str)
    if not codex_binary.is_absolute():
        raise recovery_error("claude-isolation.json.direct_codex.path", "absolute path required")
    require_regular_file(codex_binary, "claude-isolation.json.direct_codex.path")
    if not os.access(codex_binary, os.X_OK):
        raise recovery_error("claude-isolation.json.direct_codex.path", "executable required")
    if sha256_file(codex_binary) != codex_sha:
        raise recovery_error("claude-isolation.json.direct_codex.sha256", "binary hash mismatch")
    codex_probe = subprocess.run(
        [str(codex_binary), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    codex_version = codex_probe.stdout.strip()
    if codex_probe.returncode != 0 or not codex_version:
        raise recovery_error("claude-isolation.json.direct_codex.version", "version probe failed")

    frozen_path = field(metadata, "claude-isolation.json.frozen_path", str)
    env_keys = field(metadata, "claude-isolation.json.claude_env_keys", list)
    if not env_keys or not all(isinstance(value, str) and value for value in env_keys):
        raise recovery_error("claude-isolation.json.claude_env_keys", "non-empty string array required")
    shim_path = Path(field(metadata, "claude-isolation.json.shim_path", str))
    shim_target = Path(field(metadata, "claude-isolation.json.shim_target", str))
    shim_sha = field(metadata, "claude-isolation.json.shim_target_sha256", str)
    if not shim_path.is_absolute():
        raise recovery_error("claude-isolation.json.shim_path", "absolute path required")
    if not shim_target.is_absolute():
        raise recovery_error("claude-isolation.json.shim_target", "absolute path required")
    if not re.fullmatch(r"[0-9a-f]{64}", shim_sha):
        raise recovery_error(
            "claude-isolation.json.shim_target_sha256", "64 lowercase hex required"
        )
    if not shim_path.is_symlink():
        raise recovery_error("claude-isolation.json.shim_path", "symlink required")
    if lexical_symlink_target(shim_path, "claude-isolation.json.shim_path") != lexical_path(
        shim_target
    ):
        raise recovery_error("claude-isolation.json.shim_target", "symlink target mismatch")
    if lexical_path(shim_target) != lexical_path(claude_binary):
        raise recovery_error(
            "claude-isolation.json.direct_claude.path", "shim target mismatch"
        )
    if shim_sha != claude_sha:
        raise recovery_error(
            "claude-isolation.json.direct_claude.sha256", "shim target hash mismatch"
        )
    frozen_parts = frozen_path.split(os.pathsep)
    if any(
        not value or not Path(value).is_absolute() or not Path(value).is_dir()
        for value in frozen_parts
    ):
        raise recovery_error(
            "claude-isolation.json.frozen_path",
            "non-empty absolute existing directories required",
        )
    if not frozen_parts or Path(frozen_parts[0]) != shim_path.parent:
        raise recovery_error("claude-isolation.json.frozen_path", "shim directory must be first")
    if node_bin.resolve().parent not in [Path(value).resolve() for value in frozen_parts]:
        raise recovery_error("deps-staging.json.node_bin", "node directory absent from frozen_path")

    command_v = field(metadata, "claude-isolation.json.command_v_claude", dict)
    if field(command_v, "passed", bool) is not True:
        raise recovery_error("claude-isolation.json.command_v_claude.passed", "expected true")
    if field(command_v, "path", str) != str(shim_path):
        raise recovery_error("claude-isolation.json.command_v_claude.path", "shim path mismatch")
    if field(command_v, "resolved_path", str) != str(shim_target):
        raise recovery_error(
            "claude-isolation.json.command_v_claude.resolved_path", "shim target mismatch"
        )
    command_v_sha = field(command_v, "sha256", str)
    if not re.fullmatch(r"[0-9a-f]{64}", command_v_sha):
        raise recovery_error(
            "claude-isolation.json.command_v_claude.sha256", "64 lowercase hex required"
        )
    if command_v_sha != shim_sha:
        raise recovery_error("claude-isolation.json.command_v_claude.sha256", "target hash mismatch")

    user_home = external_root.parents[2]
    user_memory = user_home / ".claude" / "CLAUDE.md"
    return [
        str(attempt_dir / "isolation.json"),
        str(neutral_path),
        str(transcript_path),
        str(worktree),
        str(external_root),
        str(artifact_dir),
        str(bare_home),
        str(codex_home),
        str(canary_stdout),
        str(canary_stderr),
        ",".join(env_keys),
        frozen_path,
        str(codex_binary),
        codex_version,
        str(codex_home / "auth.json"),
        neutral_sha,
        run_id,
        task,
        opaque_run_id,
        opaque_task_id,
        arm,
        str(metadata_path),
        str(claude_home),
        str(claude_binary),
        claude_version,
        str(user_memory),
    ]


def run_checked(command: list[str], *, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        command,
        env=env,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(f"command failed: {command}: {completed.stderr}")


def self_test() -> int:
    script = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="isolation-payload-selftest-") as raw:
        base = Path(raw).resolve()
        run_id = "selftest-run"
        task = "DR-atomic-state-f11-batch-import"
        attempt = 2
        attempt_token = f"A{attempt}"
        opaque_run = "r" + hashlib.sha256(run_id.encode()).hexdigest()[:12]
        opaque_task = "f" + hashlib.sha256(task.encode()).hexdigest()[:12]
        external_root = base / "home" / ".local" / "share" / "nx01"
        attempt_dir = base / "results" / run_id / task / attempt_token
        worktree = external_root / "w" / opaque_run / opaque_task / attempt_token / "repo"
        codex_home = external_root / "d" / opaque_run / opaque_task / attempt_token
        bare_home = external_root / "h" / opaque_run / opaque_task / attempt_token
        claude_home = external_root / "claude-homes" / opaque_run / opaque_task / attempt_token
        artifact_dir = external_root / "a" / opaque_run / opaque_task / attempt_token.lower()
        bin_dir = base / "bin"
        for directory in (
            attempt_dir,
            worktree,
            codex_home,
            bare_home / "t",
            bare_home / "n",
            claude_home / "b",
            artifact_dir,
            bin_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        claude_binary = bin_dir / "claude"
        codex_binary = bin_dir / "codex"
        node_binary = bin_dir / "node"
        claude_binary.write_text("#!/bin/sh\nprintf 'claude-selftest\\n'\n", encoding="utf-8")
        codex_binary.write_text("#!/bin/sh\nprintf 'codex-selftest\\n'\n", encoding="utf-8")
        node_binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        for binary in (claude_binary, codex_binary, node_binary):
            binary.chmod(0o700)
        shim_path = claude_home / "b" / "claude"
        shim_path.symlink_to(claude_binary)
        (claude_home / ".claude").mkdir()
        (bare_home / ".npmrc").write_text("", encoding="utf-8")
        (codex_home / "config.toml").write_text('model = "selftest"\n', encoding="utf-8")
        (codex_home / "auth.json").write_bytes(b"synthetic")
        (codex_home / "auth.json").chmod(0o600)
        (worktree / ".claude" / "skills" / "devlyn:resolve").mkdir(parents=True)
        (worktree / ".claude" / "skills" / "devlyn:resolve" / "SKILL.md").write_text(
            "synthetic\n", encoding="utf-8"
        )
        (worktree / "tracked.txt").write_text("synthetic\n", encoding="utf-8")
        run_checked(["git", "-C", str(worktree), "init", "--quiet"])
        run_checked(["git", "-C", str(worktree), "config", "core.logAllRefUpdates", "false"])
        run_checked(["git", "-C", str(worktree), "add", "--all"])
        commit_env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Isolation Selftest",
            "GIT_AUTHOR_EMAIL": "selftest@example.invalid",
            "GIT_COMMITTER_NAME": "Isolation Selftest",
            "GIT_COMMITTER_EMAIL": "selftest@example.invalid",
        }
        run_checked(
            ["git", "-C", str(worktree), "commit", "--quiet", "-m", "selftest"],
            env=commit_env,
        )
        neutral_sha = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()

        (attempt_dir / "transcript.txt").write_bytes(b"")
        (attempt_dir / "shell-canary.stdout").write_bytes(b"isolation-ok")
        (attempt_dir / "shell-canary.stderr").write_bytes(b"")
        neutral = {
            "schema_version": 1,
            "seed_derived": True,
            "neutral_project_name": "harbor-tools",
            "neutralization_diff_sha256": hashlib.sha256(b"").hexdigest(),
            "neutralization_diff_bytes": 0,
            "neutral_baseline_sha": neutral_sha,
            "author_name": "Benchmark Neutralizer",
            "author_email": "neutral@example.invalid",
            "commit_date": "2000-01-01T00:00:00Z",
            "commit_message": "Initialize project",
            "git_remotes": [],
            "git_reflogs": [],
        }
        (attempt_dir / "neutralization.json").write_text(
            json.dumps(neutral, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        deps = {
            "schema_version": 1,
            "status": "PASS",
            "failed_step": None,
            "package_lock": True,
            "node_bin": str(node_binary),
            "npm_version": "selftest",
            "exit_codes": {"npm_version": 0, "npm_ci": 0, "npm_ls": 0},
        }
        (attempt_dir / "deps-staging.json").write_text(
            json.dumps(deps, indent=2) + "\n", encoding="utf-8"
        )
        env_keys = ["CLAUDE_CONFIG_DIR", "HOME", "PATH"]
        frozen_path = os.pathsep.join(
            (str(shim_path.parent), str(codex_binary.parent), str(node_binary.parent))
        )
        claude_sha = sha256_file(claude_binary)
        codex_sha = sha256_file(codex_binary)
        metadata = {
            "direct_claude": {
                "path": str(claude_binary),
                "sha256": claude_sha,
                "version": "claude-selftest",
                "requested_model": "sonnet",
                "superset_wrapper": False,
            },
            "direct_codex": {
                "path": str(codex_binary),
                "sha256": codex_sha,
                "superset_wrapper": False,
            },
            "home": str(claude_home),
            "claude_config_dir": str(claude_home / ".claude"),
            "claude_env_keys": env_keys,
            "claude_env_keys_sha256": hashlib.sha256("\n".join(env_keys).encode()).hexdigest(),
            "frozen_path": frozen_path,
            "shim_path": str(shim_path),
            "shim_target": str(claude_binary),
            "shim_target_sha256": claude_sha,
            "command_v_claude": {
                "command": "command -v claude",
                "exit_code": 0,
                "path": str(shim_path),
                "resolved_path": str(claude_binary),
                "sha256": claude_sha,
                "passed": True,
            },
            "auth_mechanism": "synthetic",
            "credentials_seeded": True,
        }
        metadata_path = attempt_dir / "claude-isolation.json"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        timing = {
            "task": task,
            "arm": "A",
            "attempt": attempt,
            "elapsed_seconds": 0,
            "invoke_exit": 0,
            "timed_out": False,
            "draw_non_diagnostic": False,
            "worktree": str(worktree),
        }
        (attempt_dir / "timing.json").write_text(
            json.dumps(timing, indent=2) + "\n", encoding="utf-8"
        )

        explicit_out = attempt_dir / "explicit.json"
        explicit_args = [
            str(explicit_out),
            str(attempt_dir / "neutralization.json"),
            str(attempt_dir / "transcript.txt"),
            str(worktree),
            str(external_root),
            str(artifact_dir),
            str(bare_home),
            str(codex_home),
            str(attempt_dir / "shell-canary.stdout"),
            str(attempt_dir / "shell-canary.stderr"),
            ",".join(env_keys),
            frozen_path,
            str(codex_binary),
            "codex-selftest",
            str(codex_home / "auth.json"),
            neutral_sha,
            run_id,
            task,
            opaque_run,
            opaque_task,
            "A",
            str(metadata_path),
            str(claude_home),
            str(claude_binary),
            "claude-selftest",
            str(external_root.parents[2] / ".claude" / "CLAUDE.md"),
        ]
        run_checked([sys.executable, str(script), *explicit_args])
        explicit_bytes = explicit_out.read_bytes()
        claude_binary.unlink()
        if not shim_path.is_symlink() or shim_path.exists():
            raise AssertionError("self-test did not create a dangling historical Claude shim")
        run_checked([sys.executable, str(script), "--post-hoc", str(attempt_dir)])
        post_hoc_bytes = (attempt_dir / "isolation.json").read_bytes()
        if explicit_bytes != post_hoc_bytes:
            raise AssertionError("normal and --post-hoc output bytes differ")

        def assert_post_hoc_rejected(case: str, expected_field: str) -> None:
            completed = subprocess.run(
                [sys.executable, str(script), "--post-hoc", str(attempt_dir)],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            expected_error = f"isolation-payload --post-hoc: {expected_field}:"
            if completed.returncode != 2 or expected_error not in completed.stderr:
                raise AssertionError(
                    f"{case} {expected_field} was not rejected: "
                    f"exit={completed.returncode} stderr={completed.stderr!r}"
                )

        deps["node_bin"] = "bin/node"
        (attempt_dir / "deps-staging.json").write_text(
            json.dumps(deps, indent=2) + "\n", encoding="utf-8"
        )
        assert_post_hoc_rejected("relative", "deps-staging.json.node_bin")
        deps["node_bin"] = str(node_binary)
        (attempt_dir / "deps-staging.json").write_text(
            json.dumps(deps, indent=2) + "\n", encoding="utf-8"
        )

        metadata["frozen_path"] = os.pathsep.join((frozen_path, "relative"))
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        assert_post_hoc_rejected(
            "relative component", "claude-isolation.json.frozen_path"
        )
        metadata["frozen_path"] = os.pathsep.join((frozen_path, str(base / "missing")))
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        assert_post_hoc_rejected(
            "nonexistent component", "claude-isolation.json.frozen_path"
        )
        metadata["frozen_path"] = frozen_path

        metadata["direct_codex"]["path"] = "bin/codex"
        metadata_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        assert_post_hoc_rejected("relative", "claude-isolation.json.direct_codex.path")
    print("ok: normal and --post-hoc isolation payload bytes identical")
    return 0


if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
    raise SystemExit(self_test())
if len(sys.argv) == 3 and sys.argv[1] == "--post-hoc":
    try:
        recovered = recover_post_hoc(Path(sys.argv[2]))
    except RecoveryError as exc:
        print(f"isolation-payload --post-hoc: {exc}", file=sys.stderr)
        raise SystemExit(2)
    sys.argv = [sys.argv[0], *recovered]
elif len(sys.argv) != ARG_COUNT + 1:
    print(
        f"usage: {Path(sys.argv[0]).name} <{ARG_COUNT} existing positional arguments> | "
        "--post-hoc <attempt-dir> | --self-test",
        file=sys.stderr,
    )
    raise SystemExit(2)

(
    out_path,
    neutral_path,
    transcript_path,
    worktree,
    external_root,
    artifact_dir,
    bare_home,
    codex_home,
    canary_stdout_path,
    canary_stderr_path,
    env_keys_csv,
    frozen_path,
    codex_binary,
    codex_version,
    auth_path,
    neutral_baseline_sha,
    run_id,
    task,
    opaque_run_id,
    opaque_task_id,
    arm,
    claude_metadata_path,
    claude_home,
    claude_binary,
    claude_version,
    user_memory_path,
) = sys.argv[1:]

transcript_bytes = Path(transcript_path).read_bytes()
transcript = transcript_bytes.decode("utf-8", errors="replace")
literal_families = {
    "global-skills-path": ("/.agents/skills/", "/.codex/skills/"),
    "devlyn-skill-identity": ("devlyn:resolve", "devlyn:auto-resolve"),
    "devlyn-runtime": (
        "DEVLYN_SKILL_DIR",
        "DEVLYN_SHARED_DIR",
        ".devlyn/pipeline.state.json",
    ),
    "host-shell-startup-leak": (
        "/Users/aipalm/.zshenv",
        "/Users/aipalm/.zprofile",
        "/Users/aipalm/.zlogin",
    ),
    "benchmark-identity": (
        "devlyn-cli",
        "auto-resolve benchmark",
        "benchmark fixture",
        "bench-test-repo",
        "devlyn-ceiling-external",
        run_id,
        task,
    ),
}
if arm == "A":
    literal_families = {
        "host-shell-startup-leak": literal_families["host-shell-startup-leak"],
        "superset-wrapper": ("/.superset/", "SUPERSET_AGENT_ID"),
    }
hits = []
lowered = transcript.lower()
for family, markers in literal_families.items():
    matched = sorted({marker for marker in markers if marker and marker.lower() in lowered})
    if matched:
        hits.append({"family": family, "markers": matched})
regexes = {
    "benchmark-identity": (
        r"\bDR-[A-Za-z0-9._-]+",
        r"\bFS1(?:-[A-Za-z0-9._-]+)?",
        r"\biter\d+\b",
        r"(?:^|/)(?:gate|gold)(?:/|$)",
    )
}
for family, patterns in regexes.items():
    if arm == "A" and family == "benchmark-identity":
        continue
    matched = sorted(
        {pattern for pattern in patterns if re.search(pattern, transcript, re.IGNORECASE | re.MULTILINE)}
    )
    if matched:
        hits.append({"family": family, "patterns": matched})

user_memory = Path(user_memory_path)
if user_memory.is_file():
    memory_lines = sorted(
        {
            line.strip()
            for line in user_memory.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(line.strip()) >= 24
        }
    )
    memory_hits = [line for line in memory_lines if line in transcript]
    if memory_hits:
        hits.append(
            {
                "family": "user-memory-leak",
                "marker_sha256": [
                    hashlib.sha256(line.encode()).hexdigest() for line in memory_hits
                ],
            }
        )

root = Path(external_root).resolve()
generated_paths = [
    Path(worktree).resolve(),
    Path(artifact_dir).resolve(),
    Path(bare_home).resolve(),
    Path(codex_home).resolve(),
]
if arm == "A":
    generated_paths.append(Path(claude_home).resolve())
forbidden_path = re.compile(
    r"(?:devlyn|ceiling|gate|iter|bench|eval|trap|fixture|arm|gold)", re.IGNORECASE
)
opaque_paths_pass = True
for path in generated_paths:
    try:
        relative = path.relative_to(root)
    except ValueError:
        opaque_paths_pass = False
        break
    if forbidden_path.search(str(relative)):
        opaque_paths_pass = False
        break

claude_metadata = None
if arm == "A" and Path(claude_metadata_path).is_file():
    claude_metadata = json.loads(Path(claude_metadata_path).read_text(encoding="utf-8"))
env_keys = (
    claude_metadata.get("claude_env_keys", [])
    if isinstance(claude_metadata, dict) and arm == "A"
    else sorted(env_keys_csv.split(","))
)
env_values = {
    "PATH": frozen_path,
    "HOME": bare_home,
    "CODEX_HOME": codex_home,
    "TERM": "dumb",
    "LANG": "en_US.UTF-8",
    "LC_ALL": "en_US.UTF-8",
    "TZ": "UTC",
    "TMPDIR": str(Path(bare_home) / "t"),
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "NPM_CONFIG_USERCONFIG": str(Path(bare_home) / ".npmrc"),
    "NPM_CONFIG_CACHE": str(Path(bare_home) / "n"),
}
if arm == "A":
    env_values.update(
        {
            "PATH": str(claude_metadata.get("frozen_path", "")),
            "HOME": claude_home,
            "CLAUDE_CONFIG_DIR": str(Path(claude_home) / ".claude"),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
            "TMPDIR": str(Path(claude_home) / "t"),
            "NPM_CONFIG_USERCONFIG": str(Path(claude_home) / ".npmrc"),
            "NPM_CONFIG_CACHE": str(Path(claude_home) / "n"),
        }
    )
forbidden_env = re.compile(
    r"devlyn|codex_companion|superset" if arm == "A" else r"claude|devlyn|codex_companion|superset",
    re.IGNORECASE,
)
canary_stdout = Path(canary_stdout_path).read_bytes()
canary_stderr = Path(canary_stderr_path).read_bytes()
neutral = json.loads(Path(neutral_path).read_text(encoding="utf-8"))
remotes = subprocess.run(
    ["git", "-C", worktree, "remote"],
    env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull},
    check=True,
    text=True,
    stdout=subprocess.PIPE,
).stdout.splitlines()
reflog_root = Path(worktree) / ".git" / "logs"
reflogs = sorted(
    str(path.relative_to(Path(worktree) / ".git"))
    for path in reflog_root.rglob("*")
    if path.is_file()
) if reflog_root.exists() else []
auth = Path(auth_path)
payload = {
    "schema_version": 2,
    "opaque_paths": {
        "external_root": str(root),
        "opaque_run_id": opaque_run_id,
        "opaque_task_id": opaque_task_id,
        "generated": [str(path) for path in generated_paths],
        "passed": opaque_paths_pass,
    },
    "environment": {
        "keys": env_keys,
        "keys_sha256": hashlib.sha256("\n".join(env_keys).encode()).hexdigest(),
        "forbidden_values_absent": not any(
            forbidden_env.search(value) for value in env_values.values()
        ),
    },
    "shell_startup_canary": {
        "passed": canary_stdout == b"isolation-ok" and not canary_stderr,
        "stdout_sha256": hashlib.sha256(canary_stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(canary_stderr).hexdigest(),
        "host_startup_files_absent": not any(
            marker.encode() in canary_stderr
            for marker in ("/.zshenv", "/.zprofile", "/.zlogin")
        ),
    },
    "neutralization": neutral,
    "git": {
        "neutral_baseline_sha": neutral_baseline_sha,
        "remotes": remotes,
        "reflogs": reflogs,
    },
    "direct_codex": {
        "path": str(Path(codex_binary).resolve()),
        "version": codex_version,
        "superset_wrapper": ".superset" in Path(codex_binary).parts,
    },
    "auth": {
        "path": str(auth.resolve()),
        "is_symlink": auth.is_symlink(),
        "mode": format(stat.S_IMODE(auth.stat().st_mode), "04o"),
    },
    "forbidden_transcript_scan": {
        "passed": not hits,
        "transcript_sha256": hashlib.sha256(transcript_bytes).hexdigest(),
        "hits": hits,
    },
}
if arm == "A":
    if not isinstance(claude_metadata, dict):
        hits.append({"family": "claude-isolation-metadata-missing"})
        claude_metadata = {}
    direct_claude = claude_metadata.get("direct_claude")
    if not isinstance(direct_claude, dict):
        direct_claude = {
            "path": str(Path(claude_binary).resolve()),
            "sha256": hashlib.sha256(Path(claude_binary).read_bytes()).hexdigest(),
            "version": claude_version,
            "superset_wrapper": ".superset" in Path(claude_binary).parts,
        }
    payload.update(
        {
            "direct_claude": direct_claude,
            "frozen_path": claude_metadata.get("frozen_path"),
            "shim_path": claude_metadata.get("shim_path"),
            "shim_target": claude_metadata.get("shim_target"),
            "shim_target_sha256": claude_metadata.get("shim_target_sha256"),
            "command_v_claude": claude_metadata.get("command_v_claude"),
            "home": claude_metadata.get("home", str(Path(claude_home).resolve())),
            "claude_config_dir": claude_metadata.get(
                "claude_config_dir", str(Path(claude_home).resolve() / ".claude")
            ),
            "claude_env_keys": claude_metadata.get("claude_env_keys", []),
            "claude_env_keys_sha256": claude_metadata.get("claude_env_keys_sha256"),
            "auth_mechanism": claude_metadata.get("auth_mechanism"),
            "credentials_seeded": claude_metadata.get("credentials_seeded", False),
        }
    )
    shim_path = Path(str(claude_metadata.get("shim_path", "")))
    shim_target = Path(str(claude_metadata.get("shim_target", "")))
    command_v = claude_metadata.get("command_v_claude") or {}
    frozen_parts = str(claude_metadata.get("frozen_path", "")).split(os.pathsep)
    try:
        shim_path.relative_to(Path(claude_home).resolve())
        shim_inside_home = True
    except ValueError:
        shim_inside_home = False
    shim_valid = (
        shim_inside_home
        and shim_path.is_symlink()
        and lexical_symlink_target(shim_path, "claude-isolation.json.shim_path")
        == lexical_path(shim_target)
        and bool(frozen_parts)
        and Path(frozen_parts[0]) == shim_path.parent
        and claude_metadata.get("shim_target_sha256") == direct_claude.get("sha256")
        and command_v.get("passed") is True
        and command_v.get("path") == str(shim_path)
        and command_v.get("resolved_path") == str(shim_target)
        and command_v.get("sha256") == claude_metadata.get("shim_target_sha256")
    )
    claude_invalid = (
        direct_claude.get("superset_wrapper") is not False
        or ".superset" in str(claude_metadata.get("frozen_path", ""))
        or not shim_valid
        or claude_metadata.get("credentials_seeded") is not True
        or not (Path(worktree) / ".claude/skills/devlyn:resolve/SKILL.md").is_file()
        or any(marker in transcript.casefold() for marker in ("not logged in", "authentication_error"))
    )
    if claude_invalid:
        hits.append({"family": "claude-isolation-contract"})
    payload["forbidden_transcript_scan"]["passed"] = not hits
    payload["forbidden_transcript_scan"]["hits"] = hits
Path(out_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
