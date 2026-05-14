#!/usr/bin/env python3
"""Spec literal verification gate (iter-0019.6 + iter-0019.8 + iter-0019.9
carrier).

Default mode (BUILD_GATE invocation, no args):
- Resolves the contract carrier in this priority order (iter-0019.8 + Codex
  R2 + iter-0019.9 Codex R-phaseA fix):
  (1) **Benchmark mode trust** (iter-0019.9 fix for the F9 regression): when
      `BENCH_WORKDIR` is set AND `.devlyn/spec-verify.json` already exists
      at script start, trust it as the run-fixture.sh-staged contract from
      `expected.json` and skip source-extract entirely. Without this guard,
      an ideate-generated spec's `## Verification` ```json``` block (e.g.
      F9 e2e novice flow generates `commitCount`/`topAuthors` while
      benchmark truth is `commits`/`authors`) silently overwrote the
      authoritative benchmark contract. For benchmarks, expected.json is
      canonical.
  (2) Otherwise, real-user spec mode first reads sibling `spec.expected.json`
      next to `spec.md`; if it exists, validate it and stage its
      `verification_commands`. A malformed sibling fails closed. If absent,
      fall back to source markdown extract.
  (3) For generated criteria and legacy handwritten specs without a sibling,
      source markdown extract reads `pipeline.state.json:
      source.{spec_path | criteria_path}` and extracts a `## Verification`
      ```json``` block. If present, overwrite `.devlyn/spec-verify.json`.
  (4) If no json block in source AND source.type=="generated": emit
      CRITICAL `correctness.spec-verify-malformed` so the fix-loop reruns
      BUILD.
  (5) If no sibling/json block in source AND source.type=="spec": benchmark mode
      with a pre-staged file would have hit branch (1). Without the
      pre-staged file, benchmark falls through to no-op (rare — fixture
      mis-config). Real-user mode silent no-op + drops any stale
      pre-staged file (preserves iter-0019.6 backward compat for
      handwritten specs without the carrier).
- For each verification_commands entry, runs the command in the work-dir,
  captures combined stdout+stderr, and asserts exit_code matches +
  stdout_contains all required literals + stdout_not_contains none of the
  forbidden literals. Mirrors run-fixture.sh's post-run verifier semantics.

Check mode (`--check <markdown_path>`):
- Used by /devlyn:ideate after writing each item spec to validate that the
  generated `## Verification` ```json``` block parses + matches the schema,
  and that present `complexity` frontmatter has a supported value.
- Exits 0 if the block is well-formed (or absent — ideate's check applies
  to both new specs that include the block and pre-carrier handwritten
  specs that omit it; absence is not failure here, only malformed JSON or
  shape error is). Exits 2 on malformed json, shape error, or unsupported
  `complexity` value.

Expected-contract check mode (`--check-expected <json_path>`):
- Used by /devlyn:ideate after writing sibling `spec.expected.json`.
- Exits 0 if the file is valid JSON and matches `_shared/expected.schema.json`
  shape, and if sibling `spec.md` has supported `complexity` frontmatter.
  Exits 2 on unreadable, malformed, unsupported fields, or unsupported sibling
  spec complexity.

Output routing:
- Default BUILD_GATE output writes `.devlyn/spec-verify-findings.jsonl` with
  `phase: build_gate` and `BGATE-*` ids.
- VERIFY may set `SPEC_VERIFY_PHASE=verify_mechanical`,
  `SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl`, and
  `SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH` so `verify-merge-findings.py` consumes
  deterministic blockers directly.

Why: iter-0018.5's prompt-only contract enforcement was empirically dead
(F9 verify=0.4 across all engines in iter-0019). Same lesson as iter-0008
prompt-only engine constraint. Mechanical bash-gate enforcement is the
only working pattern. iter-0019.8 extends iter-0019.6 from benchmark-only
to real-user runs by extracting the contract from the spec/criteria
markdown directly — closes NORTH-STAR test #14.

Exit codes:
- 0: silent no-op (no source carrier, real-user mode) OR --check passed
  OR all commands passed. Non-blocking expected-contract findings may be
  written with exit 0.
- 1: at least one command failed, carrier malformed (generated source
  required carrier, generated source had invalid json/shape, or pre-staged
  file failed shape validation), or a blocking expected-contract finding
  was emitted. Findings are written to the routed `.devlyn/` findings file:
  `.devlyn/spec-verify-findings.jsonl` by default, or the file selected by
  `SPEC_VERIFY_FINDINGS_FILE` (for example, VERIFY uses
  `.devlyn/verify-mechanical.findings.jsonl`).
- 2: invocation error (unreadable spec-verify.json, missing markdown in
  --check mode, etc.)
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def reject_json_constant(token: str) -> None:
    raise ValueError(f"invalid JSON numeric constant: {token}")


def loads_strict_json(text: str):
    return json.loads(text, parse_constant=reject_json_constant)


def output_phase() -> str:
    return os.environ.get("SPEC_VERIFY_PHASE", "build_gate")


def output_findings_name() -> str:
    return os.environ.get("SPEC_VERIFY_FINDINGS_FILE", "spec-verify-findings.jsonl")


def output_finding_prefix() -> str:
    return os.environ.get("SPEC_VERIFY_FINDING_PREFIX", "BGATE")


VERIFICATION_SECTION_RE = re.compile(
    r'(?ms)^##[ \t]+Verification\b[^\n]*\n(.*?)(?=^##[ \t]+|\Z)'
)
JSON_FENCE_RE = re.compile(r'(?ms)^```json[ \t]*\n(.*?)\n```[ \t]*$')
FORBIDDEN_RISK_PROBE_CMD_RE = re.compile(
    r'BENCH_FIXTURE_DIR|benchmark/auto-resolve/fixtures|/verifiers/|verifiers/'
)
EXTERNAL_URL_RE = re.compile(r"https?://([^/\s\"']+)", re.IGNORECASE)
INLINE_JSON_OBJECT_RE = re.compile(r'`?\{\s*"[^"\n]+"\s*:', re.IGNORECASE)
BACKTICKED_TEXT_RE = re.compile(r"`[^`\n]+`")
OBSERVABLE_COMMAND_MARKERS = ("command", "observable", "expose")
RESERVED_BACKTICK_TERMS = {"solo-headroom hypothesis", "solo_claude", "miss"}
SOLO_CEILING_CONTROL_RE = re.compile(
    r'\bS[2-6]\b|S2-S6|solo-saturated|rejected controls?|solo ceiling',
    re.IGNORECASE,
)
SOLO_CEILING_DIFFERENCE_RE = re.compile(
    r'\bdiffer(?:s|ent|ence)?\b|\bunlike\b|\bbecause\b|\bpreserve\b|\bheadroom\b',
    re.IGNORECASE,
)
COMMAND_PREFIXES = {
    "bash",
    "bun",
    "cargo",
    "git",
    "go",
    "jest",
    "make",
    "node",
    "npm",
    "pnpm",
    "printf",
    "pytest",
    "python",
    "python3",
    "ruff",
    "sh",
    "uv",
    "vitest",
    "yarn",
}
LOCAL_URL_HOSTS = {
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    '[::1]',
    '::1',
}
RISK_PROBE_TAGS = {
    "ordering_inversion",
    "boundary_overlap",
    "prior_consumption",
    "rollback_state",
    "positive_remaining",
    "stdout_stderr_contract",
    "error_contract",
    "http_error_contract",
    "auth_signature_contract",
    "idempotency_replay",
    "concurrent_state_consistency",
    "atomic_batch_state",
    "shape_contract",
}
RISK_PROBE_REQUIRED_EVIDENCE = {
    "ordering_inversion": {
        "input_order_would_choose_wrong_winner",
        "asserts_processing_order_result",
    },
    "boundary_overlap": {
        "starts_at_blocked_start",
        "ends_at_blocked_end",
        "one_minute_overlap",
    },
    "prior_consumption": {
        "same_resource_consumed_first",
        "later_entity_fails_or_reroutes",
    },
    "rollback_state": {
        "failed_entity_tentative_state_absent",
        "later_entity_uses_released_state",
    },
    "positive_remaining": {
        "asserts_full_remaining_state",
        "zero_quantity_rows_absent",
    },
    "stdout_stderr_contract": {
        "asserts_named_stream_output",
    },
    "error_contract": {
        "asserts_error_payload_or_stderr",
        "asserts_nonzero_or_exit_2",
    },
    "http_error_contract": {
        "asserts_http_error_status",
        "asserts_error_payload_body",
    },
    "auth_signature_contract": {
        "asserts_signature_over_exact_bytes",
        "asserts_tampered_or_missing_signature_rejected",
    },
    "idempotency_replay": {
        "first_delivery_then_duplicate",
        "duplicate_id_rejected_regardless_of_body",
    },
    "concurrent_state_consistency": {
        "overlapping_mutations_exercised",
        "all_successful_responses_reflected",
        "distinct_identifiers_asserted",
    },
    "atomic_batch_state": {
        "mixed_valid_invalid_batch",
        "asserts_store_unchanged_after_failure",
        "asserts_success_order_and_distinct_ids",
    },
}
SHAPE_CONTRACT_REQUIRED_EVIDENCE = {
    "uses_visible_input_key_names",
    "asserts_visible_output_key_names",
    "asserts_no_unexpected_output_keys",
}
EXPECTED_TOP_LEVEL_KEYS = {
    "verification_commands",
    "forbidden_patterns",
    "required_files",
    "forbidden_files",
    "tier_a_waivers",
    "spec_output_files",
    "max_deps_added",
}
EXPECTED_VERIFICATION_COMMAND_KEYS = {
    "cmd",
    "exit_code",
    "stdout_contains",
    "stdout_not_contains",
    "contract_refs",
}
PURE_DESIGN_ESCAPE = "all Requirements are pure-design"
SPEC_COMPLEXITY_VALUES = {"trivial", "medium", "high", "large"}


def extract_verification_block(text: str) -> str | None:
    """Return the contents of the first ```json``` fenced block under the
    first `## Verification` H2 heading, or None if not found.

    Boundary: the fenced block must appear AFTER the `## Verification`
    heading and BEFORE the next H2 (`## ...`) heading or end-of-file.
    """
    section = VERIFICATION_SECTION_RE.search(text)
    if not section:
        return None
    fence = JSON_FENCE_RE.search(section.group(1))
    return fence.group(1) if fence else None


def extract_verification_text(text: str) -> str:
    section = VERIFICATION_SECTION_RE.search(text)
    return section.group(1) if section else ""


def extract_frontmatter_field(text: str, field: str) -> str | None:
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    pattern = re.compile(rf"\s*{re.escape(field)}\s*:\s*[\"']?([^\"'\n#]+)")
    for line in text[3:end].splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip().lower()
    return None


def validate_present_spec_complexity(text: str) -> str | None:
    complexity = extract_frontmatter_field(text, "complexity")
    if complexity is None or complexity in SPEC_COMPLEXITY_VALUES:
        return None
    values = ", ".join(sorted(SPEC_COMPLEXITY_VALUES))
    return f"frontmatter complexity must be one of: {values}"


def backticked_observable_miss_commands(text: str) -> list[str]:
    commands: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if "miss" not in lower or not any(marker in lower for marker in OBSERVABLE_COMMAND_MARKERS):
            continue
        for match in BACKTICKED_TEXT_RE.finditer(line):
            value = match.group(0).strip("`")
            if is_command_like_backtick(value):
                commands.append(value)
    return commands


def is_command_like_backtick(value: str) -> bool:
    stripped = value.strip()
    lower = stripped.lower()
    if not stripped or lower in RESERVED_BACKTICK_TERMS:
        return False
    first = lower.split(maxsplit=1)[0]
    return (
        first in COMMAND_PREFIXES
        or any(marker in stripped for marker in ("/", "$", "=", "|", "&&", ";"))
        or stripped.endswith((".js", ".py", ".sh"))
    )


def has_backticked_observable_miss_command(text: str) -> bool:
    return bool(backticked_observable_miss_commands(text))


def validate_present_solo_headroom_hypothesis(text: str) -> str | None:
    lower = text.lower()
    if "solo-headroom hypothesis" not in lower and not ("solo_claude" in lower and "miss" in lower):
        return None
    if (
        "solo-headroom hypothesis" in lower
        and "solo_claude" in lower
        and "miss" in lower
        and has_backticked_observable_miss_command(text)
    ):
        return None
    return (
        "solo-headroom hypothesis must include `solo-headroom hypothesis`, "
        "`solo_claude`, `miss`, and a backticked command/observable line "
        "that exposes the miss"
    )


def validate_present_solo_ceiling_avoidance(text: str) -> str | None:
    lower = text.lower()
    if "solo ceiling avoidance" not in lower:
        return None
    if (
        "solo_claude" in lower
        and SOLO_CEILING_CONTROL_RE.search(text)
        and SOLO_CEILING_DIFFERENCE_RE.search(text)
    ):
        return None
    return (
        "solo ceiling avoidance must include `solo ceiling avoidance`, "
        "`solo_claude`, and a concrete difference from rejected or "
        "solo-saturated controls such as `S2`-`S6`"
    )


def validate_solo_headroom_commands_against_expected(
    spec_text: str,
    commands: object,
    expected_label: str,
) -> str | None:
    lower = spec_text.lower()
    if "solo-headroom hypothesis" not in lower and not ("solo_claude" in lower and "miss" in lower):
        return None
    expected_cmds = {
        command.get("cmd")
        for command in commands
        if isinstance(command, dict) and isinstance(command.get("cmd"), str)
    } if isinstance(commands, list) else set()
    hypothesis_cmds = backticked_observable_miss_commands(spec_text)
    if any(command in expected_cmds for command in hypothesis_cmds):
        return None
    return (
        "solo-headroom hypothesis observable command must match "
        f"{expected_label} verification_commands[].cmd"
    )


def command_contains_expected(actual: str, expected: str) -> bool:
    normalized_actual = " ".join(actual.split())
    normalized_expected = " ".join(expected.split())
    if not normalized_expected:
        return False
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_.:/=-]){re.escape(normalized_expected)}(?![A-Za-z0-9_.:/=-])"
    )
    return bool(pattern.search(normalized_actual))


def validate_risk_probes_cover_solo_headroom_hypothesis(
    probes: list[dict],
    verification_text: str,
) -> str | None:
    hypothesis_cmds = backticked_observable_miss_commands(verification_text)
    if not hypothesis_cmds:
        return None
    if not probes:
        return None
    derived_from = probes[0].get("derived_from")
    if not (
        isinstance(derived_from, str)
        and "solo-headroom hypothesis" in derived_from.lower()
        and any(command_contains_expected(derived_from, hypothesis_cmd) for hypothesis_cmd in hypothesis_cmds)
    ):
        return (
            "risk-probes[0].derived_from must reference the solo-headroom "
            "hypothesis bullet and observable command"
        )
    cmd = probes[0].get("cmd")
    if isinstance(cmd, str) and any(
        command_contains_expected(cmd, hypothesis_cmd)
        for hypothesis_cmd in hypothesis_cmds
    ):
        return None
    return (
        "risk-probes[0].cmd must contain a "
        "solo-headroom hypothesis observable command"
    )


def external_url_hosts(text: str) -> list[str]:
    hosts: list[str] = []
    for match in EXTERNAL_URL_RE.finditer(text or ''):
        host = match.group(1).split('@')[-1].split(':')[0].lower()
        if host not in LOCAL_URL_HOSTS and host not in hosts:
            hosts.append(host)
    return hosts


def validate_shape(data) -> str | None:
    """Return None if shape matches the canonical verification_commands
    schema; else a human-readable error string.

    Schema (iter-0019.8): top-level object with a non-empty
    `verification_commands` list of objects. Each object requires a
    non-empty string `cmd`; `exit_code` defaults to 0 and must be a
    non-bool int; `stdout_contains` and `stdout_not_contains` default to
    empty list and must be lists of strings. Bool is rejected explicitly
    because Python's `bool` subclasses `int` — `isinstance(True, int) is
    True` would otherwise let `exit_code: true` slip through.
    """
    if not isinstance(data, dict):
        return "top-level must be a JSON object"
    cmds = data.get("verification_commands")
    if not isinstance(cmds, list):
        return "verification_commands must be a list"
    if not cmds:
        return "verification_commands must contain at least one entry"
    for i, c in enumerate(cmds):
        if not isinstance(c, dict):
            return f"verification_commands[{i}] must be an object"
        cmd = c.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            return f"verification_commands[{i}].cmd must be a non-empty string"
        ec = c.get("exit_code", 0)
        if isinstance(ec, bool) or not isinstance(ec, int):
            return f"verification_commands[{i}].exit_code must be int (not bool)"
        for k in ("stdout_contains", "stdout_not_contains"):
            v = c.get(k, [])
            if not isinstance(v, list) or not all(isinstance(s, str) for s in v):
                return f"verification_commands[{i}].{k} must be a list of strings"
    return None


def validate_string_list(data: object, key: str) -> str | None:
    value = data.get(key, []) if isinstance(data, dict) else None
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return f"{key} must be a list of non-empty strings"
    return None


def validate_expected_shape(data) -> str | None:
    """Return None if shape matches the sibling spec.expected.json schema.

    Keep this dependency-free: it mirrors `_shared/expected.schema.json` enough
    to catch malformed ideate output before /devlyn:resolve consumes it.
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
    for key in ("required_files", "forbidden_files", "tier_a_waivers", "spec_output_files"):
        err = validate_string_list(data, key)
        if err:
            return err
    max_deps = data.get("max_deps_added", 0)
    if isinstance(max_deps, bool) or not isinstance(max_deps, int) or max_deps < 0:
        return "max_deps_added must be a non-negative integer"
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


def validate_expected_against_sibling_spec(expected_path: Path, data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    spec_path = expected_path.with_name("spec.md")
    if not spec_path.is_file():
        return None
    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return None
    solo_headroom_err = validate_present_solo_headroom_hypothesis(spec_text)
    if solo_headroom_err:
        return solo_headroom_err
    solo_ceiling_err = validate_present_solo_ceiling_avoidance(spec_text)
    if solo_ceiling_err:
        return solo_ceiling_err
    commands = data.get("verification_commands", [])
    solo_headroom_command_err = validate_solo_headroom_commands_against_expected(
        spec_text,
        commands,
        "spec.expected.json",
    )
    if solo_headroom_command_err:
        return solo_headroom_command_err
    if commands:
        return None
    if PURE_DESIGN_ESCAPE in spec_text:
        return None
    return (
        "verification_commands must contain at least one entry unless sibling "
        "spec.md declares all Requirements are pure-design"
    )


def validate_sibling_spec_complexity(expected_path: Path) -> str | None:
    spec_path = expected_path.with_name("spec.md")
    if not spec_path.is_file():
        return None
    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return None
    return validate_present_spec_complexity(spec_text)


def validate_risk_probe(probe: object, index: int, verification_text: str) -> str | None:
    if not isinstance(probe, dict):
        return f"risk-probes[{index}] must be a JSON object"
    probe_id = probe.get("id")
    if not isinstance(probe_id, str) or not probe_id.strip():
        return f"risk-probes[{index}].id must be a non-empty string"
    derived_from = probe.get("derived_from")
    if not isinstance(derived_from, str) or not derived_from.strip():
        return f"risk-probes[{index}].derived_from must be a non-empty string"
    if derived_from not in verification_text:
        return (
            f"risk-probes[{index}].derived_from must be an exact substring "
            "of the source ## Verification section"
        )
    shape_err = validate_shape({"verification_commands": [probe]})
    if shape_err:
        return f"risk-probes[{index}]: {shape_err}"
    cmd = probe.get("cmd", "")
    if FORBIDDEN_RISK_PROBE_CMD_RE.search(cmd):
        return (
            f"risk-probes[{index}].cmd references hidden fixture/verifier paths; "
            "risk probes must derive from visible spec text only"
        )
    external_hosts = external_url_hosts(cmd)
    if external_hosts:
        return (
            f"risk-probes[{index}].cmd references external URL(s): "
            f"{', '.join(external_hosts)}; use only worktree-local or localhost resources"
        )
    if len(cmd) > 4000:
        return f"risk-probes[{index}].cmd exceeds 4000 characters"
    tags = probe.get("tags")
    if not isinstance(tags, list) or not tags or not all(isinstance(t, str) for t in tags):
        return f"risk-probes[{index}].tags must be a non-empty list of strings"
    unknown_tags = sorted(set(tags) - RISK_PROBE_TAGS)
    if unknown_tags:
        return f"risk-probes[{index}].tags contains unknown tag(s): {', '.join(unknown_tags)}"
    if "error_contract" in tags and not re.search(
        r'stderr|exit[ `]*2|(?:prints?|writes?).{0,40}json[ -]?error|'
        r'json[ -]?error.{0,40}(?:stderr|exit)',
        derived_from,
        re.IGNORECASE,
    ):
        return (
            f"risk-probes[{index}].derived_from for error_contract must name "
            "a stderr, JSON-error stream, or exit-2 verification bullet"
        )
    if "http_error_contract" in tags and not (
        re.search(r'\b(?:400|401|403|404|409|422|5[0-9][0-9])\b|http|status', derived_from, re.IGNORECASE)
        and re.search(r'error|invalid', derived_from, re.IGNORECASE)
    ):
        return (
            f"risk-probes[{index}].derived_from for http_error_contract must name "
            "an HTTP/status error response verification bullet"
        )
    evidence = probe.get("tag_evidence")
    if not isinstance(evidence, dict):
        return f"risk-probes[{index}].tag_evidence must be an object"
    for tag in tags:
        required_evidence = RISK_PROBE_REQUIRED_EVIDENCE.get(tag)
        if not required_evidence:
            continue
        actual = evidence.get(tag)
        if not isinstance(actual, list) or not all(isinstance(item, str) for item in actual):
            return f"risk-probes[{index}].tag_evidence.{tag} must be a list of strings"
        missing_evidence = sorted(required_evidence - set(actual))
        if missing_evidence:
            return (
                f"risk-probes[{index}].tag_evidence.{tag} missing required "
                f"item(s): {', '.join(missing_evidence)}"
            )
    if "shape_contract" in tags and shape_contract_requires_evidence(derived_from):
        actual = evidence.get("shape_contract")
        if not isinstance(actual, list) or not all(isinstance(item, str) for item in actual):
            return f"risk-probes[{index}].tag_evidence.shape_contract must be a list of strings"
        required_shape = set(SHAPE_CONTRACT_REQUIRED_EVIDENCE)
        if re.search(r'error object|error body', derived_from, re.IGNORECASE) or (
            INLINE_JSON_OBJECT_RE.search(derived_from)
            and re.search(r'error|invalid', derived_from, re.IGNORECASE)
        ):
            required_shape.add("asserts_exact_error_object")
        missing_shape = sorted(required_shape - set(actual))
        if missing_shape:
            return (
                f"risk-probes[{index}].tag_evidence.shape_contract missing required "
                f"item(s): {', '.join(missing_shape)}"
            )
    return None


