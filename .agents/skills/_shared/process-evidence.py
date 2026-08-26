#!/usr/bin/env python3
"""Capture and validate run-scoped process evidence without third-party dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile
import time


SCHEMA_VERSION = "1.0"
PHASES = {"implement", "build_gate", "verify"}
CAPABILITIES = {"filesystem", "subprocess", "loopback", "pty", "network"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
OBLIGATION_KEYS = {
    "id", "phase", "cmd", "argv", "exit_code", "timeout_sec",
    "stdout_contains", "stdout_not_contains",
}


class EvidenceError(ValueError):
    pass


def _reject_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def loads_strict_json(text: str):
    return json.loads(
        text, parse_constant=_reject_constant, object_pairs_hook=_unique_object,
    )


def _read_json(path: pathlib.Path):
    try:
        return loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise EvidenceError(f"{path} is not valid UTF-8 JSON: {exc}") from exc


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _atomic_write(path: pathlib.Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".tmp.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        pathlib.Path(temporary).replace(path)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise EvidenceError(f"{label} must be an array of non-empty strings")
    return list(value)


def normalize_obligation(value: object, phase: str | None = None) -> dict:
    if not isinstance(value, dict):
        raise EvidenceError("process_evidence entry must be an object")
    unknown = sorted(set(value) - OBLIGATION_KEYS)
    if unknown:
        raise EvidenceError(f"process_evidence entry has unknown key(s): {','.join(unknown)}")
    evidence_id = value.get("id")
    if not isinstance(evidence_id, str) or ID_RE.fullmatch(evidence_id) is None:
        raise EvidenceError("process_evidence id must be a safe non-empty path component")
    declared_phase = value.get("phase")
    if declared_phase not in PHASES:
        raise EvidenceError(f"process_evidence[{evidence_id}].phase is invalid")
    if phase is not None and declared_phase != phase:
        raise EvidenceError(
            f"process_evidence[{evidence_id}].phase expected {phase}, got {declared_phase}"
        )
    has_command = "cmd" in value
    has_argv = "argv" in value
    if has_command == has_argv:
        raise EvidenceError(
            f"process_evidence[{evidence_id}] requires exactly one of cmd or argv"
        )
    command = value.get("cmd") if has_command else None
    argv = value.get("argv") if has_argv else None
    if has_command and (not isinstance(command, str) or not command):
        raise EvidenceError(f"process_evidence[{evidence_id}].cmd must be non-empty")
    if has_argv and (
        not isinstance(argv, list) or not argv or not isinstance(argv[0], str)
        or not argv[0] or any(not isinstance(arg, str) for arg in argv)
    ):
        raise EvidenceError(
            f"process_evidence[{evidence_id}].argv must be a string array with non-empty argv[0]"
        )
    exit_code = value.get("exit_code", 0)
    timeout_sec = value.get("timeout_sec", 60)
    if isinstance(exit_code, bool) or not isinstance(exit_code, int) or exit_code < 0:
        raise EvidenceError(f"process_evidence[{evidence_id}].exit_code must be non-negative int")
    if (
        isinstance(timeout_sec, bool) or not isinstance(timeout_sec, int)
        or timeout_sec < 1 or timeout_sec > 600
    ):
        raise EvidenceError(
            f"process_evidence[{evidence_id}].timeout_sec must be int from 1 to 600"
        )
    normalized = {
        "id": evidence_id,
        "phase": declared_phase,
        "exit_code": exit_code,
        "timeout_sec": timeout_sec,
        "stdout_contains": _string_list(
            value.get("stdout_contains", []),
            f"process_evidence[{evidence_id}].stdout_contains",
        ),
        "stdout_not_contains": _string_list(
            value.get("stdout_not_contains", []),
            f"process_evidence[{evidence_id}].stdout_not_contains",
        ),
    }
    normalized["cmd" if has_command else "argv"] = command if has_command else list(argv)
    return normalized


def _safe_relative_path(value: str, label: str) -> pathlib.PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise EvidenceError(f"{label} must be a non-empty POSIX relative path")
    relative = pathlib.PurePosixPath(value)
    if relative.is_absolute() or value.startswith("./") or ".." in relative.parts:
        raise EvidenceError(f"{label} escapes the worktree: {value!r}")
    return relative


def _checked_file(work: pathlib.Path, relative: str, label: str) -> pathlib.Path:
    rel = _safe_relative_path(relative, label)
    root = work.resolve()
    candidate = work.joinpath(*rel.parts)
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise EvidenceError(f"{label} is missing or escapes the worktree: {relative!r}") from exc
    if not resolved.is_file():
        raise EvidenceError(f"{label} is not a regular file: {relative!r}")
    return resolved


def _relative_to_work(work: pathlib.Path, path: pathlib.Path, label: str) -> str:
    try:
        return path.resolve().relative_to(work.resolve()).as_posix()
    except (OSError, ValueError) as exc:
        raise EvidenceError(f"{label} escapes the worktree: {path}") from exc


def _source_expected_path(work: pathlib.Path, state: dict) -> pathlib.Path | None:
    source = state.get("source")
    if not isinstance(source, dict) or source.get("type") != "spec":
        return None
    spec_path = source.get("spec_path")
    if not isinstance(spec_path, str) or not spec_path:
        raise EvidenceError("state.source.spec_path is missing")
    spec_rel = _safe_relative_path(spec_path, "state.source.spec_path")
    expected = work.joinpath(*spec_rel.parts).with_suffix(".expected.json")
    try:
        expected.resolve().relative_to(work.resolve())
    except (OSError, ValueError) as exc:
        raise EvidenceError("source expected contract escapes the worktree") from exc
    return expected if expected.is_file() else None


def declared_obligations(work: pathlib.Path, state: dict, phase: str) -> list[dict]:
    if phase not in PHASES:
        raise EvidenceError(f"unsupported evidence phase: {phase}")
    expected_path = _source_expected_path(work, state)
    if expected_path is None:
        return []
    contract = _read_json(expected_path)
    if not isinstance(contract, dict):
        raise EvidenceError(f"{expected_path} must contain a JSON object")
    raw = contract.get("process_evidence", [])
    if not isinstance(raw, list):
        raise EvidenceError("process_evidence must be an array")
    obligations = [normalize_obligation(item) for item in raw]
    ids: set[str] = set()
    for item in obligations:
        key = f"{item['phase']}:{item['id']}"
        if key in ids:
            raise EvidenceError(f"duplicate process_evidence id: {key}")
        ids.add(key)
    return [item for item in obligations if item["phase"] == phase]


def phase_round(state: dict, phase: str) -> int:
    entry = (state.get("phases") or {}).get(phase)
    round_ = entry.get("round") if isinstance(entry, dict) else None
    if isinstance(round_, bool) or not isinstance(round_, int) or round_ < 0:
        raise EvidenceError(f"state.phases.{phase}.round must be a non-negative integer")
    return round_


def manifest_relative_path(state: dict, phase: str) -> str:
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or ID_RE.fullmatch(run_id) is None:
        raise EvidenceError("state.run_id must be a safe non-empty path component")
    round_ = phase_round(state, phase)
    return f".devlyn/process-evidence/{run_id}/{phase}/round-{round_}/manifest.json"


def _expectation(obligation: dict) -> dict:
    return {
        "exit_code": obligation["exit_code"],
        "timeout_sec": obligation["timeout_sec"],
        "stdout_contains": obligation["stdout_contains"],
        "stdout_not_contains": obligation["stdout_not_contains"],
    }


def _execution(obligation: dict) -> dict:
    return {
        "command": obligation.get("cmd"),
        "argv": obligation.get("argv"),
    }


def _expectation_met(expectation: dict, outcome: dict, stdout: bytes, stderr: bytes) -> bool:
    combined = stdout + stderr
    return (
        outcome.get("kind") == "exit"
        and outcome.get("exit_code") == expectation["exit_code"]
        and all(value.encode("utf-8") in combined for value in expectation["stdout_contains"])
        and all(value.encode("utf-8") not in combined for value in expectation["stdout_not_contains"])
    )


def _stream_record(work: pathlib.Path, path: pathlib.Path, raw: bytes) -> dict:
    return {
        "path": _relative_to_work(work, path, "process evidence stream"),
        "sha256": _sha256(raw),
        "bytes": len(raw),
    }


def _load_manifest(path: pathlib.Path, run_id: str, phase: str, round_: int) -> dict:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "phase": phase,
            "round": round_,
            "entries": [],
        }
    manifest = _read_json(path)
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "run_id", "phase", "round", "entries",
    }:
        raise EvidenceError("process evidence manifest has an invalid top-level shape")
    if (
        manifest["schema_version"] != SCHEMA_VERSION or manifest["run_id"] != run_id
        or manifest["phase"] != phase or manifest["round"] != round_
        or not isinstance(manifest["entries"], list)
    ):
        raise EvidenceError("process evidence manifest identity does not match the current run")
    ids = []
    for entry in manifest["entries"]:
        evidence_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(evidence_id, str) or ID_RE.fullmatch(evidence_id) is None:
            raise EvidenceError("process evidence manifest contains a malformed id")
        if evidence_id in ids:
            raise EvidenceError("process evidence manifest contains a duplicate id")
        ids.append(evidence_id)
    return manifest


def _append_entry(
    work: pathlib.Path, manifest_path: pathlib.Path, run_id: str, phase: str,
    round_: int, evidence_id: str, execution: dict, expectation: dict,
    outcome: dict, classification: dict, stdout: bytes, stderr: bytes,
    duration_ms: int,
) -> dict:
    _relative_to_work(work, manifest_path, "process evidence manifest")
    manifest = _load_manifest(manifest_path, run_id, phase, round_)
    if any(item["id"] == evidence_id for item in manifest["entries"]):
        raise EvidenceError(f"duplicate process evidence id: {phase}:{evidence_id}")
    stdout_path = manifest_path.parent / f"{evidence_id}.stdout"
    stderr_path = manifest_path.parent / f"{evidence_id}.stderr"
    if stdout_path.exists() or stderr_path.exists():
        raise EvidenceError(f"unattributed process evidence stream already exists: {evidence_id}")
    _atomic_write(stdout_path, stdout)
    _atomic_write(stderr_path, stderr)
    entry = {
        "id": evidence_id,
        "execution": execution,
        "expectation": expectation,
        "outcome": outcome,
        "classification": classification,
        "stdout": _stream_record(work, stdout_path, stdout),
        "stderr": _stream_record(work, stderr_path, stderr),
        "duration_ms": duration_ms,
        "expectation_met": _expectation_met(expectation, outcome, stdout, stderr),
    }
    manifest["entries"].append(entry)
    _atomic_write(manifest_path, _json_bytes(manifest))
    return entry


def capture_process(
    work: pathlib.Path, manifest_path: pathlib.Path, run_id: str, phase: str,
    round_: int, obligation: dict,
) -> dict:
    item = normalize_obligation(obligation, phase)
    started = time.monotonic()
    try:
        proc = subprocess.run(
            item.get("cmd") if "cmd" in item else item["argv"],
            cwd=work, shell="cmd" in item, capture_output=True,
            timeout=item["timeout_sec"], check=False,
        )
        stdout, stderr = proc.stdout, proc.stderr
        outcome = (
            {"kind": "exit", "exit_code": proc.returncode, "signal": None}
            if proc.returncode >= 0 else
            {"kind": "signal", "exit_code": None, "signal": -proc.returncode}
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        outcome = {"kind": "timeout", "exit_code": None, "signal": None}
    except OSError as exc:
        stdout = b""
        stderr = os.fsencode(str(exc))
        outcome = {"kind": "spawn_error", "exit_code": None, "signal": None}
    return _append_entry(
        work, manifest_path, run_id, phase, round_, item["id"], _execution(item),
        _expectation(item), outcome,
        {"kind": "product_result", "operation": None}, stdout, stderr,
        max(0, round((time.monotonic() - started) * 1000)),
    )


def record_capability_denial(
    work: pathlib.Path, manifest_path: pathlib.Path, run_id: str, phase: str,
    round_: int, obligation: dict, operation: str, detail: bytes,
) -> dict:
    item = normalize_obligation(obligation, phase)
    if operation not in CAPABILITIES:
        raise EvidenceError(f"unsupported denied capability: {operation}")
    return _append_entry(
        work, manifest_path, run_id, phase, round_, item["id"], _execution(item),
        _expectation(item), {"kind": "not_run", "exit_code": None, "signal": None},
        {"kind": "capability_denied", "operation": operation}, b"", detail, 0,
    )


def _validate_stream(work: pathlib.Path, record: object, expected_path: str, label: str) -> dict:
    if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
        raise EvidenceError(f"{label} has an invalid stream record")
    if record["path"] != expected_path:
        raise EvidenceError(f"{label} path mismatch: {record['path']!r}")
    if not isinstance(record["sha256"], str) or SHA256_RE.fullmatch(record["sha256"]) is None:
        raise EvidenceError(f"{label} sha256 is invalid")
    if isinstance(record["bytes"], bool) or not isinstance(record["bytes"], int) or record["bytes"] < 0:
        raise EvidenceError(f"{label} byte count is invalid")
    raw = _checked_file(work, record["path"], label).read_bytes()
    if len(raw) != record["bytes"] or _sha256(raw) != record["sha256"]:
        raise EvidenceError(f"{label} digest or byte count mismatch")
    return {"path": record["path"], "sha256": record["sha256"]}


def validate_manifest(
    work: pathlib.Path, manifest_relative: str, run_id: str, phase: str, round_: int,
    obligations: list[dict] | None = None, *, require_expectations: bool = True,
) -> dict:
    expected_relative = (
        f".devlyn/process-evidence/{run_id}/{phase}/round-{round_}/manifest.json"
    )
    if manifest_relative != expected_relative:
        raise EvidenceError("process evidence manifest path does not match run identity")
    manifest_path = _checked_file(work, manifest_relative, "process evidence manifest")
    manifest_raw = manifest_path.read_bytes()
    manifest = _load_manifest(manifest_path, run_id, phase, round_)
    declared = {}
    for raw in obligations or []:
        item = normalize_obligation(raw, phase)
        if item["id"] in declared:
            raise EvidenceError(f"duplicate process evidence obligation id: {phase}:{item['id']}")
        declared[item["id"]] = item
    seen: set[str] = set()
    streams = []
    for index, entry in enumerate(manifest["entries"]):
        label = f"process evidence entry {index}"
        if not isinstance(entry, dict) or set(entry) != {
            "id", "execution", "expectation", "outcome", "classification",
            "stdout", "stderr", "duration_ms", "expectation_met",
        }:
            raise EvidenceError(f"{label} has an invalid shape")
        evidence_id = entry["id"]
        if not isinstance(evidence_id, str) or ID_RE.fullmatch(evidence_id) is None:
            raise EvidenceError(f"{label} id is invalid")
        if evidence_id in seen:
            raise EvidenceError(f"duplicate process evidence id: {phase}:{evidence_id}")
        seen.add(evidence_id)
        execution = entry["execution"]
        expectation = entry["expectation"]
        if not isinstance(execution, dict) or set(execution) != {"command", "argv"}:
            raise EvidenceError(f"{label} execution is invalid")
        normalized = normalize_obligation({
            "id": evidence_id, "phase": phase,
            **({"cmd": execution["command"]} if execution["command"] is not None else
               {"argv": execution["argv"]}),
            **(expectation if isinstance(expectation, dict) else {}),
        }, phase)
        if execution != _execution(normalized) or expectation != _expectation(normalized):
            raise EvidenceError(f"{label} execution or expectation is non-canonical")
        if evidence_id in declared and normalized != declared[evidence_id]:
            raise EvidenceError(f"declared process evidence mismatch: {phase}:{evidence_id}")
        outcome = entry["outcome"]
        classification = entry["classification"]
        if not isinstance(outcome, dict) or set(outcome) != {"kind", "exit_code", "signal"}:
            raise EvidenceError(f"{label} outcome is invalid")
        if not isinstance(classification, dict) or set(classification) != {"kind", "operation"}:
            raise EvidenceError(f"{label} classification is invalid")
        outcome_kind = outcome["kind"]
        if outcome_kind not in {"exit", "signal", "timeout", "spawn_error", "not_run"}:
            raise EvidenceError(f"{label} outcome kind is invalid")
        exit_code = outcome["exit_code"]
        signal_number = outcome["signal"]
        if outcome_kind == "exit":
            if (
                isinstance(exit_code, bool) or not isinstance(exit_code, int)
                or exit_code < 0 or signal_number is not None
            ):
                raise EvidenceError(f"{label} exit outcome is invalid")
        elif outcome_kind == "signal":
            if (
                exit_code is not None or isinstance(signal_number, bool)
                or not isinstance(signal_number, int) or signal_number < 1
            ):
                raise EvidenceError(f"{label} signal outcome is invalid")
        elif exit_code is not None or signal_number is not None:
            raise EvidenceError(f"{label} non-exit outcome is invalid")
        if classification["kind"] == "capability_denied":
            if classification["operation"] not in CAPABILITIES or outcome_kind != "not_run":
                raise EvidenceError(f"{label} capability classification is invalid")
        elif classification != {"kind": "product_result", "operation": None} or outcome_kind == "not_run":
            raise EvidenceError(f"{label} product classification is invalid")
        parent = pathlib.PurePosixPath(manifest_relative).parent
        stdout_record = _validate_stream(
            work, entry["stdout"], (parent / f"{evidence_id}.stdout").as_posix(),
            f"{label} stdout",
        )
        stderr_record = _validate_stream(
            work, entry["stderr"], (parent / f"{evidence_id}.stderr").as_posix(),
            f"{label} stderr",
        )
        stdout = _checked_file(work, stdout_record["path"], f"{label} stdout").read_bytes()
        stderr = _checked_file(work, stderr_record["path"], f"{label} stderr").read_bytes()
        met = _expectation_met(expectation, outcome, stdout, stderr)
        if not isinstance(entry["expectation_met"], bool) or entry["expectation_met"] != met:
            raise EvidenceError(f"{label} expectation result mismatch")
        if isinstance(entry["duration_ms"], bool) or not isinstance(entry["duration_ms"], int) or entry["duration_ms"] < 0:
            raise EvidenceError(f"{label} duration is invalid")
        if require_expectations and not met:
            raise EvidenceError(f"process evidence expectation mismatch: {phase}:{evidence_id}")
        streams.append({"id": evidence_id, "stdout": stdout_record, "stderr": stderr_record})
    missing = sorted(set(declared) - seen)
    if missing:
        raise EvidenceError(f"missing process evidence id(s): {','.join(missing)}")
    return {
        "phase": phase,
        "round": round_,
        "manifest": {"path": manifest_relative, "sha256": _sha256(manifest_raw)},
        "streams": streams,
    }


def validate_bound_carrier(work: pathlib.Path, carrier: object) -> None:
    if not isinstance(carrier, dict) or set(carrier) != {"phase", "round", "manifest", "streams"}:
        raise EvidenceError("state process-evidence carrier has an invalid shape")
    manifest = carrier["manifest"]
    if not isinstance(manifest, dict) or set(manifest) != {"path", "sha256"}:
        raise EvidenceError("state process-evidence manifest binding is invalid")
    raw = _checked_file(work, manifest["path"], "bound process evidence manifest").read_bytes()
    if not isinstance(manifest["sha256"], str) or _sha256(raw) != manifest["sha256"]:
        raise EvidenceError("bound process evidence manifest digest mismatch")
    document = _read_json(_checked_file(work, manifest["path"], "bound process evidence manifest"))
    if not isinstance(document, dict) or not isinstance(document.get("run_id"), str):
        raise EvidenceError("bound process evidence manifest identity is invalid")
    validated = validate_manifest(
        work, manifest["path"], document["run_id"],
        carrier["phase"], carrier["round"], require_expectations=False,
    )
    if validated["streams"] != carrier["streams"]:
        raise EvidenceError("bound process evidence stream binding mismatch")


def _load_state(devlyn: pathlib.Path) -> dict:
    state = _read_json(devlyn / "pipeline.state.json")
    if not isinstance(state, dict):
        raise EvidenceError("pipeline.state.json must contain an object")
    return state


def _declared_by_id(work: pathlib.Path, state: dict, phase: str, evidence_id: str) -> dict:
    matches = [item for item in declared_obligations(work, state, phase) if item["id"] == evidence_id]
    if len(matches) != 1:
        raise EvidenceError(f"undeclared process evidence id: {phase}:{evidence_id}")
    return matches[0]


def self_test() -> int:
    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        devlyn = work / ".devlyn"
        devlyn.mkdir()
        state = {
            "run_id": "rs-self-test",
            "phases": {"implement": {"round": 0}},
        }
        manifest_rel = manifest_relative_path(state, "implement")
        manifest = work / manifest_rel
        obligation = normalize_obligation({
            "id": "red-first", "phase": "implement",
            "cmd": "printf raw-out; printf raw-err >&2; exit 7",
            "exit_code": 7, "stdout_contains": ["raw-outraw-err"],
        })
        entry = capture_process(work, manifest, state["run_id"], "implement", 0, obligation)
        assert entry["expectation_met"]
        assert (manifest.parent / "red-first.stdout").read_bytes() == b"raw-out"
        assert (manifest.parent / "red-first.stderr").read_bytes() == b"raw-err"
        empty = normalize_obligation({
            "id": "empty-streams", "phase": "implement",
            "argv": [sys.executable, "-c", "pass"],
        })
        empty_entry = capture_process(
            work, manifest, state["run_id"], "implement", 0, empty,
        )
        assert empty_entry["expectation_met"]
        assert empty_entry["stdout"]["bytes"] == empty_entry["stderr"]["bytes"] == 0
        assert (manifest.parent / "empty-streams.stdout").is_file()
        assert (manifest.parent / "empty-streams.stderr").is_file()
        carrier = validate_manifest(
            work, manifest_rel, state["run_id"], "implement", 0, [obligation, empty],
        )
        assert carrier["manifest"]["sha256"] == _sha256(manifest.read_bytes())
        try:
            capture_process(work, manifest, state["run_id"], "implement", 0, obligation)
        except EvidenceError as exc:
            assert "duplicate process evidence id" in str(exc)
        else:
            raise AssertionError("duplicate evidence id was accepted")
        print("PASS process evidence raw streams, digest binding, and duplicate-id guard")

        stderr_path = manifest.parent / "red-first.stderr"
        stderr_path.write_bytes(b"altered")
        try:
            validate_manifest(work, manifest_rel, state["run_id"], "implement", 0, [obligation])
        except EvidenceError as exc:
            assert "digest or byte count mismatch" in str(exc)
        else:
            raise AssertionError("altered raw stream was accepted")
        stderr_path.write_bytes(b"raw-err")
        validate_bound_carrier(work, carrier)
        manifest.write_bytes(manifest.read_bytes() + b" ")
        try:
            validate_bound_carrier(work, carrier)
        except EvidenceError as exc:
            assert "manifest digest mismatch" in str(exc)
        else:
            raise AssertionError("altered bound manifest was accepted")
        print("PASS process evidence raw and manifest mutation detection")

    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        state = {"run_id": "rs-path-test", "phases": {"implement": {"round": 0}}}
        manifest_rel = manifest_relative_path(state, "implement")
        manifest = work / manifest_rel
        obligation = normalize_obligation({
            "id": "path-test", "phase": "implement", "argv": [sys.executable, "-c", "pass"],
        })
        capture_process(work, manifest, state["run_id"], "implement", 0, obligation)
        document = _read_json(manifest)
        document["entries"][0]["stdout"]["path"] = "../escape"
        _atomic_write(manifest, _json_bytes(document))
        try:
            validate_manifest(work, manifest_rel, state["run_id"], "implement", 0, [obligation])
        except EvidenceError as exc:
            assert "path mismatch" in str(exc)
        else:
            raise AssertionError("path-escaping evidence was accepted")
        document["entries"][0]["stdout"]["path"] = (
            pathlib.PurePosixPath(manifest_rel).parent / "path-test.stdout"
        ).as_posix()
        document["entries"].append(document["entries"][0])
        _atomic_write(manifest, _json_bytes(document))
        try:
            validate_manifest(work, manifest_rel, state["run_id"], "implement", 0, [obligation])
        except EvidenceError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("duplicate manifest id was accepted")
        print("PASS process evidence path and manifest duplicate-id rejection")

    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        state = {"run_id": "rs-expect-test", "phases": {"implement": {"round": 0}}}
        manifest_rel = manifest_relative_path(state, "implement")
        manifest = work / manifest_rel
        mismatch = normalize_obligation({
            "id": "mismatch", "phase": "implement", "cmd": "exit 0", "exit_code": 9,
        })
        entry = capture_process(work, manifest, state["run_id"], "implement", 0, mismatch)
        assert not entry["expectation_met"]
        try:
            validate_manifest(work, manifest_rel, state["run_id"], "implement", 0, [mismatch])
        except EvidenceError as exc:
            assert "expectation mismatch" in str(exc)
        else:
            raise AssertionError("expectation-mismatched evidence was accepted")
        signaled = normalize_obligation({
            "id": "signaled", "phase": "implement",
            "argv": [
                sys.executable, "-c",
                "import os, signal; os.kill(os.getpid(), signal.SIGTERM)",
            ],
        })
        signal_entry = capture_process(
            work, manifest, state["run_id"], "implement", 0, signaled,
        )
        assert signal_entry["outcome"] == {
            "kind": "signal", "exit_code": None, "signal": signal.SIGTERM,
        }
        validate_manifest(
            work, manifest_rel, state["run_id"], "implement", 0,
            require_expectations=False,
        )
        print("PASS process evidence exit expectation rejection and signal capture")

    with tempfile.TemporaryDirectory() as raw_tmp:
        work = pathlib.Path(raw_tmp)
        state = {"run_id": "rs-cap-test", "phases": {"build_gate": {"round": 0}}}
        manifest_rel = manifest_relative_path(state, "build_gate")
        manifest = work / manifest_rel
        product = normalize_obligation({
            "id": "product", "phase": "build_gate",
            "cmd": "printf 'Operation not permitted' >&2; exit 1",
        })
        denied = normalize_obligation({
            "id": "denied", "phase": "build_gate", "cmd": "python3 -m pytest",
        })
        product_entry = capture_process(
            work, manifest, state["run_id"], "build_gate", 0, product,
        )
        denied_entry = record_capability_denial(
            work, manifest, state["run_id"], "build_gate", 0, denied,
            "subprocess", b"parent route denied subprocess creation",
        )
        assert product_entry["classification"] == {"kind": "product_result", "operation": None}
        assert denied_entry["classification"] == {
            "kind": "capability_denied", "operation": "subprocess",
        }
        validate_manifest(
            work, manifest_rel, state["run_id"], "build_gate", 0,
            require_expectations=False,
        )
        print("PASS process evidence explicit capability classification without stderr heuristics")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--devlyn-dir", default=".devlyn")
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="action")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    run_parser.add_argument("--id", required=True)
    deny_parser = subparsers.add_parser("record-capability-denial")
    deny_parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    deny_parser.add_argument("--id", required=True)
    deny_parser.add_argument("--operation", choices=sorted(CAPABILITIES), required=True)
    deny_parser.add_argument("--detail", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.action is None:
        parser.error("an action is required unless --self-test")
    try:
        work = pathlib.Path(args.workdir).resolve()
        devlyn_arg = pathlib.Path(args.devlyn_dir)
        devlyn = devlyn_arg.resolve() if devlyn_arg.is_absolute() else (work / devlyn_arg).resolve()
        devlyn.relative_to(work)
        state = _load_state(devlyn)
        phase = args.phase
        round_ = phase_round(state, phase)
        manifest_rel = manifest_relative_path(state, phase)
        manifest = work / manifest_rel
        obligations = declared_obligations(work, state, phase)
        if args.action == "validate":
            carrier = validate_manifest(
                work, manifest_rel, state["run_id"], phase, round_, obligations,
            )
            sys.stdout.write(json.dumps(carrier, sort_keys=True) + "\n")
            return 0
        obligation = _declared_by_id(work, state, phase, args.id)
        if args.action == "run":
            entry = capture_process(work, manifest, state["run_id"], phase, round_, obligation)
        else:
            entry = record_capability_denial(
                work, manifest, state["run_id"], phase, round_, obligation,
                args.operation, args.detail.encode("utf-8"),
            )
        sys.stdout.write(json.dumps({
            "id": entry["id"], "expectation_met": entry["expectation_met"],
            "manifest_path": manifest_rel, "classification": entry["classification"],
        }, sort_keys=True) + "\n")
        return 0 if entry["expectation_met"] else 1
    except (EvidenceError, OSError, UnicodeError, ValueError) as exc:
        sys.stderr.write(f"BLOCKED:process-evidence-invalid: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
