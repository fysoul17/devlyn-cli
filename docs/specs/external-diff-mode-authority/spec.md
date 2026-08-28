---
complexity: medium
---

# External diff mode authority

`external-diff.patch` is a verify-only input, but the current verifier trusts it by
existence alone. Bootstrap cleanup closes cross-run staleness, not a worker creating the
artifact after PHASE 0. This spec closes that remaining authority gap and nothing else.

## Evidence and prediction

- Archived run
  `benchmark/probes/results/iter0061-b4/devlyn-snapshot/runs/rs-20260705T015026Z-5f63cc1b7a0c/pipeline.state.json`
  records `mode: free-form`.
- Its `final-report.md` records that the worker created
  `.devlyn/external-diff.patch` after an index-lock failure, and its
  `build_gate.log.md` confirms BUILD_GATE inspected the artifact.
- `config/skills/_shared/spec-verify-check.py` currently prefers that artifact at both
  diff-consumer sites without checking `state.mode`; `.devlyn/` is scope-exempt.

Prediction: a non-verify-only run with the artifact present currently proceeds into
mechanical verification. After the fix it exits 1 with the existing
`correctness.spec-verify-malformed` CRITICAL finding before consuming the patch, while
verify-only behavior remains unchanged.

## Subtractive-first decision

1. Do not add a new rule id, flag, parser, or reader-side fallback.
2. Do not silently ignore the artifact outside verify-only; that can hide untracked
   implementation files from `git diff <base_sha>`.
3. Reuse the existing malformed-carrier path at the verifier's state-reading choke point.

## Requirements

### R1 — mode-bound authority fails closed

1. After reading pipeline state and before staging or evaluating verification, an existing
   `.devlyn/external-diff.patch` with any mode other than `verify-only` emits the existing
   `correctness.spec-verify-malformed` CRITICAL finding and exits 1.
2. The error names the artifact, actual mode, and the verify-only requirement.
3. Verify-only continues consuming the exact external patch as today.

### R2 — red-first regression

1. Add a subprocess-level self-test proving a non-verify-only state plus the artifact
   fails closed with the named CRITICAL finding.
2. Add or retain a negative control proving verify-only still accepts the artifact.
3. Capture the red test result before production logic changes, then rerun it green.

### R3 — one documented owner contract

1. Document `.devlyn/external-diff.patch` next to the other state-bound runtime artifacts
   as verify-only input.
2. Keep canonical `config/skills` and tracked `.agents` bytes identical.

## Non-goals

- No change to bootstrap cleanup or archive inventory; those already close cross-run
  staleness.
- No finish-gate exemption for source specs. Specs remain read-only during a run and
  accepted amendments are committed before a new run.
- No collector change; bare terminal `PASS` is already accepted and self-tested.
- No change to iter-0110 or its user-gated m5 launch apparatus.

## Authorized implementation surface

- `config/skills/_shared/spec-verify-check.py`
- `.agents/skills/_shared/spec-verify-check.py`
- `config/skills/devlyn:resolve/references/state-schema.md`
- `.agents/skills/devlyn:resolve/references/state-schema.md`
- `docs/specs/external-diff-mode-authority/spec.md`
- `docs/specs/external-diff-mode-authority/spec.expected.json`
- `autoresearch/iterations/0111-external-diff-mode-authority.md`
- `autoresearch/HANDOFF.md`
- `autoresearch/DECISIONS.md`

