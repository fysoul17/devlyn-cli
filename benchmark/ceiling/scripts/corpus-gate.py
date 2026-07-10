#!/usr/bin/env python3
"""Freeze the iter-0068 discriminating corpus with a bare-Codex gate."""

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
EXTERNAL_ROOT = CEILING_ROOT / "external"
REAL_MANIFEST = CORPUS_ROOT / "manifest.json"
ARM_RUNNER = HERE / "run-ceiling-arm.sh"
EVALUATOR = HERE / "ceiling-eval.sh"
CONTROL_TASK = "FS1-schedule-max-runs"
REQUESTED_ALIAS = "default"
VALID_SLOTS = 3
REPLACEMENTS_PER_SLOT = 2
CODEX_VERSION_TIMEOUT_SECONDS = 30
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
MODEL_RE = re.compile(r"^model:\s*(\S+)\s*$", re.MULTILINE)
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
    mode = path.stat().st_mode & 0o777
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


def attempt_record(
    artifact_dir: Path,
    arm_attempt: str,
    slot: int,
    retry_index: int,
    runner_exit: int | None,
    evaluator_exit: int | None,
) -> dict[str, Any]:
    timing_path = artifact_dir / "timing.json"
    objective_path = artifact_dir / "objective.json"
    patch_path = artifact_dir / "patch.diff"
    transcript_path = artifact_dir / "transcript.txt"
    timing, timing_error = read_json_record(timing_path)
    objective, objective_error = read_json_record(objective_path)

    reasons: list[str] = []
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
        "apply_exit": apply_exit,
        "oracle_exit": oracle_exit,
        "valid": valid,
        "resolved": resolved,
        "outcome": "pass" if resolved is True else "fail" if valid else "INVALID",
        "attempt_invalid_reasons": reasons,
        "runtime_resolved_model": runtime_model(transcript_path),
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


def stage_and_evaluate_gold(task: str, gold_run_id: str) -> tuple[Path, int]:
    artifact_dir = RESULTS_ROOT / gold_run_id / task / "A1"
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
            "--arm-attempt",
            "A1",
        ]
    )
    return artifact_dir, completed.returncode


def run_live_attempt(
    task: str,
    run_id: str,
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
            "--attempt",
            str(attempt_number),
            "--timeout-seconds",
            str(timeout_seconds),
        ]
    )
    artifact_dir = RESULTS_ROOT / run_id / task / arm_attempt
    evaluator_exit: int | None = None
    if (artifact_dir / "patch.diff").is_file():
        evaluated = run_command(
            [
                str(EVALUATOR),
                "--run-id",
                run_id,
                "--task",
                task,
                "--arm-attempt",
                arm_attempt,
            ]
        )
        evaluator_exit = evaluated.returncode
    return artifact_dir, completed.returncode, evaluator_exit


