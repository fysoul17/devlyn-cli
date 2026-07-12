#!/usr/bin/env python3
"""Freeze the discriminating corpus with an identity-isolated bare-Codex gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
CEILING_ROOT = HERE.parent
REPO_ROOT = CEILING_ROOT.parent.parent
CORPUS_ROOT = CEILING_ROOT / "corpus"
RESULTS_ROOT = CEILING_ROOT / "results"
EXTERNAL_ROOT = Path(os.environ.get("CEILING_EXTERNAL_ROOT", Path.home() / ".local/share/nx01"))
USER_MEMORY_FILE = Path(
    os.environ.get("CEILING_REAL_HOME", str(Path.home()))
) / ".claude/CLAUDE.md"
REAL_MANIFEST = CORPUS_ROOT / "manifest.json"
ARM_RUNNER = HERE / "run-ceiling-arm.sh"
EVALUATOR = HERE / "ceiling-eval.sh"
CONTROL_TASK = "FS1-schedule-max-runs"
VALID_SLOTS = 3
REPLACEMENTS_PER_SLOT = 2
CODEX_VERSION_TIMEOUT_SECONDS = 30
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MODEL_RE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)
BARE_MODEL = "gpt-5.6-terra"
FROZEN_ENV_KEYS = tuple(
    sorted(
        (
            "CODEX_HOME",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_NOSYSTEM",
            "HOME",
            "LANG",
            "LC_ALL",
            "NPM_CONFIG_CACHE",
            "NPM_CONFIG_USERCONFIG",
            "PATH",
            "TERM",
            "TMPDIR",
            "TZ",
        )
    )
)
FROZEN_ENV_KEYS_SHA256 = hashlib.sha256("\n".join(FROZEN_ENV_KEYS).encode()).hexdigest()
BARE_CONTEXT_LITERALS = (
    ("global-skills-path", ("/.agents/skills/", "/.codex/skills/")),
    ("devlyn-skill-identity", ("devlyn:resolve", "devlyn:auto-resolve")),
    (
        "devlyn-runtime",
        ("DEVLYN_SKILL_DIR", "DEVLYN_SHARED_DIR", ".devlyn/pipeline.state.json"),
    ),
    (
        "host-shell-startup-leak",
        (
            "/Users/aipalm/.zshenv",
            "/Users/aipalm/.zprofile",
            "/Users/aipalm/.zlogin",
        ),
    ),
    (
        "benchmark-identity",
        (
            "devlyn-cli",
            "auto-resolve benchmark",
            "benchmark fixture",
            "bench-test-repo",
            "devlyn-ceiling-external",
        ),
    ),
)
BARE_CONTEXT_REGEXES = (
    (
        "benchmark-identity",
        (
            re.compile(r"\bDR-[A-Za-z0-9._-]+", re.IGNORECASE),
            re.compile(r"\bFS1(?:-[A-Za-z0-9._-]+)?", re.IGNORECASE),
            re.compile(r"\biter\d+\b", re.IGNORECASE),
            re.compile(r"(?:^|/)(?:gate|gold)(?:/|$)", re.IGNORECASE | re.MULTILINE),
        ),
    ),
)
FORBIDDEN_PATH_TOKEN_RE = re.compile(
    r"devlyn|ceiling|gate|iter|bench|eval|trap|fixture|arm|gold", re.IGNORECASE
)
DRIFT_NOTE = (
    "Alias or runtime-resolved model drift between corpus admission and the "
    "discriminating tranche invalidates the freeze and requires re-gating."
)


class GateError(RuntimeError):
    """A gate configuration or artifact error."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_record(path: Path) -> tuple[Any | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        return read_json(path), None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid-json:{exc}"


def integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def repo_head_sha() -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    sha = completed.stdout.strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40,64}", sha) is None:
        detail = completed.stderr.strip() or sha or f"exit {completed.returncode}"
        raise GateError(f"cannot capture runner commit SHA: {detail}")
    return sha


def file_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": str(path), "exists": path.is_file()}
    if not record["exists"]:
        return record
    data = path.read_bytes()
    record["bytes"] = len(data)
    record["sha256"] = hashlib.sha256(data).hexdigest()
    return record


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, indent=1, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command), flush=True)
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        shell=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="", flush=True)
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr, flush=True)
    return completed


def candidate_rows(
    manifest: dict[str, Any],
) -> list[tuple[str, dict[str, Any], bool]]:
    tranche = manifest.get("tranche3")
    if not isinstance(tranche, dict):
        raise GateError("manifest has no tranche3 object")
    tranche_tasks = tranche.get("tasks")
    if not isinstance(tranche_tasks, dict):
        raise GateError("manifest tranche3 has no tasks object")

    rows: list[tuple[str, dict[str, Any], bool]] = []
    for task, row in tranche_tasks.items():
        if isinstance(row, dict) and row.get("candidate") is True:
            rows.append((task, row, False))

    top_tasks = manifest.get("tasks")
    if not isinstance(top_tasks, dict) or not isinstance(
        top_tasks.get(CONTROL_TASK), dict
    ):
        raise GateError(f"manifest has no top-level control row {CONTROL_TASK}")
    rows.append((CONTROL_TASK, top_tasks[CONTROL_TASK], True))
    return rows


