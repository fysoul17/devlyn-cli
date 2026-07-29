---
id: "0085a-lint-baseline-hermeticity"
title: "Make lint evidence scope and npm cache hermetic"
kind: bugfix
status: FROZEN
complexity: medium
depends_on: ["0084-node-lint-applicability", "0085-verify-envelope-anatomy"]
---

# iter-0085a — make lint evidence scope and npm cache hermetic

**Status: FROZEN 2026-07-29.**

## Why this iteration exists

The iter-0085 implementation completed its analyzer and deterministic checks,
but its mandatory full skill lint exposed two baseline failures outside that
iteration's authorized surface:

1. Check 1 and Check 2 scan tracked `benchmark/**` and re-read the immutable
   iter-0084 lint receipt. That receipt necessarily repeats the checks' own
   forbidden phrases in its section headings. The same lint already excludes
   `benchmark/auto-resolve/results/**` as frozen historical evidence, but does
   not apply that policy to `benchmark/ceiling/results/**`.
2. `npm pack --dry-run --json` inherits the user-global npm cache. During the
   blocked run it failed `EPERM` on root-owned cache entries. A fresh temporary
   cache made the same pack succeed with 501 files.

As of the 2026-07-29 freeze review, the user's global cache no longer contains
root-owned entries and a global-cache pack succeeds. Therefore this iteration
does not claim a build-time red-to-green reproduction of `EPERM`; the recorded
blocked run is the observed failure, and the verification below proves the
lint no longer depends on that mutable machine state.

## Requirements

- [ ] Exclude `benchmark/ceiling/results/**` from Check 1 and Check 2 only,
  matching the existing frozen-results policy while preserving scans of live
  product, skill, benchmark source, and user-facing docs.
- [ ] Run the existing npm package-membership dry-run with a fresh cache
  allocated by `make_temp_dir`; scope `npm_config_cache` to that subprocess
  only and never mutate or repair the user's global npm cache.
- [ ] Fail closed when either temporary allocation fails. Do not fall through
  to a bare global-cache `npm pack`, and do not misreport an allocation failure
  as an npm failure.
- [ ] Remove every allocated pack temp artifact on both npm success and npm
  failure, using the script's existing guarded cleanup style.
- [ ] Add no new flag, helper abstraction, dependency, fixture tree, or
  lint-of-the-lint assertion. The tracked historical receipt plus BUILD_GATE's
  poisoned-cache full lint exercise both regression classes through the real
  lint path.

## Exact product surface

Only `scripts/lint-skills.sh` may change during IMPLEMENT. This iteration record
is orchestrator-owned input and must remain read-only to PLAN and IMPLEMENT.
The untracked iter-0085 analyzer and generated JSON are pre-existing work and
must not be staged, edited, or deleted by this run.

## Three-seat adjudication

Codex, Fable 5, and Grok 4.5 agree on the two root fixes: complete the existing
historical-results exclusion class and isolate the npm subprocess cache. Both
external seats required fail-closed allocation and unconditional guarded
cleanup. Grok proposed permanent self-inspection assertions; Fable rejected
them as overengineering. Codex adopts Fable's narrower result because counting
pathspec literals inside the lint script can self-satisfy and the real full-lint
verification already exercises both observed failures.

## Claim boundary

A pass proves only that frozen ceiling results cannot self-trigger Check 1/2,
that the package-membership check succeeds even when the inherited npm cache is
invalid, and that normal lint coverage remains green. It does not change frozen
evidence, package contents, benchmark behavior, or VERIFY timing.

## Principles check

1. **No workaround:** correct the input class and process dependency; do not
   edit evidence or repair machine-global state.
2. **No overengineering / subtractive-first:** two pathspec entries and one
   isolated temp-cache lifecycle; no new mechanism.
3. **No guesswork:** the exact offender set and fresh-cache pack were probed
   before freeze; the changed global-cache condition is recorded honestly.
4. **Optimized / Production ready:** the mandatory lint becomes repeatable
   across machines and still fails visibly on allocation or pack errors.

<!-- devlyn:verification -->
## Verification

BUILD_GATE runs `npm_config_cache=/dev/null bash scripts/lint-skills.sh`
directly. The literal verifier does not duplicate that repository-wide suite
under its fixed 60-second per-command budget.

```json
{
  "verification_commands": [
    {
      "cmd": "bash -n scripts/lint-skills.sh",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "forbidden_patterns": [
    {
      "pattern": "benchmark/ceiling/results/iter0084-node-lint-applicability|sudo chown|npm config set cache",
      "description": "Do not special-case one receipt or mutate user-global npm state.",
      "files": [
        "scripts/lint-skills.sh"
      ]
    }
  ]
}
```
