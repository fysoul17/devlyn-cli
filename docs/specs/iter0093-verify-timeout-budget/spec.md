---
complexity: medium
---

# iter-0093 — authorable per-command verification timeout budget

Three-way design round (Fable orchestrator + Codex gpt-5.6-sol + Grok 4.5,
2026-08-05) converged GO-WITH-EDITS on both seats; receipts in the session
scratchpad (`timeout-fix/{codex,grok}-response.log`). User authorized the fix
2026-08-05 after the first live in-run firing (run `rs-20260804T113416Z`,
`bash scripts/lint-skills.sh` killed at 60s; direct run 127.55s exit 0).
Decisive criteria adopted: Authorable-budget + live-runner-byte identity
(Grok) and Replay parity (Codex).

## Requirements

### R1 — `timeout_sec` field contract

- Add optional `timeout_sec` to every verification-command entry shape:
  inline `## Verification` carrier, sibling `spec.expected.json` carrier, and
  risk-probe entries (they share `validate_shape`).
- Validation: integer, `bool` explicitly rejected, `1 <= v <= 600`. Absent →
  default 60, unchanged. Reject violations fail-closed in `validate_shape`,
  `validate_expected_shape`, `EXPECTED_VERIFICATION_COMMAND_KEYS`, and
  `_shared/expected.schema.json` (its `additionalProperties: false` entry
  gains the property with a description that documents the field for spec
  authors: default 60, max 600).
- Introduce one module constant `DEFAULT_TIMEOUT_SEC = 60` in
  `spec-verify-check.py` shared by the run path, the timeout message, and the
  fix_hint; no residual hardcoded 60/`60s` literals remain on that path.
- The command run loop passes the validated declared budget to
  `subprocess.run` (`timeout_sec` when present, else the constant).

### R2 — distinct timeout identity

- Every `subprocess.TimeoutExpired` row (spec command or risk probe) emits
  rule_id `correctness.verification-timeout` instead of the current
  `correctness.spec-literal-mismatch` / `correctness.risk-probe-failed`
  conflation. Severity stays CRITICAL, confidence 1.0, blocking true;
  `file`/`criterion_ref` conventions unchanged.
- The finding message and fix_hint name the ACTUAL budget that expired and the
  `timeout_sec` field with its 600 maximum. One message shape; no
  multi-branch prose.
- The per-command result row for a timeout records the numeric budget that
  applied.

### R3 — self-tests

Extend the in-file self-test with deterministic fixtures (no sleep longer
than a few seconds):

- Field validation rejections: `true` (bool), `0`, negative, `601`, string —
  each rejected on the inline carrier; `601` and bool also rejected via the
  sibling-expected path.
- Declared budget honored both ways: a command sleeping ~2s with
  `timeout_sec: 1` → timeout finding with the new rule_id and budget-named
  message; a command sleeping ~1s with `timeout_sec: 5` → pass.
- Carrier preservation: the field survives inline, sibling-expected, and
  risk-probe entries (probe path may reuse the small sleep fixtures).
- Absent field keeps the default: an undeclared entry's timeout finding
  message names 60 (asserted via the message text of the 1s-budget fixture's
  sibling control or equivalent cheap assertion; no >60s sleeps).

### R4 — replay parity (Codex seat, adopting the 0083 precedent)

- `benchmark/auto-resolve/scripts/run-fixture.sh` post-run scorer
  (`:745-764` region) replays verification entries honoring the same
  contract: declared `timeout_sec` when present, default 60, max 600.
- `scripts/lint-fixtures.sh` fallback validator (`:164-174` region) accepts
  the optional field with the same bounds instead of rejecting it.
- Both changes get regression coverage in each script's existing test
  convention (extend the nearest existing self-test/lint fixture; no new
  test harness).

### R5 — docs and mirrors

- `probe-derive.md` rules: one sentence permitting probes to declare
  `timeout_sec` (max 600) when the exercised verification legitimately
  exceeds 60s; mirror any lint-pinned parity copy (e.g. resolve `SKILL.md`)
  as the existing parity checks require.
- `references/state-schema.md:60`: adjust the one sentence so probe failures
  surfacing as `correctness.risk-probe-failed` reads accurately now that
  timeout rows carry `correctness.verification-timeout`.
- Synchronize every changed `config/skills/**` file to the tracked `.agents`
  and ignored `.claude` installed mirrors in the same commit — BUILD_GATE
  executes the installed `_shared` bytes, so mirror identity is what makes
  this run's own `timeout_sec: 300` lint verification prove the fix live.

## Out of scope

- No change to the 60s default, the CRITICAL severity, or fail-loud behavior.
- No env-var knob, no global timeout raise, no per-phase budget system.
- No changes to other timeout sites (`codex-monitored.sh`,
  `run-bounded.py`, SURFACE_CLOSE budgets) or to archived benchmark corpora
  and result artifacts.
- No spec.expected.json sibling file for THIS spec (inline carrier only —
  the pre-fix bootstrap validator must stage it).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 config/skills/_shared/spec-verify-check.py --self-test",
      "exit_code": 0
    },
    {
      "cmd": "diff -q config/skills/_shared/spec-verify-check.py .agents/skills/_shared/spec-verify-check.py && diff -q config/skills/_shared/spec-verify-check.py .claude/skills/_shared/spec-verify-check.py && diff -q config/skills/_shared/expected.schema.json .claude/skills/_shared/expected.schema.json",
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
  ],
  "max_deps_added": 0
}
```