def artifact_path(task: str, key: str) -> Path:
    task_root = CORPUS_ROOT / task
    if key == "base_sha256":
        return task_root / "base.json"
    if key == "task_sha256":
        return task_root / "task.txt"
    if key == "source_bundle_sha256":
        return task_root / "source.bundle"
    if key == "hidden_oracle_sha256":
        return task_root / "hidden" / "oracle.sh"
    if key == "hidden_reference_sha256":
        return task_root / "hidden" / "reference.patch"
    if key.startswith("hidden_") and key.endswith("_sha256"):
        stem = key.removeprefix("hidden_").removesuffix("_sha256")
        return task_root / "hidden" / f"{stem.replace('_', '-')}.js"
    raise GateError(
        f"artifact integrity error: task={task} key={key} expected=mapped-artifact "
        f"actual=unmapped path={task_root}"
    )


def integrity_mismatch(
    task: str, key: str, expected: Any, actual: Any, path: Path
) -> GateError:
    return GateError(
        f"artifact integrity mismatch: task={task} key={key} "
        f"expected={expected!r} actual={actual!r} path={path}"
    )


def verified_frozen_hashes(task: str, row: dict[str, Any]) -> dict[str, str]:
    base_path = CORPUS_ROOT / task / "base.json"
    declared_base_hash = row.get("base_sha256")
    if not isinstance(declared_base_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", declared_base_hash
    ):
        actual = declared_base_hash if "base_sha256" in row else "missing"
        raise integrity_mismatch(
            task, "base_sha256", "lowercase-64-hex", actual, base_path
        )

    base, base_error = read_json_record(base_path)
    if base_error is not None or not isinstance(base, dict):
        actual = base_error if base_error is not None else "not-object"
        raise integrity_mismatch(task, "base.json", "valid-object", actual, base_path)

    for field in ("repo", "sha"):
        expected = row.get(field)
        if not isinstance(expected, str) or not expected:
            raise integrity_mismatch(
                task, f"manifest.{field}", "non-empty-string", expected, base_path
            )
        actual = base.get(field)
        if actual != expected:
            raise integrity_mismatch(
                task, f"base.{field}", expected, actual, base_path
            )

    verified: dict[str, str] = {"sha": row["sha"]}
    declared_hashes = sorted(key for key in row if key.endswith("_sha256"))
    for key in declared_hashes:
        path = artifact_path(task, key)
        expected = row[key]
        if not path.is_file():
            raise integrity_mismatch(task, key, expected, "missing", path)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise integrity_mismatch(task, key, expected, actual, path)
        verified[key] = actual

    verified["base_sha256"] = hashlib.sha256(base_path.read_bytes()).hexdigest()
    return verified


def verify_corpus_integrity(
    rows: list[tuple[str, dict[str, Any], bool]],
) -> dict[str, dict[str, str]]:
    return {
        task: verified_frozen_hashes(task, row) for task, row, _control in rows
    }


def refuse_frozen_live_manifest(manifest: dict[str, Any]) -> None:
    tranche = manifest.get("tranche3")
    if not isinstance(tranche, dict):
        raise GateError("manifest has no tranche3 object")
    summary = tranche.get("discriminating")
    summary_frozen = isinstance(summary, dict) and (
        summary.get("frozen") is True or summary.get("status") == "frozen"
    )
    if tranche.get("status") == "frozen" or summary_frozen:
        raise GateError(
            "live gate refuses already frozen manifest tranche3; "
            "INVALID/PENDING cohorts may rerun under a new run ID"
        )


