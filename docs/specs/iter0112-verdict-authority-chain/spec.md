---
id: iter0112-verdict-authority-chain
title: Verdict authority chain and execution envelope seal
kind: bugfix
status: planned
complexity: large
---

# Verdict authority chain and execution envelope seal

## Context

Iteration 0111 preserved command bytes and their digests, but production audit found
that the terminal verdict was still derived from mutable summary files. A failed
state-bound manifest could therefore coexist with BUILD_GATE `PASS`, and VERIFY could
be laundered to `PASS` by emptying mutable findings/results without changing any sealed
raw byte. The same audit observed duplicate JSON keys accepted by state/result/archive
readers, a PLAN output widened after completion, a handwritten `model:` file accepted
as engine attestation, a nested Codex route widened with the bypass flag after a
capability denial, and BUILD_GATE worker sessions left flat after archive.

The invariant is: a run verdict is a deterministic projection of immutable plan,
dispatch, and process-evidence receipts; no mutable derivative may contradict or erase
that authority chain.

## Observed counterexamples

1. A BUILD_GATE manifest entry with `expectation_met: false` was accepted by
   `state-phase-write.py complete --verdict PASS` because carrier validation used
   `require_expectations=False` and never compared the sealed outcome with the requested
   verdict.
2. A failed VERIFY manifest became merged `PASS` after only
   `verify-mechanical.findings.jsonl` and `spec-verify.results.json` were emptied or
   changed; manifest and raw stream bytes remained unchanged and rehashed successfully.
3. `pipeline.state.json`, VERIFY results/findings, expected-contract, bootstrap, and
   archive readers rejected NaN but accepted duplicate object keys. One live run carried
   two `process_evidence` keys until manually repaired.
4. The live run accepted a post-hoc plaintext `model: gpt-5.6-sol` file supplied through
   `--engine-session-log`; it was not the phase/round worker session. BUILD_GATE was not
   included in the retained-session attestation map.
5. After a restricted IMPLEMENT attempt failed, the same run retried nested Codex with
   `--dangerously-bypass-approvals-and-sandbox`, widened `.devlyn/plan.md`, and continued.
6. `.devlyn/build_gate.worker-session.2.jsonl` was not owned by the archive patterns.

## Subtractive-first decision

1. Derive verdict floors directly from the already-sealed manifest. Do not add a second
   evidence format or trust another summary digest.
2. Reject duplicate keys in the existing strict JSON readers. Do not introduce a JSON
   dependency.
3. Bind the existing PLAN output and canonical worker invocation files to state. Do not
   add a user-facing mode or a permissive legacy fallback for schema-v3 runs.
4. Reject the Codex bypass flag at the existing monitored wrapper. A denied route stops;
   it is never retried with wider authority inside the phase.
5. Extend the one existing archive ownership list; do not create a cleanup subsystem.

## Requirements

- [ ] R1 — Sealed process outcomes own the verdict floor. BUILD_GATE completion rejects
  `PASS`/`PASS_WITH_ISSUES` when any bound product-result expectation failed and accepts
  only `BLOCKED` when a bound entry is `capability_denied`. VERIFY merge independently
  derives `mechanical` from the bound manifest: a product mismatch is `NEEDS_WORK`, a
  capability denial is `BLOCKED`, and all expectations met is `PASS`. Mutating or
  deleting findings/results cannot improve that derived verdict while the same manifest
  remains. The manifest and raw bytes are still archived for non-PASS outcomes.
- [ ] R2 — Every JSON authority boundary touched by resolve bootstrap, expected-contract
  execution, phase state, judge collection/merge, stop/finish checks, and archive rejects
  duplicate object keys as well as NaN/Infinity. Duplicate-key input fails visibly and
  cannot be rewritten into an apparently canonical state.
- [ ] R3 — PLAN output is immutable after completion. PLAN completion binds the exact
  `.devlyn/plan.md` bytes to `pipeline.state.json`; every later spawn, completion, and
  transition rehashes them before changing state. A legal PLAN respawn replaces the
  receipt only through PLAN completion. Mid-flight plan widening blocks before the next
  state change.
- [ ] R4 — Model/session provenance is phase- and round-owned. Mutation phases and
  BUILD_GATE accept only their canonical retained worker session, never an arbitrary
  supplied path or plaintext `model:` header. Codex execution also retains a canonical
  invocation receipt produced by `codex-monitored.sh`, binds its digest into phase state,
  and cross-checks run id, phase, round, requested model, prompt, sandbox, terminal exit,
  and session path. Missing, synthesized, mismatched, or unfinished receipts block.
- [ ] R5 — Execution authority cannot widen inside a phase. `codex-monitored.sh` rejects
  `--dangerously-bypass-approvals-and-sandbox`/`--yolo`. A canonical invocation receipt
  records the actual sandbox argument. After a capability-denied manifest entry exists,
  the same phase/round cannot launch another invocation or complete as product failure or
  PASS; it terminates as `BLOCKED:build-env-underprovisioned`.
- [ ] R6 — Archive ownership covers canonical worker sessions and invocation receipts
  for every phase, including BUILD_GATE and round-suffixed variants. Bootstrap archives
  or blocks these artifacts under prior authenticated ownership, and final archive leaves
  none flat while preserving unrelated `.devlyn` data.
- [ ] R7 — Self-tests reproduce the exact counterexamples above: failed BUILD_GATE plus
  requested PASS, failed VERIFY plus emptied derivatives, capability denial plus widened
  retry, duplicate keys at each authority reader, PLAN mutation, plaintext/arbitrary
  model log, missing/mismatched invocation receipt, bypass flag, and BUILD_GATE worker
  archive. Every former false-PASS path must fail red before the fix and fail closed after.
- [ ] R8 — Canonical `config/skills` and tracked `.agents` mirrors remain byte-identical,
  the full skill lint passes, no dependency or user-facing flag is added, and existing
  legacy archived runs remain readable without granting them schema-v3 execution rights.

## Out of Scope

- Project-mode decomposition, `queue add-plan`, project closure, or iteration 0070.
- Changing the devlynd RT-21 completion classifier.
- Cryptographic protection against an administrator who can rewrite the repository,
  executable, state, and evidence together.
- A general-purpose process supervisor outside `/devlyn:resolve`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {"cmd": "python3 config/skills/_shared/process-evidence.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "python3 config/skills/_shared/spec-verify-check.py --self-test", "exit_code": 0, "timeout_sec": 300},
    {"cmd": "python3 config/skills/_shared/state-phase-write.py --self-test", "exit_code": 0, "timeout_sec": 300},
    {"cmd": "python3 config/skills/_shared/verify-merge-findings.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "python3 config/skills/_shared/resolve-bootstrap.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "python3 config/skills/_shared/archive_run.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "python3 config/skills/_shared/invocation-receipt.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "diff -qr config/skills .agents/skills", "exit_code": 0},
    {"cmd": "bash scripts/lint-skills.sh", "exit_code": 0, "timeout_sec": 300},
    {"cmd": "git diff --check", "exit_code": 0}
  ]
}
```

## Assumptions made

- Schema-v3 runs are the production authority boundary. Legacy archived records remain
  inspectable but cannot be resumed as authenticated schema-v3 executions.
- A standard explicit sandbox selection may be recorded; only bypass/approval-suppression
  flags are categorically forbidden inside the monitored nested route.
- The parent process and installed harness files are the local trust root.
