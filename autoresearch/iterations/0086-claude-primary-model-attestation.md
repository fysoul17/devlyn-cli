---
id: "0086-claude-primary-model-attestation"
title: "Attest Claude primary models without auxiliary-call false blockers"
kind: bugfix
status: FROZEN 2026-07-29
complexity: medium
depends_on: ["0085-verify-envelope-anatomy"]
---

# iter-0086 — attest Claude primary models without auxiliary-call false blockers

## Why this iteration exists

Run `rs-20260729T021414Z-26b877f33894` was blocked partly because its captured
Claude wrapper (SHA-256
`4a7d667dec0412d22e50fd4ed81559eaa7935133892eb634a84845738cb8dcc3`)
reported both `claude-opus-5[1m]` and a Haiku auxiliary. The wrapper's
top-level tuple `2854/9927/1095180/73889` exactly matches the Opus entry, while
the Haiku entry is `4106/14/0/0`; the raw-session receipt named in the archived
BUILD_GATE log contains only `claude-opus-5` assistant turns. A second captured
Fable 5 wrapper has the same primary-plus-Haiku shape and a unique exact tuple
match. `state-phase-write.py` instead treats every `modelUsage` key as an
effective worker model and rejects any wrapper with more than one key. This is
a nondeterministic false blocker in the hands-free Mission 1 path.

The distinct 600-second BUILD_GATE transport failure is not part of this
iteration. A production transport runner remains the M1.5 boundary.

## Decisive criterion

**Primary authorship without ambiguity:** accept a multi-entry Claude wrapper
only when its main-call accounting identifies exactly one primary entry; keep
every absent, malformed, zero-match, multi-match, or requested-model mismatch
case fail-closed.

## Subtractive-first answer

1. Do not whitelist Haiku or any auxiliary model name.
2. Do not choose the first, most expensive, or largest model entry.
3. Reuse the wrapper's existing top-level primary usage tuple; add no flag,
   retry, session-directory scan, or new state field.

## Requirements

- [ ] Preserve the current singleton `modelUsage` behavior.
- [ ] For a multi-entry Claude JSON wrapper, compare top-level
  `usage.{input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}`
  to each entry's corresponding camel-case counters. Accept only one exact
  four-counter match.
- [ ] Return the matched entry's model key verbatim, identical to the singleton
  path. Do not substitute `canonicalModel`: the key carries variant suffixes
  such as `[1m]` that exact attestation and seat certification compare.
- [ ] Missing or malformed top-level usage, malformed entry counters, zero
  matches, or multiple matches must retain the existing explicit
  `BLOCKED:model-attestation-failed` path. A selected primary that differs from
  `model_requested` must retain `BLOCKED:model-attestation-mismatch`.
- [ ] Apply the same primary-selection rule to the R6 replay measurement path
  so product and measurement do not disagree on the same wrapper.
- [ ] Add real-shaped regression rows for Opus+Haiku and Fable+Haiku, plus
  singleton, zero-match, duplicate-match, and requested-model-mismatch controls.
- [ ] Every selection row must hardcode its expected primary string or
  fail-closed error class independently of the selector under test. Include a
  rank-confound row where the auxiliary has larger token/cost fields but the
  top-level usage tuple uniquely matches the expected primary.
- [ ] Update the state-schema wording and both installed mirrors. Add no
  dependency, flag, fallback, or model-name allowlist.

## Exact product surface

IMPLEMENT may edit only:

- `config/skills/_shared/state-phase-write.py`;
- `.claude/skills/_shared/state-phase-write.py`;
- `.agents/skills/_shared/state-phase-write.py`;
- `benchmark/ceiling/scripts/r6-replay-cell.py`;
- `config/skills/devlyn:resolve/references/state-schema.md`;
- `.claude/skills/devlyn:resolve/references/state-schema.md`;
- `.agents/skills/devlyn:resolve/references/state-schema.md`.

This iteration record is read-only pipeline input. No adapter, engine route,
BUILD_GATE prompt, archive rule, raw benchmark receipt, or prior iteration may
change.

## Claim boundary

PASS proves only that Claude auxiliary billing calls do not masquerade as
primary-worker conflicts when the wrapper identifies one unique primary usage
entry. It does not certify arbitrary multi-model delegation, alter requested
model mismatch handling, or solve long-command transport. It assumes the
wrapper's top-level `usage` tuple remains primary-model accounting, as observed
in the two captured primary-plus-auxiliary wrappers; a future wrapper that
breaks that contract must fail the registered real-receipt comparison rather
than silently widening this claim.

Registered residual, not fixed here: `benchmark/ceiling/scripts/nodeg-cell.py`
and `benchmark/ceiling/scripts/claude-isolation.py` still require every
`modelUsage` key to name Sonnet and therefore reject auxiliary entries. They
belong to their own ceiling-runner evidence boundary; this iteration does not
silently expand into them.

## Principles check

0. **Not score-chasing:** removes an observed false terminal blocker from a
   real formal run.
7. **Mission-bound:** restores Mission 1 single-task hands-free completion; it
   adds no parallel or autonomous-organisation surface.
1. **No overengineering:** no new file, field, flag, retry, or model allowlist.
2. **No guesswork:** two real wrappers plus transcript authorship anchor the
   hypothesis; zero/multiple-match controls can falsify it.
3. **No workaround:** correct the billing-summary interpretation rather than
   retrying until the auxiliary call disappears.
4. **Worldclass / production-ready:** ambiguity and requested-model drift stay
   fail-closed.
5. **Best practice:** deterministic exact-field comparison; no heuristic rank.
6. **Layer-cost-justified:** no extra model call or phase is added.

<!-- devlyn:verification -->
## Verification

- Real-shaped primary+auxiliary rows select the transcript-authored primary.
- Zero-match and duplicate-match rows fail closed.
- Product and R6 measurement selectors agree on every shared row.
- Full skill lint runs once in the foreground outside the fixed-60-second
  literal verifier.

```json
{
  "verification_commands": [
    {
      "cmd": "python3 config/skills/_shared/state-phase-write.py --self-test",
      "exit_code": 0
    },
    {
      "cmd": "python3 benchmark/ceiling/scripts/r6-replay-cell.py self-test",
      "exit_code": 0
    },
    {
      "cmd": "cmp config/skills/_shared/state-phase-write.py .agents/skills/_shared/state-phase-write.py",
      "exit_code": 0
    },
    {
      "cmd": "cmp config/skills/_shared/state-phase-write.py .claude/skills/_shared/state-phase-write.py",
      "exit_code": 0
    },
    {
      "cmd": "cmp config/skills/devlyn:resolve/references/state-schema.md .agents/skills/devlyn:resolve/references/state-schema.md",
      "exit_code": 0
    },
    {
      "cmd": "cmp config/skills/devlyn:resolve/references/state-schema.md .claude/skills/devlyn:resolve/references/state-schema.md",
      "exit_code": 0
    },
    {
      "cmd": "python3 -m py_compile config/skills/_shared/state-phase-write.py benchmark/ceiling/scripts/r6-replay-cell.py",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ]
}
```

Done means the two observed false blockers select their transcript-authored
primary model and every genuinely ambiguous wrapper still blocks.
