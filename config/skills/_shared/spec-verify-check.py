#!/usr/bin/env python3
"""Spec literal verification gate (iter-0019.6 + iter-0019.8 + iter-0019.9
carrier).

Default mode (VERIFY MECHANICAL invocation, no args):
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
      ```json``` block. Stage executable commands; an explicit pure-design
      contract removes stale `.devlyn/spec-verify.json` instead.
  (4) A generated source always has a json block: the PHASE 0 freeze refuses
      one without it (BLOCKED:invalid-classification) and its bytes are bound.
  (5) If no sibling/json block in source AND source.type=="spec": benchmark mode
      with a pre-staged file would have hit branch (1). Without the
      pre-staged file, benchmark falls through to no-op (rare — fixture
      mis-config). Real-user mode silent no-op + drops any stale
      pre-staged file (preserves iter-0019.6 backward compat for
      handwritten specs without the carrier).
- For each verification_commands entry and included risk probe, routes the
  command through the sibling `process-evidence.py` runner. Raw stdout/stderr,
  execution outcome, classification, and byte digests are written under the
  authenticated run/phase/round manifest; expectations retain
  run-fixture.sh's combined-stream matching semantics.

Check mode (`--check <markdown_path>`):
- Spec-source authoring preflight: a present sibling `spec.expected.json`
  takes precedence; otherwise validate the legacy inline carrier. Validate
  metadata against the given Markdown path, including non-canonical names.
- Exits 2 on malformed carrier or metadata, without falling back from a bad
  sibling to inline content. An absent sibling and sentinel retain opt-in
  success. Never stages or executes commands. Generated-source runtime has
  its own inline validation and must not use this sibling-precedence route.

Expected-contract check mode (`--check-expected <json_path>`):
- Used by /devlyn-ideate after writing sibling `spec.expected.json`.
- Exits 0 if the file is valid JSON and matches `_shared/expected.schema.json`
  shape, and if sibling `spec.md` has supported `complexity` frontmatter.
  Exits 2 on unreadable, malformed, unsupported fields, or unsupported sibling
  spec complexity.

Output:
- Findings go to `.devlyn/verify-mechanical.findings.jsonl` with
  `phase: verify` and `VERIFY-MECH-*` ids, which `verify-merge-findings.py`
  consumes directly.
- `.devlyn/spec-verify.results.json` points each result at its sealed raw
  streams and includes the validated process-evidence carrier.
- In a pipeline VERIFY span, the run first records the source snapshot in
  `.devlyn/source-seal.json`; `--seal` (after owner gates and artifact
  cleanup) seals it only when the source is unchanged since that snapshot.

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
- 1: at least one command failed, carrier malformed (invalid json/shape in a
  source or sibling carrier, or a pre-staged file failed shape validation),
  or a blocking expected-contract finding
  was emitted. Findings are written to
  `.devlyn/verify-mechanical.findings.jsonl`.
- 2: invocation error (unreadable spec-verify.json, missing markdown in
  --check mode, etc.) or explicit evidence-backed
  `BLOCKED:build-env-underprovisioned` capability denial.
"""

from __future__ import annotations

import contextlib
import runpy
import importlib.util
import json
import hashlib
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


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


MECHANICAL_PHASE = "verify"
FINDINGS_NAME = "verify-mechanical.findings.jsonl"
FINDING_PREFIX = "VERIFY-MECH"
SEAL_NAME = "source-seal.json"
_PROCESS_EVIDENCE_MODULE = None


def process_evidence_module():
    global _PROCESS_EVIDENCE_MODULE
    if _PROCESS_EVIDENCE_MODULE is None:
        module_path = Path(__file__).with_name("process-evidence.py")
        spec = importlib.util.spec_from_file_location("devlyn_process_evidence", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load process evidence runner: {module_path}")
        module = importlib.util.module_from_spec(spec)
        previous_bytecode_setting = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = previous_bytecode_setting
        _PROCESS_EVIDENCE_MODULE = module
    return _PROCESS_EVIDENCE_MODULE


def mechanical_evidence_identity(state: dict, runner) -> tuple[str, str, int, str]:
    phase = MECHANICAL_PHASE
    run_id = state.get("run_id")
    phase_state = (state.get("phases") or {}).get(phase)
    round_ = phase_state.get("round") if isinstance(phase_state, dict) else None
    invalid_identity = (
        not isinstance(run_id, str)
        or runner.ID_RE.fullmatch(run_id) is None
        or isinstance(round_, bool)
        or not isinstance(round_, int)
        or round_ < 0
    )
    if invalid_identity and state.get("version") == "3.0":
        raise runner.EvidenceError(
            f"schema-v3 MECHANICAL evidence identity is invalid for phase {phase}"
        )
    if invalid_identity:
        # Standalone/benchmark invocations predate pipeline run identity. Keep
        # them evidence-backed without letting one process reuse another's
        # manifest. Real pipeline runs always take the authenticated branch.
        run_id = f"standalone-{os.getpid()}"
        round_ = 0
    identity = {"run_id": run_id, "phases": {phase: {"round": round_}}}
    return phase, run_id, round_, runner.manifest_relative_path(identity, phase)


def mechanical_obligation(vc: dict, idx: int, phase: str) -> dict:
    evidence_id = (
        f"risk-probe-{idx + 1:04d}"
        if vc.get("_risk_probe")
        else f"verification-command-{idx + 1:04d}"
    )
    return {
        "id": evidence_id,
        "phase": phase,
        "cmd": vc["cmd"],
        "exit_code": vc.get("exit_code", 0),
        "timeout_sec": verification_timeout_sec(vc),
        "stdout_contains": vc.get("stdout_contains", []) or [],
        "stdout_not_contains": vc.get("stdout_not_contains", []) or [],
    }


def capture_mechanical_command(
    runner, work: Path, manifest_path: Path, run_id: str, phase: str,
    round_: int, obligation: dict,
) -> dict:
    saved = os.environ.get("BENCH_WORKDIR")
    os.environ["BENCH_WORKDIR"] = str(work)
    try:
        return runner.capture_process(
            work, manifest_path, run_id, phase, round_, obligation,
        )
    finally:
        if saved is None:
            os.environ.pop("BENCH_WORKDIR", None)
        else:
            os.environ["BENCH_WORKDIR"] = saved


VERIFICATION_SECTION_RE = re.compile(
    r'(?ms)^<!--[ \t]*devlyn:verification[ \t]*-->[ \t]*\n(#{1,6}[ \t]+[^\n]*\n.*?)(?=^#{1,6}[ \t]+|\Z)'
)
FILES_TO_TOUCH_SECTION_RE = re.compile(
    r'(?ms)^<!--[ \t]*devlyn:authorized-surface[ \t]*-->[ \t]*\n(#{1,6}[ \t]+[^\n]*\n.*?)(?=^#{1,6}[ \t]+|\Z)'
)
JSON_FENCE_RE = re.compile(r'(?ms)^```json[ \t]*\n(.*?)\n```[ \t]*$')
FORBIDDEN_RISK_PROBE_CMD_RE = re.compile(
    r'BENCH_FIXTURE_DIR|benchmark/auto-resolve/fixtures|/verifiers/|verifiers/'
)
EXTERNAL_URL_RE = re.compile(r"https?://([^/\s\"']+)", re.IGNORECASE)
RISK_PROBE_SCRIPT_RE = re.compile(
    r'(?<![\w./-])(?:\./)?(\.devlyn/probes/[A-Za-z0-9][A-Za-z0-9._/-]*)'
)
RISK_PROBE_RAW_REF = ".devlyn/probes/"
RISK_PROBE_INTEGRITY_FIX_HINT = (
    "Probe artifacts changed after PHASE 1.5. Only the orchestrator may regenerate probes: "
    "re-run probe validation and re-write state.risk_probes_digest; workers must never modify "
    ".devlyn/risk-probes.jsonl or .devlyn/probes/."
)
INLINE_JSON_OBJECT_RE = re.compile(r'`?\{\s*"[^"\n]+"\s*:', re.IGNORECASE)
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
    "release_recovery",
    "physical_alias",
    "fixture_cleanup",
    "temp_file_preservation",
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
    "release_recovery": {
        "failure_injected_after_acquire_or_publish",
        "asserts_resource_released_or_restored_after_failure",
        "asserts_next_operation_succeeds_after_failure",
    },
    "physical_alias": {
        "same_target_reached_through_distinct_paths",
        "asserts_alias_resolved_to_one_physical_target",
    },
    "fixture_cleanup": {
        "exercises_failure_or_timeout_exit",
        "asserts_created_artifacts_absent",
    },
    "temp_file_preservation": {
        "preexisting_file_at_colliding_path",
        "exclusive_create_collision_exercised",
        "asserts_preexisting_bytes_unchanged",
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
    "pure_design",
    "required_risk_probe_requirements",
}
EXPECTED_VERIFICATION_COMMAND_KEYS = {
    "cmd",
    "exit_code",
    "timeout_sec",
    "stdout_contains",
    "stdout_not_contains",
    "contract_refs",
}
DEFAULT_TIMEOUT_SEC = 60
SPEC_COMPLEXITY_VALUES = {"trivial", "medium", "high", "large"}


def verification_timeout_sec(command: dict) -> int:
    return command.get("timeout_sec", DEFAULT_TIMEOUT_SEC)


def extract_verification_block(text: str) -> tuple[bool, str | None]:
    """Locate the verification section via the `<!-- devlyn:verification -->`
    sentinel (language-neutral — the human-readable heading after it may be
    any text, any language, any ATX heading level 1-6) and return
    (section_found, json_block).

    section_found=False: the sentinel is absent entirely — a legitimate
    handwritten spec with no mechanical verification contract. Callers treat
    this as a silent no-op, matching pre-existing backward compat.

    section_found=True, json_block=None: the sentinel is present (the author
    clearly intended a verification section) but no fenced ```json``` block
    was found inside it — this is a malformed carrier, not a no-op.
    """
    section = VERIFICATION_SECTION_RE.search(text)
    if not section:
        return (False, None)
    fence = JSON_FENCE_RE.search(section.group(1))
    return (True, fence.group(1) if fence else None)


def extract_verification_text(text: str) -> str:
    section = VERIFICATION_SECTION_RE.search(text)
    return section.group(1) if section else ""


def extract_authorized_surface_block(text: str) -> tuple[bool, str | None]:
    """Locate PLAN's `Files to touch` section via the
    `<!-- devlyn:authorized-surface -->` sentinel and return
    (section_found, json_block) — same semantics as
    `extract_verification_block()`."""
    section = FILES_TO_TOUCH_SECTION_RE.search(text)
    if not section:
        return (False, None)
    fence = JSON_FENCE_RE.search(section.group(1))
    return (True, fence.group(1) if fence else None)


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


def external_url_hosts(text: str) -> list[str]:
    hosts: list[str] = []
    for match in EXTERNAL_URL_RE.finditer(text or ''):
        host = match.group(1).split('@')[-1].split(':')[0].lower()
        if host not in LOCAL_URL_HOSTS and host not in hosts:
            hosts.append(host)
    return hosts


def referenced_risk_probe_scripts(cmd: str) -> list[str]:
    scripts: list[str] = []
    for match in RISK_PROBE_SCRIPT_RE.finditer(cmd or ""):
        path = match.group(1)
        if path not in scripts:
            scripts.append(path)
    return scripts


def unrecognized_risk_probe_reference(cmd: str) -> str | None:
    command = cmd or ""
    matches = list(RISK_PROBE_SCRIPT_RE.finditer(command))
    offset = command.find(RISK_PROBE_RAW_REF)
    while offset >= 0:
        if not any(
            match.start() <= offset and offset + len(RISK_PROBE_RAW_REF) <= match.end()
            for match in matches
        ):
            tail = command[offset:].split(maxsplit=1)[0][:80]
            return (
                f"unrecognized probe script reference {tail!r}; write it as "
                ".devlyn/probes/<file> (a ./ prefix is the only alias)"
            )
        offset = command.find(RISK_PROBE_RAW_REF, offset + len(RISK_PROBE_RAW_REF))
    return None


def validate_risk_probe_scripts(cmd: str, index: int, work: Path) -> str | None:
    unrecognized = unrecognized_risk_probe_reference(cmd)
    if unrecognized:
        return f"risk-probes[{index}].cmd has {unrecognized}"
    for rel_path in referenced_risk_probe_scripts(cmd):
        path = Path(rel_path)
        if ".." in path.parts:
            return f"risk-probes[{index}].cmd references invalid probe script path: {rel_path}"
        script_path = work / path
        if not script_path.is_file():
            return f"risk-probes[{index}].cmd references missing probe script: {rel_path}"
        try:
            content = script_path.read_text(encoding="utf-8")
        except OSError as e:
            return f"risk-probes[{index}].cmd references unreadable probe script {rel_path}: {e}"
        if FORBIDDEN_RISK_PROBE_CMD_RE.search(content):
            return (
                f"risk-probes[{index}].cmd references {rel_path}, whose content "
                "references hidden fixture/verifier paths; risk probes must "
                "derive from visible spec text only"
            )
        external_hosts = external_url_hosts(content)
        if external_hosts:
            return (
                f"risk-probes[{index}].cmd references {rel_path}, whose content "
                f"references external URL(s): {', '.join(external_hosts)}; "
                "use only worktree-local or localhost resources"
            )
    return None


def risk_probe_script_path(work: Path, rel_path: str) -> tuple[Path | None, str | None]:
    path = Path(rel_path)
    if path.is_absolute() or ".." in path.parts:
        return (None, f"referenced probe script path is invalid: {rel_path}")
    script_path = work / path
    if not script_path.is_file():
        return (None, f"referenced probe script is missing: {rel_path}")
    return (script_path, None)


def risk_probes_digest(devlyn_dir: Path) -> tuple[str | None, str | None]:
    probes_path = devlyn_dir / "risk-probes.jsonl"
    if not probes_path.is_file():
        return (None, "missing .devlyn/risk-probes.jsonl")
    try:
        probes_bytes = probes_path.read_bytes()
    except OSError as e:
        return (None, f"cannot read .devlyn/risk-probes.jsonl: {e}")
    try:
        probes_text = probes_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        return (None, f".devlyn/risk-probes.jsonl is not UTF-8: {e}")

    scripts: set[str] = set()
    for index, line in enumerate(probes_text.splitlines()):
        if not line.strip():
            continue
        try:
            probe = loads_strict_json(line)
        except ValueError as e:
            return (None, f"risk-probes[{index}] invalid JSON: {e}")
        cmd = probe.get("cmd") if isinstance(probe, dict) else ""
        unrecognized = unrecognized_risk_probe_reference(cmd)
        if unrecognized:
            return (None, f"risk-probes[{index}].cmd has {unrecognized}")
        scripts.update(referenced_risk_probe_scripts(cmd))

    digest = hashlib.sha256()
    digest.update(b".devlyn/risk-probes.jsonl\0")
    digest.update(probes_bytes)
    digest.update(b"\0")
    for rel_path in sorted(scripts):
        script_path, path_error = risk_probe_script_path(devlyn_dir.parent, rel_path)
        if path_error:
            return (None, path_error)
        assert script_path is not None
        try:
            script_bytes = script_path.read_bytes()
        except OSError as e:
            return (None, f"cannot read {rel_path}: {e}")
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(script_bytes)
        digest.update(b"\0")
    return (digest.hexdigest(), None)


def risk_probe_integrity_error(state: dict, devlyn_dir: Path) -> str | None:
    if not state_requires_risk_probes(state) and not (devlyn_dir / "risk-probes.jsonl").is_file():
        return None
    expected = state.get("risk_probes_digest")
    if not isinstance(expected, str) or not expected.strip():
        return "pipeline.state.json risk_probes_digest is required when risk probes are enabled or present"
    actual, digest_error = risk_probes_digest(devlyn_dir)
    if digest_error:
        return digest_error
    assert actual is not None
    expected = expected.strip()
    if expected != actual:
        return f"pipeline.state.json risk_probes_digest mismatch: expected {expected}, actual {actual}"
    return None


def validate_shape(data) -> str | None:
    """Return None if shape matches the canonical verification_commands
    schema; else a human-readable error string.

    Schema (iter-0019.8): top-level object with a non-empty
    `verification_commands` list of objects. Each object requires a
    non-empty string `cmd`; `exit_code` defaults to 0 and must be a
    non-bool int; `timeout_sec` defaults to DEFAULT_TIMEOUT_SEC and must be a
    non-bool int from 1 through 600; `stdout_contains` and
    `stdout_not_contains` default to empty list and must be lists of strings.
    Bool is rejected explicitly because Python's `bool` subclasses `int` —
    `isinstance(True, int) is True` would otherwise let numeric fields accept
    true.
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
        timeout_sec = c.get("timeout_sec", DEFAULT_TIMEOUT_SEC)
        if (
            isinstance(timeout_sec, bool)
            or not isinstance(timeout_sec, int)
            or not 1 <= timeout_sec <= 600
        ):
            return f"verification_commands[{i}].timeout_sec must be int from 1 to 600 (not bool)"
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
    to catch malformed ideate output before /devlyn-resolve consumes it.
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
    if "pure_design" in data and not isinstance(data["pure_design"], bool):
        return "pure_design must be a boolean"
    requirements = data.get("required_risk_probe_requirements", [])
    if not isinstance(requirements, list):
        return "required_risk_probe_requirements must be a list"
    for i, requirement in enumerate(requirements):
        if not isinstance(requirement, dict):
            return f"required_risk_probe_requirements[{i}] must be an object"
        unknown_requirement_keys = sorted(set(requirement) - {"tag", "derived_from"})
        if unknown_requirement_keys:
            return (
                f"required_risk_probe_requirements[{i}] unknown key(s): "
                f"{', '.join(unknown_requirement_keys)}"
            )
        tag = requirement.get("tag")
        if not isinstance(tag, str) or tag not in RISK_PROBE_TAGS:
            return f"required_risk_probe_requirements[{i}].tag must be one of: {', '.join(sorted(RISK_PROBE_TAGS))}"
        derived_from = requirement.get("derived_from")
        if not isinstance(derived_from, str) or not derived_from:
            return f"required_risk_probe_requirements[{i}].derived_from must be a non-empty string"
    cap_error = requirement_cap_error(requirements)
    if cap_error:
        return cap_error
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


def validate_inline_shape(data: object) -> str | None:
    if isinstance(data, dict):
        unknown = sorted(set(data) - {"verification_commands", "pure_design", "required_risk_probe_requirements"})
        if unknown:
            return (
                f"unsupported inline key(s): {', '.join(unknown)}; inline carriers "
                "support only verification_commands, pure_design and required_risk_probe_requirements. "
                "Encode these checks as commands, or use a real spec with sibling spec.expected.json."
            )
    error = validate_expected_shape(data)
    if error:
        return error
    if isinstance(data, dict) and data.get("pure_design") is True:
        if data.get("verification_commands") != []:
            return "inline pure_design: true requires an explicit empty verification_commands list"
        return None
    return validate_shape(data)


def validate_expected_against_sibling_spec(spec_path: Path, data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    if not spec_path.is_file():
        return None
    commands = data.get("verification_commands", [])
    pure_design = data.get("pure_design") is True
    if commands:
        if pure_design:
            return 'pure_design: true is contradictory with a non-empty verification_commands'
        return None
    if pure_design:
        return None
    return (
        'verification_commands must contain at least one entry unless '
        'spec.expected.json declares "pure_design": true'
    )


def validate_sibling_spec_complexity(spec_path: Path) -> str | None:
    if not spec_path.is_file():
        return None
    try:
        spec_text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return None
    return validate_present_spec_complexity(spec_text)


def validate_risk_probe(
    probe: object,
    index: int,
    verification_text: str,
    work: Path,
) -> str | None:
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
    script_err = validate_risk_probe_scripts(cmd, index, work)
    if script_err:
        return script_err
    if len(cmd) > 4000:
        return f"risk-probes[{index}].cmd exceeds 4000 characters"
    tags = probe.get("tags")
    if not isinstance(tags, list) or not tags or not all(isinstance(t, str) for t in tags):
        return f"risk-probes[{index}].tags must be a non-empty list of strings"
    unknown_tags = sorted(set(tags) - RISK_PROBE_TAGS)
    if unknown_tags:
        return f"risk-probes[{index}].tags contains unknown tag(s): {', '.join(unknown_tags)}"
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
    if "shape_contract" in tags:
        actual = evidence.get("shape_contract")
        if not isinstance(actual, list) or not all(isinstance(item, str) for item in actual):
            return f"risk-probes[{index}].tag_evidence.shape_contract must be a list of strings"
        required_shape = set(SHAPE_CONTRACT_REQUIRED_EVIDENCE)
        if "visible_text_names_exact_json_error_object" in set(actual):
            required_shape.add("asserts_exact_error_object")
        missing_shape = sorted(required_shape - set(actual))
        if missing_shape:
            return (
                f"risk-probes[{index}].tag_evidence.shape_contract missing required "
                f"item(s): {', '.join(missing_shape)}"
            )
    return None


MAX_RISK_PROBES = 3


def requirement_cap_error(requirements: list) -> str | None:
    bullets = {item.get("derived_from") for item in requirements if isinstance(item, dict)}
    if len(bullets) > MAX_RISK_PROBES:
        return (f"required_risk_probe_requirements names {len(bullets)} distinct derived_from bullets; "
                f"a run derives at most {MAX_RISK_PROBES} probes, one bullet each")
    return None


def validate_required_risk_probe_requirement(
    requirement: object, index: int, verification_text: str,
) -> str | None:
    if not isinstance(requirement, dict):
        return f"required_risk_probe_requirements[{index}] must be a JSON object"
    unknown = sorted(set(requirement) - {"tag", "derived_from"})
    if unknown:
        return f"required_risk_probe_requirements[{index}] unknown key(s): {', '.join(unknown)}"
    tag = requirement.get("tag")
    if not isinstance(tag, str) or tag not in RISK_PROBE_TAGS:
        return (
            f"required_risk_probe_requirements[{index}].tag must be one of: "
            f"{', '.join(sorted(RISK_PROBE_TAGS))}"
        )
    derived_from = requirement.get("derived_from")
    if not isinstance(derived_from, str) or not derived_from.strip():
        return f"required_risk_probe_requirements[{index}].derived_from must be a non-empty string"
    if derived_from not in verification_text:
        return (
            f"required_risk_probe_requirements[{index}].derived_from must be an "
            "exact substring of the source verification section"
        )
    return None


def resolve_required_risk_probe_requirements(
    source_md: Path | None,
) -> tuple[list[dict], str | None]:
    """Return the spec author's declared `required_risk_probe_requirements`
    (a language-neutral replacement for a keyword-prose classifier): a list
    of `{"tag": ..., "derived_from": ...}` obligations that risk-probes.jsonl
    must cover when risk probes are required. Resolved from whichever
    carrier `verification_commands` itself would come from — sibling
    `spec.expected.json` wins when present, else the inline fenced block
    under source_md's `<!-- devlyn:verification -->` sentinel. Absence in
    either carrier is not an error: it means the spec author declared no
    required risk-probe obligations, not that none apply.
    """
    if source_md is None or not source_md.is_file():
        return ([], None)
    expected_path = source_md.with_name("spec.expected.json")
    if expected_path.is_file():
        data, err = load_expected_contract(expected_path)
        if err:
            return ([], err)
        reqs = (data or {}).get("required_risk_probe_requirements", [])
    else:
        _section_found, block = extract_verification_block(source_md.read_text(encoding="utf-8"))
        if block is None:
            return ([], None)
        try:
            parsed = loads_strict_json(block)
        except ValueError as e:
            return ([], f"<!-- devlyn:verification --> ```json``` block in {source_md} has invalid JSON: {e}")
        reqs = parsed.get("required_risk_probe_requirements", []) if isinstance(parsed, dict) else []
    if not isinstance(reqs, list):
        return ([], "required_risk_probe_requirements must be a list")
    verification_text = extract_verification_text(source_md.read_text(encoding="utf-8"))
    for i, req in enumerate(reqs):
        err = validate_required_risk_probe_requirement(req, i, verification_text)
        if err:
            return ([], err)
    cap_error = requirement_cap_error(reqs)
    if cap_error:
        return ([], cap_error)
    return (reqs, None)


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

    verification_text = extract_verification_text(source_md.read_text(encoding="utf-8"))
    if not verification_text:
        return ([], "risk-probes.jsonl exists but source has no <!-- devlyn:verification --> section")

    probes: list[dict] = []
    for index, line in enumerate(probes_path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            probe = loads_strict_json(line)
        except ValueError as e:
            return ([], f"risk-probes[{index}] invalid JSON: {e}")
        err = validate_risk_probe(probe, index, verification_text, devlyn_dir.parent)
        if err:
            return ([], err)
        normalized = dict(probe)
        normalized["_risk_probe"] = True
        normalized["_risk_probe_index"] = index
        probes.append(normalized)
        if len(probes) > MAX_RISK_PROBES:
            return ([], f"risk-probes.jsonl has more than {MAX_RISK_PROBES} probes")
    if require_present and not probes:
        return ([], "risk-probes.jsonl must contain at least one probe")
    if require_present:
        required_reqs, req_err = resolve_required_risk_probe_requirements(source_md)
        if req_err:
            return ([], req_err)
        missing = [
            req for req in required_reqs
            if not any(
                req["tag"] in probe.get("tags", []) and probe.get("derived_from") == req["derived_from"]
                for probe in probes
            )
        ]
        if missing:
            formatted = "; ".join(f"{r['tag']} (derived_from={r['derived_from']!r})" for r in missing)
            return ([], f"risk-probes.jsonl missing required probe(s): {formatted}")
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
        state = loads_strict_json(state_path.read_text(encoding="utf-8"))
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
        data = loads_strict_json(state_path.read_text(encoding="utf-8"))
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
    src = state.get("source") if isinstance(state.get("source"), dict) else {}
    if source_md is None:
        if src_type == "generated":
            return f"source.criteria_path must identify an existing generated criteria file; declared path: {src.get('criteria_path')!r}."
        return None
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
    return expected_contract_error(src, source_md) if src_type == "spec" else None


def expected_contract_error(src: dict, spec_md: Path) -> str | None:
    """A sibling spec.expected.json must still be the bytes bootstrap bound, or still no directory entry at all."""
    if "expected_sha256" not in src:
        return None  # a state from before the binding existed
    sibling = spec_md.with_name("spec.expected.json")
    if src["expected_sha256"] is None:
        # A directory or a dangling symlink is an entry too; an access error is reported, never taken for absence.
        try:
            present = _present(sibling)
        except OSError as e:
            return f"cannot inspect {sibling}, whose absence bootstrap bound: {e}."
        return f"source.expected_sha256 mismatch for {sibling}: bootstrap bound its absence, but an entry exists." if present else None
    actual = _file_sha256(sibling)
    if actual != src["expected_sha256"]:
        return f"source.expected_sha256 mismatch for {sibling}: expected {src['expected_sha256']}, actual {actual}."
    return None


def load_expected_contract(expected_path: Path) -> tuple[dict | None, str | None]:
    try:
        data = loads_strict_json(expected_path.read_text(encoding="utf-8"))
    except ValueError as e:
        return (None, f"{expected_path} has invalid JSON: {e}")
    except OSError as e:
        return (None, f"{expected_path} is unreadable: {e}")
    err = validate_expected_shape(data)
    if err:
        return (None, f"{expected_path}: {err}")
    return (data, None)


def stage_from_source(md: Path, devlyn_dir: Path) -> tuple[bool, bool, str | None]:
    """Materialize .devlyn/spec-verify.json from the json block in `md`.

    Returns (found, staged, error). found=False means no sentinel. A present
    sentinel without a valid fenced JSON contract returns an error. A valid
    pure-design contract removes stale staging and returns (True, False, None);
    executable commands return (True, True, None) after writing spec-verify.json.
    """
    section_found, block = extract_verification_block(md.read_text(encoding="utf-8"))
    if not section_found:
        return (False, False, None)
    if block is None:
        return (True, False, f"`<!-- devlyn:verification -->` section in {md} has no fenced ```json``` block")
    try:
        data = loads_strict_json(block)
    except ValueError as e:
        return (True, False, f"`<!-- devlyn:verification -->` ```json``` block in {md} has invalid JSON: {e}")
    err = validate_inline_shape(data)
    if err:
        return (True, False, f"`<!-- devlyn:verification -->` ```json``` block in {md}: {err}")
    if data["verification_commands"] == []:
        (devlyn_dir / "spec-verify.json").unlink(missing_ok=True)
        return (True, False, None)
    normalized = {"verification_commands": data["verification_commands"]}
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / "spec-verify.json").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return (True, True, None)


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
    err = validate_sibling_spec_complexity(md) or validate_expected_against_sibling_spec(md, data)
    if err:
        return (True, False, f"{expected_path}: {err}", expected_path, None)
    commands = data.get("verification_commands")
    if not commands:
        spec_path = devlyn_dir / "spec-verify.json"
        if spec_path.exists():
            spec_path.unlink()
        return (True, False, None, expected_path, data)
    normalized = {"verification_commands": commands}
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / "spec-verify.json").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    return (True, True, None, expected_path, data)


def write_malformed_finding(
    devlyn_dir: Path,
    error: str,
    source_path: Path | None,
    *,
    fix_hint: str | None = None,
) -> None:
    """Emit a single CRITICAL finding for a malformed verification carrier."""
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    findings_path = devlyn_dir / FINDINGS_NAME
    file_ref = str(source_path) if source_path else ".devlyn/pipeline.state.json"
    finding = {
        "id": f"{FINDING_PREFIX}-0001",
        "rule_id": "correctness.spec-verify-malformed",
        "level": "error",
        "severity": "CRITICAL",
        "confidence": 1.0,
        "message": f"Verification contract carrier is malformed: {error}",
        "file": file_ref,
        "line": 1,
        "phase": MECHANICAL_PHASE,
        "criterion_ref": "spec-verify://carrier",
        "fix_hint": fix_hint if fix_hint is not None else (
            "Fix the sibling `spec.expected.json` file or the `## Verification` "
            "```json``` block: a JSON object with a non-empty `verification_commands` array of "
            "{cmd, exit_code?, stdout_contains?, stdout_not_contains?} "
            "entries. See references/phases/mechanical.md."
        ),
        "blocking": True,
        "status": "open",
    }
    with findings_path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps(finding) + "\n")


def write_risk_probe_integrity_finding(devlyn_dir: Path, error: str) -> None:
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    findings_path = devlyn_dir / FINDINGS_NAME
    finding = {
        "id": f"{FINDING_PREFIX}-0001",
        "rule_id": "correctness.risk-probe-integrity",
        "level": "error",
        "severity": "CRITICAL",
        "confidence": 1.0,
        "message": f"Risk probe artifact integrity check failed: {error}.",
        "file": ".devlyn/risk-probes.jsonl",
        "line": 1,
        "phase": MECHANICAL_PHASE,
        "criterion_ref": "risk-probes://digest",
        "fix_hint": RISK_PROBE_INTEGRITY_FIX_HINT,
        "blocking": True,
        "status": "open",
    }
    with findings_path.open("w", encoding="utf-8") as fh:
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


def diff_text_for_expected(work: Path, devlyn_dir: Path, state: dict,
                           sparse_absences: frozenset[str] = frozenset()) -> tuple[str, str | None]:
    external_diff = devlyn_dir / "external-diff.patch"
    if external_diff.is_file():
        try:
            return (external_diff.read_text(encoding="utf-8", errors="surrogateescape"), None)
        except OSError as e:
            return ("", f"cannot read {external_diff}: {e}")
    base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
    try:
        with observed_git(work, sparse_absences) as (git, _flags):
            return (git("diff", "--ignore-submodules=none", *([base_sha] if base_sha else [])).decode("utf-8", "surrogateescape"), None)
    except (OSError, ValueError) as exc:
        return ("", str(exc) or "git diff failed")


def count_deps_added(work: Path, state: dict, sparse_absences: frozenset[str] = frozenset()) -> int:
    base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
    try:
        with observed_git(work, sparse_absences) as (git, _flags):
            diff = git("diff", *([base_sha] if base_sha else []), "--", "package.json").decode("utf-8", "surrogateescape")
    except (OSError, ValueError):
        return 0
    in_deps = False
    count = 0
    for line in diff.splitlines():
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


def changed_files(work: Path, state: dict, devlyn_dir: Path,
                  sparse_absences: frozenset[str] = frozenset()) -> tuple[list[str], str | None]:
    external_diff = devlyn_dir / "external-diff.patch"
    if external_diff.is_file():
        names: list[str] = []
        try:
            external_bytes = external_diff.read_bytes()
        except OSError as error:
            return ([], f"cannot read {external_diff}: {error}")
        if not external_bytes:
            return ([], None)
        # Prefix depth is otherwise ambiguous (src/x becomes x with -p1).
        headers = [line for line in external_bytes.split(b"\n") if line.startswith(b"diff --git ")]
        if not headers or any(not re.fullmatch(
            rb'diff --git (a/[^"\r]*|"a/(?:[^"\\]|\\.)*") (b/[^"\r]*|"b/(?:[^"\\]|\\.)*")\r?', line,
        ) for line in headers):
            return ([], "external diff requires Git a/ and b/ path prefixes; regenerate with git diff --binary --src-prefix=a/ --dst-prefix=b/")
        # Statistics mode never applies the patch. Reverse parsing includes
        # rename sources as well as destinations without parsing quoted headers.
        for direction in ([], ["--reverse"]):
            proc = subprocess.run(
                ["git", "apply", "--numstat", "-z", "-p1", "--whitespace=nowarn", *direction], cwd=str(work),
                input=external_bytes, capture_output=True,
            )
            if proc.returncode != 0:
                return ([], (proc.stderr or proc.stdout).decode("utf-8", "replace").strip() or "git apply --numstat failed")
            for record in proc.stdout.split(b"\0"):
                if record:
                    fields = record.split(b"\t", 2)
                    if len(fields) != 3 or not fields[2]:
                        return ([], "invalid git apply --numstat path record")
                    names.append(fields[2].decode("utf-8", "surrogateescape"))
        return (list(dict.fromkeys(names)), None)
    base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
    try:
        with observed_git(work, sparse_absences) as (git, _flags):
            raw = git("diff", "--name-only", "-z", "--no-renames", "--ignore-submodules=none",
                      *([base_sha] if base_sha else []))
    except (OSError, ValueError) as exc:
        return ([], str(exc) or "git diff --name-only failed")
    return ([path.decode("utf-8", "surrogateescape") for path in raw.split(b"\0") if path], None)


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
    # Observed like the scope check: the baseline's sparse absences are not deletions.
    _baseline, sparse_absences, baseline_error = load_untracked_baseline(devlyn_dir)
    if (devlyn_dir / "external-diff.patch").is_file():
        baseline_error = None
    diff_text, diff_error = ("", baseline_error) if baseline_error else diff_text_for_expected(work, devlyn_dir, state, sparse_absences)
    paths, paths_error = [], None
    if expected_data.get("forbidden_files"):
        paths, paths_error = ([], baseline_error) if baseline_error else changed_files(work, state, devlyn_dir, sparse_absences)
    diff_error = diff_error or paths_error
    if diff_error and (
        expected_data.get("forbidden_patterns") or expected_data.get("forbidden_files")
    ):
        findings.append({
            "id": f"{FINDING_PREFIX}-{seq:04d}",
            "rule_id": "correctness.expected-contract-unverifiable",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Cannot compute diff for expected contract: {diff_error}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": MECHANICAL_PHASE,
            "criterion_ref": "spec.expected.json/forbidden_files" if paths_error else "spec.expected.json/forbidden_patterns",
            "fix_hint": "Ensure base_ref.sha is valid and any external-diff.patch is a readable Git patch with a/ and b/ prefixes.",
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
            "id": f"{FINDING_PREFIX}-{seq:04d}",
            "rule_id": "correctness.forbidden-pattern",
            "level": "error" if is_disqualifier else "warning",
            "severity": "CRITICAL" if is_disqualifier else "MEDIUM",
            "confidence": 1.0,
            "message": pattern.get("description") or f"Forbidden pattern matched: {pattern['pattern']}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": MECHANICAL_PHASE,
            "criterion_ref": f"spec.expected.json/forbidden_patterns/{i}",
            "fix_hint": "Remove the forbidden diff pattern or change the spec.expected.json contract explicitly.",
            "blocking": is_disqualifier,
            "status": "open",
        })
        seq += 1
    changed = set(paths)
    for i, required in enumerate(expected_data.get("required_files", []) or []):
        if (work / required).exists():
            continue
        findings.append({
            "id": f"{FINDING_PREFIX}-{seq:04d}",
            "rule_id": "correctness.required-file-missing",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Required file is missing: {required}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": MECHANICAL_PHASE,
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
            "id": f"{FINDING_PREFIX}-{seq:04d}",
            "rule_id": "scope.forbidden-file-touched",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Forbidden file appears in the diff: {forbidden}",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": MECHANICAL_PHASE,
            "criterion_ref": f"spec.expected.json/forbidden_files/{i}",
            "fix_hint": "Remove that file from the diff or update the expected contract.",
            "blocking": True,
            "status": "open",
        })
        seq += 1
    max_deps = expected_data.get("max_deps_added", 0)
    deps_added = count_deps_added(work, state, sparse_absences)
    if deps_added > max_deps:
        findings.append({
            "id": f"{FINDING_PREFIX}-{seq:04d}",
            "rule_id": "scope.max-deps-added-exceeded",
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": f"Added {deps_added} package dependencies; max_deps_added is {max_deps}.",
            "file": str(expected_path or "spec.expected.json"),
            "line": 1,
            "phase": MECHANICAL_PHASE,
            "criterion_ref": "spec.expected.json/max_deps_added",
            "fix_hint": "Remove the new dependency or explicitly license it in spec.expected.json.",
            "blocking": True,
            "status": "open",
        })
        seq += 1
    return (findings, seq)


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


def validate_authorized_surface_shape(data: object) -> str | None:
    if not isinstance(data, dict):
        return "top-level must be a JSON object"
    err = validate_string_list(data, "authorized_surface")
    if err:
        return err
    surface = data.get("authorized_surface", [])
    if not surface:
        return "authorized_surface must contain at least one entry"
    seen: set[str] = set()
    for entry in surface:
        if entry in seen:
            return f"authorized_surface has a duplicate entry: {entry!r}"
        seen.add(entry)
        if entry == "." or entry.startswith("/") or entry.startswith("./"):
            return (
                "authorized_surface entry must be a repo-relative path "
                f"without a leading '/' or './': {entry!r}"
            )
        stem = entry[:-3] if entry.endswith("/**") else entry
        if entry.endswith("/**") and not stem:
            return f"authorized_surface directory grant needs a non-empty prefix before '/**': {entry!r}"
        if ".." in stem.split("/"):
            return f"authorized_surface entry must not contain '..': {entry!r}"
        brace_error = validate_surface_brace_glob(entry)
        if brace_error is not None:
            return brace_error
    return None


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
            elif path.rstrip("/") == expanded.rstrip("/"):  # a nested repository: `dir/` untracked, `dir` as a gitlink
                return True
    return False


def is_devlyn_path(path: str) -> bool:
    return path == ".devlyn" or path.startswith(".devlyn/")


STATUS_ARGS = ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none")


def git_status_entries(work: Path, sparse_absences: frozenset[str] = frozenset()) -> tuple[list[tuple[str, str]], str | None]:
    try:
        with observed_git(work, sparse_absences) as (git, _flags):
            return parse_status(git(*STATUS_ARGS))
    except (OSError, ValueError) as exc:
        return ([], str(exc) or "git status failed")


def parse_status(raw: bytes) -> tuple[list[tuple[str, str]], str | None]:
    entries: list[tuple[str, str]] = []
    fields = raw.split(b"\0")
    i = 0
    while i < len(fields):
        raw = fields[i]
        i += 1
        if not raw:
            continue
        if len(raw) < 4:
            return ([], f"unexpected git status record: {raw!r}")
        status = raw[:2].decode("utf-8", "surrogateescape")
        path = raw[3:].decode("utf-8", "surrogateescape")
        entries.append((status, path))
        if ("R" in status or "C" in status) and i < len(fields) and fields[i]:
            old_path = fields[i].decode("utf-8", "surrogateescape")
            i += 1
            entries.append(("D ", old_path))
    return (entries, None)


def current_untracked_files(work: Path, sparse_absences: frozenset[str]) -> tuple[set[str], str | None]:
    entries, error = git_status_entries(work, sparse_absences)
    if error:
        return (set(), error)
    return ({path for status, path in entries if status == "??" and not is_devlyn_path(path)}, None)


EMPTY_BASELINE = '{"untracked": [], "sparse_absences": []}\n'


def load_untracked_baseline(devlyn_dir: Path) -> tuple[set[str], frozenset[str], str | None]:
    """PHASE 0's record of what the run does not own: `untracked` paths that were already there, and
    `sparse_absences`, tracked skip-worktree paths the worktree lacked. Each set grants only its own
    exemption, so a path cannot move from one to the other to hide a change."""
    baseline_path = devlyn_dir / "untracked.baseline"
    if not baseline_path.is_file():
        return (set(), frozenset(), "VERIFY MECHANICAL requires .devlyn/untracked.baseline from PHASE 0; the file is missing.")
    try:
        data = loads_strict_json(baseline_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return (set(), frozenset(), f"Cannot read {baseline_path}: {e}")
    if (not isinstance(data, dict) or set(data) != {"untracked", "sparse_absences"}
            or any(not isinstance(paths, list) or any(not isinstance(path, str) for path in paths) for paths in data.values())):
        return (set(), frozenset(), f"{baseline_path} must hold exactly the untracked and sparse_absences path lists")
    return ({path for path in data["untracked"] if not is_devlyn_path(path)}, frozenset(data["sparse_absences"]), None)


def unadopted_user_path(path: str, baseline: set[str], surface: list[str]) -> bool:
    """Whether `path` is a user's untracked path from before the run that no exact surface entry adopts.

    A nested repository is recorded as `dir/` in the baseline but becomes the gitlink `dir` once
    staged, so ownership compares paths without a trailing slash.
    """
    key = path.rstrip("/")
    return key in {item.rstrip("/") for item in baseline} and key not in {entry.rstrip("/") for entry in surface}


def load_authorized_surface(devlyn_dir: Path) -> tuple[list[str] | None, str | None]:
    plan_path = devlyn_dir / "plan.md"
    if not plan_path.is_file():
        return (
            None,
            "VERIFY MECHANICAL requires .devlyn/plan.md with a declared authorized_surface; the file is missing.",
        )
    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except OSError as e:
        return (None, f"Cannot read {plan_path}: {e}")

    _section_found, block = extract_authorized_surface_block(plan_text)
    parse_error: str | None = None
    data: dict | None = None
    if block is None:
        parse_error = (
            "plan.md must include a `<!-- devlyn:authorized-surface -->` "
            "section with a fenced ```json``` block: "
            "{\"authorized_surface\": [...]}."
        )
    else:
        try:
            parsed = loads_strict_json(block)
        except ValueError as e:
            parse_error = f"authorized_surface json block is invalid JSON: {e}"
        else:
            data = parsed
    if parse_error is None:
        parse_error = validate_authorized_surface_shape(data)
    if parse_error is not None:
        return (None, f"plan.md authorized_surface is malformed: {parse_error}")
    assert data is not None
    return (list(data["authorized_surface"]), None)


def scope_finding(
    seq: int,
    rule_id: str,
    message: str,
    file_ref: str,
    fix_hint: str,
) -> dict:
    return {
        "id": f"{FINDING_PREFIX}-{seq:04d}",
        "rule_id": rule_id,
        "level": "error",
        "severity": "CRITICAL",
        "confidence": 1.0,
        "message": message,
        "file": file_ref,
        "line": 1,
        "phase": MECHANICAL_PHASE,
        "criterion_ref": "plan.md/authorized_surface",
        "fix_hint": fix_hint,
        "blocking": True,
        "status": "open",
    }


def authorized_surface_findings(
    work: Path, devlyn_dir: Path, state: dict, finding_start: int,
) -> tuple[list[dict], int]:
    """Normal-mode MECHANICAL: enforce PLAN's declared `authorized_surface`
    against this run's diff and its created-during-run untracked files.

    This closes the measured scope-leak drift class: bare-model diffs leaked
    an out-of-scope tracked file even with the full CLAUDE.md contract loaded,
    on every measured model tier. `fix_hint` deliberately never offers
    "widen the surface" — the fix loop respawns the same IMPLEMENT worker
    that produced the leak, and letting it edit `plan.md` to authorize its
    own diff would let it self-authorize the exact drift this gate exists
    to catch. A persistent finding exhausts the shared repair budget and
    ends the run for user/orchestrator review instead.
    """
    surface, surface_error = load_authorized_surface(devlyn_dir)
    if surface_error is not None:
        return ([scope_finding(
            finding_start,
            "scope.authorized-surface-malformed",
            surface_error,
            ".devlyn/plan.md",
            (
                "PLAN must write .devlyn/plan.md with a `Files to touch` "
                "section and an authorized_surface json block before "
                "VERIFY MECHANICAL can run."
            ),
        )], finding_start + 1)
    assert surface is not None

    baseline, sparse_absences, baseline_error = load_untracked_baseline(devlyn_dir)
    if baseline_error is not None:
        return ([scope_finding(
            finding_start,
            "scope.authorized-surface-malformed",
            baseline_error,
            ".devlyn/untracked.baseline",
            (
                "PHASE 0 must write .devlyn/untracked.baseline before "
                "VERIFY so created-during-run untracked files remain "
                "visible to the scope gate."
            ),
        )], finding_start + 1)
    current_untracked, untracked_error = current_untracked_files(work, sparse_absences)
    if untracked_error is not None:
        return ([scope_finding(
            finding_start,
            "scope.authorized-surface-malformed",
            f"Cannot read current untracked files: {untracked_error}",
            ".devlyn/untracked.baseline",
            "Ensure VERIFY MECHANICAL runs inside a readable git worktree.",
        )], finding_start + 1)

    findings: list[dict] = []
    seq = finding_start
    paths, paths_error = changed_files(work, state, devlyn_dir, sparse_absences)
    if paths_error is not None:
        return ([scope_finding(
            finding_start,
            "scope.authorized-surface-malformed",
            f"Cannot read changed files: {paths_error}",
            ".devlyn/external-diff.patch" if (devlyn_dir / "external-diff.patch").is_file() else ".devlyn/pipeline.state.json",
            "Ensure base_ref.sha is valid and any external-diff.patch is a readable Git patch with a/ and b/ prefixes.",
        )], finding_start + 1)
    for path in paths:
        if unadopted_user_path(path, baseline, surface):
            # A user's untracked file from before the run is adopted only by an exact surface entry.
            findings.append(scope_finding(
                seq,
                "scope.out-of-scope-file",
                f"{path} was the user's untracked file before the run; only an exact authorized_surface entry adopts it.",
                path,
                (f"Remove {path} from the commit with `git --literal-pathspecs rm -q --cached -- {shlex.quote(path)}` and keep "
                 "the file: it is the user's. Never widen plan.md's authorized_surface to cover it."),
            ))
            seq += 1
            continue
        if path_matches_surface(path, surface):
            continue
        findings.append(scope_finding(
            seq,
            "scope.out-of-scope-file",
            f"{path} is outside PLAN's declared authorized_surface.",
            path,
            (
                f"Remove {path} from the diff. Do not widen plan.md's "
                "authorized_surface to include it — that would let this "
                "fix loop self-authorize its own scope leak. If the file "
                "is genuinely required, halt per implement.md's contract "
                "so this finding reaches the user/orchestrator for a new run."
            ),
        ))
        seq += 1
    for path in sorted(current_untracked - baseline):
        if path_matches_surface(path, surface):
            continue
        findings.append(scope_finding(
            seq,
            "scope.out-of-scope-file",
            f"{path} is an unauthorized untracked file outside the PHASE 0 baseline.",
            path,
            (
                f"Remove {path} if this run created it; a file that predates the run "
                "(one an ignore change made visible) is the user's, so leave it and keep "
                "the finding for review. Never widen plan.md's authorized_surface to cover it."
            ),
        ))
        seq += 1
    return (findings, seq)


def run_print_authorized_surface(work: Path, devlyn_dir: Path) -> int:
    """Print the changed paths the scoped checkpoint stages, NUL-separated, once every check passes.

    A refusal prints nothing to stdout and exits 2, so the checkpoint pipe stages and commits nothing.
    The commit takes the whole index, so an index entry for a user's pre-run file that no exact surface
    entry adopts refuses; so does an exactly adopted pre-run nested repository with content its commit
    lacks, because adoption records only that commit.
    """
    surface, surface_error = load_authorized_surface(devlyn_dir)
    if surface_error is not None:
        print(f"[spec-verify --print-authorized-surface] {surface_error}", file=sys.stderr)
        return 2
    assert surface is not None
    baseline, sparse_absences, baseline_error = load_untracked_baseline(devlyn_dir)
    if baseline_error is not None:
        print(f"[spec-verify --print-authorized-surface] {baseline_error}", file=sys.stderr)
        return 2
    try:
        with observed_git(work, sparse_absences) as (git, _flags):
            entries, status_error = parse_status(git(*STATUS_ARGS))
            indexed = git("ls-files", "-z")  # every index entry, at any stage
    except (OSError, ValueError) as exc:
        entries, status_error, indexed = [], str(exc) or "git failed", b""
    if status_error is not None:
        print(f"[spec-verify --print-authorized-surface] {status_error}", file=sys.stderr)
        return 2
    refusals = [
        f"{path} is the user's file from before the run and is in the index, which the checkpoint commits "
        "whole; no exact authorized_surface entry adopts it. Keep the file, drop its index entry with "
        f"`git --literal-pathspecs rm -q --cached -- {shlex.quote(path)}`, then rerun the checkpoint."
        for path in sorted({name.decode("utf-8", "surrogateescape") for name in indexed.split(b"\0") if name})
        if unadopted_user_path(path, baseline, surface)]
    # A user's untracked file from before the run is adopted only by an exact surface entry, never by a glob.
    authorized_paths = [path for path in sorted({path for _status, path in entries if not is_devlyn_path(path)})
                        if path_matches_surface(path, surface) and not unadopted_user_path(path, baseline, surface)]
    for path in authorized_paths:
        if path.rstrip("/") + "/" not in baseline:
            continue
        # An adopted pre-run nested repository is staged as a gitlink: only its commit is recorded.
        try:
            dirt = _child_git(work / path, "status", "--porcelain=v1", "-z", "--untracked-files=all",
                              "--ignore-submodules=none")
        except (OSError, ValueError) as exc:
            refusals.append(f"cannot read the adopted nested repository {path}: {exc}")
            continue
        if dirt:
            refusals.append(
                f"the adopted nested repository {path} has content its commit lacks, and adoption records only "
                "its commit. Commit or clean that content inside it and rerun the checkpoint, or complete "
                "IMPLEMENT BLOCKED and report BLOCKED:adopted-repository-dirty.")
    if refusals:
        print("[spec-verify --print-authorized-surface] refused:\n" + "\n".join(f"- {line}" for line in refusals),
              file=sys.stderr)
        return 2
    if authorized_paths:
        sys.stdout.buffer.write("\0".join(authorized_paths).encode("utf-8", "surrogateescape") + b"\0")
    return 0


def run_write_untracked_baseline(work: Path, devlyn_dir: Path) -> int:
    """PHASE 0 writer for `.devlyn/untracked.baseline`. Shares
    git_status_entries with the MECHANICAL reader so writer and comparer can
    never disagree on quoting or directory collapsing (a shell-side
    `git status --porcelain | awk` writer records untracked directories as
    `dir/` and C-quotes special characters, while the comparer sees
    `--untracked-files=all` unquoted per-file paths — every pre-existing
    file under an untracked directory would false-positive as
    created-during-run). The skip-worktree paths the worktree lacks now are
    the only sparse absences the run may keep."""
    try:
        sparse_absences = sparse_absent_entries(work)
    except (OSError, ValueError) as exc:
        print(f"[spec-verify --write-untracked-baseline] cannot read index flags: {exc}", file=sys.stderr)
        return 2
    entries, error = git_status_entries(work, sparse_absences)
    if error:
        print(f"[spec-verify --write-untracked-baseline] git status failed: {error}", file=sys.stderr)
        return 2
    untracked = sorted(
        path for status, path in entries
        if status == "??" and not is_devlyn_path(path)
    )
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / "untracked.baseline").write_text(
        json.dumps({"untracked": untracked, "sparse_absences": sorted(sparse_absences)}, indent=1) + "\n",
        encoding="utf-8",
    )
    return 0


def _git_bytes(work: Path, *args: str) -> bytes:
    proc = subprocess.run(["git", *args], cwd=str(work), capture_output=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).decode("utf-8", "replace").strip()
        raise ValueError(f"git {args[0]} failed: {detail or proc.returncode}")
    return proc.stdout


def _file_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


# Git trusts cached state through these; an observer turns them off.
CACHE_CONFIG = ("-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-c", "core.commitGraph=false")
OBSERVE_CONFIG = (*CACHE_CONFIG, "-c", "core.ignoreStat=false", "-c", "core.splitIndex=false")
# Replacement refs would make one object stand for another; C-locale diagnostics stay recognizable.
OBSERVE_ENV = {"GIT_OPTIONAL_LOCKS": "0", "GIT_NO_REPLACE_OBJECTS": "1", "LC_ALL": "C"}


def _checked(proc: subprocess.CompletedProcess, name: str) -> bytes:
    """A finished Git command's stdout. A failure raises, and so does a directory Git could not open:
    Git warns, leaves that directory's content out and still exits 0."""
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).decode("utf-8", "replace").strip()
        raise ValueError(f"git {name} failed: {detail or proc.returncode}")
    if b"could not open directory" in proc.stderr:
        raise ValueError(f"git {name} could not open every directory: {proc.stderr.decode('utf-8', 'replace').strip()}")
    return proc.stdout


