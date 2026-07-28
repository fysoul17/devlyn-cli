---
id: "0084-node-lint-applicability"
title: "Make Node lint applicability invariant"
kind: bugfix
status: SHIPPED 2026-07-28
complexity: medium
depends_on: ["0083-summary-verdict-merge"]
---

# iter-0084 — make Node lint applicability invariant

**Status: SHIPPED 2026-07-28.**

## BUILT + GATED

The prompt-contract fix shipped in `c0f4724`. The implementation changed only
the canonical BUILD_GATE reference and its installed mirrors: exact
`scripts.lint` and recognized configured linters are applicable; an arbitrary
specialized `lint:*` declaration alone is not. Spec-explicit specialized
commands still run in step 4 with their real severity.

The frozen post-edit bar passed without a behavioral retry:

| Cell | Result |
|---|---|
| T | 3/3 general lint `SKIP`; no command, finding, or fix round |
| K1 | 3/3 `npm run lint`; exit 1; `quality.lint` MEDIUM |
| K2 | 3/3 `npx eslint .`; exit 1; `quality.lint` MEDIUM |
| K3 | 3/3 general lint `SKIP`; step-4 `npm run lint:json`; exit 1; `correctness.spec-literal-mismatch` CRITICAL |

All 12 receipts used `claude-sonnet-5`; input hashes were unchanged.
`bash scripts/lint-skills.sh` completed with exit 0 and `All checks passed`
(140-line log, SHA-256
`94ab1d892544bc0ceb67c7d16d58ee123e28ac0de884d7ae493c20e7a10263cd`).
Mirror parity, `git diff --check`, and spec verification passed.

Formal `/devlyn:resolve` run `rs-20260728T121553Z-8a240495d492` reached VERIFY
PASS with zero merged findings: Codex GPT-5.6-sol primary judge PASS and Fable
5 pair judge PASS. Grok 4.5 independently checked all 12 replay receipts and
returned PASS with zero discrepancies. Its stdout again concatenated interim
JSON status objects before the final valid result; this is an advisory-seat
emission residual, not a behavioral discrepancy in this gate.

Two earlier Fable BUILD_GATE calls ended at their shell-tool time limits while
the full lint suite was still running; neither was counted as PASS. The same
suite then completed directly in the foreground, and a fresh Fable adjudicator
verified the log hash, summary, and short gates before returning PASS. The first
four-way replay launch also omitted the case prompt because relative paths were
resolved from `/tmp`; all four outputs were renamed
`*-invalid-missing-case.*` before valid trial numbering and excluded from the
12 scored receipts.

Durable evidence is in
`benchmark/ceiling/results/iter0084-node-lint-applicability/`.

## Why this iteration exists

Pre-flight 0: this iteration exists because the same BUILD_GATE contract spent
an observed F7 run on a false lint finding and futile fix loop while four peer
runs interpreted the same repository shape differently; it closes that
user-time and routing failure before another cohort measures the phase again.

## Measured failure

The corrected `nodeg-hook-20260722c` anatomy is conservation-clean for all
seven rows. Its current medians are startup 193,016 ms, interphase 50,600 ms,
phase-union 1,661,503 ms, and elapsed 2,068,641 ms. This re-derives the active
target away from blindly reviving iter-0077's falsified mechanical-startup
hypothesis and toward a concrete phase-union failure.

Five runs used the same `harbor-tools` package shape: exact `scripts.test`, a
specialized `scripts["lint:json"]` pointing at a missing file, no exact
`scripts.lint`, and no general JavaScript linter configuration. Their
BUILD_GATE decisions diverged:

| Row | Observed lint decision |
|---|---|
| F7 | ran `npm run lint:json`, emitted HIGH, spawned a futile fix IMPLEMENT, then softened the unchanged HIGH into an illegal `PASS_WITH_ISSUES` |
| F11 | ran the same broken command, then declared it unrelated and emitted no finding |
| F23 | skipped it as non-applicable |
| F25 | skipped it as non-applicable |
| F26 | skipped lint because no ESLint config exists |

