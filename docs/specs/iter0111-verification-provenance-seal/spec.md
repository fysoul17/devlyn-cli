---
id: iter0111-verification-provenance-seal
title: Verification provenance and capability seal
kind: feature
status: planned
complexity: large
---

# Verification provenance and capability seal

## Context

Task-level `/devlyn:resolve` execution is mechanically strong, but three observed runs
proved that a correct implementation can still receive an untrustworthy terminal result:
run-owned files can remain flat and be mistaken for a later run, a fresh read-only JUDGE
can rerun commands that MECHANICAL already passed and interpret sandbox denial as product
failure, and a primary `verify-judge.stdout` capture can be attributed to a skipped
pair-JUDGE. Red-first output also remained outside the authenticated state and archive,
so the independent JUDGE could not inspect evidence explicitly required by the spec.

The invariant for this feature is: every terminal verdict source is identified before
merge, every process claim is backed by run-scoped raw bytes plus a state-bound digest,
and environment capability failure cannot masquerade as a code finding.

## Observed evidence

1. Run `rs-20260826T142817Z-467b7b339412` recorded
   `pair_trigger.skipped_reason: user_no_pair` but merged `pair_judge: PASS` because the
   generic primary capture `verify-judge.stdout` matched the OTHER-judge filename scan.
2. Run `rs-20260826T152645Z-a4e3247fa09c` initially turned the same generic primary
   capture into a CRITICAL pair emission failure; only an orchestrator-time rename to
   `codex-judge.stdout` restored `pair_judge: null`.
3. The same run's read-only JUDGE reran `bash scripts/lint-skills.sh`; temporary-file
   creation was denied even though VERIFY MECHANICAL had just passed the exact command.
4. The same run finished `NEEDS_WORK` because the red-first traceback existed in
   `.devlyn/red-first-archive-null.stderr` but was neither an authenticated JUDGE input
   nor part of the deterministic archive set. It was moved after archive by hand.
5. RT-21 BUILD_GATE and VERIFY attempts under a restricted Codex sandbox produced
   loopback, PTY, and Cargo lock denials; unchanged controls passed when executed in the
   capable parent environment.
6. After deterministic archive, many prior phase prompts, task contexts, stdout/stderr,
   and retry streams remained flat under `.devlyn`, making later attribution ambiguous.

## Subtractive-first decision

1. MECHANICAL remains the sole executor of declared verification commands. Remove
   duplicate literal-command execution from JUDGE prompts instead of adding error
   heuristics to reinterpret their failures.
2. Reuse the existing archive ownership list for pre-run stale-artifact handling; do not
   create a second independently maintained cleanup list.
3. Extend the existing expected/state/archive contracts with one process-evidence shape;
   do not add a user-facing mode, fallback verdict, or optional execution branch.
4. A denied required capability is an explicit environment blocker, never a downgraded
   product finding and never a reason to silently retry with a different command.

## Requirements

- [ ] R1 — Run ownership is deterministic. Before a new bootstrap writes state, every
  flat artifact owned by the previous run is archived under the run id authenticated by
  its existing state. Missing or malformed ownership state with owned artifacts blocks
  bootstrap without deleting or re-attributing bytes. The archive ownership contract
  covers canonical prompt, task-context, stdout, stderr, event stream, retry, and
  process-evidence artifacts produced by every phase. Machine configuration, archived
  runs, and unrelated `.devlyn` data remain untouched.
- [ ] R2 — Declared process evidence is first-class. The expected-contract schema can
  declare IMPLEMENT evidence obligations such as a red-first command. A shared runner
  records the exact argv/command, exit status or signal, raw stdout, raw stderr, and byte
  digests in a run-scoped location. IMPLEMENT completion validates every declared item
  and binds its manifest digest into `pipeline.state.json` before the implementation
  checkpoint can be accepted. Missing, altered, path-escaping, duplicate-id, or
  expectation-mismatched evidence blocks the transition.
- [ ] R3 — VERIFY MECHANICAL records equivalent structured evidence for every literal
  `verification_commands` and risk probe it executes after CLEANUP. The manifest and raw
  bytes are immutable inputs to the fresh JUDGE and are rehashed before merge. JUDGE does
  not rerun literal verification, lint, test, build, or risk-probe commands. For complex
  interaction behavior, executable coverage must be declared in the expected contract
  or derived risk probes and therefore run by MECHANICAL; JUDGE performs independent
  clause-level and code-order review against the sealed results.