def _child_git(child: Path, *args: str) -> bytes:
    """Run Git inside a nested repository under the observer's object, cache and hook controls, on its
    own index as it is: a nested repository's index flags and ignore rules are trusted environment."""
    env = {key: value for key, value in os.environ.items() if key != "GIT_INDEX_FILE"}
    with tempfile.TemporaryDirectory(prefix="devlyn-child-") as tmp:
        return _checked(subprocess.run(
            ["git", "-C", str(child), *CACHE_CONFIG, "-c", f"core.hooksPath={Path(tmp) / 'no-hooks'}", *args],
            env={**env, **OBSERVE_ENV}, capture_output=True), args[0])


def _git_path(work: Path, name: str) -> Path:
    path = Path(os.fsdecode(_git_bytes(work, "rev-parse", "--git-path", name).removesuffix(b"\n")))
    return path if path.is_absolute() else work / path


def _present(path: Path) -> bool:
    """Whether anything occupies the path, a dangling symlink included; an access error raises."""
    try:
        path.lstat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    return True


def _flag_tags(listing: bytes) -> dict[str, str]:
    """Paths `git ls-files -v -z` marks skip-worktree (S) or assume-unchanged (lowercase), by tag."""
    records = (record.decode("utf-8", "surrogateescape") for record in listing.split(b"\0") if len(record) > 2)
    return {record[2:]: record[0] for record in records if record[0] == "S" or record[0].islower()}


def sparse_absent_entries(work: Path) -> frozenset[str]:
    """Skip-worktree paths the worktree lacks: a sparse checkout's absences, as found right now."""
    flags = _flag_tags(_git_bytes(work, "ls-files", "-v", "-z"))
    return frozenset(path for path, tag in flags.items() if tag in "Ss" and not _present(work / path))


@contextlib.contextmanager
def observed_git(work: Path, sparse_absences: frozenset[str] = frozenset()):
    """Run Git as an observer that index flags, caches, replacement refs and hooks cannot steer.

    Index flags make Git skip worktree content, caches make it trust stale state, replacement refs
    swap objects and hooks run worker code, and a worker can set all four; other repository
    configuration is trusted. On a private copy of the index (mtime kept, so racily clean entries
    are still content-checked) every stage-0 entry is rewritten, which clears assume-unchanged and
    invalidates the cache-tree along each entry's path (an unmerged entry stays, and status reports
    it); skip-worktree is cleared everywhere except an absent path in `sparse_absences`, the caches
    and replacement refs are off, and the real index is never written (reading a split index still
    refreshes its shared index's mtime, Git's expiry clock, as every Git read does). Yields
    (git, flags): a runner returning stdout bytes, and the original tag of every flagged path.
    """
    index = _git_path(work, "index")
    with tempfile.TemporaryDirectory(prefix="devlyn-observe-") as tmp:
        private = Path(tmp) / "index"
        if index.is_file():
            shutil.copy2(index, private)
        env = {**os.environ, **OBSERVE_ENV, "GIT_INDEX_FILE": str(private)}

        # Hooks are worker-writable and would run against the private index (post-index-change).
        config = (*OBSERVE_CONFIG, "-c", f"core.hooksPath={Path(tmp) / 'no-hooks'}")

        def git(*args: str, stdin: bytes | None = None) -> bytes:
            return _checked(subprocess.run(["git", *config, *args], cwd=str(work), env=env, input=stdin,
                                           capture_output=True), args[0])

        listing = git("ls-files", "-v", "-z")
        flags = _flag_tags(listing)
        cleared = (("--no-assume-unchanged", [record[2:] for record in listing.split(b"\0")
                                              if len(record) > 2 and record[:1] not in b"Mm"]),
                   ("--no-skip-worktree", [path.encode("utf-8", "surrogateescape") for path, tag in flags.items()
                                           if tag in "Ss" and not (path in sparse_absences and not _present(work / path))]))
        for option, paths in cleared:
            if paths:
                git("update-index", option, "-z", "--stdin", stdin=b"".join(path + b"\0" for path in paths))
        yield git, flags


def _entry_sha256(path: Path) -> str:
    """Digest one untracked entry: link text for a symlink, streamed bytes for a regular file.

    Any other type (FIFO, socket, device) would block or lie, so it fails the snapshot.
    """
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f"unsupported file type in the snapshot: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_verify_span(state: dict) -> dict | None:
    """The VERIFY span the writer opened with a recorded `pre_sha`, else None."""
    verify = (state.get("phases") or {}).get("verify")
    if (not isinstance(verify, dict) or not verify.get("started_at")
            or verify.get("completed_at") or not isinstance(verify.get("pre_sha"), str)):
        return None
    return verify