def shape_contract_requires_evidence(text: str) -> bool:
    return bool(re.search(
        r'\b(?:keys?|fields?|rows?|shape|object|json[ -]?object|'
        r'error body|stdout|stderr|response body)\b|'
        r'\b(?:applied|rejected|accounts|scheduled|accepted|remaining)\b',
        text,
        re.IGNORECASE,
    ) or INLINE_JSON_OBJECT_RE.search(text))


def required_risk_probe_tags(verification_text: str) -> set[str]:
    text = verification_text.lower()
    required: set[str] = set()
    if re.search(r'priority|higher-priority|ordered by|ordering|appears first|input order', text):
        required.add("ordering_inversion")
    if re.search(r'blocked|overlap|forbidden[ -]+window', text):
        required.add("boundary_overlap")
    if re.search(r'rolls? back|rollback|all-or-nothing|tentative', text):
        required.add("rollback_state")
    if re.search(
        r'rolls? back|rollback|all-or-nothing|tentative|reduce[s]? stock|'
        r'available to later|later orders|remaining|'
        r'(?:stock|inventory|balance|availability).{0,80}(?:later|remaining|after failures)',
        text,
    ):
        required.add("prior_consumption")
    if "remaining" in text:
        required.add("positive_remaining")
    if re.search(
        r'stderr|exit[ `]*2|(?:prints?|writes?).{0,40}json[ -]?error|'
        r'json[ -]?error.{0,40}(?:stderr|exit)',
        text,
    ):
        required.add("error_contract")
    if re.search(
        r'\b(?:400|401|403|404|409|422|5[0-9][0-9])\b|http status|status code',
        text,
    ) and re.search(r'json error|error object|error body|invalid_query|error.*field', text):
        required.add("http_error_contract")
    if re.search(
        r'\b(?:keys?|fields?|rows?|shape|json[ -]?object|'
        r'error object|error body|response body)\b|'
        r'\b(?:applied|rejected|accounts|scheduled|accepted|remaining)\b',
        text,
    ) or INLINE_JSON_OBJECT_RE.search(verification_text):
        required.add("shape_contract")
    if re.search(r'stderr|stdout|exit `?2`?', text):
        required.add("stdout_stderr_contract")
    if re.search(r'signature|signing|signed|x-signature|hmac|raw[ -]?body|timingsafeequal', text):
        required.add("auth_signature_contract")
    if re.search(
        r'replay|same.{0,40}`?id`?|already-seen|idempotent|re-delivery|'
        r'duplicate[ -]+(?:delivery|event|id)',
        text,
    ):
        required.add("idempotency_replay")
    if re.search(
        r'concurrent|close together|simultaneous|parallel|race|lost update|'
        r'many at once|several .{0,40}requests',
        text,
    ):
        required.add("concurrent_state_consistency")
    if re.search(
        r'one valid \+ one invalid|valid \+ one invalid|all-or-nothing|'
        r'same list as before|0 inserts|no partial updates',
        text,
    ):
        required.add("atomic_batch_state")
    return required


