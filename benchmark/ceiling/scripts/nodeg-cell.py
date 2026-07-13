#!/usr/bin/env python3
"""Fail-closed support for the iter-0068 no-degradation control cell."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


WALL_CAP = 3.0
AXES = (
    "design_coherence",
    "robustness",
    "spec_long_horizon_consistency",
    "maintainability_api_ergonomics",
)
CONTROL_ORDER = ("F7", "F25", "F26", "F11", "F12", "F23", "FS1")
EXCLUDED_UNFAIR = ("F21",)
FROZEN = {
    "F7": ("DR-byte-preservation-f7-out-of-scope-trap", "iter0068-gate-20260711h", "B1"),
    "F25": ("DR-shape-compound-rules-f25-cart", "iter0068-gate-20260711h", "B1"),
    "F26": ("DR-ledger-rounding-consistency-f26-payout", "iter0068-gate-20260711h", "B1"),
    "F11": ("DR-atomic-state-f11-batch-import", "iter0068-gate-20260711h", "B1"),
    "F12": ("DR-auth-signature-f12-webhook", "iter0068-f12supp2-20260712", "B1"),
    "F23": ("DR-allocation-fefo-priority-rollback-f23-fulfillment", "iter0068-gate-20260711h", "B1"),
    "FS1": ("FS1-schedule-max-runs", "iter0068-gate-20260711h", "B1"),
}


def die(message: str) -> None:
    raise SystemExit(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        die(f"invalid JSON artifact {path}: {exc}")
    if not isinstance(value, dict):
        die(f"JSON artifact must be an object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        die(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def validate_run_id(run_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id):
        die("--run-id must match ^[A-Za-z0-9][A-Za-z0-9._-]*$")


def selected_controls(tasks_csv: str | None) -> list[str]:
    if not tasks_csv:
        return list(CONTROL_ORDER)
    aliases = {task: control for control, (task, _, _) in FROZEN.items()}
    selected: list[str] = []
    for raw in tasks_csv.split(","):
        value = raw.strip()
        control = value if value in FROZEN else aliases.get(value)
        if control is None:
            die(f"invalid --tasks entry {value!r}; valid controls: {', '.join(CONTROL_ORDER)}")
        if control in selected:
            die(f"duplicate --tasks entry resolves to {control}")
        selected.append(control)
    if not selected:
        die("--tasks must select at least one control")
    return selected


def dirty_paths(repo: Path) -> list[str]:
    output = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    paths: list[str] = []
    for line in output.splitlines():
        value = line[3:]
        if " -> " in value:
            value = value.split(" -> ", 1)[1]
        paths.append(value.strip('"'))
    return paths


def require_runner_integrity(repo: Path, ceiling_root: Path, run_id: str, resume: bool) -> str:
    sha = git(repo, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
        die(f"invalid runner commit SHA: {sha!r}")
    dirty = dirty_paths(repo)
    if resume:
        allowed = f"{ceiling_root.relative_to(repo).as_posix()}/results/{run_id}/"
        dirty = [path for path in dirty if not path.startswith(allowed)]
    if dirty:
        die("runner worktree is dirty; commit or remove changes before the cell: " + ", ".join(dirty))
    return sha


def frozen_source(ceiling_root: Path, control: str) -> dict[str, Any]:
    task, run_id, attempt = FROZEN[control]
    attempt_dir = ceiling_root / "results" / run_id / task / attempt
    required = {
        "patch": attempt_dir / "patch.diff",
        "objective": attempt_dir / "objective.json",
        "timing": attempt_dir / "timing.json",
        "isolation": attempt_dir / "isolation.json",
    }
    missing = [f"{name}={path}" for name, path in required.items() if not path.is_file()]
    if missing:
        die(f"{control} frozen-B pointer missing artifacts: {', '.join(missing)}")
    objective = load_json(required["objective"])
    timing = load_json(required["timing"])
    isolation = load_json(required["isolation"])
    if objective.get("resolved") is not True:
        die(f"{control} frozen-B pointer is not resolved: {required['objective']}")
    if (
        timing.get("invoke_exit") != 0
        or timing.get("timed_out") is not False
        or not isinstance(timing.get("elapsed_seconds"), (int, float))
        or timing["elapsed_seconds"] <= 0
    ):
        die(f"{control} frozen-B timing is not a successful bounded attempt: {required['timing']}")
    if isolation.get("opaque_paths", {}).get("passed") is not True:
        die(f"{control} frozen-B opaque-path attestation did not pass: {required['isolation']}")
    if not (ceiling_root / "corpus" / task / "task.txt").is_file():
        die(f"{control} corpus task is missing: {ceiling_root / 'corpus' / task / 'task.txt'}")
    return {
        "control_id": control,
        "task": task,
        "run_id": run_id,
        "attempt": attempt,
        "attempt_dir": str(attempt_dir.resolve()),
        "patch_path": str(required["patch"].resolve()),
        "patch_sha256": sha256(required["patch"]),
        "objective_path": str(required["objective"].resolve()),
        "objective_sha256": sha256(required["objective"]),
        "timing_path": str(required["timing"].resolve()),
        "timing_sha256": sha256(required["timing"]),
        "resolved": True,
        "elapsed_seconds": timing["elapsed_seconds"],
    }


def cohort_payload(
    run_id: str,
    runner_sha: str,
    controls: list[str],
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "cell_owner": "iter-0068",
        "run_id": run_id,
        "runner_commit_sha": runner_sha,
        "registered_controls": list(CONTROL_ORDER),
        "selected_controls": controls,
        "selected_tasks": [FROZEN[control][0] for control in controls],
        "excluded_unfair": list(EXCLUDED_UNFAIR),
        "frozen_best_b_selection_rule": "objective-first lexicographic: resolve, violations, wall",
        "frozen_b_sources": [sources[control] for control in controls],
        "wall_cap": {
            "a_to_frozen_b_ratio": WALL_CAP,
            "source": "autoresearch/NORTH-STAR.md:254",
            "quoted_line": "average pair/solo wall ratio 1.73x under the 3.0 cap",
        },
    }


def preflight(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    ceiling_root = Path(args.ceiling_root).resolve()
    controls = selected_controls(args.tasks)
    runner_sha = require_runner_integrity(repo, ceiling_root, args.run_id, args.resume)
    sources = {control: frozen_source(ceiling_root, control) for control in controls}
    if args.initialize:
        run_root = ceiling_root / "results" / args.run_id
        cohort = run_root / "nodeg-cohort.json"
        if run_root.exists() and not args.resume:
            die(f"run directory already exists; use --resume only for the same run: {run_root}")
        if run_root.exists() and args.resume and not cohort.is_file():
            die(f"resume run is missing nodeg-cohort.json: {run_root}")
        if cohort.is_file():
            previous = load_json(cohort)
            if previous != cohort_payload(args.run_id, runner_sha, controls, sources):
                die(f"resume cohort identity mismatch: {cohort}")
        else:
            run_root.mkdir(parents=True, exist_ok=True)
            cohort.write_text(
                json.dumps(cohort_payload(args.run_id, runner_sha, controls, sources), indent=2) + "\n",
                encoding="utf-8",
            )
    for control in controls:
        print(FROZEN[control][0])
    return 0


def load_judge_module(script_dir: Path) -> dict[str, Any]:
    path = script_dir / "ceiling-judge.py"
    spec = importlib.util.spec_from_file_location("ceiling_judge", path)
    if spec is None or spec.loader is None:
        die(f"cannot load judge module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    namespace = vars(module)
    namespace["PACKETS"] = {"P1", "P2"}
    namespace["validate_response"] = validate_pair_response
    return namespace


def validate_pair_response(parsed: Any) -> str | None:
    if not isinstance(parsed, dict) or not isinstance(parsed.get("axes"), dict):
        return "missing axes object"
    for axis in AXES:
        row = parsed["axes"].get(axis)
        if not isinstance(row, dict):
            return f"missing axis {axis}"
        tiers = row.get("tiers")
        if not isinstance(tiers, list) or not tiers or any(not isinstance(tier, list) or not tier for tier in tiers):
            return f"{axis}: tiers must be non-empty lists"
        seen = [label for tier in tiers for label in tier]
        if sorted(seen) != ["P1", "P2"]:
            return f"{axis}: tiers must contain P1/P2 exactly once"
        strict_pairs = {
            (winner, loser)
            for index, tier in enumerate(tiers)
            for later in tiers[index + 1 :]
            for winner in tier
            for loser in later
        }
        deltas = row.get("strict_win_deltas")
        if not isinstance(deltas, list):
            return f"{axis}: strict_win_deltas must be a list"
        covered: set[tuple[str, str]] = set()
        for delta in deltas:
            if not isinstance(delta, dict):
                return f"{axis}: delta entries must be objects"
            pair = (delta.get("winner"), delta.get("loser"))
            if pair not in strict_pairs:
                return f"{axis}: delta {pair!r} is not a strict tier win"
            if not isinstance(delta.get("delta"), str) or len(delta["delta"].strip().split()) < 3:
                return f"{axis}: delta for {pair!r} must be a concrete sentence"
            covered.add(pair)
        if covered != strict_pairs:
            return f"{axis}: strict-win deltas do not match tiers"
    return None


def pair_prompt(task_text: str, packets: list[dict[str, str]]) -> str:
    blocks = [f"{packet['label']} patch.diff:\n```diff\n{packet['patch']}\n```" for packet in packets]
    example_axes = ",".join(
        f'"{axis}":{{"tiers":[["P1"],["P2"]],"strict_win_deltas":[{{"winner":"P1","loser":"P2","delta":"<one concrete sentence citing something visible in the diffs>"}}]}}'
        for axis in AXES
    )
    return (
        "You are a blind ceiling-quality judge. You receive one task and two anonymized candidate patches. "
        "Do not infer or mention model, arm, attempt, harness, source run, or author identity; judge only the task text and diffs.\n\n"
        f"Task text:\n{task_text}\n\n"
        + "\n\n".join(blocks)
        + "\n\nRank P1/P2 on exactly these axes: "
        + ", ".join(AXES)
        + ". Ties are allowed. Emit one single complete JSON object and nothing else in this shape; "
        "for every strict tier winner/loser include one concrete visible-diff delta:\n"
        + '{"axes":{'
        + example_axes
        + "}}"
    )


@contextmanager
def isolated_codex_home(script_dir: Path, run_id: str, task: str) -> Iterator[tuple[Path, list[str]]]:
    isolation = load_script(script_dir / "claude-isolation.py")
    explicit = os.environ.get("CEILING_TEST_CODEX_BIN")
    binary = Path(isolation["resolve_direct_binary"]("codex", explicit)).resolve()
    external = Path(os.environ.get("CEILING_EXTERNAL_ROOT", Path.home() / ".local/share/nx01"))
    opaque = hashlib.sha256(f"{run_id}:{task}".encode()).hexdigest()[:12]
    home = external / "nodeg-judge-homes" / opaque
    shutil.rmtree(home, ignore_errors=True)
    (home / "codex").mkdir(parents=True)
    (home / "codex/config.toml").write_text(
        'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "xhigh"\n', encoding="utf-8"
    )
    real_home = Path(os.environ.get("CEILING_REAL_HOME", str(Path.home())))
    auth_source = Path(os.environ.get("CEILING_TEST_AUTH_JSON", real_home / ".codex/auth.json"))
    if not auth_source.is_file():
        die(f"Codex judge auth file missing: {auth_source}")
    auth = home / "codex/auth.json"
    shutil.copyfile(auth_source, auth)
    auth.chmod(0o600)
    (home / "tmp").mkdir()
    previous = dict(os.environ)
    os.environ.clear()
    os.environ.update(
        {
            "PATH": f"{binary.parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(home),
            "CODEX_HOME": str(home / "codex"),
            "TERM": "dumb",
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "TZ": "UTC",
            "TMPDIR": str(home / "tmp"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
        }
    )
    try:
        yield home, [str(binary)]
    finally:
        os.environ.clear()
        os.environ.update(previous)
        shutil.rmtree(home, ignore_errors=True)


def load_script(path: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        die(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return vars(module)


def runtime_model(judge: str, meta: dict[str, Any]) -> str:
    if judge == "sonnet":
        usage = meta.get("modelUsage")
        keys = sorted(str(key) for key in usage) if isinstance(usage, dict) else []
        if not keys or not all("sonnet" in key.casefold() for key in keys):
            die(f"sonnet judge runtime model attestation missing or wrong: {keys}")
        return ",".join(keys)
    match = re.search(r"^model:\s*(\S+)\s*$", str(meta.get("stderr", "")), re.MULTILINE)
    if not match or match.group(1) != "gpt-5.6-terra":
        die(f"codex judge runtime model is not gpt-5.6-terra: {match.group(1) if match else 'missing'}")
    return match.group(1)


def judge_cli_version(judge: str, meta: dict[str, Any], codex_command: list[str] | None = None) -> str:
    if judge == "sonnet":
        isolation_path = meta.get("isolation_path")
        if not isolation_path:
            die("sonnet judge isolation metadata path missing")
        version = load_json(Path(isolation_path)).get("direct_claude", {}).get("version")
    else:
        if not codex_command:
            die("codex judge command missing for version probe")
        probe = subprocess.run(
            [*codex_command, "--version"], check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        version = (probe.stdout or probe.stderr).strip().splitlines()[0] if probe.returncode == 0 else None
    if not version:
        die(f"{judge} judge CLI version missing")
    return str(version)


def judge_cell(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    ceiling_root = Path(args.ceiling_root).resolve()
    script_dir = Path(__file__).resolve().parent
    run_root = ceiling_root / "results" / args.run_id
    cohort = load_json(run_root / "nodeg-cohort.json")
    controls = selected_controls(args.tasks)
    if cohort.get("selected_controls") != controls:
        die("judge selection does not match nodeg-cohort.json")
    if git(repo, "rev-parse", "HEAD") != cohort.get("runner_commit_sha"):
        die("runner commit changed after cell initialization")
    require_runner_integrity(repo, ceiling_root, args.run_id, True)
    judge_module = load_judge_module(script_dir)
    aggregate: dict[str, Any] = {"schema_version": 1, "run_id": args.run_id, "tasks": {}}
    for control in controls:
        source = frozen_source(ceiling_root, control)
        task = source["task"]
        task_dir = run_root / task
        judge_dir = task_dir / "nodeg-judge"
        judge_dir.mkdir(parents=True, exist_ok=True)
        a_patch = task_dir / "A1/patch.diff"
        if not a_patch.is_file():
            die(f"A patch missing for judge: {a_patch}")
        candidates = [
            {"candidate": "A", "patch_path": str(a_patch.resolve()), "patch_sha256": sha256(a_patch)},
            {"candidate": "B", "patch_path": source["patch_path"], "patch_sha256": source["patch_sha256"]},
        ]
        seed = int(hashlib.sha256(task.encode()).hexdigest(), 16)
        random.Random(seed).shuffle(candidates)
        packets = [
            {"label": f"P{index}", "patch": Path(candidate["patch_path"]).read_text(encoding="utf-8", errors="replace")}
            for index, candidate in enumerate(candidates, start=1)
        ]
        labels = {candidate["candidate"]: f"P{index}" for index, candidate in enumerate(candidates, start=1)}
        mapping = {
            "seed": seed,
            "packets": {
                f"P{index}": {"candidate": candidate["candidate"], "patch_sha256": candidate["patch_sha256"]}
                for index, candidate in enumerate(candidates, start=1)
            },
            "frozen_b_source": source,
        }
        mapping_path = judge_dir / "mapping.json"
        if mapping_path.is_file() and load_json(mapping_path) != mapping:
            die(f"judge mapping/provenance changed on resume: {mapping_path}")
        mapping_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
        prompt = pair_prompt(
            (ceiling_root / "corpus" / task / "task.txt").read_text(encoding="utf-8").rstrip("\n"),
            packets,
        )
        task_result: dict[str, Any] = {"control_id": control, "judges": {}}
        for judge in ("sonnet", "codex"):
            raw_path = judge_dir / f"{judge}.json"
            if args.resume and raw_path.is_file():
                raw = load_json(raw_path)
                if raw.get("parsed") is not None and raw.get("runtime_model"):
                    task_result["judges"][judge] = raw["result"]
                    continue
            if judge == "sonnet":
                parsed, error, attempts, meta = judge_module["call_with_retry"](
                    judge, prompt, judge_dir, ["unused"]
                )
                codex_command = None
            else:
                with isolated_codex_home(script_dir, args.run_id, task) as (_, codex_command):
                    parsed, error, attempts, meta = judge_module["call_with_retry"](
                        judge, prompt, judge_dir, codex_command
                    )
                    cli_version = judge_cli_version(judge, meta, codex_command)
            if parsed is None or error is not None:
                die(f"{task} {judge} judge failed after retries: {error}")
            model = runtime_model(judge, meta)
            if judge == "sonnet":
                cli_version = judge_cli_version(judge, meta)
            outcomes: dict[str, str] = {}
            for axis in AXES:
                tiers = parsed["axes"][axis]["tiers"]
                positions = {label: index for index, tier in enumerate(tiers) for label in tier}
                a_position = positions[labels["A"]]
                b_position = positions[labels["B"]]
                outcomes[axis] = "A_win" if a_position < b_position else "B_win" if a_position > b_position else "tie"
            result = {"runtime_model": model, "cli_version": cli_version, "axes": outcomes}
            raw = {
                "judge": judge,
                "task": task,
                "prompt": prompt,
                "attempts": attempts,
                "error": error,
                "parsed": parsed,
                "runtime_model": model,
                "result": result,
                "meta": meta,
            }
            raw_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
            task_result["judges"][judge] = result
        aggregate["tasks"][task] = task_result
    (run_root / "nodeg-judge-aggregate.json").write_text(json.dumps(aggregate, indent=2) + "\n", encoding="utf-8")
    return 0


def a_runtime_models(transcript: Path) -> list[str]:
    data = load_json(transcript)
    usage = data.get("modelUsage") or data.get("usage")
    keys = sorted(str(key) for key in usage) if isinstance(usage, dict) else []
    if not keys or not all("sonnet" in key.casefold() for key in keys):
        die(f"A runtime model attestation missing or not sonnet: {transcript}")
    return keys


def verdict(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    ceiling_root = Path(args.ceiling_root).resolve()
    run_root = ceiling_root / "results" / args.run_id
    cohort = load_json(run_root / "nodeg-cohort.json")
    controls = selected_controls(args.tasks)
    if cohort.get("selected_controls") != controls:
        die("verdict selection does not match nodeg-cohort.json")
    if git(repo, "rev-parse", "HEAD") != cohort.get("runner_commit_sha"):
        die("runner commit changed after cell initialization")
    require_runner_integrity(repo, ceiling_root, args.run_id, True)
    judge_data = load_json(run_root / "nodeg-judge-aggregate.json")
    objective_rows: dict[str, Any] = {}
    quality_rows: dict[str, Any] = {}
    wall_rows: dict[str, Any] = {}
    claude_versions: set[str] = set()
    codex_versions: set[str] = set()
    a_models: set[str] = set()
    judge_models: dict[str, set[str]] = {"sonnet": set(), "codex": set()}
    judge_versions: dict[str, set[str]] = {"sonnet": set(), "codex": set()}
    sources: list[dict[str, Any]] = []
    for control in controls:
        source = frozen_source(ceiling_root, control)
        sources.append(source)
        task = source["task"]
        attempt_dir = run_root / task / "A1"
        objective = load_json(attempt_dir / "objective.json")
        timing = load_json(attempt_dir / "timing.json")
        isolation = load_json(attempt_dir / "isolation.json")
        if isolation.get("opaque_paths", {}).get("passed") is not True:
            die(f"{control} A attempt {attempt_dir.name} opaque-path attestation did not pass: {attempt_dir / 'isolation.json'}")
        objective_rows[control] = {
            "task": task,
            "a_resolved": objective.get("resolved"),
            "frozen_b_resolved": source["resolved"],
            "passed": objective.get("resolved") is True and source["resolved"] is True,
            "a_objective_path": str((attempt_dir / "objective.json").resolve()),
            "a_objective_sha256": sha256(attempt_dir / "objective.json"),
        }
        task_judges = judge_data.get("tasks", {}).get(task, {}).get("judges", {})
        per_judge: dict[str, Any] = {}
        complete = True
        lost = False
        for judge in ("sonnet", "codex"):
            result = task_judges.get(judge, {})
            axes = result.get("axes", {})
            valid = set(axes) == set(AXES) and all(value in {"A_win", "B_win", "tie"} for value in axes.values())
            complete = complete and valid
            lost = lost or any(value == "B_win" for value in axes.values())
            if result.get("runtime_model"):
                judge_models[judge].add(result["runtime_model"])
            if result.get("cli_version"):
                judge_versions[judge].add(result["cli_version"])
            per_judge[judge] = {
                "runtime_model": result.get("runtime_model"),
                "cli_version": result.get("cli_version"),
                "axes": axes,
                "valid": valid,
            }
        quality_rows[control] = {
            "task": task,
            "judges": per_judge,
            "passed": complete and not lost,
            "rule": "both judges valid and A is never ranked below frozen B on any axis",
        }
        a_elapsed = timing.get("elapsed_seconds")
        if not isinstance(a_elapsed, (int, float)) or a_elapsed < 0:
            die(f"invalid A timing: {attempt_dir / 'timing.json'}")
        ratio = a_elapsed / source["elapsed_seconds"]
        wall_rows[control] = {
            "task": task,
            "a_elapsed_seconds": a_elapsed,
            "frozen_b_elapsed_seconds": source["elapsed_seconds"],
            "a_to_frozen_b_ratio": ratio,
            "cap": WALL_CAP,
            "passed": ratio <= WALL_CAP,
        }
        claude_versions.add(str(isolation.get("direct_claude", {}).get("version")))
        codex_versions.add(str(isolation.get("direct_codex", {}).get("version")))
        a_models.update(a_runtime_models(attempt_dir / "transcript.txt"))
    if "None" in claude_versions or "None" in codex_versions or len(claude_versions) != 1 or len(codex_versions) != 1:
        die(f"A CLI identity drift or missing identity: claude={claude_versions}, codex={codex_versions}")
    if any(len(models) != 1 for models in judge_models.values()):
        die(f"judge model identity drift: {judge_models}")
    if any(len(versions) != 1 for versions in judge_versions.values()):
        die(f"judge CLI identity drift: {judge_versions}")
    payload = {
        "schema_version": 1,
        "cell_owner": "iter-0068",
        "run_id": args.run_id,
        "cohort_identity": {
            "runner_commit_sha": cohort["runner_commit_sha"],
            "cli_versions": {
                "a_claude": next(iter(claude_versions)),
                "a_codex": next(iter(codex_versions)),
                "judge_sonnet": next(iter(judge_versions["sonnet"])),
                "judge_codex": next(iter(judge_versions["codex"])),
            },
            "resolved_models": {
                "a_orchestrator": sorted(a_models),
                "a_executor": ["gpt-5.6-terra"],
                "judge_sonnet": sorted(judge_models["sonnet"]),
                "judge_codex": sorted(judge_models["codex"]),
            },
            "a_executor_resolution_evidence": "run-ceiling-arm.sh benchmark-owned CODEX_HOME config pin",
        },
        "registered_controls": list(CONTROL_ORDER),
        "selected_controls": controls,
        "excluded_unfair": list(EXCLUDED_UNFAIR),
        "frozen_b_sources": sources,
        "bars": {
            "objective": {"per_row": objective_rows, "passed": all(row["passed"] for row in objective_rows.values())},
            "quality": {"per_row": quality_rows, "passed": all(row["passed"] for row in quality_rows.values())},
            "wall": {
                "per_row": wall_rows,
                "cap": WALL_CAP,
                "cap_source": "autoresearch/NORTH-STAR.md:254",
                "passed": all(row["passed"] for row in wall_rows.values()),
            },
        },
    }
    (run_root / "nodeg-verdict.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(run_root / "nodeg-verdict.json")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subparsers = result.add_subparsers(dest="command", required=True)
    for name in ("preflight", "judge", "verdict"):
        child = subparsers.add_parser(name)
        child.add_argument("--run-id", required=True)
        child.add_argument("--tasks")
        child.add_argument("--repo-root", required=True)
        child.add_argument("--ceiling-root", required=True)
        child.add_argument("--resume", action="store_true")
    subparsers.choices["preflight"].add_argument("--initialize", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    validate_run_id(args.run_id)
    if args.command == "preflight":
        return preflight(args)
    if args.command == "judge":
        return judge_cell(args)
    return verdict(args)


if __name__ == "__main__":
    raise SystemExit(main())