def source_snapshot(work: Path, devlyn_dir: Path, state: dict) -> tuple[dict, str, list[str]]:
    """Snapshot the source a MECHANICAL round reviews.

    Returns (document, digest, problems). The digest covers HEAD, tracked and
    staged changes (submodule content included) and their status entries, every
    nonignored untracked file outside `.devlyn/` (bytes, or link text for a
    symlink, plus mode; in normal mode a PHASE 0 baseline entry is the user's
    and counts by path and kind only, and a nested repository or worktree, which
    Git reports as one directory entry, by path only), and the current bytes of every
    verification input wherever it lives: the source spec or criteria and goal,
    the sibling `spec.expected.json`, PLAN, risk probes with their scripts, the
    PHASE 0 baseline and the external diff. Git observes through `observed_git`, and
    the document also binds the sparse absences still in place, so a flag changed or
    an absence materialized after the snapshot changes the digest.

    Problems name what keeps the tree from being sealable. In normal mode: tracked
    or staged changes (hidden ones named with their flag), untracked files outside
    the baseline, or HEAD away from the VERIFY span's `pre_sha`. In every mode: an
    unusable baseline, or one that differs from its bound digest. Ignore rules of
    every source and the content they hide are trusted environment, not attested.
    """
    baseline, sparse_absences, baseline_error = load_untracked_baseline(devlyn_dir)
    pathspec = ("--", ".", ":(exclude).devlyn")
    diff = ("diff", "--no-ext-diff", "--no-textconv", "--binary", "--submodule=diff", "--ignore-submodules=none")
    with observed_git(work, sparse_absences) as (git, flags):
        head = git("rev-parse", "HEAD").decode().strip()
        worktree = git(*diff, "HEAD", *pathspec)
        index = git(*diff, "--cached", "HEAD", *pathspec)
        entries, error = parse_status(git(*STATUS_ARGS))
        if error:
            raise ValueError(f"git status failed: {error}")
        absent = sorted(path for path, tag in flags.items()
                        if tag in "Ss" and path in sparse_absences and not _present(work / path))
    tracked = sorted([path, status] for status, path in entries if status != "??" and not is_devlyn_path(path))
    dirty = sorted({path for path, _status in tracked})
    verify_only = state.get("mode") == "verify-only"
    untracked = []
    for status, path in entries:
        if status != "??" or is_devlyn_path(path):
            continue
        target = work / path
        info = target.lstat()
        if path.endswith("/"):
            # A nested repository or worktree: the user's in normal mode, reviewed content in verify-only.
            untracked.append([path, "directory", None, _tree_sha256(target) if verify_only else None])
            continue
        kind = "symlink" if stat.S_ISLNK(info.st_mode) else "file"
        if not verify_only and path in baseline:
            untracked.append([path, kind, None, None])
            continue
        untracked.append([path, kind, oct(stat.S_IMODE(info.st_mode)), _entry_sha256(target)])
    untracked.sort()
    source = state.get("source") if isinstance(state.get("source"), dict) else {}

    def input_sha256(path_text: object) -> str | None:
        if not isinstance(path_text, str) or not path_text:
            return None
        path = Path(path_text)
        return _file_sha256(path if path.is_absolute() else work / path)

    spec_path = source.get("spec_path")
    probes = None
    if (devlyn_dir / "risk-probes.jsonl").is_file():
        probes_digest, probes_error = risk_probes_digest(devlyn_dir)
        probes = probes_digest or f"invalid: {probes_error}"
    baseline_sha = _file_sha256(devlyn_dir / "untracked.baseline")
    document = {
        "head": head,
        "worktree_diff_sha256": hashlib.sha256(worktree).hexdigest(),
        "index_diff_sha256": hashlib.sha256(index).hexdigest(),
        "status": tracked,
        "untracked": untracked,
        "sparse_absences_sha256": hashlib.sha256("\0".join(absent).encode("utf-8", "surrogateescape")).hexdigest(),
        "inputs": {
            "spec": input_sha256(spec_path),
            "spec_expected": input_sha256(str(Path(spec_path).with_name("spec.expected.json"))) if isinstance(spec_path, str) and spec_path else None,
            "criteria": input_sha256(source.get("criteria_path")),
            "goal": input_sha256(source.get("goal_path")),
            "plan": _file_sha256(devlyn_dir / "plan.md"),
            "staged_commands": _file_sha256(devlyn_dir / "spec-verify.json"),
            "risk_probes": probes,
            "untracked_baseline": baseline_sha,
            "external_diff": _file_sha256(devlyn_dir / "external-diff.patch"),
        },
    }
    digest = hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8", "surrogateescape")
    ).hexdigest()
    problems = []
    if not verify_only:
        if dirty or worktree or index:
            named = [f"{path} (hidden by index flag {flags[path]})" if path in flags else path for path in dirty]
            problems.append("tracked or staged changes: " + ", ".join(named or ["(index)"]))
        residue = sorted({row[0] for row in untracked} - baseline)
        if residue:
            problems.append("untracked files outside the PHASE 0 baseline: " + ", ".join(residue))
        verify = open_verify_span(state)
        if verify is not None and head != verify["pre_sha"]:
            problems.append(f"HEAD {head} differs from the VERIFY span's pre_sha {verify['pre_sha']}")
    if baseline_error is not None:
        problems.append(baseline_error)
    elif "untracked_baseline_sha256" in state and state["untracked_baseline_sha256"] != baseline_sha:
        problems.append(".devlyn/untracked.baseline differs from its bound digest")
    return document, digest, problems


def _tree_sha256(root: Path) -> str:
    """Digest a nested repository: its tracked entries, ignore patterns notwithstanding, and its
    nonignored untracked files (path, mode and bytes or link text, sorted), never ignored content.

    A tracked entry missing on disk counts as deleted and a repository nested inside counts the
    same way; symlinks, including ones to directories, count by link text and are never followed,
    and an unreadable path or a listed entry of another type fails the snapshot instead of dropping out.
    """
    listing = _child_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    digest = hashlib.sha256()
    for name in sorted(set(listing.split(b"\0")) - {b""}):
        path = root / name.decode("utf-8", "surrogateescape")
        try:
            info = path.lstat()
        except (FileNotFoundError, NotADirectoryError):
            record = b"deleted"
        else:
            content = _tree_sha256(path) if stat.S_ISDIR(info.st_mode) else _entry_sha256(path)
            record = oct(info.st_mode).encode() + b"\0" + content.encode()
        digest.update(name + b"\0" + record + b"\0")
    return digest.hexdigest()


def snapshot_changes(before: dict, after: dict) -> list[str]:
    """Name what differs between two snapshots so a refusal points at the paths."""
    changes = [key.removesuffix("_sha256").replace("_", " ")
               for key in ("head", "worktree_diff_sha256", "index_diff_sha256") if before.get(key) != after.get(key)]
    for name in ("status", "untracked"):
        old = {row[0]: row for row in before.get(name) or []}
        new = {row[0]: row for row in after.get(name) or []}
        changes += [f"{name} {path}" for path in sorted(set(old) | set(new)) if old.get(path) != new.get(path)]
    if before.get("sparse_absences_sha256") != after.get("sparse_absences_sha256"):
        changes.append("sparse absences")
    old_inputs, new_inputs = before.get("inputs") or {}, after.get("inputs") or {}
    changes += [f"input {key}" for key in sorted(set(old_inputs) | set(new_inputs))
                if old_inputs.get(key) != new_inputs.get(key)]
    return changes


def _seal_identity(state: dict) -> tuple[str | None, int | None]:
    verify = open_verify_span(state)
    return state.get("run_id"), verify.get("round") if verify else None


_OPENED_BY: str | None = None


def write_open_seal(work: Path, devlyn_dir: Path, state: dict) -> str | None:
    """Record the pre-execution snapshot for the open VERIFY round (no-op outside one).

    A round has exactly one snapshot: VERIFY spawn clears the file, and a second
    MECHANICAL run in the same round is refused rather than replacing evidence.
    """
    run_id, round_ = _seal_identity(state)
    if round_ is None:
        return None
    global _OPENED_BY
    seal_path = devlyn_dir / SEAL_NAME
    try:
        handle = os.open(seal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return (f"{SEAL_NAME} already exists for this VERIFY round; MECHANICAL runs once per round — "
                "open a new VERIFY round instead of rerunning it")
    os.close(handle)
    _OPENED_BY = secrets.token_hex(16)
    _write_snapshot_record(work, devlyn_dir, state, run_id, round_)
    return None


def _write_snapshot_record(work: Path, devlyn_dir: Path, state: dict, run_id: str | None, round_: int) -> None:
    record: dict = {"schema": 1, "run_id": run_id, "round": round_, "opened_by": _OPENED_BY, "seal": None}
    try:
        document, digest, problems = source_snapshot(work, devlyn_dir, state)
        record.update(snapshot=document, digest=digest, problems=problems)
    except (OSError, ValueError, MemoryError) as exc:
        record.update(snapshot=None, digest=None, problems=[f"snapshot failed: {exc}"])
    seal_path = devlyn_dir / SEAL_NAME
    temporary = seal_path.with_name(SEAL_NAME + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, seal_path)


def refresh_open_seal(work: Path, devlyn_dir: Path, state: dict) -> str | None:
    """Retake this process's own snapshot after staging, before the first command runs.

    Staging rewrites `.devlyn/spec-verify.json` (an authoritative carrier in benchmark
    mode), so the round's snapshot is final only once staging is done; no command has
    executed yet.
    """
    run_id, round_ = _seal_identity(state)
    if round_ is None or _OPENED_BY is None:
        return None
    try:
        record = loads_strict_json((devlyn_dir / SEAL_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return f"{SEAL_NAME} vanished before the first command: {exc}"
    if not isinstance(record, dict) or record.get("opened_by") != _OPENED_BY or record.get("seal") is not None:
        return f"{SEAL_NAME} is no longer this MECHANICAL run's open snapshot"
    _write_snapshot_record(work, devlyn_dir, state, run_id, round_)
    return None


def run_seal(work: Path, devlyn_dir: Path) -> int:
    """Seal the round when the source equals its pre-execution snapshot.

    Normal mode also requires that snapshot to be clean. A refusal leaves the
    seal null and appends one CRITICAL `scope.unsealed-source` finding, which the
    merge routes to repair like any other binding MECHANICAL finding.
    """
    state = read_state(devlyn_dir)
    run_id, round_ = _seal_identity(state)
    if round_ is None:
        print("[spec-verify --seal] no open VERIFY span with a recorded pre_sha", file=sys.stderr)
        return 2
    seal_path = devlyn_dir / SEAL_NAME
    try:
        record = loads_strict_json(seal_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[spec-verify --seal] {SEAL_NAME} is unreadable: {exc}", file=sys.stderr)
        return 2
    if not isinstance(record, dict) or (record.get("run_id"), record.get("round")) != (run_id, round_):
        print(f"[spec-verify --seal] {SEAL_NAME} does not belong to run {run_id} round {round_}", file=sys.stderr)
        return 2
    problems = list(record.get("problems") or [])
    if record.get("digest") is None:
        problems = list(record.get("problems") or ["snapshot missing"])
    else:
        try:
            document, digest, _now = source_snapshot(work, devlyn_dir, state)
        except (OSError, ValueError, MemoryError) as exc:
            digest, problems = None, problems + [f"snapshot failed: {exc}"]
        if digest is not None and digest != record["digest"]:
            changed = snapshot_changes(record.get("snapshot") or {}, document)
            problems.append("source changed after the MECHANICAL snapshot: " + ", ".join(changed or ["(digest)"]))
    if problems:
        record["seal"] = None
        seal_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        findings_path = devlyn_dir / FINDINGS_NAME
        count = sum(1 for line in findings_path.read_text(encoding="utf-8").splitlines() if line.strip()) \
            if findings_path.is_file() else 0
        with findings_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(scope_finding(
                count + 1, "scope.unsealed-source",
                "MECHANICAL source cannot be sealed: " + "; ".join(problems),
                ".devlyn/" + SEAL_NAME,
                "Commit every deliverable through the scoped checkpoint, remove run-owned "
                "artifacts and leave tracked files untouched after the MECHANICAL run, then rerun "
                "MECHANICAL. Never widen the authorized surface or edit the baseline.",
            )) + "\n")
        print("[spec-verify --seal] refused: " + "; ".join(problems), file=sys.stderr)
        return 1
    record["seal"] = {"digest": record["digest"], "head": record["snapshot"]["head"]}
    seal_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (devlyn_dir / FINDINGS_NAME).touch()  # A sealed round with no findings still has its carrier.
    print(f"[spec-verify --seal] sealed {record['digest']}", file=sys.stderr)
    return 0


def run_check_mode(md_path: Path) -> int:
    """Validate a spec's authoritative sibling or legacy inline carrier;
    return 0/2 without staging or execution. This is not generated-mode staging.
    """
    if not md_path.is_file():
        print(f"[spec-verify --check] error: {md_path} not found", file=sys.stderr)
        return 2
    text = md_path.read_text(encoding="utf-8")
    frontmatter_err = validate_present_spec_complexity(text)
    if frontmatter_err:
        print(f"[spec-verify --check] {md_path}: {frontmatter_err}", file=sys.stderr)
        return 2
    expected_path = md_path.with_name("spec.expected.json")
    if expected_path.is_file():
        data, err = load_expected_contract(expected_path)
        err = err or validate_expected_against_sibling_spec(md_path, data)
        if err:
            print(f"[spec-verify --check] {md_path}: sibling {expected_path}: {err}", file=sys.stderr)
            return 2
        return 0
    section_found, block = extract_verification_block(text)
    if not section_found:
        # Sentinel absent entirely — opt-in nature preserved for ideate (a
        # spec without machine verification is still valid; it just won't
        # activate the MECHANICAL literal check).
        return 0
    if block is None:
        print(
            f"[spec-verify --check] {md_path}: `<!-- devlyn:verification -->` "
            "section found but no fenced ```json``` block inside it",
            file=sys.stderr,
        )
        return 2
    try:
        data = loads_strict_json(block)
    except ValueError as e:
        print(
            f"[spec-verify --check] {md_path}: invalid JSON in "
            f"`<!-- devlyn:verification -->` ```json``` block: {e}",
            file=sys.stderr,
        )
        return 2
    err = validate_inline_shape(data)
    if err:
        print(f"[spec-verify --check] {md_path}: shape error: {err}", file=sys.stderr)
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
    complexity_err = validate_sibling_spec_complexity(expected_path.with_name("spec.md"))
    if complexity_err:
        print(f"[spec-verify --check-expected] {expected_path}: shape error: {complexity_err}", file=sys.stderr)
        return 2
    sibling_err = validate_expected_against_sibling_spec(expected_path.with_name("spec.md"), _data)
    if sibling_err:
        print(f"[spec-verify --check-expected] {expected_path}: shape error: {sibling_err}", file=sys.stderr)
        return 2
    return 0


def seal_self_test(script_path: str) -> int:
    """`--seal` seals only the source MECHANICAL ran on, and only a clean one in normal mode."""
    import shutil

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "work"
        devlyn = root / ".devlyn"
        devlyn.mkdir(parents=True)

        def git(*args: str) -> str:
            return subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                cwd=root, check=True, capture_output=True, text=True, encoding="utf-8",
            ).stdout.strip()

        (root / ".gitignore").write_text(".devlyn/\n", encoding="utf-8")
        (root / "a.txt").write_text("base\n", encoding="utf-8")
        # The spec and its sibling expected file live outside the worktree: Git cannot see them,
        # so only the snapshot's own input hashes can.
        outside = Path(tempfile.mkdtemp(dir=tmp))
        spec = outside / "spec.md"
        spec.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- prints ok\n", encoding="utf-8")
        expected = outside / "spec.expected.json"
        expected.write_text(json.dumps({"verification_commands": [
            {"cmd": "printf ok && printf artifact > coverage.out", "stdout_contains": ["ok"]}]}), encoding="utf-8")
        git("init", "-q")
        git("add", "-A")
        git("commit", "-q", "-m", "base")
        base = git("rev-parse", "HEAD")
        (root / "keep.local").write_text("user file\n", encoding="utf-8")
        os.symlink("keep.local", root / "keep.link")
        # A user's nested repository is one `?? vendor/lib/` directory entry to the outer Git. Its own
        # ignore rules cover build/, where it also tracks a file.
        nested = root / "vendor" / "lib"
        (nested / "build").mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
        (nested / "lib.txt").write_text("vendored\n", encoding="utf-8")
        (nested / ".gitignore").write_text("build/\n", encoding="utf-8")
        (nested / "build" / "keep.txt").write_text("tracked\n", encoding="utf-8")
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A", "-f"], cwd=nested, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "v"], cwd=nested, check=True)
        (devlyn / "plan.md").write_text(
            "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files\n\n```json\n"
            '{"authorized_surface": ["a.txt"]}\n```\n', encoding="utf-8",
        )
        if run_write_untracked_baseline(root, devlyn) != 0:
            print("seal fixture: baseline write failed", file=sys.stderr)
            return 1
        baseline_sha = hashlib.sha256((devlyn / "untracked.baseline").read_bytes()).hexdigest()

        def state(mode: str = "spec", pre_sha: str | None = None) -> None:
            (devlyn / "pipeline.state.json").write_text(json.dumps({
                "run_id": "rs-seal", "mode": mode, "base_ref": {"sha": base},
                "source": {"type": "spec", "spec_path": str(spec)},
                "untracked_baseline_sha256": baseline_sha,
                "phases": {"verify": {"round": 1, "started_at": "2026-10-03T00:00:00.000Z",
                                      "completed_at": None, "pre_sha": pre_sha or git("rev-parse", "HEAD")}},
            }), encoding="utf-8")

        def mechanical(clean: bool = True) -> subprocess.CompletedProcess:
            """One MECHANICAL round: fresh round (VERIFY spawn clears the seal), run, owner cleanup."""
            (devlyn / SEAL_NAME).unlink(missing_ok=True)
            shutil.rmtree(devlyn / "process-evidence", ignore_errors=True)
            run = subprocess.run([sys.executable, script_path], cwd=root, timeout=120,
                                 capture_output=True, text=True, encoding="utf-8")
            if clean:
                (root / "coverage.out").unlink(missing_ok=True)
            return run

        def seal() -> tuple[int, dict, str]:
            proc = subprocess.run([sys.executable, script_path, "--seal"], cwd=root, timeout=120,
                                  capture_output=True, text=True, encoding="utf-8")
            record = loads_strict_json((devlyn / SEAL_NAME).read_text(encoding="utf-8"))
            findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8") if (devlyn / FINDINGS_NAME).is_file() else ""
            return proc.returncode, record, findings

        def refused(label: str, needle: str) -> bool:
            rc, record, findings = seal()
            if rc != 1 or record["seal"] is not None or "scope.unsealed-source" not in findings or needle not in findings:
                print(f"seal accepted or misreported {label}: rc={rc} {record} {findings}", file=sys.stderr)
                return False
            return True

        state()
        first = mechanical(clean=False)
        if first.returncode != 0 or not (root / "coverage.out").is_file():
            print(f"seal fixture: clean MECHANICAL run failed: {first.stderr}", file=sys.stderr)
            return 1
        # Only the process that opened the round may retake its snapshot.
        global _OPENED_BY
        saved_owner = _OPENED_BY
        _OPENED_BY = "another-process"
        foreign = refresh_open_seal(root, devlyn, read_state(devlyn))
        _OPENED_BY = saved_owner
        if foreign is None or "no longer this MECHANICAL run's open snapshot" not in foreign:
            print(f"a foreign process retook the round's snapshot: {foreign}", file=sys.stderr)
            return 1
        opened = (devlyn / SEAL_NAME).read_bytes()
        rerun = subprocess.run([sys.executable, script_path], cwd=root, capture_output=True, text=True, encoding="utf-8")
        if rerun.returncode != 2 or "runs once per round" not in rerun.stderr or (devlyn / SEAL_NAME).read_bytes() != opened:
            print(f"a second MECHANICAL run replaced the round's snapshot: {rerun.stderr}", file=sys.stderr)
            return 1
        # The literal's artifact appeared after the snapshot; scope never saw it, cleanup removes it.
        if not refused("a run artifact left in place", "source changed after the MECHANICAL snapshot"):
            return 1
        (root / "coverage.out").unlink()
        rc, record, findings = seal()
        if (rc != 0 or record["seal"] != {"digest": record["digest"], "head": base} or record["problems"]
                or "scope." in findings.replace("scope.unsealed-source", "")):
            print(f"clean source was not sealed after cleanup: rc={rc} {record} {findings!r}", file=sys.stderr)
            return 1
        for label, target in (("the external expected file", expected), ("the external spec", spec),
                              ("PLAN inside .devlyn", devlyn / "plan.md")):
            original = target.read_bytes()
            target.write_bytes(original + b"\n")
            if not refused(f"a change to {label} after sealing", "source changed after the MECHANICAL snapshot"):
                return 1
            target.write_bytes(original)

        # Run-owned artifacts made after the snapshot and removed before --seal leave it sealable.
        mechanical()
        (root / "coverage.out").write_text("artifact\n", encoding="utf-8")
        (root / "coverage.out").unlink()
        if seal()[0] != 0:
            print("a removed run artifact blocked the seal", file=sys.stderr)
            return 1

        mechanical()
        (root / "residue.txt").write_text("left behind\n", encoding="utf-8")
        if not refused("residue left after the snapshot", "source changed after the MECHANICAL snapshot"):
            return 1
        (root / "residue.txt").unlink()

        mechanical()
        (root / "a.txt").write_text("edited after MECHANICAL\n", encoding="utf-8")
        if not refused("a tracked edit after the snapshot", "source changed after the MECHANICAL snapshot"):
            return 1
        git("checkout", "--", "a.txt")

        os.unlink(root / "keep.link")
        os.symlink("a.txt", root / "keep.link")
        mechanical()
        if seal()[0] != 0:
            print("a retargeted baseline symlink before MECHANICAL blocked an unchanged seal", file=sys.stderr)
            return 1
        # In normal mode baseline entries are the user's: a check that rewrites one is no source change.
        mechanical()
        os.unlink(root / "keep.link")
        os.symlink("keep.local", root / "keep.link")
        (root / "keep.local").write_text("rewritten by a tool\n", encoding="utf-8")
        if seal()[0] != 0:
            print("a rewritten baseline entry blocked a normal-mode seal", file=sys.stderr)
            return 1
        (root / "keep.local").write_text("user file\n", encoding="utf-8")
        mechanical()
        git("commit", "-q", "--allow-empty", "-m", "committed after the snapshot")
        if not refused("a commit after the snapshot", "source changed after the MECHANICAL snapshot: head"):
            return 1
        git("reset", "-q", "--hard", base)
        mechanical()
        os.chmod(root / "a.txt", 0o755)
        if not refused("a mode change after the snapshot", "worktree diff"):
            return 1
        os.chmod(root / "a.txt", 0o644)
        mechanical()
        (devlyn / "risk-probes.jsonl").write_text('{"id": "P1"}\n', encoding="utf-8")
        if not refused("probes added after the snapshot", "input risk_probes"):
            return 1
        (devlyn / "risk-probes.jsonl").unlink()

        (root / "residue.txt").write_text("unclean before MECHANICAL\n", encoding="utf-8")
        mechanical()
        if not refused("residue present at the snapshot", "untracked files outside the PHASE 0 baseline: residue.txt"):
            return 1
        (root / "residue.txt").unlink()

        (root / "a.txt").write_text("staged\n", encoding="utf-8")
        git("add", "a.txt")
        mechanical()
        if not refused("a staged change", "tracked or staged changes: a.txt"):
            return 1
        git("reset", "-q", "--hard", base)

        original_baseline = (devlyn / "untracked.baseline").read_bytes()
        edited = loads_strict_json(original_baseline.decode("utf-8"))
        edited["untracked"].append("residue.txt")
        (devlyn / "untracked.baseline").write_text(json.dumps(edited), encoding="utf-8")
        mechanical()
        if not refused("an edited baseline", "untracked.baseline differs from its bound digest"):
            return 1
        (devlyn / "untracked.baseline").write_bytes(original_baseline)

        state(pre_sha=base)
        (root / "a.txt").write_text("committed after VERIFY opened\n", encoding="utf-8")
        git("commit", "-q", "-am", "late")
        mechanical()
        if not refused("HEAD away from pre_sha", "differs from the VERIFY span's pre_sha"):
            return 1
        git("reset", "-q", "--hard", base)

        # verify-only reviews a supplied tree as found; only change after the snapshot refuses.
        (root / "a.txt").write_text("dirty under review\n", encoding="utf-8")
        state(mode="verify-only")
        mechanical()
        if seal()[0] != 0:
            print("verify-only refused an unchanged dirty tree", file=sys.stderr)
            return 1
        mechanical()
        (root / "a.txt").write_text("changed during review\n", encoding="utf-8")
        if not refused("a verify-only change after the snapshot", "source changed after the MECHANICAL snapshot"):
            return 1
        git("checkout", "--", "a.txt")
        mechanical()
        (root / "keep.local").write_text("changed during review\n", encoding="utf-8")
        if not refused("a verify-only untracked change after the snapshot", "untracked keep.local"):
            return 1
        (root / "keep.local").write_text("user file\n", encoding="utf-8")
        # A nested repository's tracked entries (an ignored-looking one included) and nonignored untracked
        # files are reviewed; its ignored output is not, and a deletion it already had is no change.
        for label, target in (("a verify-only change inside a nested repository", nested / "lib.txt"),
                              ("a change to a nested tracked file its ignore rules match", nested / "build" / "keep.txt")):
            original = target.read_bytes()
            mechanical()
            target.write_text("changed\n", encoding="utf-8")
            if not refused(label, "untracked vendor/lib/"):
                return 1
            target.write_bytes(original)
        mechanical()
        (nested / "new.txt").write_text("new\n", encoding="utf-8")
        if not refused("a new nonignored untracked file inside a nested repository", "untracked vendor/lib/"):
            return 1
        (nested / "new.txt").unlink()
        mechanical()
        (nested / "build" / "stamp").write_text("written by a check\n", encoding="utf-8")
        if seal()[0] != 0:
            print("ignored build output inside a reviewed nested repository blocked the seal", file=sys.stderr)
            return 1
        (nested / "build" / "stamp").unlink()
        (nested / "lib.txt").unlink()
        mechanical()
        if seal()[0] != 0:
            print("a deletion already inside a reviewed nested repository blocked an unchanged seal", file=sys.stderr)
            return 1
        mechanical()
        (nested / "lib.txt").write_text("vendored\n", encoding="utf-8")
        if not refused("a deleted nested file restored after the snapshot", "untracked vendor/lib/"):
            return 1
        inner = nested / "inner"  # a repository nested inside the reviewed one is digested the same way
        inner.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=inner, check=True)
        (inner / "x.txt").write_text("inner\n", encoding="utf-8")
        mechanical()
        (inner / "x.txt").write_text("changed\n", encoding="utf-8")
        if not refused("a change inside a repository nested in a reviewed one", "untracked vendor/lib/"):
            return 1
        shutil.rmtree(inner)
        (nested / "releases" / "a").mkdir(parents=True)
        (nested / "releases" / "b").mkdir()
        os.symlink("releases/a", nested / "current")
        mechanical()
        os.unlink(nested / "current")
        os.symlink("releases/b", nested / "current")
        if not refused("a directory symlink retargeted inside a nested repository", "untracked vendor/lib/"):
            return 1
        if os.name != "nt":
            # Git never lists an untracked FIFO, so a tracked path carries this one.
            (nested / "lib.txt").unlink()
            os.mkfifo(nested / "lib.txt")
            mechanical()
            if not refused("a FIFO inside a reviewed nested repository", "unsupported file type"):
                return 1
            os.unlink(nested / "lib.txt")
            (nested / "lib.txt").write_text("vendored\n", encoding="utf-8")
            if os.geteuid() != 0:
                hidden = nested / "hidden"
                hidden.mkdir()
                (hidden / "secret.txt").write_text("known path\n", encoding="utf-8")
                hidden.chmod(0o311)
                try:
                    mechanical()
                    if not refused("an unlistable subtree inside a reviewed nested repository", "snapshot failed"):
                        return 1
                finally:
                    hidden.chmod(0o755)
                shutil.rmtree(hidden)

        # Submodule content belongs to the tracked tree: residue inside it after the snapshot refuses.
        sub_source = Path(tempfile.mkdtemp(dir=tmp))
        subprocess.run(["git", "init", "-q"], cwd=sub_source, check=True)
        (sub_source / "s.txt").write_text("sub\n", encoding="utf-8")
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"], cwd=sub_source, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "s"], cwd=sub_source, check=True)
        git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(sub_source), "sub")
        git("commit", "-qm", "add submodule")
        state()
        mechanical()
        sub_rc, sub_record, _sub_findings = seal()
        if sub_rc != 0:
            print(f"a clean tree with a submodule was not sealed: {sub_record}", file=sys.stderr)
            return 1
        mechanical()
        (root / "sub" / "residue.out").write_text("left inside the submodule\n", encoding="utf-8")
        if not refused("residue inside a submodule after the snapshot", "status sub"):
            return 1
        (root / "sub" / "residue.out").unlink()
        git("config", "submodule.sub.ignore", "all")
        mechanical()
        (root / "sub" / "s.txt").write_text("edited under an ignore setting\n", encoding="utf-8")
        if not refused("a submodule edit hidden by submodule.<name>.ignore", "status sub"):
            return 1
        subprocess.run(["git", "checkout", "--", "s.txt"], cwd=root / "sub", check=True)
        # A benchmark's pre-staged carrier is the executed contract; changing it afterwards refuses.
        (devlyn / SEAL_NAME).unlink(missing_ok=True)
        shutil.rmtree(devlyn / "process-evidence", ignore_errors=True)
        (devlyn / "spec-verify.json").write_text(json.dumps({"verification_commands": [{"cmd": "printf ok"}]}),
                                                 encoding="utf-8")
        bench = subprocess.run([sys.executable, script_path], cwd=root, capture_output=True, text=True,
                               encoding="utf-8", env={**os.environ, "BENCH_WORKDIR": str(root)})
        bench_record = loads_strict_json((devlyn / SEAL_NAME).read_text(encoding="utf-8"))
        if bench_record["snapshot"]["inputs"]["staged_commands"] is None:
            print(f"benchmark MECHANICAL snapshot omitted its carrier: {bench.stderr}", file=sys.stderr)
            return 1
        (devlyn / "spec-verify.json").write_text(json.dumps({"verification_commands": [{"cmd": "exit 7"}]}),
                                                 encoding="utf-8")
        if not refused("a benchmark carrier changed after execution", "input staged_commands"):
            return 1

        (devlyn / SEAL_NAME).unlink()
        (devlyn / "pipeline.state.json").write_text(json.dumps({"run_id": "rs-seal", "phases": {}}), encoding="utf-8")
        mechanical()
        no_span = subprocess.run([sys.executable, script_path, "--seal"], cwd=root,
                                 capture_output=True, text=True, encoding="utf-8")
        if (devlyn / SEAL_NAME).exists() or no_span.returncode != 2:
            print("a run with no open VERIFY span wrote or accepted a seal", file=sys.stderr)
            return 1
    return 0