def load_risk_probes(
    devlyn_dir: Path,
    source_md: Path | None,
    *,
    require_present: bool = False,
) -> tuple[list[dict], str | None]:
    probes_path = devlyn_dir / "risk-probes.jsonl"
    if not probes_path.is_file():
        if require_present:
            return ([], "risk-probes.jsonl is required when --risk-probes is enabled")
        return ([], None)
    if source_md is None or not source_md.is_file():
        return ([], "risk-probes.jsonl exists but source markdown is unavailable")

    verification_text = extract_verification_text(source_md.read_text())
    if not verification_text:
        return ([], "risk-probes.jsonl exists but source has no ## Verification section")

    probes: list[dict] = []
    for index, line in enumerate(probes_path.read_text().splitlines()):
        if not line.strip():
            continue
        try:
            probe = loads_strict_json(line)
        except ValueError as e:
            return ([], f"risk-probes[{index}] invalid JSON: {e}")
        err = validate_risk_probe(probe, index, verification_text)
        if err:
            return ([], err)
        normalized = dict(probe)
        normalized["_risk_probe"] = True
        normalized["_risk_probe_index"] = index
        probes.append(normalized)
        if len(probes) > 3:
            return ([], "risk-probes.jsonl has more than 3 probes")
    if require_present and not probes:
        return ([], "risk-probes.jsonl must contain at least one probe")
    if require_present:
        present_tags = {tag for probe in probes for tag in probe.get("tags", [])}
        missing_tags = sorted(required_risk_probe_tags(verification_text) - present_tags)
        if missing_tags:
            return ([], f"risk-probes.jsonl missing required probe tag(s): {', '.join(missing_tags)}")
    solo_headroom_probe_err = validate_risk_probes_cover_solo_headroom_hypothesis(
        probes,
        verification_text,
    )
    if solo_headroom_probe_err:
        return ([], solo_headroom_probe_err)
    return (probes, None)


def read_source(work: Path, devlyn_dir: Path) -> tuple[str | None, Path | None]:
    """Return (source_type, markdown_path) from .devlyn/pipeline.state.json,
    or (None, None) if state is absent/unreadable. The markdown path is
    resolved against `work` when relative.
    """
    state_path = devlyn_dir / "pipeline.state.json"
    if not state_path.is_file():
        return (None, None)
    try:
        state = loads_strict_json(state_path.read_text())
    except (ValueError, OSError):
        return (None, None)
    src = state.get("source") or {}
    src_type = src.get("type")
    if src_type == "spec":
        md_path = src.get("spec_path")
    elif src_type == "generated":
        md_path = src.get("criteria_path")
    else:
        md_path = None
    if not md_path:
        return (src_type, None)
    md = Path(md_path)
    if not md.is_absolute():
        md = work / md
    return (src_type, md if md.is_file() else None)


def read_state(devlyn_dir: Path) -> dict:
    state_path = devlyn_dir / "pipeline.state.json"
    if not state_path.is_file():
        return {}
    try:
        data = loads_strict_json(state_path.read_text())
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def state_requires_risk_probes(state: dict) -> bool:
    risk_profile = state.get("risk_profile")
    return isinstance(risk_profile, dict) and risk_profile.get("risk_probes_enabled") is True


def risk_probes_state_error(state: dict) -> str | None:
    if "risk_profile" not in state:
        return None
    risk_profile = state.get("risk_profile")
    if not isinstance(risk_profile, dict):
        return "pipeline.state.json risk_profile must be an object"
    if "risk_probes_enabled" not in risk_profile:
        return None
    if not isinstance(risk_profile.get("risk_probes_enabled"), bool):
        return "pipeline.state.json risk_profile.risk_probes_enabled must be boolean"
    return None


def source_integrity_error(src_type: str | None, state: dict, source_md: Path | None) -> str | None:
    if source_md is None:
        return None
    src = state.get("source") if isinstance(state.get("source"), dict) else {}
    if src_type == "generated":
        field = "criteria_sha256"
        required = True
    elif src_type == "spec":
        field = "spec_sha256"
        required = False
    else:
        return None
    expected = src.get(field)
    qualified = f"source.{field}"
    if not isinstance(expected, str) or not expected:
        if required:
            return f"{qualified} is required for generated criteria source integrity."
        return None
    try:
        actual = hashlib.sha256(source_md.read_bytes()).hexdigest()
    except OSError as exc:
        return f"could not read {source_md} for source integrity check: {exc}"
    if expected != actual:
        return f"{qualified} mismatch for {source_md}: expected {expected}, actual {actual}."
    return None


def load_expected_contract(expected_path: Path) -> tuple[dict | None, str | None]:
    try:
        data = loads_strict_json(expected_path.read_text())
    except ValueError as e:
        return (None, f"{expected_path} has invalid JSON: {e}")
    except OSError as e:
        return (None, f"{expected_path} is unreadable: {e}")
    err = validate_expected_shape(data)
    if err:
        return (None, f"{expected_path}: {err}")
    return (data, None)


def stage_from_source(md: Path, devlyn_dir: Path) -> tuple[bool, str | None]:
    """Materialize .devlyn/spec-verify.json from the json block in `md`.

    Returns (staged, error). staged=True → wrote spec-verify.json. error
    non-None → carrier was found but malformed (caller emits CRITICAL).
    staged=False, error=None → no json block in the source (handwritten
    spec or generated source missing the contract).
    """
    block = extract_verification_block(md.read_text())
    if block is None:
        return (False, None)
    try:
        data = loads_strict_json(block)
    except ValueError as e:
        return (False, f"`## Verification` ```json``` block in {md} has invalid JSON: {e}")
    err = validate_shape(data)
    if err:
        return (False, f"`## Verification` ```json``` block in {md}: {err}")
    normalized = {"verification_commands": data["verification_commands"]}
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / "spec-verify.json").write_text(json.dumps(normalized, indent=2) + "\n")
    return (True, None)


def stage_from_expected(
    md: Path,
    devlyn_dir: Path,
) -> tuple[bool, bool, str | None, Path, dict | None]:
    """Materialize .devlyn/spec-verify.json from sibling spec.expected.json.

    Returns (found, staged, error, expected_path, expected_data).
    - found=False: no sibling file; caller may fall back to legacy inline carrier.
    - found=True, error: sibling exists but is malformed; caller must fail closed.
    - found=True, staged=False: valid pure-design contract with no commands.
    - found=True, staged=True: wrote verification_commands into spec-verify.json.
    """
    expected_path = md.with_name("spec.expected.json")
    if not expected_path.is_file():
        return (False, False, None, expected_path, None)
    data, err = load_expected_contract(expected_path)
    if err:
        return (True, False, err, expected_path, None)
    assert data is not None
    commands = data.get("verification_commands")
    if not commands:
        spec_path = devlyn_dir / "spec-verify.json"
        if spec_path.exists():
            spec_path.unlink()
        return (True, False, None, expected_path, data)
    normalized = {"verification_commands": commands}
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / "spec-verify.json").write_text(json.dumps(normalized, indent=2) + "\n")
    return (True, True, None, expected_path, data)


def write_malformed_finding(devlyn_dir: Path, error: str, source_path: Path | None) -> None:
    """Emit a single CRITICAL finding for a malformed verification carrier."""
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    findings_path = devlyn_dir / output_findings_name()
    file_ref = str(source_path) if source_path else ".devlyn/pipeline.state.json"
    finding = {
        "id": f"{output_finding_prefix()}-0001",
        "rule_id": "correctness.spec-verify-malformed",
        "level": "error",
        "severity": "CRITICAL",
        "confidence": 1.0,
        "message": f"Verification contract carrier is malformed: {error}",
        "file": file_ref,
        "line": 1,
        "phase": output_phase(),
        "criterion_ref": "spec-verify://carrier",
        "fix_hint": (
            "Fix the sibling `spec.expected.json` file or the `## Verification` "
            "```json``` block: a JSON object with a non-empty `verification_commands` array of "
            "{cmd, exit_code?, stdout_contains?, stdout_not_contains?} "
            "entries. See references/build-gate.md § 'Spec literal check'."
        ),
        "blocking": True,
        "status": "open",
    }
    with findings_path.open("w") as fh:
        fh.write(json.dumps(finding) + "\n")


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


def diff_text_for_expected(work: Path, devlyn_dir: Path, state: dict) -> tuple[str, str | None]:
    external_diff = devlyn_dir / "external-diff.patch"
    if external_diff.is_file():
        try:
            return (external_diff.read_text(), None)
        except OSError as e:
            return ("", f"cannot read {external_diff}: {e}")
    base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
    cmd = ["git", "diff"]
    if base_sha:
        cmd.append(base_sha)
    proc = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
    if proc.returncode != 0:
        return ("", (proc.stderr or proc.stdout or "git diff failed").strip())
    return (proc.stdout or "", None)


def count_deps_added(work: Path, state: dict) -> int:
    base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
    cmd = ["git", "diff"]
    if base_sha:
        cmd.append(base_sha)
    cmd.extend(["--", "package.json"])
    proc = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
    if proc.returncode != 0:
        return 0
    in_deps = False
    count = 0
    for line in (proc.stdout or "").splitlines():
        if line.startswith(("diff ", "index ", "---", "+++", "@@")):
            continue
        marker = line[:1]
        content = line[1:] if marker in {"+", "-", " "} else line
        if '"dependencies"' in content or '"devDependencies"' in content:
            in_deps = True
        elif content.strip().startswith("}"):
            in_deps = False
        elif in_deps and marker == "+":
            if re.search(r'"[^"]+"\s*:\s*"[^"]+"', content):
                count += 1
    return count


def changed_files(work: Path, state: dict, devlyn_dir: Path) -> list[str]:
    external_diff = devlyn_dir / "external-diff.patch"
    if external_diff.is_file():
        names: list[str] = []
        try:
            external_text = external_diff.read_text()
        except OSError:
            return []
        for line in external_text.splitlines():
            if line.startswith("diff --git "):
                parts = line.split()
                if len(parts) >= 4:
                    names.append(parts[3].removeprefix("b/"))
        return names
    base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
    cmd = ["git", "diff", "--name-only"]
    if base_sha:
        cmd.append(base_sha)
    proc = subprocess.run(cmd, cwd=str(work), capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]


def expected_contract_findings(
    expected_data: dict | None,
    expected_path: Path | None,
    work: Path,
    devlyn_dir: Path,
    state: dict,
    finding_start: int,
) -> tuple[list[dict], int]:
    if not expected_data:
        return ([], finding_start)
    findings: list[dict] = []
    seq = finding_start
    diff_text, diff_error = diff_text_for_expected(work, devlyn_dir, state)
    if diff_error and (
        expected_data.get("forbidden_patterns") or expected_data.get("forbidden_files")
    ):
        findings.append({
            "id": f"{output_finding_prefix()}-{seq:04d}",
            "rule_id": "correctness.expected-contract-unverifiable",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Cannot compute diff for forbidden_patterns: {diff_error}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": output_phase(),
            "criterion_ref": "spec.expected.json/forbidden_patterns",
            "fix_hint": "Ensure pipeline.state.json has base_ref.sha or provide .devlyn/external-diff.patch.",
            "blocking": True,
            "status": "open",
        })
        seq += 1
    for i, pattern in enumerate(expected_data.get("forbidden_patterns", []) or []):
        scope = slice_diff_to_files(diff_text, pattern.get("files") or [])
        if not re.search(pattern["pattern"], scope):
            continue
        is_disqualifier = pattern.get("severity") == "disqualifier"
        findings.append({
            "id": f"{output_finding_prefix()}-{seq:04d}",
            "rule_id": "correctness.forbidden-pattern",
            "level": "error" if is_disqualifier else "warning",
            "severity": "CRITICAL" if is_disqualifier else "MEDIUM",
            "confidence": 1.0,
            "message": pattern.get("description") or f"Forbidden pattern matched: {pattern['pattern']}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": output_phase(),
            "criterion_ref": f"spec.expected.json/forbidden_patterns/{i}",
            "fix_hint": "Remove the forbidden diff pattern or change the spec.expected.json contract explicitly.",
            "blocking": is_disqualifier,
            "status": "open",
        })
        seq += 1
    changed = set(changed_files(work, state, devlyn_dir))
    for i, required in enumerate(expected_data.get("required_files", []) or []):
        if (work / required).exists():
            continue
        findings.append({
            "id": f"{output_finding_prefix()}-{seq:04d}",
            "rule_id": "correctness.required-file-missing",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Required file is missing: {required}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": output_phase(),
            "criterion_ref": f"spec.expected.json/required_files/{i}",
            "fix_hint": "Create the required file or remove it from the expected contract.",
            "blocking": True,
            "status": "open",
        })
        seq += 1
    for i, forbidden in enumerate(expected_data.get("forbidden_files", []) or []):
        if forbidden not in changed:
            continue
        findings.append({
            "id": f"{output_finding_prefix()}-{seq:04d}",
            "rule_id": "scope.forbidden-file-touched",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Forbidden file appears in the diff: {forbidden}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": output_phase(),
            "criterion_ref": f"spec.expected.json/forbidden_files/{i}",
            "fix_hint": "Remove that file from the diff or update the expected contract.",
            "blocking": True,
            "status": "open",
        })
        seq += 1
    max_deps = expected_data.get("max_deps_added", 0)
    deps_added = count_deps_added(work, state)
    if deps_added > max_deps:
        findings.append({
            "id": f"{output_finding_prefix()}-{seq:04d}",
            "rule_id": "scope.max-deps-added-exceeded",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Added {deps_added} package dependencies; max_deps_added is {max_deps}.",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": output_phase(),
            "criterion_ref": "spec.expected.json/max_deps_added",
            "fix_hint": "Remove the new dependency or explicitly license it in spec.expected.json.",
            "blocking": True,
            "status": "open",
        })
        seq += 1
    return (findings, seq)


