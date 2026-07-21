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
    "implement": "implement",
    "surface_close": "surface-close",
    "cleanup": "cleanup",
}
MODEL_HEADER_RE = re.compile(r"(?m)^[ \t]*model:[ \t]*(\S+)[ \t]*$")
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
        if not path_matches_surface(path, surface):
            raise SystemExit(
                f"BLOCKED:surface-close-adjudication-out-of-surface: {citation}"
            )
        cited = work / path
        try:
            cited_lines = cited.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
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
            if not path_matches_surface(relative, surface):
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
    if phase == "surface_close" and not model:
        raise SystemExit("error: phases.surface_close spawn requires --model")
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
    if entry.get("started_at") is not None and entry.get("completed_at") is None:
        raise SystemExit(
            f"error: phases.{phase} has an open span — complete it before respawn"
        )
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
                 engine_session_log: str | None = None,
                 devlyn: pathlib.Path | None = None) -> str | None:
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

    artifact_phase = WORKER_SESSION_ARTIFACT_PHASES.get(phase)
    retained_session = None
    if devlyn is not None and artifact_phase is not None:
        candidate = devlyn / f"{artifact_phase}.worker-session.{entry.get('round')}.jsonl"
        if candidate.is_file():
            retained_session = candidate

    attestation_error = None
    if engine_session_log is None:
        entry["model_effective"] = None
        if retained_session is not None:
            attestation_error = (
                "BLOCKED:model-attestation-failed: --engine-session-log is required because "
                f"retained worker session exists: {retained_session}"
            )
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
        engine, model, engine_session_log, devlyn,
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
        attestation_log.write_text("model: other-model\n", encoding="utf-8")
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
        (work / "schedule").mkdir()
        (work / "schedule" / "__init__.py").write_text("line\n" * 700, encoding="utf-8")
        (work / "test_schedule.py").write_text("line\n", encoding="utf-8")
        (work / "tests").mkdir()
        (work / "tests" / "cli.test.js").write_text("line\n" * 170, encoding="utf-8")
        subprocess.run(
            ["git", "add", "--", "allowed.txt", "blocked.txt", "schedule/__init__.py",
             "test_schedule.py", "tests/cli.test.js"],
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
        surface = validate_authorized_surface(
            '["allowed.txt", "schedule/**", "test_schedule.py", "tests/**"]'
        )
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
        import importlib.util
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
    transition_p.add_argument("--next-triggered-by", choices=sorted(VALID_TRIGGERS), default=None)
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
        _persist_durability_event(
            pathlib.Path.cwd(), devlyn, state, state_path, args.origin_phase, args.round,
        )
        sys.stdout.write(f"ok: phases.surface_close.durability.round-{args.round}\n")
        return 0

    if args.event in surface_events:
        if args.phase != "surface_close":
            ap.error(f"{args.event} is valid only for --phase surface_close")
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