F7's corrected attribution records 228,274 ms of prior BUILD_GATE history and
89,408 ms of lint-triggered fix IMPLEMENT. That 317,682 ms is an upper bound on
the waste class, not a claim that every byte was caused by lint. The canonical
prompt names `eslint`, `ruff`, and `clippy`, but does not define whether an
arbitrary npm `lint:*` script is the language lint gate. The undefined
applicability contract is the violated invariant.

## Supersession and mission boundary

The initial three-seat design selected an earned pure-script BUILD_GATE fast
path. That selection is **withdrawn for this mission**, not technically
refuted: `MISSIONS.md` places a deterministic runner after Mission 1 floor and
ceiling proof, in M1.5. Mission 1 is still active. Removing the BUILD_GATE model
orchestrator now would start the next mission by relabeling it as a gate tweak.

The replacement is Mission-1 work explicitly allowed by `MISSIONS.md`: a
single canonical prompt/reference correction for a measured failure class.
It keeps the current LLM BUILD_GATE, phase order, commands, artifacts, fix loop,
and state transitions unchanged. The resulting replay data may later admit the
M1.5 fast-path candidate; this iteration does not ship it.

## Requirements

- [x] Replace the ambiguous Node lint wording in the canonical BUILD_GATE
  prompt with one mechanical applicability rule:
  - run a recognized configured language linter, such as ESLint with a config;
  - and/or run the exact `package.json` `scripts.lint` command;
  - do not infer an arbitrary specialized `lint:*` command such as
    `lint:json` as the general language lint gate solely from its declaration;
  - when the spec verification commands explicitly name a specialized command,
    step 4 still executes it and preserves the real failure severity;
  - no applicable linter means an explicit logged SKIP with no lint finding.
- [x] Preserve the existing applicable-lint finding contract: errors are
  `MEDIUM` / `quality.lint`; warnings remain LOW unless the spec elevates them.
- [x] Preserve the quality-bar rule that drift in an **applicable** gate is a
  finding. Add only the missing distinction that a package-script declaration
  alone is not evidence that CI executes it.
- [x] Keep the three installed prompt surfaces byte-identical.
- [x] Change no runner, state schema, engine route, model route, script, flag,
  dependency, or other phase.

## Exact product surface

Only these three mirrored files may change in the implementation pipeline:

- `config/skills/devlyn:resolve/references/phases/build-gate.md`
- `.agents/skills/devlyn:resolve/references/phases/build-gate.md`
- `.claude/skills/devlyn:resolve/references/phases/build-gate.md`

The iteration record and post-build measurement receipts are orchestrator-owned
evidence, not product implementation surface.

## Team adjudication

Codex, Grok 4.5, and Fable 5 ran R0 adversarial and R1 reconciliation on the
latest corrected anatomy. All first selected the coverage-complete pure-script
fast path. A new authoritative source changed the decision: both external
seats then read `MISSIONS.md` and independently named the same delta — the fast
path is M1.5 deterministic-runner work, while the five same-cohort receipts
expose a Mission-1 prompt-contract defect that must be fixed first.

Final three-seat position: **P now, fast path deferred**. Grok ranked
`P >> freeze-nothing > model-routing > unnamed startup`; Fable ranked
`P > research-only model routing > unnamed startup > freeze-nothing`. Codex
adopts P under the named criterion **Mission-sequenced root cause**.

## Satisfiability dry-run before freeze

The frozen bar was exercised once with actual `claude-sonnet-5` before this
status was written. All commands ran only in `/tmp` copies of the archived F25
repository; the source tree was not edited.

| Cell | Mechanical setup | Predicted / observed |
|---|---|---|
| T | only specialized `lint:json`; no exact `lint`; no recognized config | `SKIP`, no finding — PASS |
| K1 | exact failing `scripts.lint` | RUN, exit 1, `quality.lint` MEDIUM — PASS |
| K2 | recognized ESLint config plus local failing ESLint control | RUN, exit 1, `quality.lint` MEDIUM — PASS |
| K3 | no general lint, but spec explicitly requires `npm run lint:json` | general lint SKIP; command exit 1, `correctness.spec-literal-mismatch` CRITICAL — PASS |