def run_check_mode(md_path: Path) -> int:
    """`--check <markdown>` — validate the verification carrier without
    running any commands. Used by /devlyn:ideate after item-spec write.

    Exit 0: section absent OR section present and well-formed.
    Exit 2: section present but malformed (so ideate can re-prompt).
    """
    if not md_path.is_file():
        print(f"[spec-verify --check] error: {md_path} not found", file=sys.stderr)
        return 2
    text = md_path.read_text()
    frontmatter_err = validate_present_spec_complexity(text)
    if frontmatter_err:
        print(f"[spec-verify --check] {md_path}: {frontmatter_err}", file=sys.stderr)
        return 2
    solo_headroom_err = validate_present_solo_headroom_hypothesis(text)
    if solo_headroom_err:
        print(f"[spec-verify --check] {md_path}: {solo_headroom_err}", file=sys.stderr)
        return 2
    solo_ceiling_err = validate_present_solo_ceiling_avoidance(text)
    if solo_ceiling_err:
        print(f"[spec-verify --check] {md_path}: {solo_ceiling_err}", file=sys.stderr)
        return 2
    block = extract_verification_block(text)
    if block is None:
        # Section absent or no json block — opt-in nature preserved for
        # ideate (a spec without machine verification is still valid; it
        # just won't activate the BUILD_GATE gate).
        return 0
    try:
        data = loads_strict_json(block)
    except ValueError as e:
        print(
            f"[spec-verify --check] {md_path}: invalid JSON in `## Verification` "
            f"```json``` block: {e}",
            file=sys.stderr,
        )
        return 2
    err = validate_shape(data)
    if err:
        print(f"[spec-verify --check] {md_path}: shape error: {err}", file=sys.stderr)
        return 2
    solo_headroom_command_err = validate_solo_headroom_commands_against_expected(
        text,
        data.get("verification_commands", []),
        "`## Verification` JSON carrier",
    )
    if solo_headroom_command_err:
        print(f"[spec-verify --check] {md_path}: {solo_headroom_command_err}", file=sys.stderr)
        return 2
    return 0


def run_check_expected_mode(expected_path: Path) -> int:
    if not expected_path.is_file():
        print(f"[spec-verify --check-expected] error: {expected_path} not found", file=sys.stderr)
        return 2
    _data, err = load_expected_contract(expected_path)
    if err:
        print(f"[spec-verify --check-expected] {expected_path}: shape error: {err}", file=sys.stderr)
        return 2
    complexity_err = validate_sibling_spec_complexity(expected_path)
    if complexity_err:
        print(f"[spec-verify --check-expected] {expected_path}: shape error: {complexity_err}", file=sys.stderr)
        return 2
    sibling_err = validate_expected_against_sibling_spec(expected_path, _data)
    if sibling_err:
        print(f"[spec-verify --check-expected] {expected_path}: shape error: {sibling_err}", file=sys.stderr)
        return 2
    return 0


