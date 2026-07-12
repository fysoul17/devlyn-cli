#!/usr/bin/env python3
"""Freeze-time gate binding every hidden input to the visible task contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class GateError(ValueError):
    """The fixture cannot be frozen."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read {path}: {exc}") from exc


def validate_regex(pattern: str, value: Any, channel_id: str) -> None:
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise GateError(f"channel {channel_id} has invalid regex: {exc}") from exc
    rendered = value if isinstance(value, str) else json.dumps(value, sort_keys=True, separators=(",", ":"))
    if compiled.fullmatch(rendered) is None:
        raise GateError(f"channel {channel_id} rejects hidden value {rendered!r}")


def validate_executable(fixture: Path, relative: str, value: Any, channel_id: str) -> None:
    executable = (fixture / "hidden" / relative).resolve()
    hidden_root = (fixture / "hidden").resolve()
    try:
        executable.relative_to(hidden_root)
    except ValueError as exc:
        raise GateError(f"channel {channel_id} validator escapes hidden/: {relative}") from exc
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise GateError(f"channel {channel_id} validator is not executable: {relative}")
    completed = subprocess.run(
        [str(executable)],
        input=json.dumps(value, sort_keys=True) + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
        env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        raise GateError(f"channel {channel_id} rejects hidden value: {detail}")


def validate_bindings(fixture: Path, bindings: Any, channel_id: str) -> None:
    if not isinstance(bindings, list) or not bindings:
        raise GateError(f"channel {channel_id} bindings must be a non-empty array")
    seen: set[str] = set()
    has_task = False
    has_repo_evidence = False
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "excerpt"}:
            raise GateError(f"channel {channel_id} binding[{index}] is malformed")
        relative = binding["path"]
        if not isinstance(relative, str) or not relative or relative in seen:
            raise GateError(f"channel {channel_id} binding paths must be unique non-empty strings")
        seen.add(relative)
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != relative:
            raise GateError(f"channel {channel_id} binding path is unsafe: {relative}")
        if relative != "task.txt" and not relative.startswith("seed/"):
            raise GateError(f"channel {channel_id} binding must target task.txt or seed/: {relative}")
        unresolved = fixture / path
        if unresolved.is_symlink():
            raise GateError(f"channel {channel_id} binding may not be a symlink: {relative}")
        target = unresolved.resolve()
        try:
            target.relative_to(fixture)
        except ValueError as exc:
            raise GateError(f"channel {channel_id} binding escapes fixture: {relative}") from exc
        if not target.is_file():
            raise GateError(f"channel {channel_id} binding is not a regular file: {relative}")
        expected_sha = binding["sha256"]
        if not isinstance(expected_sha, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha) is None:
            raise GateError(f"channel {channel_id} binding has invalid sha256: {relative}")
        if sha256_file(target) != expected_sha:
            raise GateError(f"channel {channel_id} binding is stale: {relative}")
        excerpt = binding["excerpt"]
        try:
            source_text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise GateError(f"channel {channel_id} binding is not UTF-8: {relative}") from exc
        if not isinstance(excerpt, str) or not excerpt or excerpt not in source_text:
            raise GateError(f"channel {channel_id} excerpt is absent from {relative}")
        has_task = has_task or relative == "task.txt"
        has_repo_evidence = has_repo_evidence or relative.startswith("seed/")
    if not has_task or not has_repo_evidence:
        raise GateError(f"channel {channel_id} must bind both task.txt and seed/ evidence")


def validate_channel_values(fixture: Path, channel: dict[str, Any], channel_id: str) -> int:
    values = channel["values"]
    if not isinstance(values, list) or not values:
        raise GateError(f"channel {channel_id} values must be a non-empty array")
    validator = channel["validator"]
    if not isinstance(validator, dict) or validator.get("type") not in {"regex", "executable"}:
        raise GateError(f"channel {channel_id} has no regex or executable validator")
    if validator["type"] == "regex":
        if set(validator) != {"type", "pattern"} or not isinstance(validator.get("pattern"), str):
            raise GateError(f"channel {channel_id} regex validator is malformed")
        for value in values:
            validate_regex(validator["pattern"], value, channel_id)
    else:
        if set(validator) != {"type", "path"} or not isinstance(validator.get("path"), str):
            raise GateError(f"channel {channel_id} executable validator is malformed")
        for value in values:
            validate_executable(fixture, validator["path"], value, channel_id)
    return len(values)


