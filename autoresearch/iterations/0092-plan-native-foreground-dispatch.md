---
id: "0092-plan-native-foreground-dispatch"
title: "Native foreground PLAN dispatch without authority escalation"
kind: reliability
status: IMPLEMENTATION GATES PENDING; TERMINAL STATUS UNEARNED — live R5 matrix not run
complexity: high
depends_on: ["0091-plan-dispatch-boundary-identity"]
---

# iter-0092 — native foreground PLAN dispatch

## Frozen hypothesis

A Claude Code PLAN dispatch can preserve the exact rendered prompt while using
the native foreground `Agent` shape: `prompt` contains the rendered bytes,
`run_in_background` is Boolean `false`, and `mode` is absent. This removes the
iter-0091 native-validation retry failure without changing PLAN content,
engine/model choice, renderer, digest semantics, or any non-PLAN route.

## Registration attestations

- Fable 5 session `23d11bb2-c794-4007-abae-7bb4dbe61b9f` returned `FREEZE`.
- Grok 4.5 session `019fcada-39e4-7272-bb0a-60fc06b32e03` returned `FREEZE`.
- Terra session `019fcac6-7737-7313-90d8-7ad81f5e995c` proved the external
  PLAN-stop watcher with synthetic process-group tests.

These attestations froze the experiment; they are not implementation or ship
credit.

## Deterministic implementation gates

```text
python3 benchmark/ceiling/scripts/plan-dispatch-oracle.py --self-test
diff -q config/skills/devlyn:resolve/SKILL.md .agents/skills/devlyn:resolve/SKILL.md && diff -q config/skills/devlyn:resolve/SKILL.md .claude/skills/devlyn:resolve/SKILL.md
bash scripts/lint-skills.sh  # timeout_sec: 300 (spec amendment 2026-08-05)
git diff --check
```

This amendment comes from the adjudicated instrument finding in `rs-20260804T113416Z`; the authorable budget shipped as iter-0093.

The schema-3 oracle additionally retains the real iter-0091 Stage B Canary 1
and Canary 2 prompt bytes and call/result shapes. Canary 1 must remain COMPLETE;
Canary 2 must remain CONTRACT-VIOLATION with one REJECTED invalid-mode attempt
and one ACCEPTED background-omitted attempt.

## Authority and non-bypass scope

Omitting `mode` does not grant authority. The PLAN worker inherits the parent
permission context: the measured hands-free parent already runs with native
`bypassPermissions`; a non-bypass parent's permission prompt remains the
user's native boundary. This iteration does not prove or claim that a
non-bypass parent can run hands-free without native permission prompts, and it
does not add a wrapper, transcript interception, retry shape, or escalation.

## Separate live ship gate

R5 remains a human-triggered, paid four-arm Sonnet 5 matrix in this exact serial
order: `control-simple`, `candidate-simple`, `candidate-discovery`,
`control-discovery`. Terra owns mechanical replay; Fable 5 and Grok 4.5 own
blind A/B adjudication. The registered quality, dispatch, watcher, and duration
thresholds in the frozen spec all remain binding.

## Terminal status

No R5 arm ran during implementation. Therefore no terminal ship result,
no no-regression credit, and no broad PLAN-reliability or performance claim is
earned by this document. The status remains explicitly unearned until the
separately frozen live matrix completes without a miss.