def run_self_test() -> int:
    script_path = str(Path(__file__).resolve())
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        devlyn = work / ".devlyn"
        devlyn.mkdir()
        spec_md = work / "spec.md"
        spec_md.write_text("# Spec\n\n## Verification\n\n- probe must pass visible marker.\n")
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)}
        }))
        (devlyn / "spec-verify.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf ok", "exit_code": 0, "stdout_contains": ["ok"]}
            ]
        }) + "\n")
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P1",
            "derived_from": "probe must pass visible marker.",
            "cmd": "printf probe-ok",
            "exit_code": 0,
            "stdout_contains": ["probe-ok"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        env = os.environ.copy()
        env["BENCH_WORKDIR"] = str(work)
        good = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if good.returncode != 0:
            print(good.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").unlink()
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": True},
        }))
        missing_required_probe = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if missing_required_probe.returncode == 0:
            print("--include-risk-probes accepted missing required risk-probes.jsonl", file=sys.stderr)
            return 1
        if "risk-probes.jsonl is required when --risk-probes is enabled" not in missing_required_probe.stderr:
            print("--include-risk-probes missing required probe had the wrong error", file=sys.stderr)
            print(missing_required_probe.stderr, file=sys.stderr)
            return 1

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": False},
        }))
        missing_optional_probe = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if missing_optional_probe.returncode != 0:
            print("--include-risk-probes rejected optional missing risk-probes.jsonl", file=sys.stderr)
            print(missing_optional_probe.stderr, file=sys.stderr)
            return 1

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": "true"},
        }))
        malformed_risk_probe_state = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if malformed_risk_probe_state.returncode == 0:
            print("--include-risk-probes accepted non-boolean risk_probes_enabled", file=sys.stderr)
            return 1
        if "risk_profile.risk_probes_enabled must be boolean" not in malformed_risk_probe_state.stderr:
            print("--include-risk-probes malformed risk_probes_enabled had the wrong error", file=sys.stderr)
            print(malformed_risk_probe_state.stderr, file=sys.stderr)
            return 1

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": "enabled",
        }))
        malformed_risk_profile = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if malformed_risk_profile.returncode == 0:
            print("--include-risk-probes accepted non-object risk_profile", file=sys.stderr)
            return 1
        if "risk_profile must be an object" not in malformed_risk_profile.stderr:
            print("--include-risk-probes malformed risk_profile had the wrong error", file=sys.stderr)
            print(malformed_risk_profile.stderr, file=sys.stderr)
            return 1

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)}
        }))
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P1",
            "derived_from": "probe must pass visible marker.",
            "cmd": "printf probe-ok",
            "exit_code": 0,
            "stdout_contains": ["probe-ok"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")

        good_complexity = work / "good-complexity.md"
        good_complexity.write_text(
            "---\nid: good\ncomplexity: large\n---\n\n# Good\n\n## Verification\n\n- ok\n",
            encoding="utf-8",
        )
        good_complexity_check = subprocess.run(
            [sys.executable, script_path, "--check", str(good_complexity)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if good_complexity_check.returncode != 0:
            print(good_complexity_check.stderr, file=sys.stderr)
            return 1

        bad_complexity = work / "bad-complexity.md"
        bad_complexity.write_text(
            "---\nid: bad\ncomplexity: hihg\n---\n\n# Bad\n\n## Verification\n\n- ok\n",
            encoding="utf-8",
        )
        bad_complexity_check = subprocess.run(
            [sys.executable, script_path, "--check", str(bad_complexity)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if bad_complexity_check.returncode == 0:
            print("unsupported spec complexity was accepted", file=sys.stderr)
            return 1
        if "frontmatter complexity must be one of" not in bad_complexity_check.stderr:
            print("unsupported spec complexity did not report the allowed values", file=sys.stderr)
            print(bad_complexity_check.stderr, file=sys.stderr)
            return 1

        weak_solo_headroom = work / "weak-solo-headroom.md"
        weak_solo_headroom.write_text(
            "# Weak\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling.\n"
            "- Observable command: `node check.js` exposes behavior.\n",
            encoding="utf-8",
        )
        weak_solo_check = subprocess.run(
            [sys.executable, script_path, "--check", str(weak_solo_headroom)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if weak_solo_check.returncode == 0:
            print("weak solo-headroom hypothesis was accepted by --check", file=sys.stderr)
            return 1
        if "backticked command/observable line that exposes the miss" not in weak_solo_check.stderr:
            print("--check did not report weak solo-headroom hypothesis", file=sys.stderr)
            print(weak_solo_check.stderr, file=sys.stderr)
            return 1

        weak_descriptive_backtick = work / "weak-descriptive-backtick.md"
        weak_descriptive_backtick.write_text(
            "# Weak descriptive backtick\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss behavior where observable `priority rollback` exposes the miss.\n",
            encoding="utf-8",
        )
        weak_descriptive_check = subprocess.run(
            [sys.executable, script_path, "--check", str(weak_descriptive_backtick)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if weak_descriptive_check.returncode == 0:
            print("descriptive backtick solo-headroom hypothesis was accepted by --check", file=sys.stderr)
            return 1

        strong_solo_headroom = work / "strong-solo-headroom.md"
        strong_solo_headroom.write_text(
            "# Strong\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling exposed by `node check.js`.\n",
            encoding="utf-8",
        )
        strong_solo_check = subprocess.run(
            [sys.executable, script_path, "--check", str(strong_solo_headroom)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if strong_solo_check.returncode != 0:
            print("actionable solo-headroom hypothesis was rejected by --check", file=sys.stderr)
            print(strong_solo_check.stderr, file=sys.stderr)
            return 1

        docs_style_solo_headroom = work / "docs-style-solo-headroom.md"
        docs_style_solo_headroom.write_text(
            "# Docs style\n\n## Verification\n\n"
            "- Solo-headroom hypothesis: the spec must literally contain `solo_claude`, `miss`, and an observable command; "
            "`node check.js` exposes the miss.\n",
            encoding="utf-8",
        )
        docs_style_solo_check = subprocess.run(
            [sys.executable, script_path, "--check", str(docs_style_solo_headroom)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if docs_style_solo_check.returncode != 0:
            print("docs-style solo-headroom hypothesis was rejected by --check", file=sys.stderr)
            print(docs_style_solo_check.stderr, file=sys.stderr)
            return 1

        weak_solo_ceiling = work / "weak-solo-ceiling.md"
        weak_solo_ceiling.write_text(
            "# Weak ceiling\n\n## Verification\n\n"
            "- solo ceiling avoidance: this is not like the previous ones.\n",
            encoding="utf-8",
        )
        weak_solo_ceiling_check = subprocess.run(
            [sys.executable, script_path, "--check", str(weak_solo_ceiling)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if weak_solo_ceiling_check.returncode == 0:
            print("weak solo ceiling avoidance was accepted by --check", file=sys.stderr)
            return 1
        if "concrete difference from rejected or solo-saturated controls" not in weak_solo_ceiling_check.stderr:
            print("--check did not report weak solo ceiling avoidance", file=sys.stderr)
            print(weak_solo_ceiling_check.stderr, file=sys.stderr)
            return 1

        strong_solo_ceiling = work / "strong-solo-ceiling.md"
        strong_solo_ceiling.write_text(
            "# Strong ceiling\n\n## Verification\n\n"
            "- solo ceiling avoidance: unlike solo-saturated `S2`-`S6`, this uses a cross-run "
            "state leak because solo_claude headroom should be preserved.\n",
            encoding="utf-8",
        )
        strong_solo_ceiling_check = subprocess.run(
            [sys.executable, script_path, "--check", str(strong_solo_ceiling)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if strong_solo_ceiling_check.returncode != 0:
            print("actionable solo ceiling avoidance was rejected by --check", file=sys.stderr)
            print(strong_solo_ceiling_check.stderr, file=sys.stderr)
            return 1

        inline_mismatched_solo = work / "inline-mismatched-solo.md"
        inline_mismatched_solo.write_text(
            "# Inline mismatch\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling; "
            "`node check.js` exposes the miss.\n\n"
            "```json\n"
            + json.dumps({"verification_commands": [{"cmd": "printf ok"}]})
            + "\n```\n",
            encoding="utf-8",
        )
        inline_mismatched_check = subprocess.run(
            [sys.executable, script_path, "--check", str(inline_mismatched_solo)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if inline_mismatched_check.returncode == 0:
            print("mismatched inline solo-headroom command was accepted by --check", file=sys.stderr)
            return 1
        if "observable command must match `## Verification` JSON carrier" not in inline_mismatched_check.stderr:
            print("--check did not report mismatched inline solo-headroom command", file=sys.stderr)
            print(inline_mismatched_check.stderr, file=sys.stderr)
            return 1

        inline_matched_solo = work / "inline-matched-solo.md"
        inline_matched_solo.write_text(
            "# Inline match\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling; "
            "`printf ok` exposes the miss.\n\n"
            "```json\n"
            + json.dumps({"verification_commands": [{"cmd": "printf ok"}]})
            + "\n```\n",
            encoding="utf-8",
        )
        inline_matched_check = subprocess.run(
            [sys.executable, script_path, "--check", str(inline_matched_solo)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if inline_matched_check.returncode != 0:
            print("matched inline solo-headroom command was rejected by --check", file=sys.stderr)
            print(inline_matched_check.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P2",
            "derived_from": "probe must pass visible marker.",
            "cmd": "node $BENCH_FIXTURE_DIR/verifiers/hidden.js",
            "exit_code": 0,
        }) + "\n")
        bad = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if bad.returncode == 0:
            print("hidden verifier path was accepted", file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text('{"id":NaN}\n')
        bad_probe_nan = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if bad_probe_nan.returncode == 0:
            print("NaN risk-probes JSONL was accepted", file=sys.stderr)
            return 1
        if "invalid JSON numeric constant: NaN" not in bad_probe_nan.stderr:
            print("NaN risk-probes JSONL did not report invalid numeric constant", file=sys.stderr)
            print(bad_probe_nan.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P3",
            "derived_from": "probe must pass visible marker.",
            "cmd": "printf bad-error-derived-from",
            "exit_code": 0,
            "tags": ["error_contract"],
            "tag_evidence": {"error_contract": []},
        }) + "\n")
        bad_error_ref = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if bad_error_ref.returncode == 0:
            print("error_contract with unrelated derived_from was accepted", file=sys.stderr)
            return 1

        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling; "
            "`printf ok` exposes the miss.\n"
            "- probe must pass visible marker.\n",
            encoding="utf-8",
        )
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P4",
            "derived_from": "solo-headroom hypothesis: solo_claude should miss duplicate handling; `printf ok` exposes the miss.",
            "cmd": "printf unrelated",
            "exit_code": 0,
            "stdout_contains": ["unrelated"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        bad_solo_headroom_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if bad_solo_headroom_probe.returncode == 0:
            print("risk probe missing solo-headroom command coverage was accepted", file=sys.stderr)
            return 1
        if "risk-probes[0].cmd must contain a solo-headroom hypothesis observable command" not in bad_solo_headroom_probe.stderr:
            print("solo-headroom risk-probe coverage failure had the wrong error", file=sys.stderr)
            print(bad_solo_headroom_probe.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P4a",
            "derived_from": "probe must pass visible marker.",
            "cmd": "bash -lc 'printf ok'",
            "exit_code": 0,
            "stdout_contains": ["ok"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        bad_solo_headroom_derived_from = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if bad_solo_headroom_derived_from.returncode == 0:
            print("risk probe with unrelated solo-headroom derived_from was accepted", file=sys.stderr)
            return 1
        if "risk-probes[0].derived_from must reference the solo-headroom hypothesis bullet" not in bad_solo_headroom_derived_from.stderr:
            print("solo-headroom risk-probe derived_from failure had the wrong error", file=sys.stderr)
            print(bad_solo_headroom_derived_from.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(
            json.dumps({
                "id": "P5a",
                "derived_from": "solo-headroom hypothesis: solo_claude should miss duplicate handling; `printf ok` exposes the miss.",
                "cmd": "printf first-unrelated",
                "exit_code": 0,
                "stdout_contains": ["first-unrelated"],
                "stdout_not_contains": [],
                "tags": ["shape_contract"],
                "tag_evidence": {},
            }) + "\n" + json.dumps({
                "id": "P5b",
                "derived_from": "probe must pass visible marker.",
                "cmd": "bash -lc 'printf ok'",
                "exit_code": 0,
                "stdout_contains": ["ok"],
                "stdout_not_contains": [],
                "tags": ["shape_contract"],
                "tag_evidence": {},
            }) + "\n"
        )
        late_solo_headroom_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if late_solo_headroom_probe.returncode == 0:
            print("solo-headroom command in a later risk probe was accepted", file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P5c",
            "derived_from": "solo-headroom hypothesis: solo_claude should miss duplicate handling; `printf ok` exposes the miss.",
            "cmd": "printf ok2",
            "exit_code": 0,
            "stdout_contains": ["ok2"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        prefix_solo_headroom_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if prefix_solo_headroom_probe.returncode == 0:
            print("solo-headroom command prefix match was accepted", file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P5",
            "derived_from": "solo-headroom hypothesis: solo_claude should miss duplicate handling; `printf ok` exposes the miss.",
            "cmd": "bash -lc 'printf ok'",
            "exit_code": 0,
            "stdout_contains": ["ok"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        good_solo_headroom_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if good_solo_headroom_probe.returncode != 0:
            print("risk probe covering solo-headroom command was rejected", file=sys.stderr)
            print(good_solo_headroom_probe.stderr, file=sys.stderr)
            return 1

        expected_json = work / "spec.expected.json"
        expected_json.write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf ok", "exit_code": 0, "stdout_contains": ["ok"]}
            ],
            "forbidden_patterns": [
                {
                    "pattern": "catch\\s*\\{\\s*\\}",
                    "description": "silent catch hides failures",
                    "severity": "disqualifier",
                }
            ],
            "required_files": ["bin/cli.js"],
            "forbidden_files": [],
            "max_deps_added": 0,
        }) + "\n")
        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling.\n"
            "- Observable command: `node check.js` exposes behavior.\n"
        )
        weak_sibling_solo = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if weak_sibling_solo.returncode == 0:
            print("weak sibling solo-headroom hypothesis was accepted by --check-expected", file=sys.stderr)
            return 1
        if "backticked command/observable line that exposes the miss" not in weak_sibling_solo.stderr:
            print("--check-expected did not report weak sibling solo-headroom hypothesis", file=sys.stderr)
            print(weak_sibling_solo.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling; "
            "`node check.js` exposes the miss.\n",
            encoding="utf-8",
        )
        mismatched_sibling_solo = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if mismatched_sibling_solo.returncode == 0:
            print("mismatched sibling solo-headroom command was accepted by --check-expected", file=sys.stderr)
            return 1
        if "observable command must match spec.expected.json" not in mismatched_sibling_solo.stderr:
            print("--check-expected did not report mismatched sibling solo-headroom command", file=sys.stderr)
            print(mismatched_sibling_solo.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- solo-headroom hypothesis: solo_claude should miss duplicate handling; "
            "`printf ok` exposes the miss.\n",
            encoding="utf-8",
        )
        matched_sibling_solo = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if matched_sibling_solo.returncode != 0:
            print("matched sibling solo-headroom command was rejected by --check-expected", file=sys.stderr)
            print(matched_sibling_solo.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- Solo-headroom hypothesis: the spec must literally contain `solo_claude`, `miss`, and an observable command; "
            "`printf ok` exposes the miss.\n",
            encoding="utf-8",
        )
        docs_style_sibling_solo = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if docs_style_sibling_solo.returncode != 0:
            print("docs-style sibling solo-headroom command was rejected by --check-expected", file=sys.stderr)
            print(docs_style_sibling_solo.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- solo ceiling avoidance: this differs from controls but omits the required baseline.\n",
            encoding="utf-8",
        )
        weak_sibling_solo_ceiling = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if weak_sibling_solo_ceiling.returncode == 0:
            print("weak sibling solo ceiling avoidance was accepted by --check-expected", file=sys.stderr)
            return 1
        if "concrete difference from rejected or solo-saturated controls" not in weak_sibling_solo_ceiling.stderr:
            print("--check-expected did not report weak sibling solo ceiling avoidance", file=sys.stderr)
            print(weak_sibling_solo_ceiling.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "# Spec\n\n## Verification\n\n"
            "- solo ceiling avoidance: unlike solo-saturated `S2`-`S6`, this includes a "
            "multi-run temporal dependency because solo_claude headroom should remain.\n",
            encoding="utf-8",
        )
        strong_sibling_solo_ceiling = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if strong_sibling_solo_ceiling.returncode != 0:
            print("actionable sibling solo ceiling avoidance was rejected by --check-expected", file=sys.stderr)
            print(strong_sibling_solo_ceiling.stderr, file=sys.stderr)
            return 1

        spec_md.write_text("# Spec\n\n## Verification\n\n- probe must pass visible marker.\n")
        expected_good = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_good.returncode != 0:
            print(expected_good.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "---\nid: bad-sibling\ncomplexity: hihg\n---\n\n# Bad sibling\n\n## Verification\n\n- ok\n",
            encoding="utf-8",
        )
        expected_bad_sibling_complexity = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_bad_sibling_complexity.returncode == 0:
            print("unsupported sibling spec complexity was accepted by --check-expected", file=sys.stderr)
            return 1
        if "frontmatter complexity must be one of" not in expected_bad_sibling_complexity.stderr:
            print("--check-expected did not report unsupported sibling spec complexity", file=sys.stderr)
            print(expected_bad_sibling_complexity.stderr, file=sys.stderr)
            return 1
        spec_md.write_text("# Spec\n\n## Verification\n\n- probe must pass visible marker.\n")

        expected_json.write_text(json.dumps({"verification_commands": []}) + "\n")
        expected_empty_runtime = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_empty_runtime.returncode == 0:
            print("empty verification_commands should fail for runtime specs", file=sys.stderr)
            return 1

        pure_root = work / "pure-design"
        pure_root.mkdir()
        pure_spec = pure_root / "spec.md"
        pure_spec.write_text(
            "# Pure design\n\n## Verification\n\n- (all Requirements are pure-design; no runtime verification commands)\n",
            encoding="utf-8",
        )
        pure_expected = pure_root / "spec.expected.json"
        pure_expected.write_text(json.dumps({"verification_commands": []}) + "\n", encoding="utf-8")
        expected_empty_design = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(pure_expected)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_empty_design.returncode != 0:
            print("empty verification_commands should be valid for pure-design specs", file=sys.stderr)
            print(expected_empty_design.stderr, file=sys.stderr)
            return 1

        expected_json.write_text(json.dumps({"unknown": True}) + "\n")
        expected_bad = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_bad.returncode == 0:
            print("spec.expected.json with unknown key was accepted", file=sys.stderr)
            return 1

        expected_json.write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contians": ["ok"]}]
        }) + "\n")
        expected_bad_command = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_bad_command.returncode == 0:
            print("spec.expected.json command with unknown key was accepted", file=sys.stderr)
            return 1

        expected_json.write_text("[1]\n")
        expected_non_object = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_non_object.returncode == 0:
            print("spec.expected.json top-level array was accepted", file=sys.stderr)
            return 1
        if "top-level must be a JSON object" not in expected_non_object.stderr:
            print("spec.expected.json top-level array did not report object shape error", file=sys.stderr)
            print(expected_non_object.stderr, file=sys.stderr)
            return 1
        if "Traceback" in expected_non_object.stderr:
            print("spec.expected.json top-level array produced a traceback", file=sys.stderr)
            return 1

        expected_json.write_text("{broken\n")
        expected_invalid_json = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_invalid_json.returncode == 0:
            print("invalid spec.expected.json was accepted", file=sys.stderr)
            return 1
        if "has invalid JSON" not in expected_invalid_json.stderr:
            print("invalid spec.expected.json did not report JSON parse error", file=sys.stderr)
            print(expected_invalid_json.stderr, file=sys.stderr)
            return 1
        if "Traceback" in expected_invalid_json.stderr:
            print("invalid spec.expected.json produced a traceback", file=sys.stderr)
            return 1

        expected_json.write_text('{"verification_commands": NaN}\n')
        expected_nan_json = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
        )
        if expected_nan_json.returncode == 0:
            print("NaN spec.expected.json was accepted", file=sys.stderr)
            return 1
        if "invalid JSON numeric constant: NaN" not in expected_nan_json.stderr:
            print("NaN spec.expected.json did not report invalid numeric constant", file=sys.stderr)
            print(expected_nan_json.stderr, file=sys.stderr)
            return 1

        spec_integrity = work / "spec-integrity"
        spec_integrity.mkdir()
        spec_integrity_devlyn = spec_integrity / ".devlyn"
        spec_integrity_devlyn.mkdir()
        integrity_spec = spec_integrity / "spec.md"
        integrity_spec.write_text(
            "# Spec\n\n## Verification\n\n```json\n"
            "{\"verification_commands\":[{\"cmd\":\"printf spec-hash-ok\",\"stdout_contains\":[\"spec-hash-ok\"]}]}\n"
            "```\n",
            encoding="utf-8",
        )
        (spec_integrity_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {
                "type": "spec",
                "spec_path": str(integrity_spec),
                "spec_sha256": "0" * 64,
            }
        }))
        spec_bad_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=spec_integrity,
            capture_output=True,
            text=True,
        )
        if spec_bad_hash_run.returncode == 0:
            print("spec source with mismatched source.spec_sha256 was accepted", file=sys.stderr)
            return 1
        if "source.spec_sha256 mismatch" not in spec_bad_hash_run.stderr:
            print("spec source hash mismatch did not report source integrity", file=sys.stderr)
            print(spec_bad_hash_run.stderr, file=sys.stderr)
            return 1

        spec_hash = hashlib.sha256(integrity_spec.read_bytes()).hexdigest()
        (spec_integrity_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {
                "type": "spec",
                "spec_path": str(integrity_spec),
                "spec_sha256": spec_hash,
            }
        }))
        spec_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=spec_integrity,
            capture_output=True,
            text=True,
        )
        if spec_hash_run.returncode != 0:
            print(spec_hash_run.stderr, file=sys.stderr)
            return 1
        staged_spec_hash = loads_strict_json((spec_integrity_devlyn / "spec-verify.json").read_text())
        if staged_spec_hash.get("verification_commands", [{}])[0].get("cmd") != "printf spec-hash-ok":
            print("spec source with matching source.spec_sha256 was not staged", file=sys.stderr)
            return 1

        generated_user = work / "generated-user"
        generated_user.mkdir()
        generated_devlyn = generated_user / ".devlyn"
        generated_devlyn.mkdir()
        generated_criteria = generated_user / ".devlyn" / "criteria.generated.md"
        generated_criteria.write_text(
            "# Criteria\n\n## Verification\n\n```json\n"
            "{\"verification_commands\":[{\"cmd\":\"printf generated-ok\",\"stdout_contains\":[\"generated-ok\"]}]}\n"
            "```\n",
            encoding="utf-8",
        )
        (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "generated", "criteria_path": str(generated_criteria)}
        }))
        generated_missing_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
        )
        if generated_missing_hash_run.returncode == 0:
            print("generated criteria without source.criteria_sha256 was accepted", file=sys.stderr)
            return 1
        if "source.criteria_sha256 is required" not in generated_missing_hash_run.stderr:
            print("generated criteria without source.criteria_sha256 did not report source integrity", file=sys.stderr)
            print(generated_missing_hash_run.stderr, file=sys.stderr)
            return 1

        (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {
                "type": "generated",
                "criteria_path": str(generated_criteria),
                "criteria_sha256": "0" * 64,
            }
        }))
        generated_bad_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
        )
        if generated_bad_hash_run.returncode == 0:
            print("generated criteria with mismatched source.criteria_sha256 was accepted", file=sys.stderr)
            return 1
        if "source.criteria_sha256 mismatch" not in generated_bad_hash_run.stderr:
            print("generated criteria hash mismatch did not report source integrity", file=sys.stderr)
            print(generated_bad_hash_run.stderr, file=sys.stderr)
            return 1

        generated_hash = hashlib.sha256(generated_criteria.read_bytes()).hexdigest()
        (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {
                "type": "generated",
                "criteria_path": str(generated_criteria),
                "criteria_sha256": generated_hash,
            }
        }))
        generated_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
        )
        if generated_run.returncode != 0:
            print(generated_run.stderr, file=sys.stderr)
            return 1
        staged_generated = loads_strict_json((generated_devlyn / "spec-verify.json").read_text())
        if staged_generated.get("verification_commands", [{}])[0].get("cmd") != "printf generated-ok":
            print("generated criteria carrier was not staged into .devlyn/spec-verify.json", file=sys.stderr)
            return 1

        generated_criteria.write_text(
            "# Criteria\n\n## Verification\n\n- generated criteria omitted its machine-readable carrier.\n",
            encoding="utf-8",
        )
        malformed_generated_hash = hashlib.sha256(generated_criteria.read_bytes()).hexdigest()
        (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {
                "type": "generated",
                "criteria_path": str(generated_criteria),
                "criteria_sha256": malformed_generated_hash,
            }
        }))
        malformed_generated_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
        )
        if malformed_generated_run.returncode == 0:
            print("generated criteria without a JSON carrier was accepted", file=sys.stderr)
            return 1
        if "Generated criteria were written without one" not in malformed_generated_run.stderr:
            print("generated criteria without a JSON carrier did not report the generated-source contract", file=sys.stderr)
            print(malformed_generated_run.stderr, file=sys.stderr)
            return 1

        real_user = work / "real-user"
        real_user.mkdir()
        real_devlyn = real_user / ".devlyn"
        real_devlyn.mkdir()
        real_spec = real_user / "spec.md"
        real_spec.write_text(
            "# Spec\n\n## Verification\n\n- sibling command must print sibling-ok.\n"
        )
        (real_user / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf sibling-ok", "stdout_contains": ["sibling-ok"]}
            ]
        }) + "\n")
        (real_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(real_spec)}
        }))
        sibling_run = subprocess.run(
            [sys.executable, script_path],
            cwd=real_user,
            capture_output=True,
            text=True,
        )
        if sibling_run.returncode != 0:
            print(sibling_run.stderr, file=sys.stderr)
            return 1
        staged = loads_strict_json((real_devlyn / "spec-verify.json").read_text())
        if staged.get("verification_commands", [{}])[0].get("cmd") != "printf sibling-ok":
            print("sibling spec.expected.json was not staged into .devlyn/spec-verify.json", file=sys.stderr)
            return 1

        malformed = work / "malformed-sibling"
        malformed.mkdir()
        malformed_devlyn = malformed / ".devlyn"
        malformed_devlyn.mkdir()
        malformed_spec = malformed / "spec.md"
        malformed_spec.write_text(
            "# Spec\n\n## Verification\n\n```json\n"
            "{\"verification_commands\":[{\"cmd\":\"printf inline-ok\"}]}\n"
            "```\n"
        )
        (malformed / "spec.expected.json").write_text(json.dumps({"unknown": True}) + "\n")
        (malformed_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(malformed_spec)}
        }))
        malformed_run = subprocess.run(
            [sys.executable, script_path],
            cwd=malformed,
            capture_output=True,
            text=True,
        )
        if malformed_run.returncode == 0:
            print("malformed sibling spec.expected.json fell back to inline carrier", file=sys.stderr)
            return 1

        bench_spec = work / "bench-spec.md"
        bench_spec.write_text("# Spec\n\n## Verification\n\n- benchmark pre-staged wins.\n")
        (work / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf wrong", "stdout_contains": ["wrong"]}
            ]
        }) + "\n")
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(bench_spec)}
        }))
        (devlyn / "spec-verify.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf bench-staged", "stdout_contains": ["bench-staged"]}
            ]
        }) + "\n")
        bench_pre_staged = subprocess.run(
            [sys.executable, script_path],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if bench_pre_staged.returncode != 0:
            print(bench_pre_staged.stderr, file=sys.stderr)
            return 1
        staged_bench = loads_strict_json((devlyn / "spec-verify.json").read_text())
        if staged_bench.get("verification_commands", [{}])[0].get("cmd") != "printf bench-staged":
            print("benchmark pre-staged contract was overwritten", file=sys.stderr)
            return 1

        verify_output = work / "verify-output"
        verify_output.mkdir()
        verify_devlyn = verify_output / ".devlyn"
        verify_devlyn.mkdir()
        verify_spec = verify_output / "spec.md"
        verify_spec.write_text("# Spec\n\n## Verification\n\n- verify mechanical output.\n")
        (verify_output / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf wrong", "stdout_contains": ["expected"]}
            ]
        }) + "\n")
        (verify_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(verify_spec)}
        }))
        verify_env = os.environ.copy()
        verify_env.update({
            "SPEC_VERIFY_PHASE": "verify_mechanical",
            "SPEC_VERIFY_FINDINGS_FILE": "verify-mechanical.findings.jsonl",
            "SPEC_VERIFY_FINDING_PREFIX": "VERIFY-MECH",
        })
        verify_output_run = subprocess.run(
            [sys.executable, script_path],
            cwd=verify_output,
            env=verify_env,
            capture_output=True,
            text=True,
        )
        if verify_output_run.returncode == 0:
            print("VERIFY output-mode failing command was accepted", file=sys.stderr)
            return 1
        verify_findings = (verify_devlyn / "verify-mechanical.findings.jsonl").read_text()
        if '"phase": "verify_mechanical"' not in verify_findings or "VERIFY-MECH-" not in verify_findings:
            print("VERIFY output-mode did not route findings to verify-mechanical", file=sys.stderr)
            return 1

        contract_root = work / "expected-contract"
        contract_root.mkdir()
        contract_devlyn = contract_root / ".devlyn"
        contract_devlyn.mkdir()
        (contract_root / "package.json").write_text(
            '{\n  "dependencies": {},\n  "devDependencies": {}\n}\n'
        )
        subprocess.run(["git", "init", "-q"], cwd=contract_root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=contract_root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base"],
            cwd=contract_root,
            check=True,
        )
        base_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=contract_root,
            text=True,
        ).strip()
        contract_spec = contract_root / "spec.md"
        contract_spec.write_text("# Spec\n\n## Verification\n\n- expected contract checks.\n")
        (contract_root / "app.js").write_text("try { work(); } catch { return null; }\n")
        (contract_root / "forbidden.txt").write_text("forbidden\n")
        (contract_root / "package.json").write_text(
            '{\n  "dependencies": {\n    "left-pad": "1.3.0"\n  },\n'
            '  "devDependencies": {}\n}\n'
        )
        (contract_root / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contains": ["ok"]}],
            "forbidden_patterns": [{
                "pattern": "catch\\s*\\{\\s*return null",
                "description": "silent catch fallback",
                "severity": "disqualifier",
            }],
            "required_files": ["required.txt"],
            "forbidden_files": ["forbidden.txt"],
            "max_deps_added": 0,
        }) + "\n")
        subprocess.run(["git", "add", "-A"], cwd=contract_root, check=True)
        (contract_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(contract_spec)},
            "base_ref": {"sha": base_sha},
        }))
        contract_run = subprocess.run(
            [sys.executable, script_path],
            cwd=contract_root,
            capture_output=True,
            text=True,
        )
        if contract_run.returncode == 0:
            print("expected contract violations were accepted", file=sys.stderr)
            return 1
        findings_text = (contract_devlyn / "spec-verify-findings.jsonl").read_text()
        for rule_id in (
            "correctness.forbidden-pattern",
            "correctness.required-file-missing",
            "scope.forbidden-file-touched",
            "scope.max-deps-added-exceeded",
        ):
            if rule_id not in findings_text:
                print(f"expected contract finding missing: {rule_id}", file=sys.stderr)
                return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P4",
            "derived_from": "probe must pass visible marker.",
            "cmd": "printf weak-boundary",
            "exit_code": 0,
            "tags": ["boundary_overlap"],
            "tag_evidence": {"boundary_overlap": ["one_minute_overlap"]},
        }) + "\n")
        weak = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
        )
        if weak.returncode == 0:
            print("incomplete boundary_overlap evidence was accepted", file=sys.stderr)
            return 1

        rollback_root = work / "rollback-risk-probe"
        rollback_root.mkdir()
        rollback_devlyn = rollback_root / ".devlyn"
        rollback_devlyn.mkdir()
        rollback_spec = rollback_root / "spec.md"
        rollback_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- A failed all-or-nothing operation must roll back tentative state "
            "so later orders can use the released stock.\n"
        )
        (rollback_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(rollback_spec)}
        }))
        (rollback_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P5",
            "derived_from": (
                "A failed all-or-nothing operation must roll back tentative "
                "state so later orders can use the released stock."
            ),
            "cmd": "printf weak-rollback",
            "exit_code": 0,
            "tags": ["prior_consumption"],
            "tag_evidence": {
                "prior_consumption": [
                    "same_resource_consumed_first",
                    "later_entity_fails_or_reroutes",
                ],
            },
        }) + "\n")
        weak_rollback = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=rollback_root,
            capture_output=True,
            text=True,
        )
        if weak_rollback.returncode == 0:
            print("rollback verification text did not require rollback_state probe tag", file=sys.stderr)
            return 1

        error_root = work / "error-contract-risk-probe"
        error_root.mkdir()
        error_devlyn = error_root / ".devlyn"
        error_devlyn.mkdir()
        error_spec = error_root / "spec.md"
        error_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- Invalid input must print a JSON error object to stderr and exit 2.\n"
        )
        (error_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(error_spec)}
        }))
        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P6",
            "derived_from": "Invalid input must print a JSON error object to stderr and exit 2.",
            "cmd": "printf weak-error-contract",
            "exit_code": 0,
            "tags": ["stdout_stderr_contract", "error_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "error_contract": ["asserts_error_payload_or_stderr"],
            },
        }) + "\n")
        weak_error_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
        )
        if weak_error_contract.returncode == 0:
            print("error_contract without exit-code evidence was accepted", file=sys.stderr)
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7",
            "derived_from": "Invalid input must print a JSON error object to stderr and exit 2.",
            "cmd": "printf weak-stdio-contract",
            "exit_code": 2,
            "tags": ["stdout_stderr_contract", "error_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": [],
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
            },
        }) + "\n")
        weak_stdio_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
        )
        if weak_stdio_contract.returncode == 0:
            print("stdout_stderr_contract without stream evidence was accepted", file=sys.stderr)
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7b",
            "derived_from": "Invalid input must print a JSON error object to stderr and exit 2.",
            "cmd": "printf weak-json-error-shape-contract",
            "exit_code": 2,
            "tags": ["stdout_stderr_contract", "error_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
            },
        }) + "\n")
        weak_json_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
        )
        if weak_json_error_shape_contract.returncode == 0:
            print("JSON error object text did not require shape_contract tag", file=sys.stderr)
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7c",
            "derived_from": "Invalid input must print a JSON error object to stderr and exit 2.",
            "cmd": "printf json-error-shape-contract",
            "exit_code": 2,
            "tags": ["stdout_stderr_contract", "error_contract", "shape_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                    "asserts_exact_error_object",
                ],
            },
        }) + "\n")
        strong_json_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
        )
        if strong_json_error_shape_contract.returncode != 0:
            print("JSON error object shape_contract with exact object evidence was rejected", file=sys.stderr)
            print(strong_json_error_shape_contract.stderr, file=sys.stderr)
            return 1

        inline_json_error = (
            'Invalid input prints JSON error `{ "error": "invalid" }` to stderr and exits 2.'
        )
        error_spec.write_text("# Spec\n\n## Verification\n\n- " + inline_json_error + "\n")
        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7d",
            "derived_from": inline_json_error,
            "cmd": "printf weak-inline-json-error-shape-contract",
            "exit_code": 2,
            "tags": ["stdout_stderr_contract", "error_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
            },
        }) + "\n")
        weak_inline_json_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
        )
        if weak_inline_json_error_shape_contract.returncode == 0:
            print("inline JSON error text did not require shape_contract tag", file=sys.stderr)
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7e",
            "derived_from": inline_json_error,
            "cmd": "printf inline-json-error-shape-contract",
            "exit_code": 2,
            "tags": ["stdout_stderr_contract", "error_contract", "shape_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                    "asserts_exact_error_object",
                ],
            },
        }) + "\n")
        strong_inline_json_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
        )
        if strong_inline_json_error_shape_contract.returncode != 0:
            print("inline JSON error shape_contract with exact object evidence was rejected", file=sys.stderr)
            print(strong_inline_json_error_shape_contract.stderr, file=sys.stderr)
            return 1

        http_error_root = work / "http-error-contract-risk-probe"
        http_error_root.mkdir()
        http_error_devlyn = http_error_root / ".devlyn"
        http_error_devlyn.mkdir()
        http_error_spec = http_error_root / "spec.md"
        http_error_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- An invalid query returns HTTP 400 with JSON error body `{ \"error\": \"invalid_query\", \"field\": \"per_page\" }`.\n"
        )
        (http_error_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(http_error_spec)}
        }))
        (http_error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8",
            "derived_from": (
                "An invalid query returns HTTP 400 with JSON error body "
                "`{ \"error\": \"invalid_query\", \"field\": \"per_page\" }`."
            ),
            "cmd": "printf weak-http-error-contract",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        weak_http_error_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
        )
        if weak_http_error_contract.returncode == 0:
            print("http error text did not require http_error_contract tag", file=sys.stderr)
            return 1

        (http_error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8b",
            "derived_from": (
                "An invalid query returns HTTP 400 with JSON error body "
                "`{ \"error\": \"invalid_query\", \"field\": \"per_page\" }`."
            ),
            "cmd": "printf http-error-contract",
            "exit_code": 0,
            "tags": ["http_error_contract"],
            "tag_evidence": {
                "http_error_contract": ["asserts_http_error_status"],
            },
        }) + "\n")
        incomplete_http_error_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
        )
        if incomplete_http_error_contract.returncode == 0:
            print("http_error_contract without payload evidence was accepted", file=sys.stderr)
            return 1

        (http_error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8c",
            "derived_from": (
                "An invalid query returns HTTP 400 with JSON error body "
                "`{ \"error\": \"invalid_query\", \"field\": \"per_page\" }`."
            ),
            "cmd": "printf weak-exact-error-shape-contract",
            "exit_code": 0,
            "tags": ["http_error_contract", "shape_contract"],
            "tag_evidence": {
                "http_error_contract": [
                    "asserts_http_error_status",
                    "asserts_error_payload_body",
                ],
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                ],
            },
        }) + "\n")
        weak_exact_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
        )
        if weak_exact_error_shape_contract.returncode == 0:
            print("exact error body shape_contract without exact object evidence was accepted", file=sys.stderr)
            return 1

        (http_error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8d",
            "derived_from": (
                "An invalid query returns HTTP 400 with JSON error body "
                "`{ \"error\": \"invalid_query\", \"field\": \"per_page\" }`."
            ),
            "cmd": "printf exact-error-shape-contract",
            "exit_code": 0,
            "tags": ["http_error_contract", "shape_contract"],
            "tag_evidence": {
                "http_error_contract": [
                    "asserts_http_error_status",
                    "asserts_error_payload_body",
                ],
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                    "asserts_exact_error_object",
                ],
            },
        }) + "\n")
        strong_exact_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
        )
        if strong_exact_error_shape_contract.returncode != 0:
            print("exact error body shape_contract with exact object evidence was rejected", file=sys.stderr)
            print(strong_exact_error_shape_contract.stderr, file=sys.stderr)
            return 1

        shape_root = work / "exact-shape-risk-probe"
        shape_root.mkdir()
        shape_devlyn = shape_root / ".devlyn"
        shape_devlyn.mkdir()
        shape_spec = shape_root / "spec.md"
        shape_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- On success, output is one JSON object with keys `applied`, `rejected`, and `accounts`; "
            "`rejected` rows have keys `id` and `reason`.\n"
        )
        (shape_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(shape_spec)}
        }))
        (shape_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8c",
            "derived_from": (
                "On success, output is one JSON object with keys `applied`, `rejected`, and `accounts`; "
                "`rejected` rows have keys `id` and `reason`."
            ),
            "cmd": "printf weak-shape-contract",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        weak_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=shape_root,
            capture_output=True,
            text=True,
        )
        if weak_shape_contract.returncode == 0:
            print("shape_contract without exact key evidence was accepted", file=sys.stderr)
            return 1

        (shape_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8d",
            "derived_from": (
                "On success, output is one JSON object with keys `applied`, `rejected`, and `accounts`; "
                "`rejected` rows have keys `id` and `reason`."
            ),
            "cmd": "printf shape-contract",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                ],
            },
        }) + "\n")
        strong_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=shape_root,
            capture_output=True,
            text=True,
        )
        if strong_shape_contract.returncode != 0:
            print("shape_contract with exact key evidence was rejected", file=sys.stderr)
            print(strong_shape_contract.stderr, file=sys.stderr)
            return 1

        inline_json_success = 'On success, stdout is `{ "id": "acct_1", "status": "accepted" }`.'
        shape_spec.write_text("# Spec\n\n## Verification\n\n- " + inline_json_success + "\n")
        (shape_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8e",
            "derived_from": inline_json_success,
            "cmd": "printf weak-inline-json-shape-contract",
            "exit_code": 0,
            "tags": ["stdout_stderr_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
            },
        }) + "\n")
        weak_inline_json_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=shape_root,
            capture_output=True,
            text=True,
        )
        if weak_inline_json_shape_contract.returncode == 0:
            print("inline JSON object text did not require shape_contract tag", file=sys.stderr)
            return 1

        (shape_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8f",
            "derived_from": inline_json_success,
            "cmd": "printf inline-json-shape-contract",
            "exit_code": 0,
            "tags": ["stdout_stderr_contract", "shape_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                ],
            },
        }) + "\n")
        strong_inline_json_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=shape_root,
            capture_output=True,
            text=True,
        )
        if strong_inline_json_shape_contract.returncode != 0:
            print("inline JSON object shape_contract with key evidence was rejected", file=sys.stderr)
            print(strong_inline_json_shape_contract.stderr, file=sys.stderr)
            return 1

        forbidden_text_root = work / "forbidden-pattern-risk-probe"
        forbidden_text_root.mkdir()
        forbidden_text_devlyn = forbidden_text_root / ".devlyn"
        forbidden_text_devlyn.mkdir()
        forbidden_text_spec = forbidden_text_root / "spec.md"
        forbidden_text_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- The diff must not add forbidden fallback patterns.\n"
        )
        (forbidden_text_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(forbidden_text_spec)}
        }))
        (forbidden_text_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8",
            "derived_from": "The diff must not add forbidden fallback patterns.",
            "cmd": "printf forbidden-pattern-static-check",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        forbidden_pattern_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=forbidden_text_root,
            capture_output=True,
            text=True,
        )
        if forbidden_pattern_probe.returncode != 0:
            print("generic forbidden-pattern verification text incorrectly required boundary_overlap", file=sys.stderr)
            print(forbidden_pattern_probe.stderr, file=sys.stderr)
            return 1

        stock_validation_root = work / "stock-validation-risk-probe"
        stock_validation_root.mkdir()
        stock_validation_devlyn = stock_validation_root / ".devlyn"
        stock_validation_devlyn.mkdir()
        stock_validation_spec = stock_validation_root / "spec.md"
        stock_validation_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- A quote over combined stock exits `2`, prints one JSON error to stderr, and prints no stdout.\n"
        )
        (stock_validation_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(stock_validation_spec)}
        }))
        (stock_validation_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P9",
            "derived_from": (
                "A quote over combined stock exits `2`, prints one JSON error "
                "to stderr, and prints no stdout."
            ),
            "cmd": "printf stock-validation-error",
            "exit_code": 2,
            "tags": ["stdout_stderr_contract", "error_contract"],
            "tag_evidence": {
                "stdout_stderr_contract": ["asserts_named_stream_output"],
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
            },
        }) + "\n")
        stock_validation_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=stock_validation_root,
            capture_output=True,
            text=True,
        )
        if stock_validation_probe.returncode != 0:
            print("stock validation error text incorrectly required prior_consumption", file=sys.stderr)
            print(stock_validation_probe.stderr, file=sys.stderr)
            return 1

        webhook_root = work / "webhook-risk-probe"
        webhook_root.mkdir()
        webhook_devlyn = webhook_root / ".devlyn"
        webhook_devlyn.mkdir()
        webhook_spec = webhook_root / "spec.md"
        webhook_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- A POST whose body has been modified after signing returns 401.\n"
            "- A second POST with the same accepted `id` returns 409 even if the duplicate body would otherwise fail shape validation.\n"
        )
        (webhook_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(webhook_spec)}
        }))
        (webhook_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P10",
            "derived_from": "A POST whose body has been modified after signing returns 401.",
            "cmd": "printf weak-webhook",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        weak_webhook_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=webhook_root,
            capture_output=True,
            text=True,
        )
        if weak_webhook_probe.returncode == 0:
            print("webhook signature/replay text did not require auth/idempotency probe tags", file=sys.stderr)
            return 1

        duplicate_sku_root = work / "duplicate-sku-risk-probe"
        duplicate_sku_root.mkdir()
        duplicate_sku_devlyn = duplicate_sku_root / ".devlyn"
        duplicate_sku_devlyn.mkdir()
        duplicate_sku_spec = duplicate_sku_root / "spec.md"
        duplicate_sku_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- A cart with duplicate SKUs combines quantities before stock validation.\n"
        )
        (duplicate_sku_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(duplicate_sku_spec)}
        }))
        (duplicate_sku_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P11",
            "derived_from": "A cart with duplicate SKUs combines quantities before stock validation.",
            "cmd": "printf duplicate-sku-shape",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        duplicate_sku_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=duplicate_sku_root,
            capture_output=True,
            text=True,
        )
        if duplicate_sku_probe.returncode != 0:
            print("duplicate SKU verification text incorrectly required idempotency_replay", file=sys.stderr)
            print(duplicate_sku_probe.stderr, file=sys.stderr)
            return 1

        concurrent_root = work / "concurrent-state-risk-probe"
        concurrent_root.mkdir()
        concurrent_devlyn = concurrent_root / ".devlyn"
        concurrent_devlyn.mkdir()
        concurrent_spec = concurrent_root / "spec.md"
        concurrent_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- Several POST requests close together must all appear exactly once "
            "in GET output with distinct ids.\n"
        )
        (concurrent_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(concurrent_spec)}
        }))
        (concurrent_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P12",
            "derived_from": (
                "Several POST requests close together must all appear exactly "
                "once in GET output with distinct ids."
            ),
            "cmd": "printf weak-concurrent-state",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        weak_concurrent_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=concurrent_root,
            capture_output=True,
            text=True,
        )
        if weak_concurrent_probe.returncode == 0:
            print("concurrent state text did not require concurrent_state_consistency tag", file=sys.stderr)
            return 1

        atomic_batch_root = work / "atomic-batch-risk-probe"
        atomic_batch_root.mkdir()
        atomic_batch_devlyn = atomic_batch_root / ".devlyn"
        atomic_batch_devlyn.mkdir()
        atomic_batch_spec = atomic_batch_root / "spec.md"
        atomic_batch_spec.write_text(
            "# Spec\n\n## Verification\n\n"
            "- A POST with one valid + one invalid item returns `400`, AND a subsequent GET returns the same list as before the import.\n"
            "- A POST with all-valid items returns `201`, and the items appear in GET output in order with distinct ids.\n"
        )
        (atomic_batch_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(atomic_batch_spec)}
        }))
        (atomic_batch_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P13",
            "derived_from": (
                "A POST with one valid + one invalid item returns `400`, AND "
                "a subsequent GET returns the same list as before the import."
            ),
            "cmd": "printf weak-atomic-batch",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n")
        weak_atomic_batch_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=atomic_batch_root,
            capture_output=True,
            text=True,
        )
        if weak_atomic_batch_probe.returncode == 0:
            print("atomic batch text did not require atomic_batch_state tag", file=sys.stderr)
            return 1

        (atomic_batch_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P13b",
            "derived_from": (
                "A POST with one valid + one invalid item returns `400`, AND "
                "a subsequent GET returns the same list as before the import."
            ),
            "cmd": "printf incomplete-atomic-batch",
            "exit_code": 0,
            "tags": ["atomic_batch_state"],
            "tag_evidence": {
                "atomic_batch_state": [
                    "mixed_valid_invalid_batch",
                    "asserts_store_unchanged_after_failure",
                ],
            },
        }) + "\n")
        incomplete_atomic_batch_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=atomic_batch_root,
            capture_output=True,
            text=True,
        )
        if incomplete_atomic_batch_probe.returncode == 0:
            print("atomic_batch_state without success-order evidence was accepted", file=sys.stderr)
            return 1
    return 0


