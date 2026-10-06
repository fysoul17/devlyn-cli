#!/usr/bin/env python3
"""Strict JSON and `spec.expected.json` contract validation for the ideate loop's package check and acceptance runner."""
from __future__ import annotations

import json
import sys
import unittest


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


EXPECTED_TOP_LEVEL_KEYS = {
    "verification_commands",
    "forbidden_patterns",
    "required_files",
    "forbidden_files",
    "max_deps_added",
    "pure_design",
}
EXPECTED_VERIFICATION_COMMAND_KEYS = {
    "cmd",
    "argv",
    "exit_code",
    "timeout_sec",
    "stdout_contains",
    "stdout_not_contains",
    "contract_refs",
}
DEFAULT_TIMEOUT_SEC = 60


def verification_timeout_sec(command: dict) -> int:
    return command.get("timeout_sec", DEFAULT_TIMEOUT_SEC)


def validate_command(command: object, label: str) -> str | None:
    """Validate one command; `argv` and `cmd` are mutually exclusive."""
    if not isinstance(command, dict):
        return f"{label} must be an object"
    if "argv" in command:
        if "cmd" in command:
            return f"{label} requires exactly one of cmd or argv"
        value = command["argv"]
        if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value) or not value[0]:
            return f"{label}.argv must be a string array with non-empty argv[0]"
    else:
        cmd = command.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            return f"{label}.cmd must be a non-empty string"
    ec = command.get("exit_code", 0)
    if isinstance(ec, bool) or not isinstance(ec, int):
        return f"{label}.exit_code must be int (not bool)"
    timeout_sec = command.get("timeout_sec", DEFAULT_TIMEOUT_SEC)
    if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, int) or not 1 <= timeout_sec <= 600:
        return f"{label}.timeout_sec must be int from 1 to 600 (not bool)"
    for k in ("stdout_contains", "stdout_not_contains"):
        v = command.get(k, [])
        if not isinstance(v, list) or not all(isinstance(s, str) and s for s in v):
            return f"{label}.{k} must be a list of non-empty strings"
    return None


def validate_shape(data) -> str | None:
    """Return None if `data` has a non-empty, well-formed `verification_commands`
    list; else a human-readable error string.

    Each object requires exactly one of a non-empty string `cmd` or a
    string-array `argv`; `exit_code` defaults to 0 and must be a
    non-bool int; `timeout_sec` defaults to DEFAULT_TIMEOUT_SEC and must be a
    non-bool int from 1 through 600; `stdout_contains` and `stdout_not_contains`
    default to empty lists of non-empty strings. Bool is rejected explicitly
    because Python's `bool` subclasses `int`.
    """
    if not isinstance(data, dict):
        return "top-level must be a JSON object"
    cmds = data.get("verification_commands")
    if not isinstance(cmds, list):
        return "verification_commands must be a list"
    if not cmds:
        return "verification_commands must contain at least one entry"
    for i, c in enumerate(cmds):
        err = validate_command(c, f"verification_commands[{i}]")
        if err:
            return err
    return None


def validate_string_list(data: object, key: str) -> str | None:
    value = data.get(key, []) if isinstance(data, dict) else None
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return f"{key} must be a list of non-empty strings"
    return None


def validate_expected_shape(data) -> str | None:
    """Return None if shape matches the sibling spec.expected.json schema.

    Keep this dependency-free: it mirrors `_shared/expected.schema.json` enough
    to catch malformed contracts before a consumer executes them.
    """
    if not isinstance(data, dict):
        return "top-level must be a JSON object"
    unknown = sorted(set(data) - EXPECTED_TOP_LEVEL_KEYS)
    if unknown:
        return f"unknown top-level key(s): {', '.join(unknown)}"
    if "verification_commands" in data:
        commands = data["verification_commands"]
        if not isinstance(commands, list):
            return "verification_commands must be a list"
        if commands:
            err = validate_shape({"verification_commands": commands})
            if err:
                return err
        for i, command in enumerate(commands):
            unknown_command_keys = sorted(set(command) - EXPECTED_VERIFICATION_COMMAND_KEYS)
            if unknown_command_keys:
                return (
                    f"verification_commands[{i}] unknown key(s): "
                    f"{', '.join(unknown_command_keys)}"
                )
            contract_refs = command.get("contract_refs", [])
            if not isinstance(contract_refs, list) or not all(
                isinstance(item, str) and item for item in contract_refs
            ):
                return f"verification_commands[{i}].contract_refs must be a list of non-empty strings"
    for key in ("required_files", "forbidden_files"):
        err = validate_string_list(data, key)
        if err:
            return err
    max_deps = data.get("max_deps_added", 0)
    if isinstance(max_deps, bool) or not isinstance(max_deps, int) or max_deps < 0:
        return "max_deps_added must be a non-negative integer"
    if "pure_design" in data and not isinstance(data["pure_design"], bool):
        return "pure_design must be a boolean"
    patterns = data.get("forbidden_patterns", [])
    if not isinstance(patterns, list):
        return "forbidden_patterns must be a list"
    for i, pattern in enumerate(patterns):
        if not isinstance(pattern, dict):
            return f"forbidden_patterns[{i}] must be an object"
        unknown_pattern_keys = sorted(set(pattern) - {"pattern", "description", "files", "severity"})
        if unknown_pattern_keys:
            return (
                f"forbidden_patterns[{i}] unknown key(s): "
                f"{', '.join(unknown_pattern_keys)}"
            )
        for key in ("pattern", "description", "severity"):
            value = pattern.get(key)
            if not isinstance(value, str) or not value:
                return f"forbidden_patterns[{i}].{key} must be a non-empty string"
        if pattern["severity"] not in {"disqualifier", "warning"}:
            return f"forbidden_patterns[{i}].severity must be disqualifier or warning"
        files = pattern.get("files", [])
        if not isinstance(files, list) or not all(isinstance(item, str) and item for item in files):
            return f"forbidden_patterns[{i}].files must be a list of non-empty strings"
    return None