def validate_fixture(fixture: Path) -> dict[str, Any]:
    fixture = fixture.resolve()
    task_path = fixture / "task.txt"
    declaration_path = fixture / "hidden" / "conformance.json"
    if not task_path.is_file():
        raise GateError(f"task text missing: {task_path}")
    if not declaration_path.is_file():
        raise GateError(f"conformance declaration missing: {declaration_path}")
    task_text = task_path.read_text(encoding="utf-8")
    task_sha = sha256_text(task_text)
    declaration = load_json(declaration_path)
    if not isinstance(declaration, dict) or set(declaration) != {"schema_version", "channels"}:
        raise GateError("conformance root must contain exactly schema_version and channels")
    schema_version = declaration["schema_version"]
    if schema_version not in {"hidden-conformance-1", "hidden-conformance-2"}:
        raise GateError("conformance schema_version must equal hidden-conformance-1 or hidden-conformance-2")
    channels = declaration["channels"]
    if not isinstance(channels, list) or not channels:
        raise GateError("conformance channels must be a non-empty array")
    seen: set[str] = set()
    value_count = 0
    for index, channel in enumerate(channels):
        if not isinstance(channel, dict):
            raise GateError(f"channel[{index}] must be an object")
        required = (
            {"id", "visible_contract_excerpt", "task_sha256", "validator", "values"}
            if schema_version == "hidden-conformance-1"
            else {"id", "bindings", "validator", "values"}
        )
        if set(channel) != required:
            raise GateError(
                f"channel[{index}] fields differ: missing={sorted(required - set(channel))} "
                f"extra={sorted(set(channel) - required)}"
            )
        channel_id = channel["id"]
        if not isinstance(channel_id, str) or not channel_id or channel_id in seen:
            raise GateError(f"channel[{index}] id must be a unique non-empty string")
        seen.add(channel_id)
        if schema_version == "hidden-conformance-1":
            excerpt = channel["visible_contract_excerpt"]
            if not isinstance(excerpt, str) or not excerpt or excerpt not in task_text:
                raise GateError(f"channel {channel_id} visible-contract excerpt is absent from task.txt")
            binding = channel["task_sha256"]
            if not isinstance(binding, str) or not re.fullmatch(r"[0-9a-f]{64}", binding):
                raise GateError(f"channel {channel_id} has missing or invalid task_sha256 binding")
            if binding != task_sha:
                raise GateError(f"channel {channel_id} task_sha256 binding is stale")
        else:
            validate_bindings(fixture, channel["bindings"], channel_id)
        value_count += validate_channel_values(fixture, channel, channel_id)
    return {
        "fixture": fixture.name,
        "schema_version": schema_version,
        "task_sha256": task_sha,
        "channels": len(channels),
        "values": value_count,
    }


