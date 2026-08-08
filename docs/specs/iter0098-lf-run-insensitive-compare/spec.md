---
complexity: medium
---

# iter-0098 — oracle two-branch LF-run-insensitive delivery comparison

Design round converged 2026-08-06 (Codex+Grok AGREE-WITH-EDITS;
registration `autoresearch/iterations/0098-lf-run-insensitive-compare.md`).
Trigger: DECISIONS 0097.1 — the terminal-LF byte at the
Read→transcribe→`Agent.prompt` boundary is bidirectionally
model-unstable (0094 strip / 0096 strip-despite-cue / 0097 add onto the
canonicalized artifact); with the canonicalized source a delivered
terminal-LF run is pure transport addition. Target:
`benchmark/ceiling/scripts/plan-dispatch-oracle.py` only.

## Requirements

### R1 — dual digests recorded

For every Agent candidate, compute and record BOTH
`delivered_prompt_sha256` (raw, existing field unchanged) AND a new
`delivered_prompt_terminal_lf_stripped_sha256` =
sha256 of the delivered prompt with its terminal `0x0a` run removed
(`prompt.rstrip("\n")`); when the prompt has no terminal LF the two
values are equal. Bump the oracle payload `schema_version` for the
added field.

### R2 — two-branch acceptance predicate

At BOTH digest-enforcement sites (the in-window call-shape/acceptance
check and the delivery attestation match), delivery matches when
`recorded_render_digest == raw OR recorded_render_digest == stripped`,
evaluating the raw-exact branch FIRST. `delivered-prompt-digest-mismatch`
(and the dependent call-shape violation) fire only when BOTH branches
fail. No violation renames.

### R3 — self-tests

All existing assertions stay green; add deterministic cases:

1. Retained WITH-LF-era exact delivery (recorded digest computed over a
   prompt ending in `\n`, delivered identical) → ACCEPTED via the raw
   branch (compat).
2. Canonicalized exact delivery (no terminal LF either side) →
   ACCEPTED; raw == stripped.
3. Delivered = render + exactly one added terminal LF → ACCEPTED via
   the stripped branch; payload records UNEQUAL raw vs stripped digests.
4. Delivered = render + multiple (≥2) terminal LFs → ACCEPTED via the
   stripped branch.
5. Non-terminal content mutation (mid-body byte change) → still
   `delivered-prompt-digest-mismatch`.
6. Short literal/path indirection delivery (`$(cat …)`-class, existing
   case shape) → still a violation.

## Out of scope

- No renderer, ledger, state, watcher, scorer, or SKILL.md changes.
- No digest changes on the product/render side; the render digest
  recording is untouched.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 benchmark/ceiling/scripts/plan-dispatch-oracle.py --self-test",
      "stdout_contains": ["SELFTEST PASS"],
      "exit_code": 0,
      "timeout_sec": 300
    },
    {
      "cmd": "grep -cF 'delivered_prompt_terminal_lf_stripped_sha256' benchmark/ceiling/scripts/plan-dispatch-oracle.py | awk '{exit ($1>=2)?0:1}'",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
