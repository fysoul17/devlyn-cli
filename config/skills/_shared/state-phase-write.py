#!/usr/bin/env python3
"""Deterministic spawn/complete writer for phases.<name> in pipeline.state.json.

Usage:
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement spawn \
        --round 1 --triggered-by verify [--pre-sha <sha>] [--engine claude] [--model <id>]
    python3 state-phase-write.py --devlyn-dir .devlyn --phase implement complete \
        --verdict PASS [--post-sha <sha>] [--findings-file <path>] [--log-file <path>] \
        [--engine claude] [--model <requested-id>] [--engine-session-log <path>]

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
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

VALID_VERDICTS = {"PASS", "PASS_WITH_ISSUES", "FAIL", "NEEDS_WORK", "BLOCKED"}
VALID_TRIGGERS = {"build_gate", "verify"}
PHASE_NAMES = {"plan", "probe_derive", "implement", "surface_close", "build_gate", "cleanup", "verify", "final_report"}
MODEL_HEADER_RE = re.compile(r"(?m)^[ \t]*model:[ \t]*(\S+)[ \t]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SURFACE_ROW_RE = re.compile(
    r"^(?P<obligation>UVR-STALE|PATH-TEST): (?P<status>FIRED|N/A) "
    r"(?P<path>.+):(?P<line>[1-9][0-9]*)(?: — (?P<evidence>\S.*))?$"
)
VALIDATION_EXECUTION_RE = re.compile(
    r"npm\s+test|node\s+--test|node\s+-e|node\s+bin/|node\s+tests/|git\s+stash"
)
SURFACE_SKIP_REASON = "auto_surface_close_claude_unavailable"


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


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
    return surface


def path_matches_surface(path: str, surface: list[str]) -> bool:
    for entry in surface:
        if entry.endswith("/**"):
            prefix = entry[:-3].rstrip("/")
            if path == prefix or path.startswith(f"{prefix}/"):
                return True
        elif path == entry:
            return True
    return False


def surface_offenders(work: pathlib.Path, devlyn: pathlib.Path, state: dict,
                      surface: list[str]) -> list[str]:
    tracked, untracked = surface_delta_paths(work, devlyn, state)
    return sorted(path for path in set(tracked + untracked) if not path_matches_surface(path, surface))


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

    rows: dict[str, tuple[str, str, int, str | None, int]] = {}
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
        status = match.group("status")
        evidence = match.group("evidence")
        if status == "N/A" and evidence is None:
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-malformed: {obligation} N/A requires evidence"
            )
        path = match.group("path")
        line_number = int(match.group("line"))
        if not path_matches_surface(path, surface):
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-out-of-surface: {path}:{line_number}"
            )
        cited = work / path
        try:
            cited_lines = cited.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-citation-missing: {path}:{line_number}: {exc}"
            ) from exc
        if line_number > len(cited_lines):
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


def parse_effective_model(session_log: pathlib.Path) -> str:
    try:
        text = session_log.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read engine session log {session_log}: {exc}") from exc

    header = MODEL_HEADER_RE.search(text)
    if header:
        return header.group(1)

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
        model_usage = evidence.get("modelUsage") if isinstance(evidence, dict) else None
        if isinstance(model_usage, dict):
            models.update(model for model in model_usage if isinstance(model, str) and model)

    if len(models) == 1:
        return next(iter(models))
    if not models:
        raise ValueError(f"engine session log {session_log} has no effective-model evidence")
    raise ValueError(
        f"engine session log {session_log} has conflicting effective models: {sorted(models)}"
    )


def clear_verify_round_artifacts(devlyn: pathlib.Path) -> None:
    # The per-round reset contract covers files, not just JSON fields: a
    # VERIFY fix-loop respawn reuses the same .devlyn, so a prior round's
    # findings/stdout would otherwise read as current-round spawn evidence in
    # verify-merge-findings.py (iter-0060 R0 finding).
    # verify*.jsonl (not just *.findings.jsonl): judge-specific files like
    # verify.findings.judge-codex.jsonl end in .judge-<engine>.jsonl.
    # *-judge.* covers every engine's stdout/stderr capture (codex-judge.*,
    # claude-judge.* — adapters/claude.md ## Invocation).
    for pattern in ("verify*.jsonl", "*-judge.*"):
        for path in devlyn.glob(pattern):
            path.unlink()
    (devlyn / "verify-merge.summary.json").unlink(missing_ok=True)


def append_phase_history(entry: dict) -> None:
    if entry.get("started_at") is None:
        return
    history = entry.get("history")
    if not isinstance(history, list):
        history = []
    history.append({
        "started_at": entry.get("started_at"),
        "verdict": entry.get("verdict"),
        "completed_at": entry.get("completed_at"),
        "duration_ms": entry.get("duration_ms"),
    })
    entry["history"] = history


def do_spawn(state: dict, phase: str, round_: int, triggered_by: str | None,
             pre_sha: str | None, engine: str | None, model: str | None, *,
             input_patch_sha256: str | None = None,
             prompt_sha256: str | None = None,
             untracked_before: list[str] | None = None) -> None:
    # Merge, don't replace: a phase-gated large run's `exec` progress (or any
    # other field this script doesn't own) survives a fix-loop respawn.
    if phase == "surface_close" and engine != "claude":
        raise SystemExit("error: phases.surface_close spawn requires --engine claude")
    phases = state.setdefault("phases", {})
    entry = phases.get(phase)
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
    elif input_patch_sha256 is not None or prompt_sha256 is not None or untracked_before is not None:
        raise SystemExit("error: SURFACE_CLOSE metadata is invalid for this phase")
    if not isinstance(entry, dict):
        entry = {}
        phases[phase] = entry
    append_phase_history(entry)
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
    if engine is not None:
        entry["engine"] = engine
    if model is not None:
        entry["model_requested"] = model
    else:
        entry.setdefault("model_requested", None)
    entry.pop("model", None)
    entry["model_effective"] = None
    if pre_sha is not None:
        entry["pre_sha"] = pre_sha
    if phase == "surface_close":
        entry["input_patch_sha256"] = input_patch_sha256
        entry["prompt_sha256"] = prompt_sha256
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
                 engine_session_log: str | None = None) -> str | None:
    phases = state.setdefault("phases", {})
    entry = phases.get(phase)
    if not isinstance(entry, dict) or not entry.get("started_at"):
        raise SystemExit(f"error: phases.{phase} was never spawned (no started_at) — cannot complete")
    started = parse_iso(entry["started_at"])
    now = now_ms()
    entry["completed_at"] = now_iso(now)
    entry["duration_ms"] = max(0, round((now - started).total_seconds() * 1000))
    if phase == "verify":
        if verdict is not None:
            raise SystemExit(
                "error: phases.verify.verdict is owned by verify-merge-findings.py "
                "--write-state; do not pass --verdict to complete for this phase"
            )
        if entry.get("verdict") is None:
            raise SystemExit(
                "error: phases.verify.verdict is still null — run "
                "verify-merge-findings.py --write-state before complete"
            )
    elif verdict is not None:
        entry["verdict"] = verdict
    else:
        raise SystemExit(f"error: --verdict is required to complete phases.{phase}")
    if findings_file is not None or log_file is not None:
        artifacts = entry.setdefault("artifacts", {"findings_file": None, "log_file": None})
        if findings_file is not None:
            artifacts["findings_file"] = findings_file
        if log_file is not None:
            artifacts["log_file"] = log_file
    if engine is not None:
        entry["engine"] = engine
    if model is not None:
        entry["model_requested"] = model
    else:
        entry.setdefault("model_requested", None)
    entry.pop("model", None)

    attestation_error = None
    if engine_session_log is None:
        entry["model_effective"] = None
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


def self_test() -> int:
    import time

    with tempfile.TemporaryDirectory() as tmp:
        devlyn = pathlib.Path(tmp)
        state_path = devlyn / "pipeline.state.json"
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
        assert parse_iso(final["started_at"]) == parse_iso(respawned["started_at"])
        assert parse_iso(final["completed_at"]) >= parse_iso(final["started_at"])
        assert final["artifacts"]["findings_file"] == ".devlyn/x.jsonl"

        # complete() before spawn() must fail loudly, not silently invent data.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        try:
            do_complete(state, "build_gate", "PASS", None, None, None, None, None)
        except SystemExit as e:
            assert "never spawned" in str(e)
        else:
            raise AssertionError("complete() without a prior spawn() must raise")

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
        do_spawn(state, "plan", 0, None, None, None, None)
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
        ):
            (devlyn / name).write_text("stale\n", encoding="utf-8")
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
        ):
            assert not (devlyn / name).exists(), f"{name} must be cleared on VERIFY spawn"
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
        subprocess.run(["git", "add", "--", "allowed.txt", "blocked.txt"], cwd=work, check=True)
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
                    rejected_state, "surface_close", 0, None, pre_sha, rejected_engine, None,
                    input_patch_sha256=file_sha256(patch), prompt_sha256=file_sha256(prompt),
                    untracked_before=["kept.txt"],
                )
            except SystemExit as exc:
                assert "requires --engine claude" in str(exc)
            else:
                raise AssertionError("SURFACE_CLOSE accepted a non-Claude engine")
            assert rejected_state == {"sentinel": True}
        do_spawn(
            surface_state, "surface_close", 0, None, pre_sha, "claude", None,
            input_patch_sha256=file_sha256(patch), prompt_sha256=file_sha256(prompt),
            untracked_before=["kept.txt"],
        )
        validate_surface_inputs(work, work_devlyn, surface_state)
        validate_surface_prompt(work_devlyn, surface_state)
        ensure_surface_clean_baseline(work, work_devlyn, surface_state)
        surface = validate_authorized_surface('["allowed.txt", "tests/**"]')
        entry = surface_entry(surface_state)
        assert entry["prompt_sha256"] == file_sha256(prompt)
        try:
            do_spawn(surface_state, "surface_close", 1, None, pre_sha, "claude", None)
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

        rejected_outputs = (
            ("PASS\n", "missing UVR-STALE, PATH-TEST"),
            (
                "UVR-STALE: N/A allowed.txt:1\n"
                "PATH-TEST: N/A allowed.txt:1 — evidence\nPASS\n",
                "requires evidence",
            ),
            ("UVR-STALE: FIRED allowed.txt:1\nPASS\n", "missing PATH-TEST"),
            (
                "UVR-STALE: FIRED blocked.txt:1\n"
                "PATH-TEST: FIRED allowed.txt:1\nPASS\n",
                "out-of-surface",
            ),
            (
                "UVR-STALE: FIRED tests/missing.txt:1\n"
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
        (work / "tests").mkdir()
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

        # Effective model evidence: engine header line and rollout JSONL.
        header_log = devlyn / "codex-build.log"
        header_log.write_text("session\nmodel: gpt-5.6-sol\n", encoding="utf-8")
        assert parse_effective_model(header_log) == "gpt-5.6-sol"
        rollout_log = devlyn / "rollout.jsonl"
        rollout_log.write_text(json.dumps({
            "type": "turn_context", "payload": {"model": "gpt-5.6-terra"},
        }) + "\n", encoding="utf-8")
        assert parse_effective_model(rollout_log) == "gpt-5.6-terra"
        claude_log = devlyn / "claude-result.json"
        claude_log.write_text(json.dumps({
            "modelUsage": {"claude-alpha-1": {"inputTokens": 1}},
        }) + "\n", encoding="utf-8")
        assert parse_effective_model(claude_log) == "claude-alpha-1"

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

        # No evidence flag means the engine class exposed no session log;
        # supplied evidence must parse and never silently record null.
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "plan", 0, None, None, "claude", "claude-default")
        assert do_complete(state, "plan", "PASS", None, None, None, None, None) is None
        assert state["phases"]["plan"]["model_effective"] is None
        invalid_log = devlyn / "invalid-session.log"
        invalid_log.write_text("no model evidence\n", encoding="utf-8")
        write_state(state_path, {"phases": {}})
        state = read_state(state_path)
        do_spawn(state, "plan", 0, None, None, "claude", "claude-default")
        invalid = do_complete(
            state, "plan", "PASS", None, None, None, None, None, str(invalid_log)
        )
        assert invalid and "model-attestation-failed" in invalid
        assert state["phases"]["plan"]["model_effective"] is None
        assert state["phases"]["plan"]["verdict"] == "BLOCKED"

    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--devlyn-dir", default=".devlyn")
    ap.add_argument("--phase", choices=sorted(PHASE_NAMES))
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="event")

    spawn_p = sub.add_parser("spawn")
    spawn_p.add_argument("--round", type=int, required=True)
    spawn_p.add_argument("--triggered-by", choices=sorted(VALID_TRIGGERS), default=None)
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

    check_p = sub.add_parser("surface-check")
    check_p.add_argument("--authorized-surface-json", required=True)
    sub.add_parser("surface-rollback")
    sub.add_parser("surface-skip")

    args = ap.parse_args()
    if args.self_test:
        return self_test()

    surface_events = {"surface-check", "surface-rollback", "surface-skip"}
    if not args.phase or args.event not in {"spawn", "complete", *surface_events}:
        ap.error("--phase and a phase event are required unless --self-test")

    devlyn = pathlib.Path(args.devlyn_dir)
    if not devlyn.is_dir():
        sys.stderr.write(f"error: {devlyn} is not a directory\n")
        return 1
    state_path = devlyn / "pipeline.state.json"
    state = read_state(state_path)

    if args.event in surface_events:
        if args.phase != "surface_close":
            ap.error(f"{args.event} is valid only for --phase surface_close")
        if args.event == "surface-skip":
            do_surface_skip(state)
            write_state(state_path, state)
            sys.stdout.write("ok: phases.surface_close.surface-skip\n")
            return 0
        work = pathlib.Path.cwd()
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

    if args.event == "spawn":
        if args.phase == "verify":
            clear_verify_round_artifacts(devlyn)
        untracked_before = (
            None if args.untracked_before_json is None
            else parse_string_list(args.untracked_before_json, "--untracked-before-json")
        )
        do_spawn(
            state, args.phase, args.round, args.triggered_by, args.pre_sha, args.engine, args.model,
            input_patch_sha256=args.input_patch_sha256,
            prompt_sha256=args.prompt_sha256,
            untracked_before=untracked_before,
        )
        if args.phase == "surface_close":
            validate_surface_inputs(pathlib.Path.cwd(), devlyn, state)
            validate_surface_prompt(devlyn, state)
            ensure_surface_clean_baseline(pathlib.Path.cwd(), devlyn, state)
    else:
        attestation_error = do_complete(
            state, args.phase, args.verdict, args.post_sha, args.findings_file,
            args.log_file, args.engine, args.model, args.engine_session_log,
        )

    write_state(state_path, state)
    if args.event == "complete" and attestation_error is not None:
        sys.stderr.write(attestation_error + "\n")
        return 1
    sys.stdout.write(f"ok: phases.{args.phase}.{args.event}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