def run_self_test() -> int:
    try:
        loads_strict_json('{"verification_commands":[],"verification_commands":[{}]}')
    except ValueError as exc:
        assert "duplicate JSON key" in str(exc)
    else:
        raise AssertionError("duplicate expected-contract key was accepted")
    # Hermeticity: a pipeline replay exports BENCH_WORKDIR at the live repo;
    # inherited into scenario children it wins over their tmp cwd (the
    # default-mode work resolution below) and re-executes the LIVE
    # .devlyn/spec-verify.json — with lint as the live command this mutually
    # recursed (lint runs this self-test) into an unbounded spawn storm
    # (observed 2026-08-03, iter-0089 canary).
    os.environ.pop("BENCH_WORKDIR", None)
    script_path = str(Path(__file__).resolve())
    with tempfile.TemporaryDirectory() as help_tmp:
        for help_flag in ("--help", "-h"):
            help_result = subprocess.run(
                [sys.executable, script_path, help_flag],
                cwd=help_tmp,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if help_result.returncode != 0 or "usage:" not in help_result.stdout:
                print(f"{help_flag} did not return usage successfully", file=sys.stderr)
                return 1
            if (Path(help_tmp) / ".devlyn").exists():
                print(f"{help_flag} mutated .devlyn", file=sys.stderr)
                return 1
        unknown_result = subprocess.run(
            [sys.executable, script_path, "--not-a-real-option"],
            cwd=help_tmp,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if unknown_result.returncode != 2 or "unknown argument" not in unknown_result.stderr:
            print("unknown option did not fail closed", file=sys.stderr)
            return 1
        if (Path(help_tmp) / ".devlyn").exists():
            print("unknown option mutated .devlyn", file=sys.stderr)
            return 1
    runner = process_evidence_module()
    try:
        mechanical_evidence_identity({"version": "3.0", "phases": {}}, runner)
    except runner.EvidenceError as exc:
        assert "schema-v3 MECHANICAL evidence identity is invalid" in str(exc)
    else:
        raise AssertionError("schema-v3 MECHANICAL evidence accepted missing run identity")
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        devlyn = work / ".devlyn"
        devlyn.mkdir()
        assert path_matches_surface("src/a/example.py", ["src/{a,b}/**"])
        assert path_matches_surface("src/b/example.py", ["src/{a,b}/**"])
        assert not path_matches_surface("src/c/example.py", ["src/{a,b}/**"])
        for entry in ("src/{a,b", "src/{a,}/**", "src/{a,{b,c}}", "src/{a,**}"):
            try:
                path_matches_surface("src/a/example.py", [entry])
            except ValueError as exc:
                assert entry in str(exc) and "supported form" in str(exc)
            else:
                raise AssertionError(f"malformed brace glob accepted: {entry}")
        spec_md = work / "spec.md"
        spec_md.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- probe must pass visible marker.\n", encoding="utf-8")
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)}
        }), encoding="utf-8")
        (devlyn / "spec-verify.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf ok", "exit_code": 0, "stdout_contains": ["ok"]}
            ]
        }) + "\n", encoding="utf-8")
        probes_dir = devlyn / "probes"
        probes_dir.mkdir()
        probe_script = probes_dir / "P1.py"
        probe_script.write_text("print('probe-ok')\n", encoding="utf-8")
        risk_probe_payload = {
            "id": "P1",
            "derived_from": "probe must pass visible marker.",
            "cmd": "python3 .devlyn/probes/P1.py",
            "exit_code": 0,
            "timeout_sec": 5,
            "stdout_contains": ["probe-ok"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                ],
            },
        }
        (devlyn / "risk-probes.jsonl").write_text(json.dumps(risk_probe_payload) + "\n", encoding="utf-8")
        loaded_probes, loaded_probe_error = load_risk_probes(
            devlyn, spec_md, require_present=True
        )
        if loaded_probe_error or loaded_probes[0].get("timeout_sec") != 5:
            print("risk-probe timeout_sec was not preserved", file=sys.stderr)
            print(loaded_probe_error, file=sys.stderr)
            return 1

        if verification_timeout_sec({"cmd": "printf default"}) != DEFAULT_TIMEOUT_SEC:
            print("absent timeout_sec did not resolve to DEFAULT_TIMEOUT_SEC", file=sys.stderr)
            return 1

        inline_timeout_spec = work / "inline-timeout-spec.md"
        inline_timeout_devlyn = work / "inline-timeout-devlyn"
        for invalid_timeout in (True, 0, -1, 601, "60"):
            inline_timeout_spec.write_text(
                "# Timeout validation\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
                + json.dumps({
                    "verification_commands": [
                        {"cmd": "printf ok", "timeout_sec": invalid_timeout}
                    ]
                })
                + "\n```\n",
                encoding="utf-8",
            )
            _found, staged, inline_error = stage_from_source(
                inline_timeout_spec, inline_timeout_devlyn
            )
            if staged or not inline_error or "timeout_sec" not in inline_error:
                print(
                    f"inline carrier accepted invalid timeout_sec={invalid_timeout!r}",
                    file=sys.stderr,
                )
                return 1

        inline_timeout_spec.write_text(
            "# Timeout preservation\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
            + json.dumps({
                "verification_commands": [
                    {"cmd": "printf ok", "timeout_sec": 5}
                ]
            })
            + "\n```\n",
            encoding="utf-8",
        )
        _found, staged, inline_error = stage_from_source(
            inline_timeout_spec, inline_timeout_devlyn
        )
        inline_staged = loads_strict_json(
            (inline_timeout_devlyn / "spec-verify.json").read_text(encoding="utf-8")
        )
        if (
            not staged
            or inline_error
            or inline_staged["verification_commands"][0].get("timeout_sec") != 5
        ):
            print("inline carrier did not preserve timeout_sec", file=sys.stderr)
            return 1

        sibling_timeout_root = work / "sibling-timeout"
        sibling_timeout_root.mkdir()
        sibling_timeout_devlyn = sibling_timeout_root / ".devlyn"
        sibling_timeout_spec = sibling_timeout_root / "spec.md"
        sibling_timeout_spec.write_text("# Sibling timeout\n", encoding="utf-8")
        sibling_timeout_expected = sibling_timeout_root / "spec.expected.json"
        for invalid_timeout in (True, 601):
            sibling_timeout_expected.write_text(json.dumps({
                "verification_commands": [
                    {"cmd": "printf ok", "timeout_sec": invalid_timeout}
                ]
            }) + "\n", encoding="utf-8")
            found, staged, sibling_error, _path, _data = stage_from_expected(
                sibling_timeout_spec, sibling_timeout_devlyn
            )
            if not found or staged or not sibling_error or "timeout_sec" not in sibling_error:
                print(
                    f"sibling carrier accepted invalid timeout_sec={invalid_timeout!r}",
                    file=sys.stderr,
                )
                return 1

        sibling_timeout_expected.write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf ok", "timeout_sec": 5}
            ]
        }) + "\n", encoding="utf-8")
        found, staged, sibling_error, _path, _data = stage_from_expected(
            sibling_timeout_spec, sibling_timeout_devlyn
        )
        sibling_staged = loads_strict_json(
            (sibling_timeout_devlyn / "spec-verify.json").read_text(encoding="utf-8")
        )
        if (
            not found
            or not staged
            or sibling_error
            or sibling_staged["verification_commands"][0].get("timeout_sec") != 5
        ):
            print("sibling carrier did not preserve timeout_sec", file=sys.stderr)
            return 1

        timeout_run_root = work / "timeout-run"
        timeout_run_root.mkdir()
        timeout_run_devlyn = timeout_run_root / ".devlyn"
        timeout_run_devlyn.mkdir()
        timeout_run_spec = timeout_run_root / "spec.md"
        timeout_run_spec.write_text(
            "# Timeout execution\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
            + json.dumps({
                "verification_commands": [
                    {
                        "cmd": "python3 -c \"import time; time.sleep(2)\"",
                        "timeout_sec": 1,
                    },
                    {
                        "cmd": "python3 -c \"import time; time.sleep(1)\"",
                        "timeout_sec": 5,
                    },
                    {
                        "cmd": "printf 'Operation not permitted' >&2; exit 1",
                    },
                ]
            })
            + "\n```\n",
            encoding="utf-8",
        )
        (timeout_run_devlyn / "pipeline.state.json").write_text(json.dumps({
            "run_id": "rs-timeout-run",
            "source": {"type": "spec", "spec_path": str(timeout_run_spec)},
            "phases": {"verify": {"round": 2}},
        }), encoding="utf-8")
        timeout_run = subprocess.run(
            [sys.executable, script_path],
            cwd=timeout_run_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if timeout_run.returncode == 0:
            print("declared one-second timeout did not fail", file=sys.stderr)
            return 1
        timeout_document = loads_strict_json(
            (timeout_run_devlyn / "spec-verify.results.json").read_text(encoding="utf-8")
        )
        timeout_results = timeout_document["commands"]
        timeout_findings = [
            loads_strict_json(line)
            for line in (timeout_run_devlyn / FINDINGS_NAME).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if (
            timeout_results[0].get("reason") != "timeout"
            or timeout_results[0].get("timeout_sec") != 1
            or not timeout_results[1].get("pass")
            or timeout_results[2].get("reason") != "exit"
            or timeout_results[2].get("classification") != {
                "kind": "product_result", "operation": None,
            }
        ):
            print("declared timeout budgets were not honored", file=sys.stderr)
            print(timeout_results, file=sys.stderr)
            return 1
        timeout_carrier = timeout_document.get("process_evidence") or {}
        timeout_manifest_path = (
            ".devlyn/process-evidence/rs-timeout-run/verify/round-2/manifest.json"
        )
        timeout_manifest = loads_strict_json(
            (timeout_run_root / timeout_manifest_path).read_text(encoding="utf-8")
        )
        if (
            timeout_carrier.get("manifest", {}).get("path") != timeout_manifest_path
            or [entry.get("id") for entry in timeout_manifest.get("entries", [])] != [
                "verification-command-0001",
                "verification-command-0002",
                "verification-command-0003",
            ]
            or any(
                not (timeout_run_root / entry[stream]["path"]).is_file()
                for entry in timeout_manifest.get("entries", [])
                for stream in ("stdout", "stderr")
            )
        ):
            print("literal commands did not emit sealed VERIFY MECHANICAL evidence", file=sys.stderr)
            print(timeout_document, file=sys.stderr)
            return 1
        timeout_finding = timeout_findings[0] if timeout_findings else {}
        if (
            timeout_finding.get("rule_id") != "correctness.verification-timeout"
            or "after 1s" not in timeout_finding.get("message", "")
            or "timeout_sec" not in timeout_finding.get("message", "")
            or "600" not in timeout_finding.get("fix_hint", "")
        ):
            print("timeout finding did not carry the distinct budget contract", file=sys.stderr)
            print(timeout_finding, file=sys.stderr)
            return 1
        if (
            not any(
                finding.get("rule_id") == "correctness.spec-literal-mismatch"
                for finding in timeout_findings
            )
            or "BLOCKED:build-env-underprovisioned" in timeout_run.stderr
        ):
            print("ordinary restricted-looking stderr did not remain a product finding", file=sys.stderr)
            print(timeout_findings, file=sys.stderr)
            print(timeout_run.stderr, file=sys.stderr)
            return 1

        env = os.environ.copy()
        env["BENCH_WORKDIR"] = str(work)
        validate_without_digest = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if validate_without_digest.returncode != 0:
            print("--validate-risk-probes rejected valid probes without digest", file=sys.stderr)
            print(validate_without_digest.stderr, file=sys.stderr)
            return 1
        risk_digest, digest_error = risk_probes_digest(devlyn)
        if digest_error or not re.fullmatch(r"[0-9a-f]{64}", risk_digest or ""):
            print(f"risk_probes_digest rejected valid probes: {digest_error} {risk_digest!r}", file=sys.stderr)
            return 1
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "run_id": "rs-risk-probes",
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": True},
            "risk_probes_digest": risk_digest,
            "phases": {"verify": {"round": 4}},
        }), encoding="utf-8")
        good = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if good.returncode != 0:
            print(good.stderr, file=sys.stderr)
            return 1
        good_document = loads_strict_json(
            (devlyn / "spec-verify.results.json").read_text(encoding="utf-8")
        )
        good_manifest_path = good_document.get("process_evidence", {}).get("manifest", {}).get("path")
        good_manifest = (
            loads_strict_json((work / good_manifest_path).read_text(encoding="utf-8"))
            if isinstance(good_manifest_path, str)
            else {}
        )
        if (
            good_manifest_path != ".devlyn/process-evidence/rs-risk-probes/verify/round-4/manifest.json"
            or [entry.get("id") for entry in good_manifest.get("entries", [])] != [
                "verification-command-0001", "risk-probe-0002",
            ]
        ):
            print("literal command and risk probe did not share the sealed manifest", file=sys.stderr)
            print(good_document, file=sys.stderr)
            return 1

        probe_script.write_text("print('mutated-probe')\n", encoding="utf-8")
        mutated_script = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if mutated_script.returncode == 0:
            print("--include-risk-probes accepted mutated probe script bytes", file=sys.stderr)
            return 1
        integrity_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8")
        if "correctness.risk-probe-integrity" not in integrity_findings:
            print("mutated probe script did not emit correctness.risk-probe-integrity", file=sys.stderr)
            print(integrity_findings, file=sys.stderr)
            return 1
        probe_script.write_text("print('probe-ok')\n", encoding="utf-8")

        mutated_payload = dict(risk_probe_payload)
        mutated_payload["id"] = "P1-mutated"
        (devlyn / "risk-probes.jsonl").write_text(json.dumps(mutated_payload) + "\n", encoding="utf-8")
        mutated_jsonl = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if mutated_jsonl.returncode == 0:
            print("--include-risk-probes accepted mutated risk-probes.jsonl bytes", file=sys.stderr)
            return 1
        integrity_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8")
        if "correctness.risk-probe-integrity" not in integrity_findings:
            print("mutated risk-probes.jsonl did not emit correctness.risk-probe-integrity", file=sys.stderr)
            print(integrity_findings, file=sys.stderr)
            return 1
        (devlyn / "risk-probes.jsonl").write_text(json.dumps(risk_probe_payload) + "\n", encoding="utf-8")

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": True},
        }), encoding="utf-8")
        missing_digest = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if missing_digest.returncode == 0:
            print("--include-risk-probes accepted enabled risk probes with missing digest", file=sys.stderr)
            return 1
        integrity_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8")
        if "correctness.risk-probe-integrity" not in integrity_findings:
            print("missing risk_probes_digest did not emit correctness.risk-probe-integrity", file=sys.stderr)
            print(integrity_findings, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").unlink()
        _digest, missing_jsonl_error = risk_probes_digest(devlyn)
        if "missing .devlyn/risk-probes.jsonl" not in (missing_jsonl_error or ""):
            print(f"risk_probes_digest accepted missing risk-probes.jsonl: {missing_jsonl_error}", file=sys.stderr)
            return 1
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": True},
            "risk_probes_digest": risk_digest,
        }), encoding="utf-8")
        missing_required_probe = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if missing_required_probe.returncode == 0:
            print("--include-risk-probes accepted missing required risk-probes.jsonl", file=sys.stderr)
            return 1
        if "risk probes integrity failed" not in missing_required_probe.stderr:
            print("--include-risk-probes missing required probe had the wrong integrity error", file=sys.stderr)
            print(missing_required_probe.stderr, file=sys.stderr)
            return 1

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": False},
        }), encoding="utf-8")
        missing_optional_probe = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if missing_optional_probe.returncode != 0:
            print("--include-risk-probes rejected optional missing risk-probes.jsonl", file=sys.stderr)
            print(missing_optional_probe.stderr, file=sys.stderr)
            return 1

        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(spec_md)},
            "risk_profile": {"risk_probes_enabled": "true"},
        }), encoding="utf-8")
        malformed_risk_probe_state = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }), encoding="utf-8")
        malformed_risk_profile = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }), encoding="utf-8")
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P1",
            "derived_from": "probe must pass visible marker.",
            "cmd": "printf probe-ok",
            "exit_code": 0,
            "stdout_contains": ["probe-ok"],
            "stdout_not_contains": [],
            "tags": ["shape_contract"],
            "tag_evidence": {
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                ],
            },
        }) + "\n", encoding="utf-8")

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
            encoding="utf-8",
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
            encoding="utf-8",
        )
        if bad_complexity_check.returncode == 0:
            print("unsupported spec complexity was accepted", file=sys.stderr)
            return 1
        if "frontmatter complexity must be one of" not in bad_complexity_check.stderr:
            print("unsupported spec complexity did not report the allowed values", file=sys.stderr)
            print(bad_complexity_check.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P2",
            "derived_from": "probe must pass visible marker.",
            "cmd": "node $BENCH_FIXTURE_DIR/verifiers/hidden.js",
            "exit_code": 0,
        }) + "\n", encoding="utf-8")
        bad = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if bad.returncode == 0:
            print("hidden verifier path was accepted", file=sys.stderr)
            return 1

        probes_dir = devlyn / "probes"
        probes_dir.mkdir(exist_ok=True)
        (probes_dir / "Pscript.py").write_text("print('script-ok')\n", encoding="utf-8")
        script_probe_payload = {
            **risk_probe_payload,
            "id": "Pscript",
            "cmd": "python3 .devlyn/probes/Pscript.py",
            "stdout_contains": ["script-ok"],
        }
        (devlyn / "risk-probes.jsonl").write_text(json.dumps(script_probe_payload) + "\n", encoding="utf-8")
        good_script_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if good_script_probe.returncode != 0:
            print("risk probe script file was rejected", file=sys.stderr)
            print(good_script_probe.stderr, file=sys.stderr)
            return 1

        mixed_script_payload = {
            **script_probe_payload,
            "id": "Pmixed",
            "cmd": "python3 .devlyn/probes/Pscript.py && python3 ./.devlyn/probes/P1.py",
        }
        (devlyn / "risk-probes.jsonl").write_text(json.dumps(mixed_script_payload) + "\n", encoding="utf-8")
        mixed_script_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if mixed_script_probe.returncode != 0:
            print("canonical and ./-alias probe script references were rejected", file=sys.stderr)
            print(mixed_script_probe.stderr, file=sys.stderr)
            return 1
        mixed_digest, mixed_digest_error = risk_probes_digest(devlyn)
        if mixed_digest_error:
            print(mixed_digest_error, file=sys.stderr)
            return 1
        (probes_dir / "Pscript.py").write_text("print('script-mutated')\n", encoding="utf-8")
        canonical_mutated_digest, canonical_mutated_error = risk_probes_digest(devlyn)
        (probes_dir / "Pscript.py").write_text("print('script-ok')\n", encoding="utf-8")
        if canonical_mutated_error:
            print(canonical_mutated_error, file=sys.stderr)
            return 1
        probe_script.write_text("print('probe-mutated')\n", encoding="utf-8")
        alias_mutated_digest, alias_mutated_error = risk_probes_digest(devlyn)
        probe_script.write_text("print('probe-ok')\n", encoding="utf-8")
        if alias_mutated_error:
            print(alias_mutated_error, file=sys.stderr)
            return 1
        if len({mixed_digest, canonical_mutated_digest, alias_mutated_digest}) != 3:
            print("probe digest did not change for both canonical and ./-alias scripts", file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "Pmissing",
            "derived_from": "probe must pass visible marker.",
            "cmd": "python3 ./.devlyn/probes/missing.py",
            "exit_code": 0,
        }) + "\n", encoding="utf-8")
        missing_script_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if missing_script_probe.returncode == 0:
            print("risk probe missing script file was accepted", file=sys.stderr)
            return 1
        if "references missing probe script" not in missing_script_probe.stderr:
            print("missing risk probe script had the wrong error", file=sys.stderr)
            print(missing_script_probe.stderr, file=sys.stderr)
            return 1
        _digest, missing_script_error = risk_probes_digest(devlyn)
        if "referenced probe script is missing" not in (missing_script_error or ""):
            print(f"risk_probes_digest accepted a missing referenced script: {missing_script_error}", file=sys.stderr)
            return 1

        for bad_form in (
            "../.devlyn/probes/Pscript.py",
            "/tmp/.devlyn/probes/Pscript.py",
            "$PWD/.devlyn/probes/Pscript.py",
            "././.devlyn/probes/Pscript.py",
        ):
            (devlyn / "risk-probes.jsonl").write_text(json.dumps({
                "id": "Pbadref",
                "derived_from": "probe must pass visible marker.",
                "cmd": f"python3 {bad_form}",
                "exit_code": 0,
            }) + "\n", encoding="utf-8")
            bad_ref_probe = subprocess.run(
                [sys.executable, script_path, "--validate-risk-probes"],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            _digest, bad_ref_error = risk_probes_digest(devlyn)
            unrecognized = unrecognized_risk_probe_reference(f"python3 {bad_form}")
            expected_error = f"risk-probes[0].cmd has {unrecognized}"
            if (
                bad_ref_probe.returncode == 0
                or expected_error not in bad_ref_probe.stderr
                or expected_error not in (bad_ref_error or "")
            ):
                print(f"bad probe script reference was not rejected: {bad_form}", file=sys.stderr)
                print(bad_ref_probe.stderr, file=sys.stderr)
                print(bad_ref_error, file=sys.stderr)
                return 1

        (probes_dir / "Phidden.py").write_text("print('benchmark/auto-resolve/fixtures')\n", encoding="utf-8")
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "Phidden",
            "derived_from": "probe must pass visible marker.",
            "cmd": "python3 .devlyn/probes/Phidden.py",
            "exit_code": 0,
        }) + "\n", encoding="utf-8")
        hidden_script_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if hidden_script_probe.returncode == 0:
            print("risk probe script containing a hidden fixture path was accepted", file=sys.stderr)
            return 1
        if "whose content references hidden fixture/verifier paths" not in hidden_script_probe.stderr:
            print("hidden-path risk probe script had the wrong error", file=sys.stderr)
            print(hidden_script_probe.stderr, file=sys.stderr)
            return 1

        (probes_dir / "Pexternal.py").write_text("print('https://example.com/check')\n", encoding="utf-8")
        (devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "Pexternal",
            "derived_from": "probe must pass visible marker.",
            "cmd": "python3 .devlyn/probes/Pexternal.py",
            "exit_code": 0,
        }) + "\n", encoding="utf-8")
        external_script_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if external_script_probe.returncode == 0:
            print("risk probe script containing an external URL was accepted", file=sys.stderr)
            return 1
        if "whose content references external URL" not in external_script_probe.stderr:
            print("external-URL risk probe script had the wrong error", file=sys.stderr)
            print(external_script_probe.stderr, file=sys.stderr)
            return 1

        (devlyn / "risk-probes.jsonl").write_text('{"id":NaN}\n', encoding="utf-8")
        bad_probe_nan = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }) + "\n", encoding="utf-8")
        bad_error_ref = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if bad_error_ref.returncode == 0:
            print("error_contract with unrelated derived_from was accepted", file=sys.stderr)
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
        }) + "\n", encoding="utf-8")
        spec_md.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- probe must pass visible marker.\n", encoding="utf-8")
        expected_good = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_good.returncode != 0:
            print(expected_good.stderr, file=sys.stderr)
            return 1

        spec_md.write_text(
            "---\nid: bad-sibling\ncomplexity: hihg\n---\n\n# Bad sibling\n\n<!-- devlyn:verification -->\n## Verification\n\n- ok\n",
            encoding="utf-8",
        )
        expected_bad_sibling_complexity = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_bad_sibling_complexity.returncode == 0:
            print("unsupported sibling spec complexity was accepted by --check-expected", file=sys.stderr)
            return 1
        if "frontmatter complexity must be one of" not in expected_bad_sibling_complexity.stderr:
            print("--check-expected did not report unsupported sibling spec complexity", file=sys.stderr)
            print(expected_bad_sibling_complexity.stderr, file=sys.stderr)
            return 1
        spec_md.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- probe must pass visible marker.\n", encoding="utf-8")

        expected_json.write_text(json.dumps({"verification_commands": []}) + "\n", encoding="utf-8")
        expected_empty_runtime = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_empty_runtime.returncode == 0:
            print("empty verification_commands should fail for runtime specs", file=sys.stderr)
            return 1

        pure_root = work / "pure-design"
        pure_root.mkdir()
        pure_spec = pure_root / "spec.md"
        pure_spec.write_text(
            "# Pure design\n\n<!-- devlyn:verification -->\n## Verification\n\n- no runtime verification commands.\n",
            encoding="utf-8",
        )
        pure_expected = pure_root / "spec.expected.json"
        pure_expected.write_text(
            json.dumps({"verification_commands": [], "pure_design": True}) + "\n",
            encoding="utf-8",
        )
        expected_empty_design = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(pure_expected)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_empty_design.returncode != 0:
            print("empty verification_commands should be valid for pure-design specs", file=sys.stderr)
            print(expected_empty_design.stderr, file=sys.stderr)
            return 1

        pure_expected.write_text(
            json.dumps({
                "verification_commands": [{"cmd": "printf ok", "stdout_contains": ["ok"]}],
                "pure_design": True,
            }) + "\n",
            encoding="utf-8",
        )
        pure_design_contradiction = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(pure_expected)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if pure_design_contradiction.returncode == 0:
            print("pure_design: true with non-empty verification_commands was accepted", file=sys.stderr)
            return 1
        if "contradictory" not in pure_design_contradiction.stderr:
            print("pure_design contradiction did not report the right error", file=sys.stderr)
            print(pure_design_contradiction.stderr, file=sys.stderr)
            return 1

        pure_expected.write_text(
            json.dumps({"verification_commands": [], "pure_design": "yes"}) + "\n",
            encoding="utf-8",
        )
        pure_design_not_boolean = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(pure_expected)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if pure_design_not_boolean.returncode == 0:
            print("non-boolean pure_design was accepted", file=sys.stderr)
            return 1
        if "pure_design must be a boolean" not in pure_design_not_boolean.stderr:
            print("non-boolean pure_design did not report the right error", file=sys.stderr)
            print(pure_design_not_boolean.stderr, file=sys.stderr)
            return 1

        expected_json.write_text(json.dumps({"unknown": True}) + "\n", encoding="utf-8")
        expected_bad = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_bad.returncode == 0:
            print("spec.expected.json with unknown key was accepted", file=sys.stderr)
            return 1

        expected_json.write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contians": ["ok"]}]
        }) + "\n", encoding="utf-8")
        expected_bad_command = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_bad_command.returncode == 0:
            print("spec.expected.json command with unknown key was accepted", file=sys.stderr)
            return 1

        expected_json.write_text("[1]\n", encoding="utf-8")
        expected_non_object = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
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

        expected_json.write_text("{broken\n", encoding="utf-8")
        expected_invalid_json = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
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

        expected_json.write_text('{"verification_commands": NaN}\n', encoding="utf-8")
        expected_nan_json = subprocess.run(
            [sys.executable, script_path, "--check-expected", str(expected_json)],
            cwd=work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if expected_nan_json.returncode == 0:
            print("NaN spec.expected.json was accepted", file=sys.stderr)
            return 1
        if "invalid JSON numeric constant: NaN" not in expected_nan_json.stderr:
            print("NaN spec.expected.json did not report invalid numeric constant", file=sys.stderr)
            print(expected_nan_json.stderr, file=sys.stderr)
            return 1

        external_diff_root = work / "external-diff-mode-authority"
        external_diff_root.mkdir()
        external_diff_devlyn = external_diff_root / ".devlyn"
        external_diff_devlyn.mkdir()
        external_diff_spec = external_diff_root / "spec.md"
        external_diff_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            "- external diff remains verify-only.\n",
            encoding="utf-8",
        )
        (external_diff_root / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf external-diff-ok", "stdout_contains": ["external-diff-ok"]}
            ]
        }) + "\n", encoding="utf-8")
        (external_diff_root / "external-only.txt").write_text("base\n", encoding="utf-8")
        (external_diff_root / "outside.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=external_diff_root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=external_diff_root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base"],
            cwd=external_diff_root,
            check=True,
        )
        external_diff_base_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=external_diff_root, text=True,
            encoding="utf-8",
        ).strip()
        (external_diff_root / "outside.txt").write_text("worktree-only\n", encoding="utf-8")
        (external_diff_devlyn / "external-diff.patch").write_text(
            "diff --git a/external-only.txt b/external-only.txt\n"
            "--- a/external-only.txt\n"
            "+++ b/external-only.txt\n"
            "@@ -1 +1 @@\n"
            "-base\n"
            "+external\n",
            encoding="utf-8",
        )
        (external_diff_devlyn / "plan.md").write_text(
            "<!-- devlyn:authorized-surface -->\n## Files to touch\n\n"
            "```json\n{\"authorized_surface\": [\"external-only.txt\"]}\n```\n",
            encoding="utf-8",
        )
        (external_diff_devlyn / "untracked.baseline").write_text(EMPTY_BASELINE, encoding="utf-8")
        external_diff_state = {
            "mode": "free-form",
            "source": {"type": "spec", "spec_path": str(external_diff_spec)},
            "base_ref": {"sha": external_diff_base_sha},
        }
        external_diff_state_path = external_diff_devlyn / "pipeline.state.json"
        external_diff_state_path.write_text(json.dumps(external_diff_state) + "\n", encoding="utf-8")
        external_diff_free_form = subprocess.run(
            [sys.executable, script_path],
            cwd=external_diff_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        external_diff_findings_path = external_diff_devlyn / FINDINGS_NAME
        external_diff_free_form_findings = (
            external_diff_findings_path.read_text(encoding="utf-8")
            if external_diff_findings_path.is_file()
            else ""
        )
        external_diff_state["mode"] = "verify-only"
        external_diff_state_path.write_text(json.dumps(external_diff_state) + "\n", encoding="utf-8")
        external_diff_verify_only = subprocess.run(
            [sys.executable, script_path],
            cwd=external_diff_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if external_diff_free_form.returncode != 1:
            print("non-verify-only mode accepted .devlyn/external-diff.patch", file=sys.stderr)
            print(external_diff_free_form.stderr, file=sys.stderr)
            return 1
        if (
            '"rule_id": "correctness.spec-verify-malformed"'
            not in external_diff_free_form_findings
            or '"severity": "CRITICAL"' not in external_diff_free_form_findings
            or ".devlyn/external-diff.patch" not in external_diff_free_form_findings
            or "free-form" not in external_diff_free_form_findings
            or "verify-only" not in external_diff_free_form_findings
            or "Remove `.devlyn/external-diff.patch` for ordinary runs"
            not in external_diff_free_form_findings
            or "only when intentionally verifying an external patch"
            not in external_diff_free_form_findings
        ):
            print(
                "non-verify-only external diff did not emit the named CRITICAL finding and remediation",
                file=sys.stderr,
            )
            print(external_diff_free_form_findings, file=sys.stderr)
            return 1
        if external_diff_verify_only.returncode != 0:
            print("verify-only external diff was rejected or not consumed", file=sys.stderr)
            print(external_diff_verify_only.stderr, file=sys.stderr)
            return 1

        spec_integrity = work / "spec-integrity"
        spec_integrity.mkdir()
        spec_integrity_devlyn = spec_integrity / ".devlyn"
        spec_integrity_devlyn.mkdir()
        integrity_spec = spec_integrity / "spec.md"
        integrity_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
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
        }), encoding="utf-8")
        spec_bad_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=spec_integrity,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }), encoding="utf-8")
        spec_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=spec_integrity,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if spec_hash_run.returncode != 0:
            print(spec_hash_run.stderr, file=sys.stderr)
            return 1
        staged_spec_hash = loads_strict_json((spec_integrity_devlyn / "spec-verify.json").read_text(encoding="utf-8"))
        if staged_spec_hash.get("verification_commands", [{}])[0].get("cmd") != "printf spec-hash-ok":
            print("spec source with matching source.spec_sha256 was not staged", file=sys.stderr)
            return 1

        generated_user = work / "generated-user"
        generated_user.mkdir()
        generated_devlyn = generated_user / ".devlyn"
        generated_devlyn.mkdir()
        generated_criteria = generated_user / ".devlyn" / "criteria.generated.md"
        generated_criteria.write_text(
            "# Criteria\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
            "{\"verification_commands\":[{\"cmd\":\"printf generated-ok\",\"stdout_contains\":[\"generated-ok\"]}]}\n"
            "```\n",
            encoding="utf-8",
        )
        generated_raw = generated_criteria.read_bytes()
        generated_criteria.unlink()
        missing_source_marker = generated_user / "missing-source-command-ran"
        for pointer, bench in (
            ({}, False),
            ({"criteria_path": None}, False),
            ({"criteria_path": ""}, False),
            ({"criteria_path": ".devlyn/criteria.generated.md"}, False),
            ({"criteria_path": str(generated_criteria)}, False),
            ({"criteria_path": str(generated_user)}, False),
            ({"criteria_path": str(generated_criteria)}, True),
        ):
            (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
                "source": {"type": "generated", "criteria_sha256": hashlib.sha256(generated_raw).hexdigest(), **pointer},
                "risk_profile": {"risk_probes_enabled": True},
            }), encoding="utf-8")
            (generated_devlyn / "spec-verify.json").write_text(json.dumps({
                "verification_commands": [{"cmd": "printf unexpected > missing-source-command-ran"}],
            }), encoding="utf-8")
            (generated_devlyn / "spec-verify.results.json").unlink(missing_ok=True)
            missing_source_env = dict(os.environ)
            if bench:
                missing_source_env["BENCH_WORKDIR"] = str(generated_user)
            missing_source_run = subprocess.run(
                [sys.executable, script_path, "--include-risk-probes"],
                cwd=generated_user, env=missing_source_env,
                capture_output=True, text=True, encoding="utf-8",
            )
            if (
                missing_source_run.returncode != 1
                or "source.criteria_path" not in missing_source_run.stderr
                or f"declared path: {pointer.get('criteria_path')!r}" not in missing_source_run.stderr
            ):
                print(f"missing generated source was not rejected: {pointer}, {bench}: {missing_source_run.stderr}", file=sys.stderr)
                return 1
            missing_findings = [loads_strict_json(line) for line in
                                (generated_devlyn / FINDINGS_NAME).read_text(encoding="utf-8").splitlines()]
            if (
                len(missing_findings) != 1
                or missing_findings[0]["rule_id"] != "correctness.spec-verify-malformed"
                or missing_findings[0]["severity"] != "CRITICAL"
                or missing_findings[0]["file"] != ".devlyn/pipeline.state.json"
                or missing_findings[0]["phase"] != MECHANICAL_PHASE
                or missing_source_marker.exists()
                or (generated_devlyn / "spec-verify.results.json").exists()
            ):
                print(f"missing generated source lost its finding or executed a stale command: {missing_findings}", file=sys.stderr)
                return 1
        generated_criteria.write_bytes(generated_raw)
        (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "generated", "criteria_path": str(generated_criteria)}
        }), encoding="utf-8")
        generated_missing_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }), encoding="utf-8")
        generated_bad_hash_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }), encoding="utf-8")
        generated_run = subprocess.run(
            [sys.executable, script_path],
            cwd=generated_user,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if generated_run.returncode != 0:
            print(generated_run.stderr, file=sys.stderr)
            return 1
        staged_generated = loads_strict_json((generated_devlyn / "spec-verify.json").read_text(encoding="utf-8"))
        if staged_generated.get("verification_commands", [{}])[0].get("cmd") != "printf generated-ok":
            print("generated criteria carrier was not staged into .devlyn/spec-verify.json", file=sys.stderr)
            return 1

        inline_marker = generated_user / "inline-command-ran"
        inline_command = "printf bad > inline-command-ran; printf bad"
        for source_type in ("generated", "spec"):
            for contract, diagnostic in (
                ({"verification_commands": [{"cmd": inline_command}],
                  "required_files": ["missing.txt"]}, "unsupported inline key(s): required_files"),
                ({"verification_commands": [{"cmd": inline_command,
                  "stdout_not_contians": ["bad"]}]}, "unknown key(s): stdout_not_contians"),
                ({"verification_commands": [{"cmd": inline_command,
                  "stdout_not_contains": ["bad"]}]}, None),
            ):
                inline_marker.unlink(missing_ok=True)
                (generated_devlyn / FINDINGS_NAME).unlink(missing_ok=True)
                generated_criteria.write_text(
                    "# Inline constraints\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
                    + json.dumps(contract) + "\n```\n", encoding="utf-8",
                )
                prefix = "criteria" if source_type == "generated" else "spec"
                (generated_devlyn / "pipeline.state.json").write_text(json.dumps({
                    "source": {
                        "type": source_type,
                        f"{prefix}_path": str(generated_criteria),
                        f"{prefix}_sha256": hashlib.sha256(generated_criteria.read_bytes()).hexdigest(),
                    }
                }), encoding="utf-8")
                # A stale valid carrier must not bypass malformed source validation.
                (generated_devlyn / "spec-verify.json").write_text(json.dumps({
                    "verification_commands": [{"cmd": inline_command}]
                }), encoding="utf-8")
                inline_check = subprocess.run(
                    [sys.executable, script_path, "--check", str(generated_criteria)],
                    cwd=generated_user, capture_output=True, text=True, encoding="utf-8",
                )
                inline_run = subprocess.run(
                    [sys.executable, script_path], cwd=generated_user,
                    capture_output=True, text=True, encoding="utf-8",
                )
                assert inline_check.returncode == (2 if diagnostic else 0)
                assert inline_run.returncode == 1
                if diagnostic:
                    assert diagnostic in inline_check.stderr and diagnostic in inline_run.stderr
                    assert not inline_marker.exists(), "malformed inline constraint executed a command"
                else:
                    assert inline_marker.exists(), "valid inline output guard was not executed"
                    assert "correctness.spec-literal-mismatch" in (
                        generated_devlyn / FINDINGS_NAME
                    ).read_text(encoding="utf-8")

        real_user = work / "real-user"
        real_user.mkdir()
        real_devlyn = real_user / ".devlyn"
        real_devlyn.mkdir()
        real_spec = real_user / "spec.md"
        real_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- sibling command must print sibling-ok.\n",
            encoding="utf-8",
        )
        (real_user / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf sibling-ok", "stdout_contains": ["sibling-ok"]}
            ]
        }) + "\n", encoding="utf-8")
        (real_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(real_spec)}
        }), encoding="utf-8")
        sibling_check = subprocess.run(
            [sys.executable, script_path, "--check", str(real_spec)],
            cwd=real_user, capture_output=True, text=True, encoding="utf-8",
        )
        if sibling_check.returncode != 0 or (real_devlyn / "spec-verify.json").exists():
            print(f"sibling authoring failed or staged commands: {sibling_check.stderr}", file=sys.stderr)
            return 1
        sibling_run = subprocess.run(
            [sys.executable, script_path],
            cwd=real_user,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if sibling_run.returncode != 0:
            print(sibling_run.stderr, file=sys.stderr)
            return 1
        staged = loads_strict_json((real_devlyn / "spec-verify.json").read_text(encoding="utf-8"))
        if staged.get("verification_commands", [{}])[0].get("cmd") != "printf sibling-ok":
            print("sibling spec.expected.json was not staged into .devlyn/spec-verify.json", file=sys.stderr)
            return 1

        pure_prose = "# Design\n\n<!-- devlyn:verification -->\n## Verification\n\n- No runtime verification commands.\n"
        stale_command = {"verification_commands": [{"cmd": "printf unexpected-command"}]}
        pure_inline = pure_prose + "\n```json\n" + json.dumps(stale_command) + "\n```\n"
        pure_contract = {"pure_design": True, "verification_commands": []}
        for name, filename, source, contract, expected_rule, source_type in (
            ("pure-prose", "spec.md", pure_prose, {"pure_design": True}, None, "spec"),
            ("pure-inline", "design-notes.md", pure_inline, {"pure_design": True, "verification_commands": []}, None, "spec"),
            ("pure-bad-inline", "design-notes.md", pure_prose + "\n```json\n{broken\n```\n", {"pure_design": True}, None, "spec"),
            ("empty-runtime", "design-notes.md", pure_inline, {"verification_commands": []}, "correctness.spec-verify-malformed", "spec"),
            ("contradictory-pure", "spec.md", pure_inline, {"pure_design": True, **stale_command}, "correctness.spec-verify-malformed", "spec"),
            ("pure-required-file", "spec.md", pure_inline, {"pure_design": True, "required_files": ["missing.md"]}, "correctness.required-file-missing", "spec"),
            ("generated-pure", ".devlyn/criteria.generated.md", pure_contract, None, None, "generated"),
            ("legacy-inline-pure", "design-notes.md", pure_contract, None, None, "spec"),
            ("generated-empty-section", ".devlyn/criteria.generated.md", pure_prose, None, "correctness.spec-verify-malformed", "generated"),
            ("generated-unmarked-empty", ".devlyn/criteria.generated.md", {"verification_commands": []}, None, "correctness.spec-verify-malformed", "generated"),
            ("generated-false-empty", ".devlyn/criteria.generated.md", {**pure_contract, "pure_design": False}, None, "correctness.spec-verify-malformed", "generated"),
            ("generated-missing-list", ".devlyn/criteria.generated.md", {"pure_design": True}, None, "correctness.spec-verify-malformed", "generated"),
            ("generated-nonboolean-pure", ".devlyn/criteria.generated.md", {**pure_contract, "pure_design": 1}, None, "correctness.spec-verify-malformed", "generated"),
            ("generated-contradictory-pure", ".devlyn/criteria.generated.md", {**stale_command, "pure_design": True}, None, "correctness.spec-verify-malformed", "generated"),
            ("generated-unsupported-field", ".devlyn/criteria.generated.md", {**pure_contract, "required_files": ["missing.md"]}, None, "correctness.spec-verify-malformed", "generated"),
        ):
            case_root = work / name
            case_root.mkdir()
            case_devlyn = case_root / ".devlyn"
            case_devlyn.mkdir()
            case_spec = case_root / filename
            if isinstance(source, dict):
                source = pure_prose + "\n```json\n" + json.dumps(source) + "\n```\n"
            case_spec.write_text(source, encoding="utf-8")
            if contract is not None:
                (case_root / "spec.expected.json").write_text(json.dumps(contract), encoding="utf-8")
            (case_devlyn / "spec-verify.json").write_text(json.dumps(stale_command), encoding="utf-8")
            pointer = "criteria" if source_type == "generated" else "spec"
            (case_devlyn / "pipeline.state.json").write_text(json.dumps({
                "source": {"type": source_type, pointer + "_path": str(case_spec),
                           pointer + "_sha256": hashlib.sha256(case_spec.read_bytes()).hexdigest()},
            }), encoding="utf-8")
            case_check = subprocess.run(
                [sys.executable, script_path, "--check", str(case_spec)],
                cwd=case_root, capture_output=True, text=True, encoding="utf-8",
            )
            if case_check.returncode != (2 if expected_rule == "correctness.spec-verify-malformed" else 0):
                print(f"{name}: authoring returned {case_check.returncode}: {case_check.stderr}", file=sys.stderr)
                return 1
            case_run = subprocess.run(
                [sys.executable, script_path], cwd=case_root,
                capture_output=True, text=True, encoding="utf-8",
            )
            if case_run.returncode != (1 if expected_rule else 0):
                print(f"{name}: contract execution returned {case_run.returncode}: {case_run.stderr}", file=sys.stderr)
                return 1
            case_findings = [
                loads_strict_json(line) for line in
                (case_devlyn / FINDINGS_NAME).read_text(encoding="utf-8").splitlines()
            ]
            if [finding["rule_id"] for finding in case_findings] != ([expected_rule] if expected_rule else []):
                print(f"{name}: unexpected contract findings: {case_findings}", file=sys.stderr)
                return 1
            case_results = case_devlyn / "spec-verify.results.json"
            if expected_rule == "correctness.spec-verify-malformed":
                if case_results.exists():
                    print(f"{name}: malformed contract reached command execution", file=sys.stderr)
                    return 1
            elif (
                loads_strict_json(case_results.read_text(encoding="utf-8"))
                != {"commands": [], "process_evidence": None}
                or (case_devlyn / "spec-verify.json").exists()
            ):
                print(f"{name}: pure-design contract ran or retained a stale command", file=sys.stderr)
                return 1

        generated_root = work / "generated-pure"
        generated_devlyn = generated_root / ".devlyn"
        for prestaged in (False, True):
            if prestaged:
                (generated_devlyn / "spec-verify.json").write_text(json.dumps(pure_contract), encoding="utf-8")
            bench_pure = subprocess.run(
                [sys.executable, script_path], cwd=generated_root,
                env=dict(os.environ, BENCH_WORKDIR=str(generated_root)),
                capture_output=True, text=True, encoding="utf-8",
            )
            if bench_pure.returncode != (1 if prestaged else 0):
                print(f"pure-design benchmark precedence changed: {bench_pure.stderr}", file=sys.stderr)
                return 1
            if prestaged and "verification_commands must contain at least one entry" not in bench_pure.stderr:
                print(f"prestaged empty benchmark did not fail command validation: {bench_pure.stderr}", file=sys.stderr)
                return 1

        generated_state_path = generated_devlyn / "pipeline.state.json"
        generated_state = loads_strict_json(generated_state_path.read_text(encoding="utf-8"))
        generated_state["risk_profile"] = {"risk_probes_enabled": True, "risk_probes_explicit": True}
        generated_state_path.write_text(json.dumps(generated_state), encoding="utf-8")
        missing_pure_probe = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"], cwd=generated_root,
            capture_output=True, text=True, encoding="utf-8",
        )
        if missing_pure_probe.returncode != 1 or "risk probes integrity failed" not in missing_pure_probe.stderr:
            print(f"pure-design contract bypassed required probes: {missing_pure_probe.stderr}", file=sys.stderr)
            return 1

        generated_source = generated_devlyn / "criteria.generated.md"
        generated_source.write_text(
            generated_source.read_text(encoding="utf-8") + "\n- probe must pass visible marker.\n",
            encoding="utf-8",
        )
        generated_state["source"]["criteria_sha256"] = hashlib.sha256(generated_source.read_bytes()).hexdigest()
        (generated_devlyn / "probes").mkdir()
        (generated_devlyn / "probes/P1.py").write_bytes(probe_script.read_bytes())
        (generated_devlyn / "risk-probes.jsonl").write_text(json.dumps(risk_probe_payload) + "\n", encoding="utf-8")
        generated_state["risk_probes_digest"], pure_probe_error = risk_probes_digest(generated_devlyn)
        if pure_probe_error:
            print(pure_probe_error, file=sys.stderr)
            return 1
        generated_state_path.write_text(json.dumps(generated_state), encoding="utf-8")
        valid_pure_probe = subprocess.run(
            [sys.executable, script_path, "--include-risk-probes"], cwd=generated_root,
            capture_output=True, text=True, encoding="utf-8",
        )
        if valid_pure_probe.returncode != 0:
            print(f"pure-design contract did not execute valid probe: {valid_pure_probe.stderr}", file=sys.stderr)
            return 1
        pure_probe_results = loads_strict_json((generated_devlyn / "spec-verify.results.json").read_text(encoding="utf-8"))
        if (
            len(pure_probe_results["commands"]) != 1
            or pure_probe_results["commands"][0]["evidence_id"] != "risk-probe-0001"
            or not pure_probe_results["commands"][0]["pass"]
            or pure_probe_results["process_evidence"] is None
            or (generated_devlyn / "spec-verify.json").exists()
        ):
            print("pure-design probe did not retain exactly one verified process result", file=sys.stderr)
            return 1

        malformed = work / "malformed-sibling"
        malformed.mkdir()
        malformed_devlyn = malformed / ".devlyn"
        malformed_devlyn.mkdir()
        malformed_spec = malformed / "spec.md"
        malformed_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n```json\n"
            "{\"verification_commands\":[{\"cmd\":\"printf inline-ok\"}]}\n"
            "```\n",
            encoding="utf-8",
        )
        (malformed / "spec.expected.json").write_text(json.dumps({"unknown": True}) + "\n", encoding="utf-8")
        (malformed_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(malformed_spec)}
        }), encoding="utf-8")
        malformed_run = subprocess.run(
            [sys.executable, script_path],
            cwd=malformed,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if malformed_run.returncode == 0:
            print("malformed sibling spec.expected.json fell back to inline carrier", file=sys.stderr)
            return 1

        bench_spec = work / "bench-spec.md"
        bench_spec.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- benchmark pre-staged wins.\n", encoding="utf-8")
        (work / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf wrong", "stdout_contains": ["wrong"]}
            ]
        }) + "\n", encoding="utf-8")
        (devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(bench_spec)}
        }), encoding="utf-8")
        (devlyn / "spec-verify.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf bench-staged", "stdout_contains": ["bench-staged"], "contract_refs": ["R1"]}
            ]
        }) + "\n", encoding="utf-8")
        bench_pre_staged = subprocess.run(
            [sys.executable, script_path],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if bench_pre_staged.returncode != 0:
            print(bench_pre_staged.stderr, file=sys.stderr)
            return 1
        staged_bench = loads_strict_json((devlyn / "spec-verify.json").read_text(encoding="utf-8"))
        if staged_bench.get("verification_commands", [{}])[0].get("cmd") != "printf bench-staged":
            print("benchmark pre-staged contract was overwritten", file=sys.stderr)
            return 1

        bench_marker = work / "bench-command-ran"
        bench_command = {"cmd": "printf bad > bench-command-ran; printf bad"}
        for carrier, diagnostic in (
            ({"verification_commands": [{**bench_command, "stdout_not_contians": ["bad"]}]}, "unknown key(s): stdout_not_contians"),
            ({"verification_commands": [{**bench_command, "contract_refs": [""]}]}, "contract_refs must be a list of non-empty strings"),
            ({"verification_commands": [bench_command], "required_files": ["missing.txt"]}, "unsupported inline key(s): required_files"),
            ({"verification_commands": [bench_command], "pure_design": True}, "requires an explicit empty verification_commands list"),
            ({"verification_commands": [], "pure_design": True}, "must contain at least one entry"),
        ):
            (devlyn / "spec-verify.json").write_text(json.dumps(carrier), encoding="utf-8")
            old_bench_results = (devlyn / "spec-verify.results.json").read_bytes()
            rejected_bench = subprocess.run(
                [sys.executable, script_path], cwd=work,
                env=env,
                capture_output=True, text=True, encoding="utf-8",
            )
            rejected_findings = [loads_strict_json(line) for line in
                                 (devlyn / FINDINGS_NAME).read_text(encoding="utf-8").splitlines()]
            if (
                rejected_bench.returncode != 1 or diagnostic not in rejected_bench.stderr
                or bench_marker.exists()
                or (devlyn / "spec-verify.results.json").read_bytes() != old_bench_results
                or len(rejected_findings) != 1
                or rejected_findings[0]["rule_id"] != "correctness.spec-verify-malformed"
                or rejected_findings[0]["severity"] != "CRITICAL"
                or rejected_findings[0]["phase"] != MECHANICAL_PHASE
            ):
                print(f"benchmark failed closed incorrectly for {carrier}: {rejected_bench.stderr}", file=sys.stderr)
                return 1

        verify_output = work / "verify-output"
        verify_output.mkdir()
        verify_devlyn = verify_output / ".devlyn"
        verify_devlyn.mkdir()
        verify_spec = verify_output / "spec.md"
        verify_spec.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- verify mechanical output.\n", encoding="utf-8")
        (verify_output / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [
                {"cmd": "printf wrong", "stdout_contains": ["expected"]}
            ]
        }) + "\n", encoding="utf-8")
        (verify_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(verify_spec)}
        }), encoding="utf-8")
        verify_output_run = subprocess.run(
            [sys.executable, script_path],
            cwd=verify_output,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if verify_output_run.returncode == 0:
            print("VERIFY output-mode failing command was accepted", file=sys.stderr)
            return 1
        verify_findings = (verify_devlyn / "verify-mechanical.findings.jsonl").read_text(encoding="utf-8")
        if '"phase": "verify"' not in verify_findings or "VERIFY-MECH-" not in verify_findings:
            print("VERIFY output-mode did not route findings to verify-mechanical", file=sys.stderr)
            return 1

        contract_root = work / "expected-contract"
        contract_root.mkdir()
        contract_devlyn = contract_root / ".devlyn"
        contract_devlyn.mkdir()
        (contract_root / "package.json").write_text(
            '{\n  "dependencies": {},\n  "devDependencies": {}\n}\n',
            encoding="utf-8",
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
            encoding="utf-8",
        ).strip()
        contract_spec = contract_root / "spec.md"
        contract_spec.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- expected contract checks.\n", encoding="utf-8")
        (contract_root / "app.js").write_text("try { work(); } catch { return null; }\n", encoding="utf-8")
        (contract_root / "forbidden.txt").write_text("forbidden\n", encoding="utf-8")
        (contract_root / "package.json").write_text(
            '{\n  "dependencies": {\n    "left-pad": "1.3.0"\n  },\n'
            '  "devDependencies": {}\n}\n',
            encoding="utf-8",
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
        }) + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=contract_root, check=True)
        (contract_devlyn / "untracked.baseline").write_text(EMPTY_BASELINE, encoding="utf-8")
        (contract_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(contract_spec)},
            "base_ref": {"sha": base_sha},
        }), encoding="utf-8")
        contract_run = subprocess.run(
            [sys.executable, script_path],
            cwd=contract_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if contract_run.returncode == 0:
            print("expected contract violations were accepted", file=sys.stderr)
            return 1
        findings_text = (contract_devlyn / FINDINGS_NAME).read_text(encoding="utf-8")
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
        }) + "\n", encoding="utf-8")
        weak = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if weak.returncode == 0:
            print("incomplete boundary_overlap evidence was accepted", file=sys.stderr)
            return 1

        error_root = work / "error-contract-risk-probe"
        error_root.mkdir()
        error_devlyn = error_root / ".devlyn"
        error_devlyn.mkdir()
        error_spec = error_root / "spec.md"
        error_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            "- Invalid input must print JSON error object `{ \"error\": \"bad_input\" }` to stderr and exit 2.\n"
            "- Malformed input must exit 2 and print stderr JSON with keys `code` and `detail`; values are implementation-defined.\n",
            encoding="utf-8",
        )
        (error_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(error_spec)}
        }), encoding="utf-8")
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
        }) + "\n", encoding="utf-8")
        weak_error_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
        }) + "\n", encoding="utf-8")
        weak_stdio_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if weak_stdio_contract.returncode == 0:
            print("stdout_stderr_contract without stream evidence was accepted", file=sys.stderr)
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7c",
            "derived_from": "Invalid input must print JSON error object `{ \"error\": \"bad_input\" }` to stderr and exit 2.",
            "cmd": "printf json-error-shape-contract-missing-exact",
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
                    "visible_text_names_exact_json_error_object",
                ],
            },
        }) + "\n", encoding="utf-8")
        missing_exact_error_object = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if missing_exact_error_object.returncode == 0:
            print(
                "shape_contract claiming visible exact error object without "
                "asserts_exact_error_object was accepted",
                file=sys.stderr,
            )
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7d",
            "derived_from": "Invalid input must print JSON error object `{ \"error\": \"bad_input\" }` to stderr and exit 2.",
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
                    "visible_text_names_exact_json_error_object",
                    "asserts_exact_error_object",
                ],
            },
        }) + "\n", encoding="utf-8")
        strong_json_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if strong_json_error_shape_contract.returncode != 0:
            print("JSON error object shape_contract with exact object evidence was rejected", file=sys.stderr)
            print(strong_json_error_shape_contract.stderr, file=sys.stderr)
            return 1

        (error_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P7e",
            "derived_from": (
                "Malformed input must exit 2 and print stderr JSON with keys `code` and `detail`; "
                "values are implementation-defined."
            ),
            "cmd": "printf error-exit-shape-contract",
            "exit_code": 2,
            "tags": ["error_contract", "shape_contract"],
            "tag_evidence": {
                "error_contract": [
                    "asserts_error_payload_or_stderr",
                    "asserts_nonzero_or_exit_2",
                ],
                "shape_contract": [
                    "uses_visible_input_key_names",
                    "asserts_visible_output_key_names",
                    "asserts_no_unexpected_output_keys",
                ],
            },
        }) + "\n", encoding="utf-8")
        error_exit_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if error_exit_shape_contract.returncode != 0:
            print("error-exit shape_contract without visible exact error object was rejected", file=sys.stderr)
            print(error_exit_shape_contract.stderr, file=sys.stderr)
            return 1

        http_error_root = work / "http-error-contract-risk-probe"
        http_error_root.mkdir()
        http_error_devlyn = http_error_root / ".devlyn"
        http_error_devlyn.mkdir()
        http_error_spec = http_error_root / "spec.md"
        http_error_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            "- An invalid query returns HTTP 400 with JSON error body `{ \"error\": \"invalid_query\", \"field\": \"per_page\" }`.\n",
            encoding="utf-8",
        )
        (http_error_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(http_error_spec)}
        }), encoding="utf-8")
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
        }) + "\n", encoding="utf-8")
        incomplete_http_error_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
                    "visible_text_names_exact_json_error_object",
                ],
            },
        }) + "\n", encoding="utf-8")
        weak_exact_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
                    "visible_text_names_exact_json_error_object",
                    "asserts_exact_error_object",
                ],
            },
        }) + "\n", encoding="utf-8")
        strong_exact_error_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=http_error_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            "- On success, output is one JSON object with keys `applied`, `rejected`, and `accounts`; "
            "`rejected` rows have keys `id` and `reason`.\n",
            encoding="utf-8",
        )
        (shape_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(shape_spec)}
        }), encoding="utf-8")
        (shape_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8e",
            "derived_from": (
                "On success, output is one JSON object with keys `applied`, `rejected`, and `accounts`; "
                "`rejected` rows have keys `id` and `reason`."
            ),
            "cmd": "printf weak-shape-contract",
            "exit_code": 0,
            "tags": ["shape_contract"],
            "tag_evidence": {},
        }) + "\n", encoding="utf-8")
        weak_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=shape_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if weak_shape_contract.returncode == 0:
            print("shape_contract without any evidence was accepted", file=sys.stderr)
            return 1

        (shape_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P8f",
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
        }) + "\n", encoding="utf-8")
        strong_shape_contract = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=shape_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if strong_shape_contract.returncode != 0:
            print("shape_contract with exact key evidence was rejected", file=sys.stderr)
            print(strong_shape_contract.stderr, file=sys.stderr)
            return 1

        # iter-0049 F3: required_risk_probe_requirements replaces the deleted
        # required_risk_probe_tags() English-keyword classifier. The spec
        # author declares required {tag, derived_from} obligations directly
        # in the verification carrier instead of the harness guessing from
        # prose -- this works identically for any human language.
        required_root = work / "required-risk-probe-requirements"
        required_root.mkdir()
        required_devlyn = required_root / ".devlyn"
        required_devlyn.mkdir()
        required_spec = required_root / "spec.md"
        required_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            "- A failed all-or-nothing operation must roll back tentative state "
            "so later orders can use the released stock.\n",
            encoding="utf-8",
        )
        (required_root / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contains": ["ok"]}],
            "required_risk_probe_requirements": [
                {
                    "tag": "rollback_state",
                    "derived_from": (
                        "A failed all-or-nothing operation must roll back "
                        "tentative state so later orders can use the released stock."
                    ),
                },
            ],
        }) + "\n", encoding="utf-8")
        (required_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(required_spec)}
        }), encoding="utf-8")
        (required_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P14",
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
        }) + "\n", encoding="utf-8")
        missing_declared_requirement = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=required_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if missing_declared_requirement.returncode == 0:
            print(
                "risk-probes.jsonl missing a declared required_risk_probe_requirements "
                "entry was accepted",
                file=sys.stderr,
            )
            return 1
        if (
            "missing required probe(s)" not in missing_declared_requirement.stderr
            or "rollback_state" not in missing_declared_requirement.stderr
        ):
            print("missing required_risk_probe_requirements coverage had the wrong error", file=sys.stderr)
            print(missing_declared_requirement.stderr, file=sys.stderr)
            return 1

        (required_devlyn / "risk-probes.jsonl").write_text(json.dumps({
            "id": "P15",
            "derived_from": (
                "A failed all-or-nothing operation must roll back tentative "
                "state so later orders can use the released stock."
            ),
            "cmd": "printf good-rollback",
            "exit_code": 0,
            "tags": ["rollback_state"],
            "tag_evidence": {
                "rollback_state": [
                    "failed_entity_tentative_state_absent",
                    "later_entity_uses_released_state",
                ],
            },
        }) + "\n", encoding="utf-8")
        covered_declared_requirement = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=required_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if covered_declared_requirement.returncode != 0:
            print(
                "risk-probes.jsonl covering a declared required_risk_probe_requirements "
                "entry was rejected",
                file=sys.stderr,
            )
            print(covered_declared_requirement.stderr, file=sys.stderr)
            return 1

        (required_root / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contains": ["ok"]}],
            "required_risk_probe_requirements": [
                {"tag": "not-a-real-tag", "derived_from": "irrelevant"},
            ],
        }) + "\n", encoding="utf-8")
        malformed_requirement_tag = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=required_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if malformed_requirement_tag.returncode == 0:
            print("required_risk_probe_requirements with an unknown tag was accepted", file=sys.stderr)
            return 1

        (required_root / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contains": ["ok"]}],
            "required_risk_probe_requirements": [
                {"tag": "rollback_state", "derived_from": "text not present in the spec"},
            ],
        }) + "\n", encoding="utf-8")
        malformed_requirement_derived_from = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=required_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if malformed_requirement_derived_from.returncode == 0:
            print(
                "required_risk_probe_requirements.derived_from not present in the "
                "spec was accepted",
                file=sys.stderr,
            )
            return 1

        atomic_batch_root = work / "atomic-batch-risk-probe"
        atomic_batch_root.mkdir()
        atomic_batch_devlyn = atomic_batch_root / ".devlyn"
        atomic_batch_devlyn.mkdir()
        atomic_batch_spec = atomic_batch_root / "spec.md"
        atomic_batch_spec.write_text(
            "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
            "- A POST with one valid + one invalid item returns `400`, AND a subsequent GET returns the same list as before the import.\n"
            "- A POST with all-valid items returns `201`, and the items appear in GET output in order with distinct ids.\n",
            encoding="utf-8",
        )
        (atomic_batch_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(atomic_batch_spec)}
        }), encoding="utf-8")
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
        }) + "\n", encoding="utf-8")
        incomplete_atomic_batch_probe = subprocess.run(
            [sys.executable, script_path, "--validate-risk-probes"],
            cwd=atomic_batch_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if incomplete_atomic_batch_probe.returncode == 0:
            print("atomic_batch_state without success-order evidence was accepted", file=sys.stderr)
            return 1

        # Literal diff paths must survive Git quoting, renames and both consumers.
        literal_root = work / "literal-paths"
        literal_root.mkdir()
        literal_devlyn = literal_root / ".devlyn"
        literal_devlyn.mkdir()
        (literal_root / ".gitignore").write_text(".devlyn/\n", encoding="utf-8")
        literal_names = ["plain.txt", "설정.txt", "my file.txt"]
        if os.name != "nt":
            literal_names += ["a\tb.txt", "a\nb.txt", " leading.txt", "trailing.txt ", 'quote".txt', "back\\slash.txt", "literal*.txt"]
        for name in literal_names + ["old name.txt"]:
            (literal_root / name).write_text("original\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=literal_root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=literal_root, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], cwd=literal_root, check=True)
        for name in literal_names:
            (literal_root / name).write_text("updated\n", encoding="utf-8")
        subprocess.run(["git", "mv", "old name.txt", "new name.txt"], cwd=literal_root, check=True)
        literal_names += ["old name.txt", "new name.txt"]
        literal_state = {"base_ref": {"sha": "HEAD"}}
        literal_expected = {"forbidden_files": literal_names}
        (literal_devlyn / "untracked.baseline").write_text(EMPTY_BASELINE, encoding="utf-8")
        (literal_devlyn / "plan.md").write_text(
            "<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n"
            + json.dumps({"authorized_surface": literal_names}) + "\n```\n", encoding="utf-8",
        )
        literal_patch = subprocess.check_output(
            ["git", "diff", "--binary", "--src-prefix=a/", "--dst-prefix=b/", "HEAD"], cwd=literal_root,
        )
        literal_external = literal_devlyn / "external-diff.patch"
        for external in (False, True):
            if external:
                literal_external.write_bytes(literal_patch)
            hits, _ = expected_contract_findings(literal_expected, None, literal_root, literal_devlyn, literal_state, 1)
            assert len(hits) == len(literal_names) and all(hit["rule_id"] == "scope.forbidden-file-touched" for hit in hits), hits
            scope_hits, _ = authorized_surface_findings(literal_root, literal_devlyn, literal_state, 1)
            assert not scope_hits, scope_hits
        edit = b"diff --git a/plain.txt b/plain.txt\n--- a/plain.txt\n+++ b/plain.txt\n@@ -1 +1 @@\n-original\n+updated\n"
        (literal_devlyn / "plan.md").write_text(
            '<!-- devlyn:authorized-surface -->\n## Files to touch\n\n```json\n{"authorized_surface":["untouched.txt"]}\n```\n', encoding="utf-8",
        )
        literal_external.write_bytes(edit)
        scope_hits, _ = authorized_surface_findings(literal_root, literal_devlyn, literal_state, 1)
        assert len(scope_hits) == 1 and scope_hits[0]["rule_id"] == "scope.out-of-scope-file", scope_hits
        literal_external.write_bytes(edit.replace(b"+updated", b"+updated  "))
        subprocess.run(["git", "config", "apply.whitespace", "error"], cwd=literal_root, check=True)
        try:
            names, error = changed_files(literal_root, literal_state, literal_devlyn)
            assert names == ["plain.txt"] and error is None, (names, error)
        finally:
            subprocess.run(["git", "config", "--unset", "apply.whitespace"], cwd=literal_root, check=True)
        for patch, paths in (
            (b"", []),
            (edit.replace(b"\n", b"\r\n"), ["plain.txt"]),
            (b"diff --git a/logo.png b/logo.png\nindex 1111111..2222222 100644\nBinary files a/logo.png and b/logo.png differ\n", ["logo.png"]),
            (b"diff --git a/script b/script\nold mode 100644\nnew mode 100755\n", ["script"]),
            (b"diff --git a/keep.py b/new.py\nsimilarity index 100%\ncopy from keep.py\ncopy to new.py\n", ["new.py", "keep.py"]),
        ):
            literal_external.write_bytes(patch)
            names, error = changed_files(literal_root, literal_state, literal_devlyn)
            assert names == paths and error is None, (names, error)
        for bad_patch in (
            b"not a patch\n", b"\n", edit[:-5],
            edit.replace(b"a/plain.txt", b"plain.txt").replace(b"b/plain.txt", b"plain.txt"),
            edit.replace(b"a/plain.txt", b"src/plain.txt").replace(b"b/plain.txt", b"src/plain.txt"),
            edit.replace(b"a/plain.txt", b"i/plain.txt").replace(b"b/plain.txt", b"w/plain.txt"),
        ):
            literal_external.write_bytes(bad_patch)
            hits, _ = expected_contract_findings(literal_expected, None, literal_root, literal_devlyn, literal_state, 1)
            assert len(hits) == 1 and hits[0]["rule_id"] == "correctness.expected-contract-unverifiable", hits
            scope_hits, _ = authorized_surface_findings(literal_root, literal_devlyn, literal_state, 1)
            assert len(scope_hits) == 1 and scope_hits[0]["file"] == ".devlyn/external-diff.patch", scope_hits
        literal_external.unlink()
        names, error = changed_files(literal_root, {"base_ref": {"sha": "missing-literal-ref"}}, literal_devlyn)
        assert not names and error, (names, error)
        assert subprocess.check_output(
            ["git", "diff", "--binary", "--src-prefix=a/", "--dst-prefix=b/", "HEAD"], cwd=literal_root,
        ) == literal_patch

        # iter-0046: PLAN-declared authorized_surface enforced by normal-mode VERIFY MECHANICAL.
        scope_root = work / "scope-gate"
        scope_root.mkdir()
        scope_devlyn = scope_root / ".devlyn"
        scope_devlyn.mkdir()
        (scope_root / "bin").mkdir()
        (scope_root / "lib").mkdir()
        (scope_root / "lib2").mkdir()
        (scope_root / "data").mkdir()
        (scope_root / "bin" / "cli.js").write_text("module.exports = {};\n", encoding="utf-8")
        (scope_root / "lib" / "keep.js").write_text("module.exports = {};\n", encoding="utf-8")
        (scope_root / "lib2" / "keep.js").write_text("module.exports = {};\n", encoding="utf-8")
        (scope_root / "data" / "usage-stats.json").write_text("{}\n", encoding="utf-8")
        scope_spec = scope_root / "spec.md"
        scope_spec.write_text("# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- scope gate checks.\n", encoding="utf-8")
        (scope_root / "spec.expected.json").write_text(json.dumps({
            "verification_commands": [{"cmd": "printf ok", "stdout_contains": ["ok"]}],
        }) + "\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=scope_root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=scope_root, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "base"],
            cwd=scope_root,
            check=True,
        )
        scope_base_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=scope_root, text=True,
            encoding="utf-8",
        ).strip()
        (scope_devlyn / "pipeline.state.json").write_text(json.dumps({
            "source": {"type": "spec", "spec_path": str(scope_spec)},
            "base_ref": {"sha": scope_base_sha},
        }), encoding="utf-8")
        (scope_root / "preexisting.local").write_text("pre-existing untracked\n", encoding="utf-8")
        # Writer parity: --write-untracked-baseline must share the reader's
        # parser — untracked DIRECTORIES expand to per-file paths and
        # special-character paths stay unquoted, or every pre-existing file
        # under an untracked directory false-positives as created-during-run.
        preexisting_dir = scope_root / "pre existing dir"
        preexisting_dir.mkdir()
        (preexisting_dir / "nested file.txt").write_text("scaffold\n", encoding="utf-8")
        write_baseline_run = subprocess.run(
            [sys.executable, script_path, "--write-untracked-baseline"],
            cwd=scope_root, capture_output=True, text=True,
            encoding="utf-8",
        )
        if write_baseline_run.returncode != 0:
            print("--write-untracked-baseline failed", file=sys.stderr)
            print(write_baseline_run.stderr, file=sys.stderr)
            return 1
        baseline_data = loads_strict_json((scope_devlyn / "untracked.baseline").read_text(encoding="utf-8"))
        if baseline_data != {"untracked": ["pre existing dir/nested file.txt", "preexisting.local"], "sparse_absences": []}:
            print("--write-untracked-baseline wrote wrong content", file=sys.stderr)
            print(repr(baseline_data), file=sys.stderr)
            return 1
        scope_findings_path = scope_devlyn / FINDINGS_NAME

        # Test 1: no .devlyn/plan.md at all -> fail-closed CRITICAL, not a no-op.
        (scope_root / "bin" / "cli.js").write_text("module.exports = { ok: true };\n", encoding="utf-8")
        missing_plan_run = subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        if missing_plan_run.returncode == 0:
            print("MECHANICAL accepted a run with no plan.md", file=sys.stderr)
            return 1
        if "scope.authorized-surface-malformed" not in scope_findings_path.read_text(encoding="utf-8"):
            print("missing plan.md did not emit scope.authorized-surface-malformed", file=sys.stderr)
            return 1

        # Test 2: plan.md present but no authorized_surface json block -> malformed.
        (scope_devlyn / "plan.md").write_text(
            "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## 1. Files to touch\n\n- `bin/cli.js` (edit): ship the fix.\n",
            encoding="utf-8",
        )
        malformed_block_run = subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        if malformed_block_run.returncode == 0:
            print("MECHANICAL accepted plan.md with no authorized_surface block", file=sys.stderr)
            return 1
        if "scope.authorized-surface-malformed" not in scope_findings_path.read_text(encoding="utf-8"):
            print("missing authorized_surface block did not emit scope.authorized-surface-malformed", file=sys.stderr)
            return 1
        malformed_print_surface = subprocess.run(
            [sys.executable, script_path, "--print-authorized-surface"],
            cwd=scope_root,
            capture_output=True,
        )
        if malformed_print_surface.returncode == 0:
            print("--print-authorized-surface accepted malformed plan.md", file=sys.stderr)
            return 1

        for entry in ("src/{a,b", "src/{a,}/**", "src/{a,{b,c}}", "src/{a,**}"):
            (scope_devlyn / "plan.md").write_text(
                "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## 1. Files to touch\n\n"
                "```json\n"
                + json.dumps({"authorized_surface": [entry]}) + "\n```\n",
                encoding="utf-8",
            )
            brace_mechanical = subprocess.run(
                [sys.executable, script_path], cwd=scope_root,
                capture_output=True, text=True,
                encoding="utf-8",
            )
            brace_print_surface = subprocess.run(
                [sys.executable, script_path, "--print-authorized-surface"], cwd=scope_root,
                capture_output=True, text=True,
                encoding="utf-8",
            )
            findings_text = scope_findings_path.read_text(encoding="utf-8")
            if (
                brace_mechanical.returncode == 0
                or brace_print_surface.returncode == 0
                or "scope.authorized-surface-malformed" not in findings_text
                or "supported form" not in findings_text
                or "supported form" not in brace_print_surface.stderr
                or "Traceback" in brace_mechanical.stderr + brace_print_surface.stderr
            ):
                print(f"malformed brace glob escaped the authorized-surface carrier: {entry}", file=sys.stderr)
                return 1

        # Test 3: valid surface, in-scope-only diff -> no scope findings, exit 0.
        (scope_devlyn / "plan.md").write_text(
            "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## 1. Files to touch\n\n"
            "- `bin/cli.js` (edit): ship the fix.\n\n"
            "```json\n"
            '{"authorized_surface": ["bin/cli.js", "lib/**", "authorized-but-uncreated.txt"]}\n'
            "```\n",
            encoding="utf-8",
        )
        (scope_root / "lib" / "new.js").write_text("module.exports = { created: true };\n", encoding="utf-8")
        print_surface = subprocess.run(
            [sys.executable, script_path, "--print-authorized-surface"],
            cwd=scope_root,
            capture_output=True,
        )
        if print_surface.returncode != 0:
            print("--print-authorized-surface rejected valid plan.md", file=sys.stderr)
            print(print_surface.stderr.decode("utf-8", "replace"), file=sys.stderr)
            return 1
        printed_paths = {
            path.decode("utf-8", "surrogateescape")
            for path in print_surface.stdout.split(b"\0") if path
        }
        if printed_paths != {"bin/cli.js", "lib/new.js"}:
            print("--print-authorized-surface printed the wrong paths", file=sys.stderr)
            print(repr(printed_paths), file=sys.stderr)
            return 1
        (scope_devlyn / "untracked.baseline").unlink()
        missing_baseline_run = subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        if missing_baseline_run.returncode == 0:
            print("MECHANICAL accepted missing .devlyn/untracked.baseline", file=sys.stderr)
            return 1
        if "untracked.baseline" not in scope_findings_path.read_text(encoding="utf-8"):
            print("missing untracked baseline did not emit a scope finding", file=sys.stderr)
            return 1
        rewrite_baseline_run = subprocess.run(
            [sys.executable, script_path, "--write-untracked-baseline"],
            cwd=scope_root, capture_output=True, text=True,
            encoding="utf-8",
        )
        if rewrite_baseline_run.returncode != 0:
            print("--write-untracked-baseline re-run failed", file=sys.stderr)
            return 1
        in_scope_run = subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        if in_scope_run.returncode != 0:
            print("in-scope-only diff was rejected", file=sys.stderr)
            print(in_scope_run.stderr, file=sys.stderr)
            return 1
        if "scope." in scope_findings_path.read_text(encoding="utf-8"):
            print("in-scope-only diff produced a spurious scope finding", file=sys.stderr)
            print(scope_findings_path.read_text(encoding="utf-8"), file=sys.stderr)
            return 1

        # Test 4: directory grant covers lib/**; an out-of-scope file must be
        # flagged, and the fix_hint must never suggest self-authorization.
        (scope_root / "lib" / "keep.js").write_text("module.exports = { touched: true };\n", encoding="utf-8")
        (scope_root / "data" / "usage-stats.json").write_text('{"leaked": true}\n', encoding="utf-8")
        (scope_root / "data" / "scratch.json").write_text('{"untracked": true}\n', encoding="utf-8")
        out_of_scope_run = subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        if out_of_scope_run.returncode == 0:
            print("out-of-scope file was accepted", file=sys.stderr)
            return 1
        out_of_scope_lines = scope_findings_path.read_text(encoding="utf-8").splitlines()
        out_of_scope_findings = [loads_strict_json(line) for line in out_of_scope_lines if line.strip()]
        flagged_files = {f["file"] for f in out_of_scope_findings if f.get("rule_id") == "scope.out-of-scope-file"}
        if "data/usage-stats.json" not in flagged_files:
            print("scope.out-of-scope-file did not name data/usage-stats.json", file=sys.stderr)
            return 1
        if "data/scratch.json" not in flagged_files:
            print("created-during-run unauthorized untracked file was not flagged", file=sys.stderr)
            return 1
        if "pre existing dir/nested file.txt" in flagged_files:
            print("pre-existing untracked directory file was flagged (writer/reader parity broken)", file=sys.stderr)
            return 1
        if "preexisting.local" in flagged_files:
            print("pre-existing untracked baseline file was flagged", file=sys.stderr)
            return 1
        if "lib/keep.js" in flagged_files:
            print("lib/** directory grant did not cover lib/keep.js", file=sys.stderr)
            return 1
        for f in out_of_scope_findings:
            if f.get("rule_id") != "scope.out-of-scope-file":
                continue
            hint = f.get("fix_hint", "")
            if "Remove" not in hint or "amend" in hint.lower():
                print("scope.out-of-scope-file fix_hint must say remove, never amend/self-authorize", file=sys.stderr)
                print(hint, file=sys.stderr)
                return 1

        # Test 5: lib2/keep.js must NOT be covered by the lib/** grant
        # (directory-prefix boundary, not a bare string-prefix match).
        (scope_root / "lib2" / "keep.js").write_text("module.exports = { touched: true };\n", encoding="utf-8")
        subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        boundary_flagged = {
            loads_strict_json(line)["file"]
            for line in scope_findings_path.read_text(encoding="utf-8").splitlines() if line.strip()
        }
        if "lib2/keep.js" not in boundary_flagged:
            print("lib/** incorrectly matched lib2/keep.js (directory-prefix boundary bug)", file=sys.stderr)
            return 1

        # Test 6: verify-only reviews a supplied diff with no PLAN, so it never
        # runs this gate, even with plan.md entirely absent.
        (scope_devlyn / "plan.md").unlink()
        scope_state = loads_strict_json((scope_devlyn / "pipeline.state.json").read_text(encoding="utf-8"))
        (scope_devlyn / "pipeline.state.json").write_text(
            json.dumps({**scope_state, "mode": "verify-only"}), encoding="utf-8",
        )
        subprocess.run(
            [sys.executable, script_path], cwd=scope_root,
            capture_output=True, text=True,
            encoding="utf-8",
        )
        verify_mech_findings = scope_findings_path.read_text(encoding="utf-8")
        if "scope." in verify_mech_findings:
            print("verify-only MECHANICAL ran the PLAN authorized_surface gate", file=sys.stderr)
            print(verify_mech_findings, file=sys.stderr)
            return 1
        (scope_devlyn / "pipeline.state.json").write_text(json.dumps(scope_state), encoding="utf-8")

        # Test 7: shape validation rejects absolute paths, `..`, duplicates, and malformed braces.
        for bad_surface in (
            {"authorized_surface": ["/etc/passwd"]},
            {"authorized_surface": ["bin/../etc/passwd"]},
            {"authorized_surface": ["bin/cli.js", "bin/cli.js"]},
            {"authorized_surface": []},
            {"authorized_surface": ["src/{a,b"]},
            {"authorized_surface": ["src/{a,}/**"]},
            {"authorized_surface": ["src/{a,{b,c}}"]},
            {"authorized_surface": ["src/{a,**}"]},
        ):
            err = validate_authorized_surface_shape(bad_surface)
            if err is None:
                print(f"validate_authorized_surface_shape accepted invalid input: {bad_surface}", file=sys.stderr)
                return 1

        # Test 8 (iter-0054): heading LEVEL after the sentinel is decoration,
        # same as heading text/language (iter-0049) -- any ATX level 1-6 must
        # be accepted, not just H2. Reproduces the real iter-0047 claude-small
        # compliance-cell defect (`# Files to touch` H1 was rejected as
        # malformed, burning a repair round).
        for heading_prefix in ("#", "###"):
            h_level_text = (
                f"<!-- devlyn:authorized-surface -->\n{heading_prefix} Files to touch\n\n"
                "- `bin/cli.js` (edit): ship the fix.\n\n"
                '```json\n{"authorized_surface": ["bin/cli.js"]}\n```\n'
            )
            found, block = extract_authorized_surface_block(h_level_text)
            if not found or block is None:
                print(f"extract_authorized_surface_block rejected a {heading_prefix!r} heading after the sentinel", file=sys.stderr)
                return 1
            if loads_strict_json(block) != {"authorized_surface": ["bin/cli.js"]}:
                print(f"extract_authorized_surface_block parsed the wrong json for a {heading_prefix!r} heading", file=sys.stderr)
                return 1

        for heading_prefix in ("#", "###"):
            h_level_verif_text = (
                f"<!-- devlyn:verification -->\n{heading_prefix} Verification\n\n"
                '```json\n{"verification_commands": []}\n```\n'
            )
            found, block = extract_verification_block(h_level_verif_text)
            if not found or block is None:
                print(f"extract_verification_block rejected a {heading_prefix!r} heading after the sentinel", file=sys.stderr)
                return 1

        # Mixed levels across sections (the exact iter-0047 shape once fixed:
        # PLAN's own `## Files to touch` H2 followed by a `# Risks` H1) must
        # still bound the authorized_surface section correctly -- not swallow
        # the rest of the document.
        mixed_levels_text = (
            "# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files to touch\n\n"
            "- `bin/cli.js` (edit): ship the fix.\n\n"
            '```json\n{"authorized_surface": ["bin/cli.js"]}\n```\n\n'
            "# Risks\n\n- none.\n"
        )
        found, block = extract_authorized_surface_block(mixed_levels_text)
        if not found or block is None or loads_strict_json(block) != {"authorized_surface": ["bin/cli.js"]}:
            print("extract_authorized_surface_block mis-parsed the mixed H2/H1 section-boundary shape", file=sys.stderr)
            return 1
    return seal_self_test(script_path) or defect_witness_self_test(script_path) or binding_self_test(script_path)


# A generic store CLI: each defect below is one class the four witness tags exist to catch.
WITNESS_APP = r"""import os, pathlib, sys
DEFECTS = set(DEFECT_LIST)

def put(store, name, data):
    store = pathlib.Path(store); lock = store / ".lock"; temp = store / (name + ".tmp")
    os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    try:
        flags = os.O_CREAT | os.O_WRONLY | (os.O_TRUNC if "preserve" in DEFECTS else os.O_EXCL)
        fd = os.open(temp, flags)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(data)
            if data == "FAIL":
                raise RuntimeError("injected failure after acquire")
            os.replace(temp, store / name)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    except BaseException:
        if "release" not in DEFECTS:
            lock.unlink()
        raise
    lock.unlink()

def same(first, second):
    if "alias" in DEFECTS:
        return os.path.normcase(os.path.abspath(first)) == os.path.normcase(os.path.abspath(second))
    return os.path.samefile(first, second)

def job(work):
    scratch = pathlib.Path(work) / "job.scratch"
    scratch.write_text("partial")
    try:
        raise SystemExit(3)
    finally:
        if "cleanup" not in DEFECTS:
            scratch.unlink(missing_ok=True)

command, *args = sys.argv[1:]
if command == "put":
    try:
        put(*args)
    except (OSError, RuntimeError) as exc:
        sys.exit(f"put failed: {exc}")
elif command == "same":
    print("SAME" if same(*args) else "DIFFERENT")
else:
    job(*args)
"""

# Each probe runs the app as a subprocess in its own scratch directory and reports every check,
# so one failing mechanism never hides another.
WITNESS_PROBES = {
    "P1": r"""import os, pathlib, shutil, subprocess, sys
scratch = pathlib.Path(".devlyn/probe-scratch/P1"); shutil.rmtree(scratch, ignore_errors=True)
first, second = scratch / "a", scratch / "b"; first.mkdir(parents=True); second.mkdir()
app = lambda *a: subprocess.run([sys.executable, "app.py", *map(str, a)], capture_output=True, text=True)
failed = app("put", first, "x", "FAIL")
release = failed.returncode != 0 and not (first / ".lock").exists() and app("put", first, "y", "ok").returncode == 0
(second / "z.tmp").write_bytes(b"keep")
collided = app("put", second, "z", "ok")
preserve = collided.returncode != 0 and (second / "z.tmp").read_bytes() == b"keep" and not (second / "z").exists()
print("release ok" if release else "release FAIL"); print("preserve ok" if preserve else "preserve FAIL")
shutil.rmtree(scratch, ignore_errors=True)
""",
    "P2": r"""import os, pathlib, shutil, subprocess, sys
scratch = pathlib.Path(".devlyn/probe-scratch/P2"); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
(scratch / "target.txt").write_text("t"); (scratch / "other.txt").write_text("o")
os.link(scratch / "target.txt", scratch / "alias.txt")
same = lambda a, b: subprocess.run([sys.executable, "app.py", "same", str(a), str(b)], capture_output=True, text=True).stdout.strip()
alias = same(scratch / "target.txt", scratch / "alias.txt") == "SAME" and same(scratch / "target.txt", scratch / "other.txt") == "DIFFERENT"
print("alias ok" if alias else "alias FAIL")
shutil.rmtree(scratch, ignore_errors=True)
""",
    "P3": r"""import pathlib, shutil, subprocess, sys
scratch = pathlib.Path(".devlyn/probe-scratch/P3"); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
code = subprocess.run([sys.executable, "app.py", "job", str(scratch)], capture_output=True, text=True).returncode
print("cleanup ok" if code == 3 and not (scratch / "job.scratch").exists() else "cleanup FAIL")
shutil.rmtree(scratch, ignore_errors=True)
""",
}


def binding_self_test(script_path: str) -> int:
    """MECHANICAL observes through Git's view with worker-writable modifiers neutralized.

    A changed contract, a change hidden by an index flag (before or during the commands, after the
    seal, or re-hidden by a hook), a newly concealed deletion and a path crossing between baseline
    categories never seal; a clean sparse checkout, a verify-only tree, a host append to a shared
    exclude file and a tool's self-ignoring cache do. The observer never writes the real index.
    """
    script_path = str(Path(script_path).resolve())
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    with tempfile.TemporaryDirectory() as tmp:
        outside = Path(tmp) / "spec"
        outside.mkdir()
        spec = outside / "spec.md"
        spec.write_bytes(b"# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n- prints ok\n")

        def contract(cmd: str, **extra) -> bytes:
            return json.dumps({"verification_commands": [{"cmd": cmd}], **extra}).encode()

        def repo(name: str, *, mode: str = "spec", cmd: str = "true", setup=None, **extra):
            root = Path(tmp) / name
            devlyn = root / ".devlyn"
            devlyn.mkdir(parents=True)

            def git(*args: str) -> str:
                return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                                      check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

            (root / ".gitignore").write_bytes(b".devlyn/\n")
            for name_ in ("a.txt", "b.txt", "sparse.txt"):
                (root / name_).write_bytes(f"{name_}\n".encode())
            git("init", "-q"); git("add", "-A"); git("commit", "-q", "-m", "base")
            (outside / "spec.expected.json").write_bytes(contract(cmd, **extra))
            if setup is not None:
                setup(root, git)
            (devlyn / "plan.md").write_bytes(b'<!-- devlyn:authorized-surface -->\n## Files\n```json\n{"authorized_surface": ["a.txt"]}\n```\n')
            if run_write_untracked_baseline(root, devlyn) != 0:
                raise AssertionError(f"{name}: baseline write failed")
            head = git("rev-parse", "HEAD")
            state = {"run_id": f"rs-{name}", "mode": mode,
                     "base_ref": {"sha": head},
                     "source": {"type": "spec", "spec_path": str(spec), "spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
                                "expected_sha256": hashlib.sha256(contract(cmd, **extra)).hexdigest()},
                     "untracked_baseline_sha256": hashlib.sha256((devlyn / "untracked.baseline").read_bytes()).hexdigest(),
                     "phases": {"verify": {"round": 0, "started_at": "2026-10-03T00:00:00.000Z", "completed_at": None,
                                           "pre_sha": head}}}
            (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
            return root, devlyn, git, state

        def mechanical(root: Path, env: dict | None = None) -> subprocess.CompletedProcess:
            (root / ".devlyn" / SEAL_NAME).unlink(missing_ok=True)
            shutil.rmtree(root / ".devlyn" / "process-evidence", ignore_errors=True)
            return subprocess.run([sys.executable, script_path], cwd=root, capture_output=True, text=True, encoding="utf-8",
                                  env=env)

        def sealed(root: Path, env: dict | None = None) -> tuple[int, str]:
            mechanical(root, env)
            proc = subprocess.run([sys.executable, script_path, "--seal"], cwd=root, capture_output=True, text=True,
                                  encoding="utf-8", env=env)
            findings = root / ".devlyn" / FINDINGS_NAME
            return proc.returncode, findings.read_text(encoding="utf-8") if findings.is_file() else ""

        def sparse(root: Path, git) -> None:
            git("update-index", "--skip-worktree", "sparse.txt")
            (root / "sparse.txt").unlink()

        # A clean sparse checkout seals, and observing writes nothing in the real Git directory.
        root, devlyn, git, state = repo("sparse-clean", setup=sparse)
        index = Path(git("rev-parse", "--absolute-git-dir")) / "index"
        before = (index.read_bytes(), index.stat().st_mtime_ns, sorted(p.name for p in index.parent.rglob("*")))
        rc, findings = sealed(root)
        check(rc == 0, f"a clean sparse checkout did not seal: {findings}")
        check((index.read_bytes(), index.stat().st_mtime_ns, sorted(p.name for p in index.parent.rglob("*"))) == before,
              "observing changed the real index or Git directory")

        # A split index is read, never written: index bytes and mtime, shared-index bytes and the
        # Git directory's file set stay as they were (Git's read refreshes only the shared index's mtime).
        root, devlyn, git, state = repo("split-index")
        git("update-index", "--split-index")
        gitdir = Path(git("rev-parse", "--absolute-git-dir"))
        def split_state():
            return ({p.name: p.read_bytes() for p in gitdir.glob("sharedindex.*")},
                    ((gitdir / "index").read_bytes(), (gitdir / "index").stat().st_mtime_ns),
                    sorted(str(p.relative_to(gitdir)) for p in gitdir.rglob("*")))
        before = split_state()
        rc, findings = sealed(root)
        check(rc == 0 and split_state() == before, f"observing a split index wrote Git metadata: {findings}")

        # A sparse absence a contract forbids changing is no change.
        root, devlyn, git, state = repo("sparse-forbidden", setup=sparse, forbidden_files=["sparse.txt"])
        rc, findings = sealed(root)
        check(rc == 0 and "forbidden" not in findings, f"a sparse absence counted as a forbidden change: {findings}")

        # A changed contract is never used.
        (outside / "spec.expected.json").write_bytes(contract("printf other"))
        changed = mechanical(root)
        check(changed.returncode != 0 and "source.expected_sha256 mismatch" in changed.stderr,
              f"a changed verification contract was used: {changed.stderr}")

        # Index flags never hide a change: skip-worktree, assume-unchanged, both, or a concealed deletion.
        for name, flag, mutate in (
                ("skip-worktree", ("--skip-worktree",), lambda r: (r / "a.txt").write_bytes(b"hidden\n")),
                ("assume-unchanged", ("--assume-unchanged",), lambda r: (r / "a.txt").write_bytes(b"hidden\n")),
                ("both-flags", ("--assume-unchanged", "--skip-worktree"), lambda r: (r / "a.txt").write_bytes(b"hidden\n")),
                ("concealed-deletion", ("--skip-worktree",), lambda r: (r / "a.txt").unlink())):
            root, devlyn, git, state = repo(name, setup=sparse)
            for option in flag:
                git("update-index", option, "a.txt")
            mutate(root)
            rc, findings = sealed(root)
            check(rc == 1 and "a.txt (hidden by index flag" in findings, f"{name}: a hidden change sealed: {findings}")

        # A hook the worker installs never runs inside the observer (post-index-change would re-flag the private index).
        if os.name != "nt":
            root, devlyn, git, state = repo("hook-reflag")
            git("update-index", "--assume-unchanged", "a.txt")
            (root / "a.txt").write_bytes(b"hidden\n")
            hook = Path(git("rev-parse", "--git-path", "hooks")) / "post-index-change"
            hook = hook if hook.is_absolute() else root / hook
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_text('#!/bin/sh\n[ -n "$DEVLYN_REFLAGGED" ] && exit 0\n'
                            "DEVLYN_REFLAGGED=1 git update-index --assume-unchanged a.txt\n", encoding="utf-8")
            hook.chmod(0o755)
            rc, findings = sealed(root)
            check(rc == 1 and "a.txt (hidden by index flag h)" in findings, f"a worker hook re-hid a change: {findings}")

        # Objects are read as stored: a replacement ref or a forged commit-graph entry for base or HEAD never
        # hides a committed change from the scope check or the seal.
        def replace(root: Path, git, commit: str, tree: str) -> None:
            git("replace", commit, git("commit-tree", tree, "-m", "forged"))

        def forge_graph(root: Path, git, commit: str, tree: str) -> None:
            """Overwrite `commit`'s root-tree OID in a freshly written commit-graph."""
            git("commit-graph", "write", "--reachable")
            graph = _git_path(root, "objects/info/commit-graph")
            data = bytearray(graph.read_bytes())
            chunks = {bytes(data[8 + 12 * i:12 + 12 * i]): int.from_bytes(data[12 + 12 * i:20 + 12 * i], "big")
                      for i in range(data[6])}
            count = int.from_bytes(data[chunks[b"OIDF"] + 1020:chunks[b"OIDF"] + 1024], "big")
            oids = [bytes(data[chunks[b"OIDL"] + 20 * i:chunks[b"OIDL"] + 20 * i + 20]) for i in range(count)]
            at = chunks[b"CDAT"] + 36 * oids.index(bytes.fromhex(commit))
            data[at:at + 20] = bytes.fromhex(tree)
            graph.chmod(0o644)
            graph.write_bytes(data)

        for forge in (replace, forge_graph):
            root, devlyn, git, state = repo(f"{forge.__name__}-base")
            (root / "b.txt").write_bytes(b"outside the surface\n")
            git("commit", "-q", "-am", "worker")
            forge(root, git, state["base_ref"]["sha"], git("rev-parse", "HEAD^{tree}"))
            (root / "a.txt").write_bytes(b"checkpoint\n")
            git("commit", "-q", "-am", "checkpoint")
            state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
            (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
            rc, findings = sealed(root)
            check("b.txt is outside PLAN's declared authorized_surface" in findings,
                  f"{forge.__name__}: a forged base hid a committed change: {findings}")
            root, devlyn, git, state = repo(f"{forge.__name__}-head")
            (root / "a.txt").write_bytes(b"BAD\n")
            git("commit", "-q", "-am", "checkpoint")
            (root / "a.txt").write_bytes(b"GOOD\n")
            git("add", "a.txt")
            forge(root, git, git("rev-parse", "HEAD"), git("write-tree"))
            state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
            (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
            rc, findings = sealed(root)
            check(rc == 1 and "tracked or staged changes: a.txt" in findings,
                  f"{forge.__name__}: a forged HEAD sealed bytes it does not hold: {findings}")

        def checkpoint(root: Path) -> subprocess.CompletedProcess:
            """The documented scoped checkpoint: printer piped into staging under pipefail, then the commit."""
            pipe = subprocess.run(["bash", "-o", "pipefail", "-c",
                                   f"{shlex.quote(sys.executable)} {shlex.quote(script_path)} --print-authorized-surface"
                                   " | git --literal-pathspecs add --pathspec-from-file=- --pathspec-file-nul"],
                                  cwd=root, capture_output=True, text=True, encoding="utf-8")
            return pipe if pipe.returncode else subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x"], cwd=root,
                capture_output=True, text=True, encoding="utf-8")

        def index_layout(data: bytes) -> tuple[dict[bytes, tuple[int, int]], int, dict[bytes, bytes]]:
            """A version 2 or 3 index: each entry's (start, end) by path, where entries end, its extensions."""
            entries, offset = {}, 12
            for _ in range(int.from_bytes(data[8:12], "big")):
                flags = int.from_bytes(data[offset + 60:offset + 62], "big")
                header, length = 62 + 2 * bool(flags & 0x4000), flags & 0xFFF
                end = offset + ((header + length + 8) & ~7)
                entries[data[offset + header:offset + header + length]] = (offset, end)
                offset = end
            end, extensions = offset, {}
            while offset < len(data) - 20:
                size = int.from_bytes(data[offset + 4:offset + 8], "big")
                extensions[data[offset:offset + 4]] = data[offset:offset + 8 + size]
                offset += 8 + size
            return entries, end, extensions

        def write_index(index: Path, body: bytes) -> None:
            index.write_bytes(body + hashlib.sha1(body).digest())

        # A forged cache-tree (the index's TREE) lets the documented checkpoint commit BAD while index and
        # worktree hold GOOD; the observer rewrites every stage-0 entry, so the seal sees the difference.
        def forge_tree(root: Path, git, path: str) -> None:
            """Stage BAD and write the cache-tree, then splice in a GOOD entry built in a copy, keeping TREE."""
            index, target = _git_path(root, "index"), root / path
            target.write_bytes(b"BAD\n")
            git("add", path)
            git("write-tree")
            donor = index.with_name("donor-index")
            shutil.copy2(index, donor)
            target.write_bytes(b"GOOD\n")
            past = target.stat().st_mtime - 60  # older than the index, so staging trusts the spliced entry
            os.utime(target, (past, past))
            subprocess.run(["git", "add", path], cwd=root, env={**os.environ, "GIT_INDEX_FILE": str(donor)}, check=True)
            data, spliced = index.read_bytes(), donor.read_bytes()
            (start, end), (donor_start, donor_end) = (index_layout(data)[0][path.encode()],
                                                      index_layout(spliced)[0][path.encode()])
            write_index(index, data[:start] + spliced[donor_start:donor_end] + data[end:-20])
            donor.unlink()

        def tracked_tree(root: Path, git) -> None:
            for name_ in ("src/a.py", "u/c.txt"):
                (root / name_).parent.mkdir()
                (root / name_).write_bytes(b"base\n")
            git("add", "-A")
            git("commit", "-q", "-m", "trees")

        for name, path in (("forged-root-tree", "a.txt"), ("forged-subtree", "src/a.py")):
            root, devlyn, git, state = repo(name, setup=tracked_tree)
            (devlyn / "plan.md").write_text("<!-- devlyn:authorized-surface -->\n## Files\n```json\n"
                                            + json.dumps({"authorized_surface": ["a.txt", "src/**"]}) + "\n```\n",
                                            encoding="utf-8")
            forge_tree(root, git, path)
            if path != "a.txt":
                (root / "a.txt").write_bytes(b"in-surface edit\n")
            committed = checkpoint(root)
            state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
            (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
            index = _git_path(root, "index")
            before = index.read_bytes()
            rc, findings = sealed(root)
            check(committed.returncode == 0 and git("show", f"HEAD:{path}") == "BAD" and rc == 1
                  and f"tracked or staged changes: {path}" in findings and index.read_bytes() == before,
                  f"{name}: a forged cache-tree sealed or observing wrote the index: {committed.stderr} {findings}")

        # Rewriting stage-0 entries reaches no index portion without one; a TREE forged from HEAD still never
        # seals an empty index or a conflict-only index (Git aborts on the mismatch, an explicit refusal), and
        # a subtree holding only unmerged entries is reported as it is.
        def forge_index(root: Path, git, entries: str) -> None:
            """Give the real index these index-info entries and a TREE extension forged from HEAD's tree."""
            index = _git_path(root, "index")
            scratch = index.with_name("forged-index")
            env = {**os.environ, "GIT_INDEX_FILE": str(scratch)}
            subprocess.run(["git", "read-tree", "--empty"], cwd=root, env=env, check=True)
            subprocess.run(["git", "update-index", "--index-info"], cwd=root, env=env, input=entries.encode(), check=True)
            git("read-tree", "HEAD")
            forged = scratch.read_bytes()
            write_index(index, forged[:index_layout(forged)[1]] + index_layout(index.read_bytes())[2][b"TREE"])
            scratch.unlink()

        def unmerged(git, path: str) -> str:
            return "".join(f"100644 {git('rev-parse', f'HEAD:{blob}')} {stage}\t{path}\n"
                           for stage, blob in ((1, "a.txt"), (2, "b.txt"), (3, "sparse.txt")))

        for name, entries, reported in (
                ("empty-index", lambda git: "", None),
                ("conflict-only-index", lambda git: unmerged(git, "a.txt"), None),
                ("unmerged-subtree", lambda git: "".join(f"100644 {git('rev-parse', f'HEAD:{tracked}')} 0\t{tracked}\n"
                                                         for tracked in (".gitignore", "a.txt", "b.txt", "sparse.txt",
                                                                         "src/a.py")) + unmerged(git, "u/c.txt"),
                 "tracked or staged changes: u/c.txt")):
            root, devlyn, git, state = repo(name, setup=tracked_tree)
            forge_index(root, git, entries(git))
            index = _git_path(root, "index")
            before = index.read_bytes()
            rc, findings = sealed(root)
            check(rc == 1 and "scope.unsealed-source" in findings and index.read_bytes() == before
                  and (reported is None or (reported in findings and "snapshot failed" not in findings)),
                  f"{name}: a forged TREE over an index portion without stage-0 entries sealed: {findings}")

        # Rewriting every stage-0 entry keeps what each one means: intent-to-add stays intent-to-add.
        root, devlyn, git, state = repo("intent-to-add")
        (root / "new.txt").write_bytes(b"new\n")
        git("add", "-N", "new.txt")
        index = _git_path(root, "index")
        before = index.read_bytes()
        entries, error = git_status_entries(root)
        check(error is None and (" A", "new.txt") in entries and index.read_bytes() == before,
              f"observing changed an intent-to-add entry: {entries} {error}")

        # Git skips a directory it cannot open and still exits 0; observing refuses instead, under any caller
        # locale, at baseline writing and at MECHANICAL and the seal, while a readable directory passes.
        if os.name != "nt" and os.geteuid() != 0:
            korean = {**os.environ, "LANG": "ko_KR.UTF-8", "LC_ALL": "ko_KR.UTF-8"}

            def user_dir(root: Path, git) -> None:
                (root / "residue").mkdir()
                (root / "residue" / "draft.txt").write_bytes(b"the user's\n")
            root, devlyn, git, state = repo("unlistable", setup=user_dir)
            for mode in (0o755, 0o000, 0o111):
                (root / "residue").chmod(mode)
                try:
                    baseline = subprocess.run([sys.executable, script_path, "--write-untracked-baseline"], cwd=root,
                                              env=korean, capture_output=True, text=True, encoding="utf-8")
                    rc, findings = sealed(root, korean)
                finally:
                    (root / "residue").chmod(0o755)
                if mode == 0o755:
                    check(baseline.returncode == 0 and rc == 0, f"a readable directory failed: {baseline.stderr} {findings}")
                else:
                    needle = "could not open directory 'residue/'"
                    check(baseline.returncode == 2 and needle in baseline.stderr and rc == 1 and needle in findings,
                          f"a mode {mode:o} directory dropped out of the observation: {baseline.stderr} {findings}")
        else:
            print("SKIP unlistable-directory bindings: permission fixtures need a non-root POSIX user", file=sys.stderr)

        # Sparse absences are part of the identity: materializing one after the snapshot, even with HEAD's
        # bytes, changes it; a dangling symlink at an authorized absence is present, so it is a change.
        root, devlyn, git, state = repo("sparse-materialized", setup=sparse)
        rc, findings = sealed(root)
        record = loads_strict_json((devlyn / SEAL_NAME).read_text(encoding="utf-8"))
        (root / "sparse.txt").write_bytes(b"sparse.txt\n")
        after = source_snapshot(root, devlyn, state)
        check(rc == 0 and after[1] != record["digest"] and "sparse absences" in snapshot_changes(record["snapshot"], after[0]),
              "materializing a sparse absence kept the sealed identity")
        root, devlyn, git, state = repo("sparse-dangling", setup=sparse)
        (root / "sparse.txt").symlink_to("missing-target")
        rc, findings = sealed(root)
        check(rc == 1 and "sparse.txt" in findings, f"a dangling symlink at a sparse absence sealed: {findings}")

        # A flag set and a file changed by a verification command, or after the seal, changes the identity.
        root, devlyn, git, state = repo("command-drift", cmd="git update-index --skip-worktree a.txt && printf drift > a.txt")
        rc, findings = sealed(root)
        check(rc == 1 and "source changed after the MECHANICAL snapshot" in findings,
              f"a change made during the commands sealed: {findings}")
        root, devlyn, git, state = repo("post-seal-drift")
        rc, findings = sealed(root)
        record = loads_strict_json((devlyn / SEAL_NAME).read_text(encoding="utf-8"))
        git("update-index", "--skip-worktree", "a.txt")
        (root / "a.txt").write_bytes(b"after the seal\n")
        check(rc == 0 and source_snapshot(root, devlyn, state)[1] != record["digest"],
              "a change after the seal kept the sealed identity")

        # A path never moves between baseline categories to hide a change.
        def untracked_then_hidden(root: Path, git) -> None:
            (root / "u.txt").write_bytes(b"the user's\n")
        root, devlyn, git, state = repo("category-untracked", setup=untracked_then_hidden)
        git("add", "u.txt"); git("commit", "-q", "-m", "adopt")
        state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        git("update-index", "--skip-worktree", "u.txt")
        (root / "u.txt").unlink()
        rc, findings = sealed(root)
        check(rc == 1 and "u.txt (hidden by index flag S)" in findings, f"an untracked baseline path hid a deletion: {findings}")
        root, devlyn, git, state = repo("category-sparse", setup=sparse)
        git("update-index", "--force-remove", "sparse.txt"); git("commit", "-q", "-m", "drop")
        state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        (root / "sparse.txt").write_bytes(b"new bytes\n")
        rc, findings = sealed(root)
        check(rc == 1 and "untracked files outside the PHASE 0 baseline: sparse.txt" in findings,
              f"a sparse absence exempted a new untracked file: {findings}")

        # Expected-contract readers observe like scope: a forbidden pattern hidden by a flag is still found.
        root, devlyn, git, state = repo("hidden-forbidden", forbidden_patterns=[
            {"pattern": "FORBIDDEN", "description": "hidden forbidden text", "severity": "disqualifier"}])
        git("update-index", "--assume-unchanged", "a.txt")
        (root / "a.txt").write_bytes(b"FORBIDDEN\n")
        mechanical(root)
        mech_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8") if (devlyn / FINDINGS_NAME).is_file() else ""
        check("correctness.forbidden-pattern" in mech_findings, f"a flag hid a forbidden pattern: {mech_findings}")

        # A baseline that is missing or malformed never seals, even when its bytes match the recorded digest.
        root, devlyn, git, state = repo("baseline-missing")
        (devlyn / "untracked.baseline").unlink()
        state["untracked_baseline_sha256"] = None
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        rc, findings = sealed(root)
        check(rc == 1 and "requires .devlyn/untracked.baseline" in findings, f"a missing baseline sealed: {findings}")
        root, devlyn, git, state = repo("baseline-malformed")
        (devlyn / "untracked.baseline").write_bytes(b"a.txt\n")
        state["untracked_baseline_sha256"] = hashlib.sha256(b"a.txt\n").hexdigest()
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        rc, findings = sealed(root)
        check(rc == 1 and "untracked.baseline" in findings and "differs from its bound digest" not in findings,
              f"a malformed baseline sealed: {findings}")

        # A real cone-mode sparse checkout with a sparse index seals without false changes.
        def cone(root: Path, git) -> None:
            for name_ in ("inside/y.txt", "outside/x.txt"):
                (root / name_).parent.mkdir(parents=True, exist_ok=True)
                (root / name_).write_bytes(b"cone\n")
            git("add", "-A"); git("commit", "-q", "-m", "dirs")
            git("sparse-checkout", "set", "--cone", "inside")
            git("config", "index.sparse", "true")
            git("sparse-checkout", "reapply")
        root, devlyn, git, state = repo("sparse-index", setup=cone)
        rc, findings = sealed(root)
        check(rc == 0 and not (root / "outside" / "x.txt").exists(), f"a sparse-index checkout did not seal: {findings}")

        # Committing a user's pre-run file through a glob surface is a scope finding, however it was staged; the
        # hint's command, run by a shell as printed, drops exactly that index entry (a bracket is no glob).
        def committed_user_file(root: Path, git) -> None:
            (root / "src").mkdir()
            (root / "src" / "i.txt").write_bytes(b"tracked\n")
            git("add", "src/i.txt"); git("commit", "-q", "-m", "tracked")
            (root / "src" / "[id].txt").write_bytes(b"the user's draft\n")
        root, devlyn, git, state = repo("adoption-committed", setup=committed_user_file)
        (devlyn / "plan.md").write_text("<!-- devlyn:authorized-surface -->\n## Files\n```json\n"
                                        + json.dumps({"authorized_surface": ["src/**"]}) + "\n```\n", encoding="utf-8")
        git("--literal-pathspecs", "add", "src/[id].txt"); git("commit", "-q", "-m", "swept in")
        state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        mechanical(root)
        mech_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8") if (devlyn / FINDINGS_NAME).is_file() else ""
        check("was the user's untracked file before the run" in mech_findings,
              f"a glob surface adopted a committed user file: {mech_findings}")
        hints = [loads_strict_json(line)["fix_hint"] for line in mech_findings.splitlines() if "src/[id].txt was the user's" in line]
        command = re.search(r"`([^`]+)`", hints[0]).group(1) if hints else "false"
        hinted = subprocess.run(["bash", "-c", command], cwd=root, capture_output=True, text=True, encoding="utf-8")
        check(hinted.returncode == 0 and git("ls-files", "src") == "src/i.txt",
              f"the hint's command did not drop exactly the user's index entry: {command} {hinted.stderr}")

        # A user's untracked file from before the run is staged only by an exact surface entry.
        def user_file(root: Path, git) -> None:
            (root / "src").mkdir()
            (root / "src" / "user.txt").write_bytes(b"the user's draft\n")
        root, devlyn, git, state = repo("adoption", setup=user_file)
        def print_surface(surface: list[str]) -> subprocess.CompletedProcess:
            (devlyn / "plan.md").write_text("<!-- devlyn:authorized-surface -->\n## Files\n```json\n"
                                            + json.dumps({"authorized_surface": surface}) + "\n```\n", encoding="utf-8")
            return subprocess.run([sys.executable, script_path, "--print-authorized-surface"], cwd=root, capture_output=True)
        def staged_paths(surface: list[str]) -> list[str]:
            return [path.decode() for path in print_surface(surface).stdout.split(b"\0") if path]
        check(staged_paths(["src/**"]) == [], "a glob surface adopted the user's untracked file")
        check(staged_paths(["src/user.txt"]) == ["src/user.txt"], "an exact surface entry did not adopt the user's file")

        # A user's nested repository (baseline `src/vendor/`, gitlink `src/vendor` once staged) follows the same rule.
        def nested_repo(root: Path, git) -> None:
            vendor = root / "src" / "vendor"
            vendor.mkdir(parents=True)
            for args in (("init", "-q"), ("commit", "-q", "--allow-empty", "-m", "vendor")):
                subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=vendor, check=True,
                               capture_output=True)
        root, devlyn, git, state = repo("adoption-nested", setup=nested_repo)
        check("src/vendor/" in loads_strict_json((devlyn / "untracked.baseline").read_text(encoding="utf-8"))["untracked"],
              "the baseline did not record the nested repository")
        check(staged_paths(["src/**"]) == [], "a glob surface staged the user's nested repository")
        (devlyn / "plan.md").write_text("<!-- devlyn:authorized-surface -->\n## Files\n```json\n"
                                        + json.dumps({"authorized_surface": ["src/**"]}) + "\n```\n", encoding="utf-8")
        git("add", "src/vendor"); git("commit", "-q", "-m", "gitlink")
        state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
        (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
        mechanical(root)
        mech_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8") if (devlyn / FINDINGS_NAME).is_file() else ""
        check("src/vendor was the user's untracked file before the run" in mech_findings,
              f"a glob surface adopted the user's nested repository: {mech_findings}")
        # An exact entry, with or without the slash, adopts it through printing, staging, commit and MECHANICAL.
        for index, spelling in enumerate(("src/vendor", "src/vendor/")):
            root, devlyn, git, state = repo(f"adoption-nested-exact-{index}", setup=nested_repo)
            check(staged_paths([spelling]) == ["src/vendor/"], f"exact entry {spelling!r} did not stage the nested repository")
            git("add", "src/vendor"); git("commit", "-q", "-m", "adopted")
            state["phases"]["verify"]["pre_sha"] = git("rev-parse", "HEAD")
            (devlyn / "pipeline.state.json").write_text(json.dumps(state), encoding="utf-8")
            mechanical(root)
            mech_findings = (devlyn / FINDINGS_NAME).read_text(encoding="utf-8") if (devlyn / FINDINGS_NAME).is_file() else ""
            check("src/vendor" not in mech_findings, f"exact entry {spelling!r} still flagged the adopted repository: {mech_findings}")

        # Adoption records only a nested repository's commit, so content outside it refuses before anything is
        # printed; the child's own ignore rules and index flags stay trusted.
        def nested_files(root: Path, git) -> None:
            vendor = root / "src" / "vendor"
            vendor.mkdir(parents=True)
            (vendor / ".gitignore").write_bytes(b"build/\n")
            (vendor / "lib.txt").write_bytes(b"v1\n")
            for args in (("init", "-q"), ("add", "-A"), ("commit", "-q", "-m", "vendor")):
                subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=vendor, check=True,
                               capture_output=True)
        for index, spelling in enumerate(("src/vendor", "src/vendor/")):
            root, devlyn, git, state = repo(f"adoption-dirty-{index}", setup=nested_files)
            vendor = root / "src" / "vendor"

            def child(*args: str) -> None:
                subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=vendor, check=True,
                               capture_output=True)

            def refuses(label: str, needle: bytes) -> None:
                proc = print_surface([spelling])
                check(proc.returncode == 2 and not proc.stdout and b"src/vendor" in proc.stderr and needle in proc.stderr,
                      f"{spelling!r}: {label} in the adopted repository was not refused: {proc.stdout!r} {proc.stderr!r}")
            (vendor / "build").mkdir()
            (vendor / "build" / "out.o").write_bytes(b"ignored\n")
            child("update-index", "--assume-unchanged", "lib.txt")
            (vendor / "lib.txt").write_bytes(b"hidden by the child's own flag\n")
            check(staged_paths([spelling]) == ["src/vendor/"], f"{spelling!r}: trusted child content refused adoption")
            child("update-index", "--no-assume-unchanged", "lib.txt")
            refuses("a tracked modification", b"BLOCKED:adopted-repository-dirty")
            child("checkout", "--", "lib.txt")
            (vendor / "new.txt").write_bytes(b"new\n")
            child("add", "new.txt")
            refuses("a staged file", b"BLOCKED:adopted-repository-dirty")
            child("rm", "-q", "--cached", "new.txt")
            refuses("an untracked file", b"BLOCKED:adopted-repository-dirty")
            (vendor / "new.txt").unlink()
            (vendor / ".git" / "index").write_bytes(b"not an index")
            refuses("a failing git status", b"cannot read the adopted nested repository src/vendor/: git status failed: fatal:")

        # The checkpoint commits the whole index, so while the index holds a user's pre-run file no exact entry
        # adopts, the printer refuses before printing anything; its quoted remedies keep the files, and the rerun
        # commits the authorized work.
        user_names = ("src/[id].txt", "src/my draft.txt", "src/it's.txt", "src/adopted.txt", "src/committed.txt", "notes.txt")

        def user_files(root: Path, git) -> None:
            (root / "src").mkdir()
            (root / "src" / "i.txt").write_bytes(b"tracked\n")
            git("add", "src/i.txt"); git("commit", "-q", "-m", "tracked")
            for name_ in user_names:
                (root / name_).write_bytes(f"the user's {name_}\n".encode())
        root, devlyn, git, state = repo("checkpoint-refusal", setup=user_files)
        (devlyn / "plan.md").write_text("<!-- devlyn:authorized-surface -->\n## Files\n```json\n"
                                        + json.dumps({"authorized_surface": ["a.txt", "src/**", "src/adopted.txt"]})
                                        + "\n```\n", encoding="utf-8")
        git("--literal-pathspecs", "add", "src/committed.txt"); git("commit", "-q", "-m", "worker's own commit")
        (root / "a.txt").write_bytes(b"authorized\n")
        git("--literal-pathspecs", "add", *[name_ for name_ in user_names if name_ != "src/committed.txt"])
        index = _git_path(root, "index")

        def tree_state() -> tuple:
            return git("rev-parse", "HEAD"), index.read_bytes(), [(root / name_).read_bytes() for name_ in user_names]
        before = tree_state()
        printer = subprocess.run([sys.executable, script_path, "--print-authorized-surface"], cwd=root,
                                 capture_output=True, text=True, encoding="utf-8")
        refused_checkpoint = checkpoint(root)
        offenders = sorted(set(user_names) - {"src/adopted.txt"})
        remedies = re.findall(r"`(git --literal-pathspecs rm -q --cached -- [^`]+)`", printer.stderr)
        check(printer.returncode == 2 and printer.stdout == "" and "src/adopted.txt" not in printer.stderr
              and remedies == [f"git --literal-pathspecs rm -q --cached -- {shlex.quote(name_)}" for name_ in offenders],
              f"the printer did not refuse every unadopted indexed user file: {printer.stdout!r} {printer.stderr}")
        check(refused_checkpoint.returncode != 0 and tree_state() == before,
              f"a refused checkpoint committed, staged or changed bytes: {refused_checkpoint.stderr}")
        for remedy in remedies:
            ran = subprocess.run(["bash", "-c", remedy], cwd=root, capture_output=True, text=True, encoding="utf-8")
            check(ran.returncode == 0, f"a printed remedy failed: {remedy} {ran.stderr}")
        rerun = checkpoint(root)
        tracked = git("ls-files", "-z").split("\0")
        check(rerun.returncode == 0 and git("show", "HEAD:a.txt") == "authorized" and "src/adopted.txt" in tracked
              and "src/i.txt" in tracked and not set(offenders) & set(tracked) and tree_state()[2] == before[2],
              f"remedy and rerun did not commit the authorized work and keep the user's files: {rerun.stderr} {tracked}")

        # Ignore policy is trusted environment (owner decision 2026-10-04): the host appending to a shared
        # exclude file, or a test tool writing a self-ignoring cache .gitignore, never blocks a correct run.
        root, devlyn, git, state = repo("host-append")
        exclude = _git_path(root, "info/exclude")
        exclude.parent.mkdir(parents=True, exist_ok=True)
        with exclude.open("a", encoding="utf-8") as handle:
            handle.write("\n**/.claude/settings.local.json\n**/.claude/settings.local.json\n")
        rc, findings = sealed(root)
        check(rc == 0, f"a host append to info/exclude blocked the seal: {findings}")
        root, devlyn, git, state = repo("tool-cache")
        (root / ".pytest_cache").mkdir()
        (root / ".pytest_cache" / ".gitignore").write_bytes(b"# Created by pytest automatically.\n*\n")
        (root / ".pytest_cache" / "CACHEDIR.TAG").write_bytes(b"Signature: 8a477f597d28d172789f06886806bc55\n")
        rc, findings = sealed(root)
        check(rc == 0, f"a test tool's self-ignoring cache blocked the seal: {findings}")

        # Verify-only reviews the untracked files bootstrap saw, a diff-added .gitignore included.
        def added_ignore(root: Path, git) -> None:
            (root / "pkg").mkdir()
            (root / "pkg" / ".gitignore").write_bytes(b"dist/\n")
        root, devlyn, git, state = repo("verify-only-ignore", mode="verify-only", setup=added_ignore)
        rc, findings = sealed(root)
        check(rc == 0, f"a verify-only tree with a .gitignore did not seal: {findings}")

        # A committed `ignore = all` hides a gitlink bump from plain Git only: the scope check, forbidden files,
        # the judges' diff and forbidden patterns all see the out-of-surface pointer.
        def ignored_submodule(root: Path, git) -> None:
            source = Path(tmp) / "submodule-source"
            source.mkdir()
            for args in (("init", "-q"), ("commit", "-q", "--allow-empty", "-m", "v1")):
                subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=source, check=True,
                               capture_output=True)
            git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(source), "sub")
            git("config", "-f", ".gitmodules", "submodule.sub.ignore", "all")
            git("add", ".gitmodules"); git("commit", "-q", "-m", "submodule")
        root, devlyn, git, state = repo("ignored-gitlink", setup=ignored_submodule)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "v2"],
                       cwd=root / "sub", check=True, capture_output=True)
        git("add", "sub"); git("commit", "-q", "-m", "bump")
        scope, _seq = authorized_surface_findings(root, devlyn, state, 1)
        forbidden, _seq = expected_contract_findings({"forbidden_files": ["sub"]}, None, root, devlyn, state, 1)
        diff_text, diff_error = diff_text_for_expected(root, devlyn, state)
        patterns, _seq = expected_contract_findings({"forbidden_patterns": [
            {"pattern": "Subproject commit", "description": "a gitlink bump", "severity": "disqualifier"}]},
            None, root, devlyn, state, 1)
        check([finding["file"] for finding in scope if finding["rule_id"] == "scope.out-of-scope-file"] == ["sub"]
              and [finding["rule_id"] for finding in forbidden] == ["scope.forbidden-file-touched"],
              f"an ignore = all gitlink bump escaped scope or forbidden_files: {scope} {forbidden}")
        check(diff_error is None and "Subproject commit" in diff_text
              and [finding["rule_id"] for finding in patterns] == ["correctness.forbidden-pattern"],
              f"an ignore = all gitlink bump escaped the judges' diff or forbidden_patterns: {diff_error} {patterns}")
    if failures:
        print("binding self-test failed:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print("PASS bindings: Git observes through neutralized flags, caches and hooks; a changed contract, hidden changes "
          "and category crossings never seal; sparse, verify-only, host-appended and tool-cache trees do; the real index is untouched")
    return 0


