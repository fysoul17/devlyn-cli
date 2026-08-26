---
id: iter0113-primary-verify-budget
title: Primary VERIFY budget and timeout authority
kind: bugfix
status: planned
complexity: medium
---

# Primary VERIFY budget and timeout authority

## Context

Iteration 0112 sealed verdict authority, but its own representative verification exposed
an upstream liveness gap. Run `rs-20260826T195608Z-ea9f99ccc2c0` passed all 10 sealed
MECHANICAL commands, then the fresh isolated Codex primary JUDGE performed 64 retrieval
calls over a 4,978-line diff, emitted zero canonical stdout, and exited 124 after
600.099 seconds. The deterministic merge correctly blocked because
`verify.findings.jsonl` was absent, but the run reported only the generic missing-source
finding and retained no explicit primary-timeout carrier.

Iteration 0065 explicitly left primary-judge budgeting out of scope because no primary
overrun had then been observed. That premise is now falsified. A primary verdict is
non-optional: unlike pair-JUDGE timeout, primary timeout has no existing solo verdict to
preserve and can never become PASS.

## Subtractive-first decision

1. Keep the 600-second budget and fail-closed merge. Do not extend time or copy the pair
   TIMEOUT-to-solo semantics.
2. Bound the existing primary review process to one broad requirements pass plus one
   interaction pass. Do not add another judge or split requirements into agents.
3. Add one explicit primary-timeout marker to the existing VERIFY and archive contracts.
   Do not introduce a new state machine or user-facing flag.
4. Preserve every canonical finding observed before timeout, but apply a BLOCKED floor
   whenever the primary process timed out.

## Requirements

- [ ] R1 — The Codex primary JUDGE invocation is explicit and reproducible: monitored,
  isolated, read-only, 600-second budget, `model_reasoning_effort=high`, no model pin,
  no bypass, and direct stdout/stderr capture. The primary route is distinct from the
  pair-JUDGE route and cannot inherit pair timeout semantics.
- [ ] R2 — Primary review is process-bounded without reducing rubric coverage. It makes
  one broad pass over the source contract, sealed MECHANICAL carrier, and cumulative
  diff, then one targeted interaction pass over unresolved clauses. Related reads are
  batched; byte-identical `.agents` mirrors are not reread after sealed parity passes;
  self-test bodies/raw streams are opened only for a named unresolved clause. Before any
  third pass it emits the required terminal result. If R1–R8 or another spec axis remains
  uncovered, it emits a verdict-binding BLOCKED coverage finding instead of continuing.
- [ ] R3 — Primary process exit 124 writes
  `.devlyn/verify.primary.timeout.json` with exact engine and `budget_seconds: 600`
  before merge. A malformed marker is itself a contract blocker. A valid marker floors
  primary source verdict at BLOCKED whether stdout/findings are empty, partial, or
  otherwise parseable; any canonical findings still join the merge and cannot be erased.
  No primary-timeout path can yield PASS or pair-style solo verdict.
- [ ] R4 — Without the primary marker, existing primary missing/invalid-output behavior
  remains fail-closed. Pair-JUDGE timeout behavior and
  `.devlyn/verify.pair.timeout.json` remain byte-for-byte semantically unchanged.
- [ ] R5 — Archive ownership includes the primary-timeout marker, bootstrap archives it
  under authenticated prior-run ownership, and completed archive leaves no owned marker
  flat while preserving unrelated `.devlyn` data.
- [ ] R6 — Self-tests cover valid primary timeout with empty output, timeout plus
  verdict-binding findings, malformed/wrong-engine/wrong-budget markers, no-marker
  missing output, pair timeout non-regression, and archive/bootstrap ownership. Canonical
  `config/skills` and `.agents` mirrors remain byte-identical, full skill lint passes, no
  dependency or public flag is added, and `git diff --check` is clean.

## Out of Scope

- Treating primary timeout as PASS, PASS_WITH_ISSUES, or TIMEOUT-solo.
- Increasing the 600-second judge budget.
- Project-mode decomposition, queue ingestion, iteration 0070, or devlynd behavior.
- Splitting the primary rubric across multiple agents.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {"cmd": "python3 config/skills/_shared/verify-merge-findings.py --self-test", "exit_code": 0, "timeout_sec": 240},
    {"cmd": "python3 config/skills/_shared/archive_run.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "python3 config/skills/_shared/resolve-bootstrap.py --self-test", "exit_code": 0, "timeout_sec": 180},
    {"cmd": "diff -qr config/skills .agents/skills", "exit_code": 0},
    {"cmd": "bash scripts/lint-skills.sh", "exit_code": 0, "timeout_sec": 300},
    {"cmd": "git diff --check", "exit_code": 0}
  ]
}
```

## Assumptions made

- Exit 124 remains the canonical monitored wall-budget abort.
- `config/skills` is the canonical source and `.agents/skills` is its tracked mirror.
- A bounded primary that cannot cover the rubric must BLOCK rather than guess.
