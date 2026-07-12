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
    if declaration["schema_version"] != "hidden-conformance-1":
        raise GateError("conformance schema_version must equal hidden-conformance-1")
    channels = declaration["channels"]
    if not isinstance(channels, list) or not channels:
        raise GateError("conformance channels must be a non-empty array")
    seen: set[str] = set()
    value_count = 0
    for index, channel in enumerate(channels):
        if not isinstance(channel, dict):
            raise GateError(f"channel[{index}] must be an object")
        required = {"id", "visible_contract_excerpt", "task_sha256", "validator", "values"}
        if set(channel) != required:
            raise GateError(
                f"channel[{index}] fields differ: missing={sorted(required - set(channel))} "
                f"extra={sorted(set(channel) - required)}"
            )
        channel_id = channel["id"]
        if not isinstance(channel_id, str) or not channel_id or channel_id in seen:
            raise GateError(f"channel[{index}] id must be a unique non-empty string")
        seen.add(channel_id)
        excerpt = channel["visible_contract_excerpt"]
        if not isinstance(excerpt, str) or not excerpt or excerpt not in task_text:
            raise GateError(f"channel {channel_id} visible-contract excerpt is absent from task.txt")
        binding = channel["task_sha256"]
        if not isinstance(binding, str) or not re.fullmatch(r"[0-9a-f]{64}", binding):
            raise GateError(f"channel {channel_id} has missing or invalid task_sha256 binding")
        if binding != task_sha:
            raise GateError(f"channel {channel_id} task_sha256 binding is stale")
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
        value_count += len(values)
    return {"fixture": fixture.name, "task_sha256": task_sha, "channels": len(channels), "values": value_count}


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
        results = [validate_fixture(fixture) for fixture in args.fixtures]
    except GateError as exc:
        print(f"CONFORMANCE_FREEZE_ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "PASS", "fixtures": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