- [ ] R4 — BUILD_GATE capability is explicit. A Codex BUILD_GATE must execute required
  commands with CI-equivalent capabilities provided by the parent route. If that route
  cannot provide a required filesystem, subprocess, loopback, PTY, or network capability,
  the phase records `BLOCKED:build-env-underprovisioned` with the denied operation and
  command. It must not emit a product correctness finding, rerun a substitute command,
  or treat a restricted failure as test output. Raw capability evidence is preserved by
  the same process-evidence contract.
- [ ] R5 — Judge-source attribution is fail-closed. The primary capture has one canonical
  engine-qualified name and is never scanned as OTHER-judge evidence. When
  `pair_trigger.eligible` is false or `skipped_reason` is set, `pair_judge` remains JSON
  null. A genuine OTHER-judge carrier in that state is a CRITICAL state/capture
  contradiction; a generic primary filename cannot promote, block, or fabricate the
  pair verdict. Eligible pair state still requires canonical OTHER output and retains all
  existing timeout/emission checks.
- [ ] R6 — Archive consumes the state-declared process-evidence paths dynamically, checks
  their recorded digests, preserves their relative layout, and moves them with the run.
  No required evidence may remain flat after archive. An unsafe path, missing file, hash
  mismatch, or destination collision blocks archive visibly and never changes the
  already-derived product verdict.
- [ ] R7 — Self-tests reproduce the exact observed shapes: `user_no_pair` plus generic
  primary PASS and NEEDS_WORK captures; skipped pair plus a genuine OTHER carrier;
  restricted-command denial after a green MECHANICAL result; red-first evidence missing,
  altered, and archived; interrupted-run flat artifacts; and successful preservation of
  machine config and unrelated `.devlyn` data.
- [ ] R8 — Canonical `config/skills` and tracked `.agents` mirrors remain byte-identical,
  the full skill lint passes, and no dependency or user-facing flag is added.

## Out of Scope

- Project-mode plan decomposition and `queue add-plan`.
- Topological queue seeding, project-level closure, or reopen policy from iteration 0070.
- Changes to `devlynd` RT-21 completion classification.
- Benchmark claims about one model outperforming another.
- Automatic privilege escalation or approval bypass when the parent route lacks the
  required capability.

<!-- devlyn:verification -->
## Verification

- `python3 config/skills/_shared/resolve-bootstrap.py --self-test` proves prior-run
  artifact ownership is archived or blocked without deletion/re-attribution.
- `python3 config/skills/_shared/process-evidence.py --self-test` proves command capture,
  digest binding, path safety, mutation detection, and capability-blocker classification.
- `python3 config/skills/_shared/spec-verify-check.py --self-test` proves declared command
  and risk-probe evidence is emitted by MECHANICAL.
- `python3 config/skills/_shared/state-phase-write.py --self-test` proves IMPLEMENT
  evidence is validated and state-bound before checkpoint acceptance.
- `python3 config/skills/_shared/verify-merge-findings.py --self-test` proves primary/pair
  source attribution and skipped-pair null semantics.
- `python3 config/skills/_shared/archive_run.py --self-test` proves dynamic evidence and
  the complete run-owned artifact surface are archived without stale leftovers.
- `diff -qr config/skills .agents/skills` proves tracked mirror parity.
- `bash scripts/lint-skills.sh` runs the repository-wide contract suite.
- `git diff --check` rejects whitespace corruption.

```json
{
  "verification_commands": [
    {
      "cmd": "python3 config/skills/_shared/resolve-bootstrap.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 config/skills/_shared/process-evidence.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 config/skills/_shared/spec-verify-check.py --self-test",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 config/skills/_shared/state-phase-write.py --self-test",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "python3 config/skills/_shared/verify-merge-findings.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "python3 config/skills/_shared/archive_run.py --self-test",
      "exit_code": 0,
      "timeout_sec": 180
    },
    {
      "cmd": "diff -qr config/skills .agents/skills",
      "exit_code": 0
    },
    {
      "cmd": "bash scripts/lint-skills.sh",
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ]
}
```

## Assumptions made

- The parent orchestrator knows whether its BUILD_GATE route is CI-capable; the nested
  worker must not silently widen permissions itself.
- Existing archived runs remain readable; the new evidence fields are additive and null
  for legacy states.
- Raw process stdout/stderr may be empty but must still have explicit files and digests.