def partition_inputs(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    fixtures: list[Path] = []
    ignored_files: list[Path] = []
    for path in paths:
        if path.is_dir():
            fixtures.append(path)
        elif path.is_file():
            ignored_files.append(path.resolve())
        elif path.exists():
            raise GateError(f"fixture path is not a directory or regular file: {path}")
        else:
            raise GateError(f"fixture path does not exist: {path}")
    if not fixtures:
        raise GateError("no fixture directories remain after ignoring regular files")
    return fixtures, ignored_files


def write_fixture(root: Path, *, binding: bool = True, passing_value: bool = True) -> None:
    hidden = root / "hidden"
    hidden.mkdir(parents=True)
    task = "The mode must be one of fast or safe.\n"
    (root / "task.txt").write_text(task, encoding="utf-8")
    channel: dict[str, Any] = {
        "id": "mode",
        "visible_contract_excerpt": "mode must be one of fast or safe",
        "validator": {"type": "regex", "pattern": "^(fast|safe)$"},
        "values": ["fast" if passing_value else "turbo"],
    }
    if binding:
        channel["task_sha256"] = sha256_text(task)
    declaration = {"schema_version": "hidden-conformance-1", "channels": [channel]}
    (hidden / "conformance.json").write_text(json.dumps(declaration), encoding="utf-8")


def write_fixture_v2(root: Path, *, stale_evidence: bool = False, unsafe_path: bool = False) -> None:
    hidden = root / "hidden"
    seed = root / "seed"
    hidden.mkdir(parents=True)
    seed.mkdir()
    task = "Choose fast or safe using the repository decision.\n"
    evidence = "The supported mode is safe.\n"
    (root / "task.txt").write_text(task, encoding="utf-8")
    (seed / "decision.md").write_text(evidence, encoding="utf-8")
    evidence_path = "../outside" if unsafe_path else "seed/decision.md"
    channel = {
        "id": "mode",
        "bindings": [
            {"path": "task.txt", "sha256": sha256_text(task), "excerpt": "Choose fast or safe"},
            {
                "path": evidence_path,
                "sha256": "0" * 64 if stale_evidence else sha256_text(evidence),
                "excerpt": "supported mode is safe",
            },
        ],
        "validator": {"type": "regex", "pattern": "^(fast|safe)$"},
        "values": ["safe"],
    }
    declaration = {"schema_version": "hidden-conformance-2", "channels": [channel]}
    (hidden / "conformance.json").write_text(json.dumps(declaration), encoding="utf-8")


def self_test() -> int:
    checks = 0
    with tempfile.TemporaryDirectory(prefix="ncg-") as temporary:
        root = Path(temporary)
        passing = root / "passing"
        missing = root / "missing-binding"
        failing = root / "failing-value"
        write_fixture(passing)
        write_fixture(missing, binding=False)
        write_fixture(failing, passing_value=False)
        result = validate_fixture(passing)
        if result["values"] != 1:
            raise AssertionError("passing fixture did not validate its hidden value")
        checks += 1
        for fixture, expected in ((missing, "task_sha256"), (failing, "rejects hidden value")):
            try:
                validate_fixture(fixture)
            except GateError as exc:
                if expected not in str(exc):
                    raise AssertionError(f"unexpected failure for {fixture.name}: {exc}") from exc
            else:
                raise AssertionError(f"{fixture.name} did not fail closed")
            checks += 1
        v2 = root / "passing-v2"
        stale = root / "stale-v2"
        unsafe = root / "unsafe-v2"
        write_fixture_v2(v2)
        write_fixture_v2(stale, stale_evidence=True)
        write_fixture_v2(unsafe, unsafe_path=True)
        result = validate_fixture(v2)
        if result["schema_version"] != "hidden-conformance-2":
            raise AssertionError("v2 fixture did not report its schema")
        checks += 1
        for fixture, expected in ((stale, "binding is stale"), (unsafe, "binding path is unsafe")):
            try:
                validate_fixture(fixture)
            except GateError as exc:
                if expected not in str(exc):
                    raise AssertionError(f"unexpected v2 failure for {fixture.name}: {exc}") from exc
            else:
                raise AssertionError(f"{fixture.name} did not fail closed")
            checks += 1
        metadata = root / "power.json"
        metadata.write_text("{}\n", encoding="utf-8")
        fixtures, ignored_files = partition_inputs([passing, metadata])
        if fixtures != [passing] or ignored_files != [metadata.resolve()]:
            raise AssertionError("parent-glob inputs did not separate fixtures from regular metadata files")
        checks += 1
        for paths, expected in (([metadata], "no fixture directories"), ([root / "absent"], "does not exist")):
            try:
                partition_inputs(paths)
            except GateError as exc:
                if expected not in str(exc):
                    raise AssertionError(f"unexpected input-boundary failure: {exc}") from exc
            else:
                raise AssertionError(f"input boundary did not fail closed: {paths}")
            checks += 1
    print(f"conformance-gate self-test: PASS ({checks} checks)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixtures", nargs="*", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if args.fixtures:
            parser.error("--self-test does not accept fixture paths")
        return self_test()
    if not args.fixtures:
        parser.error("at least one fixture path is required")
    try:
        fixtures, ignored_files = partition_inputs(args.fixtures)
        results = [validate_fixture(fixture) for fixture in fixtures]
    except GateError as exc:
        print(f"CONFORMANCE_FREEZE_ERROR: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"status": "PASS", "fixtures": results, "ignored_files": [str(path) for path in ignored_files]},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
