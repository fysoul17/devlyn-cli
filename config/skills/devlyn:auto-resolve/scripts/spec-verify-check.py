#!/usr/bin/env python3
"""Spec literal verification gate (iter-0019.6).

Reads `.devlyn/spec-verify.json` (a normalized list of verification commands
staged by the harness — for benchmark fixtures, run-fixture.sh; for real
user runs, /devlyn:ideate is intended to generate this from the spec's
"## Verification" section in a future iter). For each command, runs it in
the work-dir, captures combined stdout+stderr, and asserts exit_code
matches + stdout_contains all required literals + stdout_not_contains none
of the forbidden literals. Mirrors run-fixture.sh's post-run verifier
semantics exactly so BUILD_GATE pre-emptively sees the same failures the
post-run verifier would surface.

Why: iter-0018.5's prompt-only contract enforcement was empirically dead
(F9 verify=0.4 across all engines in iter-0019). Same lesson as iter-0008
prompt-only engine constraint. Mechanical bash-gate enforcement is the
only working pattern. Codex R5 (2026-04-28) verdict: helper script is
non-optional — prose-only repeats iter-0018.5's failure mode.

Outputs:
- `.devlyn/spec-verify.results.json` — full per-command evidence (stdout
  tail, exit, reason, expected vs actual). Always written.
- `.devlyn/spec-verify-findings.jsonl` — canonical findings per
  `references/findings-schema.md`, ONE finding per failed command. Phase
  is "build_gate" (this script runs as part of the BUILD_GATE phase).
  CRITICAL severity / blocking=true / status=open. The orchestrator
  merges these into `.devlyn/build_gate.findings.jsonl` so the existing
  fix-loop machinery picks them up unchanged.

Exit codes:
- 0: spec-verify.json absent (no-op for real-user runs without staging)
  OR all commands passed.
- 1: at least one command failed (findings emitted, BUILD_GATE verdict
  should be FAIL).
- 2: invocation error (unreadable spec-verify.json, missing work_dir, etc.)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    work = Path(os.environ.get("BENCH_WORKDIR") or os.getcwd())
    devlyn_dir = work / ".devlyn"
    spec_path = devlyn_dir / "spec-verify.json"

    if not spec_path.exists():
        # Real-user runs without staging: silent no-op. Real-user contract
        # generation is a future iter (iter-0019.7+ or /devlyn:ideate
        # extension), not iter-0019.6 scope.
        return 0

    try:
        spec = json.loads(spec_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[spec-verify] error: cannot parse {spec_path}: {e}", file=sys.stderr)
        return 2

    commands = spec.get("verification_commands", [])
    if not isinstance(commands, list):
        print(f"[spec-verify] error: verification_commands must be a list", file=sys.stderr)
        return 2

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
