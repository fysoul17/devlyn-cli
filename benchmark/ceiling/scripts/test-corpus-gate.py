#!/usr/bin/env python3
"""Deterministic, isolated self-test for corpus-gate.py."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


GATE_SOURCE = Path(__file__).resolve().with_name("corpus-gate.py")
CONTROL_TASK = "FS1-schedule-max-runs"
EXPECTED_ASSERTIONS = 43
EXTERNAL_ROOT = Path.home() / ".local/share/nx01"
FROZEN_ENV_KEYS = sorted(
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


class SelfTestFailure(RuntimeError):
    """A self-test assertion failed."""


class Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise SelfTestFailure(message)
        self.count += 1


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_isolated_gate(root: Path) -> tuple[Path, Path]:
    ceiling_root = root / "benchmark" / "ceiling"
    scripts_root = ceiling_root / "scripts"
    scripts_root.mkdir(parents=True)
    gate = scripts_root / "corpus-gate.py"
    shutil.copyfile(GATE_SOURCE, gate)
    return gate, ceiling_root / "corpus"


def create_corpus_row(
    corpus_root: Path,
    task: str,
    categorical_class: str,
    *,
    candidate: bool,
) -> dict[str, Any]:
    task_root = corpus_root / task
    task_root.mkdir(parents=True)
    repo = f"synthetic://{task}"
    base_sha = hashlib.sha256(task.encode("utf-8")).hexdigest()[:40]
    base_path = task_root / "base.json"
    task_path = task_root / "task.txt"
    write_json(base_path, {"repo": repo, "sha": base_sha})
    task_path.write_text(f"Synthetic task for {task}.\n", encoding="utf-8")
    row: dict[str, Any] = {
        "repo": repo,
        "sha": base_sha,
        "base_sha256": sha256(base_path),
        "task_sha256": sha256(task_path),
        "categorical_class": categorical_class,
    }
    if candidate:
        row["candidate"] = True
    return row


def manifest_for(
    rows: dict[str, dict[str, Any]], control_row: dict[str, Any]
) -> dict[str, Any]:
    return {
        "tasks": {CONTROL_TASK: copy.deepcopy(control_row)},
        "tranche3": {
            "status": "prepared",
            "tasks": copy.deepcopy(rows),
        },
    }


def write_objective(path: Path, oracle_exit: int, resolved: bool) -> None:
    write_json(
        path,
        {"apply_exit": 0, "oracle_exit": oracle_exit, "resolved": resolved},
    )


def write_isolation(path: Path, task: str, worktree: str, transcript: str) -> None:
    transcript_bytes = transcript.encode()
    write_json(
        path,
        {
            "schema_version": 2,
            "opaque_paths": {
                "external_root": str(EXTERNAL_ROOT),
                "opaque_run_id": "r0001",
                "opaque_task_id": "fx01",
                "generated": [
                    worktree,
                    str(EXTERNAL_ROOT / "x/r0001/fx01/B1"),
                    str(EXTERNAL_ROOT / "h/r0001/fx01/B1"),
                    str(EXTERNAL_ROOT / "d/r0001/fx01/B1"),
                ],
                "passed": True,
            },
            "environment": {
                "keys": FROZEN_ENV_KEYS,
                "keys_sha256": hashlib.sha256(
                    "\n".join(FROZEN_ENV_KEYS).encode()
                ).hexdigest(),
                "forbidden_values_absent": True,
            },
            "shell_startup_canary": {
                "passed": True,
                "stdout_sha256": hashlib.sha256(b"isolation-ok").hexdigest(),
                "stderr_sha256": hashlib.sha256(b"").hexdigest(),
                "host_startup_files_absent": True,
            },
            "neutralization": {
                "schema_version": 1,
                "seed_derived": task.startswith("DR-"),
                "neutralization_diff_sha256": "0" * 64,
                "neutral_baseline_sha": "0" * 40,
                "git_remotes": [],
                "git_reflogs": [],
            },
            "git": {
                "neutral_baseline_sha": "0" * 40,
                "remotes": [],
                "reflogs": [],
            },
            "direct_codex": {
                "path": "/usr/bin/true",
                "version": "codex-cli selftest",
                "superset_wrapper": False,
            },
            "auth": {
                "path": str(EXTERNAL_ROOT / "d/r0001/fx01/B1/auth.json"),
                "is_symlink": False,
                "mode": "0600",
            },
            "forbidden_transcript_scan": {
                "passed": True,
                "transcript_sha256": hashlib.sha256(transcript_bytes).hexdigest(),
                "hits": [],
            },
        },
    )


def create_gold(fixtures: Path, task: str, *, resolved: bool) -> None:
    gold = fixtures / task / "gold"
    gold.mkdir(parents=True)
    write_objective(gold / "objective.json", 0 if resolved else 1, resolved)
    (gold / "patch.diff").write_text("synthetic gold patch\n", encoding="utf-8")


def create_attempt(fixtures: Path, task: str, number: int, kind: str) -> None:
    attempt = fixtures / task / f"B{number}"
    attempt.mkdir(parents=True)
    timed_out = kind == "timed-out"
    worktree = str(EXTERNAL_ROOT / f"w/r0001/fx01/B{number}/repo")
    write_json(
        attempt / "timing.json",
        {
            "invoke_exit": 0,
            "timed_out": timed_out,
            "worktree": worktree,
        },
    )
    if kind == "pass":
        write_objective(attempt / "objective.json", 0, True)
    elif kind == "oracle-101":
        write_objective(attempt / "objective.json", 101, False)
    else:
        write_objective(attempt / "objective.json", 1, False)
    (attempt / "patch.diff").write_text("", encoding="utf-8")
    transcript = "model: gpt-5.6-terra\n"
    (attempt / "transcript.txt").write_text(transcript, encoding="utf-8")
    write_isolation(attempt / "isolation.json", task, worktree, transcript)


def bare_attempt_record(
    gate_module: dict[str, Any],
    artifact_dir: Path,
    transcript: str | None,
    *,
    worktree: str = str(EXTERNAL_ROOT / "w/r0001/fx01/B1/repo"),
    task: str = "DR-selftest",
) -> dict[str, Any]:
    artifact_dir.mkdir(parents=True)
    write_json(
        artifact_dir / "timing.json",
        {"invoke_exit": 0, "timed_out": False, "worktree": worktree},
    )
    write_objective(artifact_dir / "objective.json", 1, False)
    (artifact_dir / "patch.diff").write_text("", encoding="utf-8")
    if transcript is not None:
        (artifact_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
        write_isolation(
            artifact_dir / "isolation.json", task, worktree, transcript
        )
    return gate_module["attempt_record"](
        artifact_dir,
        "B1",
        1,
        0,
        None,
        None,
        "selftest-run",
        task,
    )


def create_fixture_row(
    fixtures: Path,
    task: str,
    attempts: list[str],
    *,
    gold_resolved: bool = True,
) -> None:
    create_gold(fixtures, task, resolved=gold_resolved)
    for number, kind in enumerate(attempts, start=1):
        create_attempt(fixtures, task, number, kind)


def completed_detail(completed: subprocess.CompletedProcess[str]) -> str:
    return (
        f"exit={completed.returncode}\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


def run_gate(
    gate: Path,
    manifest: Path,
    run_id: str,
    *,
    fixtures: Path | None,
    disable_path: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(gate)]
    if fixtures is not None:
        command.extend(["--dry-run", str(fixtures)])
    command.extend(["--manifest", str(manifest), "--run-id", run_id])
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if disable_path:
        environment["PATH"] = ""
    return subprocess.run(
        command,
        cwd=gate.parent,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    checks = Checks()
    with tempfile.TemporaryDirectory(prefix="corpus-gate-selftest-") as temporary:
        root = Path(temporary)
        gate, corpus_root = install_isolated_gate(root)
        gate_module = runpy.run_path(str(gate))
        fixtures = root / "fixtures"
        write_json(
            fixtures / "identity.json",
            {
                "runner_commit_sha": "a" * 40,
                "bare": {
                    "cli_version": "codex-cli selftest",
                    "runtime_resolved_model": "gpt-5.6-terra",
                    "captured_at": "2026-07-10T00:00:00Z",
                }
            },
        )

        task_names = {
            "admit": "DR-admit",
            "saturated": "DR-saturated",
            "expanded_resolve": "DR-expanded-resolve",
            "oracle_retry": "DR-oracle-retry",
            "timeout_retry": "DR-timeout-retry",
            "exhausted": "DR-exhausted",
            "gold_fail": "DR-gold-fail",
        }
        rows = {
            name: create_corpus_row(
                corpus_root,
                name,
                f"class-{key}",
                candidate=True,
            )
            for key, name in task_names.items()
        }
        control_row = create_corpus_row(
            corpus_root,
            CONTROL_TASK,
            "positive-control",
            candidate=False,
        )

        create_fixture_row(fixtures, task_names["admit"], ["fail", "fail", "fail"])
        create_fixture_row(fixtures, task_names["saturated"], ["pass"])
        create_fixture_row(
            fixtures, task_names["expanded_resolve"], ["fail", "pass", "fail"]
        )
        create_fixture_row(
            fixtures,
            task_names["oracle_retry"],
            ["oracle-101", "fail", "fail", "fail"],
        )
        create_fixture_row(
            fixtures,
            task_names["timeout_retry"],
            ["timed-out", "fail", "fail", "fail"],
        )
        create_fixture_row(
            fixtures,
            task_names["exhausted"],
            ["oracle-101", "oracle-101", "oracle-101"],
        )
        create_fixture_row(
            fixtures,
            task_names["gold_fail"],
            [],
            gold_resolved=False,
        )
        create_fixture_row(fixtures, CONTROL_TASK, ["pass", "fail", "fail"])

        attempt_fixtures = root / "attempt-fixtures"
        clean = bare_attempt_record(
            gate_module,
            attempt_fixtures / "clean",
            "model: gpt-5.6-terra\nworkdir: "
            + str(EXTERNAL_ROOT / "w/r0001/fx01/B1/repo")
            + "\n// TODO(devlyn): preserve this task byte exactly.\n",
        )
        checks.require(
            clean["valid"] is True,
            "clean transcript or legal TODO(devlyn) bait was rejected",
        )

        host_startup = bare_attempt_record(
            gate_module,
            attempt_fixtures / "host-startup",
            "model: gpt-5.6-terra\n/Users/aipalm/.zshenv:35: leaked\n",
        )
        checks.require(
            "bare-context-contaminated:host-shell-startup-leak"
            in host_startup["attempt_invalid_reasons"],
            "host shell startup contamination was not rejected",
        )

        benchmark_identity = bare_attempt_record(
            gate_module,
            attempt_fixtures / "benchmark-identity",
            "model: gpt-5.6-terra\nworkdir: /tmp/r1/DR-hidden-trap/B1\n",
        )
        checks.require(
            "bare-context-contaminated:benchmark-identity"
            in benchmark_identity["attempt_invalid_reasons"],
            "structured benchmark identity contamination was not rejected",
        )

        invalid_isolation_dir = attempt_fixtures / "invalid-isolation"
        bare_attempt_record(
            gate_module,
            invalid_isolation_dir,
            "model: gpt-5.6-terra\n",
        )
        invalid_isolation = read_json(invalid_isolation_dir / "isolation.json")
        invalid_isolation["environment"]["keys"] = ["PATH"]
        write_json(invalid_isolation_dir / "isolation.json", invalid_isolation)
        invalid_isolation_record = gate_module["attempt_record"](
            invalid_isolation_dir,
            "B1",
            1,
            0,
            None,
            None,
            "selftest-run",
            "DR-selftest",
        )
        checks.require(
            invalid_isolation_record["valid"] is False
            and "isolation-environment"
            in invalid_isolation_record["attempt_invalid_reasons"],
            "malformed isolation attestation was not rejected",
        )

        skill_load = bare_attempt_record(
            gate_module,
            attempt_fixtures / "skill-load",
            "model: gpt-5.6-terra\nERROR codex_core::session::session: failed "
            "to load skill /Users/x/.agents/skills/foo/SKILL.md\n",
        )
        checks.require(
            skill_load["valid"] is False
            and "bare-context-contaminated:global-skills-path"
            in skill_load["attempt_invalid_reasons"],
            "global skill-load contamination was not rejected",
        )

        skill_read = bare_attempt_record(
            gate_module,
            attempt_fixtures / "skill-read",
            "model: gpt-5.6-terra\nsed -n '1,240p' "
            "/Users/x/.agents/skills/devlyn:resolve/SKILL.md\n",
        )
        checks.require(
            skill_read["valid"] is False
            and skill_read["attempt_invalid_reasons"][0]
            == "bare-context-contaminated:global-skills-path",
            "skill-read contamination did not name the first matching marker",
        )

        missing_transcript = bare_attempt_record(
            gate_module,
            attempt_fixtures / "missing-transcript",
            None,
        )
        empty_transcript = bare_attempt_record(
            gate_module,
            attempt_fixtures / "empty-transcript",
            "",
        )
        checks.require(
            all(
                record["valid"] is False
                and "transcript-missing" in record["attempt_invalid_reasons"]
                for record in (missing_transcript, empty_transcript)
            ),
            "missing or empty transcript was not rejected",
        )

        repo_worktree = bare_attempt_record(
            gate_module,
            attempt_fixtures / "repo-worktree",
            "model: gpt-5.6-terra\n",
            worktree=str(root / "benchmark-worktree"),
        )
        checks.require(
            repo_worktree["valid"] is False
            and "worktree-in-repo" in repo_worktree["attempt_invalid_reasons"],
            "in-repo worktree was not rejected",
        )

        wrong_model = bare_attempt_record(
            gate_module,
            attempt_fixtures / "wrong-model",
            "model: gpt-5.6-sol\n",
        )
        checks.require(
            wrong_model["valid"] is False
            and "runtime-model-mismatch" in wrong_model["attempt_invalid_reasons"],
            "wrong runtime model was not rejected",
        )

        headerless_model = bare_attempt_record(
            gate_module,
            attempt_fixtures / "headerless-model",
            "no codex header in this transcript\n",
        )
        checks.require(
            headerless_model["valid"] is False
            and "runtime-model-missing"
            in headerless_model["attempt_invalid_reasons"],
            "transcript without a model header was not rejected",
        )

        manifests = root / "manifests"
        manifests.mkdir()

        happy_rows = {
            task: rows[task]
            for task in (
                task_names["admit"],
                task_names["saturated"],
                task_names["expanded_resolve"],
                task_names["oracle_retry"],
                task_names["timeout_retry"],
            )
        }
        happy_path = manifests / "happy.json"
        happy_input = manifest_for(happy_rows, control_row)
        control_before = copy.deepcopy(happy_input["tasks"][CONTROL_TASK])
        write_json(happy_path, happy_input)
        happy_run = run_gate(
            gate,
            happy_path,
            "selftest-happy",
            fixtures=fixtures,
        )
        checks.require(
            happy_run.returncode == 0,
            "happy cohort did not freeze\n" + completed_detail(happy_run),
        )
        happy = read_json(happy_path)
        summary = happy["tranche3"]["discriminating"]
        checks.require(
            happy["tranche3"]["status"] == "frozen" and summary["frozen"] is True,
            "happy cohort did not record frozen status",
        )
        admit = summary["rows"][task_names["admit"]]
        checks.require(
            admit["admitted"] is True
            and admit["valid_attempts"] == 3
            and admit["resolved_attempts"] == 0,
            "0/3 valid bare failures were not admitted",
        )
        saturated = summary["rows"][task_names["saturated"]]
        checks.require(
            saturated["gate_reason"] == "saturated:bare-resolves"
            and saturated["valid_attempts"] == 1
            and saturated["resolved_attempts"] == 1,
            "initial resolving attempt did not saturate the row immediately",
        )
        expanded = summary["rows"][task_names["expanded_resolve"]]
        checks.require(
            expanded["gate_reason"] == "saturated:bare-resolves"
            and expanded["valid_attempts"] == 3
            and expanded["physical_attempts"] == 3,
            "initial failure did not expand to exactly three valid attempts",
        )
        oracle_retry_attempts = happy["tranche3"]["tasks"][
            task_names["oracle_retry"]
        ]["attempts"]
        checks.require(
            oracle_retry_attempts[0]["oracle_exit"] == 101
            and oracle_retry_attempts[0]["valid"] is False
            and oracle_retry_attempts[1]["slot"] == 1
            and oracle_retry_attempts[1]["retry_index"] == 1
            and oracle_retry_attempts[1]["valid"] is True,
            "oracle_exit=101 attempt was not replaced in its slot",
        )
        oracle_retry = summary["rows"][task_names["oracle_retry"]]
        checks.require(
            oracle_retry["physical_attempts"] == 4
            and oracle_retry["valid_attempts"] == 3
            and oracle_retry["admitted"] is True,
            "oracle-runtime replacement did not yield three valid attempts",
        )
        timeout_attempts = happy["tranche3"]["tasks"][
            task_names["timeout_retry"]
        ]["attempts"]
        checks.require(
            "timed-out" in timeout_attempts[0]["attempt_invalid_reasons"]
            and timeout_attempts[0]["valid"] is False
            and timeout_attempts[1]["slot"] == 1
            and timeout_attempts[1]["retry_index"] == 1
            and timeout_attempts[1]["valid"] is True,
            "timed-out attempt was not replaced in its slot",
        )
        timeout_retry = summary["rows"][task_names["timeout_retry"]]
        checks.require(
            timeout_retry["physical_attempts"] == 4
            and timeout_retry["valid_attempts"] == 3
            and timeout_retry["admitted"] is True,
            "timeout replacement did not yield three valid attempts",
        )
        expected_admitted = [
            task_names["admit"],
            task_names["oracle_retry"],
            task_names["timeout_retry"],
        ]
        expected_saturated = [
            task_names["saturated"],
            task_names["expanded_resolve"],
            CONTROL_TASK,
        ]
        checks.require(
            summary["admitted_amplification_rows"] == expected_admitted,
            "amplification rows were not recorded separately",
        )
        checks.require(
            summary["saturated_no_degradation_controls"] == expected_saturated,
            "saturated no-degradation controls were not recorded separately",
        )
        checks.require(
            set(summary["admitted_amplification_rows"]).isdisjoint(
                summary["saturated_no_degradation_controls"]
            ),
            "admitted and saturated cohorts overlap",
        )
        checks.require(
            happy["tasks"][CONTROL_TASK] == control_before,
            "FS1 top-level record was mutated",
        )
        positive_control = summary["positive_control"]
        checks.require(
            positive_control["passed"] is True
            and positive_control["gate_reason"] == "saturated:bare-resolves",
            "FS1 bare-pass positive control was not rejected",
        )
        checks.require(
            positive_control["valid_attempts"] == 1
            and positive_control["physical_attempts"] == 1,
            "FS1 positive control did not stop after one valid attempt",
        )
        checks.require(
            all(
                happy["tranche3"]["tasks"][task]["frozen"]
                for task in expected_admitted
            )
            and happy["tranche3"]["tasks"][task_names["saturated"]]["frozen"]
            is False,
            "per-row frozen flags do not match admission",
        )
        checks.require(
            summary["observed_runtime_models"] == ["gpt-5.6-terra"]
            and summary["cohort_drift_observed"] is False,
            "synthetic cohort identity was not stable",
        )
        checks.require(
            summary["cohort_identity"]["runner_commit_sha"] == "a" * 40
            and summary["cohort_identity"]["bare_codex"]["requested_alias"]
            == "gpt-5.6-terra",
            "runner commit or requested model provenance was not recorded",
        )

        pending_path = manifests / "pending.json"
        write_json(
            pending_path,
            manifest_for(
                {task_names["exhausted"]: rows[task_names["exhausted"]]},
                control_row,
            ),
        )
        pending_run = run_gate(
            gate,
            pending_path,
            "selftest-pending",
            fixtures=fixtures,
        )
        pending = read_json(pending_path)
        pending_summary = pending["tranche3"]["discriminating"]
        checks.require(
            pending_run.returncode == 1
            and pending["tranche3"]["status"] == "INVALID/PENDING",
            "exhausted cohort did not exit 1 as INVALID/PENDING\n"
            + completed_detail(pending_run),
        )
        exhausted = pending_summary["rows"][task_names["exhausted"]]
        checks.require(
            exhausted["gate_reason"] == "INVALID/PENDING"
            and pending_summary["pending"] == [task_names["exhausted"]],
            "exhausted row was not placed in pending",
        )
        exhausted_attempts = pending["tranche3"]["tasks"][
            task_names["exhausted"]
        ]["attempts"]
        checks.require(
            exhausted["physical_attempts"] == 3
            and exhausted["valid_attempts"] == 0
            and [attempt["retry_index"] for attempt in exhausted_attempts]
            == [0, 1, 2],
            "more than two replacements did not exhaust the slot",
        )
        checks.require(
            pending["tranche3"]["tasks"][task_names["exhausted"]]["admitted"]
            is False
            and pending["tranche3"]["tasks"][task_names["exhausted"]]["frozen"]
            is False,
            "exhausted row was admitted or frozen",
        )

        gold_path = manifests / "gold-invalid.json"
        write_json(
            gold_path,
            manifest_for(
                {task_names["gold_fail"]: rows[task_names["gold_fail"]]},
                control_row,
            ),
        )
        gold_run = run_gate(
            gate,
            gold_path,
            "selftest-gold-invalid",
            fixtures=fixtures,
        )
        gold_manifest = read_json(gold_path)
        gold_summary = gold_manifest["tranche3"]["discriminating"]
        checks.require(
            gold_run.returncode == 1
            and gold_manifest["tranche3"]["status"] == "INVALID-oracle",
            "gold failure did not exit 1 as INVALID-oracle\n"
            + completed_detail(gold_run),
        )
        gold_row = gold_manifest["tranche3"]["tasks"][task_names["gold_fail"]]
        checks.require(
            gold_row["gate_reason"] == "oracle-invalid"
            and gold_row["attempts"] == [],
            "gold-failing row was not rejected before bare attempts",
        )
        checks.require(
            gold_summary["oracle_invalid"] == [task_names["gold_fail"]],
            "oracle-invalid summary omitted the gold-failing row",
        )

        control_failure_fixtures = root / "control-failure-fixtures"
        write_json(
            control_failure_fixtures / "identity.json",
            {
                "runner_commit_sha": "a" * 40,
                "bare": {
                    "cli_version": "codex-cli selftest",
                    "runtime_resolved_model": "gpt-5.6-terra",
                }
            },
        )
        create_fixture_row(
            control_failure_fixtures,
            task_names["admit"],
            ["fail", "fail", "fail"],
        )
        create_fixture_row(
            control_failure_fixtures,
            CONTROL_TASK,
            ["fail", "fail", "fail"],
        )
        control_failure_path = manifests / "control-failure.json"
        control_failure_input = manifest_for(
            {task_names["admit"]: rows[task_names["admit"]]}, control_row
        )
        write_json(control_failure_path, control_failure_input)
        control_failure_run = run_gate(
            gate,
            control_failure_path,
            "selftest-control-failure",
            fixtures=control_failure_fixtures,
        )
        control_failure = read_json(control_failure_path)
        control_failure_summary = control_failure["tranche3"]["discriminating"]
        checks.require(
            control_failure_run.returncode == 1
            and control_failure["tranche3"]["status"] == "INVALID-positive-control",
            "FS1 0/3 did not invalidate the cohort\n"
            + completed_detail(control_failure_run),
        )
        checks.require(
            control_failure_summary["positive_control"]["passed"] is False
            and control_failure_summary["positive_control"]["gate_reason"]
            == "control-invalid:bare-fails"
            and control_failure_summary["positive_control"]["valid_attempts"] == 1,
            "FS1 control-failure was not detected",
        )
        checks.require(
            control_failure["tasks"][CONTROL_TASK]
            == control_failure_input["tasks"][CONTROL_TASK]
            and CONTROL_TASK
            not in control_failure_summary["admitted_amplification_rows"],
            "failed FS1 control mutated or leaked into amplification rows",
        )

        stale_path = manifests / "stale-hash.json"
        stale_manifest = manifest_for(
            {task_names["admit"]: rows[task_names["admit"]]}, control_row
        )
        stale_manifest["tranche3"]["tasks"][task_names["admit"]][
            "task_sha256"
        ] = "0" * 64
        write_json(stale_path, stale_manifest)
        stale_before = stale_path.read_bytes()
        stale_run = run_gate(
            gate,
            stale_path,
            "selftest-stale-hash",
            fixtures=fixtures,
        )
        checks.require(
            stale_run.returncode == 2
            and "artifact integrity mismatch" in stale_run.stderr
            and "task_sha256" in stale_run.stderr,
            "stale hash did not fail closed with exit 2\n"
            + completed_detail(stale_run),
        )
        checks.require(
            stale_path.read_bytes() == stale_before,
            "stale-hash failure mutated the manifest copy",
        )

        missing_base_path = manifests / "missing-base-hash.json"
        missing_base = manifest_for(
            {task_names["admit"]: rows[task_names["admit"]]}, control_row
        )
        del missing_base["tranche3"]["tasks"][task_names["admit"]][
            "base_sha256"
        ]
        write_json(missing_base_path, missing_base)
        missing_base_run = run_gate(
            gate,
            missing_base_path,
            "selftest-missing-base-hash",
            fixtures=fixtures,
        )
        checks.require(
            missing_base_run.returncode == 2
            and "base_sha256" in missing_base_run.stderr
            and "actual='missing'" in missing_base_run.stderr,
            "missing base_sha256 did not fail closed\n"
            + completed_detail(missing_base_run),
        )

        frozen_path = manifests / "frozen.json"
        frozen_manifest = manifest_for(
            {task_names["admit"]: rows[task_names["admit"]]}, control_row
        )
        frozen_manifest["tranche3"]["status"] = "frozen"
        write_json(frozen_path, frozen_manifest)
        frozen_run = run_gate(
            gate,
            frozen_path,
            "selftest-frozen-rerun",
            fixtures=None,
            disable_path=True,
        )
        checks.require(
            frozen_run.returncode == 2
            and "refuses already frozen manifest tranche3" in frozen_run.stderr,
            "frozen live rerun was not refused before Codex invocation\n"
            + completed_detail(frozen_run),
        )

        isolated_real_manifest = corpus_root / "manifest.json"
        write_json(isolated_real_manifest, happy_input)
        real_manifest_run = run_gate(
            gate,
            isolated_real_manifest,
            "selftest-real-manifest-refusal",
            fixtures=fixtures,
        )
        checks.require(
            real_manifest_run.returncode == 2
            and "--dry-run refuses the real corpus manifest"
            in real_manifest_run.stderr,
            "dry-run accepted its isolated real manifest path\n"
            + completed_detail(real_manifest_run),
        )

    if checks.count != EXPECTED_ASSERTIONS:
        raise SelfTestFailure(
            f"internal assertion count mismatch: "
            f"expected {EXPECTED_ASSERTIONS}, got {checks.count}"
        )
    print(f"SELFTEST PASS: {checks.count} assertions")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SelfTestFailure as exc:
        print(f"SELFTEST FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
