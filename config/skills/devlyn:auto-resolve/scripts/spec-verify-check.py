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
  (2) Otherwise, source markdown extract — read `pipeline.state.json:
      source.{spec_path | criteria_path}` and extract a `## Verification`
      ```json``` block. If present, overwrite `.devlyn/spec-verify.json`.
      This is the real-user carrier path; a pre-existing file from a
      killed prior run is stale and must not be trusted in real-user mode.
  (3) If no json block in source AND source.type=="generated": emit
      CRITICAL `correctness.spec-verify-malformed` so the fix-loop reruns
      BUILD.
  (4) If no json block in source AND source.type=="spec": benchmark mode
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
  generated `## Verification` ```json``` block parses + matches the schema.
- Exits 0 if the block is well-formed (or absent — ideate's check applies
  to both new specs that include the block and pre-carrier handwritten
  specs that omit it; absence is not failure here, only malformed JSON or
  shape error is). Exits 2 on malformed json or shape error.

Why: iter-0018.5's prompt-only contract enforcement was empirically dead
(F9 verify=0.4 across all engines in iter-0019). Same lesson as iter-0008
prompt-only engine constraint. Mechanical bash-gate enforcement is the
only working pattern. iter-0019.8 extends iter-0019.6 from benchmark-only
to real-user runs by extracting the contract from the spec/criteria
markdown directly — closes NORTH-STAR test #14.

Exit codes:
- 0: silent no-op (no source carrier, real-user mode) OR --check passed
  OR all commands passed.
- 1: at least one command failed OR carrier malformed (generated source
  required carrier, generated source had invalid json/shape, or pre-staged
  file failed shape validation). All paths emit a CRITICAL finding to
  `.devlyn/spec-verify-findings.jsonl`.
- 2: invocation error (unreadable spec-verify.json, missing markdown in
  --check mode, etc.)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


VERIFICATION_SECTION_RE = re.compile(
    r'(?ms)^##[ \t]+Verification\b[^\n]*\n(.*?)(?=^##[ \t]+|\Z)'
)
JSON_FENCE_RE = re.compile(r'(?ms)^```json[ \t]*\n(.*?)\n```[ \t]*$')


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


def read_source(work: Path, devlyn_dir: Path) -> tuple[str | None, Path | None]:
    """Return (source_type, markdown_path) from .devlyn/pipeline.state.json,
    or (None, None) if state is absent/unreadable. The markdown path is
    resolved against `work` when relative.
    """
    state_path = devlyn_dir / "pipeline.state.json"
    if not state_path.is_file():
        return (None, None)
    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
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
        data = json.loads(block)
    except json.JSONDecodeError as e:
        return (False, f"`## Verification` ```json``` block in {md} has invalid JSON: {e}")
    err = validate_shape(data)
    if err:
        return (False, f"`## Verification` ```json``` block in {md}: {err}")
    normalized = {"verification_commands": data["verification_commands"]}
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    (devlyn_dir / "spec-verify.json").write_text(json.dumps(normalized, indent=2) + "\n")
    return (True, None)


def write_malformed_finding(devlyn_dir: Path, error: str, source_path: Path | None) -> None:
    """Emit a single CRITICAL finding for a malformed verification carrier."""
    devlyn_dir.mkdir(parents=True, exist_ok=True)
    findings_path = devlyn_dir / "spec-verify-findings.jsonl"
    file_ref = str(source_path) if source_path else ".devlyn/pipeline.state.json"
    finding = {
        "id": "BGATE-0001",
        "rule_id": "correctness.spec-verify-malformed",
        "level": "error",
        "severity": "CRITICAL",
        "confidence": 1.0,
        "message": f"Verification contract carrier is malformed: {error}",
        "file": file_ref,
        "line": 1,
        "phase": "build_gate",
        "criterion_ref": "spec-verify://carrier",
        "fix_hint": (
            "Fix the `## Verification` ```json``` block: a JSON object with "
            "a non-empty `verification_commands` array of "
            "{cmd, exit_code?, stdout_contains?, stdout_not_contains?} "
            "entries. See references/build-gate.md § 'Spec literal check'."
        ),
        "blocking": True,
        "status": "open",
    }
    with findings_path.open("w") as fh:
        fh.write(json.dumps(finding) + "\n")