def defect_witness_self_test(script_path: str) -> int:
    """Each witness tag catches its defect class through MECHANICAL; the fixed build passes and seals."""
    import shutil

    script_path = str(Path(script_path).resolve())
    witness_markers = {
        "release_recovery": {"failure_injected_after_acquire_or_publish",
                             "asserts_resource_released_or_restored_after_failure",
                             "asserts_next_operation_succeeds_after_failure"},
        "physical_alias": {"same_target_reached_through_distinct_paths", "asserts_alias_resolved_to_one_physical_target"},
        "fixture_cleanup": {"exercises_failure_or_timeout_exit", "asserts_created_artifacts_absent"},
        "temp_file_preservation": {"preexisting_file_at_colliding_path", "exclusive_create_collision_exercised",
                                   "asserts_preexisting_bytes_unchanged"},
    }
    four = [{"tag": "fixture_cleanup", "derived_from": f"bullet {n}"} for n in range(4)]
    for shape_error in (validate_expected_shape({"verification_commands": [], "pure_design": True,
                                                 "required_risk_probe_requirements": four}),
                        validate_inline_shape({"verification_commands": [{"cmd": "true"}],
                                               "required_risk_probe_requirements": four})):
        if not shape_error or "at most 3 probes" not in shape_error:
            print(f"four distinct required bullets were accepted: {shape_error}", file=sys.stderr)
            return 1
    for tag, markers_required in witness_markers.items():
        if RISK_PROBE_REQUIRED_EVIDENCE.get(tag) != markers_required:
            print(f"{tag} marker contract drifted: {RISK_PROBE_REQUIRED_EVIDENCE.get(tag)}", file=sys.stderr)
            return 1
        for missing in sorted(markers_required):
            probe = {"id": "W", "derived_from": "prints ok", "cmd": "true", "tags": [tag],
                     "tag_evidence": {tag: sorted(RISK_PROBE_REQUIRED_EVIDENCE[tag] - {missing})}}
            error = validate_risk_probe(probe, 0, "- prints ok", Path.cwd())
            if not error or missing not in error:
                print(f"{tag} without {missing} was accepted: {error}", file=sys.stderr)
                return 1

    bullets = {
        "P1": "a failed or colliding write releases the store lock and leaves existing files untouched",
        "P2": "two paths that reach one file are reported as the same target",
        "P3": "a failing job removes the scratch files it created",
    }
    markers = {"P1": ["release ok", "preserve ok"], "P2": ["alias ok"], "P3": ["cleanup ok"]}
    tags = {"P1": ["release_recovery", "temp_file_preservation"], "P2": ["physical_alias"], "P3": ["fixture_cleanup"]}
    python = f'"{sys.executable}"'
    expected_failures = {(): {}, ("release",): {"P1": "release ok"}, ("preserve",): {"P1": "preserve ok"},
                         ("alias",): {"P2": "alias ok"}, ("cleanup",): {"P3": "cleanup ok"},
                         ("release", "preserve", "alias", "cleanup"): {"P1": "release ok", "P2": "alias ok", "P3": "cleanup ok"}}
    with tempfile.TemporaryDirectory() as tmp:
        for defects, failures in expected_failures.items():
            root = Path(tmp) / ("build-" + ("-".join(defects) or "fixed"))
            devlyn = root / ".devlyn"
            (devlyn / "probes").mkdir(parents=True)

            def git(*args: str) -> str:
                return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                                      check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

            block = {"verification_commands": [{"cmd": f"{python} app.py same app.py app.py", "stdout_contains": ["SAME"]}],
                     "required_risk_probe_requirements": [{"tag": tag, "derived_from": bullets[pid]}
                                                          for pid in bullets for tag in tags[pid]]}
            (root / "spec.md").write_bytes((
                "# Spec\n\n<!-- devlyn:verification -->\n## Verification\n\n"
                + "".join(f"- {bullet}\n" for bullet in bullets.values())
                + "\n```json\n" + json.dumps(block) + "\n```\n").encode("utf-8"))
            (root / ".gitignore").write_bytes(b".devlyn/\n")
            (root / "app.py").write_bytes(b"# placeholder\n")
            git("init", "-q"); git("add", "-A"); git("commit", "-q", "-m", "base")
            base = git("rev-parse", "HEAD")
            (root / "app.py").write_bytes(WITNESS_APP.replace("DEFECT_LIST", repr(sorted(defects))).encode("utf-8"))
            git("commit", "-q", "-am", "build")
            (devlyn / "plan.md").write_bytes(
                b'# PLAN\n\n<!-- devlyn:authorized-surface -->\n## Files\n\n```json\n{"authorized_surface": ["app.py"]}\n```\n')
            probes = []
            for pid, script in WITNESS_PROBES.items():
                (devlyn / "probes" / f"{pid}.py").write_bytes(script.encode("utf-8"))
                probes.append({"id": pid, "derived_from": bullets[pid], "cmd": f"{python} .devlyn/probes/{pid}.py",
                               "exit_code": 0, "stdout_contains": markers[pid], "tags": tags[pid],
                               "tag_evidence": {tag: sorted(RISK_PROBE_REQUIRED_EVIDENCE[tag]) for tag in tags[pid]}})
            (devlyn / "risk-probes.jsonl").write_bytes("".join(json.dumps(item) + "\n" for item in probes).encode("utf-8"))
            if run_write_untracked_baseline(root, devlyn) != 0:
                print("witness fixture: baseline write failed", file=sys.stderr)
                return 1
            digest, error = risk_probes_digest(devlyn)
            if error:
                print(f"witness fixture: probes do not digest: {error}", file=sys.stderr)
                return 1
            (devlyn / "pipeline.state.json").write_bytes(json.dumps({
                "run_id": "rs-witness", "mode": "spec", "base_ref": {"sha": base},
                "source": {"type": "spec", "spec_path": "spec.md",
                           "spec_sha256": hashlib.sha256((root / "spec.md").read_bytes()).hexdigest()},
                "risk_profile": {"high_risk": True, "reasons": ["declared-risk-probe-requirements"],
                                 "risk_probes_enabled": True, "risk_probes_explicit": False, "pair_default_enabled": True},
                "risk_probes_digest": digest,
                "untracked_baseline_sha256": hashlib.sha256((devlyn / "untracked.baseline").read_bytes()).hexdigest(),
                "phases": {"verify": {"round": 0, "started_at": "2026-10-03T00:00:00.000Z",
                                      "completed_at": None, "pre_sha": git("rev-parse", "HEAD")}},
            }).encode("utf-8"))
            run = subprocess.run([sys.executable, script_path, "--include-risk-probes"], cwd=root, timeout=300,
                                 capture_output=True, text=True, encoding="utf-8")
            findings = [loads_strict_json(line) for line in (devlyn / FINDINGS_NAME).read_text(encoding="utf-8").splitlines()
                        if line.strip()] if (devlyn / FINDINGS_NAME).is_file() else []
            probe_failures = [item for item in findings if item.get("rule_id") == "correctness.risk-probe-failed"]
            failed = {str(item.get("criterion_ref")).removeprefix("risk-probe:"): item for item in probe_failures}
            label = "+".join(defects) or "fixed"
            if set(failed) != set(failures) or any(item.get("severity") != "CRITICAL" for item in failed.values()) \
                    or any(failures[pid] not in failed[pid].get("message", "") for pid in failures) \
                    or (run.returncode == 0) != (not failures) or len(probe_failures) != len(failed):
                print(f"witness {label}: wrong probe outcome rc={run.returncode} failed={sorted(failed)} "
                      f"expected={sorted(failures)} findings={findings} stderr={run.stderr[-2000:]}", file=sys.stderr)
                return 1
            if not failures:
                sealed = subprocess.run([sys.executable, script_path, "--seal"], cwd=root, timeout=120,
                                        capture_output=True, text=True, encoding="utf-8")
                if sealed.returncode != 0:
                    print(f"witness fixed build did not seal: {sealed.stderr} {sealed.stdout}", file=sys.stderr)
                    return 1
            if (devlyn / "probe-scratch").exists() and any((devlyn / "probe-scratch").iterdir()):
                print(f"witness {label}: probe scratch left behind", file=sys.stderr)
                return 1
            shutil.rmtree(root, ignore_errors=True)
    print("PASS defect witnesses: each tag catches its defect through MECHANICAL; the fixed build passes and seals")
    return 0


