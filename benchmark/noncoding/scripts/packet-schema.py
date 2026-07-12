#!/usr/bin/env python3
"""Dependency-free fail-closed validator for the frozen pud-1 shape."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class PacketError(ValueError):
    """A packet does not conform to pud-1."""


def require_object(value: Any, path: str, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PacketError(f"{path} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise PacketError(f"{path} fields differ: missing={missing} extra={extra}")
    return value


def require_string(value: Any, path: str) -> str:
    if not isinstance(value, str):
        raise PacketError(f"{path} must be a string")
    return value


def require_string_array(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        raise PacketError(f"{path} must be an array")
    for index, item in enumerate(value):
        require_string(item, f"{path}[{index}]")
    return value


def validate_acceptance(value: Any, path: str) -> None:
    if not isinstance(value, list):
        raise PacketError(f"{path} must be an array")
    for index, item in enumerate(value):
        record = require_object(item, f"{path}[{index}]", {"id", "observable"})
        require_string(record["id"], f"{path}[{index}].id")
        require_string(record["observable"], f"{path}[{index}].observable")


def validate_packet(packet: Any) -> dict[str, Any]:
    root = require_object(
        packet,
        "$",
        {"schema_version", "project_acceptance", "tasks", "open_questions", "assumptions"},
    )
    if root["schema_version"] != "pud-1":
        raise PacketError("$.schema_version must equal pud-1")
    validate_acceptance(root["project_acceptance"], "$.project_acceptance")
    tasks = root["tasks"]
    if not isinstance(tasks, list):
        raise PacketError("$.tasks must be an array")
    task_ids: list[str] = []
    for index, item in enumerate(tasks):
        path = f"$.tasks[{index}]"
        task = require_object(
            item,
            path,
            {"id", "objective", "depends_on", "context_refs", "scope", "acceptance", "handoff"},
        )
        task_ids.append(require_string(task["id"], f"{path}.id"))
        require_string(task["objective"], f"{path}.objective")
        require_string_array(task["depends_on"], f"{path}.depends_on")
        refs = task["context_refs"]
        if not isinstance(refs, list):
            raise PacketError(f"{path}.context_refs must be an array")
        for ref_index, item_ref in enumerate(refs):
            ref_path = f"{path}.context_refs[{ref_index}]"
            ref = require_object(item_ref, ref_path, {"path", "line_start", "line_end", "claim"})
            require_string(ref["path"], f"{ref_path}.path")
            require_string(ref["claim"], f"{ref_path}.claim")
            for field in ("line_start", "line_end"):
                if not isinstance(ref[field], int) or isinstance(ref[field], bool) or ref[field] < 1:
                    raise PacketError(f"{ref_path}.{field} must be a positive integer")
            if ref["line_end"] < ref["line_start"]:
                raise PacketError(f"{ref_path}.line_end precedes line_start")
        scope = require_object(task["scope"], f"{path}.scope", {"may_change", "must_preserve"})
        require_string_array(scope["may_change"], f"{path}.scope.may_change")
        require_string_array(scope["must_preserve"], f"{path}.scope.must_preserve")
        validate_acceptance(task["acceptance"], f"{path}.acceptance")
        require_string(task["handoff"], f"{path}.handoff")
    if len(task_ids) != len(set(task_ids)):
        raise PacketError("$.tasks ids must be unique")
    known_ids = set(task_ids)
    for index, task in enumerate(tasks):
        unknown = sorted(set(task["depends_on"]) - known_ids)
        if unknown:
            raise PacketError(f"$.tasks[{index}].depends_on references unknown ids: {unknown}")
    questions = root["open_questions"]
    if not isinstance(questions, list):
        raise PacketError("$.open_questions must be an array")
    for index, item in enumerate(questions):
        path = f"$.open_questions[{index}]"
        question = require_object(item, path, {"question", "blocking", "evidence_refs"})
        require_string(question["question"], f"{path}.question")
        if not isinstance(question["blocking"], bool):
            raise PacketError(f"{path}.blocking must be a boolean")
        require_string_array(question["evidence_refs"], f"{path}.evidence_refs")
    assumptions = root["assumptions"]
    if not isinstance(assumptions, list):
        raise PacketError("$.assumptions must be an array")
    for index, item in enumerate(assumptions):
        path = f"$.assumptions[{index}]"
        assumption = require_object(item, path, {"statement", "evidence_refs"})
        require_string(assumption["statement"], f"{path}.statement")
        require_string_array(assumption["evidence_refs"], f"{path}.evidence_refs")
    return root


def load_packet(path: Path) -> dict[str, Any]:
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"cannot read packet {path}: {exc}") from exc
    return validate_packet(packet)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packets", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        for packet in args.packets:
            load_packet(packet)
    except PacketError as exc:
        print(f"PUD_1_ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"pud-1: PASS ({len(args.packets)} packet(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