def dry_attempt_dir(
    fixture_root: Path, run_id: str, task: str, arm_attempt: str
) -> Path:
    candidates = [
        fixture_root / task / arm_attempt,
        fixture_root / run_id / task / arm_attempt,
        fixture_root / "results" / run_id / task / arm_attempt,
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def dry_gold_dir(fixture_root: Path, run_id: str, task: str) -> Path:
    candidates = [
        fixture_root / task / "gold",
        fixture_root / "gold" / task / "A1",
        fixture_root / f"{run_id}-gold" / task / "A1",
        fixture_root / "results" / f"{run_id}-gold" / task / "A1",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return candidates[0]


def objective_reasons(
    objective: Any | None, objective_error: str | None
) -> tuple[list[str], int | None, int | None, bool | None]:
    if objective_error == "missing":
        return ["objective-missing"], None, None, None
    if objective_error is not None:
        return [f"objective-{objective_error}"], None, None, None
    if not isinstance(objective, dict):
        return ["objective-not-object"], None, None, None

    reasons: list[str] = []
    apply_exit = integer(objective.get("apply_exit"))
    oracle_exit = integer(objective.get("oracle_exit"))
    resolved_value = objective.get("resolved")
    resolved = resolved_value if isinstance(resolved_value, bool) else None
    if apply_exit is None:
        reasons.append("apply-exit-missing-or-invalid")
    elif apply_exit != 0:
        reasons.append(f"apply-exit:{apply_exit}")
    if oracle_exit not in (0, 1):
        rendered = "missing-or-invalid" if oracle_exit is None else str(oracle_exit)
        reasons.append(f"oracle-runtime:{rendered}")
    if resolved is None:
        reasons.append("resolved-missing-or-invalid")
    elif oracle_exit in (0, 1) and resolved != (oracle_exit == 0):
        reasons.append("resolved-oracle-mismatch")
    return reasons, apply_exit, oracle_exit, resolved


def contamination_reasons(transcript: str, run_id: str, task: str) -> list[str]:
    reasons: list[str] = []
    lowered = transcript.casefold()
    literal_families = list(BARE_CONTEXT_LITERALS) + [
        ("benchmark-identity", (run_id, task))
    ]
    for marker_id, markers in literal_families:
        if any(marker and marker.casefold() in lowered for marker in markers):
            reason = f"bare-context-contaminated:{marker_id}"
            if reason not in reasons:
                reasons.append(reason)
    for marker_id, patterns in BARE_CONTEXT_REGEXES:
        if any(pattern.search(transcript) for pattern in patterns):
            reason = f"bare-context-contaminated:{marker_id}"
            if reason not in reasons:
                reasons.append(reason)
    if USER_MEMORY_FILE.is_file():
        user_markers = {
            line.strip()
            for line in USER_MEMORY_FILE.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            if len(line.strip()) >= 24
        }
        if any(marker in transcript for marker in user_markers):
            reasons.append("bare-context-contaminated:user-memory-leak")
    return reasons


def valid_hex(value: Any, lengths: tuple[int, ...]) -> bool:
    return isinstance(value, str) and len(value) in lengths and bool(
        re.fullmatch(r"[0-9a-f]+", value)
    )


def isolation_reasons(
    isolation: Any | None,
    isolation_error: str | None,
    transcript_bytes: bytes,
    worktree: str | None,
    task: str,
    *,
    live: bool,
) -> list[str]:
    if isolation_error == "missing":
        return ["isolation-missing"]
    if isolation_error is not None:
        return [f"isolation-{isolation_error}"]
    if not isinstance(isolation, dict):
        return ["isolation-not-object"]

    reasons: list[str] = []
    if isolation.get("schema_version") != 2:
        reasons.append("isolation-schema")

    opaque = isolation.get("opaque_paths")
    if not isinstance(opaque, dict) or opaque.get("passed") is not True:
        reasons.append("isolation-opaque-paths")
    else:
        try:
            root = Path(str(opaque["external_root"])).resolve()
            if root != EXTERNAL_ROOT.resolve():
                raise ValueError
            generated = opaque["generated"]
            if not isinstance(generated, list) or not generated:
                raise ValueError
            resolved_paths = [Path(str(path)).resolve() for path in generated]
            for path in resolved_paths:
                relative = path.relative_to(root)
                if FORBIDDEN_PATH_TOKEN_RE.search(str(relative)):
                    raise ValueError
            if worktree is None or Path(worktree).resolve() not in resolved_paths:
                raise ValueError
            for key in ("opaque_run_id", "opaque_task_id"):
                if not re.fullmatch(r"[a-z][a-z0-9]*", str(opaque.get(key, ""))):
                    raise ValueError
        except (KeyError, TypeError, ValueError):
            reasons.append("isolation-opaque-paths")

    environment = isolation.get("environment")
    if (
        not isinstance(environment, dict)
        or environment.get("keys") != list(FROZEN_ENV_KEYS)
        or environment.get("keys_sha256") != FROZEN_ENV_KEYS_SHA256
        or environment.get("forbidden_values_absent") is not True
    ):
        reasons.append("isolation-environment")

    canary = isolation.get("shell_startup_canary")
    if (
        not isinstance(canary, dict)
        or canary.get("passed") is not True
        or canary.get("host_startup_files_absent") is not True
        or not valid_hex(canary.get("stdout_sha256"), (64,))
        or not valid_hex(canary.get("stderr_sha256"), (64,))
    ):
        reasons.append("isolation-shell-startup")

    neutral = isolation.get("neutralization")
    if (
        not isinstance(neutral, dict)
        or neutral.get("schema_version") != 1
        or neutral.get("seed_derived") is not task.startswith("DR-")
        or not valid_hex(neutral.get("neutralization_diff_sha256"), (64,))
        or not valid_hex(neutral.get("neutral_baseline_sha"), (40, 64))
        or neutral.get("git_remotes") != []
        or neutral.get("git_reflogs") != []
    ):
        reasons.append("isolation-neutralization")

    git = isolation.get("git")
    if (
        not isinstance(git, dict)
        or not isinstance(neutral, dict)
        or git.get("neutral_baseline_sha") != neutral.get("neutral_baseline_sha")
        or git.get("remotes") != []
        or git.get("reflogs") != []
    ):
        reasons.append("isolation-git-metadata")

    direct = isolation.get("direct_codex")
    if (
        not isinstance(direct, dict)
        or not Path(str(direct.get("path", ""))).is_absolute()
        or ".superset" in Path(str(direct.get("path", ""))).parts
        or direct.get("superset_wrapper") is not False
        or not isinstance(direct.get("version"), str)
        or not direct["version"].strip()
    ):
        reasons.append("isolation-direct-codex")

    auth = isolation.get("auth")
    if (
        not isinstance(auth, dict)
        or auth.get("is_symlink") is not False
        or auth.get("mode") != "0600"
    ):
        reasons.append("isolation-auth")

    scan = isolation.get("forbidden_transcript_scan")
    if (
        not isinstance(scan, dict)
        or scan.get("passed") is not True
        or scan.get("hits") != []
        or scan.get("transcript_sha256")
        != hashlib.sha256(transcript_bytes).hexdigest()
    ):
        reasons.append("isolation-transcript-scan")

    if live and worktree:
        try:
            completed = subprocess.run(
                ["git", "-C", worktree, "remote"],
                env={
                    **os.environ,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                },
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            reflog_root = Path(worktree) / ".git" / "logs"
            if completed.returncode != 0 or completed.stdout.splitlines() or (
                reflog_root.exists()
                and any(path.is_file() for path in reflog_root.rglob("*"))
            ):
                reasons.append("isolation-git-metadata")
        except OSError:
            reasons.append("isolation-git-metadata")
        if isinstance(auth, dict):
            auth_path = Path(str(auth.get("path", "")))
            try:
                if (
                    auth_path.is_symlink()
                    or not auth_path.is_file()
                    or auth_path.stat().st_mode & 0o777 != 0o600
                ):
                    reasons.append("isolation-auth")
            except OSError:
                reasons.append("isolation-auth")
        if isinstance(direct, dict):
            direct_path = Path(str(direct.get("path", "")))
            if not direct_path.is_file() or not os.access(direct_path, os.X_OK):
                reasons.append("isolation-direct-codex")

    return list(dict.fromkeys(reasons))


def attempt_record(
    artifact_dir: Path,
    arm_attempt: str,
    slot: int,
    retry_index: int,
    runner_exit: int | None,
    evaluator_exit: int | None,
    run_id: str,
    task: str,
) -> dict[str, Any]:
    timing_path = artifact_dir / "timing.json"
    objective_path = artifact_dir / "objective.json"
    patch_path = artifact_dir / "patch.diff"
    transcript_path = artifact_dir / "transcript.txt"
    isolation_path = artifact_dir / "isolation.json"
    timing, timing_error = read_json_record(timing_path)
    objective, objective_error = read_json_record(objective_path)
    isolation, isolation_error = read_json_record(isolation_path)
    resolved_model = runtime_model(transcript_path)

    reasons: list[str] = []
    worktree: Any = None
    if timing_error == "missing":
        reasons.append("timing-missing")
    elif timing_error is not None:
        reasons.append(f"timing-{timing_error}")
    elif not isinstance(timing, dict):
        reasons.append("timing-not-object")
    else:
        invoke_exit = integer(timing.get("invoke_exit"))
        if invoke_exit is None:
            reasons.append("invoke-exit-missing-or-invalid")
        elif invoke_exit != 0:
            reasons.append(f"invoke-exit:{invoke_exit}")
        timed_out = timing.get("timed_out")
        if timed_out is True:
            reasons.append("timed-out")
        elif timed_out is not False:
            reasons.append("timed-out-missing-or-invalid")
        worktree = timing.get("worktree")
        if isinstance(worktree, str):
            try:
                Path(worktree).resolve().relative_to(REPO_ROOT)
            except ValueError:
                pass
            else:
                reasons.append("worktree-in-repo")

    try:
        transcript_bytes = transcript_path.read_bytes()
    except OSError:
        transcript_bytes = b""
    transcript = transcript_bytes.decode("utf-8", errors="replace")
    if not transcript:
        reasons.append("transcript-missing")
    else:
        if resolved_model is None:
            reasons.append("runtime-model-missing")
        elif resolved_model != BARE_MODEL:
            reasons.append("runtime-model-mismatch")
        reasons.extend(contamination_reasons(transcript, run_id, task))

    reasons.extend(
        isolation_reasons(
            isolation,
            isolation_error,
            transcript_bytes,
            worktree if isinstance(worktree, str) else None,
            task,
            live=runner_exit is not None,
        )
    )

    patch = file_record(patch_path)
    if not patch["exists"]:
        reasons.append("patch-not-captured")

    objective_invalid, apply_exit, oracle_exit, objective_resolved = objective_reasons(
        objective, objective_error
    )
    reasons.extend(objective_invalid)
    if evaluator_exit is not None and evaluator_exit != 0:
        reasons.append(f"evaluator-exit:{evaluator_exit}")
    valid = not reasons
    resolved = objective_resolved if valid else None

    return {
        "attempt": arm_attempt,
        "slot": slot,
        "retry_index": retry_index,
        "artifact_dir": str(artifact_dir),
        "runner_exit": runner_exit,
        "evaluator_exit": evaluator_exit,
        "timing": timing,
        "timing_error": timing_error,
        "patch": patch,
        "objective": objective,
        "objective_error": objective_error,
        "isolation": isolation,
        "isolation_error": isolation_error,
        "apply_exit": apply_exit,
        "oracle_exit": oracle_exit,
        "valid": valid,
        "resolved": resolved,
        "outcome": "pass" if resolved is True else "fail" if valid else "INVALID",
        "attempt_invalid_reasons": reasons,
        "runtime_resolved_model": resolved_model,
    }


def runtime_model(transcript_path: Path) -> str | None:
    if not transcript_path.is_file():
        return None
    try:
        match = MODEL_RE.search(
            transcript_path.read_text(encoding="utf-8", errors="replace")
        )
    except OSError:
        return None
    return match.group(1) if match else None


def gold_record(
    artifact_dir: Path,
    run_id: str,
    evaluator_exit: int | None,
) -> dict[str, Any]:
    objective, objective_error = read_json_record(artifact_dir / "objective.json")
    invalid, apply_exit, oracle_exit, resolved_field = objective_reasons(
        objective, objective_error
    )
    patch = file_record(artifact_dir / "patch.diff")
    if not patch["exists"]:
        invalid.append("patch-not-captured")
    if evaluator_exit is not None and evaluator_exit != 0:
        invalid.append(f"evaluator-exit:{evaluator_exit}")
    if resolved_field is not True:
        invalid.append("resolved-not-true")
    valid = not invalid and apply_exit == 0 and oracle_exit == 0
    return {
        "attempt": "A1",
        "run_id": run_id,
        "artifact_dir": str(artifact_dir),
        "evaluator_exit": evaluator_exit,
        "patch": patch,
        "objective": objective,
        "objective_error": objective_error,
        "apply_exit": apply_exit,
        "oracle_exit": oracle_exit,
        "resolved": valid,
        "invalid_reasons": invalid,
    }


def staged_attempt_dir(opaque_run_id: str, opaque_task_id: str, attempt: str) -> Path:
    return EXTERNAL_ROOT / "x" / opaque_run_id / opaque_task_id / attempt


def stage_and_evaluate_gold(
    task: str, gold_run_id: str, opaque_run_id: str, opaque_task_id: str
) -> tuple[Path, int]:
    artifact_dir = staged_attempt_dir(opaque_run_id, opaque_task_id, "A1")
    artifact_dir.mkdir(parents=True)
    reference = CORPUS_ROOT / task / "hidden" / "reference.patch"
    if not reference.is_file():
        raise GateError(f"gold reference missing: {reference}")
    shutil.copyfile(reference, artifact_dir / "patch.diff")
    completed = run_command(
        [
            str(EVALUATOR),
            "--run-id",
            gold_run_id,
            "--task",
            task,
            "--opaque-run-id",
            opaque_run_id,
            "--opaque-task-id",
            opaque_task_id,
            "--arm-attempt",
            "A1",
            "--attempt-dir",
            str(artifact_dir),
        ]
    )
    return artifact_dir, completed.returncode


def run_live_attempt(
    task: str,
    run_id: str,
    opaque_run_id: str,
    opaque_task_id: str,
    attempt_number: int,
    timeout_seconds: int,
) -> tuple[Path, int, int | None]:
    arm_attempt = f"B{attempt_number}"
    completed = run_command(
        [
            str(ARM_RUNNER),
            "--task",
            task,
            "--arm",
            "B",
            "--run-id",
            run_id,
            "--opaque-run-id",
            opaque_run_id,
            "--opaque-task-id",
            opaque_task_id,
            "--result-dir",
            str(staged_attempt_dir(opaque_run_id, opaque_task_id, arm_attempt)),
            "--attempt",
            str(attempt_number),
            "--timeout-seconds",
            str(timeout_seconds),
        ]
    )
    artifact_dir = staged_attempt_dir(opaque_run_id, opaque_task_id, arm_attempt)
    evaluator_exit: int | None = None
    if (artifact_dir / "patch.diff").is_file():
        evaluated = run_command(
            [
                str(EVALUATOR),
                "--run-id",
                run_id,
                "--task",
                task,
                "--opaque-run-id",
                opaque_run_id,
                "--opaque-task-id",
                opaque_task_id,
                "--arm-attempt",
                arm_attempt,
                "--attempt-dir",
                str(artifact_dir),
            ]
        )
        evaluator_exit = evaluated.returncode
    return artifact_dir, completed.returncode, evaluator_exit


def initialize_row(
    task: str,
    row: dict[str, Any],
    control: bool,
    hashes: dict[str, str],
    run_id: str,
    opaque_run_id: str,
    opaque_task_id: str,
    timeout_seconds: int,
    fixture_root: Path | None,
) -> dict[str, Any]:
    gold_run_id = f"{run_id}-gold"
    if fixture_root is None:
        gold_dir, gold_evaluator_exit = stage_and_evaluate_gold(
            task, gold_run_id, opaque_run_id, opaque_task_id
        )
    else:
        gold_dir = dry_gold_dir(fixture_root, run_id, task)
        gold_evaluator_exit = None
    gold = gold_record(gold_dir, gold_run_id, gold_evaluator_exit)

    categorical_class = (
        "positive-control" if control else str(row.get("categorical_class"))
    )
    result: dict[str, Any] = {
        "task": task,
        "categorical_class": categorical_class,
        "control": control,
        "hashes": hashes,
        "admitted": False,
        "gate_reason": "oracle-invalid" if not gold["resolved"] else "PENDING",
        "gold_attempt": gold,
        "attempts": [],
        "valid_attempts": 0,
        "resolved_attempts": 0,
        "physical_attempts": 0,
        "opaque_task_id": opaque_task_id,
        "_pending": False,
    }
    if gold["resolved"]:
        result["_pending"] = not collect_valid_slot(
            result,
            1,
            run_id,
            opaque_run_id,
            opaque_task_id,
            timeout_seconds,
            fixture_root,
        )
    return result


def collect_valid_slot(
    result: dict[str, Any],
    slot: int,
    run_id: str,
    opaque_run_id: str,
    opaque_task_id: str,
    timeout_seconds: int,
    fixture_root: Path | None,
) -> bool:
    for retry_index in range(REPLACEMENTS_PER_SLOT + 1):
        attempt_number = len(result["attempts"]) + 1
        arm_attempt = f"B{attempt_number}"
        if fixture_root is None:
            artifact_dir, runner_exit, evaluator_exit = run_live_attempt(
                result["task"],
                run_id,
                opaque_run_id,
                opaque_task_id,
                attempt_number,
                timeout_seconds,
            )
        else:
            artifact_dir = dry_attempt_dir(
                fixture_root, run_id, result["task"], arm_attempt
            )
            runner_exit = None
            evaluator_exit = None
        record = attempt_record(
            artifact_dir,
            arm_attempt,
            slot,
            retry_index,
            runner_exit,
            evaluator_exit,
            run_id,
            result["task"],
        )
        result["attempts"].append(record)
        if record["valid"]:
            return True
    return False


def complete_row(
    result: dict[str, Any],
    run_id: str,
    opaque_run_id: str,
    timeout_seconds: int,
    fixture_root: Path | None,
) -> None:
    if (
        not result["gold_attempt"]["resolved"]
        or result["_pending"]
        or result["control"]
    ):
        return
    valid = [attempt for attempt in result["attempts"] if attempt["valid"]]
    if valid and valid[0]["resolved"] is True:
        return
    for slot in range(2, VALID_SLOTS + 1):
        if not collect_valid_slot(
            result,
            slot,
            run_id,
            opaque_run_id,
            result["opaque_task_id"],
            timeout_seconds,
            fixture_root,
        ):
            result["_pending"] = True
            break


def finalize_row(result: dict[str, Any]) -> None:
    if not result["gold_attempt"]["resolved"]:
        result.pop("_pending", None)
        return
    valid = [attempt for attempt in result["attempts"] if attempt["valid"]]
    resolved = [attempt for attempt in valid if attempt["resolved"] is True]
    result["valid_attempts"] = len(valid)
    result["resolved_attempts"] = len(resolved)
    result["physical_attempts"] = len(result["attempts"])
    if result["_pending"]:
        result["gate_reason"] = "INVALID/PENDING"
    elif result["control"]:
        result["gate_reason"] = (
            "saturated:bare-resolves"
            if len(valid) == 1 and resolved
            else "control-invalid:bare-fails"
        )
    elif len(valid) == 1 and resolved:
        result["gate_reason"] = "saturated:bare-resolves"
    elif len(valid) != VALID_SLOTS:
        result["gate_reason"] = "INVALID/PENDING"
    elif resolved:
        result["gate_reason"] = "saturated:bare-resolves"
    else:
        result["admitted"] = True
        result["gate_reason"] = f"admitted:{result['categorical_class']}"
    result.pop("_pending", None)


def direct_codex_path() -> Path:
    explicit = os.environ.get("CEILING_TEST_CODEX_BIN")
    candidates = (
        [Path(explicit)]
        if explicit
        else [
            Path(directory) / "codex"
            for directory in os.environ.get("PATH", "").split(os.pathsep)
            if directory
        ]
    )
    for candidate in candidates:
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        if ".superset" in candidate.parts:
            continue
        resolved = candidate.resolve()
        if resolved.name == "codex.js":
            package_root = resolved.parent.parent
            native = sorted(
                path.resolve()
                for path in (package_root / "node_modules" / "@openai").glob(
                    "codex-*/vendor/*/bin/codex*"
                )
                if path.is_file() and os.access(path, os.X_OK)
            )
            if native:
                resolved = native[0]
        return resolved
    raise GateError("direct non-Superset Codex CLI not found")


def live_identity(run_id: str, captured_at: str) -> tuple[dict[str, Any], str]:
    binary = direct_codex_path()
    try:
        completed = subprocess.run(
            [str(binary), "--version"],
            cwd=REPO_ROOT,
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=CODEX_VERSION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise GateError(
            "codex --version timed out after "
            f"{CODEX_VERSION_TIMEOUT_SECONDS} seconds"
        ) from exc
    if completed.returncode != 0 or not completed.stdout.strip():
        detail = completed.stderr.strip() or f"exit {completed.returncode}"
        raise GateError(f"cannot capture codex CLI version: {detail}")
    return (
        {
            "cli_version": completed.stdout.strip(),
            "binary_path": str(binary),
            "requested_alias": BARE_MODEL,
            "runtime_resolved_model": None,
            "run_id": run_id,
            "captured_at": captured_at,
        },
        repo_head_sha(),
    )


def dry_identity(
    fixture_root: Path, run_id: str, captured_at: str
) -> tuple[dict[str, Any], str]:
    identity_path = fixture_root / "identity.json"
    identity = read_json(identity_path) if identity_path.is_file() else None
    if not isinstance(identity, dict):
        raise GateError(f"dry-run identity object missing: {identity_path}")
    runner_commit_sha = identity.get("runner_commit_sha")
    if not isinstance(runner_commit_sha, str) or re.fullmatch(
        r"[0-9a-f]{40,64}", runner_commit_sha
    ) is None:
        raise GateError(f"dry-run identity has no runner commit SHA: {identity_path}")
    bare = identity.get("bare")
    if not isinstance(bare, dict):
        bare = identity.get("bare_codex")
    if isinstance(bare, dict):
        identity = bare
    cli_version = identity.get("cli_version", identity.get("codex_cli_version"))
    if not isinstance(cli_version, str) or not cli_version.strip():
        raise GateError(f"dry-run identity has no CLI version: {identity_path}")
    resolved = identity.get(
        "runtime_resolved_model", identity.get("resolved_model")
    )
    if resolved is not None and not isinstance(resolved, str):
        raise GateError(f"dry-run identity has invalid resolved model: {identity_path}")
    return (
        {
            "cli_version": cli_version.strip(),
            "binary_path": identity.get("binary_path"),
            "requested_alias": BARE_MODEL,
            "runtime_resolved_model": resolved.strip() if resolved else None,
            "run_id": run_id,
            "captured_at": identity.get("captured_at", captured_at),
        },
        runner_commit_sha,
    )


def update_identity_models(
    identity: dict[str, Any], results: list[dict[str, Any]]
) -> tuple[list[str], bool]:
    models = {
        attempt["runtime_resolved_model"]
        for result in results
        for attempt in result["attempts"]
        if attempt.get("runtime_resolved_model")
    }
    if identity.get("runtime_resolved_model"):
        models.add(identity["runtime_resolved_model"])
    observed = sorted(models)
    identity["observed_runtime_models"] = observed
    identity["runtime_resolved_model"] = observed[0] if len(observed) == 1 else None
    return observed, len(observed) > 1


def opaque_run_id(run_id: str) -> str:
    return "r" + hashlib.sha256(run_id.encode()).hexdigest()[:12]


def opaque_task_ids(
    rows: list[tuple[str, dict[str, Any], bool]],
) -> dict[str, str]:
    return {task: f"fx{index:02d}" for index, (task, _row, _control) in enumerate(rows, 1)}


def write_opaque_plan(
    run_token: str,
    rows: list[tuple[str, dict[str, Any], bool]],
    task_ids: dict[str, str],
) -> None:
    plan = {
        "schema_version": 1,
        "opaque_run_id": run_token,
        "row_order": [task_ids[task] for task, _row, _control in rows],
        "attempt_policy": {
            task_ids[task]: {
                "control": control,
                "initial_valid_slots": [1],
                "expansion_valid_slots_after_initial_fail": [] if control else [2, 3],
                "replacements_per_slot": REPLACEMENTS_PER_SLOT,
                "physical_attempt_numbering": "sequential-B1-through-B9",
            }
            for task, _row, control in rows
        },
    }
    atomic_write_json(EXTERNAL_ROOT / "x" / run_token / "plan.json", plan)


def update_materialized_paths(
    result: dict[str, Any], run_id: str, gold_run_id: str
) -> None:
    task = result["task"]
    gold_destination = RESULTS_ROOT / gold_run_id / task / "A1"
    result["gold_attempt"]["artifact_dir"] = str(gold_destination)
    gold_patch = result["gold_attempt"].get("patch")
    if isinstance(gold_patch, dict):
        gold_patch["path"] = str(gold_destination / "patch.diff")
    for attempt in result["attempts"]:
        destination = RESULTS_ROOT / run_id / task / attempt["attempt"]
        attempt["artifact_dir"] = str(destination)
        for record_name in ("patch",):
            record = attempt.get(record_name)
            if isinstance(record, dict):
                record["path"] = str(destination / "patch.diff")


def materialize_live_artifacts(
    run_id: str,
    run_token: str,
    task_ids: dict[str, str],
    results: list[dict[str, Any]],
) -> None:
    gold_run_id = f"{run_id}-gold"
    for result in results:
        task = result["task"]
        opaque_task = task_ids[task]
        source_root = EXTERNAL_ROOT / "x" / run_token / opaque_task
        if result["gold_attempt"]["artifact_dir"]:
            source = source_root / "A1"
            destination = RESULTS_ROOT / gold_run_id / task / "A1"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        for attempt in result["attempts"]:
            source = source_root / attempt["attempt"]
            destination = RESULTS_ROOT / run_id / task / attempt["attempt"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        update_materialized_paths(result, run_id, gold_run_id)

    # This is deliberately the final write: no model child is alive when the
    # human task IDs become associated with their opaque workspace IDs.
    atomic_write_json(
        RESULTS_ROOT / run_id / "opaque-map.json",
        {
            "schema_version": 1,
            "opaque_run_id": run_token,
            "tasks": {opaque: task for task, opaque in task_ids.items()},
        },
    )


def live_roots(run_id: str) -> list[Path]:
    gold_run_id = f"{run_id}-gold"
    run_token = opaque_run_id(run_id)
    return [
        RESULTS_ROOT / run_id,
        RESULTS_ROOT / gold_run_id,
        EXTERNAL_ROOT / "x" / run_token,
        EXTERNAL_ROOT / "w" / run_token,
        EXTERNAL_ROOT / "h" / run_token,
        EXTERNAL_ROOT / "d" / run_token,
        EXTERNAL_ROOT / "v" / run_token,
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gate tranche3 candidates plus FS1 on one gold evaluation and "
            "staged identity-isolated bare-Codex outcomes."
        ),
        epilog=(
            "Dry fixtures use identity.json plus TASK/gold/{objective.json,"
            "patch.diff} and TASK/Bn/{timing.json,objective.json,patch.diff}."
        ),
    )
    parser.add_argument("--run-id", required=True, help="new admission cohort ID")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="manifest to update (live default: corpus/manifest.json)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=3600,
        help="per-invocation live timeout (default: 3600)",
    )
    parser.add_argument(
        "--dry-run",
        type=Path,
        metavar="FIXTURE_DIR",
        help="consume synthetic artifacts; never invoke Codex or evaluators",
    )
    args = parser.parse_args(argv)
    if not RUN_ID_RE.fullmatch(args.run_id) or args.run_id in {".", ".."}:
        parser.error("--run-id must contain only letters, digits, dot, underscore, dash")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if args.dry_run is not None and args.manifest is None:
        parser.error("--dry-run requires an explicit --manifest copy")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dry_run = args.dry_run is not None
    fixture_root = args.dry_run.resolve() if dry_run else None
    manifest_path = (
        args.manifest.resolve() if args.manifest is not None else REAL_MANIFEST.resolve()
    )
    if dry_run and manifest_path == REAL_MANIFEST.resolve():
        raise GateError("--dry-run refuses the real corpus manifest; pass a copy")
    if not manifest_path.is_file():
        raise GateError(f"manifest missing: {manifest_path}")
    if fixture_root is not None and not fixture_root.is_dir():
        raise GateError(f"fixture directory missing: {fixture_root}")

    if not dry_run:
        existing = [path for path in live_roots(args.run_id) if path.exists()]
        if existing:
            rendered = ", ".join(str(path) for path in existing)
            raise GateError(f"run ID already has live artifacts: {rendered}")

    manifest = read_json(manifest_path)
    if not dry_run:
        refuse_frozen_live_manifest(manifest)
    rows = candidate_rows(manifest)
    verified_hashes = verify_corpus_integrity(rows)
    run_token = opaque_run_id(args.run_id)
    task_ids = opaque_task_ids(rows)
    if not dry_run:
        write_opaque_plan(run_token, rows, task_ids)
    captured_at = utc_timestamp()
    identity, runner_commit_sha = (
        dry_identity(fixture_root, args.run_id, captured_at)
        if fixture_root is not None
        else live_identity(args.run_id, captured_at)
    )

    results: list[dict[str, Any]] = []
    for task, row, control in rows:
        print(f"[corpus-gate] {task}: gold + initial bare-B attempt", flush=True)
        result = initialize_row(
            task,
            row,
            control,
            verified_hashes[task],
            args.run_id,
            run_token,
            task_ids[task],
            args.timeout_seconds,
            fixture_root,
        )
        results.append(result)

    for result in results:
        complete_row(
            result,
            args.run_id,
            run_token,
            args.timeout_seconds,
            fixture_root,
        )
        finalize_row(result)
        print(
            f"[corpus-gate] {result['task']}: {result['gate_reason']} "
            f"valid={result['valid_attempts']} resolved={result['resolved_attempts']}",
            flush=True,
        )

    if not dry_run:
        materialize_live_artifacts(args.run_id, run_token, task_ids, results)

    observed_models, cohort_drift = update_identity_models(identity, results)
    pending = [
        result["task"]
        for result in results
        if result["gate_reason"] == "INVALID/PENDING"
    ]
    oracle_invalid = [
        result["task"]
        for result in results
        if result["gate_reason"] == "oracle-invalid"
    ]
    control_result = next(result for result in results if result["control"])
    control_failed = control_result["gate_reason"] != "saturated:bare-resolves"
    freeze_ok = (
        not pending and not oracle_invalid and not cohort_drift and not control_failed
    )

    for result in results:
        if result["control"]:
            continue
        task = result["task"]
        row = manifest["tranche3"]["tasks"][task]
        row["admitted"] = result["admitted"]
        row["frozen"] = bool(freeze_ok and result["admitted"])
        row["gate_reason"] = result["gate_reason"]
        row["gold_attempt"] = result["gold_attempt"]
        row["attempts"] = result["attempts"]

    admitted = [
        result["task"]
        for result in results
        if result["admitted"] and not result["control"]
    ]
    saturated = [
        result["task"]
        for result in results
        if result["gate_reason"] == "saturated:bare-resolves"
    ]
    rejected = [
        result["task"]
        for result in results
        if not result["admitted"] and result["gate_reason"] != "INVALID/PENDING"
    ]
    row_summaries = {
        result["task"]: {
            "categorical_class": result["categorical_class"],
            "control": result["control"],
            "hashes": result["hashes"],
            "admitted": result["admitted"],
            "gate_reason": result["gate_reason"],
            "gold_resolved": result["gold_attempt"]["resolved"],
            "valid_attempts": result["valid_attempts"],
            "resolved_attempts": result["resolved_attempts"],
            "physical_attempts": result["physical_attempts"],
        }
        for result in results
    }
    if cohort_drift:
        status = "INVALID-cohort-drift"
    elif control_failed:
        status = "INVALID-positive-control"
    elif oracle_invalid:
        status = "INVALID-oracle"
    elif pending:
        status = "INVALID/PENDING"
    else:
        status = "frozen"

    tranche = manifest["tranche3"]
    tranche["status"] = status
    tranche["frozen_at"] = captured_at if freeze_ok else None
    tranche["discriminating"] = {
        "status": status,
        "frozen": freeze_ok,
        "frozen_at": captured_at if freeze_ok else None,
        "run_id": args.run_id,
        "selection_rule": (
            "gold reference resolves once; one valid bare resolve saturates a row, "
            "while admission requires exactly three valid bare failures; FS1 uses "
            "exactly one valid control attempt"
        ),
        "cohort_identity": {
            "runner_commit_sha": runner_commit_sha,
            "bare_codex": identity,
            "gold_oracle": {
                "runner": EVALUATOR.name,
                "run_id": f"{args.run_id}-gold",
                "captured_at": captured_at,
            },
        },
        "drift_note": DRIFT_NOTE,
        "cohort_drift_observed": cohort_drift,
        "observed_runtime_models": observed_models,
        "positive_control": {
            **control_result,
            "passed": not control_failed,
        },
        "admitted_amplification_rows": admitted,
        "saturated_no_degradation_controls": saturated,
        "admitted": admitted,
        "rejected": rejected,
        "oracle_invalid": oracle_invalid,
        "pending": pending,
        "rows": row_summaries,
    }
    atomic_write_json(manifest_path, manifest)
    print(
        f"[corpus-gate] wrote {manifest_path}: status={status} "
        f"admitted={len(admitted)} rejected={len(rejected)} pending={len(pending)}",
        flush=True,
    )
    return 0 if freeze_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"corpus-gate: {exc}", file=sys.stderr)
        raise SystemExit(2)