def main() -> int:
    include_risk_probes = False
    validate_risk_probes_only = False
    if "--include-risk-probes" in sys.argv[1:]:
        include_risk_probes = True
        sys.argv = [arg for arg in sys.argv if arg != "--include-risk-probes"]
    if "--validate-risk-probes" in sys.argv[1:]:
        validate_risk_probes_only = True
        sys.argv = [arg for arg in sys.argv if arg != "--validate-risk-probes"]

    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        return run_self_test()

    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        if len(sys.argv) != 3:
            print("usage: spec-verify-check.py --check <markdown-path>", file=sys.stderr)
            return 2
        return run_check_mode(Path(sys.argv[2]))

    if len(sys.argv) >= 2 and sys.argv[1] == "--check-expected":
        if len(sys.argv) != 3:
            print("usage: spec-verify-check.py --check-expected <json-path>", file=sys.stderr)
            return 2
        return run_check_expected_mode(Path(sys.argv[2]))

    bench_mode = "BENCH_WORKDIR" in os.environ
    work = Path(os.environ.get("BENCH_WORKDIR") or os.getcwd())
    devlyn_dir = work / ".devlyn"
    spec_path = devlyn_dir / "spec-verify.json"

    # iter-0019.8 + iter-0019.9 (Codex R-phaseA): determine the contract
    # carrier source for THIS run. Order:
    #   1. Benchmark mode (BENCH_WORKDIR set) AND a pre-staged
    #      .devlyn/spec-verify.json exists at script start: TRUST it (this is
    #      the run-fixture.sh contract staged from expected.json). Skip
    #      source-extract entirely. iter-0019.9 closes the F9 regression where
    #      source-extract from an ideate-generated spec overwrote the
    #      benchmark contract — for benchmarks, expected.json is canonical.
    #   2. Otherwise, real-user source.type=="spec" first attempts the sibling
    #      spec.expected.json next to spec.md. If present, validate it and stage
    #      its verification_commands. If malformed, fail closed. If absent,
    #      continue to legacy source-extract.
    #   3. Source-extract reads
    #      `pipeline.state.json:source.{spec_path | criteria_path}`. If it has
    #      a json block, overwrite .devlyn/spec-verify.json with it.
    #   4. If source has no json block AND source.type=="generated":
    #      CRITICAL spec-verify-malformed — generated criteria must ship a
    #      verifiable contract per the generated-criteria output contract.
    #   5. If source has no sibling/json block AND source.type=="spec":
    #      - Real-user mode: silent no-op (preserves iter-0019.6 backward
    #        compat for handwritten specs without the carrier). Drop any
    #        stale pre-staged file.
    #      - Benchmark mode: fall through to the pre-staged-trust branch
    #        (covers pre-iter-0019.9 fixtures whose spec.md has prose-only
    #        Verification — run-fixture.sh staged the contract regardless).
    pre_staged = spec_path.is_file()  # captured BEFORE any potential write
    trust_bench_staged = bench_mode and pre_staged
    src_type, source_md = read_source(work, devlyn_dir)
    state = read_state(devlyn_dir)
    integrity_error = source_integrity_error(src_type, state, source_md)
    if integrity_error:
        print(f"[spec-verify] carrier malformed: {integrity_error}", file=sys.stderr)
        write_malformed_finding(devlyn_dir, integrity_error, source_md)
        return 1
    expected_data: dict | None = None
    expected_path: Path | None = None
    if validate_risk_probes_only:
        _risk_probes, risk_error = load_risk_probes(
            devlyn_dir, source_md, require_present=True
        )
        if risk_error:
            print(f"[spec-verify] risk probes malformed: {risk_error}", file=sys.stderr)
            write_malformed_finding(devlyn_dir, risk_error, devlyn_dir / "risk-probes.jsonl")
            return 1
        print("[spec-verify] risk probes valid", file=sys.stderr)
        return 0
    if source_md is not None and not trust_bench_staged:
        if src_type == "spec":
            expected_found, expected_staged, expected_error, expected_path, expected_data = stage_from_expected(
                source_md, devlyn_dir
            )
            if expected_error is not None:
                print(f"[spec-verify] carrier malformed: {expected_error}", file=sys.stderr)
                write_malformed_finding(devlyn_dir, expected_error, expected_path)
                return 1
            if expected_staged:
                staged, error = (True, None)
            else:
                staged, error = stage_from_source(source_md, devlyn_dir)
        else:
            staged, error = stage_from_source(source_md, devlyn_dir)
        if error is not None:
            print(f"[spec-verify] carrier malformed: {error}", file=sys.stderr)
            write_malformed_finding(devlyn_dir, error, source_md)
            return 1
        if not staged:
            if src_type == "generated":
                msg = (
                    f"generated {source_md.name} must include a "
                    "`## Verification` ```json``` block (verification_commands "
                    "array). Generated criteria were written without one."
                )
                print(f"[spec-verify] {msg}", file=sys.stderr)
                write_malformed_finding(devlyn_dir, msg, source_md)
                return 1
            # source.type=="spec", no block in spec markdown.
            if not bench_mode and expected_data is None:
                # Real-user handwritten spec: silent no-op. Drop any stale
                # pre-staged file so a killed prior run cannot poison this
                # run's gate.
                if spec_path.exists():
                    spec_path.unlink()
                return 0
            # Benchmark mode with no source block AND no pre-staged file
            # (rare — fixture mis-config) falls through to the no-pre-staged
            # silent no-op branch below.

    # iter-0019.9 (Codex R2 caveat): close the real-user no-source-md
    # stale-orphan gap. If pipeline.state.json is absent or has no source,
    # but a stale .devlyn/spec-verify.json exists in real-user mode, drop
    # it — the only legitimate path that reaches here with a pre-staged
    # file is benchmark mode (run-fixture.sh staged it).
    if source_md is None and not bench_mode and spec_path.exists():
        spec_path.unlink()
        return 0

    commands: list[dict] = []
    if not spec_path.exists():
        # No source markdown carrier AND no pre-staged file. Silent no-op
        # for benchmark misconfigurations (no fixture to gate against) and
        # for real-user runs without spec/criteria. Generated source case
        # is handled above.
        if expected_data is None:
            return 0
    else:
        try:
            spec = loads_strict_json(spec_path.read_text())
        except (ValueError, OSError) as e:
            print(f"[spec-verify] error: cannot parse {spec_path}: {e}", file=sys.stderr)
            return 2

        # iter-0019.8 (Codex R2 #2): apply full shape validation to pre-staged
        # carriers too — bool exit_code, empty list, whitespace-only cmd were
        # silently accepted on the benchmark path. Empty list is rejected
        # because "all 0 commands passed" is vacuously true.
        shape_err = validate_shape(spec)
        if shape_err:
            print(f"[spec-verify] error: {spec_path}: {shape_err}", file=sys.stderr)
            write_malformed_finding(devlyn_dir, f"{spec_path}: {shape_err}", None)
            return 1
        commands = list(spec["verification_commands"])
    if include_risk_probes:
        risk_state_error = risk_probes_state_error(state)
        if risk_state_error:
            print(f"[spec-verify] risk probes malformed: {risk_state_error}", file=sys.stderr)
            write_malformed_finding(devlyn_dir, risk_state_error, Path("pipeline.state.json"))
            return 1
        risk_probes, risk_error = load_risk_probes(
            devlyn_dir,
            source_md,
            require_present=state_requires_risk_probes(state),
        )
        if risk_error:
            print(f"[spec-verify] risk probes malformed: {risk_error}", file=sys.stderr)
            write_malformed_finding(devlyn_dir, risk_error, devlyn_dir / "risk-probes.jsonl")
            return 1
        commands.extend(risk_probes)

    devlyn_dir.mkdir(parents=True, exist_ok=True)
    results_path = devlyn_dir / "spec-verify.results.json"
    findings_path = devlyn_dir / output_findings_name()

    verify_env = os.environ.copy()
    verify_env["BENCH_WORKDIR"] = str(work)

    results: list[dict] = []
    findings: list[dict] = []
    finding_seq = 1

    for idx, vc in enumerate(commands):
        cmd = vc.get("cmd")
        if not cmd:
            results.append({"index": idx, "cmd": None, "pass": False,
                            "reason": "missing_cmd"})
            continue

        is_risk_probe = bool(vc.get("_risk_probe"))
        expected_exit = vc.get("exit_code", 0)
        stdout_contains = vc.get("stdout_contains", []) or []
        stdout_not_contains = vc.get("stdout_not_contains", []) or []

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(work),
                shell=True,
                env=verify_env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            # Mirror run-fixture.sh post-run verifier: combined stdout+stderr.
            out = (proc.stdout or "") + (proc.stderr or "")
            ok_exit = proc.returncode == expected_exit
            ok_contains = all(s in out for s in stdout_contains)
            ok_not = not any(s in out for s in stdout_not_contains)
            passed = bool(ok_exit and ok_contains and ok_not)

            if passed:
                reason = None
            elif not ok_exit:
                reason = "exit"
            elif not ok_contains:
                reason = "missing_contains"
            else:
                reason = "unexpected_text"

            results.append({
                "index": idx,
                "cmd": cmd,
                "expected_exit": expected_exit,
                "actual_exit": proc.returncode,
                "stdout_contains": stdout_contains,
                "stdout_not_contains": stdout_not_contains,
                "pass": passed,
                "reason": reason,
                "stdout_tail": out[-500:],
            })

            if not passed:
                # Construct fine-grained message naming the specific failure.
                if not ok_exit:
                    msg = (
                        f"Verification command #{idx + 1} failed: expected exit "
                        f"{expected_exit}, got {proc.returncode}."
                    )
                elif not ok_contains:
                    missing = [s for s in stdout_contains if s not in out]
                    msg = (
                        f"Verification command #{idx + 1} failed: expected "
                        f"output to contain {missing!r}."
                    )
                else:
                    forbidden = [s for s in stdout_not_contains if s in out]
                    msg = (
                        f"Verification command #{idx + 1} failed: output "
                        f"contained forbidden literal(s) {forbidden!r}."
                    )

                fix_hint = (
                    f"See .devlyn/spec-verify.results.json for the captured "
                    f"output. Update implementation so `{cmd}` matches the "
                    f"contract (exit_code={expected_exit}, "
                    f"contains={stdout_contains}, not_contains={stdout_not_contains})."
                )

                rule_id = (
                    "correctness.risk-probe-failed"
                    if is_risk_probe
                    else "correctness.spec-literal-mismatch"
                )
                criterion_ref = (
                    f"risk-probe:{vc.get('id')}"
                    if is_risk_probe
                    else f"spec-verify://verification_commands/{idx}"
                )
                file_ref = (
                    ".devlyn/risk-probes.jsonl"
                    if is_risk_probe
                    else ".devlyn/spec-verify.json"
                )
                if is_risk_probe:
                    fix_hint = (
                        f"Risk probe `{vc.get('id')}` derived from "
                        f"{vc.get('derived_from')!r} failed. See "
                        ".devlyn/spec-verify.results.json for captured output "
                        "and update the implementation to satisfy the visible "
                        "verification bullet."
                    )

                findings.append({
                    "id": f"{output_finding_prefix()}-{finding_seq:04d}",
                    "rule_id": rule_id,
                    "level": "error",
                    "severity": "CRITICAL",
                    "confidence": 1.0,
                    "message": msg,
                    "file": file_ref,
                    "line": 1,
                    "phase": output_phase(),
                    "criterion_ref": criterion_ref,
                    "fix_hint": fix_hint,
                    "blocking": True,
                    "status": "open",
                })
                finding_seq += 1

        except subprocess.TimeoutExpired:
            results.append({"index": idx, "cmd": cmd, "pass": False,
                            "reason": "timeout"})
            rule_id = (
                "correctness.risk-probe-failed"
                if vc.get("_risk_probe")
                else "correctness.spec-literal-mismatch"
            )
            findings.append({
                "id": f"{output_finding_prefix()}-{finding_seq:04d}",
                "rule_id": rule_id,
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": (
                    f"Verification command #{idx + 1} timed out after 60s."
                ),
                "file": ".devlyn/risk-probes.jsonl" if vc.get("_risk_probe") else ".devlyn/spec-verify.json",
                "line": 1,
                "phase": output_phase(),
                "criterion_ref": (
                    f"risk-probe:{vc.get('id')}"
                    if vc.get("_risk_probe")
                    else f"spec-verify://verification_commands/{idx}"
                ),
                "fix_hint": (
                    f"Command `{cmd}` exceeded 60s. Reduce work or fix a "
                    f"hang in the implementation."
                ),
                "blocking": True,
                "status": "open",
            })
            finding_seq += 1
        except Exception as e:  # noqa: BLE001 — surface any harness error explicitly
            results.append({"index": idx, "cmd": cmd, "pass": False,
                            "reason": f"error:{e.__class__.__name__}:{e}"})
            rule_id = (
                "correctness.risk-probe-failed"
                if vc.get("_risk_probe")
                else "correctness.spec-literal-mismatch"
            )
            findings.append({
                "id": f"{output_finding_prefix()}-{finding_seq:04d}",
                "rule_id": rule_id,
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": (
                    f"Verification command #{idx + 1} raised "
                    f"{e.__class__.__name__}: {e}."
                ),
                "file": ".devlyn/risk-probes.jsonl" if vc.get("_risk_probe") else ".devlyn/spec-verify.json",
                "line": 1,
                "phase": output_phase(),
                "criterion_ref": (
                    f"risk-probe:{vc.get('id')}"
                    if vc.get("_risk_probe")
                    else f"spec-verify://verification_commands/{idx}"
                ),
                "fix_hint": (
                    f"Command `{cmd}` could not be executed. Check the work-dir "
                    f"state and any environment setup the command requires."
                ),
                "blocking": True,
                "status": "open",
            })
            finding_seq += 1

    expected_findings, finding_seq = expected_contract_findings(
        expected_data,
        expected_path,
        work,
        devlyn_dir,
        state,
        finding_seq,
    )
    findings.extend(expected_findings)

    results_path.write_text(json.dumps({"commands": results}, indent=2) + "\n")

    # Append findings (jsonl). BUILD_GATE merge step concatenates this onto
    # build_gate.findings.jsonl; never overwrite the orchestrator's own gate
    # findings. Truncate this file each run since it is a per-round artifact.
    with findings_path.open("w") as fh:
        for f in findings:
            fh.write(json.dumps(f) + "\n")

    failed = [r for r in results if r.get("pass") is False]
    blocking_findings = [f for f in findings if f.get("severity") in {"CRITICAL", "HIGH"}]
    if failed or blocking_findings:
        print(
            f"[spec-verify] {len(failed)}/{len(results)} command(s) failed; "
            f"{len(findings)} finding(s) written to {findings_path}",
            file=sys.stderr,
        )
        return 1

    print(
        f"[spec-verify] all {len(results)} command(s) passed",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