def process_row(
    task: str,
    row: dict[str, Any],
    control: bool,
    hashes: dict[str, str],
    run_id: str,
    timeout_seconds: int,
    fixture_root: Path | None,
) -> dict[str, Any]:
    gold_run_id = f"{run_id}-gold"
    if fixture_root is None:
        gold_dir, gold_evaluator_exit = stage_and_evaluate_gold(task, gold_run_id)
    else:
        gold_dir = dry_gold_dir(fixture_root, run_id, task)
        gold_evaluator_exit = None
    gold = gold_record(gold_dir, gold_run_id, gold_evaluator_exit)

    attempts: list[dict[str, Any]] = []
    if not gold["resolved"]:
        return {
            "task": task,
            "categorical_class": (
                "positive-control" if control else row.get("categorical_class")
            ),
            "control": control,
            "hashes": hashes,
            "admitted": False,
            "gate_reason": "oracle-invalid",
            "gold_attempt": gold,
            "attempts": attempts,
            "valid_attempts": 0,
            "resolved_attempts": 0,
            "physical_attempts": 0,
        }

    physical_attempt = 0
    pending = False
    for slot in range(1, VALID_SLOTS + 1):
        slot_valid = False
        for retry_index in range(REPLACEMENTS_PER_SLOT + 1):
            physical_attempt += 1
            arm_attempt = f"B{physical_attempt}"
            if fixture_root is None:
                artifact_dir, runner_exit, evaluator_exit = run_live_attempt(
                    task, run_id, physical_attempt, timeout_seconds
                )
            else:
                artifact_dir = dry_attempt_dir(
                    fixture_root, run_id, task, arm_attempt
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
            )
            attempts.append(record)
            if record["valid"]:
                slot_valid = True
                break
        if not slot_valid:
            pending = True
            break

    valid_attempts = [attempt for attempt in attempts if attempt["valid"]]
    resolved_attempts = [
        attempt for attempt in valid_attempts if attempt["resolved"] is True
    ]
    categorical_class = (
        "positive-control" if control else str(row.get("categorical_class"))
    )
    if pending or len(valid_attempts) != VALID_SLOTS:
        admitted = False
        gate_reason = "INVALID/PENDING"
    elif resolved_attempts:
        admitted = False
        gate_reason = "saturated:bare-resolves"
    else:
        admitted = True
        gate_reason = f"admitted:{categorical_class}"

    return {
        "task": task,
        "categorical_class": categorical_class,
        "control": control,
        "hashes": hashes,
        "admitted": admitted,
        "gate_reason": gate_reason,
        "gold_attempt": gold,
        "attempts": attempts,
        "valid_attempts": len(valid_attempts),
        "resolved_attempts": len(resolved_attempts),
        "physical_attempts": len(attempts),
    }


def live_identity(run_id: str, captured_at: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["codex", "--version"],
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
    return {
        "cli_version": completed.stdout.strip(),
        "requested_alias": REQUESTED_ALIAS,
        "runtime_resolved_model": None,
        "run_id": run_id,
        "captured_at": captured_at,
    }


def dry_identity(fixture_root: Path, run_id: str, captured_at: str) -> dict[str, Any]:
    identity_path = fixture_root / "identity.json"
    identity = read_json(identity_path) if identity_path.is_file() else None
    if not isinstance(identity, dict):
        raise GateError(f"dry-run identity object missing: {identity_path}")
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
    return {
        "cli_version": cli_version.strip(),
        "requested_alias": REQUESTED_ALIAS,
        "runtime_resolved_model": resolved.strip() if resolved else None,
        "run_id": run_id,
        "captured_at": identity.get("captured_at", captured_at),
    }


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


def live_roots(run_id: str) -> list[Path]:
    gold_run_id = f"{run_id}-gold"
    return [
        RESULTS_ROOT / run_id,
        RESULTS_ROOT / gold_run_id,
        EXTERNAL_ROOT / "workspaces" / run_id,
        EXTERNAL_ROOT / "workspaces" / gold_run_id,
        EXTERNAL_ROOT / "eval" / run_id,
        EXTERNAL_ROOT / "eval" / gold_run_id,
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gate tranche3 candidates plus FS1 on one gold evaluation and "
            "exactly three valid bare-Codex outcomes."
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
    captured_at = utc_timestamp()
    identity = (
        dry_identity(fixture_root, args.run_id, captured_at)
        if fixture_root is not None
        else live_identity(args.run_id, captured_at)
    )

    results: list[dict[str, Any]] = []
    for task, row, control in rows:
        print(f"[corpus-gate] {task}: gold + bare-B gate", flush=True)
        result = process_row(
            task,
            row,
            control,
            verified_hashes[task],
            args.run_id,
            args.timeout_seconds,
            fixture_root,
        )
        results.append(result)
        print(
            f"[corpus-gate] {task}: {result['gate_reason']} "
            f"valid={result['valid_attempts']} resolved={result['resolved_attempts']}",
            flush=True,
        )

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
            "gold reference resolves once and bare Codex has exactly three "
            "valid attempts with zero resolves"
        ),
        "cohort_identity": {
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