def main() -> int:
    if "--help" in sys.argv[1:] or "-h" in sys.argv[1:]:
        print(
            "usage: spec-verify-check.py [-h | --help | --include-risk-probes | "
            "--validate-risk-probes | "
            "--print-authorized-surface | --write-untracked-baseline | --seal | "
            "--check <markdown-path> | --check-expected <json-path> | --self-test]"
        )
        return 0
    include_risk_probes = False
    validate_risk_probes_only = False
    print_authorized_surface = False
    write_untracked_baseline = False
    seal = False
    if "--seal" in sys.argv[1:]:
        seal = True
        sys.argv = [arg for arg in sys.argv if arg != "--seal"]
    if "--include-risk-probes" in sys.argv[1:]:
        include_risk_probes = True
        sys.argv = [arg for arg in sys.argv if arg != "--include-risk-probes"]
    if "--validate-risk-probes" in sys.argv[1:]:
        validate_risk_probes_only = True
        sys.argv = [arg for arg in sys.argv if arg != "--validate-risk-probes"]
    if "--print-authorized-surface" in sys.argv[1:]:
        print_authorized_surface = True
        sys.argv = [arg for arg in sys.argv if arg != "--print-authorized-surface"]
    if "--write-untracked-baseline" in sys.argv[1:]:
        write_untracked_baseline = True
        sys.argv = [arg for arg in sys.argv if arg != "--write-untracked-baseline"]

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

    if len(sys.argv) != 1:
        print(f"unknown argument(s): {' '.join(sys.argv[1:])}", file=sys.stderr)
        return 2

    bench_mode = "BENCH_WORKDIR" in os.environ
    work = Path(os.environ.get("BENCH_WORKDIR") or os.getcwd())
    devlyn_dir = work / ".devlyn"
    spec_path = devlyn_dir / "spec-verify.json"

    if seal:
        if include_risk_probes or validate_risk_probes_only or print_authorized_surface or write_untracked_baseline:
            print("usage: spec-verify-check.py --seal", file=sys.stderr)
            return 2
        return run_seal(work, devlyn_dir)

    if print_authorized_surface:
        if include_risk_probes or validate_risk_probes_only or write_untracked_baseline or len(sys.argv) != 1:
            print("usage: spec-verify-check.py --print-authorized-surface", file=sys.stderr)
            return 2
        return run_print_authorized_surface(work, devlyn_dir)

    if write_untracked_baseline:
        if include_risk_probes or validate_risk_probes_only or len(sys.argv) != 1:
            print("usage: spec-verify-check.py --write-untracked-baseline", file=sys.stderr)
            return 2
        return run_write_untracked_baseline(work, devlyn_dir)

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
    #      a json block, stage its commands or clear stale staging for an
    #      explicit pure-design contract.
    #   4. A generated source without a json block never gets here: the
    #      PHASE 0 freeze refuses it and its bytes are bound.
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
    if not validate_risk_probes_only:
        seal_error = write_open_seal(work, devlyn_dir, state)
        if seal_error:
            print(f"[spec-verify] {seal_error}", file=sys.stderr)
            return 2
        # Scope is judged on the snapshot tree, before any command can add artifacts;
        # `--seal` later requires the final tree to equal that snapshot.
        base_sha = ((state.get("base_ref") or {}).get("sha") or "").strip()
        scope_findings = (
            authorized_surface_findings(work, devlyn_dir, state, 1)[0]
            if state.get("mode") != "verify-only" and base_sha else []
        )
    else:
        scope_findings = []

    external_diff = devlyn_dir / "external-diff.patch"
    if external_diff.is_file() and state.get("mode") != "verify-only":
        error = (
            ".devlyn/external-diff.patch requires pipeline.state.json mode "
            f"'verify-only'; actual mode is {state.get('mode')!r}"
        )
        print(f"[spec-verify] carrier malformed: {error}", file=sys.stderr)
        write_malformed_finding(
            devlyn_dir,
            error,
            external_diff,
            fix_hint=(
                "Remove `.devlyn/external-diff.patch` for ordinary runs, or use "
                "`/devlyn-resolve --verify-only <diff-or-PR-ref> --spec <path>` only when "
                "intentionally verifying an external patch."
            ),
        )
        return 1
    integrity_error = source_integrity_error(src_type, state, source_md)
    if integrity_error:
        print(f"[spec-verify] carrier malformed: {integrity_error}", file=sys.stderr)
        write_malformed_finding(devlyn_dir, integrity_error, source_md)
        return 1
    expected_data: dict | None = None
    expected_path: Path | None = None
    contract_found = False
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
            contract_found, _staged, expected_error, expected_path, expected_data = stage_from_expected(
                source_md, devlyn_dir
            )
            if expected_error is not None:
                print(f"[spec-verify] carrier malformed: {expected_error}", file=sys.stderr)
                write_malformed_finding(devlyn_dir, expected_error, expected_path)
                return 1
            if contract_found:
                error = None
            else:
                contract_found, _staged, error = stage_from_source(source_md, devlyn_dir)
        else:
            contract_found, _staged, error = stage_from_source(source_md, devlyn_dir)
        if error is not None:
            print(f"[spec-verify] carrier malformed: {error}", file=sys.stderr)
            write_malformed_finding(devlyn_dir, error, source_md)
            return 1
        if not contract_found:
            # A handwritten spec with no block (the PHASE 0 freeze already refused a
            # generated source without one, and its bytes are rechecked above).
            if not bench_mode:
                # Drop any stale pre-staged file so a killed prior run cannot poison
                # this run's gate; the missing-contract rule below decides the rest.
                if spec_path.exists():
                    spec_path.unlink()
                    seal_error = refresh_open_seal(work, devlyn_dir, state)
                    if seal_error:
                        print(f"[spec-verify] {seal_error}", file=sys.stderr)
                        return 2
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
        seal_error = refresh_open_seal(work, devlyn_dir, state)
        if seal_error:
            print(f"[spec-verify] {seal_error}", file=sys.stderr)
            return 2
        return 0

    commands: list[dict] = []
    if not spec_path.exists():
        # A declared pure-design contract continues through probes/results, and so does
        # a VERIFY round without any contract; elsewhere a missing handwritten/benchmark
        # contract stays an opt-in no-op. The PHASE 0 freeze refuses a generated source without one.
        if not contract_found and open_verify_span(state) is None:
            return 0
    else:
        try:
            spec = loads_strict_json(spec_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as e:
            print(f"[spec-verify] error: cannot parse {spec_path}: {e}", file=sys.stderr)
            return 2

        # Pre-staged commands need the strict carrier vocabulary too: unknown
        # expectations were silently ignored. Keep the nonempty shape gate;
        # a benchmark's staged empty list must not become a pure-design pass.
        shape_err = validate_shape(spec) or validate_inline_shape(spec)
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
        integrity_error = risk_probe_integrity_error(state, devlyn_dir)
        if integrity_error:
            print(f"[spec-verify] risk probes integrity failed: {integrity_error}", file=sys.stderr)
            write_risk_probe_integrity_finding(devlyn_dir, integrity_error)
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
    seal_error = refresh_open_seal(work, devlyn_dir, state)
    if seal_error:
        print(f"[spec-verify] {seal_error}", file=sys.stderr)
        return 2
    results_path = devlyn_dir / "spec-verify.results.json"
    findings_path = devlyn_dir / FINDINGS_NAME

    results: list[dict] = []
    findings: list[dict] = []
    finding_seq = 1
    runner = process_evidence_module()
    evidence_phase, evidence_run_id, evidence_round, manifest_relative = (
        mechanical_evidence_identity(state, runner)
    )
    manifest_path = work / manifest_relative
    obligations: list[dict] = []
    capability_denials: list[dict] = []
    evidence_error: str | None = None

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
        timeout_sec = verification_timeout_sec(vc)
        obligation = mechanical_obligation(vc, idx, evidence_phase)
        obligations.append(obligation)
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

        try:
            entry = capture_mechanical_command(
                runner, work, manifest_path, evidence_run_id, evidence_phase,
                evidence_round, obligation,
            )
            stdout = (work / entry["stdout"]["path"]).read_bytes()
            stderr = (work / entry["stderr"]["path"]).read_bytes()
        except (runner.EvidenceError, OSError, UnicodeError, ValueError) as exc:
            evidence_error = str(exc)
            results.append({
                "index": idx,
                "cmd": cmd,
                "pass": False,
                "reason": "process_evidence_invalid",
            })
            findings.append({
                "id": f"{FINDING_PREFIX}-{finding_seq:04d}",
                "rule_id": "invariant.process-evidence-invalid",
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": f"MECHANICAL process evidence is invalid: {exc}.",
                "file": manifest_relative,
                "line": 1,
                "phase": MECHANICAL_PHASE,
                "criterion_ref": "process-evidence://mechanical",
                "fix_hint": (
                    "Preserve the existing manifest and raw streams, then fix the "
                    "runner identity or evidence mutation before rerunning this phase."
                ),
                "blocking": True,
                "status": "open",
            })
            finding_seq += 1
            break

        outcome = entry["outcome"]
        classification = entry["classification"]
        combined = stdout + stderr
        actual_exit = outcome["exit_code"] if outcome["kind"] == "exit" else None
        ok_exit = outcome["kind"] == "exit" and actual_exit == expected_exit
        ok_contains = all(s.encode("utf-8") in combined for s in stdout_contains)
        ok_not = not any(s.encode("utf-8") in combined for s in stdout_not_contains)
        passed = entry["expectation_met"]
        if classification["kind"] == "capability_denied":
            reason = "capability_denied"
            capability_denials.append({
                "cmd": cmd,
                "operation": classification["operation"],
                "evidence_id": entry["id"],
            })
        elif passed:
            reason = None
        elif outcome["kind"] == "timeout":
            reason = "timeout"
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
            "actual_exit": actual_exit,
            "timeout_sec": timeout_sec,
            "stdout_contains": stdout_contains,
            "stdout_not_contains": stdout_not_contains,
            "pass": passed,
            "reason": reason,
            "evidence_id": entry["id"],
            "outcome": outcome,
            "classification": classification,
            "stdout": entry["stdout"],
            "stderr": entry["stderr"],
        })

        if classification["kind"] == "capability_denied" or passed:
            continue

        if outcome["kind"] == "timeout":
            findings.append({
                "id": f"{FINDING_PREFIX}-{finding_seq:04d}",
                "rule_id": "correctness.verification-timeout",
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": (
                    f"Verification command #{idx + 1} timed out after {timeout_sec}s "
                    f"(timeout_sec={timeout_sec}, maximum 600)."
                ),
                "file": file_ref,
                "line": 1,
                "phase": MECHANICAL_PHASE,
                "criterion_ref": criterion_ref,
                "fix_hint": (
                    f"Command `{cmd}` exceeded its {timeout_sec}s timeout_sec budget. "
                    "Increase timeout_sec up to 600 when the verification legitimately "
                    "needs more time, or fix a hang in the implementation."
                ),
                "blocking": True,
                "status": "open",
            })
            finding_seq += 1
            continue

        if not ok_exit:
            actual = (
                str(actual_exit)
                if outcome["kind"] == "exit"
                else f"{outcome['kind']}"
                + (f" signal {outcome['signal']}" if outcome["kind"] == "signal" else "")
            )
            msg = (
                f"Verification command #{idx + 1} failed: expected exit "
                f"{expected_exit}, got {actual}."
            )
        elif not ok_contains:
            missing = [s for s in stdout_contains if s.encode("utf-8") not in combined]
            msg = (
                f"Verification command #{idx + 1} failed: expected "
                f"output to contain {missing!r}."
            )
        else:
            forbidden = [s for s in stdout_not_contains if s.encode("utf-8") in combined]
            msg = (
                f"Verification command #{idx + 1} failed: output "
                f"contained forbidden literal(s) {forbidden!r}."
            )

        rule_id = (
            "correctness.risk-probe-failed"
            if is_risk_probe
            else "correctness.spec-literal-mismatch"
        )
        fix_hint = (
            f"Inspect `{manifest_relative}` entry `{entry['id']}` and its sealed raw "
            f"streams. Update implementation so `{cmd}` matches the contract "
            f"(exit_code={expected_exit}, contains={stdout_contains}, "
            f"not_contains={stdout_not_contains})."
        )
        if is_risk_probe:
            fix_hint = (
                f"Risk probe `{vc.get('id')}` derived from {vc.get('derived_from')!r} "
                f"failed. Inspect `{manifest_relative}` entry `{entry['id']}` and "
                "update the implementation to satisfy the visible verification bullet."
            )

        findings.append({
            "id": f"{FINDING_PREFIX}-{finding_seq:04d}",
            "rule_id": rule_id,
            "level": "error",
            "severity": "CRITICAL",
            "confidence": 1.0,
            "message": msg,
            "file": file_ref,
            "line": 1,
            "phase": MECHANICAL_PHASE,
            "criterion_ref": criterion_ref,
            "fix_hint": fix_hint,
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

    for finding in scope_findings:
        findings.append({**finding, "id": f"{FINDING_PREFIX}-{finding_seq:04d}"})
        finding_seq += 1

    evidence_carrier = None
    if evidence_error is None and obligations:
        try:
            evidence_carrier = runner.validate_manifest(
                work, manifest_relative, evidence_run_id, evidence_phase,
                evidence_round, obligations, require_expectations=False,
            )
            results = runner.bound_carrier_summary_commands(work, evidence_carrier)
        except (runner.EvidenceError, OSError, UnicodeError, ValueError) as exc:
            evidence_error = str(exc)
            findings.append({
                "id": f"{FINDING_PREFIX}-{finding_seq:04d}",
                "rule_id": "invariant.process-evidence-invalid",
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": f"MECHANICAL process evidence validation failed: {exc}.",
                "file": manifest_relative,
                "line": 1,
                "phase": MECHANICAL_PHASE,
                "criterion_ref": "process-evidence://mechanical",
                "fix_hint": (
                    "Preserve the manifest and raw streams, then correct the "
                    "missing, altered, or path-escaping evidence before rerunning."
                ),
                "blocking": True,
                "status": "open",
            })
            finding_seq += 1

    results_path.write_text(json.dumps({
        "commands": results,
        "process_evidence": evidence_carrier,
    }, indent=2) + "\n", encoding="utf-8")

    # Findings (jsonl). The owner appends its language/browser gate findings
    # after this run, and `--seal` appends a refusal; truncate here since this
    # run opens the round's MECHANICAL findings.
    with findings_path.open("w", encoding="utf-8") as fh:
        for f in findings:
            fh.write(json.dumps(f) + "\n")

    failed = [r for r in results if r.get("pass") is False]
    blocking_findings = [f for f in findings if f.get("severity") in {"CRITICAL", "HIGH"}]
    if capability_denials:
        denial = capability_denials[0]
        print(
            "BLOCKED:build-env-underprovisioned: "
            f"{denial['operation']} denied for `{denial['cmd']}`; "
            f"evidence {manifest_relative}#{denial['evidence_id']}",
            file=sys.stderr,
        )
        return 2
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
    runpy.run_path(str(Path(__file__).with_name("platform-support.py")))["configure_utf8"]()
    sys.exit(main())
