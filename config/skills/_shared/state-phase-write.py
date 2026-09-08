#!/usr/bin/env python3
"""Deterministic spawn/complete writer for phases.<name> in pipeline.state.json.

Usage:
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement spawn \
        --round 1 --triggered-by verify [--pre-sha <sha>] [--engine claude] [--model <id>]
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement durability-enforce \
        --round 1 --origin-phase verify
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement complete \
        --verdict PASS [--post-sha <sha>] [--findings-file <path>] [--log-file <path>] \
        [--engine claude] [--model <requested-id>] [--engine-session-log <path>]
    python3 state-phase-write.py --devlyn-dir .devlyn --phase plan transition \
        --verdict PASS --next-phase implement --next-round 0 --next-engine claude

references/state-schema.md#write-protocol is the contract this implements.
A prior hand-edited fix-loop respawn left `started_at` at its original round's
value while `completed_at`/`duration_ms`/`round`/`triggered_by` advanced to the
new round, producing an internally inconsistent phase timeline. `spawn` always
resets `started_at` fresh and nulls the completion fields; `complete` derives
`duration_ms` from the phase's own recorded `started_at`, so the two can never
drift apart again.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import difflib
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import runpy
import shutil
import subprocess
import sys
import tempfile

VALID_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "FAIL", "NEEDS_WORK", "BLOCKED"}
VALID_TRIGGERS = {"build_gate", "verify"}
SPAWN_TRIGGERS = VALID_TRIGGERS | {"plan"}
PHASE_NAMES = {"plan", "probe_derive", "implement", "surface_close", "build_gate", "cleanup", "verify", "final_report"}
LEGAL_TRANSITIONS = {
    "plan": {"probe_derive", "implement", "final_report"},
    "probe_derive": {"implement", "final_report"},
    "implement": {"implement", "surface_close", "build_gate", "cleanup", "verify", "final_report"},
    "surface_close": {"build_gate", "cleanup", "verify", "final_report"},
    "build_gate": {"implement", "cleanup", "verify", "final_report"},
    "cleanup": {"verify", "final_report"},
    "verify": {"implement", "final_report"},
    "final_report": set(),
}
WORKER_SESSION_ARTIFACT_PHASES = {
    "plan": "plan",
    "implement": "implement",
    "surface_close": "surface-close",
    "build_gate": "build_gate",
    "cleanup": "cleanup",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SURFACE_ROW_RE = re.compile(
    r"^(?P<obligation>UVR-STALE|PATH-TEST): (?:"
    r"(?P<fired>FIRED) (?P<fired_path>.+):(?P<fired_line>[1-9][0-9]*)"
    r"(?: — (?P<fired_evidence>\S.*))?|"
    r"(?P<na>N/A) (?P<na_path>.+?)(?::(?P<na_line>[1-9][0-9]*))?"
    r"(?: — (?P<na_evidence>\S.*))?)$"
)
VALIDATION_EXECUTION_RE = re.compile(
    r"npm\s+test|node\s+--test|node\s+-e|node\s+bin/|node\s+tests/|git\s+stash"
)
SURFACE_SKIP_REASON = "auto_surface_close_claude_unavailable"
SURFACE_RECOVERY_REASON = "surface_close_rolled_back_adjudication_malformed"
PLAN_MAX_DISPATCHES = 2
PLAN_SPAWN_RECEIPT_FIELDS = (
    "round", "started_at", "triggered_by", "engine", "model_requested", "prompt_sha256",
)
PLAN_COMPLETION_RECEIPT_FIELDS = (
    "completed_at", "duration_ms", "verdict", "model_effective", "output_sha256",
)
PLAN_RECEIPT_FIELDS = PLAN_SPAWN_RECEIPT_FIELDS + PLAN_COMPLETION_RECEIPT_FIELDS
_PROCESS_EVIDENCE_MODULE = None
_INVOCATION_RECEIPT_MODULE = None


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict_json(text: str):
    return json.loads(
        text,
        parse_constant=reject_json_constant,
        object_pairs_hook=reject_duplicate_keys,
    )


def now_ms() -> datetime.datetime:
    # Truncate to millisecond precision at capture time — now_iso()'s string
    # representation is millisecond-precise, so any duration_ms computed from
    # a not-yet-truncated `now` can be off by a sub-millisecond rounding
    # remainder from what re-parsing the stored completed_at would give.
    dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.replace(microsecond=(dt.microsecond // 1000) * 1000)


def now_iso(dt: datetime.datetime | None = None) -> str:
    dt = dt or now_ms()
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(value: str) -> datetime.datetime:
    text = value[:-1] if value.endswith("Z") else value
    if "." in text:
        head, frac = text.split(".", 1)
        text = f"{head}.{(frac + '000000')[:6]}"
    return datetime.datetime.fromisoformat(text).replace(tzinfo=datetime.timezone.utc)


def read_state(state_path: pathlib.Path) -> dict:
    if not state_path.is_file():
        raise SystemExit(f"error: {state_path} not found")
    try:
        return loads_strict_json(state_path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SystemExit(f"error: {state_path} is not valid JSON: {e}")


def write_state(state_path: pathlib.Path, state: dict) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), prefix=state_path.name + ".tmp.")
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
        pathlib.Path(tmp_name).replace(state_path)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise


def validate_plan_output(state: dict, devlyn: pathlib.Path | None, phase: str) -> None:
    plan = (state.get("phases") or {}).get("plan")
    if not isinstance(plan, dict) or plan.get("completed_at") is None:
        return
    expected = plan.get("output_sha256")
    if expected is None and state.get("version") != "3.0":
        return
    if (
        expected is None and "output_sha256" in plan and plan.get("verdict") == "BLOCKED"
        and devlyn is not None and not os.path.lexists(devlyn / "plan.md")
    ):
        if phase != "final_report":
            raise SystemExit("BLOCKED:plan-output-missing: only final_report is allowed")
        return
    if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None:
        raise SystemExit("BLOCKED:plan-integrity-invalid: phases.plan.output_sha256 is missing")
    if devlyn is None:
        raise SystemExit("BLOCKED:plan-integrity-invalid: .devlyn is required to rehash PLAN output")
    plan_path = devlyn / "plan.md"
    try:
        actual = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SystemExit(f"BLOCKED:plan-integrity-invalid: cannot read {plan_path}: {exc}") from exc
    if actual != expected:
        raise SystemExit(
            "BLOCKED:plan-integrity-mismatch: "
            f"expected={expected} actual={actual} path={plan_path}"
        )


def bind_plan_output(state: dict, devlyn: pathlib.Path | None) -> None:
    if devlyn is None:
        raise SystemExit("BLOCKED:plan-integrity-invalid: .devlyn is required to bind PLAN output")
    plan_path = devlyn / "plan.md"
    plan = state["phases"]["plan"]
    if (
        plan.get("verdict") == "BLOCKED" and plan.get("output_sha256") is None
        and not os.path.lexists(plan_path)
    ):
        digest = None
    else:
        try:
            digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise SystemExit(f"BLOCKED:plan-integrity-invalid: cannot read {plan_path}: {exc}") from exc
    plan["output_sha256"] = digest


def final_report_digest(state: dict, devlyn: pathlib.Path | None, log_file: str | None) -> str:
    try:
        if devlyn is None or not log_file:
            raise ValueError("--log-file must name .devlyn/final-report.md")
        path = devlyn / "final-report.md"
        supplied = pathlib.Path(log_file)
        if supplied.parent.resolve() / supplied.name != devlyn.resolve() / path.name:
            raise ValueError("--log-file must name the canonical final-report.md")
        if path.is_symlink() or not path.is_file():
            raise ValueError("final-report.md must be a nonsymlink regular file")
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        run_id = state.get("run_id")
        prefix = "<!-- devlyn:final-report run_id="
        if (
            not isinstance(run_id, str) or not run_id or not lines
            or lines[0] != f"{prefix}{run_id} -->"
            or sum(line.startswith(prefix) for line in lines) != 1
        ):
            raise ValueError("first line must uniquely identify the current state.run_id")
        if not any(line.strip() for line in lines[1:]):
            raise ValueError("final-report.md body must not be empty")
        return hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED:final-report-invalid: {exc}") from exc


def process_evidence_module():
    global _PROCESS_EVIDENCE_MODULE
    if _PROCESS_EVIDENCE_MODULE is None:
        module_path = pathlib.Path(__file__).with_name("process-evidence.py")
        spec = importlib.util.spec_from_file_location("devlyn_process_evidence", module_path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"BLOCKED:process-evidence-invalid: cannot load {module_path}")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode_setting = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode_setting
        _PROCESS_EVIDENCE_MODULE = module
    return _PROCESS_EVIDENCE_MODULE


def invocation_receipt_module():
    global _INVOCATION_RECEIPT_MODULE
    if _INVOCATION_RECEIPT_MODULE is None:
        module_path = pathlib.Path(__file__).with_name("invocation-receipt.py")
        spec = importlib.util.spec_from_file_location("devlyn_invocation_receipt", module_path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"BLOCKED:invocation-receipt-invalid: cannot load {module_path}")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode_setting = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode_setting
        _INVOCATION_RECEIPT_MODULE = module
    return _INVOCATION_RECEIPT_MODULE


def bind_process_evidence(
    state: dict, phase: str, verdict: str | None,
    devlyn: pathlib.Path | None, work: pathlib.Path | None,
) -> None:
    if phase == "implement" and verdict not in {"PASS", "PASS_WITH_ISSUES"}:
        return
    if phase not in {"implement", "build_gate"}:
        return
    source = state.get("source")
    if work is None or devlyn is None:
        if isinstance(source, dict) and source.get("type") == "spec":
            raise SystemExit(
                "BLOCKED:process-evidence-invalid: worktree is required for spec evidence validation"
            )
        state.setdefault("process_evidence", None)
        return
    runner = process_evidence_module()
    try:
        results_path = devlyn / "spec-verify.results.json"
        if phase == "implement":
            obligations = runner.declared_obligations(work, state, phase)
            if not obligations:
                state.setdefault("process_evidence", None)
                return
            round_ = runner.phase_round(state, phase)
            manifest_path = runner.manifest_relative_path(state, phase)
            carrier = runner.validate_manifest(
                work, manifest_path, state.get("run_id"), phase, round_, obligations,
            )
        elif verdict == "BLOCKED" and not os.path.lexists(results_path):
            round_ = runner.phase_round(state, phase)
            carrier = runner.validate_manifest(
                work, runner.manifest_relative_path(state, phase),
                state.get("run_id"), phase, round_, require_expectations=False,
            )
        else:
            if not results_path.is_file():
                raise runner.EvidenceError(
                    "spec-verify.results.json is missing for BUILD_GATE completion"
                )
            results = loads_strict_json(results_path.read_text(encoding="utf-8"))
            if not isinstance(results, dict):
                raise runner.EvidenceError(
                    "spec-verify.results.json must contain a JSON object"
                )
            commands = results.get("commands")
            if not isinstance(commands, list):
                raise runner.EvidenceError(
                    "spec-verify.results.json commands must be an array"
                )
            carrier = results.get("process_evidence")
            if carrier is None:
                if commands:
                    raise runner.EvidenceError(
                        "BUILD_GATE commands exist without a process-evidence carrier"
                    )
                manifest_path = work / runner.manifest_relative_path(state, phase)
                if manifest_path.exists():
                    raise runner.EvidenceError(
                        "BUILD_GATE manifest exists without a process-evidence carrier"
                    )
                if runner.mechanical_evidence_required(work, state):
                    raise runner.EvidenceError(
                        "required BUILD_GATE evidence has no process-evidence carrier"
                    )
                state.setdefault("process_evidence", None)
                return
            round_ = runner.phase_round(state, phase)
            manifest = carrier.get("manifest") if isinstance(carrier, dict) else None
            if (
                not isinstance(carrier, dict)
                or carrier.get("phase") != phase
                or carrier.get("round") != round_
                or not isinstance(manifest, dict)
                or manifest.get("path") != runner.manifest_relative_path(state, phase)
            ):
                raise runner.EvidenceError(
                    "BUILD_GATE process-evidence carrier does not match the active run/round"
                )
            outcome = runner.validate_summary_commands(work, commands, carrier)
            if outcome["verdict"] == "BLOCKED" and verdict != "BLOCKED":
                denial = outcome["capability_denials"][0]
                raise runner.EvidenceError(
                    "BUILD_GATE capability denial requires BLOCKED verdict: "
                    f"{denial['id']}:{denial['operation']}"
                )
            if (
                outcome["verdict"] == "NEEDS_WORK"
                and verdict in {"PASS", "PASS_WITH_ISSUES"}
            ):
                raise runner.EvidenceError(
                    "BUILD_GATE process evidence mismatch cannot complete as "
                    f"{verdict}: {','.join(outcome['failed_ids'])}"
                )
    except (runner.EvidenceError, OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED:process-evidence-invalid: {exc}") from exc
    existing = state.get("process_evidence")
    if existing is None:
        existing = []
    if not isinstance(existing, list):
        raise SystemExit("BLOCKED:process-evidence-invalid: state.process_evidence must be null or an array")
    try:
        for prior in existing:
            runner.validate_bound_carrier(work, prior)
    except runner.EvidenceError as exc:
        raise SystemExit(f"BLOCKED:process-evidence-invalid: {exc}") from exc
    if any(
        isinstance(item, dict)
        and item.get("phase") == carrier["phase"]
        and item.get("round") == carrier["round"]
        for item in existing
    ):
        raise SystemExit(
            "BLOCKED:process-evidence-invalid: duplicate state carrier for "
            f"{phase} round {carrier['round']}"
        )
    state["process_evidence"] = [*existing, carrier]


def parse_string_list(raw: str, label: str) -> list[str]:
    try:
        value = loads_strict_json(raw)
    except ValueError as exc:
        raise SystemExit(f"error: {label} is not valid JSON: {exc}") from exc
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"error: {label} must be a JSON array of strings")
    return value


def run_git_paths(work: pathlib.Path, *args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args], cwd=work, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git command failed"
        raise SystemExit(f"error: {detail}")
    return [os.fsdecode(item) for item in proc.stdout.split(b"\0") if item]


def surface_entry(state: dict) -> dict:
    entry = (state.get("phases") or {}).get("surface_close")
    if not isinstance(entry, dict) or not entry.get("started_at"):
        raise SystemExit("error: phases.surface_close was never spawned")
    pre_sha = entry.get("pre_sha")
    patch_digest = entry.get("input_patch_sha256")
    prompt_digest = entry.get("prompt_sha256")
    baseline = entry.get("untracked_before")
    if not isinstance(pre_sha, str) or not pre_sha:
        raise SystemExit("error: phases.surface_close.pre_sha is missing")
    if not isinstance(patch_digest, str) or not SHA256_RE.fullmatch(patch_digest):
        raise SystemExit("error: phases.surface_close.input_patch_sha256 must be 64 lowercase hex characters")
    if not isinstance(prompt_digest, str) or not SHA256_RE.fullmatch(prompt_digest):
        raise SystemExit("error: phases.surface_close.prompt_sha256 must be 64 lowercase hex characters")
    if not isinstance(baseline, list) or any(not isinstance(item, str) for item in baseline):
        raise SystemExit("error: phases.surface_close.untracked_before must be a string array")
    return entry


def devlyn_prefix(work: pathlib.Path, devlyn: pathlib.Path) -> str:
    try:
        return devlyn.resolve().relative_to(work.resolve()).as_posix().strip("/")
    except ValueError as exc:
        raise SystemExit("error: --devlyn-dir must be inside --workdir") from exc


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise SystemExit(f"BLOCKED:surface-close-input-mismatch: {path}: {exc}") from exc
    return digest.hexdigest()


def validate_surface_inputs(work: pathlib.Path, devlyn: pathlib.Path, state: dict) -> None:
    entry = surface_entry(state)
    source = state.get("source")
    if not isinstance(source, dict):
        raise SystemExit("BLOCKED:surface-close-input-mismatch: source is missing")
    goal_path = source.get("goal_path")
    goal_digest = source.get("goal_sha256")
    if not isinstance(goal_path, str) or not goal_path or not isinstance(goal_digest, str):
        raise SystemExit("BLOCKED:surface-close-input-mismatch: Goal metadata is missing")
    goal = work / goal_path
    try:
        goal.resolve().relative_to(work.resolve())
    except (OSError, ValueError) as exc:
        raise SystemExit("BLOCKED:surface-close-input-mismatch: Goal path escapes worktree") from exc
    patch = devlyn / "surface-close.input.patch"
    if file_sha256(goal) != goal_digest or file_sha256(patch) != entry["input_patch_sha256"]:
        raise SystemExit("BLOCKED:surface-close-input-mismatch: artifact digest changed")


def validate_surface_prompt(devlyn: pathlib.Path, state: dict) -> None:
    prompt = devlyn / "surface-close.prompt"
    if file_sha256(prompt) != surface_entry(state)["prompt_sha256"]:
        raise SystemExit("BLOCKED:surface-close-prompt-mismatch")


def surface_delta_paths(work: pathlib.Path, devlyn: pathlib.Path, state: dict) -> tuple[list[str], list[str]]:
    entry = surface_entry(state)
    pre_sha = entry["pre_sha"]
    prefix = devlyn_prefix(work, devlyn)
    tracked = set(run_git_paths(work, "diff", "--name-only", "-z", pre_sha, "--"))
    untracked_now = set(run_git_paths(work, "ls-files", "--others", "--exclude-standard", "-z"))
    new_untracked = untracked_now - set(entry["untracked_before"])

    def external(path: str) -> bool:
        return bool(path) and path != prefix and not path.startswith(f"{prefix}/")

    return (
        sorted(path for path in tracked if external(path)),
        sorted(path for path in new_untracked if external(path)),
    )


def ensure_surface_clean_baseline(work: pathlib.Path, devlyn: pathlib.Path, state: dict) -> None:
    tracked, new_untracked = surface_delta_paths(work, devlyn, state)
    if tracked or new_untracked:
        detail = json.dumps(sorted(set(tracked + new_untracked)))
        raise SystemExit(f"BLOCKED:surface-close-preexisting-delta: {detail}")


def validate_surface_brace_glob(entry: str) -> str | None:
    if "{" not in entry and "}" not in entry:
        return None
    brace = re.search(r"\{([^{}]*)\}", entry)
    alternatives = brace.group(1).split(",") if brace else []
    if (
        entry.count("{") != 1
        or entry.count("}") != 1
        or len(alternatives) < 2
        or any(not value or any(char in value for char in "{},/*") for value in alternatives)
    ):
        return (
            f"unsupported brace glob {entry!r}; supported form is {{alt1,alt2,...}} "
            "with at least two non-empty plain alternatives"
        )
    return None


def validate_authorized_surface(raw: str) -> list[str]:
    surface = parse_string_list(raw, "--authorized-surface-json")
    if not surface:
        raise SystemExit("error: --authorized-surface-json must not be empty")
    for entry in surface:
        path = entry[:-3] if entry.endswith("/**") else entry
        parts = pathlib.PurePosixPath(path).parts
        if (
            not path or path == "." or path.startswith("./")
            or pathlib.PurePosixPath(path).is_absolute() or ".." in parts
        ):
            raise SystemExit(f"error: invalid authorized_surface entry: {entry!r}")
        brace_error = validate_surface_brace_glob(entry)
        if brace_error is not None:
            raise SystemExit(f"error: {brace_error}")
    return surface


def path_matches_surface(path: str, surface: list[str]) -> bool:
    for entry in surface:
        brace_error = validate_surface_brace_glob(entry)
        if brace_error is not None:
            raise ValueError(brace_error)
        if "{" in entry:
            brace = re.search(r"\{([^{}]*)\}", entry)
            assert brace is not None
            alternatives = brace.group(1).split(",")
            entries = tuple(
                entry[:brace.start()] + value + entry[brace.end():]
                for value in alternatives
            )
        else:
            entries = (entry,)
        for expanded in entries:
            if expanded.endswith("/**"):
                prefix = expanded[:-3].rstrip("/")
                if path == prefix or path.startswith(f"{prefix}/"):
                    return True
            elif path == expanded:
                return True
    return False


def safe_path_matches_surface(path: str, surface: list[str]) -> bool:
    parsed = pathlib.PurePosixPath(path)
    return not (parsed.is_absolute() or ".." in parsed.parts) and path_matches_surface(path, surface)


def worktree_file_exists(work: pathlib.Path, path: str) -> bool:
    parsed = pathlib.PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts:
        return False
    try:
        resolved = (work / path).resolve()
        resolved.relative_to(work.resolve())
        return resolved.is_file()
    except (OSError, RuntimeError, ValueError):
        return False


def worktree_path_exists(work: pathlib.Path, path: str) -> bool:
    parsed = pathlib.PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts:
        return False
    try:
        resolved = (work / path).resolve()
        resolved.relative_to(work.resolve())
        return resolved.exists()
    except (OSError, RuntimeError, ValueError):
        return False


def resolve_na_surface_citation(
    work: pathlib.Path, raw: str, parsed_path: str, parsed_line: int | None,
    surface: list[str],
) -> tuple[str, int | None]:
    def proven(path: str) -> bool:
        if path in surface and not path.endswith("/**"):
            return True
        return worktree_file_exists(work, path) and any(
            entry.endswith("/**") and safe_path_matches_surface(path, [entry])
            for entry in surface
        )

    if proven(raw):
        return raw, None
    if worktree_path_exists(work, raw) and not safe_path_matches_surface(raw, surface):
        raise SystemExit(f"BLOCKED:surface-close-adjudication-out-of-surface: {raw}")
    if (
        worktree_path_exists(work, parsed_path)
        and not safe_path_matches_surface(parsed_path, surface)
    ):
        raise SystemExit(f"BLOCKED:surface-close-adjudication-out-of-surface: {raw}")
    for split in range(len(raw) - 1, -1, -1):
        if raw[split] != ":" or not proven(raw[:split]):
            continue
        suffix = raw[split:]
        if not re.fullmatch(r":[1-9][0-9]*", suffix):
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-malformed: citation {raw!r}"
            )
        return raw[:split], int(suffix[1:])
    return parsed_path, parsed_line


def surface_offenders(work: pathlib.Path, devlyn: pathlib.Path, state: dict,
                      surface: list[str]) -> list[str]:
    tracked, untracked = surface_delta_paths(work, devlyn, state)
    return sorted(path for path in set(tracked + untracked) if not safe_path_matches_surface(path, surface))


def path_exists_at_commit(work: pathlib.Path, sha: str, path: str) -> bool:
    proc = subprocess.run(
        ["git", "ls-tree", "--name-only", "-z", sha, "--", path],
        cwd=work, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git ls-tree failed"
        raise SystemExit(f"error: {detail}")
    return bool(proc.stdout)


def remove_worktree_path(work: pathlib.Path, path: str) -> None:
    parsed = pathlib.PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts:
        raise SystemExit(f"error: rollback path escapes worktree: {path!r}")
    target = work / path
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)


def rollback_surface_delta(work: pathlib.Path, devlyn: pathlib.Path, state: dict) -> list[str]:
    entry = surface_entry(state)
    pre_sha = entry["pre_sha"]
    tracked, untracked = surface_delta_paths(work, devlyn, state)
    restore = [path for path in tracked if path_exists_at_commit(work, pre_sha, path)]
    remove = sorted(set(untracked + [
        path for path in tracked if not path_exists_at_commit(work, pre_sha, path)
    ]))
    if restore:
        proc = subprocess.run(
            ["git", "restore", f"--source={pre_sha}", "--staged", "--worktree", "--", *restore],
            cwd=work, capture_output=True, check=False,
        )
        if proc.returncode != 0:
            detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git restore failed"
            raise SystemExit(f"error: {detail}")
    if remove:
        proc = subprocess.run(
            ["git", "rm", "-f", "--cached", "--ignore-unmatch", "--", *remove],
            cwd=work, capture_output=True, check=False,
        )
        if proc.returncode != 0:
            detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git rm --cached failed"
            raise SystemExit(f"error: {detail}")
        for path in remove:
            remove_worktree_path(work, path)
    return sorted(set(restore + remove))


def validate_surface_adjudication(
    work: pathlib.Path, devlyn: pathlib.Path, state: dict, surface: list[str],
) -> dict[str, str]:
    output = devlyn / "surface-close.stdout"
    try:
        lines = output.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"BLOCKED:surface-close-adjudication-malformed: {output}: {exc}") from exc

    rows: dict[str, tuple[str, str, int | None, str | None, int]] = {}
    for index, line in enumerate(lines):
        if "UVR-STALE:" not in line and "PATH-TEST:" not in line:
            continue
        match = SURFACE_ROW_RE.fullmatch(line)
        if match is None:
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-malformed: line {index + 1}: {line!r}"
            )
        obligation = match.group("obligation")
        if obligation in rows:
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-malformed: duplicate {obligation} row"
            )
        status = "FIRED" if match.group("fired") else "N/A"
        evidence = match.group("fired_evidence") or match.group("na_evidence")
        if status == "N/A" and evidence is None:
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-malformed: {obligation} N/A requires evidence"
            )
        path = match.group("fired_path") or match.group("na_path")
        raw_line = match.group("fired_line") or match.group("na_line")
        line_number = int(raw_line) if raw_line is not None else None
        citation = path if line_number is None else f"{path}:{line_number}"
        if status == "N/A":
            path, line_number = resolve_na_surface_citation(
                work, citation, path, line_number, surface,
            )
            citation = path if line_number is None else f"{path}:{line_number}"
        if not safe_path_matches_surface(path, surface):
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-out-of-surface: {citation}"
            )
        try:
            cited = (work / path).resolve()
            cited.relative_to(work.resolve())
            cited_lines = cited.read_text(encoding="utf-8").splitlines()
        except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-citation-missing: {citation}: {exc}"
            ) from exc
        if line_number is not None and line_number > len(cited_lines):
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-citation-missing: {path}:{line_number}"
            )
        rows[obligation] = (status, path, line_number, evidence, index)

    missing = [name for name in ("UVR-STALE", "PATH-TEST") if name not in rows]
    if missing:
        raise SystemExit(
            "BLOCKED:surface-close-adjudication-malformed: missing " + ", ".join(missing)
        )
    pass_lines = [index for index, line in enumerate(lines) if line == "PASS"]
    if len(pass_lines) != 1 or pass_lines[0] <= max(row[4] for row in rows.values()):
        raise SystemExit(
            "BLOCKED:surface-close-adjudication-malformed: exactly one PASS must follow both rows"
        )
    statuses = {name: row[0] for name, row in rows.items()}
    if all(status == "N/A" for status in statuses.values()):
        tracked, untracked = surface_delta_paths(work, devlyn, state)
        if tracked or untracked:
            raise SystemExit("BLOCKED:surface-close-empty-pass-has-delta")
    return statuses


def surface_transcript_commands(transcript: pathlib.Path) -> list[str]:
    try:
        lines = transcript.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"BLOCKED:surface-close-worker-session-invalid: {transcript}: {exc}") from exc
    commands: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = loads_strict_json(line)
        except ValueError as exc:
            raise SystemExit(
                f"BLOCKED:surface-close-worker-session-invalid: line {line_number}: {exc}"
            ) from exc
        if not isinstance(event, dict):
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                if item.get("name") != "Bash":
                    continue
                tool_input = item.get("input")
                command = tool_input.get("command") if isinstance(tool_input, dict) else None
                if isinstance(command, str):
                    commands.append(command)
    return commands


def validate_surface_execution(devlyn: pathlib.Path, state: dict) -> None:
    entry = surface_entry(state)
    transcript = devlyn / f"surface-close.worker-session.{entry.get('round')}.jsonl"
    commands = surface_transcript_commands(transcript)
    hits = [command for command in commands if VALIDATION_EXECUTION_RE.search(command)]
    if hits:
        raise SystemExit(
            "BLOCKED:surface-close-validation-execution: " + json.dumps(hits)
        )


def validate_surface_write_audit(
    work: pathlib.Path, devlyn: pathlib.Path, state: dict, surface: list[str],
) -> list[str]:
    entry = surface_entry(state)
    transcript = devlyn / f"surface-close.worker-session.{entry.get('round')}.jsonl"
    try:
        lines = transcript.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"BLOCKED:surface-close-worker-session-invalid: {transcript}: {exc}") from exc
    targets: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = loads_strict_json(line)
        except ValueError as exc:
            raise SystemExit(
                f"BLOCKED:surface-close-worker-session-invalid: line {line_number}: {exc}"
            ) from exc
        message = event.get("message") if isinstance(event, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            if item.get("name") not in {"Edit", "Write"}:
                continue
            tool_input = item.get("input")
            raw_target = tool_input.get("file_path") if isinstance(tool_input, dict) else None
            if not isinstance(raw_target, str) or not raw_target:
                raise SystemExit(
                    "BLOCKED:surface-close-write-audit-violation: "
                    f"line {line_number}: Edit/Write target missing"
                )
            target = pathlib.Path(raw_target)
            try:
                resolved = (target if target.is_absolute() else work / target).resolve()
                relative = resolved.relative_to(work.resolve()).as_posix()
            except (OSError, ValueError) as exc:
                raise SystemExit(
                    "BLOCKED:surface-close-write-audit-violation: "
                    f"line {line_number}: {raw_target!r}"
                ) from exc
            if not safe_path_matches_surface(relative, surface):
                raise SystemExit(
                    "BLOCKED:surface-close-write-audit-violation: "
                    f"line {line_number}: {relative!r}"
                )
            targets.append(relative)
    return targets


def require_surface_adjudication_malformed(
    work: pathlib.Path, devlyn: pathlib.Path, state: dict, surface: list[str],
) -> None:
    try:
        validate_surface_adjudication(work, devlyn, state, surface)
    except SystemExit as exc:
        if str(exc).startswith("BLOCKED:surface-close-adjudication-malformed:"):
            return
        raise
    raise SystemExit(
        "error: surface-adjudication-recover requires "
        "BLOCKED:surface-close-adjudication-malformed"
    )


CLAUDE_USAGE_COUNTERS = (
    ("input_tokens", "inputTokens"),
    ("output_tokens", "outputTokens"),
    ("cache_read_input_tokens", "cacheReadInputTokens"),
    ("cache_creation_input_tokens", "cacheCreationInputTokens"),
)


def select_claude_primary_model(evidence: dict) -> str:
    model_usage = evidence.get("modelUsage")
    models = (
        [model for model in model_usage if isinstance(model, str) and model]
        if isinstance(model_usage, dict)
        else []
    )
    if len(models) == 1:
        return models[0]
    if not models:
        raise ValueError("Claude JSON wrapper has no effective-model evidence")

    usage = evidence.get("usage")
    if not isinstance(usage, dict):
        raise ValueError("multi-entry Claude JSON wrapper has malformed top-level usage")

    def counters(container: dict, fields: tuple[str, ...]) -> tuple[int, ...]:
        values = tuple(container.get(field) for field in fields)
        if any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 0
            for value in values
        ):
            raise ValueError("multi-entry Claude JSON wrapper has malformed usage counters")
        return values

    primary_usage = counters(
        usage, tuple(field[0] for field in CLAUDE_USAGE_COUNTERS)
    )
    matches = []
    for model in models:
        entry = model_usage[model]
        if not isinstance(entry, dict):
            raise ValueError("multi-entry Claude JSON wrapper has malformed modelUsage entry")
        if counters(
            entry, tuple(field[1] for field in CLAUDE_USAGE_COUNTERS)
        ) == primary_usage:
            matches.append(model)
    if len(matches) == 1:
        return matches[0]
    raise ValueError(
        "multi-entry Claude JSON wrapper has no unique primary usage match"
    )


def parse_effective_model(session_log: pathlib.Path) -> str:
    try:
        text = session_log.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read engine session log {session_log}: {exc}") from exc

    models: set[str] = set()
    if session_log.suffix == ".jsonl":
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = loads_strict_json(line)
            except ValueError as exc:
                raise ValueError(
                    f"engine session log {session_log} has malformed JSONL at line {line_number}: {exc}"
                ) from exc
            if not isinstance(event, dict) or event.get("type") != "turn_context":
                continue
            payload = event.get("payload")
            model = payload.get("model") if isinstance(payload, dict) else None
            if isinstance(model, str) and model:
                models.add(model)
    else:
        try:
            evidence = loads_strict_json(text)
        except ValueError:
            evidence = None
        if isinstance(evidence, dict) and isinstance(evidence.get("modelUsage"), dict):
            return select_claude_primary_model(evidence)

    if len(models) == 1:
        return next(iter(models))
    if not models:
        raise ValueError(f"engine session log {session_log} has no effective-model evidence")
    raise ValueError(
        f"engine session log {session_log} has conflicting effective models: {sorted(models)}"
    )


def _git_output(work: pathlib.Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", *args], cwd=work, input=input_bytes, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git command failed"
        raise SystemExit(f"BLOCKED:closure-durability-mechanical: {detail}")
    return proc.stdout


def _commit_blob(work: pathlib.Path, sha: str, path: str) -> bytes | None:
    if not path_exists_at_commit(work, sha, path):
        return None
    return _git_output(work, "show", f"{sha}:{path}")


def _line_matches(haystack: list[bytes], needle: list[bytes]) -> list[int]:
    if not needle or len(needle) > len(haystack):
        return []
    width = len(needle)
    return [index for index in range(len(haystack) - width + 1)
            if haystack[index:index + width] == needle]


def _nearest(matches: list[int], expected: int) -> int | None:
    return min(matches, key=lambda value: (abs(value - expected), value)) if matches else None


def _block_image_index(lines: list[bytes], image: list[bytes], block: dict) -> int | None:
    matches = []
    before = block["_before_lines"]
    after = block["_after_lines"]
    for index in _line_matches(lines, image):
        if before and (index < len(before) or lines[index - len(before):index] != before):
            continue
        end = index + len(image)
        if after and lines[end:end + len(after)] != after:
            continue
        matches.append(index)
    return _nearest(matches, block["_expected_index"])


def _block_anchor_index(lines: list[bytes], block: dict) -> int | None:
    before = block["_before_lines"]
    after = block["_after_lines"]
    if not before and not after:
        return 0 if not lines else None
    candidates = []
    for index in range(len(lines) + 1):
        if before and (index < len(before) or lines[index - len(before):index] != before):
            continue
        if after and lines[index:index + len(after)] != after:
            continue
        candidates.append(index)
    return _nearest(candidates, block["_expected_index"])


def _map_pre_fix_span(block: dict, pre_fix_lines: list[bytes]) -> None:
    post_lines = block["_post_lines"]
    if post_lines:
        index = _block_image_index(pre_fix_lines, post_lines, block)
    else:
        index = _block_anchor_index(pre_fix_lines, block)
    if index is None:
        block["_pre_fix_anchor"] = False
        return
    block["_pre_fix_anchor"] = True
    block["_expected_index"] = index
    width = max(1, len(post_lines))
    block["pre_fix_span"] = [index + 1, index + width]


def surface_change_blocks(work: pathlib.Path, state: dict,
                          pre_fix_sha: str | None = None) -> list[dict]:
    surface = ((state.get("phases") or {}).get("surface_close") or {})
    pre_sha = surface.get("pre_sha")
    post_sha = surface.get("post_sha")
    if not isinstance(pre_sha, str) or not pre_sha or not isinstance(post_sha, str) or not post_sha:
        return []
    paths = run_git_paths(work, "diff", "--name-only", "--no-renames", "-z", pre_sha, post_sha, "--")
    blocks = []
    for path in paths:
        parsed = pathlib.PurePosixPath(path)
        if parsed.is_absolute() or ".." in parsed.parts:
            raise SystemExit(f"BLOCKED:closure-durability-mechanical: unsafe surface path {path!r}")
        old_blob = _commit_blob(work, pre_sha, path)
        post_blob = _commit_blob(work, post_sha, path)
        old_lines = [] if old_blob is None else old_blob.splitlines(keepends=True)
        post_lines = [] if post_blob is None else post_blob.splitlines(keepends=True)
        matcher = difflib.SequenceMatcher(None, old_lines, post_lines, autojunk=False)
        opcodes = matcher.get_opcodes()
        for ordinal, (tag, old_start, old_end, new_start, new_end) in enumerate(opcodes):
            if tag == "equal":
                continue
            old_image = old_lines[old_start:old_end]
            post_image = post_lines[new_start:new_end]
            before_lines = []
            after_lines = []
            if ordinal > 0 and opcodes[ordinal - 1][0] == "equal":
                _tag, _i1, _i2, prior_start, prior_end = opcodes[ordinal - 1]
                before_lines = post_lines[max(prior_start, prior_end - 2):prior_end]
            if ordinal + 1 < len(opcodes) and opcodes[ordinal + 1][0] == "equal":
                _tag, _i1, _i2, next_start, next_end = opcodes[ordinal + 1]
                after_lines = post_lines[next_start:min(next_end, next_start + 2)]
            identity = hashlib.sha256(
                path.encode("utf-8", "surrogateescape") + b"\0"
                + str(old_start + 1).encode() + b":" + str(old_end - old_start).encode() + b"\0"
                + str(new_start + 1).encode() + b":" + str(new_end - new_start).encode() + b"\0"
                + b"".join(old_image) + b"\0" + b"".join(post_image)
            ).hexdigest()[:16]
            width = max(1, len(post_image))
            block = {
                "id": f"{path}:{ordinal}:{identity}",
                "path": path,
                "pre_fix_span": [new_start + 1, new_start + width],
                "_pre_lines": old_image,
                "_post_lines": post_image,
                "_before_lines": before_lines,
                "_after_lines": after_lines,
                "_expected_index": new_start,
                "_pre_fix_anchor": True,
                "_post_exists": post_blob is not None,
            }
            if pre_fix_sha is not None:
                pre_fix_blob = _commit_blob(work, pre_fix_sha, path)
                _map_pre_fix_span(block, [] if pre_fix_blob is None else pre_fix_blob.splitlines(keepends=True))
            blocks.append(block)
    return blocks


def classify_surface_block(block: dict, current: bytes | None) -> str:
    lines = [] if current is None else current.splitlines(keepends=True)
    post_lines = block["_post_lines"]
    pre_lines = block["_pre_lines"]
    if post_lines:
        post_index = _block_image_index(lines, post_lines, block)
        if post_index is not None:
            block["_restore_index"] = post_index
            return "SURVIVED"
        if pre_lines:
            pre_index = _block_image_index(lines, pre_lines, block)
            if pre_index is not None:
                block["_restore_index"] = pre_index
                return "REVERTED"
        else:
            anchor = _block_anchor_index(lines, block)
            if anchor is not None:
                block["_restore_index"] = anchor
                return "REVERTED"
        return "EVOLVED"
    pre_index = _block_image_index(lines, pre_lines, block)
    if pre_index is not None:
        block["_restore_index"] = pre_index
        return "REVERTED"
    anchor = _block_anchor_index(lines, block)
    if anchor is not None:
        block["_restore_index"] = anchor
        return "SURVIVED"
    return "EVOLVED"


def finding_targets_block(block: dict, findings: list[dict]) -> bool:
    start, end = block["pre_fix_span"]
    for finding in findings:
        path = finding.get("path", finding.get("file"))
        line = finding.get("line")
        if path == block["path"] and isinstance(line, int) and not isinstance(line, bool):
            if start <= line <= end:
                return True
    return False


def _read_triggering_findings(devlyn: pathlib.Path, origin_phase: str) -> tuple[list[dict], str]:
    name = "build_gate.findings.jsonl" if origin_phase == "build_gate" else "verify-merged.findings.jsonl"
    path = devlyn / name
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise SystemExit(f"BLOCKED:closure-durability-receipt: {path}: {exc}") from exc
    findings = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            finding = loads_strict_json(line.decode("utf-8"))
        except (UnicodeError, ValueError) as exc:
            raise SystemExit(
                f"BLOCKED:closure-durability-receipt: {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(finding, dict):
            raise SystemExit(
                f"BLOCKED:closure-durability-receipt: {path}:{line_number} is not an object"
            )
        findings.append(finding)
    return findings, hashlib.sha256(raw).hexdigest()


def _worktree_file(work: pathlib.Path, path: str) -> bytes | None:
    target = work / path
    if target.is_file() or target.is_symlink():
        return target.read_bytes()
    return None


def _restored_files(work: pathlib.Path, blocks: list[dict]) -> dict[str, bytes | None]:
    desired = {}
    for path in sorted({block["path"] for block in blocks}):
        current = _worktree_file(work, path)
        lines = [] if current is None else current.splitlines(keepends=True)
        path_blocks = sorted(
            (block for block in blocks if block["path"] == path),
            key=lambda block: block["_restore_index"], reverse=True,
        )
        for block in path_blocks:
            index = block["_restore_index"]
            pre_lines = block["_pre_lines"]
            post_lines = block["_post_lines"]
            if lines[index:index + len(pre_lines)] != pre_lines:
                raise SystemExit(
                    f"BLOCKED:closure-durability-apply: restore anchor changed for {block['id']}"
                )
            lines[index:index + len(pre_lines)] = post_lines
        desired[path] = b"".join(lines) if lines or any(
            block["_post_exists"] for block in path_blocks
        ) else None
    return desired


def _restore_patch(work: pathlib.Path, desired: dict[str, bytes | None]) -> bytes:
    parts = []
    with tempfile.TemporaryDirectory(prefix="closure-durability-") as tmp:
        root = pathlib.Path(tmp)
        for path, wanted in desired.items():
            old = root / "old" / path
            new = root / "new" / path
            current = _worktree_file(work, path)
            if current is not None:
                old.parent.mkdir(parents=True, exist_ok=True)
                old.write_bytes(current)
            if wanted is not None:
                new.parent.mkdir(parents=True, exist_ok=True)
                new.write_bytes(wanted)
            old_arg = str(old.relative_to(root)) if current is not None else "/dev/null"
            new_arg = str(new.relative_to(root)) if wanted is not None else "/dev/null"
            proc = subprocess.run(
                ["git", "diff", "--no-index", "--binary", "--src-prefix=a/", "--dst-prefix=b/",
                 "--", old_arg, new_arg],
                cwd=root, capture_output=True, check=False,
            )
            if proc.returncode not in (0, 1):
                detail = os.fsdecode(proc.stderr or proc.stdout).strip() or "git diff --no-index failed"
                raise SystemExit(f"BLOCKED:closure-durability-apply: {detail}")
            patch = proc.stdout
            encoded = path.encode("utf-8", "surrogateescape")
            rewritten = []
            header = True
            for line in patch.splitlines(keepends=True):
                if line.startswith(b"@@ ") or line.startswith(b"GIT binary patch"):
                    header = False
                if header and line.startswith((b"diff --git ", b"--- ", b"+++ ", b"Binary files ")):
                    for prefix in (b"a/old/", b"a/new/"):
                        line = line.replace(prefix + encoded, b"a/" + encoded)
                    for prefix in (b"b/old/", b"b/new/"):
                        line = line.replace(prefix + encoded, b"b/" + encoded)
                rewritten.append(line)
            parts.append(b"".join(rewritten))
    return b"".join(parts)


def _tracked_status(work: pathlib.Path) -> bytes:
    return _git_output(work, "status", "--porcelain=v1", "-z", "--untracked-files=no")


def _apply_restore_patch(work: pathlib.Path, patch: bytes, paths: list[str]) -> None:
    before = _tracked_status(work)
    if before:
        raise SystemExit("BLOCKED:closure-durability-apply: tracked worktree/index is not clean")
    check = subprocess.run(
        ["git", "apply", "--check", "--index", "-"], cwd=work,
        input=patch, capture_output=True, check=False,
    )
    if check.returncode != 0:
        if _tracked_status(work) != before:
            raise SystemExit("BLOCKED:closure-durability-apply: preflight mutated tracked state")
        detail = os.fsdecode(check.stderr or check.stdout).strip() or "git apply --check failed"
        raise SystemExit(f"BLOCKED:closure-durability-apply: {detail}")
    apply = subprocess.run(
        ["git", "apply", "--index", "-"], cwd=work,
        input=patch, capture_output=True, check=False,
    )
    if apply.returncode != 0:
        subprocess.run(
            ["git", "restore", "--source=HEAD", "--staged", "--worktree", "--", *paths],
            cwd=work, capture_output=True, check=False,
        )
        if _tracked_status(work) != before:
            raise SystemExit("BLOCKED:closure-durability-apply: failed apply left partial mutation")
        detail = os.fsdecode(apply.stderr or apply.stdout).strip() or "git apply failed"
        raise SystemExit(f"BLOCKED:closure-durability-apply: {detail}")


def _write_json_atomic(path: pathlib.Path, value: dict) -> bytes:
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".tmp.")
    try:
        with open(fd, "wb") as handle:
            handle.write(raw)
        pathlib.Path(tmp_name).replace(path)
    except BaseException:
        pathlib.Path(tmp_name).unlink(missing_ok=True)
        raise
    return raw


def _surface_durability_ledger(state: dict) -> list[dict]:
    phases = state.setdefault("phases", {})
    surface = phases.get("surface_close")
    if surface is None:
        surface = {}
        phases["surface_close"] = surface
    if not isinstance(surface, dict):
        raise SystemExit("BLOCKED:closure-durability-receipt: phases.surface_close is malformed")
    ledger = surface.setdefault("durability", [])
    if not isinstance(ledger, list) or any(not isinstance(item, dict) for item in ledger):
        raise SystemExit("BLOCKED:closure-durability-receipt: durability ledger is malformed")
    return ledger


def _receipt_blocks(blocks: list[dict]) -> list[dict]:
    return [{
        "id": block["id"],
        "path": block["path"],
        "pre_fix_span": block["pre_fix_span"],
        "classification": block["classification"],
        "finding_targeted": block["finding_targeted"],
        "action": block["action"],
    } for block in blocks]


def _rollback_durability_creation(
    work: pathlib.Path, receipt_path: pathlib.Path, state: dict, receipt: dict,
) -> None:
    restore_sha = receipt.get("restore_commit_sha")
    fix_sha = receipt["fix_commit_sha"]
    restored_paths = sorted({
        block["path"] for block in receipt.get("blocks", [])
        if block.get("action") == "restored"
    })
    if restore_sha is not None:
        head = _git_output(work, "rev-parse", "HEAD").decode().strip()
        if head != restore_sha:
            raise SystemExit("BLOCKED:closure-durability-rollback: restore commit is no longer HEAD")
        restore = subprocess.run(
            ["git", "restore", f"--source={fix_sha}", "--staged", "--worktree", "--", *restored_paths],
            cwd=work, capture_output=True, check=False,
        )
        if restore.returncode != 0:
            detail = os.fsdecode(restore.stderr or restore.stdout).strip() or "git restore failed"
            raise SystemExit(f"BLOCKED:closure-durability-rollback: {detail}")
        update = subprocess.run(
            ["git", "update-ref", "HEAD", fix_sha, restore_sha],
            cwd=work, capture_output=True, check=False,
        )
        if update.returncode != 0:
            subprocess.run(
                ["git", "restore", f"--source={restore_sha}", "--staged", "--worktree", "--",
                 *restored_paths], cwd=work, capture_output=True, check=False,
            )
            detail = os.fsdecode(update.stderr or update.stdout).strip() or "git update-ref failed"
            raise SystemExit(f"BLOCKED:closure-durability-rollback: {detail}")
    receipt_path.unlink(missing_ok=True)
    ledger = _surface_durability_ledger(state)
    ledger[:] = [
        item for item in ledger
        if not (item.get("round") == receipt["round"]
                and item.get("origin_phase") == receipt["origin_phase"])
    ]
    head = _git_output(work, "rev-parse", "HEAD").decode().strip()
    if head != fix_sha or _tracked_status(work):
        raise SystemExit("BLOCKED:closure-durability-rollback: rollback left partial mutation")


def _validate_durability_receipt(
    work: pathlib.Path, devlyn: pathlib.Path, state: dict, origin_phase: str, round_: int,
    receipt_path: pathlib.Path, findings_digest: str, ledger: list[dict],
) -> dict | None:
    matches = [item for item in ledger if item.get("round") == round_]
    if not receipt_path.exists() and not matches:
        return None
    if not receipt_path.is_file() or len(matches) != 1:
        raise SystemExit(
            f"BLOCKED:closure-durability-receipt: missing or duplicate round {round_} receipt/ledger"
        )
    try:
        raw = receipt_path.read_bytes()
        receipt = loads_strict_json(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit(f"BLOCKED:closure-durability-receipt: {receipt_path}: {exc}") from exc
    required = {
        "schema_version", "round", "origin_phase", "triggering_findings_sha256",
        "surface_close_commit_sha", "pre_fix_sha", "fix_commit_sha", "post_restore_sha",
        "restore_commit_sha", "blocks",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise SystemExit("BLOCKED:closure-durability-receipt: receipt fields are stale or malformed")
    surface = ((state.get("phases") or {}).get("surface_close") or {})
    expected_surface_sha = surface.get("post_sha") if isinstance(surface, dict) else None
    if (
        receipt["schema_version"] != 1 or receipt["round"] != round_
        or receipt["origin_phase"] != origin_phase
        or receipt["triggering_findings_sha256"] != findings_digest
        or receipt["surface_close_commit_sha"] != expected_surface_sha
    ):
        raise SystemExit("BLOCKED:closure-durability-receipt: receipt metadata is stale")
    blocks = receipt.get("blocks")
    if not isinstance(blocks, list):
        raise SystemExit("BLOCKED:closure-durability-receipt: blocks must be an array")
    block_fields = {"id", "path", "pre_fix_span", "classification", "finding_targeted", "action"}
    for block in blocks:
        span = block.get("pre_fix_span") if isinstance(block, dict) else None
        if (
            not isinstance(block, dict) or set(block) != block_fields
            or not isinstance(block.get("id"), str) or not isinstance(block.get("path"), str)
            or not isinstance(span, list) or len(span) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in span)
            or span[0] > span[1]
            or block.get("classification") not in {"SURVIVED", "REVERTED", "EVOLVED"}
            or not isinstance(block.get("finding_targeted"), bool)
            or block.get("action") not in {"restored", "finding-targeted", "none"}
        ):
            raise SystemExit("BLOCKED:closure-durability-receipt: block entry is malformed")
    sha_fields = ("pre_fix_sha", "fix_commit_sha", "post_restore_sha")
    if any(not isinstance(receipt.get(field), str) or not re.fullmatch(r"[0-9a-f]{40,64}", receipt[field])
           for field in sha_fields):
        raise SystemExit("BLOCKED:closure-durability-receipt: commit sha is malformed")
    restore_sha = receipt.get("restore_commit_sha")
    if restore_sha is not None and (
        not isinstance(restore_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", restore_sha)
    ):
        raise SystemExit("BLOCKED:closure-durability-receipt: restore_commit_sha is malformed")
    head = _git_output(work, "rev-parse", "HEAD").decode().strip()
    if head != receipt["post_restore_sha"] or (restore_sha is not None and restore_sha != head):
        raise SystemExit("BLOCKED:closure-durability-receipt: receipt does not match current HEAD")
    if restore_sha is None and receipt["fix_commit_sha"] != receipt["post_restore_sha"]:
        raise SystemExit("BLOCKED:closure-durability-receipt: no-op receipt changed HEAD")
    if restore_sha is not None:
        parent = _git_output(work, "rev-parse", f"{restore_sha}^").decode().strip()
        subject = _git_output(work, "show", "-s", "--format=%s", restore_sha).decode().strip()
        if parent != receipt["fix_commit_sha"] or subject != f"chore(pipeline): closure-restore round {round_}":
            raise SystemExit("BLOCKED:closure-durability-receipt: restore commit evidence is stale")
    fix_parent = _git_output(work, "rev-parse", f"{receipt['fix_commit_sha']}^").decode().strip()
    fix_subject = _git_output(
        work, "show", "-s", "--format=%s", receipt["fix_commit_sha"]
    ).decode().strip()
    if fix_parent != receipt["pre_fix_sha"] or fix_subject != f"chore(pipeline): implement fix round {round_}":
        raise SystemExit("BLOCKED:closure-durability-receipt: fix checkpoint evidence is stale")
    receipt_rel = f"{devlyn_prefix(work, devlyn)}/{receipt_path.name}"
    expected_ledger = {
        "round": round_,
        "origin_phase": origin_phase,
        "receipt_path": receipt_rel,
        "receipt_sha256": hashlib.sha256(raw).hexdigest(),
        "restore_commit_sha": restore_sha,
    }
    if matches[0] != expected_ledger:
        raise SystemExit("BLOCKED:closure-durability-receipt: ledger entry is stale")
    return receipt


def enforce_closure_durability_reentry(
    work: pathlib.Path, devlyn: pathlib.Path, state: dict, origin_phase: str, round_: int,
    *, require_existing: bool = False,
) -> dict | None:
    if round_ < 1:
        return None
    if origin_phase not in VALID_TRIGGERS:
        raise SystemExit(f"BLOCKED:closure-durability-receipt: invalid origin phase {origin_phase!r}")
    findings, findings_digest = _read_triggering_findings(devlyn, origin_phase)
    ledger = _surface_durability_ledger(state)
    receipt_path = devlyn / f"closure-durability.round-{round_}.json"
    existing = _validate_durability_receipt(
        work, devlyn, state, origin_phase, round_, receipt_path, findings_digest, ledger,
    )
    if existing is not None:
        return existing
    if require_existing:
        raise SystemExit(
            f"BLOCKED:closure-durability-receipt: round {round_} checkpoint receipt is missing"
        )

    if any(item.get("round") == round_ or item.get("origin_phase") == origin_phase
           and item.get("receipt_path") == f"{devlyn_prefix(work, devlyn)}/{receipt_path.name}"
           for item in ledger):
        raise SystemExit("BLOCKED:closure-durability-receipt: append-only ledger collision")
    if _tracked_status(work):
        raise SystemExit("BLOCKED:closure-durability-apply: tracked worktree/index is not clean")
    fix_commit_sha = _git_output(work, "rev-parse", "HEAD").decode().strip()
    fix_subject = _git_output(work, "show", "-s", "--format=%s", fix_commit_sha).decode().strip()
    if fix_subject != f"chore(pipeline): implement fix round {round_}":
        raise SystemExit(
            f"BLOCKED:closure-durability-receipt: expected fix checkpoint round {round_}, got {fix_subject!r}"
        )
    pre_fix_sha = _git_output(work, "rev-parse", f"{fix_commit_sha}^").decode().strip()
    surface = ((state.get("phases") or {}).get("surface_close") or {})
    surface_commit_sha = surface.get("post_sha") if isinstance(surface, dict) else None
    blocks = surface_change_blocks(work, state, pre_fix_sha)
    restore_blocks = []
    for block in blocks:
        classification = classify_surface_block(block, _worktree_file(work, block["path"]))
        targeted = finding_targets_block(block, findings)
        block["classification"] = classification
        block["finding_targeted"] = targeted
        if classification == "REVERTED" and not targeted:
            block["action"] = "restored"
            restore_blocks.append(block)
        elif targeted:
            block["action"] = "finding-targeted"
        else:
            block["action"] = "none"

    restore_commit_sha = None
    if restore_blocks:
        desired = _restored_files(work, restore_blocks)
        patch = _restore_patch(work, desired)
        if not patch:
            raise SystemExit("BLOCKED:closure-durability-apply: restored blocks produced an empty patch")
        paths = sorted(desired)
        _apply_restore_patch(work, patch, paths)
        commit = subprocess.run(
            ["git", "commit", "-m", f"chore(pipeline): closure-restore round {round_}"],
            cwd=work, capture_output=True, check=False,
        )
        if commit.returncode != 0:
            subprocess.run(
                ["git", "restore", "--source=HEAD", "--staged", "--worktree", "--", *paths],
                cwd=work, capture_output=True, check=False,
            )
            detail = os.fsdecode(commit.stderr or commit.stdout).strip() or "git commit failed"
            raise SystemExit(f"BLOCKED:closure-durability-apply: {detail}")
        restore_commit_sha = _git_output(work, "rev-parse", "HEAD").decode().strip()
    post_restore_sha = _git_output(work, "rev-parse", "HEAD").decode().strip()
    receipt = {
        "schema_version": 1,
        "round": round_,
        "origin_phase": origin_phase,
        "triggering_findings_sha256": findings_digest,
        "surface_close_commit_sha": surface_commit_sha,
        "pre_fix_sha": pre_fix_sha,
        "fix_commit_sha": fix_commit_sha,
        "post_restore_sha": post_restore_sha,
        "restore_commit_sha": restore_commit_sha,
        "blocks": _receipt_blocks(blocks),
    }
    try:
        raw = _write_json_atomic(receipt_path, receipt)
        ledger.append({
            "round": round_,
            "origin_phase": origin_phase,
            "receipt_path": f"{devlyn_prefix(work, devlyn)}/{receipt_path.name}",
            "receipt_sha256": hashlib.sha256(raw).hexdigest(),
            "restore_commit_sha": restore_commit_sha,
        })
    except BaseException as exc:
        _rollback_durability_creation(work, receipt_path, state, receipt)
        raise SystemExit(f"BLOCKED:closure-durability-receipt: {exc}") from exc
    return receipt


def _persist_durability_event(
    work: pathlib.Path, devlyn: pathlib.Path, state: dict, state_path: pathlib.Path,
    origin_phase: str, round_: int, writer=write_state,
) -> dict:
    receipt_path = devlyn / f"closure-durability.round-{round_}.json"
    existed = receipt_path.exists()
    receipt = enforce_closure_durability_reentry(
        work, devlyn, state, origin_phase, round_,
    )
    try:
        writer(state_path, state)
    except BaseException:
        if not existed:
            _rollback_durability_creation(work, receipt_path, state, receipt)
        raise
    return receipt


def clear_verify_round_artifacts(devlyn: pathlib.Path) -> None:
    # The per-round reset contract covers files, not just JSON fields: a
    # VERIFY fix-loop respawn reuses the same .devlyn, so a prior round's
    # findings/stdout would otherwise read as current-round spawn evidence in
    # verify-merge-findings.py (iter-0060 R0 finding).
    # verify*.jsonl (not just *.findings.jsonl): judge-specific files like
    # verify.findings.judge-codex.jsonl end in .judge-<engine>.jsonl.
    # The judge suffixes cover harness-owned stdout/stderr captures and the
    # collector-written pair-judge.summary.json, without matching prompts.
    for pattern in ("verify*.jsonl", "*-judge.stdout", "*-judge.stderr", "*-judge.summary.json"):
        for path in devlyn.glob(pattern):
            path.unlink()
    (devlyn / "verify-merge.summary.json").unlink(missing_ok=True)


def is_plan_dispatch_receipt(entry: dict) -> bool:
    return all(field in entry for field in PLAN_RECEIPT_FIELDS)


def append_phase_history(entry: dict, phase: str) -> None:
    if entry.get("started_at") is None:
        return
    history = entry.get("history")
    if not isinstance(history, list):
        history = []
    if phase == "plan" and is_plan_dispatch_receipt(entry):
        fields = PLAN_RECEIPT_FIELDS + (
            ("invocation_receipt",) if "invocation_receipt" in entry else ()
        )
    elif phase in WORKER_SESSION_ARTIFACT_PHASES and "invocation_receipt" in entry:
        fields = (
            "started_at", "verdict", "completed_at", "duration_ms",
            "invocation_receipt",
        ) + (("role_argv",) if "role_argv" in entry else ())
    elif phase == "verify":
        fields = ("started_at", "verdict", "completed_at", "duration_ms", "round", "engine", "role_evidence")
    else:
        fields = ("started_at", "verdict", "completed_at", "duration_ms")
    history.append({field: entry.get(field) for field in fields})
    entry["history"] = history


def role_config_module():
    return runpy.run_path(pathlib.Path(__file__).with_name("role-config.py"))


def bind_worker_role_argv(state, phase, entry, devlyn, receipt):
    if phase not in {"implement", "cleanup"}:
        return None
    helper = role_config_module()
    resolution = helper["snapshot"](state)
    effort = resolution["roles"]["worker"]["effort_requested"] if resolution else None
    if effort is None:
        return None
    path = devlyn / f"{phase}.argv.{entry['round']}.json"
    if path.is_symlink() or not path.is_file():
        raise ValueError("explicit worker effort requires the retained native argv array")
    raw = path.read_bytes()
    argv = helper["loads"](raw)
    if not isinstance(argv, list) or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("worker argv must be an array of strings")
    if hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest() != receipt["argv_sha256"]:
        raise ValueError("worker argv differs from the actual invocation receipt")
    values = [argv[i + 1] for i, arg in enumerate(argv[:-1]) if arg in {"-c", "--config"}]
    efforts = [value.split("=", 1)[1].strip('"') for value in values if value.startswith("model_reasoning_effort=")]
    if efforts != [effort]:
        raise ValueError("worker effort differs from the frozen explicit selection")
    return {"path": ".devlyn/" + path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "effort_requested": effort, "identity_basis": "invocation-argv"}


def freeze_roles(state: dict, work: pathlib.Path, default_engine: str) -> dict:
    helper = role_config_module()
    existing = helper["snapshot"](state)
    if existing is not None:
        return existing
    if any(isinstance(entry, dict) and entry.get("started_at") for entry in state.get("phases", {}).values()):
        raise ValueError("BLOCKED:invalid-engine-config: roles must be frozen before phase dispatch")
    resolved = helper["resolve"](
        work, default_engine,
        flag_engine=state.get("engine") if state.get("engine_source") == "flag" else None,
        run_input=state.get("role_config_input"), no_pair=state.get("role_no_pair", False),
    )
    state["role_resolution"] = resolved
    state["engine"], state["engine_source"] = resolved["legacy_engine"], resolved["legacy_source"]
    return resolved


def do_spawn(state: dict, phase: str, round_: int, triggered_by: str | None,
             pre_sha: str | None, engine: str | None, model: str | None, *,
             input_patch_sha256: str | None = None,
             prompt_sha256: str | None = None,
             untracked_before: list[str] | None = None,
             devlyn: pathlib.Path | None = None) -> None:
    if phase in {"implement", "cleanup", "verify"} and "role_resolution" in state:
        resolution = role_config_module()["snapshot"](state)
        selected = resolution["roles"]["primary_judge" if phase == "verify" else "worker"]
        if engine is not None and engine != selected["engine"]:
            raise SystemExit("BLOCKED:role-selection-mismatch: phase engine differs from frozen selection")
        engine = selected["engine"]
        wanted_model = selected["model_requested"]
        if wanted_model is not None and model is not None and wanted_model != model:
            raise SystemExit("BLOCKED:role-selection-mismatch: phase model differs from frozen selection")
        model = wanted_model or model
    # Merge, don't replace: a phase-gated large run's `exec` progress (or any
    # other field this script doesn't own) survives a fix-loop respawn.
    phases_value = state.get("phases")
    entry = phases_value.get(phase) if isinstance(phases_value, dict) else None
    validate_plan_output(state, devlyn, phase)
    if phase == "plan":
        history = entry.get("history", []) if isinstance(entry, dict) else []
        if not isinstance(history, list):
            raise SystemExit("error: phases.plan.history must be an array")
        dispatch_count = len(history) + int(
            isinstance(entry, dict) and entry.get("started_at") is not None
        )
        if dispatch_count >= PLAN_MAX_DISPATCHES:
            raise SystemExit("BLOCKED:plan-respawn-exhausted")
        if round_ != dispatch_count:
            raise SystemExit(
                f"BLOCKED:plan-round-nonmonotonic: expected={dispatch_count} supplied={round_}"
            )
        if not isinstance(engine, str) or not engine:
            raise SystemExit("error: phases.plan spawn requires --engine")
        if not isinstance(model, str) or not model:
            raise SystemExit("error: phases.plan spawn requires --model")
        if prompt_sha256 is None or not SHA256_RE.fullmatch(prompt_sha256):
            raise SystemExit("error: phases.plan spawn requires --prompt-sha256")
        if dispatch_count > 0 and triggered_by is None:
            raise SystemExit("error: phases.plan re-spawn requires --triggered-by")
    if phase == "surface_close" and engine != "claude":
        raise SystemExit("error: phases.surface_close spawn requires --engine claude")
    if phase == "surface_close" and not model:
        raise SystemExit("error: phases.surface_close spawn requires --model")
    if phase == "surface_close" and isinstance(entry, dict) and (
        entry.get("started_at") is not None or entry.get("skipped_reason") is not None
    ):
        raise SystemExit("error: phases.surface_close is one-shot and cannot be re-entered")
    if phase == "surface_close":
        if pre_sha is None:
            raise SystemExit("error: phases.surface_close spawn requires --pre-sha")
        if input_patch_sha256 is None or not SHA256_RE.fullmatch(input_patch_sha256):
            raise SystemExit("error: phases.surface_close spawn requires --input-patch-sha256")
        if prompt_sha256 is None or not SHA256_RE.fullmatch(prompt_sha256):
            raise SystemExit("error: phases.surface_close spawn requires --prompt-sha256")
        if untracked_before is None:
            raise SystemExit("error: phases.surface_close spawn requires --untracked-before-json")
    elif phase == "plan":
        if input_patch_sha256 is not None or untracked_before is not None:
            raise SystemExit("error: SURFACE_CLOSE metadata is invalid for this phase")
    else:
        if input_patch_sha256 is not None or untracked_before is not None:
            raise SystemExit("error: SURFACE_CLOSE metadata is invalid for this phase")
        if prompt_sha256 is not None and SHA256_RE.fullmatch(prompt_sha256) is None:
            raise SystemExit("error: --prompt-sha256 must be a lowercase SHA-256 digest")
        requested_engine = (
            engine if isinstance(engine, str) and engine else
            entry.get("engine") if isinstance(entry, dict) else
            state.get("engine")
        )
        if (
            state.get("version") == "3.0"
            and requested_engine == "codex"
            and phase in WORKER_SESSION_ARTIFACT_PHASES
            and prompt_sha256 is None
        ):
            raise SystemExit(
                f"error: schema-v3 Codex phases.{phase} spawn requires --prompt-sha256"
            )
        requested_model = (
            model if isinstance(model, str) and model else
            entry.get("model_requested") if isinstance(entry, dict) else None
        )
        if (
            state.get("version") == "3.0"
            and requested_engine == "codex"
            and phase in WORKER_SESSION_ARTIFACT_PHASES
            and not requested_model
        ):
            raise SystemExit(
                f"error: schema-v3 Codex phases.{phase} spawn requires --model"
            )
    phases = state.setdefault("phases", {})
    if not isinstance(entry, dict):
        entry = {}
        phases[phase] = entry
    if entry.get("started_at") is not None and entry.get("completed_at") is None:
        raise SystemExit(
            f"error: phases.{phase} has an open span — complete it before respawn"
        )
    append_phase_history(entry, phase)
    if phase in WORKER_SESSION_ARTIFACT_PHASES:
        entry.pop("invocation_receipt", None)
        entry.pop("role_argv", None)
    entry["started_at"] = now_iso()
    entry["completed_at"] = None
    entry["duration_ms"] = None
    entry["round"] = round_
    entry["triggered_by"] = triggered_by
    entry["verdict"] = None
    entry["artifacts"] = {"findings_file": None, "log_file": None}
    entry["sub_verdicts"] = None
    if phase == "verify":
        entry["judge_durations_ms"] = None
        entry.pop("role_evidence", None)
    if engine is not None:
        entry["engine"] = engine
    elif (
        state.get("version") == "3.0"
        and "engine" not in entry
        and isinstance(state.get("engine"), str)
        and state["engine"]
    ):
        entry["engine"] = state["engine"]
    if model is not None:
        entry["model_requested"] = model
    else:
        entry.setdefault("model_requested", None)
    entry.pop("model", None)
    entry["model_effective"] = None
    if pre_sha is not None:
        entry["pre_sha"] = pre_sha
    if prompt_sha256 is not None:
        entry["prompt_sha256"] = prompt_sha256
    if phase == "surface_close":
        entry["input_patch_sha256"] = input_patch_sha256
        entry["untracked_before"] = untracked_before


def do_surface_skip(state: dict) -> None:
    phases = state.setdefault("phases", {})
    existing = phases.get("surface_close")
    if isinstance(existing, dict) and (
        existing.get("started_at") is not None or existing.get("skipped_reason") is not None
    ):
        raise SystemExit("error: phases.surface_close is one-shot and cannot be re-entered")
    phases["surface_close"] = {
        "started_at": None,
        "completed_at": now_iso(),
        "duration_ms": 0,
        "round": 0,
        "triggered_by": None,
        "verdict": None,
        "engine": "claude",
        "model_requested": None,
        "model_effective": None,
        "artifacts": {"findings_file": None, "log_file": None},
        "sub_verdicts": None,
        "skipped_reason": SURFACE_SKIP_REASON,
    }


def do_complete(state: dict, phase: str, verdict: str | None,
                 post_sha: str | None, findings_file: str | None, log_file: str | None,
                 engine: str | None, model: str | None,
                 engine_session_log: str | None = None,
                 devlyn: pathlib.Path | None = None,
                 work: pathlib.Path | None = None) -> str | None:
    phases = state.setdefault("phases", {})
    entry = phases.get(phase)
    if not isinstance(entry, dict) or not entry.get("started_at"):
        raise SystemExit(f"error: phases.{phase} was never spawned (no started_at) — cannot complete")
    if phase == "verify" and verdict is not None:
        raise SystemExit(
            "error: phases.verify.verdict is owned by verify-merge-findings.py "
            "--write-state; do not pass --verdict to complete for this phase"
        )
    if entry.get("completed_at") is not None:
        raise SystemExit(
            f"error: phases.{phase} already completed — respawn before completing again"
        )
    if phase != "plan":
        validate_plan_output(state, devlyn, phase)
    if phase == "final_report":
        report_digest = final_report_digest(state, devlyn, log_file)
        log_file = ".devlyn/final-report.md"
    if phase == "plan" and entry.get("prompt_sha256") is not None:
        missing = [field for field in PLAN_SPAWN_RECEIPT_FIELDS if field not in entry]
        if missing:
            raise SystemExit(
                "error: phases.plan spawn receipt is incomplete: " + ",".join(missing)
            )
        if engine is not None and engine != entry["engine"]:
            raise SystemExit("error: phases.plan completion cannot replace spawn engine")
        if model is not None and model != entry["model_requested"]:
            raise SystemExit("error: phases.plan completion cannot replace requested model")
    if state.get("version") == "3.0" and phase != "plan":
        if engine is not None and engine != entry.get("engine"):
            raise SystemExit(f"error: phases.{phase} completion cannot replace spawn engine")
        if model is not None and model != entry.get("model_requested"):
            raise SystemExit(
                f"error: phases.{phase} completion cannot replace requested model"
            )
    bind_process_evidence(state, phase, verdict, devlyn, work)
    started = parse_iso(entry["started_at"])
    now = now_ms()
    entry["completed_at"] = now_iso(now)
    entry["duration_ms"] = max(0, round((now - started).total_seconds() * 1000))
    if phase == "verify":
        if entry.get("verdict") is None:
            raise SystemExit(
                "error: phases.verify.verdict is still null — run "
                "verify-merge-findings.py --write-state before complete"
            )
    elif verdict is not None:
        entry["verdict"] = verdict
    else:
        raise SystemExit(f"error: --verdict is required to complete phases.{phase}")
    if phase == "plan":
        if state.get("version") == "3.0":
            bind_plan_output(state, devlyn)
        else:
            entry.setdefault("output_sha256", None)
    if phase == "final_report":
        entry["output_sha256"] = report_digest
    if findings_file is not None or log_file is not None:
        artifacts = entry.setdefault("artifacts", {"findings_file": None, "log_file": None})
        if findings_file is not None:
            artifacts["findings_file"] = findings_file
        if log_file is not None:
            artifacts["log_file"] = log_file
    if engine is not None and phase != "plan":
        entry["engine"] = engine
    if model is not None and phase != "plan":
        entry["model_requested"] = model
    elif phase != "plan":
        entry.setdefault("model_requested", None)
    entry.pop("model", None)

    artifact_phase = WORKER_SESSION_ARTIFACT_PHASES.get(phase)
    retained_session = None
    if devlyn is not None and artifact_phase is not None:
        candidate = devlyn / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
        if candidate.is_file():
            retained_session = candidate

    attestation_error = None
    schema_v3_worker = (
        state.get("version") == "3.0"
        and artifact_phase is not None
        and entry.get("engine") == "codex"
    )
    if schema_v3_worker and retained_session is None:
        expected_session = (
            devlyn / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
            if devlyn is not None else
            pathlib.Path(".devlyn") / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
        )
        attestation_error = (
            "BLOCKED:model-attestation-failed: canonical retained worker session is missing: "
            f"{expected_session}"
        )
    if (
        attestation_error is None
        and schema_v3_worker
        and engine_session_log is not None
        and pathlib.Path(engine_session_log).resolve() != retained_session.resolve()
    ):
        attestation_error = (
            "BLOCKED:model-attestation-failed: --engine-session-log must be the canonical "
            f"phase/round session {retained_session}"
        )
    if attestation_error is not None:
        entry["model_effective"] = None
    elif engine_session_log is None:
        entry["model_effective"] = None
        if retained_session is not None:
            attestation_error = (
                "BLOCKED:model-attestation-failed: --engine-session-log is required because "
                f"retained worker session exists: {retained_session}"
            )
    elif schema_v3_worker:
        receipt_path = devlyn / f"{artifact_phase}.invocation.{entry.get('round')}.json"
        try:
            receipt = invocation_receipt_module().validate_receipt(
                work.resolve(), receipt_path,
                run_id=state.get("run_id"),
                phase=phase,
                round_=entry.get("round"),
                model=entry.get("model_requested"),
                prompt_sha256=entry.get("prompt_sha256"),
                session_path=retained_session,
            )
            if receipt["exit_code"] != 0:
                raise invocation_receipt_module().ReceiptError(
                    f"Codex invocation exited {receipt['exit_code']}"
                )
            role_argv = bind_worker_role_argv(state, phase, entry, devlyn, receipt)
            if role_argv is not None:
                entry["role_argv"] = role_argv
            entry["model_effective"] = None  # The receipt binds argv, not an observed model.
            entry["invocation_receipt"] = receipt
        except (OSError, UnicodeError, ValueError) as exc:
            entry["model_effective"] = None
            attestation_error = f"BLOCKED:invocation-receipt-invalid: {exc}"
    else:
        try:
            entry["model_effective"] = parse_effective_model(pathlib.Path(engine_session_log))
        except ValueError as exc:
            entry["model_effective"] = None
            attestation_error = f"BLOCKED:model-attestation-failed: {exc}"
        requested = entry.get("model_requested")
        effective = entry.get("model_effective")
        if attestation_error is None and requested is not None and requested != effective:
            attestation_error = (
                "BLOCKED:model-attestation-mismatch: "
                f"requested={requested} effective={effective}"
            )
    if attestation_error is not None:
        entry["verdict"] = "BLOCKED"
    if post_sha is not None:
        entry["post_sha"] = post_sha
    return attestation_error


def do_transition(
    state: dict,
    phase: str,
    next_phase: str,
    verdict: str | None,
    post_sha: str | None,
    findings_file: str | None,
    log_file: str | None,
    engine: str | None,
    model: str | None,
    engine_session_log: str | None,
    devlyn: pathlib.Path,
    next_round: int,
    next_triggered_by: str | None,
    next_pre_sha: str | None,
    next_engine: str | None,
    next_model: str | None,
    *,
    next_input_patch_sha256: str | None = None,
    next_prompt_sha256: str | None = None,
    next_untracked_before: list[str] | None = None,
    between=None,
    work: pathlib.Path | None = None,
) -> dict:
    """Validate complete + caller-selected spawn against a copy of state.

    The caller owns the next phase and every judgment-bearing argument.  This
    primitive only validates the requested edge and applies both lifecycle
    mutations to a detached candidate, which the CLI commits with one atomic
    state-file replacement.
    """
    if next_phase not in LEGAL_TRANSITIONS.get(phase, set()):
        raise SystemExit(f"error: illegal phase transition: {phase} -> {next_phase}")
    candidate = copy.deepcopy(state)
    attestation_error = do_complete(
        candidate, phase, verdict, post_sha, findings_file, log_file,
        engine, model, engine_session_log, devlyn, work,
    )
    if attestation_error is not None:
        raise SystemExit(attestation_error)
    if between is not None:
        between()
    do_spawn(
        candidate, next_phase, next_round, next_triggered_by,
        next_pre_sha, next_engine, next_model,
        input_patch_sha256=next_input_patch_sha256,
        prompt_sha256=next_prompt_sha256,
        untracked_before=next_untracked_before,
        devlyn=devlyn,
    )
    return candidate


def do_surface_adjudication_recovery(state: dict, devlyn: pathlib.Path) -> str | None:
    entry = surface_entry(state)
    attestation_error = do_complete(
        state, "surface_close", "BLOCKED", entry["pre_sha"], None,
        ".devlyn/surface-close.stdout", None, None,
        str(devlyn / "surface-close.output.json"), devlyn,
    )
    if attestation_error is not None:
        return attestation_error
    entry["verdict"] = None
    entry["skipped_reason"] = SURFACE_RECOVERY_REASON
    entry["continued_after_block"] = True
    return None


def final_report_self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        devlyn = work / ".devlyn"
        devlyn.mkdir()
        state_path = devlyn / "pipeline.state.json"
        report = devlyn / "final-report.md"
        script = pathlib.Path(__file__).resolve()
        archive = script.with_name("archive_run.py")
        run_id = "rs-final-report-0126"
        write_state(state_path, {"version": "3.0", "run_id": run_id, "engine": "claude", "phases": {}})
        command = [sys.executable, str(script), "--devlyn-dir", ".devlyn", "--phase", "final_report"]
        spawned = subprocess.run(command + ["spawn", "--round", "0"], cwd=work, capture_output=True, text=True)
        assert spawned.returncode == 0, spawned.stderr
        before = state_path.read_bytes()
        marker = f"<!-- devlyn:final-report run_id={run_id} -->\n"
        valid = (marker + "# Report\nPASS_WITH_ISSUES — retained LOW finding.\n").encode("utf-8")
        outside = work / "other.md"
        outside.write_bytes(valid)
        cases = (
            "missing-argument", "missing-file", "empty", "blank-body", "stale",
            "missing-marker", "duplicate-marker", "invalid-utf8", "directory", "symlink", "wrong-path",
        )
        for case in cases:
            if report.is_dir() and not report.is_symlink():
                report.rmdir()
            else:
                report.unlink(missing_ok=True)
            args = ["--log-file", ".devlyn/final-report.md"]
            if case == "missing-argument":
                args = []
            elif case == "empty":
                report.write_bytes(b"")
            elif case == "blank-body":
                report.write_text(marker + " \t\n", encoding="utf-8")
            elif case == "stale":
                report.write_bytes(valid.replace(run_id.encode(), b"another-run"))
            elif case == "missing-marker":
                report.write_bytes(b"# Report\nBLOCKED\n")
            elif case == "duplicate-marker":
                report.write_bytes(valid + marker.encode())
            elif case == "invalid-utf8":
                report.write_bytes(marker.encode() + b"\xff")
            elif case == "directory":
                report.mkdir()
            elif case == "symlink":
                report.symlink_to(outside)
            elif case == "wrong-path":
                report.write_bytes(valid)
                args = ["--log-file", str(outside)]
            result = subprocess.run(command + ["complete", "--verdict", "PASS_WITH_ISSUES", *args],
                                    cwd=work, capture_output=True, text=True)
            assert result.returncode == 1 and "BLOCKED:final-report-invalid" in result.stderr, (case, result)
            assert state_path.read_bytes() == before, case
        report.write_bytes(valid)
        result = subprocess.run(command + ["complete", "--verdict", "PASS_WITH_ISSUES", "--log-file", ".devlyn/final-report.md"],
                                cwd=work, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        completed_bytes = state_path.read_bytes()
        completed = read_state(state_path)
        final = completed["phases"]["final_report"]
        assert final["completed_at"] is not None and final["verdict"] == "PASS_WITH_ISSUES"
        assert final["artifacts"]["log_file"] == ".devlyn/final-report.md"
        assert final["output_sha256"] == hashlib.sha256(valid).hexdigest()
        archive_command = [sys.executable, str(archive), "--devlyn-dir", ".devlyn"]
        for case in ("missing", "altered", "null-digest", "malformed-digest", "wrong-path", "symlink"):
            candidate = copy.deepcopy(completed)
            report.unlink(missing_ok=True)
            report.write_bytes(valid)
            if case == "missing":
                report.unlink()
            elif case == "altered":
                report.write_bytes(valid + b"changed after completion\n")
            elif case in {"null-digest", "malformed-digest"}:
                candidate["phases"]["final_report"]["output_sha256"] = None if case == "null-digest" else "invalid"
            elif case == "wrong-path":
                candidate["phases"]["final_report"]["artifacts"]["log_file"] = str(outside)
            else:
                report.unlink()
                report.symlink_to(outside)
            write_state(state_path, candidate)
            before_archive = state_path.read_bytes()
            result = subprocess.run(archive_command, cwd=work, capture_output=True, text=True)
            assert result.returncode == 1 and "error: archive blocked:" in result.stderr, (case, result)
            assert state_path.read_bytes() == before_archive, case
            assert not (devlyn / "runs").exists(), case
            if case != "missing":
                assert report.is_symlink() if case == "symlink" else report.read_bytes() == (
                    valid + b"changed after completion\n" if case == "altered" else valid
                ), case
        report.unlink()
        report.write_bytes(valid)
        state_path.write_bytes(completed_bytes)
        result = subprocess.run(archive_command, cwd=work, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        target = devlyn / "runs" / run_id
        assert (target / "final-report.md").read_bytes() == valid
        assert (target / "pipeline.state.json").read_bytes() == completed_bytes
        assert not state_path.exists() and not report.exists()
        assert outside.read_bytes() == valid
    print("PASS iter-0126 final report: 11 invalid CLI completions preserve state; exact binding/archive; 6 archive refusals preserve artifacts")


def self_test() -> int:
    import time

    final_report_self_test()
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp); devlyn = work / ".devlyn"; devlyn.mkdir()
        helper = role_config_module()
        config = {"roles": {"worker": {"engine": "codex", "model": "gpt-6-astra", "effort": "high"},
                            "primary_judge": {"engine": "claude"}}}
        (devlyn / "engines.json").write_bytes(helper["encoded"](config))
        state = {"version": "3.0", "engine": "codex", "engine_source": "default", "phases": {}}
        frozen = freeze_roles(state, work, "codex")
        (devlyn / "engines.json").write_text('{"executor":"claude"}')
        assert freeze_roles(state, work, "codex") == frozen
        do_spawn(state, "verify", 0, None, None, None, None, devlyn=devlyn)
        assert state["engine"] == "codex" and state["phases"]["verify"]["engine"] == "claude"
        for phase in ("implement", "cleanup"):
            before = copy.deepcopy(state)
            try:
                do_spawn(state, phase, 0, None, None, "claude", None, devlyn=devlyn)
            except SystemExit:
                pass
            else:
                raise AssertionError("wrong worker engine accepted")
            assert state == before
        argv = ["--json", "-m", "gpt-6-astra", "-c", "model_reasoning_effort=high", "task"]
        receipt = {"argv_sha256": hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest()}
        path = devlyn / "implement.argv.0.json"
        path.write_text(json.dumps(argv))
        binding = bind_worker_role_argv(state, "implement", {"round": 0}, devlyn, receipt)
        assert binding["effort_requested"] == "high"
        path.write_text(json.dumps([*argv, "extra"]))
        try:
            bind_worker_role_argv(state, "implement", {"round": 0}, devlyn, receipt)
        except ValueError:
            pass
        else:
            raise AssertionError("modified worker argv accepted")
        assert bind_worker_role_argv(state, "build_gate", {}, devlyn, receipt) is None
    print("PASS explicit roles: frozen primary/worker routing and actual worker argv binding")

    try:
        loads_strict_json('{"process_evidence":null,"process_evidence":[]}')
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate pipeline state key was accepted")

    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp)
        state_path = devlyn / "pipeline.state.json"
        write_state(state_path, {"phases": {}})

        # Iter-0089 P-0089-1/2/6: PLAN authorization is a CLI-level,
        # state-derived ledger contract. Rejections must leave the actual
        # state file byte-identical, not merely preserve an in-memory copy.
        script = str(pathlib.Path(__file__).resolve())
        digest0 = hashlib.sha256(b"plan prompt round 0").hexdigest()
        digest1 = hashlib.sha256(b"plan prompt round 1").hexdigest()

        def plan_cli(*event_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable, script, "--devlyn-dir", str(devlyn),
                    "--phase", "plan", *event_args,
                ],
                capture_output=True, text=True, check=False,
            )

        def assert_plan_rejected_unchanged(
            expected_stderr: str, *event_args: str,
        ) -> None:
            before = state_path.read_bytes()
            before_hash = hashlib.sha256(before).hexdigest()
            result = plan_cli(*event_args)
            assert result.returncode != 0, result.stdout
            assert result.stderr.strip() == expected_stderr, result.stderr
            after = state_path.read_bytes()
            assert after == before
            assert hashlib.sha256(after).hexdigest() == before_hash

        required_spawn = (
            "spawn", "--round", "0", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", digest0,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --engine",
            "spawn", "--round", "0", "--model", "plan-test-model",
            "--prompt-sha256", digest0,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --model",
            "spawn", "--round", "0", "--engine", "claude",
            "--prompt-sha256", digest0,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --prompt-sha256",
            "spawn", "--round", "0", "--engine", "claude",
            "--model", "plan-test-model",
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan spawn requires --prompt-sha256",
            "spawn", "--round", "0", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", "ABC",
        )
        assert_plan_rejected_unchanged(
            "BLOCKED:plan-round-nonmonotonic: expected=0 supplied=1",
            "spawn", "--round", "1", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", digest0,
        )

        result = plan_cli(*required_spawn)
        assert result.returncode == 0, result.stderr
        plan0 = read_state(state_path)["phases"]["plan"]
        assert {field: plan0[field] for field in PLAN_SPAWN_RECEIPT_FIELDS} == {
            "round": 0,
            "started_at": plan0["started_at"],
            "triggered_by": None,
            "engine": "claude",
            "model_requested": "plan-test-model",
            "prompt_sha256": digest0,
        }
        result = plan_cli("complete", "--verdict", "NEEDS_WORK")
        assert result.returncode == 0, result.stderr
        completed0 = read_state(state_path)["phases"]["plan"]
        assert all(field in completed0 for field in PLAN_RECEIPT_FIELDS)
        assert completed0["model_effective"] is None
        assert completed0["completed_at"] is not None
        assert completed0["duration_ms"] >= 0
        assert_plan_rejected_unchanged(
            "BLOCKED:plan-round-nonmonotonic: expected=1 supplied=0",
            "spawn", "--round", "0", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert_plan_rejected_unchanged(
            "BLOCKED:plan-round-nonmonotonic: expected=1 supplied=2",
            "spawn", "--round", "2", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert_plan_rejected_unchanged(
            "error: phases.plan re-spawn requires --triggered-by",
            "spawn", "--round", "1", "--engine", "claude",
            "--model", "plan-test-model", "--prompt-sha256", digest1,
        )
        result = plan_cli(
            "spawn", "--round", "1", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert result.returncode == 0, result.stderr
        plan1 = read_state(state_path)["phases"]["plan"]
        assert len(plan1["history"]) == 1
        assert set(plan1["history"][0]) == set(PLAN_RECEIPT_FIELDS)
        assert plan1["history"][0]["prompt_sha256"] == digest0
        assert plan1["prompt_sha256"] == digest1
        guard_error = (
            "error: phases.plan complete with PASS or PASS_WITH_ISSUES requires "
            "--phase plan transition --verdict <verdict> --next-phase <phase>"
        )
        assert_plan_rejected_unchanged(
            guard_error, "complete", "--verdict", "PASS",
        )
        assert_plan_rejected_unchanged(
            guard_error, "complete", "--verdict", "PASS_WITH_ISSUES",
        )
        result = plan_cli(
            "transition", "--verdict", "PASS", "--next-phase", "implement",
            "--next-round", "0", "--next-engine", "claude",
        )
        assert result.returncode == 0, result.stderr
        for supplied_round in (0, 1, 2):
            assert_plan_rejected_unchanged(
                "BLOCKED:plan-respawn-exhausted",
                "spawn", "--round", str(supplied_round),
                "--triggered-by", "plan", "--engine", "claude",
                "--model", "plan-test-model", "--prompt-sha256", digest1,
            )
        old_receipt = {
            "started_at": "2026-01-01T00:00:00.000Z",
            "verdict": "PASS",
            "completed_at": "2026-01-01T00:00:01.000Z",
            "duration_ms": 1000,
        }
        assert not is_plan_dispatch_receipt(old_receipt)
        assert is_plan_dispatch_receipt(read_state(state_path)["phases"]["plan"])

        # Iter-0112: schema-v3 PLAN output is an immutable authority receipt.
        plan_output = devlyn / "plan.md"
        plan_output.write_text("# Authorized plan\n- config/skills/x.py\n", encoding="utf-8")
        write_state(state_path, {"version": "3.0", "phases": {}})
        result = plan_cli(*required_spawn)
        assert result.returncode == 0, result.stderr
        result = plan_cli(
            "transition", "--verdict", "PASS", "--next-phase", "implement",
            "--next-round", "0", "--next-engine", "claude",
        )
        assert result.returncode == 0, result.stderr
        sealed_plan_state = read_state(state_path)
        assert sealed_plan_state["phases"]["plan"]["output_sha256"] == hashlib.sha256(
            plan_output.read_bytes()
        ).hexdigest()
        plan_output.write_text(
            "# Authorized plan\n- config/skills/x.py\n- unapproved.py\n",
            encoding="utf-8",
        )
        before = state_path.read_bytes()
        blocked_plan_mutation = subprocess.run(
            [
                sys.executable, script, "--devlyn-dir", str(devlyn),
                "--phase", "build_gate", "spawn", "--round", "0",
            ],
            capture_output=True, text=True, check=False,
        )
        assert blocked_plan_mutation.returncode != 0
        assert "BLOCKED:plan-integrity-mismatch" in blocked_plan_mutation.stderr
        assert state_path.read_bytes() == before
        assert_plan_rejected_unchanged(
            "error: phases.plan already completed — respawn before completing again",
            "complete", "--verdict", "NEEDS_WORK",
        )
        print("PASS iter-0112 PLAN output digest blocks mid-flight widening")

        write_state(state_path, {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        })
        result = plan_cli("complete", "--verdict", "BLOCKED")
        assert result.returncode == 0, result.stderr
        assert read_state(state_path)["phases"]["plan"]["verdict"] == "BLOCKED"
        write_state(state_path, {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        })
        result = plan_cli(
            "complete", "--verdict", "PASS", "--engine-session-log",
            str(devlyn / "missing-session.jsonl"),
        )
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:model-attestation-failed" in result.stderr
        assert guard_error not in result.stderr
        attestation_blocked = read_state(state_path)["phases"]["plan"]
        assert attestation_blocked["verdict"] == "BLOCKED"
        assert attestation_blocked["completed_at"] is not None
        assert attestation_blocked["model_effective"] is None
        legacy_state = {"phases": {"plan": old_receipt | {"round": 0}}}
        write_state(state_path, legacy_state)
        result = plan_cli(
            "spawn", "--round", "1", "--triggered-by", "plan",
            "--engine", "claude", "--model", "plan-test-model",
            "--prompt-sha256", digest1,
        )
        assert result.returncode == 0, result.stderr
        archived_legacy = read_state(state_path)["phases"]["plan"]["history"][0]
        assert archived_legacy == old_receipt
        print("PASS iter-0089 PLAN ledger: P-0089-1/2/6")

        write_state(state_path, {"phases": {}})

        # Round 0: spawn -> complete.
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "claude", None)
        write_state(state_path, state)
        round0_started = read_state(state_path)["phases"]["implement"]["started_at"]

        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "implement", "NEEDS_WORK", None, None, None, None, "test-model-id")
        write_state(state_path, state)
        entry = read_state(state_path)["phases"]["implement"]
        assert "history" not in entry, "history must be absent before re-entry"
        assert entry["completed_at"] is not None
        assert entry["duration_ms"] >= 0
        assert parse_iso(entry["completed_at"]) >= parse_iso(entry["started_at"])
        expected_ms = round((parse_iso(entry["completed_at"]) - parse_iso(entry["started_at"])).total_seconds() * 1000)
        assert entry["duration_ms"] == expected_ms, (entry["duration_ms"], expected_ms)

        # Round 1: fix-loop respawn — this is the literal iter-0042 regression.
        time.sleep(0.05)
        state = read_state(state_path)
        do_spawn(state, "implement", 1, "verify", None, None, None)
        write_state(state_path, state)
        respawned = read_state(state_path)["phases"]["implement"]
        assert respawned["started_at"] != round0_started, "started_at must refresh on respawn"
        assert respawned["completed_at"] is None, "respawn must null stale completed_at"
        assert respawned["duration_ms"] is None, "respawn must null stale duration_ms"
        assert respawned["verdict"] is None, "respawn must null stale verdict"
        assert respawned["engine"] == "claude", "engine preserved when not re-supplied"
        assert respawned["round"] == 1
        assert respawned["triggered_by"] == "verify"
        assert len(respawned["history"]) == 1
        history0 = respawned["history"][0]
        assert history0["started_at"] == round0_started
        assert history0["verdict"] == "NEEDS_WORK"
        assert history0["completed_at"] == entry["completed_at"]
        assert history0["duration_ms"] == entry["duration_ms"]
        assert set(history0) == {"started_at", "verdict", "completed_at", "duration_ms"}

        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "implement", "PASS", None, ".devlyn/x.jsonl", None, None, None)
        write_state(state_path, state)
        final = read_state(state_path)["phases"]["implement"]
        assert final["verdict"] == "PASS"
        assert read_state(state_path)["process_evidence"] is None
        assert parse_iso(final["started_at"]) == parse_iso(respawned["started_at"])
        assert parse_iso(final["completed_at"]) >= parse_iso(final["started_at"])
        assert final["artifacts"]["findings_file"] == ".devlyn/x.jsonl"

        # Iter-0111 R2: successful IMPLEMENT completion and transition both
        # validate declared evidence before any lifecycle mutation, then bind
        # the exact manifest and stream digests into state. Legacy runs with no
        # declaration remain legal through the null carrier asserted above.
        evidence_work = devlyn / "process-evidence-state"
        evidence_devlyn = evidence_work / ".devlyn"
        evidence_spec_dir = evidence_work / "docs" / "evidence"
        evidence_devlyn.mkdir(parents=True)
        evidence_spec_dir.mkdir(parents=True)
        (evidence_spec_dir / "spec.md").write_text("# Evidence fixture\n", encoding="utf-8")
        (evidence_spec_dir / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf build-gate"}],
            "process_evidence": [{
                "id": "red-first",
                "phase": "implement",
                "cmd": "printf red-before-fix >&2; exit 7",
                "exit_code": 7,
                "stdout_contains": ["red-before-fix"],
            }],
        }) + "\n", encoding="utf-8")
        evidence_state = {
            "run_id": "rs-state-evidence",
            "source": {"type": "spec", "spec_path": "docs/evidence/spec.md"},
            "phases": {"implement": None, "build_gate": None},
        }
        do_spawn(evidence_state, "implement", 0, None, None, "codex", None)
        evidence_state_path = evidence_devlyn / "pipeline.state.json"
        write_state(evidence_state_path, evidence_state)
        evidence_script = str(pathlib.Path(__file__).resolve())

        def evidence_state_cli(event: str, *event_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable, evidence_script, "--devlyn-dir", ".devlyn",
                    "--phase", "implement", event, *event_args,
                ],
                cwd=evidence_work, capture_output=True, text=True, check=False,
            )

        for event_args in (
            ("complete", "--verdict", "PASS"),
            (
                "transition", "--verdict", "PASS", "--next-phase", "build_gate",
                "--next-round", "0",
            ),
        ):
            before = evidence_state_path.read_bytes()
            result = evidence_state_cli(event_args[0], *event_args[1:])
            assert result.returncode != 0
            assert "BLOCKED:process-evidence-invalid" in result.stderr
            assert "missing" in result.stderr
            assert evidence_state_path.read_bytes() == before

        runner_script = str(pathlib.Path(__file__).with_name("process-evidence.py").resolve())
        captured = subprocess.run(
            [
                sys.executable, runner_script, "--devlyn-dir", ".devlyn", "run",
                "--phase", "implement", "--id", "red-first",
            ],
            cwd=evidence_work, capture_output=True, text=True, check=False,
        )
        assert captured.returncode == 0, captured.stderr
        manifest_rel = loads_strict_json(captured.stdout)["manifest_path"]
        manifest = evidence_work / manifest_rel
        stderr_path = manifest.parent / "red-first.stderr"
        original_stderr = stderr_path.read_bytes()
        stderr_path.write_bytes(b"altered")
        before = evidence_state_path.read_bytes()
        altered = evidence_state_cli("complete", "--verdict", "PASS")
        assert altered.returncode != 0
        assert "digest or byte count mismatch" in altered.stderr
        assert evidence_state_path.read_bytes() == before
        stderr_path.write_bytes(original_stderr)
        transitioned = evidence_state_cli(
            "transition", "--verdict", "PASS", "--next-phase", "build_gate",
            "--next-round", "0",
        )
        assert transitioned.returncode == 0, transitioned.stderr
        sealed_state = read_state(evidence_state_path)
        carrier = sealed_state["process_evidence"][0]
        assert carrier["phase"] == "implement" and carrier["round"] == 0
        assert carrier["manifest"]["path"] == manifest_rel
        assert carrier["manifest"]["sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
        assert sealed_state["phases"]["implement"]["verdict"] == "PASS"
        assert sealed_state["phases"]["build_gate"]["started_at"] is not None
        print("PASS iter-0111 process evidence: completion/transition gate and state digest binding")

        # Gate-discovered iter-0111 regression: BUILD_GATE MECHANICAL emitted
        # sealed process evidence, but completion left it outside the state
        # binding and archive_run.py correctly rejected the orphaned files.
        def build_gate_state_cli(
            event: str, *event_args: str,
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [
                    sys.executable, evidence_script, "--devlyn-dir", ".devlyn",
                    "--phase", "build_gate", event, *event_args,
                ],
                cwd=evidence_work, capture_output=True, text=True, check=False,
            )

        results_path = evidence_devlyn / "spec-verify.results.json"
        results_path.write_text(json.dumps({
            "commands": [{"pass": True}], "process_evidence": None,
        }) + "\n", encoding="utf-8")
        before = evidence_state_path.read_bytes()
        missing = build_gate_state_cli("complete", "--verdict", "PASS")
        assert missing.returncode != 0
        assert "commands exist without a process-evidence carrier" in missing.stderr
        assert evidence_state_path.read_bytes() == before
        results_path.write_text(json.dumps({
            "commands": [], "process_evidence": None,
        }) + "\n", encoding="utf-8")
        removed = build_gate_state_cli("complete", "--verdict", "PASS")
        assert removed.returncode != 0
        assert "required BUILD_GATE evidence has no process-evidence carrier" in removed.stderr
        assert evidence_state_path.read_bytes() == before

        runner = process_evidence_module()

        def write_build_gate_results() -> dict:
            current = read_state(evidence_state_path)
            round_ = runner.phase_round(current, "build_gate")
            obligation = runner.normalize_obligation({
                "id": "verification-command-0001",
                "phase": "build_gate",
                "argv": [sys.executable, "-c", "print('sealed build gate')"],
            })
            relative = runner.manifest_relative_path(current, "build_gate")
            runner.capture_process(
                evidence_work, evidence_work / relative, current["run_id"],
                "build_gate", round_, obligation,
            )
            build_carrier = runner.validate_manifest(
                evidence_work, relative, current["run_id"], "build_gate", round_,
                [obligation], require_expectations=False,
            )
            results_path.write_text(json.dumps({
                "commands": runner.bound_carrier_summary_commands(
                    evidence_work, build_carrier,
                ),
                "process_evidence": build_carrier,
            }) + "\n", encoding="utf-8")
            return build_carrier

        build_carrier_0 = write_build_gate_results()
        completed = build_gate_state_cli("complete", "--verdict", "PASS")
        assert completed.returncode == 0, completed.stderr
        completed_state = read_state(evidence_state_path)
        assert completed_state["process_evidence"] == [carrier, build_carrier_0]

        spawned = build_gate_state_cli(
            "spawn", "--round", "1", "--triggered-by", "build_gate",
        )
        assert spawned.returncode == 0, spawned.stderr
        build_carrier_1 = write_build_gate_results()
        transitioned = build_gate_state_cli(
            "transition", "--verdict", "PASS", "--next-phase", "cleanup",
            "--next-round", "0",
        )
        assert transitioned.returncode == 0, transitioned.stderr
        build_bound_state = read_state(evidence_state_path)
        assert build_bound_state["process_evidence"] == [
            carrier, build_carrier_0, build_carrier_1,
        ]
        assert build_bound_state["phases"]["cleanup"]["started_at"] is not None
        print("PASS iter-0111 BUILD_GATE evidence: completion/transition state binding")

        # Iter-0112 audit counterexample: a valid carrier previously authenticated
        # bytes only, so a failed entry or capability denial could still be completed
        # with caller-supplied PASS.
        build_bound_state["phases"]["build_gate"] = None
        do_spawn(build_bound_state, "build_gate", 2, "build_gate", None, None, None)
        write_state(evidence_state_path, build_bound_state)
        mismatch = runner.normalize_obligation({
            "id": "verification-command-0001",
            "phase": "build_gate",
            "argv": [sys.executable, "-c", "raise SystemExit(7)"],
        })
        mismatch_rel = runner.manifest_relative_path(build_bound_state, "build_gate")
        runner.capture_process(
            evidence_work, evidence_work / mismatch_rel, build_bound_state["run_id"],
            "build_gate", 2, mismatch,
        )
        mismatch_carrier = runner.validate_manifest(
            evidence_work, mismatch_rel, build_bound_state["run_id"], "build_gate", 2,
            [mismatch], require_expectations=False,
        )
        mismatch_commands = runner.bound_carrier_summary_commands(
            evidence_work, mismatch_carrier,
        )
        mismatch_commands[0]["pass"] = True
        results_path.write_text(json.dumps({
            "commands": mismatch_commands, "process_evidence": mismatch_carrier,
        }) + "\n", encoding="utf-8")
        before = evidence_state_path.read_bytes()
        laundered = build_gate_state_cli("complete", "--verdict", "PASS")
        assert laundered.returncode != 0
        assert "command 0 disagrees with sealed process evidence" in laundered.stderr
        assert evidence_state_path.read_bytes() == before
        results_path.write_text(json.dumps({
            "commands": [], "process_evidence": None,
        }) + "\n", encoding="utf-8")
        removed_after_capture = build_gate_state_cli("complete", "--verdict", "PASS")
        assert removed_after_capture.returncode != 0
        assert "manifest exists without a process-evidence carrier" in removed_after_capture.stderr
        assert evidence_state_path.read_bytes() == before
        results_path.write_text(json.dumps({
            "commands": runner.bound_carrier_summary_commands(
                evidence_work, mismatch_carrier,
            ),
            "process_evidence": mismatch_carrier,
        }) + "\n", encoding="utf-8")
        failed = build_gate_state_cli("complete", "--verdict", "FAIL")
        assert failed.returncode == 0, failed.stderr

        failed_state = read_state(evidence_state_path)
        do_spawn(failed_state, "build_gate", 3, "build_gate", None, None, None)
        write_state(evidence_state_path, failed_state)
        denied = runner.normalize_obligation({
            "id": "verification-command-0001",
            "phase": "build_gate",
            "cmd": "python3 -m pytest",
        })
        denied_rel = runner.manifest_relative_path(failed_state, "build_gate")
        runner.record_capability_denial(
            evidence_work, evidence_work / denied_rel, failed_state["run_id"],
            "build_gate", 3, denied, "subprocess", b"parent denied",
        )
        denied_carrier = runner.validate_manifest(
            evidence_work, denied_rel, failed_state["run_id"], "build_gate", 3,
            [denied], require_expectations=False,
        )
        denied_commands = runner.bound_carrier_summary_commands(
            evidence_work, denied_carrier,
        )
        denied_commands[0]["pass"] = True
        results_path.write_text(json.dumps({
            "commands": denied_commands, "process_evidence": denied_carrier,
        }) + "\n", encoding="utf-8")
        before = evidence_state_path.read_bytes()
        denial_laundered = build_gate_state_cli("complete", "--verdict", "PASS")
        assert denial_laundered.returncode != 0
        assert "command 0 disagrees with sealed process evidence" in denial_laundered.stderr
        assert evidence_state_path.read_bytes() == before
        results_path.write_text(json.dumps({
            "commands": runner.bound_carrier_summary_commands(
                evidence_work, denied_carrier,
            ),
            "process_evidence": denied_carrier,
        }) + "\n", encoding="utf-8")
        blocked = build_gate_state_cli("complete", "--verdict", "BLOCKED")
        assert blocked.returncode == 0, blocked.stderr
        print("PASS iter-0112 BUILD_GATE sealed outcome owns the verdict floor")

        def test_interrupted_build_gate() -> None:
            # Iter-0119 R1-R5: interrupted observations bind only to BLOCKED,
            # without changing their bytes or bypassing archive/receipt guards.
            work = (devlyn / "interrupted-build-gate").resolve()
            active = work / ".devlyn"
            active.mkdir(parents=True)
            state_file = active / "pipeline.state.json"
            summary = active / "spec-verify.results.json"
            runner = process_evidence_module()
            archive_spec = importlib.util.spec_from_file_location(
                "interrupted_archive", pathlib.Path(__file__).with_name("archive_run.py"),
            )
            assert archive_spec is not None and archive_spec.loader is not None
            archive = importlib.util.module_from_spec(archive_spec)
            archive_spec.loader.exec_module(archive)
            fixture = {
                "version": "3.0", "run_id": "rs-interrupted-build-gate",
                "source": {"type": "spec", "spec_path": "spec.md"},
                "phases": {"build_gate": None, "final_report": None},
                "process_evidence": None,
            }
            do_spawn(fixture, "build_gate", 0, None, None, "claude", None)
            write_state(state_file, fixture)
            open_bytes = state_file.read_bytes()
            relative = runner.manifest_relative_path(fixture, "build_gate")
            manifest = work / relative
            obligations = [
                runner.normalize_obligation({
                    "id": f"verification-command-{index:04d}", "phase": "build_gate",
                    "argv": [sys.executable, "-c", (
                        "import os; os.write(1, b'observed\\x00\\xff\\n'); "
                        f"os.write(2, b'diagnostic\\r\\n'); raise SystemExit({exit_code})"
                    )],
                })
                for index, exit_code in enumerate((0, 7, 0), 1)
            ]
            (work / "spec.md").write_text("# Interrupted build fixture\n", encoding="utf-8")
            (work / "spec.expected.json").write_text(json.dumps({
                "process_evidence": obligations,
            }), encoding="utf-8")
            assert runner.declared_obligations(work, fixture, "build_gate") == obligations
            for obligation in obligations[:2]:
                runner.capture_process(
                    work, manifest, fixture["run_id"], "build_gate", 0, obligation,
                )
            manifest_bytes = manifest.read_bytes()
            document = loads_strict_json(manifest_bytes.decode("utf-8"))
            assert [entry["expectation_met"] for entry in document["entries"]] == [True, False]
            assert [entry["outcome"] for entry in document["entries"]] == [
                {"kind": "exit", "exit_code": code, "signal": None} for code in (0, 7)
            ]
            observed = {path: path.read_bytes() for path in manifest.parent.iterdir()}
            assert set(observed) == {manifest} | {
                manifest.parent / f"verification-command-{index:04d}.{stream}"
                for index in (1, 2) for stream in ("stdout", "stderr")
            }
            carrier = runner.validate_manifest(
                work, relative, fixture["run_id"], "build_gate", 0,
                require_expectations=False,
            )
            cli_env = {key: value for key, value in os.environ.items()
                       if not key.startswith("DEVLYN_INVOCATION_")}
            cli_env["PYTHONDONTWRITEBYTECODE"] = "1"

            def cli(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(pathlib.Path(__file__).resolve()),
                     "--devlyn-dir", ".devlyn", "--phase", "build_gate", *args],
                    cwd=work, env=cli_env, capture_output=True, text=True, check=False,
                )

            def rejected(*args: str, error: str = "BLOCKED:process-evidence-invalid") -> None:
                before = state_file.read_bytes()
                result = cli(*args)
                assert result.returncode != 0, result.stdout
                assert error in result.stderr, result.stderr
                assert state_file.read_bytes() == before

            def archived(state: dict) -> None:
                paths = archive.dynamic_evidence_artifacts(active, state)
                assert set(paths) == set(observed)
                assert {path: path.read_bytes() for path in paths} == observed
                assert {path: path.read_bytes() for path in manifest.parent.iterdir()} == observed

            def terminal() -> dict:
                state = read_state(state_file)
                entry = state["phases"]["build_gate"]
                assert entry["verdict"] == "BLOCKED"
                assert entry["completed_at"] is not None and entry["duration_ms"] >= 0
                assert entry["model_effective"] is None
                assert entry.get("invocation_receipt") is None
                assert state["phases"]["final_report"] is None
                assert state["process_evidence"] == [carrier]
                assert not summary.exists() and not summary.is_symlink()
                archived(state)
                return state

            completed = cli("complete", "--verdict", "BLOCKED")
            assert completed.returncode == 0, completed.stderr
            bound = terminal()
            print("PASS iter-0119 absent-summary BLOCKED persists exact five-file evidence")

            for control in ("unbound", "tampered", "manifest", "binding", "malformed", "duplicate"):
                candidate = copy.deepcopy(bound)
                extra = manifest.parent / "unexpected.stdout"
                stream = manifest.parent / "verification-command-0001.stdout"
                if control == "unbound":
                    extra.write_bytes(b"unbound")
                elif control == "tampered":
                    stream.write_bytes(b"tampered")
                elif control == "manifest":
                    manifest.write_text("{", encoding="utf-8")
                elif control == "malformed":
                    candidate["process_evidence"] = [{}]
                elif control == "duplicate":
                    candidate["process_evidence"].append(copy.deepcopy(carrier))
                else:
                    candidate["process_evidence"][0]["manifest"]["sha256"] = "0" * 64
                try:
                    archive.dynamic_evidence_artifacts(active, candidate)
                except archive.ArchiveError as exc:
                    if control == "duplicate":
                        assert "duplicate state-bound process-evidence" in str(exc), str(exc)
                    else:
                        assert ("unbound process-evidence" if control == "unbound" else
                                "invalid bound process evidence") in str(exc), str(exc)
                else:
                    raise AssertionError(f"archive accepted {control}")
                extra.unlink(missing_ok=True)
                stream.write_bytes(observed[stream])
                manifest.write_bytes(manifest_bytes)
            archived(bound)

            state_file.write_bytes(open_bytes)
            for verdict in ("PASS", "PASS_WITH_ISSUES", "NEEDS_WORK", "FAIL"):
                rejected("complete", "--verdict", verdict, error="spec-verify.results.json is missing")
            rejected("complete", error="spec-verify.results.json is missing")
            manifest.unlink()
            rejected("complete", "--verdict", "BLOCKED")
            manifest.write_text("{", encoding="utf-8")
            rejected("complete", "--verdict", "BLOCKED")
            for control in ("run_id", "phase", "round", "expectation", "expectation_met",
                            "duplicate", "path", "bytes", "sha256"):
                altered = copy.deepcopy(document)
                entry = altered["entries"][1]
                if control in {"run_id", "phase", "round"}:
                    altered[control] = {"run_id": "rs-wrong", "phase": "implement", "round": 1}[control]
                elif control == "expectation":
                    entry["expectation"]["exit_code"] = "zero"
                elif control == "expectation_met":
                    entry[control] = True
                elif control == "duplicate":
                    altered["entries"].append(copy.deepcopy(entry))
                else:
                    entry["stdout"][control] = {
                        "path": "../escaped.stdout", "bytes": entry["stdout"]["bytes"] + 1,
                        "sha256": "0" * 64,
                    }[control]
                manifest.write_text(json.dumps(altered), encoding="utf-8")
                rejected("complete", "--verdict", "BLOCKED")
            manifest.write_bytes(manifest_bytes)
            stream = manifest.parent / "verification-command-0001.stdout"
            stream.write_bytes(b"tampered")
            rejected("complete", "--verdict", "BLOCKED")
            stream.write_bytes(observed[stream])
            outside = devlyn / "escaped-evidence"
            for path in (manifest, manifest.parent / "verification-command-0001.stdout"):
                outside.write_bytes(observed[path])
                path.unlink()
                path.symlink_to(outside)
                rejected("complete", "--verdict", "BLOCKED")
                path.unlink()
                path.write_bytes(observed[path])
            bad_prior = copy.deepcopy(carrier)
            bad_prior["manifest"]["sha256"] = "0" * 64
            for invalid, error in (
                ({}, "state.process_evidence must be null or an array"),
                ([{}], "state process-evidence carrier has an invalid shape"),
                ([bad_prior], "bound process evidence manifest digest mismatch"),
                ([carrier], "duplicate state carrier"),
            ):
                candidate = copy.deepcopy(fixture)
                candidate["process_evidence"] = invalid
                write_state(state_file, candidate)
                rejected("complete", "--verdict", "BLOCKED", error=error)
            state_file.write_bytes(open_bytes)

            commands = runner.bound_carrier_summary_commands(work, carrier)
            wrong_commands = copy.deepcopy(commands)
            wrong_commands[1]["pass"] = True
            wrong_carrier = copy.deepcopy(carrier)
            wrong_carrier["round"] = 1
            for content in (
                "{", "[]", json.dumps({"commands": {}}),
                json.dumps({"commands": commands, "process_evidence": None}),
                json.dumps({"commands": commands, "process_evidence": wrong_carrier}),
                json.dumps({"commands": wrong_commands, "process_evidence": carrier}),
            ):
                summary.write_text(content, encoding="utf-8")
                rejected("complete", "--verdict", "BLOCKED")
            summary.unlink()
            summary.mkdir()
            rejected("complete", "--verdict", "BLOCKED")
            summary.rmdir()
            summary.symlink_to(active / "absent-summary")
            rejected("complete", "--verdict", "BLOCKED")
            summary.unlink()
            # A valid summary symlink retains the existing outcome floor.
            target = devlyn / "valid-summary.json"
            target.write_text(json.dumps({
                "commands": commands, "process_evidence": carrier,
            }), encoding="utf-8")
            summary.symlink_to(target)
            for verdict in ("PASS", "PASS_WITH_ISSUES"):
                rejected("complete", "--verdict", verdict, error="mismatch cannot complete")
            completed = cli("complete", "--verdict", "FAIL")
            assert completed.returncode == 0, completed.stderr
            summarized = read_state(state_file)
            assert summarized["phases"]["build_gate"]["verdict"] == "FAIL"
            assert summarized["process_evidence"] == [carrier]
            archived(summarized)
            summary.unlink()
            print("PASS iter-0119 ineligible verdicts, invalid summaries and integrity controls preserve state")

            # Valid nonzero receipt: transition stays atomic; standalone
            # completion persists BLOCKED before reporting the receipt error.
            prompt = active / "build_gate.prompt.0"
            prompt.write_text("inspect interrupted build\n", encoding="utf-8")
            session = active / "build_gate.worker-session.0.jsonl"
            session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
            receipt = active / "build_gate.invocation.0.json"
            model = "gpt-5.6-sol"
            candidate = copy.deepcopy(fixture)
            candidate["phases"]["build_gate"].update({
                "engine": "codex", "model_requested": model,
                "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
            })
            write_state(state_file, candidate)
            receipts = invocation_receipt_module()
            receipts.start_receipt(
                work, receipt, fixture["run_id"], "build_gate", 0, str(prompt), str(session),
                ["--json", "-C", str(work), "-s", "workspace-write", "-m", model,
                 "-c", "sandbox_workspace_write.network_access=true", "inspect interrupted build"],
            )
            receipts.finish_receipt(work, receipt, 7)
            receipt_bytes = receipt.read_bytes()
            error = "BLOCKED:invocation-receipt-invalid: Codex invocation exited 7"
            rejected(
                "transition", "--verdict", "BLOCKED", "--engine-session-log", str(session),
                "--next-phase", "final_report", "--next-round", "0", error=error,
            )
            completed = cli(
                "complete", "--verdict", "BLOCKED", "--engine-session-log", str(session),
            )
            assert completed.returncode == 1, completed.stdout
            assert completed.stderr.strip() == error, completed.stderr
            terminal()
            assert receipt.read_bytes() == receipt_bytes
            print("PASS iter-0119 nonzero receipt persists BLOCKED before exit1; transition stays atomic")

            candidate = copy.deepcopy(bound)
            do_spawn(candidate, "build_gate", 1, None, None, "claude", None)
            write_state(state_file, candidate)
            next_relative = runner.manifest_relative_path(candidate, "build_gate")
            runner.capture_process(
                work, work / next_relative, fixture["run_id"], "build_gate", 1, obligations[0],
            )
            next_carrier = runner.validate_manifest(
                work, next_relative, fixture["run_id"], "build_gate", 1,
                require_expectations=False,
            )
            completed = cli("complete", "--verdict", "BLOCKED")
            assert completed.returncode == 0, completed.stderr
            appended = read_state(state_file)
            assert appended["process_evidence"] == [carrier, next_carrier]
            assert appended["phases"]["build_gate"]["verdict"] == "BLOCKED"
            assert {path: path.read_bytes() for path in observed} == observed
            assert set(observed).issubset(archive.dynamic_evidence_artifacts(active, appended))

        test_interrupted_build_gate()

        # complete() before spawn() must fail loudly, not silently invent data.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        try:
            do_complete(state, "build_gate", "PASS", None, None, None, None, None)
        except SystemExit as e:
            assert "never spawned" in str(e)
        else:
            raise AssertionError("complete() without a prior spawn() must raise")

        # F11 rs-20260721T065728Z receipt: VERIFY merge wrote BLOCKED, but the
        # caller skipped complete() before re-entry. Respawn must fail without
        # archiving the open span as history.
        f11_open = {
            "phases": {
                "verify": {
                    "started_at": "2026-07-21T07:08:11.684Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "verdict": "BLOCKED",
                }
            }
        }
        before_f11 = json.dumps(f11_open, sort_keys=True)
        try:
            do_spawn(f11_open, "verify", 1, "verify", None, "codex", None)
        except SystemExit as e:
            assert "open span" in str(e) and "complete it before respawn" in str(e)
        else:
            raise AssertionError("respawn over an open F11 span must fail")
        assert json.dumps(f11_open, sort_keys=True) == before_f11
        assert "history" not in f11_open["phases"]["verify"]

        # Transition is one state transaction: a forced failure between its
        # validated halves leaves the authoritative state byte-identical.
        transition_state = {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        }
        write_state(state_path, transition_state)
        transition_before = state_path.read_bytes()

        def fail_between_halves() -> None:
            raise RuntimeError("forced transition failure")

        try:
            do_transition(
                transition_state, "plan", "implement", "PASS", None,
                None, None, None, None, None, devlyn, 0, None, None,
                "claude", None, between=fail_between_halves,
            )
        except RuntimeError as exc:
            assert str(exc) == "forced transition failure"
        else:
            raise AssertionError("forced transition failure did not fire")
        assert state_path.read_bytes() == transition_before
        assert transition_state["phases"]["plan"]["completed_at"] is None
        print("PASS self-test transition atomicity: forced midpoint failure left state unchanged")

        attestation_state = copy.deepcopy(transition_state)
        attestation_state["phases"]["plan"]["model_requested"] = "wanted-model"
        attestation_log = devlyn / "transition-attestation.log"
        attestation_log.write_text(json.dumps({
            "modelUsage": {"other-model": {"inputTokens": 1}},
        }) + "\n", encoding="utf-8")
        write_state(state_path, attestation_state)
        attestation_before = state_path.read_bytes()
        try:
            do_transition(
                attestation_state, "plan", "implement", "PASS", None,
                None, None, None, None, str(attestation_log), devlyn,
                0, None, None, "claude", None,
            )
        except SystemExit as exc:
            assert "BLOCKED:model-attestation-mismatch" in str(exc)
        else:
            raise AssertionError("transition accepted mismatched model attestation")
        assert state_path.read_bytes() == attestation_before
        print("PASS self-test transition attestation: mismatch left state unchanged")

        try:
            do_transition(
                transition_state, "plan", "cleanup", "PASS", None,
                None, None, None, None, None, devlyn, 0, None, None,
                "claude", None,
            )
        except SystemExit as exc:
            assert "illegal phase transition: plan -> cleanup" in str(exc)
        else:
            raise AssertionError("transition accepted an illegal phase edge")
        assert state_path.read_bytes() == attestation_before
        print("PASS self-test transition legal-edge guard: illegal edge left state unchanged")

        transitioned = do_transition(
            transition_state, "plan", "implement", "PASS", None,
            None, None, None, None, None, devlyn, 0, None, None,
            "claude", None,
        )
        write_state(state_path, transitioned)
        assert transitioned["phases"]["plan"]["verdict"] == "PASS"
        assert transitioned["phases"]["plan"]["completed_at"] is not None
        assert transitioned["phases"]["implement"]["started_at"] is not None
        assert transitioned["phases"]["implement"]["verdict"] is None
        print("PASS self-test transition happy path: complete + spawn committed together")

        cli_state = {
            "phases": {
                "plan": {
                    "started_at": "2026-01-01T00:00:00.000Z",
                    "completed_at": None,
                    "duration_ms": None,
                    "round": 0,
                    "triggered_by": None,
                    "verdict": None,
                },
                "implement": None,
            }
        }
        write_state(state_path, cli_state)
        cli_transition = subprocess.run(
            [
                sys.executable, str(pathlib.Path(__file__).resolve()),
                "--devlyn-dir", str(devlyn), "--phase", "plan", "transition",
                "--verdict", "PASS", "--next-phase", "implement",
                "--next-round", "0", "--next-engine", "claude",
            ],
            capture_output=True, text=True,
        )
        assert cli_transition.returncode == 0, cli_transition.stderr
        cli_receipt = loads_strict_json(cli_transition.stdout)
        assert cli_receipt["completed_phase"] == "plan"
        assert cli_receipt["completed_verdict"] == "PASS"
        assert cli_receipt["next_phase"] == "implement"
        assert cli_receipt["state_sha256"] == hashlib.sha256(state_path.read_bytes()).hexdigest()
        print("PASS self-test transition CLI: machine-only JSON receipt")

        open_next = copy.deepcopy(transition_state)
        open_next["phases"]["implement"] = {
            "started_at": "2026-01-01T00:00:01.000Z",
            "completed_at": None,
            "duration_ms": None,
            "round": 0,
            "triggered_by": None,
            "verdict": None,
        }
        write_state(state_path, open_next)
        open_next_before = state_path.read_bytes()
        try:
            do_transition(
                open_next, "plan", "implement", "PASS", None,
                None, None, None, None, None, devlyn, 1, None, None,
                "claude", None,
            )
        except SystemExit as exc:
            assert "open span" in str(exc) and "complete it before respawn" in str(exc)
        else:
            raise AssertionError("transition opened a phase that already had an open span")
        assert state_path.read_bytes() == open_next_before
        print("PASS self-test transition open-span guard: rejected without mutation")

        # A completed FAIL round must be retained before a fix-loop respawn
        # resets the live record.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "build_gate", 0, None, None, "claude", None)
        write_state(state_path, state)
        time.sleep(0.05)
        state = read_state(state_path)
        do_complete(state, "build_gate", "FAIL", None, None, None, None, None)
        write_state(state_path, state)
        failed_round = read_state(state_path)["phases"]["build_gate"]
        state = read_state(state_path)
        do_spawn(state, "build_gate", 1, "build_gate", None, None, None)
        write_state(state_path, state)
        respawned_fail = read_state(state_path)["phases"]["build_gate"]
        assert respawned_fail["verdict"] is None
        assert len(respawned_fail["history"]) == 1
        assert respawned_fail["history"][0]["verdict"] == "FAIL"
        assert respawned_fail["history"][0]["completed_at"] == failed_round["completed_at"]

        # VERIFY flow: verify-merge-findings.py already wrote verdict; complete()
        # must preserve it when --verdict is omitted.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, None, "claude", None)
        assert state["phases"]["verify"]["judge_durations_ms"] is None
        state["phases"]["verify"]["verdict"] = "PASS"
        state["phases"]["verify"]["sub_verdicts"] = {"mechanical": "PASS", "judge": "PASS"}
        state["phases"]["verify"]["judge_durations_ms"] = {"judge": 23, "pair_judge": None}
        write_state(state_path, state)
        state = read_state(state_path)
        do_complete(state, "verify", None, None, None, None, None, None)
        write_state(state_path, state)
        verify_entry = read_state(state_path)["phases"]["verify"]
        assert verify_entry["verdict"] == "PASS", "complete() must preserve pre-set verdict when omitted"
        assert verify_entry["sub_verdicts"] == {"mechanical": "PASS", "judge": "PASS"}
        assert verify_entry["judge_durations_ms"] == {"judge": 23, "pair_judge": None}
        assert verify_entry["completed_at"] is not None

        # An explicit --verdict for VERIFY must be rejected — its verdict is
        # owned exclusively by verify-merge-findings.py --write-state.
        state = read_state(state_path)
        try:
            do_complete(state, "verify", "PASS", None, None, None, None, None)
        except SystemExit as e:
            assert "owned by verify-merge-findings.py" in str(e)
        else:
            raise AssertionError("complete() must reject an explicit --verdict for VERIFY")
        do_spawn(state, "verify", 1, "verify", None, None, None)
        assert state["phases"]["verify"]["judge_durations_ms"] is None

        # Non-VERIFY phases require --verdict explicitly; complete() must not
        # silently accept an unset verdict the way VERIFY's omit-to-preserve
        # flow does.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, None, "claude", "plan-test-model",
            prompt_sha256=digest0,
        )
        write_state(state_path, state)
        state = read_state(state_path)
        try:
            do_complete(state, "plan", None, None, None, None, None, None)
        except SystemExit as e:
            assert "is required" in str(e)
        else:
            raise AssertionError("complete() with no --verdict on a non-VERIFY phase must raise")

        # VERIFY complete() before verify-merge-findings.py wrote a verdict
        # must also fail loudly, not silently pass with a null verdict.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "verify", 0, None, None, None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        try:
            do_complete(state, "verify", None, None, None, None, None, None)
        except SystemExit as e:
            assert "still null" in str(e)
        else:
            raise AssertionError("VERIFY complete() with no verdict anywhere must raise")

        # VERIFY respawn must clear the prior round's on-disk artifacts too —
        # a stale round-0 pair findings file would otherwise read as
        # current-round spawn evidence in verify-merge-findings.py
        # (iter-0060 R0 finding: current-round spawn evidence).
        for name in (
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.findings.judge-codex.jsonl",
            "verify-merged.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
            "claude-judge.stderr",
            "pair-judge.summary.json",
        ):
            (devlyn / name).write_text("stale\n", encoding="utf-8")
        (devlyn / "codex-primary-judge.prompt.md").write_text("current\n", encoding="utf-8")
        (devlyn / "spec-verify.json").write_text("{}", encoding="utf-8")
        clear_verify_round_artifacts(devlyn)
        for name in (
            "verify.findings.jsonl",
            "verify.pair.findings.jsonl",
            "verify.findings.judge-codex.jsonl",
            "verify-merged.findings.jsonl",
            "verify-merge.summary.json",
            "codex-judge.stdout",
            "claude-judge.stdout",
            "claude-judge.stderr",
            "pair-judge.summary.json",
        ):
            assert not (devlyn / name).exists(), f"{name} must be cleared on VERIFY spawn"
        assert (devlyn / "codex-primary-judge.prompt.md").exists(), "judge prompts must survive VERIFY spawn"
        assert (devlyn / "spec-verify.json").exists(), "non-VERIFY-round files must survive"

        # Fix-loop respawn of phase-gated IMPLEMENT must preserve `exec`
        # (routing truth for large runs, state-schema.md line 55) — spawn
        # merges into the existing entry rather than replacing it wholesale.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "claude", None)
        state["phases"]["implement"]["exec"] = {
            "total": 3, "current": 3, "statuses": ["PASS", "PASS", "PASS"], "commits": ["a", "b", "c"],
        }
        write_state(state_path, state)
        state = read_state(state_path)
        do_complete(state, "implement", "PASS", None, None, None, None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        do_spawn(state, "implement", 1, "verify", None, None, None)
        write_state(state_path, state)
        respawned_exec = read_state(state_path)["phases"]["implement"]
        assert respawned_exec["exec"]["current"] == 3, "spawn must not clobber unowned fields like exec"
        assert respawned_exec["verdict"] is None, "respawn still nulls owned fields even with exec present"
        assert len(respawned_exec["history"]) == 1
        assert respawned_exec["history"][0]["verdict"] == "PASS"

        # Existing history is append-only; a respawn must not clobber prior
        # entries that were already preserved from older rounds.
        write_state(state_path, {
            "phases": {
                "implement": {
                    "started_at": "2026-01-01T00:00:02.000Z",
                    "completed_at": "2026-01-01T00:00:03.000Z",
                    "duration_ms": 1000,
                    "round": 2,
                    "triggered_by": "verify",
                    "verdict": "FAIL",
                    "engine": "codex",
                    "history": [{
                        "started_at": "2026-01-01T00:00:00.000Z",
                        "verdict": "FAIL",
                        "completed_at": "2026-01-01T00:00:01.000Z",
                        "duration_ms": 1000,
                    }],
                }
            }
        })
        state = read_state(state_path)
        do_spawn(state, "implement", 3, "verify", None, None, None)
        write_state(state_path, state)
        history_preserved = read_state(state_path)["phases"]["implement"]["history"]
        assert len(history_preserved) == 2
        assert history_preserved[0]["started_at"] == "2026-01-01T00:00:00.000Z"
        assert history_preserved[1]["started_at"] == "2026-01-01T00:00:02.000Z"

        # complete() records a post-state commit when a bounded phase needs an
        # exact diff window for later mechanical checks.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "cleanup", 0, None, "pre-sha", None, None)
        write_state(state_path, state)
        state = read_state(state_path)
        do_complete(state, "cleanup", "PASS", "post-sha", None, None, None, None)
        write_state(state_path, state)
        cleanup_entry = read_state(state_path)["phases"]["cleanup"]
        assert cleanup_entry["pre_sha"] == "pre-sha"
        assert cleanup_entry["post_sha"] == "post-sha"

        # SURFACE_CLOSE keeps its one-shot envelope, adjudication grammar,
        # scope boundary, rollback, and execution prohibition mechanical.
        work = devlyn / "surface-repo"
        work.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        subprocess.run(["git", "config", "user.email", "self-test@example.invalid"], cwd=work, check=True)
        subprocess.run(["git", "config", "user.name", "self-test"], cwd=work, check=True)
        (work / "allowed.txt").write_text("base\n", encoding="utf-8")
        (work / "blocked.txt").write_text("base\n", encoding="utf-8")
        (work / "blocked:literal.txt:1").write_text("base\n", encoding="utf-8")
        (work / "blocked:raw.txt").write_text("base\n", encoding="utf-8")
        (work / "branchbase").write_text("line\n" * 10, encoding="utf-8")
        (work / "branchbase:7").write_text("base\n", encoding="utf-8")
        (work / "branchbase:dir").mkdir()
        (work / "branchbase:dir" / "marker").write_text("base\n", encoding="utf-8")
        (work / "exact:1").write_text("base\n", encoding="utf-8")
        (work / "schedule").mkdir()
        (work / "schedule" / "__init__.py").write_text("line\n" * 700, encoding="utf-8")
        (work / "test_schedule.py").write_text("line\n", encoding="utf-8")
        (work / "tests").mkdir()
        (work / "tests" / "cli.test.js").write_text("line\n" * 170, encoding="utf-8")
        (work / "tests" / "literal:1-3").write_text("line\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "--", "allowed.txt", "blocked.txt", "blocked:literal.txt:1",
             "blocked:raw.txt", "branchbase", "branchbase:7", "branchbase:dir/marker",
             "exact:1", "schedule/__init__.py", "test_schedule.py", "tests/cli.test.js",
             "tests/literal:1-3"],
            cwd=work, check=True,
        )
        subprocess.run(["git", "commit", "-qm", "base"], cwd=work, check=True)
        pre_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=work, check=True, capture_output=True, text=True,
        ).stdout.strip()
        work_devlyn = work / ".devlyn"
        work_devlyn.mkdir()
        (work / "kept.txt").write_text("keep\n", encoding="utf-8")
        goal = work_devlyn / "goal.raw.txt"
        patch = work_devlyn / "surface-close.input.patch"
        prompt = work_devlyn / "surface-close.prompt"
        goal.write_text("goal\n", encoding="utf-8")
        patch.write_text("patch\n", encoding="utf-8")
        prompt.write_text("adapter\nbody\ninputs\n", encoding="utf-8")
        surface_state = {
            "source": {
                "goal_path": ".devlyn/goal.raw.txt",
                "goal_sha256": file_sha256(goal),
            },
            "phases": {},
        }
        for rejected_engine in (None, "codex"):
            rejected_state = {"sentinel": True}
            try:
                do_spawn(
                    rejected_state, "surface_close", 0, None, pre_sha, rejected_engine, "sonnet",
                    input_patch_sha256=file_sha256(patch), prompt_sha256=file_sha256(prompt),
                    untracked_before=["kept.txt"],
                )
            except SystemExit as exc:
                assert "requires --engine claude" in str(exc)
            else:
                raise AssertionError("SURFACE_CLOSE accepted a non-Claude engine")
            assert rejected_state == {"sentinel": True}
        rejected_state = {"sentinel": True}
        try:
            do_spawn(
                rejected_state, "surface_close", 0, None, pre_sha, "claude", None,
                input_patch_sha256=file_sha256(patch), prompt_sha256=file_sha256(prompt),
                untracked_before=["kept.txt"],
            )
        except SystemExit as exc:
            assert "phases.surface_close spawn requires --model" in str(exc)
        else:
            raise AssertionError("SURFACE_CLOSE accepted a missing requested model")
        assert rejected_state == {"sentinel": True}
        do_spawn(
            surface_state, "surface_close", 0, None, pre_sha, "claude", "sonnet",
            input_patch_sha256=file_sha256(patch), prompt_sha256=file_sha256(prompt),
            untracked_before=["kept.txt"],
        )
        validate_surface_inputs(work, work_devlyn, surface_state)
        validate_surface_prompt(work_devlyn, surface_state)
        ensure_surface_clean_baseline(work, work_devlyn, surface_state)
        (work_devlyn / "pipeline.state.json").write_text(
            json.dumps(surface_state), encoding="utf-8",
        )
        for entry in ("src/{a,b", "src/{a,}/**", "src/{a,{b,c}}", "src/{a,**}"):
            surface_check = subprocess.run(
                [
                    sys.executable, str(pathlib.Path(__file__).resolve()),
                    "--devlyn-dir", ".devlyn", "--phase", "surface_close", "surface-check",
                    "--authorized-surface-json", json.dumps([entry]),
                ],
                cwd=work, capture_output=True, text=True,
            )
            if (
                surface_check.returncode == 0
                or "error: unsupported brace glob" not in surface_check.stderr
                or "supported form" not in surface_check.stderr
                or "Traceback" in surface_check.stderr
            ):
                raise AssertionError(f"surface-check did not fail closed for {entry}: {surface_check.stderr}")
        surface = validate_authorized_surface(
            '["allowed.txt", "branchbase", "exact-link", "exact:1", "schedule/**", '
            '"test_schedule.py", "tests/**", "x.ts"]'
        )
        assert path_matches_surface("src/a/example.py", ["src/{a,b}/**"])
        assert path_matches_surface("src/b/example.py", ["src/{a,b}/**"])
        assert not path_matches_surface("src/c/example.py", ["src/{a,b}/**"])
        for entry in ("src/{a,b", "src/{a,}/**", "src/{a,{b,c}}", "src/{a,**}"):
            try:
                validate_authorized_surface(json.dumps([entry]))
            except SystemExit as exc:
                assert str(exc).startswith("error: unsupported brace glob") and "supported form" in str(exc)
            else:
                raise AssertionError(f"malformed brace glob passed validation: {entry}")
            try:
                path_matches_surface("src/a/example.py", [entry])
            except ValueError as exc:
                assert entry in str(exc) and "supported form" in str(exc)
            else:
                raise AssertionError(f"malformed brace glob accepted: {entry}")
        outside = devlyn / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        (work / "outside-link").symlink_to(outside)
        assert worktree_file_exists(work, "allowed.txt")
        assert not worktree_file_exists(work, str(outside))
        assert not worktree_file_exists(work, "../outside.txt")
        assert not worktree_file_exists(work, "outside-link")
        assert worktree_path_exists(work, "branchbase:dir")
        assert not worktree_path_exists(work, str(outside))
        assert not worktree_path_exists(work, "../outside.txt")
        assert not worktree_path_exists(work, "outside-link")
        (work / "outside-link").unlink()
        for link, target in (
            ("exact-link", "allowed.txt"),
            ("tests/inside-link", "cli.test.js"),
        ):
            (work / link).symlink_to(target)
            output = work_devlyn / "surface-close.stdout"
            output.write_text(
                f"UVR-STALE: N/A {link} — contained symlink\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                encoding="utf-8",
            )
            validate_surface_adjudication(
                work, work_devlyn, surface_state, surface,
            )
            (work / link).unlink()
        for link in ("exact-link", "tests/outside-link"):
            (work / link).symlink_to(outside)
            output = work_devlyn / "surface-close.stdout"
            output.write_text(
                f"UVR-STALE: N/A {link} — escaping symlink\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                encoding="utf-8",
            )
            try:
                validate_surface_adjudication(
                    work, work_devlyn, surface_state, surface,
                )
            except SystemExit as exc:
                assert "citation-missing" in str(exc), (link, exc)
            else:
                raise AssertionError(f"SURFACE_CLOSE followed escaping symlink: {link}")
            (work / link).unlink()
        entry = surface_entry(surface_state)
        assert entry["prompt_sha256"] == file_sha256(prompt)
        assert entry["model_requested"] == "sonnet"
        try:
            do_spawn(surface_state, "surface_close", 1, None, pre_sha, "claude", "sonnet")
        except SystemExit as exc:
            assert "one-shot" in str(exc)
        else:
            raise AssertionError("SURFACE_CLOSE re-entry must fail")

        output = work_devlyn / "surface-close.stdout"
        output.write_text(
            "UVR-STALE: FIRED allowed.txt:1\n"
            "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
            encoding="utf-8",
        )
        assert validate_surface_adjudication(work, work_devlyn, surface_state, surface) == {
            "UVR-STALE": "FIRED", "PATH-TEST": "FIRED",
        }
        output.write_text(
            "UVR-STALE: FIRED allowed.txt:1 — updated visible text\n"
            "PATH-TEST: N/A allowed.txt:1 — goal names no uncovered path\nPASS\n",
            encoding="utf-8",
        )
        validate_surface_adjudication(work, work_devlyn, surface_state, surface)
        output.write_text(
            "UVR-STALE: N/A exact:1 — exact colon path is unchanged\n"
            "PATH-TEST: N/A exact:1:1 — exact colon path line is covered\nPASS\n",
            encoding="utf-8",
        )
        validate_surface_adjudication(work, work_devlyn, surface_state, surface)
        output.write_text(
            "UVR-STALE: N/A tests/literal:1-3 — literal range-shaped path is unchanged\n"
            "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
            encoding="utf-8",
        )
        validate_surface_adjudication(work, work_devlyn, surface_state, surface)

        output.write_text(
            "PATH-TEST review confirms every success/failure path the goal specifies (chaining in both positions, exact-nth-run cancellation via both `run_pending()` and `run_all()`, first-limit-wins with `.until()` in both directions, `next_run`/`idle_seconds` reflecting removal, validation errors, repeated-call override, per-job independence) is already covered by the added tests — no gap found.\n\n"
            "UVR-STALE: FIRED schedule/__init__.py:690 — `Job.run()`'s docstring described CancelJob only via `.until()`'s deadline, omitting the new `max_runs` cancellation path added to the same method in this diff (line 715); updated the docstring minimally.\n"
            "PATH-TEST: N/A test_schedule.py — every success/failure path in the goal (chaining order, exact-nth-run cutoff via both `run_pending()`/`run_all()`, `.until()` first-limit-wins both directions, `next_run`/`idle_seconds` post-removal, validation errors, repeat-call override, per-job independence) already has a covering test in the patch.\n"
            "PASS\n",
            encoding="utf-8",
        )
        validate_surface_adjudication(work, work_devlyn, surface_state, surface)
        output.write_text(
            "UVR-STALE: N/A tests/cli.test.js — USAGE in bin/cli.js was already updated in this patch to document `fulfill-wave --input PATH`; no authorized file has stale interface text.\n"
            "PATH-TEST: FIRED tests/cli.test.js:166 — goal names \"file-read failures\" as a distinct exit-2 path, implemented via the shared catch in `runFulfillWave`, but untested before this addition.\n"
            "PASS\n",
            encoding="utf-8",
        )
        validate_surface_adjudication(work, work_devlyn, surface_state, surface)

        rejected_outputs = (
            ("PASS\n", "missing UVR-STALE, PATH-TEST"),
            (
                "UVR-STALE: N/A allowed.txt:1\n"
                "PATH-TEST: N/A allowed.txt:1 — evidence\nPASS\n",
                "requires evidence",
            ),
            ("UVR-STALE: FIRED allowed.txt:1\nPASS\n", "missing PATH-TEST"),
            (
                "UVR-STALE: FIRED allowed.txt:1\n"
                "UVR-STALE: FIRED allowed.txt:1\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "duplicate UVR-STALE",
            ),
            (
                "PASS\nUVR-STALE: FIRED allowed.txt:1\n"
                "PATH-TEST: FIRED allowed.txt:1\n",
                "exactly one PASS must follow both rows",
            ),
            (
                "UVR-STALE: N/A allowed.txt — \n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "requires evidence",
            ),
            (
                "UVR-STALE: FIRED blocked.txt:1\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: FIRED allowed.txt:2\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "citation-missing",
            ),
            (
                "UVR-STALE: N/A allowed.txt:49-73,223-235,293-295 — production range citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A allowed.txt:1, allowed.txt:1 — production list citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A tests/cli.test.js:1-3 — glob range citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A x.ts:12:34 — doubled line citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A allowed.txt:0 — zero line citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A allowed.txt:012 — leading-zero line citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A allowed.txt: — empty line citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "adjudication-malformed",
            ),
            (
                "UVR-STALE: N/A blocked.txt:1 — blocked parsed path\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A blocked.txt:1-3 — blocked range citation\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A blocked:literal.txt:1 — blocked raw colon path\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A blocked:raw.txt:1 — blocked parsed colon path\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A branchbase:7 — existing unauthorized raw path\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A branchbase:dir:1 — existing unauthorized parsed directory\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A tests/../blocked.txt:1 — wildcard traversal\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: N/A tests/ghost.txt:1 — nonexistent glob descendant\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "citation-missing",
            ),
        )
        for raw_output, marker in rejected_outputs:
            output.write_text(raw_output, encoding="utf-8")
            try:
                validate_surface_adjudication(work, work_devlyn, surface_state, surface)
            except SystemExit as exc:
                assert marker in str(exc), (marker, exc)
            else:
                raise AssertionError(f"SURFACE_CLOSE accepted invalid adjudication: {marker}")

        output.write_text(
            "UVR-STALE: N/A allowed.txt:49-73,223-235,293-295 — production range citation\n"
            "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
            encoding="utf-8",
        )
        require_surface_adjudication_malformed(
            work, work_devlyn, surface_state, surface,
        )
        output.write_text(
            "UVR-STALE: N/A allowed.txt:1 — no stale interface text\n"
            "PATH-TEST: N/A allowed.txt:1 — requested path already covered\nPASS\n",
            encoding="utf-8",
        )
        validate_surface_adjudication(work, work_devlyn, surface_state, surface)

        transcript = work_devlyn / "surface-close.worker-session.0.jsonl"
        transcript.write_text(json.dumps({
            "message": {"content": [{
                "type": "tool_use", "name": "Bash",
                "input": {"command": "git diff -- allowed.txt"},
            }]},
        }) + "\n", encoding="utf-8")
        validate_surface_execution(work_devlyn, surface_state)
        for validation_command in ("npm test", "node bin/cli.js version"):
            transcript.write_text(json.dumps({
                "message": {"content": [{
                    "type": "tool_use", "name": "Bash",
                    "input": {"command": validation_command},
                }]},
            }) + "\n", encoding="utf-8")
            try:
                validate_surface_execution(work_devlyn, surface_state)
            except SystemExit as exc:
                assert "validation-execution" in str(exc)
            else:
                raise AssertionError(
                    f"SURFACE_CLOSE execution audit accepted {validation_command}"
                )

        transcript.write_text(
            json.dumps({"message": {"content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": str(work / "allowed.txt")}},
                {"type": "tool_use", "name": "Write", "input": {"file_path": "tests/new.txt"}},
            ]}}) + "\n",
            encoding="utf-8",
        )
        assert validate_surface_write_audit(
            work, work_devlyn, surface_state, surface,
        ) == ["allowed.txt", "tests/new.txt"]
        for invalid_target in (str(work / "blocked.txt"), str(work_devlyn / "hidden.txt"), "../escape.txt"):
            transcript.write_text(
                json.dumps({"message": {"content": [{
                    "type": "tool_use", "name": "Edit",
                    "input": {"file_path": invalid_target},
                }]}}) + "\n",
                encoding="utf-8",
            )
            try:
                validate_surface_write_audit(work, work_devlyn, surface_state, surface)
            except SystemExit as exc:
                assert "write-audit-violation" in str(exc)
            else:
                raise AssertionError(f"SURFACE_CLOSE write audit accepted {invalid_target}")

        wrapper_log = work_devlyn / "surface-close.output.json"
        wrapper_log.write_text(json.dumps({
            "result": output.read_text(encoding="utf-8"),
            "modelUsage": {"sonnet": {"inputTokens": 1}},
        }) + "\n", encoding="utf-8")
        completion_state = loads_strict_json(json.dumps(surface_state))
        assert do_complete(
            completion_state, "surface_close", "PASS", pre_sha, None,
            ".devlyn/surface-close.stdout", None, None, str(wrapper_log),
            devlyn=work_devlyn,
        ) is None
        completed_surface = completion_state["phases"]["surface_close"]
        assert completed_surface["model_requested"] == "sonnet"
        assert completed_surface["model_effective"] == "sonnet"
        assert completed_surface["verdict"] == "PASS"

        recovery_state = loads_strict_json(json.dumps(surface_state))
        recovery_started_at = recovery_state["phases"]["surface_close"]["started_at"]
        output.write_text("UVR-STALE: FIRED allowed.txt:1\nPASS\n", encoding="utf-8")
        (work / "allowed.txt").write_text("surface edit\n", encoding="utf-8")
        transcript.write_text(
            json.dumps({"message": {"content": [{
                "type": "tool_use", "name": "Edit",
                "input": {"file_path": str(work / "allowed.txt")},
            }]}}) + "\n",
            encoding="utf-8",
        )
        require_surface_adjudication_malformed(
            work, work_devlyn, recovery_state, surface,
        )
        assert rollback_surface_delta(work, work_devlyn, recovery_state) == ["allowed.txt"]
        assert validate_surface_write_audit(
            work, work_devlyn, recovery_state, surface,
        ) == ["allowed.txt"]
        assert do_surface_adjudication_recovery(recovery_state, work_devlyn) is None
        recovered = recovery_state["phases"]["surface_close"]
        assert recovered["started_at"] == recovery_started_at
        assert isinstance(recovered["duration_ms"], int)
        assert recovered["verdict"] is None
        assert recovered["skipped_reason"] == SURFACE_RECOVERY_REASON
        assert recovered["continued_after_block"] is True

        (work / "allowed.txt").write_text("pre-existing\n", encoding="utf-8")
        try:
            ensure_surface_clean_baseline(work, work_devlyn, surface_state)
        except SystemExit as exc:
            assert "surface-close-preexisting-delta" in str(exc)
        else:
            raise AssertionError("SURFACE_CLOSE accepted a pre-existing tracked delta")
        subprocess.run(["git", "restore", "--", "allowed.txt"], cwd=work, check=True)
        (work / "allowed.txt").write_text("changed\n", encoding="utf-8")
        (work / "blocked.txt").write_text("changed\n", encoding="utf-8")
        (work / "tests" / "new.txt").write_text("new\n", encoding="utf-8")
        (work / "escape.txt").write_text("new\n", encoding="utf-8")
        assert surface_offenders(work, work_devlyn, surface_state, surface) == ["blocked.txt", "escape.txt"]
        restored = rollback_surface_delta(work, work_devlyn, surface_state)
        assert restored == ["allowed.txt", "blocked.txt", "escape.txt", "tests/new.txt"]
        assert (work / "allowed.txt").read_text(encoding="utf-8") == "base\n"
        assert (work / "blocked.txt").read_text(encoding="utf-8") == "base\n"
        assert (work / "kept.txt").read_text(encoding="utf-8") == "keep\n"
        assert not (work / "tests" / "new.txt").exists()
        assert not (work / "escape.txt").exists()

        skipped_state = {"phases": {}}
        do_surface_skip(skipped_state)
        skipped = skipped_state["phases"]["surface_close"]
        assert skipped["verdict"] is None
        assert skipped["skipped_reason"] == SURFACE_SKIP_REASON

        # Effective model evidence: handwritten headers are not provenance;
        # canonical rollout JSONL and Claude wrapper output remain accepted.
        header_log = devlyn / "codex-build.log"
        header_log.write_text("session\nmodel: gpt-5.6-sol\n", encoding="utf-8")
        try:
            parse_effective_model(header_log)
        except ValueError as exc:
            assert "no effective-model evidence" in str(exc)
        else:
            raise AssertionError("plaintext model header was accepted as provenance")
        rollout_log = devlyn / "rollout.jsonl"
        rollout_log.write_text(json.dumps({
            "type": "turn_context", "payload": {"model": "gpt-5.6-terra"},
        }) + "\n", encoding="utf-8")
        assert parse_effective_model(rollout_log) == "gpt-5.6-terra"
        claude_log = devlyn / "claude-result.json"

        def claude_wrapper(primary_usage, entries):
            wrapper = {"modelUsage": {}}
            if primary_usage is not None:
                wrapper["usage"] = dict(zip((
                    "input_tokens", "output_tokens", "cache_read_input_tokens",
                    "cache_creation_input_tokens",
                ), primary_usage))
            for model, entry_usage, metadata in entries:
                entry = dict(zip((
                    "inputTokens", "outputTokens", "cacheReadInputTokens",
                    "cacheCreationInputTokens",
                ), entry_usage))
                entry.update(metadata)
                wrapper["modelUsage"][model] = entry
            return wrapper

        oversized_counter = 10 ** 400
        claude_selector_rows = (
            (
                "singleton",
                {"modelUsage": {"claude-alpha-1": {"inputTokens": 1}}},
                "claude-alpha-1",
            ),
            (
                "opus-primary",
                claude_wrapper(
                    (2854, 9927, 1095180, 73889),
                    (
                        ("claude-" "haiku-4-5-20251001", (4106, 14, 0, 0), {
                            "costUSD": 0.004176,
                        }),
                        ("claude-" "opus-5[1m]", (2854, 9927, 1095180, 73889), {
                            "costUSD": 1.5489249999999999,
                            "canonicalModel": "claude-" "opus-5",
                        }),
                    ),
                ),
                "claude-" "opus-5[1m]",
            ),
            (
                "fable-primary",
                claude_wrapper(
                    (8068, 26740, 403950, 76656),
                    (
                        ("claude-" "haiku-4-5-20251001", (2246, 22, 0, 0), {
                            "costUSD": 0.002356,
                        }),
                        ("claude-" "fable-5", (8068, 26740, 403950, 76656), {
                            "costUSD": 3.35475,
                            "canonicalModel": "claude-" "fable-5",
                        }),
                    ),
                ),
                "claude-" "fable-5",
            ),
            (
                "rank-confound",
                claude_wrapper(
                    (3, 5, 7, 11),
                    (
                        ("larger-auxiliary", (300000, 500000, 700000, 1100000), {
                            "costUSD": 999.0,
                        }),
                        ("expected-primary", (3, 5, 7, 11), {"costUSD": 0.01}),
                    ),
                ),
                "expected-primary",
            ),
            (
                "oversized-integer",
                claude_wrapper(
                    (oversized_counter, 5, 7, 11),
                    (
                        ("oversized-primary", (oversized_counter, 5, 7, 11), {}),
                        ("auxiliary", (3, 5, 7, 11), {}),
                    ),
                ),
                "oversized-primary",
            ),
            (
                "zero-match",
                claude_wrapper(
                    (1, 2, 3, 4),
                    (("model-a", (10, 2, 3, 4), {}), ("model-b", (1, 20, 3, 4), {})),
                ),
                ValueError,
            ),
            (
                "duplicate-match",
                claude_wrapper(
                    (1, 2, 3, 4),
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (1, 2, 3, 4), {})),
                ),
                ValueError,
            ),
            (
                "missing-top-level-usage",
                claude_wrapper(
                    None,
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (5, 6, 7, 8), {})),
                ),
                ValueError,
            ),
            (
                "malformed-top-level-float",
                claude_wrapper(
                    (1.0, 2, 3, 4),
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (5, 6, 7, 8), {})),
                ),
                ValueError,
            ),
            (
                "malformed-top-level-negative",
                claude_wrapper(
                    (-1, 2, 3, 4),
                    (("model-a", (-1, 2, 3, 4), {}), ("model-b", (5, 6, 7, 8), {})),
                ),
                ValueError,
            ),
            (
                "malformed-entry-counter",
                claude_wrapper(
                    (1, 2, 3, 4),
                    (("model-a", (1, 2, 3, 4), {}), ("model-b", (True, 20, 30, 40), {})),
                ),
                ValueError,
            ),
        )
        for row_name, wrapper, expected in claude_selector_rows:
            claude_log.write_text(json.dumps(wrapper) + "\n", encoding="utf-8")
            if expected is ValueError:
                try:
                    parse_effective_model(claude_log)
                except ValueError:
                    pass
                else:
                    raise AssertionError(f"Claude selector accepted {row_name}")
            else:
                assert parse_effective_model(claude_log) == expected, row_name

        claude_log.write_text(
            json.dumps(claude_selector_rows[-1][1]) + "\n", encoding="utf-8"
        )
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, None, "claude", "claude-default",
            prompt_sha256=digest0,
        )
        malformed = do_complete(
            state, "plan", "PASS", None, None, None, None, None, str(claude_log)
        )
        assert malformed and "model-attestation-failed" in malformed
        assert state["phases"]["plan"]["model_effective"] is None
        assert state["phases"]["plan"]["verdict"] == "BLOCKED"

        # Requested/effective drift is a persisted, fail-closed attestation.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "codex", "gpt-5.5")
        mismatch = do_complete(
            state, "implement", "PASS", None, None, None, None, None, str(rollout_log)
        )
        mismatched = state["phases"]["implement"]
        assert mismatch and "model-attestation-mismatch" in mismatch
        assert mismatched["model_requested"] == "gpt-5.5"
        assert mismatched["model_effective"] == "gpt-5.6-terra"
        assert mismatched["verdict"] == "BLOCKED"

        claude_log.write_text(
            json.dumps(claude_selector_rows[1][1]) + "\n", encoding="utf-8"
        )
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "build_gate", 0, None, None, "claude", "claude-" "opus-5")
        mismatch = do_complete(
            state, "build_gate", "PASS", None, None, None, None, None, str(claude_log)
        )
        mismatched = state["phases"]["build_gate"]
        assert mismatch and "model-attestation-mismatch" in mismatch
        assert mismatched["model_requested"] == "claude-" "opus-5"
        assert mismatched["model_effective"] == "claude-" "opus-5[1m]"
        assert mismatched["verdict"] == "BLOCKED"

        # A retained mutation-worker session makes the completion flag
        # mandatory; without a retained file, null remains legal.
        retained_log = devlyn / "implement.worker-session.0.jsonl"
        retained_log.write_text(json.dumps({
            "type": "turn_context", "payload": {"model": "gpt-5.6-terra"},
        }) + "\n", encoding="utf-8")
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "codex", "gpt-5.6-terra")
        omitted = do_complete(
            state, "implement", "PASS", None, None, None, None, None,
            devlyn=devlyn,
        )
        assert omitted and "model-attestation-failed" in omitted
        assert str(retained_log) in omitted
        assert state["phases"]["implement"]["model_effective"] is None
        assert state["phases"]["implement"]["verdict"] == "BLOCKED"

        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "implement", 0, None, None, "codex", "gpt-5.6-terra")
        assert do_complete(
            state, "implement", "PASS", None, None, None, None, None,
            str(retained_log), devlyn=devlyn,
        ) is None
        assert state["phases"]["implement"]["model_effective"] == "gpt-5.6-terra"
        assert state["phases"]["implement"]["verdict"] == "PASS"

        receipt_work = devlyn / "receipt-work"
        receipt_devlyn = receipt_work / ".devlyn"
        receipt_devlyn.mkdir(parents=True)
        receipt_prompt = receipt_devlyn / "implement.prompt.0"
        receipt_prompt.write_text("implement exactly\n", encoding="utf-8")
        receipt_session = receipt_devlyn / "implement.worker-session.0.jsonl"
        receipt_session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        receipt_path = receipt_devlyn / "implement.invocation.0.json"
        receipt_model = "gpt-5.6-sol"
        receipt_prompt_sha = hashlib.sha256(receipt_prompt.read_bytes()).hexdigest()
        inherited_engine_state = {
            "version": "3.0",
            "run_id": "rs-inherited-engine",
            "engine": "codex",
            "phases": {"implement": None},
        }
        try:
            do_spawn(
                inherited_engine_state, "implement", 0, None, None, None, None,
                prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
            )
        except SystemExit as exc:
            assert "spawn requires --model" in str(exc)
        else:
            raise AssertionError("schema-v3 inherited Codex engine accepted no model")
        do_spawn(
            inherited_engine_state, "implement", 0, None, None, None, receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        assert inherited_engine_state["phases"]["implement"]["engine"] == "codex"
        receipt_state = {
            "version": "3.0",
            "run_id": "rs-invocation-state",
            "engine": "codex",
            "phases": {"implement": None},
        }
        do_spawn(
            receipt_state, "implement", 0, None, None, "codex", receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        receipt_runner = invocation_receipt_module()
        receipt_runner.start_receipt(
            receipt_work, receipt_path, receipt_state["run_id"], "implement", 0,
            str(receipt_prompt), str(receipt_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write", "-m", receipt_model,
             "-c", "sandbox_workspace_write.network_access=false", "implement exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, receipt_path, 0)
        rerouted_state = copy.deepcopy(receipt_state)
        assert do_complete(
            receipt_state, "implement", "PASS", None, None, None, None, None,
            str(receipt_session), devlyn=receipt_devlyn, work=receipt_work,
        ) is None
        receipt_entry = receipt_state["phases"]["implement"]
        assert receipt_entry["model_effective"] is None
        assert receipt_entry["model_requested"] == receipt_model
        assert receipt_entry["invocation_receipt"]["path"] == (
            ".devlyn/implement.invocation.0.json"
        )

        # A native reroute remains a failed phase even after a successful terminal event.
        receipt_session.write_text(
            '{"type":"item.completed","item":{"type":"error",'
            '"message":"model rerouted: gpt-5.6-sol -> other (Policy)"}}\n'
            '{"type":"turn.completed"}\n', encoding="utf-8",
        )
        receipt_path.unlink()
        receipt_runner.start_receipt(
            receipt_work, receipt_path, rerouted_state["run_id"], "implement", 0,
            str(receipt_prompt), str(receipt_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write", "-m", receipt_model,
             "-c", "sandbox_workspace_write.network_access=false", "implement exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, receipt_path, 0)
        reroute_error = do_complete(
            rerouted_state, "implement", "PASS", None, None, None, None, None,
            str(receipt_session), devlyn=receipt_devlyn, work=receipt_work,
        )
        assert reroute_error and "model reroute" in reroute_error
        assert rerouted_state["phases"]["implement"]["verdict"] == "BLOCKED"
        do_spawn(rerouted_state, "implement", 1, None, None, "codex", receipt_model,
                 prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn)
        assert rerouted_state["phases"]["implement"]["history"][-1]["verdict"] == "BLOCKED"

        plan_prompt = receipt_devlyn / "plan.prompt.0"
        plan_prompt.write_text("plan exactly\n", encoding="utf-8")
        plan_session = receipt_devlyn / "plan.worker-session.0.jsonl"
        plan_session.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        plan_path = receipt_devlyn / "plan.invocation.0.json"
        (receipt_devlyn / "plan.md").write_text("## Files to touch\n", encoding="utf-8")
        plan_model = "gpt-5.6-sol"
        plan_prompt_sha = hashlib.sha256(plan_prompt.read_bytes()).hexdigest()
        plan_state = {
            "version": "3.0",
            "run_id": "rs-plan-invocation",
            "engine": "codex",
            "phases": {"plan": None},
        }
        do_spawn(
            plan_state, "plan", 0, None, None, "codex", plan_model,
            prompt_sha256=plan_prompt_sha, devlyn=receipt_devlyn,
        )
        receipt_runner.start_receipt(
            receipt_work, plan_path, plan_state["run_id"], "plan", 0,
            str(plan_prompt), str(plan_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "plan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path, 0)
        assert do_complete(
            plan_state, "plan", "PASS", None, None, None, None, None,
            str(plan_session), devlyn=receipt_devlyn, work=receipt_work,
        ) is None
        plan_entry = plan_state["phases"]["plan"]
        assert plan_entry["model_effective"] is None
        assert plan_entry["model_requested"] == plan_model
        assert plan_entry["invocation_receipt"]["path"] == ".devlyn/plan.invocation.0.json"
        assert plan_entry["output_sha256"] == hashlib.sha256(
            (receipt_devlyn / "plan.md").read_bytes()
        ).hexdigest()
        plan_prompt_1 = receipt_devlyn / "plan.prompt.1"
        plan_prompt_1.write_text("replan exactly\n", encoding="utf-8")
        plan_session_1 = receipt_devlyn / "plan.worker-session.1.jsonl"
        plan_session_1.write_text('{"type":"thread.started"}\n', encoding="utf-8")
        plan_path_1 = receipt_devlyn / "plan.invocation.1.json"
        plan_prompt_sha_1 = hashlib.sha256(plan_prompt_1.read_bytes()).hexdigest()
        do_spawn(
            plan_state, "plan", 1, "plan", None, "codex", plan_model,
            prompt_sha256=plan_prompt_sha_1, devlyn=receipt_devlyn,
        )
        plan_history = plan_state["phases"]["plan"]["history"]
        assert plan_history[0]["invocation_receipt"]["path"] == (
            ".devlyn/plan.invocation.0.json"
        )
        assert "invocation_receipt" not in plan_state["phases"]["plan"]
        receipt_runner.start_receipt(
            receipt_work, plan_path_1, plan_state["run_id"], "plan", 1,
            str(plan_prompt_1), str(plan_session_1),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "replan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path_1, 0)
        assert do_complete(
            plan_state, "plan", "PASS", None, None, None, None, None,
            str(plan_session_1), devlyn=receipt_devlyn, work=receipt_work,
        ) is None
        assert plan_state["phases"]["plan"]["invocation_receipt"]["path"] == (
            ".devlyn/plan.invocation.1.json"
        )

        confused_state = {
            "version": "3.0",
            "run_id": "rs-invocation-confused",
            "engine": "codex",
            "phases": {"implement": None},
        }
        do_spawn(
            confused_state, "implement", 0, None, None, "codex", receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        confused_before = copy.deepcopy(confused_state)
        try:
            do_complete(
                confused_state, "implement", "PASS", None, None, None,
                "claude", receipt_model, str(receipt_session),
                devlyn=receipt_devlyn, work=receipt_work,
            )
        except SystemExit as exc:
            assert "cannot replace spawn engine" in str(exc)
        else:
            raise AssertionError("completion replaced a Codex spawn with Claude attestation")
        assert confused_state == confused_before
        try:
            do_complete(
                confused_state, "implement", "PASS", None, None, None,
                None, "other-model", str(receipt_session),
                devlyn=receipt_devlyn, work=receipt_work,
            )
        except SystemExit as exc:
            assert "cannot replace requested model" in str(exc)
        else:
            raise AssertionError("completion replaced the requested Codex model")
        assert confused_state == confused_before

        wrong_path_state = {
            "version": "3.0",
            "run_id": "rs-invocation-wrong-path",
            "engine": "codex",
            "phases": {"implement": None},
        }
        do_spawn(
            wrong_path_state, "implement", 0, None, None, "codex", receipt_model,
            prompt_sha256=receipt_prompt_sha, devlyn=receipt_devlyn,
        )
        arbitrary_log = receipt_devlyn / "handwritten.log"
        arbitrary_log.write_text(f"model: {receipt_model}\n", encoding="utf-8")
        wrong_path_error = do_complete(
            wrong_path_state, "implement", "PASS", None, None, None, None, None,
            str(arbitrary_log), devlyn=receipt_devlyn, work=receipt_work,
        )
        assert wrong_path_error and "canonical phase/round session" in wrong_path_error
        assert wrong_path_state["phases"]["implement"]["verdict"] == "BLOCKED"
        print("PASS iter-0112 canonical Codex invocation receipt and session ownership")

        # Iter-0121: rs-20260906T173436Z-5a086a70590e exited 1 with an
        # empty canonical session and no plan. Exercise the real CLI writes.
        receipt_state_path = receipt_devlyn / "pipeline.state.json"
        missing_plan_output = receipt_devlyn / "plan.md"
        missing_plan_output.unlink()
        plan_session.write_bytes(b"")
        plan_path.unlink()
        receipt_runner.start_receipt(
            receipt_work, plan_path, plan_state["run_id"], "plan", 0,
            str(plan_prompt), str(plan_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "plan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path, 1)
        failed_receipt_bytes = plan_path.read_bytes()

        def receipt_cli(phase: str, *event_args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [sys.executable, script, "--devlyn-dir", str(receipt_devlyn),
                 "--phase", phase, *event_args],
                cwd=receipt_work, capture_output=True, text=True, check=False,
            )

        write_state(receipt_state_path, {
            "version": "3.0", "run_id": plan_state["run_id"],
            "engine": "codex", "phases": {},
        })
        result = receipt_cli(
            "plan", "spawn", "--round", "0", "--engine", "codex",
            "--model", plan_model, "--prompt-sha256", plan_prompt_sha,
        )
        assert result.returncode == 0, result.stderr
        open_plan_bytes = receipt_state_path.read_bytes()
        blocked_args = (
            "--verdict", "BLOCKED", "--engine-session-log", str(plan_session),
        )
        result = receipt_cli("plan", "complete", *blocked_args)
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:invocation-receipt-invalid: Codex invocation exited 1" in result.stderr, result.stderr
        blocked_plan = read_state(receipt_state_path)["phases"]["plan"]
        assert blocked_plan["verdict"] == "BLOCKED"
        assert blocked_plan["output_sha256"] is None
        assert blocked_plan["model_effective"] is None
        assert blocked_plan["completed_at"] is not None
        assert blocked_plan["duration_ms"] == round((
            parse_iso(blocked_plan["completed_at"]) - parse_iso(blocked_plan["started_at"])
        ).total_seconds() * 1000)
        assert blocked_plan["duration_ms"] >= 0
        assert not os.path.lexists(missing_plan_output)
        assert plan_path.read_bytes() == failed_receipt_bytes
        print("PASS iter-0121 failed PLAN worker persists BLOCKED timing/null output and receipt error")

        for phase, event_args in [
            (phase, (
                "spawn", "--round", "1" if phase == "plan" else "0",
                "--triggered-by", "plan", "--engine", "codex",
                "--model", plan_model, "--prompt-sha256", plan_prompt_sha,
            )) for phase in sorted(PHASE_NAMES - {"final_report"})
        ] + [
            ("surface_close", ("surface-skip",)),
            ("surface_close", ("surface-check", "--authorized-surface-json", "[]")),
            ("surface_close", ("surface-adjudication-recover", "--authorized-surface-json", "[]")),
            ("surface_close", ("surface-rollback",)),
            ("implement", ("durability-enforce", "--round", "1", "--origin-phase", "verify")),
        ]:
            before = receipt_state_path.read_bytes()
            result = receipt_cli(phase, *event_args)
            assert result.returncode == 1, (phase, event_args, result.stderr)
            assert "BLOCKED:plan-output-missing" in result.stderr, (phase, event_args, result.stderr)
            assert receipt_state_path.read_bytes() == before
        result = receipt_cli("final_report", "spawn", "--round", "0")
        assert result.returncode == 0, result.stderr
        blocked_report = receipt_devlyn / "final-report.md"
        blocked_report.write_text(
            f"<!-- devlyn:final-report run_id={read_state(receipt_state_path)['run_id']} -->\n"
            "# BLOCKED\nPLAN invocation failed; no PLAN output was produced.\n", encoding="utf-8",
        )
        result = receipt_cli("final_report", "complete", "--verdict", "BLOCKED", "--log-file", str(blocked_report))
        assert result.returncode == 0, result.stderr
        terminal_state = read_state(receipt_state_path)
        assert terminal_state["phases"]["plan"] == blocked_plan
        assert terminal_state["phases"]["final_report"]["completed_at"] is not None
        assert terminal_state["phases"]["final_report"]["verdict"] == "BLOCKED"
        assert terminal_state["phases"]["final_report"]["output_sha256"] == hashlib.sha256(blocked_report.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as archive_tmp:
            archive_work = pathlib.Path(archive_tmp)
            archive_devlyn = archive_work / ".devlyn"
            archive_devlyn.mkdir()
            retained = (receipt_state_path, blocked_report, plan_path, plan_prompt, plan_session)
            for source in retained:
                shutil.copy2(source, archive_devlyn / source.name)
            archived = subprocess.run(
                [sys.executable, str(pathlib.Path(script).with_name("archive_run.py"))],
                cwd=archive_work, capture_output=True, text=True,
            )
            assert archived.returncode == 0, archived.stderr
            destination = archive_devlyn / "runs" / terminal_state["run_id"]
            assert not (archive_devlyn / "pipeline.state.json").exists()
            assert not (destination / "plan.md").exists()
            assert all((destination / source.name).read_bytes() == source.read_bytes() for source in retained)
        print("PASS iter-0121 missing-output BLOCKED permits final closure and refuses all work spawns/special events")

        # Non-BLOCKED requests cannot obtain the exception via failed attestation.
        for verdict in sorted(VALID_VERDICTS - {"BLOCKED"}):
            receipt_state_path.write_bytes(open_plan_bytes)
            result = receipt_cli(
                "plan", "complete", "--verdict", verdict,
                "--engine-session-log", str(plan_session),
            )
            assert result.returncode == 1, (verdict, result.stderr)
            assert "BLOCKED:plan-integrity-invalid" in result.stderr
            assert receipt_state_path.read_bytes() == open_plan_bytes
        for next_phase in ("implement", "probe_derive", "final_report"):
            result = receipt_cli(
                "plan", "transition", *blocked_args, "--next-phase", next_phase,
                "--next-round", "0", "--next-engine", "claude",
            )
            assert result.returncode == 1, result.stderr
            assert "Codex invocation exited 1" in result.stderr
            assert receipt_state_path.read_bytes() == open_plan_bytes
        plan_path.write_text("{", encoding="utf-8")
        result = receipt_cli("plan", "complete", *blocked_args)
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:invocation-receipt-invalid" in result.stderr
        malformed_plan = read_state(receipt_state_path)["phases"]["plan"]
        assert malformed_plan["verdict"] == "BLOCKED"
        assert malformed_plan["model_effective"] is None
        assert malformed_plan["output_sha256"] is None
        assert malformed_plan["completed_at"] is not None

        # Even attested BLOCKED completion cannot transition into more work.
        plan_path.unlink()
        receipt_runner.start_receipt(
            receipt_work, plan_path, plan_state["run_id"], "plan", 0,
            str(plan_prompt), str(plan_session),
            ["--json", "-C", str(receipt_work), "-s", "workspace-write",
             "-m", plan_model, "-c",
             "sandbox_workspace_write.network_access=false", "plan exactly"],
        )
        receipt_runner.finish_receipt(receipt_work, plan_path, 0)
        receipt_state_path.write_bytes(open_plan_bytes)
        for next_phase in ("implement", "probe_derive"):
            result = receipt_cli(
                "plan", "transition", *blocked_args, "--next-phase", next_phase,
                "--next-round", "0", "--next-engine", "claude",
            )
            assert result.returncode == 1, result.stderr
            assert "BLOCKED:plan-output-missing" in result.stderr
            assert receipt_state_path.read_bytes() == open_plan_bytes
        result = receipt_cli(
            "plan", "transition", *blocked_args, "--next-phase", "final_report",
            "--next-round", "0",
        )
        assert result.returncode == 0, result.stderr
        absent_transition_bytes = receipt_state_path.read_bytes()
        assert read_state(receipt_state_path)["phases"]["plan"]["model_effective"] is None
        print("PASS iter-0121 non-BLOCKED output requirement, malformed receipt and atomic transitions")

        for path_kind in ("file", "directory", "dangling-symlink", "unreadable"):
            if path_kind == "directory":
                missing_plan_output.mkdir()
            elif path_kind == "dangling-symlink":
                missing_plan_output.symlink_to(receipt_devlyn / "missing-target")
            else:
                missing_plan_output.write_bytes(b"## Files to touch\n")
                if path_kind == "unreadable":
                    missing_plan_output.chmod(0)
            try:
                receipt_state_path.write_bytes(absent_transition_bytes)
                result = receipt_cli("final_report", "complete", "--verdict", "BLOCKED")
                assert result.returncode == 1, (path_kind, result.stderr)
                assert "BLOCKED:plan-integrity-invalid" in result.stderr
                assert receipt_state_path.read_bytes() == absent_transition_bytes
                if path_kind in {"directory", "dangling-symlink"} or (
                    path_kind == "unreadable" and not os.access(missing_plan_output, os.R_OK)
                ):
                    receipt_state_path.write_bytes(open_plan_bytes)
                    result = receipt_cli("plan", "complete", *blocked_args)
                    assert result.returncode == 1, (path_kind, result.stderr)
                    assert "BLOCKED:plan-integrity-invalid" in result.stderr
                    assert receipt_state_path.read_bytes() == open_plan_bytes
            finally:
                if path_kind == "directory":
                    missing_plan_output.rmdir()
                else:
                    if path_kind == "unreadable":
                        missing_plan_output.chmod(0o600)
                    missing_plan_output.unlink()
        print("PASS iter-0121 lexical absence rejects existing/nonregular/unreadable output")

        # BLOCKED with bytes still binds them, including across legal correction.
        missing_plan_output.write_bytes(b"## Files to touch\n")
        receipt_state_path.write_bytes(open_plan_bytes)
        result = receipt_cli("plan", "complete", *blocked_args)
        assert result.returncode == 0, result.stderr
        bound_bytes = receipt_state_path.read_bytes()
        assert read_state(receipt_state_path)["phases"]["plan"]["output_sha256"] == hashlib.sha256(
            missing_plan_output.read_bytes()
        ).hexdigest()
        result = receipt_cli(
            "plan", "spawn", "--round", "1", "--triggered-by", "plan",
            "--engine", "codex", "--model", plan_model,
            "--prompt-sha256", plan_prompt_sha_1,
        )
        assert result.returncode == 0, result.stderr
        correction_bytes = receipt_state_path.read_bytes()
        missing_plan_output.unlink()
        result = receipt_cli(
            "plan", "complete", "--verdict", "BLOCKED",
            "--engine-session-log", str(plan_session_1),
        )
        assert result.returncode == 1, result.stderr
        assert "BLOCKED:plan-integrity-invalid" in result.stderr
        assert receipt_state_path.read_bytes() == correction_bytes
        for changed in (False, True):
            if changed:
                missing_plan_output.write_bytes(b"altered plan\n")
            receipt_state_path.write_bytes(bound_bytes)
            result = receipt_cli("final_report", "spawn", "--round", "0")
            assert result.returncode == 1, result.stderr
            assert "BLOCKED:plan-integrity-" in result.stderr
            assert receipt_state_path.read_bytes() == bound_bytes
        print("PASS iter-0121 BLOCKED output binding rejects deletion/tampering and lost correction output")

        retained_log.unlink()
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "cleanup", 0, None, None, "claude", "claude-default")
        assert do_complete(
            state, "cleanup", "PASS", None, None, None, None, None,
            devlyn=devlyn,
        ) is None
        assert state["phases"]["cleanup"]["model_effective"] is None

        # Supplied evidence must parse and never silently record null.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, None, "claude", "claude-default",
            prompt_sha256=digest0,
        )
        assert do_complete(state, "plan", "PASS", None, None, None, None, None) is None
        assert state["phases"]["plan"]["model_effective"] is None
        invalid_log = devlyn / "invalid-session.log"
        invalid_log.write_text("no model evidence\n", encoding="utf-8")
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(
            state, "plan", 0, None, None, "claude", "claude-default",
            prompt_sha256=digest0,
        )
        invalid = do_complete(
            state, "plan", "PASS", None, None, None, None, None, str(invalid_log)
        )
        assert invalid and "model-attestation-failed" in invalid
        assert state["phases"]["plan"]["model_effective"] is None
        assert state["phases"]["plan"]["verdict"] == "BLOCKED"

        def write_fixture_tree(repo: pathlib.Path, files: dict[str, str]) -> None:
            existing = {
                path.relative_to(repo).as_posix() for path in repo.rglob("*")
                if path.is_file() and ".git" not in path.parts and ".devlyn" not in path.parts
            }
            for path in existing - set(files):
                (repo / path).unlink()
            for path, content in files.items():
                target = repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

        def commit_fixture(repo: pathlib.Path, files: dict[str, str], message: str) -> str:
            write_fixture_tree(repo, files)
            paths = sorted(set(files) | {
                path.relative_to(repo).as_posix() for path in repo.rglob("*")
                if path.is_file() and ".git" not in path.parts and ".devlyn" not in path.parts
            })
            subprocess.run(["git", "add", "--all", "--", *paths], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", message], cwd=repo, check=True)
            return subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                capture_output=True, text=True,
            ).stdout.strip()

        def durability_fixture(
            name: str, base_files: dict[str, str], surface_files: dict[str, str],
            fix_files: dict[str, str], origin: str, findings: list[dict], round_: int = 1,
            with_surface_post: bool = True,
        ) -> tuple[pathlib.Path, pathlib.Path, dict, str, str]:
            repo = devlyn / name
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "self-test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "self-test"], cwd=repo, check=True)
            base_sha = commit_fixture(repo, base_files, "base")
            surface_sha = commit_fixture(repo, surface_files, "surface close")
            fix_sha = commit_fixture(repo, fix_files, f"chore(pipeline): implement fix round {round_}")
            fixture_devlyn = repo / ".devlyn"
            fixture_devlyn.mkdir()
            findings_name = (
                "build_gate.findings.jsonl" if origin == "build_gate"
                else "verify-merged.findings.jsonl"
            )
            (fixture_devlyn / findings_name).write_text(
                "".join(json.dumps(finding) + "\n" for finding in findings), encoding="utf-8",
            )
            surface_entry = {"pre_sha": base_sha, "durability": []}
            if with_surface_post:
                surface_entry["post_sha"] = surface_sha
            fixture_state = {"phases": {"surface_close": surface_entry}}
            return repo, fixture_devlyn, fixture_state, fix_sha, surface_sha

        # M-CP 1/8/9: exact -19c topology. The VERIFY finding is line 60,
        # outside the pre-fix USAGE block; the unrelated real fix survives,
        # the USAGE revert is restored, and the frozen gate's check-7 function
        # observes the separate closure-restore commit's final tree.
        base_lines = [f"line {index}\n" for index in range(1, 66)]
        base_lines[6] = "const USAGE = `\n"
        base_lines[7] = "usage: cli <command>\n"
        base_lines[9] = "  version                 Show version\n"
        base_lines[10] = "`;\n"
        base_lines[59] = "  return args.indexOf('--format')\n"
        surface_lines = list(base_lines)
        surface_lines[9] = "  version --format <fmt>  Show version\n"
        fix_lines = list(base_lines)
        fix_lines[59] = "  return args.lastIndexOf('--format')\n"
        exact_repo, exact_devlyn, exact_state, exact_fix, _ = durability_fixture(
            "durability-exact", {"bin/cli.js": "".join(base_lines)},
            {"bin/cli.js": "".join(surface_lines)}, {"bin/cli.js": "".join(fix_lines)},
            "verify", [{"id": "-19c", "file": "bin/cli.js", "line": 60}],
        )
        exact_receipt = enforce_closure_durability_reentry(
            exact_repo, exact_devlyn, exact_state, "verify", 1,
        )
        exact_text = (exact_repo / "bin/cli.js").read_text(encoding="utf-8")
        assert "version --format <fmt>" in exact_text
        assert "lastIndexOf('--format')" in exact_text
        assert exact_receipt and exact_receipt["restore_commit_sha"]
        assert exact_receipt["fix_commit_sha"] == exact_fix
        assert subprocess.run(
            ["git", "show", "-s", "--format=%s", "HEAD"], cwd=exact_repo,
            check=True, capture_output=True, text=True,
        ).stdout.strip() == "chore(pipeline): closure-restore round 1"
        gate_spec = importlib.util.spec_from_file_location(
            "f7_carrier_gate", pathlib.Path(__file__).resolve().parents[3]
            / "benchmark/ceiling/scripts/f7-carrier-gate.py",
        )
        gate = importlib.util.module_from_spec(gate_spec)
        gate_spec.loader.exec_module(gate)
        assert gate.check7(exact_text)[0]
        print("PASS M-CP self-test 1/8/9: -19c restore + file-line targeting + frozen check 7")

        # M-CP 2: BUILD_GATE uses the same durability route.
        build_repo, build_devlyn, build_state, _, _ = durability_fixture(
            "durability-build", {"a.txt": "old\n"}, {"a.txt": "surface\n"},
            {"a.txt": "old\n"}, "build_gate",
            [{"id": "BG", "file": "a.txt", "line": 8}],
        )
        build_state["phases"]["implement"] = {"round": 1, "triggered_by": "build_gate"}
        write_state(build_devlyn / "pipeline.state.json", build_state)
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--devlyn-dir", ".devlyn",
             "--phase", "implement", "durability-enforce", "--round", "1",
             "--origin-phase", "build_gate"],
            cwd=build_repo, check=True, capture_output=True,
        )
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--devlyn-dir", ".devlyn",
             "--phase", "build_gate", "spawn", "--round", "1"],
            cwd=build_repo, check=True, capture_output=True,
        )
        # The next phase's first spawn shares rounds.global=1 but is not a
        # VERIFY re-entry; it must not reinterpret the BUILD_GATE receipt.
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()), "--devlyn-dir", ".devlyn",
             "--phase", "verify", "spawn", "--round", "1"],
            cwd=build_repo, check=True, capture_output=True,
        )
        build_receipt = loads_strict_json(
            (build_devlyn / "closure-durability.round-1.json").read_text(encoding="utf-8")
        )
        assert (build_repo / "a.txt").read_text(encoding="utf-8") == "surface\n"
        assert build_receipt and build_receipt["origin_phase"] == "build_gate"
        print("PASS M-CP self-test 2: build_gate and verify routes")

        # M-CP 3: block-granular multi-file partial revert mixture.
        mix_base = {
            "mix.txt": "A\nkeep-1\nB\nkeep-2\nC\n", "other.txt": "old\n",
            "context.txt": "before\nold\nafter\n",
        }
        mix_surface = {
            "mix.txt": "A-sc\nkeep-1\nB-sc\nkeep-2\nC-sc\n", "other.txt": "new\n",
            "context.txt": "before\nnew\nafter\n",
        }
        mix_fix = {
            "mix.txt": "A-sc\nkeep-1\nB-evolved\nkeep-2\nC\n", "other.txt": "old\n",
            "context.txt": "changed-context\nold\nafter\n",
        }
        mix_repo, mix_devlyn, mix_state, _, _ = durability_fixture(
            "durability-mix", mix_base, mix_surface, mix_fix, "verify", [],
        )
        mix_receipt = enforce_closure_durability_reentry(
            mix_repo, mix_devlyn, mix_state, "verify", 1,
        )
        mix_classes = [block["classification"] for block in mix_receipt["blocks"]]
        assert {"SURVIVED", "EVOLVED", "REVERTED"} <= set(mix_classes), mix_receipt["blocks"]
        assert (mix_repo / "mix.txt").read_text(encoding="utf-8") == (
            "A-sc\nkeep-1\nB-evolved\nkeep-2\nC-sc\n"
        )
        assert (mix_repo / "other.txt").read_text(encoding="utf-8") == "new\n"
        assert (mix_repo / "context.txt").read_text(encoding="utf-8") == (
            "changed-context\nold\nafter\n"
        )
        print("PASS M-CP self-test 3: multi-file SURVIVED/EVOLVED/REVERTED partial restore")

        # M-CP 4: a deleted additive SC block is REVERTED and restored.
        add_repo, add_devlyn, add_state, _, _ = durability_fixture(
            "durability-add", {"docs/x.txt": "head\ntail\n"},
            {"docs/x.txt": "head\na/old/docs/x.txt\ntail\n"},
            {"docs/x.txt": "head\ntail\n"}, "verify", [],
        )
        add_receipt = enforce_closure_durability_reentry(add_repo, add_devlyn, add_state, "verify", 1)
        assert (add_repo / "docs/x.txt").read_text(encoding="utf-8") == (
            "head\na/old/docs/x.txt\ntail\n"
        )
        assert any(block["classification"] == "REVERTED" for block in add_receipt["blocks"])
        print("PASS M-CP self-test 4: deleted additive block restored")

        # M-CP 5: an exact line-targeted deletion is preserved, not restored.
        target_repo, target_devlyn, target_state, target_fix, _ = durability_fixture(
            "durability-target", {"target.txt": "head\ntail\n"},
            {"target.txt": "head\nconsolidate\ntail\n"}, {"target.txt": "head\ntail\n"},
            "verify", [{"id": "E1", "path": "target.txt", "line": 2}],
        )
        target_receipt = enforce_closure_durability_reentry(
            target_repo, target_devlyn, target_state, "verify", 1,
        )
        assert (target_repo / "target.txt").read_text(encoding="utf-8") == "head\ntail\n"
        assert target_receipt["restore_commit_sha"] is None
        assert target_receipt["post_restore_sha"] == target_fix
        assert target_receipt["blocks"][0]["finding_targeted"] is True
        print("PASS M-CP self-test 5: finding-targeted deletion not restored")

        # M-CP 6: once ledgered, a missing or stale receipt blocks re-entry.
        target_path = target_devlyn / "closure-durability.round-1.json"
        target_raw = target_path.read_bytes()
        target_state["phases"]["implement"] = {"round": 1, "triggered_by": "verify"}
        write_state(target_devlyn / "pipeline.state.json", target_state)
        stale_verify_artifact = target_devlyn / "verify.findings.jsonl"
        stale_verify_artifact.write_text("stale\n", encoding="utf-8")
        target_path.unlink()
        for mode in ("missing", "stale"):
            if mode == "stale":
                target_path.write_bytes(target_raw.replace(b'"schema_version": 1', b'"schema_version": 2'))
            try:
                enforce_closure_durability_reentry(
                    target_repo, target_devlyn, target_state, "verify", 1,
                )
            except SystemExit as exc:
                assert "closure-durability-receipt" in str(exc)
            else:
                raise AssertionError(f"{mode} durability receipt was accepted")
            if mode == "missing":
                reentry = subprocess.run(
                    [sys.executable, str(pathlib.Path(__file__).resolve()),
                     "--devlyn-dir", ".devlyn", "--phase", "verify", "spawn",
                     "--round", "1"],
                    cwd=target_repo, capture_output=True, text=True,
                )
                assert reentry.returncode != 0
                assert "closure-durability-receipt" in reentry.stderr
                assert stale_verify_artifact.exists(), "re-entry guard must run before VERIFY clearing"
        target_path.write_bytes(target_raw)

        # Skipping the explicit post-fix checkpoint cannot be repaired by the
        # spawn guard: re-entry is validation-only and both artifacts missing
        # must block without changing the fix tree.
        skipped_repo, skipped_devlyn, skipped_state, skipped_fix, _ = durability_fixture(
            "durability-skipped-checkpoint", {"skip.txt": "base\n"},
            {"skip.txt": "surface\n"}, {"skip.txt": "base\n"}, "build_gate", [],
        )
        skipped_state["phases"]["implement"] = {"round": 1, "triggered_by": "build_gate"}
        write_state(skipped_devlyn / "pipeline.state.json", skipped_state)
        skipped = subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).resolve()),
             "--devlyn-dir", ".devlyn", "--phase", "build_gate", "spawn", "--round", "1"],
            cwd=skipped_repo, capture_output=True, text=True,
        )
        assert skipped.returncode != 0 and "checkpoint receipt is missing" in skipped.stderr
        assert not (skipped_devlyn / "closure-durability.round-1.json").exists()
        assert subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=skipped_repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip() == skipped_fix

        receipt_repo, receipt_devlyn, receipt_state, receipt_fix, _ = durability_fixture(
            "durability-receipt-write-fail", {"receipt.txt": "base\n"},
            {"receipt.txt": "surface\n"}, {"receipt.txt": "base\n"}, "verify", [],
        )
        original_json_writer = globals()["_write_json_atomic"]
        def fail_receipt_write(_path, _value):
            raise OSError("injected receipt write failure")
        globals()["_write_json_atomic"] = fail_receipt_write
        try:
            try:
                enforce_closure_durability_reentry(
                    receipt_repo, receipt_devlyn, receipt_state, "verify", 1,
                )
            except SystemExit as exc:
                assert "injected receipt write failure" in str(exc)
            else:
                raise AssertionError("receipt write failure did not fail closed")
        finally:
            globals()["_write_json_atomic"] = original_json_writer
        assert _git_output(receipt_repo, "rev-parse", "HEAD").decode().strip() == receipt_fix
        assert (receipt_repo / "receipt.txt").read_text(encoding="utf-8") == "base\n"
        assert not (receipt_devlyn / "closure-durability.round-1.json").exists()
        assert receipt_state["phases"]["surface_close"]["durability"] == []

        state_repo, state_devlyn, state_state, state_fix, _ = durability_fixture(
            "durability-state-write-fail", {"state.txt": "base\n"},
            {"state.txt": "surface\n"}, {"state.txt": "base\n"}, "verify", [],
        )
        def fail_state_write(_path, _state):
            raise OSError("injected state write failure")
        try:
            _persist_durability_event(
                state_repo, state_devlyn, state_state,
                state_devlyn / "pipeline.state.json", "verify", 1,
                writer=fail_state_write,
            )
        except OSError as exc:
            assert "injected state write failure" in str(exc)
        else:
            raise AssertionError("state write failure did not fail closed")
        assert _git_output(state_repo, "rev-parse", "HEAD").decode().strip() == state_fix
        assert (state_repo / "state.txt").read_text(encoding="utf-8") == "base\n"
        assert not (state_devlyn / "closure-durability.round-1.json").exists()
        assert state_state["phases"]["surface_close"]["durability"] == []
        print("PASS M-CP self-test 6: missing/stale receipt fails closed")

        # M-CP 7: failed patch preflight leaves index and worktree byte-clean.
        before_status = _tracked_status(target_repo)
        before_bytes = (target_repo / "target.txt").read_bytes()
        try:
            _apply_restore_patch(target_repo, b"not a patch\n", ["target.txt"])
        except SystemExit as exc:
            assert "closure-durability-apply" in str(exc)
        else:
            raise AssertionError("invalid restore patch was accepted")
        assert _tracked_status(target_repo) == before_status
        assert (target_repo / "target.txt").read_bytes() == before_bytes

        binary_repo = devlyn / "durability-binary"
        binary_repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=binary_repo, check=True)
        subprocess.run(["git", "config", "user.email", "self-test@example.invalid"], cwd=binary_repo, check=True)
        subprocess.run(["git", "config", "user.name", "self-test"], cwd=binary_repo, check=True)
        binary_path = binary_repo / "binary.dat"
        binary_path.write_bytes(b"\x00base\xff\n")
        subprocess.run(["git", "add", "--", "binary.dat"], cwd=binary_repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=binary_repo, check=True)
        wanted_binary = b"\x00a/old/binary.dat\xffb/new/binary.dat\n"
        binary_patch = _restore_patch(binary_repo, {"binary.dat": wanted_binary})
        _apply_restore_patch(binary_repo, binary_patch, ["binary.dat"])
        assert binary_path.read_bytes() == wanted_binary
        assert _git_output(binary_repo, "show", ":binary.dat") == wanted_binary

        literal_repo = devlyn / "durability-header-literal"
        literal_repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=literal_repo, check=True)
        subprocess.run(["git", "config", "user.email", "self-test@example.invalid"], cwd=literal_repo, check=True)
        subprocess.run(["git", "config", "user.name", "self-test"], cwd=literal_repo, check=True)
        literal_path = literal_repo / "literal.txt"
        literal_path.write_bytes(b"-- a/old/literal.txt\n")
        subprocess.run(["git", "add", "--", "literal.txt"], cwd=literal_repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=literal_repo, check=True)
        wanted_literal = b"++ b/new/literal.txt\n"
        literal_patch = _restore_patch(literal_repo, {"literal.txt": wanted_literal})
        _apply_restore_patch(literal_repo, literal_patch, ["literal.txt"])
        assert literal_path.read_bytes() == wanted_literal
        assert _git_output(literal_repo, "show", ":literal.txt") == wanted_literal
        print("PASS M-CP self-test 7: apply failure leaves zero partial mutation")

        # File-only findings are deliberately non-targeting.
        file_repo, file_devlyn, file_state, _, _ = durability_fixture(
            "durability-file-only", {"usage.txt": "usage old\n"},
            {"usage.txt": "usage --format\n"}, {"usage.txt": "usage old\n"},
            "verify", [{"id": "file-only", "file": "usage.txt"}],
        )
        file_receipt = enforce_closure_durability_reentry(
            file_repo, file_devlyn, file_state, "verify", 1,
        )
        assert (file_repo / "usage.txt").read_text(encoding="utf-8") == "usage --format\n"
        assert file_receipt["blocks"][0]["finding_targeted"] is False
        print("PASS M-CP self-test 8: file-only finding cannot mask restore")

        # Skipped/no-post-SHA is receipt-visible and commit-free.
        noop_repo, noop_devlyn, noop_state, noop_fix, _ = durability_fixture(
            "durability-noop", {"noop.txt": "base\n"}, {"noop.txt": "surface\n"},
            {"noop.txt": "fix\n"}, "build_gate", [], with_surface_post=False,
        )
        noop_receipt = enforce_closure_durability_reentry(
            noop_repo, noop_devlyn, noop_state, "build_gate", 1,
        )
        assert noop_receipt["blocks"] == [] and noop_receipt["restore_commit_sha"] is None
        assert noop_receipt["post_restore_sha"] == noop_fix
        print("PASS M-CP self-test no-op: no post_sha writes receipt without commit")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--phase", choices=sorted(PHASE_NAMES))
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--freeze-roles", action="store_true")
    ap.add_argument("--default-engine", default="claude")
    sub = ap.add_subparsers(dest="event")

    spawn_p = sub.add_parser("spawn")
    spawn_p.add_argument("--round", type=int, required=True)
    spawn_p.add_argument("--triggered-by", choices=sorted(SPAWN_TRIGGERS), default=None)
    spawn_p.add_argument("--pre-sha", default=None)
    spawn_p.add_argument("--input-patch-sha256", default=None)
    spawn_p.add_argument("--prompt-sha256", default=None)
    spawn_p.add_argument("--untracked-before-json", default=None)
    spawn_p.add_argument("--engine", default=None)
    spawn_p.add_argument("--model", default=None)

    complete_p = sub.add_parser("complete")
    complete_p.add_argument("--verdict", choices=sorted(VALID_VERDICTS), default=None)
    complete_p.add_argument("--post-sha", default=None)
    complete_p.add_argument("--findings-file", default=None)
    complete_p.add_argument("--log-file", default=None)
    complete_p.add_argument("--engine", default=None)
    complete_p.add_argument("--model", default=None)
    complete_p.add_argument("--engine-session-log", default=None)

    transition_p = sub.add_parser("transition")
    transition_p.add_argument("--verdict", choices=sorted(VALID_VERDICTS), default=None)
    transition_p.add_argument("--post-sha", default=None)
    transition_p.add_argument("--findings-file", default=None)
    transition_p.add_argument("--log-file", default=None)
    transition_p.add_argument("--engine", default=None)
    transition_p.add_argument("--model", default=None)
    transition_p.add_argument("--engine-session-log", default=None)
    transition_p.add_argument("--next-phase", choices=sorted(PHASE_NAMES), required=True)
    transition_p.add_argument("--next-round", type=int, required=True)
    transition_p.add_argument("--next-triggered-by", choices=sorted(SPAWN_TRIGGERS), default=None)
    transition_p.add_argument("--next-pre-sha", default=None)
    transition_p.add_argument("--next-input-patch-sha256", default=None)
    transition_p.add_argument("--next-prompt-sha256", default=None)
    transition_p.add_argument("--next-untracked-before-json", default=None)
    transition_p.add_argument("--next-engine", default=None)
    transition_p.add_argument("--next-model", default=None)

    check_p = sub.add_parser("surface-check")
    check_p.add_argument("--authorized-surface-json", required=True)
    recover_p = sub.add_parser("surface-adjudication-recover")
    recover_p.add_argument("--authorized-surface-json", required=True)
    sub.add_parser("surface-rollback")
    sub.add_parser("surface-skip")
    durability_p = sub.add_parser("durability-enforce")
    durability_p.add_argument("--round", type=int, required=True)
    durability_p.add_argument("--origin-phase", choices=sorted(VALID_TRIGGERS), required=True)

    args = ap.parse_args()
    if args.self_test:
        return self_test()

    if args.freeze_roles:
        devlyn = pathlib.Path(args.devlyn_dir)
        state_path = devlyn / "pipeline.state.json"
        try:
            state = read_state(state_path)
            result = freeze_roles(state, devlyn.resolve().parent, args.default_engine)
            write_state(state_path, state)
            print(json.dumps(result, sort_keys=True))
            return 0
        except (ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 1

    surface_events = {
        "surface-check", "surface-adjudication-recover", "surface-rollback", "surface-skip",
    }
    if not args.phase or args.event not in {"spawn", "complete", "transition", "durability-enforce", *surface_events}:
        ap.error("--phase and a phase event are required unless --self-test")
    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    state_path = devlyn / "pipeline.state.json"
    state = read_state(state_path)

    if args.event == "durability-enforce":
        if args.phase != "implement":
            ap.error("durability-enforce is valid only for --phase implement")
        validate_plan_output(state, devlyn, args.phase)
        _persist_durability_event(
            pathlib.Path.cwd(), devlyn, state, state_path, args.origin_phase, args.round,
        )
        sys.stdout.write(f"ok: phases.surface_close.durability.round-{args.round}\n")
        return 0

    if args.event in surface_events:
        if args.phase != "surface_close":
            ap.error(f"{args.event} is valid only for --phase surface_close")
        validate_plan_output(state, devlyn, args.phase)
        if args.event == "surface-skip":
            do_surface_skip(state)
            write_state(state_path, state)
            sys.stdout.write("ok: phases.surface_close.surface-skip\n")
            return 0
        work = pathlib.Path.cwd()
        if args.event == "surface-adjudication-recover":
            validate_surface_inputs(work, devlyn, state)
            validate_surface_prompt(devlyn, state)
            surface = validate_authorized_surface(args.authorized_surface_json)
            offenders = surface_offenders(work, devlyn, state, surface)
            if offenders:
                raise SystemExit(
                    "BLOCKED:surface-close-out-of-surface: " + json.dumps(offenders)
                )
            validate_surface_execution(devlyn, state)
            require_surface_adjudication_malformed(work, devlyn, state, surface)
            rollback_surface_delta(work, devlyn, state)
            tracked, untracked = surface_delta_paths(work, devlyn, state)
            if tracked or untracked:
                raise SystemExit(
                    "BLOCKED:surface-close-rollback-failed: "
                    + json.dumps(sorted(set(tracked + untracked)))
                )
            validate_surface_write_audit(work, devlyn, state, surface)
            attestation_error = do_surface_adjudication_recovery(state, devlyn)
            write_state(state_path, state)
            if attestation_error is not None:
                sys.stderr.write(attestation_error + "\n")
                return 1
            sys.stdout.write("ok: phases.surface_close.surface-adjudication-recover\n")
            return 0
        if args.event == "surface-check":
            validate_surface_inputs(work, devlyn, state)
            surface = validate_authorized_surface(args.authorized_surface_json)
            offenders = surface_offenders(work, devlyn, state, surface)
            if offenders:
                sys.stderr.write("BLOCKED:surface-close-out-of-scope: " + json.dumps(offenders) + "\n")
                return 2
            validate_surface_adjudication(work, devlyn, state, surface)
            validate_surface_execution(devlyn, state)
            sys.stdout.write("ok: phases.surface_close.surface-check\n")
            return 0
        restored = rollback_surface_delta(work, devlyn, state)
        sys.stdout.write("ok: phases.surface_close.surface-rollback " + json.dumps(restored) + "\n")
        return 0

    if args.event in {"spawn", "transition"}:
        spawn_phase = args.phase if args.event == "spawn" else args.next_phase
        spawn_round = args.round if args.event == "spawn" else args.next_round
        implement = (state.get("phases") or {}).get("implement")
        fix_reentry = (
            spawn_phase in VALID_TRIGGERS and spawn_round >= 1
            and isinstance(implement, dict)
            and implement.get("round") == spawn_round
            and implement.get("triggered_by") == spawn_phase
        )
        if fix_reentry:
            enforce_closure_durability_reentry(
                pathlib.Path.cwd(), devlyn, state, spawn_phase, spawn_round,
                require_existing=True,
            )
        if args.event == "spawn":
            untracked_before = (
                None if args.untracked_before_json is None
                else parse_string_list(args.untracked_before_json, "--untracked-before-json")
            )
            do_spawn(
                state, args.phase, args.round, args.triggered_by, args.pre_sha, args.engine, args.model,
                input_patch_sha256=args.input_patch_sha256,
                prompt_sha256=args.prompt_sha256,
                untracked_before=untracked_before,
                devlyn=devlyn,
            )
        else:
            next_untracked_before = (
                None if args.next_untracked_before_json is None
                else parse_string_list(
                    args.next_untracked_before_json, "--next-untracked-before-json"
                )
            )
            state = do_transition(
                state, args.phase, args.next_phase, args.verdict, args.post_sha,
                args.findings_file, args.log_file, args.engine, args.model,
                args.engine_session_log, devlyn, args.next_round,
                args.next_triggered_by, args.next_pre_sha, args.next_engine,
                args.next_model,
                next_input_patch_sha256=args.next_input_patch_sha256,
                next_prompt_sha256=args.next_prompt_sha256,
                next_untracked_before=next_untracked_before,
                work=pathlib.Path.cwd(),
            )
        if spawn_phase == "surface_close":
            validate_surface_inputs(pathlib.Path.cwd(), devlyn, state)
            validate_surface_prompt(devlyn, state)
            ensure_surface_clean_baseline(pathlib.Path.cwd(), devlyn, state)
        write_state(state_path, state)
        if spawn_phase == "verify":
            clear_verify_round_artifacts(devlyn)
        if args.event == "transition":
            opened = state["phases"][args.next_phase]
            completed = (
                opened["history"][-1]
                if args.phase == args.next_phase
                else state["phases"][args.phase]
            )
            raw = state_path.read_bytes()
            sys.stdout.write(json.dumps({
                "completed_phase": args.phase,
                "completed_at": completed["completed_at"],
                "completed_verdict": completed["verdict"],
                "next_phase": args.next_phase,
                "next_started_at": opened["started_at"],
                "next_round": opened["round"],
                "state_path": str(state_path),
                "state_sha256": hashlib.sha256(raw).hexdigest(),
            }, sort_keys=True) + "\n")
            return 0
    else:
        attestation_error = do_complete(
            state, args.phase, args.verdict, args.post_sha, args.findings_file,
            args.log_file, args.engine, args.model, args.engine_session_log, devlyn,
            pathlib.Path.cwd(),
        )
        if (
            args.phase == "plan"
            and state["phases"]["plan"]["verdict"] in {"PASS", "PASS_WITH_ISSUES"}
        ):
            raise SystemExit(
                "error: phases.plan complete with PASS or PASS_WITH_ISSUES requires "
                "--phase plan transition --verdict <verdict> --next-phase <phase>"
            )

    if args.event not in {"spawn", "transition"}:
        write_state(state_path, state)
    if args.event == "complete" and attestation_error is not None:
        sys.stderr.write(attestation_error + "\n")
        return 1
    sys.stdout.write(f"ok: phases.{args.phase}.{args.event}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
