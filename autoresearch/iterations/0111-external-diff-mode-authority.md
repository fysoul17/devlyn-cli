---
id: "0111-external-diff-mode-authority"
title: "Fail-closed authority for verify-only external diffs"
kind: product-fix
status: REGISTERED 2026-08-28 — implementation pending
complexity: medium
depends_on: ["harness-artifact-integrity-seal"]
---

# iter-0111 — external diff mode authority

## Why this iter exists

Pre-flight 0: this removes an observed single-task harness integrity failure. Archived
free-form run `rs-20260705T015026Z-5f63cc1b7a0c` created
`.devlyn/external-diff.patch` after PHASE 0 and mechanical gates trusted it. Current
bootstrap cleanup prevents stale inheritance but cannot prevent the in-run writer class.

Mission 1: this seals the existing BUILD_GATE / VERIFY mechanical path. It adds no
multi-run substrate and does not modify iter-0110's user-gated model experiment.

## Evidence, prediction, and violated invariant

- Archived `pipeline.state.json` records `mode: free-form`.
- Archived `final-report.md:30` records the index-lock failure and patch creation;
  `build_gate.log.md:5` records inspection of the patch.
- Current `spec-verify-check.py` prefers the patch whenever it exists at both diff
  consumers and never reads `mode` there.
- `.devlyn/` is excluded from authorized-surface enforcement.

Prediction: a worker-created patch survives bootstrap and is trusted in a full run. A
preflight at the verifier's existing state choke point will turn that silent authority
escalation into `correctness.spec-verify-malformed` CRITICAL without changing verify-only.

Violated invariant: `.devlyn/external-diff.patch` is authoritative only when PHASE 0
established `mode: verify-only`; file existence alone is never authority.

## Registered minimal change

1. Add one fail-closed mode/artifact preflight after state is read and before carrier
   staging or gate evaluation.
2. Reuse the existing malformed finding and exit path; add no rule, flag, or abstraction.
3. Pin non-verify failure and verify-only preservation in the existing self-test.
4. Add one state-schema artifact sentence and synchronize the tracked `.agents` mirror.

HX-2 is explicitly excluded: source specs are read-only during a run, accepted amendments
are committed before a new run, finish-gate reversion is the current fail-closed contract,
and bare `PASS` already has a passing collector regression.

## Design review freeze

- Opus 5 found the archived in-run writer counterexample and rejected both closure and a
  silent-ignore guard; it proposed failing closed at the existing state choke point.
- grok-4.6 initially favored closure from bootstrap cleanup alone. After receiving the
  archived counterexample, it revised to the same fail-closed design and found no
  CRITICAL/HIGH issue in the proposal.
- Independent code tracing confirmed the archive bytes, both mode-blind consumers, the
  three affected gate families, and the `.devlyn/` scope exemption.

No design branch remains open before implementation.

## Authorized surface

<!-- devlyn:authorized-surface -->
```json
[
  "config/skills/_shared/spec-verify-check.py",
  ".agents/skills/_shared/spec-verify-check.py",
  "config/skills/devlyn:resolve/references/state-schema.md",
  ".agents/skills/devlyn:resolve/references/state-schema.md",
  "docs/specs/external-diff-mode-authority/spec.md",
  "docs/specs/external-diff-mode-authority/spec.expected.json",
  "autoresearch/iterations/0111-external-diff-mode-authority.md",
  "autoresearch/HANDOFF.md",
  "autoresearch/DECISIONS.md"
]
```

## Verification

<!-- devlyn:verification -->
```json
{
  "verification_commands": [
    {"cmd": "python3 config/skills/_shared/spec-verify-check.py --self-test", "timeout_sec": 300},
    {"cmd": "diff -q config/skills/_shared/spec-verify-check.py .agents/skills/_shared/spec-verify-check.py && diff -q config/skills/devlyn:resolve/references/state-schema.md .agents/skills/devlyn:resolve/references/state-schema.md"},
    {"cmd": "bash scripts/lint-skills.sh", "timeout_sec": 600},
    {"cmd": "git diff --check"}
  ]
}
```

## Principles check

- Pre-flight 0 — PASS: observed free-form artifact authority is the target.
- Mission 1 — PASS: single-run mechanical verification only.
- No workaround — reject unauthorized authority instead of ignoring its bytes.
- No overengineering — one invariant check, existing finding, no new option.
- No guesswork — a falsifiable prediction and raw archived witness precede the edit.
- Worldclass / production ready — invalid mode/artifact state is explicit and blocking.
- Best practice — authority derives from state, not ambient file existence.
- Optimized — no extra model turn or runtime subprocess.

