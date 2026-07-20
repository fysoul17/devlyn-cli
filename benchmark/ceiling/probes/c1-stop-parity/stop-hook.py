#!/usr/bin/env python3
"""Project-scope Stop hook for the frozen C1 parity probe."""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import pathlib
import sys
import time
from types import ModuleType
from typing import Any


INCOMPLETE_EXIT = 79
BLOCK_REASON = "C1 terminal claim is incomplete; continue without changing .devlyn state"


def load_classifier(path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("c1_terminal_claim_check", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"classifier cannot be loaded: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def append_invocation(path: pathlib.Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        stream.seek(0)
        ordinal = sum(1 for line in stream if line.strip()) + 1
        record["ordinal"] = ordinal
        stream.seek(0, 2)
        stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def emit_block(form: str, reason: str) -> int:
    if form == "json":
        print(json.dumps({"decision": "block"}, separators=(",", ":")))
        return 0
    print(reason, file=sys.stderr)
    return 2


def parse_input(expected_event: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.load(sys.stdin)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, f"invalid hook input: {type(exc).__name__}"
    if not isinstance(value, dict):
        return None, "hook input must be a JSON object"
    if value.get("hook_event_name") != expected_event:
        return None, f"hook_event_name must be {expected_event}"
    if expected_event == "Stop" and not isinstance(value.get("stop_hook_active"), bool):
        return None, "stop_hook_active must be boolean"
    return value, None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        required=True,
        choices=("always-block", "state", "internal-error", "stop-failure"),
    )
    parser.add_argument("--block-form", required=True, choices=("exit2", "json"))
    parser.add_argument("--classifier", required=True, type=pathlib.Path)
    parser.add_argument("--root", required=True, type=pathlib.Path)
    parser.add_argument("--log", required=True, type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    expected_event = "StopFailure" if args.mode == "stop-failure" else "Stop"
    hook_input, input_error = parse_input(expected_event)
    observed_ns = time.monotonic_ns()
    base: dict[str, Any] = {
        "observed_ns": observed_ns,
        "hook_event_name": None if hook_input is None else hook_input["hook_event_name"],
        "stop_hook_active": None if hook_input is None else hook_input.get("stop_hook_active"),
        "mode": args.mode,
        "block_form": args.block_form,
        "classifier_status": None,
        "classifier_exit": None,
        "classifier_expected": False,
        "block_requested": True,
        "wrapper_exit": 2,
    }

    if input_error is not None:
        base["classifier_status"] = "HOOK_INPUT_MALFORMED"
        append_invocation(args.log, base)
        print(f"C1 hook failure: {input_error}", file=sys.stderr)
        return 2

    if args.mode == "stop-failure":
        base.update(
            classifier_status="STOP_FAILURE",
            classifier_expected=True,
            block_requested=False,
            wrapper_exit=0,
        )
        append_invocation(args.log, base)
        return 0

    if args.mode == "always-block":
        wrapper_exit = 0 if args.block_form == "json" else 2
        base.update(
            classifier_status="ALWAYS_BLOCK",
            classifier_expected=True,
            wrapper_exit=wrapper_exit,
        )
        append_invocation(args.log, base)
        return emit_block(args.block_form, "C1 canary block; produce another model turn")

    if args.mode == "internal-error":
        base.update(
            classifier_status="INTENTIONAL_HOOK_INTERNAL_ERROR",
            block_requested=False,
            wrapper_exit=5,
        )
        append_invocation(args.log, base)
        print("C1 intentional hook internal-error control", file=sys.stderr)
        return 5

    try:
        result = load_classifier(args.classifier).classify(args.root)
        status = result.status
        classifier_exit = INCOMPLETE_EXIT if result.incomplete else 0
    except (AttributeError, ImportError, OSError, RuntimeError, SyntaxError, TypeError, ValueError) as exc:
        base["classifier_status"] = f"CLASSIFIER_ERROR:{type(exc).__name__}"
        append_invocation(args.log, base)
        print(f"C1 classifier failure: {type(exc).__name__}", file=sys.stderr)
        return 2

    incomplete_expected = classifier_exit == INCOMPLETE_EXIT and status.startswith("INCOMPLETE:")
    allow_expected = classifier_exit == 0 and status in {"CLEAN", "NOT_APPLICABLE"}
    if incomplete_expected:
        wrapper_exit = 0 if args.block_form == "json" else 2
        base.update(
            classifier_status=status,
            classifier_exit=classifier_exit,
            classifier_expected=True,
            wrapper_exit=wrapper_exit,
        )
        append_invocation(args.log, base)
        return emit_block(args.block_form, BLOCK_REASON)
    if allow_expected:
        base.update(
            classifier_status=status,
            classifier_exit=classifier_exit,
            classifier_expected=True,
            block_requested=False,
            wrapper_exit=0,
        )
        append_invocation(args.log, base)
        return 0

    base.update(classifier_status=status, classifier_exit=classifier_exit)
    append_invocation(args.log, base)
    print(f"C1 unexpected classifier result: status={status} exit={classifier_exit}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