def run_check_mode(md_path: Path) -> int:
    """`--check <markdown>` — validate the verification carrier without
    running any commands. Used by /devlyn:ideate after item-spec write.

    Exit 0: section absent OR section present and well-formed.
    Exit 2: section present but malformed (so ideate can re-prompt).
    """
    if not md_path.is_file():
        print(f"[spec-verify --check] error: {md_path} not found", file=sys.stderr)
        return 2
    block = extract_verification_block(md_path.read_text())
    if block is None:
        # Section absent or no json block — opt-in nature preserved for
        # ideate (a spec without machine verification is still valid; it
        # just won't activate the BUILD_GATE gate).
        return 0
    try:
        data = json.loads(block)
    except json.JSONDecodeError as e:
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
    return 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--check":
        if len(sys.argv) != 3:
            print("usage: spec-verify-check.py --check <markdown-path>", file=sys.stderr)
            return 2
        return run_check_mode(Path(sys.argv[2]))

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
    #   2. Otherwise, attempt source-extract from
    #      `pipeline.state.json:source.{spec_path | criteria_path}`. If it has
    #      a json block, overwrite .devlyn/spec-verify.json with it. This is
    #      the real-user carrier path; in real-user mode a pre-existing file
    #      is stale (from a killed prior run) and must NOT be trusted.
    #   3. If source has no json block AND source.type=="generated":
    #      CRITICAL spec-verify-malformed — generated criteria must ship a
    #      verifiable contract per phase-1-build.md <output_contract>.
    #   4. If source has no json block AND source.type=="spec":
    #      - Real-user mode: silent no-op (preserves iter-0019.6 backward
    #        compat for handwritten specs without the carrier). Drop any
    #        stale pre-staged file.
    #      - Benchmark mode: fall through to the pre-staged-trust branch
    #        (covers pre-iter-0019.9 fixtures whose spec.md has prose-only
    #        Verification — run-fixture.sh staged the contract regardless).
    pre_staged = spec_path.is_file()  # captured BEFORE any potential write
    trust_bench_staged = bench_mode and pre_staged
    src_type, source_md = read_source(work, devlyn_dir)
    if source_md is not None and not trust_bench_staged:
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
                    "array). PHASE 1 BUILD generated criteria without one."
                )
                print(f"[spec-verify] {msg}", file=sys.stderr)
                write_malformed_finding(devlyn_dir, msg, source_md)
                return 1
            # source.type=="spec", no block in spec markdown.
            if not bench_mode:
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

    if not spec_path.exists():
        # No source markdown carrier AND no pre-staged file. Silent no-op
        # for benchmark misconfigurations (no fixture to gate against) and
        # for real-user runs without spec/criteria. Generated source case
        # is handled above.
        return 0

    try:
        spec = json.loads(spec_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
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
    commands = spec["verification_commands"]

    devlyn_dir.mkdir(parents=True, exist_ok=True)
    results_path = devlyn_dir / "spec-verify.results.json"
    findings_path = devlyn_dir / "spec-verify-findings.jsonl"

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

                findings.append({
                    "id": f"BGATE-{finding_seq:04d}",
                    "rule_id": "correctness.spec-literal-mismatch",
                    "level": "error",
                    "severity": "CRITICAL",
                    "confidence": 1.0,
                    "message": msg,
                    "file": ".devlyn/spec-verify.json",
                    "line": 1,
                    "phase": "build_gate",
                    "criterion_ref": f"spec-verify://verification_commands/{idx}",
                    "fix_hint": fix_hint,
                    "blocking": True,
                    "status": "open",
                })
                finding_seq += 1

        except subprocess.TimeoutExpired:
            results.append({"index": idx, "cmd": cmd, "pass": False,
                            "reason": "timeout"})
            findings.append({
                "id": f"BGATE-{finding_seq:04d}",
                "rule_id": "correctness.spec-literal-mismatch",
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": (
                    f"Verification command #{idx + 1} timed out after 60s."
                ),
                "file": ".devlyn/spec-verify.json",
                "line": 1,
                "phase": "build_gate",
                "criterion_ref": f"spec-verify://verification_commands/{idx}",
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
            findings.append({
                "id": f"BGATE-{finding_seq:04d}",
                "rule_id": "correctness.spec-literal-mismatch",
                "level": "error",
                "severity": "CRITICAL",
                "confidence": 1.0,
                "message": (
                    f"Verification command #{idx + 1} raised "
                    f"{e.__class__.__name__}: {e}."
                ),
                "file": ".devlyn/spec-verify.json",
                "line": 1,
                "phase": "build_gate",
                "criterion_ref": f"spec-verify://verification_commands/{idx}",
                "fix_hint": (
                    f"Command `{cmd}` could not be executed. Check the work-dir "
                    f"state and any environment setup the command requires."
                ),
                "blocking": True,
                "status": "open",
            })
            finding_seq += 1

    results_path.write_text(json.dumps({"commands": results}, indent=2) + "\n")

    # Append findings (jsonl). BUILD_GATE merge step concatenates this onto
    # build_gate.findings.jsonl; never overwrite the orchestrator's own gate
    # findings. Truncate this file each run since it is a per-round artifact.
    with findings_path.open("w") as fh:
        for f in findings:
            fh.write(json.dumps(f) + "\n")

    failed = [r for r in results if r.get("pass") is False]
    if failed:
        print(
            f"[spec-verify] {len(failed)}/{len(results)} command(s) failed; "
            f"{len(findings)} CRITICAL finding(s) written to {findings_path}",
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