def slice_diff_to_files(diff_text: str, files: list[str]) -> str:
    if not files:
        return diff_text
    out: list[str] = []
    keep = False
    for line in diff_text.splitlines(keepends=True):
        if line.startswith("diff --git "):
            keep = any(path in line for path in files)
        if keep:
            out.append(line)
    return "".join(out)


class ContractTests(unittest.TestCase):
    def test_strict_json(self):
        for text, message in (('{"a":1,"a":2}', "duplicate JSON key"), ('{"a":NaN}', "invalid JSON numeric constant")):
            with self.assertRaisesRegex(ValueError, message):
                loads_strict_json(text)

    def test_cmd_and_argv_are_mutually_exclusive(self):
        ok = {"verification_commands": [{"argv": ["python3", "-c", "pass"], "contract_refs": ["R1"]}, {"cmd": "true"}]}
        self.assertIsNone(validate_expected_shape(ok))
        for command, message in (
            ({"cmd": "true", "argv": ["true"]}, "exactly one of cmd or argv"),
            ({"argv": []}, "argv must be a string array"),
            ({"argv": ["", "x"]}, "argv must be a string array"),
            ({"argv": ["x", 1]}, "argv must be a string array"),
            ({}, "cmd must be a non-empty string"),
        ):
            self.assertIn(message, validate_expected_shape({"verification_commands": [command]}))

    def test_command_fields(self):
        for command, message in (
            ({"cmd": "x", "exit_code": True}, "exit_code must be int"),
            ({"cmd": "x", "timeout_sec": 601}, "timeout_sec must be int from 1 to 600"),
            ({"cmd": "x", "stdout_contains": "x"}, "stdout_contains must be a list of non-empty strings"),
            ({"cmd": "x", "stdout_contains": [""]}, "stdout_contains must be a list of non-empty strings"),
            ({"cmd": "x", "stdout_not_contains": [""]}, "stdout_not_contains must be a list of non-empty strings"),
            ({"cmd": "x", "contract_refs": [""]}, "contract_refs must be a list of non-empty strings"),
            ({"cmd": "x", "extra": 1}, "unknown key(s): extra"),
        ):
            self.assertIn(message, validate_expected_shape({"verification_commands": [command]}))
        self.assertEqual(validate_expected_shape([]), "top-level must be a JSON object")
        self.assertIn("unknown top-level key(s): process_evidence", validate_expected_shape({"process_evidence": []}))

    def test_diff_helpers(self):
        diff = ('diff --git a/package.json b/package.json\n--- a/package.json\n+++ b/package.json\n@@ -1,3 +1,5 @@\n'
                ' {\n   "dependencies": {\n+    "left-pad": "1.0.0",\n+    "is-odd": "3.0.0"\n   }\n }\n'
                'diff --git a/other b/other\n+x\n')
        self.assertNotIn("other", slice_diff_to_files(diff, ["package.json"]))
        self.assertEqual(slice_diff_to_files(diff, []), diff)


def main() -> int:
    if sys.argv[1:] != ["--self-test"]:
        print("usage: expected-contract.py --self-test", file=sys.stderr)
        return 2
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests))
    if result.wasSuccessful():
        print(f"expected-contract self-test: PASS ({result.testsRun} tests)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