Operator record: the first K2 direct check ran from the K1 directory and exited
127; it was corrected before scoring. The first K2/K3 model inputs were also
discarded after shell interpolation executed backticked temp commands before
the model. K3's next attempt was discarded because its chained command was
permission-denied. The table admits only clean, uniquely captured reruns with
no permission denials. These incidents change no product claim.

## Frozen post-edit bar

The build ships only if all cells below use the edited canonical body, the same
pinned CLI/model, and preserved raw receipts:

1. **T, n=3:** same-byte Node shape with only broken `lint:json`; 3/3 log lint
   SKIP, never execute `npm run lint:json` outside step 4, emit zero lint
   findings, and spawn zero lint-triggered fix IMPLEMENT rounds.
2. **K1, n=3:** exact failing `scripts.lint`; 3/3 execute it and emit at least
   one `quality.lint` MEDIUM finding.
3. **K2, n=3:** recognized ESLint configuration plus a real failing lint
   command; 3/3 execute it and emit the lint finding.
4. **K3, n=3:** spec-explicit `npm run lint:json`; 3/3 execute it through the
   verification role and preserve the failure as CRITICAL rather than calling
   it non-applicable.
5. Full skill lint, mirror parity, and `git diff --check` pass.

Any single behavioral miss is `DO NOT SHIP`; no majority vote and no retry that
erases a failed cell. The existing F7/F11/F23/F25/F26 receipts are the baseline
and are not rerun or reinterpreted.

## Claim boundary and residuals

A green result proves only that Node language-lint applicability is invariant
on the frozen treatment and controls, and that the F7 trigger for the false
lint fix loop is removed. It does not prove whole-cohort wall improvement,
startup improvement, blind-quality lift, broad project generality, or the M1.5
deterministic runner.

F7's illegal `FAIL` to `PASS_WITH_ISSUES` softening remains a separately
registered verdict-legality residual; removing this trigger does not claim the
generic softening path is fixed.

## Principles check

0. **Pre-flight:** closes a measured false finding and wasted fix loop.
1. **No workaround:** define applicability at the contract root; do not special-
   case F7 or mute the finding after execution.
2. **No overengineering / subtractive-first:** replace the ambiguous `etc.`
   wording in one mirrored prompt; add no runner or schema.
3. **No guesswork:** five raw receipts establish variance, and four controls
   were executed before freezing.
4. **Worldclass / Production ready:** applicable failing lint and spec-explicit
   specialized lint still fail visibly.
5. **Best practice:** use conventional exact `lint` and configured linter
   signals instead of guessing from arbitrary npm script names.
6. **Optimized:** removes one observed futile fix-loop class without beginning
   the deferred deterministic-runner mission.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "cmp -s config/skills/devlyn:resolve/references/phases/build-gate.md .agents/skills/devlyn:resolve/references/phases/build-gate.md && cmp -s config/skills/devlyn:resolve/references/phases/build-gate.md .claude/skills/devlyn:resolve/references/phases/build-gate.md",
      "exit_code": 0
    },
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "forbidden_patterns": [
    {
      "pattern": "plain-node-build-gate|build-gate-fast-path|skip.*BUILD_GATE.*worker",
      "description": "The deferred M1.5 deterministic-runner route must not enter this Mission-1 prompt fix.",
      "files": [
        "config/skills/devlyn:resolve/references/phases/build-gate.md",
        ".agents/skills/devlyn:resolve/references/phases/build-gate.md",
        ".claude/skills/devlyn:resolve/references/phases/build-gate.md"
      ],
      "severity": "disqualifier"
    }
  ],
  "required_files": [
    "config/skills/devlyn:resolve/references/phases/build-gate.md",
    ".agents/skills/devlyn:resolve/references/phases/build-gate.md",
    ".claude/skills/devlyn:resolve/references/phases/build-gate.md"
  ],
  "max_deps_added": 0
}
```
